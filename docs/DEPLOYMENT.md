# Kilo Guardian - K3s Deployment Documentation
**Complete guide for deploying and managing Kilo Guardian on K3s**

Last Updated: 2026-01-04
Current Status: ✅ Production Ready

---

## System Overview

Kilo Guardian runs on K3s (lightweight Kubernetes) with 15 microservices deployed in the `kilo-guardian` namespace.

**Current Deployment:**
- **Platform:** K3s on Pop!_OS 22.04 LTS
- **Namespace:** kilo-guardian
- **Total Pods:** 15
- **Network:** 10.42.0.0/16 (K3s Pod Network)
- **Storage:** Local persistent volumes

---

## Prerequisites

### System Requirements

**Minimum:**
- CPU: 4 cores
- RAM: 8GB
- Disk: 100GB SSD
- OS: Ubuntu/Debian/Pop!_OS

**Recommended:**
- CPU: 8+ cores
- RAM: 16GB
- Disk: 256GB NVMe SSD
- OS: Pop!_OS 22.04 LTS

### Software Requirements

```bash
# K3s (automatically installs kubectl)
curl -sfL https://get.k3s.io | sh -

# Verify installation
sudo systemctl status k3s
kubectl get nodes
```

---

## Initial Setup

### 1. Install K3s

```bash
# Install K3s with default options
curl -sfL https://get.k3s.io | sh -

# Configure kubectl for non-root access
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $(whoami):$(whoami) ~/.kube/config
export KUBECONFIG=~/.kube/config

# Add to .bashrc for persistence
echo 'export KUBECONFIG=~/.kube/config' >> ~/.bashrc
```

### 2. Verify K3s Installation

```bash
# Check cluster status
kubectl cluster-info

# Check nodes
kubectl get nodes

# Expected: 1 node in Ready status
```

### 3. Create Namespace

```bash
kubectl create namespace kilo-guardian
```

---

## Deployment Process

### Option 1: Deploy from Manifests (Recommended)

```bash
# Navigate to K3s manifests directory
cd /home/kilo/Desktop/Kilo_Ai_microservice/k3s

# Apply all manifests
kubectl apply -f . -n kilo-guardian

# Watch pods come online
watch kubectl get pods -n kilo-guardian
```

**Expected:** All 15 pods transition to `Running` status within 2-3 minutes.

### Option 2: Deploy Individual Services

```bash
# Deploy in order (if dependencies matter):

# 1. Core infrastructure
kubectl apply -f configmaps/ -n kilo-guardian
kubectl apply -f secrets/ -n kilo-guardian

# 2. Backend services
kubectl apply -f deployments/gateway.yaml -n kilo-guardian
kubectl apply -f deployments/meds.yaml -n kilo-guardian
kubectl apply -f deployments/reminder.yaml -n kilo-guardian
kubectl apply -f deployments/habits.yaml -n kilo-guardian
kubectl apply -f deployments/financial.yaml -n kilo-guardian
kubectl apply -f deployments/ai-brain.yaml -n kilo-guardian
kubectl apply -f deployments/library.yaml -n kilo-guardian
kubectl apply -f deployments/ml-engine.yaml -n kilo-guardian
kubectl apply -f deployments/ollama.yaml -n kilo-guardian
kubectl apply -f deployments/cam.yaml -n kilo-guardian
kubectl apply -f deployments/voice.yaml -n kilo-guardian
kubectl apply -f deployments/usb-transfer.yaml -n kilo-guardian
kubectl apply -f deployments/socketio.yaml -n kilo-guardian

# 3. Frontend
kubectl apply -f deployments/frontend.yaml -n kilo-guardian

# 4. Services (networking)
kubectl apply -f services/ -n kilo-guardian
```

---

## Service Architecture

### Network Topology

```
External (NodePort)
├─► 30000 → kilo-frontend (React UI)
└─► 30800 → kilo-gateway (API)

Internal (ClusterIP)
├─► kilo-gateway:8000        ──► Routes to all backends
├─► kilo-ai-brain:9004       ──► AI/RAG engine
├─► kilo-meds:9001           ──► Medication tracking
├─► kilo-meds-v2:9001        ──► Updated medications
├─► kilo-reminder:9002       ──► Reminders & timeline
├─► kilo-habits:9003         ──► Habit tracking
├─► kilo-financial:9005      ──► Financial management
├─► kilo-library:9006        ──► Knowledge base
├─► kilo-cam:9007            ──► Camera & pose detection
├─► kilo-ml-engine:9008      ──► ML processing
├─► kilo-voice:9009          ──► Voice input
├─► kilo-socketio:9010       ──► Real-time events
├─► kilo-usb-transfer:8006   ──► File transfer
└─► kilo-ollama:11434        ──► Local LLM
```

