#!/bin/bash
# Kilo AI System - Complete Startup and Access Script

export KUBECONFIG=~/.kube/config

echo "========================================="
echo "🚀 Starting Kilo AI Microservices System"
echo "========================================="
echo ""

# Check if k3s is running
if ! systemctl is-active --quiet k3s; then
    echo "⚠️  k3s service is not running. Please start it with:"
    echo "   sudo systemctl start k3s"
    exit 1
fi

echo "✅ k3s is running"
echo ""

# Check pod status
echo "📊 Checking service status..."
echo ""

TOTAL_PODS=$(kubectl get pods -n kilo-guardian --no-headers 2>/dev/null | wc -l)
READY_PODS=$(kubectl get pods -n kilo-guardian --no-headers 2>/dev/null | grep "1/1.*Running" | wc -l)

echo "Services: $READY_PODS/$TOTAL_PODS ready"
echo ""

# Show service status
kubectl get pods -n kilo-guardian -o custom-columns=\
NAME:.metadata.name,\
READY:.status.containerStatuses[0].ready,\
STATUS:.status.phase,\
RESTARTS:.status.containerStatuses[0].restartCount \
2>/dev/null | head -15

echo ""
echo "========================================="
echo "🌐 Starting Port Forwards..."
echo "========================================="
echo ""

# Kill any existing port forwards
killall kubectl 2>/dev/null
sleep 2

# Port forward all services
kubectl port-forward -n kilo-guardian svc/kilo-frontend 3000:80 &>/dev/null &
kubectl port-forward -n kilo-guardian svc/kilo-gateway 8000:8000 &>/dev/null &
kubectl port-forward -n kilo-guardian svc/kilo-ai-brain 9004:9004 &>/dev/null &
kubectl port-forward -n kilo-guardian svc/kilo-library 9006:9006 &>/dev/null &
kubectl port-forward -n kilo-guardian svc/kilo-meds 9001:9001 &>/dev/null &
kubectl port-forward -n kilo-guardian svc/kilo-reminder 9002:9002 &>/dev/null &
kubectl port-forward -n kilo-guardian svc/kilo-habits 9003:9003 &>/dev/null &
kubectl port-forward -n kilo-guardian svc/kilo-financial 9005:9005 &>/dev/null &
kubectl port-forward -n kilo-guardian svc/kilo-cam 9007:9007 &>/dev/null &
kubectl port-forward -n kilo-guardian svc/kilo-ml-engine 9008:9008 &>/dev/null &
kubectl port-forward -n kilo-guardian svc/kilo-voice 9009:9009 &>/dev/null &
kubectl port-forward -n kilo-guardian svc/kilo-usb-transfer 8006:8006 &>/dev/null &
kubectl port-forward -n kilo-guardian svc/kilo-ollama 11434:11434 &>/dev/null &

sleep 3

echo "✅ Port forwards established!"
echo ""

echo "========================================="
echo "📱 Kilo AI System Ready!"
echo "========================================="
echo ""
echo "Access your services at:"
echo ""
echo "  🌐 Frontend (Local):     http://localhost:30000"
echo "  🌐 Frontend (Tablet):    http://192.168.68.64:30000"
echo ""
echo "  Legacy port forwards:"
echo "  🌐 Frontend (Web UI):    http://localhost:3000"
echo "  🧠 AI Brain API:         http://localhost:9004"
echo "  📚 Library of Truth:     http://localhost:9006"
echo "  💊 Medications:          http://localhost:9001"
echo "  ⏰ Reminders:            http://localhost:9002"
echo "  🎯 Habits:               http://localhost:9003"
echo "  💰 Financial:            http://localhost:9005"
echo "  📷 Camera/Tablet:        http://localhost:9007"
echo "  🤖 ML Engine:            http://localhost:9008"
echo "  🎤 Voice (STT/TTS):      http://localhost:9009"
echo "  🔌 USB Transfer:         http://localhost:8006"
echo "  🦙 Ollama LLM:           http://localhost:11434"
echo "  🌉 Gateway:              http://localhost:8000"
echo ""
echo "========================================="
echo "📖 Quick Commands:"
echo "========================================="
echo ""
echo "  View all services:    kubectl get pods -n kilo-guardian"
echo "  View logs:            kubectl logs -n kilo-guardian deployment/kilo-ai-brain -f"
echo "  Restart a service:    kubectl rollout restart deployment/kilo-gateway -n kilo-guardian"
echo "  Test endpoints:       ~/test-all-endpoints.sh"
echo ""
echo "========================================="
echo "🛑 To stop:"
echo "========================================="
echo ""
echo "  Press Ctrl+C, then run: killall kubectl"
echo ""
echo "Port forwards are active. System ready for tablet connection!"
echo ""

# Keep script running
trap "echo ''; echo 'Stopping port forwards...'; killall kubectl; exit 0" INT TERM

# Wait indefinitely
while true; do
    sleep 1
done
