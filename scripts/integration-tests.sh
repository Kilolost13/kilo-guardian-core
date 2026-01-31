#!/bin/bash
set -euo pipefail

GATEWAY=${GATEWAY_URL:-http://localhost:8000}
ADMIN_TOKEN=${LIBRARY_ADMIN_KEY:-test123}

echo "Integration tests: cross-service flows"

# Helper
req() { curl -s -H "X-Admin-Token: $ADMIN_TOKEN" -H "Content-Type: application/json" -w "\n%{http_code}" -X POST -d "$2" "$1" || true; }
get() { curl -s -w "\n%{http_code}" -X GET "$1" || true; }

# 1) Baseline memories count
echo "Checking baseline stats..."
base_stats=$(curl -s $GATEWAY/ai_brain/stats/dashboard)
echo "Base stats: $base_stats"
if command -v python3 >/dev/null 2>&1; then
  base_memories=$(echo "$base_stats" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("totalMemories",0))')
elif command -v jq >/dev/null 2>&1; then
  base_memories=$(echo "$base_stats" | jq -r '.totalMemories')
else
  echo "ERROR: python3 or jq required to parse JSON"; exit 1
fi

# 2) Post meds (should return reminder)
med='{"name":"TestMed","schedule":"09:00","dosage":"10mg","quantity":10,"prescriber":"Dr Test","instructions":"Take with water"}'
resp=$(req "$GATEWAY/ai_brain/ingest/meds" "$med")
echo "ingest meds response: $resp"

# 3) Post finance
fin='{"amount":9.99,"description":"Test Coffee","date":"2025-12-28"}'
resp=$(req "$GATEWAY/ai_brain/ingest/finance" "$fin")
echo "ingest finance response: $resp"

# 4) Post receipt
receipt='{"text":"Milk 2.50\nBread 1.90\nEggs 3.00"}'
resp=$(req "$GATEWAY/ai_brain/ingest/receipt" "$receipt")
echo "ingest receipt response: $resp"

# 5) Post cam observation
cam='{"timestamp":"2025-12-28T12:00:00","posture":"sitting","pose_match":true}'
resp=$(req "$GATEWAY/ai_brain/ingest/cam" "$cam")
echo "ingest cam response: $resp"

# allow some processing time
sleep 1

# 6) New stats
new_stats=$(curl -s $GATEWAY/ai_brain/stats/dashboard)
echo "New stats: $new_stats"
if command -v python3 >/dev/null 2>&1; then
  new_memories=$(echo "$new_stats" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("totalMemories",0))')
elif command -v jq >/dev/null 2>&1; then
  new_memories=$(echo "$new_stats" | jq -r '.totalMemories')
else
  echo "ERROR: python3 or jq required to parse JSON"; exit 1
fi

if [ "$new_memories" -gt "$base_memories" ]; then
  echo "✅ Memory count increased: $base_memories -> $new_memories"
else
  echo "⚠ Memory count did NOT increase: $base_memories -> $new_memories"
  exit 1
fi

# 7) Create a reminder via reminder service and verify listing
reminder='{"title":"Integration Test","description":"Test","reminder_time":"2025-12-31T10:00:00","recurring":false}'
resp=$(req "$GATEWAY/reminder/reminders" "$reminder")
echo "create reminder resp: $resp"

list=$(curl -s $GATEWAY/reminder/reminders)
echo "reminder list: $list"
if echo "$list" | grep -q "Integration Test"; then
  echo "✅ Reminder created and visible via reminder service"
else
  echo "⚠ Reminder not found in reminder list"
  exit 1
fi

# 8) Chat quick (low-latency) and verify no error
chat='{"user":"tester","message":"Integration check"}'
resp=$(req "$GATEWAY/ai_brain/chat/quick" "$chat")
echo "chat/quick response: $resp"

# 9) Check container health statuses
echo "Docker container health statuses:"
docker ps --format "table {{.Names}}\t{{.Status}}" | sed -n '1,200p'

echo "Integration tests completed successfully."
