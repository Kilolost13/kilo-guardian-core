from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from sqlmodel import SQLModel, create_engine, Session, Field
from typing import Optional, List
import os
import httpx
import datetime
import json

# Habit models
class Habit(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    frequency: str = "daily"
    target_count: int = 1
    active: bool = True
    med_id: Optional[int] = Field(default=None, index=True)
    preferred_times: Optional[str] = None  # comma-separated HH:MM
    created_at: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat())

class HabitCompletion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    habit_id: int
    completion_date: str
    count: int = 1
    reminder_id: Optional[int] = None
    status: Optional[str] = None  # completed | skipped
    med_id: Optional[int] = None

db_url = "sqlite:////tmp/habits.db"
engine = create_engine(db_url, echo=False)


def _ensure_columns():
    """Best-effort schema drift fixer for new columns when using SQLite."""
    try:
        with engine.connect() as conn:
            cols = conn.execute("PRAGMA table_info(habit)").fetchall()
            col_names = {c[1] for c in cols}
            if 'med_id' not in col_names:
                conn.execute("ALTER TABLE habit ADD COLUMN med_id INTEGER")
            if 'preferred_times' not in col_names:
                conn.execute("ALTER TABLE habit ADD COLUMN preferred_times VARCHAR")
            if 'created_at' not in col_names:
                conn.execute("ALTER TABLE habit ADD COLUMN created_at VARCHAR")
        with engine.connect() as conn:
            cols = conn.execute("PRAGMA table_info(habitcompletion)").fetchall()
            col_names = {c[1] for c in cols}
            if 'reminder_id' not in col_names:
                conn.execute("ALTER TABLE habitcompletion ADD COLUMN reminder_id INTEGER")
            if 'status' not in col_names:
                conn.execute("ALTER TABLE habitcompletion ADD COLUMN status VARCHAR")
            if 'med_id' not in col_names:
                conn.execute("ALTER TABLE habitcompletion ADD COLUMN med_id INTEGER")
    except Exception as e:
        print("[HABITS] Schema check failed (non-fatal):", e)


from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        SQLModel.metadata.create_all(engine)
        _ensure_columns()
    except Exception:
        pass
    yield


app = FastAPI(title="Habits Service", lifespan=lifespan)

# Health check endpoints
@app.get("/status")
@app.get("/health")
def status():
    return {"status": "ok"}

AI_BRAIN_URL = os.getenv("AI_BRAIN_URL", "http://ai_brain:9004/ingest/habit")

# optional centralized admin validation client (gateway) - lazy import
gateway_validate_token = None


def _require_admin(headers: dict = None) -> bool:
    """If an X-Admin-Token header is present, validate it via gateway; otherwise permissive when no local ADMIN_TOKEN is set."""
    token_required = os.getenv("ADMIN_TOKEN")
    token = None
    if headers:
        token = headers.get('x-admin-token') or headers.get('X-Admin-Token')
    if token_required:
        if token == token_required:
            return True
        raise Exception("invalid admin token")
    # no local token: permissive if no header; if header provided, attempt gateway validation
    if not token:
        return True
    global gateway_validate_token
    if gateway_validate_token is None:
        try:
            from microservice.gateway.admin_client import validate_token as _gval
            gateway_validate_token = _gval
        except Exception:
            gateway_validate_token = None
    if gateway_validate_token:
        try:
            return gateway_validate_token(token)
        except Exception:
            return False
    return False

# startup handled by lifespan

@app.get("/")
def list_habits():
    with Session(engine) as session:
        habits = session.query(Habit).all()
        # Fetch all completions in a single query to avoid N+1 problem
        all_completions = session.query(HabitCompletion).all()
        
        # Group completions by habit_id for efficient lookup
        completions_by_habit = {}
        for c in all_completions:
            if c.habit_id not in completions_by_habit:
                completions_by_habit[c.habit_id] = []
            completions_by_habit[c.habit_id].append(c)
        
        result = []
        for h in habits:
            # Get completions from pre-fetched dict
            completions = completions_by_habit.get(h.id, [])
            # Convert to dict and add completions
            habit_dict = {
                "id": h.id,
                "name": h.name,
                "frequency": h.frequency,
                "target_count": h.target_count,
                "active": h.active,
                "completions": [
                    {
                        "id": c.id,
                        "habit_id": c.habit_id,
                        "completion_date": c.completion_date,
                        "count": c.count
                    } for c in completions
                ]
            }
            result.append(habit_dict)
        return result

@app.post("/")
def add_habit(h: Habit, background_tasks: BackgroundTasks = None):
    with Session(engine) as session:
        session.add(h)
        session.commit()
        session.refresh(h)
    # Send to ai_brain
    if background_tasks:
        background_tasks.add_task(_send_to_ai_brain, h)
    else:
        import asyncio
        asyncio.create_task(_send_to_ai_brain(h))
    return h


