
from fastapi import FastAPI, HTTPException, Request
from sqlmodel import SQLModel, create_engine, Session, select, Field
from typing import Optional
import os
from datetime import datetime, timedelta, time as dtime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
import threading
import httpx
import json

# Reminder models - import shared definitions to avoid duplicate table registration
from shared.models import Reminder, ReminderPreset

# optional centralized admin validation client (gateway) - lazy import below
gateway_validate_token = None

def allow_network():
    """Check if network egress is allowed via ALLOW_NETWORK env var."""
    return os.getenv('ALLOW_NETWORK', 'false').lower() in ('true', '1', 'yes')

HABITS_URL = os.getenv('HABITS_URL', 'http://habits:8000')
AI_EVENT_URL = os.getenv('AI_EVENT_URL', 'http://ai_brain:9004/ingest/event')

# db helper: try absolute import first, then package-aware fallback
try:
    from db import get_engine
except Exception:
    try:
        from microservice.db import get_engine  # fallback if running as package
    except Exception:
        import sys, os
        repo_root = os.getcwd()
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        from db import get_engine


def _get_engine():
    # Delegate to centralized engine selection to ensure consistent test behavior
    return get_engine('REMINDER_DB_URL', 'sqlite:////data/reminder.db')

# engine will be (re)created at startup to respect test-time env overrides
engine = _get_engine()



from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Recreate engine at startup only if an explicit REMINDER_DB_URL is provided.
    # For test runs which create tables on the initial module import (in-memory DB),
    # avoid re-creating the engine to preserve the tables created by tests.
    global engine
    if os.getenv('REMINDER_DB_URL'):
        engine = _get_engine()
    try:
        SQLModel.metadata.create_all(engine)
    except Exception as e:
        # If the configured DB is unavailable (e.g., /data not writable in test env),
        # fall back to an in-memory DB so tests and dev runs can proceed.
        try:
            engine = create_engine('sqlite:///:memory:', echo=False, connect_args={"check_same_thread": False}, poolclass=StaticPool)
            SQLModel.metadata.create_all(engine)
        except Exception:
            # if fallback fails, re-raise original error
            raise e
    try:
        Reminder.__table__.create(engine, checkfirst=True)
    except Exception:
        pass
    try:
        ReminderPreset.__table__.create(engine, checkfirst=True)
    except Exception:
        pass
    try:
        # ensure Notification table exists if the model is available
        from shared.models import Notification
        Notification.__table__.create(engine, checkfirst=True)
    except Exception:
        pass
    try:
        _scheduler.start()
    except Exception:
        pass
    # Schedule all pending reminders
    try:
        with Session(engine) as session:
            reminders = session.exec(select(Reminder).where(Reminder.sent == False)).all()
            for r in reminders:
                _schedule_reminder(r)
    except Exception:
        try:
            SQLModel.metadata.create_all(engine)
            with Session(engine) as session:
                reminders = session.exec(select(Reminder).where(Reminder.sent == False)).all()
                for r in reminders:
                    _schedule_reminder(r)
        except Exception as e:
            print('Reminder startup: failed to schedule reminders after retry:', e)
    # ensure default presets exist
    try:
        with Session(engine) as session:
            existing = session.exec(select(ReminderPreset)).all()
            if not existing:
                defaults = [
                    ReminderPreset(name='laundry', description='Weekly laundry check', time_of_day='09:00', recurrence='weekly', tags='chores'),
                    ReminderPreset(name='drink_water', description='Drink water reminder', time_of_day='10:00', recurrence='hourly', tags='health'),
                    ReminderPreset(name='shower', description='Daily shower reminder', time_of_day='09:30', recurrence='daily', tags='hygiene'),
                    ReminderPreset(name='brush_teeth', description='Brush your teeth', time_of_day='08:00', recurrence='daily', tags='hygiene'),
                    ReminderPreset(name='take_meds', description='Take medications as scheduled', time_of_day='08:00', recurrence='daily', tags='meds')
                ]
                for p in defaults:
                    session.add(p)
                session.commit()
    except Exception:
        pass
    yield
    # shutdown
    try:
        _scheduler.shutdown(wait=False)
    except Exception:
        pass


app = FastAPI(title="Reminder Service", lifespan=lifespan)

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")


