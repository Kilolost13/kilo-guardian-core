#!/bin/bash
# Rebuild and deploy AI Brain with tools support

set -e

echo "🔧 Rebuilding Kilo AI Brain with Tools Support"
echo "=============================================="
echo ""

# Build Docker image
echo "📦 Building Docker image..."
cd /home/brain_ai/projects/kilo

# Build with project root as context (needed for shared models)
docker build \
  -t kilo-ai-brain:tools-v1 \
  -f services/ai_brain/Dockerfile \
  .

if [ $? -ne 0 ]; then
    echo "❌ Docker build failed"
    exit 1
fi

echo "✅ Docker image built successfully"
echo ""

# Tag and push to local registry
echo "🚀 Pushing to HP server registry..."
docker tag kilo-ai-brain:tools-v1 192.168.68.56:5000/kilo-ai-brain:tools-v1
docker push 192.168.68.56:5000/kilo-ai-brain:tools-v1

if [ $? -ne 0 ]; then
    echo "❌ Failed to push to registry"
    exit 1
fi

echo "✅ Image pushed to registry"
echo ""

# Deploy to K3s
echo "☸️  Deploying to K3s..."
ssh kilo@192.168.68.56 'sudo kubectl set image deployment/kilo-ai-brain -n kilo-guardian kilo-ai-brain=192.168.68.56:5000/kilo-ai-brain:tools-v1'

if [ $? -ne 0 ]; then
    echo "❌ K3s deployment failed"
    exit 1
fi

echo "✅ Deployment updated"
echo ""

# Wait for rollout
echo "⏳ Waiting for rollout..."
ssh kilo@192.168.68.56 'sudo kubectl rollout status deployment/kilo-ai-brain -n kilo-guardian --timeout=120s'

if [ $? -ne 0 ]; then
    echo "❌ Rollout failed"
    exit 1
fi

echo "✅ Rollout complete"
echo ""

# Check pod status
echo "🔍 Checking pod status..."
ssh kilo@192.168.68.56 'sudo kubectl get pods -n kilo-guardian -l app=kilo-ai-brain'

echo ""
echo "=============================================="
echo "✅ AI Brain with Tools deployed successfully!"
echo ""
echo "Test with:"
echo "  curl -X POST http://192.168.68.56:9004/chat \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"user\":\"kyle\",\"message\":\"Check the K3s cluster\",\"context\":[]}'"
echo ""
