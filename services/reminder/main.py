import os
import sys
import threading
from datetime import datetime, timedelta, time as dtime
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Request
from sqlmodel import Session, select, create_engine
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
import httpx

# Add shared directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from shared.models import Reminder, ReminderPreset, Notification

# Use shared database path from PVC
db_url = os.getenv("DATABASE_URL", "sqlite:////app/kilo_data/kilo_guardian.db")
engine = create_engine(db_url, connect_args={"check_same_thread": False})

_scheduler = BackgroundScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    _scheduler.start()
    # Re-schedule all pending reminders on startup
    with Session(engine) as session:
        reminders = session.exec(select(Reminder).where(Reminder.sent == False)).all()
        for r in reminders:
            _schedule_reminder(r)
    yield
    _scheduler.shutdown()

app = FastAPI(title="Kilo Reminder Service", lifespan=lifespan)

def _schedule_reminder(r: Reminder):
    job_id = f"reminder_{r.id}"
    try:
        when = datetime.fromisoformat(r.when)
        if r.recurrence == "daily":
            trigger = CronTrigger(hour=when.hour, minute=when.minute)
        else:
            trigger = DateTrigger(run_date=when)
        
        _scheduler.add_job(_send_reminder_task, trigger, args=[r.id], id=job_id, replace_existing=True)
    except Exception as e:
        print(f"Scheduling failed: {e}")

def _send_reminder_task(reminder_id: int):
    with Session(engine) as session:
        r = session.get(Reminder, reminder_id)
        if r:
            print(f"🔔 REMINDER: {r.text}")
            r.sent = True
            session.add(r)
            session.commit()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def list_reminders():
    with Session(engine) as session:
        return session.exec(select(Reminder)).all()

@app.post("/")
def add_reminder(r: Reminder):
    with Session(engine) as session:
        session.add(r)
        session.commit()
        session.refresh(r)
        _schedule_reminder(r)
        return r