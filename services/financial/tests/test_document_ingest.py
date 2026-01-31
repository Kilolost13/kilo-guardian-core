import io
from fastapi.testclient import TestClient
from financial.main import app, engine, IngestedDocument
from sqlmodel import SQLModel, Session, select

# Ensure tables exist for tests
SQLModel.metadata.create_all(engine)
client = TestClient(app)


def test_statement_ingest_creates_transactions_and_deduplicates():
    content = b"2024-01-01 PAYROLL +1234.56\n2024-01-02 RENT -900.00\n"
    files = {"file": ("statement.txt", io.BytesIO(content), "text/plain")}

    r = client.post("/ingest/document", files=files)
    assert r.status_code == 200
    data = r.json()
    assert data.get("duplicate") is False
    txs = data.get("transactions") or []
    assert len(txs) == 2
    amounts = sorted(round(t["amount"], 2) for t in txs)
    assert amounts == [-900.00, 1234.56]

    # post same file again -> should deduplicate
    r2 = client.post("/ingest/document", files=files)
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2.get("duplicate") is True
    assert len(data2.get("transactions") or []) == 2

    # ensure document persisted
    with Session(engine) as session:
        docs = session.exec(select(IngestedDocument)).all()
        assert len(docs) >= 1
        assert docs[0].transaction_count == 2
