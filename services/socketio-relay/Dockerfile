FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    python-socketio==5.11.0 \
    aiohttp==3.9.1

# Copy application
COPY main.py .

# Expose port
EXPOSE 9010

# Run the application
CMD ["python", "main.py"]
