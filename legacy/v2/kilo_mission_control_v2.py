#!/usr/bin/env python3
"""
KILO MISSION CONTROL V2 - TRUE LONG ARMS OVERSEER
Designed for Beelink Mini PC (AMD Ryzen 7) - CPU-ONLY Mode

This version has ACTUAL CONTROL over the HP k3s cluster, not just observation.

SAFETY SYSTEM:
- Monitors CPU and Memory usage in real-time
- Automatic kill switch if CPU > 88% sustained or Memory > 80%
- Visual warning indicators (Green/Yellow/Red)
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import subprocess
import os
import threading
import time
import psutil

# --- CONFIGURATION ---
MODEL_DIR = os.path.expanduser("~/.lmstudio/models")
CODE_DIR = os.path.expanduser("~/Desktop/AI_stuff/old_hacksaw_fingers")
HP_IP = "192.168.68.56"
KUBECONFIG = os.path.expanduser("~/.kube/hp-k3s-config")
LLM_PORT = 11434  # Use the actual llama-server port

# Set environment
os.environ['KUBECONFIG'] = KUBECONFIG

# HARD-CODED STABILITY PARAMETERS (DO NOT MODIFY)
CONTEXT_SIZE = 8192      # Limit context to prevent power spikes
MAX_TOKENS = 1024        # Cap output generation
GPU_LAYERS = 0           # CPU-only mode (no GPU)
THREADS = 4              # Use 4 threads (safer, prevents 85%+ CPU spikes)
AIDER_MAP_TOKENS = 512   # Reduce Aider token overhead

# SAFETY THRESHOLDS
CPU_CRITICAL = 88        # Auto-kill if CPU > 88% for sustained period
MEMORY_CRITICAL = 80     # Auto-kill if Memory > 80%
CPU_WARNING = 65         # Yellow warning zone
MEMORY_WARNING = 65      # Yellow warning zone
MONITOR_INTERVAL = 1.5   # Check every 1.5 seconds


class KiloMissionControl:
    def __init__(self, root):
        self.root = root
        self.root.title("KILO MISSION CONTROL V2 - LONG ARMS OVERSEER")
        self.root.geometry("700x950")

        # Model mapping (display name -> full path)
        self.model_paths = {}

        # Safety monitoring state
        self.monitoring = True
        self.cpu_high_time = 0
        self.auto_killed = False

        # COSMIC Desktop compatibility fix
        self.root.update_idletasks()

        # Header
        header = tk.Label(
            root,
            text="🦾 KILO LONG ARMS CONTROL 🦾",
            font=("Arial", 18, "bold"),
            fg="#ff3b30"
        )
        header.pack(pady=10)

        # System Info
        info_frame = tk.Frame(root, relief="ridge", borderwidth=2)
        info_frame.pack(pady=5, padx=20, fill="x")
        tk.Label(
            info_frame,
            text=f"OVERSEER (Beelink): 192.168.68.60 | WORKER (HP): {HP_IP}",
            font=("Courier", 9, "bold"),
            fg="purple"
        ).pack(pady=3)

        # RAM status display
        total_ram_gb = psutil.virtual_memory().total / (1024**3)
        ram_color = "green" if total_ram_gb >= 22 else "orange"
        tk.Label(
            info_frame,
            text=f"✓ {total_ram_gb:.1f} GB RAM available (iGPU: 512 MB)",
            font=("Courier", 8),
            fg=ram_color
        ).pack(pady=2)

        # SAFETY MONITOR PANEL
        safety_frame = tk.LabelFrame(
            root,
            text="SAFETY MONITOR - AUTO BREAKER ACTIVE",
            font=("Arial", 10, "bold"),
            fg="#ff3b30",
            relief="ridge",
            borderwidth=3
        )
        safety_frame.pack(pady=10, padx=20, fill="x")

        # CPU Monitor
        cpu_container = tk.Frame(safety_frame)
        cpu_container.pack(pady=5, fill="x", padx=10)
        tk.Label(cpu_container, text="CPU:", font=("Arial", 9, "bold"), width=8, anchor="w").pack(side="left")
        self.cpu_label = tk.Label(
            cpu_container,
            text="0%",
            font=("Courier", 10, "bold"),
            width=6,
            anchor="e"
        )
        self.cpu_label.pack(side="left")
        self.cpu_bar = ttk.Progressbar(cpu_container, length=400, mode='determinate')
        self.cpu_bar.pack(side="left", padx=10)

        # Memory Monitor
        mem_container = tk.Frame(safety_frame)
        mem_container.pack(pady=5, fill="x", padx=10)
        tk.Label(mem_container, text="Memory:", font=("Arial", 9, "bold"), width=8, anchor="w").pack(side="left")
        self.mem_label = tk.Label(
            mem_container,
            text="0% (0.0/0.0 GB)",
            font=("Courier", 9, "bold"),
            width=20,
            anchor="e"
        )
        self.mem_label.pack(side="left")
        self.mem_bar = ttk.Progressbar(mem_container, length=300, mode='determinate')
        self.mem_bar.pack(side="left", padx=10)

        # Safety Status
        self.safety_status = tk.Label(
            safety_frame,
            text="SYSTEM STABLE - MONITORING ACTIVE",
            font=("Arial", 9),
            fg="green"
        )
        self.safety_status.pack(pady=5)

        # PHASE 1: LOCAL BRAIN (Beelink AI)
        phase1_frame = tk.LabelFrame(root, text="PHASE 1: LOCAL AI BRAIN (Beelink)", font=("Arial", 11, "bold"), fg="#28a745")
        phase1_frame.pack(pady=10, padx=20, fill="both", expand=False)

        tk.Label(phase1_frame, text="Select Intelligence Model:", font=("Arial", 10)).pack(pady=5)
        self.model_var = tk.StringVar()
        self.model_dropdown = ttk.Combobox(
            phase1_frame,
            textvariable=self.model_var,
            width=60,
            state="readonly"
        )
        self.refresh_models()
        self.model_dropdown.pack(pady=5)

        tk.Button(
            phase1_frame,
            text="ACTIVATE LOCAL BRAIN (8K Context / 4 Threads)",
            bg="#28a745",
            fg="white",
            font=("Arial", 10, "bold"),
            width=45,
            height=2,
            command=self.start_brain
        ).pack(pady=10)

        tk.Button(
            phase1_frame,
            text="💬 CHAT WITH KILO AI",
            bg="#9b59b6",
            fg="white",
            font=("Arial", 10, "bold"),
            width=45,
            height=2,
            command=self.open_chat
        ).pack(pady=5)

        # PHASE 2: CLUSTER CONTROL (Long Arms to HP)
        phase2_frame = tk.LabelFrame(root, text="PHASE 2: HP CLUSTER CONTROL (Long Arms)", font=("Arial", 11, "bold"), fg="purple")
        phase2_frame.pack(pady=10, padx=20, fill="both", expand=True)

        # Cluster Status Display
        self.cluster_status_text = scrolledtext.ScrolledText(
            phase2_frame,
            height=12,
            font=("Courier", 9),
            bg="#1e1e1e",
            fg="#00ff00",
            wrap=tk.WORD
        )
        self.cluster_status_text.pack(pady=5, padx=10, fill="both", expand=True)
        self.cluster_status_text.insert("1.0", "Cluster status: Not checked yet\nClick 'REFRESH STATUS' to query HP cluster...")

        # Control Buttons
        button_frame = tk.Frame(phase2_frame)
        button_frame.pack(pady=10)

        tk.Button(
            button_frame,
            text="🚀 START ALL SERVICES",
            bg="#28a745",
            fg="white",
            font=("Arial", 10, "bold"),
            width=20,
            height=2,
            command=self.start_all_services
        ).grid(row=0, column=0, padx=5, pady=5)

        tk.Button(
            button_frame,
            text="⏹️ STOP ALL SERVICES",
            bg="#dc3545",
            fg="white",
            font=("Arial", 10, "bold"),
            width=20,
            height=2,
            command=self.stop_all_services
        ).grid(row=0, column=1, padx=5, pady=5)

        tk.Button(
            button_frame,
            text="🔄 REFRESH STATUS",
            bg="#007bff",
            fg="white",
            font=("Arial", 10, "bold"),
            width=20,
            height=2,
            command=self.refresh_cluster_status
        ).grid(row=1, column=0, padx=5, pady=5)

        tk.Button(
            button_frame,
            text="⏰ WAKE HP",
            bg="#ffc107",
            fg="black",
            font=("Arial", 10, "bold"),
            width=20,
            height=2,
            command=self.wake_hp
        ).grid(row=1, column=1, padx=5, pady=5)

        # EMERGENCY CONTROLS
        tk.Frame(root, height=2, bd=1, relief="sunken").pack(fill="x", padx=30, pady=10)

        tk.Button(
            root,
            text="🛑 EMERGENCY KILL SWITCH",
            bg="#dc3545",
            fg="white",
            font=("Arial", 12, "bold"),
            width=35,
            height=2,
            command=self.emergency_kill
        ).pack(pady=10)

        # Status Bar
        self.status_label = tk.Label(
            root,
            text="SYSTEM STATUS: STANDBY",
            font=("Arial", 10),
            fg="gray"
        )
        self.status_label.pack(side="bottom", pady=10)

        # Start safety monitoring thread
        self.monitor_thread = threading.Thread(target=self.safety_monitor, daemon=True)
        self.monitor_thread.start()

        # Auto-refresh disabled to prevent distracting blinking
        # Use the "REFRESH STATUS" button instead

    def run_kubectl(self, args):
        """Helper to run kubectl commands"""
        try:
            result = subprocess.run(
                ["kubectl"] + args,
                capture_output=True,
                text=True,
                timeout=10,
                env=os.environ
            )
            return result.stdout, result.stderr, result.returncode
        except Exception as e:
            return "", str(e), 1

    def refresh_cluster_status(self):
        """Query HP cluster and display detailed status"""
        def _task():
            self.update_cluster_display("Querying HP cluster...\n")

            # Check if HP is reachable
            ping_result = subprocess.run(
                ["ping", "-c", "1", "-W", "2", HP_IP],
                capture_output=True
            )

            if ping_result.returncode != 0:
                self.update_cluster_display(f"❌ HP WORKER OFFLINE\nCannot reach {HP_IP}\nTry 'WAKE HP' button")
                return

            # Get nodes
            stdout, stderr, rc = self.run_kubectl(["get", "nodes", "-o", "wide"])

            if rc != 0:
                self.update_cluster_display(f"❌ K3S CLUSTER UNREACHABLE\n{stderr}")
                return

            output = []
            output.append("="*70)
            output.append("HP K3S CLUSTER STATUS")
            output.append("="*70)
            output.append("\nNODES:")
            output.append(stdout)

            # Get all pods
            stdout, stderr, rc = self.run_kubectl(["get", "pods", "-n", "default"])

            if rc == 0:
                output.append("\nPODS (default namespace):")
                output.append(stdout)

                # Count running pods
                lines = stdout.split('\n')[1:]  # Skip header
                total = len([l for l in lines if l.strip()])
                running = len([l for l in lines if 'Running' in l and '1/1' in l])

                output.append(f"\nSUMMARY: {running}/{total} pods running")

            # Get deployments
            stdout, stderr, rc = self.run_kubectl(["get", "deployments", "-n", "default"])

            if rc == 0:
                output.append("\nDEPLOYMENTS:")
                output.append(stdout)

            self.update_cluster_display("\n".join(output))

        threading.Thread(target=_task, daemon=True).start()

    def update_cluster_display(self, text):
        """Update cluster status display (thread-safe)"""
        def _update():
            self.cluster_status_text.delete("1.0", tk.END)
            self.cluster_status_text.insert("1.0", text)

        self.root.after(0, _update)

    def start_all_services(self):
        """Scale all deployments to 1 replica"""
        if not messagebox.askyesno("Confirm", "Start all services on HP cluster?"):
            return

        def _task():
            self.update_cluster_display("Starting all services on HP cluster...\n")

            # Get all deployments
            stdout, stderr, rc = self.run_kubectl(["get", "deployments", "-n", "default", "-o", "name"])

            if rc != 0:
                self.update_cluster_display(f"Error getting deployments:\n{stderr}")
                return

            deployments = [d.strip() for d in stdout.split('\n') if d.strip()]

            output = ["Starting services:"]
            for dep in deployments:
                dep_name = dep.replace("deployment.apps/", "")
                output.append(f"\n🚀 Scaling {dep_name}...")

                _, stderr, rc = self.run_kubectl(["scale", dep, "-n", "default", "--replicas=1"])

                if rc == 0:
                    output.append(f"   ✓ {dep_name} started")
                else:
                    output.append(f"   ❌ {dep_name} failed: {stderr}")

            output.append("\n" + "="*70)
            output.append("Waiting for pods to start (10 seconds)...")
            self.update_cluster_display("\n".join(output))

            time.sleep(10)
            self.refresh_cluster_status()

        threading.Thread(target=_task, daemon=True).start()

    def stop_all_services(self):
        """Scale all deployments to 0 replicas"""
        if not messagebox.askyesno("Confirm", "Stop all services on HP cluster?"):
            return

        def _task():
            self.update_cluster_display("Stopping all services on HP cluster...\n")

            # Scale all deployments to 0
            stdout, stderr, rc = self.run_kubectl(["scale", "deployment", "--all", "-n", "default", "--replicas=0"])

            if rc == 0:
                self.update_cluster_display("✓ All services stopped\n\nRefreshing status...")
                time.sleep(3)
                self.refresh_cluster_status()
            else:
                self.update_cluster_display(f"❌ Error stopping services:\n{stderr}")

        threading.Thread(target=_task, daemon=True).start()

    def wake_hp(self):
        """Wake HP machine (WoL or SSH command)"""
        def _task():
            self.update_cluster_display(f"Attempting to wake HP at {HP_IP}...\n")

            # Try pinging first
            result = subprocess.run(["ping", "-c", "1", "-W", "2", HP_IP], capture_output=True)

            if result.returncode == 0:
                self.update_cluster_display(f"✓ HP is already online at {HP_IP}")
            else:
                self.update_cluster_display(f"⏰ HP is offline\nTip: Configure Wake-on-LAN or manually power on HP\n\nHP IP: {HP_IP}")

        threading.Thread(target=_task, daemon=True).start()

    def auto_refresh_cluster(self):
        """Auto-refresh cluster status every 10 seconds"""
        def _refresh_loop():
            while True:
                time.sleep(10)
                if self.monitoring:  # Only refresh if monitoring is active
                    self.refresh_cluster_status()

        threading.Thread(target=_refresh_loop, daemon=True).start()

    def safety_monitor(self):
        """Background thread that monitors system resources and auto-kills on overload"""
        while self.monitoring:
            try:
                # Get current CPU and Memory usage
                cpu_percent = psutil.cpu_percent(interval=1)
                mem_percent = psutil.virtual_memory().percent
                mem_available_gb = psutil.virtual_memory().available / (1024**3)

                # Update GUI (thread-safe)
                self.root.after(0, self.update_safety_display, cpu_percent, mem_percent)

                # ENHANCED SAFETY BREAKER LOGIC
                if mem_available_gb < 2.0:
                    self.root.after(0, self.auto_emergency_kill, "CRITICAL MEMORY SHORTAGE", f"{mem_available_gb:.1f}GB free")
                elif mem_percent > MEMORY_CRITICAL:
                    self.root.after(0, self.auto_emergency_kill, "MEMORY OVERLOAD", mem_percent)
                elif cpu_percent > CPU_CRITICAL:
                    self.cpu_high_time += MONITOR_INTERVAL
                    if self.cpu_high_time >= 5:
                        self.root.after(0, self.auto_emergency_kill, "CPU OVERLOAD", cpu_percent)
                elif cpu_percent > 80 and mem_percent > 70:
                    self.cpu_high_time += MONITOR_INTERVAL
                    if self.cpu_high_time >= 3:
                        self.root.after(0, self.auto_emergency_kill, "COMBINED OVERLOAD", f"CPU:{cpu_percent:.0f}% MEM:{mem_percent:.0f}%")
                else:
                    self.cpu_high_time = 0

            except Exception as e:
                print(f"Safety monitor error: {e}")

            time.sleep(MONITOR_INTERVAL)

    def update_safety_display(self, cpu, mem):
        """Update the safety monitor display with current values"""
        # Get memory info
        mem_info = psutil.virtual_memory()
        mem_used_gb = mem_info.used / (1024**3)
        mem_total_gb = mem_info.total / (1024**3)

        self.cpu_bar['value'] = cpu
        self.mem_bar['value'] = mem
        self.cpu_label.config(text=f"{cpu:.1f}%")
        self.mem_label.config(text=f"{mem:.1f}% ({mem_used_gb:.1f}/{mem_total_gb:.0f} GB)")

        if cpu >= CPU_CRITICAL or mem >= MEMORY_CRITICAL:
            cpu_color = "#dc3545"
            status_text = "CRITICAL - AUTO BREAKER ARMED"
            status_color = "#dc3545"
        elif cpu >= CPU_WARNING or mem >= MEMORY_WARNING:
            cpu_color = "#ffc107"
            status_text = "WARNING - HIGH LOAD DETECTED"
            status_color = "#ffc107"
        else:
            cpu_color = "#28a745"
            status_text = "SYSTEM STABLE - MONITORING ACTIVE"
            status_color = "#28a745"

        self.cpu_label.config(fg=cpu_color)
        self.mem_label.config(fg=cpu_color)

        if not self.auto_killed:
            self.safety_status.config(text=status_text, fg=status_color)

    def auto_emergency_kill(self, reason, value):
        """Automatically triggered emergency shutdown on critical overload"""
        if self.auto_killed:
            return

        self.auto_killed = True
        subprocess.run(["pkill", "-9", "-f", "llama-server"], check=False)
        subprocess.run(["pkill", "-9", "-f", "aider"], check=False)
        subprocess.run(["pkill", "-9", "-f", "llama-cli"], check=False)

        if isinstance(value, (int, float)):
            value_str = f"{value:.1f}%"
        else:
            value_str = str(value)

        self.safety_status.config(text=f"AUTO-KILLED: {reason} ({value_str})", fg="#dc3545")
        self.status_label.config(text="AUTOMATIC SAFETY SHUTDOWN TRIGGERED", fg="#dc3545")

        messagebox.showerror(
            "AUTOMATIC SAFETY SHUTDOWN",
            f"System overload detected!\n\nReason: {reason}\nValue: {value_str}"
        )

    def refresh_models(self):
        """Scan LM Studio directory recursively for available .gguf models"""
        try:
            self.model_paths = {}
            display_names = []

            if os.path.exists(MODEL_DIR):
                for root, dirs, files in os.walk(MODEL_DIR):
                    for file in files:
                        if file.endswith(".gguf") and not file.startswith("mmproj"):
                            full_path = os.path.join(root, file)
                            # Create a nicer display name (folder + filename)
                            rel_path = os.path.relpath(full_path, MODEL_DIR)
                            display_name = rel_path
                            self.model_paths[display_name] = full_path
                            display_names.append(display_name)

            self.model_dropdown['values'] = sorted(display_names)
            if display_names:
                self.model_dropdown.current(0)
        except Exception as e:
            print(f"Model scan error: {e}")

    def start_brain(self):
        """Launch llama-server with hard-coded stability parameters"""
        display_name = self.model_var.get()
        if not display_name:
            return messagebox.showwarning("Warning", "Select a model first")

        model_full_path = self.model_paths.get(display_name)
        if not model_full_path:
            return messagebox.showerror("Error", "Model path not found")

        # MEMORY OPTIMIZATION: Kill any existing llama-servers first
        # This prevents multiple models from consuming RAM simultaneously
        existing_servers = subprocess.run(
            ["pgrep", "-f", "llama-server"],
            capture_output=True,
            text=True
        )

        if existing_servers.stdout.strip():
            response = messagebox.askyesno(
                "AI Model Already Running",
                "Another AI model is already loaded in memory.\n\n"
                "Kill the old model and load this one?\n"
                "(Saves 2-3 GB of RAM)"
            )
            if response:
                subprocess.run(["pkill", "-f", "llama-server"], check=False)
                time.sleep(2)  # Wait for cleanup
            else:
                return  # User cancelled

        self.auto_killed = False

        # Determine the llama-server binary path
        server_bin = os.path.expanduser("~/llama.cpp/build/bin/llama-server")

        cmd = (
            f"{server_bin} "
            f"-m '{model_full_path}' "
            f"-c {CONTEXT_SIZE} "
            f"-n {MAX_TOKENS} "
            f"-ngl {GPU_LAYERS} "
            f"-t {THREADS} "
            f"--port {LLM_PORT}"
        )

        subprocess.Popen(['cosmic-term', '--', 'bash', '-c', f"{cmd}; exec bash"])
        self.status_label.config(text=f"LOCAL BRAIN ACTIVE: {os.path.basename(model_full_path)} | Port {LLM_PORT}", fg="#28a745")

    def open_chat(self):
        """Open chat window to talk to Kilo AI"""
        # Try V3 first (smart + memory + cluster-aware), fallback to V2
        chat_script_v3 = os.path.join(CODE_DIR, "kilo_chat_v3.py")
        chat_script_v2 = os.path.join(CODE_DIR, "kilo_chat_v2.py")
        chat_script_v1 = os.path.join(CODE_DIR, "kilo_chat.py")

        if os.path.exists(chat_script_v3):
            subprocess.Popen(['python3', chat_script_v3])
            self.status_label.config(text="SMART CHAT V3 OPENED (Memory + Routing)", fg="#9b59b6")
        elif os.path.exists(chat_script_v2):
            subprocess.Popen(['python3', chat_script_v2])
            self.status_label.config(text="CLUSTER-AWARE CHAT V2 OPENED", fg="#9b59b6")
        elif os.path.exists(chat_script_v1):
            subprocess.Popen(['python3', chat_script_v1])
                subprocess.Popen(['python3', chat_script])
                self.status_label.config(text="CHAT WINDOW OPENED", fg="#9b59b6")
            else:
                messagebox.showerror("Error", "Chat script not found")

    def emergency_kill(self):
        """Manual emergency kill switch"""
        subprocess.run(["pkill", "-f", "llama-server"], check=False)
        subprocess.run(["pkill", "-f", "aider"], check=False)
        self.auto_killed = False
        self.status_label.config(text="MANUAL EMERGENCY SHUTDOWN", fg="#dc3545")


if __name__ == "__main__":
    root = tk.Tk()
    app = KiloMissionControl(root)
    root.mainloop()
