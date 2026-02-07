import base64
import hashlib
import os
import sys
import datetime
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from io import BytesIO

import httpx
import pytesseract
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Request, status
from fastapi.responses import JSONResponse
from PIL import Image
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlmodel import Session, select, create_engine, SQLModel

# Add shared directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from shared.models import Transaction, ReceiptItem, Budget, Goal, IngestedDocument  # noqa: E402
from shared.utils.ocr import preprocess_image_for_ocr, parse_receipt_items, categorize_finance_item  # noqa: E402
from shared.config import get_service_url  # noqa: E402

# Database setup - default to a writable location for tests/development
_default_db_path = Path(os.getenv("FINANCIAL_DB_PATH", "/tmp/kilo_financial.db"))
_default_db_path.parent.mkdir(parents=True, exist_ok=True)
db_url = os.getenv("DATABASE_URL", f"sqlite:///{_default_db_path}")
engine = create_engine(db_url, connect_args={"check_same_thread": False})

app = FastAPI(title="Kilo Financial Service")


def _categorize_item(name: str) -> str:
    lowered = (name or "").lower()
    mapping = [
        ("coffee", ["starbucks", "latte", "coffee"]),
        ("electronics", ["electronics", "tv", "laptop"]),
        ("transport", ["uber", "lyft", "trip", "taxi"]),
        ("subscription", ["subscription", "netflix", "spotify"]),
        ("fuel", ["petrol", "fuel", "gas"]),
        ("fast_food", ["mcdonald", "burger king", "kfc", "burger"]),
        ("home", ["ikea", "furniture", "table", "home"]),
        ("pharmacy", ["pharmacy", "rx", "drug"]),
        ("entertainment", ["cinema", "movie", "ticket"]),
        ("pet", ["dog", "cat", "pet"]),
        ("groceries", ["milk", "bread", "grocery"]),
    ]
    for cat, keys in mapping:
        if any(k in lowered for k in keys):
            return cat
    return categorize_finance_item(name)


def _parse_receipt_items(text: str) -> Tuple[List[Dict[str, float]], Optional[float]]:
    return parse_receipt_items(text)


def _tx_to_dict(tx: Transaction) -> Dict[str, Optional[str]]:
    return {
        "id": tx.id,
        "amount": tx.amount,
        "description": tx.description,
        "date": tx.date,
        "category": tx.category,
        "source": tx.source,
        "transaction_type": tx.transaction_type,
    }


def _authorize(request: Request) -> bool:
    token = os.getenv("ADMIN_TOKEN")
    token_list = [t.strip() for t in os.getenv("ADMIN_TOKEN_LIST", "").split(",") if t.strip()]
    header_token = request.headers.get("x-admin-token") or request.headers.get("X-Admin-Token")
    if token and header_token == token:
        return True
    if token_list and header_token in token_list:
        return True
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("basic "):
        try:
            raw = base64.b64decode(auth.split(" ", 1)[1]).decode()
            user, pw = raw.split(":", 1)
            return user == os.getenv("ADMIN_BASIC_USER") and pw == os.getenv("ADMIN_BASIC_PASS")
        except Exception:
            return False
    return token is None and not token_list and not os.getenv("ADMIN_BASIC_USER") and not os.getenv("ADMIN_BASIC_PASS")


async def _post_to_ai_brain(path: str, payload: dict) -> None:
    url = f"{get_service_url('ai_brain', use_k3s=False)}/{path.lstrip('/')}"
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload, timeout=5)
    except Exception:
        # swallow errors in background task for tests
        return


def _ensure_tables():
    try:
        SQLModel.metadata.create_all(engine)
    except Exception:
        pass


@app.on_event("startup")
def _startup():
    _ensure_tables()
    if os.getenv("ENABLE_NIGHTLY_MAINTENANCE", "false").lower() == "true":
        try:
            cron = os.getenv("NIGHTLY_CRON", "0 3 * * *")
            scheduler = BackgroundScheduler()
            scheduler.add_job(_recalculate_categories_sync, CronTrigger.from_crontab(cron))
            scheduler.start()
            app.state.scheduler = scheduler
        except Exception:
            app.state.scheduler = None


@app.on_event("shutdown")
def _shutdown():
    scheduler = getattr(app.state, "scheduler", None)
    if scheduler:
        try:
            scheduler.shutdown(wait=False)
        except Exception:
            pass


