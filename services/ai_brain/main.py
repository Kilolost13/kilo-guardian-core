from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Form, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
import httpx
import re
import datetime
from collections import defaultdict
import base64
from io import BytesIO
import subprocess
from shutil import which
import json
import hashlib
# OpenAI removed - Kilo runs 100% locally with Ollama
try:
    from gtts import gTTS
except Exception:
    gTTS = None
try:
    from tenacity import retry, stop_after_attempt, wait_exponential
except Exception:
    # simple fallback retry decorator
    def retry(*args, **kwargs):
        def _decorator(f):
            return f
        return _decorator
    def stop_after_attempt(n):
        return None
    def wait_exponential(*args, **kwargs):
        return None
from starlette.concurrency import run_in_threadpool
import uuid
import logging
logger = logging.getLogger(__name__)
from fastapi.responses import FileResponse
import pathlib
import os
# include orchestration routes
import importlib.util
import pathlib

try:
    # Preferred when running as a package
    from .orchestrator import router as orchestration_router
except Exception as e:
    logger.debug("Failed to import .orchestrator: %s", e)
    # Fallback for running as a module or from Docker where package context may be missing
    try:
        from orchestrator import router as orchestration_router
    except Exception as e2:
        logger.debug("Failed to import local orchestrator module: %s", e2)
        # Try a couple of absolute import locations
        try:
            import importlib
            mod = importlib.import_module("ai_brain.orchestrator")
            orchestration_router = getattr(mod, "router", None)
        except Exception as e3:
            logger.debug("Failed to import ai_brain.orchestrator: %s", e3)
            try:
                mod = importlib.import_module("microservice.ai_brain.orchestrator")
                orchestration_router = getattr(mod, "router", None)
            except Exception:
                # Try loading the module directly from file path as a last resort
                try:
                    base = pathlib.Path(__file__).parent
                    candidate = base / "orchestrator.py"
                    if not candidate.exists():
                        candidate = base / "ai_brain" / "orchestrator.py"
                    spec = importlib.util.spec_from_file_location("ai_brain.orchestrator", str(candidate))
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    orchestration_router = getattr(mod, "router", None)
                    # register to sys.modules so subsequent imports (and patches) can find it
                    try:
                        import sys
                        sys.modules["ai_brain.orchestrator"] = mod
                        try:
                            import ai_brain as _ai_pkg
                            setattr(_ai_pkg, "orchestrator", mod)
                        except Exception:
                            pass
                    except Exception:
                        pass
                except Exception:
                    orchestration_router = None

# Support pluggable STT/TTS via environment variables (defaults to 'none' -> dummy)
STT_PROVIDER = os.environ.get("STT_PROVIDER", "none")
TTS_PROVIDER = os.environ.get("TTS_PROVIDER", "none")

# Compatibility: convert Pydantic models to dicts supporting v1 (.dict()) and v2 (.model_dump())
def _to_dict(m):
    """Return a serializable dict for a pydantic model or object."""
    try:
        # Pydantic v2
        return m.model_dump()
    except Exception:
        try:
            return m.dict()
        except Exception:
            try:
                return dict(m)
            except Exception:
                return getattr(m, "__dict__", {})


from contextlib import asynccontextmanager
try:
    from .db import get_session
except Exception:
    # Try absolute package import (when running tests or module executed differently)
    from ai_brain.db import get_session

try:
    from .utils.network import require_network_or_raise
except Exception:
    from ai_brain.utils.network import require_network_or_raise


def _get_memory_model():
    """Lazily import the shared Memory model at call time.

    Try a few import locations so the function works both when the ai_brain
    package is executed in isolation and when tests import the project with
    the repository root on sys.path (where the module is available as
    `shared.models`).
    """
    candidates = [
        "models",
        "shared.models",
        "ai_brain.models",
    ]
    for cand in candidates:
        try:
            module = __import__(cand, fromlist=["Memory"])
            Memory = getattr(module, "Memory", None)
            if Memory is not None:
                return Memory
        except Exception:
            continue
    return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    try:
        try:
            from .db import init_db
            init_db()
        except Exception:
            pass

        # Initialize Phase 3 & 4 components
        try:
            from .async_processing import async_pipeline
            from .data_partitioning import data_partitioner
            from .knowledge_graph import knowledge_graph

            # Start async processing pipeline
            async_pipeline.start()

            # Initialize data partitioner
            # (data_partitioner is already initialized as global instance)

            # Load existing knowledge graph if available
            kg_file = "/tmp/ai_brain_knowledge_graph.json"
            if os.path.exists(kg_file):
                knowledge_graph.load_graph(kg_file)

            logger.info("Phase 3 & 4 components initialized successfully")

        except Exception as e:
            logger.warning(f"Failed to initialize Phase 3 & 4 components: {e}")

        # Ensure orchestrator routes are mounted on startup (handles import-order quirks
        # when pytest or other runners import modules out-of-order).
        try:
            import importlib
            mod = importlib.import_module('ai_brain.orchestrator')
            orchestration_router = getattr(mod, 'router', None)
            if orchestration_router is not None:
                # include router on the app instance that will be passed into lifespan
                try:
                    app.include_router(orchestration_router)
                    logger.info("Mounted orchestrator router on startup")
                except Exception as e:
                    logger.warning(f"Failed to include orchestrator router on startup: {e}")
        except Exception as e:
            logger.debug(f"Orchestrator not importable on startup: {e}")

    except Exception:
        pass
    yield
    # shutdown
    try:
        # Save knowledge graph on shutdown
        from .knowledge_graph import knowledge_graph
        kg_file = "/tmp/ai_brain_knowledge_graph.json"
        knowledge_graph.save_graph(kg_file)

        # Stop async processing
        from .async_processing import async_pipeline
        async_pipeline.stop()

        logger.info("Phase 3 & 4 components shut down successfully")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Prometheus metrics: create only if not already present (safe for repeated imports)
if 'REQUEST_COUNT' not in globals():
    REQUEST_COUNT = Counter('ai_brain_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
else:
    # reuse existing
    REQUEST_COUNT = globals()['REQUEST_COUNT']

if 'REQUEST_LATENCY' not in globals():
    REQUEST_LATENCY = Histogram('ai_brain_request_latency_seconds', 'Request latency', ['method', 'endpoint'])
else:
    REQUEST_LATENCY = globals()['REQUEST_LATENCY']

if 'IN_PROGRESS' not in globals():
    IN_PROGRESS = Gauge('ai_brain_inprogress_requests', 'In-progress requests')
else:
    IN_PROGRESS = globals()['IN_PROGRESS']

app = FastAPI(title="AI Brain Service", lifespan=lifespan)

# Middleware to collect metrics
@app.middleware("http")
async def metrics_middleware(request, call_next):
    method = request.method
    # Use path without query for metric labels
    endpoint = request.url.path
    IN_PROGRESS.inc()
    start = request.scope.get('time_start', None)
    with REQUEST_LATENCY.labels(method=method, endpoint=endpoint).time():
        try:
            response = await call_next(request)
            status = str(response.status_code)
            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
            return response
        except Exception as e:
            # On error, increment error counter and re-raise
            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status='500').inc()
            raise
        finally:
            IN_PROGRESS.dec()

