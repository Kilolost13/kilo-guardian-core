AI Brain STT/TTS Integration Guide

Overview

This document explains how to enable and configure Speech-to-Text (STT) and Text-to-Speech (TTS) providers for the `ai_brain` microservice.

Environment variables (in `.env` or container):

- STT_PROVIDER: 'none' (default) or 'openai'
- TTS_PROVIDER: 'none' (default) or 'gtts'
- PROVIDER_API_KEY: API key for provider when needed (e.g., OpenAI)
- GATEWAY_URL: URL used by integration tests (default: http://127.0.0.1:8001)

Enabling OpenAI Whisper (STT)

1. Sign up and get an OpenAI API key.
2. Set environment variables:

```bash
STT_PROVIDER=openai
PROVIDER_API_KEY=sk-xxxx
```

3. The `ai_brain` service will send audio uploads to OpenAI's transcription endpoint using `model=\"whisper-1\"`.

Notes:
- The current implementation uses `requests` to post audio to OpenAI's `v1/audio/transcriptions` endpoint. It can be replaced with the OpenAI Python SDK on request.
- Ensure the container has network access to api.openai.com and the API key is kept secret (use docker secrets or a vault in production).

Enabling gTTS (TTS)

1. No API key required; gTTS uses Google's translate TTS service via the `gTTS` Python library.
2. Set environment variable:

```bash
TTS_PROVIDER=gtts
```

3. When enabled, responses from `/chat/voice` will include `tts_base64` containing base64-encoded MP3 audio.

Production considerations

- Move blocking provider calls to background tasks or separate worker processes.
- Add retry/backoff and better error handling for provider HTTP calls.
- Use docker secrets or a secret manager for API keys.
- Consider higher-quality paid TTS providers (ElevenLabs, Amazon Polly) for production-grade audio.

Background TTS mode

The `ai_brain` service supports two TTS modes for `/chat/voice`:

- inline (default): TTS is generated within the request and returned as `tts_base64` in the response.
- background: the service will schedule TTS generation and return a `tts_url` you can poll; the file will be written to `/data` and served at `/tts/{filename}`.

To request background mode, include a `tts_mode=background` form field when calling `/chat/voice`. The inline mode is used by default to keep compatibility with existing callers and integration tests.

Running integration tests

From the `microservice` directory:

```bash
# ensure services are up (docker compose up -d --build)
python3 tests/integration_test.py
```

If integration tests fail, inspect logs:

```bash
docker compose logs ai_brain
```

Contact

If you want me to wire additional providers (ElevenLabs, OpenAI SDK, or async background workers), tell me which provider and I'll implement it and add CI.