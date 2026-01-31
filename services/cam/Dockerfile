FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --upgrade pip && pip install poetry && poetry config virtualenvs.create false && poetry install --no-interaction --no-root
# Install system dependencies for camera access and OpenCV
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    v4l-utils \
    && rm -rf /var/lib/apt/lists/*
# model download is handled at runtime by /app/download_model.py to avoid curl dependency
COPY ./download_model.py /app/download_model.py
COPY . .
# copy wait-for script and make executable
COPY wait-for.sh /app/wait-for.sh
RUN chmod +x /app/wait-for.sh /app/download_model.py || true
# Wait for ai_brain to be healthy before starting; downloader runs inside wait-for wrapper
CMD ["/app/wait-for.sh", "ai_brain:9004", "--", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9007"]
