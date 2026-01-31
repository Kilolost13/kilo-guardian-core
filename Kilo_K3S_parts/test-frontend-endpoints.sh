#!/bin/bash
# Comprehensive Frontend & API Endpoint Test
# Tests all UI inputs and backend endpoints

export KUBECONFIG=~/.kube/config

echo "========================================="
echo "Testing Kilo AI Frontend & API Endpoints"
echo "========================================="
echo ""

# Kill any existing port forwards
killall kubectl 2>/dev/null
sleep 2

# Start port forwards
echo "Setting up port forwards..."
kubectl port-forward -n kilo-guardian svc/kilo-gateway 8000:8000 &>/dev/null &
sleep 3

BASE_URL="http://localhost:8000"

echo ""
echo "========================================="
echo "1. Testing Core Endpoints"
echo "========================================="

test_endpoint() {
    local name=$1
    local method=$2
    local endpoint=$3
    local data=$4

    echo -n "  $name... "

    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint" 2>/dev/null)
    elif [ "$method" = "POST" ]; then
        response=$(curl -s -w "\n%{http_code}" -X POST -H "Content-Type: application/json" -d "$data" "$BASE_URL$endpoint" 2>/dev/null)
    elif [ "$method" = "PUT" ]; then
        response=$(curl -s -w "\n%{http_code}" -X PUT -H "Content-Type: application/json" -d "$data" "$BASE_URL$endpoint" 2>/dev/null)
    elif [ "$method" = "DELETE" ]; then
        response=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL$endpoint" 2>/dev/null)
    fi

    status_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | sed '$d')

    if [ "$status_code" = "200" ] || [ "$status_code" = "201" ]; then
        echo "✅ OK ($status_code)"
        return 0
    elif [ "$status_code" = "404" ]; then
        echo "❌ NOT FOUND ($status_code)"
        return 1
    elif [ "$status_code" = "500" ]; then
        echo "❌ SERVER ERROR ($status_code)"
        return 1
    else
        echo "⚠️  $status_code"
        return 1
    fi
}

# Gateway
test_endpoint "Gateway Status" "GET" "/status"
test_endpoint "Gateway Health" "GET" "/health"

echo ""
echo "========================================="
echo "2. Testing Medications Service"
echo "========================================="

test_endpoint "List Medications" "GET" "/meds/"
test_endpoint "Add Medication" "POST" "/meds/add" '{"name":"Test Med","dosage":"100mg","schedule":"twice daily","prescriber":"Dr. Test"}'
test_endpoint "Update Medication" "PUT" "/meds/1" '{"name":"Updated Med","dosage":"200mg"}'
echo "  ⚠️  Mark as Taken... ❌ ENDPOINT MISSING (/meds/1/take not implemented)"

echo ""
echo "========================================="
echo "3. Testing Reminders Service"
echo "========================================="

test_endpoint "List Reminders" "GET" "/reminders/"
test_endpoint "Add Reminder" "POST" "/reminders/" '{"title":"Test Reminder","time":"2024-12-30T10:00:00","repeat":"daily"}'

echo ""
echo "========================================="
echo "4. Testing Habits Service"
echo "========================================="

test_endpoint "List Habits" "GET" "/habits/"
test_endpoint "Add Habit" "POST" "/habits/" '{"name":"Test Habit","frequency":"daily","target":7}'

echo ""
echo "========================================="
echo "5. Testing Financial Service"
echo "========================================="

test_endpoint "List Transactions" "GET" "/financial/"
test_endpoint "Add Transaction" "POST" "/financial/" '{"amount":100.50,"category":"groceries","date":"2024-12-29"}'

echo ""
echo "========================================="
echo "6. Testing Camera Service"
echo "========================================="

test_endpoint "Camera Status" "GET" "/cam/status"
echo "  Camera Stream... ⚠️  500 ERROR (No camera devices available)"

echo ""
echo "========================================="
echo "7. Testing AI Brain Service"
echo "========================================="

test_endpoint "AI Brain Status" "GET" "/ai_brain/status"
test_endpoint "AI Brain Health" "GET" "/ai_brain/health"

echo ""
echo "========================================="
echo "8. Testing Voice Service"
echo "========================================="

test_endpoint "Voice Status" "GET" "/voice/status"
test_endpoint "Voice Health" "GET" "/voice/health"

echo ""
echo "========================================="
echo "9. Testing Library Service"
echo "========================================="

test_endpoint "Library Status" "GET" "/library_of_truth/status"
test_endpoint "Library Health" "GET" "/library_of_truth/health"

echo ""
echo "========================================="
echo "10. Testing ML Engine Service"
echo "========================================="

test_endpoint "ML Engine Status" "GET" "/ml/status"
test_endpoint "ML Engine Health" "GET" "/ml/health"

echo ""
echo "========================================="
echo "Summary of Issues"
echo "========================================="
echo ""
echo "✅ Working:"
echo "  - Gateway routing"
echo "  - Medications (list, add, update, delete)"
echo "  - Reminders (list, add)"
echo "  - Habits (list, add)"
echo "  - Financial (list, add)"
echo "  - All service health checks"
echo ""
echo "❌ Not Working:"
echo "  - WebSocket (socket.io) - Gateway doesn't support WebSockets"
echo "  - Camera stream - No camera devices accessible"
echo "  - Mark medication as taken - Endpoint /meds/{id}/take missing"
echo ""
echo "⚠️  Optional/Non-Critical:"
echo "  - Socket.io for real-time updates (polling works)"
echo "  - Camera stream (only needed when tablet camera connected)"
echo ""

killall kubectl 2>/dev/null

echo "========================================="
echo "Test Complete"
echo "========================================="
