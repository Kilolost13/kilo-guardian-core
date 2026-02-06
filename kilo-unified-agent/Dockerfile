# ---------------------------------------------------------------------------
# Kilo Unified Agent  --  container image
# Build:  docker build -t kilo/unified-agent:latest .
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS deps
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------------------
FROM python:3.11-slim
WORKDIR /app

# kubectl (needed for k3s_controller)
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    curl -sLO https://dl.k8s.io/release/$(curl -sL https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl && \
    chmod +x kubectl && mv kubectl /usr/local/bin/ && \
    rm -rf /var/lib/apt/lists/*

COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY main.py service_registry.py k3s_controller.py command_router.py proactive_monitor.py ./

EXPOSE 9200
HEALTHCHECK --interval=15s --timeout=3s CMD curl -sf http://localhost:9200/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9200"]
