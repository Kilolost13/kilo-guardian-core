from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from starlette.responses import JSONResponse
import httpx
import os
from sqlmodel import SQLModel, Field, create_engine, Session, select
from typing import Optional
import secrets
import hashlib
import datetime
import time
import asyncio
import logging
logger = logging.getLogger(__name__)


app = FastAPI(title="Kilos API Gateway")

# Add CORS middleware to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# admin tokens DB (simple centralized token store for admin UI/automation)
DB_URL = os.getenv("GATEWAY_DB_URL", "sqlite:////tmp/gateway.db")
engine = create_engine(DB_URL, echo=False)


class AdminToken(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    label: Optional[str] = None
    token_hash: str
    revoked: bool = False
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


@app.on_event("startup")
def startup():
    try:
        SQLModel.metadata.create_all(engine)
    except Exception:
        pass


def _hash_token(token: str) -> str:
    """
    Hash a token using bcrypt for secure storage.
    Falls back to SHA256 if bcrypt unavailable (for backward compatibility).
    """
    try:
        import bcrypt
        # Use bcrypt for secure password hashing (with salt)
        salt = bcrypt.gensalt(rounds=12)  # 12 rounds is good balance of security/performance
        token_hash = bcrypt.hashpw(token.encode(), salt)
        return token_hash.decode('ascii')
    except ImportError:
        # Fallback to SHA256 if bcrypt not installed
        # NOTE: SHA256 without salt is less secure, install bcrypt in production
        import logging
        logging.warning("bcrypt not installed, using SHA256 (less secure). Install: pip install bcrypt")
        h = hashlib.sha256()
        h.update(token.encode())
        return h.hexdigest()


def _validate_header_token(header_token: Optional[str]) -> bool:
    """
    Validate a token against stored hashes.
    Supports both bcrypt and SHA256 hashes for backward compatibility.
    """
    if not header_token:
        return False
    try:
        # Pre-compute SHA256 hash once for efficiency
        sha256_hash = hashlib.sha256(header_token.encode()).hexdigest()
        
        with Session(engine) as sess:
            # Get all non-revoked tokens
            q = sess.exec(select(AdminToken).where(AdminToken.revoked == False))

            for token_record in q.all():
                stored_hash = token_record.token_hash

                # Check if it's a bcrypt hash (starts with $2b$)
                if stored_hash.startswith('$2b$'):
                    try:
                        import bcrypt
                        if bcrypt.checkpw(header_token.encode(), stored_hash.encode('ascii')):
                            return True
                    except ImportError:
                        pass
                else:
                    # SHA256 hash - simple comparison (use pre-computed hash)
                    if sha256_hash == stored_hash:
                        return True

            return False
    except Exception:
        return False


def _is_admin_request(request: Request) -> bool:
    """Return True if the request contains a valid admin credential.

    Accepts either a stored admin token (X-Admin-Token), or the bootstrap
    LIBRARY_ADMIN_KEY for environments still using that static key.
    """
    header = request.headers.get('x-admin-token')
    library_admin_key = os.environ.get('LIBRARY_ADMIN_KEY')

    if header and library_admin_key and header.strip() == library_admin_key.strip():
        return True

    auth_header = request.headers.get('authorization')
    if auth_header and library_admin_key and library_admin_key in auth_header:
        return True

    return _validate_header_token(header)


@app.post("/admin/tokens")
async def create_admin_token(request: Request):
    """Create a new admin token. If this is the first token ever created, allow creation without auth.
    Otherwise require X-Admin-Token header with a valid token."""
    header = request.headers.get("x-admin-token")
    # allow first token creation if DB empty
    with Session(engine) as sess:
        existing = sess.exec(select(AdminToken)).all()
        count = len(existing)
    if count > 0 and not _validate_header_token(header):
        raise HTTPException(status_code=401, detail="Unauthorized")

    new_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(new_token)
    at = AdminToken(label="generated", token_hash=token_hash)
    with Session(engine) as sess:
        sess.add(at)
        sess.commit()
        sess.refresh(at)

    return {"id": at.id, "token": new_token}


@app.get("/admin/tokens")
async def list_admin_tokens(request: Request):
    header = request.headers.get("x-admin-token")
    if not _validate_header_token(header):
        raise HTTPException(status_code=401, detail="Unauthorized")
    out = []
    with Session(engine) as sess:
        rows = sess.exec(select(AdminToken).order_by(AdminToken.created_at.desc())).all()
        for r in rows:
            out.append({"id": r.id, "label": r.label, "revoked": bool(r.revoked), "created_at": str(r.created_at)})
    return {"tokens": out}


@app.post("/admin/tokens/{token_id}/revoke")
async def revoke_admin_token(token_id: int, request: Request):
    header = request.headers.get("x-admin-token")
    if not _validate_header_token(header):
        raise HTTPException(status_code=401, detail="Unauthorized")
    with Session(engine) as sess:
        row = sess.get(AdminToken, token_id)
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
        row.revoked = True
        sess.add(row)
        sess.commit()
    return {"status": "ok"}


@app.post("/admin/validate")
async def validate_admin_token(payload: dict = None, request: Request = None):
    # token may be supplied via header or body {"token": "..."}
    header = request.headers.get("x-admin-token") if request is not None else None
    body_token = None
    if payload and isinstance(payload, dict):
        body_token = payload.get("token")
    token = header or body_token
    if not token or not _validate_header_token(token):
        raise HTTPException(status_code=401, detail="Invalid")
    return {"valid": True}

# Health check endpoint (alias for /health)
@app.get("/status")
async def status():
    return {"status": "ok"}

SERVICE_URLS = {
    "meds": os.getenv("MEDS_URL", "http://docker_meds_1:9001"),
    "reminder": os.getenv("REMINDER_URL", "http://docker_reminder_1:9002"),
    "reminders": os.getenv("REMINDER_URL", "http://docker_reminder_1:9002"),  # Alias for plural
    "habits": os.getenv("HABITS_URL", "http://docker_habits_1:9003"),
    "ai_brain": os.getenv("AI_BRAIN_URL", "http://docker_ai_brain_1:9004"),
    "financial": os.getenv("FINANCIAL_URL", "http://docker_financial_1:9005"),
    "library_of_truth": os.getenv("LIBRARY_OF_TRUTH_URL", "http://docker_library_of_truth_1:9006"),
    "cam": os.getenv("CAM_URL", "http://docker_cam_1:9007"),
    "ml": os.getenv("ML_ENGINE_URL", "http://docker_ml_engine_1:9008"),
    "voice": os.getenv("VOICE_URL", "http://docker_voice_1:9009"),
    "usb": os.getenv("USB_TRANSFER_URL", "http://docker_usb_transfer_1:8006"),
}

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get('/admin/ai_brain/metrics')
async def admin_ai_brain_metrics(request: Request):
    """Proxy ai_brain metrics to admin users only.

    Validates X-Admin-Token using the gateway's token store. Returns raw Prometheus metrics text.
    """
    if not _is_admin_request(request):
        raise HTTPException(status_code=401, detail='Unauthorized')

    service_url = SERVICE_URLS.get('ai_brain')
    if not service_url:
        raise HTTPException(status_code=404, detail='Service not found')

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"{service_url.rstrip('/')}/metrics", headers={"X-Admin-Token": header})
            return Response(content=resp.content, media_type=resp.headers.get('content-type','text/plain'), status_code=resp.status_code)
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=str(e))


