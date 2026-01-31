# ai_brain

Run and environment notes for the ai_brain service.

Required env vars (development):

- STT_PROVIDER (default: none) - e.g. `openai`
- TTS_PROVIDER (default: none) - e.g. `gtts`
- LLM_PROVIDER (default: none) - e.g. `ollama`
- OLLAMA_BIN (optional) - path to local `ollama` binary
- OLLAMA_MODEL (optional) - model name for ollama fallback
- AI_BRAIN_CALLBACK_URL - public callback URL for reminders (optional)
- CALLBACK_SECRET - HMAC secret for verifying reminder callbacks (optional)

Docker build/run (from `microservice/`):

```bash
# build and start ai_brain only
docker-compose build ai_brain
docker-compose up -d ai_brain

# tail logs
docker-compose logs -f ai_brain
```

Smoke-test (from project root):

```bash
./scripts/smoke_test.sh localhost 9004 8000
```

Notes:
- The Dockerfile runs the service as the `ai_brain` package (`uvicorn ai_brain.main:app`) so relative imports inside the package resolve correctly.
- If you see import errors in container logs, ensure `PYTHONPATH=/app` or that the package is present at `/app/ai_brain` inside the image.
