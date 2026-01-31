#!/usr/bin/env python3
"""
KILO MISSION CONTROL - Consolidated AI System Dashboard
Designed for Beelink Mini PC (AMD Ryzen 7) - CPU-ONLY Mode

Hard-coded stability parameters to prevent power crashes:
- Context limit: 8192 tokens
- Output limit: 1024 tokens
- GPU layers: 0 (CPU-only)
- Threads: 8 (Ryzen cores)

SAFETY SYSTEM:
- Monitors CPU and Memory usage in real-time
- Automatic kill switch if CPU > 95% sustained or Memory > 85%
- Visual warning indicators (Green/Yellow/Red)
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os
import threading
import time
import psutil
import httpx

# --- CONFIGURATION ---
MODEL_DIR = os.path.expanduser("~/.lmstudio/models")
CODE_DIR = os.path.expanduser("~/Desktop/AI_stuff/old_hacksaw_fingers")
OBSIDIAN_DIR = os.path.expanduser("~/Documents/Obsidian Vault")
K3S_MANAGER_URL = "http://localhost:9011"
LLM_PORT = 8081  # Changed from 8080 to avoid socat conflict

# HARD-CODED STABILITY PARAMETERS (DO NOT MODIFY)
CONTEXT_SIZE = 8192      # Limit context to prevent power spikes
MAX_TOKENS = 1024        # Cap output generation
GPU_LAYERS = 0           # CPU-only mode (no GPU)
THREADS = 4              # Use 4 threads (safer, prevents 85%+ CPU spikes)
AIDER_MAP_TOKENS = 512   # Reduce Aider token overhead

# SAFETY THRESHOLDS (Tuned for 22 GB usable RAM + Ryzen 7 power limits)
# NOTE: iGPU reduced to 512 MB in BIOS (was 4GB) - gained ~3GB usable RAM
CPU_CRITICAL = 88        # Auto-kill if CPU > 88% for sustained period
MEMORY_CRITICAL = 80     # Auto-kill if Memory > 80% (updated for 22 GB available)
CPU_WARNING = 65         # Yellow warning zone
MEMORY_WARNING = 65      # Yellow warning zone (updated for 22 GB available)
MONITOR_INTERVAL = 1.5   # Check every 1.5 seconds (faster reaction)


class KiloMissionControl:
    def __init__(self, root):
        self.root = root
        self.root.title("KILO MISSION CONTROL - LONG ARMS MODE")
        self.root.geometry("550x850")

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
            text="KILO MISSION CONTROL",
            font=("Arial", 16, "bold"),
            fg="#ff3b30"
        )
        header.pack(pady=10)

        # System Info
        info_frame = tk.Frame(root, relief="ridge", borderwidth=2)
        info_frame.pack(pady=5, padx=20, fill="x")
        tk.Label(
            info_frame,
            text=f"BEELINK IP: 192.168.68.60 | HP IP: 192.168.68.56",
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
        self.cpu_bar = ttk.Progressbar(cpu_container, length=300, mode='determinate')
        self.cpu_bar.pack(side="left", padx=10)

        # Memory Monitor
        mem_container = tk.Frame(safety_frame)
        mem_container.pack(pady=5, fill="x", padx=10)
        tk.Label(mem_container, text="Memory:", font=("Arial", 9, "bold"), width=8, anchor="w").pack(side="left")
        self.mem_label = tk.Label(
            mem_container,
            text="0%",
            font=("Courier", 10, "bold"),
            width=6,
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

        # PHASE 1: BRAIN (Model Selection & Server)
        phase1_frame = tk.LabelFrame(root, text="PHASE 1: BRAIN ACTIVATION", font=("Arial", 11, "bold"), fg="#28a745")
        phase1_frame.pack(pady=10, padx=20, fill="both", expand=True)

        tk.Label(phase1_frame, text="Select Intelligence Model:", font=("Arial", 10)).pack(pady=5)
        self.model_var = tk.StringVar()
        self.model_dropdown = ttk.Combobox(
            phase1_frame,
            textvariable=self.model_var,
            width=50,
            state="readonly"
        )
        self.refresh_models()
        self.model_dropdown.pack(pady=5)

        tk.Button(
            phase1_frame,
            text="ACTIVATE BRAIN (8K Context / 4 Threads)",
            bg="#28a745",
            fg="white",
            font=("Arial", 10, "bold"),
            width=35,
            height=2,
            command=self.start_brain
        ).pack(pady=10)

        # PHASE 2: OPERATOR (Aider)
        phase2_frame = tk.LabelFrame(root, text="PHASE 2: OPERATOR DEPLOYMENT", font=("Arial", 11, "bold"), fg="#007bff")
        phase2_frame.pack(pady=10, padx=20, fill="both", expand=True)

        tk.Button(
            phase2_frame,
            text="DEPLOY OPERATOR (Aider)",
            bg="#007bff",
            fg="white",
            font=("Arial", 10, "bold"),
            width=35,
            height=2,
            command=self.start_operator
        ).pack(pady=10)

        # PHASE 3: LONG ARMS (HP Cluster Control)
        phase3_frame = tk.LabelFrame(root, text="PHASE 3: HP CLUSTER OVERSEER", font=("Arial", 11, "bold"), fg="purple")
        phase3_frame.pack(pady=10, padx=20, fill="both", expand=True)

        self.cluster_status_label = tk.Label(
            phase3_frame,
            text="CLUSTER STATUS: UNKNOWN",
            font=("Courier", 9, "bold"),
            fg="gray"
        )
        self.cluster_status_label.pack(pady=5)

        tk.Button(
            phase3_frame,
            text="QUERY HP CLUSTER STATUS",
            bg="purple",
            fg="white",
            font=("Arial", 10, "bold"),
            width=35,
            command=self.query_cluster
        ).pack(pady=5)

        # EMERGENCY CONTROLS
        tk.Frame(root, height=2, bd=1, relief="sunken").pack(fill="x", padx=30, pady=10)

        tk.Button(
            root,
            text="EMERGENCY KILL SWITCH",
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

    def query_cluster(self):
        """Query the local k3s-manager for HP cluster status"""
        def _task():
            try:
                with httpx.Client(timeout=5.0) as client:
                    r = client.get(f"{K3S_MANAGER_URL}/cluster/status")
                    if r.status_code == 200:
                        data = r.json()
                        status_text = f"ONLINE: {data['nodes']} Nodes | {data['pods']['running']}/{data['pods']['total']} Pods Running"
                        self.cluster_status_label.config(text=status_text, fg="green")
                    else:
                        self.cluster_status_label.config(text="OFFLINE: MANAGER UNREACHABLE", fg="red")
            except Exception as e:
                self.cluster_status_label.config(text=f"ERROR: {str(e)[:40]}", fg="red")
        
        threading.Thread(target=_task, daemon=True).start()

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
        self.cpu_bar['value'] = cpu
        self.mem_bar['value'] = mem
        self.cpu_label.config(text=f"{cpu:.1f}%")
        self.mem_label.config(text=f"{mem:.1f}%")

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

        self.auto_killed = False
        
        # Determine the llama-server binary path (assuming ~/llama.cpp/build/bin/llama-server)
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
        self.status_label.config(text=f"BRAIN ACTIVE: {os.path.basename(model_full_path)} | Port {LLM_PORT}", fg="#28a745")

    def start_operator(self):
        """Launch Aider with optimized token mapping"""
        if not os.path.exists(CODE_DIR):
            return messagebox.showerror("Error", f"Code directory not found: {CODE_DIR}")

        # Use LLM_PORT for Aider connection
        cmd = (
            f"cd '{CODE_DIR}' && "
            f"export OPENAI_API_BASE=http://localhost:{LLM_PORT}/v1 && "
            f"export OPENAI_API_KEY=not-needed && "
            f"aider --architect --map-tokens {AIDER_MAP_TOKENS}"
        )

        subprocess.Popen(['cosmic-term', '--', 'bash', '-c', f"{cmd}; exec bash"])
        self.status_label.config(text=f"OPERATOR DEPLOYED (Port {LLM_PORT})", fg="#007bff")

    def open_obsidian(self):
        """Open Obsidian vault for mission logs"""
        if os.path.exists(OBSIDIAN_DIR):
            subprocess.Popen(['xdg-open', OBSIDIAN_DIR])
        else:
            messagebox.showerror("Error", f"Obsidian vault not found")

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