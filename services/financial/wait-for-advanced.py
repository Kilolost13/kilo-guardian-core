#!/usr/bin/env python3
from __future__ import annotations
import sys
import os
import socket
import time

TIMEOUT = int(os.environ.get("WAIT_FOR_TIMEOUT", "60"))
MAX_BACKOFF = int(os.environ.get("WAIT_FOR_MAX_BACKOFF", "8"))


def wait_tcp(host: str, port: int, timeout: int, max_backoff: int) -> bool:
    start = time.time()
    backoff = 1
    while True:
        try:
            with socket.create_connection((host, port), timeout=2):
                return True
        except Exception:
            pass
        if time.time() - start >= timeout:
            return False
        time.sleep(backoff)
        backoff = min(max_backoff, backoff * 2)


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    services = []
    cmd = []
    for i, a in enumerate(argv):
        if a == "--":
            cmd = argv[i + 1 :]
            break
        services.append(a)

    for s in services:
        if not s:
            continue
        host, port = s.split(":", 1)
        port = int(port)
        print(f"waiting for {host}:{port}")
        ok = wait_tcp(host, port, TIMEOUT, MAX_BACKOFF)
        if not ok:
            print(f"timed out waiting for {host}:{port}", file=sys.stderr)
            return 1
    if cmd:
        os.execvp(cmd[0], cmd)


if __name__ == "__main__":
    raise SystemExit(main())
