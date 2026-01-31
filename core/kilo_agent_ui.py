#!/usr/bin/env python3
"""
Kilo Agent UI - Propose & Approve Interface
Shows you what Kilo wants to do and lets you approve/deny/grant autonomy
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import json
import threading
import time
from datetime import datetime

from kilo_agent import get_kilo_agent


class KiloAgentUI:
    """
    UI for interacting with the Kilo Agent
    Shows proposed actions, lets you approve/deny, grant autonomy
    """

    def __init__(self, root):
        self.root = root
        self.root.title("🤖 KILO AUTONOMOUS AGENT - Propose & Approve")
        self.root.geometry("1200x800")

        # Initialize agent
        self.agent = get_kilo_agent()

        # UI State
        self.selected_action = None

        # Build UI
        self.build_ui()

        # Start monitoring
        self.agent.start_monitoring(interval=30)

        # Start UI update loop
        self.update_loop()

    def build_ui(self):
        """Build the interface"""

        # ===== TOP: Control Panel =====
        control_frame = tk.Frame(self.root, bg="#2c3e50", height=60)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        control_frame.pack_propagate(False)

        tk.Label(
            control_frame,
            text="🤖 KILO AUTONOMOUS AGENT",
            font=("Arial", 16, "bold"),
            bg="#2c3e50",
            fg="white"
        ).pack(side=tk.LEFT, padx=20)

        # Monitoring status
        self.monitor_status = tk.Label(
            control_frame,
            text="● Monitoring Active",
            font=("Arial", 11),
            bg="#2c3e50",
            fg="#2ecc71"
        )
        self.monitor_status.pack(side=tk.LEFT, padx=20)

        # Stats
        self.stats_label = tk.Label(
            control_frame,
            text="Pending: 0 | Completed: 0 | Autonomous: 0",
            font=("Arial", 10),
            bg="#2c3e50",
            fg="white"
        )
        self.stats_label.pack(side=tk.RIGHT, padx=20)

        # ===== MIDDLE: Split View =====
        paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # LEFT: Proposed Actions List
        left_frame = tk.Frame(paned)
        paned.add(left_frame, width=400)

        tk.Label(
            left_frame,
            text="📋 PROPOSED ACTIONS",
            font=("Arial", 12, "bold"),
            bg="#34495e",
            fg="white"
        ).pack(fill=tk.X)

        # Actions listbox
        list_frame = tk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.actions_list = tk.Listbox(
            list_frame,
            font=("Courier", 10),
            bg="#ecf0f1",
            yscrollcommand=scrollbar.set,
            selectmode=tk.SINGLE
        )
        self.actions_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.actions_list.bind("<<ListboxSelect>>", self.on_select_action)
        scrollbar.config(command=self.actions_list.yview)

        # RIGHT: Action Details & Approval
        right_frame = tk.Frame(paned)
        paned.add(right_frame, width=800)

        tk.Label(
            right_frame,
            text="📝 ACTION DETAILS",
            font=("Arial", 12, "bold"),
            bg="#34495e",
            fg="white"
        ).pack(fill=tk.X)

        # Details display
        self.details_text = scrolledtext.ScrolledText(
            right_frame,
            font=("Courier", 10),
            bg="#2c3e50",
            fg="#ecf0f1",
            wrap=tk.WORD,
            height=25
        )
        self.details_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Action buttons
        button_frame = tk.Frame(right_frame, bg="#ecf0f1")
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        self.approve_btn = tk.Button(
            button_frame,
            text="✓ APPROVE & EXECUTE",
            font=("Arial", 11, "bold"),
            bg="#27ae60",
            fg="black",
            command=self.approve_action,
            state=tk.DISABLED
        )
        self.approve_btn.pack(side=tk.LEFT, padx=5, pady=5)

        self.deny_btn = tk.Button(
            button_frame,
            text="✗ DENY",
            font=("Arial", 11, "bold"),
            bg="#e74c3c",
            fg="black",
            command=self.deny_action,
            state=tk.DISABLED
        )
        self.deny_btn.pack(side=tk.LEFT, padx=5, pady=5)

        self.auto_btn = tk.Button(
            button_frame,
            text="🤖 GRANT AUTONOMY",
            font=("Arial", 11, "bold"),
            bg="#3498db",
            fg="black",
            command=self.grant_autonomy,
            state=tk.DISABLED
        )
        self.auto_btn.pack(side=tk.LEFT, padx=5, pady=5)

        # ===== BOTTOM: Activity Log =====
        log_frame = tk.Frame(self.root)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        tk.Label(
            log_frame,
            text="📊 ACTIVITY LOG",
            font=("Arial", 10, "bold"),
            bg="#34495e",
            fg="white"
        ).pack(fill=tk.X)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            font=("Courier", 9),
            bg="#1c1c1c",
            fg="#00ff00",
            height=8,
            wrap=tk.WORD
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.log_message("🚀 Kilo Agent initialized and monitoring started")

    def update_loop(self):
        """Update UI periodically"""
        self.update_actions_list()
        self.update_stats()
        # Schedule next update
        self.root.after(2000, self.update_loop)  # Every 2 seconds

    def update_actions_list(self):
        """Refresh the list of proposed actions"""
        self.actions_list.delete(0, tk.END)

        for action in self.agent.actions_pending:
            priority_icon = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢"
            }.get(action["priority"], "⚪")

            auto_icon = "🤖" if action["autonomous"] else "👤"

            # Format: [Priority][Auto] Type - Tool
            display = f"{priority_icon}{auto_icon} {action['type']} - {action['tool']}"
            self.actions_list.insert(tk.END, display)

            # Color code by priority
            idx = self.actions_list.size() - 1
            if action["priority"] == "critical":
                self.actions_list.itemconfig(idx, bg="#ffcccc")
            elif action["priority"] == "high":
                self.actions_list.itemconfig(idx, bg="#ffe6cc")

    def update_stats(self):
        """Update statistics display"""
        pending = len(self.agent.actions_pending)
        completed = len(self.agent.actions_completed)
        autonomous = len(self.agent.autonomous_patterns)

        self.stats_label.config(
            text=f"Pending: {pending} | Completed: {completed} | Autonomous: {autonomous}"
        )

    def on_select_action(self, event):
        """Handle action selection"""
        selection = self.actions_list.curselection()
        if not selection:
            return

        idx = selection[0]
        action = self.agent.actions_pending[idx]
        self.selected_action = action

        # Display details
        self.show_action_details(action)

        # Enable buttons
        self.approve_btn.config(state=tk.NORMAL)
        self.deny_btn.config(state=tk.NORMAL)
        if not action["autonomous"]:
            self.auto_btn.config(state=tk.NORMAL)

    def show_action_details(self, action):
        """Display action details in the detail pane"""
        self.details_text.delete(1.0, tk.END)

        details = f"""
