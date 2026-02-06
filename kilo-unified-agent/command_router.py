"""
Command Router -- routes natural-language commands to the right Kilo service.

Strategy:
  1. Keyword-table scan (ordered by priority).  First match wins.
  2. If keyword confidence >= 0.8, route immediately (deterministic fast path).
  3. Otherwise, sentence-transformer embedding similarity against service
     capabilities (semantic slow path).  Threshold: cosine > 0.5.
  4. If target is a k3s pod  -> direct HTTP call with intent-aware endpoint selection.
  5. If target is a guardian service -> forwarded to Gemini with full system context.
  6. No match at all -> Gemini fallback with system context.

Gemini carries the full 3-layer context prompt so it can kubectl exec into pods,
run host commands, etc. when the keyword router cannot handle the request.
"""

import asyncio
import logging
import os
import shlex
import subprocess
from typing import Any, Dict, List, Tuple

import httpx

# ---------------------------------------------------------------------------
# Sentence-Transformer model  (loaded once at import time)
# ---------------------------------------------------------------------------
os.environ["TOKENIZERS_PARALLELISM"] = "false"

try:
    import numpy as np
    from sentence_transformers import SentenceTransformer
    _embedding_model: "SentenceTransformer | None" = SentenceTransformer("all-MiniLM-L6-v2")
except ImportError:
    _embedding_model = None
    np = None  # type: ignore[assignment]
except Exception:
    _embedding_model = None

logger = logging.getLogger("CommandRouter")

if _embedding_model:
    logger.info("Loaded SentenceTransformer (all-MiniLM-L6-v2) for semantic routing.")
else:
    logger.warning("SentenceTransformer unavailable -- falling back to keyword-only routing.")

# ---------------------------------------------------------------------------
# Service-capability embeddings  (populated at startup via precompute_*)
# ---------------------------------------------------------------------------
# {service_name: np.ndarray  shape=(n_capabilities, 384)}
_service_cap_embeddings: Dict[str, Any] = {}


def precompute_service_embeddings(registry) -> None:
    """
    Encode every service's capability strings into 384-d vectors.
    Call once during agent startup, AFTER the registry is populated.
    """
    if not _embedding_model:
        logger.warning("Cannot precompute service embeddings -- model not loaded.")
        return

    logger.info("Precomputing service capability embeddings...")
    _service_cap_embeddings.clear()

    for name, svc in registry.services.items():
        if svc.capabilities:
            embs = _embedding_model.encode(svc.capabilities, show_progress_bar=False)
            _service_cap_embeddings[name] = embs

    logger.info("Precomputed embeddings for %d services.", len(_service_cap_embeddings))


def _cosine(a, b) -> float:
    """Cosine similarity between two 1-D numpy arrays."""
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def _semantic_route(text: str) -> Tuple[str, float]:
    """
    Compare *text* against every precomputed service capability.
    Returns (service_name, confidence) if cosine > 0.5, else ("gemini_fallback", 0.0).
    Confidence is mapped from [0.5, 1.0] -> [0.6, 0.95] so keyword hits at 1.0
    always take priority.
    """
    if not _embedding_model or not _service_cap_embeddings:
        return ("gemini_fallback", 0.0)

    query_emb = _embedding_model.encode([text], show_progress_bar=False)[0]

    best_svc: str | None = None
    best_sim = -1.0

    for name, cap_embs in _service_cap_embeddings.items():
        for cap_emb in cap_embs:
            sim = _cosine(query_emb, cap_emb)
            if sim > best_sim:
                best_sim = sim
                best_svc = name

    if best_svc and best_sim > 0.5:
        # Linear remap: 0.5 -> 0.6, 1.0 -> 0.95
        conf = 0.6 + 0.35 * (best_sim - 0.5) / 0.5
        return (best_svc, round(conf, 3))

    return ("gemini_fallback", 0.0)


