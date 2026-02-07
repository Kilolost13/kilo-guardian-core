# Kilo Guardian - Documentation Index

## 📚 Documentation Overview

This documentation provides comprehensive information about the Kilo Guardian system, a K3s-deployed AI assistant for personal life management.

## 🚀 Quick Start

### System Architecture
- **K3s Deployment**: Microservices running on K3s cluster
- **Backend**: FastAPI-based Python microservices
- **Frontend**: React application at `frontend/kilo-react-frontend`
- **Database**: SQLite with SQLModel (SQLAlchemy-based ORM)
- **LLM**: Ollama running on dedicated hardware

### Key Services
1. **AI Brain** - Core intelligence and conversation handling
2. **Gateway** - API router and central entry point
3. **Library of Truth** - Knowledge base and PDF storage
4. **Reminder** - Timeline and reminders
5. **Habits** - Habit tracking and analytics
6. **Meds** - Medication management
7. **Financial** - Budget and transaction tracking
8. **Camera** - Camera and pose detection
9. **Voice** - Voice input processing
10. **ML Engine** - ML processing
11. **SocketIO Relay** - Real-time communication

## 🔧 Development

### Local Development
```bash
# Backend services (individual service)
cd services/ai_brain
python3 main.py

# Frontend
cd frontend/kilo-react-frontend
npm install
npm start
```

### Deployment
```bash
# Deploy all services to K3s
./scripts/deploy-to-k3s.sh

# Check service status
kubectl get pods -n kilo-guardian
```

## 📊 System Features

### AI & Memory
- Conversational AI with context awareness
- Long-term memory with vector embeddings
- Knowledge base integration
- RAG-based information retrieval

### Health & Wellness
- Medication tracking and reminders
- Habit formation and monitoring
- Goal setting and progress tracking

### User Experience
- Voice-controlled interface
- Real-time updates and notifications
- Responsive web interface

### Infrastructure
- K3s orchestration
- SQLite + SQLModel for data persistence
- FastAPI for all microservices
- No Redis or PostgreSQL dependencies

## 🛠️ Tech Stack

- **Backend**: Python 3, FastAPI, SQLModel
- **Frontend**: React, TypeScript
- **Database**: SQLite (file-based, no server)
- **Container Orchestration**: K3s (lightweight Kubernetes)
- **LLM**: Ollama (local, air-gapped capable)

## 📈 Hardware Setup

The system runs on two PCs:
- **Beelink** (192.168.68.60): Overseer/agent, Ollama LLM server
- **HP** (192.168.68.56): K3s cluster worker node

See the main [README.md](../README.md) for complete architecture details and operational guide.

