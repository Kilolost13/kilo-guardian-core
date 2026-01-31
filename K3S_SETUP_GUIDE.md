# Kilo Guardian - K3s Setup Guide

This guide will help you install K3s, configure kubectl access, and deploy Kilo Guardian.

## Problem We're Solving

**Issue:** When you update code in services (like Financial), the changes don't appear in K3s because:
1. Docker images are built with `:latest` tag
2. K3s caches images and doesn't pull updated versions
3. No automated build process ensures fresh images

**Solution:**
- Build all images fresh with timestamps
- Set `imagePullPolicy: Never` to use local images
- Import images directly into K3s containerd
- Restart deployments to pick up new images

---

## Prerequisites

- Ubuntu/Pop!_OS 22.04+ (or similar Linux distro)
- Docker installed and running
- Sudo access
- 4GB+ RAM available
- 20GB+ disk space

---

## Step 1: Install K3s

K3s is a lightweight Kubernetes distribution perfect for local development and edge deployments.

```bash
# Install K3s (this will take a few minutes)
curl -sfL https://get.k3s.io | sh -

# Wait for K3s to start
sudo systemctl status k3s

# Should show "active (running)"
```

**What this does:**
- Installs K3s as a systemd service
- Sets up containerd (container runtime)
- Creates kubectl config at `/etc/rancher/k3s/k3s.yaml`
- Starts a single-node Kubernetes cluster

---

## Step 2: Configure kubectl Access

By default, K3s config requires sudo. Let's fix that:

```bash
# Create .kube directory
mkdir -p ~/.kube

# Copy K3s config to your user directory
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config

# Fix ownership
sudo chown $USER:$USER ~/.kube/config

# Fix permissions (important for security)
chmod 600 ~/.kube/config

# Test kubectl access
kubectl get nodes

# You should see your node in "Ready" state
```

**Troubleshooting:**
- If `kubectl get nodes` fails, check that K3s is running: `sudo systemctl status k3s`
- If connection refused, restart K3s: `sudo systemctl restart k3s`

---

## Step 3: Verify Kubernetes MCP Server

The Kubernetes MCP server should now connect:

```bash
# Check MCP server status
claude mcp list

# You should see:
# kubernetes: npx -y kubernetes-mcp-server@latest - ✓ Connected
```

If it still shows as failed, restart your Claude Code session.

---

## Step 4: Build All Services

The new build script builds all Docker images and imports them into K3s:

```bash
cd /home/brain_ai/Desktop/AI_stuff/old_hacksaw_fingers

# Build all services (this will take 10-20 minutes first time)
./build-all-services.sh
```

**What this does:**
- Builds all 13 microservices + frontend
- Tags images with timestamp for cache busting
- Exports to tar files
- Imports into K3s containerd
- Reports success/failure for each service

**First time build notes:**
- Python dependencies will be downloaded
- npm packages will be installed
- This is normal and only slow the first time

---

## Step 5: Deploy to K3s

The deploy script applies manifests and restarts deployments:

```bash
# Full build and deploy
./deploy-to-k3s.sh

# This will:
# 1. Build fresh images (calls build-all-services.sh)
# 2. Apply K8s manifests
# 3. Restart all deployments
# 4. Wait for pods to be ready
# 5. Show status
```

**To skip the build step** (if you just built):
```bash
SKIP_BUILD=true ./deploy-to-k3s.sh
```

---

## Step 6: Verify Deployment

```bash
# Check all pods
kubectl get pods -n kilo-guardian

# You should see all services running:
# NAME                              READY   STATUS    RESTARTS
# kilo-gateway-xxx                  1/1     Running   0
# kilo-ai-brain-xxx                 1/1     Running   0
# kilo-frontend-xxx                 1/1     Running   0
# kilo-financial-xxx                1/1     Running   0
# ... etc

# Check specific service logs
kubectl logs -n kilo-guardian deployment/kilo-financial -f

# Describe a pod for troubleshooting
kubectl describe pod -n kilo-guardian <pod-name>
```

---

## Daily Workflow

### When You Update Code

```bash
cd /home/brain_ai/Desktop/AI_stuff/old_hacksaw_fingers

# Build and deploy everything
./deploy-to-k3s.sh

# Or build just one service (faster):
cd services/financial
docker build -t kilo/financial:latest -f Dockerfile ../..
docker save kilo/financial:latest -o /tmp/kilo-financial.tar
sudo k3s ctr images import /tmp/kilo-financial.tar
kubectl rollout restart deployment/kilo-financial -n kilo-guardian

# Watch it restart
kubectl get pods -n kilo-guardian -w
```

### Quick Rebuild Script (for single service)

Save this as `rebuild-service.sh`:
```bash
#!/bin/bash
SERVICE=$1
if [ -z "$SERVICE" ]; then
    echo "Usage: ./rebuild-service.sh <service-name>"
    echo "Example: ./rebuild-service.sh financial"
    exit 1
fi

echo "Building kilo/$SERVICE..."
cd "services/$SERVICE"
docker build -t "kilo/$SERVICE:latest" -f Dockerfile ../..
docker save "kilo/$SERVICE:latest" -o "/tmp/kilo-$SERVICE.tar"
sudo k3s ctr images import "/tmp/kilo-$SERVICE.tar"
kubectl rollout restart "deployment/kilo-$SERVICE" -n kilo-guardian
echo "Done! Watch with: kubectl get pods -n kilo-guardian"
```

