import os
import base64
from fastapi.testclient import TestClient
import pytest

# import app after setting environment variables in each test to exercise startup logic



def test_recalculate_requires_token(monkeypatch):
    # ensure a single token is required; import the module after env set so it picks it up
    monkeypatch.setenv('ADMIN_TOKEN', 'secrettoken')
    monkeypatch.delenv('ADMIN_TOKEN_LIST', raising=False)
    monkeypatch.delenv('ADMIN_BASIC_USER', raising=False)
    monkeypatch.delenv('ADMIN_BASIC_PASS', raising=False)
    import importlib
    # clear existing models to avoid redefinition errors during reload
    from sqlmodel import SQLModel
    SQLModel.metadata.clear()
    import financial.main as fm
    importlib.reload(fm)

    client = TestClient(fm.app)

    r = client.post('/admin/recalculate_categories')
    assert r.status_code == 403

    r = client.post('/admin/recalculate_categories', headers={'x-admin-token': 'secrettoken'})
    assert r.status_code == 200



def test_basic_auth_allows(monkeypatch):
    monkeypatch.delenv('ADMIN_TOKEN', raising=False)
    monkeypatch.delenv('ADMIN_TOKEN_LIST', raising=False)
    monkeypatch.setenv('ADMIN_BASIC_USER', 'admin')
    monkeypatch.setenv('ADMIN_BASIC_PASS', 'p@ss')
    import importlib
    from sqlmodel import SQLModel
    SQLModel.metadata.clear()
    import financial.main as fm
    importlib.reload(fm)

    client = TestClient(fm.app)

    creds = base64.b64encode(b'admin:p@ss').decode()
    r = client.post('/admin/recalculate_categories', headers={'Authorization': f'Basic {creds}'})
    assert r.status_code == 200


def test_scheduler_attached_when_enabled(monkeypatch):
    monkeypatch.setenv('ENABLE_NIGHTLY_MAINTENANCE', 'true')
    monkeypatch.setenv('NIGHTLY_CRON', '*/5 * * * *')

    # reload the module to trigger startup event with scheduler
    import importlib
    from sqlmodel import SQLModel
    SQLModel.metadata.clear()
    import financial.main as fm
    importlib.reload(fm)

    client = TestClient(fm.app)

    # If apscheduler is available, the app.state.scheduler should exist and have at least one job
    scheduler = getattr(fm.app.state, 'scheduler', None)
    if scheduler is None:
        pytest.skip('APScheduler not available in test environment')

    jobs = scheduler.get_jobs()
    assert len(jobs) >= 1

    # cleanup: shutdown scheduler
    try:
        scheduler.shutdown(wait=False)
    except Exception:
        pass
