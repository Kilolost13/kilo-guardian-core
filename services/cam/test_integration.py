import pytest
from fastapi.testclient import TestClient
from cam.main import app
import io
from PIL import Image

client = TestClient(app)

def make_dummy_image():
    img = Image.new('RGB', (100, 100), color = 'red')
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    buf.seek(0)
    return buf

def test_ocr_image(monkeypatch):
    # Patch httpx.AsyncClient.post to avoid real network call
    async def fake_post(*args, **kwargs):
        class Resp: status_code = 200
        async def json(self): return {"status": "ok"}
        return Resp()
    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    img = make_dummy_image()
    response = client.post("/ocr", files={"file": ("test.jpg", img, "image/jpeg")})
    assert response.status_code == 200
    assert "text" in response.json()

def test_analyze_pose(monkeypatch):
    async def fake_post(*args, **kwargs):
        class Resp: status_code = 200
        async def json(self): return {"status": "ok"}
        return Resp()
    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    img = make_dummy_image()
    response = client.post("/analyze_pose", files={"file": ("test.jpg", img, "image/jpeg")})
    assert response.status_code == 200
    assert "posture" in response.json()

def test_compare_pose(monkeypatch):
    async def fake_post(*args, **kwargs):
        class Resp: status_code = 200
        async def json(self): return {"status": "ok"}
        return Resp()
    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    img1 = make_dummy_image()
    img2 = make_dummy_image()
    response = client.post("/compare_pose", files={"user_image": ("user.jpg", img1, "image/jpeg"), "reference_image": ("ref.jpg", img2, "image/jpeg")})
    assert response.status_code == 200
    assert "match" in response.json()
