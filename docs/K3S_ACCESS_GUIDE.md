# k3s Services - Access & Testing Guide

## Current Service Status

**✅ Healthy Services (9):**
- ai_brain, financial, frontend, library, ml_engine, ollama, reminder, usb_transfer, voice

**⚠️ Need Attention (4):**
- cam, gateway, habits, meds (failing health checks, need investigation)

---

## How to Access Your Services

### Method 1: Port Forwarding (Recommended for Testing)

**Access the Frontend (Web UI):**
```bash
kubectl port-forward -n kilo-guardian svc/kilo-frontend 3000:80
# Then open in browser: http://localhost:3000
```

**Access AI Brain API:**
```bash
kubectl port-forward -n kilo-guardian svc/kilo-ai-brain 9004:9004
# Then test: curl http://localhost:9004/status
```

**Access Gateway (when fixed):**
```bash
kubectl port-forward -n kilo-guardian svc/kilo-gateway 8000:8000
# Then open: http://localhost:8000
```

**Access Ollama:**
```bash
kubectl port-forward -n kilo-guardian svc/kilo-ollama 11434:11434
# Then test: curl http://localhost:11434/api/tags
```

**Access Library of Truth:**
```bash
kubectl port-forward -n kilo-guardian svc/kilo-library 9006:9006
# Test: curl http://localhost:9006/status
```

---

## Testing Commands

### 1. Check All Pod Status
```bash
kubectl get pods -n kilo-guardian
```

### 2. Check Specific Service Logs
```bash
# View live logs
kubectl logs -n kilo-guardian deployment/kilo-ai-brain -f

# View last 50 lines
kubectl logs -n kilo-guardian deployment/kilo-frontend --tail=50

# View logs from a specific pod
kubectl logs -n kilo-guardian kilo-ollama-xxxxx
```

### 3. Check Service Endpoints
```bash
kubectl get svc -n kilo-guardian
kubectl get endpoints -n kilo-guardian
```

### 4. Test Service Connectivity (from inside cluster)
```bash
# Run a test pod
kubectl run test-pod -n kilo-guardian --image=curlimages/curl:latest -i --tty --rm -- sh

# Inside the test pod, test services:
curl http://kilo-ai-brain:9004/status
curl http://kilo-library:9006/status
curl http://kilo-frontend:80/
exit
```

### 5. Check Pod Details
```bash
kubectl describe pod -n kilo-guardian kilo-frontend-xxxxx
```

### 6. Execute Commands in a Pod
```bash
kubectl exec -n kilo-guardian -it kilo-ai-brain-xxxxx -- /bin/sh
```

---

## Quick Service Tests

### Test AI Brain
```bash
# Port forward
kubectl port-forward -n kilo-guardian svc/kilo-ai-brain 9004:9004 &

# Test the endpoint
curl http://localhost:9004/status
curl http://localhost:9004/health

# Stop port forward
killall kubectl
```

### Test Frontend
```bash
# Port forward
kubectl port-forward -n kilo-guardian svc/kilo-frontend 3000:80 &

# Open in browser or test with curl
curl -I http://localhost:3000

# Stop port forward
killall kubectl
```

### Test Library of Truth
```bash
kubectl port-forward -n kilo-guardian svc/kilo-library 9006:9006 &
curl http://localhost:9006/status
killall kubectl
```

### Test Ollama (LLM)
```bash
kubectl port-forward -n kilo-guardian svc/kilo-ollama 11434:11434 &
curl http://localhost:11434/api/tags
killall kubectl
```

---

## Common Troubleshooting

### Pod Won't Start
```bash
# Check pod events
kubectl describe pod -n kilo-guardian <pod-name>

# Check logs
kubectl logs -n kilo-guardian <pod-name>

# Check previous logs (if crashed)
kubectl logs -n kilo-guardian <pod-name> --previous
```

### Service Not Accessible
```bash
# Check if service exists
kubectl get svc -n kilo-guardian kilo-frontend

# Check endpoints
kubectl get endpoints -n kilo-guardian kilo-frontend

# Test from within cluster
kubectl run test -n kilo-guardian --rm -i --tty --image=curlimages/curl -- curl http://kilo-frontend:80
```

