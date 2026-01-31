from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import Response
from PIL import Image, ImageEnhance, ImageFilter
from io import BytesIO
import pytesseract
import re
from sqlmodel import SQLModel, create_engine, Session, Field
from typing import Optional, List
import os
import httpx
import numpy as np
import cv2
import uuid
import json
from pathlib import Path
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Med model definition
from datetime import datetime

class Med(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    schedule: str
    dosage: str
    quantity: int = 0
    prescriber: str = ""
    instructions: str = ""
    last_taken: Optional[str] = None  # ISO format datetime string
    taken_count: int = 0  # Track how many times taken
    frequency_per_day: int = 1
    times: Optional[str] = None  # comma-separated HH:MM
    from_ocr: bool = False
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class OcrJob(SQLModel, table=True):
    """Track OCR processing jobs for async processing"""
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: str = Field(index=True, unique=True)  # UUID for tracking
    status: str = Field(default="pending")  # pending, processing, completed, failed
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    image_path: str = ""  # Path to saved image
    ocr_text: Optional[str] = None  # Raw OCR output
    error_message: Optional[str] = None
    medication_id: Optional[int] = None  # ID of created medication if successful
    result_data: Optional[str] = None  # JSON string of result data

db_url = "sqlite:////data/meds.db"
engine = create_engine(db_url, echo=False)

# Image storage directory
IMAGE_STORAGE_DIR = Path("/data/prescription_images")
IMAGE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def _ensure_columns():
    """Best-effort SQLite schema migrator for newly added med fields."""
    try:
        with engine.connect() as conn:
            cols = conn.execute("PRAGMA table_info(med)").fetchall()
            names = {c[1] for c in cols}
            if 'frequency_per_day' not in names:
                conn.execute("ALTER TABLE med ADD COLUMN frequency_per_day INTEGER DEFAULT 1")
            if 'times' not in names:
                conn.execute("ALTER TABLE med ADD COLUMN times VARCHAR")
            if 'from_ocr' not in names:
                conn.execute("ALTER TABLE med ADD COLUMN from_ocr BOOLEAN DEFAULT 0")
            if 'created_at' not in names:
                conn.execute("ALTER TABLE med ADD COLUMN created_at VARCHAR")
    except Exception as e:
        print("[MEDS] Schema check failed (non-fatal):", e)

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        os.makedirs("/data", exist_ok=True)
        IMAGE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        SQLModel.metadata.create_all(engine)
        _ensure_columns()
    except Exception:
        pass
    yield


app = FastAPI(title="Meds OCR Service", lifespan=lifespan)

# Health check endpoints
@app.get("/status")
@app.get("/health")
def status():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

AI_BRAIN_URL = os.getenv("AI_BRAIN_URL", "http://ai_brain:9004/ingest/meds")
AI_EVENT_URL = os.getenv("AI_EVENT_URL", "http://ai_brain:9004/ingest/event")
REMINDER_BASE = os.getenv("REMINDER_URL", "http://reminder:8000")
REMINDER_SERIES_URL = os.getenv("REMINDER_SERIES_URL", f"{REMINDER_BASE.rstrip('/')}/series")
HABITS_BASE = os.getenv("HABITS_URL", "http://habits:8000")
HABITS_ADHERENCE_URL = os.getenv("HABITS_ADHERENCE_URL", f"{HABITS_BASE.rstrip('/')}/med-adherence")
HABITS_LOG_URL = os.getenv("HABITS_LOG_URL", f"{HABITS_BASE.rstrip('/')}/log")

RETRY_COUNT = int(os.getenv("HTTP_RETRY_COUNT", "2"))
RETRY_DELAY = float(os.getenv("HTTP_RETRY_DELAY", "0.3"))
CB_FAIL_THRESHOLD = int(os.getenv("HTTP_CB_FAILS", "5"))
CB_COOLDOWN = float(os.getenv("HTTP_CB_COOLDOWN", "15"))

_cb_state = {"open_until": 0.0, "fail_count": 0}
SERVICE_NAME = "meds"

cb_failures = Counter("cb_failures_total", "Circuit breaker failures", ["service", "target"])
cb_skips = Counter("cb_skips_total", "Calls skipped due to open circuit", ["service", "target"])
cb_success = Counter("cb_success_total", "Successful downstream calls", ["service", "target"])
cb_open_gauge = Gauge("cb_open", "Circuit breaker open (1=open)", ["service"])
cb_open_until_gauge = Gauge("cb_open_until", "Circuit open until timestamp", ["service"])
cb_open_gauge.labels(SERVICE_NAME).set(0)
cb_open_until_gauge.labels(SERVICE_NAME).set(0)


async def _post_json_with_retry(url: str, payload: dict, tag: str, retries: int = None, timeout: float = 5.0):
    global _cb_state
    retries = RETRY_COUNT if retries is None else retries
    now = asyncio.get_event_loop().time()
    if _cb_state["open_until"] > now:
        print(f"[{tag}] circuit open; skipping call to {url}")
        cb_skips.labels(SERVICE_NAME, tag).inc()
        cb_open_gauge.labels(SERVICE_NAME).set(1)
        cb_open_until_gauge.labels(SERVICE_NAME).set(_cb_state["open_until"])
        return False

    last_error = None
    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(retries + 1):
            try:
                resp = await client.post(url, json=payload)
                if resp.status_code < 400:
                    _cb_state["fail_count"] = 0
                    cb_success.labels(SERVICE_NAME, tag).inc()
                    cb_open_gauge.labels(SERVICE_NAME).set(0)
                    cb_open_until_gauge.labels(SERVICE_NAME).set(0)
                    return True
                last_error = f"status {resp.status_code}: {resp.text}"
            except Exception as e:
                last_error = str(e)
            await asyncio.sleep(RETRY_DELAY * (attempt + 1))

    # record failure and possibly open circuit
    _cb_state["fail_count"] += 1
    cb_failures.labels(SERVICE_NAME, tag).inc()
    if _cb_state["fail_count"] >= CB_FAIL_THRESHOLD:
        _cb_state["open_until"] = now + CB_COOLDOWN
        cb_open_gauge.labels(SERVICE_NAME).set(1)
        cb_open_until_gauge.labels(SERVICE_NAME).set(_cb_state["open_until"])
        print(f"[{tag}] circuit opened for {CB_COOLDOWN}s after failures")

    if last_error:
        print(f"[{tag}] failed after retries: {last_error}")
    return False

# startup handled by lifespan

@app.get("/")
def list_meds():
    with Session(engine) as session:
        meds = session.query(Med).all()
        return meds

def preprocess_image_for_ocr(image: Image.Image) -> Image.Image:
    """
    Preprocess image to improve OCR accuracy:
    - Convert to grayscale
    - Enhance contrast
    - Apply denoising
    - Apply adaptive thresholding
    - Upscale for better character recognition
    """
    # Convert PIL image to numpy array
    img_array = np.array(image)

    # Convert to grayscale
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array

    # Upscale image 2x for better OCR (helps with small text)
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    # Denoise
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

    # Apply adaptive thresholding to handle varying lighting
    thresh = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )

    # Morphological operations to clean up noise
    kernel = np.ones((1, 1), np.uint8)
    cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    # Convert back to PIL Image
    return Image.fromarray(cleaned)