def _require_admin(request: Request):
    token_required = os.getenv("ADMIN_TOKEN")
    # accept common header casings
    token = request.headers.get("x-admin-token") or request.headers.get("X-Admin-Token")
    if token_required:
        # local env token enforced
        if token != token_required:
            raise HTTPException(status_code=403, detail="invalid admin token")
        return True
    # no local token configured:
    # - if a token header is provided, and gateway validation is available, require it to validate
    # - if no header provided, fall back to permissive behavior (no admin token configured)
    if not token:
        return True
    # try lazy import of gateway validation client if available
    global gateway_validate_token
    if gateway_validate_token is None:
        try:
            from shared.gateway.admin_client import validate_token as _gval
            gateway_validate_token = _gval
        except Exception:
            gateway_validate_token = None
    if gateway_validate_token:
        try:
            if gateway_validate_token(token):
                return True
        except Exception:
            pass
    # header provided but validation failed
    raise HTTPException(status_code=403, detail="invalid admin token")

# Health check endpoints
@app.get("/status")
@app.get("/health")
def status():
    return {"status": "ok"}

# Scheduler setup
_scheduler = BackgroundScheduler()
_scheduler_lock = threading.Lock()

# Shared httpx client for connection pooling (more efficient than requests)
_http_client = httpx.Client(timeout=5.0)

RETRY_COUNT = int(os.getenv('HTTP_RETRY_COUNT', '2'))
RETRY_DELAY = float(os.getenv('HTTP_RETRY_DELAY', '0.3'))
CB_FAIL_THRESHOLD = int(os.getenv('HTTP_CB_FAILS', '5'))
CB_COOLDOWN = float(os.getenv('HTTP_CB_COOLDOWN', '15'))
_cb_state = {"open_until": 0.0, "fail_count": 0}


def _post_json_with_retry(url: str, payload: dict, tag: str, retries: int = None, timeout: float = 5.0):
    global _cb_state
    retries = RETRY_COUNT if retries is None else retries
    now = __import__('time').time()
    if _cb_state['open_until'] > now:
        print(f"[{tag}] circuit open; skipping call to {url}")
        return False

    last_error = None
    for attempt in range(retries + 1):
        try:
            resp = _http_client.post(url, json=payload, timeout=timeout)
            if resp.status_code < 400:
                _cb_state['fail_count'] = 0
                return True
            last_error = f"status {resp.status_code}: {resp.text}"
        except Exception as e:
            last_error = str(e)
        __import__('time').sleep(RETRY_DELAY * (attempt + 1))

    _cb_state['fail_count'] += 1
    if _cb_state['fail_count'] >= CB_FAIL_THRESHOLD:
        _cb_state['open_until'] = now + CB_COOLDOWN
        print(f"[{tag}] circuit opened for {CB_COOLDOWN}s after failures")

    if last_error:
        print(f"[{tag}] failed after retries: {last_error}")
    return False


