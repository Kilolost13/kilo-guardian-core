#!/usr/bin/env python3
"""
Kilo Chat Interface - Simple chat window to talk to the AI brain
"""

import tkinter as tk
from tkinter import scrolledtext, messagebox
import requests
import json
import threading

LLM_URL = "http://localhost:11434"

class KiloChat:
    def __init__(self, root):
        self.root = root
        self.root.title("💬 Chat with Kilo AI")
        self.root.geometry("700x600")

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
            text="Connected to Kilo AI Brain",
            font=("Arial", 9),
            fg="green",
            anchor="w"
        )
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

        # Chat history
        self.conversation_history = []

        # Welcome message
        self.add_message("KILO", "Hello! I'm Kilo, your AI assistant. How can I help you today?")

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
        else:
            prefix = "KILO: "
            self.chat_display.insert(tk.END, f"\n{prefix}", "kilo")
            self.chat_display.insert(tk.END, f"{message}\n", "kilo_text")
            self.chat_display.tag_config("kilo", foreground="#00ff00", font=("Arial", 11, "bold"))
            self.chat_display.tag_config("kilo_text", foreground="#00ff00")

        self.chat_display.see(tk.END)

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
        self.send_button.config(state=tk.DISABLED, text="Thinking...")
        self.status_label.config(text="Kilo is thinking...", fg="orange")

        # Get AI response in background thread
        threading.Thread(target=self.get_ai_response, daemon=True).start()

    def get_ai_response(self):
        """Get response from AI brain"""
        try:
            # Prepare request
            payload = {
                "model": "model",  # Doesn't matter, server already loaded
                "messages": [
                    {"role": "system", "content": "You are Kilo, a helpful AI assistant. You are part of a Long Arms architecture where you (running on Beelink) help control a Kubernetes cluster on an HP machine. Be concise and friendly."}
                ] + self.conversation_history[-10:],  # Last 10 messages for context
                "max_tokens": 512,
                "temperature": 0.7
            }

            # Send request
            response = requests.post(
                f"{LLM_URL}/v1/chat/completions",
                json=payload,
                timeout=60
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
        self.status_label.config(text="Connected to Kilo AI Brain", fg="green")
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
