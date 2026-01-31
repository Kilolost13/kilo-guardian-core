#!/usr/bin/env bash
set -euo pipefail

# Kilo Guardian - Complete Build and Deploy Script
# This script builds fresh images and deploys them to K3s

PROJECT_ROOT="/home/brain_ai/Desktop/AI_stuff/old_hacksaw_fingers"
cd "$PROJECT_ROOT"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "========================================="
echo "🚀 Kilo Guardian - Full Deployment"
echo "========================================="
echo ""

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found${NC}"
    exit 1
fi

if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl not found${NC}"
    exit 1
fi

if ! command -v k3s &> /dev/null; then
    echo -e "${RED}❌ K3s not installed${NC}"
    echo ""
    echo "Install K3s with:"
    echo "  curl -sfL https://get.k3s.io | sh -"
    echo ""
    echo "Then configure kubectl:"
    echo "  mkdir -p ~/.kube"
    echo "  sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config"
    echo "  sudo chown \$USER:\$USER ~/.kube/config"
    exit 1
fi

# Check if K3s is running
if ! systemctl is-active --quiet k3s; then
    echo -e "${RED}❌ K3s service is not running${NC}"
    echo "Start it with: sudo systemctl start k3s"
    exit 1
fi

# Check kubectl access
if ! kubectl version --short >/dev/null 2>&1; then
    echo -e "${RED}❌ kubectl cannot reach cluster${NC}"
    echo ""
    echo "Configure kubectl with:"
    echo "  mkdir -p ~/.kube"
    echo "  sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config"
    echo "  sudo chown \$USER:\$USER ~/.kube/config"
    exit 1
fi

echo -e "${GREEN}✅ All prerequisites met${NC}"
echo ""

# Option to skip build
SKIP_BUILD=${SKIP_BUILD:-false}

if [ "$SKIP_BUILD" != "true" ]; then
    echo "========================================="
    echo "🔨 Step 1: Building Fresh Images"
    echo "========================================="
    echo ""

    if [ -f "$PROJECT_ROOT/build-all-services.sh" ]; then
        "$PROJECT_ROOT/build-all-services.sh"

        if [ $? -ne 0 ]; then
            echo -e "${RED}❌ Build failed. Aborting deployment.${NC}"
            exit 1
        fi
    else
        echo -e "${YELLOW}⚠️  build-all-services.sh not found, skipping build${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  SKIP_BUILD=true, using existing images${NC}"
    echo ""
fi

echo "========================================="
echo "🚢 Step 2: Deploying to K3s"
echo "========================================="
echo ""

NS="kilo-guardian"

# Apply manifests
echo "📦 Applying Kubernetes manifests..."
echo ""

# Create namespace
kubectl apply -f "$PROJECT_ROOT/k3s/namespace.yaml"

# Apply secrets and config
kubectl apply -f "$PROJECT_ROOT/k3s/secret-library-admin.yaml" -n "$NS" || echo "Secret may already exist"
kubectl apply -f "$PROJECT_ROOT/k3s/configmap.yaml" -n "$NS"

# Apply deployments and services
kubectl apply -f "$PROJECT_ROOT/k3s/deployments-and-services.yaml" -n "$NS"
kubectl apply -f "$PROJECT_ROOT/k3s/more-services.yaml" -n "$NS"

# Apply other resources
kubectl apply -f "$PROJECT_ROOT/k3s/pdbs-and-hpas.yaml" -n "$NS" || echo "PDBs/HPAs may not apply yet"
kubectl apply -f "$PROJECT_ROOT/k3s/ingress.yaml" -n "$NS" || echo "Ingress may not apply yet"

echo ""
echo -e "${GREEN}✅ Manifests applied${NC}"
echo ""

# Force image refresh by restarting deployments
echo "========================================="
echo "🔄 Step 3: Restarting Deployments"
echo "========================================="
echo ""

DEPLOYMENTS=(
    "kilo-gateway"
    "kilo-ai-brain"
    "kilo-frontend"
    "kilo-ollama"
    "kilo-meds"
    "kilo-reminder"
    "kilo-habits"
    "kilo-financial"
    "kilo-ml-engine"
    "kilo-usb-transfer"
    "kilo-library"
    "kilo-cam"
    "kilo-voice"
    "kilo-socketio"
)

for deployment in "${DEPLOYMENTS[@]}"; do
    if kubectl get deployment "$deployment" -n "$NS" &>/dev/null; then
        echo "🔄 Restarting $deployment..."
        kubectl rollout restart deployment/"$deployment" -n "$NS"
    else
        echo -e "${YELLOW}⚠️  Deployment $deployment not found, skipping${NC}"
    fi
done

echo ""
echo -e "${GREEN}✅ Deployments restarted${NC}"
echo ""

# Wait for deployments to be ready
echo "========================================="
echo "⏳ Step 4: Waiting for Pods"
echo "========================================="
echo ""

echo "Waiting for pods to be ready (this may take a minute)..."
sleep 10

kubectl wait --for=condition=ready pod \
    --selector=app \
    --namespace="$NS" \
    --timeout=120s || echo "Some pods may still be starting..."

echo ""

# Show status
echo "========================================="
echo "📊 Deployment Status"
echo "========================================="
echo ""

kubectl get pods -n "$NS" -o wide

echo ""
echo "========================================="
echo "✅ Deployment Complete!"
echo "========================================="
echo ""

TOTAL_PODS=$(kubectl get pods -n "$NS" --no-headers 2>/dev/null | wc -l)
READY_PODS=$(kubectl get pods -n "$NS" --no-headers 2>/dev/null | grep "1/1.*Running" | wc -l)

echo "📊 Status: $READY_PODS/$TOTAL_PODS pods ready"
echo ""

if [ "$READY_PODS" -eq "$TOTAL_PODS" ] && [ "$TOTAL_PODS" -gt 0 ]; then
    echo -e "${GREEN}🎉 All services are running!${NC}"
else
    echo -e "${YELLOW}⚠️  Some services are still starting. Check with:${NC}"
    echo "   kubectl get pods -n $NS"
    echo "   kubectl logs -n $NS deployment/kilo-gateway"
fi

echo ""
echo "========================================="
echo "🌐 Access Information"
echo "========================================="
echo ""
echo "NodePort Services (direct access):"
echo "  🌐 Frontend:  http://localhost:30000"
echo "  🌉 Gateway:   http://localhost:30800"
echo ""
echo "Or use port forwarding:"
echo "  kubectl port-forward -n $NS svc/kilo-frontend 3000:80"
echo "  kubectl port-forward -n $NS svc/kilo-gateway 8000:8000"
echo ""
echo "========================================="
echo "📖 Useful Commands"
echo "========================================="
echo ""
echo "  View pods:          kubectl get pods -n $NS"
echo "  View logs:          kubectl logs -n $NS deployment/kilo-financial -f"
echo "  Describe pod:       kubectl describe pod -n $NS <pod-name>"
echo "  Exec into pod:      kubectl exec -n $NS -it <pod-name> -- /bin/bash"
echo "  Restart service:    kubectl rollout restart deployment/kilo-financial -n $NS"
echo ""
echo "  Rebuild & redeploy: ./deploy-to-k3s.sh"
echo "  Build only:         ./build-all-services.sh"
echo ""
