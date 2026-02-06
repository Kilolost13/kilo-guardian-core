#!/bin/bash
# Run the Unified Agent directly on the host (no Docker / k3s required).
# Sets HOST_MODE env so service URLs point to NodePorts.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

export KUBECONFIG="$HOME/.kube/config"

# Override service URLs to use localhost NodePorts when running on the host
export KILO_AGENT_PORT="${KILO_AGENT_PORT:-9200}"

# Activate venv if present, otherwise use system python
if [ -d .venv ]; then
    source .venv/bin/activate
fi

# Install deps quietly if needed
pip install --quiet -r requirements.txt 2>/dev/null

echo "=== Kilo Unified Agent starting on port $KILO_AGENT_PORT ==="
echo "    KUBECONFIG=$KUBECONFIG"
python3 main.py