### Service Dependencies

```
kilo-frontend
  └─► kilo-gateway
       ├─► kilo-meds
       ├─► kilo-reminder
       ├─► kilo-habits
       ├─► kilo-financial
       ├─► kilo-library
       ├─► kilo-ai-brain
       │    └─► kilo-ollama
       ├─► kilo-ml-engine
       ├─► kilo-cam
       ├─► kilo-voice
       ├─► kilo-socketio
       └─► kilo-usb-transfer
```

---

## Post-Deployment Verification

### 1. Check Pod Status

```bash
kubectl get pods -n kilo-guardian
```

**Expected Output:**
- All pods: `1/1 READY`
- Status: `Running`
- Restarts: Low (< 5)

### 2. Check Services

```bash
kubectl get svc -n kilo-guardian
```

**Expected:** 15 services listed with proper IPs.

### 3. Test Connectivity

```bash
# Test frontend
curl http://localhost:30000

# Test gateway
curl http://localhost:30800/meds/

# Run comprehensive test
/home/kilo/test-services.sh
```

### 4. View Logs

```bash
# Gateway logs (check for errors)
kubectl logs deployment/kilo-gateway -n kilo-guardian --tail=50

# AI Brain logs
kubectl logs deployment/kilo-ai-brain -n kilo-guardian --tail=50
```

---

## Configuration Management

### Environment Variables

Managed via Kubernetes Secrets and ConfigMaps.

#### Create Secrets

```bash
# API keys
kubectl create secret generic kilo-secrets \
  --from-literal=library-admin-key='your-secure-key' \
  -n kilo-guardian

# Ollama model config
kubectl create configmap ollama-config \
  --from-literal=model='llama3.1:8b' \
  -n kilo-guardian
```

#### Update Secrets

```bash
# Edit existing secret
kubectl edit secret kilo-secrets -n kilo-guardian

# Or delete and recreate
kubectl delete secret kilo-secrets -n kilo-guardian
kubectl create secret generic kilo-secrets --from-literal=...
```

### Persistent Storage

Services use local storage via hostPath volumes:

```yaml
volumes:
  - name: data
    hostPath:
      path: /var/lib/kilo-guardian/<service-name>
      type: DirectoryOrCreate
```

**Backup Locations:**
- Medications: `/var/lib/kilo-guardian/meds/`
- Financial: `/var/lib/kilo-guardian/financial/`
- AI Brain: `/var/lib/kilo-guardian/ai-brain/`

---

## Updating Services

### Rolling Update

```bash
# Update service image
kubectl set image deployment/kilo-frontend \
  frontend=my-repo/kilo-frontend:v2.0 \
  -n kilo-guardian

# Watch rollout
kubectl rollout status deployment/kilo-frontend -n kilo-guardian
```

### Zero-Downtime Update

```bash
# K3s automatically does rolling updates
# Default strategy:
# - maxUnavailable: 0
# - maxSurge: 1

kubectl apply -f deployments/kilo-frontend.yaml -n kilo-guardian
```

### Rollback

```bash
# Undo last deployment
kubectl rollout undo deployment/kilo-frontend -n kilo-guardian

# Rollback to specific revision
kubectl rollout undo deployment/kilo-frontend \
  --to-revision=2 \
  -n kilo-guardian
```

---

## Scaling

### Manual Scaling

```bash
# Scale ML engine to 3 replicas
kubectl scale deployment/kilo-ml-engine \
  --replicas=3 \
  -n kilo-guardian

# Scale back to 1
kubectl scale deployment/kilo-ml-engine \
  --replicas=1 \
  -n kilo-guardian
```

### Auto-Scaling (Advanced)

```bash
# Horizontal Pod Autoscaler (requires metrics-server)
kubectl autoscale deployment/kilo-ml-engine \
  --cpu-percent=70 \
  --min=1 \
  --max=5 \
  -n kilo-guardian
```

---

## Backup & Restore

### Backup Procedure

```bash
#!/bin/bash
# backup-kilo-guardian.sh

BACKUP_DIR="/home/kilo/backups/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup all K3s manifests
cp -r /home/kilo/Desktop/Kilo_Ai_microservice/k3s "$BACKUP_DIR/"

# Backup database files from pods
for service in kilo-meds kilo-financial kilo-habits kilo-reminder; do
  POD=$(kubectl get pod -l app=$service -n kilo-guardian -o jsonpath='{.items[0].metadata.name}')
  kubectl exec $POD -n kilo-guardian -- tar -czf - /app/data > "$BACKUP_DIR/${service}-data.tar.gz"
done

echo "Backup complete: $BACKUP_DIR"
```

