from fastapi.testclient import TestClient
from financial.main import app, engine
from sqlmodel import SQLModel

# Ensure DB tables exist for tests
SQLModel.metadata.create_all(engine)

client = TestClient(app)


def test_status():
    r = client.get("/status")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_add_and_list_transaction():
    payload = {
        "amount": 12.34,
        "description": "test tx",
        "date": "2025-12-17T00:00:00",
        "source": "manual"
    }
    r = client.post("/", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data.get("amount") == 12.34
    # now list
    r2 = client.get("/")
    assert r2.status_code == 200
    items = r2.json()
    assert any(x.get("amount") == 12.34 for x in items)


def test_summary_endpoint():
    r = client.get("/summary")
    assert r.status_code == 200
    j = r.json()
    assert "total_income" in j and "total_expenses" in j and "balance" in j
