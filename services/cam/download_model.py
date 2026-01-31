#!/usr/bin/env python3
"""Download mediapipe model if MODEL_URL provided via env var.
This avoids installing curl in the image and uses urllib instead.
"""
import os
import sys
from urllib.request import urlopen


def download(url: str, dest: str) -> bool:
    try:
        with urlopen(url, timeout=10) as r, open(dest, "wb") as f:
            f.write(r.read())
        return True
    except Exception as e:
        print(f"download failed: {e}")
        return False


def main():
    url = os.environ.get("MODEL_URL")
    if not url:
        print("MODEL_URL not set; skipping model download")
        return 0
    dest = "/app/pose_landmarker_lite.task"
    if os.path.exists(dest):
        print("model already present; skipping")
        return 0
    print(f"downloading model from {url} to {dest}")
    ok = download(url, dest)
    if not ok:
        print("model download failed; continuing without model")
    else:
        print("model downloaded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
