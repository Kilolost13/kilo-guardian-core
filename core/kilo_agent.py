#!/usr/bin/env python3
"""
KILO AUTONOMOUS AGENT - The Real Deal
A proactive AI agent that can actually DO things, not just chat.

CAPABILITIES:
- Proactive monitoring of k3s cluster
- Autonomous decision-making
- Tool use (kubectl, file ops, code modification)
- Propose & approve workflow
- Learning from interactions
- Gradual autonomy granting

PHILOSOPHY:
- Propose → Approve → Execute → Learn
- Build trust through successful actions
- Earn autonomy for proven patterns
"""

import os
import json
import time
import threading
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
import requests

# Import Kilo components
from kilo_memory import get_kilo_memory
from kilo_router import get_kilo_router
from kilo_pod_access import get_pod_access
from kilo_agent_brain import get_kilo_brain


class KiloAgent:
    """
    The Real Kilo - A proactive AI agent with actual capabilities

    This is NOT a chatbot. This is an agent that:
    1. Monitors your k3s cluster continuously
    2. Detects issues and opportunities
    3. Proposes specific actions with reasoning
    4. Executes approved actions using real tools
    5. Learns from successes and failures
    6. Earns autonomy for proven patterns
    """

    def __init__(self, llm_url="http://localhost:11434", kubeconfig=None, model="Phi-3-mini-4k-instruct-q4.gguf"):
        self.llm_url = llm_url
        self.model = model
        self.kubeconfig = kubeconfig or os.path.expanduser("~/.kube/hp-k3s-config")
        os.environ['KUBECONFIG'] = self.kubeconfig

        # Initialize components
        self.memory = get_kilo_memory()
        self.router = get_kilo_router()
        self.pod_access = get_pod_access()
        self.brain = get_kilo_brain(llm_url=llm_url, model=model)  # The intelligence layer

        # Agent state
        self.monitoring = False
        self.actions_proposed = []
        self.actions_pending = []
        self.actions_completed = []
        self.autonomous_patterns = []  # Patterns that can run without approval

        # Tool registry
        self.tools = self._register_tools()

        # Monitoring state
        self.last_cluster_state = {}
        self.issues_detected = []

    def _register_tools(self) -> Dict[str, Callable]:
        """
        Register all tools the agent can use
        These are the agent's HANDS - what it can actually DO
        """
        return {
            # K3s cluster operations
            "kubectl_get": self.tool_kubectl_get,
            "kubectl_apply": self.tool_kubectl_apply,
            "kubectl_delete": self.tool_kubectl_delete,
            "kubectl_scale": self.tool_kubectl_scale,
            "kubectl_exec": self.tool_kubectl_exec,

            # File operations
            "read_file": self.tool_read_file,
            "write_file": self.tool_write_file,
            "modify_file": self.tool_modify_file,

            # Code operations
            "modify_deployment_yaml": self.tool_modify_deployment,
            "modify_service_yaml": self.tool_modify_service,

            # Analysis
            "analyze_logs": self.tool_analyze_logs,
            "check_health": self.tool_check_health,

            # Git operations
            "git_commit": self.tool_git_commit,
        }

    # ==================== TOOL IMPLEMENTATIONS ====================
    # These are the agent's actual capabilities

    def tool_kubectl_get(self, resource: str, namespace: str = "default", output: str = "yaml") -> Dict[str, Any]:
        """Get k3s resource - READ ONLY, always safe"""
        try:
            cmd = ["kubectl", "get", resource, "-n", namespace, "-o", output]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "tool": "kubectl_get",
                "safe": True  # Read-only, always safe
            }
        except Exception as e:
            return {"success": False, "error": str(e), "tool": "kubectl_get"}

    def tool_kubectl_apply(self, yaml_content: str, namespace: str = "default") -> Dict[str, Any]:
        """Apply k3s resource - WRITE OPERATION, needs approval"""
        try:
            # Write to temp file
            temp_file = f"/tmp/kilo_apply_{int(time.time())}.yaml"
            with open(temp_file, 'w') as f:
                f.write(yaml_content)

            cmd = ["kubectl", "apply", "-f", temp_file, "-n", namespace]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            # Cleanup
            os.remove(temp_file)

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "tool": "kubectl_apply",
                "safe": False,  # Write operation, needs approval
                "yaml_applied": yaml_content
            }
        except Exception as e:
            return {"success": False, "error": str(e), "tool": "kubectl_apply"}

    def tool_kubectl_delete(self, resource: str, name: str, namespace: str = "default") -> Dict[str, Any]:
        """Delete k3s resource - DESTRUCTIVE, needs approval"""
        try:
            cmd = ["kubectl", "delete", resource, name, "-n", namespace]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "tool": "kubectl_delete",
                "safe": False,  # Destructive, needs approval
                "deleted": f"{resource}/{name}"
            }
        except Exception as e:
            return {"success": False, "error": str(e), "tool": "kubectl_delete"}

    def tool_kubectl_scale(self, deployment: str, replicas: int, namespace: str = "default") -> Dict[str, Any]:
        """Scale deployment - WRITE OPERATION, needs approval"""
        try:
            cmd = ["kubectl", "scale", f"deployment/{deployment}",
                   f"--replicas={replicas}", "-n", namespace]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "tool": "kubectl_scale",
                "safe": False,  # Write operation, needs approval
                "action": f"Scaled {deployment} to {replicas} replicas"
            }
        except Exception as e:
            return {"success": False, "error": str(e), "tool": "kubectl_scale"}

    def tool_kubectl_exec(self, pod: str, command: List[str], namespace: str = "default") -> Dict[str, Any]:
        """Execute command in pod - POTENTIALLY DANGEROUS, needs approval"""
        try:
            cmd = ["kubectl", "exec", pod, "-n", namespace, "--"] + command
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "tool": "kubectl_exec",
                "safe": False,  # Execution, needs approval
                "command": " ".join(command)
            }
        except Exception as e:
            return {"success": False, "error": str(e), "tool": "kubectl_exec"}

    def tool_read_file(self, filepath: str) -> Dict[str, Any]:
        """Read file - READ ONLY, always safe"""
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            return {
                "success": True,
                "content": content,
                "tool": "read_file",
                "safe": True  # Read-only, always safe
            }
        except Exception as e:
            return {"success": False, "error": str(e), "tool": "read_file"}

    def tool_write_file(self, filepath: str, content: str, backup: bool = True) -> Dict[str, Any]:
        """Write file - WRITE OPERATION, needs approval"""
        try:
            # Backup if requested and file exists
            if backup and os.path.exists(filepath):
                backup_path = f"{filepath}.backup.{int(time.time())}"
                with open(filepath, 'r') as f:
                    with open(backup_path, 'w') as bf:
                        bf.write(f.read())

            # Write new content
            with open(filepath, 'w') as f:
                f.write(content)

            return {
                "success": True,
                "tool": "write_file",
                "safe": False,  # Write operation, needs approval
                "filepath": filepath,
                "backup": backup_path if backup else None
            }
        except Exception as e:
            return {"success": False, "error": str(e), "tool": "write_file"}

    def tool_modify_file(self, filepath: str, old_text: str, new_text: str) -> Dict[str, Any]:
        """Modify file content - WRITE OPERATION, needs approval"""
        try:
            with open(filepath, 'r') as f:
                content = f.read()

            if old_text not in content:
                return {
                    "success": False,
                    "error": f"Text not found in file: {old_text[:50]}...",
                    "tool": "modify_file"
                }

            new_content = content.replace(old_text, new_text)

            # Create backup
            backup_path = f"{filepath}.backup.{int(time.time())}"
            with open(backup_path, 'w') as f:
                f.write(content)

            # Write modified content
            with open(filepath, 'w') as f:
                f.write(new_content)

            return {
                "success": True,
                "tool": "modify_file",
                "safe": False,  # Write operation, needs approval
                "filepath": filepath,
                "backup": backup_path,
                "changes": f"Replaced {len(old_text)} chars with {len(new_text)} chars"
            }
        except Exception as e:
            return {"success": False, "error": str(e), "tool": "modify_file"}

    def tool_modify_deployment(self, deployment_name: str, modifications: Dict[str, Any],
                               namespace: str = "default") -> Dict[str, Any]:
        """Modify deployment YAML - WRITE OPERATION, needs approval"""
        # This is a high-level wrapper that:
        # 1. Gets current deployment YAML
        # 2. Modifies it according to specs
        # 3. Applies the changes
        try:
            # Get current deployment
            result = self.tool_kubectl_get(f"deployment/{deployment_name}", namespace, "yaml")
            if not result["success"]:
                return result

            import yaml
            deployment = yaml.safe_load(result["output"])

            # Apply modifications
            for key, value in modifications.items():
                if key == "replicas":
                    deployment["spec"]["replicas"] = value
                elif key == "image":
                    deployment["spec"]["template"]["spec"]["containers"][0]["image"] = value
                elif key == "env":
                    deployment["spec"]["template"]["spec"]["containers"][0]["env"] = value
                # Add more modification types as needed

            # Convert back to YAML
            new_yaml = yaml.dump(deployment)

            return {
                "success": True,
                "tool": "modify_deployment",
                "safe": False,  # Write operation, needs approval
                "deployment": deployment_name,
                "modifications": modifications,
                "new_yaml": new_yaml,
                "ready_to_apply": True
            }
        except Exception as e:
            return {"success": False, "error": str(e), "tool": "modify_deployment"}

    def tool_modify_service(self, service_name: str, modifications: Dict[str, Any],
                           namespace: str = "default") -> Dict[str, Any]:
        """Modify service YAML - similar to deployment modification"""
        # Similar implementation as modify_deployment
        pass

    def tool_analyze_logs(self, pod: str, namespace: str = "default",
                         lines: int = 100) -> Dict[str, Any]:
        """Analyze pod logs - READ ONLY, always safe"""
        try:
            cmd = ["kubectl", "logs", pod, "-n", namespace, f"--tail={lines}"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            # Simple analysis
            logs = result.stdout
            issues = []
            if "error" in logs.lower():
                issues.append("Errors detected in logs")
            if "exception" in logs.lower():
                issues.append("Exceptions detected in logs")
            if "failed" in logs.lower():
                issues.append("Failures detected in logs")

            return {
                "success": result.returncode == 0,
                "logs": logs,
                "issues": issues,
                "tool": "analyze_logs",
                "safe": True  # Read-only, always safe
            }
        except Exception as e:
            return {"success": False, "error": str(e), "tool": "analyze_logs"}

    def tool_check_health(self, namespace: str = "default") -> Dict[str, Any]:
        """Check cluster health - READ ONLY, always safe"""
        try:
            health = {
                "nodes": self.tool_kubectl_get("nodes", namespace="all"),
                "pods": self.tool_kubectl_get("pods", namespace),
                "deployments": self.tool_kubectl_get("deployments", namespace),
            }

            # Analyze health
            issues = []
            if "NotReady" in health["nodes"]["output"]:
                issues.append("Some nodes are NotReady")
            if "CrashLoopBackOff" in health["pods"]["output"]:
                issues.append("Some pods are in CrashLoopBackOff")
            if "0/" in health["deployments"]["output"]:
                issues.append("Some deployments have 0 replicas")

            return {
                "success": True,
                "health": health,
                "issues": issues,
                "tool": "check_health",
                "safe": True  # Read-only, always safe
            }
        except Exception as e:
            return {"success": False, "error": str(e), "tool": "check_health", "issues": []}

    def tool_git_commit(self, filepath: str, message: str) -> Dict[str, Any]:
        """Commit file changes to git - WRITE OPERATION, needs approval"""
        try:
            # Get the directory of the file
            directory = os.path.dirname(filepath)
            filename = os.path.basename(filepath)

            # Git add
            subprocess.run(["git", "add", filename], cwd=directory, check=True)

            # Git commit
            subprocess.run(["git", "commit", "-m", message], cwd=directory, check=True)

            return {
                "success": True,
                "tool": "git_commit",
                "safe": False,  # Write operation, needs approval
                "committed": filepath,
                "message": message
            }
        except Exception as e:
            return {"success": False, "error": str(e), "tool": "git_commit"}

    # ==================== AGENT CORE LOGIC ====================

    def propose_action(self, action_type: str, tool_name: str, params: Dict[str, Any],
                      reasoning: str, priority: str = "medium") -> Dict[str, Any]:
        """
        Propose an action to the user
        This is the key to the "propose & approve" workflow
        """
        # Check if we already have this exact proposal pending
        for existing in self.actions_pending:
            if (existing["type"] == action_type and
                existing["tool"] == tool_name and
                existing["params"] == params):
                # Already pending, don't duplicate
                return existing

        proposal = {
            "id": f"action_{int(time.time())}_{len(self.actions_proposed)}",
            "timestamp": datetime.now().isoformat(),
            "type": action_type,
            "tool": tool_name,
            "params": params,
            "reasoning": reasoning,
            "priority": priority,
            "status": "pending_approval",
            "autonomous": self._is_autonomous_pattern(action_type, tool_name, params)
        }

        self.actions_proposed.append(proposal)
        self.actions_pending.append(proposal)

        # Log to memory
        self.memory.log_interaction("system", "proposed_action", json.dumps(proposal))

        return proposal

    def execute_action(self, action_id: str, approved: bool = False) -> Dict[str, Any]:
        """
        Execute an approved action
        """
        # Find the action
        action = None
        for a in self.actions_pending:
            if a["id"] == action_id:
                action = a
                break

        if not action:
            return {"success": False, "error": "Action not found"}

        # Check if needs approval
        if not action["autonomous"] and not approved:
            return {"success": False, "error": "Action requires approval"}

        # Get the tool
        tool = self.tools.get(action["tool"])
        if not tool:
            return {"success": False, "error": f"Tool not found: {action['tool']}"}

        # Execute the tool
        try:
            result = tool(**action["params"])

            # Update action status
            action["status"] = "completed" if result["success"] else "failed"
            action["result"] = result
            action["executed_at"] = datetime.now().isoformat()

            # Move to completed
            self.actions_pending.remove(action)
            self.actions_completed.append(action)

            # Learn from this execution
            self._learn_from_action(action, result)

            # Log to memory
            self.memory.log_interaction("system", "executed_action", json.dumps({
                "action_id": action_id,
                "success": result["success"],
                "tool": action["tool"]
            }))

            return result

        except Exception as e:
            action["status"] = "error"
            action["error"] = str(e)
            return {"success": False, "error": str(e)}

    def _is_autonomous_pattern(self, action_type: str, tool_name: str, params: Dict[str, Any]) -> bool:
        """Check if this action matches an autonomous pattern"""
        for pattern in self.autonomous_patterns:
            if (pattern.get("action_type") == action_type and
                pattern.get("tool") == tool_name):
                # Could add more sophisticated matching here
                return True
        return False

    def _learn_from_action(self, action: Dict[str, Any], result: Dict[str, Any]):
        """Learn from executed actions to build autonomous patterns"""
        # If action was successful and user approved it, consider for autonomy
        if result["success"] and action["status"] == "completed":
            # Store successful pattern
            pattern = {
                "action_type": action["type"],
                "tool": action["tool"],
                "params_pattern": action["params"],
                "success_count": 1,
                "added_at": datetime.now().isoformat()
            }

            # Check if similar pattern exists
            for existing in self.autonomous_patterns:
                if (existing["action_type"] == pattern["action_type"] and
                    existing["tool"] == pattern["tool"]):
                    existing["success_count"] += 1
                    return

            # Add new pattern after 3 successful executions
            # This builds trust gradually
            if action.get("manual_approvals", 0) >= 3:
                self.autonomous_patterns.append(pattern)
                print(f"✓ Pattern granted autonomy: {pattern['action_type']} via {pattern['tool']}")

    def start_monitoring(self, interval: int = 30):
        """Start proactive monitoring loop"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, args=(interval,), daemon=True)
        self.monitor_thread.start()
        print(f"✓ Kilo monitoring started (interval: {interval}s)")

    def stop_monitoring(self):
        """Stop monitoring loop"""
        self.monitoring = False
        print("✓ Kilo monitoring stopped")

    def _monitoring_loop(self, interval: int):
        """
        Proactive monitoring loop - THE HEART OF THE AGENT
        This is what makes Kilo proactive instead of reactive
        """
        print("🔍 Kilo is now watching your cluster...")

        while self.monitoring:
            try:
                # Check cluster health
                health = self.tool_check_health()

                # Add null checks
                if health and health.get("success") and health.get("issues"):
                    # Issues detected! Propose actions
                    for issue in health["issues"]:
                        self._handle_issue(issue, health)

                # Check for other opportunities
                self._check_optimization_opportunities()

                # Sleep until next check
                time.sleep(interval)

            except Exception as e:
                print(f"⚠️ Monitoring error: {e}")
                time.sleep(interval)

    def _handle_issue(self, issue: str, health_data: Dict[str, Any]):
        """Handle a detected issue with CLEAR reasoning"""
        print(f"🔍 Detected issue: {issue}")

        # Handle specific issues with clear reasoning
        if "0 replicas" in issue:
            # Check ALL namespaces for 0/0 deployments
            for namespace in ["default", "kilo-guardian", "monitoring"]:
                deployments_result = self.tool_kubectl_get("deployments", namespace=namespace, output="wide")
                if deployments_result.get("success"):
                    lines = deployments_result["output"].split('\n')
                    for line in lines[1:]:  # Skip header
                        if line.strip() and "0/0" in line:
                            parts = line.split()
                            if parts and len(parts) >= 2:
                                deployment_name = parts[0]
                                ready = parts[1]

                                # Propose scaling with CLEAR reasoning
                                self.propose_action(
                                    action_type="fix_zero_replicas",
                                    tool_name="kubectl_scale",
                                    params={"deployment": deployment_name, "replicas": 1, "namespace": namespace},
                                    reasoning=f"Deployment '{deployment_name}' in namespace '{namespace}' has {ready} replicas. "
                                             f"This means it's not running at all - no pods serving traffic. "
                                             f"Scaling to 1 replica will start the service and make it functional.",
                                    priority="medium"
                                )
                                print(f"💡 Proposed fix for {namespace}/{deployment_name}: scale from 0 to 1 (currently offline)")

        elif "CrashLoopBackOff" in issue:
            # Handle pod crashes with analysis
            self.propose_action(
                action_type="diagnose_crashloop",
                tool_name="analyze_logs",
                params={"pod": "detected_pod", "namespace": "default"},
                reasoning=f"Pod is crashing repeatedly. Need to check logs to find root cause (config error, missing dependency, etc.)",
                priority="critical"
            )

        else:
            print(f"ℹ️ Issue noted but no action needed: {issue}")

    def _handle_issue_fallback(self, issue: str, health_data: Dict[str, Any]):
        """Fallback logic when brain doesn't respond"""
        # Simple rule-based fallback
        if "CrashLoopBackOff" in issue:
            self.propose_action(
                action_type="diagnose_crashloop",
                tool_name="analyze_logs",
                params={"pod": "unknown", "namespace": "default"},
                reasoning=f"Detected {issue}. Analyzing logs to find root cause.",
                priority="high"
            )

    def _check_optimization_opportunities(self):
        """Look for ACTUAL optimization opportunities - not random suggestions"""
        # DISABLED for now - the brain just proposes random scaling
        # Only use issue detection (0 replicas, crashes, etc.)
        # TODO: Re-enable when brain can actually detect real optimizations
        pass

    def _gather_cluster_data(self) -> Dict[str, Any]:
        """Gather current cluster data for analysis"""
        # Get pods, deployments, services, etc.
        data = {}

        try:
            # Get deployments in a simple format
            deployments_result = self.tool_kubectl_get("deployments", namespace="default", output="wide")
            if deployments_result.get("success"):
                # Parse deployment names from kubectl output
                lines = deployments_result["output"].split('\n')
                deployment_names = []
                for line in lines[1:]:  # Skip header
                    if line.strip():
                        parts = line.split()
                        if parts:
                            deployment_names.append(parts[0])

                data["deployment_names"] = deployment_names
                data["deployments_raw"] = deployments_result["output"]

            # Get pods
            pods_result = self.tool_kubectl_get("pods", namespace="default", output="wide")
            if pods_result.get("success"):
                data["pods_raw"] = pods_result["output"]

        except Exception as e:
            print(f"⚠️ Error gathering cluster data: {e}")

        return data


def get_kilo_agent():
    """Factory function to get Kilo agent instance"""
    return KiloAgent()


if __name__ == "__main__":
    # Test the agent
    agent = KiloAgent()

    # Example: Propose an action
    proposal = agent.propose_action(
        action_type="scale_deployment",
        tool_name="kubectl_scale",
        params={"deployment": "nginx", "replicas": 3, "namespace": "default"},
        reasoning="Current deployment has 1 replica but we need high availability",
        priority="medium"
    )

    print(f"Proposed action: {proposal}")

    # User would approve this
    # result = agent.execute_action(proposal["id"], approved=True)
