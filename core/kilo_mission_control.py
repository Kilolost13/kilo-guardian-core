#!/usr/bin/env python3
"""
KILO MISSION CONTROL V3 - INTEGRATED AI CHAT + CLUSTER CONTROL
Combines cluster management with intelligent AI chat in one unified interface.

NEW IN V3:
- Integrated chat panel (no separate window)
- Memory system for learning preferences
- Smart command routing
- Tabbed interface for clean organization
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import subprocess
import os
import threading
import time
import psutil
import requests
import json

# Import Kilo V3 components
try:
    from kilo_memory import get_kilo_memory
    from kilo_router import get_kilo_router
    from kilo_pod_access import get_pod_access
    from kilo_auto_data_fetch import get_auto_fetch
    KILO_V3_AVAILABLE = True
except ImportError:
    KILO_V3_AVAILABLE = False
    print("Warning: Kilo V3 modules not found - chat will have limited features")

# --- CONFIGURATION ---
MODEL_DIR = os.path.expanduser("~/.lmstudio/models")
CODE_DIR = os.path.expanduser("~/Desktop/AI_stuff/old_hacksaw_fingers")
HP_IP = "192.168.68.56"
KUBECONFIG = os.path.expanduser("~/.kube/hp-k3s-config")
LLM_PORT = 8080  # llama.cpp server (change to 11434 for Ollama)
LLM_URL = f"http://localhost:{LLM_PORT}"

# Set environment
os.environ['KUBECONFIG'] = KUBECONFIG

# HARD-CODED STABILITY PARAMETERS (DO NOT MODIFY)
CONTEXT_SIZE = 8192
MAX_TOKENS = 1024
GPU_LAYERS = 0
THREADS = 4

# SAFETY THRESHOLDS
CPU_CRITICAL = 88
MEMORY_CRITICAL = 80
CPU_WARNING = 65
MEMORY_WARNING = 65
MONITOR_INTERVAL = 1.5


class KiloMissionControlV3:
    def __init__(self, root):
        self.root = root
        self.root.title("🚀 KILO MISSION CONTROL V3 - UNIFIED COMMAND CENTER")
        self.root.geometry("1000x900")

        # Initialize Kilo V3 components
        if KILO_V3_AVAILABLE:
            self.memory = get_kilo_memory()
            self.router = get_kilo_router()
            self.pod_access = get_pod_access()
            self.auto_fetch = get_auto_fetch()
        else:
            self.memory = None
            self.router = None
            self.pod_access = None
            self.auto_fetch = None

        # Model mapping
        self.model_paths = {}

        # Safety monitoring state
        self.monitoring = True
        self.cpu_high_time = 0
        self.auto_killed = False

        # Chat state
        self.conversation_history = []

        # Build UI
        self.build_ui()

        # Start safety monitoring thread
        self.monitor_thread = threading.Thread(target=self.safety_monitor, daemon=True)
        self.monitor_thread.start()

    def build_ui(self):
        """Build the unified UI"""
        # Header
        header = tk.Label(
            self.root,
            text="🚀 KILO UNIFIED COMMAND CENTER V3",
            font=("Arial", 18, "bold"),
            fg="#ff3b30"
        )
        header.pack(pady=10)

        # System Info
        info_frame = tk.Frame(self.root, relief="ridge", borderwidth=2)
        info_frame.pack(pady=5, padx=20, fill="x")

        status_text = f"OVERSEER (Beelink): 192.168.68.60 | WORKER (HP): {HP_IP}"
        if KILO_V3_AVAILABLE:
            status_text += " | AI: V3 (Smart + Memory)"
        tk.Label(
            info_frame,
            text=status_text,
            font=("Courier", 9, "bold"),
            fg="purple"
        ).pack(pady=3)

        # RAM status
        total_ram_gb = psutil.virtual_memory().total / (1024**3)
        ram_color = "green" if total_ram_gb >= 22 else "orange"
        tk.Label(
            info_frame,
            text=f"✓ {total_ram_gb:.1f} GB RAM available",
            font=("Courier", 8),
            fg=ram_color
        ).pack(pady=2)

        # SAFETY MONITOR PANEL (compact)
        self.build_safety_panel()

        # TABBED INTERFACE
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(pady=10, padx=20, fill="both", expand=True)

        # Tab 1: AI Brain + Chat
        self.chat_tab = tk.Frame(self.notebook)
        self.notebook.add(self.chat_tab, text="🧠 AI BRAIN + CHAT")
        self.build_chat_tab()

        # Tab 2: Cluster Control
        self.cluster_tab = tk.Frame(self.notebook)
        self.notebook.add(self.cluster_tab, text="🦾 CLUSTER CONTROL")
        self.build_cluster_tab()

        # Bottom status bar
        self.status_label = tk.Label(
            self.root,
            text="SYSTEM STATUS: STANDBY",
            font=("Arial", 10),
            fg="gray"
        )
        self.status_label.pack(side="bottom", pady=10)

        # Emergency kill button (always visible)
        tk.Button(
            self.root,
            text="🛑EMERGENCY KILL SWITCH",
            bg="#dc3545",
            fg="white",
            font=("Arial", 11, "bold"),
            width=30,
            height=1,
            command=self.emergency_kill
        ).pack(side="bottom", pady=5)

    def build_safety_panel(self):
        """Build compact safety monitor"""
        safety_frame = tk.LabelFrame(
            self.root,
            text="SAFETY MONITOR",
            font=("Arial", 9, "bold"),
            fg="#ff3b30"
        )
        safety_frame.pack(pady=5, padx=20, fill="x")

        # CPU and Memory in one row
        monitor_row = tk.Frame(safety_frame)
        monitor_row.pack(pady=5, fill="x", padx=10)

        # CPU
        tk.Label(monitor_row, text="CPU:", font=("Arial", 8, "bold"), width=5).pack(side="left")
        self.cpu_label = tk.Label(monitor_row, text="0%", font=("Courier", 9, "bold"), width=6)
        self.cpu_label.pack(side="left")
        self.cpu_bar = ttk.Progressbar(monitor_row, length=200, mode='determinate')
        self.cpu_bar.pack(side="left", padx=5)

        # Memory
        tk.Label(monitor_row, text="MEM:", font=("Arial", 8, "bold"), width=5).pack(side="left", padx=(10, 0))
        self.mem_label = tk.Label(monitor_row, text="0%", font=("Courier", 9, "bold"), width=15)
        self.mem_label.pack(side="left")
        self.mem_bar = ttk.Progressbar(monitor_row, length=200, mode='determinate')
        self.mem_bar.pack(side="left", padx=5)

        # Safety status
        self.safety_status = tk.Label(
            safety_frame,
            text="SYSTEM STABLE",
            font=("Arial", 8),
            fg="green"
        )
        self.safety_status.pack(pady=3)

    def build_chat_tab(self):
        """Build AI Brain + Chat interface"""
        # Model selection
        model_frame = tk.LabelFrame(self.chat_tab, text="AI Model Selection", font=("Arial", 10, "bold"))
        model_frame.pack(pady=10, padx=10, fill="x")

        self.model_var = tk.StringVar()
        self.model_dropdown = ttk.Combobox(
            model_frame,
            textvariable=self.model_var,
            width=60,
            state="readonly"
        )
        self.refresh_models()
        self.model_dropdown.pack(pady=5, padx=10)

        tk.Button(
            model_frame,
            text="🚀 ACTIVATE AI BRAIN",
            bg="#28a745",
            fg="white",
            font=("Arial", 10, "bold"),
            command=self.start_brain
        ).pack(pady=5)

        # Chat interface
        chat_frame = tk.LabelFrame(self.chat_tab, text="💬 Chat with Kilo AI", font=("Arial", 10, "bold"))
        chat_frame.pack(pady=10, padx=10, fill="both", expand=True)

        # Chat display
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            font=("Arial", 10),
            bg="#1e1e1e",
            fg="#00ff00",
            height=15
        )
        self.chat_display.pack(padx=10, pady=10, fill="both", expand=True)

        # Welcome message
        welcome = "🤖 Kilo V3 Ready!\n\n"
        if KILO_V3_AVAILABLE:
            welcome += "✅ Memory System Active\n✅ Command Router Active\n\nTry:\n"
            welcome += "• 'Teach: preference is value'\n"
            welcome += "• 'What's running?'\n"
            welcome += "• 'What did I tell you about...?'\n"
        else:
            welcome += "⚠️ Running in basic mode\n"
        self.add_chat_message("KILO", welcome)

        # Input area
        input_frame = tk.Frame(chat_frame)
        input_frame.pack(padx=10, pady=5, fill="x")

        tk.Label(input_frame, text="You:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)

        self.chat_input = tk.Entry(input_frame, font=("Arial", 10))
        self.chat_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.chat_input.bind("<Return>", lambda e: self.send_chat_message())

        self.send_button = tk.Button(
            input_frame,
            text="Send",
            bg="#007bff",
            fg="white",
            font=("Arial", 9, "bold"),
            command=self.send_chat_message
        )
        self.send_button.pack(side=tk.LEFT, padx=5)

        # Chat status
        self.chat_status = tk.Label(
            chat_frame,
            text="💡 Activate AI Brain first, then chat!",
            font=("Arial", 8),
            fg="orange"
        )
        self.chat_status.pack(pady=3)

    def build_cluster_tab(self):
        """Build cluster control interface"""
        # Cluster status display
        status_frame = tk.LabelFrame(self.cluster_tab, text="Cluster Status", font=("Arial", 10, "bold"))
        status_frame.pack(pady=10, padx=10, fill="both", expand=True)

        self.cluster_status_text = scrolledtext.ScrolledText(
            status_frame,
            height=15,
            font=("Courier", 9),
            bg="#1e1e1e",
            fg="#00ff00",
            wrap=tk.WORD
        )
        self.cluster_status_text.pack(pady=5, padx=10, fill="both", expand=True)
        self.cluster_status_text.insert("1.0", "Click 'REFRESH STATUS' to query cluster...")

        # Control buttons
        button_frame = tk.Frame(self.cluster_tab)
        button_frame.pack(pady=10)

        tk.Button(
            button_frame,
            text="🚀 START ALL",
            bg="#28a745",
            fg="white",
            font=("Arial", 10, "bold"),
            width=15,
            command=self.start_all_services
        ).grid(row=0, column=0, padx=5, pady=5)

        tk.Button(
            button_frame,
            text="⏹️ STOP ALL",
            bg="#dc3545",
            fg="white",
            font=("Arial", 10, "bold"),
            width=15,
            command=self.stop_all_services
        ).grid(row=0, column=1, padx=5, pady=5)

        tk.Button(
            button_frame,
            text="🔄 REFRESH",
            bg="#007bff",
            fg="white",
            font=("Arial", 10, "bold"),
            width=15,
            command=self.refresh_cluster_status
        ).grid(row=1, column=0, padx=5, pady=5)

        tk.Button(
            button_frame,
            text="⏰ WAKE HP",
            bg="#ffc107",
            fg="black",
            font=("Arial", 10, "bold"),
            width=15,
            command=self.wake_hp
        ).grid(row=1, column=1, padx=5, pady=5)

    # ========== CHAT FUNCTIONS ========== 

    def add_chat_message(self, sender, message):
        """Add message to chat display"""
        if sender == "YOU":
            self.chat_display.insert(tk.END, f"\n\x70 YOU: ", "user")
            self.chat_display.insert(tk.END, f"{message}\n", "user_text")
            self.chat_display.tag_config("user", foreground="#00bfff", font=("Arial", 10, "bold"))
            self.chat_display.tag_config("user_text", foreground="#ffffff")
        elif sender == "SYSTEM":
            self.chat_display.insert(tk.END, f"\n\x67 SYSTEM: ", "system")
            self.chat_display.insert(tk.END, f"{message}\n", "system_text")
            self.chat_display.tag_config("system", foreground="#ffc107", font=("Arial", 10, "bold"))
            self.chat_display.tag_config("system_text", foreground="#ffc107")
        else:
            self.chat_display.insert(tk.END, f"\n\x62 KILO: ", "kilo")
            self.chat_display.insert(tk.END, f"{message}\n", "kilo_text")
            self.chat_display.tag_config("kilo", foreground="#00ff00", font=("Arial", 10, "bold"))
            self.chat_display.tag_config("kilo_text", foreground="#00ff00")

        self.chat_display.see(tk.END)

    def send_chat_message(self):
        """Send message to AI"""
        message = self.chat_input.get().strip()
        if not message:
            return

        self.chat_input.delete(0, tk.END)
        self.add_chat_message("YOU", message)

        if not KILO_V3_AVAILABLE:
            self.add_chat_message("SYSTEM", "Kilo V3 modules not available. Install kilo_memory.py and kilo_router.py")
            return

        # Classify intent
        intent, _ = self.router.classify_intent(message)

        # Handle teach/recall directly
        if intent == "teach":
            response = self.handle_teach_command(message)
            self.add_chat_message("KILO", response)
            return

        if intent == "recall":
            response = self.handle_recall_command(message)
            self.add_chat_message("KILO", response)
            return

        # Add to history
        self.conversation_history.append({"role": "user", "content": message})

        # Get AI response in thread
        self.send_button.config(state=tk.DISABLED, text="Thinking...")
        self.chat_status.config(text="🤔 Kilo is thinking...", fg="orange")

        threading.Thread(target=self.get_ai_response, args=(intent,), daemon=True).start()

    def handle_teach_command(self, message):
        """Handle teach command"""
        key, value, category = self.router.parse_teach_command(message)
        if not key or not value:
            return "I couldn't understand. Try: 'Teach: key is value'"

        self.memory.teach_fact(key, value, category)
        return f"✓ Learned! {key} = '{value}' ({category})"

    def handle_recall_command(self, message):
        """Handle recall command"""
        key = self.router.parse_recall_command(message)
        value = self.memory.recall_fact(key) if key else None

        if value:
            return f"I remember: {key} = '{value}'"
        return f"I don't remember anything about '{key}'"

    def get_ai_response(self, intent):
        """Get AI response with cluster context"""
        try:
            # Get cluster context if needed
            cluster_context = ""
            if self.router.should_query_cluster(intent):
                self.root.after(0, lambda: self.chat_status.config(text="📊 Querying cluster...", fg="orange"))
                # Pass intent to help it decide which data to fetch
                cluster_context = self.get_cluster_context_for_ai(intent)

            # Get memory summary
            memory_summary = self.memory.get_memory_summary()

            # Build system prompt
            system_prompt = f"""You are Kilo, an intelligent AI assistant with real-time cluster access and memory.

