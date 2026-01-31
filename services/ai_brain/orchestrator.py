from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from datetime import datetime, timedelta
# Import models lazily via helper to avoid import-order circular issues during tests
from .db import get_session, init_db

def _get_model(name: str):
    try:
        import importlib
        mod = importlib.import_module("ai_brain.models")
        return getattr(mod, name, None)
    except Exception:
        return None

from pydantic import BaseModel
from typing import Optional, List
import httpx
import os
import json
from sqlmodel import select

router = APIRouter()
REMINDER_URL = os.environ.get("REMINDER_URL", "http://reminder:9002")
K3S_MANAGER_URL = os.environ.get("K3S_MANAGER_URL", "http://localhost:9011")

# Simple DTOs for incoming requests
class SedentaryCreate(BaseModel):
    user_id: str

class CamReportDTO(BaseModel):
    # make user_id optional for backward compatibility with test clients
    user_id: Optional[str] = None
    face_id: Optional[str] = None
    posture: str
    timestamp: Optional[datetime] = None
    location_hash: Optional[str] = None
    image_id: Optional[str] = None
    # extra fields from camera pipeline that some clients send
    pose_match: Optional[bool] = None
    mse: Optional[float] = None

class MedUploadDTO(BaseModel):
    user_id: str
    med_name: str
    dosage: Optional[str] = None
    schedule_text: Optional[str] = None

class MedConfirmDTO(BaseModel):
    user_id: str
    med_id: int
    taken: bool

class UserSettingsDTO(BaseModel):
    opt_out_camera: Optional[bool] = None
    opt_out_habits: Optional[bool] = None

# --- Cluster Management (The "Long Arms") ---

@router.get("/cluster/status")
async def get_cluster_status():
    """Oversee the health of the HP cluster"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{K3S_MANAGER_URL}/cluster/status")
            r.raise_for_status()
            return r.json()
    except Exception as e:
        return {"status": "unreachable", "error": str(e), "manager_url": K3S_MANAGER_URL}

@router.get("/cluster/services")
async def get_cluster_services():
    """List services running on the HP 'body'"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{K3S_MANAGER_URL}/services")
            r.raise_for_status()
            return r.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"K3s Manager unreachable: {str(e)}")

# Utility: call reminder service to create a reminder
async def create_reminder(text: str, when_dt: datetime):
    payload = {"text": text, "when": when_dt.isoformat()}
    try:
        # include callback URL and hint for the reminder service
        cb = os.environ.get('AI_BRAIN_CALLBACK_URL')
        headers = {}
        if cb:
            payload['_callback'] = cb.rstrip('/') + '/reminder/callback'
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(f"{REMINDER_URL}/", json=payload, headers=headers)
            r.raise_for_status()
            return r.json().get("id") or r.json().get("id")
    except Exception as e:
        print("Failed to create reminder:", e)
        return None


@router.post('/reminder/callback')
async def reminder_callback(request: Request):
    """Receive reminder-sent callbacks from the reminder service.
    Verifies the HMAC signature if CALLBACK_SECRET is configured."""
    body = await request.body()
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    # verify signature
    sig = request.headers.get('X-Callback-Signature')
    secret = os.environ.get('CALLBACK_SECRET')
    if secret and sig:
        import hmac, hashlib
        computed = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(computed, sig):
            raise HTTPException(status_code=401, detail="Invalid signature")
    rid = payload.get('id') or payload.get('reminder_id') or payload.get('reminderId')
    text = payload.get('text') or payload.get('reminder_text')
    when = payload.get('when')
    with get_session() as session:
        SentReminder = _get_model('SentReminder')
        if SentReminder is None:
            raise HTTPException(status_code=500, detail='Model SentReminder not available')
        sr = SentReminder(reminder_id=rid, reminder_text=text, when=when)
        session.add(sr)
        session.commit()
    return {"status":"ok"}


def get_user_settings(session, user_id: str):
    from .models import UserSettings
    stmt = select(UserSettings).where(UserSettings.user_id == user_id)
    res = session.exec(stmt).first()
    return res


