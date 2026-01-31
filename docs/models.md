# AI Memory Assistant - Data Models

Generated on: 2025-12-24 08:01:57

## Overview

The system uses SQLAlchemy models for data persistence with PostgreSQL.

## Core Models

### Memory Model
```python
class Memory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str
    memory_type: str  # conversation, medication, habit, finance, reminder, knowledge
    importance: int  # 1-10 scale
    user_id: int
    timestamp: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

### Conversation Model
```python
class Conversation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    messages: List[Dict[str, str]]
    user_id: int
    summary: Optional[str]
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

### Medication Model
```python
class Medication(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    dosage: str
    schedule: str
    instructions: Optional[str]
    prescriber: Optional[str]
    quantity: int
    user_id: int
```

### Reminder Model
```python
class Reminder(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    text: str
    when: str
    time: str
    completed: bool = False
    recurring: bool = False
    user_id: int
```

### User Model
```python
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    email: str = Field(unique=True)
    hashed_password: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

## Relationships

- **User → Memories**: One-to-many
- **User → Conversations**: One-to-many
- **User → Medications**: One-to-many
- **User → Reminders**: One-to-many
- **Memory → User**: Many-to-one (foreign key)

## Database Schema

The system uses PostgreSQL with the following key tables:
- `memory`
- `conversation`
- `medication`
- `reminder`
- `user`

## Data Validation

All models include validation:
- Memory importance: 1-10 range
- Required fields: content, memory_type, user_id
- Email format validation for users
- Date/time format validation