# Expose Prometheus metrics endpoint (restricted to admin access)
@app.get('/metrics')
async def metrics(request: Request):
    """Return Prometheus metrics only if a valid admin token is provided.

    Accepts either header `X-Admin-Token: <token>` or `Authorization: Bearer <token>`.
    The token is compared against METRICS_TOKEN env var or LIBRARY_ADMIN_KEY as a fallback.
    """
    # Token sources
    token = request.headers.get('x-admin-token') or request.headers.get('authorization')
    if token and token.lower().startswith('bearer '):
        token = token.split(' ', 1)[1]

    METRICS_TOKEN = os.environ.get('METRICS_TOKEN') or os.environ.get('LIBRARY_ADMIN_KEY')

    if not METRICS_TOKEN:
        # If no token configured, restrict to localhost
        client_host = request.client.host if request.client else None
        if client_host not in ('127.0.0.1', '::1', 'localhost'):
            raise HTTPException(status_code=403, detail='Metrics access restricted to localhost or admin token')
    else:
        if token != METRICS_TOKEN:
            raise HTTPException(status_code=401, detail='Unauthorized')

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Mount orchestration routes if available
import logging
if 'orchestration_router' in globals() and orchestration_router is not None:
    try:
        app.include_router(orchestration_router)
    except Exception as e:
        logging.exception("Failed to include orchestration router: %s", e)
else:
    # Try importing the orchestrator module directly and include its router if present.
    try:
        import importlib
        mod = importlib.import_module("ai_brain.orchestrator")
        orchestration_router = getattr(mod, "router", None)
        if orchestration_router is not None:
            app.include_router(orchestration_router)
    except Exception as e:
        logging.info("orchestration router not available: %s", e)

# Last-ditch attempt: if earlier imports failed due to import-order issues,
# try again now. This ensures tests that load modules in an unusual order still
# get the orchestrator endpoints mounted when possible.
try:
    import importlib
    mod = importlib.import_module("ai_brain.orchestrator")
    orchestration_router = getattr(mod, "router", None)
    if orchestration_router is not None:
        app.include_router(orchestration_router)
except Exception as e:
    logging.debug("late import of orchestrator failed: %s", e)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Mount static files for the "Kilo Lite" frontend (if directory exists)
import os.path
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

    @app.get("/")
    async def read_root():
        return FileResponse('static/index.html')
else:
    logging.warning("Static directory not found, skipping static file serving")

    @app.get("/")
    async def read_root():
        return {"message": "Kilo AI Brain API", "status": "ok"}

# Health check endpoints
@app.get("/status")
@app.get("/health")
def status():
    return {"status": "ok"}

# In-memory user model (replace with DB in production)
user_state = {
    "habits": [],
    "reminders": [],
    "meds": [],
    "finance": [],
    "pantry": {},
    "cam_observations": [],
    "activity_log": [],
}

# --- Models ---
class ChatRequest(BaseModel):
    user: Optional[str] = None
    message: str
    context: Optional[List[str]] = None

class ChatResponse(BaseModel):
    response: str
    context: Optional[List[str]] = None

class MedData(BaseModel):
    name: str
    schedule: str
    dosage: str
    quantity: int
    prescriber: str
    instructions: str

class FinanceData(BaseModel):
    amount: float
    description: str
    date: str

class ReceiptData(BaseModel):
    text: str  # raw OCR text from receipt

class CamObservation(BaseModel):
    timestamp: str
    posture: str  # e.g., 'sitting', 'standing', 'lying'
    pose_match: Optional[bool] = None
    mse: Optional[float] = None
    location: Optional[str] = None

class Reminder(BaseModel):
    text: str
    when: str
    escalated: bool = False

class HabitData(BaseModel):
    name: str
    frequency: str

class HabitCompletionData(BaseModel):
    habit: str
    completion_date: str
    count: int
    frequency: str

class BudgetData(BaseModel):
    category: str
    monthly_limit: float
    created_at: str

class GoalData(BaseModel):
    name: str
    target_amount: float
    current_amount: float
    deadline: Optional[str] = None
    message: str

# --- Library of Truth Integration ---
LIBRARY_URL = "http://library_of_truth:9006"  # Adjust port if needed

async def search_library(query: str):
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{LIBRARY_URL}/search", params={"q": query, "limit": 3})
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
    return []


def synthesize_answer(question: str, passages: list) -> str:
    if not passages:
        return f"Hey Kyle! I'm Kilo, your AI assistant. I searched my memories and library but didn't find specific information about '{question}'. You can:\n• Use /remember <text> to store new information\n• Use /recall <query> to search your memories\n• Ask me about your medications, habits, or finances\n• Upload prescription or receipt images\n\nWhat can I help you with?"
    # Compose a personalized answer from the found passages
    summary = []
    for p in passages:
        summary.append(f"From {p['book']} (p.{p['page']}): {p['text']}")
    # In a real system, use LLM or advanced summarization here
    return f"Here's what I found for '{question}':\n" + '\n'.join(summary)


