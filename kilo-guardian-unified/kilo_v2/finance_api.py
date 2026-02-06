def get_finance_advice(user: str):
    # Dummy spending and goals logic for now; replace with real data as needed
    SPENDING_PATH = os.path.join(os.path.dirname(__file__), "../spending.json")
    GOALS_PATH = os.path.join(os.path.dirname(__file__), "../finance_goals.json")

    def load_spending():
        if not os.path.exists(SPENDING_PATH):
            return []
        with open(SPENDING_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_goals():
        if not os.path.exists(GOALS_PATH):
            return {}
        with open(GOALS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    spending = [s for s in load_spending() if s["user"] == user]
    goals = load_goals().get(user, {})
    advice = []
    import datetime
    from collections import defaultdict

    monthly = defaultdict(float)
    now = datetime.datetime.now()
    for s in spending:
        try:
            dt = datetime.datetime.fromisoformat(s["date"])
        except Exception:
            continue
        if dt.year == now.year and dt.month == now.month:
            monthly[s["category"]] += s["amount"]
    for cat, limit in goals.items():
        spent = monthly.get(cat, 0)
        if spent > limit:
            advice.append(
                f"You have exceeded your {cat} goal by ${spent - limit:.2f} this month."
            )
        elif spent > 0.8 * limit:
            advice.append(
                f"Warning: You are close to your {cat} goal (${spent:.2f} of ${limit:.2f})."
            )
        else:
            advice.append(
                f"Your {cat} spending is on track (${spent:.2f} of ${limit:.2f})."
            )
    if not advice:
        advice.append("No goals set or no spending recorded for this month.")
    return {"advice": advice}


import json
import os

from fastapi import APIRouter, File, HTTPException, UploadFile

FINANCE_PATH = os.path.join(os.path.dirname(__file__), "../finance_docs.json")
FINANCE_UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "../finance_uploads")
os.makedirs(FINANCE_UPLOAD_DIR, exist_ok=True)

router = APIRouter()


def load_finance_docs():
    if not os.path.exists(FINANCE_PATH):
        return []
    with open(FINANCE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_finance_docs(docs):
    with open(FINANCE_PATH, "w", encoding="utf-8") as f:
        json.dump(docs, f, indent=2)


@router.post("/finance/upload-csv")
def upload_banking_csv(user: str, file: UploadFile = File(...)):
    docs = load_finance_docs()
    file_path = os.path.join(FINANCE_UPLOAD_DIR, f"{user}_{file.filename}")
    with open(file_path, "wb") as f_out:
        f_out.write(file.file.read())
    docs.append(
        {"user": user, "filename": file.filename, "type": "csv", "path": file_path}
    )
    save_finance_docs(docs)
    return {"message": f"Received file: {file.filename}", "path": file_path}


@router.post("/finance/upload-document")
def upload_financial_document(user: str, file: UploadFile = File(...)):
    docs = load_finance_docs()
    file_path = os.path.join(FINANCE_UPLOAD_DIR, f"{user}_{file.filename}")
    with open(file_path, "wb") as f_out:
        f_out.write(file.file.read())
    docs.append(
        {"user": user, "filename": file.filename, "type": "document", "path": file_path}
    )
    save_finance_docs(docs)
    return {"message": f"Received document: {file.filename}", "path": file_path}
