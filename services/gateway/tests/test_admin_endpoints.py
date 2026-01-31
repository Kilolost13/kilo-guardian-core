from fastapi.testclient import TestClient
import importlib
from sqlmodel import SQLModel


def reload_gateway_module():
    import sys
    from pathlib import Path
    import os, time
    repo_root = str(Path(__file__).resolve().parents[3])
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    # ensure an isolated gateway DB for tests so test runs are hermetic
    os.environ['GATEWAY_DB_URL'] = f"sqlite:////tmp/gateway_test_{os.getpid()}_{int(time.time()*1000)}.db"
    if 'microservice.gateway.main' in sys.modules:
        del sys.modules['microservice.gateway.main']
    gm = importlib.import_module('microservice.gateway.main')
    try:
        SQLModel.metadata.create_all(gm.engine)
    except Exception:
        pass
    return gm


def test_admin_token_lifecycle():
    gm = reload_gateway_module()
    client = TestClient(gm.app)

    # create first token without auth
    r = client.post('/admin/tokens')
    assert r.status_code == 200
    data = r.json()
    assert 'token' in data
    token = data['token']
    tid = data['id']

    # validate via POST body
    r2 = client.post('/admin/validate', json={'token': token})
    assert r2.status_code == 200
    assert r2.json().get('valid') is True

    # list tokens requires header
    r3 = client.get('/admin/tokens', headers={'x-admin-token': token})
    assert r3.status_code == 200
    js = r3.json()
    assert 'tokens' in js

    # revoke
    r4 = client.post(f'/admin/tokens/{tid}/revoke', headers={'x-admin-token': token})
    assert r4.status_code == 200

    # validate should fail now
    r5 = client.post('/admin/validate', json={'token': token})
    assert r5.status_code == 401
