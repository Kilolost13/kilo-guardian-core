#!/usr/bin/env bash
set -euo pipefail

echo "Running repo integration tests..."

check() {
  desc="$1"
  shift
  echo "- $desc"
  if "$@"; then
    echo "  OK"
    return 0
  else
    echo "  FAIL"
    return 1
  fi
}

# Gateway
check "Gateway /status" curl -sS -f http://localhost:8000/status | grep -q '"status":"ok"'

# ai_brain chat (JSON)
check "ai_brain /chat (JSON)" curl -sS -f -X POST http://localhost:9004/chat -H "Content-Type: application/json" --data-raw '{"message":"integration test"}' | grep -q 'response'

# ai_brain chat/voice (form)
check "ai_brain /chat/voice (form)" curl -sS -f -X POST http://localhost:9004/chat/voice -F "message=integration test" | grep -q 'tts_base64'

# meds add
check "meds /add" curl -sS -f -X POST http://localhost:9001/add -H "Content-Type: application/json" --data-raw '{"name":"TestMed","schedule":"daily","dosage":"1 pill","quantity":1,"prescriber":"CI","instructions":"Take"}' | grep -q '"name"'

# reminder root (ensure output is JSON array/object)
check "reminder /" bash -c "curl -sS -f http://localhost:9002/ | sed -n '1p' | grep -Eq '^[[:space:]]*[][\{]'
"

# frontend root
check "frontend /" curl -sS -f -I http://localhost:3000/ >/dev/null

echo "All integration checks passed." 
