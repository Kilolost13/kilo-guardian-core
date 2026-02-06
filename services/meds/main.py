import os
import sys
import asyncio
import uuid
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import Response
from PIL import Image
from io import BytesIO
import httpx
from sqlmodel import Session, select, create_engine
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Add shared directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from shared.models import Med, OcrJob
from shared.utils.ocr import preprocess_image_for_ocr, parse_frequency, parse_times

# Use shared database path from PVC
db_url = os.getenv("DATABASE_URL", "sqlite:////app/kilo_data/kilo_guardian.db")
engine = create_engine(db_url, connect_args={"check_same_thread": False})

IMAGE_STORAGE_DIR = Path("/app/kilo_data/prescription_images")

app = FastAPI(title="Kilo Meds Service")

@app.on_event("startup")
async def startup():
    IMAGE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def list_meds():
    with Session(engine) as session:
        return session.exec(select(Med)).all()

@app.post("/extract")
async def extract_med(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    job_id = str(uuid.uuid4())
    img_bytes = await file.read()
    image = Image.open(BytesIO(img_bytes))
    
    # Save for record
    path = IMAGE_STORAGE_DIR / f"{job_id}.jpg"
    image.save(path)

    with Session(engine) as session:
        job = OcrJob(job_id=job_id, status="pending", image_path=str(path))
        session.add(job)
        session.commit()

    background_tasks.add_task(process_med_ocr, job_id)
    return {"job_id": job_id, "status": "pending"}

async def process_med_ocr(job_id: str):
    # This would call AI Brain or run local Tesseract using shared.utils.ocr
    # Simplified for brevity in this step
    pass

@app.post("/add")
def add_med(med: Med):
    with Session(engine) as session:
        session.add(med)
        session.commit()
        session.refresh(med)
        return med