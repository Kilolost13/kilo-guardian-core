from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
import httpx
import os
from sqlmodel import SQLModel, Field, create_engine, Session, select
from typing import Optional
import secrets
import hashlib
import datetime


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
from shared.db import get_engine

# Centralized engine selection
engine = get_engine('GATEWAY_DB_URL', 'sqlite:////data/gateway.db')


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
                    # SHA256 hash - simple comparison
                    h = hashlib.sha256()
                    h.update(header_token.encode())
                    if h.hexdigest() == stored_hash:
                        return True

            return False
    except Exception:
        return False


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
    "meds": os.getenv("MEDS_URL", "http://meds:9001"),
    "reminder": os.getenv("REMINDER_URL", "http://reminder:9002"),
    "habits": os.getenv("HABITS_URL", "http://habits:9003"),
    "ai_brain": os.getenv("AI_BRAIN_URL", "http://ai_brain:9004"),
    "financial": os.getenv("FINANCIAL_URL", "http://financial:9005"),
    "library_of_truth": os.getenv("LIBRARY_OF_TRUTH_URL", "http://library_of_truth:9006"),
    "cam": os.getenv("CAM_URL", "http://cam:9007"),
    "ml": os.getenv("ML_ENGINE_URL", "http://ml_engine:9008"),
    "voice": os.getenv("VOICE_URL", "http://voice:9009"),
}

@app.get("/health")
async def health():
    return {"status": "ok"}

async def _proxy(request: Request, service: str, path: str):
    service_url = SERVICE_URLS.get(service)
    if not service_url:
        raise HTTPException(status_code=404, detail="Service not found")

    url = f"{service_url}/{path}"
    headers = dict(request.headers)
    # The Host header should be the service's host, not the gateway's
    headers["host"] = service_url.split("://")[1].split(":")[0]

    import sys
    async with httpx.AsyncClient() as client:
        try:
            req = client.build_request(
                request.method,
                url,
                headers=headers,
                params=request.query_params,
                content=await request.body()
            )
            resp = await client.send(req, stream=True)
            content_type = resp.headers.get("content-type", "application/json")
            data = await resp.aread()

            # Handle binary responses (images, PDFs, etc.)
            if content_type.startswith("image/") or content_type == "application/pdf":
                from fastapi.responses import Response as FastAPIResponse
                return FastAPIResponse(content=data, media_type=content_type, status_code=resp.status_code)

            # Handle JSON responses
            import json
            try:
                parsed = json.loads(data)
                return JSONResponse(content=parsed, status_code=resp.status_code)
            except Exception as e:
                # Try to decode as text
                try:
                    text_content = data.decode('utf-8')
                    return JSONResponse(content={"raw": text_content}, status_code=resp.status_code)
                except UnicodeDecodeError:
                    # If it's not decodable, return as base64
                    import base64
                    return JSONResponse(content={"raw_base64": base64.b64encode(data).decode()}, status_code=resp.status_code)
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Bad Gateway: {e}")


@app.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_all(request: Request, service: str, path: str):
    return await _proxy(request, service, path)

@app.api_route("/{service}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_root(request: Request, service: str):
    return await _proxy(request, service, "")
