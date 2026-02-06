from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from kilo_v2.auth_manager import AuthManager
from kilo_v2.config import ENVIRONMENT, KILO_API_KEY
from kilo_v2.startup_guard import startup_guard
from kilo_v2.stripe_manager import StripeManager

_auth_manager = None
_stripe_manager = None

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _ensure_auth_manager():
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager(ENVIRONMENT)
    return _auth_manager


def _ensure_stripe_manager():
    global _stripe_manager
    if _stripe_manager is None:
        _stripe_manager = StripeManager()
    return _stripe_manager


def get_current_user():
    # Placeholder for dependency injection, should be replaced with actual logic
    # For now, raise 401 to indicate not implemented
    raise HTTPException(status_code=401, detail="Not implemented: get_current_user")


async def get_api_key(api_key: str = Depends(api_key_header)):
    if KILO_API_KEY is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key not configured on the server.",
        )
    if api_key is None or api_key != KILO_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )
    return api_key