def upsert_user_settings(session, user_id: str, opts: dict):
    from .models import UserSettings
    s = get_user_settings(session, user_id)
    if not s:
        s = UserSettings(user_id=user_id, opt_out_camera=opts.get('opt_out_camera', False), opt_out_habits=opts.get('opt_out_habits', False))
        session.add(s)
    else:
        if 'opt_out_camera' in opts and opts['opt_out_camera'] is not None:
            s.opt_out_camera = opts['opt_out_camera']
        if 'opt_out_habits' in opts and opts['opt_out_habits'] is not None:
            s.opt_out_habits = opts['opt_out_habits']
        session.add(s)
    session.commit()
    session.refresh(s)
    return s

# Note: router-level startup handlers are deprecated; initialization at import
# time (idempotent) is used below to ensure schema exists in tests.

# Also ensure tables exist at import time as a fallback for environments
# where the FastAPI lifespan startup event may not run before the first
# request (some test collectors import modules in ways that delay startup).
# init_db is idempotent and will drop/create when using the in-memory DB.
try:
    init_db()
except Exception as e:
    # Log but don't fail import — tests will fail later if DB unusable
    print(f"init_db failed: {e}")

@router.post("/reminder/sedentary")
async def create_sedentary(s: SedentaryCreate):
    # Create sedentary state and schedule reminders at +1h, +2h, +3h
    with get_session() as session:
        # check user opt-out for camera tracking
        us = get_user_settings(session, s.user_id)
        if us and us.opt_out_camera:
            return {"status":"opted_out"}
        now = datetime.utcnow()
        SedentaryState = _get_model('SedentaryState')
        if SedentaryState is None:
            raise HTTPException(status_code=500, detail='Model SedentaryState not available')
        state = SedentaryState(user_id=s.user_id, start_time=now, last_movement=now, reminder_count=0, active=True, returned_after_reminder_count=0)
        session.add(state)
        session.commit()
        session.refresh(state)
        # schedule reminders
        reminder_ids = []
        for hrs in (1,2,3):
            when = now + timedelta(hours=hrs)
            rid = await create_reminder(f"Sedentary reminder for {s.user_id}: been sitting for {hrs} hour(s)", when)
            if rid:
                reminder_ids.append(rid)
        # store reminder ids as JSON string (reminder service may be unavailable in tests)
        state.reminder_ids_json = json.dumps(reminder_ids)
        session.add(state)
        session.commit()
        return {"status":"ok","state_id": state.id, "reminder_ids": reminder_ids}

@router.post("/ingest/cam")
async def ingest_cam(report: CamReportDTO):
    # Save cam report and update sedentary state(s)
    with get_session() as session:
        # check opt-out
        uid = report.user_id or os.environ.get('DEFAULT_USER_ID') or 'unknown'
        us = get_user_settings(session, uid)
        if us and us.opt_out_camera:
            return {"status":"opted_out", "feedback": "camera tracking opted out"}
        # ensure timestamp
        ts = report.timestamp or datetime.utcnow()
        CamReport = _get_model('CamReport')
        if CamReport is None:
            raise HTTPException(status_code=500, detail='Model CamReport not available')
        cr = CamReport(user_id=uid, face_id=report.face_id, posture=report.posture, timestamp=ts, location_hash=report.location_hash, image_id=report.image_id)
        session.add(cr)
        session.commit()
        # Find active sedentary session for user
        SedentaryState = _get_model('SedentaryState')
        if SedentaryState is None:
            raise HTTPException(status_code=500, detail='Model SedentaryState not available')
        stmt = select(SedentaryState).where(SedentaryState.user_id == report.user_id, SedentaryState.active == True)
        res = session.exec(stmt).all()
        if not res:
            # offer lightweight feedback even when no sedentary session exists
            fb = f"Detected posture: {report.posture}"
            return {"status":"ok","msg":"no active sedentary session", "feedback": fb}
        state = res[-1]
        prev_last = state.last_movement
        # Update last_movement if posture indicates movement
        if report.posture != 'sitting':
            # movement recorded — update last_movement and check if there were any
            # reminders previously sent for this session so we can increment
            # returned_after_reminder_count when appropriate.
            state.last_movement = report.timestamp
            # check sent reminders table for any reminder ids associated with this state
            SentReminder = _get_model('SentReminder')
            sent = []
            try:
                if state.reminder_ids_json and SentReminder is not None:
                    rids = json.loads(state.reminder_ids_json)
                    if rids:
                        stmt = select(SentReminder).where(SentReminder.reminder_id.in_(rids))
                        sent = session.exec(stmt).all()
            except Exception:
                sent = []
            if sent:
                state.returned_after_reminder_count = state.returned_after_reminder_count + 1
            session.add(state)
            session.commit()
            fb = "Great job standing up!" if report.posture == 'standing' else f"Movement recorded: {report.posture}"
            return {"status":"ok","msg":"movement recorded","returned_after_reminder_count": state.returned_after_reminder_count, "feedback": fb}
        else:
            # posture == sitting
            # detect return after reminder: count reminders in state.reminder_ids that are past and assume they were fired
            now = datetime.utcnow()
            returned_count = 0
            # check any stored reminder ids (we persist as JSON)
            try:
                if state.reminder_ids_json:
                    rids = json.loads(state.reminder_ids_json)
                else:
                    rids = []
                if rids:
                    try:
                        async with httpx.AsyncClient(timeout=5.0) as client:
                            r = await client.get(f"{REMINDER_URL}/")
                            reminders = r.json()
                            # map id->sent
                            sent_map = {str(rem.get('id')): rem.get('sent') for rem in reminders}
                            for rid in rids:
                                rid_s = str(rid)
                                if rid_s in sent_map and sent_map[rid_s]:
                                    # placeholder for future logic
                                    pass
                    except Exception:
                        pass
            except Exception:
                pass
            # no detailed returned detection for now; just update last_movement
            session.add(state)
            session.commit()
            fb = f"Detected posture: {report.posture}"
            return {"status":"ok","msg":"sitting noted", "feedback": fb}

