import os
import time
import requests
from PIL import Image, ImageDraw


def test_financial_receipt_end_to_end():
    # Only run in integration CI when explicitly enabled
    if os.getenv("RUN_ACCEPTANCE", "false").lower() != "true":
        import pytest

        pytest.skip("Acceptance tests disabled")

    base = "http://127.0.0.1:9005"
    ai_brain = "http://127.0.0.1:9004"

    # wait for financial service to be ready
    for _ in range(60):
        try:
            r = requests.get(f"{base}/status", timeout=2)
            if r.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        raise AssertionError("financial service not ready")

    # create a small sample receipt image with clear OCR-friendly text
    img = Image.new("RGB", (400, 120), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    text = "Milk 2.99\nBread 1.50\n"
    draw.text((10, 10), text, fill=(0, 0, 0))
    path = "/tmp/ci_sample_receipt.png"
    img.save(path)

    with open(path, "rb") as f:
        files = {"file": ("receipt.png", f, "image/png")}
        r = requests.post(f"{base}/receipt", files=files, timeout=30)

    assert r.status_code == 200

    # Give background task a moment and check ai_brain received the ingest
    for _ in range(20):
        try:
            rr = requests.get(f"{ai_brain}/received", timeout=2)
            if rr.status_code == 200 and rr.json():
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        raise AssertionError("ai_brain did not receive any posts")

    received = rr.json()
    assert any(r.get("path") == "/ingest/receipt" for r in received), f"no receipt ingest found in {received}"
