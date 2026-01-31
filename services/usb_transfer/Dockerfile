FROM python:3.11-slim

# Install system dependencies for USB handling
RUN apt-get update && apt-get install -y \
    usbutils \
    udev \
    cryptsetup \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy shared models first (for future use)
COPY shared /app/shared

# Copy service code
COPY services/usb_transfer /app/usb_transfer
WORKDIR /app/usb_transfer

# Copy requirements and install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create config directory
RUN mkdir -p /etc/kilo

# Expose port
EXPOSE 8006

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8006/health || exit 1

# Ensure Python can import the package from /app
ENV PYTHONPATH=/app

# Run the application via uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8006"]