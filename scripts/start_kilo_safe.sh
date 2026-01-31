#!/bin/bash

# Kilo Safe Mode Launcher (Beelink Friendly)
# This script launches the Kilo AI Agent using a lightweight, power-safe configuration.
# It uses llama.cpp with the Phi-3 model instead of Ollama to prevent crashes.

# Directory setup
cd "$(dirname "$0")"
PROJECT_ROOT=$(pwd)

# 1. Kill any existing heavy AI processes to ensure safety
echo "Stopping any existing AI processes and clearing ports..."
pkill -f llama-server
pkill -f ollama
killall -9 llama-server 2>/dev/null
# Force kill anything on port 8090 or 9004
fuser -k 8090/tcp 2>/dev/null
fuser -k 9004/tcp 2>/dev/null
sleep 2

# 2. Start llama-server with SAFE settings (CPU only, limited threads)
# -ngl 0: No GPU offload (prevents voltage spikes)
# -t 4: Limit to 4 threads (prevents CPU power spikes)
echo "Starting llama-server (Safe Mode)..."
~/llama.cpp/build/bin/llama-server \
  -m /home/brain_ai/.lmstudio/models/microsoft/Phi-3-mini-4k-instruct-GGUF/Phi-3-mini-4k-instruct-q4.gguf \
  --port 8090 \
  -c 4096 \
  -ngl 0 \
  -t 4 \
  --ctx-size 4096 \
  > llama_server.log 2>&1 &

LLAMA_PID=$!
echo "llama-server started with PID $LLAMA_PID"

# Wait for server to be ready
echo "Waiting 10 seconds for llama-server to initialize..."
sleep 10

# 3. Start AI Brain
echo "Starting AI Brain Service..."

# Configure AI Brain to use our local llama-server
export OLLAMA_URL="http://localhost:8090"
export LLM_PROVIDER="ollama"
export OLLAMA_MODEL="phi3"

# Ensure Python can find the modules
export PYTHONPATH=$PROJECT_ROOT:$PYTHONPATH

# Activate Virtual Environment
source $PROJECT_ROOT/venv/bin/activate

# Start the FastAPI service using the venv uvicorn
$PROJECT_ROOT/venv/bin/uvicorn services.ai_brain.main:app --host 0.0.0.0 --port 9004 --reload

# Cleanup on exit
kill $LLAMA_PID
