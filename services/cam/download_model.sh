#!/usr/bin/env bash
# Download the MediaPipe pose landmarker model to cam/pose_landmarker_lite.task
# Expects MODEL_URL env var. If not set, will exit 0 (skip).
set -euo pipefail
if [ -z "${MODEL_URL:-}" ]; then
  echo "MODEL_URL not set; skipping download"
  exit 0
fi
mkdir -p cam
curl -fsSL "$MODEL_URL" -o cam/pose_landmarker_lite.task
ls -lh cam/pose_landmarker_lite.task