@router.post("/meds/upload")
async def meds_upload(payload: MedUploadDTO):
    with get_session() as session:
        # very simple schedule parser: find times like HH:MM
        times = []
        if payload.schedule_text:
            import re
            matches = re.findall(r"(\d{1,2}:\d{2})", payload.schedule_text)
            times = matches
        MedRecord = _get_model('MedRecord')
        if MedRecord is None:
            raise HTTPException(status_code=500, detail='Model MedRecord not available')
        med = MedRecord(user_id=payload.user_id, name=payload.med_name, dosage=payload.dosage, schedule=times)
        session.add(med)
        session.commit()
        session.refresh(med)
        reminder_ids = []
        now = datetime.utcnow()
        for t in times:
            hh, mm = [int(x) for x in t.split(":")]
            when = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if when < now:
                when = when + timedelta(days=1)
            rid = await create_reminder(f"Take {med.name} ({med.dosage or ''})", when)
            if rid:
                reminder_ids.append(rid)
        return {"status":"ok","med_id": med.med_id, "reminders": reminder_ids}

@router.post("/reminder/meds/confirm")
def meds_confirm(c: MedConfirmDTO):
    with get_session() as session:
        MedAdherence = _get_model('MedAdherence')
        if MedAdherence is None:
            raise HTTPException(status_code=500, detail='Model MedAdherence not available')
        adherence = MedAdherence(med_id=c.med_id, user_id=c.user_id, timestamp=datetime.utcnow(), taken=c.taken)
        session.add(adherence)
        session.commit()
        return {"status":"ok"}


@router.post('/user/{user_id}/settings')
def set_user_settings(user_id: str, settings: UserSettingsDTO):
    with get_session() as session:
        opts = settings.model_dump()
        s = upsert_user_settings(session, user_id, opts)
        return {"status":"ok","settings": {"opt_out_camera": s.opt_out_camera, "opt_out_habits": s.opt_out_habits}}

@router.get('/user/{user_id}/settings')
def get_settings(user_id: str):
    with get_session() as session:
        s = get_user_settings(session, user_id)
        if not s:
            return {"user_id": user_id, "opt_out_camera": False, "opt_out_habits": False}
        return {"user_id": user_id, "opt_out_camera": s.opt_out_camera, "opt_out_habits": s.opt_out_habits}