INTENT: {intent}

"""
            if cluster_context:
                system_prompt += f"{cluster_context}\n\n"

            if memory_summary:
                system_prompt += f"{memory_summary}\n\n"

            system_prompt += """YOU HAVE AUTOMATIC FULL CLUSTER DATA ACCESS:

IMPORTANT - DATA IS AUTOMATICALLY FETCHED:
When user asks about cluster data, you receive COMPREHENSIVE REAL DATA including:
- Logs from ALL running pods (last 200 lines each)
- Environment variables from all pods
- Database contents (if databases exist in pods)
- API responses (common endpoints automatically probed)
- File contents from common data directories
- Process lists
- Disk usage

The data below is REAL, ACTUAL data from the cluster - NOT metadata!

HOW TO USE THIS DATA:
1. User asks: "Analyze my finance data"
2. You receive: ACTUAL logs, database content, API responses from finance pods
3. You analyze: The REAL data you see below
4. You respond: With specific insights based on ACTUAL numbers/data

EXAMPLE - Finance Analysis:
User: "How's my spending?"
You see in the data: [Actual database rows showing transactions]
You respond: "Based on your transaction history, you spent $X on Y..."

CRITICAL RULES:
- The cluster data provided IS REAL - analyze it!
- Don't ask "which pod?" - you have data from ALL running pods
- Don't ask "what data?" - you have logs, databases, files, APIs
- If data is empty/missing, pod might be stopped - tell user to start it
- Be specific - cite actual numbers, log entries, database values you see

