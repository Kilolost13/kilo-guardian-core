#!/usr/bin/env bash
set -euo pipefail
# Use the Python-based wait-for-advanced
python3 -m financial.scripts.run_alembic_upgrade || true
exec python3 /app/wait-for-advanced.py "ai_brain:9004" -- uvicorn main:app --host 0.0.0.0 --port 9005
