FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including cron
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory for models
RUN mkdir -p /data/ml_models

# Set up cron job for nightly training
COPY crontab /etc/cron.d/ml-training
RUN chmod 0644 /etc/cron.d/ml-training && \
    crontab /etc/cron.d/ml-training && \
    touch /var/log/cron.log

# Make training script executable
RUN chmod +x /app/train_models.py

EXPOSE 9008

# Start cron in background and then start uvicorn
CMD cron && uvicorn main:app --host 0.0.0.0 --port 9008
