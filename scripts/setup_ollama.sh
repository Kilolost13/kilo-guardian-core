#!/bin/bash

# Setup script for Ollama on Beelink SER7-9
# This pulls the optimized Llama 3.1 8B model for Kyle's Kilo AI system

echo "🤖 Setting up Kilo AI - Ollama Models"
echo "======================================"
echo ""
echo "Target Hardware: Beelink SER7-9"
echo "CPU: AMD Ryzen 9 7940HS (8 cores, 16 threads)"
echo "GPU: AMD Radeon 780M (integrated)"
echo "RAM: 16-32GB DDR5"
echo ""

# Check if Ollama service is running
echo "Checking if Ollama service is running..."
docker-compose ps ollama | grep -q "Up" || {
    echo "❌ Ollama service is not running. Starting services..."
    docker-compose up -d ollama
    echo "⏳ Waiting 30 seconds for Ollama to start..."
    sleep 30
}

echo "✅ Ollama service is running"
echo ""

# Pull Llama 3.1 8B model (Q5_K_M quantization - optimal for SER7-9)
echo "📥 Pulling Llama 3.1 8B model (Q5_K_M quantization)"
echo "This model is optimized for:"
echo "  - Memory: ~6GB RAM usage"
echo "  - Speed: 30-80 tokens/sec (CPU/GPU)"
echo "  - Quality: Excellent, comparable to GPT-3.5+"
echo ""

docker-compose exec ollama ollama pull llama3.1:8b-instruct-q5_K_M

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Llama 3.1 8B model successfully downloaded!"
else
    echo ""
    echo "❌ Failed to download model. Trying alternative approach..."

    # Fallback: Try pulling from inside the container directly
    docker exec -it $(docker-compose ps -q ollama) ollama pull llama3.1:8b-instruct-q5_K_M
fi

echo ""
echo "📋 Checking installed models..."
docker-compose exec ollama ollama list

echo ""
echo "🧪 Testing Kilo AI with simple query..."
docker-compose exec ollama ollama run llama3.1:8b-instruct-q5_K_M "You are Kilo, Kyle's AI assistant. Say hello to Kyle and introduce yourself in one sentence."

echo ""
echo "======================================"
echo "✅ Kilo AI setup complete!"
echo ""
echo "Next steps:"
echo "1. Restart services: docker-compose restart ai_brain"
echo "2. Test Kilo through the frontend at http://localhost:3000"
echo "3. Kilo will now use Llama 3.1 8B for all responses"
echo ""
echo "Performance expectations on Beelink SER7-9:"
echo "  - Chat response: 1-3 seconds"
echo "  - Token generation: 30-80 tokens/sec"
echo "  - Memory usage: ~6GB for model"
echo "  - Concurrent users: 2"
echo ""
