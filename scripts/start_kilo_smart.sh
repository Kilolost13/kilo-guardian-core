#!/bin/bash

# Kilo SMART Mode Launcher (Llama 3.1 8B)
# This mode uses a smarter model for better reasoning.
# SAFETY: We limit it to 2 threads to prevent power crashes on the Beelink.

# Directory setup
cd "$(dirname "$0")"
PROJECT_ROOT=$(pwd)

# 1. Kill any existing heavy AI processes
echo "Stopping existing AI processes..."
pkill -f llama-server
pkill -f ollama
killall -9 llama-server 2>/dev/null
fuser -k 8090/tcp 2>/dev/null
fuser -k 9004/tcp 2>/dev/null
sleep 2

# 2. Start llama-server with SMART settings (Llama 3.1)
# -m: Path to the new smart model
# -ngl 0: No GPU (Safety)
# -t 2: ULTRA SAFE THREADING (Only 2 threads to handle the heavier math without spiking power)
echo "Starting llama-server (Smart Mode - Llama 3.1)..."
~/llama.cpp/build/bin/llama-server \
  -m /home/brain_ai/.lmstudio/models/unsloth/Meta-Llama-3.1-8B-Instruct-GGUF/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf \
  --port 8090 \
  -c 4096 \
  -ngl 0 \
  -t 2 \
  --ctx-size 4096 \
  > llama_server.log 2>&1 &

LLAMA_PID=$!
echo "llama-server started with PID $LLAMA_PID"

# Wait longer for the big model to load
echo "Waiting 15 seconds for Llama 3.1 to load..."
sleep 15

# 3. Start AI Brain
echo "Starting AI Brain Service..."

export OLLAMA_URL="http://localhost:8090"
export OLLAMA_MODEL="llama3.1" # Tell the brain we are using the big gun

# Ensure Python can find the modules
export PYTHONPATH=$PROJECT_ROOT:$PYTHONPATH

# Activate Virtual Environment
source $PROJECT_ROOT/venv/bin/activate

# Start the FastAPI service
$PROJECT_ROOT/venv/bin/uvicorn services.ai_brain.main:app --host 0.0.0.0 --port 9004 --reload

# Cleanup on exit
kill $LLAMA_PID
