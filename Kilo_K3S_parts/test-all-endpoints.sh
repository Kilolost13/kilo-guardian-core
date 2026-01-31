#!/bin/bash
# Test all k3s service endpoints

export KUBECONFIG=~/.kube/config

echo "========================================="
echo "Testing All Kilo AI Microservices"
echo "========================================="
echo ""

# Port forward services in background
echo "Setting up port forwards..."
kubectl port-forward -n kilo-guardian svc/kilo-frontend 3000:80 &>/dev/null &
kubectl port-forward -n kilo-guardian svc/kilo-ai-brain 9004:9004 &>/dev/null &
kubectl port-forward -n kilo-guardian svc/kilo-library 9006:9006 &>/dev/null &
kubectl port-forward -n kilo-guardian svc/kilo-reminder 9002:9002 &>/dev/null &
kubectl port-forward -n kilo-guardian svc/kilo-ml-engine 9008:9008 &>/dev/null &
kubectl port-forward -n kilo-guardian svc/kilo-voice 9009:9009 &>/dev/null &
kubectl port-forward -n kilo-guardian svc/kilo-usb-transfer 8006:8006 &>/dev/null &
kubectl port-forward -n kilo-guardian svc/kilo-cam 9007:9007 &>/dev/null &
kubectl port-forward -n kilo-guardian svc/kilo-ollama 11434:11434 &>/dev/null &

sleep 5
echo "Port forwards established!"
echo ""

# Test function
test_endpoint() {
    local name=$1
    local url=$2
    echo -n "Testing $name... "

    response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)

    if [ "$response" = "200" ] || [ "$response" = "307" ] || [ "$response" = "404" ]; then
        echo "✅ OK (HTTP $response)"
        return 0
    else
        echo "❌ FAILED (HTTP $response)"
        return 1
    fi
}

# Test all services
test_endpoint "Frontend" "http://localhost:3000/"
test_endpoint "AI Brain /status" "http://localhost:9004/status"
test_endpoint "Library /status" "http://localhost:9006/status"
test_endpoint "Reminder" "http://localhost:9002/"
test_endpoint "ML Engine /status" "http://localhost:9008/status"
test_endpoint "Voice /status" "http://localhost:9009/status"
test_endpoint "USB Transfer /health" "http://localhost:8006/health"
test_endpoint "Cam /status" "http://localhost:9007/status"
test_endpoint "Ollama /api/tags" "http://localhost:11434/api/tags"

echo ""
echo "========================================="
echo "Service URLs (while script runs):"
echo "========================================="
echo "Frontend:      http://localhost:3000"
echo "AI Brain:      http://localhost:9004"
echo "Library:       http://localhost:9006"
echo "Reminder:      http://localhost:9002"
echo "ML Engine:     http://localhost:9008"
echo "Voice:         http://localhost:9009"
echo "USB Transfer:  http://localhost:8006"
echo "Cam:           http://localhost:9007"
echo "Ollama:        http://localhost:11434"
echo ""
echo "Press Ctrl+C to stop port forwards"

# Keep running
wait