@router.post("/events")
async def log_event(evt: dict):
    # accept generic habit events
    with get_session() as session:
        ts = evt.get('timestamp') or datetime.utcnow()
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts)
            except Exception:
                ts = datetime.utcnow()
        HabitEvent = _get_model('HabitEvent')
        if HabitEvent is None:
            raise HTTPException(status_code=500, detail='Model HabitEvent not available')
        he = HabitEvent(user_id=evt.get('user_id'), event_type=evt.get('event_type'), timestamp=ts)
        session.add(he)
        session.commit()
        # after storing, compute profile and detect anomalies
        profiles = []
        stmt = select(HabitEvent).where(HabitEvent.user_id == evt.get('user_id'))
        evts = session.exec(stmt).all()
        from collections import defaultdict
        import statistics
        groups = defaultdict(list)
        for e in evts:
            # exclude the event we just stored (he) from the profile computation so
            # anomaly detection compares the new event against the historical baseline
            try:
                if e.id == he.id:
                    continue
            except Exception:
                pass
            secs = e.timestamp.hour*3600 + e.timestamp.minute*60 + e.timestamp.second
            groups[e.event_type].append(secs)
        # compute for this event_type only using a persisted profile if available
        etype = evt.get('event_type')
        seq = groups.get(etype, [])
        data_points = len(seq)
        # fetch existing profile if present
        HabitProfile = _get_model('HabitProfile')
        if HabitProfile is None:
            raise HTTPException(status_code=500, detail='Model HabitProfile not available')
        prof_stmt = select(HabitProfile).where(HabitProfile.user_id == evt.get('user_id'), HabitProfile.event_type == etype)
        prof = session.exec(prof_stmt).first()
        if prof:
            mean = prof.mean_seconds
            std = prof.stddev_seconds
            confidence = prof.confidence
        else:
            # allow profile creation when there are at least 2 historical points
            # so that the third incoming event can establish a baseline
            if data_points >= 2:
                mean = statistics.mean(seq)
                std = statistics.pstdev(seq) if data_points>1 else 0.0
                confidence = min(1.0, (data_points+1)/7.0)
                # persist profile
                hp = HabitProfile(user_id=evt.get('user_id'), event_type=etype, mean_seconds=mean, stddev_seconds=std, frequency_per_week=(data_points/7.0), data_points=data_points, confidence=confidence)
                session.add(hp)
                session.commit()
                prof = hp
            else:
                prof = None

        # detection: use profile if it exists
        # Default threshold set lower for quicker detection in low-data scenarios;
        # can be tuned via HABIT_CONFIDENCE_THRESHOLD env var in production.
        threshold = float(os.environ.get('HABIT_CONFIDENCE_THRESHOLD', '0.4'))
        if prof and prof.confidence >= threshold:
            cur_secs = he.timestamp.hour*3600 + he.timestamp.minute*60 + he.timestamp.second
            if prof.stddev_seconds and (cur_secs < prof.mean_seconds - 2*prof.stddev_seconds or cur_secs > prof.mean_seconds + 2*prof.stddev_seconds):
                # check user opt-out for habits
                us = get_user_settings(session, evt.get('user_id'))
                if not (us and us.opt_out_habits):
                    # create a gentle check-in reminder
                    when = datetime.utcnow() + timedelta(minutes=1)
                    await create_reminder(f"We noticed a change in your {etype} pattern. Are you okay?", when)
        return {"status":"ok"}

@router.get("/user/{user_id}/habits")
def get_habits(user_id: str):
    # build simple profiles per event_type
    with get_session() as session:
        HabitEvent = _get_model('HabitEvent')
        if HabitEvent is None:
            raise HTTPException(status_code=500, detail='Model HabitEvent not available')
        stmt = select(HabitEvent).where(HabitEvent.user_id == user_id)
        evts = session.exec(stmt).all()
        if not evts:
            return {"user_id": user_id, "profiles": []}
        from collections import defaultdict
        import statistics
        groups = defaultdict(list)
        for e in evts:
            secs = e.timestamp.hour*3600 + e.timestamp.minute*60 + e.timestamp.second
            groups[e.event_type].append(secs)
        profiles = []
        for etype, seq in groups.items():
            data_points = len(seq)
            mean = statistics.mean(seq)
            std = statistics.pstdev(seq) if data_points>1 else 0.0
            freq = data_points/7.0
            confidence = min(1.0, data_points/7.0)
            prof = {
                "user_id": user_id,
                "event_type": etype,
                "mean_seconds": mean,
                "stddev_seconds": std,
                "frequency_per_week": freq,
                "data_points": data_points,
                "confidence": confidence
            }
            profiles.append(prof)
        return {"user_id": user_id, "profiles": profiles}