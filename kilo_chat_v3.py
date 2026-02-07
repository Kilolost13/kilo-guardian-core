#!/usr/bin/env python3
"""
Kilo Chat Interface V3 - CLUSTER-AWARE + MEMORY + COMMAND ROUTING
Now Kilo can:
- SEE your HP cluster (v2 feature)
- REMEMBER your preferences (NEW)
- UNDERSTAND command intent (NEW)
- LEARN from you (NEW)
"""

import tkinter as tk
from tkinter import scrolledtext, messagebox
import requests
import json
import threading
import subprocess
import os

# Import new modules from core
from core.kilo_memory import get_kilo_memory
from core.kilo_router import get_kilo_router

# Import configuration
from shared.config import LLM_URL, KUBECONFIG, HP_IP

class KiloChat:
    def __init__(self, root):
        self.root = root
        self.root.title("💬 Chat with Kilo AI (Smart + Cluster-Aware)")
        self.root.geometry("800x700")

        # Initialize memory and router
        self.memory = get_kilo_memory()
        self.router = get_kilo_router()

        # Chat history display
        self.chat_display = scrolledtext.ScrolledText(
            root,
            wrap=tk.WORD,
            font=("Arial", 11),
            bg="#1e1e1e",
            fg="#00ff00",
            insertbackground="white"
        )
        self.chat_display.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Input frame
        input_frame = tk.Frame(root)
        input_frame.pack(padx=10, pady=5, fill=tk.X)

        tk.Label(input_frame, text="You:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)

        self.input_box = tk.Entry(input_frame, font=("Arial", 11))
        self.input_box.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.input_box.bind("<Return>", lambda e: self.send_message())

        self.send_button = tk.Button(
            input_frame,
            text="Send",
            bg="#28a745",
            fg="white",
            font=("Arial", 10, "bold"),
            command=self.send_message
        )
        self.send_button.pack(side=tk.LEFT, padx=5)

        # Status bar
        self.status_label = tk.Label(
            root,
            text="Connected to Kilo AI Brain + HP Cluster + Memory",
            font=("Arial", 9),
            fg="green",
            anchor="w"
        )
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

        # Chat history
        self.conversation_history = []

        # Welcome message
        welcome_msg = """Hello! I'm Kilo V3, your intelligent cluster-aware AI assistant.

NEW FEATURES:
✅ I can SEE your HP k3s cluster in real-time
✅ I can REMEMBER your preferences
✅ I can UNDERSTAND different command types
✅ I can LEARN from you

Try saying:
- "What's running?" (cluster status)
- "Teach: I prefer TinyLlama for simple questions" (learn preference)
- "What did I tell you about TinyLlama?" (recall memory)
- "What should I add?" (smart advice based on what you already have)

How can I help you today?"""

        self.add_message("KILO", welcome_msg)

        # Focus on input
        self.input_box.focus()

    def add_message(self, sender, message):
        """Add a message to the chat display"""
        if sender == "YOU":
            prefix = "YOU: "
            self.chat_display.insert(tk.END, f"\n{prefix}", "user")
            self.chat_display.insert(tk.END, f"{message}\n", "user_text")
            self.chat_display.tag_config("user", foreground="#00bfff", font=("Arial", 11, "bold"))
            self.chat_display.tag_config("user_text", foreground="#ffffff")
        elif sender == "SYSTEM":
            prefix = "SYSTEM: "
            self.chat_display.insert(tk.END, f"\n{prefix}", "system")
            self.chat_display.insert(tk.END, f"{message}\n", "system_text")
            self.chat_display.tag_config("system", foreground="#ffc107", font=("Arial", 11, "bold"))
            self.chat_display.tag_config("system_text", foreground="#ffc107")
        else:
            prefix = "KILO: "
            self.chat_display.insert(tk.END, f"\n{prefix}", "kilo")
            self.chat_display.insert(tk.END, f"{message}\n", "kilo_text")
            self.chat_display.tag_config("kilo", foreground="#00ff00", font=("Arial", 11, "bold"))
            self.chat_display.tag_config("kilo_text", foreground="#00ff00")

        self.chat_display.see(tk.END)

    def run_kubectl(self, args):
        """Run kubectl command and return output"""
        try:
            env = os.environ.copy()
            env['KUBECONFIG'] = KUBECONFIG
            result = subprocess.run(
                ["kubectl"] + args,
                capture_output=True,
                text=True,
                timeout=10,
                env=env
            )
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return f"Error: {result.stderr.strip()}"
        except Exception as e:
            return f"Error: {str(e)}"

    def get_cluster_context(self):
        """Gather current cluster state to feed to AI"""
        context_parts = []

        context_parts.append("=== CURRENT HP CLUSTER STATE ===")

        # Check if HP is reachable
        ping_result = subprocess.run(
            ["ping", "-c", "1", "-W", "2", HP_IP],
            capture_output=True
        )

        if ping_result.returncode != 0:
            context_parts.append(f"HP Cluster ({HP_IP}): OFFLINE - Not reachable")
            return "\n".join(context_parts)

        context_parts.append(f"HP Cluster ({HP_IP}): ONLINE")

        # Get nodes
        nodes = self.run_kubectl(["get", "nodes", "--no-headers"])
        if nodes and "Error" not in nodes:
            node_count = len(nodes.split('\n'))
            context_parts.append(f"\nNodes: {node_count} node(s)")
            context_parts.append(nodes)
        else:
            context_parts.append("\nNodes: Unable to query (cluster may be down)")

        # Get deployments
        deployments = self.run_kubectl(["get", "deployments", "-n", "default", "--no-headers"])
        if deployments and "Error" not in deployments:
            lines = [l for l in deployments.split('\n') if l.strip()]
            total_deployments = len(lines)
            running_deployments = len([l for l in lines if '/0' not in l.split()[1]])

            context_parts.append(f"\nDeployments: {total_deployments} total")
            context_parts.append(f"Currently running: {running_deployments}/{total_deployments}")
            context_parts.append("\nDeployment details:")
            context_parts.append(deployments)
        else:
            context_parts.append("\nDeployments: Unable to query")

        # Get pods
        pods = self.run_kubectl(["get", "pods", "-n", "default", "--no-headers"])
        if pods and "Error" not in pods:
            if not pods or pods == "No resources found":
                context_parts.append("\nPods: 0 (all services stopped)")
            else:
                lines = [l for l in pods.split('\n') if l.strip()]
                total_pods = len(lines)
                running_pods = len([l for l in lines if 'Running' in l and '1/1' in l])
                context_parts.append(f"\nPods: {running_pods}/{total_pods} running")
                context_parts.append("Pod details:")
                context_parts.append(pods)
        else:
            context_parts.append("\nPods: Unable to query")

        # Get services
        services = self.run_kubectl(["get", "services", "-n", "default", "--no-headers"])
        if services and "Error" not in services:
            service_lines = [l for l in services.split('\n') if l.strip() and 'kubernetes' not in l.lower()]
            context_parts.append(f"\nServices: {len(service_lines)} exposed")
            # Just list service names
            for line in service_lines:
                parts = line.split()
                if len(parts) > 0:
                    context_parts.append(f"  - {parts[0]}")

        context_parts.append("\n=== END CLUSTER STATE ===")

        return "\n".join(context_parts)

    def handle_teach_command(self, message):
        """Handle a teach/remember command"""
        fact_key, fact_value, category = self.router.parse_teach_command(message)

        if not fact_key or not fact_value:
            return "I couldn't understand what you want me to learn. Try: 'Teach: preference is value' or 'Remember that my preference is value'"

        success = self.memory.teach_fact(fact_key, fact_value, category)

        if success:
            return f"✓ Learned! I'll remember that your {fact_key} is '{fact_value}' ({category} category)"
        else:
            return "Sorry, I had trouble storing that fact. Please try again."

    def handle_recall_command(self, message):
        """Handle a recall/lookup command"""
        fact_key = self.router.parse_recall_command(message)

        if not fact_key:
            return "What would you like me to recall?"

        fact_value = self.memory.recall_fact(fact_key)

        if fact_value:
            return f"I remember: Your {fact_key} is '{fact_value}'"
        else:
            return f"I don't have any stored information about '{fact_key}'. You can teach me by saying 'Teach: {fact_key} is ...'"

    def send_message(self):
        """Send user message to AI and get response"""
        message = self.input_box.get().strip()
        if not message:
            return

        # Clear input
        self.input_box.delete(0, tk.END)

        # Add user message to display
        self.add_message("YOU", message)

        # Classify intent
        intent, extracted_data = self.router.classify_intent(message)

        # Log interaction
        self.memory.log_interaction(intent, message)

        # Handle teach/recall commands directly (no AI needed)
        if intent == "teach":
            response = self.handle_teach_command(message)
            self.add_message("KILO", response)
            return

        if intent == "recall":
            response = self.handle_recall_command(message)
            self.add_message("KILO", response)
            return

        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": message})

        # Disable send button while processing
        if self.router.should_query_cluster(intent):
            self.send_button.config(state=tk.DISABLED, text="Checking cluster...")
            self.status_label.config(text="Querying HP cluster...", fg="orange")
        else:
            self.send_button.config(state=tk.DISABLED, text="Thinking...")
            self.status_label.config(text="Kilo is thinking...", fg="orange")

        # Get AI response in background thread
        threading.Thread(target=self.get_ai_response, args=(intent,), daemon=True).start()

    def get_ai_response(self, intent):
        """Get response from AI brain with cluster context and memory"""
        try:
            # Get cluster context if needed
            cluster_context = ""
            if self.router.should_query_cluster(intent):
                cluster_context = self.get_cluster_context()

            # Update status
            self.root.after(0, lambda: self.status_label.config(text="Kilo is thinking...", fg="orange"))

            # Get memory summary
            memory_summary = self.memory.get_memory_summary()

            # Build enhanced system prompt with cluster awareness AND memory
            system_prompt = f"""You are Kilo, an intelligent AI assistant with REAL-TIME access to the user's Kubernetes cluster AND memory of their preferences.

COMMAND INTENT: {intent}
(This tells you what type of request the user is making: status, advice, troubleshoot, etc.)

"""

            if cluster_context:
                system_prompt += f"{cluster_context}\n\n"

            if memory_summary:
                system_prompt += f"{memory_summary}\n\n"

            system_prompt += """WHAT YOU CAN SEE:
- Which deployments/pods exist in the cluster
- Which services are running vs stopped (replicas 0/0 vs 1/1)
- Node status (online/offline)
- Basic kubectl output (pod names, status, replicas)
- User preferences stored in your memory

WHAT YOU CANNOT SEE (DO NOT CLAIM TO HAVE ACCESS):
- Data INSIDE pods (databases, files, application data)
- Logs (unless explicitly fetched with kubectl logs)
- Metrics from applications (you only see deployment metadata)
- Financial data, user data, or any application-level information
- Prometheus/Grafana dashboards (you see they exist, not their data)

CRITICAL RULES:
- NEVER claim you can "access pod data" or "analyze data from pods"
- NEVER make up analysis of data you cannot see
- If asked about pod contents/data, say: "I can only see that the pod exists and its status. I cannot access data inside pods."
- Be honest about limitations - don't hallucinate capabilities
- You REMEMBER user preferences from memory system
- You UNDERSTAND command intent
- Give advice based on what you CAN see

Architecture:
- Beelink (192.168.68.60): Where you run, the overseer
- HP (192.168.68.56): K3s cluster worker node
- Services: 13 microservices (ai-brain, gateway, frontend, etc.)
- Already installed: Helm, Prometheus, Grafana (but you CANNOT see their data)

Answer based on ACTUAL cluster state you can see and LEARNED preferences."""

            # Prepare request
            payload = {
                "model": "model",
                "messages": [
                    {"role": "system", "content": system_prompt}
                ] + self.conversation_history[-10:],
                "max_tokens": 512,
                "temperature": 0.7
            }

            # Send request
            response = requests.post(
                f"{LLM_URL}/v1/chat/completions",
                json=payload,
                timeout=90
            )

            if response.status_code == 200:
                data = response.json()
                ai_message = data['choices'][0]['message']['content']

                # Add to conversation history
                self.conversation_history.append({"role": "assistant", "content": ai_message})

                # Log the interaction with response
                self.memory.log_interaction(
                    intent,
                    self.conversation_history[-2]["content"],  # User message
                    ai_message,
                    cluster_context if cluster_context else "N/A"
                )

                # Update UI on main thread
                self.root.after(0, lambda: self.display_ai_response(ai_message))
            else:
                error_msg = f"Error: Server returned {response.status_code}"
                self.root.after(0, lambda: self.display_error(error_msg))

        except requests.exceptions.Timeout:
            self.root.after(0, lambda: self.display_error("Request timed out. The AI might be overloaded."))
        except requests.exceptions.ConnectionError:
            self.root.after(0, lambda: self.display_error("Cannot connect to AI brain. Is llama-server running?"))
        except Exception as e:
            self.root.after(0, lambda: self.display_error(f"Error: {str(e)}"))

    def display_ai_response(self, message):
        """Display AI response (called on main thread)"""
        self.add_message("KILO", message)
        self.send_button.config(state=tk.NORMAL, text="Send")
        self.status_label.config(text="Connected to Kilo AI Brain + HP Cluster + Memory", fg="green")
        self.input_box.focus()

    def display_error(self, error_msg):
        """Display error message (called on main thread)"""
        self.add_message("SYSTEM", f"⚠️ {error_msg}")
        self.send_button.config(state=tk.NORMAL, text="Send")
        self.status_label.config(text="Error - Check connection", fg="red")
        self.input_box.focus()


if __name__ == "__main__":
    root = tk.Tk()
    app = KiloChat(root)
    root.mainloop()