def _parse_frequency(text: str) -> int:
    # Look for patterns like "2x/day", "twice daily", "every 8 hours"
    try:
        text_lower = text.lower()
        m = re.search(r"(\d+)\s*x\s*/?\s*day", text_lower)
        if m:
            return max(1, int(m.group(1)))
        if "twice daily" in text_lower or "two times a day" in text_lower:
            return 2
        if "three times" in text_lower:
            return 3
        every_hours = re.search(r"every\s+(\d+)\s*hour", text_lower)
        if every_hours:
            hours = int(every_hours.group(1))
            if hours > 0:
                return max(1, round(24 / hours))
    except Exception:
        pass
    return 1


def _parse_times(text: str) -> List[str]:
    times = re.findall(r"\b(\d{1,2}:\d{2})\s*(?:am|pm|AM|PM)?\b", text)
    # Normalize to HH:MM 24h if am/pm present is missing; keep as-is for now
    return [t.strip() for t in times]


def _med_times_list(med: Med) -> List[str]:
    if med.times:
        return [t.strip() for t in med.times.split(',') if t.strip()]
    # fallback: try to pull HH:MM from schedule text
    matches = re.findall(r"\b(\d{1,2}:\d{2})\b", med.schedule or "")
    return matches or []


async def _fan_out_med(med: Med):
    """Notify reminder, habits, and AI Brain about a med change (best-effort)."""
    payload_times = _med_times_list(med)
    # Reminders: create/update series
    await _post_json_with_retry(REMINDER_SERIES_URL, {
        "med_id": med.id,
        "name": med.name,
        "frequency_per_day": med.frequency_per_day,
        "times": payload_times,
        "start_date": med.created_at,
        "schedule": med.schedule,
    }, tag="MEDS->REMINDER")

    # Habits: upsert med adherence
    await _post_json_with_retry(HABITS_ADHERENCE_URL, {
        "med_id": med.id,
        "name": med.name,
        "target_per_day": med.frequency_per_day,
        "times": payload_times,
    }, tag="MEDS->HABITS")

    # AI Brain event log
    await _post_json_with_retry(AI_EVENT_URL, {
        "type": "med.prescribed",
        "source": "meds",
        "destination": ["reminder", "habits"],
        "payload": {
            "med_id": med.id,
            "name": med.name,
            "frequency_per_day": med.frequency_per_day,
            "times": payload_times,
            "from_ocr": med.from_ocr,
        }
    }, tag="MEDS->AI")

