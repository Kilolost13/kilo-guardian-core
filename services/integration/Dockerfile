FROM ghcr.io/kilolost13/microservice-integration-base:ci

# Create a non-root user for running the integration runner (base already
# creates the app user, but keep args for local overrides)
ARG APP_USER=app
ARG APP_UID=1000
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Copy only what's needed for the integration runner to keep image small
COPY microservice/integration/requirements.txt ./microservice/integration/requirements.txt
COPY microservice/integration/test_runner.py ./microservice/integration/test_runner.py

# Copy the services so uvicorn can import them
COPY microservice ./microservice

# Install app-level requirements (fastapi, uvicorn, sqlmodel, etc.)
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install -r microservice/integration/requirements.txt

# create runtime directories and make sure the app user owns them
RUN mkdir -p /app/data /tmp && chown -R ${APP_USER}:${APP_USER} /app

USER ${APP_USER}
WORKDIR /app/microservice/integration

EXPOSE 8001 8002 8003 9000

CMD ["python3", "test_runner.py"]