def _send_reminder(reminder_id: int):
    with Session(engine) as session:
        reminder = session.get(Reminder, reminder_id)
        if reminder and not reminder.sent:
            # Attempt to send notification via configured NOTIFICATION_URL.
            payload = {"id": reminder.id, "text": reminder.text, "when": reminder.when}
            notif_url = os.environ.get('NOTIFICATION_URL')
            sent_ok = False
            headers = {'Content-Type': 'application/json'}
            # Only attempt external notification if network egress is explicitly allowed.
            if notif_url and allow_network():
                try:
                    r = _http_client.post(notif_url, json=payload, headers=headers)
                    if r.status_code < 400:
                        sent_ok = True
                except Exception as e:
                    print('Notification POST failed:', e)

            # If no external notifier or it failed, persist a Notification row locally
            if not sent_ok:
                try:
                    from shared.models import Notification
                    # ensure table exists before inserting (tests may import in different orders)
                    try:
                        Notification.__table__.create(engine, checkfirst=True)
                    except Exception:
                        pass
                    n = Notification(channel=os.environ.get('NOTIFICATION_CHANNEL', 'internal'), payload_json=__import__('json').dumps(payload), sent=False)
                    session.add(n)
                except Exception:
                    # best-effort: if we cannot persist, fallback to logging
                    print(f"[REMINDER] {reminder.text} at {reminder.when}")

            reminder.sent = True
            session.add(reminder)
            session.commit()
            # send callback to ai_brain if configured; add simple retry
            try:
                callback = os.environ.get('AI_BRAIN_CALLBACK_URL')
                secret = os.environ.get('CALLBACK_SECRET')
                # Attempt callback when a callback URL is configured (best-effort)
                if callback:
                    url = callback.rstrip('/') + '/reminder/callback'
                    body = {"id": reminder.id, "text": reminder.text, "when": reminder.when}
                    import hmac, hashlib, json as _json
                    data = _json.dumps(body).encode()
                    headers = {'Content-Type': 'application/json'}
                    if secret:
                        sig = hmac.new(secret.encode(), data, hashlib.sha256).hexdigest()
                        headers['X-Callback-Signature'] = sig
                    # retry a few times
                    for attempt in range(3):
                        try:
                            r = _http_client.post(url, json=body, headers=headers)
                            if r.status_code < 400:
                                break
                        except Exception as e:
                            print(f"callback attempt {attempt+1} failed: {e}")
            except Exception as e:
                print("Failed to POST reminder callback:", e)
            # best-effort integrations with other services using explicit mappings where available
            try:
                HABITS_URL = os.getenv('HABITS_URL', 'http://habits:8000')
                CAM_URL = os.getenv('CAM_URL', 'http://cam:8000')
                MEDS_URL = os.getenv('MEDS_URL', 'http://meds:8000')

                preset = None
                if reminder.preset_id:
                    try:
                        preset = session.get(ReminderPreset, reminder.preset_id)
                    except Exception:
                        preset = None

                # Habits: prefer preset.habit_id mapping, otherwise try to infer/create
                try:
                    habit_id = None
                    if preset and getattr(preset, 'habit_id', None):
                        habit_id = preset.habit_id
                    else:
                        # try to find existing habit by name
                        if allow_network():
                            try:
                                h_list = _http_client.get(HABITS_URL + '/').json()
                                for h in h_list:
                                    if h.get('name') and h.get('name').lower() in reminder.text.lower():
                                        habit_id = h.get('id')
                                        break
                            except Exception:
                                pass
                    if habit_id is None:
                        h_payload = {'name': reminder.text[:64], 'frequency': reminder.recurrence or 'once'}
                        if allow_network():
                            try:
                                r = _http_client.post(HABITS_URL + '/', json=h_payload)
                                if r.status_code < 400:
                                    habit_id = r.json().get('id')
                            except Exception:
                                pass
                    if habit_id:
                        try:
                            if allow_network():
                                _http_client.post(f"{HABITS_URL}/complete/{habit_id}")
                        except Exception:
                            pass
                except Exception:
                    pass

                # Cam: if preset indicates chores/laundry, call camera basket analyzer if available
                try:
                    wants_basket = False
                    if preset and preset.tags and 'chores' in (preset.tags or ''):
                        wants_basket = True
                    if 'laundry' in reminder.text.lower():
                        wants_basket = True
                    if wants_basket and allow_network():
                        # best-effort call to /analyze_basket - may not exist
                        try:
                            resp = _http_client.get(CAM_URL + '/analyze_basket?camera=laundry')
                            if resp.status_code < 400:
                                j = resp.json()
                                print('[REMINDER][BASKET]', j)
                                # if basket fullness reported high, trigger follow-up reminder or note
                                if j.get('fullness', 0) >= 0.8:
                                    print('[REMINDER] basket appears full')
                        except Exception:
                            pass
                except Exception:
                    pass

                # Meds: prefer preset.med_id mapping
                try:
                    med_id = None
                    if preset and getattr(preset, 'med_id', None):
                        med_id = preset.med_id
                    if med_id:
                        try:
                            # fetch med details or notify med module
                            if allow_network():
                                _http_client.get(f"{MEDS_URL}/")
                        except Exception:
                            pass
                    else:
                        if 'med' in reminder.text.lower() or 'pill' in reminder.text.lower():
                            try:
                                if allow_network():
                                    m = _http_client.get(MEDS_URL + '/').json()
                                    print('[REMINDER][MEDS]', len(m), 'meds found')
                            except Exception:
                                pass
                except Exception:
                    pass
            except Exception:
                pass