def process_ocr_job(job_id: str):
    """Background worker to process OCR job via AI Brain's intelligent analysis"""
    with Session(engine) as session:
        job = session.query(OcrJob).filter(OcrJob.job_id == job_id).first()
        if not job:
            print(f"[OCR] Job {job_id} not found")
            return

        try:
            # Update status to processing
            job.status = "processing"
            session.add(job)
            session.commit()

            print(f"[OCR] Starting processing for job {job_id}")

            # Load image from disk
            image_path = Path(job.image_path)
            if not image_path.exists():
                raise FileNotFoundError(f"Image not found: {image_path}")

            print(f"[OCR] Sending to AI Brain for intelligent analysis...")

            # Send to AI Brain's /analyze/prescription endpoint (with LLM parsing)
            import httpx
            with open(image_path, 'rb') as img_file:
                files = {'image': ('prescription.jpg', img_file, 'image/jpeg')}

                # Call AI Brain with timeout (synchronous for background worker)
                with httpx.Client(timeout=300.0) as client:
                    response = client.post(
                        "http://kilo-ai-brain:9004/analyze/prescription",
                        files=files
                    )

                    if response.status_code != 200:
                        raise Exception(f"AI Brain returned {response.status_code}: {response.text}")

                    result = response.json()
                    print(f"[OCR] AI Brain analysis complete: {result.get('success', False)}")

                    if not result.get('success'):
                        raise Exception(result.get('error', 'Analysis failed'))

                    # Extract medication data from AI Brain's LLM-parsed response
                    ocr_text = result.get('ocr_text', '')
                    med_data = result.get('parsed_data', {})

                    job.ocr_text = ocr_text
                    session.add(job)
                    session.commit()

            # Parse frequency/times from schedule if available
            schedule_text = med_data.get('schedule', '')
            freq = _parse_frequency(schedule_text) if schedule_text else 1
            times = _parse_times(schedule_text) if schedule_text else None

            # Create medication from AI-extracted data
            med = Med(
                name=med_data.get('medication_name') or med_data.get('name') or 'Unknown Medication',
                dosage=med_data.get('dosage', ''),
                schedule=schedule_text,
                quantity=0,  # AI Brain doesn't extract quantity yet
                prescriber=med_data.get('prescriber', ''),
                instructions=med_data.get('instructions', ''),
                frequency_per_day=freq,
                times=",".join(times) if times else None,
                from_ocr=True,
            )

            # Save medication to database
            session.add(med)
            session.commit()
            session.refresh(med)

            print(f"[OCR] Created medication via AI Brain: {med.name} (ID: {med.id})")

            # Update job with success
            job.status = "completed"
            job.completed_at = datetime.utcnow().isoformat()
            job.medication_id = med.id
            job.result_data = json.dumps({
                "id": med.id,
                "name": med.name,
                "schedule": med.schedule,
                "dosage": med.dosage,
                "quantity": med.quantity,
                "prescriber": med.prescriber,
                "instructions": med.instructions
            })
            session.add(job)
            session.commit()

            print(f"[OCR] Job {job_id} completed successfully")

            # Send to AI brain asynchronously (fire and forget)
            import asyncio
            try:
                asyncio.create_task(_send_to_ai_brain(med))
                asyncio.create_task(_fan_out_med(med))
            except:
                pass

        except Exception as e:
            print(f"[OCR] Job {job_id} failed: {e}")
            import traceback
            traceback.print_exc()
            job.status = "failed"
            job.completed_at = datetime.utcnow().isoformat()
            job.error_message = str(e)
            session.add(job)
            session.commit()

