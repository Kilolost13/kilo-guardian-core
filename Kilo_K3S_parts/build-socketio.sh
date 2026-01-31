#!/bin/bash
# Build and import Socket.IO relay service

echo "Building Socket.IO relay container..."
cd /home/kilo/Desktop/Kilo_Ai_microservice/services/socketio-relay

# Build with sudo (since docker is removed, we'll use nerdctl or build manually)
# First, try to build a simple container using Python base image

echo "Creating container image..."

# Create a temporary build directory
BUILD_DIR=$(mktemp -d)
cp main.py Dockerfile "$BUILD_DIR/"
cd "$BUILD_DIR"

# Build with k3s ctr
sudo k3s ctr images pull docker.io/library/python:3.11-slim

# Create a simple tar with our files
mkdir -p socketio-relay
cp main.py socketio-relay/
cd socketio-relay

# Install dependencies locally first
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn python-socketio aiohttp

# Actually, let's just use buildah which should work
cd /home/kilo/Desktop/Kilo_Ai_microservice/services/socketio-relay

# Try buildah
if command -v buildah &> /dev/null; then
    buildah bud -t kilo/socketio-relay:latest .
    buildah push kilo/socketio-relay:latest oci-archive:socketio-relay.tar
    sudo k3s ctr images import socketio-relay.tar
else
    echo "❌ buildah not installed"
    echo "Please install with: sudo apt-get install -y buildah"
    echo "Then run this script again"
    exit 1
fi

echo "✅ Socket.IO relay container built and imported!"
