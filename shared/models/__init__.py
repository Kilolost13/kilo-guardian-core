from sqlmodel import SQLModel, Field
from typing import Optional


class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    amount: float
    description: str
    date: str
    source: Optional[str] = None  # e.g., 'manual', 'ocr'


class ReceiptItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    transaction_id: int
    name: str
    price: float
    category: Optional[str] = None


class Reminder(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    text: str
    when: str  # ISO format string
    sent: bool = False
    recurrence: Optional[str] = None
    timezone: Optional[str] = None
    preset_id: Optional[int] = None


class ReminderPreset(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    time_of_day: Optional[str] = None  # HH:MM
    recurrence: Optional[str] = None  # daily, weekly, hourly, or cron
    tags: Optional[str] = None
    habit_id: Optional[int] = None
    med_id: Optional[int] = None


__all__ = [
    "Transaction",
    "ReceiptItem",
    "Reminder",
    "ReminderPreset",
]

# Service-specific models that are safe to centralize for test collection
class Habit(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    frequency: str


class HabitCompletion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    habit_id: int
    completed_at: str


class Med(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = ""
    schedule: str = ""
    dosage: str = ""
    quantity: int = 0
    prescriber: str = ""
    instructions: str = ""
    created_at: Optional[str] = None


class Entry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    book: str
    page: int
    chunk: int
    text: str

__all__.extend(["Habit", "HabitCompletion", "Med", "Entry"])


# Memory model for ai_brain: stores normalized events, text blobs and an optional
# embedding (stored as JSON) so the service can perform retrieval/nearest-neighbor
# searches without requiring an external vector DB. This model is intentionally
# compact and pluggable; later we can move embeddings to FAISS or a managed store.
from datetime import datetime
from typing import Optional


class Memory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    source: Optional[str] = None  # e.g., 'cam', 'receipt', 'meds', 'user'
    modality: Optional[str] = None  # 'text','image','audio'
    text_blob: Optional[str] = None
    metadata_json: Optional[str] = None
    embedding_json: Optional[str] = None  # store list[float] as json
    privacy_label: Optional[str] = None
    ttl_seconds: Optional[int] = None


__all__.append("Memory")


# Notification model to persist outgoing notifications when an external
# notification service is not configured. This allows the reminder service to
# record notifications for later inspection in tests or UI.
class Notification(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    channel: Optional[str] = None  # e.g., 'sms','email','push'
    payload_json: Optional[str] = None
    sent: bool = False


__all__.append("Notification")
