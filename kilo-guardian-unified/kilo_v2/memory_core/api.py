"""
Unified API endpoints for Memory Core: reminders, medications, habits, and memory events.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter()

# Import memory core components
from .db import get_memory_db

# Global reminder engine instance (initialized in server_core.py)
_reminder_engine = None


def set_reminder_engine(engine):
    """Set the global reminder engine instance."""
    global _reminder_engine
    _reminder_engine = engine


def get_reminder_engine():
    """Get the global reminder engine instance."""
    if not _reminder_engine:
        raise HTTPException(status_code=500, detail="Reminder engine not initialized")
    return _reminder_engine


# ===== Request/Response Models =====


class ReminderCreate(BaseModel):
    text: str
    scheduled_time: str  # ISO format datetime
    recurring: Optional[str] = None
    priority: str = "normal"
    category: Optional[str] = None


class ReminderResponse(BaseModel):
    id: int
    text: str
    scheduled_time: str
    recurring: Optional[str]
    acknowledged: bool
    snoozed_until: Optional[str]
    priority: str
    category: Optional[str]
    created_at: str
    updated_at: str


class MedicationCreate(BaseModel):
    name: str
    dosage: str
    frequency: str
    times: str  # Comma-separated times like "08:00,14:00,20:00"
    notes: Optional[str] = None


class MedicationResponse(BaseModel):
    id: int
    name: str
    dosage: str
    frequency: str
    times: str
    notes: Optional[str]
    active: bool
    created_at: str
    updated_at: str


class MedicationLogCreate(BaseModel):
    medication_id: int
    scheduled_time: str
    taken_time: Optional[str] = None
    notes: Optional[str] = None


class MemoryEventCreate(BaseModel):
    event_text: str
    event_time: Optional[str] = None
    event_type: Optional[str] = None


class HabitCreate(BaseModel):
    name: str
    target_frequency: str  # "daily", "twice daily", "weekly", etc.
    description: Optional[str] = None


class HabitResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    target_frequency: str
    streak: int
    last_completed: Optional[str]
    active: bool
    created_at: str
    updated_at: str


# ===== Reminder Endpoints =====


@router.post("/memory/reminders", response_model=dict)
def create_reminder(reminder: ReminderCreate):
    """Create a new reminder."""
    try:
        db = get_memory_db()
        engine = get_reminder_engine()

        # Add to database
        reminder_id = db.add_reminder(
            text=reminder.text,
            scheduled_time=reminder.scheduled_time,
            recurring=reminder.recurring,
            priority=reminder.priority,
            category=reminder.category,
        )

        # Schedule with reminder engine
        engine.schedule_reminder(reminder_id)

        return {"status": "ok", "reminder_id": reminder_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/reminders", response_model=List[dict])
def list_reminders(include_acknowledged: bool = Query(False)):
    """Get all reminders."""
    try:
        db = get_memory_db()
        reminders = db.get_reminders(include_acknowledged=include_acknowledged)
        return reminders
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/reminders/{reminder_id}", response_model=dict)
def get_reminder(reminder_id: int):
    """Get a specific reminder by ID."""
    try:
        db = get_memory_db()
        reminder = db.get_reminder(reminder_id)
        if not reminder:
            raise HTTPException(status_code=404, detail="Reminder not found")
        return reminder
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/reminders/{reminder_id}/acknowledge", response_model=dict)
def acknowledge_reminder(reminder_id: int):
    """Acknowledge a reminder (mark as completed)."""
    try:
        engine = get_reminder_engine()
        success = engine.acknowledge_reminder(reminder_id)
        if not success:
            raise HTTPException(status_code=404, detail="Reminder not found")
        return {"status": "ok", "acknowledged": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/reminders/{reminder_id}/snooze", response_model=dict)
def snooze_reminder(reminder_id: int, minutes: int = Query(10)):
    """Snooze a reminder for specified minutes."""
    try:
        engine = get_reminder_engine()
        success = engine.snooze_reminder(reminder_id, minutes=minutes)
        if not success:
            raise HTTPException(status_code=404, detail="Reminder not found")
        return {"status": "ok", "snoozed_minutes": minutes}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/memory/reminders/{reminder_id}", response_model=dict)
def delete_reminder(reminder_id: int):
    """Delete a reminder."""
    try:
        db = get_memory_db()
        success = db.delete_reminder(reminder_id)
        if not success:
            raise HTTPException(status_code=404, detail="Reminder not found")
        return {"status": "ok", "deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Medication Endpoints =====


@router.post("/memory/medications", response_model=dict)
def create_medication(medication: MedicationCreate):
    """Add a new medication."""
    try:
        db = get_memory_db()
        med_id = db.add_medication(
            name=medication.name,
            dosage=medication.dosage,
            frequency=medication.frequency,
            times=medication.times,
            notes=medication.notes,
        )
        return {"status": "ok", "medication_id": med_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/medications", response_model=List[dict])
def list_medications(active_only: bool = Query(True)):
    """Get all medications."""
    try:
        db = get_memory_db()
        medications = db.get_medications(active_only=active_only)
        return medications
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/medications/log", response_model=dict)
def log_medication_taken(log_entry: MedicationLogCreate):
    """Log that a medication was taken."""
    try:
        db = get_memory_db()
        log_id = db.log_medication_taken(
            medication_id=log_entry.medication_id,
            scheduled_time=log_entry.scheduled_time,
            taken_time=log_entry.taken_time,
            notes=log_entry.notes,
        )
        return {"status": "ok", "log_id": log_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/medications/logs", response_model=List[dict])
def get_medication_logs(
    medication_id: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    """Get medication logs, optionally filtered by medication ID and date range."""
    try:
        db = get_memory_db()
        logs = db.get_medication_logs(
            medication_id=medication_id, start_date=start_date, end_date=end_date
        )
        return logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/medications/logs/today", response_model=List[dict])
def get_medication_logs_today(medication_id: Optional[int] = Query(None)):
    """Get medication logs for today, optionally filtered by medication ID."""
    try:
        db = get_memory_db()
        logs = db.get_medication_logs_today(medication_id=medication_id)
        return logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/medications/{medication_id}/logs/today", response_model=List[dict])
def get_medication_logs_today_by_id(medication_id: int):
    """Get today's logs for a specific medication."""
    try:
        db = get_memory_db()
        logs = db.get_medication_logs_today(medication_id=medication_id)
        return logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Memory Event Endpoints =====


