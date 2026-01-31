# Kilo AI Learning System - Implementation Plan

## Overview
Transform Kilo from a static assistant to a learning system that adapts to Kyle's patterns and behaviors.

---

## Phase 1: Foundation Upgrades (Week 1)

### 1.1 Remove OpenAI Fallback
**Why**: Air-gapped system, Kilo should be fully local
**Changes**:
- Remove all OpenAI API code from `ai_brain/main.py`
- Force Ollama-only mode
- Update personality to "Kilo" instead of generic assistant

**Files to Modify**:
- `microservice/ai_brain/main.py`

### 1.2 Optimize for Beelink SER7-9
**Hardware Specs**:
- CPU: AMD Ryzen 9 7940HS (8 cores, 16 threads)
- RAM: 16-32GB DDR5
- GPU: Radeon 780M (integrated, 12 compute units)
- Storage: NVMe SSD

**Model Recommendations**:
- **Primary LLM**: Llama 3.1 8B (Q5_K_M quantization)
  - Memory: ~6GB
  - Speed: ~30-40 tokens/sec on CPU, ~60-80 on GPU
  - Quality: Excellent, comparable to GPT-3.5+

- **Embedding Model**: all-MiniLM-L6-v2 (current)
  - Memory: ~100MB
  - Fast enough on CPU

- **Learning Model**: scikit-learn + lightweight neural net
  - Memory: <500MB
  - Training: Runs in background

**Docker Configuration Updates**:
```yaml
ollama:
  environment:
    - OLLAMA_NUM_PARALLEL=2  # Can handle 2 concurrent requests
    - OLLAMA_MAX_LOADED_MODELS=2
    - OLLAMA_GPU_LAYERS=33  # Use integrated GPU
```

### 1.3 Tablet as Thin Client
**Architecture**:
```
Tablet (Frontend Only)
  ↓ HTTP requests over LAN
Beelink SER7-9 (All Processing)
  - Gateway (port 8000)
  - AI Brain (port 9004)
  - All microservices
  - Databases
  - ML training
```

**Network Setup**:
- Static IP for Beelink: `192.168.1.100` (example)
- Tablet connects via WiFi
- Frontend `.env.local`: `REACT_APP_API_URL=http://192.168.1.100:8000`

---

## Phase 2: Machine Learning System (Week 2-3)

### 2.1 Learning System Architecture

**Data Collection** (Already Happening):
- Habit completions with timestamps
- Medication adherence patterns
- Financial spending habits
- Reminder completion rates

**Learning Goals**:
1. **Habit Prediction**: Predict if Kyle will complete a habit today
2. **Optimal Timing**: Learn best times to send reminders
3. **Pattern Recognition**: Identify correlations (e.g., "Kyle takes meds after morning coffee")
4. **Personalized Motivation**: Generate custom encouragement based on what works

### 2.2 ML Models to Implement

#### Model 1: Habit Completion Predictor
**Algorithm**: Logistic Regression + Random Forest
**Features**:
- Day of week
- Time of day
- Recent streak length
- Weather (if available)
- Other habits completed today
- Previous week's completion rate

**Output**: Probability Kyle will complete habit (0-1)

**Use Case**: If probability < 0.6, send proactive reminder

#### Model 2: Optimal Reminder Time
**Algorithm**: K-Means Clustering + Time Series Analysis
**Features**:
- Historical completion times
- Success rate by hour
- Day of week patterns

**Output**: Best 3 time windows to send reminders

#### Model 3: Habit Trigger Detection
**Algorithm**: Association Rule Mining (Apriori algorithm)
**Features**:
- Habit co-occurrence patterns
- Temporal sequences (habit A → habit B)

**Output**: Rules like "If morning_coffee completed, remind take_meds in 15min"

### 2.3 New Microservice: ML Engine

**New Service**: `microservice/ml_engine/main.py`