@app.post("/extract")
async def extract_med_from_image(
    file: UploadFile = File(None),
    files: List[UploadFile] = File(None),
    background_tasks: BackgroundTasks = None
):
    """
    Submit prescription image for OCR processing.
    Returns immediately with job_id for polling status.
    """
    # Generate unique job ID
    job_id = str(uuid.uuid4())

    try:
        # Handle multiple images (stitch) or single image
        if files and len(files) > 0:
            # Multiple images - stitch them horizontally
            images = []
            for f in files:
                if not f.content_type.startswith("image/"):
                    continue
                img_bytes = f.file.read()
                img = Image.open(BytesIO(img_bytes))
                images.append(img)

            if len(images) == 0:
                raise HTTPException(status_code=400, detail="No valid images provided.")

            # Stitch images horizontally
            widths, heights = zip(*(i.size for i in images))
            total_width = sum(widths)
            max_height = max(heights)
            final_image = Image.new('RGB', (total_width, max_height))
            x_offset = 0
            for img in images:
                final_image.paste(img, (x_offset, 0))
                x_offset += img.width

        elif file:
            # Single image
            if not file.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="File must be an image.")
            img_bytes = file.file.read()
            final_image = Image.open(BytesIO(img_bytes))
        else:
            raise HTTPException(status_code=400, detail="No image provided.")

        # Save image to disk
        image_path = IMAGE_STORAGE_DIR / f"{job_id}.jpg"
        final_image.save(image_path, "JPEG", quality=95)

        print(f"[OCR] Saved image for job {job_id} to {image_path}")

        # Create job record
        job = OcrJob(
            job_id=job_id,
            status="pending",
            image_path=str(image_path)
        )

        with Session(engine) as session:
            session.add(job)
            session.commit()

        # Queue background processing
        if background_tasks:
            background_tasks.add_task(process_ocr_job, job_id)
        else:
            # Fallback for testing
            import asyncio
            asyncio.create_task(asyncio.to_thread(process_ocr_job, job_id))

        print(f"[OCR] Queued job {job_id} for processing")

        return {
            "job_id": job_id,
            "status": "pending",
            "message": "Image received. Processing in background...",
            "poll_url": f"/extract/{job_id}/status"
        }

    except Exception as e:
        print(f"[OCR] Error creating job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process image: {str(e)}")

