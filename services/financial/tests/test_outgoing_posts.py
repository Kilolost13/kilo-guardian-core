import time
from fastapi.testclient import TestClient
from financial.main import app, engine
from sqlmodel import SQLModel
import httpx
import pytesseract


# Ensure DB tables exist for tests
SQLModel.metadata.create_all(engine)

client = TestClient(app)


class DummyAsyncClient:
    """A very small async-client replacement that records post() calls."""
    def __init__(self, *a, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json=None, timeout=None):
        # this attribute will be set by tests to capture calls
        if hasattr(self, "_capture") and callable(self._capture):
            return await self._capture(url, json=json, timeout=timeout)
        class R:
            status_code = 200

        return R()


def test_send_transaction_to_ai_brain(monkeypatch):
    calls = []

    async def fake_post(url, json=None, timeout=None):
        calls.append((url, json))
        class R:
            status_code = 200

        return R()

    # Monkeypatch AsyncClient to our dummy and attach the fake_post as _capture
    monkeypatch.setattr(httpx, "AsyncClient", DummyAsyncClient)
    DummyAsyncClient._capture = staticmethod(fake_post)

    payload = {"amount": 1.23, "description": "t", "date": "2025-12-17T00:00:00"}
    r = client.post("/", json=payload)
    assert r.status_code == 200

    # background tasks in TestClient run after response; poll briefly for call
    for _ in range(20):
        if calls:
            break
        time.sleep(0.05)

    assert calls, "no outgoing post captured"
    url, jsonp = calls[0]
    assert "ingest/finance" in url
    assert jsonp["amount"] == 1.23


def test_receipt_outgoing(monkeypatch):
    calls = []

    async def fake_post(url, json=None, timeout=None):
        calls.append((url, json))
        class R:
            status_code = 200

        return R()

    monkeypatch.setattr(httpx, "AsyncClient", DummyAsyncClient)
    DummyAsyncClient._capture = staticmethod(fake_post)

    # Mock OCR output so tests don't require system tesseract
    monkeypatch.setattr(pytesseract, "image_to_string", lambda img: "Milk 2.99\nBread 1.50\n")

    # create a tiny valid PNG so PIL can open it during the request
    from PIL import Image
    img = Image.new('RGB', (1, 1), color='white')
    img.save("/tmp/receipt_test.png", "PNG")

    with open("/tmp/receipt_test.png", "rb") as f:
        files = {"file": ("receipt.png", f, "image/png")}
        r = client.post("/receipt", files=files)

    assert r.status_code == 200

    for _ in range(20):
        if calls:
            break
        time.sleep(0.05)

    assert calls, "no outgoing receipt post captured"
    url, jsonp = calls[0]
    assert "ingest/receipt" in url
    assert "Milk" in jsonp["text"]