@app.get("/admin/status")
async def admin_status():
    """Aggregate health status from all backend services"""
    import httpx
    from datetime import datetime

    results = {}
    async with httpx.AsyncClient(timeout=2.0) as client:
        for name, service_url in SERVICE_URLS.items():
            svc_entry = {"ok": False, "checked_at": datetime.utcnow().isoformat(), "message": None}
            health_url = f"{service_url.rstrip('/')}/health"
            try:
                resp = await client.get(health_url)
                svc_entry["ok"] = resp.status_code < 400
                try:
                    svc_entry["message"] = resp.json()
                except Exception:
                    svc_entry["message"] = resp.text
            except Exception as e:
                svc_entry["message"] = str(e)

            results[name] = svc_entry

    # Provide top-level boolean flags for backward compatibility
    out = {}
    all_ok = True
    for k, v in results.items():
        out[k] = bool(v.get("ok", False))
        if not v.get("ok", False):
            all_ok = False

    # Backwards-compatible aliases expected by frontend
    out["gateway"] = True
    out["reminders"] = out.get("reminder", out.get("reminders", False))
    out["finance"] = out.get("financial", out.get("finance", False))

    out["status"] = "online" if all_ok else "degraded"
    out["checked_at"] = datetime.utcnow().isoformat()
    out["details"] = results

    return out


