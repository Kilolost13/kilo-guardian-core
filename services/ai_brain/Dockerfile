FROM python:3.11-slim
WORKDIR /app

# Copy shared models from the monorepo root (build context is repo root)
COPY shared /app/shared

# Copy source into /app/ai_brain so the package is available as 'ai_brain'
COPY services/ai_brain /app/ai_brain

# Copy models directory for offline/air-gapped deployment (if exists)
# Run package_models.sh first to populate this directory
# The models directory should be at the parent level (../models)
RUN mkdir -p /app/models
RUN pip install --upgrade pip

# Install dependencies from inside the package folder
WORKDIR /app/ai_brain
RUN pip install poetry \
	&& poetry config virtualenvs.create false \
	&& poetry install --no-interaction --no-root

RUN mkdir -p /data
RUN apt-get update && apt-get install -y tesseract-ocr && rm -rf /var/lib/apt/lists/*

# Set environment variables for offline model loading
ENV SENTENCE_TRANSFORMERS_HOME=/app/models/sentence_transformers
ENV TRANSFORMERS_CACHE=/app/models/transformers_cache
ENV HF_HOME=/app/models/huggingface_cache
ENV TESSDATA_PREFIX=/app/models/tesseract

# Ensure Python can import the package from /app
ENV PYTHONPATH=/app

# Run as a package so relative imports inside ai_brain work correctly
CMD ["uvicorn", "ai_brain.main:app", "--host", "0.0.0.0", "--port", "9004"]
