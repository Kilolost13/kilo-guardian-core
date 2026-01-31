#!/bin/bash

###############################################################################
# Kilo Guardian - Automated Endpoint Testing Script
# Generated: 2025-12-28
# Purpose: Test all microservice endpoints to verify deployment and routing
###############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Admin token for authenticated endpoints
ADMIN_TOKEN="${LIBRARY_ADMIN_KEY:-test123}"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Kilo Guardian - Endpoint Testing Suite                 ║${NC}"
echo -e "${BLUE}║  Testing all microservices and gateway routes           ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

###############################################################################
# Helper Functions
###############################################################################

test_endpoint() {
    local service_name="$1"
    local method="$2"
    local endpoint="$3"
    local expected_status="${4:-200}"
    local auth="${5:-false}"
    local body="${6:-}"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    local url="http://localhost:8000${endpoint}"
    local curl_args=(-s -w "\n%{http_code}" -X "$method")

    # Add auth header if required
    if [ "$auth" = "true" ]; then
        curl_args+=(-H "X-Admin-Token: $ADMIN_TOKEN")
    fi

    # Add body if provided
    if [ -n "$body" ]; then
        curl_args+=(-H "Content-Type: application/json" -d "$body")
    fi

    # Execute request
    local response
    response=$(curl "${curl_args[@]}" "$url" 2>/dev/null || echo -e "\nERROR")

    local http_code
    http_code=$(echo "$response" | tail -n1)
    local body_response
    body_response=$(echo "$response" | head -n-1)

    # Check status code
    if [ "$expected_status" = "ANY" ] && [ "$http_code" != "ERROR" ]; then
        echo -e "${GREEN}✓${NC} [$service_name] $method $endpoint → $http_code"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    elif [ "$http_code" = "$expected_status" ]; then
        echo -e "${GREEN}✓${NC} [$service_name] $method $endpoint → $http_code"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}✗${NC} [$service_name] $method $endpoint → $http_code (expected $expected_status)"
        if [ -n "$body_response" ]; then
            echo -e "${YELLOW}  Response: ${body_response:0:100}${NC}"
        fi
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

test_direct_service() {
    local service_name="$1"
    local port="$2"
    local endpoint="${3:-/health}"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    local url="http://localhost:$port$endpoint"
    local response
    response=$(curl -s -w "\n%{http_code}" "$url" 2>/dev/null || echo -e "\nERROR")

    local http_code
    http_code=$(echo "$response" | tail -n1)

    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo -e "${GREEN}✓${NC} [$service_name:$port] Direct connection OK"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}✗${NC} [$service_name:$port] Direct connection FAILED → $http_code"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

section_header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

###############################################################################
# Test Suite
###############################################################################

section_header "1. Gateway Service Health"
test_endpoint "Gateway" "GET" "/health" "200"
test_endpoint "Gateway" "GET" "/status" "200"
test_endpoint "Gateway" "GET" "/admin/status" "200"

section_header "2. Direct Service Health Checks"
echo "Testing direct connectivity to each microservice..."
test_direct_service "Meds" "9001"
test_direct_service "Reminder" "9002"
test_direct_service "Habits" "9003"
test_direct_service "AI Brain" "9004"
test_direct_service "Financial" "9005"
test_direct_service "Library" "9006"
test_direct_service "Camera" "9007"
test_direct_service "ML Engine" "9008"
test_direct_service "Voice" "9009"
test_direct_service "USB Transfer" "8006"

section_header "3. Medications Service (via Gateway)"
test_endpoint "Meds" "GET" "/meds/health" "200"
test_endpoint "Meds" "GET" "/meds/" "200" "true"
echo -e "${YELLOW}  Note: Other meds endpoints require test data (skipping CRUD tests)${NC}"

section_header "4. Reminder Service - CRITICAL TESTS"
echo "Testing reminder endpoints (this is where the schema mismatch exists)..."

# Test original endpoint
test_endpoint "Reminder" "GET" "/reminder/" "200" "false"

# Test custom frontend endpoints (these may fail if not deployed)
echo -e "\n${YELLOW}Testing custom frontend-compatible endpoints:${NC}"
test_endpoint "Reminder" "GET" "/reminder/reminders" "200" "false"

# Try creating a reminder with frontend schema
echo -e "\n${YELLOW}Testing reminder creation with frontend schema:${NC}"
REMINDER_DATA='{"title":"Test Reminder","description":"Automated test","reminder_time":"2025-12-30T10:00:00","recurring":false}'
test_endpoint "Reminder" "POST" "/reminder/reminders" "200" "true" "$REMINDER_DATA"

section_header "5. Habits Service (via Gateway)"
test_endpoint "Habits" "GET" "/habits/health" "200"
test_endpoint "Habits" "GET" "/habits/" "200" "true"
echo -e "${YELLOW}  Note: Other habits endpoints require test data (skipping CRUD tests)${NC}"