def _parse_prometheus_metrics(text: str, service_label: str):
    """Lightweight Prometheus exposition parser for a small metric subset.

    Extracts circuit-breaker related metrics and ignores the rest to keep
    latency minimal and avoid pulling in heavy parsers.
    """
    target_metrics = {
        "cb_open": None,
        "cb_open_until": None,
        "cb_failures_total": None,
        "cb_skips_total": None,
        "cb_success_total": None,
    }

    if not text:
        return target_metrics

    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        for metric_name in list(target_metrics.keys()):
            if not line.startswith(metric_name):
                continue

            # Ensure we only capture the metric for this service label if present
            if "{" in line and f'service="{service_label}"' not in line:
                continue

            parts = line.split()
            if len(parts) < 2:
                continue
            try:
                target_metrics[metric_name] = float(parts[-1])
            except ValueError:
                continue
    return target_metrics


@app.get("/admin/metrics/summary")
async def admin_metrics_summary(request: Request):
    """Summarize Prometheus circuit-breaker metrics from core services.

    Requires admin auth (X-Admin-Token or LIBRARY_ADMIN_KEY). Returns a small
    JSON payload so the admin UI can render a status card without parsing the
    entire exposition format.
    """
    if not _is_admin_request(request):
        raise HTTPException(status_code=401, detail="Unauthorized")

    import httpx
    from datetime import datetime

    services_to_query = {
        "meds": SERVICE_URLS.get("meds"),
        "reminder": SERVICE_URLS.get("reminder"),
        "habits": SERVICE_URLS.get("habits"),
    }

    results = {}
    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, base_url in services_to_query.items():
            entry = {"ok": False, "fetched_at": datetime.utcnow().isoformat(), "metrics": None, "message": None}
            if not base_url:
                entry["message"] = "no service url"
                results[name] = entry
                continue

            metrics_url = f"{base_url.rstrip('/')}/metrics"
            try:
                resp = await client.get(metrics_url)
                entry["ok"] = resp.status_code < 400
                if resp.status_code < 400:
                    entry["metrics"] = _parse_prometheus_metrics(resp.text, service_label=name)
                else:
                    entry["message"] = f"status {resp.status_code}"
            except Exception as e:
                entry["message"] = str(e)
            results[name] = entry

    return {"services": results, "generated_at": datetime.utcnow().isoformat()}

