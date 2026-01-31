#!/usr/bin/env python3
"""
wait-for-advanced.py

TCP-based wait-for utility with exponential backoff.
Usage: wait-for-advanced.py host:port [host2:port2 ...] -- cmd args...
"""
import os
import socket
import sys
import time
import subprocess


def parse_args(argv):
    services = []
    cmd = []
    for i, a in enumerate(argv):
        if a == "--":
            cmd = argv[i + 1 :]
            break
        services.append(a)
    return services, cmd


def wait_for_tcp(host, port, timeout, max_backoff):
    start = time.time()
    backoff = 1
    while True:
        try:
            with socket.create_connection((host, port), timeout=2):
                return True
        except Exception:
            pass
        elapsed = time.time() - start
        if elapsed >= timeout:
            return False
        time.sleep(backoff)
        backoff = min(max_backoff, backoff * 2)


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    TIMEOUT = int(os.environ.get("WAIT_FOR_TIMEOUT", "60"))
    MAX_BACKOFF = int(os.environ.get("WAIT_FOR_MAX_BACKOFF", "8"))
    services, cmd = parse_args(argv)

    if not services:
        if cmd:
            os.execvp(cmd[0], cmd)
        return 0

    for s in services:
        if not s:
            # empty service string means skip
            continue
        if ":" not in s:
            print(f"Invalid service '{s}', expected host:port", file=sys.stderr)
            return 2
        host, port_s = s.split(":", 1)
        try:
            port = int(port_s)
        except ValueError:
            print(f"Invalid port in '{s}'", file=sys.stderr)
            return 2
        print(f"[wait-for] waiting for {host}:{port} (timeout {TIMEOUT}s)")
        ok = wait_for_tcp(host, port, TIMEOUT, MAX_BACKOFF)
        if not ok:
            print(f"[wait-for] timeout after {TIMEOUT}s waiting for {host}:{port}", file=sys.stderr)
            return 1
        print(f"[wait-for] {host}:{port} reachable")

    if cmd:
        os.execvp(cmd[0], cmd)


if __name__ == "__main__":
    raise SystemExit(main())
