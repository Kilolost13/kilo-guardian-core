import logging

from kilo_v2.server_core import _add_hmac_key, _ensure_submissions_dir, _load_hmac_keys

router = APIRouter()
logger = logging.getLogger("kilo_v2.routers.admin")


async def _enforce_core_dependencies(request: Request, core):
    dep_mod = importlib.import_module("kilo_v2.dependencies")
    override_get_api = request.app.dependency_overrides.get(dep_mod.get_api_key, None)
    if override_get_api:
        if hasattr(override_get_api, "__call__"):
            res = override_get_api()
            if hasattr(res, "__await__"):
                await res
    else:
        api_key_value = request.headers.get("X-API-Key")
        await dep_mod.get_api_key(api_key_value)
    dep_mod.startup_guard(request)


@router.get("/api/submissions/list")
async def list_submissions(request: Request, limit: int = 50):
    core = importlib.import_module("kilo_v2.server_core")
    await _enforce_core_dependencies(request, core)
    submissions_dir = _ensure_submissions_dir()
    from kilo_v2.admin_service import list_submissions as _list

    return _list(submissions_dir, limit=limit)


@router.get("/api/submissions/verify")
async def verify_submissions(request: Request):
    core = importlib.import_module("kilo_v2.server_core")
    await _enforce_core_dependencies(request, core)
    submissions_dir = _ensure_submissions_dir()
    from kilo_v2.admin_service import verify_submissions as _verify

    return _verify(submissions_dir, _load_hmac_keys)


@router.post("/api/hmac/rotate")
async def hmac_rotate(request: Request, req: Any):
    core = importlib.import_module("kilo_v2.server_core")
    await _enforce_core_dependencies(request, core)
    submissions_dir = _ensure_submissions_dir()
    from kilo_v2.admin_service import hmac_rotate as _rotate

    return _rotate(_add_hmac_key, submissions_dir, req)


@router.get("/api/hmac/keys")
async def hmac_keys(request: Request):
    core = importlib.import_module("kilo_v2.server_core")
    await _enforce_core_dependencies(request, core)
    from kilo_v2.admin_service import hmac_keys as _keys

    return _keys(_load_hmac_keys)
