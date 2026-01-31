# Kilo AI - Beelink SER7-9 Deployment Guide

This guide covers deploying Kilo on the Beelink SER7-9 mini PC for optimal performance.

---

## Hardware Specifications

**Beelink SER7-9**:
- **CPU**: AMD Ryzen 9 7940HS (8 cores, 16 threads, up to 5.2 GHz)
- **GPU**: AMD Radeon 780M (integrated, 12 compute units)
- **RAM**: 16-32GB DDR5 (recommended: 32GB)
- **Storage**: 1TB NVMe SSD
- **Network**: 2.5GbE LAN + WiFi 6E

**Recommended RAM Configuration**: 32GB for best performance

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      Beelink SER7-9 (Brain)                     │
├─────────────────────────────────────────────────────────────────┤
│  Docker Containers:                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Ollama       │  │ AI Brain     │  │ ML Engine    │          │
│  │ Llama 3.1 8B │  │ RAG + Memory │  │ scikit-learn │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Gateway      │  │ Meds         │  │ Finance      │          │
│  │ API Router   │  │ OCR          │  │ Budgets      │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Habits       │  │ Reminders    │  │ Library      │          │
│  │ Tracking     │  │ Scheduler    │  │ Knowledge    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              ↕ HTTP over LAN
┌─────────────────────────────────────────────────────────────────┐
│                    Tablet (Thin Client - I/O Only)              │
│                                                                   │
│  React Frontend:                                                 │
│  - Display UI                                                    │
│  - Camera capture                                                │
│  - Microphone input                                             │
│  - Touch interface                                               │
│  - NO processing                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Step 1: Operating System Setup

### Install Ubuntu Server 22.04 LTS

