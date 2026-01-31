#!/usr/bin/env bash
set -euo pipefail
# Use python-based advanced wait wrapper (no upstream services configured)
exec python3 /app/wait-for-advanced.py "" -- uvicorn main:app --host 0.0.0.0 --port 9006