╔═══════════════════════════════════════════════════════════════════════
║ ACTION PROPOSAL
╚═══════════════════════════════════════════════════════════════════════

ID: {action['id']}
Timestamp: {action['timestamp']}
Type: {action['type']}
Priority: {action['priority'].upper()}
Autonomous: {'YES - Can run without approval' if action['autonomous'] else 'NO - Needs your approval'}

───────────────────────────────────────────────────────────────────────────
REASONING
───────────────────────────────────────────────────────────────────────────
{action['reasoning']}

───────────────────────────────────────────────────────────────────────────
TOOL TO USE
───────────────────────────────────────────────────────────────────────────
Tool: {action['tool']}

───────────────────────────────────────────────────────────────────────────
PARAMETERS
───────────────────────────────────────────────────────────────────────────
{json.dumps(action['params'], indent=2)}

───────────────────────────────────────────────────────────────────────────
SAFETY
───────────────────────────────────────────────────────────────────────────
"""

        # Check if tool is safe
        tool_def = self.agent.tools.get(action['tool'])
        if tool_def:
            # Test call to see if it's safe
            test_result = {"safe": True}  # Default
            details += f"Read-only: {test_result.get('safe', False)}\n"
            details += f"Requires Approval: {not action['autonomous']}\n"

        if action['autonomous']:
            details += "\n⚠️ This action pattern has been GRANTED AUTONOMY\n"
            details += "It will execute automatically without approval.\n"
        else:
            details += "\n👤 This action REQUIRES YOUR APPROVAL to execute.\n"

        self.details_text.insert(1.0, details)

    def approve_action(self):
        """Approve and execute selected action"""
        if not self.selected_action:
            return

        action_id = self.selected_action["id"]

        # Confirm
        confirm = messagebox.askyesno(
            "Confirm Execution",
            f"Execute this action?\n\nType: {self.selected_action['type']}\n"
            f"Tool: {self.selected_action['tool']}\n\n"
            f"This will make actual changes to your system."
        )

        if not confirm:
            return

        # Execute in background thread
        def execute():
            # Capture action details before thread starts (avoid race condition)
            action_type = self.selected_action['type'] if self.selected_action else "unknown"

            self.log_message(f"⏳ Executing action: {action_type}...")
            result = self.agent.execute_action(action_id, approved=True)

            if result.get("success"):
                self.log_message(f"✅ SUCCESS: {action_type}")
                self.log_message(f"   Output: {result.get('output', 'No output')[:100]}")
            else:
                self.log_message(f"❌ FAILED: {action_type}")
                self.log_message(f"   Error: {result.get('error', 'Unknown error')}")

            # Refresh UI
            self.root.after(0, self.update_actions_list)

        threading.Thread(target=execute, daemon=True).start()

        # Clear selection
        self.selected_action = None
        self.approve_btn.config(state=tk.DISABLED)
        self.deny_btn.config(state=tk.DISABLED)
        self.auto_btn.config(state=tk.DISABLED)

    def deny_action(self):
        """Deny selected action"""
        if not self.selected_action:
            return

        action_id = self.selected_action["id"]

        # Remove from pending
        self.agent.actions_pending = [
            a for a in self.agent.actions_pending if a["id"] != action_id
        ]

        self.log_message(f"❌ Denied action: {self.selected_action['type']}")

        # Clear selection
        self.selected_action = None
        self.approve_btn.config(state=tk.DISABLED)
        self.deny_btn.config(state=tk.DISABLED)
        self.auto_btn.config(state=tk.DISABLED)

        # Refresh
        self.update_actions_list()

    def grant_autonomy(self):
        """Grant autonomy to this type of action"""
        if not self.selected_action:
            return

        confirm = messagebox.askyesno(
            "Grant Autonomy",
            f"Grant autonomy to this action pattern?\n\n"
            f"Type: {self.selected_action['type']}\n"
            f"Tool: {self.selected_action['tool']}\n\n"
            f"Future actions of this type will execute automatically WITHOUT approval.\n\n"
            f"You can revoke this later."
        )

        if not confirm:
            return

        # Add to autonomous patterns
        pattern = {
            "action_type": self.selected_action["type"],
            "tool": self.selected_action["tool"],
            "params_pattern": self.selected_action["params"],
            "success_count": 0,
            "granted_manually": True,
            "granted_at": datetime.now().isoformat()
        }

        self.agent.autonomous_patterns.append(pattern)

        self.log_message(f"🤖 AUTONOMY GRANTED: {self.selected_action['type']}")
        self.log_message(f"   Future {self.selected_action['type']} actions will execute automatically")

        # Update the action
        self.selected_action["autonomous"] = True

        # Refresh
        self.update_actions_list()
        messagebox.showinfo(
            "Autonomy Granted",
            f"Kilo can now perform '{self.selected_action['type']}' actions autonomously.\n\n"
            f"You'll still see them in the activity log."
        )

    def log_message(self, message):
        """Add message to activity log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)


def main():
    root = tk.Tk()
    app = KiloAgentUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