async def _proxy(request: Request, service: str, path: str):
    service_url = SERVICE_URLS.get(service)
    if not service_url:
        raise HTTPException(status_code=404, detail="Service not found")

    url = f"{service_url}/{path}"
    headers = dict(request.headers)
    # The Host header should be the service's host, not the gateway's
    headers["host"] = service_url.split("://")[1].split(":")[0]

    # Remove content-length as we may be streaming
    headers.pop("content-length", None)

    # Use a slightly more robust request with timing and retries for slow endpoints
    retries = 2
    backoff = 0.5
    async with httpx.AsyncClient(timeout=120.0) as client:  # Increased timeout for OCR/LLM processing
        last_exc = None
        for attempt in range(1, retries + 1):
            start_ts = time.time()
            try:
                # Check if this is a multipart/form-data request (file upload)
                content_type = request.headers.get("content-type", "")

                if "multipart/form-data" in content_type:
                    # For multipart, stream the body directly to preserve boundaries
                    req = client.build_request(
                        request.method,
                        url,
                        headers=headers,
                        params=request.query_params,
                        content=request.stream()  # Stream instead of body()
                    )
                else:
                    # For regular requests, use body
                    req = client.build_request(
                        request.method,
                        url,
                        headers=headers,
                        params=request.query_params,
                        content=await request.body()
                    )
                resp = await client.send(req, stream=True)
                elapsed = time.time() - start_ts

                # Log slow responses for ai_brain specifically
                if service == 'ai_brain' and elapsed > 3.0:
                    logger.warning(f"ai_brain slow response: {request.method} {path} took {elapsed:.2f}s (attempt {attempt})")

                content_type = resp.headers.get("content-type", "application/json")
                data = await resp.aread()

                # Handle binary responses (images, PDFs, etc.)
                if content_type.startswith("image/") or content_type == "application/pdf":
                    from fastapi.responses import Response as FastAPIResponse
                    logger.info(f"Proxy OK: {request.method} {url} -> {resp.status_code} in {elapsed:.2f}s")
                    return FastAPIResponse(content=data, media_type=content_type, status_code=resp.status_code)

                # Handle JSON responses
                import json
                try:
                    parsed = json.loads(data)
                    logger.info(f"Proxy OK: {request.method} {url} -> {resp.status_code} in {elapsed:.2f}s")
                    return JSONResponse(content=parsed, status_code=resp.status_code)
                except Exception:
                    try:
                        text_content = data.decode('utf-8')
                        logger.info(f"Proxy OK (text): {request.method} {url} -> {resp.status_code} in {elapsed:.2f}s")
                        return JSONResponse(content={"raw": text_content}, status_code=resp.status_code)
                    except UnicodeDecodeError:
                        import base64
                        logger.info(f"Proxy OK (binary): {request.method} {url} -> {resp.status_code} in {elapsed:.2f}s")
                        return JSONResponse(content={"raw_base64": base64.b64encode(data).decode()}, status_code=resp.status_code)

            except httpx.RequestError as e:
                elapsed = time.time() - start_ts
                logger.error(f"Proxy request error to {service} {url} (attempt {attempt}) after {elapsed:.2f}s: {e}")
                last_exc = e
                if attempt < retries:
                    await client.aclose()
                    await asyncio.sleep(backoff * attempt)
                    continue
                else:
                    raise HTTPException(status_code=502, detail=f"Bad Gateway: {e}")


@app.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_all(request: Request, service: str, path: str):
    return await _proxy(request, service, path)

@app.api_route("/{service}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_root(request: Request, service: str):
    return await _proxy(request, service, "")

# Socket.IO support for real-time updates (optional dependency)
try:
    import socketio
except ImportError:  # pragma: no cover - optional path for minimal installs
    socketio = None
    logger.warning("python-socketio not installed; skipping real-time updates")

if socketio:
    # Create Socket.IO server
    sio = socketio.AsyncServer(
        async_mode='asgi',
        cors_allowed_origins='*',
        logger=False,
        engineio_logger=False
    )

    # Wrap with ASGI app
    socket_app = socketio.ASGIApp(
        socketio_server=sio,
        socketio_path='socket.io'
    )

    # Mount Socket.IO app
    app.mount('/socket.io', socket_app)

    @sio.event
    async def connect(sid, environ):
        logger.info(f"Socket.IO client connected: {sid}")
        await sio.emit('connected', {'status': 'ok'}, room=sid)

    @sio.event
    async def disconnect(sid):
        logger.info(f"Socket.IO client disconnected: {sid}")

    @sio.event
    async def ping(sid, data):
        """Handle ping from client"""
        await sio.emit('pong', {'timestamp': time.time()}, room=sid)
