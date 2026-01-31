#!/usr/bin/env python3
"""
HTTP wait-for for cam service. Tries /status then / root.
"""
import os
import sys
import time
from urllib.request import urlopen

TIMEOUT = int(os.environ.get("WAIT_FOR_TIMEOUT", "60"))


def parse_args(argv):
    services = []
    cmd = []
    for i, a in enumerate(argv):
        if a == "--":
            cmd = argv[i + 1 :]
            break
        services.append(a)
    return services, cmd


def check_http(host, port):
    for path in ("/status", "/"):
        try:
            with urlopen(f"http://{host}:{port}{path}", timeout=2) as r:
                if 200 <= r.getcode() < 400:
                    return True
        except Exception:
            pass
    return False


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    # attempt model download (no-op if MODEL_URL not set or file exists)
    try:
        import subprocess
        subprocess.run(["python3", "/app/download_model.py"], check=False)
    except Exception:
        pass
    services, cmd = parse_args(argv)
    for s in services:
        host, port = s.split(":", 1)
        print(f"Waiting for {host}:{port} (timeout {TIMEOUT}s)")
        start = time.time()
        while time.time() - start < TIMEOUT:
            if check_http(host, port):
                print(f"{host}:{port} is up")
                break
            time.sleep(1)
        else:
            print(f"Timed out waiting for {host}:{port}")
            return 1
    if cmd:
        os.execvp(cmd[0], cmd)


if __name__ == "__main__":
    raise SystemExit(main())