async def _stt_from_uploadfile(file: UploadFile) -> str:
    """
    Speech-to-text placeholder. Will be replaced by local Whisper in voice microservice.
    For now, returns a placeholder message.
    """
    # Read bytes (kept for interface compatibility)
    data = await file.read()

    # TODO: Integrate with local Whisper microservice
    # For now, return placeholder
    return "(voice recognized - Whisper integration coming soon)"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def _tts_sync(text: str) -> bytes:
    if TTS_PROVIDER == "gtts":
        # gTTS uses Google's online TTS service. Gate this behind ALLOW_NETWORK.
        require_network_or_raise("TTS provider 'gtts' requires network access or set ALLOW_NETWORK=true")
        bio = BytesIO()
        tts = gTTS(text=text, lang='en')
        tts.write_to_fp(bio)
        return bio.getvalue()
    # fallback: synthesize a short WAV tone containing the text as simple beeps
    try:
        import wave, struct, math
        duration = 1.0
        framerate = 22050
        amplitude = 16000
        freq = 440.0
        nframes = int(duration * framerate)
        bio = BytesIO()
        with wave.open(bio, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(framerate)
            for i in range(nframes):
                t = float(i) / framerate
                value = int(amplitude * math.sin(2.0 * math.pi * freq * t))
                data = struct.pack('<h', value)
                wf.writeframesraw(data)
        return bio.getvalue()
    except Exception:
        return b"AUDIO-DATA"


async def _tts_to_base64(text: str) -> str:
    try:
        data = await run_in_threadpool(_tts_sync, text)
        return base64.b64encode(data).decode()
    except Exception:
        return base64.b64encode(b"AUDIO-DATA").decode()


# JSON chat endpoint with RAG (Retrieval Augmented Generation)
@app.post("/chat", response_model=ChatResponse)
async def chat_json(req: ChatRequest):
    """
    Chat endpoint with memory-aware RAG.

    Searches relevant memories and augments the LLM prompt with context.
    Stores the conversation for future retrieval.
    """
    # Check for special memory commands
    message = req.message.strip()

    # /remember command - explicitly store a memory
    if message.startswith("/remember "):
        memory_text = message[10:].strip()
        try:
            Memory = _get_memory_model()
            if Memory:
                s = get_session()
                emb = _embed_text(memory_text)
                mem = Memory(
                    source="user",
                    modality="text",
                    text_blob=memory_text,
                    embedding_json=json.dumps(emb),
                    privacy_label="private"
                )
                s.add(mem)
                s.commit()
                s.refresh(mem)
                return ChatResponse(
                    response=f"✓ Memory stored (ID: {mem.id}). I'll remember: '{memory_text}'",
                    context=req.context
                )
        except Exception as e:
            return ChatResponse(response=f"Error storing memory: {e}", context=req.context)

    # /recall command - search memories
    elif message.startswith("/recall "):
        query = message[8:].strip()
        try:
            from .memory_search import search_memories_by_text
            s = get_session()
            results = search_memories_by_text(query, s, limit=5)
            if results:
                response_parts = [f"Found {len(results)} relevant memories:\n"]
                for i, mem in enumerate(results, 1):
                    response_parts.append(
                        f"{i}. [{mem['source']}] {mem['text'][:100]}... (similarity: {mem['similarity']:.2f})"
                    )
                return ChatResponse(response="\n".join(response_parts), context=req.context)
            else:
                return ChatResponse(response=f"No memories found for '{query}'", context=req.context)
        except Exception as e:
            return ChatResponse(response=f"Error searching memories: {e}", context=req.context)

    # /forget command - delete a memory
    elif message.startswith("/forget "):
        try:
            memory_id = int(message[8:].strip())
            from .memory_search import delete_memory
            s = get_session()
            if delete_memory(memory_id, s):
                return ChatResponse(response=f"✓ Memory {memory_id} deleted", context=req.context)
            else:
                return ChatResponse(response=f"Memory {memory_id} not found", context=req.context)
        except ValueError:
            return ChatResponse(response="Usage: /forget <memory_id>", context=req.context)
        except Exception as e:
            return ChatResponse(response=f"Error deleting memory: {e}", context=req.context)

    # Normal chat with RAG
    try:
        from .rag import generate_rag_response_with_tools, store_conversation_memory
        s = get_session()

        # Generate RAG response with tool support
        rag_result = generate_rag_response_with_tools(
            user_query=req.message,
            session=s,
            max_context_memories=5,
            enable_tools=True  # Enable real-time data access
        )

        response_text = rag_result["response"]

        # Check if response was a breaker message (starts with lightning or snowflake icon from breaker)
        if response_text.startswith("⚡") or response_text.startswith("❄️"):
             # It's a safety block, return it without storing memory (avoids polluting history)
             return ChatResponse(response=response_text, context=req.context)

        # Store this conversation turn as a memory
        try:
            store_conversation_memory(
                user_query=req.message,
                ai_response=response_text,
                session=s
            )
        except Exception as e:
            logging.warning(f"Failed to store conversation memory: {e}")

        # Log Kilo's response for quality monitoring and drift detection
        try:
            from .models import KiloResponse
            kilo_log = KiloResponse(
                user_id=req.user,
                user_query=req.message,
                response=response_text,
                tools_used=json.dumps(rag_result.get("tools_used", [])),
                response_length=len(response_text),
                model_used=rag_result.get("model", "unknown"),
                timestamp=datetime.datetime.utcnow()
            )
            s.add(kilo_log)
            s.commit()
            logger.info(f"[RESPONSE LOG] Logged response {kilo_log.id} for user {req.user}")
        except Exception as e:
            logging.warning(f"Failed to log Kilo response: {e}")

        return ChatResponse(response=response_text, context=req.context)

    except Exception as e:
        logging.error(f"RAG error: {e}")
        # Fallback to simple library search
        passages = await search_library(req.message)
        answer = synthesize_answer(req.message, passages)
        return ChatResponse(response=answer, context=req.context)

# Lightweight quick chat endpoint (no RAG) for low-latency responses
@app.post("/chat/quick", response_model=ChatResponse)
async def chat_quick(req: ChatRequest):
    """
    Quick chat endpoint that avoids the RAG pipeline for lower latency.
    Uses library search and simple synthesis as a fast fallback.
    """
    try:
        # Quick path: search library and synthesize a short answer
        passages = await search_library(req.message)
        answer = synthesize_answer(req.message, passages)
        return ChatResponse(response=answer, context=req.context)
    except Exception as e:
        logging.error(f"chat_quick error: {e}")
        # As a last resort echo the message back
        return ChatResponse(response=f"I heard: {req.message}", context=req.context)

# Form/multipart chat endpoint for voice or form-based input
@app.post("/chat/voice")
async def chat_voice(
    user: Optional[str] = Form(None),
    message: Optional[str] = Form(None),
    audio: Optional[UploadFile] = None
):
    import pathlib
    # If audio is provided, simulate speech-to-text (STT)
    if audio is not None:
        # Run pluggable STT
        stt_text = await _stt_from_uploadfile(audio)
        input_text = stt_text
    elif message:
        input_text = message
    else:
        raise HTTPException(status_code=400, detail="No input provided.")

    # Simulate AI response
    ai_response = f"You said: {input_text}"

    # TTS mode: inline (default) or background
    tts_mode = "inline"
    tts_url = None
    # If the client provided tts_mode as form field, capture it
    # (FastAPI will ignore unknown form fields in signature; read raw form if needed)
    # For now, default to inline behavior for compatibility with integration tests.

    if tts_mode == "inline":
        dummy_audio = await _tts_to_base64(ai_response)
        return JSONResponse({
            "text": ai_response,
            "tts_base64": dummy_audio,
            "tts_url": tts_url,
            "input_text": input_text
        })
    else:
        # background mode: generate file and return a tts_url immediately
        fname = f"tts-{uuid.uuid4().hex}.mp3"
        path = pathlib.Path("/data") / fname

        def _bg_write_tts(text, out_path):
            data = _tts_sync(text)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "wb") as f:
                f.write(data)

        # schedule background write
        from fastapi import BackgroundTasks
        bg = BackgroundTasks()
        bg.add_task(_bg_write_tts, ai_response, path)
        # mount background tasks to run after response
        response = JSONResponse({"text": ai_response, "tts_base64": None, "tts_url": f"/tts/{fname}", "input_text": input_text})
        response.background = bg
        return response
