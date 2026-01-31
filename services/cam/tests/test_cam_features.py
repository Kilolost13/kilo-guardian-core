import os
import sys
from pathlib import Path
import tempfile
import json
import numpy as np
import cv2
from fastapi.testclient import TestClient

# make repo root importable
repo_root = str(Path(__file__).resolve().parents[3])
sys.path.insert(0, repo_root)

from microservice.cam.main import app, EMB_PATH

client = TestClient(app)


def _create_blank_image(w=320, h=240, color=(255,255,255)):
    img = np.zeros((h,w,3), dtype=np.uint8)
    img[:] = color
    return img


def _create_full_basket_image(w=320, h=240):
    img = _create_blank_image(w,h)
    # draw dark rectangle in center to simulate fullness
    cv2.rectangle(img, (int(w*0.25), int(h*0.25)), (int(w*0.75), int(h*0.75)), (30,30,30), -1)
    return img


def _img_to_bytes(img):
    _, buf = cv2.imencode('.jpg', img)
    return buf.tobytes()


def test_basket_fullness():
    img_full = _create_full_basket_image()
    calls = []
    # capture external calls (reminder create)
    def fake_get(url, *args, **kwargs):
        # return a dummy presets listing
        class R:
            status_code = 200
            def json(self):
                return [{'id': 1, 'name': 'laundry'}]
        calls.append(('get', url))
        return R()
    def fake_post(url, *args, **kwargs):
        calls.append(('post', url))
        class R:
            status_code = 200
        return R()
    # monkeypatch requests.get/post only for the duration of this test and restore
    import microservice.cam.main as cammod
    orig_get = cammod.requests.get
    orig_post = cammod.requests.post
    cammod.requests.get = fake_get
    cammod.requests.post = fake_post
    try:
        resp = client.post('/analyze_basket', files={'file': ('full.jpg', _img_to_bytes(img_full), 'image/jpeg')})
    finally:
        cammod.requests.get = orig_get
        cammod.requests.post = orig_post
    assert resp.status_code == 200
    j = resp.json()
    assert 'fullness' in j
    assert j['fullness'] > 0.2

    img_empty = _create_blank_image()
    resp = client.post('/analyze_basket', files={'file': ('empty.jpg', _img_to_bytes(img_empty), 'image/jpeg')})
    assert resp.status_code == 200
    j = resp.json()
    assert j['fullness'] < 0.05
    # ensure reminder create was invoked for full image
    assert any('presets' in url for t, url in calls if t == 'get')
    assert any('/presets/' in url and '/create' in url for t, url in calls if t == 'post')


def test_face_register_and_recognize(tmp_path, monkeypatch):
    # ensure fresh embeddings
    try:
        os.remove(EMB_PATH)
    except Exception:
        pass
    img = _create_blank_image()
    cv2.circle(img, (160,120), 40, (50,50,50), -1)
    b = _img_to_bytes(img)
    r = client.post('/register_face', data={'name':'kyle'}, files={'file':('k.jpg', b, 'image/jpeg')})
    assert r.status_code == 200
    # recognize same image
    r2 = client.post('/recognize_face', files={'file':('k2.jpg', b, 'image/jpeg')})
    assert r2.status_code == 200
    j = r2.json()
    assert j['name'] == 'kyle'
    assert j['score'] > 0.8


def test_detect_activity_and_notify(monkeypatch):
    calls = []
    def fake_post(url, json=None, timeout=None):
        calls.append((url, json))
        class R: pass
        return R()
    monkeypatch.setattr('microservice.cam.main.requests.post', fake_post)
    # create image with large dark blob
    img = _create_full_basket_image()
    resp = client.post('/detect_activity', files={'file':('act.jpg', _img_to_bytes(img), 'image/jpeg')})
    assert resp.status_code == 200
    j = resp.json()
    assert 'activities' in j
    assert 'cooking' in j['activities'] or 'present' in j['activities']
    # ensure ai_brain notified
    assert calls
