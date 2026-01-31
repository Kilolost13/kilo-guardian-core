#!/bin/bash
# Rebuild meds service with new /take endpoint

echo "========================================="
echo "Rebuilding Meds Service with /take endpoint"
echo "========================================="
echo ""

cd /home/kilo/Desktop/Kilo_Ai_microservice/services/meds

# Check if we need to install build tools
if ! command -v buildah &> /dev/null; then
    echo "Installing buildah..."
    sudo apt-get update -qq
    sudo apt-get install -y buildah
fi

echo "Building meds container..."
buildah bud -t kilo/meds:latest .

echo "Exporting to tar..."
buildah push kilo/meds:latest oci-archive:meds.tar:kilo/meds:latest

echo "Importing to k3s..."
sudo k3s ctr images import meds.tar

echo "Restarting meds deployment..."
export KUBECONFIG=~/.kube/config
kubectl rollout restart deployment/kilo-meds -n kilo-guardian

echo ""
echo "✅ Meds service rebuilt and redeployed!"
echo ""
echo "Waiting for pod to be ready..."
sleep 10
kubectl get pods -n kilo-guardian | grep meds

echo ""
echo "Test the new endpoint:"
echo "kubectl port-forward -n kilo-guardian svc/kilo-meds 9001:9001 &"
echo "curl -X POST http://localhost:9001/1/take"