# --- Ingest endpoints and other APIs ---
@app.post("/ingest/meds")
def ingest_meds(med: MedData, background_tasks: BackgroundTasks):
    user_state["meds"].append(_to_dict(med))
    # Proactively set a reminder
    reminder = Reminder(text=f"Take {med.name} as scheduled.", when=med.schedule)
    user_state["reminders"].append(_to_dict(reminder))
    background_tasks.add_task(_log_activity, f"Ingested med: {med.name}")
    # Persist a Memory for this med ingestion
    try:
        Memory = _get_memory_model()
        if Memory is not None:
            s = get_session()
            txt = f"med:{med.name} schedule:{med.schedule} dosage:{med.dosage}"
            emb = _embed_text(txt)
            mem = Memory(source="meds", modality="text", text_blob=txt, metadata_json=json.dumps(_to_dict(med)), embedding_json=json.dumps(emb))
            s.add(mem)
            s.commit()
            s.refresh(mem)
    except Exception:
        pass
    return {"status": "ok", "reminder": reminder}

@app.post("/ingest/finance")
def ingest_finance(fin: FinanceData, background_tasks: BackgroundTasks):
    user_state["finance"].append(_to_dict(fin))
    background_tasks.add_task(_log_activity, f"Finance event: {fin.description}")
    # Persist a Memory for this finance event
    try:
        Memory = _get_memory_model()
        if Memory is not None:
            s = get_session()
            txt = f"finance:{fin.description} amount:{fin.amount} date:{fin.date}"
            emb = _embed_text(txt)
            mem = Memory(source="finance", modality="text", text_blob=txt, metadata_json=json.dumps(_to_dict(fin)), embedding_json=json.dumps(emb))
            s.add(mem)
            s.commit()
            s.refresh(mem)
    except Exception:
        pass
    return {"status": "ok"}

@app.post("/ingest/receipt")
def ingest_receipt(receipt: ReceiptData, background_tasks: BackgroundTasks):
    items = _parse_receipt(receipt.text)
    for item in items:
        user_state["pantry"][item] = user_state["pantry"].get(item, 0) + 1
    background_tasks.add_task(_log_activity, f"Receipt processed: {items}")
    # Persist a Memory for the whole receipt and per-item
    try:
        Memory = _get_memory_model()
        if Memory is not None:
            s = get_session()
            txt = receipt.text
            emb = _embed_text(txt)
            mem = Memory(source="receipt", modality="text", text_blob=txt, metadata_json=json.dumps({"items": items}), embedding_json=json.dumps(emb))
            s.add(mem)
            s.commit()
            s.refresh(mem)
            # also create short memories per item
            for it in items:
                it_txt = f"purchased:{it}"
                emb2 = _embed_text(it_txt)
                mem2 = Memory(source="receipt", modality="text", text_blob=it_txt, metadata_json=json.dumps({}), embedding_json=json.dumps(emb2))
                s.add(mem2)
            s.commit()
    except Exception:
        pass
    return {"status": "ok", "items": items}

@app.post("/ingest/cam")
def ingest_cam(obs: CamObservation, background_tasks: BackgroundTasks):
    user_state["cam_observations"].append(_to_dict(obs))
    background_tasks.add_task(_log_activity, f"Cam observed: {obs.posture} at {obs.timestamp} match={obs.pose_match}")
    feedback = None
    if obs.pose_match is not None:
        feedback = "Great job! Your pose matches the reference." if obs.pose_match else "Try to adjust your posture to match the reference."
    elif obs.posture in ("sitting", "standing", "lying"):
        feedback = f"Detected posture: {obs.posture}."
    # Persist a Memory for this cam observation
    try:
        Memory = _get_memory_model()
        if Memory is not None:
            s = get_session()
            txt = f"posture:{obs.posture} match:{obs.pose_match}"
            emb = _embed_text(txt)
            mem = Memory(source="cam", modality="text", text_blob=txt, metadata_json=json.dumps(_to_dict(obs)), embedding_json=json.dumps(emb))
            s.add(mem)
            s.commit()
            s.refresh(mem)
    except Exception:
        pass
    return {"status": "ok", "feedback": feedback}


@app.post("/ingest/habit")
def ingest_habit(habit: HabitData, background_tasks: BackgroundTasks):
    user_state["habits"].append(_to_dict(habit))
    background_tasks.add_task(_log_activity, f"New habit tracked: {habit.name}")
    # Persist a Memory for this habit
    try:
        Memory = _get_memory_model()
        if Memory is not None:
            s = get_session()
            txt = f"habit:{habit.name} frequency:{habit.frequency}"
            emb = _embed_text(txt)
            mem = Memory(source="habits", modality="text", text_blob=txt, metadata_json=json.dumps(_to_dict(habit)), embedding_json=json.dumps(emb))
            s.add(mem)
            s.commit()
            s.refresh(mem)
    except Exception:
        pass
    return {"status": "ok"}

@app.post("/ingest/habit_completion")
def ingest_habit_completion(completion: HabitCompletionData, background_tasks: BackgroundTasks):
    background_tasks.add_task(_log_activity, f"Habit completed: {completion.habit} on {completion.completion_date}")
    # Persist a Memory for this completion
    try:
        Memory = _get_memory_model()
        if Memory is not None:
            s = get_session()
            txt = f"completed_habit:{completion.habit} date:{completion.completion_date} count:{completion.count}"
            emb = _embed_text(txt)
            mem = Memory(source="habits", modality="text", text_blob=txt, metadata_json=json.dumps(_to_dict(completion)), embedding_json=json.dumps(emb))
            s.add(mem)
            s.commit()
            s.refresh(mem)
    except Exception:
        pass
    return {"status": "ok"}

@app.post("/ingest/budget")
def ingest_budget(budget: BudgetData, background_tasks: BackgroundTasks):
    background_tasks.add_task(_log_activity, f"Budget set: {budget.category} - ${budget.monthly_limit}")
    # Persist a Memory for this budget
    try:
        Memory = _get_memory_model()
        if Memory is not None:
            s = get_session()
            txt = f"budget:{budget.category} limit:${budget.monthly_limit}/month"
            emb = _embed_text(txt)
            mem = Memory(source="finance", modality="text", text_blob=txt, metadata_json=json.dumps(_to_dict(budget)), embedding_json=json.dumps(emb))
            s.add(mem)
            s.commit()
            s.refresh(mem)
    except Exception:
        pass
    return {"status": "ok"}

