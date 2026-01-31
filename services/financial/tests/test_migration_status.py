from fastapi.testclient import TestClient
from financial.main import app
import os

client = TestClient(app)


def test_migration_status_endpoint():
    prev = os.environ.get('ADMIN_TOKEN')
    try:
        os.environ['ADMIN_TOKEN'] = 'admintest'
        headers = {'X-Admin-Token': 'admintest'}
        r = client.get('/admin/migration_status', headers=headers)
        assert r.status_code == 200
    finally:
        if prev is None:
            os.environ.pop('ADMIN_TOKEN', None)
        else:
            os.environ['ADMIN_TOKEN'] = prev
    j = r.json()
    assert 'db_revision' in j and 'heads' in j
