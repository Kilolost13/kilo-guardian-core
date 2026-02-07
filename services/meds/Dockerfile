FROM python:3.11-slim
RUN mkdir -p /app
WORKDIR /app
# Copy shared models first
COPY shared /app/shared
# Copy service code
COPY services/meds /app/meds
WORKDIR /app/meds
# Install dependencies (pyproject.toml is now in /app/meds)
RUN pip install --upgrade pip && pip install poetry && poetry config virtualenvs.create false && poetry install --no-interaction --no-root
RUN mkdir -p /data
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
COPY services/meds/wait-for-advanced.py /app/wait-for-advanced.py
COPY services/meds/wait-for.sh /app/wait-for.sh
RUN chmod +x /app/wait-for-advanced.py /app/wait-for.sh || true
ENV PYTHONPATH=/app
CMD ["/app/wait-for.sh"]
