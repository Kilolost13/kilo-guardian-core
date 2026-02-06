#!/usr/bin/env python3
"""
Kilo Unified Agent  --  Operations & Control Plane  v1.0
=========================================================
Single FastAPI entry-point that merges:

  * All k3s microservice management   (from Kilo_Ai_microservice)
  * Guardian-unified capabilities     (reasoning / plugins / personas)
  * Proactive monitoring + notifications
  * Gemini CLI deep-reasoning fallback (when quota available)

Replaces the standalone:
  ~/kilo_agent_api.py      (v4.0 agent API)
  ~/gemini_bridge.py       (Ollama-compat Gemini shim)

Port: 9200  (same as previous kilo_agent_api.py)

Endpoint map
------------
  GET  /                          -- service identity & registered service count
  GET  /health                    -- liveness probe
  GET  /services                  -- full registry dump (layer, caps, health)
  GET  /services/{name}/health    -- single-service health probe
  GET  /services/healthcheck/all  -- parallel health check all k3s services
  POST /agent/command             -- route & execute a natural-language command
  POST /agent/notify              -- push a notification into the queue
  GET  /agent/messages            -- pull recent notifications
  GET  /k3s/pods                  -- parsed pod list
  GET  /k3s/pods/{pod}/logs       -- tail pod logs
  POST /k3s/pods/{pod}/exec       -- exec command inside a pod
  POST /k3s/pods/{pod}/restart    -- delete pod (controller recreates)
  GET  /k3s/services              -- kubectl get svc -o wide
  GET  /k3s/events                -- recent cluster events
  POST /k3s/scale                 -- scale a Deployment
  GET  /k3s/resources             -- kubectl top pods
  POST /monitoring/run            -- trigger one proactive-check cycle
  GET  /monitoring/alerts         -- current open alerts
  GET  /data/monitoring           -- proactive monitor status / stats
  POST /v1/chat/completions       -- OpenAI-compat Gemini bridge
  POST /api/generate              -- Ollama-compat Gemini bridge
"""

import logging
import os
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Dict, List

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from service_registry  import ServiceRegistry, resolve_cluster_ips
from k3s_controller    import (
    get_pods, get_pod_logs, exec_in_pod,
    restart_pod, get_services, get_events,
    scale_deployment, get_resource_usage,
)
from command_router    import route_command, call_k3s_service, call_gemini, call_guardian_service, precompute_service_embeddings
from proactive_monitor import ProactiveMonitor

# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("KiloUnifiedAgent")

