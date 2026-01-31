# Kilo AI: System Architecture & Modification Guide

Kilo is a **Local-First, Privacy-First AI Agent** optimized for low-power hardware (like Beelink mini-PCs). Unlike cloud AIs (ChatGPT), Kilo lives entirely on your hard drive and does not require an internet connection to think.

---

## 1. The Core Components (The "Trinity")

### A. The Inference Engine (`llama.cpp`)
*   **What it is:** The "Engine Room." It loads the AI model and handles the heavy math.
*   **Location:** `~/llama.cpp/build/bin/llama-server`
*   **Key Logic:** We run this with specific "Safe Flags":
    *   `-ngl 0`: Disables GPU (prevents power spikes).
    *   `-t 2` or `-t 4`: Limits CPU threads (keeps the Beelink from "shitting the bed").

### B. The AI Brain (FastAPI Service)
*   **What it is:** The "Pre-frontal Cortex." It handles your requests, manages memory, and talks to the Engine.
*   **Location:** `services/ai_brain/main.py`
*   **How to Modify Personality:** Edit `services/ai_brain/rag.py`. Look for the `system_prompt` string. This is where you tell Kilo to be "witty," "concise," or "aggressive."

### C. The Mission Control (Desktop GUI)
*   **What it is:** The "Dashboard." A Python/Tkinter app that gives you a window into the system.
*   **Location:** `Kilo-gui.py`
*   **Key Feature:** The hardware monitor. It uses `psutil` to read your Beelink's temperature and load in real-time.

---

## 2. The Memory System (RAG)

Kilo uses **RAG (Retrieval-Augmented Generation)**. 
1.  **Ingestion:** When you use the **Vault** or **Gmail Sync**, the text is broken into small chunks.
2.  **Embedding:** Each chunk is turned into a math vector (using `all-MiniLM-L6-v2`).
3.  **Retrieval:** When you ask a question, Kilo turns your question into math, finds the most similar chunks in his database, and says: *"Based on these notes I found in your Vault, here is the answer..."*

**Database Location:** `/data/ai_brain.db` (SQLite)

---

## 3. The Safety Layer (Circuit Breaker)

This is the "Breaker Box" we installed to prevent hardware crashes.
*   **File:** `services/ai_brain/circuit_breaker.py`
*   **Logic:** It enforces a **1500 character limit** and a **5-second cooldown**.
*   **Modification:** If you move Kilo to a powerful gaming PC later, you can disable this or raise the limits in this file.

---

## 4. How to Export Kilo

If you want to move Kilo to another Linux machine:

1.  **The Code:** Copy the entire `old_hacksaw_fingers` directory.
2.  **The Models:** Copy your `.gguf` files from `~/.lmstudio/models/...` to the same path on the new machine.
3.  **The Engine:** You must have `llama.cpp` installed on the new machine (or compile it there).
4.  **The Environment:** 
    *   Run `python3 -m venv venv`
    *   Run `./venv/bin/pip install -r requirements.txt` (or manually install `fastapi`, `uvicorn`, `sqlmodel`, `psutil`).

---

## 5. File Map for Developers

| File | Purpose | Why touch it? |
| :--- | :--- | :--- |
| `start_kilo_eco.sh` | Launches Phi-3 mode | Change CPU thread limits |
| `start_kilo_smart.sh`| Launches Llama 3.1 mode | Point to a new/smarter model |
| `services/ai_brain/rag.py` | Prompt & RAG logic | Change his "voice" or how he remembers |
| `vault_ingestor.py` | File reading logic | Add support for PDF or Word docs |
| `email_ingestor.py` | Gmail Bridge | Change which labels/folders he watches |
| `Kilo-gui.py` | Desktop Application | Add new buttons or hardware stats |

---

## 6. Extending Kilo: The Developer's Cookbook

### How to Change Kilo's Personality
1.  Open `services/ai_brain/rag.py`.
2.  Find the variable `system_prompt`.
3.  Change the description. 
    *   *Example:* If you want him to be a "Grumpy System Administrator," tell him exactly that in the bullet points.
4.  Restart the AI Brain script.

### How to Add a New "Eye" (Connector)
If you want Kilo to see a new source of data (like a Calendar or Todo list):
1.  Create a new script (e.g., `calendar_ingestor.py`) based on the `vault_ingestor.py` template.
2.  Your script should fetch the data, format it as text, and send a POST request to `http://localhost:9004/chat` with the message format: `/remember [SOURCE NAME]: Your text here`.
3.  To add a button for it in the GUI, open `Kilo-gui.py` and duplicate the `sync_vault` logic.

### How to Adjust Safety for Better Hardware
If you move Kilo to a machine that isn't "power fragile":
1.  **Thread Count:** Open `start_kilo_smart.sh` and change `-t 2` to something higher (like half your total CPU cores).
2.  **Circuit Breaker:** Open `services/ai_brain/circuit_breaker.py`.
    *   Increase `MAX_PROMPT_CHARS` (e.g., from 1500 to 5000).
    *   Decrease `COOLDOWN_SECONDS` (e.g., from 5.0 to 0.5).

### How to Add a "Live Skill" (Command Execution)
If you want Kilo to *do* something (like lock your screen or play a sound):
1.  Open `services/ai_brain/main.py`.
2.  Create a new `@app.post("/skill/action")` endpoint.
3.  Use Python's `subprocess` module to run your local system commands.
4.  **Caution:** Be careful with this! Local agents have the same permissions as your user.
