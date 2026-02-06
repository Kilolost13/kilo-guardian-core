import importlib
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from kilo_v2.server_core import (
    diagnostics,
    get_error_stats,
    get_recent_errors,
    health_check,
    system_metrics,
)

router = APIRouter()
logger = logging.getLogger("kilo_v2.routers.system")


@router.get("/api/system/health")
def system_health():
    return health_check()


@router.get("/api/system/metrics")
def system_metrics(limit: int = 60):
    return system_metrics(limit=limit)


@router.get("/api/system/errors/stats")
def system_error_stats():
    return get_error_stats()


@router.get("/api/system/errors/recent")
def system_errors_recent(limit: int = 50):
    return get_recent_errors(limit=limit)


# Note: system update endpoints have been moved to `routers.update`.


@router.get("/api/diagnostics")
def diagnostics():
    return diagnostics()


@router.get("/api/model/status")
def model_status():
    try:
        from kilo_v2.model_manager import get_model_status

        return get_model_status()
    except ImportError as e:
        logger.error(f"Failed to import model_manager: {e}")
        raise HTTPException(status_code=500, detail="ModelManager not available")
    except Exception as e:
        logger.error(f"Error getting model status: {e}")
        raise HTTPException(status_code=500, detail="Error getting model status")
