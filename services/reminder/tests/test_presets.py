import os
import sys
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

# make repo root importable so `import microservice...` works
repo_root = str(Path(__file__).resolve().parents[3])
sys.path.insert(0, repo_root)

# set a temporary sqlite file before importing the app
fd, path = tempfile.mkstemp(prefix='reminder_test_', suffix='.db')
os.close(fd)
os.environ['REMINDER_DB_URL'] = f"sqlite:///{path}"

ADMIN = 'test-admin-token'
os.environ['ADMIN_TOKEN'] = ADMIN

from microservice.reminder.main import app


def test_presets_seeded_and_create_from_preset():
    # ensure presets seeded on startup
    with TestClient(app) as client:
        r = client.get('/presets')
        assert r.status_code == 200
        presets = r.json()
        assert isinstance(presets, list)
        assert any(p.get('name') == 'laundry' for p in presets)

        # create a new preset via admin
        payload = {
            'name': 'test_quick',
            'description': 'quick test',
            'time_of_day': '23:59',
            'recurrence': 'daily'
        }
        r = client.post('/presets', json=payload, headers={'x-admin-token': ADMIN})
        assert r.status_code == 200
        new = r.json()
        pid = new.get('id')
        assert pid is not None

        # create reminder from preset
        r = client.post(f'/presets/{pid}/create')
        assert r.status_code == 200
        rem = r.json()
        assert rem.get('preset_id') == pid
        assert 'when' in rem


def test_suggestions_and_patch():
    with TestClient(app) as client:
        r = client.get('/suggestions')
        assert r.status_code == 200
        s = r.json()
        assert 'suggestions' in s

        # patch an existing preset (use first preset)
        r = client.get('/presets')
        presets = r.json()
        assert presets
        pid = presets[0]['id']
        patch = {'habit_id': 42}
        r = client.patch(f'/presets/{pid}', json=patch, headers={'x-admin-token': ADMIN})
        assert r.status_code == 200
        updated = r.json()
        assert updated.get('habit_id') == 42