@app.post("/ingest/goal")
def ingest_goal(goal: GoalData, background_tasks: BackgroundTasks):
    background_tasks.add_task(_log_activity, f"Financial goal: {goal.message}")
    # Persist a Memory for this goal
    try:
        Memory = _get_memory_model()
        if Memory is not None:
            s = get_session()
            txt = goal.message
            emb = _embed_text(txt)
            mem = Memory(source="finance", modality="text", text_blob=txt, metadata_json=json.dumps(_to_dict(goal)), embedding_json=json.dumps(emb))
            s.add(mem)
            s.commit()
            s.refresh(mem)
    except Exception:
        pass
    return {"status": "ok"}

@app.post('/ingest/cam_activity')
def ingest_cam_activity(payload: Dict[str, Any], background_tasks: BackgroundTasks = None):
    """Receive activity observations from cam and return simple recipe suggestions when cooking is detected."""
    ts = payload.get('timestamp')
    activities = payload.get('activities', [])
    user_state['activity_log'].append({'timestamp': ts, 'activities': activities})
    suggestions = []
    if 'cooking' in activities:
        # build simple suggestions from pantry items
        pantry = user_state.get('pantry', {})
        items = list(pantry.keys())
        if items:
            # naive combinations
            for i in range(min(3, len(items))):
                a = items[i]
                b = items[(i+1) % len(items)] if len(items) > 1 else None
                if b:
                    suggestions.append(f"Use {a} with {b}")
                else:
                    suggestions.append(f"Cook something with {a}")
        else:
            suggestions.append('No pantry items found; try adding groceries')
    # optional background logging
    if background_tasks is not None:
        background_tasks.add_task(_log_activity, f"Cam activity: {activities}")
    # Persist a Memory for this cam activity bundle
    try:
        Memory = _get_memory_model()
        if Memory is not None:
            s = get_session()
            txt = f"cam_activity:{activities}"
            emb = _embed_text(txt)
            mem = Memory(source="cam", modality="text", text_blob=txt, metadata_json=json.dumps({'activities': activities}), embedding_json=json.dumps(emb))
            s.add(mem)
            s.commit()
            s.refresh(mem)
    except Exception:
        pass
    return {'status': 'ok', 'suggestions': suggestions}

@app.post("/reminder/ack")
def acknowledge_reminder(reminder: Reminder):
    for r in user_state["reminders"]:
        if r["text"] == reminder.text and r["when"] == reminder.when:
            r["escalated"] = False
    return {"status": "acknowledged"}

# --- Voice Stubs ---
@app.post("/voice/activate")
def voice_activate(audio: UploadFile = File(...)):
    # Save uploaded activation audio and attempt a lightweight transcription
    try:
        data = audio.file.read()
        fname = f"/tmp/voice-activate-{uuid.uuid4().hex}-{getattr(audio, 'filename', 'audio') }"
        with open(fname, 'wb') as f:
            f.write(data)
        # attempt to decode as text
        try:
            txt = data.decode('utf-8')
        except Exception:
            txt = None
        return {"status": "saved", "path": fname, "transcription": txt}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/voice/speak")
def voice_speak(text: str):
    # Generate TTS audio (base64) and return a temporary path and the base64 payload
    try:
        data = _tts_sync(text)
        fname = f"/tmp/tts-{uuid.uuid4().hex}.wav"
        with open(fname, 'wb') as f:
            f.write(data)
        b64 = base64.b64encode(data).decode()
        return {"status": "ok", "text": text, "tts_path": fname, "tts_base64": b64}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# --- Analytics and Feedback Endpoints ---
@app.get("/analytics/habits")
def habit_analytics():
    completions = defaultdict(list)
    for h in user_state.get("habits", []):
        name = h.get("name")
        for c in h.get("completions", []):
            completions[name].append(c["completed_at"])
    analytics = {}
    for name, times in completions.items():
        times_sorted = sorted(times)
        streak = _calculate_streak(times_sorted)
        analytics[name] = {
            "total_completions": len(times),
            "current_streak": streak,
            "last_completed": times_sorted[-1] if times_sorted else None
        }
    return analytics

@app.get("/feedback/habits")
def habit_feedback():
    analytics = habit_analytics()
    feedback = []
    for name, stats in analytics.items():
        if stats["current_streak"] >= 5:
            feedback.append(f"Great job keeping up with '{name}'! Your streak is {stats['current_streak']} days.")
        elif stats["current_streak"] == 0:
            feedback.append(f"You haven't completed '{name}' recently. Try to get back on track!")
        else:
            feedback.append(f"You're doing well with '{name}', current streak: {stats['current_streak']}.")
    return {"feedback": feedback}


@app.get("/stats/dashboard")
async def get_dashboard_stats():
    """
    Aggregate stats from all services for the dashboard.
    Returns counts and metrics for display in the main dashboard.
    """
    stats = {
        "totalMemories": 0,
        "activeHabits": 0,
        "upcomingReminders": 0,
        "monthlySpending": 0,
        "insightsGenerated": 0
    }

    # Get memory count from local storage
    try:
        with get_session() as session:
            from sqlmodel import select, func
            from .models import Memory
            stats["totalMemories"] = session.exec(select(func.count(Memory.id))).one()
    except Exception:
        pass

    # Fetch from other services
    async with httpx.AsyncClient(timeout=2.0) as client:
        # Habits
        try:
            resp = await client.get("http://docker_habits_1:9003/")
            if resp.status_code == 200:
                habits = resp.json()
                stats["activeHabits"] = len([h for h in habits if h.get("active", True)])
        except Exception:
            pass

        # Reminders
        try:
            resp = await client.get("http://docker_reminder_1:9002/")
            if resp.status_code == 200:
                reminders = resp.json()
                stats["upcomingReminders"] = len([r for r in reminders if not r.get("sent", False)])
        except Exception:
            pass

        # Financial
        try:
            resp = await client.get("http://docker_financial_1:9005/summary")
            if resp.status_code == 200:
                summary = resp.json()
                stats["monthlySpending"] = abs(summary.get("total_expenses", 0))
        except Exception:
            pass

    # Insights generated is based on memories + conversations
    stats["insightsGenerated"] = stats["totalMemories"]

    return stats


