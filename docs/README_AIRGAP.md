# Air-Gapped Deployment Guide for Kilo AI Memory Assistant

This comprehensive guide covers deploying Kilo in a fully offline, air-gapped environment with no external network access.

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Model Packaging](#model-packaging)
4. [Configuration](#configuration)
5. [Docker Deployment](#docker-deployment)
6. [Security Setup](#security-setup)
7. [Verification](#verification)
8. [Troubleshooting](#troubleshooting)

---

## Overview

**Kilo** is designed as a privacy-first AI memory assistant that can operate completely offline. This guide ensures:
- ✅ **No external network calls** (ALLOW_NETWORK=false)
- ✅ **All AI models run locally** (sentence-transformers, Ollama, MediaPipe)
- ✅ **Local speech/OCR processing** (Tesseract, VOSK)
- ✅ **Encrypted confidential memories** (Fernet encryption)
- ✅ **Secure authentication** (bcrypt token hashing)

---

## Prerequisites

### On Internet-Connected System (for preparation)

1. **Operating System**: Linux (Ubuntu 20.04+) or macOS
2. **Docker**: Version 20.10+
3. **Docker Compose**: Version 2.0+
4. **Disk Space**: ~10GB for models and images
5. **Tools**:
   ```bash
   # Install required tools
   sudo apt-get install curl unzip python3 python3-pip
   pip3 install sentence-transformers
   ```

6. **Ollama** (optional but recommended):
   ```bash
   curl -fsSL https://ollama.ai/install.sh | sh
   ```

### On Air-Gapped System

1. **Docker** and **Docker Compose** pre-installed
2. **Storage**: 10GB free disk space
3. **Transfer method**: USB drive, secure file transfer, or physical media

---

## Model Packaging

### Step 1: Download All Models (Internet-Connected System)

```bash
cd microservice

# Run the model packaging script
bash tools/package_models.sh
```

This script will download:
- ✓ **sentence-transformers** (all-MiniLM-L6-v2) - 80MB - for semantic memory search
- ✓ **MediaPipe pose landmarker** - 27MB - for camera posture detection
- ✓ **Tesseract language data** (eng.traineddata) - for OCR
- ✓ **VOSK speech model** (optional) - 40MB - for offline speech-to-text
- ✓ **Ollama models** - tinyllama (637MB) + mistral (4.1GB) - for local LLM

**Output**: `microservice/models.tar.gz`

### Step 2: Package Ollama Models Separately

```bash
# Ollama models are stored in ~/.ollama/models
# Package them separately (large files)
tar -czf ollama-models.tar.gz -C ~/.ollama models/
```

### Step 3: Build Docker Images (Internet-Connected)

```bash
cd microservice

# Build all images
docker-compose build

# Save images to tarball
docker save \
  microservice-gateway \
  microservice-ai_brain \
  microservice-meds \
  microservice-habits \
  microservice-financial \
  microservice-reminder \
  microservice-library_of_truth \
  microservice-cam \
  microservice-frontend \
  -o kilo-docker-images.tar
```

### Step 4: Transfer to Air-Gapped System

Transfer these files to the air-gapped system:
- `models.tar.gz` (~150MB)
- `ollama-models.tar.gz` (~5GB)
- `kilo-docker-images.tar` (~2GB)
- Entire `microservice/` directory (source code)

---

## Configuration

### Step 1: Extract Models on Air-Gapped System

```bash
cd microservice

# Extract model files
tar -xzf models.tar.gz

# Extract Ollama models to home directory
mkdir -p ~/.ollama
tar -xzf ollama-models.tar.gz -C ~/.ollama
```

### Step 2: Load Docker Images

```bash
docker load -i kilo-docker-images.tar
```

### Step 3: Configure Environment Variables

Edit `microservice/.env`:

```bash
# === AIR-GAPPED CONFIGURATION ===

# Network: MUST be false for air-gapped deployment
ALLOW_NETWORK=false

# STT/TTS: Use local providers only
STT_PROVIDER=none         # Or 'vosk' if VOSK model installed
TTS_PROVIDER=none         # Or 'pyttsx3' for local TTS

# LLM Provider: Use Ollama for local AI
LLM_PROVIDER=ollama
OLLAMA_MODEL=tinyllama    # Or 'mistral' for better quality
OLLAMA_BIN=/usr/local/bin/ollama  # Adjust to your ollama path

# Security: Set strong admin keys
LIBRARY_ADMIN_KEY=YOUR_SECURE_KEY_HERE_CHANGE_THIS

# Encryption: Generate and set encryption key
# Generate with: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
MEMORY_ENCRYPTION_KEY=YOUR_FERNET_KEY_HERE

# Model paths (already set in Dockerfiles, but can override)
SENTENCE_TRANSFORMERS_HOME=/app/models/sentence_transformers
EMBEDDING_MODEL_PATH=/app/models/sentence_transformers/all-MiniLM-L6-v2

# Gateway URL (leave as default for docker-compose)
GATEWAY_URL=http://127.0.0.1:8000
```

### Step 4: Generate Encryption Key

```bash
# Generate Fernet encryption key for confidential memories
python3 << EOF
from cryptography.fernet import Fernet
key = Fernet.generate_key()
print(f"MEMORY_ENCRYPTION_KEY={key.decode()}")
EOF
```

Add the output to your `.env` file.

---

## Docker Deployment

### Step 1: Verify docker-compose.yml

Ensure all services have `ALLOW_NETWORK=false`:

```yaml
services:
  ai_brain:
    environment:
      - ALLOW_NETWORK=false  # ✓ Air-gapped
      - STT_PROVIDER=none
      - TTS_PROVIDER=none
      - LIBRARY_URL=http://library_of_truth:9006
  # ... (all other services should have ALLOW_NETWORK=false)
```

### Step 2: Start Services

```bash
cd microservice

# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f ai_brain
```

Look for startup validation messages:
```
============================================================
KILO AI MEMORY ASSISTANT - Startup Checks
============================================================
Network mode: DISABLED (air-gapped)
STT provider: none
TTS provider: none
✓ Embedding model loaded successfully
✓ Ollama binary found: /usr/local/bin/ollama
✓ Tesseract OCR found: /usr/bin/tesseract
✓ Air-gapped mode configured correctly
============================================================
✓ All checks passed - service ready
============================================================
```

### Step 3: Access the Application

- **Frontend**: http://localhost:3000
- **API Gateway**: http://localhost:8000
- **AI Brain API**: http://localhost:9004

---

## Security Setup

### Step 1: Create Admin Token

```bash
# Create first admin token (no auth required for first token)
curl -X POST http://localhost:8000/admin/tokens

# Output:
# {"id": 1, "token": "abc123...xyz"}

# Save this token securely!
export ADMIN_TOKEN="abc123...xyz"
```

### Step 2: Test Authentication

```bash
# List tokens (requires authentication)
curl -H "X-Admin-Token: $ADMIN_TOKEN" \
  http://localhost:8000/admin/tokens
```

### Step 3: Create Additional Tokens

```bash
# Create token for another user/service
curl -X POST \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  http://localhost:8000/admin/tokens
```

### Step 4: Revoke Compromised Tokens

```bash
# Revoke token ID 2
curl -X POST \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  http://localhost:8000/admin/tokens/2/revoke
```

---

## Verification

### Test 1: Memory Storage and Retrieval

```bash
# Store a memory
curl -X POST http://localhost:9004/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "/remember I take blood pressure medication every morning at 8am",
    "user": "test_user"
  }'

# Expected: {"response": "✓ Memory stored (ID: 1). I'll remember: ..."}
```

### Test 2: Semantic Search

```bash
# Recall related memories
curl -X POST http://localhost:9004/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "/recall medication",
    "user": "test_user"
  }'

# Expected: List of memories related to medication
```

### Test 3: RAG (Context-Aware Responses)

```bash
# Ask a question (AI will search memories for context)
curl -X POST http://localhost:9004/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What medications do I take?",
    "user": "test_user"
  }'

# Expected: AI response referencing your stored memory about blood pressure medication
```

### Test 4: Verify No Network Calls

```bash
# Monitor network traffic (should be zero external calls)
docker-compose logs ai_brain | grep -i "network disabled"

# Expected: "network disabled: TTS provider 'gtts' requires network access"
# (if you try to use external providers)
```

---

## Troubleshooting

### Issue: "Embedding model not available"

**Cause**: sentence-transformers model not found

**Fix**:
```bash
# Check if models directory exists
docker-compose exec ai_brain ls -la /app/models/sentence_transformers/

# If missing, extract models.tar.gz in the correct location
tar -xzf models.tar.gz -C microservice/ai_brain/
docker-compose restart ai_brain
```

### Issue: "Ollama binary not found"

**Cause**: Ollama not installed on air-gapped system

**Fix**:
```bash
# Option 1: Transfer Ollama binary from internet-connected system
# On internet system:
which ollama  # Find ollama location
tar -czf ollama-binary.tar.gz /usr/local/bin/ollama

# On air-gapped system:
tar -xzf ollama-binary.tar.gz -C /

# Option 2: Use library-only mode (no LLM)
# Edit .env:
LLM_PROVIDER=library  # Falls back to library search
```

### Issue: "RuntimeError: network disabled"

**Cause**: External provider configured but ALLOW_NETWORK=false

**Fix**:
```bash
# Edit .env to use local providers:
STT_PROVIDER=none  # Or 'vosk'
TTS_PROVIDER=none  # Or 'pyttsx3'

# Restart services
docker-compose restart
```

### Issue: Memories not persisting after restart

**Cause**: SQLite databases in /tmp/ are ephemeral

**Fix**:
```bash
# Add volumes to docker-compose.yml:
services:
  ai_brain:
    volumes:
      - ./data/ai_brain:/data
      - ./db/ai_brain.db:/tmp/ai_brain.db
  # Repeat for all services
```

### Issue: "bcrypt not installed" warning

**Cause**: Optional dependency missing

**Fix**:
```bash
# Install in Docker image by adding to requirements:
docker-compose exec ai_brain pip install bcrypt

# Or rebuild with updated pyproject.toml
```

---

## Performance Optimization

### Use Faster LLM Model

```bash
# Edit .env:
OLLAMA_MODEL=tinyllama  # Faster, lower quality
# vs
OLLAMA_MODEL=mistral    # Slower, higher quality
```

### Reduce Memory Consolidation Frequency

```bash
# Add to .env:
CONSOLIDATION_DAYS=60  # Consolidate memories older than 60 days (default: 30)
```

### Limit Memory Search Results

```bash
# In ai_brain RAG configuration, reduce max_context_memories:
# Edit ai_brain/rag.py line 15:
max_context_memories=3  # Default is 5
```

---

## Maintenance

### Backup Databases

```bash
# Backup all SQLite databases
mkdir -p backups
docker-compose exec ai_brain cp /tmp/ai_brain.db /data/backup.db
# Copy from container
docker cp $(docker-compose ps -q ai_brain):/data/backup.db backups/ai_brain-$(date +%Y%m%d).db
```

### Run Memory Consolidation Manually

```bash
docker-compose exec ai_brain python3 -c "
from ai_brain.db import get_session
from ai_brain.memory_consolidation import run_nightly_maintenance

session = get_session()
stats = run_nightly_maintenance(session)
print(f'Consolidated: {stats}')
"
```

### Update Models (requires temporary internet)

```bash
# On internet-connected system, re-run:
bash tools/package_models.sh

# Transfer models.tar.gz to air-gapped system and extract
```

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────┐
│                   KILO AI MEMORY ASSISTANT              │
│                 (Fully Air-Gapped Deployment)           │
└─────────────────────────────────────────────────────────┘

External Network: ❌ DISABLED (ALLOW_NETWORK=false)

┌──────────────┐
│   Frontend   │  Port 3000 (React UI)
│  (Nginx)     │
└──────┬───────┘
       │
┌──────▼───────┐
│   Gateway    │  Port 8000 (API Router)
└──────┬───────┘
       │
       ├─► AI Brain (9004) ──┬─► Embeddings (local sentence-transformers)
       │                     ├─► LLM (local Ollama: tinyllama/mistral)
       │                     ├─► Memory Search (SQLite + semantic search)
       │                     └─► RAG (context injection)
       │
       ├─► Meds (9001) ─────► OCR (Tesseract)
       ├─► Financial (9005) ─► Receipt OCR
       ├─► Habits (9003) ────► Tracking & Analytics
       ├─► Reminder (9002) ──► APScheduler
       ├─► Cam (9007) ───────► MediaPipe Pose Detection
       └─► Library (9006) ───► PDF Knowledge Base

All data stored locally in SQLite databases
Confidential memories encrypted with Fernet
Admin tokens hashed with bcrypt
```

---

## Security Checklist

- [✓] `ALLOW_NETWORK=false` in all service configurations
- [✓] Strong `LIBRARY_ADMIN_KEY` set (not default value)
- [✓] `MEMORY_ENCRYPTION_KEY` generated and configured
- [✓] Admin tokens created with bcrypt hashing
- [✓] No external API keys in `.env` file
- [✓] All models downloaded and packaged locally
- [✓] Network traffic monitored (should be zero external calls)
- [✓] Databases backed up regularly
- [✓] Docker volumes configured for persistence

---

## Support

For issues with air-gapped deployment:

1. Check logs: `docker-compose logs -f ai_brain`
2. Run startup checks: `docker-compose exec ai_brain python3 -m ai_brain.startup_checks`
3. Verify models: `docker-compose exec ai_brain ls -la /app/models/`
4. Test embeddings: `docker-compose exec ai_brain python3 -m ai_brain.embeddings`

---

## License & Credits

- **Kilo AI Memory Assistant**: Privacy-first, offline-capable AI assistant
- **sentence-transformers**: Semantic text embeddings
- **Ollama**: Local LLM runtime
- **MediaPipe**: Pose detection
- **Tesseract**: OCR engine