@app.get("/extract/{job_id}/status")
def get_job_status(job_id: str):
    """Get status of OCR job"""
    with Session(engine) as session:
        job = session.query(OcrJob).filter(OcrJob.job_id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        response = {
            "job_id": job.job_id,
            "status": job.status,
            "created_at": job.created_at,
            "completed_at": job.completed_at
        }

        if job.status == "completed":
            # Include result data
            if job.result_data:
                response["result"] = json.loads(job.result_data)
            response["ocr_text"] = job.ocr_text
        elif job.status == "failed":
            response["error"] = job.error_message

        return response

@app.get("/extract/{job_id}/result")
def get_job_result(job_id: str):
    """Get result of completed OCR job"""
    with Session(engine) as session:
        job = session.query(OcrJob).filter(OcrJob.job_id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.status == "pending" or job.status == "processing":
            raise HTTPException(status_code=202, detail="Job still processing")

        if job.status == "failed":
            raise HTTPException(status_code=500, detail=job.error_message or "OCR processing failed")

        if job.status == "completed":
            result = json.loads(job.result_data) if job.result_data else {}
            result["ocr_text"] = job.ocr_text
            return result

        raise HTTPException(status_code=500, detail="Unknown job status")

@app.put("/{med_id}")
def update_med(med_id: int, med: Med, background_tasks: BackgroundTasks = None):
    with Session(engine) as session:
        db_med = session.get(Med, med_id)
        if not db_med:
            raise HTTPException(status_code=404, detail="Medication not found")
        db_med.name = med.name
        db_med.dosage = med.dosage
        db_med.schedule = med.schedule
        db_med.quantity = med.quantity
        db_med.prescriber = med.prescriber
        db_med.instructions = med.instructions
        db_med.frequency_per_day = med.frequency_per_day or 1
        db_med.times = med.times or db_med.times
        session.add(db_med)
        session.commit()
        session.refresh(db_med)
    if background_tasks:
        background_tasks.add_task(_send_to_ai_brain, db_med)
        background_tasks.add_task(_fan_out_med, db_med)
    else:
        import asyncio
        asyncio.create_task(_send_to_ai_brain(db_med))
        asyncio.create_task(_fan_out_med(db_med))
    return db_med

@app.post("/add")
def add_med(med: Med, background_tasks: BackgroundTasks = None):
    with Session(engine) as session:
        if not med.created_at:
            med.created_at = datetime.utcnow().isoformat()
        if not med.frequency_per_day:
            med.frequency_per_day = 1
        if not med.times:
            med.times = ",".join(_parse_times(med.schedule)) if med.schedule else med.times
        session.add(med)
        session.commit()
        session.refresh(med)
    # Send to ai_brain
    if background_tasks:
        background_tasks.add_task(_send_to_ai_brain, med)
        background_tasks.add_task(_fan_out_med, med)
    else:
        import asyncio
        asyncio.create_task(_send_to_ai_brain(med))
        asyncio.create_task(_fan_out_med(med))
    return med

@app.delete("/{med_id}")
def delete_med(med_id: int):
    with Session(engine) as session:
        med = session.get(Med, med_id)
        if not med:
            raise HTTPException(status_code=404, detail="Medication not found")
        session.delete(med)
        session.commit()
    return {"status": "deleted"}

@app.post("/{med_id}/take")
def mark_med_taken(med_id: int):
    """Mark a medication as taken right now"""
    with Session(engine) as session:
        med = session.get(Med, med_id)
        if not med:
            raise HTTPException(status_code=404, detail="Medication not found")

        # Update last taken time and increment counter
        med.last_taken = datetime.utcnow().isoformat()
        med.taken_count = (med.taken_count or 0) + 1

        session.add(med)
        session.commit()
        session.refresh(med)

    return {
        "status": "taken",
        "med_id": med.id,
        "med_name": med.name,
        "last_taken": med.last_taken,
        "taken_count": med.taken_count
    }

async def _send_to_ai_brain(med: Med):
    await _post_json_with_retry(AI_BRAIN_URL, {
        "name": med.name,
        "schedule": med.schedule,
        "dosage": med.dosage,
        "quantity": med.quantity,
        "prescriber": med.prescriber,
        "instructions": med.instructions,
        "frequency_per_day": med.frequency_per_day,
        "times": _med_times_list(med),
        "from_ocr": med.from_ocr,
        "created_at": med.created_at,
    }, tag="MEDS->AI")
