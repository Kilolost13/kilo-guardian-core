import os
import httpx

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://gateway:8000")


def validate_token(token: str) -> bool:
    """Call the gateway /admin/validate endpoint to check a token."""
    if not token:
        return False
    try:
        url = f"{GATEWAY_URL}/admin/validate"
        resp = httpx.post(url, json={"token": token}, timeout=3.0)
        return resp.status_code == 200
    except Exception:
        return False
