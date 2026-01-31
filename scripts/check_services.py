#!/usr/bin/env python3
"""CI helper: check multiple services for readiness and optional admin endpoints.

Usage: python scripts/check_services.py

Reads environment variables for ADMIN_TOKEN and uses it when querying admin endpoints.
Exits with 0 if all checks pass, non-zero otherwise.
"""
import os
import sys
import time
import requests
import argparse
import json

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
RETRY = int(os.getenv("CHECK_RETRY", "20"))
SLEEP = float(os.getenv("CHECK_SLEEP", "3"))

SERVICES = [
    {"name": "ai_brain", "url": "http://localhost:9004/status", "admin": False},
    {"name": "financial", "url": "http://localhost:9005/admin/migration_status", "admin": True},
    {"name": "gateway", "url": "http://localhost:8000/status", "admin": False},
]


def check_one(svc, retry=RETRY, sleep=SLEEP, admin_token=ADMIN_TOKEN):
    headers = {}
    if svc.get("admin") and admin_token:
        headers["x-admin-token"] = admin_token
    attempt = 0
    last_status = None
    last_error = None
    for i in range(1, retry + 1):
        attempt = i
        try:
            r = requests.get(svc["url"], headers=headers, timeout=5)
            last_status = r.status_code
            if r.status_code == 200:
                return {"name": svc["name"], "ok": True, "attempts": i, "status": r.status_code}
            else:
                last_error = f"status={r.status_code}"
        except Exception as e:
            last_error = str(e)
        time.sleep(sleep)

    return {"name": svc["name"], "ok": False, "attempts": attempt, "status": last_status, "error": last_error}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--json", action="store_true", help="Emit machine-readable JSON summary")
    p.add_argument("--callback", help="Optional URL to POST JSON results to")
    args = p.parse_args(argv)

    results = []
    overall_ok = True
    for svc in SERVICES:
        res = check_one(svc)
        results.append(res)
        if not res.get("ok"):
            overall_ok = False

    summary = {
        "timestamp": int(time.time()),
        "overall_ok": overall_ok,
        "services": results,
    }

    if args.json or args.callback:
        out = json.dumps(summary)
        print(out)
    else:
        # human-friendly print
        for r in results:
            if r.get("ok"):
                print(f"{r['name']}: OK (attempts={r['attempts']})")
            else:
                print(f"{r['name']}: FAILED (attempts={r['attempts']}, status={r.get('status')}, error={r.get('error')})")

    if args.callback:
        try:
            h = {"Content-Type": "application/json"}
            if ADMIN_TOKEN:
                h["x-admin-token"] = ADMIN_TOKEN
            resp = requests.post(args.callback, json=summary, headers=h, timeout=10)
            print(f"Callback POST status: {resp.status_code}")
        except Exception as e:
            print(f"Callback POST failed: {e}")

    if not overall_ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