**Endpoints**:
- `POST /train/habits` - Train habit prediction models
- `GET /predict/habit/{habit_id}` - Get completion probability
- `GET /recommend/reminder_time/{habit_id}` - Get optimal reminder times
- `GET /insights/patterns` - Get discovered patterns

**Training Schedule**:
- Nightly at 2 AM (lightweight, runs in background)
- Incremental learning (updates existing models)
- Stores trained models in `/data/ml_models/`

**Tech Stack**:
```python
# Libraries for ML Engine
- scikit-learn (classical ML)
- pandas (data processing)
- numpy (numerical ops)
- joblib (model persistence)
```

---

## Phase 3: Voice Interface (Week 4)

### 3.1 Voice Architecture

**Flow**:
```
Tablet Microphone
  ↓ (Record audio, send to Brain)
Beelink SER7-9: Whisper Model (speech-to-text)
  ↓ (Text transcription)
Kilo AI Brain (process request)
  ↓ (Generate response)
Beelink SER7-9: Piper TTS (text-to-speech)
  ↓ (Audio file)
Tablet Speakers (play audio)
```

### 3.2 Voice Models (Local)

**Speech-to-Text**: Whisper.cpp
- Model: `whisper-small` (244MB)
- Languages: English + others
- Accuracy: ~95% for clear speech
- Speed: Real-time on Ryzen 9

**Text-to-Speech**: Piper TTS
- Model: `en_US-lessac-medium` (63MB)
- Quality: Natural-sounding voice
- Speed: Faster than real-time
- Customizable voice (can train on your voice)

### 3.3 Implementation

**New Service**: `microservice/voice/main.py`

**Endpoints**:
- `POST /transcribe` - Audio → Text (Whisper)
- `POST /synthesize` - Text → Audio (Piper)
- `POST /chat` - Full voice chat (transcribe → AI → synthesize)

**Frontend Changes**:
- Add microphone button on Dashboard
- "Hold to talk" interaction
- Display transcription + response
- Auto-play audio response

**Wake Word** (Optional):
- Use Porcupine wake word detection
- Wake phrase: "Hey Kilo"
- Always-listening mode for hands-free

---

## Phase 4: Advanced Learning Features (Week 5+)

### 4.1 Personalized AI Responses

**Context-Aware Responses**:
Kilo learns Kyle's:
- Communication style preferences
- Motivational triggers (what encourages you)
- Stress patterns (when you need gentler reminders)
- Humor preferences

**Implementation**:
- Store response feedback (thumbs up/down on AI responses)
- Fine-tune response generation using LoRA adapters
- Small model (~100MB) that customizes Llama 3.1's output

### 4.2 Predictive Reminders

**Proactive Behavior**:
Instead of just reminding you at set times, Kilo:
- Predicts when you'll forget
- Detects anomalies ("You usually take meds by now, reminder?")
- Suggests new habits based on patterns ("You always exercise after work, want to track that?")

### 4.3 Long-Term Memory

**Enhanced RAG System**:
- **Episodic Memory**: Remembers conversations and context
- **Semantic Memory**: Understands concepts (e.g., "Kyle prefers concise reminders")
- **Procedural Memory**: Learns routines and sequences

**Implementation**:
- Upgrade embedding model to `all-mpnet-base-v2` (better quality)
- Add memory consolidation (summarize old memories nightly)
- Implement memory importance scoring (forget trivial, remember important)

---

## Phase 5: Model Training on Kyle's Data (Ongoing)

### 5.1 Data Pipeline

**Continuous Learning Loop**:
```
1. Kyle uses Kilo daily
2. System collects interaction data
3. Nightly: ML models retrain on new data
4. Next day: Kilo is slightly better adapted
5. Repeat
```

### 5.2 Privacy-Preserving Learning

**All Training Happens Locally**:
- No data leaves the Beelink device
- Encrypted database for sensitive memories
- User control: Can delete specific memories
- Model checkpoints: Can "roll back" if learning goes wrong

