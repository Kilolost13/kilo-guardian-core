# Kilo AI Memory Assistant - Architecture Overview

**Version:** 1.0.0
**Target Audience:** Technical stakeholders, developers, system architects
**Last Updated:** December 2025

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Principles](#architecture-principles)
3. [Service Architecture](#service-architecture)
4. [Data Flow](#data-flow)
5. [Technology Stack](#technology-stack)
6. [AI/ML Pipeline](#aiml-pipeline)
7. [Security Architecture](#security-architecture)
8. [Performance & Scalability](#performance--scalability)
9. [Deployment Architecture](#deployment-architecture)
10. [Future Architecture](#future-architecture)

---

## System Overview

Kilo AI is a **microservices-based, air-gapped AI memory assistant** designed for healthcare and personal assistance applications. The system runs entirely offline on commodity hardware, ensuring complete data privacy and HIPAA readiness.

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interfaces                           │
├─────────────┬─────────────┬─────────────┬──────────────────────┤
│  Web UI     │   Voice     │   Camera    │   USB Transfer       │
│  (React)    │  (Whisper)  │  (OpenCV)   │  (Secure Import)     │
│  Port 3000  │   Mic/Spk   │   /dev/vid  │   /media, /mnt       │
└─────────────┴─────────────┴─────────────┴──────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                       API Gateway (Port 8000)                     │
│  - Request routing                                                │
│  - Load balancing                                                 │
│  - Health check aggregation                                       │
└──────────────────────────────────────────────────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                     Microservices Layer                           │
├───────────────┬────────────┬────────────┬────────────┬──────────┤
│  AI Brain     │    Meds    │   Habits   │  Finance   │  Voice   │
│  (9004)       │   (9001)   │   (9003)   │  (9005)    │  (9009)  │
│               │            │            │            │          │
│  - RAG        │  - CRUD    │  - Track   │  - Budget  │  - STT   │
│  - LLM        │  - OCR     │  - Analyze │  - OCR     │  - TTS   │
│  - Memory     │  - Remind  │  - Predict │  - Report  │  - Wake  │
├───────────────┼────────────┼────────────┼────────────┼──────────┤
│  Reminder     │    Cam     │ ML Engine  │  Library   │   USB    │
│  (9002)       │   (9007)   │   (9008)   │  (9006)    │  (8006)  │
│               │            │            │            │          │
│  - Schedule   │  - Detect  │  - Train   │  - Store   │  - Sync  │
│  - Notify     │  - Monitor │  - Batch   │  - Encrypt │  - Secure│
│  - ACK        │  - Alert   │  - Infer   │  - Search  │  - Import│
└───────────────┴────────────┴────────────┴────────────┴──────────┘
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                        Data Layer                                 │
├─────────────────────┬───────────────────┬────────────────────────┤
│  SQLite Databases   │  Vector Indices   │  File Storage          │
│  - Memories         │  - HNSW Index     │  - Audio (TTS/STT)     │
│  - Medications      │  - Embeddings     │  - Images (OCR)        │
│  - Habits           │  - Partitions     │  - Receipts            │
│  - Finances         │                   │  - Logs                │
│  - Reminders        │                   │                        │
└─────────────────────┴───────────────────┴────────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                     ML/AI Models (Local)                          │
├──────────────┬──────────────┬──────────────┬───────────────────┤
│  Llama 3.1   │  Whisper     │  Piper TTS   │  MiniLM          │
│  8B Instruct │  (Tiny/Base) │  (en-US)     │  Embeddings      │
│  (Ollama)    │  (STT)       │  (Voice)     │  (Semantic)      │
└──────────────┴──────────────┴──────────────┴───────────────────┘
```

---

## Architecture Principles

### 1. **Privacy-First Design**
- **Zero external dependencies** - All processing happens locally
- **Air-gapped deployment** - No internet required for operation
- **Data sovereignty** - User owns 100% of their data
- **Encryption at rest** - Fernet encryption for sensitive memories
- **No telemetry** - Zero data collection or tracking

### 2. **Microservices Architecture**
- **Loose coupling** - Services communicate via REST APIs
- **Single responsibility** - Each service has one focused purpose
- **Independent scaling** - Services can be scaled individually
- **Fault isolation** - Service failures don't cascade
- **Technology diversity** - Services can use different tools

### 3. **Offline-First Operation**
- **Local LLM** - Ollama with Llama 3.1 8B model
- **Local STT/TTS** - Whisper and Piper for voice
- **Local ML** - scikit-learn for predictive analytics
- **Local embeddings** - sentence-transformers for semantic search
- **No cloud APIs** - Complete independence from external services

### 4. **Scalability & Performance**
- **Async processing** - Non-blocking background tasks
- **Data partitioning** - Time/source/user-based partitioning
- **Vector indexing** - HNSW for fast similarity search
- **Resource management** - Adaptive batch sizing
- **Caching** - Embedding and query result caching

### 5. **User-Centric Design**
- **Accessibility** - Voice, touch, keyboard interfaces
- **Simplicity** - Minimal cognitive load for elderly users
- **Reliability** - 99.9%+ uptime with health checks
- **Transparency** - Explainable AI with confidence scores
- **Control** - User can export/delete all data

---

## Service Architecture

### Microservices Breakdown

#### 1. AI Brain Service (Port 9004)
**Purpose:** Core intelligence - memory management, RAG, LLM responses

**Responsibilities:**
- Memory ingestion and storage (medications, habits, finances, voice, camera)
- Semantic search using sentence-transformers embeddings
- LLM integration with Ollama (Llama 3.1 8B)
- Retrieval-Augmented Generation (RAG) for context-aware responses
- Knowledge graph construction and reasoning
- Predictive analytics (habit/health forecasting)
- Conversation management with goal tracking

**Tech Stack:**
- FastAPI for REST API
- SQLAlchemy ORM with SQLite
- sentence-transformers for embeddings (all-MiniLM-L6-v2)
- Ollama Python client for LLM
- NetworkX for knowledge graphs
- Cryptography (Fernet) for encryption

**Database Schema:**
- `memories` table: id, text_blob, embedding_json, source, metadata_json, created_at, importance_score, encrypted

**Key Algorithms:**
- Cosine similarity for semantic search
- HNSW indexing for approximate nearest neighbors
- Hierarchical memory consolidation
- Importance scoring based on recency, relevance, and user engagement

---

#### 2. Medications Service (Port 9001)
**Purpose:** Medication tracking and OCR prescription analysis

**Responsibilities:**
- CRUD operations for medications
- Prescription OCR with Tesseract
- Medication interaction warnings
- Adherence tracking
- Refill reminders

**Tech Stack:**
- FastAPI
- SQLite with SQLAlchemy
- Tesseract OCR for prescription analysis
- OpenCV for image preprocessing

**Database Schema:**
- `medications` table: id, name, dosage, frequency, prescribing_doctor, start_date, end_date, active, instructions

---

#### 3. Habit Tracking Service (Port 9003)
**Purpose:** Track daily habits and health activities

**Responsibilities:**
- Habit creation and management
- Completion logging with timestamps
- Streak calculation
- Pattern recognition
- Goal tracking

**Tech Stack:**
- FastAPI
- SQLite with SQLAlchemy
- Pandas for data analysis
- Matplotlib for visualizations (planned)

**Database Schema:**
- `habits` table: id, name, type, frequency, target_duration, reminder_time, active
- `habit_completions` table: id, habit_id, completed_at, duration_minutes, notes

---

#### 4. Financial Service (Port 9005)
**Purpose:** Budget and expense tracking for medical costs

**Responsibilities:**
- Transaction CRUD
- Receipt OCR
- Budget management
- Spending insights
- Category-based reporting

**Tech Stack:**
- FastAPI
- SQLite with SQLAlchemy
- Tesseract OCR
- Pandas for analytics

**Database Schema:**
- `transactions` table: id, amount, category, description, date, payment_method
- `budgets` table: id, category, monthly_limit, current_spent

---

#### 5. Reminder Service (Port 9002)
**Purpose:** Scheduled reminders and notifications

**Responsibilities:**
- Reminder creation with recurrence patterns
- Time-based scheduling
- Acknowledgment tracking
- Integration with AI Brain for smart reminders

**Tech Stack:**
- FastAPI
- SQLite with SQLAlchemy
- APScheduler for job scheduling

**Database Schema:**
- `reminders` table: id, title, type, scheduled_time, recurrence, recurrence_days, status, next_occurrence
- `acknowledgments` table: id, reminder_id, acknowledged_at, action_taken

---

#### 6. Voice Service (Port 9009)
**Purpose:** Speech-to-text and text-to-speech

**Responsibilities:**
- Voice transcription with Whisper
- Voice synthesis with Piper TTS
- Wake word detection (planned)
- Audio file management

**Tech Stack:**
- FastAPI
- Whisper.cpp (local STT)
- Piper TTS (local voice synthesis)
- PyAudio for audio capture

**Audio Formats:**
- Input: WAV, MP3
- Output: WAV (16kHz, mono)

---

#### 7. Camera Service (Port 9007)
**Purpose:** Visual monitoring and prescription OCR

**Responsibilities:**
- Activity detection
- Fall detection (planned)
- Prescription OCR
- Receipt capture
- Privacy-preserving processing (no cloud uploads)

**Tech Stack:**
- FastAPI
- OpenCV for image processing
- Tesseract OCR
- YOLO for object detection (planned)

**Privacy Features:**
- All processing local
- No image uploads
- Optional image deletion after processing

---

#### 8. ML Engine Service (Port 9008)
**Purpose:** Machine learning model training and inference

**Responsibilities:**
- Habit adherence prediction
- Health pattern recognition
- Anomaly detection
- Model training on historical data

**Tech Stack:**
- FastAPI
- scikit-learn for ML models
- Pandas for data preprocessing
- Joblib for model persistence

**Models:**
- Random Forest for habit prediction
- LSTM for time-series forecasting (planned)
- Clustering for pattern recognition

---

#### 9. Library of Truth Service (Port 9006)
**Purpose:** Long-term knowledge storage and retrieval

**Responsibilities:**
- Store consolidated memories
- Encrypted storage for sensitive data
- Fast search and retrieval
- Data export/import

**Tech Stack:**
- FastAPI
- SQLite with full-text search
- Cryptography (Fernet) for encryption

**Security:**
- Admin key authentication
- Fernet encryption for PII
- Audit logging

---

#### 10. USB Transfer Service (Port 8006)
**Purpose:** Secure USB data import/export

**Responsibilities:**
- Detect USB devices
- Encrypted data transfer
- Backup and restore
- Security scanning

**Tech Stack:**
- FastAPI
- pyudev for USB detection
- Cryptography for encryption

**Security:**
- Whitelisted USB devices
- Virus scanning (ClamAV planned)
- Encrypted backups

---

#### 11. API Gateway (Port 8000)
**Purpose:** Central entry point for all client requests

**Responsibilities:**
- Request routing to appropriate services
- Load balancing (future)
- Health check aggregation
- Request logging

**Tech Stack:**
- FastAPI
- httpx for service communication

**Routing Rules:**
- `/chat` → AI Brain (9004)
- `/meds` → Medications (9001)
- `/habits` → Habits (9003)
- `/finance` → Financial (9005)
- `/reminders` → Reminder (9002)
- `/voice` → Voice (9009)

---

#### 12. Frontend Service (Ports 80/443)
**Purpose:** User interface for tablet interaction

**Responsibilities:**
- Tablet-optimized React UI
- Real-time updates
- Voice interaction UI
- Settings management

**Tech Stack:**
- React 18.3 + TypeScript
- TailwindCSS for styling
- Framer Motion for animations
- Recharts for visualizations
- Nginx for serving static files

**Pages:**
1. Dashboard - Health overview, quick actions
2. Medications - Med list, schedule, adherence
3. Reminders - Upcoming reminders, ACK
4. Finance - Budget, transactions
5. Habits - Tracking, streaks, insights
6. Admin - Settings, export, logs

---

## Data Flow

### 1. User Chat Interaction Flow

```
User → Frontend (React) → Gateway (8000) → AI Brain (9004)
                                              ↓
                                        1. Parse message
                                        2. Generate embedding
                                        3. Search memories (vector DB)
                                        4. Retrieve top K memories
                                        5. Build RAG context
                                        6. Send to LLM (Ollama)
                                        7. Stream response
                                              ↓
Frontend ← Gateway ← AI Brain ← LLM Response
```

**Step Details:**

1. **Frontend** - User types message in chat UI
2. **Gateway** - Routes POST /chat to AI Brain
3. **AI Brain** - Receives message, checks if memory search needed
4. **Embedding Generation** - Convert message to 384-dim vector using MiniLM
5. **Vector Search** - Cosine similarity search in SQLite (or HNSW index)
6. **Context Building** - Top 5-10 memories formatted as RAG context
7. **LLM Prompt** - System prompt + context + user message → Ollama
8. **Response Streaming** - LLM generates response token-by-token
9. **Return to User** - Frontend displays response with sources

**Optimization:**
- Embedding caching (reduces latency by 3-5x)
- HNSW indexing (10-100x faster search)
- Async processing (non-blocking)

---

### 2. Medication Tracking Flow

```
User scans prescription → Camera/Upload → Gateway → AI Brain
                                              ↓
                                    1. OCR extraction (Tesseract)
                                    2. Parse medication details
                                    3. Store in Meds service
                                    4. Create memory in AI Brain
                                    5. Set reminders
                                              ↓
Database ← Meds Service ← Reminder Service
```

**OCR Processing:**
1. Image preprocessing (grayscale, contrast, deskew)
2. Tesseract OCR extraction
3. Regex parsing for medication name, dosage, frequency
4. Confidence scoring (threshold: 0.7)
5. User confirmation if low confidence

---

### 3. Habit Completion Flow

```
User → Frontend → Gateway → Habits Service
                                 ↓
                          1. Log completion
                          2. Update streak
                          3. Calculate stats
                          4. Notify AI Brain
                                 ↓
                          AI Brain creates memory
                                 ↓
                          ML Engine updates patterns
```

---

### 4. Predictive Insights Flow

```
Scheduled Task (daily) → ML Engine
                              ↓
                        1. Fetch recent memories
                        2. Train/update models
                        3. Generate predictions
                        4. Send to AI Brain
                              ↓
                        AI Brain → Proactive reminders
                              ↓
                        Frontend displays insights
```

---

## Technology Stack

### Backend

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Web Framework** | FastAPI | REST APIs, async support, auto docs |
| **ORM** | SQLAlchemy | Database abstraction |
| **Database** | SQLite (WAL mode) | Lightweight, embedded, ACID |
| **Embeddings** | sentence-transformers | Semantic search (all-MiniLM-L6-v2) |
| **LLM** | Ollama (Llama 3.1 8B) | Local conversational AI |
| **STT** | Whisper.cpp | Speech-to-text (tiny/base models) |
| **TTS** | Piper | Text-to-speech (en-US voice) |
| **OCR** | Tesseract | Prescription/receipt analysis |
| **Computer Vision** | OpenCV | Image preprocessing |
| **ML** | scikit-learn | Predictive models |
| **Graphs** | NetworkX | Knowledge graph |
| **Encryption** | Cryptography (Fernet) | Data encryption |
| **Job Scheduling** | APScheduler | Reminder scheduling |

### Frontend

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Framework** | React 18.3 | UI components |
| **Language** | TypeScript | Type safety |
| **Styling** | TailwindCSS | Utility-first CSS |
| **Animation** | Framer Motion | Smooth transitions |
| **Charts** | Recharts | Data visualization |
| **HTTP Client** | Axios | API requests |
| **Routing** | React Router | SPA navigation |
| **Build** | Webpack (react-scripts) | Bundling |
| **Server** | Nginx | Static file serving, reverse proxy |

### Infrastructure

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Containerization** | Docker | Service isolation |
| **Orchestration** | Docker Compose | Multi-container management |
| **Networking** | Docker bridge | Inter-service communication |
| **SSL/TLS** | OpenSSL (self-signed) | Local HTTPS |
| **Health Checks** | Docker healthcheck | Service monitoring |

---

## AI/ML Pipeline

### 1. Embedding Pipeline

```
Text Input → Tokenization → Model Inference → 384-dim Vector
     ↓              ↓                ↓                ↓
"Take meds"  → [101,2202,...] → MiniLM-L6-v2 → [0.45, -0.12, ...]
```

**Model:** `sentence-transformers/all-MiniLM-L6-v2`
- **Size:** 23MB (quantized)
- **Dimensions:** 384
- **Speed:** ~50 embeddings/second (CPU)
- **Quality:** High for semantic similarity

**Caching Strategy:**
- LRU cache for frequent queries
- TTL: 1 hour
- Max size: 10,000 embeddings

---

### 2. RAG Pipeline

```
User Query → Embedding → Vector Search → Top K Memories
                                              ↓
                                        Context Window
                                              ↓
                            System Prompt + Context + Query
                                              ↓
                                        LLM (Llama 3.1)
                                              ↓
                                          Response
```

**Context Window Management:**
- Max tokens: 2048 (Llama 3.1 limit: 8192)
- Context allocation: 1500 tokens for memories, 500 for prompt
- Memory ranking: Cosine similarity + recency + importance

**Prompt Template:**
```
System: You are Kilo, a helpful AI health assistant.

Context (from user's memory):
[Memory 1: High relevance]
[Memory 2: Medium relevance]
...

User: {user_query}