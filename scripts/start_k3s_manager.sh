#!/bin/bash
# Start K3s Manager Service on Beelink
# This gives Kilo the ability to manage the HP k3s cluster

cd "$(dirname "$0")/services/k3s_manager"

echo "Starting K3s Manager on port 9011..."
python3 main.py
