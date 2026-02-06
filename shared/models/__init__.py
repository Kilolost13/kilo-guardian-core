from sqlmodel import SQLModel, Field
from typing import Optional, List
from datetime import datetime

# --- Financial Models ---

class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    amount: float
    description: str
    date: str
    category: Optional[str] = None
    source: Optional[str] = None  # e.g., 'manual', 'ocr', 'doc:sha256'
    transaction_type: Optional[str] = None # 'income' | 'expense'

class ReceiptItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    transaction_id: int = Field(index=True)
    name: str
    price: float
    category: Optional[str] = None

class Budget(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    category: str = Field(index=True)
    monthly_limit: float
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class Goal(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    target_amount: float
    current_amount: float = 0.0
    deadline: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed: bool = False

class IngestedDocument(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: Optional[str] = None
    content_type: Optional[str] = None
    sha256: str = Field(index=True)
    kind: Optional[str] = None  # receipt | statement | auto
    status: Optional[str] = None
    error: Optional[str] = None
    transaction_count: int = 0
    source_tag: Optional[str] = None
    extracted_text: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

# --- Medication Models ---

class Med(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    schedule: str
    dosage: str
    quantity: int = 0
    prescriber: str = ""
    instructions: str = ""
    last_taken: Optional[str] = None  # ISO format string
    taken_count: int = 0
    frequency_per_day: int = 1
    times: Optional[str] = None  # comma-separated HH:MM
    from_ocr: bool = False
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class OcrJob(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: str = Field(index=True, unique=True)
    status: str = Field(default="pending")  # pending, processing, completed, failed
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    image_path: str = ""
    ocr_text: Optional[str] = None
    error_message: Optional[str] = None
    target_id: Optional[int] = None  # Resulting Med or Transaction ID
    result_data: Optional[str] = None  # JSON string

# --- Habit Models ---

class Habit(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    frequency: str = "daily"
    target_count: int = 1
    active: bool = True
    med_id: Optional[int] = Field(default=None, index=True)
    preferred_times: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class HabitCompletion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    habit_id: int = Field(index=True)
    completion_date: str
    count: int = 1

# --- Reminder Models ---

class Reminder(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    text: str
    when: str
    sent: bool = False
    escalated: bool = False
    recurrence: Optional[str] = None
    timezone: Optional[str] = None
    preset_id: Optional[int] = None

class ReminderPreset(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    time_of_day: Optional[str] = None
    recurrence: Optional[str] = None
    tags: Optional[str] = None
    habit_id: Optional[int] = None
    med_id: Optional[int] = None

# --- Core AI & Knowledge Models ---

class Memory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    source: Optional[str] = None
    modality: Optional[str] = None
    text_blob: Optional[str] = None
    metadata_json: Optional[str] = None
    embedding_json: Optional[str] = None
    privacy_label: Optional[str] = None
    ttl_seconds: Optional[int] = None

class Entry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    book: str
    page: int
    chunk: int
    text: str

class Notification(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    channel: Optional[str] = None
    payload_json: Optional[str] = None
    sent: bool = False

__all__ = [
    "Transaction", "ReceiptItem", "Budget", "Goal", "IngestedDocument",
    "Med", "OcrJob", "Habit", "HabitCompletion",
    "Reminder", "ReminderPreset", "Memory", "Entry", "Notification"
]