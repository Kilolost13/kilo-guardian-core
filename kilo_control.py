import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os

# --- CONFIGURATION (Change these paths if you moved your folders) ---
MODEL_DIR = os.path.expanduser("~/llama.cpp")
CODE_DIR = os.path.expanduser("~/Desktop/AI_stuff/old_hacksaw_fingers")
OBSIDIAN_DIR = os.path.expanduser("~/Documents/Obsidian Vault")

class KiloControl:
    def __init__(self, root):
        self.root = root
        self.root.title("KILO OPERATIONAL CONTROL (CPU MODE)")
        self.root.geometry("450x550")
        
        # COSMIC Desktop Fix: Forces window to register position before dropdown clicks
        self.root.update_idletasks()

        tk.Label(root, text="KILO AI SYSTEM CONTROL", font=("Arial", 14, "bold"), fg="#ff3b30").pack(pady=15)

        # 1. Model Selection
        tk.Label(root, text="Intelligence Model Select:", font=("Arial", 10, "bold")).pack()
        self.model_var = tk.StringVar()
        self.model_dropdown = ttk.Combobox(root, textvariable=self.model_var, width=45, state="readonly")
        self.refresh_models()
        self.model_dropdown.pack(pady=10)

        # 2. Operational Buttons
        # Note: Set to 12k context and CPU-only for stability on Beelink
        tk.Button(root, text="ACTIVATE BRAIN (12K Context / CPU)", bg="#28a745", fg="white", width=30, height=2,
                  command=self.start_server).pack(pady=10)
        
        tk.Button(root, text="DEPLOY OPERATOR (Aider)", bg="#007bff", fg="white", width=30, height=2,
                  command=self.start_aider).pack(pady=5)

        tk.Button(root, text="OPEN MISSION LOGS (Obsidian)", width=30,
                  command=lambda: subprocess.Popen(['xdg-open', OBSIDIAN_DIR])).pack(pady=10)

        # 3. Kill Switch
        tk.Frame(root, height=2, bd=1, relief="sunken").pack(fill="x", padx=30, pady=20)
        tk.Button(root, text="EMERGENCY SHUTDOWN", bg="#dc3545", fg="white", font=("Arial", 11, "bold"),
                  width=30, height=2, command=self.kill_everything).pack()

        self.status_label = tk.Label(root, text="SYSTEM STATUS: STANDBY", font=("Arial", 9), fg="gray")
        self.status_label.pack(side="bottom", pady=10)

    def refresh_models(self):
        try:
            if not os.path.exists(MODEL_DIR): 
                os.makedirs(MODEL_DIR)
            files = [f for f in os.listdir(MODEL_DIR) if f.endswith(".gguf")]
            self.model_dropdown['values'] = sorted(files)
            if files: 
                self.model_dropdown.current(0)
        except Exception as e: 
            print(f"Scan error: {e}")

    def start_server(self):
        model = self.model_var.get()
        if not model: 
            return messagebox.showwarning("!", "Select Model First")
        
        # TACTICAL SETTINGS:
        # -c 12288: Enough for your 10k repo + 2k room to talk
        # -ngl 0: DISBLES GPU TO PREVENT CRASHES
        # -t 8: Uses 8 Ryzen CPU threads
        full_cmd = f"cd {MODEL_DIR} && ./build/bin/llama-server -m {model} -c 12288 -ngl 0 -t 8"
        
        # Launching in cosmic-term (Pop!_OS 24.04 native)
        subprocess.Popen(['cosmic-term', '--', 'bash', '-c', f"{full_cmd}; exec bash"])
        
        self.status_label.config(text=f"BRAIN ACTIVE: {model} (CPU)", fg="#28a745")

    def start_aider(self):
        if not os.path.exists(CODE_DIR):
            return messagebox.showerror("Error", f"Repo folder not found at {CODE_DIR}")
            
        # Pointing Aider to the local server we just started
        full_cmd = f"cd '{CODE_DIR}' && export OPENAI_API_BASE=http://localhost:8080/v1 && export OPENAI_API_KEY=none && aider --architect"
        subprocess.Popen(['cosmic-term', '--', 'bash', '-c', f"{full_cmd}; exec bash"])
        self.status_label.config(text="OPERATOR DEPLOYED (Aider)", fg="#007bff")

    def kill_everything(self):
        # Cleans up both processes if things get stuck
        subprocess.run(["pkill", "-f", "llama-server"])
        subprocess.run(["pkill", "-f", "aider"])
        self.status_label.config(text="SYSTEM STATUS: ALL PROCESSES KILLED", fg="#dc3545")
        messagebox.showwarning("Kill Switch", "AI processes have been terminated.")

if __name__ == "__main__":
    root = tk.Tk()
    app = KiloControl(root)
    root.mainloop()