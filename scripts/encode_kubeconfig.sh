#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 /path/to/kubeconfig"
  exit 1
fi

KUBECONFIG_FILE=$1
if [ ! -f "$KUBECONFIG_FILE" ]; then
  echo "File not found: $KUBECONFIG_FILE"
  exit 1
fi

# Optionally replace 127.0.0.1 with public IP (prompt the user)
read -p "(Optional) If kubeconfig references 127.0.0.1, enter <node-ip> or press Enter to skip: " NODE_IP
if [ -n "$NODE_IP" ]; then
  sed "s/127.0.0.1/$NODE_IP/g" "$KUBECONFIG_FILE" | base64 -w0
else
  base64 -w0 "$KUBECONFIG_FILE"
fi
