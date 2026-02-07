import tkinter as tk
from tkinter import ttk, scrolledtext, font, messagebox
import threading
import time
import requests
import psutil
import os
import sys
import subprocess

# Configuration
API_URL = "http://localhost:9004/chat"
THEME = {
    "bg": "#0d1117",        # Dark background
    "fg": "#c9d1d9",        # Light text
    "accent": "#3fb950",    # Zombie Green
    "warning": "#d29922",   # Yellow
    "danger": "#f85149",    # Red
    "panel_bg": "#161b22",  # Slightly lighter panel
    "input_bg": "#0d1117"
}
SAFE_TEMP_LIMIT = 75.0  # Degrees Celsius
MAX_CHARS = 1500

class KiloGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Kilo Mission Control - Safe Mode")
        self.root.geometry("900x650")
        self.root.configure(bg=THEME["bg"])
        
        self.mode = "ECO" # Default start mode

        # Custom Fonts
        self.font_main = font.Font(family="Segoe UI", size=10)
        self.font_mono = font.Font(family="Consolas", size=9)
        self.font_header = font.Font(family="Segoe UI", size=12, weight="bold")

        self.setup_layout()
        
        # Start background threads
        self.running = True
        self.monitor_thread = threading.Thread(target=self.update_stats_loop, daemon=True)
        self.monitor_thread.start()

        # Initial greeting
        self.add_message("System", "Mission Control ready. Monitoring Beelink vitals...", "system")

    def setup_layout(self):
        # Main Container: Split into Chat (Left) and Vitals (Right)
        main_frame = tk.Frame(self.root, bg=THEME["bg"])
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # --- LEFT: CHAT AREA ---
        chat_frame = tk.Frame(main_frame, bg=THEME["bg"])
        chat_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # Header
        header_frame = tk.Frame(chat_frame, bg=THEME["bg"])
        header_frame.pack(fill="x", pady=(0, 5))
        
        tk.Label(header_frame, text="🧠 KILO AI", font=self.font_header, 
                         bg=THEME["bg"], fg=THEME["accent"], anchor="w").pack(side="left")
        
        # Action Buttons Frame
        btn_frame = tk.Frame(header_frame, bg=THEME["bg"])
        btn_frame.pack(side="right")

        # Sync Vault Button
        self.sync_btn = tk.Button(btn_frame, text="📥 SYNC VAULT", command=self.sync_vault,
                                bg="#21262d", fg="white", font=("Segoe UI", 9),
                                activebackground="#30363d", activeforeground="white",
                                bd=0, padx=10)
        self.sync_btn.pack(side="left", padx=5)

        # Sync Gmail Button
        self.gmail_btn = tk.Button(btn_frame, text="📧 SYNC GMAIL", command=self.sync_gmail,
                                bg="#21262d", fg="white", font=("Segoe UI", 9),
                                activebackground="#30363d", activeforeground="white",
                                bd=0, padx=10)
        self.gmail_btn.pack(side="left", padx=5)

        # Mode Switch Button
        self.mode_btn = tk.Button(btn_frame, text="MODE: ECO 🍃", command=self.toggle_mode,
                                bg="#238636", fg="white", font=("Segoe UI", 9, "bold"),
                                activebackground="#2ea043", activeforeground="white",
                                bd=0, padx=10)
        self.mode_btn.pack(side="left")

        # Chat History
        self.chat_display = scrolledtext.ScrolledText(chat_frame, 
                                                    bg=THEME["panel_bg"], 
                                                    fg=THEME["fg"],
                                                    font=self.font_main,
                                                    insertbackground=THEME["accent"],
                                                    borderwidth=0,
                                                    padx=10, pady=10)
        self.chat_display.pack(fill="both", expand=True, pady=(0, 10))
        self.chat_display.tag_config("user", foreground=THEME["accent"], font=("Segoe UI", 10, "bold"))
        self.chat_display.tag_config("ai", foreground=THEME["fg"])
        self.chat_display.tag_config("system", foreground=THEME["warning"], font=("Consolas", 9, "italic"))
        self.chat_display.tag_config("error", foreground=THEME["danger"])
        self.chat_display.configure(state="disabled")

        # Input Area
        input_frame = tk.Frame(chat_frame, bg=THEME["bg"])
        input_frame.pack(fill="x")

        self.char_counter = tk.Label(input_frame, text=f"0 / {MAX_CHARS}", 
                                   bg=THEME["bg"], fg="#8b949e", font=self.font_mono)
        self.char_counter.pack(anchor="e")

        self.input_entry = tk.Entry(input_frame, 
                                  bg=THEME["input_bg"], 
                                  fg="white", 
                                  insertbackground="white",
                                  font=self.font_main,
                                  relief="flat",
                                  highlightthickness=1,
                                  highlightbackground="#30363d",
                                  highlightcolor=THEME["accent"])
        self.input_entry.pack(fill="x", ipady=8)
        self.input_entry.bind("<Return>", self.send_message)
        self.input_entry.bind("<KeyRelease>", self.update_counter)

        # --- RIGHT: VITALS PANEL ---
        vitals_frame = tk.Frame(main_frame, bg=THEME["panel_bg"], width=250)
        vitals_frame.pack(side="right", fill="y", ipadx=10)
        vitals_frame.pack_propagate(False) # Force width

        tk.Label(vitals_frame, text="HARDWARE VITALS", font=self.font_mono, 
                 bg=THEME["panel_bg"], fg="#8b949e").pack(pady=10)

        # CPU Temp
        self.temp_label = self.create_vital_widget(vitals_frame, "CPU TEMP", "0°C")
        # CPU Load
        self.load_label = self.create_vital_widget(vitals_frame, "CPU LOAD", "0%")
        # RAM Usage
        self.ram_label = self.create_vital_widget(vitals_frame, "RAM USAGE", "0%")
        
        # Status Light
        self.status_canvas = tk.Canvas(vitals_frame, width=20, height=20, bg=THEME["panel_bg"], highlightthickness=0)
        self.status_canvas.pack(pady=20)
        self.status_light = self.status_canvas.create_oval(2, 2, 18, 18, fill=THEME["accent"], outline="")
        self.status_text = tk.Label(vitals_frame, text="SYSTEM NORMAL", bg=THEME["panel_bg"], fg=THEME["accent"], font=self.font_mono)
        self.status_text.pack()

    def sync_vault(self):
        self.sync_btn.config(state="disabled", text="READING...")
        self.add_message("System", "Syncing Vault folder... (Scanning for new files)", "system")
        
        def run_sync():
            try:
                # Use venv python to run ingestor
                venv_python = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv/bin/python3")
                script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vault_ingestor.py")
                
                result = subprocess.run([venv_python, script_path], capture_output=True, text=True)
                
                # Update UI from thread
                self.root.after(0, lambda: self.add_message("System", f"Vault Sync Result: {result.stdout.strip()}", "system"))
            except Exception as e:
                self.root.after(0, lambda: self.add_message("Error", f"Vault sync failed: {e}", "error"))
            finally:
                self.root.after(0, lambda: self.sync_btn.config(state="normal", text="📥 SYNC VAULT"))

        threading.Thread(target=run_sync, daemon=True).start()

    def sync_gmail(self):
        user = os.environ.get("KILO_EMAIL_USER")
        pw = os.environ.get("KILO_EMAIL_PASS")

        if not user or not pw:
            # Simple credential check
            self.add_message("System", "Gmail credentials missing. Run Kilo with KILO_EMAIL_USER and KILO_EMAIL_PASS set.", "error")
            return

        self.gmail_btn.config(state="disabled", text="CHECKING...")
        self.add_message("System", f"Syncing Gmail label 'To Kilo' for {user}...", "system")
        
        def run_sync():
            try:
                venv_python = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv/bin/python3")
                script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "email_ingestor.py")
                
                result = subprocess.run([venv_python, script_path], capture_output=True, text=True)
                self.root.after(0, lambda: self.add_message("System", f"Gmail Sync Result: {result.stdout.strip()}", "system"))
            except Exception as e:
                self.root.after(0, lambda: self.add_message("Error", f"Gmail sync failed: {e}", "error"))
            finally:
                self.root.after(0, lambda: self.gmail_btn.config(state="normal", text="📧 SYNC GMAIL"))

        threading.Thread(target=run_sync, daemon=True).start()

    def toggle_mode(self):
        new_mode = "SMART" if self.mode == "ECO" else "ECO"
        
        if not messagebox.askyesno("Switch Mode", f"Switch to {new_mode} mode?\n\nThis will restart the AI Brain. It takes about 15-20 seconds."):
            return

        self.add_message("System", f"Switching to {new_mode} mode... Please wait.", "system")
        self.mode_btn.config(state="disabled", text="SWITCHING...")
        
        # Determine script
        script = "start_kilo_smart.sh" if new_mode == "SMART" else "start_kilo_eco.sh"
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), script)
        
        # Launch in background
        try:
            # We use a terminal emulator to run the script so the user can see the log output
            # Try gnome-terminal (common on Pop!_OS) or x-terminal-emulator
            subprocess.Popen(["gnome-terminal", "--", "bash", "-c", f"{script_path}; exec bash"])
            
            self.mode = new_mode
            if self.mode == "SMART":
                self.mode_btn.config(text="MODE: SMART 🧠", bg="#8957e5") # Purple for smart
            else:
                self.mode_btn.config(text="MODE: ECO 🍃", bg="#238636")   # Green for eco
                
        except Exception as e:
            self.add_message("Error", f"Failed to switch mode: {e}", "error")
        finally:
            self.mode_btn.config(state="normal")

    def create_vital_widget(self, parent, title, value):
        frame = tk.Frame(parent, bg=THEME["panel_bg"], pady=5)
        frame.pack(fill="x")
        tk.Label(frame, text=title, font=("Consolas", 8), bg=THEME["panel_bg"], fg="#8b949e").pack()
        lbl = tk.Label(frame, text=value, font=("Segoe UI", 24, "bold"), bg=THEME["panel_bg"], fg=THEME["fg"])
        lbl.pack()
        return lbl

    def update_counter(self, event=None):
        text = self.input_entry.get()
        count = len(text)
        
        # Enforce Limit
        if count > MAX_CHARS:
            self.input_entry.delete(MAX_CHARS, tk.END)
            text = self.input_entry.get()
            count = MAX_CHARS
            self.root.bell() # Beep

        self.char_counter.config(text=f"{count} / {MAX_CHARS}")
        
        if count >= MAX_CHARS:
            self.char_counter.config(fg=THEME["danger"])
            self.input_entry.config(highlightbackground=THEME["danger"], highlightcolor=THEME["danger"])
        elif count >= 1200:
            self.char_counter.config(fg=THEME["warning"])
            self.input_entry.config(highlightbackground=THEME["warning"], highlightcolor=THEME["warning"])
        else:
            self.char_counter.config(fg="#8b949e")
            self.input_entry.config(highlightbackground="#30363d", highlightcolor=THEME["accent"])

    def add_message(self, sender, text, tag):
        self.chat_display.configure(state="normal")
        self.chat_display.insert(tk.END, f"\n{sender}:\n", tag)
        self.chat_display.insert(tk.END, f"{text}\n")
        self.chat_display.see(tk.END)
        self.chat_display.configure(state="disabled")

    def send_message(self, event=None):
        msg = self.input_entry.get().strip()
        if not msg: return

        self.input_entry.delete(0, tk.END)
        self.update_counter()
        self.add_message("You", msg, "user")

        # Send in background thread
        threading.Thread(target=self._send_api_request, args=(msg,), daemon=True).start()

    def _send_api_request(self, msg):
        try:
            self.status_text.config(text="PROCESSING...", fg=THEME["warning"])
            self.status_canvas.itemconfig(self.status_light, fill=THEME["warning"])
            
            response = requests.post(API_URL, json={"message": msg}, timeout=60)
            data = response.json()
            
            if "response" in data:
                # Check for circuit breaker messages in the response
                reply = data["response"]
                if reply.startswith("❄️") or reply.startswith("⚡"):
                     self.add_message("Kilo (Safety)", reply, "system")
                else:
                     self.add_message("Kilo", reply, "ai")
            else:
                self.add_message("Error", "Invalid response from brain.", "error")

        except Exception as e:
            self.add_message("Error", f"Could not connect to Kilo: {e}", "error")
        finally:
            self.reset_status()

    def reset_status(self):
        # Allow stats loop to set the color/text back
        pass

    def update_stats_loop(self):
        while self.running:
            try:
                # 1. CPU Load
                cpu_pct = psutil.cpu_percent()
                self.load_label.config(text=f"{cpu_pct}%")

                # 2. RAM Usage
                ram_pct = psutil.virtual_memory().percent
                self.ram_label.config(text=f"{ram_pct}%")

                # 3. Temperature (Linux specific attempt)
                temp = 0.0
                try:
                    # Generic Linux thermal zone check
                    temps = psutil.sensors_temperatures()
                    if 'k10temp' in temps: # AMD CPU (Common in Beelinks)
                        temp = temps['k10temp'][0].current
                    elif 'coretemp' in temps: # Intel CPU
                        temp = temps['coretemp'][0].current
                    elif 'acpitz' in temps: # Generic ACPI
                        temp = temps['acpitz'][0].current
                    else:
                        # Fallback: try first available
                        for name, entries in temps.items():
                            if entries:
                                temp = entries[0].current
                                break
                except Exception:
                    temp = 0.0

                self.temp_label.config(text=f"{temp:.1f}°C")

                # Safety Warnings
                if temp > SAFE_TEMP_LIMIT:
                    self.temp_label.config(fg=THEME["danger"])
                    self.status_text.config(text="OVERHEATING!", fg=THEME["danger"])
                    self.status_canvas.itemconfig(self.status_light, fill=THEME["danger"])
                elif cpu_pct > 90:
                    self.load_label.config(fg=THEME["warning"])
                    self.status_text.config(text="HIGH LOAD", fg=THEME["warning"])
                    self.status_canvas.itemconfig(self.status_light, fill=THEME["warning"])
                else:
                    self.temp_label.config(fg=THEME["fg"])
                    self.load_label.config(fg=THEME["fg"])
                    self.status_text.config(text="SYSTEM NORMAL", fg=THEME["accent"])
                    self.status_canvas.itemconfig(self.status_light, fill=THEME["accent"])

            except Exception as e:
                print(f"Monitor error: {e}")

            time.sleep(2)

if __name__ == "__main__":
    # Ensure psutil is installed
    try:
        import psutil
    except ImportError:
        print("Installing required package 'psutil'...")
        os.system("pip3 install psutil")
        import psutil

    # Ensure requests is installed
    try:
        import requests
    except ImportError:
        print("Installing required package 'requests'...")
        os.system("pip3 install requests")
        import requests

    root = tk.Tk()
    app = KiloGUI(root)
    root.mainloop()
