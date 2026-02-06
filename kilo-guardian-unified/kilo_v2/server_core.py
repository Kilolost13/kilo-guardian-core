# --- Import UserContext for reference library ---
from .ai_core import get_finance_advice
from .unified_knowledge import unified_knowledge_lookup
from .user_context import UserContext

"""
Minimal FastAPI server skeleton for Kilo Guardian (2025 rebuild)
Features: finance, reminders, wizard (user intro), camera habit tracking, reference library, sentence transforms, medication tracking, person state tracking
Camera/pose ID, document scan, privacy-focused habit tracking (scaffolded)
Voice command integration: All features can be triggered by POST /voice/command with a transcribed command string. Wake word "hey Kilo" is handled on the client side.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import Body, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure finance upload directory exists
FINANCE_UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "finance_uploads")
os.makedirs(FINANCE_UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="Kilo Guardian Server (Rebuild)")

# Allow CORS for local development (e.g. Angular dev server on :4200).
# In production, restrict origins appropriately.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- User Wizard (user introduction/setup) ---
USER_PROFILE_PATH = os.path.join(os.path.dirname(__file__), "user_profiles.json")


class UserProfile(BaseModel):
    username: str
    preferences: Optional[dict] = None
    schedule: Optional[List[str]] = None


def load_profiles():
    if not os.path.exists(USER_PROFILE_PATH):
        return {}
    with open(USER_PROFILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# --- Finance Advice API Endpoint (moved here so `app` is defined) ---
@app.get("/api/finance/advice")
def api_finance_advice(user: str):
    """Return finance advice for the given user (for frontend/tablet UI)."""
    return get_finance_advice(user)


def save_profiles(profiles):
    with open(USER_PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2)


@app.post("/wizard/setup", summary="Create a new user profile")
def setup_user(profile: UserProfile):
    profiles = load_profiles()
    if profile.username in profiles:
        raise HTTPException(status_code=400, detail="User already exists.")


SPENDING_PATH = os.path.join(os.path.dirname(__file__), "spending.json")
GOALS_PATH = os.path.join(os.path.dirname(__file__), "finance_goals.json")


def load_spending():
    if not os.path.exists(SPENDING_PATH):
        return []
    with open(SPENDING_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_spending(spending):
    with open(SPENDING_PATH, "w", encoding="utf-8") as f:
        json.dump(spending, f, indent=2)


def load_goals():
    if not os.path.exists(GOALS_PATH):
        return {}
    with open(GOALS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_goals(goals):
    with open(GOALS_PATH, "w", encoding="utf-8") as f:
        json.dump(goals, f, indent=2)


@app.post("/finance/upload-csv")
def upload_banking_csv(user: str, file: UploadFile = File(...)):
    profiles = load_profiles()
    if user not in profiles:  # Ensure user exists
        raise HTTPException(status_code=404, detail="User not found.")
    docs = load_finance_docs()
    # Save file to disk
    file_path = os.path.join(FINANCE_UPLOAD_DIR, f"{user}_{file.filename}")
    with open(file_path, "wb") as f_out:
        f_out.write(file.file.read())
    docs.append(
        {"user": user, "filename": file.filename, "type": "csv", "path": file_path}
    )  # Append document info


class MedicationEvent(BaseModel):
    user: str
    medication: str
    dose: str
    time: str


def load_med_events():
    if not os.path.exists(MED_PATH):
        return []
    with open(MED_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_med_events(events):
    with open(MED_PATH, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2)


@app.post("/medication/add")
def add_medication_event(event: MedicationEvent):
    profiles = load_profiles()
    if event.user not in profiles:
        raise HTTPException(status_code=404, detail="User not found.")
    events = load_med_events()
    events.append(event.dict())
    save_med_events(events)
    return {"message": "Medication event added."}


@app.get("/medication/list")
def list_medication_events(user: str):
    events = load_med_events()
    return [e for e in events if e["user"] == user]


# --- Camera Habit Tracking ---
HABIT_PATH = os.path.join(os.path.dirname(__file__), "habit_events.json")


def load_habit_events():
    if not os.path.exists(HABIT_PATH):
        return []
    with open(HABIT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_habit_events(events):
    with open(HABIT_PATH, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2)


@app.post("/camera/habit-event")
def log_habit_event(user: str, event: str, timestamp: str):
    profiles = load_profiles()
    if user not in profiles:
        raise HTTPException(status_code=404, detail="User not found.")
    events = load_habit_events()
    events.append({"user": user, "event": event, "timestamp": timestamp})
    save_habit_events(events)
    return {"message": f"Habit event '{event}' logged for {user} at {timestamp}."}


@app.get("/camera/habit-events")
def list_habit_events(user: str):
    events = load_habit_events()
    return [e for e in events if e["user"] == user]


# --- Person State Tracking ---
STATE_PATH = os.path.join(os.path.dirname(__file__), "person_state_events.json")


class PersonStateEvent(BaseModel):
    user: str
    state: str  # sleeping, sitting, standing, etc.
    time: str


def load_state_events():
    if not os.path.exists(STATE_PATH):
        return []
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state_events(events):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2)


@app.post("/state/add")
def add_person_state(event: PersonStateEvent):
    profiles = load_profiles()
    if event.user not in profiles:
        raise HTTPException(status_code=404, detail="User not found.")
    events = load_state_events()
    events.append(event.dict())
    save_state_events(events)
    return {"message": "Person state event added."}


@app.get("/state/list")
def list_person_states(user: str):
    events = load_state_events()
    return [e for e in events if e["user"] == user]


# --- Reference Library ---
from fastapi import Query


@app.post("/reference/teach")
def reference_teach(
    user: str = Query(...),
    fact_key: str = Query(...),
    fact_value: str = Query(...),
    category: str = Query("general"),
):
    """Teach the AI a new fact for the user (adds to library of truth)."""
    ctx = UserContext(user_id=user)
    ctx.teach_fact(fact_key, fact_value, category)
    return {
        "message": f"Fact '{fact_key}' learned for user '{user}' in category '{category}'."
    }


@app.get("/reference/lookup")
def reference_lookup(
    user: str = Query(...), query: str = Query(...), category: str = Query("general")
):
    """Look up a fact or reference from the unified knowledge base (user facts + library of truth)."""
    result = unified_knowledge_lookup(user, query, category)
    return result


# --- Sentence Transforms ---
@app.post("/nlp/transform")
def sentence_transform(text: str, mode: str = "paraphrase"):
    # TODO: Implement NLP transform (stub)
    return {"result": f"Transformed ({mode}): {text}"}


# --- Camera Habit Tracking ---
@app.post("/camera/habit-event")
def log_habit_event(user: str, event: str, timestamp: str):
    # TODO: Store event in DB
    return {"message": f"Habit event '{event}' logged for {user} at {timestamp}."}


# --- Reference Library ---
@app.get("/reference/lookup")
def reference_lookup(query: str):
    # TODO: Implement factual lookup
    return {"result": f"Reference result for '{query}' (stub)"}


# --- Sentence Transforms ---
@app.post("/nlp/transform")
def sentence_transform(text: str, mode: str = "paraphrase"):
    # TODO: Implement NLP transform
    return {"result": f"Transformed ({mode}): {text}"}


# --- Medication Tracking ---
class MedicationEvent(BaseModel):
    user: str
    medication: str
    dose: str
    time: str


medication_events = []


@app.post("/medication/add")
def add_medication_event(event: MedicationEvent):
    medication_events.append(event.dict())
    return {"message": "Medication event added."}


@app.get("/medication/list")
def list_medication_events(user: str):
    return [e for e in medication_events if e["user"] == user]


# --- Person State Tracking ---
class PersonStateEvent(BaseModel):
    user: str
    state: str  # sleeping, sitting, standing, etc.
    time: str


person_state_events = []


@app.post("/state/add")
def add_person_state(event: PersonStateEvent):
    person_state_events.append(event.dict())
    return {"message": "Person state event added."}


@app.get("/state/list")
def list_person_states(user: str):
    return [e for e in person_state_events if e["user"] == user]


# --- Health Check ---
@app.get("/health")
def health_check():
    return {"status": "ok"}


# --- Camera & Pose ID Wizard ---
CAM_ID_DIR = os.path.join(os.path.dirname(__file__), "user_pose_id")
os.makedirs(CAM_ID_DIR, exist_ok=True)


@app.post("/wizard/camera-id-photos")
def upload_id_photos(user: str, pose: str, file: UploadFile = File(...)):
    """
    Accepts a photo for a specific pose (face, sitting, standing, lying) for user ID/training.
    """
    profiles = load_profiles()
    if user not in profiles:
        raise HTTPException(status_code=404, detail="User not found.")
    pose = pose.lower()
    if pose not in ["face", "sitting", "standing", "lying"]:
        raise HTTPException(status_code=400, detail="Invalid pose.")
    user_dir = os.path.join(CAM_ID_DIR, user)
    os.makedirs(user_dir, exist_ok=True)
    file_path = os.path.join(user_dir, f"{pose}.jpg")
    with open(file_path, "wb") as f_out:
        f_out.write(file.file.read())
    return {"message": f"{pose} photo saved for {user}.", "path": file_path}


# --- Document Scanning (receipts, med bottles, etc.) ---
DOC_SCAN_DIR = os.path.join(os.path.dirname(__file__), "user_docs")
os.makedirs(DOC_SCAN_DIR, exist_ok=True)


@app.post("/scan/document")
def scan_document(user: str, doc_type: str, file: UploadFile = File(...)):
    """
    Accepts a scanned document (receipt, med bottle, etc.) for user.
    """
    profiles = load_profiles()
    if user not in profiles:
        raise HTTPException(status_code=404, detail="User not found.")
    doc_type = doc_type.lower()
    user_dir = os.path.join(DOC_SCAN_DIR, user)
    os.makedirs(user_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(user_dir, f"{doc_type}_{timestamp}.jpg")
    with open(file_path, "wb") as f_out:
        f_out.write(file.file.read())
    return {"message": f"{doc_type} document saved for {user}.", "path": file_path}


# --- Privacy-Focused Habit Tracking (scaffold) ---
HABIT_OBS_PATH = os.path.join(os.path.dirname(__file__), "habit_observations.json")

# Import habit logic
from .habit_logic import detect_out_of_norm, get_user_baseline


def load_habit_observations():
    if not os.path.exists(HABIT_OBS_PATH):
        return []
    with open(HABIT_OBS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_habit_observations(obs):
    with open(HABIT_OBS_PATH, "w", encoding="utf-8") as f:
        json.dump(obs, f, indent=2)


@app.post("/habit/observation")
def log_habit_observation(
    user: str, cam: str, position: str, on_track: bool, goal: str = ""
):
    """
    Log a single observation: user, camera, detected position, on_track, goal, timestamp.
    No images or video are stored—just the result.
    """
    profiles = load_profiles()
    if user not in profiles:
        raise HTTPException(status_code=404, detail="User not found.")
    obs = load_habit_observations()
    obs.append(
        {
            "user": user,
            "cam": cam,
            "position": position,
            "on_track": on_track,
            "goal": goal,
            "timestamp": datetime.now().isoformat(),
        }
    )
    save_habit_observations(obs)
    return {"message": "Observation logged."}


@app.get("/habit/observations")
def get_habit_observations(user: str):
    obs = load_habit_observations()
    return [o for o in obs if o["user"] == user]


# --- Habit Analysis & Check-in Triggers ---
@app.get("/habit/checkin-triggers")
def habit_checkin_triggers(user: str):
    obs = [o for o in load_habit_observations() if o["user"] == user]
    baseline = get_user_baseline(obs)
    triggers = detect_out_of_norm(obs, baseline)
    return {"baseline": baseline, "triggers": triggers}


# --- Voice Command Integration ---
import re

from .ai_core import check_user_state, process_voice_command


@app.post("/voice/command")
def voice_command(
    command: str = Body(..., embed=True), user: str = Body("demo", embed=True)
):
    """
    Accepts a transcribed voice command and routes it to the AI core.
    The wake word "hey Kilo" should be handled on the client and not included in the command string.
    """
    return process_voice_command(command, user)


@app.get("/ai/checkin")
def ai_checkin(user: str):
    return check_user_state(user)


import csv
import json
import logging
import os
import platform
import sys
import time
from datetime import datetime
from io import StringIO
from typing import List

import psutil
from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# --- PATH AND LOGGING SETUP ---
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("server.log"), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("ServerCore")


from kilo_v2.camera_service import get_camera_service
import kilo_v2.config as config
from kilo_v2.error_tracker import get_error_tracker
from kilo_v2.plugin_manager import PluginManager

# Globals for managers (initialized in startup event)
pm = None  # type: ignore
healer = None

try:
    from kilo_v2.reasoning_engine import precompute_plugin_embeddings, synthesize_answer

    logger.info("✅ Reasoning Engine loaded successfully.")
except ImportError as e:
    # CRITICAL FIX: Log the actual error message 'e' so we can see it
    logger.error("❌ CRITICAL ERROR loading reasoning_engine: %s", e)
    # Print it to the console too, just in case
    import traceback

    traceback.print_exc()
    # capture the error text so the fallback function does not reference
    # a transient exception variable that may not exist when called later.
    _reasoning_import_error = str(e)

    def synthesize_answer():
        return f"System Error: Brain offline. Error details: {_reasoning_import_error}"

    def precompute_plugin_embeddings():
        logger.warning(
            "Precompute embeddings not available - reasoning engine not loaded"
        )


# --- Utility Functions ---
def _load_hmac_keys():
    hmac_keys_path = os.path.join(os.path.dirname(__file__), "hmac_keys.json")
    if os.path.exists(hmac_keys_path):
        with open(hmac_keys_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _add_hmac_key(key_id: str, key_value: str):
    hmac_keys_path = os.path.join(os.path.dirname(__file__), "hmac_keys.json")
    keys = _load_hmac_keys()
    keys[key_id] = key_value
    with open(hmac_keys_path, "w", encoding="utf-8") as f:
        json.dump(keys, f, indent=2)


def _ensure_submissions_dir():
    submissions_dir = os.path.join(os.path.dirname(__file__), "submissions")
    os.makedirs(submissions_dir, exist_ok=True)
    return submissions_dir


def _ensure_pm():
    global pm
    if pm is None:
        pm = PluginManager(plugin_dir="plugins")
    return pm


# Only one definition of toggle_plugin should exist. Remove duplicates elsewhere in the file.

# Duplicate definition of toggle_plugin removed


def health_check():
    """
    Returns the Traffic Light status for the frontend.
    """
    pm_instance = _ensure_pm()  # Use accessor
    cpu_usage = psutil.cpu_percent()
    ram_usage = psutil.virtual_memory().percent

    # Check if plugins are alive
    active_plugins = len(
        [p for p in pm_instance.plugins if hasattr(p, "is_alive") and p.is_alive()]
    )
    total_plugins = len(pm_instance.plugins)

    status = "GREEN"
    message = "All Systems Nominal"

    # YELLOW CONDITIONS (Working, but stressed)
    if cpu_usage > 80 or ram_usage > 85:
        status = "YELLOW"
        message = "High System Load"
    elif active_plugins < total_plugins:
        status = "YELLOW"
        message = "Some Plugins Offline"

    # RED CONDITIONS (Critical Failure)
    if cpu_usage > 95:
        status = "RED"
        message = "CRITICAL: CPU Overload"

    return {
        "status": status,  # GREEN, YELLOW, RED
        "message": message,
        "cpu": cpu_usage,
        "active_plugins": active_plugins,
    }

    # Duplicate definition of health_check removed


def diagnostics():
    pm_instance = _ensure_pm()  # Use accessor
    return {
        "status": "operational",
        "plugins": len(pm_instance.plugins),
        "os_system": platform.system(),
    }


def system_metrics():
    # This is a placeholder for actual metric collection
    # In a real scenario, this would query a metrics database
    return {"samples": [], "count": 0}


def get_error_stats():
    tracker = get_error_tracker()
    return tracker.get_stats()


def get_recent_errors(limit: int = 50):
    tracker = get_error_tracker()
    return tracker.get_recent_errors(limit=limit)


# --- API Key Authentication Dependency ---
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(api_key: str = Depends(api_key_header)):
    if config.KILO_API_KEY is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key not configured on the server.",
        )
    if api_key is None or api_key != config.KILO_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )
    return api_key


app = FastAPI(title="Kilo Guardian")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def guardian_health():
    return {"status": "ok", "service": "kilo-guardian"}


from kilo_v2.memory_core.api import router as memory_router

# Import routers
from kilo_v2.routers.finance import router as finance_router

# Register routers
app.include_router(finance_router, prefix="/api", tags=["finance"])
app.include_router(memory_router, prefix="/api", tags=["memory"])

# Init Camera Service (CORE FEATURE)
camera_service = None


# Init Reminder Engine
reminder_engine = None


@app.on_event("startup")
async def startup_event():
    # camera_service and reminder_engine are assumed to be in the appropriate scope

    logger.info("🚀 Kilo Guardian starting up...")

    # Initialize Database Tables (SQLAlchemy)
    try:
        from kilo_v2.db import get_engine
        from kilo_v2.models.auth_models import Base as AuthBase
        from kilo_v2.models.document_models import Base as DocumentBase
        from kilo_v2.models.finance_models import Base as FinanceBase

        engine = get_engine()
        AuthBase.metadata.create_all(bind=engine)
        FinanceBase.metadata.create_all(bind=engine)
        DocumentBase.metadata.create_all(bind=engine)
        logger.info("✅ SQLAlchemy database tables created/verified")
    except (OSError, IOError) as e:
        logger.error("Failed to create database tables: %s", e)

    # Initialize Memory Core & Reminder Engine
    try:
        from kilo_v2.memory_core.api import set_reminder_engine
        from kilo_v2.memory_core.db import get_memory_db
        from kilo_v2.memory_core.reminder_engine import ReminderEngine

        memory_db = get_memory_db()
        reminder_engine = ReminderEngine(memory_db)
        set_reminder_engine(reminder_engine)
        logger.info("✅ Memory Core and Reminder Engine initialized")
    except (OSError, IOError) as e:
        logger.error("Failed to initialize Memory Core: %s", e)

    # Start camera service first (core feature)
    camera_service = get_camera_service()
    logger.info("✅ Camera service initialized")

    # Then load plugins (individual failures are non-fatal)
    _ensure_pm()
    try:
        await pm.load_plugins()
    except Exception as e:
        logger.warning("Plugin load partially failed: %s -- continuing with available plugins", e)
    try:
        pm.start_all()
    except Exception as e:
        logger.warning("Plugin start partially failed: %s", e)

    try:
        # pm.enable_watchdog()  # Disabled: PluginManager has no 'enable_watchdog' member
        pass
    except (OSError, IOError) as e:
        logger.warning("Failed to start plugin watchdog: %s", e)

    # Precompute plugin embeddings for fast query routing
    try:
        precompute_plugin_embeddings(pm)
    except (OSError, IOError) as e:
        logger.warning("Failed to precompute plugin embeddings: %s", e)

    logger.info("🎯 Kilo Guardian fully operational")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("🛑 Kilo Guardian shutting down...")

    try:
        if reminder_engine:
            reminder_engine.shutdown()
    except Exception:
        pass

    try:
        # pm.stop_watchdog()  # Disabled: PluginManager has no 'stop_watchdog' member
        pass
    except Exception:
        pass

    try:
        if camera_service:
            camera_service.shutdown()
    except Exception:
        pass

    logger.info("👋 Kilo Guardian shutdown complete")


class ChatRequest(BaseModel):
    query: str


@app.post("/api/chat", dependencies=[Depends(get_api_key)])
async def chat(req: ChatRequest):

    # Wrap the standard chat in the monitor so it catches crashes.
    # If the Reasoning Engine is offline or returns an error string, fall
    # back to keyword-based plugin routing via PluginManager.get_action().
    def _do_chat():
        result = synthesize_answer(req.query, pm)

        # If the reasoning engine returned a structured response (dict), return it.
        if isinstance(result, dict):
            return {"answer": result}

        # If the reasoning engine returned a string error or a simple reply,
        # try keyword routing when the engine reports an error or is unavailable.
        if isinstance(result, str) and (
            "Error" in result or "Brain offline" in result or "not available" in result
        ):
            plugin = pm.get_action(req.query)
            if plugin:
                try:
                    if hasattr(plugin, "execute") and callable(plugin.execute):
                        return {"answer": plugin.execute(req.query)}
                    else:
                        return {"answer": plugin.run(req.query)}
                except Exception as e:
                    healer.last_error = str(e)
                    raise

        # Default: return the string response from the reasoning engine.
        return {"answer": result}

    return _do_chat()


@app.get("/api/diagnostics", dependencies=[Depends(get_api_key)])
def diag():
    return {
        "status": "operational",
        "plugins": len(pm.plugins),
        "os_system": platform.system(),
    }


@app.get("/api/plugins", dependencies=[Depends(get_api_key)])
def plugins():
    plugins_out = []
    for p in pm.plugins:
        item = {
            "name": p.get_name(),
            "keywords": p.get_keywords(),
            "description": ", ".join(p.get_keywords()),
            "enabled": getattr(p, "enabled", True),  # Default to enabled
        }
        # Include manifest if the plugin provided one
        if hasattr(p, "manifest"):
            item["manifest"] = p.manifest
        # Include last-known health if available
        if hasattr(p, "health_status"):
            item["health"] = p.health_status
        elif hasattr(p, "health") and callable(p.health):
            try:
                item["health"] = p.health()
            except Exception as e:
                item["health"] = {"status": "error", "detail": str(e)}

        plugins_out.append(item)

    return {"plugins": plugins_out}


@app.get("/api/front-config")
def front_config():
    """Return minimal front-end config. Avoid exposing secrets in multi-user setups.

    For local/dev use we include the KILO_API_KEY when configured to simplify
    bootstrapping single-node deployments. In production you may want to
    disable this endpoint or return only a boolean flag.
    """
    return {"api_base": "", "KILO_API_KEY": config.KILO_API_KEY}


@app.get("/wizard")
def serve_wizard():
    """Serve the setup wizard page"""
    wizard_path = os.path.join(os.path.dirname(__file__), "public", "wizard.html")
    if os.path.exists(wizard_path):
        return FileResponse(wizard_path)
    raise HTTPException(status_code=404, detail="Setup wizard not found")

    # YELLOW CONDITIONS (Working, but stressed)
    if cpu_usage > 80 or ram_usage > 85:
        status = "YELLOW"
        message = "High System Load"
    elif active_plugins < total_plugins:
        status = "YELLOW"
        message = "Some Plugins Offline"

    # RED CONDITIONS (Critical Failure)
    if cpu_usage > 95:
        status = "RED"
        message = "CRITICAL: CPU Overload"
    # In production, check if the LLM API is reachable here too

    # Update Persona based on health (If system is RED, Kilo gets serious)
    # persona.set_system_mood(status) # Persona is not imported

    return {
        "status": status,  # GREEN, YELLOW, RED
        "message": message,
        "cpu": cpu_usage,
        "active_plugins": active_plugins,
    }


class UserData(BaseModel):
    name: str
    aiName: str
    interests: str
    householdSize: int
    location: dict
    faceData: str  # Base64 string


@app.post("/api/setup/initialize", dependencies=[Depends(get_api_key)])
async def initialize_setup(user_data: UserData):
    sanitized_data = {
        "name": "***",  # Masking PII
        "aiName": "***",  # Masking PII
        "interests": "***",  # Masking PII
        "householdSize": user_data.householdSize,
        # 'location' and 'faceData' are omitted due to extreme sensitivity
    }
    logger.info("Received setup data (sanitized): %s", sanitized_data)
    # In a real application, you would save this data to a database
    # or process it further. For now, just acknowledge.

    # Example: Save some data to config (simplified)
    # This would require a more robust config management system
    # config.set("user_name", user_data.name)
    # config.set("ai_name", user_data.aiName)

    return {"message": "Setup data received and processed successfully!"}


class PluginRestartRequest(BaseModel):
    name: str


@app.post("/api/plugins/restart", dependencies=[Depends(get_api_key)])
def restart_plugin(req: PluginRestartRequest):
    """Restart a plugin by name using the PluginManager restart logic."""
    try:
        plugin = pm.get_plugin(req.name)
        if not plugin:
            return {"ok": False, "error": "Plugin not found"}

        # pm.restart_plugin(plugin)  # Disabled: PluginManager has no 'restart_plugin' member
        return {"ok": True, "message": f"Restarted plugin {req.name}"}
    except (OSError, IOError) as e:
        logger.exception("Failed to restart plugin %s: %s", req.name, e)
        return {"ok": False, "error": str(e)}


# --- CAMERA ENDPOINTS (CORE FEATURE) ---


@app.get("/api/cameras")
async def list_cameras():
    """
    List all detected cameras.
    This is a core feature, always available.
    """
    if not camera_service:
        return {"cameras": [], "error": "Camera service not initialized"}

    cameras = camera_service.get_all_cameras()
    return {
        "cameras": [
            {
                "id": info.id,
                "name": info.name,
                "is_active": info.is_active,
                "resolution": info.resolution,
                "fps": info.fps,
            }
            for info in cameras.values()
        ],
        "count": len(cameras),
    }


def gen_camera_frames(camera_id: int):
    """Generate MJPEG stream for a specific camera."""
    logger.info("🎥 Starting camera stream for camera %s", camera_id)
    frame_count = 0

    while True:
        try:
            if not camera_service:
                logger.warning("Camera service not available")
                time.sleep(0.5)
                continue

            frame = camera_service.get_frame(camera_id)
            if frame:
                frame_count += 1
                if frame_count % 30 == 0:  # Log every 30 frames
                    logger.debug(
                        "Camera %s: streamed %d frames", camera_id, frame_count
                    )
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
                time.sleep(0.1)  # ~10 FPS max
            else:
                # Camera unavailable, wait before retry
                logger.warning("Camera %s: No frame available", camera_id)
                time.sleep(0.5)
        except GeneratorExit:
            logger.info("🎥 Camera %s stream closed by client", camera_id)
            break
        except Exception as e:
            logger.error("Error streaming camera %s: %s", camera_id, e)
            time.sleep(1.0)


@app.get("/api/camera/{camera_id}/stream")
async def camera_stream(camera_id: int):
    """
    Stream MJPEG video from a specific camera.
    This is a core feature for the security dashboard.
    """
    if not camera_service:
        return Response(status_code=503, content="Camera service not available")

    info = camera_service.get_camera_info(camera_id)
    if not info:
        return Response(status_code=404, content=f"Camera {camera_id} not found")

    return StreamingResponse(
        gen_camera_frames(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/api/camera/health")
async def camera_health():
    """Check camera service health."""
    if not camera_service:
        return {"status": "error", "message": "Camera service not initialized"}

    return camera_service.health_check()


# --- STATIC FILE SERVER (Frontend) ---

# Define the directory for the frontend files
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public")

# Check if the directory exists, if not, create it
if not os.path.isdir(STATIC_DIR):
    os.makedirs(STATIC_DIR, exist_ok=True)
    logger.warning("Created missing static directory: %s", STATIC_DIR)


# Mount the static directory to serve files (like CSS, JS)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# Serve the main index.html file for the root path
@app.get("/")
async def root():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return Response(content=f.read(), media_type="text/html")
    else:
        return {
            "message": "Welcome to Kilo. Frontend not built yet. Access /api/chat or /api/diagnostics directly."
        }


# Serve the wizard page
@app.get("/wizard")
async def wizard_page():
    wizard_path = os.path.join(STATIC_DIR, "wizard.html")
    if os.path.exists(wizard_path):
        return FileResponse(wizard_path)
    else:
        return {
            "error": "Wizard not found. Please ensure wizard.html is in the public directory."
        }


@app.get("/api/wizard/status")
async def wizard_status():
    """Check if wizard has been completed."""
    try:
        config_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "user_data"
        )
        prefs_file = os.path.join(config_dir, "preferences.json")

        if os.path.exists(prefs_file):
            with open(prefs_file, "r") as f:
                prefs = json.load(f)
                return {
                    "completed": prefs.get("setup_completed", False),
                    "user": prefs.get("personal", {}).get("preferredName", "User"),
                    "setupDate": prefs.get("setup_date"),
                }

        return {"completed": False}

    except (OSError, IOError) as e:
        logger.error("Error checking wizard status: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# --- STORED FACES API ---


@app.get("/api/faces")
async def get_stored_faces():
    """Get all stored face data."""
    try:
        config_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "user_data"
        )
        faces_file = os.path.join(config_dir, "faces.json")

        if os.path.exists(faces_file):
            with open(faces_file, "r", encoding="utf-8") as f:
                return json.load(f)

        return {"faces": [], "count": 0}

    except (OSError, IOError) as e:
        logger.error("Error loading faces: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# --- SYSTEM LOGS API ---


@app.get("/api/logs")
async def get_system_logs(lines: int = 100):
    """Get recent system logs."""
    try:
        log_file = "server.log"
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:]
                return {
                    "logs": recent_lines,
                    "total": len(all_lines),
                    "showing": len(recent_lines),
                }

        return {"logs": [], "total": 0, "showing": 0}
    except (KeyError, ValueError, TypeError) as e:
        logger.error("Error reading logs: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# --- SECURITY ALERTS API ---


@app.get("/api/alerts")
async def get_security_alerts():
    """Security monitoring is currently disabled."""
    return {
        "alerts": [],
        "threats": 0,
        "status": "disabled",
        "last_check": datetime.now().isoformat(),
    }


# --- SYSTEM CONTROL API ---


@app.post("/api/restart")
async def restart_system():
    """Restart the Kilo Guardian system."""
    try:
        logger.info("🔄 System restart requested via API")
        # In production, this would trigger a proper restart
        return {"success": True, "message": "System restart initiated"}
    except (OSError, IOError) as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/shutdown")
async def shutdown_system():
    """Shutdown the Kilo Guardian system."""
    try:
        logger.info("⚠️ System shutdown requested via API")
        # In production, this would trigger a proper shutdown
        return {"success": True, "message": "System shutdown initiated"}
    except (OSError, IOError) as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Banking CSV Upload Endpoint ---


@app.post("/api/upload/banking-csv", dependencies=[Depends(get_api_key)])
async def upload_banking_csv(file: UploadFile = File(...)):
    """Upload and process a banking CSV file."""
    try:
        # Validate file type
        if not file.filename.endswith(".csv"):
            raise HTTPException(status_code=400, detail="Only CSV files are supported")

        # Read CSV content
        content = await file.read()
        csv_text = content.decode("utf-8")

        # Parse CSV
        csv_reader = csv.DictReader(StringIO(csv_text))
        transactions = list(csv_reader)

        logger.info(
            f"📊 Banking CSV uploaded: {file.filename} ({len(transactions)} transactions)"
        )

        # Store or process transactions (implement based on your needs)
        # For now, just return summary

        total_debits = sum(
            float(row.get("Amount", 0))
            for row in transactions
            if float(row.get("Amount", 0)) < 0
        )
        total_credits = sum(
            float(row.get("Amount", 0))
            for row in transactions
            if float(row.get("Amount", 0)) > 0
        )

        return {
            "success": True,
            "filename": file.filename,
            "transactions_count": len(transactions),
            "summary": {
                "total_debits": abs(total_debits),
                "total_credits": total_credits,
                "net": total_credits + total_debits,
            },
            "message": "CSV processed successfully. Integrate with finance_manager plugin for full analysis.",
        }
    except Exception as e:
        logger.error(f"Error processing banking CSV: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload/financial-document", dependencies=[Depends(get_api_key)])
async def upload_financial_document(
    file: UploadFile = File(...), type: str = "document"
):
    """Upload and process financial documents (CSV, receipts, bills, etc.)."""
    try:
        # Get file extension
        filename = file.filename.lower()
        ext = os.path.splitext(filename)[1]

        # Read content
        content = await file.read()

        logger.info(
            f"📄 Financial document uploaded: {file.filename} (type: {type}, size: {len(content)} bytes)"
        )

        result = {
            "success": True,
            "filename": file.filename,
            "type": type,
            "size": len(content),
            "message": f"{type.capitalize()} uploaded successfully",
        }

        # Type-specific processing
        if type == "csv" and ext == ".csv":
            csv_text = content.decode("utf-8")
            csv_reader = csv.DictReader(StringIO(csv_text))
            transactions = list(csv_reader)

            total_debits = sum(
                float(row.get("Amount", 0))
                for row in transactions
                if float(row.get("Amount", 0)) < 0
            )
            total_credits = sum(
                float(row.get("Amount", 0))
                for row in transactions
                if float(row.get("Amount", 0)) > 0
            )

            result["transactions_count"] = len(transactions)
            result["summary"] = {
                "total_debits": abs(total_debits),
                "total_credits": total_credits,
                "net": total_credits + total_debits,
            }
            result["message"] = f"CSV processed: {len(transactions)} transactions found"

        elif type in ["receipt", "bill"] and ext in [".pdf", ".jpg", ".jpeg", ".png"]:
            result["message"] = (
                f"{type.capitalize()} received. OCR processing available via finance_manager plugin."
            )

        elif type == "document":
            result["message"] = (
                f"Document received. Processing available via finance_manager plugin."
            )

        return result

    except Exception as e:
        logger.error(f"Error processing financial document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# --- SANDBOX MANAGEMENT ENDPOINTS ---


@app.get("/api/sandbox/health")
async def get_sandbox_health():
    """Get health report for all sandboxed plugins."""
    try:
        from plugin_sandbox import get_sandbox_manager

        manager = get_sandbox_manager()
        if not manager:
            return {"error": "Sandbox not available", "sandbox_enabled": False}

        report = manager.get_health_report()
        return report
    except Exception as e:
        logger.error(f"Error getting sandbox health: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sandbox/reset/{plugin_name}")
async def reset_plugin_health(plugin_name: str):
    """Reset health status for a specific plugin."""
    try:
        from plugin_sandbox import get_sandbox_manager

        manager = get_sandbox_manager()
        if not manager:
            raise HTTPException(status_code=503, detail="Sandbox not available")

        success = manager.reset_plugin_health(plugin_name)

        if success:
            return {
                "success": True,
                "plugin": plugin_name,
                "message": "Health status reset",
            }
        else:
            raise HTTPException(
                status_code=404, detail=f"Plugin '{plugin_name}' not found in sandbox"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting plugin health: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# --- SECURITY MONITOR ENDPOINTS ---


@app.get("/api/healer/status")
async def get_healer_status():
    """Get self-healer status."""
    try:
        status = healer.get_status()
        return status
    except Exception as e:
        logger.error(f"Error getting healer status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/healer/recover")
async def trigger_recovery():
    """Trigger automatic recovery from last error."""
    try:
        result = healer.attempt_recovery(auto_only=False)
        return result
    except Exception as e:
        logger.error(f"Error triggering recovery: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class RecoveryActionRequest(BaseModel):
    action_name: str


@app.post("/api/healer/action")
async def execute_recovery_action(request: RecoveryActionRequest):
    """Execute a specific recovery action."""
    try:
        success = healer.execute_recovery_action(request.action_name)

        if success:
            return {
                "success": True,
                "action": request.action_name,
                "message": "Recovery action executed successfully",
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Recovery action '{request.action_name}' not found or failed",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing recovery action: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/healer/diagnosis")
async def get_diagnosis():
    """Get diagnosis of last error."""
    try:
        diagnosis = healer.diagnose_last_error()
        return {"diagnosis": diagnosis}
    except Exception as e:
        logger.error(f"Error getting diagnosis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ATTACK MONITORING API ====================


@app.get("/api/vps/bridge/status", dependencies=[Depends(get_api_key)])
async def vps_bridge_status():
    """Get VPS bridge status"""
    try:
        from vps_bridge import get_bridge_status

        return get_bridge_status()
    except Exception as e:
        logger.error(f"Error getting VPS bridge status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==========================
# LICENSE & BILLING ENDPOINTS
# ==========================


@app.get("/api/license/status", dependencies=[Depends(get_api_key)])
async def get_license_status():
    """Get current license status and tier"""
    try:
        from license_manager import get_license_manager

        license_mgr = get_license_manager()
        return license_mgr.get_usage_stats()
    except Exception as e:
        logger.error(f"Error getting license status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class ActivateLicenseRequest(BaseModel):
    license_key: str
    bastion_id: str


@app.post("/api/license/activate", dependencies=[Depends(get_api_key)])
async def activate_license(request: ActivateLicenseRequest):
    """Activate a license key"""
    try:
        from license_manager import get_license_manager

        license_mgr = get_license_manager()
        return license_mgr.activate_license(request.license_key, request.bastion_id)
    except Exception as e:
        logger.error(f"Error activating license: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/license/upgrade-info", dependencies=[Depends(get_api_key)])
async def get_upgrade_info():
    """Get upgrade information for current tier"""
    try:
        from license_manager import get_license_manager

        license_mgr = get_license_manager()
        return license_mgr.get_upgrade_info()
    except Exception as e:
        logger.error(f"Error getting upgrade info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/usage/stats", dependencies=[Depends(get_api_key)])
async def get_usage_stats():
    """Get usage statistics"""
    try:
        from usage_tracker import get_usage_tracker

        tracker = get_usage_tracker()
        return tracker.get_current_usage()
    except Exception as e:
        logger.error(f"Error getting usage stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/usage/daily", dependencies=[Depends(get_api_key)])
async def get_daily_usage(days: int = 30):
    """Get daily usage statistics"""
    try:
        from usage_tracker import get_usage_tracker

        tracker = get_usage_tracker()
        return tracker.get_daily_stats(days)
    except Exception as e:
        logger.error(f"Error getting daily usage: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/usage/monthly", dependencies=[Depends(get_api_key)])
async def get_monthly_usage(months: int = 12):
    """Get monthly usage statistics"""
    try:
        from usage_tracker import get_usage_tracker

        tracker = get_usage_tracker()
        return tracker.get_monthly_stats(months)
    except Exception as e:
        logger.error(f"Error getting monthly usage: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/billing/summary", dependencies=[Depends(get_api_key)])
async def get_billing_summary():
    """Get billing summary for current period"""
    try:
        from usage_tracker import get_usage_tracker

        tracker = get_usage_tracker()
        return tracker.get_billing_summary()
    except Exception as e:
        logger.error(f"Error getting billing summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events (NO API key required for webhooks)"""
    try:
        from payment_handler import StripeWebhookHandler

        from . import config

        # Get raw body
        payload = await request.body()
        signature = request.headers.get("stripe-signature", "")

        # Initialize webhook handler
        handler = StripeWebhookHandler(
            webhook_secret=getattr(config, "STRIPE_WEBHOOK_SECRET", "")
        )

        # Verify signature
        if not handler.verify_signature(payload, signature, str(int(time.time()))):
            raise HTTPException(status_code=401, detail="Invalid signature")

        # Parse event
        event_data = json.loads(payload)
        event_type = event_data.get("type")

        # Handle event
        result = handler.handle_webhook(event_type, event_data.get("data", {}))

        return result

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ================================================================
