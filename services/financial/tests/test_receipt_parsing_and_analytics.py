from fastapi.testclient import TestClient
from financial.main import app, engine, _parse_receipt_items
from sqlmodel import SQLModel
import pytesseract

# Ensure DB tables exist for tests
SQLModel.metadata.create_all(engine)
client = TestClient(app)


def test_parse_receipt_detection_and_normalization():
    text = """
    Milk 2,99
    Bread 1.50
    Total 4,49
    """
    items, detected = _parse_receipt_items(text)
    assert detected is not None
    assert abs(detected - 4.49) < 0.001
    assert len(items) == 2
    names = [i['name'].lower() for i in items]
    assert any('milk' in n for n in names)
    assert any('bread' in n for n in names)


def test_receipt_upload_and_summary(monkeypatch):
    # Mock OCR output
    monkeypatch.setattr(pytesseract, "image_to_string", lambda img: "Milk 2.99\nBread 1.50\nTotal 4.49\n")

    # create a tiny valid PNG so PIL can open it (OCR is mocked)
    from PIL import Image
    img = Image.new('RGB', (1, 1), color='white')
    img.save("/tmp/receipt_test.png", "PNG")

    with open("/tmp/receipt_test.png", "rb") as f:
        files = {"file": ("receipt.png", f, "image/png")}
        r = client.post("/receipt", files=files)

    assert r.status_code == 200
    j = r.json()
    tx = j.get("transaction")
    items = j.get("items")
    assert tx is not None
    assert abs(tx.get("amount") - 4.49) < 0.01
    assert len(items) == 2

    # check summary includes spend_by_category and groceries should be present
    r2 = client.get("/summary")
    assert r2.status_code == 200
    s = r2.json()
    assert "spend_by_category" in s
    sbc = s["spend_by_category"]
    assert any(k in sbc for k in ("groceries", "other"))
