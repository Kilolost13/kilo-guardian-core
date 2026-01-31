#!/usr/bin/env python3
"""
Kilo Chat Interface V2 - WITH CLUSTER AWARENESS
Now Kilo can actually SEE your HP cluster and give specific advice!
"""

import tkinter as tk
from tkinter import scrolledtext, messagebox
import requests
import json
import threading
import subprocess
import os

LLM_URL = "http://localhost:11434"
KUBECONFIG = os.path.expanduser("~/.kube/hp-k3s-config")
HP_IP = "192.168.68.56"

class KiloChat:
    def __init__(self, root):
        self.root = root
        self.root.title("💬 Chat with Kilo AI (Cluster-Aware)")
        self.root.geometry("800x700")

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
            text="Connected to Kilo AI Brain + HP Cluster",
            font=("Arial", 9),
            fg="green",
            anchor="w"
        )
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

        # Chat history
        self.conversation_history = []

        # Welcome message
        self.add_message("KILO", "Hello! I'm Kilo, your cluster-aware AI assistant. I can see your HP k3s cluster and give you specific advice. How can I help you today?")

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

    def send_message(self):
        """Send user message to AI and get response"""
        message = self.input_box.get().strip()
        if not message:
            return

        # Clear input
        self.input_box.delete(0, tk.END)

        # Add user message to display
        self.add_message("YOU", message)

        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": message})

        # Disable send button while processing
        self.send_button.config(state=tk.DISABLED, text="Checking cluster...")
        self.status_label.config(text="Querying HP cluster...", fg="orange")

        # Get AI response in background thread
        threading.Thread(target=self.get_ai_response, daemon=True).start()

    def get_ai_response(self):
        """Get response from AI brain with cluster context"""
        try:
            # Get current cluster state
            cluster_context = self.get_cluster_context()

            # Update status
            self.root.after(0, lambda: self.status_label.config(text="Kilo is thinking...", fg="orange"))

            # Build enhanced system prompt with cluster awareness
            system_prompt = f"""You are Kilo, an AI assistant with REAL-TIME access to the user's Kubernetes cluster.

IMPORTANT: You can SEE the actual cluster state below. Use this information to give SPECIFIC, ACCURATE advice.

{cluster_context}

Your capabilities:
- You can see what's ACTUALLY running (not just guess)
- Give specific advice based on REAL cluster state
- Don't suggest things that are already installed/running
- Be concise and helpful

Architecture:
- Beelink (192.168.68.60): Where you run, the overseer
- HP (192.168.68.56): K3s cluster worker node
- Services: 13 microservices (ai-brain, gateway, frontend, etc.)
- Already installed: Helm, Prometheus, Grafana

Answer the user's question based on the ACTUAL cluster state shown above."""

            # Prepare request with cluster context
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
                timeout=90  # Longer timeout since we're doing more work
            )

            if response.status_code == 200:
                data = response.json()
                ai_message = data['choices'][0]['message']['content']

                # Add to conversation history
                self.conversation_history.append({"role": "assistant", "content": ai_message})

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
        self.status_label.config(text="Connected to Kilo AI Brain + HP Cluster", fg="green")
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
