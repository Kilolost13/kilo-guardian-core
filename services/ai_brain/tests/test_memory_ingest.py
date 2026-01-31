from fastapi.testclient import TestClient
from sqlmodel import select
import sys
import pathlib


def test_ingest_creates_memory():
    # Ensure repository root is on sys.path so microservice.* imports succeed
    # file is .../microservice/ai_brain/tests/<file>, so go up 3 to reach repo root
    repo_root = pathlib.Path(__file__).resolve().parents[3]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from ai_brain.main import app
    from ai_brain.db import get_session
    from shared.models import Memory

    client = TestClient(app)
    with client:
        resp = client.post("/ingest/receipt", json={"text": "Apple 1.00\nBanana 2.00\n"})
        assert resp.status_code == 200
        sess = get_session()
        # Try to query via SQLModel class
        results = sess.exec(select(Memory)).all()
        # As a fallback, check raw SQL table count to ensure table exists and rows inserted
        try:
            raw = sess.execute("SELECT COUNT(*) as c FROM memory").fetchone()
            raw_count = raw[0] if raw is not None else 0
        except Exception:
            raw_count = 0
        # Expect at least one memory related to the receipt or items
        assert (raw_count > 0) or any((m.text_blob and ("Apple" in m.text_blob or "purchased:Apple" in m.text_blob)) for m in results), f"No receipt memory found (raw_count={raw_count}, results={results})"
