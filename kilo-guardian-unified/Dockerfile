FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Build args: set INSTALL_ML=true to install heavy ML deps (sentence-transformers, faiss, torch)
ARG INSTALL_ML=false

# Install system dependencies needed to build some Python wheels
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential gcc curl git libsndfile1 libgl1 nmap wireguard wireguard-tools openvpn && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements-prod.txt /app/requirements-prod.txt
COPY requirements-ml.txt /app/requirements-ml.txt

# Install production requirements first
RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r /app/requirements-prod.txt

# Optionally install ML requirements (may add large native deps)
RUN if [ "${INSTALL_ML}" = "true" ] ; then \
    pip install --no-cache-dir -r /app/requirements-ml.txt ; \
    else \
    echo "Skipping ML requirements (BUILD_ARG INSTALL_ML not true)" ; \
    fi

# Copy the full project
COPY . /app

# Ensure entrypoint is executable and set ownership
RUN chmod +x /app/entrypoint.sh && \
    groupadd -r kilo && useradd -r -g kilo kilo && chown -R kilo:kilo /app

ENV PATH="/home/kilo/.local/bin:$PATH"
USER kilo

# Expose the internal app port (matches .env.example PORT)
EXPOSE 8001

ENTRYPOINT ["/app/entrypoint.sh"]