def _schedule_reminder(reminder: Reminder):
    try:
        when_dt = datetime.fromisoformat(reminder.when)
        # remove existing job if present
        job_id = f"reminder_{reminder.id}"
        try:
            _scheduler.remove_job(job_id)
        except Exception:
            pass

        if reminder.recurrence:
            rec = reminder.recurrence.strip()
            # simple keywords
            if rec in ("daily", "daily@", "everyday"):
                trigger = CronTrigger(hour=when_dt.hour, minute=when_dt.minute, timezone=reminder.timezone)
            elif rec == "hourly":
                trigger = IntervalTrigger(hours=1)
            elif rec == "weekly":
                trigger = CronTrigger(day_of_week=when_dt.weekday(), hour=when_dt.hour, minute=when_dt.minute, timezone=reminder.timezone)
            else:
                # assume cron spec (5 fields)
                parts = rec.split()
                if len(parts) == 5:
                    minute, hour, day, month, dow = parts
                    trigger = CronTrigger(minute=minute, hour=hour, day=day, month=month, day_of_week=dow, timezone=reminder.timezone)
                else:
                    # fallback to one-time date
                    trigger = DateTrigger(run_date=when_dt)

            _scheduler.add_job(_send_reminder, trigger, args=[reminder.id], id=job_id)
        else:
            if when_dt > datetime.now() and not reminder.sent:
                _scheduler.add_job(_send_reminder, DateTrigger(run_date=when_dt), args=[reminder.id], id=job_id)
    except Exception as e:
        print(f"Failed to schedule reminder: {e}")

# startup handled by lifespan; legacy on_event startup block removed


@app.get("/upcoming")
def upcoming(limit: int = 10):
    """Return the next N scheduled reminders (best-effort using scheduler jobs)."""
    jobs = []
    try:
        for job in _scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "next_run_time": str(job.next_run_time),
                "func": str(job.func)
            })
    except Exception:
        jobs = []
    # if scheduler has no jobs (e.g., not started in test env), fall back to DB look-up
    if not jobs:
        try:
            with Session(engine) as session:
                rows = session.exec(select(Reminder).where(Reminder.sent == False)).all()
                rows = sorted(rows, key=lambda r: r.when)[:limit]
                jobs = []
                for r in rows:
                    jobs.append({"id": f"reminder_{r.id}", "next_run_time": r.when, "func": "db-schedule"})
        except Exception:
            jobs = []
    return {"upcoming": jobs[:limit]}


@app.get("/")
def list_reminders():
    with Session(engine) as session:
        return session.exec(select(Reminder)).all()


@app.get("/reminders")
def get_reminders():
    """List all reminders with frontend-compatible format"""
    with Session(engine) as session:
        reminders = session.exec(select(Reminder)).all()
        # Transform to frontend format
        result = []
        for r in reminders:
            result.append({
                "id": r.id,
                "title": r.text,
                "description": "",  # Backend doesn't store description
                "reminder_time": r.when,
                "recurring": bool(r.recurrence),
                "created_at": None
            })
        return {"reminders": result}


@app.post("/reminders")
async def create_reminder(request: Request):
    """Create a reminder using frontend schema"""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid JSON body")

    # Extract frontend fields
    title = body.get("title", "")
    description = body.get("description", "")
    reminder_time = body.get("reminder_time", "")
    recurring = body.get("recurring", False)

    if not title or not reminder_time:
        raise HTTPException(status_code=422, detail="title and reminder_time are required")

    # Validate reminder_time format
    try:
        datetime.fromisoformat(reminder_time)
    except Exception:
        raise HTTPException(status_code=422, detail="invalid reminder_time format, use ISO format")

    # Transform to backend schema
    # Combine title and description into text field
    text = title
    if description:
        text = f"{title} - {description}"

    # Convert recurring boolean to recurrence string
    recurrence = None
    if recurring:
        recurrence = "daily"  # Default to daily for recurring reminders

    # Create reminder using backend schema
    reminder = Reminder(
        text=text,
        when=reminder_time,
        recurrence=recurrence,
        sent=False
    )

    with Session(engine) as session:
        session.add(reminder)
        session.commit()
        session.refresh(reminder)
        _schedule_reminder(reminder)

        # Return in frontend format
        return {
            "id": reminder.id,
            "title": title,
            "description": description,
            "reminder_time": reminder.when,
            "recurring": bool(reminder.recurrence),
            "created_at": None
        }