@app.get("/memory/visualization")
async def get_memory_visualization():
    """
    Return memory visualization data for charts and graphs.
    Includes timeline data and category breakdown.
    """
    viz_data = {
        "timeline": [],
        "categories": []
    }

    try:
        with get_session() as session:
            from sqlmodel import select
            from .models import Memory
            from collections import defaultdict

            memories = session.exec(select(Memory)).all()

            # Group by date for timeline
            by_date = defaultdict(int)
            by_category = defaultdict(int)

            for memory in memories:
                # Extract date from timestamp
                try:
                    date_str = memory.timestamp[:10] if hasattr(memory, 'timestamp') else datetime.datetime.utcnow().isoformat()[:10]
                    by_date[date_str] += 1
                except Exception:
                    pass

                # Category from metadata or default
                category = "general"
                if hasattr(memory, 'metadata') and memory.metadata:
                    if isinstance(memory.metadata, dict):
                        category = memory.metadata.get("category", "general")
                by_category[category] += 1

            # Convert to list format for frontend
            viz_data["timeline"] = [
                {"date": date, "count": count}
                for date, count in sorted(by_date.items())
            ][-30:]  # Last 30 days

            viz_data["categories"] = [
                {"name": cat, "count": count}
                for cat, count in sorted(by_category.items(), key=lambda x: x[1], reverse=True)
            ][:10]  # Top 10 categories

    except Exception as e:
        # Return empty data on error
        logger.error(f"Failed to generate memory visualization: {e}")

    return viz_data


# --- Helpers ---
def _parse_receipt(text: str) -> List[str]:
    lines = text.splitlines()
    items = []
    for line in lines:
        m = re.match(r"([A-Za-z ]+)\s+\d+\.\d{2}", line)
        if m:
            items.append(m.group(1).strip())
    return items


def _log_activity(event: str):
    user_state["activity_log"].append({"event": event, "timestamp": datetime.datetime.utcnow().isoformat()})


