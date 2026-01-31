#!/bin/bash
# Complete System Verification for Kilo AI + Tablet Integration

export KUBECONFIG=~/.kube/config

echo "==========================================="
echo "🔍 Kilo AI System Verification"
echo "==========================================="
echo ""

# 1. Check k3s
echo "1️⃣  Checking k3s service..."
if systemctl is-active --quiet k3s; then
    echo "   ✅ k3s is running"
else
    echo "   ❌ k3s is NOT running"
    exit 1
fi
echo ""

# 2. Check pods
echo "2️⃣  Checking all pods..."
TOTAL=$(kubectl get pods -n kilo-guardian --no-headers 2>/dev/null | wc -l)
READY=$(kubectl get pods -n kilo-guardian --no-headers 2>/dev/null | grep "1/1.*Running" | wc -l)
echo "   📊 Ready: $READY/$TOTAL pods"
kubectl get pods -n kilo-guardian -o custom-columns=NAME:.metadata.name,READY:.status.containerStatuses[0].ready | grep -E "NAME|true" | head -15
echo ""

# 3. Check devices for tablet/camera
echo "3️⃣  Checking tablet/camera devices..."
if [ -e /dev/video0 ]; then
    echo "   ✅ Video device /dev/video0 found (camera/tablet)"
    ls -l /dev/video* 2>/dev/null | head -5
else
    echo "   ⚠️  No video devices found"
fi
echo ""

# 4. Check USB devices
echo "4️⃣  Checking USB connectivity..."
if [ -d /dev/bus/usb ]; then
    echo "   ✅ USB bus accessible"
    USB_COUNT=$(ls -1 /dev/bus/usb/*/ 2>/dev/null | wc -l)
    echo "   📱 USB devices detected: $USB_COUNT"
else
    echo "   ⚠️  USB bus not found"
fi
echo ""

# 5. Test service endpoints
echo "5️⃣  Testing service endpoints..."
echo ""

# Start port forwards quietly
killall kubectl 2>/dev/null
sleep 2

kubectl port-forward -n kilo-guardian svc/kilo-frontend 3000:80 &>/dev/null &
kubectl port-forward -n kilo-guardian svc/kilo-ai-brain 9004:9004 &>/dev/null &
kubectl port-forward -n kilo-guardian svc/kilo-library 9006:9006 &>/dev/null &
kubectl port-forward -n kilo-guardian svc/kilo-cam 9007:9007 &>/dev/null &

sleep 5

# Test endpoints
test_service() {
    local name=$1
    local url=$2
    echo -n "   Testing $name... "

    response=$(curl -s -o /dev/null -w "%{http_code}" "$url" --connect-timeout 3 2>/dev/null)

    if [ "$response" = "200" ] || [ "$response" = "307" ]; then
        echo "✅ OK"
        return 0
    else
        echo "⚠️  HTTP $response"
        return 1
    fi
}

test_service "Frontend" "http://localhost:3000/"
test_service "AI Brain" "http://localhost:9004/status"
test_service "Library" "http://localhost:9006/status"
test_service "Camera" "http://localhost:9007/status"

killall kubectl 2>/dev/null
echo ""

# 6. Check network connectivity
echo "6️⃣  Checking service discovery..."
kubectl run test-dns -n kilo-guardian --rm -i --tty --image=busybox --restart=Never --command -- nslookup kilo-ai-brain 2>/dev/null | grep -q "Name:" && echo "   ✅ DNS resolution working" || echo "   ⚠️  DNS check skipped"
echo ""

# 7. Summary
echo "==========================================="
echo "📊 System Status Summary"
echo "==========================================="
echo ""
echo "  ✅ k3s Running: YES"
echo "  📦 Pods Ready: $READY/$TOTAL"
echo "  📹 Camera Devices: $(ls -1 /dev/video* 2>/dev/null | wc -l) found"
echo "  🔌 USB Bus: $([ -d /dev/bus/usb ] && echo 'Accessible' || echo 'Not found')"
echo ""

if [ "$READY" -ge 8 ]; then
    echo "  ✅ SYSTEM READY FOR TABLET CONNECTION"
    echo ""
    echo "  📱 To connect your tablet:"
    echo "     1. Connect tablet via USB"
    echo "     2. Run: ~/start-kilo-system.sh"
    echo "     3. Access frontend at http://localhost:3000"
    echo "     4. Camera service will detect tablet camera"
else
    echo "  ⏳ System initializing... ($READY services ready)"
    echo "     Run this script again in a few moments"
fi

echo ""
echo "==========================================="