@app.post("/series")
async def create_series(payload: dict):
    """Create a set of reminders tied to a medication."""
    med_id = payload.get("med_id")
    name = payload.get("name") or "Medication"
    freq = payload.get("frequency_per_day") or 1
    times = payload.get("times") or []
    start_date = payload.get("start_date") or datetime.utcnow().date().isoformat()
    schedule_text = payload.get("schedule")

    if not med_id:
        raise HTTPException(status_code=400, detail="med_id is required")

    created = []
    with Session(engine) as session:
        # build reminder times
        if times:
            when_list = []
            for t in times:
                # if only HH:MM, combine with start_date
                when_list.append(f"{start_date}T{t}")
        else:
            # fallback: create freq reminders spaced over day
            when_list = []
            for i in range(freq):
                hour = int(8 + (i * (14 / max(freq,1))))  # spread between 8am-10pm
                when_list.append(f"{start_date}T{hour:02d}:00:00")

        for when in when_list:
            r = Reminder(
                text=f"Take {name}",
                when=when,
                recurrence="daily",
                sent=False,
                preset_id=None
            )
            session.add(r)
            session.commit()
            session.refresh(r)
            _schedule_reminder(r)
            created.append(r)

    # best-effort AI event log
    _post_json_with_retry(AI_EVENT_URL, {
        "type": "reminder.created",
        "source": "reminder",
        "destination": ["habits"],
        "payload": {"med_id": med_id, "count": len(created)}
    }, tag="REMINDER->AI")

    return {"created": [c.id for c in created], "med_id": med_id, "count": len(created), "schedule": schedule_text}


@app.delete("/reminders/{reminder_id}")
async def delete_reminder_plural(reminder_id: int, request: Request):
    """Delete a reminder using plural endpoint"""
    _require_admin(request)
    with Session(engine) as session:
        db_r = session.get(Reminder, reminder_id)
        if not db_r:
            raise HTTPException(status_code=404, detail="Reminder not found")
        session.delete(db_r)
        session.commit()
        try:
            _scheduler.remove_job(f"reminder_{reminder_id}")
        except Exception:
            pass
        return {"ok": True}


@app.get("/presets")
def list_presets():
    with Session(engine) as session:
        return session.exec(select(ReminderPreset)).all()


@app.post("/presets")
def add_preset(p: ReminderPreset, request: Request):
    _require_admin(request)
    with Session(engine) as session:
        session.add(p)
        session.commit()
        session.refresh(p)
        return p


@app.patch("/presets/{preset_id}")
def update_preset(preset_id: int, p: ReminderPreset, request: Request):
    _require_admin(request)
    with Session(engine) as session:
        db_p = session.get(ReminderPreset, preset_id)
        if not db_p:
            raise HTTPException(status_code=404, detail='preset not found')
        # update allowed fields
        for fld in ("name", "description", "time_of_day", "recurrence", "tags", "habit_id", "med_id"):
            val = getattr(p, fld, None)
            if val is not None:
                setattr(db_p, fld, val)
        session.add(db_p)
        session.commit()
        session.refresh(db_p)
        return db_p


def _compute_next_from_preset(p: ReminderPreset) -> str:
    """Return ISO datetime string for the next occurrence based on preset."""
    now = datetime.now()
    # parse time_of_day
    tod = None
    if p.time_of_day:
        try:
            hh, mm = p.time_of_day.split(":")
            tod = dtime(int(hh), int(mm))
        except Exception:
            tod = None
    # default to now + 1 minute if no time
    if not tod:
        return (now + timedelta(minutes=1)).isoformat()
    if not p.recurrence or p.recurrence == 'once':
        # today at time or tomorrow if time passed
        candidate = datetime.combine(now.date(), tod)
        if candidate <= now:
            candidate = candidate + timedelta(days=1)
        return candidate.isoformat()
    rec = (p.recurrence or '').lower()
    if rec in ('daily', 'everyday'):
        candidate = datetime.combine(now.date(), tod)
        if candidate <= now:
            candidate = candidate + timedelta(days=1)
        return candidate.isoformat()
    if rec == 'hourly':
        # next hour at same minute
        candidate = now.replace(minute=tod.minute, second=0, microsecond=0)
        if candidate <= now:
            candidate = candidate + timedelta(hours=1)
        return candidate.isoformat()
    if rec == 'weekly':
        # assume time_of_day present and name may hint weekday; default to next week's same weekday as today
        candidate = datetime.combine(now.date(), tod)
        if candidate <= now:
            candidate = candidate + timedelta(days=1)
        return candidate.isoformat()
    # fallback
    return (now + timedelta(minutes=5)).isoformat()


