AI Orchestration: Sedentary / Meds / Habits

New endpoints (ai_brain service)

- POST /reminder/sedentary
  - Body: {"user_id": "<user>"}
  - Creates a sedentary tracking session for that user and schedules 3 reminders at +1h/+2h/+3h via the `reminder` service (if available).

- POST /ingest/cam
  - Body: {"user_id": "<user>", "face_id": "<face>", "posture": "sitting|standing|walking", "timestamp": "ISO8601", "location_hash": "...", "image_id": "..."}
  - Saves cam reports and updates sedentary state. Camera should report every 5–10s.

- POST /meds/upload
  - Body: {"user_id":"<user>", "med_name":"Aspirin", "dosage":"100mg", "schedule_text":"once daily at 08:00"}
  - Stores med record and creates reminders based on parsed schedule (next occurrence).

- POST /reminder/meds/confirm
  - Body: {"user_id":"<user>", "med_id":123, "taken": true}
  - Logs adherence to the med.

- POST /events
  - Generic habit events ingestion: {"user_id":"<user>", "event_type":"wake_time", "timestamp":"ISO8601"}

- GET /user/{user_id}/habits
  - Returns simple habit profiles per event type (mean, stddev, frequency, confidence).

DB and storage

- Uses SQLite by default at `/tmp/ai_brain.db` (configurable via `AI_BRAIN_DB` env var). Models are defined in `ai_brain/models.py`.
- Tables are auto-created on startup.

Scheduler and reminders

- The service calls the existing `reminder` microservice to add scheduled reminders. If the `reminder` service is not available (tests/local), the calls are logged and the med/sedentary records are still saved locally.

Running tests

From `microservice` directory:

```bash
# run unit tests for orchestrator
PYTHONPATH=. pytest -q ai_brain/tests/test_orchestrator.py
```

Example curl payloads

Create sedentary session:

```bash
curl -X POST http://127.0.0.1:9004/reminder/sedentary -H 'Content-Type: application/json' -d '{"user_id":"user1"}'
```

Send camera report:

```bash
curl -X POST http://127.0.0.1:9004/ingest/cam -H 'Content-Type: application/json' -d '{"user_id":"user1","posture":"sitting","timestamp":"2025-12-16T12:00:00"}'
```

Upload med from OCR:

```bash
curl -X POST http://127.0.0.1:9004/meds/upload -H 'Content-Type: application/json' -d '{"user_id":"user1","med_name":"Aspirin","dosage":"100mg","schedule_text":"08:00"}'
```

Log med adherence:

```bash
curl -X POST http://127.0.0.1:9004/reminder/meds/confirm -H 'Content-Type: application/json' -d '{"user_id":"user1","med_id":1,"taken":true}'
```

Notes & next steps

- Habit anomaly detection: basic profile computation is implemented; anomaly-to-notification wiring can be added to check on new events and call the `reminder` service when confidence threshold is met.
- Privacy & opt-out: per-user opt-out flag and more granular controls can be added to the user profile and checked before tracking; implement as needed.
