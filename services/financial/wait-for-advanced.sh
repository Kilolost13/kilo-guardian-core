#!/usr/bin/env bash
set -euo pipefail

# Advanced wait-for script (copied locally for image build compatibility)
TIMEOUT=${WAIT_FOR_TIMEOUT:-60}
MAX_BACKOFF=${WAIT_FOR_MAX_BACKOFF:-8}

services=("${@}")

if [ ${#services[@]} -eq 0 ]; then
  echo "No services to wait for"
  exec "$@"
fi

for s in "${services[@]}"; do
  host=${s%%:*}
  port=${s##*:}
  echo "[wait-for] waiting for ${host}:${port} (timeout ${TIMEOUT}s)"
  start_ts=$(date +%s)
  backoff=1
  while true; do
    if (echo > /dev/tcp/${host}/${port}) >/dev/null 2>&1; then
      echo "[wait-for] ${host}:${port} reachable"
      break
    fi
    now=$(date +%s)
    elapsed=$((now - start_ts))
    if [ $elapsed -ge $TIMEOUT ]; then
      echo "[wait-for] timeout after ${elapsed}s waiting for ${host}:${port}" >&2
      exit 1
    fi
    sleep $backoff
    backoff=$((backoff * 2))
    if [ $backoff -gt $MAX_BACKOFF ]; then
      backoff=$MAX_BACKOFF
    fi
  done
done

if [ "$#" -gt 0 ]; then
  exec "${@: -1}"
fi
