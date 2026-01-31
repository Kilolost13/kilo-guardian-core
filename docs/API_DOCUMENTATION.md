# Kilo AI Memory Assistant - API Documentation

**Version:** 1.0.0
**Base URL:** `http://localhost:8000` (Gateway)
**API Style:** REST
**Authentication:** Admin key for sensitive endpoints
**Last Updated:** December 2025

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Core Services](#core-services)
4. [AI Brain API](#ai-brain-api)
5. [Medication API](#medication-api)
6. [Habit Tracking API](#habit-tracking-api)
7. [Financial API](#financial-api)
8. [Reminder API](#reminder-api)
9. [Advanced Features API](#advanced-features-api)
10. [Error Handling](#error-handling)
11. [Rate Limits](#rate-limits)
12. [Examples](#examples)

---

## Overview

The Kilo AI system exposes REST APIs across 12 microservices, orchestrated through an API Gateway. All services communicate internally via Docker network and are accessible externally through the gateway on port 8000.

### Service Architecture

```
┌─────────────────────────────────────────────────────┐
│                   API Gateway (8000)                 │
├─────────────────────────────────────────────────────┤
│  AI Brain  │  Meds  │  Habits  │  Finance │  Voice  │
│    9004    │  9001  │   9003   │   9005   │  9009   │
├─────────────────────────────────────────────────────┤
│  Reminder  │  Cam   │ ML Engine│ Library  │   USB   │
│    9002    │  9007  │   9008   │   9006   │  8006   │
└─────────────────────────────────────────────────────┘
```

### Common Response Format

```json
{
  "status": "success",
  "data": { ... },
  "message": "Optional message",
  "timestamp": "2025-12-25T12:00:00Z"
}
```

---

## Authentication

### Admin Key Authentication

Some endpoints require admin authentication via the `X-Admin-Key` header:

```http
X-Admin-Key: your-admin-key-here
```

**Setting Admin Key:**
Set via environment variable: `LIBRARY_ADMIN_KEY=your-secure-key`

### No User Authentication

Currently, the system assumes single-user deployment. Multi-user support planned for Phase 6.

---

## Core Services

### Health Check Endpoints

#### GET /status
Check system status and health.

**Request:**
```http
GET /status HTTP/1.1
Host: localhost:8000
```

**Response:**
```json
{
  "status": "healthy",
  "services": {
    "ai_brain": "running",
    "meds": "running",
    "habits": "running",
    "finance": "running",
    "voice": "running",
    "reminder": "running"
  },
  "uptime": 86400,
  "version": "1.0.0"
}
```

---

## AI Brain API

Base path: `/` (proxied through gateway to AI Brain service on port 9004)

### Chat & Conversation

#### POST /chat
Send a message to the AI assistant and receive a response.

**Request:**
```http
POST /chat HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "message": "What medications am I taking for high blood pressure?",
  "use_memory": true,
  "max_memories": 10
}
```

**Response:**
```json
{
  "response": "Based on your records, you are currently taking Lisinopril 10mg once daily for high blood pressure. You started this medication on November 15, 2025, prescribed by Dr. Smith.",
  "memories_used": 3,
  "confidence": 0.92,
  "sources": [
    {
      "id": 1234,
      "text": "Lisinopril 10mg prescribed by Dr. Smith",
      "created_at": "2025-11-15T09:30:00Z",
      "relevance": 0.95
    }
  ]
}
```

**Parameters:**
- `message` (string, required): User's question or statement
- `use_memory` (boolean, default: true): Whether to search memories for context
- `max_memories` (integer, default: 10): Maximum number of relevant memories to retrieve
- `temperature` (float, default: 0.7): LLM temperature (0.0-1.0)

---

#### POST /chat/voice
Voice-based chat interaction.

**Request:**
```http
POST /chat/voice HTTP/1.1
Host: localhost:8000
Content-Type: multipart/form-data

audio: <audio file WAV/MP3>
```

**Response:**
```json
{
  "transcription": "What medications am I taking?",
  "response": "You are taking Lisinopril 10mg for high blood pressure...",
  "audio_url": "/tts/response_12345.wav"
}
```

---

### Memory Management

#### POST /ingest/meds
Ingest medication data into memory.

**Request:**
```http
POST /ingest/meds HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "medication_name": "Lisinopril",
  "dosage": "10mg",
  "frequency": "Once daily",
  "prescribing_doctor": "Dr. Smith",
  "start_date": "2025-11-15",
  "notes": "For high blood pressure control"
}
```

**Response:**
```json
{
  "status": "success",
  "memory_id": 1234,
  "message": "Medication memory created"
}
```

---

#### POST /ingest/habit
Log a habit activity.

**Request:**
```http
POST /ingest/habit HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "event_type": "exercise",
  "duration_minutes": 30,
  "intensity": "moderate",
  "notes": "Morning walk around the neighborhood"
}
```

**Response:**
```json
{
  "status": "success",
  "memory_id": 1235,
  "streak_updated": true,
  "current_streak": 7
}
```

---

#### POST /ingest/habit_completion
Mark a habit as completed (for scheduled habits).

**Request:**
```http
POST /ingest/habit_completion HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "habit_id": 42,
  "completed_at": "2025-12-25T08:00:00Z",
  "notes": "Completed morning exercise"
}
```

**Response:**
```json
{
  "status": "success",
  "habit": {
    "id": 42,
    "name": "Morning Exercise",
    "streak": 8,
    "completion_rate": 0.87
  }
}
```

---

#### POST /ingest/finance
Track a financial transaction.

**Request:**
```http
POST /ingest/finance HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "amount": 45.99,
  "category": "medication",
  "description": "Monthly prescription refill",
  "transaction_date": "2025-12-25",
  "payment_method": "insurance_copay"
}
```

**Response:**
```json
{
  "status": "success",
  "memory_id": 1236,
  "running_balance": 245.50
}
```

---

#### POST /ingest/receipt
Upload and process a receipt image.

**Request:**
```http
POST /ingest/receipt HTTP/1.1
Host: localhost:8000
Content-Type: multipart/form-data

image: <receipt image file>
category: "medical"
```

**Response:**
```json
{
  "status": "success",
  "memory_id": 1237,
  "ocr_results": {
    "total_amount": 45.99,
    "vendor": "CVS Pharmacy",
    "date": "2025-12-25",
    "items_extracted": [
      "Lisinopril 10mg - $45.99"
    ]
  }
}
```

---

#### POST /ingest/cam
Store camera activity event.

**Request:**
```http
POST /ingest/cam HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "event_type": "person_detected",
  "timestamp": "2025-12-25T14:30:00Z",
  "confidence": 0.95,
  "metadata": {
    "location": "living_room",
    "activity": "sitting"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "memory_id": 1238
}
```

---

#### POST /ingest/goal
Create a new goal.

**Request:**
```http
POST /ingest/goal HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "goal_type": "habit_formation",
  "title": "Exercise 30 minutes daily",
  "target_value": 30,
  "duration_days": 30,
  "start_date": "2025-12-25"
}
```

**Response:**
```json
{
  "status": "success",
  "memory_id": 1239,
  "goal_id": 15
}
```

---

### Analytics & Insights

#### GET /analytics/habits
Get habit analytics and patterns.

**Request:**
```http
GET /analytics/habits?days=30 HTTP/1.1
Host: localhost:8000
```

**Response:**
```json
{
  "period": "30_days",
  "habits": [
    {
      "habit_type": "exercise",
      "total_completions": 25,
      "completion_rate": 0.83,
      "average_duration": 32,
      "streak": 8,
      "trend": "improving"
    }
  ],
  "insights": [
    "You're most consistent with morning exercise",
    "Consider setting a reminder for weekend workouts"
  ]
}
```

**Parameters:**
- `days` (integer, default: 30): Number of days to analyze
- `habit_type` (string, optional): Filter by specific habit type

---

#### GET /feedback/habits
Get personalized habit feedback and recommendations.

**Request:**
```http
GET /feedback/habits HTTP/1.1
Host: localhost:8000
```

**Response:**
```json
{
  "overall_score": 8.5,
  "feedback": [
    {
      "habit": "morning_exercise",
      "status": "excellent",
      "message": "Great 8-day streak! Keep it up!",
      "suggestions": [
        "Try increasing duration by 5 minutes",
        "Add variety with different exercise types"
      ]
    },
    {
      "habit": "evening_meditation",
      "status": "needs_improvement",
      "message": "Only 40% completion this week",
      "suggestions": [
        "Set a consistent time for meditation",
        "Try a shorter 5-minute session to build consistency"
      ]
    }
  ]
}
```

---

#### POST /analyze/prescription
Analyze a prescription image with OCR.

**Request:**
```http
POST /analyze/prescription HTTP/1.1
Host: localhost:8000
Content-Type: multipart/form-data

image: <prescription image file>
```

**Response:**
```json
{
  "status": "success",
  "extracted_data": {
    "medication_name": "Lisinopril",
    "dosage": "10mg",
    "frequency": "Once daily",
    "quantity": "30 tablets",
    "refills": 3,
    "prescribing_doctor": "Dr. Jane Smith",
    "pharmacy": "CVS Pharmacy #1234",
    "rx_number": "RX123456",
    "date_prescribed": "2025-12-20"
  },
  "confidence": 0.89,
  "raw_ocr_text": "Full extracted text..."
}
```

---

### Voice Interface

#### POST /voice/activate
Activate voice listening mode.

**Request:**
```http
POST /voice/activate HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "duration_seconds": 10,
  "wake_word": "hey kilo"
}
```

**Response:**
```json
{
  "status": "listening",
  "session_id": "voice_session_12345",
  "timeout": 10
}
```

---

#### POST /voice/speak
Convert text to speech.

**Request:**
```http
POST /voice/speak HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "text": "Your medication reminder: Take Lisinopril now.",
  "voice": "female",
  "speed": 1.0
}
```

**Response:**
```json
{
  "status": "success",
  "audio_url": "/tts/message_12345.wav",
  "duration_seconds": 5.2
}
```

---

#### GET /tts/{filename}
Download generated TTS audio file.

**Request:**
```http
GET /tts/message_12345.wav HTTP/1.1
Host: localhost:8000
```

**Response:**
Binary WAV audio file.

---

## Advanced Features API (Phase 3 & 4)

### Scalability Features

#### GET /api/v1/scalability/status
Get status of scalability features (async processing, partitioning, resource management).

**Request:**
```http
GET /api/v1/scalability/status HTTP/1.1
Host: localhost:8000
```

**Response:**
```json
{
  "async_processing": {
    "active": true,
    "queue_size": 5,
    "tasks_processed": 1234,
    "avg_processing_time": 0.45
  },
  "data_partitioning": {
    "partitions": 12,
    "total_size_mb": 450.5,
    "partition_details": {
      "time_2025-12": {
        "file_count": 1500,
        "total_size_mb": 45.2,
        "avg_file_size_kb": 30.8
      }
    }
  },
  "resource_management": {
    "current_batch_size": 50,
    "should_throttle": false
  }
}
```

---

#### POST /api/v1/async/embeddings
Submit text for asynchronous embedding generation.

**Request:**
```http
POST /api/v1/async/embeddings HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "texts": [
    "Morning walk completed - 30 minutes",
    "Blood pressure: 120/80 mmHg",
    "Took Lisinopril at 8 AM"
  ],
  "priority": 1
}
```

**Response:**
```json
{
  "task_id": "embed_task_12345",
  "status": "submitted",
  "estimated_completion": "30-60 seconds"
}
```

**Priority Levels:**
- 0: Highest priority
- 1: High priority
- 2: Normal priority
- 3: Low priority

---

#### POST /api/v1/async/indexing
Index memories asynchronously for faster search.

**Request:**
```http
POST /api/v1/async/indexing HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "memory_ids": [1234, 1235, 1236, 1237],
  "priority": 2
}
```

**Response:**
```json
{
  "task_id": "index_task_67890",
  "status": "submitted",
  "memories_to_index": 4
}
```

---

#### POST /api/v1/async/consolidation
Consolidate old memories to reduce storage and improve performance.

**Request:**
```http
POST /api/v1/async/consolidation HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "partition_key": "time_2024-01",
  "days_old": 365
}
```

**Response:**
```json
{
  "task_id": "consolidate_task_11111",
  "status": "submitted",
  "partition": "time_2024-01"
}
```

---

### Predictive Analytics

#### GET /api/v1/predictive/insights
Get predictive insights and proactive recommendations.

**Request:**
```http
GET /api/v1/predictive/insights HTTP/1.1
Host: localhost:8000
```

**Response:**
```json
{
  "insights": [
    {
      "type": "habit_reminder",
      "priority": "high",
      "message": "Based on your patterns, now would be a great time for your evening walk",
      "confidence": 0.8,
      "recommended_action": "log_habit"
    },
    {
      "type": "health_check",
      "priority": "medium",
      "message": "You've been sitting for 2 hours. A quick stretch would be beneficial.",
      "confidence": 0.7,
      "recommended_action": "activity_reminder"
    },
    {
      "type": "medication_reminder",
      "priority": "high",
      "message": "Time for your medication - staying consistent is important!",
      "confidence": 0.9,
      "recommended_action": "take_medication"
    }
  ],
  "generated_at": "2025-12-25T14:30:00Z",
  "model_status": "trained"
}
```

---

### Knowledge Graph

#### GET /api/v1/knowledge/graph/stats
Get knowledge graph statistics.

**Request:**
```http
GET /api/v1/knowledge/graph/stats HTTP/1.1
Host: localhost:8000
```

**Response:**
```json
{
  "graph_stats": {
    "total_entities": 342,
    "total_relationships": 567,
    "entity_breakdown": {
      "person": 5,
      "habit": 45,
      "medication": 12,
      "location": 8,
      "activity": 180,
      "concept": 85,
      "time": 7
    },
    "relationship_breakdown": {
      "causes": 34,
      "prevents": 12,
      "improves": 89,
      "worsens": 15,
      "related_to": 234,
      "occurs_at": 120,
      "belongs_to": 45,
      "similar_to": 18
    }
  },
  "entity_types": {
    "person": "People and users",
    "habit": "Habits and routines",
    "medication": "Medications and health"
  },
  "relationship_types": {
    "causes": "Causal relationship",
    "prevents": "Preventive relationship",
    "improves": "Improvement relationship"
  }
}
```

---

#### POST /api/v1/knowledge/graph/build
Build knowledge graph from existing memory data.

**Request:**
```http
POST /api/v1/knowledge/graph/build HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "limit": 1000
}
```

**Response:**
```json
{
  "status": "completed",
  "memories_processed": 1000,
  "entities_added": 234,
  "relationships_added": 456,
  "graph_stats": {
    "total_entities": 576,
    "total_relationships": 1023
  }
}
```

---

#### GET /api/v1/knowledge/reason/{entity_id}
Get reasoning insights about a specific entity.

**Request:**
```http
GET /api/v1/knowledge/reason/medication_lisinopril HTTP/1.1
Host: localhost:8000
```

**Response:**
```json
{
  "entity_id": "medication_lisinopril",
  "impacts": [
    {
      "impact_type": "improves",
      "target_entity": "cardiovascular_health",
      "strength": 0.85,
      "evidence_count": 12
    },
    {
      "impact_type": "prevents",
      "target_entity": "hypertension_complications",
      "strength": 0.78,
      "evidence_count": 8
    }
  ],
  "suggested_actions": [
    {
      "action": "monitor_blood_pressure",
      "reason": "Track medication effectiveness",
      "confidence": 0.9,
      "expected_impact": "better_health_outcomes"
    }
  ]
}
```

---

### Conversation Management

#### POST /api/v1/conversation/start
Start a new conversation session.

**Request:**
```http
POST /api/v1/conversation/start HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "user_id": "user_123",
  "initial_context": {
    "topic": "medication_management",
    "goal": "review_current_medications"
  }
}
```

**Response:**
```json
{
  "conversation_id": "conv_abc123",
  "status": "active",
  "created_at": "2025-12-25T14:30:00Z"
}
```

---

#### POST /api/v1/conversation/{conversation_id}/turn
Add a conversation turn.

**Request:**
```http
POST /api/v1/conversation/conv_abc123/turn HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "user_message": "What medications am I currently taking?",
  "ai_response": "You are currently taking Lisinopril 10mg for high blood pressure..."
}
```

**Response:**
```json
{
  "status": "success",
  "turn_number": 1,
  "context_updated": true
}
```

---

#### POST /api/v1/conversation/{conversation_id}/goals
Set goals for a conversation.

**Request:**
```http
POST /api/v1/conversation/conv_abc123/goals HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "goals": [
    {
      "type": "medication_review",
      "description": "Review all current medications",
      "priority": "high"
    },
    {
      "type": "adherence_check",
      "description": "Check medication adherence",
      "priority": "medium"
    }
  ]
}
```

**Response:**
```json
{
  "status": "success",
  "goals_set": 2
}
```

---

#### GET /api/v1/conversation/{conversation_id}/context
Get current conversation context.

**Request:**
```http
GET /api/v1/conversation/conv_abc123/context HTTP/1.1
Host: localhost:8000
```

**Response:**
```json
{
  "conversation_id": "conv_abc123",
  "user_id": "user_123",
  "turns": [
    {
      "turn_number": 1,
      "user_message": "What medications am I taking?",
      "ai_response": "You are taking Lisinopril...",
      "timestamp": "2025-12-25T14:30:00Z"
    }
  ],
  "goals": [
    {
      "type": "medication_review",
      "status": "in_progress",
      "progress": 0.5
    }
  ],
  "topics_discussed": ["medications", "blood_pressure"],
  "total_turns": 1
}
```

---

#### GET /api/v1/conversation/{conversation_id}/suggestions
Get suggested next actions for the conversation.

**Request:**
```http
GET /api/v1/conversation/conv_abc123/suggestions HTTP/1.1
Host: localhost:8000
```

**Response:**
```json
{
  "suggestions": [
    {
      "action": "review_adherence",
      "description": "Check how consistently you've been taking medications",
      "priority": "high",
      "confidence": 0.85
    },
    {
      "action": "set_reminder",
      "description": "Set a reminder for next medication time",
      "priority": "medium",
      "confidence": 0.75
    }
  ]
}
```

---

### Goal Management

#### GET /api/v1/user/{user_id}/insights
Get personalized insights for a user.

**Request:**
```http
GET /api/v1/user/user_123/insights HTTP/1.1
Host: localhost:8000
```

**Response:**
```json
{
  "user_id": "user_123",
  "insights": [
    {
      "type": "habit_pattern",
      "message": "You exercise most consistently between 7-9 AM",
      "confidence": 0.88
    },
    {
      "type": "medication_adherence",
      "message": "Your medication adherence is 95% this month - excellent!",
      "confidence": 0.92
    }
  ],
  "generated_at": "2025-12-25T14:30:00Z"
}
```

---

#### POST /api/v1/goals/suggest
Get goal suggestions based on user data.

**Request:**
```http
POST /api/v1/goals/suggest HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "user_id": "user_123",
  "focus_area": "health_improvement"
}
```

**Response:**
```json
{
  "suggestions": [
    {
      "goal_type": "habit_formation",
      "title": "Exercise 30 minutes daily",
      "description": "Based on your activity patterns, this is achievable",
      "estimated_difficulty": "medium",
      "expected_impact": "high"
    },
    {
      "goal_type": "medication_management",
      "title": "100% medication adherence",
      "description": "You're at 95% - push for perfect adherence",
      "estimated_difficulty": "easy",
      "expected_impact": "high"
    }
  ]
}
```

---

#### GET /api/v1/goals/templates
Get available goal templates.

**Request:**
```http
GET /api/v1/goals/templates HTTP/1.1
Host: localhost:8000
```

**Response:**
```json
{
  "templates": [
    {
      "id": "habit_formation",
      "name": "Form a New Habit",
      "description": "Build consistency with a new healthy habit",
      "default_duration_days": 30,
      "success_criteria": "Complete habit 80% of days"
    },
    {
      "id": "medication_management",
      "name": "Medication Adherence",
      "description": "Take medications consistently as prescribed",
      "default_duration_days": 90,
      "success_criteria": "100% adherence"
    },
    {
      "id": "health_improvement",
      "name": "Health Improvement",
      "description": "Improve a specific health metric",
      "default_duration_days": 60,
      "success_criteria": "Measurable improvement in target metric"
    }
  ]
}
```

---

## Medication API

Base path: `/meds` (proxied through gateway to Meds service on port 9001)

### Medication Management

#### GET /meds
List all medications.

**Request:**
```http
GET /meds HTTP/1.1
Host: localhost:8000
```

**Response:**
```json
{
  "medications": [
    {
      "id": 1,
      "name": "Lisinopril",
      "dosage": "10mg",
      "frequency": "Once daily",
      "active": true,
      "start_date": "2025-11-15",
      "prescribing_doctor": "Dr. Smith"
    }
  ]
}
```

---

#### POST /meds
Create a new medication entry.

**Request:**
```http
POST /meds HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "name": "Metformin",
  "dosage": "500mg",
  "frequency": "Twice daily",
  "prescribing_doctor": "Dr. Johnson",
  "start_date": "2025-12-25",
  "instructions": "Take with meals"
}
```

**Response:**
```json
{
  "status": "success",
  "medication_id": 2,
  "message": "Medication added successfully"
}
```

---

#### PUT /meds/{medication_id}
Update medication details.

**Request:**
```http
PUT /meds/2 HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "dosage": "1000mg",
  "frequency": "Twice daily with meals"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Medication updated"
}
```

---

#### DELETE /meds/{medication_id}
Mark medication as inactive (soft delete).

**Request:**
```http
DELETE /meds/2 HTTP/1.1
Host: localhost:8000
```

**Response:**
```json
{
  "status": "success",
  "message": "Medication deactivated"
}
```

---

## Habit Tracking API

Base path: `/habits` (proxied through gateway to Habits service on port 9003)

### Habit Management

#### GET /habits
List all tracked habits.

**Request:**
```http
GET /habits HTTP/1.1
Host: localhost:8000
```

**Response:**
```json
{
  "habits": [
    {
      "id": 1,
      "name": "Morning Exercise",
      "type": "exercise",
      "frequency": "daily",
      "target_duration": 30,
      "current_streak": 8,
      "completion_rate": 0.87,
      "active": true
    }
  ]
}
```

---

#### POST /habits
Create a new habit to track.

**Request:**
```http
POST /habits HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "name": "Evening Meditation",
  "type": "mental_health",
  "frequency": "daily",
  "target_duration": 10,
  "reminder_time": "20:00"
}
```

**Response:**
```json
{
  "status": "success",
  "habit_id": 2,
  "message": "Habit created"
}
```

---

#### POST /habits/{habit_id}/complete
Mark habit as completed for today.

**Request:**
```http
POST /habits/2/complete HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "completed_at": "2025-12-25T20:15:00Z",
  "duration_minutes": 12,
  "notes": "Focused on breathing exercises"
}
```

**Response:**
```json
{
  "status": "success",
  "streak": 1,
  "message": "Habit logged successfully"
}
```

---

## Financial API

Base path: `/finance` (proxied through gateway to Financial service on port 9005)

### Transaction Management

#### GET /finance/transactions
List financial transactions.

**Request:**
```http
GET /finance/transactions?category=medication&limit=10 HTTP/1.1
Host: localhost:8000
```

**Response:**
```json
{
  "transactions": [
    {
      "id": 1,
      "amount": 45.99,
      "category": "medication",
      "description": "Lisinopril refill",
      "date": "2025-12-25",
      "payment_method": "insurance_copay"
    }
  ],
  "total": 1,
  "page": 1
}
```

---

#### POST /finance/transactions
Add a new transaction.

**Request:**
```http
POST /finance/transactions HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "amount": 89.50,
  "category": "medical_appointment",
  "description": "Doctor visit copay",
  "date": "2025-12-25",
  "payment_method": "credit_card"
}
```

**Response:**
```json
{
  "status": "success",
  "transaction_id": 2,
  "running_balance": 135.49
}
```

---

#### GET /finance/budget
Get budget overview.

**Request:**
```http
GET /finance/budget?month=2025-12 HTTP/1.1
Host: localhost:8000
```

**Response:**
```json
{
  "month": "2025-12",
  "categories": {
    "medication": {
      "budget": 200,
      "spent": 135.49,
      "remaining": 64.51,
      "percentage_used": 0.68
    },
    "medical_appointments": {
      "budget": 500,
      "spent": 89.50,
      "remaining": 410.50,
      "percentage_used": 0.18
    }
  },
  "total_budget": 1500,
  "total_spent": 224.99,
  "total_remaining": 1275.01
}
```

---

## Reminder API

Base path: `/reminders` (proxied through gateway to Reminder service on port 9002)

### Reminder Management

#### GET /reminders
List all reminders.

**Request:**
```http
GET /reminders?status=active HTTP/1.1
Host: localhost:8000
```

**Response:**
```json
{
  "reminders": [
    {
      "id": 1,
      "title": "Take Lisinopril",
      "type": "medication",
      "scheduled_time": "08:00",
      "recurrence": "daily",
      "status": "active",
      "next_occurrence": "2025-12-26T08:00:00Z"
    }
  ]
}
```

---

#### POST /reminders
Create a new reminder.

**Request:**
```http
POST /reminders HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "title": "Blood pressure check",
  "type": "health_check",
  "scheduled_time": "09:00",
  "recurrence": "weekly",
  "recurrence_days": ["Monday", "Thursday"]
}
```

**Response:**
```json
{
  "status": "success",
  "reminder_id": 2,
  "next_occurrence": "2025-12-29T09:00:00Z"
}
```

---

#### POST /reminder/ack
Acknowledge a reminder as completed.

**Request:**
```http
POST /reminder/ack HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "reminder_id": 1,
  "acknowledged_at": "2025-12-25T08:05:00Z",
  "action_taken": "completed"
}
```

**Response:**
```json
{
  "status": "success",
  "next_occurrence": "2025-12-26T08:00:00Z"
}
```

---

## Error Handling

### Standard Error Response

```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid medication dosage format",
    "details": {
      "field": "dosage",
      "expected": "e.g., 10mg, 500mg"
    }
  },
  "timestamp": "2025-12-25T14:30:00Z"
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Invalid request parameters |
| `AUTHENTICATION_ERROR` | 401 | Missing or invalid admin key |
| `NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | Resource already exists |
| `INTERNAL_ERROR` | 500 | Server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

---

## Rate Limits

Currently, no rate limiting is enforced for local deployment. For multi-user deployments, consider implementing rate limiting at the gateway level.

---

## Code Examples

### Python

```python
import requests

# Chat with AI
response = requests.post(
    "http://localhost:8000/chat",
    json={
        "message": "What medications am I taking?",
        "use_memory": True
    }
)
print(response.json()["response"])

# Add medication
requests.post(
    "http://localhost:8000/ingest/meds",
    json={
        "medication_name": "Lisinopril",
        "dosage": "10mg",
        "frequency": "Once daily"
    }
)

# Get predictive insights
insights = requests.get(
    "http://localhost:8000/api/v1/predictive/insights"
).json()
for insight in insights["insights"]:
    print(f"{insight['type']}: {insight['message']}")
```

### JavaScript

```javascript
// Chat with AI
fetch('http://localhost:8000/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: 'What medications am I taking?',
    use_memory: true
  })
})
.then(res => res.json())
.then(data => console.log(data.response));

// Get knowledge graph stats
fetch('http://localhost:8000/api/v1/knowledge/graph/stats')
  .then(res => res.json())
  .then(stats => console.log(stats.graph_stats));
```

### cURL

```bash
# Chat
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What medications am I taking?"}'

# Add habit completion
curl -X POST http://localhost:8000/ingest/habit_completion \
  -H "Content-Type: application/json" \
  -d '{"habit_id": 1, "completed_at": "2025-12-25T08:00:00Z"}'

# Get predictive insights
curl http://localhost:8000/api/v1/predictive/insights
```

---

## WebSocket Support (Planned)

Future versions will support WebSocket connections for:
- Real-time reminder notifications
- Live voice conversation streaming
- Camera activity alerts

---

## Versioning

API version is included in URL path for advanced features: `/api/v1/...`

Breaking changes will increment the version number: `/api/v2/...`

---

## Support

For API issues or questions:
- **Documentation:** See `docs/` directory
- **Issues:** GitHub Issues
- **Email:** support@kilo-ai.com (planned)

---

**Last Updated:** December 2025
**API Version:** 1.0.0
**Maintained by:** Kilo AI Team
