#!/usr/bin/env bash
set -euo pipefail

# Kilo Guardian - Build All Services Script
# This script builds all Docker images and imports them into K3s

PROJECT_ROOT="/home/brain_ai/Desktop/AI_stuff/old_hacksaw_fingers"
cd "$PROJECT_ROOT"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "🔨 Building All Kilo Guardian Services"
echo "========================================="
echo ""

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install Docker first.${NC}"
    exit 1
fi

# Check if K3s is installed
if ! command -v k3s &> /dev/null; then
    echo -e "${YELLOW}⚠️  K3s not installed. Images will be built but not imported.${NC}"
    echo -e "${YELLOW}   Install K3s first: curl -sfL https://get.k3s.io | sh -${NC}"
    K3S_INSTALLED=false
else
    K3S_INSTALLED=true
fi

# Generate build timestamp for cache busting
BUILD_TIMESTAMP=$(date +%Y%m%d-%H%M%S)
echo "📅 Build timestamp: $BUILD_TIMESTAMP"
echo ""

# Define all services
declare -A SERVICES
SERVICES=(
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
)

# Frontend
SERVICES["frontend"]="frontend/kilo-react-frontend"

SUCCESS_COUNT=0
FAIL_COUNT=0
FAILED_SERVICES=()

# Build each service
for service in "${!SERVICES[@]}"; do
    service_path="${SERVICES[$service]}"

    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Building: $service${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # Check if Dockerfile exists
    if [ ! -f "$service_path/Dockerfile" ]; then
        echo -e "${RED}❌ Dockerfile not found at $service_path/Dockerfile${NC}"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        FAILED_SERVICES+=("$service")
        continue
    fi

    # Build the image
    echo "🔨 Building kilo/$service:latest..."

    if docker build -t "kilo/$service:latest" \
                   -t "kilo/$service:$BUILD_TIMESTAMP" \
                   --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
                   --build-arg BUILD_TIMESTAMP="$BUILD_TIMESTAMP" \
                   -f "$service_path/Dockerfile" \
                   . ; then
        echo -e "${GREEN}✅ Built kilo/$service:latest${NC}"

        # Import to K3s if installed
        if [ "$K3S_INSTALLED" = true ]; then
            echo "📦 Importing to K3s..."

            # Save to tar
            docker save "kilo/$service:latest" -o "/tmp/kilo-$service.tar"

            # Import to K3s
            if sudo k3s ctr images import "/tmp/kilo-$service.tar"; then
                echo -e "${GREEN}✅ Imported to K3s${NC}"
                rm "/tmp/kilo-$service.tar"
            else
                echo -e "${RED}❌ Failed to import to K3s${NC}"
                FAIL_COUNT=$((FAIL_COUNT + 1))
                FAILED_SERVICES+=("$service")
                continue
            fi
        fi

        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo -e "${RED}❌ Failed to build kilo/$service${NC}"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        FAILED_SERVICES+=("$service")
    fi

    echo ""
done

# Summary
echo "========================================="
echo "📊 Build Summary"
echo "========================================="
echo -e "${GREEN}✅ Successful: $SUCCESS_COUNT${NC}"
echo -e "${RED}❌ Failed: $FAIL_COUNT${NC}"
echo ""

if [ ${#FAILED_SERVICES[@]} -gt 0 ]; then
    echo -e "${RED}Failed services:${NC}"
    for failed_service in "${FAILED_SERVICES[@]}"; do
        echo "  - $failed_service"
    done
    echo ""
fi

# Save build info
echo "$BUILD_TIMESTAMP" > "$PROJECT_ROOT/.last_build"
echo "📝 Build timestamp saved to .last_build"
echo ""

if [ "$K3S_INSTALLED" = true ]; then
    echo "========================================="
    echo "🚀 Next Steps"
    echo "========================================="
    echo ""
    echo "1. Deploy/update services:"
    echo "   ./deploy-to-k3s.sh"
    echo ""
    echo "2. Or manually restart deployments:"
    echo "   kubectl rollout restart deployment/kilo-gateway -n kilo-guardian"
    echo "   kubectl rollout restart deployment/kilo-financial -n kilo-guardian"
    echo "   # etc..."
    echo ""
else
    echo "========================================="
    echo "⚙️  Install K3s First"
    echo "========================================="
    echo ""
    echo "Run: curl -sfL https://get.k3s.io | sh -"
    echo ""
    echo "Then run this script again to import images."
    echo ""
fi

exit $FAIL_COUNT
