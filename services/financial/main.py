import os
import sys
import datetime
from pathlib import Path
from typing import Optional, List, Dict

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from sqlmodel import Session, select, create_engine
from PIL import Image
from io import BytesIO
import httpx

# Add shared directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from shared.models import Transaction, ReceiptItem, Budget, Goal, IngestedDocument
from shared.utils.ocr import preprocess_image_for_ocr, parse_receipt_items, categorize_finance_item

db_url = os.getenv("DATABASE_URL", "sqlite:////app/kilo_data/kilo_guardian.db")
engine = create_engine(db_url, connect_args={"check_same_thread": False})

app = FastAPI(title="Kilo Financial Service")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/transactions")
def list_transactions():
    with Session(engine) as session:
        return session.exec(select(Transaction)).all()

@app.post("/transaction")
def add_transaction(tx: Transaction):
    with Session(engine) as session:
        session.add(tx)
        session.commit()
        session.refresh(tx)
        return tx

@app.post("/receipt")
async def upload_receipt(file: UploadFile = File(...)):
    img_bytes = await file.read()
    image = Image.open(BytesIO(img_bytes))
    
    # Use centralized OCR utility
    processed_img = preprocess_image_for_ocr(image)
    # (In real implementation, call tesseract here or AI Brain)
    # text = pytesseract.image_to_string(processed_img)
    
    return {"status": "processing", "message": "Receipt logic consolidated"}

@app.get("/budgets")
def get_budgets():
    with Session(engine) as session:
        return session.exec(select(Budget)).all()