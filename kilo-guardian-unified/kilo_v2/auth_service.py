import logging
from datetime import datetime

from fastapi import HTTPException, Request, Response

from kilo_v2.dependencies import _ensure_auth_manager, _ensure_stripe_manager

logger = logging.getLogger(__name__)


async def register_user(request, response):
    try:
        stripe_customer_id = None
        if _ensure_stripe_manager() and _ensure_stripe_manager().enabled:
            stripe_customer_id = _ensure_stripe_manager().create_customer(
                email=request.email,
                name=request.full_name,
                metadata={"signup_date": datetime.now().isoformat()},
            )
        result = _ensure_auth_manager().create_user(
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            stripe_customer_id=stripe_customer_id,
        )
        if not result["success"]:
            raise HTTPException(
                status_code=400, detail=result.get("error", "Registration failed")
            )
        logger.info(f"✅ New user registered: {request.email}")
        return {
            "success": True,
            "user_id": result["user_id"],
            "message": "Account created successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def login_user(request, req, response):
    try:
        ip_address = req.client.host if req.client else "unknown"
        user_agent = req.headers.get("user-agent", "unknown")
        result = _ensure_auth_manager().authenticate(
            email=request.email,
            password=request.password,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        if not result["success"]:
            raise HTTPException(
                status_code=401, detail=result.get("error", "Authentication failed")
            )
        response.set_cookie(
            key="bastion_session",
            value=result["session_token"],
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=30 * 24 * 60 * 60,
        )
        logger.info(f"✅ User logged in: {request.email}")
        return {"success": True, "user": result["user"], "message": "Login successful"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def logout_user(response, user):
    try:
        session_token = user.get("session_token")
        if session_token:
            _ensure_auth_manager().logout(session_token)
        response.delete_cookie("bastion_session")
        logger.info(f"✅ User logged out: {user.get('email')}")
        return {"success": True, "message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Logout error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def get_me(user):
    return {"user": user}


async def link_appliance(request, user):
    try:
        result = _ensure_auth_manager().link_appliance(
            user_id=user["id"],
            hardware_id=request.hardware_id,
            device_name=request.device_name,
        )
        if not result["success"]:
            raise HTTPException(
                status_code=400, detail=result.get("error", "Failed to link appliance")
            )
        logger.info(f"✅ Appliance linked: {request.device_name} to {user['email']}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Link appliance error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def get_appliances(user):
    try:
        appliances = _ensure_auth_manager().get_user_appliances(user["id"])
        return {"appliances": appliances}
    except Exception as e:
        logger.error(f"Get appliances error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def get_purchases(user):
    try:
        purchases = _ensure_auth_manager().get_user_purchases(user["id"])
        return {"purchases": purchases}
    except Exception as e:
        logger.error(f"Get purchases error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
