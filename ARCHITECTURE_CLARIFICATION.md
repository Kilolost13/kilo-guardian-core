# Kilo Architecture Clarification

## ⚠️ Important: Avoiding Resource Conflicts

You're absolutely right - running both "Kilo AI agent" and "ai-brain" on Beelink would overload it!

## 🎯 Current Setup (CORRECT)

### Beelink (Lightweight Control)
```
✅ llama.cpp         (Port 11434) - LLM inference only
✅ k3s-manager       (Port 9011)  - Cluster management
✅ kubectl           - CLI tool
❌ ai-brain          - NOT running here (runs in k3s)
```

**Resource Usage on Beelink:**
- llama.cpp: ~2.7GB RAM (Phi-3-mini model loaded)
- k3s-manager: ~30MB RAM
- Total: ~2.8GB RAM

### HP K3s (Heavy Workloads)
```
✅ kilo-ai-brain     - The actual AI agent brain
✅ kilo-frontend     - Web UI
✅ kilo-gateway      - API gateway
✅ All microservices - 11 total pods
```

**Resource Usage on HP:**
- All pods combined: ~4-6GB RAM
- k3s overhead: ~1GB RAM

## 🧠 What is "ai-brain"?

**ai-brain IS the Kilo AI agent!** It includes:
- RAG (Retrieval-Augmented Generation)
- Memory system
- Agent orchestration
- Tool calling
- Skill execution

It runs in k3s on HP and calls back to Beelink's llama.cpp for LLM inference.

## 🔄 How They Work Together

```
User Request
    ↓
kilo-frontend (HP k3s)
    ↓
kilo-gateway (HP k3s)
    ↓
kilo-ai-brain (HP k3s) ← This is the agent!
    ↓
llama.cpp (Beelink) ← Just provides LLM inference
    ↓
Response flows back
```

## ✅ What Should Run Where

### Beelink ONLY runs:
1. **llama.cpp** - Lightweight inference server
2. **k3s-manager** - Cluster management API
3. ❌ **NOT ai-brain** - Too heavy, already in k3s

### HP k3s runs:
1. **kilo-ai-brain** - The full AI agent
2. **All microservices** - Financial, habits, etc.
3. **Frontend** - Web interface

## 🚫 Common Mistake to Avoid

**DON'T** run `services/ai_brain/main.py` directly on Beelink!
- It's already running in k3s on HP
- Running it twice would:
  - Duplicate processing
  - Compete for llama.cpp resources
  - Waste RAM on Beelink
  - Cause port conflicts

## 🎯 Correct Usage

### To interact with Kilo:
1. **Via Web UI**: http://192.168.68.56:30001
2. **Via API**: http://192.168.68.56:30801
3. **Via k3s-manager**: http://localhost:9011 (from Beelink)

### To manage the cluster (from Beelink):
```bash
# Check status
curl http://localhost:9011/cluster/status

# Scale services
curl -X POST http://localhost:9011/services/scale \
  -d '{"service":"kilo-ai-brain","replicas":2}'
```

## 📊 Current Resource Footprint

**Beelink:**
- llama.cpp: 2.7GB RAM
- k3s-manager: 30MB RAM
- **Total: ~2.8GB** ✅ Safe

**HP:**
- 11 running pods: ~6GB RAM
- k3s overhead: ~1GB RAM
- **Total: ~7GB** ✅ Within capacity

## ✨ Summary

- ✅ **ai-brain runs ONLY in k3s on HP**
- ✅ **llama.cpp runs ONLY on Beelink**
- ✅ **They communicate via network (port 11434)**
- ✅ **Beelink stays lightweight and responsive**
- ✅ **HP handles all the heavy AI work**

This hybrid architecture keeps Beelink from "blowing up" while giving Kilo full power on the HP!
