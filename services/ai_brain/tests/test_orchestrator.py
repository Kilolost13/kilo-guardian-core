import time
from fastapi.testclient import TestClient
from ai_brain.main import app

client = TestClient(app)

def test_create_sedentary_and_ingest_cam():
    # create sedentary session
    r = client.post("/reminder/sedentary", json={"user_id":"orch_user1"})
    assert r.status_code == 200
    data = r.json()
    assert "state_id" in data
    state_id = data["state_id"]
    # ingest cam report sitting
    now_iso = "2025-12-16T12:00:00Z"
    r2 = client.post("/ingest/cam", json={"user_id":"orch_user1","posture":"sitting","timestamp":now_iso})
    assert r2.status_code == 200
    # ingest movement
    now_iso2 = "2025-12-16T12:05:00Z"
    r3 = client.post("/ingest/cam", json={"user_id":"orch_user1","posture":"standing","timestamp":now_iso2})
    assert r3.status_code == 200

def test_meds_upload_and_confirm():
    r = client.post("/meds/upload", json={"user_id":"orch_user1","med_name":"Aspirin","dosage":"100mg","schedule_text":"08:00"})
    assert r.status_code == 200
    data = r.json()
    assert "med_id" in data
    med_id = data["med_id"]
    # confirm adherence
    r2 = client.post("/reminder/meds/confirm", json={"user_id":"user1","med_id":med_id,"taken":True})
    assert r2.status_code == 200

def test_habit_profile():
    # log events
    client.post("/events", json={"user_id":"orch_user1","event_type":"wake_time","timestamp":"2025-12-10T07:30:00"})
    client.post("/events", json={"user_id":"orch_user1","event_type":"wake_time","timestamp":"2025-12-11T07:35:00"})
    client.post("/events", json={"user_id":"orch_user1","event_type":"wake_time","timestamp":"2025-12-12T07:40:00"})
    r = client.get("/user/orch_user1/habits")
    assert r.status_code == 200
    data = r.json()
    assert data["profiles"]
