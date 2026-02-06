import os
import sys
import asyncio
import datetime
import json
from typing import Optional, List

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from sqlmodel import Session, select, create_engine
import httpx

# Add shared directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from shared.models import Habit, HabitCompletion

# Use shared database path from PVC
db_url = os.getenv("DATABASE_URL", "sqlite:////app/kilo_data/kilo_guardian.db")
engine = create_engine(db_url, connect_args={"check_same_thread": False})

app = FastAPI(title="Kilo Habits Service")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def list_habits():
    with Session(engine) as session:
        habits = session.exec(select(Habit)).all()
        # Fetch completions logic
        result = []
        for h in habits:
            completions = session.exec(select(HabitCompletion).where(HabitCompletion.habit_id == h.id)).all()
            habit_dict = h.dict()
            habit_dict["completions"] = [c.dict() for c in completions]
            result.append(habit_dict)
        return result

@app.post("/")
def add_habit(h: Habit):
    with Session(engine) as session:
        session.add(h)
        session.commit()
        session.refresh(h)
        return h

@app.post("/complete/{habit_id}")
def complete_habit(habit_id: int):
    today = datetime.datetime.utcnow().date().isoformat()
    with Session(engine) as session:
        habit = session.get(Habit, habit_id)
        if not habit:
            raise HTTPException(status_code=404, detail="Habit not found")
        
        completion = HabitCompletion(habit_id=habit_id, completion_date=today, count=1)
        session.add(completion)
        session.commit()
        return completion