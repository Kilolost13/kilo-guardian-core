import asyncio
import importlib
import logging
from typing import Any  # noqa: F401

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()
logger = logging.getLogger("kilo_v2.routers.update")


def _get_core():
    return importlib.import_module("kilo_v2.server_core")


async def _enforce_core_dependencies(request: Request, core):
    dep_mod = importlib.import_module("kilo_v2.dependencies")
    override_get_api = request.app.dependency_overrides.get(dep_mod.get_api_key, None)
    if override_get_api:
        if asyncio.iscoroutinefunction(override_get_api):
            await override_get_api()
        else:
            override_get_api()
    else:
        api_key_value = request.headers.get("X-API-Key")
        await dep_mod.get_api_key(api_key_value)
    dep_mod.startup_guard(request)


@router.get("/api/system/update/check")
async def check_for_updates(request: Request):
    core = _get_core()
    await _enforce_core_dependencies(request, core)
    from kilo_v2.update_service import check_for_updates as _check

    try:
        result = _check()
        return result
    except Exception as e:
        logger.error(f"Update check failed in router: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/system/update/download")
async def download_update(request: Request):
    core = _get_core()
    await _enforce_core_dependencies(request, core)
    from kilo_v2.update_service import download_update as _download

    try:
        result = _download()
        return result
    except Exception as e:
        logger.error(f"Update download failed in router: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/system/update/apply")
async def apply_update(request: Request, iso_path: str):
    core = _get_core()
    await _enforce_core_dependencies(request, core)
    from kilo_v2.update_service import apply_update as _apply

    try:
        result = _apply(iso_path)
        return result
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="ISO file not found")
    except Exception as e:
        logger.error(f"Update apply failed in router: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/system/update/rollback")
async def rollback_update(request: Request):
    core = _get_core()
    await _enforce_core_dependencies(request, core)
    from kilo_v2.update_service import rollback_update as _rollback

    try:
        result = _rollback()
        return result
    except Exception as e:
        logger.error(f"Rollback failed in router: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/system/generations")
async def list_generations(request: Request):
    core = _get_core()
    await _enforce_core_dependencies(request, core)
    from kilo_v2.update_service import list_generations as _list_gens

    try:
        return _list_gens()
    except Exception as e:
        logger.error(f"List generations failed in router: {e}")
        raise HTTPException(status_code=500, detail=str(e))