DO NOT HALLUCINATE:
- Only analyze data that's actually in the cluster data below
- If you don't see finance data, say "No finance pod is running"
- If database is empty, say "Database has no data"
- If you see errors in logs, report the ACTUAL errors

Architecture: Beelink (overseer) + HP k3s cluster (worker)
Already installed: Helm, Prometheus, Grafana
DATA ACCESS: AUTOMATIC - comprehensive data fetched from all running pods!
"""

            # Send to AI
            payload = {
                "model": "model",
                "messages": [
                    {"role": "system", "content": system_prompt}
                ] + self.conversation_history[-10:]
            }

            response = requests.post(
                f"{LLM_URL}/v1/chat/completions",
                json=payload,
                timeout=90
            )

            if response.status_code == 200:
                ai_message = response.json()['choices'][0]['message']['content']
                self.conversation_history.append({"role": "assistant", "content": ai_message})
                self.root.after(0, lambda: self.display_ai_response(ai_message))
            else:
                self.root.after(0, lambda: self.display_chat_error(f"AI error: {response.status_code}"))

        except Exception as e:
            self.root.after(0, lambda: self.display_chat_error(str(e)))

    def display_ai_response(self, message):
        """Display AI response"""
        self.add_chat_message("KILO", message)
        self.send_button.config(state=tk.NORMAL, text="Send")
        self.chat_status.config(text="✅ Ready", fg="green")

    def display_chat_error(self, error):
        """Display chat error"""
        self.add_chat_message("SYSTEM", f"⚠️ {error}")
        self.send_button.config(state=tk.NORMAL, text="Send")
        self.chat_status.config(text="❌ Error", fg="red")

    def get_cluster_context_for_ai(self, intent="general"):
        """
        Get COMPREHENSIVE cluster data for AI
        Automatically fetches ALL available data from running pods
        """
        # Check HP reachability
        ping_result = subprocess.run(["ping", "-c", "1", "-W", "2", HP_IP], capture_output=True)

        if ping_result.returncode != 0:
            return f"=== HP CLUSTER OFFLINE ===\nHP ({HP_IP}): NOT REACHABLE"

        # Try to get data
        try:
            # If the user is asking for advice or a follow-up, 
            # and there's previous context about finances, 
            # we should check if they're asking about finance specifically.
            
            # Simple heuristic: if intent is advice or follow-up, check finance pods first
            if intent in ["advice", "follow_up"]:
                print("Checking for finance pods...")
                finance_data = self.auto_fetch.get_finance_specific_data()
                if finance_data["finance_pods"]:
                    print(f"Found {len(finance_data['finance_pods'])} finance pods. Fetching data...")
                    # We wrap the specific finance data in a standard cluster data format
                    # but only for the finance pods
                    formatted = "=== FINANCE DATA FETCHED ===\n"
                    for pod in finance_data["finance_pods"]:
                        if pod in finance_data["finance_data"]:
                            pod_formatted = self.auto_fetch.format_data_for_ai({
                                "total_pods": 1,
                                "running_pods": 1,
                                "pods": [pod],
                                "data_by_pod": {pod: finance_data["finance_data"][pod]}
                            })
                            formatted += pod_formatted + "\n"
                    return formatted

            # Default to full cluster fetch
            print("Auto-fetching full cluster data...")
            cluster_data = self.auto_fetch.fetch_all_cluster_data()
            formatted_data = self.auto_fetch.format_data_for_ai(cluster_data)
            return formatted_data
        except Exception as e:
            # Fallback to basic metadata if auto-fetch fails
            context_parts = [f"=== HP CLUSTER STATE (Basic) ==="]
            context_parts.append(f"HP ({HP_IP}): ONLINE")
            context_parts.append(f"Note: Auto data fetch failed: {e}")

            # Get deployments
            stdout, _, rc = self.run_kubectl(["get", "deployments", "-n", "default", "--no-headers"])
            if rc == 0 and stdout:
                context_parts.append(f"\nDeployments:\n{stdout}")

            return "\n".join(context_parts)

    # ========== CLUSTER FUNCTIONS ========== 

    def run_kubectl(self, args):
        """Run kubectl command"""
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
        """Query and display cluster status"""
        def _task():
            self.update_cluster_display("Querying HP cluster...\n")

            ping_result = subprocess.run(["ping", "-c", "1", "-W", "2", HP_IP], capture_output=True)

            if ping_result.returncode != 0:
                self.update_cluster_display(f"❌ HP OFFLINE\nCannot reach {HP_IP}")
                return

            output = ["="*60, "HP K3S CLUSTER STATUS", "="*60, ""]

            # Nodes
            stdout, _, rc = self.run_kubectl(["get", "nodes", "-o", "wide"])
            if rc == 0:
                output.append("NODES:")
                output.append(stdout)

            # Pods
            stdout, _, rc = self.run_kubectl(["get", "pods", "-n", "default"])
            if rc == 0:
                output.append("\nPODS:")
                output.append(stdout)

            # Deployments
            stdout, _, rc = self.run_kubectl(["get", "deployments", "-n", "default"])
            if rc == 0:
                output.append("\nDEPLOYMENTS:")
                output.append(stdout)

            self.update_cluster_display("\n".join(output))

        threading.Thread(target=_task, daemon=True).start()

    def update_cluster_display(self, text):
        """Update cluster display (thread-safe)"""
        def _update():
            self.cluster_status_text.delete("1.0", tk.END)
            self.cluster_status_text.insert("1.0", text)
        self.root.after(0, _update)

    def start_all_services(self):
        """Start all services"""
        if not messagebox.askyesno("Confirm", "Start all services?"):
            return

        def _task():
            stdout, _, rc = self.run_kubectl(["get", "deployments", "-n", "default", "-o", "name"])
            if rc != 0:
                return

            for dep in stdout.split('\n'):
                if dep.strip():
                    self.run_kubectl(["scale", dep.strip(), "-n", "default", "--replicas=1"])

            time.sleep(10)
            self.refresh_cluster_status()

        threading.Thread(target=_task, daemon=True).start()

    def stop_all_services(self):
        """Stop all services"""
        if not messagebox.askyesno("Confirm", "Stop all services?"):
            return

        def _task():
            self.run_kubectl(["scale", "deployment", "--all", "-n", "default", "--replicas=0"])
            time.sleep(3)
            self.refresh_cluster_status()

        threading.Thread(target=_task, daemon=True).start()

    def wake_hp(self):
        """Wake HP"""
        result = subprocess.run(["ping", "-c", "1", "-W", "2", HP_IP], capture_output=True)
        if result.returncode == 0:
            messagebox.showinfo("HP Status", f"HP is already online at {HP_IP}")
        else:
            messagebox.showwarning("HP Status", f"HP is offline. Power it on manually.")

    # ========== MODEL FUNCTIONS ========== 

    def refresh_models(self):
        """Scan for .gguf models"""
        self.model_paths = {}
        display_names = []

        if os.path.exists(MODEL_DIR):
            for root, _, files in os.walk(MODEL_DIR):
                for file in files:
                    if file.endswith(".gguf") and not file.startswith("mmproj"):
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, MODEL_DIR)
                        self.model_paths[rel_path] = full_path
                        display_names.append(rel_path)

        self.model_dropdown['values'] = sorted(display_names)
        if display_names:
            self.model_dropdown.current(0)

    def start_brain(self):
        """Start AI brain"""
        display_name = self.model_var.get()
        if not display_name:
            return messagebox.showwarning("Warning", "Select a model first")

        model_path = self.model_paths.get(display_name)
        if not model_path:
            return messagebox.showerror("Error", "Model not found")

        # Check for existing server
        existing = subprocess.run(["pgrep", "-f", "llama-server"], capture_output=True, text=True)
        if existing.stdout.strip():
            if messagebox.askyesno("Model Running", "Kill old model and load new one?"):
                subprocess.run(["pkill", "-f", "llama-server"])
                time.sleep(2)
            else:
                return

        self.auto_killed = False

        server_bin = os.path.expanduser("~/llama.cpp/build/bin/llama-server")
        cmd = f"{server_bin} -m '{model_path}' -c {CONTEXT_SIZE} -n {MAX_TOKENS} -ngl {GPU_LAYERS} -t {THREADS} --port {LLM_PORT}"

        subprocess.Popen(['cosmic-term', '--', 'bash', '-c', f"{cmd}; exec bash"])
        self.status_label.config(text=f"AI BRAIN ACTIVE: {os.path.basename(model_path)}", fg="#28a745")
        self.chat_status.config(text="✅ AI Brain active - Ready to chat!", fg="green")

    # ========== SAFETY FUNCTIONS ========== 

    def safety_monitor(self):
        """Background safety monitoring"""
        while self.monitoring:
            try:
                cpu = psutil.cpu_percent(interval=1)
                mem = psutil.virtual_memory().percent
                mem_avail_gb = psutil.virtual_memory().available / (1024**3)

                self.root.after(0, self.update_safety_display, cpu, mem)

                if mem_avail_gb < 2.0 or mem > MEMORY_CRITICAL:
                    self.root.after(0, self.auto_emergency_kill, "MEMORY OVERLOAD", mem)
                elif cpu > CPU_CRITICAL:
                    self.cpu_high_time += MONITOR_INTERVAL
                    if self.cpu_high_time >= 5:
                        self.root.after(0, self.auto_emergency_kill, "CPU OVERLOAD", cpu)
                else:
                    self.cpu_high_time = 0

            except Exception as e:
                print(f"Safety monitor error: {e}")

            time.sleep(MONITOR_INTERVAL)

    def update_safety_display(self, cpu, mem):
        """Update safety display"""
        mem_info = psutil.virtual_memory()
        mem_used_gb = mem_info.used / (1024**3)
        mem_total_gb = mem_info.total / (1024**3)

        self.cpu_bar['value'] = cpu
        self.mem_bar['value'] = mem
        self.cpu_label.config(text=f"{cpu:.1f}%")
        self.mem_label.config(text=f"{mem:.1f}% ({mem_used_gb:.1f}/{mem_total_gb:.0f}GB)")

        if cpu >= CPU_CRITICAL or mem >= MEMORY_CRITICAL:
            color = "#dc3545"
            status = "CRITICAL"
        elif cpu >= CPU_WARNING or mem >= MEMORY_WARNING:
            color = "#ffc107"
            status = "WARNING"
        else:
            color = "#28a745"
            status = "STABLE"

        self.cpu_label.config(fg=color)
        self.mem_label.config(fg=color)
        if not self.auto_killed:
            self.safety_status.config(text=status, fg=color)

    def auto_emergency_kill(self, reason, value):
        """Auto emergency shutdown"""
        if self.auto_killed:
            return

        self.auto_killed = True
        subprocess.run(["pkill", "-9", "-f", "llama-server"], check=False)

        self.safety_status.config(text=f"AUTO-KILLED: {reason}", fg="#dc3545")
        messagebox.showerror("AUTO SHUTDOWN", f"{reason}: {value}")

    def emergency_kill(self):
        """Manual emergency kill"""
        subprocess.run(["pkill", "-f", "llama-server"], check=False)
        subprocess.run(["pkill", "-f", "aider"], check=False)
        self.auto_killed = False
        self.status_label.config(text="MANUAL SHUTDOWN", fg="#dc3545")
        messagebox.showinfo("Emergency Kill", "All AI processes terminated")


if __name__ == "__main__":
    root = tk.Tk()
    app = KiloMissionControlV3(root)
    root.mainloop()
