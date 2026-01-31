#!/usr/bin/env python3
"""
Kilo Agent UI Enhanced - With Cluster Visibility & Manual Controls
Shows cluster state + lets you help Kilo when brain fails
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import json
import threading
import time
from datetime import datetime

from kilo_agent import get_kilo_agent


class KiloAgentUIEnhanced:
    """
    Enhanced UI with:
    - Cluster status view (see real deployments/pods)
    - Manual action controls (help Kilo when brain messes up)
    - Proposed actions (Kilo's suggestions)
    """

    def __init__(self, root):
        self.root = root
        self.root.title("🤖 KILO AUTONOMOUS AGENT - Enhanced Control")
        self.root.geometry("1600x900")

        # Initialize agent
        self.agent = get_kilo_agent()

        # UI State
        self.selected_action = None
        self.cluster_data = {}

        # Build UI
        self.build_ui()

        # Start monitoring
        self.agent.start_monitoring(interval=30)

        # Start UI update loop
        self.update_loop()

    def build_ui(self):
        """Build the enhanced interface"""

        # ===== TOP: Control Panel =====
        control_frame = tk.Frame(self.root, bg="#2c3e50", height=60)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        control_frame.pack_propagate(False)

        tk.Label(
            control_frame,
            text="🤖 KILO AUTONOMOUS AGENT - ENHANCED",
            font=("Arial", 16, "bold"),
            bg="#2c3e50",
            fg="white"
        ).pack(side=tk.LEFT, padx=20)

        self.monitor_status = tk.Label(
            control_frame,
            text="● Monitoring Active",
            font=("Arial", 11),
            bg="#2c3e50",
            fg="#2ecc71"
        )
        self.monitor_status.pack(side=tk.LEFT, padx=20)

        self.stats_label = tk.Label(
            control_frame,
            text="Pending: 0 | Completed: 0 | Deployments: 0",
            font=("Arial", 10),
            bg="#2c3e50",
            fg="white"
        )
        self.stats_label.pack(side=tk.RIGHT, padx=20)

        # ===== MAIN: Three-column layout =====
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # LEFT: Cluster Status
        left_frame = tk.Frame(main_frame, width=400)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        self.build_cluster_status(left_frame)

        # MIDDLE: Proposed Actions
        middle_frame = tk.Frame(main_frame, width=600)
        middle_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self.build_proposed_actions(middle_frame)

        # RIGHT: Manual Actions
        right_frame = tk.Frame(main_frame, width=400)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        self.build_manual_actions(right_frame)

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

        self.log_message("🚀 Kilo Agent Enhanced UI initialized")

    def build_cluster_status(self, parent):
        """Build cluster status panel"""
        tk.Label(
            parent,
            text="📊 CLUSTER STATUS",
            font=("Arial", 12, "bold"),
            bg="#2c3e50",
            fg="white"
        ).pack(fill=tk.X)

        # Deployments list
        tk.Label(
            parent,
            text="Deployments (default namespace):",
            font=("Arial", 10, "bold"),
            bg="#ecf0f1"
        ).pack(fill=tk.X, pady=(5, 0))

        deploy_frame = tk.Frame(parent)
        deploy_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = tk.Scrollbar(deploy_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.deployments_list = tk.Listbox(
            deploy_frame,
            font=("Courier", 9),
            bg="#ffffff",
            yscrollcommand=scrollbar.set,
            selectmode=tk.SINGLE
        )
        self.deployments_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.deployments_list.yview)

        # Refresh button
        tk.Button(
            parent,
            text="🔄 Refresh Cluster Data",
            command=self.refresh_cluster_data,
            bg="#3498db",
            fg="black",
            font=("Arial", 10)
        ).pack(fill=tk.X, padx=5, pady=5)

    def build_proposed_actions(self, parent):
        """Build proposed actions panel (existing functionality)"""
        tk.Label(
            parent,
            text="📋 KILO'S PROPOSALS",
            font=("Arial", 12, "bold"),
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
            font=("Courier", 10),
            bg="#ecf0f1",
            yscrollcommand=scrollbar.set,
            selectmode=tk.SINGLE
        )
        self.actions_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.actions_list.bind("<<ListboxSelect>>", self.on_select_action)
        scrollbar.config(command=self.actions_list.yview)

        # Action details
        self.details_text = scrolledtext.ScrolledText(
            parent,
            font=("Courier", 9),
            bg="#2c3e50",
            fg="#ecf0f1",
            wrap=tk.WORD,
            height=15
        )
        self.details_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Action buttons
        button_frame = tk.Frame(parent, bg="#ecf0f1")
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        self.approve_btn = tk.Button(
            button_frame,
            text="✓ APPROVE",
            font=("Arial", 10, "bold"),
            bg="#27ae60",
            fg="black",
            command=self.approve_action,
            state=tk.DISABLED
        )
        self.approve_btn.pack(side=tk.LEFT, padx=5, pady=5)

        self.deny_btn = tk.Button(
            button_frame,
            text="✗ DENY",
            font=("Arial", 10, "bold"),
            bg="#e74c3c",
            fg="black",
            command=self.deny_action,
            state=tk.DISABLED
        )
        self.deny_btn.pack(side=tk.LEFT, padx=5, pady=5)

        self.auto_btn = tk.Button(
            button_frame,
            text="🤖 GRANT AUTONOMY",
            font=("Arial", 10, "bold"),
            bg="#3498db",
            fg="black",
            command=self.grant_autonomy,
            state=tk.DISABLED
        )
        self.auto_btn.pack(side=tk.LEFT, padx=5, pady=5)

    def build_manual_actions(self, parent):
        """Build manual action controls - YOU control Kilo"""
        tk.Label(
            parent,
            text="🎮 MANUAL CONTROL",
            font=("Arial", 12, "bold"),
            bg="#8e44ad",
            fg="white"
        ).pack(fill=tk.X)

        tk.Label(
            parent,
            text="Help Kilo when brain fails!",
            font=("Arial", 9),
            bg="#ecf0f1"
        ).pack(fill=tk.X, pady=(5, 10))

        # Deployment selector
        tk.Label(parent, text="1. Select Deployment:", font=("Arial", 10, "bold")).pack(anchor=tk.W, padx=5)

        self.manual_deployment_var = tk.StringVar()
        self.manual_deployment_combo = ttk.Combobox(
            parent,
            textvariable=self.manual_deployment_var,
            state="readonly",
            font=("Arial", 10)
        )
        self.manual_deployment_combo.pack(fill=tk.X, padx=5, pady=5)

        # Action selector
        tk.Label(parent, text="2. Select Action:", font=("Arial", 10, "bold")).pack(anchor=tk.W, padx=5, pady=(10, 0))

        self.manual_action_var = tk.StringVar(value="scale")
        actions = [
            ("Scale Replicas", "scale"),
            ("Restart Pods", "restart"),
            ("View Logs", "logs"),
        ]

        for text, value in actions:
            tk.Radiobutton(
                parent,
                text=text,
                variable=self.manual_action_var,
                value=value,
                font=("Arial", 9)
            ).pack(anchor=tk.W, padx=20)

        # Parameters
        tk.Label(parent, text="3. Parameters:", font=("Arial", 10, "bold")).pack(anchor=tk.W, padx=5, pady=(10, 0))

        param_frame = tk.Frame(parent)
        param_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(param_frame, text="Replicas:").pack(side=tk.LEFT)
        self.manual_replicas_var = tk.StringVar(value="3")
        tk.Entry(param_frame, textvariable=self.manual_replicas_var, width=5).pack(side=tk.LEFT, padx=5)

        # Execute button
        tk.Button(
            parent,
            text="⚡ EXECUTE MANUAL ACTION",
            font=("Arial", 11, "bold"),
            bg="#e67e22",
            fg="black",
            command=self.execute_manual_action
        ).pack(fill=tk.X, padx=5, pady=20)

        # Info
        info_text = scrolledtext.ScrolledText(
            parent,
            font=("Courier", 8),
            bg="#f8f9fa",
            height=8,
            wrap=tk.WORD
        )
        info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        info_text.insert("1.0", """HOW TO USE MANUAL CONTROL:

1. Select deployment from dropdown
   (Shows REAL deployments from cluster)

2. Choose action (scale, restart, logs)

3. Set parameters (e.g., replica count)

4. Click EXECUTE

This bypasses the brain and runs directly!
Use when brain hallucinates wrong names.""")
        info_text.config(state=tk.DISABLED)

    def refresh_cluster_data(self):
        """Refresh cluster status from k3s"""
        self.log_message("🔄 Refreshing cluster data...")

        def refresh():
            try:
                self.cluster_data = self.agent._gather_cluster_data()
                deployment_names = self.cluster_data.get("deployment_names", [])

                # Update deployments list
                self.deployments_list.delete(0, tk.END)
                for name in deployment_names:
                    self.deployments_list.insert(tk.END, f"📦 {name}")

                # Update manual action dropdown
                self.manual_deployment_combo['values'] = deployment_names
                if deployment_names:
                    self.manual_deployment_combo.current(0)

                self.log_message(f"✓ Found {len(deployment_names)} deployments")

            except Exception as e:
                self.log_message(f"❌ Refresh failed: {e}")

        threading.Thread(target=refresh, daemon=True).start()

    def execute_manual_action(self):
        """Execute manual action bypassing the brain"""
        deployment = self.manual_deployment_var.get()
        action = self.manual_action_var.get()

        if not deployment:
            messagebox.showwarning("No Selection", "Please select a deployment first!")
            return

        try:
            replicas = int(self.manual_replicas_var.get())
        except ValueError:
            messagebox.showwarning("Invalid Input", "Replicas must be a number!")
            return

        # Confirm
        confirm = messagebox.askyesno(
            "Confirm Manual Action",
            f"Execute {action} on {deployment}?\n\nReplicas: {replicas}\n\nThis bypasses Kilo's brain!"
        )

        if not confirm:
            return

        def execute():
            self.log_message(f"⚡ MANUAL: {action} {deployment} to {replicas} replicas")

            if action == "scale":
                result = self.agent.tools["kubectl_scale"](
                    deployment=deployment,
                    replicas=replicas,
                    namespace="default"
                )

                if result.get("success"):
                    self.log_message(f"✅ MANUAL SUCCESS: Scaled {deployment} to {replicas}")
                else:
                    self.log_message(f"❌ MANUAL FAILED: {result.get('error', 'Unknown')}")

        threading.Thread(target=execute, daemon=True).start()

    def update_loop(self):
        """Update UI periodically"""
        self.update_actions_list()
        self.update_stats()

        # Auto-refresh cluster data every 30 seconds
        if not hasattr(self, '_last_cluster_refresh') or \
           time.time() - self._last_cluster_refresh > 30:
            self.refresh_cluster_data()
            self._last_cluster_refresh = time.time()

        self.root.after(2000, self.update_loop)

    def update_actions_list(self):
        """Refresh proposed actions list"""
        self.actions_list.delete(0, tk.END)

        for action in self.agent.actions_pending:
            priority_icon = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢"
            }.get(action["priority"], "⚪")

            auto_icon = "🤖" if action["autonomous"] else "👤"
            display = f"{priority_icon}{auto_icon} {action['type']} - {action['tool']}"
            self.actions_list.insert(tk.END, display)

            idx = self.actions_list.size() - 1
            if action["priority"] == "critical":
                self.actions_list.itemconfig(idx, bg="#ffcccc")
            elif action["priority"] == "high":
                self.actions_list.itemconfig(idx, bg="#ffe6cc")

    def update_stats(self):
        """Update statistics"""
        pending = len(self.agent.actions_pending)
        completed = len(self.agent.actions_completed)
        deployments = len(self.cluster_data.get("deployment_names", []))

        self.stats_label.config(
            text=f"Pending: {pending} | Completed: {completed} | Deployments: {deployments}"
        )

    def on_select_action(self, event):
        """Handle action selection"""
        selection = self.actions_list.curselection()
        if not selection:
            return

        idx = selection[0]
        action = self.agent.actions_pending[idx]
        self.selected_action = action

        self.show_action_details(action)

        self.approve_btn.config(state=tk.NORMAL)
        self.deny_btn.config(state=tk.NORMAL)
        if not action["autonomous"]:
            self.auto_btn.config(state=tk.NORMAL)

    def show_action_details(self, action):
        """Display action details"""
        self.details_text.delete(1.0, tk.END)

        details = f"""
╔═══════════════════════════════════════════════════════════
║ ACTION PROPOSAL
╚═══════════════════════════════════════════════════════════

Type: {action['type']}
Tool: {action['tool']}
Priority: {action['priority'].upper()}
Autonomous: {'YES' if action['autonomous'] else 'NO'}

REASONING:
{action['reasoning']}

PARAMETERS:
{json.dumps(action['params'], indent=2)}

{'⚠️ Requires approval' if not action['autonomous'] else '✓ Can run autonomously'}
"""
        self.details_text.insert(1.0, details)

    def approve_action(self):
        """Approve and execute"""
        if not self.selected_action:
            return

        action_id = self.selected_action["id"]

        def execute():
            action_type = self.selected_action['type'] if self.selected_action else "unknown"
            self.log_message(f"⏳ Executing: {action_type}...")

            result = self.agent.execute_action(action_id, approved=True)

            if result.get("success"):
                self.log_message(f"✅ SUCCESS: {action_type}")
            else:
                self.log_message(f"❌ FAILED: {action_type} - {result.get('error', '')}")

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
        self.agent.actions_pending = [
            a for a in self.agent.actions_pending if a["id"] != action_id
        ]

        self.log_message(f"❌ Denied: {self.selected_action['type']}")

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
            "params_pattern": self.selected_action["params"],
            "success_count": 0,
            "granted_manually": True,
            "granted_at": datetime.now().isoformat()
        }

        self.agent.autonomous_patterns.append(pattern)
        self.selected_action["autonomous"] = True

        self.log_message(f"🤖 AUTONOMY GRANTED: {self.selected_action['type']}")
        self.update_actions_list()

    def log_message(self, message):
        """Add to activity log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)


def main():
    root = tk.Tk()
    app = KiloAgentUIEnhanced(root)
    root.mainloop()


if __name__ == "__main__":
    main()
