#!/usr/bin/env python3
"""
KILO AGENT BRAIN - LLM Integration with Function Calling

This module adds the "brain" to Kilo's "hands" (tools).
It enables intelligent decision-making using LLM function calling.

CAPABILITIES:
- Analyzes cluster state intelligently
- Decides which tools to use
- Generates appropriate parameters
- Creates reasoned action proposals
"""

import json
import requests
from typing import Dict, List, Any, Optional


class KiloAgentBrain:
    """
    The intelligence layer for Kilo Agent
    Uses LLM function calling to make smart decisions
    """

    def __init__(self, llm_url: str = "http://localhost:11434", model: str = "Phi-3-mini-4k-instruct-q4.gguf"):
        self.llm_url = llm_url
        self.model = model
        self.conversation_history = []
        # llama.cpp uses OpenAI-compatible API

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Minimal tool schemas for low-context models like Phi-3"""
        return [
            {
                "name": "kubectl_scale",
                "description": "Scale deployment. Use EXACT deployment name from list provided.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "deployment": {
                            "type": "string",
                            "description": "EXACT deployment name from the cluster (not a placeholder)"
                        },
                        "replicas": {
                            "type": "integer",
                            "description": "Number of replicas (1-10)"
                        }
                    },
                    "required": ["deployment", "replicas"]
                }
            }
        ]

    def analyze_cluster_state(self, cluster_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyze cluster state and decide what actions to propose
        Uses LLM with function calling to make intelligent decisions

        Returns: List of action proposals with tool calls and reasoning
        """
        # Very explicit prompt for Phi-3
        system_prompt = "Use kubectl_scale with deployment names from the list. DO NOT invent names."

        # Extract deployment names
        deployment_names = cluster_data.get("deployment_names", [])

        if deployment_names and len(deployment_names) > 0:
            # List first 10 deployments
            names_list = deployment_names[:10]
            user_prompt = f"Available deployments: {', '.join(names_list)}.\n\nPick ONE from this list and scale it to 3 replicas."
        else:
            user_prompt = "No deployments found."

        # Call LLM with function calling
        try:
            proposals = self._call_llm_with_functions(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                tools=self.get_tool_schemas()
            )
            return proposals
        except Exception as e:
            print(f"⚠️ LLM analysis error: {e}")
            return []

    def analyze_issue(self, issue_description: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analyze a specific issue and propose a solution

        Args:
            issue_description: Description of the issue
            context: Additional context (pod names, logs, etc.)

        Returns: Action proposal with tool, params, and reasoning
        """
        system_prompt = "You are Kilo. Analyze issues and propose solutions using REAL resource names from the context."

        # Extract actual names from context if available
        context_summary = str(context).replace('\n', ' ')[:400]
        user_prompt = f"Issue: {issue_description}\nContext: {context_summary}\n\nPropose solution with ACTUAL resource names (not placeholders)."

        try:
            proposals = self._call_llm_with_functions(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                tools=self.get_tool_schemas()
            )
            return proposals[0] if proposals else None
        except Exception as e:
            print(f"⚠️ Issue analysis error: {e}")
            return None

    def _call_llm_with_functions(self, system_prompt: str, user_prompt: str,
                                  tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Call LLM with function calling support

        This uses llama.cpp's OpenAI-compatible API with function calling
        Returns list of proposed actions
        """
        # Build messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # Convert tool schemas to OpenAI format for llama.cpp
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"]
                }
            }
            for tool in tools
        ]

        # Call llama.cpp server (OpenAI-compatible endpoint)
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": openai_tools,
            # Note: tool_choice might not be supported by all llama.cpp versions
            "temperature": 0.0,  # Deterministic - no creativity!
            "max_tokens": 200,    # Keep it short
            "top_p": 0.1         # Very focused on most likely tokens
        }

        try:
            response = requests.post(
                f"{self.llm_url}/v1/chat/completions",  # OpenAI-compatible endpoint
                json=payload,
                timeout=60
            )

            # If error, print details for debugging
            if response.status_code != 200:
                print(f"⚠️ LLM Error Response: {response.text[:500]}")

            response.raise_for_status()

            result = response.json()

            # Extract function calls from OpenAI-format response
            if "choices" not in result or not result["choices"]:
                return []

            message = result["choices"][0].get("message", {})
            tool_calls = message.get("tool_calls", [])

            if not tool_calls:
                # No function calls, check if there's text reasoning
                text_response = message.get("content", "")
                if text_response:
                    print(f"LLM response (no tool calls): {text_response}")
                return []

            # Convert tool calls to action proposals
            proposals = []
            for call in tool_calls:
                # OpenAI format: call.function.name and call.function.arguments
                function_data = call.get("function", {})
                function_name = function_data.get("name")

                # Arguments might be JSON string or dict
                arguments = function_data.get("arguments", {})
                if isinstance(arguments, str):
                    import json as json_lib
                    try:
                        arguments = json_lib.loads(arguments)
                    except:
                        print(f"⚠️ Failed to parse function arguments: {arguments}")
                        continue

                # Map tool call to action proposal
                action_type = self._infer_action_type(function_name, arguments)

                proposal = {
                    "tool": function_name,
                    "params": arguments,
                    "action_type": action_type,
                    "reasoning": message.get("content", f"LLM proposed {function_name}"),
                    "priority": self._infer_priority(function_name, arguments)
                }
                proposals.append(proposal)

            return proposals

        except requests.exceptions.RequestException as e:
            print(f"⚠️ LLM request failed: {e}")
            return []
        except Exception as e:
            print(f"⚠️ LLM processing error: {e}")
            return []

    def _infer_action_type(self, tool_name: str, params: Dict[str, Any]) -> str:
        """Infer a descriptive action type from tool name and params"""
        action_types = {
            "kubectl_get": "gather_info",
            "analyze_logs": "diagnose_issue",
            "check_health": "health_check",
            "kubectl_scale": "scale_deployment",
            "kubectl_exec": "execute_command",
            "kubectl_apply": "apply_config",
            "modify_deployment_yaml": "update_deployment"
        }
        return action_types.get(tool_name, "unknown_action")

    def _infer_priority(self, tool_name: str, params: Dict[str, Any]) -> str:
        """Infer priority based on tool and context"""
        # Read-only tools are lower priority
        if tool_name in ["kubectl_get", "check_health", "analyze_logs"]:
            return "low"

        # Scaling and modifications are medium
        if tool_name in ["kubectl_scale", "modify_deployment_yaml"]:
            return "medium"

        # Exec and apply are higher priority (more impactful)
        if tool_name in ["kubectl_exec", "kubectl_apply"]:
            return "high"

        return "medium"

    def chat(self, user_message: str) -> str:
        """
        Have a conversation with the LLM (for conversational interface)
        This is separate from function calling - used for user interaction
        """
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        payload = {
            "model": self.model,
            "messages": self.conversation_history,
            "temperature": 0.7,
            "max_tokens": 500
        }

        try:
            response = requests.post(
                f"{self.llm_url}/v1/chat/completions",  # OpenAI-compatible endpoint
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            result = response.json()
            # OpenAI format: result.choices[0].message.content
            assistant_message = result.get("choices", [{}])[0].get("message", {}).get("content", "")

            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })

            return assistant_message

        except Exception as e:
            return f"Error communicating with LLM: {e}"


def get_kilo_brain(llm_url: str = "http://localhost:11434", model: str = "Phi-3-mini-4k-instruct-q4.gguf"):
    """Factory function to get Kilo brain instance"""
    return KiloAgentBrain(llm_url=llm_url, model=model)


if __name__ == "__main__":
    # Test the brain
    brain = KiloAgentBrain()
    print("Using llama.cpp server at http://localhost:8080")

    # Test cluster analysis
    test_cluster_data = {
        "pods": {
            "nginx-abc123": {
                "status": "CrashLoopBackOff",
                "restarts": 5
            },
            "redis-def456": {
                "status": "Running",
                "restarts": 0
            }
        },
        "deployments": {
            "nginx": {
                "replicas": "0/3",
                "available": 0
            }
        }
    }

    print("Testing cluster analysis...")
    proposals = brain.analyze_cluster_state(test_cluster_data)

    if proposals:
        print(f"\n✓ Got {len(proposals)} proposals:")
        for p in proposals:
            print(f"  - {p['action_type']} via {p['tool']}: {p['reasoning']}")
    else:
        print("  No proposals generated (LLM may not be running)")
