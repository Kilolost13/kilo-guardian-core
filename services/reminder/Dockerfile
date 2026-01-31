FROM python:3.11-slim
RUN mkdir -p /app
WORKDIR /app
# Copy shared models first
COPY shared /app/shared
# Copy service code
COPY services/reminder /app/reminder
WORKDIR /app/reminder
# Install dependencies
RUN pip install --upgrade pip && pip install poetry && poetry config virtualenvs.create false && poetry install --no-interaction --no-root
RUN mkdir -p /data
RUN apt-get update && rm -rf /var/lib/apt/lists/*
ENV PYTHONPATH=/app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9002"]
