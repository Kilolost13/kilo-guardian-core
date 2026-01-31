from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Request
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text
from sqlmodel import SQLModel, Session, Field, select
from typing import Optional, List, Dict
import os
import httpx
import datetime
from PIL import Image
from io import BytesIO
import pytesseract
import re
import base64
from contextlib import asynccontextmanager
import hashlib
from pathlib import Path
try:
    import PyPDF2  # optional for PDF text extraction
except Exception:
    PyPDF2 = None
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

from shared.models import Transaction, ReceiptItem
# Financial models
# Use shared models where appropriate to avoid duplicate definitions during test collection


class Budget(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    category: str
    monthly_limit: float
    created_at: Optional[str] = None  # Auto-generated if not provided


class Goal(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    target_amount: float
    current_amount: float = 0.0
    deadline: Optional[str] = None
    created_at: Optional[str] = None  # Auto-generated if not provided
    completed: bool = False


class IngestedDocument(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: Optional[str] = None
    content_type: Optional[str] = None
    sha256: str = Field(index=True)
    kind: Optional[str] = None  # receipt | statement | auto
    status: Optional[str] = None
    error: Optional[str] = None
    transaction_count: int = 0
    source_tag: Optional[str] = None
    extracted_text: Optional[str] = None
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


# Centralized engine selection (prefers in-memory for tests and fallbacks if /data not writable)
engine = get_engine('FINANCIAL_DB_URL', 'sqlite:////data/financial.db')
UPLOAD_DIR = Path("/data/financial_uploads")


# Scheduler control defaults (used by lifespan)
ENABLE_NIGHTLY_MAINTENANCE = os.getenv("ENABLE_NIGHTLY_MAINTENANCE", "false").lower() in ("1", "true", "yes")
NIGHTLY_CRON = os.getenv("NIGHTLY_CRON", "0 2 * * *")  # default: daily at 02:00
# runtime scheduler handle (set up at startup if enabled)
_scheduler = None


# Health check endpoint will be attached to the app created with lifespan below


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    try:
        SQLModel.metadata.create_all(engine)
        try:
            from financial.scripts.add_category_column_if_missing import ensure_column
            ensure_column()
        except Exception:
            print("Warning: failed to run migration helper")
        try:
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            print("Warning: failed to create upload dir")
        # schedule nightly maintenance if enabled
        global _scheduler
        if ENABLE_NIGHTLY_MAINTENANCE:
            try:
                from apscheduler.schedulers.background import BackgroundScheduler
                from apscheduler.triggers.cron import CronTrigger
                _scheduler = BackgroundScheduler()
                cron_parts = NIGHTLY_CRON.split()
                if len(cron_parts) == 5:
                    minute, hour, day, month, dow = cron_parts
                    trigger = CronTrigger(minute=minute, hour=hour, day=day, month=month, day_of_week=dow)
                else:
                    trigger = CronTrigger.from_crontab(NIGHTLY_CRON)
                _scheduler.add_job(_recalculate_categories_background, trigger=trigger, id='nightly_recat')
                _scheduler.start()
                app.state.scheduler = _scheduler
                print("Nightly maintenance scheduler started")
            except Exception as e:
                print(f"Warning: failed to start scheduler: {e}")
    except Exception:
        pass
    yield
    # shutdown
    try:
        if _scheduler:
            _scheduler.shutdown(wait=False)
            print("Scheduler shut down")
    except Exception:
        pass



app = FastAPI(title="Financial Service", lifespan=lifespan)

# Instrument Prometheus metrics
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

# Prometheus custom metrics for ingestion
from prometheus_client import Counter

ingest_total = Counter("financial_ingest_total", "Documents ingested", ["kind"])
ingest_failed_total = Counter("financial_ingest_failed_total", "Failed ingests", ["kind", "reason"])
ingest_duplicate_total = Counter("financial_ingest_duplicates_total", "Duplicate uploads", ["kind"])
ingest_transactions_total = Counter("financial_ingest_transactions_total", "Transactions created from ingests", ["kind"])


# Health check endpoints
@app.get("/status")
@app.get("/health")
def status():
    return {"status": "ok"}


AI_BRAIN_URL = os.getenv("AI_BRAIN_URL", "http://ai_brain:9004/ingest/finance")
# Note: admin credentials are read at call-time to allow tests to set env vars after import


# startup/shutdown handled by lifespan


def _check_admin_auth(request: Request):
    """Centralized admin auth: supports legacy x-admin-token, ADMIN_TOKEN_LIST, and optional Basic auth.
    If no admin credentials are configured, the endpoint is open (same legacy behavior when ADMIN_TOKEN was not set).
    """
    # read admin credentials dynamically from environment
    ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
    ADMIN_TOKEN_LIST = set([t for t in (os.getenv("ADMIN_TOKEN_LIST") or "").split(",") if t])
    ADMIN_BASIC_USER = os.getenv("ADMIN_BASIC_USER")
    ADMIN_BASIC_PASS = os.getenv("ADMIN_BASIC_PASS")

    # if no admin credential is configured, allow
    if not (ADMIN_TOKEN or ADMIN_TOKEN_LIST or (ADMIN_BASIC_USER and ADMIN_BASIC_PASS)):
        # no local admin configured; if a header is provided, try gateway centralized validation
        token = request.headers.get("x-admin-token")
        if not token:
            return True
        # lazy import gateway validator
        try:
            from gateway.admin_client import validate_token as _gval
            if _gval(token):
                return True
        except Exception:
            pass
        raise HTTPException(status_code=403, detail="invalid admin credentials")

    # check x-admin-token header
    token = request.headers.get("x-admin-token")
    if token:
        if ADMIN_TOKEN and token == ADMIN_TOKEN:
            return True
        if token in ADMIN_TOKEN_LIST:
            return True

    # check HTTP Basic Authorization header
    auth = request.headers.get("authorization")
    if auth and auth.lower().startswith("basic ") and ADMIN_BASIC_USER and ADMIN_BASIC_PASS:
        try:
            payload = base64.b64decode(auth.split(None, 1)[1]).decode()
            user, pwd = payload.split(":", 1)
            if user == ADMIN_BASIC_USER and pwd == ADMIN_BASIC_PASS:
                return True
        except Exception:
            pass

    # nothing matched
    raise HTTPException(status_code=403, detail="invalid admin credentials")


# shutdown handled by lifespan


@app.get("/")
@app.get("/transactions")  # Frontend-compatible alias
def list_transactions():
    with Session(engine) as session:
        txs = session.exec(select(Transaction)).all()
        out = []
        for t in txs:
            items = session.exec(select(ReceiptItem).where(ReceiptItem.transaction_id == t.id)).all()
            d = t.dict()
            d["items"] = [it.dict() for it in items]
            # Derive transaction_type for frontend (income vs expense)
            d["transaction_type"] = "income" if (d.get("amount") or 0) > 0 else "expense"
            # Derive category: use most common receipt item category, else categorize description
            if items:
                cat_counts = {}
                for it in items:
                    cat = (it.category or "uncategorized").lower()
                    cat_counts[cat] = cat_counts.get(cat, 0) + 1
                d["category"] = max(cat_counts, key=cat_counts.get)
            else:
                d["category"] = _categorize_item(d.get("description") or "")
            # Provide created_at for UI consistency
            d.setdefault("created_at", d.get("date"))
            out.append(d)
        return out


@app.get("/summary")
def get_financial_summary():
    def safe_number(val):
        try:
            if val is None:
                return 0.0
            num = float(val)
            if num != num or num is None:  # NaN or None
                return 0.0
            return num
        except Exception:
            return 0.0
    with Session(engine) as session:
        transactions = session.exec(select(Transaction)).all()
        total_income = sum(safe_number(t.amount) for t in transactions if safe_number(t.amount) > 0)
        total_expenses = sum(safe_number(t.amount) for t in transactions if safe_number(t.amount) < 0)
        balance = total_income + total_expenses
        # Aggregate by category from receipt items for a simple analytics view
        receipt_items = session.exec(select(ReceiptItem)).all()
        by_category: Dict[str, float] = {}
        for it in receipt_items:
            cat = _categorize_item(it.name)
            by_category[cat] = by_category.get(cat, 0) + safe_number(it.price)
        return {
            "total_income": float(total_income),
            "total_expenses": float(total_expenses),
            "balance": float(balance),
            "spend_by_category": {k: float(safe_number(v)) for k, v in by_category.items()},
            "transaction_count": len(transactions)
        }


@app.get("/shopping_habits")
def get_shopping_habits():
    with Session(engine) as session:
        receipt_items = session.exec(select(ReceiptItem)).all()
        item_counts = {}
        for item in receipt_items:
            item_counts[item.name] = item_counts.get(item.name, 0) + 1
        sorted_items = sorted(item_counts.items(), key=lambda item: item[1], reverse=True)
        return {"most_frequent_items": sorted_items[:5]}


@app.get("/spending_trends")
def get_spending_trends():
    with Session(engine) as session:
        transactions = session.exec(select(Transaction)).all()
        monthly_spending = {}
        for t in transactions:
            month = datetime.datetime.fromisoformat(t.date).strftime("%Y-%m")
            monthly_spending[month] = monthly_spending.get(month, 0) + t.amount
        sorted_spending = sorted(monthly_spending.items())
        return {"monthly_spending": sorted_spending}


@app.post("/")
@app.post("/transaction")  # Frontend-compatible alias
def add_transaction(payload: dict, background_tasks: BackgroundTasks = None):
    # Extract transaction_type from payload (frontend sends this but model doesn't have it)
    transaction_type = payload.get("transaction_type", "income")
    amount = float(payload.get("amount", 0))

    # Convert expense amounts to negative (backend stores expenses as negative)
    if transaction_type == "expense" and amount > 0:
        amount = -amount

    # Create Transaction object with fields the model actually has
    t = Transaction(
        amount=amount,
        description=payload.get("description", ""),
        date=payload.get("date", datetime.datetime.now().strftime("%Y-%m-%d")),
        source=payload.get("source", "manual")
    )

    with Session(engine) as session:
        session.add(t)
        session.commit()
        session.refresh(t)
    # Send to ai_brain
    if background_tasks:
        background_tasks.add_task(_send_to_ai_brain, t)
    else:
        import asyncio
        asyncio.create_task(_send_to_ai_brain(t))
    return t


@app.put("/{transaction_id}")
def update_transaction(transaction_id: int, t: Transaction, background_tasks: BackgroundTasks = None):
    with Session(engine) as session:
        db_transaction = session.get(Transaction, transaction_id)
        if not db_transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        db_transaction.amount = t.amount
        db_transaction.category = t.category
        db_transaction.description = t.description
        db_transaction.date = t.date
        db_transaction.type = t.type
        session.add(db_transaction)
        session.commit()
        session.refresh(db_transaction)
    if background_tasks:
        background_tasks.add_task(_send_to_ai_brain, db_transaction)
    return db_transaction


@app.delete("/{transaction_id}")
@app.delete("/transactions/{transaction_id}")  # Frontend-compatible alias
def delete_transaction(transaction_id: int):
    with Session(engine) as session:
        transaction = session.get(Transaction, transaction_id)
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        # Delete associated receipt items
        items = session.exec(select(ReceiptItem).where(ReceiptItem.transaction_id == transaction_id)).all()
        for item in items:
            session.delete(item)
        session.delete(transaction)
        session.commit()
    return {"status": "deleted"}


# Budget endpoints
@app.get("/budgets")
def get_budgets():
    def safe_number(val):
        try:
            if val is None:
                return 0.0
            num = float(val)
            if num != num or num is None:
                return 0.0
            return num
        except Exception:
            return 0.0
    with Session(engine) as session:
        budgets = session.exec(select(Budget)).all()
        # Calculate spent and percentage for each budget
        transactions = session.exec(select(Transaction)).all()
        now = datetime.datetime.utcnow()
        current_month = now.strftime('%Y-%m')
        out = []
        for b in budgets:
            # Sum expenses for this category in the current month
            spent = sum(
                abs(safe_number(t.amount))
                for t in transactions
                if t.category == b.category and safe_number(t.amount) < 0 and t.date.startswith(current_month)
            )
            monthly_limit = safe_number(b.monthly_limit)
            percentage = (spent / monthly_limit * 100) if monthly_limit > 0 else 0
            d = b.dict()
            d['spent'] = float(spent)
            d['percentage'] = float(percentage)
            d['monthly_limit'] = float(monthly_limit)
            out.append(d)
        return out


@app.post("/budgets")
@app.post("/budget")  # Frontend-compatible alias
def create_budget(budget: Budget, background_tasks: BackgroundTasks = None):
    budget.created_at = datetime.datetime.utcnow().isoformat()
    with Session(engine) as session:
        session.add(budget)
        session.commit()
        session.refresh(budget)
    if background_tasks:
        background_tasks.add_task(_send_budget_to_ai, budget)
    return budget


@app.put("/budgets/{budget_id}")
def update_budget(budget_id: int, budget: Budget):
    with Session(engine) as session:
        db_budget = session.get(Budget, budget_id)
        if not db_budget:
            raise HTTPException(status_code=404, detail="Budget not found")
        db_budget.category = budget.category
        db_budget.monthly_limit = budget.monthly_limit
        session.add(db_budget)
        session.commit()
        session.refresh(db_budget)
        return db_budget


@app.delete("/budgets/{budget_id}")
def delete_budget(budget_id: int):
    with Session(engine) as session:
        budget = session.get(Budget, budget_id)
        if not budget:
            raise HTTPException(status_code=404, detail="Budget not found")
        session.delete(budget)
        session.commit()
    return {"status": "deleted"}


# Goal endpoints
@app.get("/goals")
def get_goals():
    def safe_number(val):
        try:
            if val is None:
                return 0.0
            num = float(val)
            if num != num or num is None:
                return 0.0
            return num
        except Exception:
            return 0.0
    with Session(engine) as session:
        goals = session.exec(select(Goal)).all()
        out = []
        for g in goals:
            target_amount = safe_number(g.target_amount)
            current_amount = safe_number(g.current_amount)
            progress = (current_amount / target_amount * 100) if target_amount > 0 else 0
            d = g.dict()
            d['progress'] = float(progress)
            d['target_amount'] = float(target_amount)
            d['current_amount'] = float(current_amount)
            out.append(d)
        return out


@app.post("/goals")
@app.post("/goal")  # Frontend-compatible alias
def create_goal(goal: Goal, background_tasks: BackgroundTasks = None):
    goal.created_at = datetime.datetime.utcnow().isoformat()
    with Session(engine) as session:
        session.add(goal)
        session.commit()
        session.refresh(goal)
    if background_tasks:
        background_tasks.add_task(_send_goal_to_ai, goal)
    return goal


@app.put("/goals/{goal_id}")
def update_goal(goal_id: int, goal: Goal):
    with Session(engine) as session:
        db_goal = session.get(Goal, goal_id)
        if not db_goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        db_goal.name = goal.name
        db_goal.target_amount = goal.target_amount
        db_goal.current_amount = goal.current_amount
        db_goal.deadline = goal.deadline
        db_goal.completed = goal.completed
        session.add(db_goal)
        session.commit()
        session.refresh(db_goal)
    return db_goal


@app.delete("/goals/{goal_id}")
def delete_goal(goal_id: int):
    with Session(engine) as session:
        goal = session.get(Goal, goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        session.delete(goal)
        session.commit()
    return {"status": "deleted"}


@app.post("/receipt")
def upload_receipt(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    content = file.file.read()
    img = Image.open(BytesIO(content))
    text = pytesseract.image_to_string(img)
    items, detected_total = _parse_receipt_items(text)
    summed = sum(i['price'] for i in items)
    # Prefer a clearly indicated total on the receipt when available and reasonable
    if detected_total is not None:
        # if detected total differs wildly from summed items, trust detected_total
        if abs(detected_total - summed) > max(0.01, 0.1 * abs(summed)):
            total = detected_total
        else:
            total = summed
    else:
        total = summed
    t = Transaction(
        amount=total,
        description="Receipt Upload",
        date=datetime.datetime.utcnow().isoformat(),
        source='ocr',
    )
    with Session(engine) as session:
        session.add(t)
        session.commit()
        session.refresh(t)
        for item in items:
            cat = _categorize_item(item.get('name', ''))
            ri = ReceiptItem(
                transaction_id=t.id,
                name=item['name'],
                price=item['price'],
                category=cat,
            )
            session.add(ri)
        session.commit()
        # serialize within the session so detached-instance issues do not occur
        tx_serialized = {
            "id": getattr(t, "id", None),
            "amount": getattr(t, "amount", None),
            "description": getattr(t, "description", None),
            "date": getattr(t, "date", None),
            "source": getattr(t, "source", None),
        }
    # Send to ai_brain
    if background_tasks:
        background_tasks.add_task(_send_receipt_to_ai_brain, text)
    else:
        import asyncio
        asyncio.create_task(_send_receipt_to_ai_brain(text))
    # ensure the Transaction is serialized to native types for JSON
    # model_dump()/dict() behavior can vary across SQLModel versions; serialize explicitly
        return {"transaction": tx_serialized, "items": items}
    return {"transaction": tx_serialized, "items": items}


@app.post("/ingest/document")
def ingest_document(file: UploadFile = File(...), kind: str = "auto", background_tasks: BackgroundTasks = None):
    content = file.file.read()
    filename = file.filename or "upload"
    content_type = file.content_type or ""
    sha = _sha256_bytes(content)
    source_tag = f"doc:{sha[:12]}"
    requested_kind = (kind or "auto").lower()

    # deduplicate by hash
    with Session(engine) as session:
        existing = session.exec(select(IngestedDocument).where(IngestedDocument.sha256 == sha)).first()
        if existing:
            ingest_duplicate_total.labels(existing.kind or "unknown").inc()
            txs = session.exec(select(Transaction).where(Transaction.source == existing.source_tag)).all()
            return {
                "duplicate": True,
                "document": existing.dict(),
                "transactions": [t.dict() for t in txs],
            }

    # Save original file for audit/reference
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        dest = UPLOAD_DIR / f"{sha}{Path(filename).suffix}"
        with open(dest, "wb") as f:
            f.write(content)
    except Exception:
        pass

    text = _extract_text_generic(content, content_type, filename)
    detected_kind = requested_kind if requested_kind != "auto" else _detect_document_kind(text, filename)

    doc = IngestedDocument(
        filename=filename,
        content_type=content_type,
        sha256=sha,
        kind=detected_kind,
        status="processing",
        source_tag=source_tag,
        extracted_text=text[:10000],  # cap for storage
    )

    transactions_created = []
    items_created = []
    try:
        with Session(engine) as session:
            session.add(doc)
            session.commit()
            session.refresh(doc)

        if detected_kind == "receipt":
            items, detected_total = _parse_receipt_items(text)
            summed = sum(i['price'] for i in items)
            total = detected_total if detected_total is not None and abs(detected_total - summed) > max(0.01, 0.1 * abs(summed)) else summed
            t = Transaction(
                amount=total,
                description=f"Receipt ({filename})",
                date=datetime.datetime.utcnow().isoformat(),
                source=source_tag,
            )
            with Session(engine) as session:
                session.add(t)
                session.commit()
                session.refresh(t)
                for item in items:
                    cat = _categorize_item(item.get('name', ''))
                    ri = ReceiptItem(
                        transaction_id=t.id,
                        name=item['name'],
                        price=item['price'],
                        category=cat,
                    )
                    session.add(ri)
                    items_created.append(ri.dict())
                session.commit()
                transactions_created.append(t.dict())
            ingest_total.labels("receipt").inc()
            ingest_transactions_total.labels("receipt").inc(len(transactions_created))
        else:
            txs = _parse_statement_transactions(text)
            with Session(engine) as session:
                for tx in txs:
                    txn = Transaction(
                        amount=tx['amount'],
                        description=tx['description'],
                        date=tx['date'],
                        source=source_tag,
                    )
                    session.add(txn)
                    session.commit()
                    session.refresh(txn)
                    transactions_created.append(txn.dict())
            ingest_total.labels("statement").inc()
            ingest_transactions_total.labels("statement").inc(len(transactions_created))

        # update document row
        with Session(engine) as session:
            stored = session.get(IngestedDocument, doc.id)
            if stored:
                stored.status = "processed"
                stored.transaction_count = len(transactions_created)
                session.add(stored)
                session.commit()

        # async fan-out to AI if available
        if background_tasks:
            background_tasks.add_task(_send_receipt_to_ai_brain, text)
        else:
            import asyncio
            asyncio.create_task(_send_receipt_to_ai_brain(text))

        return {
            "duplicate": False,
            "document": doc.dict(),
            "transactions": transactions_created,
            "items": items_created if detected_kind == "receipt" else None,
        }
    except Exception as e:
        ingest_failed_total.labels(detected_kind or "unknown", type(e).__name__).inc()
        with Session(engine) as session:
            stored = session.get(IngestedDocument, doc.id)
            if stored:
                stored.status = "failed"
                stored.error = str(e)
                session.add(stored)
                session.commit()
        raise HTTPException(status_code=500, detail=f"ingestion failed: {e}")


@app.get("/ingested-documents")
def get_ingested_documents(limit: int = 50):
    """List all ingested documents with their processing status"""
    with Session(engine) as session:
        docs = session.exec(
            select(IngestedDocument).order_by(IngestedDocument.created_at.desc()).limit(limit)
        ).all()
        return {"documents": [doc.dict() for doc in docs]}


@app.delete("/ingested-documents/{doc_id}")
def delete_ingested_document(doc_id: int, purge_file: bool = True):
    """Delete an ingested document and any transactions/items sourced from it"""
    with Session(engine) as session:
        doc = session.get(IngestedDocument, doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        # Delete transactions and receipt items sourced from this document
        if doc.source_tag:
            txs = session.exec(select(Transaction).where(Transaction.source == doc.source_tag)).all()
            for tx in txs:
                items = session.exec(select(ReceiptItem).where(ReceiptItem.transaction_id == tx.id)).all()
                for it in items:
                    session.delete(it)
                session.delete(tx)

        # Remove document record
        session.delete(doc)
        session.commit()

    # Remove stored file if requested (best-effort)
    if purge_file:
        try:
            fname = f"{doc.sha256}{Path(doc.filename or '').suffix}"
            fpath = UPLOAD_DIR / fname
            if fpath.exists():
                fpath.unlink()
        except Exception:
            pass

    return {"deleted": doc_id, "purged_file": purge_file}


@app.get("/spending/analytics")
def get_spending_analytics():
    """Generate spending analytics and insights from transactions"""
    with Session(engine) as session:
        transactions = session.exec(select(Transaction)).all()
        receipt_items = session.exec(select(ReceiptItem)).all()
        
        if not transactions:
            return {
                "total_transactions": 0,
                "insights": ["No transactions found. Upload some documents to get started!"]
            }
        
        # Calculate totals
        total_spent = sum(abs(t.amount) for t in transactions if t.amount < 0)
        total_income = sum(t.amount for t in transactions if t.amount > 0)
        
        # Category breakdown
        category_spending = {}
        for item in receipt_items:
            cat = item.category or 'uncategorized'
            category_spending[cat] = category_spending.get(cat, 0) + item.price
        
        # Monthly trends
        monthly_spending = {}
        for t in transactions:
            try:
                month = datetime.datetime.fromisoformat(t.date).strftime("%Y-%m")
                monthly_spending[month] = monthly_spending.get(month, 0) + abs(t.amount)
            except Exception:
                pass
        
        # Top categories
        top_categories = sorted(category_spending.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Most frequent items
        item_counts = {}
        for item in receipt_items:
            item_counts[item.name] = item_counts.get(item.name, 0) + 1
        top_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Generate insights
        insights = []
        if total_spent > 0:
            insights.append(f"💰 Total spending: ${total_spent:.2f}")
        if total_income > 0:
            insights.append(f"💵 Total income: ${total_income:.2f}")
        
        if top_categories:
            top_cat, top_amt = top_categories[0]
            insights.append(f"🏆 Top spending category: {top_cat} (${top_amt:.2f})")
        
        if len(monthly_spending) >= 2:
            months = sorted(monthly_spending.items())
            recent = months[-1][1]
            prev = months[-2][1]
            change = ((recent - prev) / prev * 100) if prev > 0 else 0
            trend = "📈 increased" if change > 0 else "📉 decreased"
            insights.append(f"Spending {trend} by {abs(change):.1f}% from last month")
        
        if top_items:
            top_item, count = top_items[0]
            insights.append(f"🛒 Most purchased: {top_item} ({count}x)")
        
        # Average transaction
        avg_transaction = total_spent / len([t for t in transactions if t.amount < 0]) if transactions else 0
        if avg_transaction > 0:
            insights.append(f"📊 Average transaction: ${avg_transaction:.2f}")
        
        return {
            "total_transactions": len(transactions),
            "total_spent": total_spent,
            "total_income": total_income,
            "category_breakdown": category_spending,
            "top_categories": top_categories,
            "monthly_trends": sorted(monthly_spending.items()),
            "top_items": top_items,
            "insights": insights,
            "average_transaction": avg_transaction
        }


@app.post("/admin/recalculate_categories")
def recalculate_categories(request: Request, background_tasks: BackgroundTasks):
    """Trigger re-categorization. Requires ADMIN_TOKEN header when ADMIN_TOKEN is set.
    Runs as a background job to avoid long blocking calls.
    """
    _check_admin_auth(request)

    # schedule background job
    background_tasks.add_task(_recalculate_categories_background)
    return {"status": "scheduled"}


@app.get("/admin/migration_status")
def migration_status(request: Request):
    """Return current DB alembic revision and available heads.
    Requires ADMIN_TOKEN when set.
    """
    _check_admin_auth(request)

    # determine alembic heads
    try:
        from alembic.config import Config as AlembicConfig
        from alembic.script import ScriptDirectory
        alembic_ini = os.path.join(os.getcwd(), 'alembic.ini')
        cfg = AlembicConfig(alembic_ini)
        script = ScriptDirectory.from_config(cfg)
        heads = script.get_heads()
    except Exception:
        heads = []

    # read current revision from alembic_version table if present
    current = None
    try:
        with engine.connect() as conn:
            r = conn.execute(text("SELECT version_num FROM alembic_version"))
            row = r.fetchone()
            if row:
                current = row[0]
    except Exception:
        current = None

    return {"db_revision": current, "heads": heads}


def _recalculate_categories_background(batch_size: int = 200):
    updated = 0
    total = 0
    with Session(engine) as session:
        offset = 0
        while True:
            items = session.exec(select(ReceiptItem).offset(offset).limit(batch_size)).all()
            if not items:
                break
            for it in items:
                total += 1
                new_cat = _categorize_item(it.name or "")
                if it.category != new_cat:
                    it.category = new_cat
                    session.add(it)
                    updated += 1
            session.commit()
            offset += batch_size
    print(f"Recalculate categories completed: updated={updated}, total={total}")
    return {"updated": updated, "total": total}


def _sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def _extract_text_from_pdf(content: bytes) -> Optional[str]:
    if not PyPDF2:
        return None
    try:
        reader = PyPDF2.PdfReader(BytesIO(content))
        texts = []
        for page in reader.pages:
            try:
                texts.append(page.extract_text() or "")
            except Exception:
                continue
        return "\n".join(texts)
    except Exception:
        return None


def _extract_text_generic(content: bytes, content_type: Optional[str], filename: Optional[str]) -> str:
    # If text file, decode directly
    if content_type and content_type.startswith("text"):
        try:
            return content.decode(errors="ignore")
        except Exception:
            pass

    # If PDF
    if (content_type and "pdf" in content_type.lower()) or (filename and filename.lower().endswith(".pdf")):
        pdf_text = _extract_text_from_pdf(content)
        if pdf_text:
            return pdf_text

    # Try OCR on image
    try:
        img = Image.open(BytesIO(content))
        return pytesseract.image_to_string(img)
    except Exception:
        # fallback: best-effort decode
        try:
            return content.decode(errors="ignore")
        except Exception:
            return ""


def _detect_document_kind(text: str, filename: Optional[str]) -> str:
    lower = text.lower()
    if "statement" in lower or "ending balance" in lower or "available balance" in lower:
        return "statement"
    if filename and any(filename.lower().endswith(ext) for ext in [".pdf", ".stmt", ".ofx"]):
        return "statement"
    if "total" in lower and "tax" in lower:
        return "receipt"
    return "statement"  # default to statement for banking docs


def _parse_statement_transactions(text: str) -> List[Dict[str, object]]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    txs: List[Dict[str, object]] = []
    today = datetime.datetime.utcnow().date()

    # More flexible patterns for various statement formats
    patterns = [
        # ISO date: 2024-01-15 Description $123.45
        re.compile(r"(?P<date>\d{4}-\d{2}-\d{2})\s+(?P<desc>.+?)\s+(?P<amount>[()\-\+$€£]?\s*\d+[.,]\d{2})"),
        # US date: 01/15/2024 Description $123.45
        re.compile(r"(?P<date>\d{1,2}/\d{1,2}/\d{2,4})\s+(?P<desc>.+?)\s+(?P<amount>[()\-\+$€£]?\s*\d+[.,]\d{2})"),
        # UK date: 15/01/2024 Description £123.45
        re.compile(r"(?P<date>\d{1,2}/\d{1,2}/\d{2,4})\s+(?P<desc>[^0-9]+?)\s+(?P<amount>[()\-\+$€£]?\s*\d+[.,]\d{2})"),
        # Date with dashes: 15-01-2024 Description 123.45
        re.compile(r"(?P<date>\d{1,2}-\d{1,2}-\d{2,4})\s+(?P<desc>.+?)\s+(?P<amount>[()\-\+$€£]?\s*\d+[.,]\d{2})"),
        # Description only with amount at end: Something here 123.45
        re.compile(r"(?P<desc>.+?)\s+(?P<amount>[()\-\+$€£]?\s*\d+[.,]\d{2})\s*$"),
    ]

    # Look for any line with a money amount
    money_pattern = re.compile(r"[()\-\+$€£]?\s*\d+[.,]\d{2}")

    def _normalize_date(ds: Optional[str]) -> str:
        if not ds:
            return today.isoformat()
        try:
            ds = ds.strip()
            if "/" in ds:
                parts = ds.split("/")
                if len(parts) == 3:
                    # Try MM/DD/YYYY (US format)
                    try:
                        m, d, y = parts
                        if len(y) == 2:
                            y = "20" + y
                        return datetime.date(int(y), int(m), int(d)).isoformat()
                    except:
                        # Try DD/MM/YYYY (UK format)
                        d, m, y = parts
                        if len(y) == 2:
                            y = "20" + y
                        return datetime.date(int(y), int(m), int(d)).isoformat()
            elif "-" in ds:
                parts = ds.split("-")
                if len(parts) == 3:
                    # Try YYYY-MM-DD
                    if len(parts[0]) == 4:
                        return datetime.date.fromisoformat(ds).isoformat()
                    # Try DD-MM-YYYY
                    d, m, y = parts
                    if len(y) == 2:
                        y = "20" + y
                    return datetime.date(int(y), int(m), int(d)).isoformat()
            return datetime.date.fromisoformat(ds).isoformat()
        except Exception:
            return today.isoformat()

    for line in lines:
        # Skip header/footer lines
        if len(line) < 10 or any(keyword in line.lower() for keyword in [
            'page', 'statement', 'balance', 'total', 'account', 'beginning', 'ending', 'summary'
        ]):
            continue
        
        # Only process lines with money amounts
        if not money_pattern.search(line):
            continue

        matched = None
        for pat in patterns:
            m = pat.search(line)
            if m:
                matched = m
                break
        
        if not matched:
            continue
            
        gd = matched.groupdict()
        desc = gd.get("desc", "Transaction").strip()
        amt_raw = gd.get("amount", "0").strip()
        
        # Skip if description is too short or just numbers
        if len(desc) < 3 or desc.isdigit():
            continue
        
        # Handle parentheses negatives and signs
        is_negative = amt_raw.startswith("(") and amt_raw.endswith(")")
        amt_raw = re.sub(r"[()$€£\s]", "", amt_raw)
        
        try:
            amt = _normalize_price(amt_raw)
            if is_negative:
                amt = -abs(amt)
        except:
            continue
        
        date_str = _normalize_date(gd.get("date"))
        
        txs.append({
            "description": desc.strip()[:100],  # Limit description length
            "amount": float(amt),
            "date": date_str,
            "category": _categorize_item(desc),
        })

    # Deduplicate by desc+amount+date
    seen = set()
    deduped = []
    for tx in txs:
        key = (tx["description"].lower(), round(tx["amount"], 2), tx["date"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(tx)
    
    print(f"[PARSER] Extracted {len(deduped)} transactions from {len(lines)} lines")
    return deduped


async def _send_to_ai_brain(t: Transaction):
    async with httpx.AsyncClient() as client:
        try:
            await client.post(AI_BRAIN_URL, json={
                "amount": t.amount,
                "description": t.description,
                "date": t.date
            }, timeout=5)
        except Exception as e:
            print(f"[AI_BRAIN] Failed to send transaction: {e}")


async def _send_receipt_to_ai_brain(text: str):
    async with httpx.AsyncClient() as client:
        try:
            await client.post("http://ai_brain:9004/ingest/receipt", json={"text": text}, timeout=5)
        except Exception as e:
            print(f"[AI_BRAIN] Failed to send receipt: {e}")


async def _send_budget_to_ai(budget: Budget):
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                "http://ai_brain:9004/ingest/budget",
                json={
                    "category": budget.category,
                    "monthly_limit": budget.monthly_limit,
                    "created_at": budget.created_at,
                },
                timeout=5,
            )
        except Exception as e:
            print(f"[AI_BRAIN] Failed to send budget: {e}")


async def _send_goal_to_ai(goal: Goal):
    async with httpx.AsyncClient() as client:
        try:
            # Check progress and send motivational message
            progress_percent = (goal.current_amount / goal.target_amount * 100) if goal.target_amount > 0 else 0
            remaining = goal.target_amount - goal.current_amount

            message = (
                f"Financial goal '{goal.name}': "
                f"${goal.current_amount:.2f} of ${goal.target_amount:.2f} saved "
                f"({progress_percent:.1f}% complete). ${remaining:.2f} remaining."
            )

            await client.post(
                "http://ai_brain:9004/ingest/goal",
                json={
                    "name": goal.name,
                    "target_amount": goal.target_amount,
                    "current_amount": goal.current_amount,
                    "deadline": goal.deadline,
                    "message": message,
                },
                timeout=5,
            )
        except Exception as e:
            print(f"[AI_BRAIN] Failed to send goal: {e}")


def _parse_receipt_items(text: str):
    """
    Parse receipt text heuristically.
    Returns (items, detected_total) where detected_total is either a found 'total' on the receipt or None.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    items: List[Dict[str, object]] = []
    detected_total: Optional[float] = None

    price_re = re.compile(r"([-+]?\d+[.,]\d{2})")
    # scan for explicit total lines first
    for line in reversed(lines[-10:]):
        if re.search(r"\b(total|amount due|grand total|balance)\b", line, re.IGNORECASE):
            m = price_re.search(line)
            if m:
                detected_total = _normalize_price(m.group(1))
                break

    for line in lines:
        # skip obvious non-item lines
        if re.search(r"\b(total|subtotal|tax|change|amount due|visa|mastercard|card)\b", line, re.IGNORECASE):
            continue
        m = price_re.search(line)
        if m:
            price = _normalize_price(m.group(1))
            # try to extract a name by removing the price token and quantity markers
            name_part = price_re.sub('', line).strip()
            # remove leading quantity like '2 x' or '1x'
            name_part = re.sub(r"^\d+\s*[xX]\s*", '', name_part).strip()
            # remove trailing separators
            name_part = re.sub(r"[\-\.:,\s]+$", '', name_part)
            if not name_part:
                name_part = "item"
            items.append({"name": name_part, "price": float(price)})

    return items, detected_total


def _normalize_price(p: str) -> float:
    # converts strings like '1,99' or '1.99' into float
    s = p.replace(',', '.')
    # strip any non-numeric leading/trailing
    s = re.sub(r"[^0-9.\-+]", "", s)
    try:
        return float(s)
    except Exception:
        return 0.0


def _categorize_item(name: str) -> str:
    n = re.sub(r"[^a-z0-9 ]", " ", name.lower())

    # Expanded keyword mapping to cover many common categories
    mapping = {
        'groceries': [
            'milk', 'bread', 'cheese', 'apple', 'banana', 'eggs', 'butter', 'grocery',
            'supermarket', 'super market', 'aldi', 'lidl', 'wholefoods', 'tesco',
            'sainsbury', 'safeway',
        ],
        'produce': ['vegetable', 'vegetables', 'produce', 'lettuce', 'tomato', 'potato', 'onion', 'carrot', 'cucumber'],
        'bakery': ['bakery', 'baker', 'bread', 'croissant', 'baguette'],
        'coffee': ['coffee', 'latte', 'espresso', 'cappuccino', 'starbucks'],
        'restaurants': ['restaurant', 'cafe', 'diner', 'burger', 'pizza', 'bistro', 'barbecue', 'brasserie'],
        'fast_food': ['mcdonald', 'kfc', 'burgerking', 'burger king', 'tacobell', 'wendys', 'subway'],
        'alcohol': ['beer', 'wine', 'vodka', 'whiskey', 'liquor', 'spirits', 'brewery'],
        'beverages': ['soda', 'cola', 'juice', 'water', 'tea'],
        'fuel': ['gas', 'petrol', 'diesel', 'fuel', 'shell', 'bp', 'esso'],
        'transport': ['uber', 'taxi', 'train', 'bus', 'lyft', 'metro', 'tube'],
        'pharmacy': ['pharm', 'drug', 'pharmacy', 'rx', 'pharmacy'],
        'health': ['doctor', 'clinic', 'hospital', 'dentist', 'optician'],
        'beauty': ['cosmetic', 'cosmetics', 'makeup', 'salon', 'barber', 'hairdresser'],
        'clothing': ['clothing', 'apparel', 'shirt', 'jeans', 'dress', 'h&m', 'zara', 'uniqlo'],
        'electronics': ['iphone', 'samsung', 'laptop', 'computer', 'electronics', 'tv', 'headphone'],
        'entertainment': ['movie', 'cinema', 'netflix', 'spotify', 'concert', 'theatre', 'theater'],
        'utilities': ['electric', 'water', 'gas bill', 'internet', 'utility', 'utilities'],
        'subscription': ['subscription', 'monthly', 'membership', 'netflix', 'spotify', 'amazon prime'],
        'insurance': ['insurance', 'insurer', 'premium'],
        'home': ['ikea', 'home', 'furniture', 'mattress', 'homedepot', 'b&q'],
        'cleaning': ['detergent', 'cleaner', 'soap', 'bleach'],
        'baby': ['diaper', 'nappy', 'formula', 'baby'],
        'pet': ['pet', 'dog food', 'cat food', 'vet'],
        'garden': ['garden', 'plants', 'garden centre', 'nursery'],
        'sports': ['gym', 'fitness', 'sport', 'sports'],
        'books': ['book', 'barnes', 'bookstore', 'amazon books'],
        'other': []
    }

    # Quick heuristics: look for currency-like tokens to help classify
    tokens = n.split()

    # categorical shortcuts / precedence for common semantic keywords
    if re.search(r"\b(subscription|monthly|membership|renewal|auto renew)\b", n):
        return 'subscription'

    # merchant-specific shortcuts for fast food / well-known brands
    if re.search(r"\b(mcdonald|mcdonalds|kfc|burgerking|tacobell|wendys|subway)\b", n):
        return 'fast_food'

    # category precedence: specific merchant names or keywords first
    for cat, keys in mapping.items():
        for k in keys:
            if k in n:
                return cat

    # fallback heuristics
    if any(t.isdigit() for t in tokens):
        # numbers present usually indicate an item line; assume groceries
        return 'groceries'

    return 'other'