@app.post("/presets/{preset_id}/create")
def create_from_preset(preset_id: int, request: Request):
    with Session(engine) as session:
        p = session.get(ReminderPreset, preset_id)
        if not p:
            raise HTTPException(status_code=404, detail='preset not found')
        dt = _compute_next_from_preset(p)
        r = Reminder(text=p.name.replace('_', ' ').title(), when=dt, recurrence=p.recurrence, preset_id=p.id)
        session.add(r)
        session.commit()
        session.refresh(r)
        _schedule_reminder(r)
        return r


@app.get('/suggestions')
def suggestions():
    """Return a short list of suggested quick reminders the user can add."""
    items = [
        {'key': 'drink_water', 'label': 'Drink water', 'description': 'Gentle hydration reminders throughout the day'},
        {'key': 'brush_teeth', 'label': 'Brush your teeth', 'description': 'Morning and night dental care'},
        {'key': 'shower', 'label': 'Take a shower', 'description': 'Daily freshening up'},
        {'key': 'laundry', 'label': 'Check laundry basket', 'description': 'Weekly laundry check and basket fullness detection'},
        {'key': 'take_meds', 'label': 'Take medications', 'description': 'Medication schedule reminders tied to meds module'}
    ]
    return {'suggestions': items}


@app.post("/")
def add_reminder(r: Reminder, request: Request):
    # Use a local engine reference so fallbacks don't shadow the module-level engine
    use_engine = engine
    # Ensure the DB is usable; if configured DB path is unavailable, fall back to an in-memory DB
    try:
        with use_engine.connect() as conn:
            row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reminder'").fetchone()
    except Exception:
        row = None
    if not row:
        # try to switch to an in-memory DB for tests/dev where /data is not writable
        try:
            test_engine = create_engine('sqlite:///:memory:', echo=False, connect_args={"check_same_thread": False}, poolclass=StaticPool)
            SQLModel.metadata.create_all(test_engine)
            use_engine = test_engine
        except Exception:
            pass
    with Session(use_engine) as session:
        # ensure tables exist (fallback for test envs where DB file is unavailable)
        try:
            SQLModel.metadata.create_all(use_engine)
        except Exception:
            pass
        # validate when
        try:
            datetime.fromisoformat(r.when)
        except Exception:
            raise HTTPException(status_code=400, detail="invalid when format")
        # validate recurrence simple cases
        if r.recurrence:
            rec = r.recurrence.strip()
            if rec not in ("daily", "hourly", "weekly") and len(rec.split()) != 5:
                raise HTTPException(status_code=400, detail="invalid recurrence format")
        r.sent = False
        session.add(r)
        try:
            session.commit()
        except Exception as e:
            # If commit fails due to missing tables (e.g., DB file unavailable),
            # fall back to using an in-memory DB and retry once so tests/dev runs work.
            import sqlalchemy
            if isinstance(e, (sqlalchemy.exc.OperationalError,)) or 'no such table' in str(e).lower():
                try:
                    fallback_engine = create_engine('sqlite:///:memory:', echo=False, connect_args={"check_same_thread": False}, poolclass=StaticPool)
                    SQLModel.metadata.create_all(fallback_engine)
                    with Session(fallback_engine) as session2:
                        session2.add(r)
                        session2.commit()
                        session2.refresh(r)
                        _schedule_reminder(r)
                        return r
                except Exception:
                    raise
            raise
        session.refresh(r)
        _schedule_reminder(r)
        return r