### Restore Procedure

```bash
#!/bin/bash
# restore-kilo-guardian.sh

BACKUP_DIR="/home/kilo/backups/20260104-120000"

# Restore manifests
kubectl delete namespace kilo-guardian
kubectl create namespace kilo-guardian
kubectl apply -f "$BACKUP_DIR/k3s/" -n kilo-guardian

# Wait for pods to start
sleep 60

# Restore data to pods
for service in kilo-meds kilo-financial kilo-habits kilo-reminder; do
  POD=$(kubectl get pod -l app=$service -n kilo-guardian -o jsonpath='{.items[0].metadata.name}')
  cat "$BACKUP_DIR/${service}-data.tar.gz" | kubectl exec -i $POD -n kilo-guardian -- tar -xzf - -C /
done
```

---

## Disaster Recovery

### Complete System Recovery

1. **Reinstall K3s:**
   ```bash
   curl -sfL https://get.k3s.io | sh -
   ```

2. **Recreate namespace:**
   ```bash
   kubectl create namespace kilo-guardian
   ```

3. **Apply manifests:**
   ```bash
   kubectl apply -f k3s/ -n kilo-guardian
   ```

4. **Restore data from backup**

5. **Verify system:**
   ```bash
   kubectl get pods -n kilo-guardian
   curl http://localhost:30000
   ```

---

## Security Hardening

### Network Policies

```yaml
# Restrict frontend to only talk to gateway
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-policy
  namespace: kilo-guardian
spec:
  podSelector:
    matchLabels:
      app: kilo-frontend
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: kilo-gateway
```

### RBAC

```yaml
# Create service account with limited permissions
apiVersion: v1
kind: ServiceAccount
metadata:
  name: kilo-sa
  namespace: kilo-guardian
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: kilo-role
  namespace: kilo-guardian
rules:
- apiGroups: [""]
  resources: ["pods", "services"]
  verbs: ["get", "list"]
```

### Pod Security

```yaml
# Run as non-root user
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000
  capabilities:
    drop:
    - ALL
```

---

## Monitoring

### Built-in Monitoring

```bash
# Resource usage
kubectl top pods -n kilo-guardian
kubectl top nodes

# Events
kubectl get events -n kilo-guardian --sort-by='.lastTimestamp'

# Logs
kubectl logs -f deployment/kilo-gateway -n kilo-guardian
```

### Install Metrics Server (Optional)

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

---

## Troubleshooting

### Pods Not Starting

```bash
# Check pod status
kubectl describe pod <pod-name> -n kilo-guardian

# Check events
kubectl get events -n kilo-guardian

# Check logs
kubectl logs <pod-name> -n kilo-guardian
```

### Network Issues

```bash
# Test pod-to-pod connectivity
kubectl exec deployment/kilo-gateway -n kilo-guardian -- ping kilo-meds

# Check DNS
kubectl exec deployment/kilo-gateway -n kilo-guardian -- nslookup kilo-meds
```

### Resource Issues

```bash
# Check resource usage
kubectl top pods -n kilo-guardian

# Check limits
kubectl describe pod <pod-name> -n kilo-guardian | grep -A 5 "Limits"
```

---

## Best Practices

1. **Always use manifests** - Version control your YAML files
2. **Test in staging first** - Never deploy untested changes
3. **Monitor resource usage** - Prevent resource exhaustion
4. **Keep backups** - Daily backups of critical data
5. **Document changes** - Update docs when you modify configs
6. **Use labels consistently** - Makes management easier
7. **Implement health checks** - Ensure service reliability
8. **Limit resource requests** - Prevent resource hogging

---

## Next Steps

1. **Production Checklist:**
   - [ ] Configure automated backups
   - [ ] Set up monitoring alerts
   - [ ] Implement network policies
   - [ ] Enable RBAC
   - [ ] Document recovery procedures
   - [ ] Test disaster recovery

2. **Optimization:**
   - [ ] Tune resource limits
   - [ ] Implement caching
   - [ ] Enable horizontal pod autoscaling
   - [ ] Optimize database queries

3. **Security:**
   - [ ] Rotate secrets regularly
   - [ ] Audit access logs
   - [ ] Scan images for vulnerabilities
   - [ ] Implement pod security policies

---

## Additional Resources

- [Operations Guide](OPERATIONS.md) - Daily operations
- [Tablet Access](TABLET_ACCESS.md) - Remote access setup
- [Pod Health Report](POD_HEALTH_REPORT.md) - Current status
- [Service Communication Test](SERVICE_COMMUNICATION_TEST.md) - Connectivity verification

---

**Kilo Guardian K3s Deployment - Production Ready! 🚀**
