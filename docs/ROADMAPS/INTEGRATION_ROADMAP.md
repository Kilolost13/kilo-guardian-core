# Kilo Guardian System - Integration Roadmap

**Document Version:** 1.0
**Last Updated:** December 27, 2025
**Status:** Planning Phase - Awaiting Resources

---

## Executive Summary

This document outlines the transformation of Kilo Guardian from a collection of independent microservices into a fully integrated, AI-powered medication adherence and health coaching system. The goal is to create a seamless experience where adding a medication automatically triggers reminders, habit tracking, AI monitoring, and proactive coaching.

**Target Outcome:** A system that not only reminds Kyle to take medications but actively learns his patterns, predicts adherence issues, and provides personalized coaching to improve health outcomes.

---

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Target State Vision](#target-state-vision)
3. [Architecture Evolution](#architecture-evolution)
4. [Development Phases](#development-phases)
5. [Timeline & Resources](#timeline--resources)
6. [Technical Requirements](#technical-requirements)
7. [API Changes & Extensions](#api-changes--extensions)
8. [Testing Strategy](#testing-strategy)
9. [Risk Assessment](#risk-assessment)
10. [Success Metrics](#success-metrics)

---

## Current State Analysis

### Working Modules (v1.0 - Production Ready)

#### ✅ Medications Service (Port 9001)
- **Status:** Fully functional
- **Features:**
  - CRUD operations for medications
  - Fields: name, schedule, dosage, quantity, prescriber, instructions
  - Prescription scanning via OCR (tablet camera)
  - SQLite persistence
- **Limitations:**
  - No automatic reminder creation
  - No habit tracking integration
  - No adherence monitoring
  - Manual data entry required

#### ✅ Reminder Service (Port 9002)
- **Status:** Fully functional
- **Features:**
  - Create one-time and recurring reminders
  - Flexible scheduling (daily, weekly, hourly, cron)
  - Preset templates (meds, hygiene, chores)
  - APScheduler background job execution
- **Limitations:**
  - No automatic creation from medication schedules
  - No confirmation that dose was taken
  - No missed dose tracking
  - No integration with habits or AI

#### ✅ Habits Service (Port 9003)
- **Status:** Fully functional
- **Features:**
  - Track habit completions
  - Frequency tracking (daily, weekly, etc.)
  - Completion history
- **Limitations:**
  - Manual completion logging
  - No automatic tracking from reminders
  - No streak tracking
  - No adherence analytics

#### ✅ AI Brain Service (Port 9004)
- **Status:** Functional with basic RAG
- **Features:**
  - Retrieval Augmented Generation (RAG)
  - Semantic memory search with sentence-transformers
  - Local LLM support (Ollama: tinyllama/mistral)
  - Memory storage with encryption for sensitive data
  - Query endpoint for conversational interactions
- **Limitations:**
  - No event subscriptions
  - No proactive monitoring
  - No pattern detection
  - No coaching recommendations
  - Reactive only (responds to queries, doesn't initiate)

#### ✅ Financial Service (Port 9005)
- **Status:** Functional
- **Features:** Transaction tracking, receipt OCR
- **Relevance:** Track medication costs, insurance claims

#### ✅ Gateway Service (Port 8000)
- **Status:** Functional
- **Features:** API routing, health checks, CORS
- **Limitations:**
  - Simple proxy only
  - No event bus
  - No service-to-service orchestration

### Current Architecture Pattern

```
┌─────────────┐
│   Frontend  │
│  (React)    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Gateway   │
│  (FastAPI)  │
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────┐
│  Independent Microservices           │
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐        │
│  │Meds│ │Rem │ │Hab │ │AI  │        │
│  └────┘ └────┘ └────┘ └────┘        │
│    ↕      ↕      ↕      ↕            │
│  [SQLite DBs - No Communication]    │
└──────────────────────────────────────┘
```

**Key Observation:** Services are completely isolated. No cross-service communication exists.

---

## Target State Vision

### The Integrated Experience

#### Scenario: Kyle Adds a New Medication

**Current Workflow:**
1. Kyle adds "Lisinopril 10mg, once daily at 8am" to Meds service
2. Kyle manually creates a reminder for 8am
3. Kyle manually creates a habit "Take Lisinopril"
4. Kyle manually logs each dose
5. No tracking if he misses doses
6. No AI assistance

**Target Workflow:**
1. Kyle adds "Lisinopril 10mg, once daily at 8am" to Meds service
2. **System automatically:**
   - Creates recurring daily reminder at 8am
   - Creates habit "Take Lisinopril" with daily frequency
   - Links reminder → medication → habit
   - AI Brain subscribes to medication adherence events
3. **At 8am:** Reminder fires
4. **Kyle confirms dose:**
   - Taps reminder notification
   - System logs habit completion
   - AI Brain records adherence event
   - Updates medication quantity (-1)
5. **If missed:**
   - 8:30am: AI detects missed reminder
   - 9am: Gentle coaching message: "Hey Kyle, noticed you haven't taken your Lisinopril yet. Everything okay?"
   - Offers to snooze or mark as taken
6. **Pattern detection:**
   - AI notices: "Kyle is often 30 minutes late on weekends"
   - Suggestion: "Would you like to move weekend reminders to 8:30am?"
7. **Running low:**
   - AI detects: "You have 3 days of Lisinopril left"
   - Proactive: "Time to refill your prescription. Would you like me to remind you to call the pharmacy?"

### Target Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Frontend                         │
│            (React - Tablet Optimized)               │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│              Gateway + Event Bus                    │
│  ┌──────────┐  ┌─────────────┐  ┌──────────────┐   │
│  │  Router  │  │ Event Queue │  │ Orchestrator │   │
│  └──────────┘  └─────────────┘  └──────────────┘   │
└──────┬──────────────┬───────────────┬──────────────┘
       │              │               │
       │         ┌────▼────┐          │
       │         │ Events: │          │
       │         │ • med.added        │
       │         │ • reminder.fired   │
       │         │ • dose.taken       │
       │         │ • dose.missed      │
       │         └─────────┘          │
       │                              │
┌──────▼──────────────────────────────▼──────────────┐
│         Integrated Microservices                    │
│                                                     │
│  ┌──────────┐      ┌──────────┐      ┌─────────┐  │
│  │   Meds   │─────▶│ Reminders│─────▶│ Habits  │  │
│  │  Service │◀─────│  Service │◀─────│ Service │  │
│  └──────────┘      └──────────┘      └─────────┘  │
│       │                  │                 │       │
│       │                  │                 │       │
│       └──────────────────┼─────────────────┘       │
│                          │                         │
│                    ┌─────▼─────┐                   │
│                    │ AI Brain  │                   │
│                    │  Service  │                   │
│                    │           │                   │
│                    │ • Monitor │                   │
│                    │ • Analyze │                   │
│                    │ • Coach   │                   │
│                    │ • Predict │                   │
│                    └───────────┘                   │
└─────────────────────────────────────────────────────┘
```

---

## Architecture Evolution

### 1. Service-to-Service Communication

#### Current: No Communication
Services cannot talk to each other. Frontend is the only client.

#### Target: Direct API Calls + Event Bus

**Option A: Direct Service-to-Service HTTP Calls**
- Meds service calls Reminder service API directly
- Pros: Simple, synchronous, easy to debug
- Cons: Tight coupling, cascade failures

**Option B: Event-Driven Architecture (Recommended)**
- Services publish events to event bus
- Other services subscribe to relevant events
- Pros: Loose coupling, scalable, resilient
- Cons: Eventual consistency, more complex

**Recommended Hybrid Approach:**
- Use direct HTTP calls for immediate actions (create reminder when med added)
- Use events for monitoring and analytics (AI Brain subscribes to all events)

#### Implementation: Simple Event Bus

```python
# shared/event_bus.py
from typing import Callable, Dict, List
import httpx
import os

class EventBus:
    """Simple HTTP-based event bus for service communication"""

    def __init__(self):
        self.subscribers: Dict[str, List[str]] = {}

    async def publish(self, event_type: str, payload: dict):
        """Publish event to all subscribers"""
        subscribers = self.subscribers.get(event_type, [])

        async with httpx.AsyncClient() as client:
            for subscriber_url in subscribers:
                try:
                    await client.post(
                        f"{subscriber_url}/events",
                        json={"type": event_type, "data": payload},
                        timeout=5.0
                    )
                except Exception as e:
                    print(f"Failed to notify {subscriber_url}: {e}")
                    # Continue to other subscribers

    def subscribe(self, event_type: str, callback_url: str):
        """Subscribe to event type"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback_url)

# Event types
EVENTS = {
    "medication.added": "New medication added",
    "medication.updated": "Medication details changed",
    "medication.deleted": "Medication removed",
    "reminder.fired": "Reminder triggered",
    "reminder.snoozed": "Reminder snoozed by user",
    "dose.taken": "User confirmed taking dose",
    "dose.missed": "Dose not taken within window",
    "habit.completed": "Habit marked complete",
    "pattern.detected": "AI detected behavioral pattern",
}
```

### 2. Cross-Service Dependencies

#### Medication → Reminder
When medication added/updated:
1. Parse schedule string (e.g., "twice daily at 8am and 8pm")
2. Create/update recurring reminders
3. Link reminder to medication (med_id in reminder preset)

#### Reminder → Habit
When reminder created for medication:
1. Create corresponding habit
2. Link habit to reminder preset

#### All Services → AI Brain
All services publish events to AI Brain:
1. AI Brain stores events as memories
2. Analyzes patterns over time
3. Generates coaching insights

### 3. Data Model Extensions

#### Enhanced Medication Model
```python
class Med(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    schedule: str  # e.g., "daily at 8am"
    dosage: str
    quantity: int
    prescriber: str
    instructions: str
    created_at: Optional[str] = None

    # NEW FIELDS
    reminder_ids: Optional[str] = None  # JSON array of reminder IDs
    habit_id: Optional[int] = None      # Linked habit
    adherence_rate: Optional[float] = None  # Calculated by AI
    last_taken: Optional[str] = None    # ISO datetime
    next_dose: Optional[str] = None     # ISO datetime
    low_quantity_threshold: int = 7     # Days supply before alert
```

#### Enhanced Reminder Model
```python
class Reminder(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    text: str
    when: str
    sent: bool = False
    recurrence: Optional[str] = None
    timezone: Optional[str] = None
    preset_id: Optional[int] = None

    # NEW FIELDS
    med_id: Optional[int] = None        # Link to medication
    habit_id: Optional[int] = None      # Link to habit
    confirmation_required: bool = False  # Wait for user confirmation
    confirmed_at: Optional[str] = None   # When user confirmed
    missed: bool = False                 # Marked as missed
    snooze_count: int = 0               # How many times snoozed
```

#### Enhanced Habit Model
```python
class Habit(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    frequency: str

    # NEW FIELDS
    med_id: Optional[int] = None        # Link to medication
    reminder_id: Optional[int] = None   # Link to reminder
    streak: int = 0                     # Current streak
    longest_streak: int = 0
    total_completions: int = 0
    adherence_rate: Optional[float] = None  # % completed on time
```

#### New: AdherenceEvent Model
```python
class AdherenceEvent(SQLModel, table=True):
    """Track all medication adherence events for AI analysis"""
    id: Optional[int] = Field(default=None, primary_key=True)
    med_id: int
    reminder_id: int
    event_type: str  # "taken", "missed", "snoozed", "late"
    scheduled_time: str  # ISO datetime
    actual_time: Optional[str] = None  # When actually taken
    minutes_late: Optional[int] = None
    created_at: str  # ISO datetime
    metadata: Optional[str] = None  # JSON for additional context
```

---

## Development Phases

### Phase 1: Medication → Reminder Integration (3-4 weeks)

**Goal:** When medication is added, automatically create appropriate reminders.

#### Tasks

**Week 1: Schedule Parsing & Reminder Creation**
- [ ] Create schedule parser (`shared/schedule_parser.py`)
  - Input: "twice daily at 8am and 8pm"
  - Output: List of reminder specs with times and recurrence
  - Support formats: "daily at 8am", "every 6 hours", "3x daily"
- [ ] Add `create_reminders_for_medication()` function to meds service
- [ ] Modify `POST /meds` endpoint to call reminder service
- [ ] Add error handling for reminder creation failures

**Week 2: Bidirectional Linking**
- [ ] Add `med_id` field to Reminder model (migration)
- [ ] Add `reminder_ids` field to Med model (migration)
- [ ] Update meds service to store reminder IDs
- [ ] Create `GET /meds/{id}/reminders` endpoint

**Week 3: Update & Delete Cascades**
- [ ] Update medication schedule → update linked reminders
- [ ] Delete medication → delete linked reminders
- [ ] Handle edge cases (partial failures, orphaned reminders)

**Week 4: Testing & UI Updates**
- [ ] Integration tests for meds-reminders flow
- [ ] Update frontend to show linked reminders on med detail page
- [ ] Add "View Reminders" button on medication card
- [ ] Documentation updates

**Deliverables:**
- ✅ Adding medication automatically creates reminders
- ✅ Reminders are linked to medications
- ✅ Updating/deleting meds updates/deletes reminders
- ✅ Frontend shows linked reminders

**API Changes:**
```python
# POST /meds (enhanced)
{
  "name": "Lisinopril",
  "schedule": "daily at 8am",
  "dosage": "10mg",
  ...
}
# Response now includes:
{
  "id": 1,
  "name": "Lisinopril",
  "reminder_ids": [15, 16],  # Auto-created
  ...
}

# New endpoint
GET /meds/{id}/reminders
# Returns array of linked reminder objects
```

---

### Phase 2: Reminders → Habits Tracking (2-3 weeks)

**Goal:** Track medication adherence as habits with completion logging.

#### Tasks

**Week 1: Reminder Confirmation Flow**
- [ ] Add `confirmation_required` flag to reminders
- [ ] Create `POST /reminders/{id}/confirm` endpoint
  - Marks reminder as confirmed
  - Records `confirmed_at` timestamp
  - Returns success
- [ ] Add timeout logic: mark as "missed" if not confirmed in X minutes
- [ ] Frontend: Add "Mark as Taken" button to reminder notifications

**Week 2: Habit Integration**
- [ ] Create habit when medication reminder is created
- [ ] Link reminder → habit (add `habit_id` to Reminder)
- [ ] When reminder confirmed → auto-complete habit
- [ ] Calculate streak and adherence rate

**Week 3: Adherence Tracking**
- [ ] Create AdherenceEvent table
- [ ] Log events: taken, missed, late, snoozed
- [ ] Create `GET /meds/{id}/adherence` endpoint
  - Returns adherence stats (rate, streak, history)
- [ ] Frontend: Adherence dashboard for each medication

**Deliverables:**
- ✅ Reminder confirmation flow works
- ✅ Habits auto-created and auto-completed
- ✅ Adherence tracking with history
- ✅ UI shows adherence stats

**API Changes:**
```python
# New endpoint
POST /reminders/{id}/confirm
{
  "taken_at": "2025-12-27T08:05:00"  # Optional, defaults to now
}
# Response:
{
  "ok": true,
  "habit_completed": true,
  "streak": 7
}

# New endpoint
GET /meds/{id}/adherence
# Response:
{
  "med_id": 1,
  "adherence_rate": 0.92,  # 92%
  "current_streak": 7,
  "longest_streak": 14,
  "recent_events": [
    {"date": "2025-12-27", "status": "taken", "minutes_late": 5},
    {"date": "2025-12-26", "status": "taken", "minutes_late": 0},
    {"date": "2025-12-25", "status": "missed"},
  ]
}
```

---

### Phase 3: AI Brain Monitoring (3-4 weeks)

**Goal:** AI Brain passively monitors all adherence events and builds pattern understanding.

#### Tasks

**Week 1: Event Subscription System**
- [ ] Implement simple event bus (see architecture section)
- [ ] All services publish events to AI Brain
- [ ] AI Brain `/events` endpoint to receive notifications
- [ ] Store events as Memory entries

**Week 2: Memory Enhancement for Adherence**
- [ ] Enhance Memory model with structured metadata
- [ ] Create specialized memory types:
  - `adherence_event`: dose taken/missed
  - `behavioral_pattern`: detected pattern
  - `coaching_interaction`: user response to coaching
- [ ] Build semantic search for adherence queries

**Week 3: Pattern Detection Algorithms**
- [ ] Detect late-taking patterns (e.g., "late on weekends")
- [ ] Detect miss patterns (e.g., "forgets evening dose")
- [ ] Detect improvement/decline trends
- [ ] Store patterns as memories with confidence scores

**Week 4: Query Interface**
- [ ] Create `POST /ai_brain/analyze_adherence` endpoint
  - Input: med_id or user_id
  - Output: Patterns, insights, recommendations
- [ ] Frontend: "AI Insights" panel on medication page
- [ ] Show detected patterns to user

**Deliverables:**
- ✅ AI Brain receives all adherence events
- ✅ Pattern detection working
- ✅ Query interface for insights
- ✅ UI displays AI insights

**API Changes:**
```python
# AI Brain receives events
POST /ai_brain/events
{
  "type": "dose.missed",
  "data": {
    "med_id": 1,
    "reminder_id": 15,
    "scheduled_time": "2025-12-27T08:00:00",
    "missed_at": "2025-12-27T09:00:00"
  }
}

# New endpoint
POST /ai_brain/analyze_adherence
{
  "med_id": 1,
  "days": 30  # Analyze last 30 days
}
# Response:
{
  "adherence_rate": 0.92,
  "patterns": [
    {
      "type": "late_on_weekends",
      "confidence": 0.85,
      "description": "You typically take your medication 30-45 minutes late on Saturday and Sunday",
      "occurrences": 6,
      "suggestion": "Consider moving weekend reminders to 8:30am"
    }
  ],
  "insights": [
    "Your adherence has improved by 15% over the last month!",
    "You have a 7-day streak going - great work!"
  ]
}
```

---

### Phase 4: Proactive AI Coaching (4-5 weeks)

**Goal:** AI Brain actively coaches user with timely, personalized interventions.

#### Tasks

**Week 1: Proactive Notification System**
- [ ] Create notification queue in AI Brain
- [ ] AI generates coaching messages based on events
- [ ] Deliver via:
  - Frontend notifications (WebSocket)
  - Optional: SMS (Twilio integration)
  - Optional: Email
- [ ] User preferences for notification frequency

**Week 2: Coaching Message Generation**
- [ ] Template system for common scenarios:
  - Missed dose (gentle reminder)
  - Low quantity (refill reminder)
  - Pattern detected (suggestion)
  - Streak milestone (encouragement)
- [ ] LLM-powered personalized messages
- [ ] Tone: Supportive, non-judgmental, encouraging

**Week 3: Context-Aware Interventions**
- [ ] Time-based: Don't notify late at night
- [ ] Frequency: Don't overwhelm user
- [ ] Effectiveness tracking: Learn what works
- [ ] User feedback on messages (helpful/not helpful)

**Week 4: Conversational Interface**
- [ ] Chat interface for medication questions
- [ ] "Ask AI about my medications"
- [ ] RAG-enhanced responses using:
  - Medication instructions
  - Adherence history
  - Medical knowledge base

**Week 5: Testing & Refinement**
- [ ] A/B test message effectiveness
- [ ] Tune notification timing
- [ ] User acceptance testing
- [ ] Privacy review

**Deliverables:**
- ✅ Proactive coaching messages
- ✅ Smart notification timing
- ✅ Conversational AI assistant
- ✅ User feedback loop

**Example Coaching Scenarios:**

```python
# Scenario 1: Missed Dose
Event: dose.missed at 8:30am (30 min late)
AI Action:
  - Wait 15 minutes (give user time)
  - Generate: "Hey Kyle, noticed you haven't taken your Lisinopril yet. Everything okay? Tap to mark as taken."
  - If no response by 9am: "Friendly reminder - Lisinopril is still waiting 😊"

# Scenario 2: Pattern Detected
Event: pattern.detected (late_on_weekends)
AI Action:
  - Wait for good time (not during weekend)
  - Generate: "I noticed you tend to take your meds about 30 minutes later on weekends. Would you like me to adjust your weekend reminders to 8:30am instead of 8am?"
  - Options: [Yes, change it] [No, keep as is] [Snooze suggestion]

# Scenario 3: Low Quantity
Event: medication.quantity == 5 (5 doses left)
AI Action:
  - Calculate: 5 days until refill needed
  - Generate: "You have 5 days of Lisinopril left. Time to refill! Would you like me to remind you to call Dr. Smith's office?"
  - Options: [Yes, remind me tomorrow] [Already scheduled] [Dismiss]

# Scenario 4: Streak Milestone
Event: habit.streak == 7
AI Action:
  - Generate: "🎉 You've taken your Lisinopril on time for 7 days straight! Great job staying consistent!"
  - Encourage continued adherence

# Scenario 5: Improvement Trend
Event: adherence_rate increased from 0.75 to 0.90
AI Action:
  - Generate: "Your medication adherence has improved by 15% this month! Whatever you're doing is working - keep it up! 💪"
```

**API Changes:**
```python
# New endpoint
GET /ai_brain/coaching/messages
# Returns pending coaching messages for user

# New endpoint
POST /ai_brain/coaching/feedback
{
  "message_id": "abc123",
  "helpful": true,
  "action_taken": "snoozed_reminder"
}
# AI learns from feedback

# WebSocket for real-time notifications
ws://gateway:8000/ws/coaching
# Streams coaching messages as they're generated
```

---

## Timeline & Resources

### Estimated Timeline

| Phase | Duration | Start | End | Effort |
|-------|----------|-------|-----|--------|
| Phase 1: Meds → Reminders | 4 weeks | Week 1 | Week 4 | 80h |
| Phase 2: Reminders → Habits | 3 weeks | Week 5 | Week 7 | 60h |
| Phase 3: AI Monitoring | 4 weeks | Week 8 | Week 11 | 80h |
| Phase 4: Proactive Coaching | 5 weeks | Week 12 | Week 16 | 100h |
| **Total** | **16 weeks** | | | **320h** |

**Note:** Timeline assumes:
- Single developer working part-time (20h/week)
- Or contractor/agency full-time (40h/week = 8 weeks)
- Minimal scope creep
- No major technical blockers

### Resource Requirements

#### Development Resources
- **Developer:** Full-stack with Python/FastAPI + React/TypeScript experience
- **AI/ML Expertise:** Understanding of RAG, LLMs, pattern detection (can be learned)
- **DevOps:** Docker, service orchestration (existing setup sufficient)

#### Infrastructure
- **Current:** Local deployment sufficient for Phases 1-3
- **Phase 4:** Consider cloud deployment for:
  - SMS notifications (Twilio - ~$0.01/message)
  - Email notifications (SendGrid - free tier)
  - Better LLM (OpenAI API - ~$0.002/request or continue local)

#### Estimated Costs
- **Development:** 320h × $50-150/h = **$16,000 - $48,000**
- **Infrastructure:** $0 - $50/month (if using paid services)
- **Total:** **$16,000 - $48,000** for complete system

**Budget Options:**
1. **DIY (Kyle builds it):** $0 cash, 320h time investment
2. **Contractor:** $16k-25k (mid-tier developer)
3. **Agency:** $40k-50k (faster, higher quality)

---

## Technical Requirements

### Dependencies to Add

```toml
# shared/pyproject.toml additions
[tool.poetry.dependencies]
python = "^3.11"
# Existing...
httpx = "^0.27.0"  # For service-to-service HTTP calls
python-multipart = "^0.0.9"  # For file uploads
websockets = "^12.0"  # For real-time notifications
pydantic = "^2.0"  # Better data validation

# AI/ML enhancements
scikit-learn = "^1.4.0"  # Pattern detection
pandas = "^2.2.0"  # Data analysis for adherence trends
```

### Environment Variables

```bash
# .env additions

# Service URLs (for cross-service communication)
MEDS_URL=http://meds:9001
REMINDER_URL=http://reminder:9002
HABITS_URL=http://habits:9003
AI_BRAIN_URL=http://ai_brain:9004

# Event bus configuration
EVENT_BUS_ENABLED=true
EVENT_TIMEOUT=5.0

# AI Coaching configuration
COACHING_ENABLED=true
NOTIFICATION_CHANNELS=frontend,sms,email
TWILIO_ACCOUNT_SID=xxx  # Optional: SMS
TWILIO_AUTH_TOKEN=xxx
TWILIO_FROM_NUMBER=xxx
SENDGRID_API_KEY=xxx  # Optional: Email

# Adherence thresholds
MISSED_DOSE_GRACE_MINUTES=30
LOW_QUANTITY_THRESHOLD_DAYS=7
COACHING_FREQUENCY_HOURS=4  # Min time between coaching messages
```

### Database Migrations

Each phase requires schema updates:

```sql
-- Phase 1: Meds → Reminders
ALTER TABLE med ADD COLUMN reminder_ids TEXT;  -- JSON array
ALTER TABLE reminder ADD COLUMN med_id INTEGER;

-- Phase 2: Reminders → Habits
ALTER TABLE reminder ADD COLUMN habit_id INTEGER;
ALTER TABLE reminder ADD COLUMN confirmation_required BOOLEAN DEFAULT FALSE;
ALTER TABLE reminder ADD COLUMN confirmed_at TEXT;
ALTER TABLE reminder ADD COLUMN missed BOOLEAN DEFAULT FALSE;
ALTER TABLE habit ADD COLUMN med_id INTEGER;
ALTER TABLE habit ADD COLUMN reminder_id INTEGER;
ALTER TABLE habit ADD COLUMN streak INTEGER DEFAULT 0;
ALTER TABLE habit ADD COLUMN adherence_rate REAL;

-- Create new table
CREATE TABLE adherence_event (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  med_id INTEGER NOT NULL,
  reminder_id INTEGER NOT NULL,
  event_type TEXT NOT NULL,
  scheduled_time TEXT NOT NULL,
  actual_time TEXT,
  minutes_late INTEGER,
  created_at TEXT NOT NULL,
  metadata TEXT
);

-- Phase 3: AI Monitoring
-- Enhance memory table with structured fields
ALTER TABLE memory ADD COLUMN event_type TEXT;
ALTER TABLE memory ADD COLUMN med_id INTEGER;
ALTER TABLE memory ADD COLUMN pattern_confidence REAL;

-- Phase 4: Coaching
CREATE TABLE coaching_message (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT,
  med_id INTEGER,
  message_type TEXT,  -- "missed_dose", "pattern_detected", etc.
  message_text TEXT,
  generated_at TEXT,
  delivered_at TEXT,
  read_at TEXT,
  feedback TEXT,  -- "helpful", "not_helpful", "dismissed"
  action_taken TEXT
);
```

### Performance Considerations

1. **Database Indexing:**
   ```sql
   CREATE INDEX idx_adherence_med ON adherence_event(med_id);
   CREATE INDEX idx_adherence_time ON adherence_event(scheduled_time);
   CREATE INDEX idx_memory_event_type ON memory(event_type);
   ```

2. **Caching:**
   - Cache adherence calculations (recalculate daily)
   - Cache AI-generated insights (refresh every 6-12 hours)

3. **Async Processing:**
   - Event publishing should be async (don't block user requests)
   - Pattern detection runs as background job (nightly)
   - Coaching message generation queued

---

## API Changes & Extensions

### Medications Service

#### Enhanced Endpoints

```python
# POST /meds (enhanced)
# Now automatically creates reminders and habits
@app.post("/meds")
async def create_medication(med: Med):
    # Create medication
    med = save_to_db(med)

    # Parse schedule and create reminders
    reminders = await create_reminders_for_schedule(
        med_id=med.id,
        schedule=med.schedule
    )
    med.reminder_ids = [r.id for r in reminders]

    # Publish event
    await event_bus.publish("medication.added", {
        "med_id": med.id,
        "name": med.name,
        "schedule": med.schedule
    })

    return med

# New endpoints
GET /meds/{id}/reminders
GET /meds/{id}/adherence
GET /meds/{id}/insights  # AI-generated insights
POST /meds/{id}/refill   # Log refill, update quantity
```

### Reminder Service

```python
# New endpoints
POST /reminders/{id}/confirm  # User confirms dose taken
POST /reminders/{id}/snooze   # Existing, enhanced
GET /reminders/missed         # List all missed reminders
GET /reminders/upcoming       # Next 24h reminders

# Enhanced event publishing
@app.post("/reminders/{id}/confirm")
async def confirm_reminder(id: int, confirmed_at: str = None):
    reminder = get_reminder(id)
    reminder.confirmed_at = confirmed_at or now()

    # Calculate if late
    scheduled = parse_iso(reminder.when)
    actual = parse_iso(reminder.confirmed_at)
    minutes_late = (actual - scheduled).total_seconds() / 60

    # Complete linked habit
    if reminder.habit_id:
        await complete_habit(reminder.habit_id)

    # Log adherence event
    await log_adherence_event(
        med_id=reminder.med_id,
        reminder_id=id,
        event_type="taken",
        scheduled_time=reminder.when,
        actual_time=confirmed_at,
        minutes_late=minutes_late
    )

    # Publish event
    await event_bus.publish("dose.taken", {
        "med_id": reminder.med_id,
        "reminder_id": id,
        "minutes_late": minutes_late
    })

    return {"ok": True, "minutes_late": minutes_late}
```

### Habits Service

```python
# Enhanced endpoints
POST /habits/{id}/complete  # Now includes auto-completion metadata
GET /habits/{id}/streak     # Current and longest streak
GET /habits/medication/{med_id}  # Get habit for specific medication
```

### AI Brain Service

```python
# New endpoints
POST /ai_brain/events       # Receive events from other services
POST /ai_brain/analyze_adherence  # Analyze patterns
GET /ai_brain/coaching/messages   # Get pending coaching messages
POST /ai_brain/coaching/feedback  # User feedback on coaching
GET /ai_brain/patterns      # Detected behavioral patterns

# Enhanced query endpoint
POST /ai_brain/query
{
  "question": "How am I doing with my medications?",
  "context": {
    "include_adherence": true,
    "include_patterns": true
  }
}
# Response includes medication adherence summary
```

### Gateway Service

```python
# New WebSocket endpoint
@app.websocket("/ws/coaching")
async def coaching_websocket(websocket: WebSocket):
    await websocket.accept()
    # Subscribe to coaching messages
    # Stream messages to frontend in real-time

# New event bus proxy
@app.post("/events/publish")
async def publish_event(event: Event):
    # Allow services to publish events via gateway
    await event_bus.publish(event.type, event.data)
```

---

## Testing Strategy

### Unit Tests

Each phase requires comprehensive unit tests:

```python
# Phase 1 tests
def test_schedule_parser():
    """Test parsing various schedule formats"""
    assert parse_schedule("daily at 8am") == [{"hour": 8, "minute": 0, "recurrence": "daily"}]
    assert parse_schedule("twice daily at 8am and 8pm") == [
        {"hour": 8, "minute": 0, "recurrence": "daily"},
        {"hour": 20, "minute": 0, "recurrence": "daily"}
    ]

def test_create_reminders_for_medication():
    """Test automatic reminder creation"""
    med = create_medication(name="Test", schedule="daily at 8am")
    assert len(med.reminder_ids) == 1
    reminder = get_reminder(med.reminder_ids[0])
    assert reminder.med_id == med.id
    assert reminder.recurrence == "daily"
```

### Integration Tests

```python
# Phase 2 integration test
def test_medication_adherence_flow():
    """Test complete flow: add med → reminder fires → user confirms → habit logged"""

    # 1. Create medication
    med = create_medication(name="Lisinopril", schedule="daily at 8am")

    # 2. Verify reminder created
    assert len(med.reminder_ids) == 1
    reminder = get_reminder(med.reminder_ids[0])

    # 3. Verify habit created
    habit = get_habit_by_id(reminder.habit_id)
    assert habit.name == "Take Lisinopril"

    # 4. Simulate reminder firing
    fire_reminder(reminder.id)

    # 5. User confirms dose
    response = confirm_reminder(reminder.id)
    assert response["ok"] == True

    # 6. Verify habit completion
    completions = get_habit_completions(habit.id)
    assert len(completions) == 1

    # 7. Verify adherence event logged
    events = get_adherence_events(med_id=med.id)
    assert len(events) == 1
    assert events[0].event_type == "taken"
```

### End-to-End Tests

```python
# Phase 4 E2E test
def test_ai_coaching_missed_dose():
    """Test AI detects missed dose and sends coaching message"""

    # 1. Setup: medication with reminder
    med = create_medication(name="Test Med", schedule="daily at 8am")

    # 2. Simulate reminder fired but not confirmed
    travel_to_time("2025-12-27 08:00:00")
    fire_reminder(med.reminder_ids[0])

    # 3. Wait past grace period
    travel_to_time("2025-12-27 08:35:00")

    # 4. Check for coaching message
    messages = get_coaching_messages()
    assert len(messages) == 1
    assert messages[0].message_type == "missed_dose"
    assert "haven't taken" in messages[0].message_text.lower()
```

### Load Testing

```python
# Simulate high event volume
def test_event_bus_performance():
    """Ensure event bus can handle 100 events/sec"""
    events = []
    for i in range(1000):
        events.append({
            "type": "dose.taken",
            "data": {"med_id": i, "timestamp": now()}
        })

    start = time.time()
    for event in events:
        event_bus.publish(event["type"], event["data"])
    duration = time.time() - start

    assert duration < 10  # Should complete in under 10 seconds
```

### User Acceptance Testing

**Phase 4 UAT Checklist:**
- [ ] Kyle can add a medication and see reminders auto-created
- [ ] Reminder notifications appear on schedule
- [ ] "Mark as Taken" button works and updates adherence
- [ ] Missing a dose triggers coaching message within 30 min
- [ ] Coaching messages are helpful and not annoying
- [ ] AI insights accurately reflect behavior
- [ ] Pattern suggestions make sense
- [ ] Low quantity alerts work correctly
- [ ] Streak milestones are celebrated appropriately

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Service-to-service calls fail** | Medium | High | Implement retry logic, circuit breakers, graceful degradation |
| **Event bus becomes bottleneck** | Low | Medium | Start simple (HTTP), can upgrade to Redis/RabbitMQ if needed |
| **AI pattern detection inaccurate** | Medium | Medium | Start with simple rules, gradually add ML. User feedback loop. |
| **Database migrations fail** | Low | High | Test migrations on copy, backup before running, rollback plan |
| **LLM costs too high** | Low | Low | Use local models (already doing), cache responses |
| **Notification spam annoys user** | Medium | High | Conservative frequency limits, user preferences, learn from feedback |

### Product Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Feature creep** | High | High | Stick to phased roadmap, say no to scope additions |
| **User doesn't engage with coaching** | Medium | Medium | A/B test messages, make opt-in, improve relevance |
| **Complexity overwhelms user** | Low | Medium | Gradual rollout, good defaults, optional features |
| **Privacy concerns with AI monitoring** | Low | High | All data stays local, encrypted storage, transparency |

### Schedule Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Underestimated effort** | Medium | Medium | 20% buffer in timeline, prioritize MVP features |
| **Blocked by dependencies** | Low | Medium | Phases designed to be independent, can parallelize |
| **Developer unavailable** | Medium | High | Good documentation, modular design for handoff |

---

## Success Metrics

### Phase 1 Success Criteria
- ✅ 100% of new medications auto-create reminders
- ✅ Reminder-medication linking works bidirectionally
- ✅ Zero orphaned reminders after medication deletion
- ✅ Schedule parser handles 90%+ of common formats

### Phase 2 Success Criteria
- ✅ Reminder confirmation flow < 2 taps
- ✅ Habit completion logged automatically 100% of time
- ✅ Adherence calculation accuracy validated manually
- ✅ UI shows adherence stats within 1 second

### Phase 3 Success Criteria
- ✅ AI Brain receives 100% of adherence events
- ✅ Pattern detection accuracy > 80% (validated manually)
- ✅ Query response time < 2 seconds
- ✅ Insights are actionable and relevant

### Phase 4 Success Criteria
- ✅ Coaching messages delivered within 5 minutes of trigger
- ✅ User engagement rate > 30% (user interacts with message)
- ✅ Helpfulness rating > 70% (user marks as helpful)
- ✅ Adherence improvement: +10% after 30 days of coaching
- ✅ Zero false-positive notifications

### Overall System Success
- 📈 **Medication adherence rate > 90%** (primary goal)
- 😊 **User satisfaction > 4/5 stars**
- 🤖 **AI coaching perceived as helpful, not intrusive**
- 💊 **Refill alerts prevent running out of medications**
- 📊 **User gains insights into their health habits**

---

## Next Steps

### Before Starting Development

1. **Review & Approval**
   - [ ] Kyle reviews roadmap and approves vision
   - [ ] Confirm timeline and budget constraints
   - [ ] Prioritize phases (can Phase 4 be postponed?)

2. **Resource Planning**
   - [ ] Decide: DIY, contractor, or agency?
   - [ ] Allocate budget
   - [ ] Set start date

3. **Technical Preparation**
   - [ ] Backup current system and database
   - [ ] Create development branch
   - [ ] Set up test environment (copy of production)

4. **Phase 1 Kickoff**
   - [ ] Create GitHub issues for all Phase 1 tasks
   - [ ] Set up project board
   - [ ] Schedule weekly progress reviews
   - [ ] Start with schedule parser (least risky)

### Incremental Approach (Recommended)

Don't have to commit to all phases at once:

1. **Start with Phase 1** (4 weeks, $4k-12k)
   - Delivers immediate value (auto-reminder creation)
   - Validates architecture decisions
   - Can stop here if budget/time constrained

2. **Evaluate after Phase 1**
   - Is it working as expected?
   - Does Kyle find it useful?
   - Continue to Phase 2 or iterate?

3. **Progressive Enhancement**
   - Each phase adds value independently
   - Can take breaks between phases
   - Funding can be staggered

---

## Appendix A: Alternative Architectures

### Option 1: Monolithic (Not Recommended)
Merge all services into single application.
- **Pros:** Simpler deployment, no service-to-service calls
- **Cons:** Tight coupling, harder to scale, loses microservice benefits

### Option 2: Full Event Sourcing (Overkill)
Use event sourcing pattern with event store.
- **Pros:** Complete audit trail, time travel, replay events
- **Cons:** Much more complex, requires specialized infrastructure

### Option 3: Serverless (Future Consideration)
Deploy as AWS Lambda functions with EventBridge.
- **Pros:** Auto-scaling, pay-per-use, managed infrastructure
- **Cons:** Vendor lock-in, cold starts, costs at scale

**Recommendation:** Stick with current microservices + simple event bus. Can evolve later if needed.

---

## Appendix B: AI/ML Algorithms

### Pattern Detection Approaches

#### 1. Late-Taking Pattern
```python
def detect_late_pattern(events: List[AdherenceEvent]) -> Pattern:
    """Detect if user consistently takes dose late on certain days"""

    # Group by day of week
    by_dow = defaultdict(list)
    for event in events:
        if event.event_type == "taken":
            dow = datetime.fromisoformat(event.scheduled_time).weekday()
            by_dow[dow].append(event.minutes_late)

    # Check for patterns
    patterns = []
    for dow, lates in by_dow.items():
        avg_late = mean(lates)
        if avg_late > 15:  # Consistently >15 min late
            patterns.append({
                "type": "late_on_day",
                "day": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dow],
                "avg_minutes_late": avg_late,
                "confidence": min(len(lates) / 10, 1.0)  # More data = higher confidence
            })

    return patterns
```

#### 2. Adherence Trend
```python
def detect_adherence_trend(events: List[AdherenceEvent]) -> Trend:
    """Detect if adherence is improving or declining"""

    # Calculate adherence rate by week
    weekly_rates = []
    for week_start in week_boundaries(events):
        week_events = filter_by_week(events, week_start)
        taken = sum(1 for e in week_events if e.event_type == "taken")
        total = len(week_events)
        weekly_rates.append(taken / total if total > 0 else 0)

    # Linear regression to detect trend
    if len(weekly_rates) < 3:
        return None

    slope, _ = linear_regression(weekly_rates)

    if slope > 0.05:
        return {"trend": "improving", "rate": slope}
    elif slope < -0.05:
        return {"trend": "declining", "rate": slope}
    else:
        return {"trend": "stable"}
```

#### 3. Predictive Adherence
```python
def predict_adherence_risk(user_context: dict) -> float:
    """Predict likelihood user will miss next dose"""

    features = [
        user_context["time_of_day"],  # Evening doses more likely missed
        user_context["day_of_week"],  # Weekends less consistent
        user_context["recent_streak"],  # Long streak = momentum
        user_context["time_since_last_coaching"],
        user_context["recent_adherence_rate"]
    ]

    # Simple logistic regression (can upgrade to ML model)
    risk_score = logistic_function(features, learned_weights)

    return risk_score  # 0-1, higher = more likely to miss
```

---

## Appendix C: Coaching Message Templates

### Template Categories

#### 1. Missed Dose - Gentle Reminder
```
"Hey Kyle, noticed you haven't taken your {medication} yet. Everything okay?"

Options:
- [Mark as Taken]
- [Snooze 15 min]
- [I took it earlier]
```

#### 2. Pattern Detected - Suggestion
```
"I noticed you tend to take {medication} about {N} minutes late on {days}.

Would you like me to adjust your {days} reminders to {suggested_time} instead?"

Options:
- [Yes, change it]
- [No, keep as is]
- [Remind me later]
```

#### 3. Low Quantity - Refill Alert
```
"You have {N} days of {medication} left. Time to refill!

Would you like me to:
• Remind you to call {prescriber}
• Add refill to your calendar
• Dismiss (I already ordered it)"
```

#### 4. Streak Milestone - Encouragement
```
"🎉 You've taken {medication} on time for {N} days straight!

Your consistency is paying off. Keep up the great work!"
```

#### 5. Improvement Detected - Celebration
```
"Your adherence has improved by {percent}% this month!

Whatever you're doing is working. You should be proud! 💪"
```

#### 6. Adherence Decline - Support
```
"I noticed your {medication} adherence has dropped from {old}% to {new}% recently.

Life gets busy - no judgment! Would you like help getting back on track?

Options:
- [Yes, help me]
- [I'm aware, working on it]
- [Dismiss]"
```

---

## Appendix D: Privacy & Security Considerations

### Data Sensitivity

**Highly Sensitive:**
- Medication names, dosages, prescribers (PHI)
- Adherence events (health data)
- AI-generated health insights

**Moderately Sensitive:**
- Reminder times (behavioral data)
- Habit tracking (lifestyle data)

### Privacy-First Design

1. **Local-First Storage**
   - All data stays on Kyle's device/server
   - No cloud sync required
   - Air-gapped deployment option maintained

2. **Encryption at Rest**
   - Medication data encrypted (already using Fernet)
   - Adherence events encrypted
   - AI memories with sensitive data encrypted

3. **Encryption in Transit**
   - All service-to-service calls use HTTPS (in production)
   - WebSocket connections encrypted

4. **Minimal Data Retention**
   - Coaching messages auto-delete after 30 days
   - Adherence events aggregated monthly, details purged
   - AI patterns stored, individual events summarized

5. **User Control**
   - Export all data (GDPR-style)
   - Delete specific medications and all linked data
   - Opt-out of AI coaching entirely
   - Opt-out of specific pattern detection

### Security Enhancements

```python
# shared/privacy.py
from cryptography.fernet import Fernet
import os

class PrivacyManager:
    def __init__(self):
        self.key = os.getenv("ENCRYPTION_KEY").encode()
        self.cipher = Fernet(self.key)

    def encrypt_sensitive(self, data: dict) -> str:
        """Encrypt medication/health data"""
        import json
        plaintext = json.dumps(data).encode()
        return self.cipher.encrypt(plaintext).decode()

    def decrypt_sensitive(self, encrypted: str) -> dict:
        """Decrypt medication/health data"""
        import json
        plaintext = self.cipher.decrypt(encrypted.encode())
        return json.loads(plaintext)

    def anonymize_for_ai(self, med_name: str) -> str:
        """Replace actual med name with generic code for AI"""
        # Map medications to codes (Med-A, Med-B, etc.)
        # AI sees patterns without knowing specific meds
        return self.med_name_map.get(med_name, f"Med-{hash(med_name) % 100}")
```

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-27 | Claude (via Kyle) | Initial roadmap created |

---

## Conclusion

This roadmap transforms Kilo Guardian from a helpful set of tools into an intelligent health assistant that actively supports medication adherence through automation, monitoring, and personalized coaching.

**Key Takeaways:**

1. **Phased Approach:** Each phase delivers value independently. Can start small and expand.

2. **Realistic Timeline:** 16 weeks for complete system, but Phase 1 alone provides significant value.

3. **Privacy-First:** All data stays local, encrypted, under user control.

4. **AI as Assistant:** AI augments user's efforts, doesn't replace human judgment.

5. **Incremental Investment:** Can fund phase-by-phase based on results.

**When Kyle is ready to proceed:**
1. Review and prioritize phases
2. Allocate time or budget
3. Create GitHub project
4. Start with Phase 1
5. Iterate based on results

This system has the potential to significantly improve Kyle's medication adherence and overall health outcomes. The technology is proven, the architecture is sound, and the path forward is clear.

---

**Questions or feedback?** Update this document as the project evolves.

**Ready to start?** Begin with Phase 1, Task 1: Schedule Parser. 🚀
