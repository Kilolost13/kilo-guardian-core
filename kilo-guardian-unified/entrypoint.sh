#!/bin/sh
set -e
exec uvicorn kilo_v2.server_core:app --host 0.0.0.0 --port 8001 --workers 1 --log-level info