# ---------------------------------------------------------------------------
app = FastAPI(title="Kilo Unified Agent", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Singletons
# ---------------------------------------------------------------------------
registry = ServiceRegistry()


class _MQ:
    """Simple in-memory notification queue with TTL filtering."""

    def __init__(self, max_size: int = 200):
        self._q: deque = deque(maxlen=max_size)

    def push(self, msg: Dict):
        msg.setdefault("timestamp", datetime.now().isoformat())
        self._q.append(msg)

    def recent(self, count: int = 20, since_minutes: int = 60) -> List[Dict]:
        cutoff = datetime.now() - timedelta(minutes=since_minutes)
        out = []
        for m in self._q:
            try:
                if datetime.fromisoformat(m["timestamp"]) >= cutoff:
                    out.append(m)
            except (KeyError, ValueError):
                out.append(m)
        return out[-count:]


mq = _MQ()


async def _on_alert(alert: Dict):
    """Callback: proactive monitor pushes here."""
    mq.push(alert)


monitor = ProactiveMonitor(registry=registry, notify=_on_alert)



# ---------------------------------------------------------------------------
# Startup: resolve ClusterIPs so host-mode service calls work
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def on_startup():
    await resolve_cluster_ips(registry)
    precompute_service_embeddings(registry)
    logger.info("Service URLs resolved. Registry ready.")

# ---------------------------------------------------------------------------
# Pydantic request bodies
# ---------------------------------------------------------------------------

class CommandReq(BaseModel):
    command: str
    params: Dict[str, Any] = {}


class NotifyReq(BaseModel):
    type:     str            = "notification"
    content:  str
    priority: str            = "normal"
    metadata: Dict[str, Any] = {}


class ExecReq(BaseModel):
    command: List[str]


class ScaleReq(BaseModel):
    deployment: str
    replicas:   int


# ---------------------------------------------------------------------------
# Root / health
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    return {
        "service":             "Kilo Unified Agent",
        "version":             "1.0.0",
        "status":              "running",
        "registered_services": len(registry.services),
        "layers":              ["k3s", "guardian", "host"],
    }


@app.get("/health")
async def health():
    return {"status": "ok", "ts": datetime.now().isoformat()}


# ---------------------------------------------------------------------------
# Service registry
# ---------------------------------------------------------------------------
@app.get("/services")
async def list_services():
    return registry.get_status()


@app.get("/services/{name}/health")
async def svc_health(name: str):
    ok = await registry.health_check(name)
    return {"service": name, "healthy": ok}


@app.get("/services/healthcheck/all")
async def svc_health_all():
    res = await registry.health_check_all()
    return {
        "results":      res,
        "healthy_count": sum(res.values()),
        "total":        len(res),
    }


# ---------------------------------------------------------------------------
# K3s cluster operations
# ---------------------------------------------------------------------------
@app.get("/k3s/pods")
async def kube_pods():
    return await get_pods()


@app.get("/k3s/pods/{pod}/logs")
async def kube_logs(pod: str, tail: int = 50):
    return await get_pod_logs(pod, tail=tail)


@app.post("/k3s/pods/{pod}/exec")
async def kube_exec(pod: str, req: ExecReq):
    return await exec_in_pod(pod, req.command)


@app.post("/k3s/pods/{pod}/restart")
async def kube_restart(pod: str):
    return await restart_pod(pod)


@app.get("/k3s/services")
async def kube_services():
    return await get_services()


@app.get("/k3s/events")
async def kube_events():
    return await get_events()


@app.post("/k3s/scale")
async def kube_scale(req: ScaleReq):
    return await scale_deployment(req.deployment, req.replicas)


@app.get("/k3s/resources")
async def kube_resources():
    return await get_resource_usage()


# ---------------------------------------------------------------------------
# Agent command routing
# ---------------------------------------------------------------------------
@app.post("/agent/command")
async def agent_command(req: CommandReq):
    """
    Route flow:
      keyword match -> direct k3s service call  (fast path)
                    -> guardian target          -> Gemini with context
                    -> no match / call failed   -> Gemini fallback
    """
    target, conf = route_command(req.command, registry)
    logger.info("route: '%s' -> %s (conf=%.2f)", req.command[:60], target, conf)

    # --- local cluster ops ---
    if target == "k3s_ops":
        return await _k3s_command(req.command)

    # --- system health summary ---
    if target == "system_health":
        res = await registry.health_check_all()
        unhealthy = [n for n, ok in res.items() if not ok]
        return {
            "success":   True,
            "message":   f"{sum(res.values())}/{len(res)} services healthy",
            "unhealthy": unhealthy,
        }

    # --- help ---
    if target == "help":
        return {"success": True, "message": _HELP}

    # --- unified k3s + guardian routing ---
    is_guardian = target in ("guardian", "reasoning-engine", "plugin-manager", "persona-manager", 
                            "drone-control", "meshtastic", "security-monitor")
    
    if is_guardian:
        result = await call_guardian_service(req.command, registry)
    else:
        result = await call_k3s_service(target, req.command, registry)

    if result.get("success"):
        return result

    # --- catch-all: Gemini deep-reasoning ---
    return await call_gemini(req.command)


async def _k3s_command(cmd: str) -> Dict[str, Any]:
    """Parse simple cluster-operation commands from natural language."""
    lower = cmd.lower()

    if "log" in lower:
        for word in lower.split():
            if word.startswith("kilo-"):
                return await get_pod_logs(word)
        return {"success": False, "message": "Specify pod name: 'logs kilo-<name>'"}

    if "restart" in lower:
        for word in lower.split():
            if word.startswith("kilo-"):
                return await restart_pod(word)
        return {"success": False, "message": "Specify pod name: 'restart kilo-<name>'"}

    if "event" in lower:
        return await get_events()

    if "resource" in lower or "top" in lower:
        return await get_resource_usage()

    # default: list pods
    return await get_pods()


# ---------------------------------------------------------------------------
# Notifications / message queue
# ---------------------------------------------------------------------------
@app.post("/agent/notify")
async def notify(req: NotifyReq):
    mq.push({
        "type":     req.type,
        "content":  req.content,
        "priority": req.priority,
        "metadata": req.metadata,
    })
    return {"status": "ok"}


@app.get("/agent/messages")
async def messages(since_minutes: int = 60, count: int = 20):
    return {"messages": mq.recent(count=count, since_minutes=since_minutes)}

# Alias /messages to /agent/messages for frontend compatibility
@app.get("/messages")
async def messages_alias(since_minutes: int = 60, count: int = 20):
    return await messages(since_minutes=since_minutes, count=count)


# ---------------------------------------------------------------------------
# Proactive monitoring
# ---------------------------------------------------------------------------
@app.post("/monitoring/run")
async def mon_run():
    alerts = await monitor.run_checks()
    return {"alerts": alerts, "count": len(alerts)}


@app.get("/monitoring/alerts")
async def mon_alerts():
    return {"alerts": [m for m in mq.recent(since_minutes=120) if m.get("severity")]}


@app.get("/data/monitoring")
async def mon_data():
    # Return monitor status and summary stats
    res = await monitor.get_status()
    return res


# ---------------------------------------------------------------------------
# Gemini bridge  (drop-in replacement for ~/gemini_bridge.py)
#   POST /v1/chat/completions   -- OpenAI format
#   POST /api/generate          -- Ollama format
# ---------------------------------------------------------------------------
async def _gemini_bridge(request: Request):
    body = await request.json()
    if "messages" in body:
        prompt = (body["messages"] or [{}])[-1].get("content", "")
    else:
        prompt = body.get("prompt", "Hello")

    result = await call_gemini(prompt)
    text   = result.get("message", "")
    return {
        "choices":  [{"message": {"role": "assistant", "content": text}}],
        "response": text,       # Ollama compat
    }


app.add_api_route("/v1/chat/completions", _gemini_bridge, methods=["POST"])
app.add_api_route("/api/generate",        _gemini_bridge, methods=["POST"])


# ---------------------------------------------------------------------------
# Help text
# ---------------------------------------------------------------------------
_HELP = """\
=== Kilo Unified Agent  v1.0 ===
Commands are routed automatically by keyword.  Examples:

  reminders            list / check reminders
  habits               habit tracking & streaks
  meds                 medication status & adherence
  budget / spending    financial overview & alerts
  camera               camera & monitoring status
  voice                voice / speech commands
  library              knowledge-base search
  pods / k3s           cluster management (list, logs, restart, scale)
  health / status      full system health check
  drone                drone control  (guardian)
  mesh                 Meshtastic mesh tracking
  persona / mode       switch persona (home / pro / business)
  security             security & intrusion alerts

Anything not matched above is forwarded to Gemini for deep reasoning
across host, cluster, and pod-interior layers.
"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("KILO_AGENT_PORT", "9200"))
    logger.info("Starting Kilo Unified Agent on port %d", port)
    logger.info("Registered services: %s", list(registry.services.keys()))
    uvicorn.run(app, host="0.0.0.0", port=port)