Make it executable:
```bash
chmod +x rebuild-service.sh

# Use it:
./rebuild-service.sh financial
```

---

## Accessing Services

### NodePort Access (Direct)

Services are exposed via NodePort:

```bash
# Frontend
http://localhost:30000

# Gateway API
http://localhost:30800
```

### Port Forwarding (Alternative)

```bash
# Forward specific services to localhost
kubectl port-forward -n kilo-guardian svc/kilo-frontend 3000:80 &
kubectl port-forward -n kilo-guardian svc/kilo-gateway 8000:8000 &
kubectl port-forward -n kilo-guardian svc/kilo-financial 9005:9005 &

# Then access at:
# http://localhost:3000 (frontend)
# http://localhost:8000 (gateway)
# http://localhost:9005 (financial)

# Kill port forwards:
killall kubectl
```

### Use the start script

```bash
# The existing script still works:
cd Kilo_K3S_parts
./start-kilo-system.sh

# This sets up all port forwards automatically
```

---

## Troubleshooting

### Pod Won't Start

```bash
# Check pod status
kubectl get pods -n kilo-guardian

# Get detailed info
kubectl describe pod -n kilo-guardian <pod-name>

# Check logs
kubectl logs -n kilo-guardian <pod-name>

# Common issues:
# - ImagePullBackOff: Image not imported correctly
# - CrashLoopBackOff: Service crashing, check logs
# - Pending: Insufficient resources or scheduling issue
```

### Service Not Responding

```bash
# Check if service exists
kubectl get svc -n kilo-guardian

# Check endpoints
kubectl get endpoints -n kilo-guardian

# Test service directly
kubectl port-forward -n kilo-guardian svc/kilo-financial 9005:9005
curl http://localhost:9005/health
```

### Image Updates Not Working

```bash
# Force rebuild and reimport
./build-all-services.sh

# Delete old pods (they'll be recreated with new images)
kubectl delete pod -n kilo-guardian -l app=kilo-financial

# Or rollout restart
kubectl rollout restart deployment/kilo-financial -n kilo-guardian
```

### K3s Not Starting

```bash
# Check status
sudo systemctl status k3s

# View logs
sudo journalctl -u k3s -f

# Restart K3s
sudo systemctl restart k3s

# If completely broken, reinstall:
/usr/local/bin/k3s-uninstall.sh
curl -sfL https://get.k3s.io | sh -
```

---

## Understanding imagePullPolicy

Your K3s manifests now have `imagePullPolicy: Never` for all `kilo/*` images:

```yaml
containers:
- name: financial
  image: kilo/financial:latest
  imagePullPolicy: Never  # Always use local image, never pull
```

**Why `Never`?**
- Your images are built locally, not pushed to a registry
- K3s should always use the local image you imported
- This prevents "ImagePullBackOff" errors

**For external images** (like `ollama/ollama:latest`), we use `IfNotPresent`:
- Pull once if not present
- Use cached version afterwards

---

## Architecture Notes

### Image Flow

```
[Your Code]
    ↓
[docker build] → Docker image: kilo/financial:latest
    ↓
[docker save] → Tar file: /tmp/kilo-financial.tar
    ↓
[k3s ctr images import] → K3s containerd storage
    ↓
[kubectl rollout restart] → New pod uses updated image
```

### Why K3s Instead of Docker Compose?

**Docker Compose Issues You Had:**
- Service-to-service DNS resolution breaking
- Network connectivity issues
- No built-in health checks
- Manual restart required

**K3s Benefits:**
- Stable DNS (service.namespace.svc.cluster.local)
- Built-in load balancing
- Health checks and self-healing
- Automatic restarts on failure
- Production-grade orchestration

---

## Next Steps

1. ✅ K3s installed and running
2. ✅ kubectl configured
3. ✅ MCP server connected
4. ✅ Services built and deployed
5. 🎯 **Test the financial service updates work**

```bash
# Make a change to financial service code
vim services/financial/app.py

# Rebuild and deploy
./deploy-to-k3s.sh

# Verify the change took effect
kubectl logs -n kilo-guardian deployment/kilo-financial --tail=50
```

---

## Quick Reference Commands

```bash
# View all pods
kubectl get pods -n kilo-guardian

# View all services
kubectl get svc -n kilo-guardian

# Follow logs
kubectl logs -n kilo-guardian deployment/kilo-financial -f

# Exec into pod
kubectl exec -n kilo-guardian -it <pod-name> -- /bin/bash

# Restart deployment
kubectl rollout restart deployment/kilo-financial -n kilo-guardian

# Watch rollout
kubectl rollout status deployment/kilo-financial -n kilo-guardian

# Delete pod (forces recreation)
kubectl delete pod -n kilo-guardian <pod-name>

# Port forward
kubectl port-forward -n kilo-guardian svc/kilo-financial 9005:9005

# Full rebuild and deploy
./deploy-to-k3s.sh

# Build only (no deploy)
./build-all-services.sh
```

---

## Summary

You now have:
- ✅ K3s installed and configured
- ✅ Automated build script (`build-all-services.sh`)
- ✅ Automated deploy script (`deploy-to-k3s.sh`)
- ✅ `imagePullPolicy: Never` in all manifests
- ✅ Kubernetes MCP server connected

**The image stale problem is solved!** Every time you run `./deploy-to-k3s.sh`, it will:
1. Build fresh Docker images
2. Import them into K3s
3. Restart deployments with new images

Your changes will now always appear in K3s. 🎉