section_header "6. Financial Service (via Gateway)"
test_endpoint "Financial" "GET" "/financial/health" "200"
test_endpoint "Financial" "GET" "/financial/transactions" "200" "true"
test_endpoint "Financial" "GET" "/financial/summary" "200" "true"
test_endpoint "Financial" "GET" "/financial/budgets" "200" "true"
test_endpoint "Financial" "GET" "/financial/goals" "200" "true"

section_header "7. AI Brain Service (via Gateway)"
test_endpoint "AI Brain" "GET" "/ai_brain/health" "200"
test_endpoint "AI Brain" "GET" "/ai_brain/status" "200"

# Test missing dashboard endpoints that frontend expects
echo -e "\n${YELLOW}Testing endpoints that Dashboard.tsx expects:${NC}"
test_endpoint "AI Brain" "GET" "/ai_brain/memory/visualization" "ANY" "false"
test_endpoint "Stats" "GET" "/ai_brain/stats/dashboard" "ANY" "false"

section_header "8. ML Engine Service (via Gateway)"
test_endpoint "ML Engine" "GET" "/ml/health" "200"
test_endpoint "ML Engine" "GET" "/ml/insights/patterns" "200" "true"

section_header "9. Library of Truth Service (via Gateway)"
test_endpoint "Library" "GET" "/library_of_truth/health" "200"
echo -e "${YELLOW}  Note: Library of Truth not used by frontend${NC}"

section_header "10. Camera Service (via Gateway)"
test_endpoint "Camera" "GET" "/cam/health" "200"
echo -e "${YELLOW}  Note: Camera service not directly used by frontend${NC}"

section_header "11. Voice Service (via Gateway)"
test_endpoint "Voice" "GET" "/voice/health" "200"
echo -e "${YELLOW}  Note: Voice service not used by frontend${NC}"

section_header "12. USB Transfer Service (via Gateway)"
test_endpoint "USB" "GET" "/usb/health" "200"
echo -e "${YELLOW}  Note: USB Transfer not used by frontend${NC}"

section_header "13. Admin Endpoints"
echo -e "${YELLOW}Testing admin endpoints that frontend uses:${NC}"
test_endpoint "Admin" "GET" "/admin/status" "200"

# This endpoint doesn't exist but frontend calls it
echo -e "\n${YELLOW}Testing backup endpoint (expected to fail):${NC}"
test_endpoint "Admin" "POST" "/admin/backup" "ANY" "true"

###############################################################################
# Critical Frontend Path Tests
###############################################################################

section_header "14. Frontend API Path Validation"
echo "Testing actual paths that frontend components call..."

echo -e "\n${BLUE}Medications.tsx paths:${NC}"
test_endpoint "Frontend" "GET" "/meds" "200" "true"

echo -e "\n${BLUE}Reminders.tsx paths:${NC}"
test_endpoint "Frontend" "GET" "/reminder/reminders" "200" "false"

echo -e "\n${BLUE}Finance.tsx paths:${NC}"
test_endpoint "Frontend" "GET" "/financial/transactions" "200" "true"
test_endpoint "Frontend" "GET" "/financial/summary" "200" "true"

echo -e "\n${BLUE}Habits.tsx paths:${NC}"
test_endpoint "Frontend" "GET" "/habits" "200" "true"

echo -e "\n${BLUE}Dashboard.tsx paths (may fail):${NC}"
test_endpoint "Frontend" "GET" "/ml/insights/patterns" "200" "true"
test_endpoint "Frontend" "GET" "/ai_brain/memory/visualization" "ANY" "false"
test_endpoint "Frontend" "GET" "/ai_brain/stats/dashboard" "ANY" "false"

###############################################################################
# Results Summary
###############################################################################

section_header "TEST RESULTS SUMMARY"
echo ""
echo -e "Total Tests:  ${BLUE}$TOTAL_TESTS${NC}"
echo -e "Passed:       ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed:       ${RED}$FAILED_TESTS${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✓ ALL TESTS PASSED - System is healthy!                ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
    exit 0
else
    PASS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))
    echo -e "${YELLOW}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║  ⚠ SOME TESTS FAILED - Pass rate: ${PASS_RATE}%                  ║${NC}"
    echo -e "${YELLOW}║  Review failures above and check ENDPOINT_FIXES.md       ║${NC}"
    echo -e "${YELLOW}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Common issues:${NC}"
    echo "1. Reminder service endpoints may not be deployed"
    echo "2. Dashboard expects non-existent /memory/visualization and /stats/dashboard"
    echo "3. Admin backup endpoint doesn't exist"
    echo ""
    echo -e "See ${BLUE}ENDPOINT_FIXES.md${NC} for detailed fix instructions."
    exit 1
fi
