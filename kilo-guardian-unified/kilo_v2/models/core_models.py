from datetime import datetime

from sqlalchemy import Boolean, Column, Float, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

from kilo_v2.models.auth_models import Base


class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True)
    timestamp = Column(
        String, nullable=False, default=lambda: datetime.utcnow().isoformat()
    )
    type = Column(String, nullable=False)
    source = Column(String, nullable=False)
    confidence = Column(Float)
    data = Column(Text)


class Habit(Base):
    __tablename__ = "habits"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    habit_key = Column(String, nullable=False, unique=True)
    pattern_json = Column(Text)


class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id = Column(Integer, primary_key=True)
    timestamp = Column(
        String, nullable=False, default=lambda: datetime.utcnow().isoformat()
    )
    activity_type = Column(String, nullable=False)
    location = Column(String)
    duration_minutes = Column(Integer)
    detected_by = Column(String)
    notes = Column(Text)


class HealthReminder(Base):
    __tablename__ = "health_reminders"
    id = Column(Integer, primary_key=True)
    reminder_type = Column(String)
    message = Column(Text)
    frequency = Column(String)
    interval_minutes = Column(Integer)
    next_trigger = Column(String)
    priority = Column(String)
    active = Column(Boolean, default=True)


class LifeAdminTask(Base):
    __tablename__ = "life_admin_tasks"
    id = Column(Integer, primary_key=True)
    task_name = Column(String, nullable=False)
    category = Column(String)
    due_date = Column(String)
    priority = Column(String)
    completed = Column(Boolean, default=False)
    ai_suggested = Column(Boolean, default=False)
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())


class DailyWellness(Base):
    __tablename__ = "daily_wellness"
    date = Column(String, primary_key=True)
    total_active_minutes = Column(Integer, default=0)
    total_sedentary_minutes = Column(Integer, default=0)
    steps = Column(Integer, default=0)
    water_glasses = Column(Integer, default=0)
    sleep_hours = Column(Float, default=0)
    mood = Column(String)
    wellness_score = Column(Integer, default=0)


class CurrentSession(Base):
    __tablename__ = "current_session"
    id = Column(Integer, primary_key=True)
    session_start = Column(String)
    current_activity = Column(String)
    current_location = Column(String)
    warned_sedentary = Column(Boolean, default=False)
