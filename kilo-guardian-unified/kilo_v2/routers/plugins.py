import asyncio
import importlib
import logging

from fastapi import APIRouter, Request

from kilo_v2.server_core import _ensure_healer, _ensure_pm, toggle_plugin

router = APIRouter()
logger = logging.getLogger("kilo_v2.routers.plugins")


async def _enforce_core_dependencies(request: Request):
    """Ensure API key header and startup guard (honor overrides)."""
    dep_mod = importlib.import_module("kilo_v2.dependencies")
    override_get_api = request.app.dependency_overrides.get(dep_mod.get_api_key, None)
    if override_get_api:
        # If the override is async, await it; else, call directly.
        if asyncio.iscoroutinefunction(override_get_api):
            await override_get_api()
        else:
            override_get_api()
    else:
        # Call get_api_key explicitly with the header value to mimic
        # FastAPI dependency injection. This avoids bypassing the header
        # check when calling the function directly (no DI runtime).
        api_key_value = request.headers.get("X-API-Key")
        await dep_mod.get_api_key(api_key_value)
    # startup guard is not async
    dep_mod.startup_guard(request)


@router.get("/api/plugins")
async def list_plugins(request: Request):
    await _enforce_core_dependencies(request)
    pm_ = _ensure_pm()
    from kilo_v2.plugin_service import list_plugins as _list_plugins

    return _list_plugins(pm_)


@router.post("/api/plugins/restart")
async def restart_plugin(request: Request, req=None):
    await _enforce_core_dependencies(request)
    pm_ = _ensure_pm()
    from kilo_v2.plugin_service import restart_plugin as _restart

    return _restart(pm_, req)


@router.post("/api/plugins/execute")
async def execute_plugin(request: Request, req=None):
    await _enforce_core_dependencies(request)
    pm_ = _ensure_pm()
    healer_ = _ensure_healer()
    from kilo_v2.plugin_service import execute_plugin as _execute

    return _execute(pm_, healer_, req)


@router.get("/api/plugins/health")
async def plugins_health(request: Request):
    await _enforce_core_dependencies(request)
    pm_ = _ensure_pm()
    sandbox_manager = None
    try:
        from plugin_sandbox import get_sandbox_manager

        sandbox_manager = get_sandbox_manager()
    except Exception:
        sandbox_manager = None

    from kilo_v2.plugin_service import get_plugins_health as _get_health

    return _get_health(pm_, sandbox_manager)


@router.post("/api/plugins/{plugin_name}/toggle")
async def toggle_plugin(request: Request, plugin_name: str):
    await _enforce_core_dependencies(request)
    try:
        return toggle_plugin(plugin_name)
    except Exception as e:
        logger.error(f"Failed to toggle plugin {plugin_name}: {e}")
        raise
