import importlib
import sys
from pathlib import Path
import time
import os
from fastapi.testclient import TestClient
from sqlmodel import SQLModel
import pytest


def reload_module(module_path, env_overrides=None):
    repo_root = str(Path(__file__).resolve().parents[3])
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    try:
        SQLModel.metadata.clear()
    except Exception:
        pass
    if env_overrides:
        for k, v in env_overrides.items():
            os.environ[k] = v
    if module_path in sys.modules:
        del sys.modules[module_path]
    return importlib.import_module(module_path)


@pytest.mark.skipif(os.environ.get('RUN_INTEGRATION') != '1', reason="Integration test - set RUN_INTEGRATION=1 to run")
def test_gateway_financial_and_library_admin_flow():
    gw_db = f"sqlite:////tmp/gateway_it_{os.getpid()}_{int(time.time()*1000)}.db"
    fin_db = f"sqlite:////tmp/financial_it_{os.getpid()}_{int(time.time()*1000)}.db"
    lib_db = f"sqlite:////tmp/library_it_{os.getpid()}_{int(time.time()*1000)}.db"

    # start gateway
    gm = reload_module('microservice.gateway.main', {'GATEWAY_DB_URL': gw_db})
    try:
        SQLModel.metadata.create_all(gm.engine)
    except Exception:
        pass
    gw_client = TestClient(gm.app)

    # create admin token
    r = gw_client.post('/admin/tokens')
    assert r.status_code == 200
    token = r.json()['token']
    tid = r.json()['id']

    # ensure gateway validates token
    ok = False
    for _ in range(10):
        rr = gw_client.post('/admin/validate', json={'token': token})
        if rr.status_code == 200:
            ok = True
            break
        time.sleep(0.05)
    assert ok

    # load financial service with isolated DB
    fm = reload_module('microservice.financial.main', {'FINANCIAL_DB_URL': fin_db})
    try:
        SQLModel.metadata.create_all(fm.engine)
    except Exception:
        pass

    # patch validator to use gateway DB directly
    import microservice.gateway.admin_client as admin_client

    def gw_validate_db(token_arg: str) -> bool:
        try:
            from sqlmodel import select
            import hashlib
            h = hashlib.sha256()
            h.update(token_arg.encode())
            token_hash = h.hexdigest()
            with gm.Session(gm.engine) as s:
                q = s.exec(select(gm.AdminToken).where(gm.AdminToken.token_hash == token_hash, gm.AdminToken.revoked == False))
                return q.first() is not None
        except Exception:
            return False

    try:
        admin_client.validate_token = gw_validate_db
    except Exception:
        pass

    try:
        fm.gateway_validate_token = gw_validate_db
    except Exception:
        pass

    fc = TestClient(fm.app)

    # call admin endpoint recalculate_categories - should succeed with header
    r = fc.post('/admin/recalculate_categories', headers={'x-admin-token': token}, json={})
    assert r.status_code == 200

    # load library_of_truth with isolated DB
    lm = reload_module('microservice.library_of_truth.main', {'LIBRARY_OF_TRUTH_DB_URL': lib_db})
    try:
        SQLModel.metadata.create_all(lm.engine)
    except Exception:
        pass

    try:
        admin_client.validate_token = gw_validate_db
    except Exception:
        pass
    try:
        lm.gateway_validate_token = gw_validate_db
    except Exception:
        pass

    lc = TestClient(lm.app)

    # call parse_books (admin-protected) with header
    r2 = lc.post('/parse_books', headers={'x-admin-token': token})
    assert r2.status_code in (200, 204)

    # revoke token and confirm failure
    rr = gw_client.post(f'/admin/tokens/{tid}/revoke', headers={'x-admin-token': token})
    assert rr.status_code == 200
    # ensure gateway rejects
    r3 = gw_client.post('/admin/validate', json={'token': token})
    assert r3.status_code == 401

    # library parse should now be forbidden
    r4 = lc.post('/parse_books', headers={'x-admin-token': token})
    assert r4.status_code == 403
