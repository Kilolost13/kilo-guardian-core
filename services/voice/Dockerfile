FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory for voice models
RUN mkdir -p /data/voice_models

EXPOSE 9009

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9009"]
