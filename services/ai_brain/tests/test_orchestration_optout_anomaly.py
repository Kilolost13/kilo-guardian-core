import os
# use an in-memory DB for tests to avoid touching disk and to keep tests isolated
os.environ['AI_BRAIN_DB'] = 'sqlite:///:memory:'
from fastapi.testclient import TestClient
from ai_brain.main import app
import pytest
from unittest.mock import patch

client = TestClient(app)

def test_opt_out_camera():
    # set opt-out
    r = client.post("/user/user1/settings", json={"opt_out_camera": True})
    assert r.status_code == 200
    # try to create sedentary
    r2 = client.post("/reminder/sedentary", json={"user_id":"user1"})
    assert r2.status_code == 200
    assert r2.json().get('status') == 'opted_out'

@patch('ai_brain.orchestrator.create_reminder')
def test_anomaly_triggers_reminder(mock_create_reminder):
    # make stub for reminder creation
    mock_create_reminder.return_value = 999
    # ensure settings allow habits
    client.post("/user/user2/settings", json={"opt_out_habits": False})
    # post several events to build profile
    client.post("/events", json={"user_id":"user2","event_type":"wake_time","timestamp":"2025-12-10T07:30:00"})
    client.post("/events", json={"user_id":"user2","event_type":"wake_time","timestamp":"2025-12-11T07:35:00"})
    client.post("/events", json={"user_id":"user2","event_type":"wake_time","timestamp":"2025-12-12T07:40:00"})
    # anomalous event far outside mean
    client.post("/events", json={"user_id":"user2","event_type":"wake_time","timestamp":"2025-12-12T23:00:00"})
    # ensure reminder creation was attempted
    assert mock_create_reminder.called