1. Download Ubuntu Server 22.04 LTS from [ubuntu.com](https://ubuntu.com/download/server)
2. Create bootable USB with Rufus (Windows) or dd (Linux)
3. Install Ubuntu on Beelink SER7-9
4. During installation:
   - Enable OpenSSH server
   - Set username: `kilo` (or your preference)
   - Enable automatic security updates

### Post-Install Configuration

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y \
    git \
    curl \
    wget \
    htop \
    net-tools \
    build-essential \
    vim

# Set static IP (recommended for LAN access)
sudo nano /etc/netplan/00-installer-config.yaml
```

Example netplan config for static IP:
```yaml
network:
  version: 2
  ethernets:
    enp1s0:  # Your ethernet interface name
      dhcp4: no
      addresses:
        - 192.168.1.100/24  # Change to your network
      gateway4: 192.168.1.1
      nameservers:
        addresses: [8.8.8.8, 8.8.8.4]
```

Apply network config:
```bash
sudo netplan apply
```

---

## Step 2: Docker Installation

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Logout and login again for group changes
exit
```

---

## Step 3: AMD GPU Setup (Optional but Recommended)

Enable AMD Radeon 780M GPU support for Ollama:

```bash
# Install ROCm (AMD's GPU compute platform)
wget https://repo.radeon.com/amdgpu-install/latest/ubuntu/jammy/amdgpu-install_*.deb
sudo apt install ./amdgpu-install_*.deb
sudo amdgpu-install -y --usecase=rocm

# Verify GPU is detected
rocm-smi

# Add user to render and video groups
sudo usermod -aG render,video $USER

# Reboot to apply changes
sudo reboot
```

---

## Step 4: Clone Kilo Repository

```bash
cd /home/kilo
git clone https://github.com/YOUR_USERNAME/kilo-ai.git
cd kilo-ai/microservice
```

---

## Step 5: Environment Configuration

Create `.env` file:

```bash
cat > .env << 'EOF'
# Kilo AI Configuration for Beelink SER7-9

# Air-gapped mode (set to true for local-only operation)
ALLOW_NETWORK=false

# Admin credentials
ADMIN_TOKEN=your-secure-admin-token-here
LIBRARY_ADMIN_KEY=your-library-admin-key-here

# Ollama Configuration
OLLAMA_MODEL=llama3.1:8b-instruct-q5_K_M
OLLAMA_NUM_PARALLEL=2
OLLAMA_GPU_LAYERS=33

# ML Engine Configuration
ENABLE_ML_TRAINING=true
ML_TRAINING_SCHEDULE=0 2 * * *  # Train at 2 AM daily

# Voice Configuration (future)
ENABLE_VOICE=false
WHISPER_MODEL=whisper-small
PIPER_VOICE=en_US-lessac-medium

# Resource Limits (adjust based on your RAM)
# With 32GB RAM:
DOCKER_MEMORY_LIMIT=28G
OLLAMA_MEMORY=8G
# With 16GB RAM:
# DOCKER_MEMORY_LIMIT=14G
# OLLAMA_MEMORY=6G

EOF
```

---

## Step 6: Deploy Kilo Services

```bash
# Build all services
docker-compose build

# Start services
docker-compose up -d

# Watch logs
docker-compose logs -f

# Check service status
docker-compose ps
```

---

## Step 7: Setup Ollama and Pull Models

```bash
# Run the Ollama setup script
chmod +x setup_ollama.sh
./setup_ollama.sh
```

This will:
- Pull Llama 3.1 8B model (~5GB download)
- Configure GPU acceleration
- Test model with a sample query

**Manual alternative**:
```bash
# Pull model manually
docker-compose exec ollama ollama pull llama3.1:8b-instruct-q5_K_M

# Test model
docker-compose exec ollama ollama run llama3.1:8b-instruct-q5_K_M "Hello, I am Kilo. Introduce yourself briefly."
```

---

## Step 8: Tablet Configuration

On your tablet (Android/iPad):

1. **Install Fully Kiosk Browser** (Android) or **Kiosk Pro** (iPad)
2. **Set home URL**: `http://192.168.1.100:3000` (use your Beelink IP)
3. **Enable kiosk mode**
4. **Configure settings**:
   - Enable camera access
   - Enable microphone access
   - Disable sleep mode
   - Enable auto-reload on network reconnect

### Tablet .env.local (if building frontend locally)

If you're building the React frontend on the tablet:

```bash
# In microservice/frontend/kilo-react-frontend/.env.local
REACT_APP_API_URL=http://192.168.1.100:8000
```

Otherwise, the nginx-served frontend from Beelink will automatically route to the gateway.

---

## Step 9: Verify Deployment

### Check all services are running

```bash
docker-compose ps

# Expected output:
# gateway        Up (healthy)
# ai_brain       Up (healthy)
# ollama         Up (healthy)
# ml_engine      Up (healthy)
# meds           Up (healthy)
# financial      Up (healthy)
# habits         Up (healthy)
# reminders      Up (healthy)
# library        Up (healthy)
# cam            Up (healthy)
# frontend       Up (healthy)
```

### Test API Gateway

```bash
curl http://localhost:8000/status
# Should return: {"status":"ok"}
```

### Test AI Brain with Kilo

```bash
curl -X POST http://localhost:9004/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello Kilo, who are you?"}'

# Should return Kilo's introduction
```

### Test ML Engine

```bash
curl http://localhost:9008/status
# Should return: {"status":"ok","models_trained":0,"models_dir":"/data/ml_models"}
```

### Access Frontend

Open browser on any device on the network:
- **HTTP**: `http://192.168.1.100:3000`
- **HTTPS**: `https://192.168.1.100:3443` (self-signed cert)

---

## Step 10: Performance Tuning

### Monitor Resource Usage

```bash
# Real-time resource monitoring
htop

# Docker stats
docker stats

# GPU monitoring (if ROCm installed)
watch -n 1 rocm-smi
```

### Optimize for Your RAM Configuration

**With 32GB RAM** (Recommended):
- Ollama can load multiple models simultaneously
- ML training can run in background without impacting performance
- Handles 3-4 concurrent users comfortably

**With 16GB RAM** (Minimum):
- Ollama loads one model at a time
- ML training should run during off-hours only
- Handles 1-2 concurrent users

Edit `docker-compose.yml` to adjust memory limits if needed.

---

## Performance Expectations

### Beelink SER7-9 with 32GB RAM

**LLM Performance (Llama 3.1 8B)**:
- Token generation: 60-80 tokens/sec (with GPU)
- Token generation: 30-40 tokens/sec (CPU only)
- Response time: 1-3 seconds for typical queries
- Concurrent users: 2-3

**ML Engine**:
- Habit prediction: <100ms
- Pattern analysis: <500ms
- Nightly training: 2-5 minutes

**OCR Performance**:
- Prescription scan: 1-2 seconds
- Receipt scan: 1-2 seconds

**Memory Usage**:
- Ollama (Llama 3.1 8B): ~6GB
- AI Brain + services: ~2GB
- ML Engine: ~500MB
- Total: ~9GB (leaves 23GB free for OS and cache)

---

## Maintenance

### Daily

```bash
# Check logs for errors
docker-compose logs --tail=100

# Check disk space
df -h
```

### Weekly

```bash
# Update containers
docker-compose pull
docker-compose up -d

# Clean up old images
docker image prune -a

# Backup data
sudo tar -czf kilo-backup-$(date +%Y%m%d).tar.gz /var/lib/docker/volumes/
```

### Monthly

```bash
# System updates
sudo apt update && sudo apt upgrade -y

# Check ML model performance
curl http://localhost:9008/stats
```

---

## Troubleshooting

### Ollama Not Starting

```bash
# Check Ollama logs
docker-compose logs ollama

# Restart Ollama
docker-compose restart ollama

# If GPU issues, try CPU-only mode
# Edit docker-compose.yml: Remove GPU configuration
```

### AI Brain Slow Responses

```bash
# Check if model is loaded
docker-compose exec ollama ollama list

# Check Ollama performance
docker stats ollama

# Reduce parallel requests if needed
# Edit .env: OLLAMA_NUM_PARALLEL=1
```

### ML Engine Training Fails

```bash
# Check ML Engine logs
docker-compose logs ml_engine

# Manually trigger training
curl -X POST http://localhost:9008/train/habits

# Check model storage
ls -lh /var/lib/docker/volumes/microservice_ml_models/_data/
```

---

## Security Considerations

### Air-Gapped Mode

When `ALLOW_NETWORK=false`:
- No external network access
- All AI processing is local
- All data stays on Beelink

### Firewall Configuration

```bash
# Allow only LAN access
sudo ufw enable
sudo ufw allow from 192.168.1.0/24 to any port 8000
sudo ufw allow from 192.168.1.0/24 to any port 3000
sudo ufw allow 22  # SSH

# Block all other incoming
sudo ufw default deny incoming
sudo ufw default allow outgoing
```

---

## Next Steps

1. **Configure Tablet**: Set up kiosk mode and point to Beelink IP
2. **Train ML Models**: Use Kilo for a week, then check ML insights
3. **Voice Integration**: Follow [AI_LEARNING_PLAN.md](AI_LEARNING_PLAN.md) Phase 3
4. **Customize Kilo**: Adjust personality and prompts to your preferences

---

## Support

For issues or questions:
- Check logs: `docker-compose logs [service_name]`
- Review [AI_LEARNING_PLAN.md](AI_LEARNING_PLAN.md) for feature details
- Check GitHub issues

---

**You're now running Kilo AI on dedicated hardware! The system will learn your patterns and become more helpful over time.**
