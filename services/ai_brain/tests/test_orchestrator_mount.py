from fastapi.testclient import TestClient
import sys
import pathlib

# Ensure repo root on sys.path so tests can be run from the file directly
repo_root = pathlib.Path(__file__).resolve().parents[3]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from ai_brain.main import app

client = TestClient(app)


def test_orchestrator_routes_present():
    # ensure the router endpoints are present on the app
    paths = {r.path for r in app.routes if hasattr(r, "path")}
    assert "/reminder/sedentary" in paths
    assert "/user/{user_id}/settings" in paths
    assert "/meds/upload" in paths


def test_orchestrator_endpoints_respond():
    # POST to settings should return 200 and persist settings
    r = client.post("/user/test_user/settings", json={"opt_out_camera": True})
    assert r.status_code == 200
    assert r.json().get("settings") is not None

    # Use a different user that hasn't opted out for sedentary
    r2 = client.post("/reminder/sedentary", json={"user_id": "test_user_noopt"})
    assert r2.status_code == 200
    data = r2.json()
    assert "state_id" in data

    # Ingest a cam report for that non-opted-out user: should return 200 and not raise
    obs = {
        "timestamp": "2025-12-16T12:00:00Z",
        "posture": "sitting",
        "user_id": "test_user_noopt",
    }
    r3 = client.post("/ingest/cam", json=obs)
    assert r3.status_code == 200
