#!/usr/bin/env bash
set -euo pipefail

# Kilo Guardian - Quick Rebuild Single Service
# Usage: ./rebuild-service.sh <service-name>
# Example: ./rebuild-service.sh financial

SERVICE=$1

if [ -z "${SERVICE:-}" ]; then
    echo "Usage: ./rebuild-service.sh <service-name>"
    echo ""
    echo "Available services:"
    echo "  gateway, ai_brain, meds, reminder, habits, financial,"
    echo "  library, cam, ml_engine, voice, usb_transfer, socketio, frontend"
    echo ""
    echo "Example:"
    echo "  ./rebuild-service.sh financial"
    exit 1
fi

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_ROOT="/home/brain_ai/Desktop/AI_stuff/old_hacksaw_fingers"
cd "$PROJECT_ROOT"

echo "========================================="
echo "🔨 Rebuilding: $SERVICE"
echo "========================================="
echo ""

# Map service names to paths
declare -A SERVICE_PATHS
SERVICE_PATHS=(
    ["gateway"]="services/gateway"
    ["ai_brain"]="services/ai_brain"
    ["meds"]="services/meds"
    ["reminder"]="services/reminder"
    ["habits"]="services/habits"
    ["financial"]="services/financial"
    ["library"]="services/library_of_truth"
    ["cam"]="services/cam"
    ["ml_engine"]="services/ml_engine"
    ["voice"]="services/voice"
    ["usb_transfer"]="services/usb_transfer"
    ["socketio"]="services/socketio-relay"
    ["frontend"]="frontend/kilo-react-frontend"
)

SERVICE_PATH="${SERVICE_PATHS[$SERVICE]:-}"

if [ -z "$SERVICE_PATH" ]; then
    echo -e "${RED}❌ Unknown service: $SERVICE${NC}"
    echo ""
    echo "Available services:"
    for s in "${!SERVICE_PATHS[@]}"; do
        echo "  - $s"
    done
    exit 1
fi

if [ ! -f "$SERVICE_PATH/Dockerfile" ]; then
    echo -e "${RED}❌ Dockerfile not found at $SERVICE_PATH/Dockerfile${NC}"
    exit 1
fi

# Build timestamp
BUILD_TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Build the image
echo "🔨 Building Docker image..."
if docker build -t "kilo/$SERVICE:latest" \
               -t "kilo/$SERVICE:$BUILD_TIMESTAMP" \
               --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
               --build-arg BUILD_TIMESTAMP="$BUILD_TIMESTAMP" \
               -f "$SERVICE_PATH/Dockerfile" \
               . ; then
    echo -e "${GREEN}✅ Built kilo/$SERVICE:latest${NC}"
else
    echo -e "${RED}❌ Build failed${NC}"
    exit 1
fi

# Check if K3s is installed
if ! command -v k3s &> /dev/null; then
    echo -e "${YELLOW}⚠️  K3s not installed. Image built but not imported.${NC}"
    echo "Install K3s: curl -sfL https://get.k3s.io | sh -"
    exit 0
fi

# Export to tar
echo "📦 Exporting to tar..."
docker save "kilo/$SERVICE:latest" -o "/tmp/kilo-$SERVICE.tar"

# Import to K3s
echo "📥 Importing to K3s..."
if sudo k3s ctr images import "/tmp/kilo-$SERVICE.tar"; then
    echo -e "${GREEN}✅ Imported to K3s${NC}"
    rm "/tmp/kilo-$SERVICE.tar"
else
    echo -e "${RED}❌ Failed to import to K3s${NC}"
    exit 1
fi

# Map service names to deployment names (handle special cases)
case "$SERVICE" in
    ai_brain)
        DEPLOYMENT="kilo-ai-brain"
        ;;
    library)
        DEPLOYMENT="kilo-library"
        ;;
    ml_engine)
        DEPLOYMENT="kilo-ml-engine"
        ;;
    usb_transfer)
        DEPLOYMENT="kilo-usb-transfer"
        ;;
    *)
        DEPLOYMENT="kilo-$SERVICE"
        ;;
esac

# Restart deployment
echo "🔄 Restarting deployment..."
if kubectl rollout restart "deployment/$DEPLOYMENT" -n kilo-guardian 2>/dev/null; then
    echo -e "${GREEN}✅ Deployment restarted${NC}"
else
    echo -e "${YELLOW}⚠️  Deployment not found or not yet created${NC}"
    echo "You may need to run ./deploy-to-k3s.sh first to create deployments"
fi

echo ""
echo "========================================="
echo "✅ Service Rebuilt Successfully!"
echo "========================================="
echo ""
echo "Watch the rollout:"
echo "  kubectl get pods -n kilo-guardian -w"
echo ""
echo "View logs:"
echo "  kubectl logs -n kilo-guardian deployment/$DEPLOYMENT -f"
echo ""
echo "Test the service:"
echo "  kubectl port-forward -n kilo-guardian svc/$DEPLOYMENT <port>:<port>"
echo ""