def _embed_text(text: str, dim: int = 384):
    """
    Generate semantic embedding for text using sentence-transformers.
    Falls back to hash-based embedding if model unavailable.

    This function is used throughout the codebase for backward compatibility.
    For new code, prefer using ai_brain.embeddings.embed_text directly.
    """
    try:
        from .embeddings import embed_text
        return embed_text(text)
    except Exception:
        # Fallback to simple hash-based embedding
        if not text:
            return [0.0] * dim
        h = hashlib.sha256(text.encode('utf-8')).hexdigest()
        vals = []
        chunk_size = max(2, len(h) // dim)
        for i in range(dim):
            chunk = h[i * chunk_size:(i + 1) * chunk_size]
            if not chunk:
                vals.append(0.0)
                continue
            intval = int(chunk, 16)
            maxval = float(int('f' * len(chunk), 16))
            vals.append(intval / maxval)
        return vals[:dim]


def _calculate_streak(times_sorted):
    if not times_sorted:
        return 0
    streak = 1
    last_date = datetime.datetime.fromisoformat(times_sorted[-1]).date()
    for t in reversed(times_sorted[:-1]):
        d = datetime.datetime.fromisoformat(t).date()
        if (last_date - d).days == 1:
            streak += 1
            last_date = d
        else:
            break
    return streak


@app.get("/tts/{fname}")
def serve_tts(fname: str):
    path = pathlib.Path("/data") / fname
    if not path.exists():
        raise HTTPException(status_code=404, detail="TTS not ready")
    return FileResponse(str(path), media_type="audio/mpeg")


@app.post("/analyze/prescription")
async def analyze_prescription(image: UploadFile = File(...)):
    """
    Analyze prescription image using OCR to extract medication information.
    Supports single image uploads. Text from curved bottles can be captured.
    Returns structured medication data that can be added to the medication schedule.
    """
    try:
        # Import OCR libraries
        try:
            import pytesseract
            from PIL import Image
        except ImportError as e:
            raise HTTPException(status_code=500, detail=f"OCR libraries not available: {e}")

        # Read and process the image
        image_bytes = await image.read()
        pil_image = Image.open(BytesIO(image_bytes))
        ocr_text = pytesseract.image_to_string(pil_image)

        if not ocr_text.strip():
            return {
                "success": False,
                "error": "No text detected in image. Please ensure the prescription is clearly visible and well-lit.",
                "ocr_text": "",
                "images_processed": 1
            }

        # Use RAG/LLM to parse the prescription text
        try:
            from .rag import generate_rag_response
            s = get_session()

            # Craft a prompt to extract medication information
            prompt = f"""Analyze this prescription text and extract medication information in JSON format.

Prescription text:
{ocr_text}

Please extract the following fields if available:
- medication_name: The name of the medication
- dosage: The dosage amount and units (e.g., "500mg", "10ml")
- schedule: How often to take it (e.g., "twice daily", "every 8 hours", "once at bedtime")
- prescriber: Doctor's name if visible
- instructions: Any special instructions (e.g., "take with food", "avoid alcohol")

Return ONLY a JSON object with these fields. If a field is not found, use null."""

            rag_result = generate_rag_response(
                user_query=prompt,
                session=s,
                max_context_memories=0  # Don't need memory context for prescription parsing
            )

            response_text = rag_result["response"]

            # Try to extract JSON from the response
            import re
            json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
            if json_match:
                parsed_data = json.loads(json_match.group())
            else:
                # Fallback: return raw text if JSON parsing fails
                parsed_data = {
                    "medication_name": None,
                    "dosage": None,
                    "schedule": None,
                    "prescriber": None,
                    "instructions": response_text
                }

            return {
                "success": True,
                "ocr_text": ocr_text,
                "parsed_data": parsed_data,
                "ai_interpretation": response_text,
                "images_processed": 1
            }

        except Exception as e:
            # Fallback: return OCR text without AI parsing
            return {
                "success": True,
                "ocr_text": ocr_text,
                "parsed_data": None,
                "error": f"AI parsing failed: {e}. Raw OCR text available.",
                "images_processed": 1
            }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Image analysis failed: {e}")


# Orchestration router is mounted above if available (guarded)


# ===== PHASE 3 & 4 ADVANCED FEATURES =====

@app.get("/api/v1/scalability/status")
async def get_scalability_status():
    """Get status of scalability features"""
    from .async_processing import async_pipeline, resource_manager
    from .data_partitioning import data_partitioner, partitioned_store

    pipeline_stats = async_pipeline.get_stats()
    partition_stats = data_partitioner.get_partition_stats()

    return {
        "async_processing": {
            "active": async_pipeline.is_running,
            "queue_size": pipeline_stats.get("queue_size", 0),
            "tasks_processed": pipeline_stats.get("tasks_processed", 0),
            "avg_processing_time": pipeline_stats.get("avg_processing_time", 0)
        },
        "data_partitioning": {
            "partitions": len(partition_stats),
            "total_size_mb": sum(p.get("total_size_mb", 0) for p in partition_stats.values()),
            "partition_details": partition_stats
        },
        "resource_management": {
            "current_batch_size": resource_manager.get_optimal_batch_size(),
            "should_throttle": resource_manager.should_throttle()
        }
    }


@app.post("/api/v1/async/embeddings")
async def generate_embeddings_async(texts: List[str], priority: int = 1):
    """Generate embeddings asynchronously"""
    from .async_processing import async_pipeline

    if not texts:
        raise HTTPException(status_code=400, detail="No texts provided")

    task_id = async_pipeline.submit_embedding_task(texts, priority)
    return {"task_id": task_id, "status": "submitted", "estimated_completion": "30-60 seconds"}


@app.post("/api/v1/async/indexing")
async def index_memories_async(memory_ids: List[int], priority: int = 2):
    """Index memories asynchronously"""
    from .async_processing import async_pipeline
    from .db import get_session

    if not memory_ids:
        raise HTTPException(status_code=400, detail="No memory IDs provided")

    # Get memory data
    with get_session() as session:
        Memory = _get_memory_model()
        if not Memory:
            raise HTTPException(status_code=500, detail="Memory model not available")

        memories = session.query(Memory).filter(Memory.id.in_(memory_ids)).all()
        memory_data = [
            {
                "id": m.id,
                "text_blob": m.text_blob,
                "embedding_json": m.embedding_json,
                "metadata_json": m.metadata_json
            }
            for m in memories
        ]

    task_id = async_pipeline.submit_indexing_task(memory_data, priority)
    return {"task_id": task_id, "status": "submitted", "memories_to_index": len(memory_data)}


@app.post("/api/v1/async/consolidation")
async def consolidate_memories_async(partition_key: str = None, days_old: int = 30):
    """Consolidate old memories asynchronously"""
    from .async_processing import async_pipeline

    task_id = async_pipeline.submit_consolidation_task(partition_key or "default", days_old=days_old)
    return {"task_id": task_id, "status": "submitted", "partition": partition_key}


@app.get("/api/v1/predictive/insights")
async def get_predictive_insights():
    """Get predictive insights and recommendations"""
    from .predictive_modeling import predictive_analytics

    # Get recent memory data for training (simplified)
    with get_session() as session:
        Memory = _get_memory_model()
        if Memory:
            recent_memories = session.query(Memory).order_by(Memory.created_at.desc()).limit(100).all()
            memory_data = [
                {
                    "source": m.source,
                    "text_blob": m.text_blob,
                    "metadata_json": m.metadata_json,
                    "created_at": m.created_at.isoformat()
                }
                for m in recent_memories
            ]

            # Train models with recent data
            predictive_analytics.train_all_models(memory_data)

    # Generate insights
    insights = predictive_analytics.get_proactive_insights()

    return {
        "insights": insights,
        "generated_at": datetime.datetime.utcnow(),
        "model_status": "trained" if predictive_analytics.models["habits"].is_trained else "training"
    }


@app.get("/api/v1/knowledge/graph/stats")
async def get_knowledge_graph_stats():
    """Get knowledge graph statistics"""
    from .knowledge_graph import knowledge_graph

    stats = knowledge_graph.get_graph_stats()
    return {
        "graph_stats": stats,
        "entity_types": knowledge_graph.entity_types,
        "relationship_types": knowledge_graph.relationship_types
    }


@app.post("/api/v1/knowledge/graph/build")
async def build_knowledge_graph(limit: int = 1000):
    """Build knowledge graph from memory data"""
    from .knowledge_graph import knowledge_graph

    with get_session() as session:
        Memory = _get_memory_model()
        if not Memory:
            raise HTTPException(status_code=500, detail="Memory model not available")

        memories = session.query(Memory).order_by(Memory.created_at.desc()).limit(limit).all()
        memory_data = [
            {
                "source": m.source,
                "text_blob": m.text_blob,
                "metadata_json": m.metadata_json
            }
            for m in memories
        ]

    entities_added = knowledge_graph.build_from_memories(memory_data)

    return {
        "status": "completed",
        "memories_processed": len(memory_data),
        "entities_added": entities_added,
        "graph_stats": knowledge_graph.get_graph_stats()
    }


@app.get("/api/v1/knowledge/reason/{entity_id}")
async def reason_about_entity(entity_id: str):
    """Get reasoning insights about an entity"""
    from .knowledge_graph import knowledge_reasoner

    impacts = knowledge_reasoner.reason_about_impact(entity_id)
    suggestions = knowledge_reasoner.suggest_actions({"indicators": []})  # Simplified

    return {
        "entity_id": entity_id,
        "impacts": impacts,
        "suggested_actions": suggestions
    }


@app.post("/api/v1/conversation/start")
async def start_conversation(user_id: str, initial_context: Dict[str, Any] = None):
    """Start a new conversation"""
    from .conversation_management import conversation_manager

    conversation_id = str(uuid.uuid4())
    conversation_manager.start_conversation(conversation_id, user_id, initial_context)

    return {
        "conversation_id": conversation_id,
        "status": "started",
        "user_id": user_id
    }


@app.post("/api/v1/conversation/{conversation_id}/turn")
async def add_conversation_turn(conversation_id: str, user_message: str, ai_response: str):
    """Add a turn to a conversation"""
    from .conversation_management import conversation_manager

    success = conversation_manager.add_turn(conversation_id, user_message, ai_response)

    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {"status": "added", "conversation_id": conversation_id}


@app.post("/api/v1/conversation/{conversation_id}/goals")
async def set_conversation_goals(conversation_id: str, goals: List[Dict[str, Any]]):
    """Set goals for a conversation"""
    from .conversation_management import conversation_manager

    success = conversation_manager.set_goals(conversation_id, goals)

    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {"status": "set", "goals_count": len(goals)}


@app.get("/api/v1/conversation/{conversation_id}/context")
async def get_conversation_context(conversation_id: str):
    """Get conversation context"""
    from .conversation_management import conversation_manager

    context = conversation_manager.get_conversation_context(conversation_id)

    if not context:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return context


@app.get("/api/v1/conversation/{conversation_id}/suggestions")
async def get_conversation_suggestions(conversation_id: str):
    """Get conversation suggestions"""
    from .conversation_management import conversation_manager

    suggestions = conversation_manager.suggest_next_actions(conversation_id)
    return {"suggestions": suggestions}


@app.get("/api/v1/user/{user_id}/insights")
async def get_user_insights(user_id: str):
    """Get user insights from conversation history"""
    from .conversation_management import conversation_manager

    insights = conversation_manager.get_user_insights(user_id)
    return {"user_id": user_id, "insights": insights}


@app.post("/api/v1/goals/suggest")
async def suggest_goals(user_context: Dict[str, Any]):
    """Suggest goals based on user context"""
    from .conversation_management import goal_assistant

    suggestions = goal_assistant.suggest_goals_based_on_context(user_context)
    return {"suggested_goals": suggestions}


@app.get("/api/v1/goals/templates")
async def get_goal_templates():
    """Get available goal templates"""
    from .conversation_management import goal_assistant

    return {"templates": list(goal_assistant.goal_templates.keys())}


# ===== END PHASE 3 & 4 FEATURES =====


# ===== PROACTIVE AGENT INTEGRATION =====

# Import agent bridge
try:
    from .agent_bridge import agent_queue, agent_handler, AgentMessage, AgentCommand, AgentResponse
except:
    try:
        from agent_bridge import agent_queue, agent_handler, AgentMessage, AgentCommand, AgentResponse
    except:
        # Fallback - agent bridge not available
        agent_queue = None
        agent_handler = None
        AgentMessage = None
        AgentCommand = None
        AgentResponse = None


@app.post("/agent/notify")
async def agent_notify(message: Dict[str, Any]):
    """
    Endpoint for proactive agent to post notifications to chat

    Example:
    POST /agent/notify
    {
        "type": "reminder",
        "content": "⏰ Reminder in 30 minutes: Take Adderall",
        "priority": "high"
    }
    """
    if agent_queue is None or AgentMessage is None:
        raise HTTPException(status_code=503, detail="Agent bridge not available")

    try:
        agent_msg = AgentMessage(**message)
        await agent_queue.add_message(agent_msg)
        return {"status": "ok", "message": "Notification queued"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid message format: {str(e)}")


@app.get("/agent/messages")
async def get_agent_messages(since_minutes: int = 5, count: int = 10):
    """
    Get pending agent messages for chat display

    Query params:
    - since_minutes: Get messages from last N minutes (default 5)
    - count: Max number of messages to return (default 10)
    """
    if agent_queue is None:
        return {"messages": []}

    from datetime import datetime, timedelta
    since = datetime.now() - timedelta(minutes=since_minutes)

    messages = await agent_queue.get_pending_messages(since=since)

    # Convert to dict for JSON serialization
    return {
        "messages": [
            {
                "type": msg.type,
                "content": msg.content,
                "priority": msg.priority,
                "timestamp": msg.timestamp.isoformat(),
                "metadata": msg.metadata
            }
            for msg in messages[-count:]
        ]
    }


@app.post("/agent/command")
async def execute_agent_command(command: Dict[str, Any]):
    """
    Execute a command through the proactive agent

    Example:
    POST /agent/command
    {
        "command": "show my spending today",
        "params": {},
        "user": "user"
    }
    """
    if agent_handler is None or AgentCommand is None:
        raise HTTPException(status_code=503, detail="Agent handler not available")

    try:
        cmd = AgentCommand(**command)
        response = await agent_handler.handle_command(cmd)

        return {
            "success": response.success,
            "message": response.message,
            "data": response.data
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error executing command: {str(e)}",
            "data": None
        }


@app.get("/agent/status")
async def get_agent_status():
    """Get status of agent integration"""
    if agent_queue is None:
        return {"status": "unavailable", "message": "Agent bridge not loaded"}

    recent = await agent_queue.get_recent_messages(count=5)

    return {
        "status": "ok",
        "queue_size": len(agent_queue.messages),
        "recent_message_count": len(recent),
        "last_message": recent[-1].timestamp.isoformat() if recent else None
    }


# ===== KILO RESPONSE MONITORING =====

@app.get("/responses/recent")
async def get_recent_responses(
    user_id: Optional[str] = None,
    limit: int = 50,
    flagged_only: bool = False
):
    """
    Retrieve recent Kilo responses for quality monitoring and drift detection.

    Args:
        user_id: Filter by specific user (default: all users)
        limit: Number of responses to return (default: 50, max: 500)
        flagged_only: Only return flagged responses (default: False)
    """
    try:
        from .models import KiloResponse
        s = get_session()

        limit = min(limit, 500)  # Cap at 500

        query = s.query(KiloResponse)

        if user_id:
            query = query.filter(KiloResponse.user_id == user_id)

        if flagged_only:
            query = query.filter(KiloResponse.flagged == True)

        responses = query.order_by(KiloResponse.timestamp.desc()).limit(limit).all()

        return {
            "count": len(responses),
            "responses": [
                {
                    "id": r.id,
                    "user_id": r.user_id,
                    "user_query": r.user_query,
                    "response": r.response,
                    "tools_used": json.loads(r.tools_used) if r.tools_used else [],
                    "response_length": r.response_length,
                    "model_used": r.model_used,
                    "timestamp": r.timestamp.isoformat(),
                    "flagged": r.flagged,
                    "notes": r.notes
                }
                for r in responses
            ]
        }
    except Exception as e:
        logger.error(f"Error retrieving responses: {e}")
        return {"error": str(e), "count": 0, "responses": []}


@app.post("/responses/{response_id}/flag")
async def flag_response(response_id: int, notes: Optional[str] = None):
    """
    Flag a response as problematic for review.

    Args:
        response_id: ID of the response to flag
        notes: Optional notes about why it was flagged
    """
    try:
        from .models import KiloResponse
        s = get_session()

        response = s.query(KiloResponse).filter(KiloResponse.id == response_id).first()

        if not response:
            raise HTTPException(status_code=404, detail="Response not found")

        response.flagged = True
        if notes:
            response.notes = notes

        s.commit()

        return {
            "success": True,
            "message": f"Response {response_id} flagged",
            "response_id": response_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error flagging response: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/responses/stats")
async def get_response_stats(user_id: Optional[str] = None, days: int = 7):
    """
    Get statistics about Kilo's responses for drift detection.

    Args:
        user_id: Filter by specific user (default: all users)
        days: Number of days to analyze (default: 7)
    """
    try:
        from .models import KiloResponse
        from sqlalchemy import func
        s = get_session()

        cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)

        query = s.query(KiloResponse).filter(KiloResponse.timestamp >= cutoff_date)

        if user_id:
            query = query.filter(KiloResponse.user_id == user_id)

        total_responses = query.count()
        flagged_count = query.filter(KiloResponse.flagged == True).count()

        # Average response length
        avg_length = s.query(func.avg(KiloResponse.response_length)).filter(
            KiloResponse.timestamp >= cutoff_date
        ).scalar() or 0

        # Most common tools used
        all_responses = query.all()
        tool_usage = defaultdict(int)
        for r in all_responses:
            if r.tools_used:
                try:
                    tools = json.loads(r.tools_used)
                    for tool in tools:
                        tool_usage[tool] += 1
                except:
                    pass

        return {
            "period_days": days,
            "total_responses": total_responses,
            "flagged_responses": flagged_count,
            "flagged_percentage": (flagged_count / total_responses * 100) if total_responses > 0 else 0,
            "avg_response_length": int(avg_length),
            "tool_usage": dict(tool_usage),
            "user_id": user_id or "all"
        }
    except Exception as e:
        logger.error(f"Error getting response stats: {e}")
        return {"error": str(e)}


# ===== END PROACTIVE AGENT INTEGRATION =====
