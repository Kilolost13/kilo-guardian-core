from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class SedentaryState(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str
    start_time: datetime
    last_movement: Optional[datetime] = None
    reminder_count: int = 0
    active: bool = True
    returned_after_reminder_count: int = 0
    reminder_ids_json: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CamReport(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str
    face_id: Optional[str] = None
    posture: str  # 'sitting','standing','walking'
    timestamp: datetime
    location_hash: Optional[str] = None
    image_id: Optional[str] = None

class MedRecord(SQLModel, table=True):
    med_id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str
    name: str
    dosage: Optional[str] = None
    schedule_json: Optional[str] = Field(default=None)  # JSON string list of times e.g. ['08:00']
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MedAdherence(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    med_id: int
    user_id: str
    timestamp: datetime
    taken: bool

class HabitEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str
    event_type: str
    timestamp: datetime

class HabitProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str
    event_type: str
    mean_seconds: Optional[float] = None
    stddev_seconds: Optional[float] = None
    frequency_per_week: Optional[float] = None
    data_points: int = 0
    confidence: float = 0.0
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserSettings(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str
    opt_out_camera: bool = False
    opt_out_habits: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SentReminder(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    reminder_id: Optional[int] = None
    reminder_text: Optional[str] = None
    when: Optional[str] = None
    received_at: datetime = Field(default_factory=datetime.utcnow)
