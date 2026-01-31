#!/usr/bin/env python3
"""
Kilo Agent UI - COMPLETE EDITION
The full autonomous agent with conversational interface!
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import json
import threading
import time
import re
from datetime import datetime

from kilo_agent import get_kilo_agent


class KiloAgentComplete:
    """
    Complete Kilo Agent UI with:
    - Cluster status view
    - Proposed actions (approve/deny)
    - Manual controls
    - CHAT INTERFACE (talk to Kilo!)
    """

    def __init__(self, root):
        self.root = root
        self.root.title("🤖 KILO AUTONOMOUS AGENT - Complete Edition")
        self.root.geometry("1800x1000")

        # Initialize agent
        self.agent = get_kilo_agent()

        # UI State
        self.selected_action = None
        self.cluster_data = {}
        self.chat_history = []
        self.hp_connected = False
        self.kilo_activity = "Starting up..."

        # Build UI
        self.build_ui()

        # Start monitoring
        self.agent.start_monitoring(interval=30)

        # Start UI update loop
        self.update_loop()

        # Welcome message
        self.chat_message("Kilo", "👋 Hey! I'm Kilo, your autonomous k3s agent. Ask me anything, tell me what to do, or just call me a doofus when I mess up!")

    def build_ui(self):
        """Build the complete interface"""

        # ===== TOP: Control Panel =====
        control_frame = tk.Frame(self.root, bg="#2c3e50", height=100)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        control_frame.pack_propagate(False)

        # Title
        tk.Label(
            control_frame,
            text="🤖 KILO AUTONOMOUS AGENT - COMPLETE",
            font=("Arial", 16, "bold"),
            bg="#2c3e50",
            fg="white"
        ).pack(side=tk.TOP, pady=(10, 5))

        # Status bar with HP connection and Kilo activity
        status_bar = tk.Frame(control_frame, bg="#2c3e50")
        status_bar.pack(side=tk.TOP, fill=tk.X, padx=20)

        # LEFT: HP Connection Status
        hp_frame = tk.Frame(status_bar, bg="#34495e", relief=tk.RAISED, borderwidth=2)
        hp_frame.pack(side=tk.LEFT, padx=5)

        tk.Label(
            hp_frame,
            text="HP Server:",
            font=("Arial", 9, "bold"),
            bg="#34495e",
            fg="white"
        ).pack(side=tk.LEFT, padx=5)

        self.hp_status_indicator = tk.Label(
            hp_frame,
            text="●",
            font=("Arial", 16),
            bg="#34495e",
            fg="#95a5a6"  # Gray until we check
        )
        self.hp_status_indicator.pack(side=tk.LEFT, padx=2)

        self.hp_status_text = tk.Label(
            hp_frame,
            text="Checking...",
            font=("Arial", 9),
            bg="#34495e",
            fg="white"
        )
        self.hp_status_text.pack(side=tk.LEFT, padx=5)

        self.hp_reconnect_btn = tk.Button(
            hp_frame,
            text="🔄",
            font=("Arial", 8),
            bg="#3498db",
            fg="white",
            command=self.reconnect_hp,
            width=2,
            state=tk.DISABLED
        )
        self.hp_reconnect_btn.pack(side=tk.LEFT, padx=5)

        # MIDDLE: Kilo Activity Status
        activity_frame = tk.Frame(status_bar, bg="#16a085", relief=tk.RAISED, borderwidth=2)
        activity_frame.pack(side=tk.LEFT, padx=20, fill=tk.X, expand=True)

        tk.Label(
            activity_frame,
            text="🧠 Kilo:",
            font=("Arial", 9, "bold"),
            bg="#16a085",
            fg="white"
        ).pack(side=tk.LEFT, padx=5)

        self.activity_status = tk.Label(
            activity_frame,
            text="Starting up...",
            font=("Arial", 10, "italic"),
            bg="#16a085",
            fg="white"
        )
        self.activity_status.pack(side=tk.LEFT, padx=5)

        # RIGHT: Stats
        self.stats_label = tk.Label(
            status_bar,
            text="Pending: 0 | Completed: 0",
            font=("Arial", 10),
            bg="#2c3e50",
            fg="white"
        )
        self.stats_label.pack(side=tk.RIGHT, padx=5)

        # ===== MAIN: Split between top panels and chat =====
        main_container = tk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # TOP HALF: Cluster + Actions + Manual (existing)
        top_frame = tk.Frame(main_container)
        top_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        # LEFT: Cluster Status
        left_frame = tk.Frame(top_frame, width=400)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        self.build_cluster_status(left_frame)

        # MIDDLE: Proposed Actions
        middle_frame = tk.Frame(top_frame, width=600)
        middle_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self.build_proposed_actions(middle_frame)

        # RIGHT: Manual Actions
        right_frame = tk.Frame(top_frame, width=400)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        self.build_manual_actions(right_frame)

        # BOTTOM HALF: Chat Interface
        chat_frame = tk.Frame(main_container, height=300)
        chat_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        self.build_chat_interface(chat_frame)

    def build_cluster_status(self, parent):
        """Build cluster status panel"""
        tk.Label(
            parent,
            text="📊 CLUSTER STATUS",
            font=("Arial", 11, "bold"),
            bg="#2c3e50",
            fg="white"
        ).pack(fill=tk.X)

        # Deployments list
        deploy_frame = tk.Frame(parent)
        deploy_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = tk.Scrollbar(deploy_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.deployments_list = tk.Listbox(
            deploy_frame,
            font=("Courier", 9),
            bg="#ffffff",
            yscrollcommand=scrollbar.set
        )
        self.deployments_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.deployments_list.yview)

        tk.Button(
            parent,
            text="🔄 Refresh",
            command=self.refresh_cluster_data,
            bg="#3498db",
            fg="black",
            font=("Arial", 9)
        ).pack(fill=tk.X, padx=5, pady=5)

    def build_proposed_actions(self, parent):
        """Build proposed actions panel"""
        tk.Label(
            parent,
            text="📋 KILO'S PROPOSALS",
            font=("Arial", 11, "bold"),
            bg="#34495e",
            fg="white"
        ).pack(fill=tk.X)

        # Actions list
        list_frame = tk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.actions_list = tk.Listbox(
            list_frame,
            font=("Courier", 9),
            bg="#ecf0f1",
            yscrollcommand=scrollbar.set
        )
        self.actions_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.actions_list.bind("<<ListboxSelect>>", self.on_select_action)
        scrollbar.config(command=self.actions_list.yview)

        # Action details
        self.details_text = scrolledtext.ScrolledText(
            parent,
            font=("Courier", 8),
            bg="#2c3e50",
            fg="#ecf0f1",
            wrap=tk.WORD,
            height=10
        )
        self.details_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Buttons
        button_frame = tk.Frame(parent)
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        self.approve_btn = tk.Button(
            button_frame,
            text="✓",
            font=("Arial", 9, "bold"),
            bg="#27ae60",
            fg="black",
            command=self.approve_action,
            state=tk.DISABLED,
            width=3
        )
        self.approve_btn.pack(side=tk.LEFT, padx=2)

        self.deny_btn = tk.Button(
            button_frame,
            text="✗",
            font=("Arial", 9, "bold"),
            bg="#e74c3c",
            fg="black",
            command=self.deny_action,
            state=tk.DISABLED,
            width=3
        )
        self.deny_btn.pack(side=tk.LEFT, padx=2)

        self.auto_btn = tk.Button(
            button_frame,
            text="🤖",
            font=("Arial", 9, "bold"),
            bg="#3498db",
            fg="black",
            command=self.grant_autonomy,
            state=tk.DISABLED,
            width=3
        )
        self.auto_btn.pack(side=tk.LEFT, padx=2)

    def build_manual_actions(self, parent):
        """Build manual controls"""
        tk.Label(
            parent,
            text="🎮 MANUAL CONTROL",
            font=("Arial", 11, "bold"),
            bg="#8e44ad",
            fg="white"
        ).pack(fill=tk.X)

        tk.Label(parent, text="Deployment:", font=("Arial", 9)).pack(anchor=tk.W, padx=5, pady=(5,0))

        self.manual_deployment_var = tk.StringVar()
        self.manual_deployment_combo = ttk.Combobox(
            parent,
            textvariable=self.manual_deployment_var,
            state="readonly",
            font=("Arial", 9)
        )
        self.manual_deployment_combo.pack(fill=tk.X, padx=5, pady=2)

        param_frame = tk.Frame(parent)
        param_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(param_frame, text="Replicas:", font=("Arial", 9)).pack(side=tk.LEFT)
        self.manual_replicas_var = tk.StringVar(value="3")
        tk.Entry(param_frame, textvariable=self.manual_replicas_var, width=5).pack(side=tk.LEFT, padx=5)

        tk.Button(
            parent,
            text="⚡ EXECUTE",
            font=("Arial", 10, "bold"),
            bg="#e67e22",
            fg="black",
            command=self.execute_manual_action
        ).pack(fill=tk.X, padx=5, pady=5)

    def build_chat_interface(self, parent):
        """Build the chat interface - TALK TO KILO!"""
        tk.Label(
            parent,
            text="💬 CHAT WITH KILO",
            font=("Arial", 12, "bold"),
            bg="#16a085",
            fg="white"
        ).pack(fill=tk.X)

        # Chat history
        chat_scroll_frame = tk.Frame(parent)
        chat_scroll_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = tk.Scrollbar(chat_scroll_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.chat_display = scrolledtext.ScrolledText(
            chat_scroll_frame,
            font=("Arial", 10),
            bg="#ecf0f1",
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set
        )
        self.chat_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.chat_display.yview)

        # Configure tags for colored messages
        self.chat_display.tag_config("user", foreground="#2c3e50", font=("Arial", 10, "bold"))
        self.chat_display.tag_config("kilo", foreground="#16a085", font=("Arial", 10, "bold"))
        self.chat_display.tag_config("system", foreground="#95a5a6", font=("Arial", 9, "italic"))

        # Chat input
        input_frame = tk.Frame(parent)
        input_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

        self.chat_input = tk.Entry(
            input_frame,
            font=("Arial", 11)
        )
        self.chat_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        self.chat_input.bind("<Return>", lambda e: self.send_chat_message())

        tk.Button(
            input_frame,
            text="Send",
            font=("Arial", 10, "bold"),
            bg="#16a085",
            fg="white",
            command=self.send_chat_message
        ).pack(side=tk.RIGHT)

        # Quick buttons
        quick_frame = tk.Frame(parent)
        quick_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

        tk.Label(quick_frame, text="Quick:", font=("Arial", 8)).pack(side=tk.LEFT, padx=5)

        quick_buttons = [
            ("Why?", "Why did you propose that?"),
            ("Status?", "What's the cluster status?"),
            ("Good job!", "Good job!"),
            ("You doofus", "You silly goose!")
        ]

        for label, command in quick_buttons:
            tk.Button(
                quick_frame,
                text=label,
                font=("Arial", 8),
                command=lambda cmd=command: self.quick_chat(cmd)
            ).pack(side=tk.LEFT, padx=2)

    def chat_message(self, sender, message):
        """Add message to chat display"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        if sender == "You":
            tag = "user"
            prefix = f"[{timestamp}] You: "
        elif sender == "Kilo":
            tag = "kilo"
            prefix = f"[{timestamp}] Kilo: "
        else:
            tag = "system"
            prefix = f"[{timestamp}] "

        self.chat_display.insert(tk.END, prefix, tag)
        self.chat_display.insert(tk.END, message + "\n")
        self.chat_display.see(tk.END)

    def quick_chat(self, message):
        """Send a quick chat message"""
        self.chat_input.delete(0, tk.END)
        self.chat_input.insert(0, message)
        self.send_chat_message()

    def send_chat_message(self):
        """Send chat message to Kilo"""
        message = self.chat_input.get().strip()
        if not message:
            return

        self.chat_input.delete(0, tk.END)
        self.chat_message("You", message)

        # Process in background
        def process():
            response = self.process_chat(message)
            self.root.after(0, lambda: self.chat_message("Kilo", response))

        threading.Thread(target=process, daemon=True).start()

    def process_chat(self, message):
        """Process chat message and generate response"""
        message_lower = message.lower()

        # COMMANDS: Scale operations
        if match := re.search(r'scale\s+(\S+)\s+to\s+(\d+)', message_lower):
            deployment = match.group(1)
            replicas = int(match.group(2))
            return self.command_scale(deployment, replicas)

        # POSITIVE FEEDBACK
        if any(word in message_lower for word in ["good", "nice", "great", "awesome", "thanks", "thank"]):
            return self.handle_positive_feedback()

        # NEGATIVE FEEDBACK / SILLY NAMES
        if any(word in message_lower for word in ["bad", "wrong", "dumb", "doofus", "silly", "goose", "stupid"]):
            return self.handle_negative_feedback(message)

        # GREETINGS (check early)
        if any(word in message_lower for word in ["hi", "hello", "hey", "sup"]) and len(message_lower.split()) <= 3:
            return "Hey! I'm watching the cluster for you. Everything looks " + \
                   ("good so far!" if len(self.agent.actions_pending) == 0 else "like it could use some fixes!")

        # HELP
        if "help" in message_lower:
            return "I can:\n" + \
                   "• Scale deployments: 'scale <name> to <number>'\n" + \
                   "• Answer questions: 'what's running?', 'what pods?', 'any proposals?'\n" + \
                   "• Get status: 'status?', 'what's happening?'\n" + \
                   "• Explain: 'why did you propose that?'\n" + \
                   "• Take feedback: 'good job!' or 'you silly goose!'"

        # SPECIFIC QUESTIONS: What deployments/pods are running (more specific patterns first!)
        if any(phrase in message_lower for phrase in ["what deployment", "what pod", "what's running", "whats running",
                                                        "show deployment", "show pod", "list deployment", "list pod"]):
            return self.list_deployments()

        # QUESTIONS: Proposals / suggestions
        if any(phrase in message_lower for phrase in ["proposal", "suggest", "recommend", "should i", "any action"]):
            return self.list_proposals()

        # QUESTIONS: Why/Reasoning
        if "why" in message_lower:
            return self.explain_last_action()

        # QUESTIONS: General status (less specific, check after specific queries)
        if any(word in message_lower for word in ["status", "happening", "going on", "up to"]):
            return self.get_status_summary()

        # DEFAULT: Contextual response based on cluster state
        return self.get_contextual_response(message)

    def command_scale(self, deployment, replicas):
        """Execute scale command from chat"""
        # Find matching deployment
        deployment_names = self.cluster_data.get("deployment_names", [])
        matches = [d for d in deployment_names if deployment.lower() in d.lower()]

        if not matches:
            return f"I can't find a deployment matching '{deployment}'. Available: {', '.join(deployment_names[:5])}..."

        if len(matches) > 1:
            return f"Multiple matches for '{deployment}': {', '.join(matches)}. Be more specific!"

        deployment_name = matches[0]

        # Execute scaling
        try:
            result = self.agent.tools["kubectl_scale"](
                deployment=deployment_name,
                replicas=replicas,
                namespace="default"
            )

            if result.get("success"):
                return f"✓ Scaled {deployment_name} to {replicas} replicas! It should be at {replicas} pods shortly."
            else:
                return f"✗ Failed to scale {deployment_name}: {result.get('error', 'Unknown error')}"
        except Exception as e:
            return f"✗ Error scaling: {e}"

    def handle_positive_feedback(self):
        """Handle positive feedback"""
        responses = [
            "Thanks! I'm learning from you every day! 🎉",
            "Glad I got it right! That's what I'm here for!",
            "Awesome! I'll remember this worked well!",
            "Yay! *happy beep boop noises* 🤖"
        ]
        import random
        return random.choice(responses)

    def handle_negative_feedback(self, message):
        """Handle negative feedback"""
        if "goose" in message.lower():
            return "🦆 Honk honk! Okay okay, I'll try to be less goose-like. What should I do differently?"

        responses = [
            "Oops! My bad. What should I have done instead?",
            "Sorry! I'm still learning. Tell me what I did wrong so I can improve!",
            "You're right, that was dumb. Help me understand what went wrong?",
            "Noted! I'll try not to be a doofus next time. What's the correct approach?"
        ]
        import random
        return random.choice(responses)

    def explain_last_action(self):
        """Explain the last proposed action"""
        if self.agent.actions_proposed:
            last = self.agent.actions_proposed[-1]
            return f"I proposed '{last['type']}' because: {last['reasoning']}"
        else:
            return "I haven't proposed anything yet! I'm just watching the cluster for issues."

    def get_status_summary(self):
        """Get cluster status summary"""
        deployment_names = self.cluster_data.get("deployment_names", [])
        pending = len(self.agent.actions_pending)

        return f"I'm monitoring {len(deployment_names)} deployments. " + \
               f"I have {pending} pending proposals. " + \
               f"Everything {'looks good!' if pending == 0 else 'has some issues I want to fix!'}"

    def list_deployments(self):
        """List current deployments"""
        deployment_names = self.cluster_data.get("deployment_names", [])

        if not deployment_names:
            return "I don't see any deployments yet. Let me check the cluster..."

        if len(deployment_names) <= 5:
            return f"I'm watching these deployments: {', '.join(deployment_names)}"
        else:
            return f"I'm watching {len(deployment_names)} deployments: {', '.join(deployment_names[:5])}, and {len(deployment_names)-5} more."

    def list_proposals(self):
        """List current proposals"""
        if not self.agent.actions_pending:
            return "I don't have any proposals right now. Everything looks stable!"

        proposals = []
        for action in self.agent.actions_pending[:3]:  # Show top 3
            proposals.append(f"• {action['type']}: {action['reasoning'][:80]}...")

        response = f"I have {len(self.agent.actions_pending)} proposals:\n" + "\n".join(proposals)

        if len(self.agent.actions_pending) > 3:
            response += f"\n...and {len(self.agent.actions_pending)-3} more"

        return response

    def get_contextual_response(self, message):
        """Generate contextual response based on current state"""
        pending = len(self.agent.actions_pending)
        deployments = len(self.cluster_data.get("deployment_names", []))

        # Generic helpful response
        responses = [
            f"I'm not sure what you mean. I'm currently watching {deployments} deployments with {pending} pending proposals.",
            "Hmm, I don't quite understand. Try asking 'what's the status?' or 'help'",
            "Not sure what you're asking! Type 'help' to see what I can do."
        ]

        import random
        return random.choice(responses)

    def refresh_cluster_data(self):
        """Refresh cluster data"""
        def refresh():
            try:
                self.cluster_data = self.agent._gather_cluster_data()
                deployment_names = self.cluster_data.get("deployment_names", [])

                self.deployments_list.delete(0, tk.END)
                for name in deployment_names:
                    self.deployments_list.insert(tk.END, f"📦 {name}")

                self.manual_deployment_combo['values'] = deployment_names
                if deployment_names:
                    self.manual_deployment_combo.current(0)

            except Exception as e:
                self.chat_message("System", f"Refresh failed: {e}")

        threading.Thread(target=refresh, daemon=True).start()

    def execute_manual_action(self):
        """Execute manual action"""
        deployment = self.manual_deployment_var.get()
        if not deployment:
            return

        try:
            replicas = int(self.manual_replicas_var.get())
        except:
            return

        def execute():
            result = self.agent.tools["kubectl_scale"](
                deployment=deployment,
                replicas=replicas,
                namespace="default"
            )

            if result.get("success"):
                self.chat_message("System", f"✓ Manually scaled {deployment} to {replicas}")
            else:
                self.chat_message("System", f"✗ Manual action failed: {result.get('error')}")

        threading.Thread(target=execute, daemon=True).start()

    def check_hp_connection(self):
        """Check if HP server k3s is reachable"""
        try:
            result = self.agent.tools["kubectl_get"]("nodes", namespace="default", output="wide")
            if result.get("success") and result.get("output"):
                self.hp_connected = True
                return True
            else:
                self.hp_connected = False
                return False
        except Exception as e:
            self.hp_connected = False
            return False

    def reconnect_hp(self):
        """Attempt to reconnect to HP server"""
        self.update_activity_status("Reconnecting to HP server...")
        self.chat_message("System", "Attempting to reconnect to HP server...")

        def reconnect():
            success = self.check_hp_connection()
            if success:
                self.root.after(0, lambda: self.chat_message("System", "✓ Reconnected to HP server!"))
                self.root.after(0, lambda: self.update_activity_status("Idle"))
            else:
                self.root.after(0, lambda: self.chat_message("System", "✗ Failed to reconnect. Check network/SSH connection."))
                self.root.after(0, lambda: self.update_activity_status("Idle"))

        threading.Thread(target=reconnect, daemon=True).start()

    def update_activity_status(self, status: str):
        """Update Kilo's current activity"""
        self.kilo_activity = status
        self.activity_status.config(text=status)

    def update_hp_status_ui(self):
        """Update HP connection status in UI"""
        if self.hp_connected:
            self.hp_status_indicator.config(fg="#2ecc71")  # Green
            self.hp_status_text.config(text="Connected")
            self.hp_reconnect_btn.config(state=tk.DISABLED)
        else:
            self.hp_status_indicator.config(fg="#e74c3c")  # Red
            self.hp_status_text.config(text="Disconnected")
            self.hp_reconnect_btn.config(state=tk.NORMAL)

    def update_loop(self):
        """Update UI periodically"""
        self.update_actions_list()
        self.update_stats()

        # Check HP connection every 10 seconds
        if not hasattr(self, '_last_hp_check') or \
           time.time() - self._last_hp_check > 10:
            threading.Thread(target=self.check_hp_connection, daemon=True).start()
            self._last_hp_check = time.time()
            self.update_hp_status_ui()

        # Refresh cluster data every 30 seconds
        if not hasattr(self, '_last_cluster_refresh') or \
           time.time() - self._last_cluster_refresh > 30:
            self.refresh_cluster_data()
            self._last_cluster_refresh = time.time()

        # Update activity based on agent state
        if len(self.agent.actions_pending) > 0:
            self.update_activity_status(f"Waiting for approval ({len(self.agent.actions_pending)} proposals)")
        elif self.agent.monitoring:
            self.update_activity_status("Monitoring cluster... 👀")
        else:
            self.update_activity_status("Idle")

        self.root.after(2000, self.update_loop)

    def update_actions_list(self):
        """Update proposed actions"""
        self.actions_list.delete(0, tk.END)

        for action in self.agent.actions_pending:
            priority_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(action["priority"], "⚪")
            display = f"{priority_icon} {action['type']}"
            self.actions_list.insert(tk.END, display)

    def update_stats(self):
        """Update statistics"""
        pending = len(self.agent.actions_pending)
        completed = len(self.agent.actions_completed)

        # Get running pod count
        running_pods = 0
        try:
            result = self.agent.tools["kubectl_get"]("pods", namespace="default", output="wide")
            if result.get("success") and result.get("output"):
                lines = result["output"].split('\n')
                for line in lines[1:]:  # Skip header
                    if line.strip() and "Running" in line:
                        running_pods += 1
        except:
            running_pods = 0

        self.stats_label.config(text=f"Pods: {running_pods} running | Pending: {pending} | Completed: {completed}")

    def on_select_action(self, event):
        """Handle action selection"""
        selection = self.actions_list.curselection()
        if not selection:
            return

        idx = selection[0]
        action = self.agent.actions_pending[idx]
        self.selected_action = action

        details = f"{action['type']}\n\n{action['reasoning']}\n\nParams: {json.dumps(action['params'], indent=2)}"
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(1.0, details)

        self.approve_btn.config(state=tk.NORMAL)
        self.deny_btn.config(state=tk.NORMAL)
        if not action["autonomous"]:
            self.auto_btn.config(state=tk.NORMAL)

    def approve_action(self):
        """Approve action"""
        if not self.selected_action:
            return

        action_id = self.selected_action["id"]

        def execute():
            action_type = self.selected_action.get('type', 'unknown')
            result = self.agent.execute_action(action_id, approved=True)

            if result.get("success"):
                self.chat_message("System", f"✓ Executed: {action_type}")
            else:
                self.chat_message("System", f"✗ Failed: {action_type} - {result.get('error', '')}")

            self.root.after(0, self.update_actions_list)

        threading.Thread(target=execute, daemon=True).start()

        self.selected_action = None
        self.approve_btn.config(state=tk.DISABLED)
        self.deny_btn.config(state=tk.DISABLED)
        self.auto_btn.config(state=tk.DISABLED)

    def deny_action(self):
        """Deny action"""
        if not self.selected_action:
            return

        action_id = self.selected_action["id"]
        self.agent.actions_pending = [a for a in self.agent.actions_pending if a["id"] != action_id]

        self.chat_message("Kilo", "Okay, I won't do that. Was I being a doofus?")

        self.selected_action = None
        self.approve_btn.config(state=tk.DISABLED)
        self.deny_btn.config(state=tk.DISABLED)
        self.auto_btn.config(state=tk.DISABLED)

        self.update_actions_list()

    def grant_autonomy(self):
        """Grant autonomy"""
        if not self.selected_action:
            return

        pattern = {
            "action_type": self.selected_action["type"],
            "tool": self.selected_action["tool"],
            "granted_at": datetime.now().isoformat()
        }

        self.agent.autonomous_patterns.append(pattern)
        self.selected_action["autonomous"] = True

        self.chat_message("Kilo", f"Thanks for trusting me with '{self.selected_action['type']}'! I'll handle these automatically from now on.")
        self.update_actions_list()


def main():
    root = tk.Tk()
    app = KiloAgentComplete(root)
    root.mainloop()


if __name__ == "__main__":
    main()
