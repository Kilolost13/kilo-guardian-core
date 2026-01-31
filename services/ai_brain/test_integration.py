import pytest
from fastapi.testclient import TestClient
from ai_brain.main import app
import datetime

def test_ingest_cam():
    client = TestClient(app)
    obs = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "posture": "standing",
        "pose_match": True,
        "mse": 0.001
    }
    response = client.post("/ingest/cam", json=obs)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "feedback" in data
    assert "Great job" in data["feedback"] or "Detected posture" in data["feedback"]
