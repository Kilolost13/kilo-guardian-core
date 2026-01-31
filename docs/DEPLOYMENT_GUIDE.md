# Kilo AI Microservice - Deployment Guide

This guide explains two deployment methods for the Kilo AI microservice system: Docker Compose and Kubernetes (k3s).

---

## Table of Contents
- [System Overview](#system-overview)
- [Docker Compose Deployment](#docker-compose-deployment)
- [Kubernetes (k3s) Deployment](#kubernetes-k3s-deployment)
- [Comparison](#comparison)
- [Migration Guide](#migration-guide)

---

## System Overview

The Kilo AI microservice system consists of 14 services:

| Service | Port | Description |
|---------|------|-------------|
| **gateway** | 8000 | API Gateway - routes requests to all services |
| **ai_brain** | 9004 | Core AI engine with LLM integration |
| **frontend** | 3000/3443 | React web interface |
| **ollama** | 11434 | LLM model runner (Llama 3.1 8B) |
| **meds** | 9001 | Medication tracking |
| **reminder** | 9002 | Reminder service |
| **habits** | 9003 | Habit tracking |
| **financial** | 9005 | Financial management |
| **library_of_truth** | 9006 | Knowledge base |
| **cam** | 9007 | Camera integration |
| **ml_engine** | 9008 | Machine learning engine |
| **voice** | 9009 | Voice (STT/TTS with Whisper/Piper) |
| **usb_transfer** | 8006 | USB device management |
| **frontend-proto** | 8080 | Prototype frontend (optional) |

---

## Docker Compose Deployment

### Prerequisites
- Docker Engine (v20.10+)
- Docker Compose (v2.0+)
- 8GB+ RAM recommended
- 50GB+ disk space

### Directory Structure
```
Kilo_Ai_microservice/
├── infra/docker/
│   ├── docker-compose.yml       # Full production setup
│   └── docker-compose.test.yml  # Lightweight test setup (no Ollama)
├── services/
│   ├── gateway/
│   ├── ai_brain/
│   ├── meds/
│   └── ... (other services)
└── frontend/
```

### Environment Setup
1. Create `.env` file in project root:
```bash
LIBRARY_ADMIN_KEY=your-secure-admin-key-here
OLLAMA_MODEL=llama3.1:8b
```

### Deployment Commands

**Start all services:**
```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice/infra/docker
docker-compose up -d
```

**View logs:**
```bash
docker-compose logs -f [service_name]
```

**Stop all services:**
```bash
docker-compose down
```

**Stop and remove volumes (WARNING: deletes data):**
```bash
docker-compose down -v
```

### Docker Compose Features

**Advantages:**
- Simple single-command deployment
- Built-in service dependencies and health checks
- Automatic container restart on failure
- Shared volumes for persistent data
- Easy local development

**Volume Management:**
Docker creates named volumes for persistent data:
- `gateway_data` - Gateway configuration
- `ai_brain_data` - AI models and cache
- `ollama_models` - Ollama model files (~4GB)
- `meds_data`, `habits_data`, `financial_data`, etc.

**Networking:**
All services run on a bridge network and can communicate via service names (e.g., `http://ai_brain:9004`).

### Health Checks
Each service has health checks defined:
```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:9004/status')"]
  interval: 10s
  timeout: 3s
  retries: 5
```

---

## Kubernetes (k3s) Deployment

### Prerequisites
- k3s installed (`curl -sfL https://get.k3s.io | sh -`)
- kubectl configured
- 8GB+ RAM recommended
- 50GB+ disk space

### Directory Structure
```
Kilo_Ai_microservice/
└── k3s/
    ├── namespace.yaml                   # kilo-guardian namespace
    ├── configmap.yaml                   # Shared configuration
    ├── secret-library-admin.yaml        # Secrets
    ├── deployments-and-services.yaml    # Core services
    ├── more-services.yaml               # Additional services
    ├── pdbs-and-hpas.yaml              # Pod disruption budgets & autoscaling
    ├── ingress.yaml                     # Ingress routing
    ├── servicemonitors.yaml             # Prometheus monitoring
    ├── prometheus-values.yaml           # Prometheus config
    └── deploy.sh                        # Automated deployment script
```

### Quick Start

**1. Install k3s (if not already installed):**
```bash
curl -sfL https://get.k3s.io | sh -
```

**2. Configure kubectl access:**
```bash
sudo mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $USER:$USER ~/.kube/config
chmod 600 ~/.kube/config
```

**3. Deploy all services:**
```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice
./k3s/deploy.sh
```

Or manually:
```bash
kubectl apply -f k3s/namespace.yaml
kubectl apply -f k3s/secret-library-admin.yaml
kubectl apply -f k3s/configmap.yaml
kubectl apply -f k3s/deployments-and-services.yaml
kubectl apply -f k3s/more-services.yaml
kubectl apply -f k3s/pdbs-and-hpas.yaml
kubectl apply -f k3s/ingress.yaml
```

### Kubernetes Features

**Advantages:**
- Production-grade orchestration
- Automatic pod rescheduling and self-healing
- Built-in service discovery and load balancing
- Horizontal pod autoscaling (HPA)
- Rolling updates with zero downtime
- Resource limits and requests
- Better monitoring integration (Prometheus)

**Architecture:**
- **Namespace:** `kilo-guardian` - isolates all resources
- **ConfigMap:** Shared environment variables
- **Secrets:** Sensitive data (admin keys, tokens)
- **Deployments:** Manage pod replicas and updates
- **Services:** Internal load balancing (ClusterIP)
- **Ingress:** External HTTP routing (via Traefik)

### Managing Deployments

**Check deployment status:**
```bash
kubectl get pods -n kilo-guardian
kubectl get deployments -n kilo-guardian
kubectl get services -n kilo-guardian
```

**View logs:**
```bash
kubectl logs -n kilo-guardian deployment/kilo-gateway -f
```

**Scale a service:**
```bash
kubectl scale deployment/kilo-gateway -n kilo-guardian --replicas=3
```

**Update an image:**
```bash
kubectl set image deployment/kilo-gateway -n kilo-guardian gateway=kilo/gateway:v2
```

**Rollback a deployment:**
```bash
kubectl rollout undo deployment/kilo-gateway -n kilo-guardian
```

**Delete all resources:**
```bash
kubectl delete namespace kilo-guardian
```

### Resource Management

Each service has defined resource limits:
```yaml
resources:
  requests:
    cpu: "100m"      # Minimum CPU
    memory: "128Mi"  # Minimum RAM
  limits:
    cpu: "500m"      # Maximum CPU
    memory: "512Mi"  # Maximum RAM
```

**AI Brain service** (higher requirements):
```yaml
resources:
  requests:
    cpu: "250m"
    memory: "512Mi"
  limits:
    cpu: "1"
    memory: "2Gi"
```

### Persistent Storage

K3s uses local-path provisioner by default. For production, you may want to configure persistent volumes:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ai-brain-data
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

### Monitoring with Prometheus

The deployment includes Prometheus setup via Helm:

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace \
  -f k3s/prometheus-values.yaml
```

Access Prometheus:
```bash
kubectl port-forward -n monitoring svc/monitoring-kube-prometheus-prometheus 9090:9090
# Open http://localhost:9090
```

---

## Comparison

| Feature | Docker Compose | Kubernetes (k3s) |
|---------|---------------|------------------|
| **Complexity** | Simple | Moderate |
| **Setup Time** | 5 minutes | 15 minutes |
| **Resource Overhead** | Low (~200MB) | Medium (~500MB) |
| **Scalability** | Single host only | Multi-node capable |
| **Auto-healing** | Container restart | Pod rescheduling |
| **Load Balancing** | None (single instance) | Built-in |
| **Rolling Updates** | Manual | Automatic |
| **Monitoring** | Basic (logs) | Advanced (Prometheus) |
| **Best For** | Development, single-server | Production, high availability |

---

## Migration Guide

### Docker to k3s Migration

**1. Export Docker images:**
```bash
docker save -o images.tar kilo/gateway:latest kilo/ai_brain:latest ...
```

**2. Import to k3s:**
```bash
sudo k3s ctr images import images.tar
```

**3. Deploy to k3s:**
```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice
./k3s/deploy.sh
```

**4. Verify deployment:**
```bash
kubectl get pods -n kilo-guardian
```

**5. Stop Docker containers:**
```bash
cd infra/docker
docker-compose down
```

### k3s to Docker Migration

**1. Export data from k3s volumes** (if needed)

**2. Stop k3s deployments:**
```bash
kubectl delete namespace kilo-guardian
```

**3. Start Docker Compose:**
```bash
cd infra/docker
docker-compose up -d
```

---

## Troubleshooting

### Docker Compose Issues

**Containers keep restarting:**
```bash
docker-compose logs [service_name]
docker inspect [container_name]
```

**Port conflicts:**
```bash
sudo netstat -tlnp | grep [port]
```

### k3s Issues

**Pods in CrashLoopBackOff:**
```bash
kubectl describe pod [pod-name] -n kilo-guardian
kubectl logs [pod-name] -n kilo-guardian
```

**Image pull errors:**
```bash
# Check if images are imported
sudo k3s crictl images
```

**Service not accessible:**
```bash
kubectl get svc -n kilo-guardian
kubectl port-forward -n kilo-guardian svc/kilo-gateway 8000:8000
```

---

## Air-Gapped Deployment Notes

Both deployment methods support air-gapped environments:

**Docker:**
- Pre-pull all images and save to tar
- Transfer tar files to air-gapped system
- Load images: `docker load -i images.tar`

**k3s:**
- Install k3s with `INSTALL_K3S_SKIP_DOWNLOAD=false`
- Pre-load images: `sudo k3s ctr images import images.tar`
- Use local registry or pre-loaded images

---

## Security Considerations

1. **Change default secrets** in `.env` and `secret-library-admin.yaml`
2. **Limit network access** with firewall rules
3. **Regular updates** for base images and dependencies
4. **Enable HTTPS** for production (use nginx/traefik with TLS)
5. **Backup volumes** regularly

---

## Support & Resources

- Project Repository: `/home/kilo/Desktop/Kilo_Ai_microservice`
- Docker Compose docs: https://docs.docker.com/compose/
- k3s documentation: https://docs.k3s.io/
- Kubernetes docs: https://kubernetes.io/docs/