@router.post("/memory/events", response_model=dict)
def create_memory_event(event: MemoryEventCreate):
    """Add a memory event (for 'what did I do today' queries)."""
    try:
        db = get_memory_db()
        event_id = db.add_memory_event(
            event_text=event.event_text,
            event_time=event.event_time,
            event_type=event.event_type,
        )
        return {"status": "ok", "event_id": event_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/events", response_model=List[dict])
def list_memory_events(
    start_time: Optional[str] = Query(None), end_time: Optional[str] = Query(None)
):
    """Get memory events within a time range."""
    try:
        db = get_memory_db()
        events = db.get_memory_events(start_time=start_time, end_time=end_time)
        return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/search", response_model=List[dict])
def semantic_search_events(
    query: str = Query(..., description="Natural language search query"),
    k: int = Query(5, ge=1, le=50, description="Number of results to return"),
    start_time: Optional[str] = Query(
        None, description="Filter by start time (ISO format)"
    ),
    end_time: Optional[str] = Query(
        None, description="Filter by end time (ISO format)"
    ),
):
    """
    Semantic search for memory events using natural language queries.

    Examples:
    - "when did I go to the grocery store?"
    - "what did I do last Tuesday?"
    - "meetings about the project"

    Uses FAISS vector similarity search for intelligent matching.
    Falls back to text search if FAISS unavailable.
    """
    try:
        db = get_memory_db()
        results = db.semantic_search(
            query=query, k=k, start_time=start_time, end_time=end_time
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Habit Endpoints =====


@router.post("/memory/habits", response_model=dict)
def create_habit(habit: HabitCreate):
    """Add a new habit to track."""
    try:
        db = get_memory_db()
        habit_id = db.add_habit(
            name=habit.name,
            target_frequency=habit.target_frequency,
            description=habit.description,
        )
        return {"status": "ok", "habit_id": habit_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/habits", response_model=List[dict])
def list_habits(active_only: bool = Query(True)):
    """Get all habits."""
    try:
        db = get_memory_db()
        habits = db.get_habits(active_only=active_only)
        return habits
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/habits/{habit_id}/complete", response_model=dict)
def complete_habit(habit_id: int):
    """Mark a habit as completed for today."""
    try:
        engine = get_reminder_engine()
        success = engine.track_habit(habit_id)
        if not success:
            raise HTTPException(status_code=404, detail="Habit not found")
        return {"status": "ok", "completed": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Alert Endpoints =====


@router.get("/memory/alerts", response_model=List[dict])
def get_pending_alerts():
    """Get all pending alerts for the user."""
    try:
        engine = get_reminder_engine()
        alerts = engine.get_pending_alerts()
        return alerts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/alerts/{alert_id}/clear", response_model=dict)
def clear_alert(alert_id: str):
    """Clear a specific alert."""
    try:
        engine = get_reminder_engine()
        # Handle both int IDs and string IDs like "med_1"
        try:
            alert_id_parsed = int(alert_id)
        except ValueError:
            alert_id_parsed = alert_id

        engine.clear_alert(alert_id_parsed)
        return {"status": "ok", "cleared": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Nudge Endpoint =====


@router.get("/memory/nudge", response_model=List[dict])
def get_nudge_items():
    """Get all items needing user attention (overdue reminders, pending habits, etc.)."""
    try:
        engine = get_reminder_engine()
        nudge_items = engine.nudge()
        return nudge_items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Camera Placeholder (for Phase 4) =====


@router.get("/memory/camera/snapshot")
def camera_snapshot():
    """Capture and return camera snapshot (placeholder for Phase 4)."""
    # TODO Phase 4: Implement camera integration
    return {
        "status": "not_implemented",
        "message": "Camera integration pending Phase 4",
    }


# ===== Pattern Recognition Endpoints =====


@router.post("/memory/patterns/learn", response_model=dict)
def learn_patterns(time_window_days: int = Query(default=30, ge=1, le=365)):
    """
    Learn behavioral patterns from memory events.

    Args:
        time_window_days: Number of days of history to analyze (default: 30)

    Returns:
        Pattern learning statistics
    """
    try:
        from datetime import datetime, timedelta

        from kilo_v2.pattern_recognizer import get_pattern_recognizer

        db = get_memory_db()
        recognizer = get_pattern_recognizer()

        # Load events from specified time window
        start_time = (datetime.now() - timedelta(days=time_window_days)).isoformat()
        events = db.get_memory_events(start_time=start_time)

        # Learn patterns
        patterns_updated = recognizer.learn_from_memory_events(events)

        # Get summary
        summary = recognizer.get_pattern_summary()

        return {
            "status": "success",
            "events_analyzed": len(events),
            "patterns_updated": patterns_updated,
            "summary": summary,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/patterns/insights", response_model=List[dict])
def get_pattern_insights(time_window_days: int = Query(default=7, ge=1, le=30)):
    """
    Get actionable insights from learned behavioral patterns.

    Args:
        time_window_days: Time window for analysis (default: 7 days)

    Returns:
        List of PatternInsight objects with recommendations
    """
    try:
        from kilo_v2.pattern_recognizer import get_pattern_recognizer

        recognizer = get_pattern_recognizer()
        insights = recognizer.generate_insights(time_window_days=time_window_days)

        # Convert dataclass to dict
        insights_dict = [
            {
                "category": i.category,
                "insight_type": i.insight_type,
                "title": i.title,
                "description": i.description,
                "recommendation": i.recommendation,
                "confidence": i.confidence,
                "data": i.data,
            }
            for i in insights
        ]

        return insights_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/patterns/summary", response_model=dict)
def get_pattern_summary():
    """
    Get summary of all learned patterns.

    Returns:
        Dictionary with pattern statistics
    """
    try:
        from kilo_v2.pattern_recognizer import get_pattern_recognizer

        recognizer = get_pattern_recognizer()
        summary = recognizer.get_pattern_summary()

        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/patterns/detect_deviation", response_model=dict)
def detect_deviation(context: dict):
    """
    Detect deviations from learned patterns for a given event context.

    Args:
        context: Event context with event_type, event_time, event_text

    Returns:
        DeviationReport with severity and recommendations
    """
    try:
        from kilo_v2.pattern_recognizer import get_pattern_recognizer

        recognizer = get_pattern_recognizer()
        report = recognizer.detect_deviation(context)

        return {
            "is_deviation": report.is_deviation,
            "severity": report.severity,
            "summary": report.summary,
            "details": report.details,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