# ---------------------------------------------------------------------------
# Route table
# (keywords, target, priority)   lower priority = checked first
# ---------------------------------------------------------------------------
ROUTES: List[Tuple[List[str], str, int]] = [
    # --- domain services (priority 0) ---
    (["remind", "reminder", "reminders", "remind me"],
     "reminder", 0),
    (["habit", "habits", "streak", "complete habit", "mark habit", "habits done"],
     "habits", 0),
    (["med", "meds", "medication", "medications", "pill", "pills", "dosage", "taken"],
     "meds", 0),
    (["spend", "spending", "budget", "money", "expense", "expenses",
      "bill", "bills", "financial", "finance", "csv upload", "bank", "income"],
     "financial", 0),
    (["camera", "cam", "face", "who is that", "posture", "sitting", "standing"],
     "cam", 0),
    (["voice", "listen", "speak", "say", "tts", "stt", "speech", "read aloud"],
     "voice", 0),
    (["library", "reference", "look up", "define"],
     "library", 0),
    (["predict", "forecast", "ml", "machine learning", "pattern", "trend", "analytics"],
     "ml_engine", 0),
    (["usb", "transfer", "sync file", "upload file"],
     "usb_transfer", 0),
    # --- guardian capabilities (priority 1 -> Gemini with context) ---
    (["drone", "fly", "flight", "fpv", "geofence", "altitude"],
     "drone_control", 1),
    (["mesh", "meshtastic", "radio", "lora", "tracker"],
     "meshtastic", 1),
    (["persona", "mode", "home mode", "pro mode", "business mode", "switch mode"],
     "persona_manager", 1),
    (["security", "intrusion", "alert", "honeypot", "threat", "audit"],
     "security_monitor", 1),
    # --- cluster ops (priority 2) ---
    (["pod", "pods", "kubectl", "cluster", "k3s", "deploy",
      "restart pod", "scale", "namespace", "deployment"],
     "k3s_ops", 2),
    (["health", "status", "system status", "all services", "dashboard"],
     "system_health", 2),
    # --- meta ---
    (["help", "what can you do", "commands", "available"],
     "help", 3),
]


def route_command(text: str, registry=None) -> Tuple[str, float]:
    """
    Return (target_service, confidence).

    Routing priority:
      1. Keyword match (conf 0.8 or 1.0)  -- deterministic, instant
      2. Semantic embedding match          -- covers paraphrases / synonyms
      3. gemini_fallback (conf 0.0)        -- deep-reasoning via Gemini CLI
    """
    lower = text.lower().strip()
    best_svc, best_pri, best_conf = None, 999, 0.0

    for keywords, svc, pri in ROUTES:
        for kw in keywords:
            if kw in lower:
                conf = 1.0 if " " in kw else 0.8
                if pri < best_pri or (pri == best_pri and conf > best_conf):
                    best_svc, best_pri, best_conf = svc, pri, conf
                break          # first keyword hit in this route is enough

    # --- fast path: keyword matched with high confidence ---
    if best_svc and best_conf >= 0.8:
        return (best_svc, best_conf)

    # --- slow path: semantic similarity (only when keywords miss) ---
    if _embedding_model and _service_cap_embeddings:
        sem_target, sem_conf = _semantic_route(text)
        if sem_target != "gemini_fallback":
            logger.info("Semantic route: '%s' -> %s (conf=%.3f)", text[:60], sem_target, sem_conf)
            return (sem_target, sem_conf)

    return ("gemini_fallback", 0.0)


# ---------------------------------------------------------------------------
# Direct k3s service calls (intent-aware)
# ---------------------------------------------------------------------------
async def call_k3s_service(service_name: str, command: str, registry) -> Dict[str, Any]:
    """
    Hit the k3s microservice with an endpoint chosen by intent.
    Falls back to GET / if no specific endpoint matches.
    """
    svc = registry.services.get(service_name)
    if not svc or not svc.url:
        return {"success": False, "message": f"Service '{service_name}' not reachable"}

    lower = command.lower()

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:

            if service_name == "reminder":
                resp = await client.get(f"{svc.url}/")
                if resp.status_code == 200:
                    items = resp.json() if isinstance(resp.json(), list) else []
                    lines = [f"  - {r.get('text','?')} @ {r.get('when','?')}" for r in items]
                    return {"success": True,
                            "message": "Reminders:\n" + ("\n".join(lines) or "  (none)"),
                            "service": service_name}

            elif service_name == "habits":
                resp = await client.get(f"{svc.url}/")
                if resp.status_code == 200:
                    items = resp.json() if isinstance(resp.json(), list) else []
                    lines = [
                        f"  {h.get('name','?')}: {h.get('completions_today',0)}/{h.get('target_count',1)}"
                        for h in items
                    ]
                    return {"success": True,
                            "message": "Habits:\n" + ("\n".join(lines) or "  (none)"),
                            "service": service_name}

            elif service_name == "meds":
                resp = await client.get(f"{svc.url}/")
                if resp.status_code == 200:
                    items = resp.json() if isinstance(resp.json(), list) else []
                    lines = [f"  {m.get('name','?')} - {m.get('schedule','?')}" for m in items]
                    return {"success": True,
                            "message": "Medications:\n" + ("\n".join(lines) or "  (none)"),
                            "service": service_name}

            elif service_name == "financial":
                path = "/budgets" if "budget" in lower else "/summary"
                resp = await client.get(f"{svc.url}{path}")
                if resp.status_code == 200:
                    return {"success": True, "message": str(resp.json()), "service": service_name}

            elif service_name == "library":
                # strip routing keywords to get the real query
                query = lower
                for kw in ["library", "reference", "look up", "define"]:
                    query = query.replace(kw, "")
                query = query.strip() or "help"
                resp = await client.get(f"{svc.url}/search", params={"q": query})
                if resp.status_code == 200:
                    return {"success": True, "message": str(resp.json()), "service": service_name}

            # --- generic fallback: root endpoint ---
            resp = await client.get(f"{svc.url}/")
            return {"success": True, "message": resp.text[:1000], "service": service_name}

    except httpx.ConnectError:
        return {"success": False, "message": f"Cannot connect to {service_name} ({svc.url})"}
    except Exception as e:
        return {"success": False, "message": f"{service_name}: {e}"}


