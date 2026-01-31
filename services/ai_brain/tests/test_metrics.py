import requests
import os

def test_metrics_direct_requires_token():
    url = os.environ.get('AI_BRAIN_URL', 'http://localhost:9004')
    # Without token should fail (401 or 403)
    r = requests.get(f"{url}/metrics")
    assert r.status_code in (401, 403)


def test_metrics_via_gateway_with_admin():
    gw = os.environ.get('GATEWAY_URL', 'http://localhost:8000')
    # Try to create admin token (may return null if tokens already exist)
    resp = requests.post(f"{gw}/admin/tokens")
    # If tokens already exist, creating a new token returns 401; fall back to LIBRARY_ADMIN_KEY in that case
    if resp.status_code == 200:
        token = resp.json().get('token')
        if not token:
            token = os.environ.get('LIBRARY_ADMIN_KEY', 'kilo-secure-admin-2024')
    else:
        token = os.environ.get('LIBRARY_ADMIN_KEY', 'kilo-secure-admin-2024')

    # Now fetch metrics via gateway admin proxy
    r = requests.get(f"{gw}/admin/ai_brain/metrics", headers={"X-Admin-Token": token})
    assert r.status_code == 200
    assert 'ai_brain_requests_total' in r.text