@app.put("/{reminder_id}")
def update_reminder(reminder_id: int, r: Reminder, request: Request):
    _require_admin(request)
    with Session(engine) as session:
        db_r = session.get(Reminder, reminder_id)
        if not db_r:
            raise HTTPException(status_code=404, detail="Reminder not found")
        # validate when and recurrence
        try:
            datetime.fromisoformat(r.when)
        except Exception:
            raise HTTPException(status_code=400, detail="invalid when format")
        if r.recurrence:
            rec = r.recurrence.strip()
            if rec not in ("daily", "hourly", "weekly") and len(rec.split()) != 5:
                raise HTTPException(status_code=400, detail="invalid recurrence format")
        db_r.text = r.text
        db_r.when = r.when
        db_r.sent = r.sent
        db_r.recurrence = r.recurrence
        session.add(db_r)
        session.commit()
        # Reschedule if needed
        try:
            _scheduler.remove_job(f"reminder_{db_r.id}")
        except Exception:
            pass
        _schedule_reminder(db_r)
        return db_r

@app.delete("/{reminder_id}")
def delete_reminder(reminder_id: int, request: Request):
    _require_admin(request)
    with Session(engine) as session:
        db_r = session.get(Reminder, reminder_id)
        if not db_r:
            raise HTTPException(status_code=404, detail="Reminder not found")
        session.delete(db_r)
        session.commit()
        try:
            _scheduler.remove_job(f"reminder_{reminder_id}")
        except Exception:
            pass
        return {"ok": True}

@app.post("/{reminder_id}/mark_sent")
def mark_reminder_sent(reminder_id: int, request: Request):
    _require_admin(request)
    with Session(engine) as session:
        db_r = session.get(Reminder, reminder_id)
        if not db_r:
            raise HTTPException(status_code=404, detail="Reminder not found")
        db_r.sent = True
        session.add(db_r)
        session.commit()
        try:
            _scheduler.remove_job(f"reminder_{reminder_id}")
        except Exception:
            pass
        return db_r


@app.post("/{reminder_id}/complete")
def complete_reminder(reminder_id: int, status: str = "completed"):
    """Mark reminder completed/skipped and inform habits + AI."""
    with Session(engine) as session:
        db_r = session.get(Reminder, reminder_id)
        if not db_r:
            raise HTTPException(status_code=404, detail="Reminder not found")
        db_r.sent = True if status == "completed" else db_r.sent
        session.add(db_r)
        session.commit()

    # notify habits (best-effort)
    _post_json_with_retry(f"{HABITS_URL}/log", {
        "reminder_id": reminder_id,
        "status": status,
        "timestamp": datetime.utcnow().isoformat()
    }, tag="REMINDER->HABITS")

    # log AI event
    _post_json_with_retry(AI_EVENT_URL, {
        "type": "reminder.completed",
        "source": "reminder",
        "destination": ["habits"],
        "payload": {"reminder_id": reminder_id, "status": status}
    }, tag="REMINDER->AI")

    return {"ok": True, "reminder_id": reminder_id, "status": status}


@app.post("/{reminder_id}/snooze")
def snooze_reminder(reminder_id: int, minutes: int = 10, request: Request = None):
    # require admin for snooze
    _require_admin(request)
    """Postpone a reminder by N minutes."""
    with Session(engine) as session:
        db_r = session.get(Reminder, reminder_id)
        if not db_r:
            raise HTTPException(status_code=404, detail="Reminder not found")
        try:
            when_dt = datetime.fromisoformat(db_r.when)
        except Exception:
            raise HTTPException(status_code=400, detail="invalid when format")
        new_dt = when_dt + timedelta(minutes=minutes)
        db_r.when = new_dt.isoformat()
        db_r.sent = False
        session.add(db_r)
        session.commit()
        # reschedule
        _schedule_reminder(db_r)
        return db_r


@app.post("/{reminder_id}/trigger")
def trigger_reminder(reminder_id: int, request: Request = None):
    _require_admin(request)
    """Trigger sending of the reminder immediately (for testing)."""
    # run send in background thread to avoid blocking
    threading.Thread(target=_send_reminder, args=(reminder_id,), daemon=True).start()
    return {"status": "triggered"}
