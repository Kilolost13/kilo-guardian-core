"""
ai_core.py: Central AI orchestrator for Kilo Guardian
Ties together sentence transforms, finance, habit, reminders, and voice logic.
Integrates: Phi-3, TinyLlama (NLP), Tesseract, OCR-Torch (OCR)
"""

from typing import Any, Dict

from . import habit_logic

# Import finance module for advice
# Import UserContext for library of truth
from .finance_api import get_finance_advice as _get_finance_advice
from .unified_knowledge import unified_knowledge_lookup
from .user_context import UserContext

# --- Library of Truth Integration ---


# Unified knowledge lookup (user facts + library of truth)
def get_user_fact(user: str, fact_key: str, category: str = "general") -> str:
    result = unified_knowledge_lookup(user, fact_key, category)
    if result.get("found"):
        if result["source"] == "user_fact":
            return result["result"]
        elif result["source"] == "library_of_truth":
            # Return the first matching reference chunk's text, if available
            if isinstance(result["result"], list) and result["result"]:
                return result["result"][0]["text"]
            return "No reference found."
    return f"No fact or reference found for '{fact_key}'."


# --- Finance Advice Integration ---
def get_finance_advice(user: str):
    """Call the finance module to get advice for a user."""
    return _get_finance_advice(user)


# from . import reminders_logic  # Placeholder for future reminders logic

# --- Ollama Integration ---
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"  # Default Ollama endpoint
OLLAMA_MODELS = {"phi3": "phi-3-mini-4k-instruct-q4", "tinyllama": "tinyllama-test"}

