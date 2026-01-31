import importlib
import sys
import time
from fastapi.testclient import TestClient
from sqlmodel import SQLModel


def get_app():
    try:
        SQLModel.metadata.clear()
    except Exception:
        pass
    # ensure a fresh import so SQLModel declaratives don't collide
    if 'microservice.reminder.main' in sys.modules:
        del sys.modules['microservice.reminder.main']
    rm = importlib.import_module('microservice.reminder.main')
    rm.SQLModel.metadata.create_all(rm.engine)
    return rm, TestClient(rm.app)


def test_daily_recurrence():
    rm, client = get_app()
    # set when to next minute
    when = (rm.datetime.utcnow() + rm.timedelta(minutes=1)).isoformat()
    resp = client.post('/', json={'text': 'daily test', 'when': when, 'recurrence': 'daily'})
    assert resp.status_code == 200
    rid = resp.json()['id']
    up = client.get('/upcoming').json()
    assert any(f'reminder_{rid}' in j['id'] for j in up['upcoming'])


def test_hourly_recurrence():
    rm, client = get_app()
    when = (rm.datetime.utcnow() + rm.timedelta(minutes=1)).isoformat()
    resp = client.post('/', json={'text': 'hourly test', 'when': when, 'recurrence': 'hourly'})
    assert resp.status_code == 200
    rid = resp.json()['id']
    up = client.get('/upcoming').json()
    assert any(f'reminder_{rid}' in j['id'] for j in up['upcoming'])


def test_weekly_recurrence():
    rm, client = get_app()
    when = (rm.datetime.utcnow() + rm.timedelta(minutes=1)).isoformat()
    resp = client.post('/', json={'text': 'weekly test', 'when': when, 'recurrence': 'weekly'})
    assert resp.status_code == 200
    rid = resp.json()['id']
    up = client.get('/upcoming').json()
    assert any(f'reminder_{rid}' in j['id'] for j in up['upcoming'])


def test_cron_recurrence():
    rm, client = get_app()
    when = (rm.datetime.utcnow() + rm.timedelta(minutes=1)).isoformat()
    cron = '*/5 * * * *'
    resp = client.post('/', json={'text': 'cron test', 'when': when, 'recurrence': cron})
    assert resp.status_code == 200
    rid = resp.json()['id']
    up = client.get('/upcoming').json()
    assert any(f'reminder_{rid}' in j['id'] for j in up['upcoming'])
