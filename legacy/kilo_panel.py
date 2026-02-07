import tkinter as tk
import subprocess
import os

def run_script(path):
    # This launches your script in a brand new terminal window
    subprocess.Popen(['gnome-terminal', '--', 'bash', '-c', f'{path}; exec bash'])

root = tk.Tk()
root.title("Kilo AI Control Panel")
root.geometry("300x400")

tk.Label(root, text="Kilo AI Systems", font=("Arial", 14, "bold")).pack(pady=10)

# Button 1: Start the Server
tk.Button(root, text="1. Start Brain (Server)", width=25, bg="gray", 
          command=lambda: run_script('/home/brain_ai/Desktop/start_brain.sh')).pack(pady=5)

# Button 2: Start Aider
tk.Button(root, text="2. Launch Operator (Aider)", width=25, bg="green", fg="white",
          command=lambda: run_script('/home/brain_ai/Desktop/start_kilo_docs.sh')).pack(pady=5)

# Button 3: Open Obsidian
tk.Button(root, text="3. Open Obsidian Vault", width=25,
          command=lambda: subprocess.Popen(['xdg-open', '/home/brain_ai/Documents/Obsidian Vault/'])).pack(pady=5)

root.mainloop()