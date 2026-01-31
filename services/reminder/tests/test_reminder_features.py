import importlib
import os
import time
from fastapi.testclient import TestClient
from sqlmodel import SQLModel
import pytest

# Ensure clean DB and reload module per test to pick up env changes

def reload_reminder_module():
    try:
        SQLModel.metadata.clear()
    except Exception:
        pass
    # import module fresh so environment changes and monkeypatches are picked up
    import importlib as _importlib
    import sys as _sys
    if 'microservice.reminder.main' in _sys.modules:
        del _sys.modules['microservice.reminder.main']
    rm = _importlib.import_module('microservice.reminder.main')
    # ensure tables exist for tests
    try:
        rm.SQLModel.metadata.create_all(rm.engine)
    except Exception:
        pass
    return rm


def test_add_and_upcoming_and_trigger(monkeypatch):
    # ensure no admin token required
    monkeypatch.delenv('ADMIN_TOKEN', raising=False)
    rm = reload_reminder_module()
    client = TestClient(rm.app)

    # create reminder for 1 minute in the future
    when = (rm.datetime.utcnow() + rm.timedelta(minutes=1)).isoformat()
    resp = client.post('/', json={'text': 'test 1', 'when': when})
    assert resp.status_code == 200
    data = resp.json()
    rid = data['id']

    # upcoming should show at least one scheduled job (wait briefly if needed)
    up = {}
    for _ in range(10):
        up = client.get('/upcoming').json()
        if len(up.get('upcoming', [])) >= 1:
            break
        time.sleep(0.1)
    assert len(up.get('upcoming', [])) >= 1

    # trigger immediately
    r2 = client.post(f'/{rid}/trigger')
    assert r2.status_code == 200
    assert r2.json()['status'] == 'triggered'


def test_snooze_and_mark(monkeypatch):
    monkeypatch.delenv('ADMIN_TOKEN', raising=False)
    rm = reload_reminder_module()
    client = TestClient(rm.app)

    when = (rm.datetime.utcnow() + rm.timedelta(minutes=1)).isoformat()
    resp = client.post('/', json={'text': 'test snooze', 'when': when})
    assert resp.status_code == 200
    data = resp.json()
    rid = data['id']

    # snooze (no admin token configured so should work)
    r = client.post(f'/{rid}/snooze', json={'minutes': 5})
    assert r.status_code == 200
    new_when = r.json()['when']
    assert new_when != when

    # mark sent
    r2 = client.post(f'/{rid}/mark_sent')
    assert r2.status_code == 200
    # verify via GET list
    lst = client.get('/').json()
    item = next((x for x in lst if x['id'] == rid), None)
    assert item is not None
    assert item.get('sent') is True


def test_callback_invoked(monkeypatch):
    # monkeypatch requests.post to capture callback
    called = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        called['url'] = url
        called['json'] = json
        class R:
            status_code = 200
        return R()

    # patch the requests.post used by the reminder module specifically
    monkeypatch.setattr('microservice.reminder.main.requests.post', fake_post, raising=False)
    monkeypatch.setenv('AI_BRAIN_CALLBACK_URL', 'http://example.local')
    rm = reload_reminder_module()
    client = TestClient(rm.app)

    when = (rm.datetime.utcnow() + rm.timedelta(seconds=1)).isoformat()
    resp = client.post('/', json={'text': 'callback test', 'when': when})
    assert resp.status_code == 200
    rid = resp.json()['id']

    # call send directly to avoid background thread timing issues in full test run
    rm._send_reminder(rid)
    assert 'url' in called
    assert called['url'].endswith('/reminder/callback')


def test_admin_protection(monkeypatch):
    # set admin token and verify protected endpoints reject without header
    monkeypatch.setenv('ADMIN_TOKEN', 'secret')
    rm = reload_reminder_module()
    client = TestClient(rm.app)

    when = (rm.datetime.utcnow() + rm.timedelta(minutes=1)).isoformat()
    resp = client.post('/', json={'text': 'admin test', 'when': when})
    rid = resp.json()['id']

    r = client.post(f'/{rid}/snooze', json={'minutes': 1})
    assert r.status_code == 403

    r2 = client.post(f'/{rid}/snooze', json={'minutes': 1}, headers={'x-admin-token': 'secret'})
    assert r2.status_code == 200