#!/bin/bash
# Create kubectl symlink for k3s

sudo ln -sf /usr/local/bin/k3s /usr/local/bin/kubectl
echo "kubectl symlink created!"
echo "Testing..."
kubectl get pods -n kilo-guardian
