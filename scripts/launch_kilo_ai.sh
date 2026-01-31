#!/bin/bash
# Kilo AI System Launcher
# Launches all services using k3s manifests

cd "$(dirname "$0")"

# Optional: Build images if needed (uncomment if building locally)
# docker build -t kilo-frontend:latest ./frontend/kilo-react-frontend
# ...repeat for other services...

# Apply all manifests
kubectl apply -f k3s/

# Wait and show status
sleep 2
echo "--- Kilo AI System Status ---"
kubectl get pods -A
kubectl get svc -A

echo "Kilo AI System launch complete!"