# ---------------------------------------------------------------------------
# Guardian-pod forwarding
# ---------------------------------------------------------------------------
GUARDIAN_API_KEY = "kilo-guardian-internal-2026"


async def call_guardian_service(command: str, registry) -> Dict[str, Any]:
    """
    Forward a command to the guardian pod's /api/chat endpoint.
    The guardian's reasoning engine routes it to the correct plugin internally.
    Falls back gracefully so the caller can try Gemini next.
    """
    svc = registry.services.get("guardian")
    if not svc or not svc.url:
        return {"success": False, "message": "Guardian pod not reachable"}

    headers = {"X-API-Key": GUARDIAN_API_KEY}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{svc.url}/api/chat",
                json={"query": command},
                headers=headers,
            )
            if resp.status_code == 200:
                data = resp.json()
                answer = data.get("answer", data)
                return {"success": True, "message": str(answer), "source": "guardian"}
            return {"success": False, "message": f"Guardian {resp.status_code}: {resp.text[:200]}"}
    except httpx.ConnectError:
        return {"success": False, "message": "Cannot connect to guardian pod"}
    except Exception as e:
        return {"success": False, "message": f"Guardian error: {e}"}


# ---------------------------------------------------------------------------
# Gemini CLI integration
# ---------------------------------------------------------------------------
_NVM  = 'export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"'
_KUBE = 'export KUBECONFIG="$HOME/.kube/config"'

_SYS_CTX = (
    "You are Kilo, an intelligent personal agent with deep access to a k3s cluster "
    "running on a Pop!_OS host.  You operate across 3 layers:\n"
    "  LAYER 1 (Host)   -- system stats: free, top, df, htop.\n"
    "  LAYER 2 (Cluster)-- kubectl / helm.  Namespace: kilo-guardian.\n"
    "  LAYER 3 (Pod Interior) -- kubectl exec to read databases, configs, logs "
    "inside running pods.\n\n"
    "Running pods in kilo-guardian:\n"
    "  kilo-ai-brain(:9004)   kilo-gateway(:8000)    kilo-reminder(:9002)\n"
    "  kilo-habits(:9000)     kilo-meds(:9000)       kilo-financial(:9005)\n"
    "  kilo-library(:9006)    kilo-cam(:9007)        kilo-voice(:9008)\n"
    "  kilo-ml-engine(:9009)  kilo-socketio(:9010)   kilo-usb-transfer(:9010)\n"
    "  kilo-marketing(:80)\n\n"
    "Monitoring: Prometheus (NodePort 30900), Grafana (NodePort 30300).\n"
    "Unified Agent control plane: port 9200.\n"
)


def _run_gemini_sync(prompt: str, timeout: int) -> subprocess.CompletedProcess:
    full = _SYS_CTX + f"\nUser: {prompt}"
    cmd  = f'{_NVM} && {_KUBE} && gemini {shlex.quote(full)} --yolo'
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)


async def call_gemini(prompt: str, timeout: int = 180) -> Dict[str, Any]:
    """
    Run Gemini CLI in a thread so we don't block the event loop.
    Handles quota-exhausted errors gracefully.
    """
    try:
        proc = await asyncio.to_thread(_run_gemini_sync, prompt, timeout)
        if proc.returncode == 0:
            return {"success": True, "message": proc.stdout.strip(), "source": "gemini"}
        if "exhausted" in proc.stderr.lower() or "429" in proc.stderr:
            return {
                "success": False,
                "message": "Gemini quota exhausted -- will retry when quota resets (~10 h cycle).",
                "source": "gemini",
                "retry":  True,
            }
        return {"success": False, "message": proc.stderr[:500], "source": "gemini"}
    except subprocess.TimeoutExpired:
        return {"success": False, "message": "Gemini timed out (3 min limit).", "source": "gemini"}
    except Exception as e:
        return {"success": False, "message": str(e), "source": "gemini"}