# --- Model/Tool Imports ---
# NLP: Hugging Face Transformers (pip install transformers torch)
try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

    # Load models once (adjust model names/paths as needed)
    phi3_tokenizer = AutoTokenizer.from_pretrained("microsoft/phi-3-mini-4k-instruct")
    phi3_model = AutoModelForCausalLM.from_pretrained(
        "microsoft/phi-3-mini-4k-instruct"
    )
    tinyllama_tokenizer = AutoTokenizer.from_pretrained(
        "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    )
    tinyllama_model = AutoModelForCausalLM.from_pretrained(
        "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    )
except Exception as e:
    phi3_tokenizer = phi3_model = tinyllama_tokenizer = tinyllama_model = None

# OCR: pytesseract (pip install pytesseract) and system tesseract-ocr
try:
    import pytesseract
except ImportError:
    pytesseract = None

# OCR-Torch: easyocr (pip install easyocr torch)
try:
    import easyocr

    ocr_reader = easyocr.Reader(["en"])
except Exception:
    ocr_reader = None

# --- NLP Model Stubs ---


def ollama_transform(text: str, model: str = "phi3", mode: str = "paraphrase") -> str:
    """
    Use Ollama HTTP API to run local GGUF models (Phi-3, TinyLlama).
    """
    model_name = OLLAMA_MODELS.get(model, "phi-3-mini-4k-instruct-q4")
    prompt = f"Paraphrase: {text}" if mode == "paraphrase" else f"Rephrase: {text}"
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": model_name, "prompt": prompt, "stream": False},
            timeout=30,
        )
        if response.status_code == 200:
            result = response.json().get("response", "")
            return result.strip()
        else:
            return f"(Ollama error: {response.status_code})"
    except Exception as e:
        return f"(Ollama call failed: {e})"


def phi3_transform(text: str, mode: str = "paraphrase") -> str:
    return ollama_transform(text, model="phi3", mode=mode)


def tinyllama_transform(text: str, mode: str = "paraphrase") -> str:
    return ollama_transform(text, model="tinyllama", mode=mode)


# from . import finance_logic  # Placeholder for future finance logic
# from . import reminders_logic  # Placeholder for future reminders logic


# --- Sentence Transforms (stub) ---
def transform_sentence(text: str, mode: str = "paraphrase", model: str = "phi3") -> str:
    """
    Use the specified model for sentence transform.
    """
    if model == "phi3":
        return phi3_transform(text, mode)
    if model == "tinyllama":
        return tinyllama_transform(text, mode)
    return f"(Unknown model) {text}"


# --- Voice Command Processing ---
def process_voice_command(command: str, user: str) -> Dict[str, Any]:
    """
    Parse the command, route to the right feature, and return a response dict.
    """
    cmd = command.strip().lower()
    # Unified Knowledge: Fact or reference lookup
    if (
        cmd.startswith("lookup fact")
        or cmd.startswith("what is")
        or cmd.startswith("who is")
    ):
        # Example: "lookup fact birthday" or "what is my birthday"
        tokens = cmd.split()
        # Try to extract fact_key from command
        if "fact" in tokens:
            idx = tokens.index("fact")
            if idx + 1 < len(tokens):
                fact_key = tokens[idx + 1]
            else:
                fact_key = ""
        elif "what is" in cmd:
            fact_key = cmd.replace("what is", "").replace("my", "").strip()
        elif "who is" in cmd:
            fact_key = cmd.replace("who is", "").replace("my", "").strip()
        else:
            fact_key = cmd
        value = get_user_fact(user, fact_key)
        return {"response": value}
    # Library of Truth: Teach fact
    if cmd.startswith("teach fact") or cmd.startswith("remember that"):
        # Example: "teach fact birthday 1990-01-01" or "remember that my birthday is 1990-01-01"
        tokens = cmd.split()
        if "fact" in tokens:
            idx = tokens.index("fact")
            if idx + 2 < len(tokens):
                fact_key = tokens[idx + 1]
                fact_value = " ".join(tokens[idx + 2 :])
                ctx = UserContext(user_id=user)
                ctx.teach_fact(fact_key, fact_value)
                return {"response": f"Fact '{fact_key}' learned as '{fact_value}'."}
        elif "remember that" in cmd:
            # Example: "remember that my birthday is 1990-01-01"
            after = cmd.replace("remember that", "").strip()
            if "is" in after:
                parts = after.split("is", 1)
                fact_key = parts[0].replace("my", "").strip()
                fact_value = parts[1].strip()
                ctx = UserContext(user_id=user)
                ctx.teach_fact(fact_key, fact_value)
                return {"response": f"Fact '{fact_key}' learned as '{fact_value}'."}
        return {"response": "Could not parse fact to teach."}
    # Example routing logic
    if "reminder" in cmd:
        return {"response": "(Stub) Reminder logic called."}
    if "finance" in cmd or "spending" in cmd:
        return {"response": "(Stub) Finance logic called."}
    if "habit" in cmd or "activity" in cmd:
        # Use habit_logic
        # In real use, pass user observations
        return {"response": "(Stub) Habit logic called."}
    if "paraphrase" in cmd or "rephrase" in cmd:
        # Example: choose model based on command
        model = (
            "phi3" if "phi3" in cmd else ("tinyllama" if "tinyllama" in cmd else "phi3")
        )
        return {"response": transform_sentence(cmd, model=model)}
    if "ocr" in cmd or "scan" in cmd:
        return {"response": "(Stub) OCR logic called."}
    return {"response": "Sorry, I didn't understand that command."}


# --- OCR Stubs ---
def tesseract_ocr(image_path: str) -> str:
    """
    Use pytesseract to extract text from image.
    """
    if not pytesseract:
        return "(pytesseract not available)"
    try:
        return pytesseract.image_to_string(image_path)
    except Exception as e:
        return f"(Tesseract OCR error: {e})"


def ocr_torch(image_path: str) -> str:
    """
    Use easyocr to extract text from image.
    """
    if not ocr_reader:
        return "(easyocr not available)"
    try:
        result = ocr_reader.readtext(image_path, detail=0)
        return "\n".join(result)
    except Exception as e:
        return f"(OCR-Torch error: {e})"


# --- Check User State (stub) ---
def check_user_state(user: str) -> Dict[str, Any]:
    # TODO: Run habit and finance logic, decide if check-in/reminder needed
    return {"checkin": False, "message": "(Stub) User state normal."}


# Expand this module as you add more logic and features.
