# Kilo Hybrid Architecture - Setup Complete

## 🎯 Current Architecture (Option C - Hybrid)

```
┌────────────────────────────────┐
│   BEELINK (192.168.68.60)      │
│   - Kilo codebase              │
│   - llama.cpp (TODO)           │
│   - kubectl client ✓           │
│   - Manages HP k3s remotely ✓  │
└────────────────────────────────┘
                 │
                 │ kubectl over port 6443
                 ▼
┌────────────────────────────────┐
│   HP (192.168.68.56)           │
│   K3S Cluster Running:         │
│   ✓ kilo-ai-brain              │
│   ✓ kilo-frontend              │
│   ✓ kilo-gateway               │
│   ✓ kilo-financial             │
│   ✓ kilo-habits                │
│   ✓ kilo-meds                  │
│   ✓ kilo-reminder              │
│   ✓ kilo-library               │
│   ✓ monitoring (Grafana)       │
└────────────────────────────────┘
```

## 🌐 Access Points

Access these from **any browser on your network**:

- **Kilo Frontend**: http://192.168.68.56:30001
- **Kilo Gateway API**: http://192.168.68.56:30801
- **Grafana Dashboard**: http://192.168.68.56:30300
- **Prometheus**: http://192.168.68.56:30900

## ✅ What's Working

1. **kubectl Access** - Beelink can manage HP k3s cluster
2. **Networking** - HP internet fixed (k3s routing rule applied)
3. **SSH Access** - Beelink ↔ HP communication working
4. **Services Deployed**:
   - ai-brain (port 9004)
   - frontend (web UI)
   - gateway (API proxy)
   - financial, habits, meds, reminder, library microservices

## 🔧 What Still Needs Setup

### 1. llama.cpp on Beelink
Currently ai-brain in k3s has no LLM backend. Options:

**Option A**: Run llama.cpp on Beelink
```bash
cd ~/llama.cpp/build/bin
./llama-server -m ~/.lmstudio/models/.../model.gguf \
  --host 0.0.0.0 --port 9999 -ngl 0 -t 2
```
Then configure ai-brain to call `http://192.168.68.60:9999`

**Option B**: Deploy llama.cpp in k3s on HP
- More power available
- More complex setup

### 2. Update ai-brain Configuration
Configure ai-brain pod to connect to Beelink's llama.cpp:
```yaml
env:
- name: LLM_URL
  value: "http://192.168.68.60:9999"
```

### 3. Setup Kilo Agent on Beelink
Create `/home/brain_ai/Desktop/AI_stuff/old_hacksaw_fingers/services/k3s_manager/`:
- manager.py - Manages k3s deployments
- Add skills to query cluster status
- Add skills to deploy/scale services

## 📝 Quick Commands

### From Beelink (kubectl already configured)

```bash
# Check all pods
kubectl get pods -n kilo-guardian

# Check services
kubectl get svc -n kilo-guardian

# Scale a service
kubectl scale deployment kilo-financial --replicas=2 -n kilo-guardian

# View logs
kubectl logs -n kilo-guardian -l app=kilo-ai-brain --tail=50

# Restart a service
kubectl rollout restart deployment kilo-gateway -n kilo-guardian
```

### From HP (via SSH)

```bash
ssh kilo@192.168.68.56 'sudo kubectl get pods -A'
```

## 🔄 Next Steps

1. **Start llama.cpp on Beelink** (Option A recommended)
2. **Configure ai-brain to use Beelink's LLM**
3. **Add k3s management to Kilo agent** (Task #4)
4. **Test end-to-end flow** (Task #5)
5. **Update system guide** with hybrid architecture

## 📊 Service Port Map

| Service | Internal Port | NodePort | Purpose |
|---------|--------------|----------|---------|
| frontend | 80 | 30001 | Web UI |
| gateway | 8000 | 30801 | API Gateway |
| ai-brain | 9004 | - | RAG & Agent Logic |
| financial | 9005 | - | Finance Tracking |
| habits | 9003 | - | Habit Tracker |
| meds | 9001 | - | Medication Reminders |
| reminder | 9002 | - | General Reminders |
| library | 9006 | - | Library of Truth |
| grafana | 80 | 30300 | Monitoring |
| prometheus | 9090 | 30900 | Metrics |

## 🐛 Known Issues

1. **ai-brain** - Missing `networkx` module (non-critical)
2. **llama.cpp** - Not yet connected
3. **Frontend** - May need backend configuration

## 📚 Related Files

- Beelink codebase: `/home/brain_ai/Desktop/AI_stuff/old_hacksaw_fingers/`
- HP manifests: `~/Desktop/Kilo_Ai_microservice/k3s/`
- kubeconfig: `~/.kube/hp-k3s.yaml` (on Beelink)
- System guide: `KILO_SYSTEM_GUIDE.md`
- Network fix: `HP_FIXED_SUMMARY.md`

Setup completed: 2026-01-29