@app.post("/med-adherence")
def upsert_med_adherence(payload: dict, request: Request = None, background_tasks: BackgroundTasks = None):
    """
    Upsert a habit representing medication adherence, keyed by med_id.
    Expected payload: { med_id, name, target_per_day, times: ["08:00", ...] }
    """
    med_id = payload.get("med_id")
    if not med_id:
        raise HTTPException(status_code=400, detail="med_id is required")

    name = payload.get("name") or f"Medication {med_id}"
    target = payload.get("target_per_day") or payload.get("frequency_per_day") or 1
    times = payload.get("times") or []
    times_str = ",".join(times) if isinstance(times, list) else str(times)

    with Session(engine) as session:
        existing = session.query(Habit).filter(Habit.med_id == med_id).first()
        if existing:
            existing.name = name
            existing.target_count = target
            existing.frequency = "daily"
            existing.preferred_times = times_str
            session.add(existing)
            session.commit()
            session.refresh(existing)
            habit = existing
        else:
            habit = Habit(
                name=name,
                frequency="daily",
                target_count=target,
                med_id=med_id,
                preferred_times=times_str,
            )
            session.add(habit)
            session.commit()
            session.refresh(habit)

    if background_tasks:
        background_tasks.add_task(_send_to_ai_brain, habit)
    else:
        import asyncio
        asyncio.create_task(_send_to_ai_brain(habit))

    return habit


@app.post("/log")
def log_med_adherence(payload: dict, background_tasks: BackgroundTasks = None):
    """
    Record a completion/skip event for a med-linked habit.
    Payload: { habit_id?, med_id?, reminder_id?, status, timestamp }
    """
    habit_id = payload.get("habit_id")
    med_id = payload.get("med_id")
    status = payload.get("status", "completed")
    reminder_id = payload.get("reminder_id")
    ts = payload.get("timestamp") or datetime.datetime.utcnow().isoformat()

    if not habit_id and not med_id:
        raise HTTPException(status_code=400, detail="habit_id or med_id required")

    with Session(engine) as session:
        habit = None
        if habit_id:
            habit = session.get(Habit, habit_id)
        if not habit and med_id:
            habit = session.query(Habit).filter(Habit.med_id == med_id).first()
        if not habit:
            raise HTTPException(status_code=404, detail="Habit not found for logging")

        completion = HabitCompletion(
            habit_id=habit.id,
            completion_date=ts,
            count=1,
            reminder_id=reminder_id,
            status=status,
            med_id=med_id or habit.med_id,
        )
        session.add(completion)
        session.commit()
        session.refresh(completion)

    if background_tasks:
        background_tasks.add_task(_send_completion_to_ai_brain, habit, completion)
    else:
        import asyncio
        asyncio.create_task(_send_completion_to_ai_brain(habit, completion))

    return completion

@app.put("/{habit_id}")
def update_habit(habit_id: int, h: Habit):
    with Session(engine) as session:
        db_habit = session.get(Habit, habit_id)
        if not db_habit:
            raise HTTPException(status_code=404, detail="Habit not found")
        db_habit.name = h.name
        db_habit.frequency = h.frequency
        db_habit.target_count = h.target_count
        db_habit.active = h.active
        session.add(db_habit)
        session.commit()
        session.refresh(db_habit)
        return db_habit

@app.delete("/{habit_id}")
def delete_habit(habit_id: int):
    with Session(engine) as session:
        habit = session.get(Habit, habit_id)
        if not habit:
            raise HTTPException(status_code=404, detail="Habit not found")
        # Delete associated completions using bulk delete (more efficient)
        session.query(HabitCompletion).filter(HabitCompletion.habit_id == habit_id).delete()
        session.delete(habit)
        session.commit()
    return {"status": "deleted"}

@app.post("/complete/{habit_id}")
def complete_habit(habit_id: int, background_tasks: BackgroundTasks = None):
    today = datetime.datetime.utcnow().date().isoformat()
    with Session(engine) as session:
        habit = session.get(Habit, habit_id)
        if not habit:
            raise HTTPException(status_code=404, detail="Habit not found")

        # Check if already completed today
        existing = session.query(HabitCompletion).filter(
            HabitCompletion.habit_id == habit_id,
            HabitCompletion.completion_date == today
        ).first()

        if existing:
            existing.count += 1
            session.commit()
            session.refresh(existing)
            completion = existing
        else:
            completion = HabitCompletion(
                habit_id=habit_id,
                completion_date=today,
                count=1
            )
            session.add(completion)
            session.commit()
            session.refresh(completion)

    # Send to ai_brain
    if background_tasks:
        background_tasks.add_task(_send_completion_to_ai_brain, habit, completion)
    else:
        import asyncio
        asyncio.create_task(_send_completion_to_ai_brain(habit, completion))
    return completion

async def _send_to_ai_brain(h: Habit):
    async with httpx.AsyncClient() as client:
        try:
            await client.post(AI_BRAIN_URL, json={
                "name": h.name,
                "frequency": h.frequency
            }, timeout=5)
        except Exception as e:
            print(f"[AI_BRAIN] Failed to send habit: {e}")

async def _send_completion_to_ai_brain(h: Habit, c: HabitCompletion):
    async with httpx.AsyncClient() as client:
        try:
            await client.post("http://ai_brain:9004/ingest/habit_completion", json={
                "habit": h.name,
                "completion_date": c.completion_date,
                "count": c.count,
                "frequency": h.frequency
            }, timeout=5)
        except Exception as e:
            print(f"[AI_BRAIN] Failed to send habit completion: {e}")