### Health Check Failing
```bash
# Check readiness/liveness probes
kubectl describe pod -n kilo-guardian <pod-name> | grep -A 10 "Liveness\|Readiness"

# View pod logs for health check errors
kubectl logs -n kilo-guardian <pod-name> --tail=100
```

---

## Accessing Multiple Services at Once

Create a script to forward all ports:

```bash
#!/bin/bash
# save as ~/forward-all-ports.sh

kubectl port-forward -n kilo-guardian svc/kilo-frontend 3000:80 &
kubectl port-forward -n kilo-guardian svc/kilo-gateway 8000:8000 &
kubectl port-forward -n kilo-guardian svc/kilo-ai-brain 9004:9004 &
kubectl port-forward -n kilo-guardian svc/kilo-library 9006:9006 &
kubectl port-forward -n kilo-guardian svc/kilo-ollama 11434:11434 &

echo "All services forwarded!"
echo "Frontend: http://localhost:3000"
echo "Gateway: http://localhost:8000"
echo "AI Brain: http://localhost:9004"
echo "Library: http://localhost:9006"
echo "Ollama: http://localhost:11434"
echo ""
echo "Press Ctrl+C to stop all forwards, then run: killall kubectl"
wait
```

Make it executable and run:
```bash
chmod +x ~/forward-all-ports.sh
~/forward-all-ports.sh
```

To stop all port forwards:
```bash
killall kubectl
```

---

## Monitoring

### Watch Pod Status in Real-Time
```bash
watch -n 2 'kubectl get pods -n kilo-guardian'
```

### Stream All Logs
```bash
# Install stern (optional)
# brew install stern  # on macOS
# Or use kubectl directly

kubectl logs -n kilo-guardian -l app=kilo-ai-brain -f
```

### Check Resource Usage
```bash
kubectl top pods -n kilo-guardian
kubectl top nodes
```

---

## Restart Services

### Restart a Deployment
```bash
kubectl rollout restart deployment/kilo-frontend -n kilo-guardian
```

### Delete and Recreate a Pod
```bash
kubectl delete pod -n kilo-guardian kilo-frontend-xxxxx
# A new pod will be created automatically
```

### Scale a Service
```bash
# Scale up
kubectl scale deployment/kilo-ai-brain -n kilo-guardian --replicas=2

# Scale down
kubectl scale deployment/kilo-ai-brain -n kilo-guardian --replicas=1
```

---

## Useful Aliases

Add to your `~/.bashrc`:

```bash
alias k='kubectl'
alias kgp='kubectl get pods -n kilo-guardian'
alias kgs='kubectl get svc -n kilo-guardian'
alias klogs='kubectl logs -n kilo-guardian'
alias kdesc='kubectl describe -n kilo-guardian'
alias kexec='kubectl exec -n kilo-guardian -it'
```

Then reload:
```bash
source ~/.bashrc
```

---

## Next Steps to Fix Remaining Services

### Gateway, Habits, Meds, Cam
These services are running but failing health checks. To investigate:

```bash
# Check logs
kubectl logs -n kilo-guardian deployment/kilo-gateway --tail=100

# Check health probe configuration
kubectl describe deployment -n kilo-guardian kilo-gateway | grep -A 5 "Liveness\|Readiness"

# Try accessing directly (port forward and test)
kubectl port-forward -n kilo-guardian svc/kilo-gateway 8000:8000
curl http://localhost:8000/status
```

The issue is likely:
1. Health check endpoints don't exist (e.g., /health or /status)
2. Services take too long to start (increase initialDelaySeconds)
3. Service dependencies aren't ready yet

---

## Production Tips

1. **Use Ingress** for external access instead of port-forwarding
2. **Set up monitoring** with Prometheus/Grafana
3. **Configure persistent volumes** for data that needs to survive pod restarts
4. **Enable autoscaling** with HPA for high-traffic services
5. **Set resource limits** to prevent resource exhaustion

---

## Emergency Commands

### Delete Everything and Start Over
```bash
kubectl delete namespace kilo-guardian
# Then redeploy using deploy.sh
```

### Get All Resources
```bash
kubectl get all -n kilo-guardian
```

### Export Current Config
```bash
kubectl get all -n kilo-guardian -o yaml > kilo-backup.yaml
```