### 5.3 Feedback Mechanisms

**Kyle Provides Feedback**:
- "Was this reminder helpful?" (Yes/No)
- "Rate this AI response" (1-5 stars)
- "Mark habit as completed" (positive signal)
- Ignore reminder (negative signal)

**System Learns From**:
- Explicit feedback (ratings)
- Implicit feedback (what you actually do)
- Temporal patterns (when you're active)

---

## Implementation Priority

### High Priority (Start Immediately)
1. ✅ Remove OpenAI fallback
2. ✅ Update personality to "Kilo"
3. ✅ Optimize Ollama for Beelink specs
4. 🔄 Implement basic ML Engine service
5. 🔄 Deploy habit completion predictor

### Medium Priority (Next 2-3 Weeks)
6. 🔄 Voice interface (Whisper + Piper)
7. 🔄 Optimal reminder timing model
8. 🔄 Pattern detection system

### Low Priority (Future Enhancements)
9. ⏳ Fine-tune LLM on Kyle's style
10. ⏳ Wake word detection
11. ⏳ Advanced memory consolidation

---

## Technical Specifications

### ML Engine Requirements
```dockerfile
FROM python:3.11-slim

RUN pip install \
    scikit-learn==1.3.2 \
    pandas==2.1.4 \
    numpy==1.26.2 \
    joblib==1.3.2 \
    fastapi==0.104.1 \
    sqlmodel==0.0.14

WORKDIR /app
COPY main.py .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9006"]
```

### Voice Service Requirements
```dockerfile
FROM python:3.11-slim

# Install Whisper.cpp and Piper TTS
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    build-essential

RUN pip install \
    faster-whisper==0.10.0 \
    piper-tts==1.2.0 \
    fastapi==0.104.1

WORKDIR /app
COPY main.py .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9007"]
```

### Ollama Configuration for Llama 3.1 8B
```bash
# Pull model
docker-compose exec ollama ollama pull llama3.1:8b-instruct-q5_K_M

# Set as default in AI Brain
AI_BRAIN_MODEL=llama3.1:8b-instruct-q5_K_M
```

---

## Performance Expectations

### Beelink SER7-9 with 32GB RAM

**Concurrent Capacity**:
- Llama 3.1 8B: 2 simultaneous users
- Whisper Small: 3 simultaneous transcriptions
- ML training: Background (doesn't interrupt other tasks)

**Response Times**:
- Chat response: 1-3 seconds (50 tokens)
- Voice transcription: <1 second per 10 seconds of audio
- Habit prediction: <100ms
- Pattern analysis: <500ms

### Network Requirements
- Tablet ↔ Brain: 100 Mbps LAN (WiFi 5 or better)
- Latency: <10ms on local network

---

## Next Steps

### Immediate Actions
1. Run implementation of Phase 1 changes
2. Set up ML Engine service skeleton
3. Test upgraded Llama 3.1 model
4. Implement basic habit predictor

### Questions for Kyle
1. Do you have the Beelink yet, or planning to get it?
2. What RAM configuration? (16GB or 32GB recommended)
3. Priority: Voice interface or ML learning first?
4. Any specific habits you want Kilo to learn first?

---

## Learning System Example

**After 1 Week of Data**:
```
Kilo learns: Kyle takes morning meds 90% of time at 8:15 AM
```

**After 1 Month of Data**:
```
Kilo learns:
- Kyle more likely to exercise on Mon/Wed/Fri
- Medication adherence drops on weekends (send extra reminder)
- Financial tracking happens mostly on Sundays
```

**After 3 Months of Data**:
```
Kilo predicts:
- "It's Wednesday, 85% chance Kyle will exercise - preemptively encourage"
- "Kyle hasn't logged water intake by 2 PM, unusual - gentle reminder"
- "Spending pattern suggests budget overrun by month-end - early warning"
```

This is **true personalization** - Kilo becomes YOUR assistant, not a generic one.
