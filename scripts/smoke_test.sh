#!/usr/bin/env bash
set -euo pipefail

# Simple smoke test for the microservice stack
# Usage: ./scripts/smoke_test.sh [HOST_PREFIX]
# HOST_PREFIX defaults to localhost and ports assume compose default mapping

HOST=${1:-"localhost"}
AI_PORT=${2:-9004}
GATEWAY_PORT=${3:-8000}

echo "Checking ai_brain status..."
if ! curl -sS "http://${HOST}:${AI_PORT}/status" | grep -q 'ok'; then
  echo "ai_brain /status failed"
  exit 2
fi

echo "ai_brain status OK"

echo "Testing chat JSON..."
RESP=$(curl -sS -X POST "http://${HOST}:${AI_PORT}/chat" -H "Content-Type: application/json" -d '{"message":"hello"}')
if [ -z "$RESP" ]; then
  echo "chat JSON request failed"
  exit 3
fi

echo "Chat JSON response: $RESP"

# Test voice/form chat via gateway if available
if curl -sS "http://${HOST}:${GATEWAY_PORT}/" >/dev/null 2>&1; then
  echo "Gateway reachable; testing voice/form endpoint via gateway..."
  G_RESP=$(curl -sS -X POST "http://${HOST}:${GATEWAY_PORT}/api/ai_brain/chat/voice" -F "message=smoke test" )
  echo "Gateway chat/voice response: $G_RESP"
else
  echo "Gateway not reachable on ${GATEWAY_PORT}; skipping gateway tests"
fi

echo "Smoke tests completed successfully"
