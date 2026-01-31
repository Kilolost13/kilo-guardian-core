# Kilo K3s Management Skills

Kilo now has full control over the HP k3s cluster!

## 🚀 K3s Manager Service Running

**Location**: Beelink (localhost)
**Port**: 9011
**Status**: ✅ Running (PID: 28041)

## 📡 Available Skills

### 1. Check Cluster Health
```bash
curl http://localhost:9011/cluster/status
```
**What it shows**: Nodes, running pods, namespace status

### 2. List All Services
```bash
curl http://localhost:9011/services
```
**What it shows**: All deployments with replica counts and status

### 3. Get Service Endpoints
```bash
curl http://localhost:9011/endpoints
```
**What it shows**: All accessible URLs (NodePorts, LoadBalancers)

### 4. Scale a Service
```bash
curl -X POST http://localhost:9011/services/scale \
  -H "Content-Type: application/json" \
  -d '{"service": "kilo-financial", "replicas": 2}'
```
**What it does**: Scales service up or down

### 5. Restart a Service
```bash
curl -X POST http://localhost:9011/services/restart \
  -H "Content-Type: application/json" \
  -d '{"service": "kilo-gateway"}'
```
**What it does**: Rolling restart of service

### 6. Get Service Logs
```bash
curl -X POST http://localhost:9011/services/logs \
  -H "Content-Type: application/json" \
  -d '{"service": "kilo-ai-brain", "lines": 50}'
```
**What it shows**: Recent logs from the service

### 7. Get Pod Status
```bash
curl http://localhost:9011/services/kilo-frontend/status
```
**What it shows**: Detailed pod information (restarts, readiness)

### 8. Execute Command in Pod
```bash
curl -X POST http://localhost:9011/services/exec \
  -H "Content-Type: application/json" \
  -d '{"service": "kilo-ai-brain", "command": "ls -la /app"}'
```
**What it does**: Runs command inside service container

## 🤖 How Kilo Uses These Skills

Kilo can now answer questions like:
- **"What's running on the cluster?"** → Calls `/services`
- **"Is the frontend healthy?"** → Calls `/services/kilo-frontend/status`
- **"Scale up financial service"** → Calls `/services/scale`
- **"Show me ai-brain logs"** → Calls `/services/logs`
- **"Restart the gateway"** → Calls `/services/restart`

## 🔌 Integrating with ai_brain

To make these skills available to Kilo's AI brain, update `services/ai_brain/main.py`:

```python
import httpx

K3S_MANAGER_URL = "http://localhost:9011"

@app.post("/skill/k3s/status")
async def k3s_status():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{K3S_MANAGER_URL}/cluster/status")
        return resp.json()

@app.post("/skill/k3s/services")
async def k3s_services():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{K3S_MANAGER_URL}/services")
        return resp.json()

@app.post("/skill/k3s/scale")
async def k3s_scale(service: str, replicas: int):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{K3S_MANAGER_URL}/services/scale",
            json={"service": service, "replicas": replicas}
        )
        return resp.json()
```

## 🎯 Current System Status

**llama.cpp (Beelink)**: ✅ Running on port 11434
**K3s Manager (Beelink)**: ✅ Running on port 9011
**kubectl**: ✅ Configured

**HP K3s Services**:
- ✅ kilo-ai-brain (1/1)
- ✅ kilo-frontend (1/1) - http://192.168.68.56:30001
- ✅ kilo-gateway (1/1) - http://192.168.68.56:30801
- ✅ kilo-financial (1/1)
- ✅ kilo-habits (1/1)
- ✅ kilo-meds (1/1)
- ✅ kilo-reminder (1/1)
- ✅ kilo-library (1/1)

## 🔄 Auto-Start on Boot

To start k3s manager automatically:

```bash
# Add to ~/.bashrc or create systemd service
/home/brain_ai/Desktop/AI_stuff/old_hacksaw_fingers/start_k3s_manager.sh &
```

## 📊 Quick Test

```bash
# Check if manager is running
curl http://localhost:9011/health

# Get cluster status
curl http://localhost:9011/cluster/status | python3 -m json.tool

# List all endpoints
curl http://localhost:9011/endpoints | python3 -m json.tool
```

Skills created: 2026-01-29
