# 🧠 Kilo Guardian - AI Cognitive Support System
**Privacy-First, Self-Hosted, Kubernetes-Deployed AI Assistant**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![K3s](https://img.shields.io/badge/K3s-Ready-326CE5.svg)](https://k3s.io/)
[![React](https://img.shields.io/badge/React-19.2.3-61DAFB.svg)](https://reactjs.org/)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB.svg)](https://www.python.org/)

---

## ✨ Overview

**Kilo Guardian** is a comprehensive cognitive support system running entirely on your local infrastructure. It combines AI-powered memory management, health tracking, financial oversight, and habit formation into a unified, privacy-first platform.

**Current Status:** ✅ **100% Operational** - 15 microservices running on K3s

---

## 🎯 Quick Access

### From Your Tablet or Mobile Device
```bash
# SSH tunnel to access Kilo Guardian
ssh -L 3000:localhost:30000 -L 8000:localhost:30800 kilo@192.168.68.66
```
Then open: **http://localhost:3000**

See [docs/TABLET_ACCESS.md](docs/TABLET_ACCESS.md) for detailed setup.

### From Server (Local)
- **Frontend:** http://localhost:30000
- **Gateway API:** http://localhost:30800

---

## 🏗️ Architecture

### System Overview
```
┌─────────────────────────────────────────────────────────┐
│          KILO GUARDIAN KUBERNETES CLUSTER               │
│                    (K3s on Pop!_OS)                     │
└─────────────────────────────────────────────────────────┘

External Access (NodePort):
├─► Frontend (30000)  ──► React UI
└─► Gateway (30800)   ──► API Router

Kubernetes Services (ClusterIP):
├─► Frontend Service     : kilo-frontend (80)
├─► API Gateway         : kilo-gateway (8000)
│
├─► Core Services:
│   ├─► Medications     : kilo-meds (9001)
│   ├─► Medications v2  : kilo-meds-v2 (9001)
│   ├─► Reminders       : kilo-reminder (9002)
│   ├─► Habits          : kilo-habits (9003)
│   ├─► Financial       : kilo-financial (9005)
│   └─► Library         : kilo-library (9006)
│
├─► Intelligence Layer:
│   ├─► AI Brain        : kilo-ai-brain (9004)
│   ├─► ML Engine       : kilo-ml-engine (9008)
│   └─► Ollama          : kilo-ollama (11434)
│
├─► I/O Services:
│   ├─► Camera          : kilo-cam (9007)
│   ├─► Voice           : kilo-voice (9009)
│   └─► USB Transfer    : kilo-usb-transfer (8006)
│
└─► Real-Time:
    └─► SocketIO        : kilo-socketio (9010)

All services in namespace: kilo-guardian
Network: 10.42.0.0/16 (K3s Pod Network)
```

### Technology Stack

**Infrastructure:**
- K3s (Lightweight Kubernetes)
- Kubernetes 1.28+
- Pop!_OS 22.04 LTS

**Backend:**
- Python 3.11
- FastAPI
- SQLite + SQLModel
- sentence-transformers
- Ollama (Local LLM)

**Frontend:**
- React 19.2.3
- TypeScript 4.9.5
- TailwindCSS
- React Router v6

---

## 📦 What's Running

| Service | Pod Name | Status | Function |
|---------|----------|--------|----------|
| Frontend | kilo-frontend | ✅ Running | React UI |
| Gateway | kilo-gateway | ✅ Running | API Router & Auth |
| Medications | kilo-meds | ✅ Running | Med tracking & OCR |
| Medications v2 | kilo-meds-v2 | ✅ Running | Updated version |
| Reminders | kilo-reminder | ✅ Running | Timeline & alerts |
| Habits | kilo-habits | ✅ Running | Habit tracking |
| AI Brain | kilo-ai-brain | ✅ Running | RAG & Memory |
| Financial | kilo-financial | ✅ Running | Budget & receipts |
| Library | kilo-library | ✅ Running | Knowledge base |
| Camera | kilo-cam | ✅ Running | Pose detection |
| ML Engine | kilo-ml-engine | ✅ Running | ML processing |
| Voice | kilo-voice | ✅ Running | Voice input |
| USB Transfer | kilo-usb-transfer | ✅ Running | File transfer |
| SocketIO | kilo-socketio | ✅ Running | Real-time events |
| Ollama | kilo-ollama | ✅ Running | Local LLM |

**Total:** 15 pods, all healthy

---

## 🚀 Features

### 🔒 Privacy & Security
- ✅ **100% Self-Hosted** - All data stays on your server
- ✅ **No Cloud Dependencies** - Fully offline capable
- ✅ **Local AI** - Ollama runs LLMs on-premise
- ✅ **Encrypted Storage** - Sensitive data protected
- ✅ **Network Isolation** - K3s internal networking

### 🤖 AI Intelligence
- ✅ **Semantic Memory** - RAG-powered context recall
- ✅ **Smart Suggestions** - AI-driven recommendations
- ✅ **Natural Language** - Chat interface for all modules
- ✅ **Context Awareness** - Learns your patterns

### 📱 Tablet-Optimized
- ✅ **Touch-Friendly UI** - Large touch targets (60px+)
- ✅ **Responsive Design** - Works on any screen size
- ✅ **PWA-Ready** - Install as app on mobile
- ✅ **Fast Performance** - Optimized React build

### 🔧 Production Features
- ✅ **High Availability** - K3s self-healing
- ✅ **Service Discovery** - Automatic DNS routing
- ✅ **Health Monitoring** - Built-in health checks
- ✅ **Easy Scaling** - Kubernetes-native scaling
- ✅ **Rolling Updates** - Zero-downtime deployments

---

## 📚 Documentation

### Getting Started
- **[TABLET_ACCESS.md](docs/TABLET_ACCESS.md)** - Access from tablet/mobile
- **[K3S_ACCESS_GUIDE.md](docs/K3S_ACCESS_GUIDE.md)** - Kubernetes deployment guide
- **[DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)** - Full deployment instructions

### Operations
- **[POD_HEALTH_REPORT.md](docs/POD_HEALTH_REPORT.md)** - Current system status
- **[SERVICE_COMMUNICATION_TEST.md](docs/SERVICE_COMMUNICATION_TEST.md)** - Connectivity verification
- **[K8S_HARDENING_SUMMARY.md](docs/K8S_HARDENING_SUMMARY.md)** - Security configuration

### Features
- **[ROADMAPS/INTEGRATION_ROADMAP.md](docs/ROADMAPS/INTEGRATION_ROADMAP.md)** - Future integration plans
- **[ROADMAPS/VOICE_ROADMAP.md](docs/ROADMAPS/VOICE_ROADMAP.md)** - Voice feature roadmap

### Technical Details
- **[EXTERNAL_CAMERA_IMPLEMENTATION.md](docs/EXTERNAL_CAMERA_IMPLEMENTATION.md)** - Camera system
- **[MULTI_CAMERA_SYSTEM.md](docs/MULTI_CAMERA_SYSTEM.md)** - Multi-camera setup
- **[PERFORMANCE_IMPROVEMENTS.md](docs/PERFORMANCE_IMPROVEMENTS.md)** - Optimization history

---

## 🛠️ Common Operations

### Check System Status
```bash
# View all pods
kubectl get pods -n kilo-guardian

# Check services
kubectl get svc -n kilo-guardian

# View logs for a service
kubectl logs -n kilo-guardian deployment/kilo-gateway --tail=50
```

### Manage Services
```bash
# Restart a service
kubectl rollout restart deployment/kilo-meds -n kilo-guardian

# Scale a service
kubectl scale deployment/kilo-ml-engine --replicas=2 -n kilo-guardian

# View resource usage
kubectl top pods -n kilo-guardian
```

### Troubleshooting
```bash
# Check pod details
kubectl describe pod <pod-name> -n kilo-guardian

# Get pod events
kubectl get events -n kilo-guardian --sort-by='.lastTimestamp'

# Access pod shell
kubectl exec -it deployment/kilo-gateway -n kilo-guardian -- /bin/sh
```

See [docs/OPERATIONS.md](docs/OPERATIONS.md) for comprehensive operations guide.

---

## 🔍 Project Structure

```
kilo-guardian-core/
├── services/              # Microservice implementations
│   ├── ai_brain/         # RAG & memory search
│   ├── cam/              # Camera & pose detection
│   ├── financial/        # Budget & transaction tracking
│   ├── gateway/          # API router & authentication
│   ├── habits/           # Habit tracking & analytics
│   ├── library_of_truth/ # Knowledge base & PDF storage
│   ├── meds/             # Medication management
│   ├── ml_engine/        # ML processing engine
│   ├── reminder/         # Timeline & reminders
│   ├── socketio-relay/   # Real-time communication
│   ├── usb_transfer/     # File transfer service
│   ├── voice/            # Voice input processing
│   └── k3s_manager/      # K3s cluster management
│
├── frontend/             # React frontend
│   └── kilo-react-frontend/
│       ├── src/
│       │   ├── components/
│       │   ├── pages/
│       │   └── services/
│       └── public/
│
├── core/                 # Core agent functionality
│   ├── kilo_agent.py    # Main agent logic
│   ├── kilo_agent_brain.py
│   ├── kilo_agent_ui.py # UI interface (canonical)
│   ├── kilo_memory.py   # Memory management
│   ├── kilo_router.py   # Command routing
│   └── kilo_pod_access.py
│
├── shared/               # Shared utilities & config
│   ├── config.py        # Centralized configuration
│   ├── db.py            # Unified database access (SQLModel)
│   ├── models/          # Shared data models
│   └── utils/           # Helper functions
│
├── k3s/                  # Kubernetes manifests
│   ├── deployments/
│   ├── services/
│   └── configmaps/
│
├── docs/                 # Documentation
│   ├── ROADMAPS/        # Future planning
│   ├── REPORTS/         # Historical reports
│   └── *.md             # Current documentation
│
├── scripts/              # Operational scripts
│   ├── deploy-to-k3s.sh
│   ├── check-status.sh
│   └── launch_*.sh
│
├── legacy/               # Legacy/experimental code
│   ├── v1/              # Old version 1
│   ├── v2/              # Old version 2
│   └── *.py             # Archived experiments
│
├── kilo_agent_api.py     # Agent API service
├── kilo_proactive_agent.py # Proactive monitoring agent
└── start-proactive-agent.sh # Agent startup script

```

---

## 🎯 Module Features

### 💊 Medications
- Medication schedule with timers
- Prescription OCR scanning
- Dosage tracking
- Prescriber management

### 📅 Reminders
- Timeline view
- Voice input support
- Recurring reminders
- Priority levels

### 💰 Financial
- Budget tracking
- Receipt OCR
- Transaction categorization
- Monthly summaries
- Goal setting

### ✅ Habits
- Daily habit tracking
- Streak counters
- Progress visualization
- Weekly calendar view
- Custom icons

### 🧠 AI Brain
- Semantic memory search
- RAG-powered chat
- Context-aware responses
- Memory consolidation

### 📚 Library
- PDF knowledge base
- Document search
- Note management
- Tag organization

---

## 📊 Performance

- **Pod Startup:** < 30 seconds
- **API Response:** < 100ms (avg)
- **Frontend Load:** < 2 seconds
- **Memory Usage:** ~4GB total
- **CPU Usage:** < 20% (idle)

---

## 🔐 Security Features

- ✅ **Network Policies** - Service-to-service restrictions
- ✅ **RBAC** - Role-based access control
- ✅ **Pod Security** - Non-root containers
- ✅ **Secret Management** - Kubernetes secrets
- ✅ **Internal DNS** - ClusterIP-only backend services
- ✅ **NodePort Limited** - Only frontend & gateway exposed

---

## 🧪 Testing

### API Testing
```bash
# Test gateway
curl http://localhost:30800/meds/

# Test financial summary
curl http://localhost:30800/financial/summary

# Test reminder list
curl http://localhost:30800/reminder/reminders
```

### Frontend Testing
Open http://localhost:30000 and verify:
- ✅ Dashboard loads
- ✅ All 6 modules accessible
- ✅ Data persists across refreshes
- ✅ Navigation works smoothly

---

## 🚨 Troubleshooting

### Services Won't Start
1. Check pod status: `kubectl get pods -n kilo-guardian`
2. View logs: `kubectl logs <pod-name> -n kilo-guardian`
3. Check events: `kubectl get events -n kilo-guardian`

### Can't Access Frontend
1. Verify NodePort: `kubectl get svc -n kilo-guardian`
2. Check firewall: `sudo ufw status`
3. Test locally: `curl http://localhost:30000`

### Database Issues
1. Check pod restart count: `kubectl get pods -n kilo-guardian`
2. View logs for errors
3. Verify volume mounts: `kubectl describe pod <pod-name> -n kilo-guardian`

---

## 🤝 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- **K3s** - Lightweight Kubernetes
- **Ollama** - Local LLM runtime
- **sentence-transformers** - Semantic embeddings
- **FastAPI** - Modern Python API framework
- **React** - UI framework
- **TailwindCSS** - Utility-first CSS

---

## 📞 Support

For issues or questions:
- Check logs: `kubectl logs <service> -n kilo-guardian`
- View documentation: `docs/`
- System status: [docs/POD_HEALTH_REPORT.md](docs/POD_HEALTH_REPORT.md)

---

## 🎉 Current Status

✅ **Infrastructure:** K3s cluster fully operational
✅ **Backend:** 13 microservices running
✅ **Frontend:** React UI deployed and accessible
✅ **Database:** SQLite with persistent storage
✅ **AI:** Ollama LLM ready
✅ **Networking:** All services communicating
✅ **Documentation:** Comprehensive guides available

**System Health:** 100% - All 15 pods running

---

**Built for privacy-conscious users who want powerful AI without compromising data sovereignty**

🤖 Deployed with Kubernetes | 🔒 Secured by Design | 🏠 Runs Entirely On-Premise
