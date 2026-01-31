# Integration test image and runner

This folder contains the integration test runner and Dockerfiles used to run end-to-end checks
for the microservices locally and in CI.

What’s in here
- `Dockerfile.base` - prebuilt base image that contains heavy system dependencies (Tesseract, dev libs) and common Python runtime packages (Pillow, pytesseract). This image is intended to be built infrequently and pushed to GHCR.
- `Dockerfile` - integration image that `FROM` the base image and installs only app-level requirements.
- `test_runner.py` - the existing integration runner that starts services and exercises flows.
- `tests/` - pytest wrapper that calls the runner so CI can run it as a test.

Local quickstart

1) Build and tag the base image locally (matches CI behavior):

```bash
# from repository root
docker build -f microservice/integration/Dockerfile.base -t microservice-integration-base:local microservice/integration
```

2) Build the integration image that uses the base:

```bash
docker build -f microservice/integration/Dockerfile -t ms-integration:local .
```

3) Run the integration tests inside the image (mount the repo so new tests are available):

```bash
docker run --rm -u 0 -v "$PWD":/src -w /src ms-integration:local sh -c "python3 -m pip install --upgrade pip pytest requests && pytest microservice/integration/tests -q"
```

Notes
- CI pushes the base image to GHCR so downstream builds can `FROM ghcr.io/<org>/microservice-integration-base:...` and avoid reinstalling heavy OS packages on every run.
- To mirror CI tagging locally, tag the base image with `ghcr.io/<your-org>/microservice-integration-base:<sha-or-tag>` and push it to your registry.
Integration test runner

This folder contains a lightweight integration test runner that:

- Starts a mock HTTP server to capture outgoing callbacks
- Starts the key microservices (ai_brain, reminder, financial) with uvicorn
- Waits for their /status endpoints to become available
- Exercises reminder -> callback flow and basic status endpoints

Usage (locally):

```bash
# from repository root
python3 microservice/integration/test_runner.py
```

To run inside Docker (optional):

```bash
# Build from repository root so the Docker build context includes the `microservice/` package
docker build -f microservice/integration/Dockerfile -t ms-integration .
# Run (host networking recommended for quick local verification)
docker run --rm --network host ms-integration

If you mount a host `microservice/` directory into `/app/microservice` when running the container, make sure you do not change the internal structure expected by the runner. Prefer running the container without volume mounts in CI.
```

Notes:
- The runner runs uvicorn processes directly and uses in-container ports 8001/8002/8003.
- For CI, run this container on a host/runner that allows binding to required ports or adapt to start services via docker-compose instead.
