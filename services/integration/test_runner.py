import os
import time
import json
import signal
import subprocess
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta


RECEIVED = []


class MockHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get('content-length', 0))
            body = self.rfile.read(length) if length else b''
            try:
                data = json.loads(body.decode())
            except Exception:
                data = body.decode()
            RECEIVED.append({'path': self.path, 'headers': dict(self.headers), 'body': data})
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())


def start_mock_server(port=9000):
    srv = HTTPServer(('0.0.0.0', port), MockHandler)

    def run():
        try:
            srv.serve_forever()
        except Exception:
            pass

    t = threading.Thread(target=run, daemon=True)
    t.start()
    return srv


def start_service(module_spec, port, extra_env=None):
    # Ensure subprocess Python path includes repo root so module imports like
    # `microservice.ai_brain` work reliably regardless of how pytest was invoked.
    env = os.environ.copy()
    # Ensure child processes can import both top-level helpers (db.py) and the
    # `microservice` package. Add both microservice dir and its parent to PYTHONPATH.
    micro_dir = os.path.abspath(os.getcwd())  # microservice dir
    parent_dir = os.path.abspath(os.path.dirname(micro_dir))
    parts = [micro_dir, parent_dir]
    if env.get('PYTHONPATH'):
        parts.append(env.get('PYTHONPATH'))
    # Ensure platform-appropriate separator
    env['PYTHONPATH'] = os.pathsep.join(parts)
    if extra_env:
        env.update(extra_env)
    cmd = [
        'uvicorn',
        f'{module_spec}:app',
        '--host', '0.0.0.0',
        '--port', str(port),
        '--log-level', 'warning'
    ]
    # If port is already in use, try to identify and terminate any process
    # listening on it to avoid flakiness in CI where a previous test run
    # may have left a server running.
    try:
        import socket
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', int(port)))
        s.close()
    except Exception:
        try:
            # try to find processes with lsof and kill them
            res = subprocess.check_output(['lsof', '-t', f'-i:{port}']).decode().strip()
            pids = [int(x) for x in res.split() if x.strip()]
            for pid in pids:
                try:
                    os.kill(pid, 15)
                except Exception:
                    pass
        except Exception:
            # best effort only; continue to start the service and let it fail if port truly in use
            pass

    # ensure no stale compiled bytecode interferes
    try:
        for root, dirs, files in os.walk(micro_dir):
            if '__pycache__' in dirs:
                try:
                    import shutil
                    shutil.rmtree(os.path.join(root, '__pycache__'))
                except Exception:
                    pass
    except Exception:
        pass

    # Prefer invoking uvicorn with the same Python interpreter to ensure
    # the child process sees the same site-packages and PYTHONPATH.
    try:
        import sys
        # If the current Python has uvicorn importable, prefer running it via
        # `python -m uvicorn` so it uses the same site-packages and PYTHONPATH.
        try:
            subprocess.check_call([sys.executable, '-c', 'import uvicorn'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            cmd = [sys.executable, '-m', 'uvicorn', f'{module_spec}:app', '--host', '0.0.0.0', '--port', str(port), '--log-level', 'warning']
        except Exception:
            # fallback to global uvicorn command if module not importable
            cmd = ['uvicorn', f'{module_spec}:app', '--host', '0.0.0.0', '--port', str(port), '--log-level', 'warning']
    except Exception:
        # ultimate fallback
        cmd = ['uvicorn', f'{module_spec}:app', '--host', '0.0.0.0', '--port', str(port), '--log-level', 'warning']

    p = subprocess.Popen(cmd, env=env, cwd=micro_dir)
    return p


def wait_for(url, timeout=15):
    import requests

    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=1)
            if r.status_code < 500:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def run_integration():
    import requests

    mock = start_mock_server(0)
    mock_port = mock.server_address[1]
    procs = []
    try:
        # start ai_brain, reminder, financial
        # start ai_brain without admin token
        procs.append(start_service('microservice.ai_brain.main', 8002, extra_env={'ADMIN_TOKEN': ''}))
        # reminder should not require admin for trigger in integration runner; unset ADMIN_TOKEN
        reminder_db = 'sqlite:////tmp/reminder_integration.db'
        procs.append(start_service('microservice.reminder.main', 8001, extra_env={'AI_BRAIN_CALLBACK_URL': f'http://127.0.0.1:{mock_port}', 'ADMIN_TOKEN': '', 'REMINDER_DB_URL': reminder_db}))
        # point financial outgoing posts at the mock server so we can assert the payloads; unset ADMIN_TOKEN and use separate DB
        financial_db = 'sqlite:////tmp/financial_integration.db'
        procs.append(start_service('microservice.financial.main', 8003, extra_env={'AI_BRAIN_URL': f'http://127.0.0.1:{mock_port}/ingest/finance', 'ADMIN_TOKEN': '', 'FINANCIAL_DB_URL': financial_db}))
        # wait for readiness
        ok = wait_for('http://127.0.0.1:8001/status', timeout=20)
        ok &= wait_for('http://127.0.0.1:8002/status', timeout=20)
        ok &= wait_for('http://127.0.0.1:8003/status', timeout=20)
        if not ok:
            print('One or more services failed to start')
            return 2

        failures = 0

        # Test: create a reminder and verify callback reaches mock server
        when = (datetime.utcnow() + timedelta(seconds=1)).isoformat()
        r = requests.post('http://127.0.0.1:8001/', json={'text': 'integration test', 'when': when})
        if r.status_code != 200:
            print('Failed to create reminder', r.status_code, r.text)
            failures += 1
        else:
            rid = r.json().get('id')
            requests.post(f'http://127.0.0.1:8001/{rid}/trigger')
            # wait for mock callback
            start = time.time()
            seen = False
            while time.time() - start < 10:
                if RECEIVED:
                    seen = True
                    break
                time.sleep(0.2)
            if not seen:
                print('Callback not received by mock server')
                failures += 1
            else:
                print('Callback received:', RECEIVED[-1]['path'])

        # Test: create a financial transaction and verify outgoing POST to AI_BRAIN (mock)
        tx = {
            'amount': 42.5,
            'description': 'integration-transaction',
            'date': datetime.utcnow().isoformat()
        }
        rtx = requests.post('http://127.0.0.1:8003/', json=tx)
        if rtx.status_code != 200:
            print('Failed to create financial transaction', rtx.status_code, rtx.text)
            failures += 1
        else:
            # verify transaction persisted locally
            lst = requests.get('http://127.0.0.1:8003/').json()
            if not any(t.get('amount') == tx['amount'] and t.get('description') == tx['description'] for t in lst):
                print('Transaction not found in financial list')
                failures += 1
            # verify mock received the outgoing post to /ingest/finance
            found = any(r['path'].endswith('/ingest/finance') and isinstance(r['body'], dict) and r['body'].get('amount') == tx['amount'] for r in RECEIVED)
            if not found:
                print('financial outgoing POST to AI_BRAIN not observed in mock')
                failures += 1
            else:
                print('financial outgoing POST observed')

        # Test: simple status endpoints
        for port in (8001, 8002, 8003):
            try:
                rr = requests.get(f'http://127.0.0.1:{port}/status', timeout=2)
                if rr.status_code != 200:
                    print(f'status check failed for port {port}')
                    failures += 1
            except Exception as e:
                print('status check exception', e)
                failures += 1

        return 1 if failures else 0

    finally:
        try:
            mock.shutdown()
        except Exception:
            pass
        for p in procs:
            try:
                p.terminate()
            except Exception:
                pass


if __name__ == '__main__':
    code = run_integration()
    print('\nIntegration runner exiting with code', code)
    raise SystemExit(code)