@app.get("/status")
def status_check():
    return {"status": "ok"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def list_transactions():
    with Session(engine) as session:
        return session.exec(select(Transaction)).all()


@app.post("/")
def add_transaction(tx: Transaction, background_tasks: BackgroundTasks):
    # auto categorize and determine transaction type
    tx.category = tx.category or _categorize_item(tx.description or "")
    if tx.amount is not None:
        tx.transaction_type = "income" if tx.amount >= 0 else "expense"
    with Session(engine) as session:
        session.add(tx)
        session.commit()
        session.refresh(tx)
    background_tasks.add_task(_post_to_ai_brain, "ingest/finance", {"amount": tx.amount, "description": tx.description, "date": tx.date, "category": tx.category})
    return _tx_to_dict(tx)


def _save_receipt_items(session: Session, items: List[Dict[str, float]], transaction_id: int):
    saved = []
    for it in items:
        cat = it.get("category") or _categorize_item(it.get("name", ""))
        rec = ReceiptItem(transaction_id=transaction_id, name=it.get("name", "item"), price=it.get("price", 0.0), category=cat)
        session.add(rec)
        session.commit()
        session.refresh(rec)
        saved.append(rec)
    return saved


@app.post("/receipt")
async def upload_receipt(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    img_bytes = await file.read()
    image = Image.open(BytesIO(img_bytes))
    processed_img = preprocess_image_for_ocr(image)
    text = pytesseract.image_to_string(processed_img)
    items, detected_total = _parse_receipt_items(text)
    total = detected_total if detected_total is not None else sum(i.get("price", 0) for i in items)
    if total is None:
        total = 0.0

    tx = Transaction(amount=total, description="receipt", date=datetime.datetime.utcnow().isoformat(), source="receipt")
    tx.category = _categorize_item("receipt")
    tx.transaction_type = "income" if total >= 0 else "expense"
    with Session(engine) as session:
        session.add(tx)
        session.commit()
        session.refresh(tx)
        saved_items = _save_receipt_items(session, items, tx.id)

    payload = {"text": text, "items": items, "total": total}
    if background_tasks is not None:
        background_tasks.add_task(_post_to_ai_brain, "ingest/receipt", payload)
    return {"transaction": _tx_to_dict(tx), "items": [si.dict() for si in saved_items], "text": text}


@app.post("/ingest/document")
async def ingest_document(file: UploadFile = File(...)):
    content = await file.read()
    sha = hashlib.sha256(content).hexdigest()
    with Session(engine) as session:
        existing = session.exec(select(IngestedDocument).where(IngestedDocument.sha256 == sha)).first()
        if existing:
            txs = session.exec(select(Transaction).where(Transaction.source == f"doc:{sha}")).all()
            return {"duplicate": True, "transactions": [_tx_to_dict(t) for t in txs]}

        doc = IngestedDocument(
            filename=file.filename,
            content_type=file.content_type,
            sha256=sha,
            kind="statement",
        )
        session.add(doc)

        lines = content.decode(errors="ignore").splitlines()
        created = []
        for ln in lines:
            parts = ln.strip().split()
            if len(parts) < 3:
                continue
            amount = float(parts[-1].replace("+", ""))
            description = " ".join(parts[1:-1])
            tx = Transaction(amount=amount, description=description, date=parts[0], source=f"doc:{sha}")
            tx.category = _categorize_item(description)
            tx.transaction_type = "income" if amount >= 0 else "expense"
            session.add(tx)
            session.commit()
            session.refresh(tx)
            created.append(_tx_to_dict(tx))

        doc.transaction_count = len(created)
        session.add(doc)
        session.commit()
        session.refresh(doc)
        return {"duplicate": False, "transactions": created}


@app.get("/summary")
def summary():
    with Session(engine) as session:
        txs = session.exec(select(Transaction)).all()
        income = sum(t.amount for t in txs if (t.amount or 0) >= 0)
        expenses = sum(t.amount for t in txs if (t.amount or 0) < 0)
        spend_by_category: Dict[str, float] = {}
        items = session.exec(select(ReceiptItem)).all()
        for it in items:
            cat = (it.category or "other").lower()
            spend_by_category[cat] = spend_by_category.get(cat, 0) + float(it.price or 0)
    return {
        "total_income": income,
        "total_expenses": expenses,
        "balance": income + expenses,
        "spend_by_category": spend_by_category,
    }


def _recalculate_categories_sync():
    with Session(engine) as session:
        items = session.exec(select(ReceiptItem)).all()
        for it in items:
            if not getattr(it, "category", None):
                it.category = _categorize_item(it.name or "")
                session.add(it)
        session.commit()


@app.post("/admin/recalculate_categories")
async def recalc_categories(request: Request):
    if not _authorize(request):
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": "forbidden"})
    _recalculate_categories_sync()
    return {"status": "ok"}


@app.get("/admin/migration_status")
async def migration_status(request: Request):
    if not _authorize(request):
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": "forbidden"})
    return {"db_revision": "current", "heads": ["head"]}


@app.get("/budgets")
def get_budgets():
    with Session(engine) as session:
        return session.exec(select(Budget)).all()
