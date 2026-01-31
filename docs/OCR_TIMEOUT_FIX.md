# Prescription OCR Timeout Fix - Implementation Summary
**Date:** 2026-01-04
**Status:** ✅ IMPLEMENTED - Ready for Deployment

---

## Problem Identified

### Root Cause
Prescription OCR was timing out because:
1. **Gateway timeout:** Only 30 seconds
2. **OCR processing time:** 15-50+ seconds (preprocessing + Tesseract OCR)
3. **Result:** Requests timing out, images discarded, no medication added

### Evidence
```
Gateway logs:
Proxy request error to meds http://kilo-meds:9001/extract (attempt 1) after 30.00s:
INFO: 10.42.0.183:59732 - "POST /meds/extract HTTP/1.1" 500 Internal Server Error
```

---

## Solution Implemented

### NEW WORKFLOW (Async Processing with Polling)

```
┌──────────────┐
│ 1. Tablet    │ Captures prescription image
│ captures     │
└──────┬───────┘
       │ POST /meds/extract (image blob)
       ▼
┌──────────────┐
│ 2. Meds      │ • Saves image to disk immediately
│ Service      │ • Creates OcrJob record (status="pending")
│              │ • Returns job_id to frontend
│              │ • Queues background worker
└──────┬───────┘
       │ Response: {job_id: "uuid", status: "pending"}
       ▼
┌──────────────┐
│ 3. Frontend  │ • Receives job_id
│ starts       │ • Starts polling every 3 seconds
│ polling      │ • Shows "⏳ SCANNING..." to user
└──────┬───────┘
       │ GET /meds/extract/{job_id}/status (every 3s)
       ▼
┌──────────────┐
│ 4. Background│ • Loads image from disk
│ Worker       │ • Preprocesses (upscale, denoise, threshold) [5-10s]
│ processes    │ • Runs Tesseract OCR [10-40s]
│ OCR          │ • Parses medication data (regex)
│              │ • Saves Med to database
│              │ • Updates job status="completed"
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ 5. Frontend  │ • Polls and sees status="completed"
│ receives     │ • Displays medication data
│ result       │ • Refreshes medications list
│              │ • Shows "✓ Added [Med Name]!"
└──────────────┘
```

---

## Code Changes

### 1. Backend: Meds Service (`services/meds/main.py`)

#### Added New Model
```python
class OcrJob(SQLModel, table=True):
    """Track OCR processing jobs for async processing"""
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: str = Field(index=True, unique=True)  # UUID
    status: str = Field(default="pending")  # pending, processing, completed, failed
    created_at: str
    completed_at: Optional[str] = None
    image_path: str = ""  # Path to saved image on disk
    ocr_text: Optional[str] = None  # Raw OCR output
    error_message: Optional[str] = None
    medication_id: Optional[int] = None
    result_data: Optional[str] = None  # JSON string
```

#### Modified `/extract` Endpoint
- **Before:** Synchronous OCR processing (15-50s), returned medication immediately
- **After:**
  - Saves image to `/data/prescription_images/{uuid}.jpg`
  - Creates `OcrJob` record
  - Queues background task
  - **Returns immediately** with `job_id` (~100ms response time)

#### Added New Endpoints
```python
GET /extract/{job_id}/status
# Returns: {status, job_id, created_at, completed_at, result?, error?}

GET /extract/{job_id}/result
# Returns medication data when completed
# HTTP 202 if still processing
# HTTP 500 if failed
```

#### Added Background Worker
```python
def process_ocr_job(job_id: str):
    # Load image from disk
    # Preprocess image
    # Run Tesseract OCR
    # Parse medication data
    # Save to database
    # Update job status
```

### 2. Frontend: Medications Page (`frontend/src/pages/Medications.tsx`)

#### Updated `handlePrescriptionCapture`
- **Before:** Waited for synchronous response (30s+ wait, then timeout)
- **After:**
  - Submits image → receives `job_id`
  - Polls `/meds/extract/{job_id}/status` every 3 seconds
  - Max 60 polls (3 minutes total)
  - Displays result when `status === "completed"`
  - Shows error if `status === "failed"`

```typescript
const { job_id } = await api.post('/meds/extract', formData);

// Poll for results every 3 seconds
while (pollCount < maxPolls) {
  const statusResponse = await api.get(`/meds/extract/${job_id}/status`);

  if (status === 'completed') {
    setScanResult({ success: true, message: `✓ Added ${result.name}!`, data: result });
    fetchMedications();
    return;
  } else if (status === 'failed') {
    setScanResult({ success: false, message: error });
    return;
  }

  await sleep(3000); // Wait 3 seconds before next poll
}
```

### 3. Gateway Service (`services/gateway/main.py`)

#### Increased Timeout
```python
# Before
async with httpx.AsyncClient(timeout=30.0) as client:

# After
async with httpx.AsyncClient(timeout=120.0) as client:  # Increased for OCR/LLM
```

**Note:** While not strictly necessary (since `/extract` now returns immediately), this provides safety margin for other slow endpoints.

---

## Image Persistence

### Storage Location
```
/data/prescription_images/
├── {uuid1}.jpg  (saved prescription image)
├── {uuid2}.jpg
└── {uuid3}.jpg
```

### Benefits
1. ✅ **No data loss:** Images persisted even if processing fails
2. ✅ **Retry capability:** Can reprocess failed jobs later
3. ✅ **Audit trail:** Keep history of scanned prescriptions
4. ✅ **Debugging:** Can review original images for OCR failures

### Cleanup (Optional Future Enhancement)
```python
# Delete images older than 30 days
@app.on_event("startup")
async def cleanup_old_images():
    cutoff = datetime.utcnow() - timedelta(days=30)
    for image_file in IMAGE_STORAGE_DIR.glob("*.jpg"):
        if image_file.stat().st_mtime < cutoff.timestamp():
            image_file.unlink()
```

---

## Deployment Instructions

### Step 1: Rebuild Meds Service

```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice/services/meds

# Build new Docker image
docker build -t kilo-meds:v2 .

# Save to tar
docker save kilo-meds:v2 -o /tmp/kilo-meds-v2.tar

# Import to k3s
sudo k3s ctr images import /tmp/kilo-meds-v2.tar

# Update deployment
kubectl set image deployment/kilo-meds meds=kilo-meds:v2 -n kilo-guardian

# Watch rollout
kubectl rollout status deployment/kilo-meds -n kilo-guardian
```

### Step 2: Rebuild Gateway Service

```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice/services/gateway

# Build and deploy
docker build -t kilo-gateway:v2 .
docker save kilo-gateway:v2 -o /tmp/kilo-gateway-v2.tar
sudo k3s ctr images import /tmp/kilo-gateway-v2.tar
kubectl set image deployment/kilo-gateway gateway=kilo-gateway:v2 -n kilo-guardian
kubectl rollout status deployment/kilo-gateway -n kilo-guardian
```

### Step 3: Rebuild Frontend

```bash
cd /home/kilo/Desktop/Kilo_Ai_microservice/frontend/kilo-react-frontend

# Build React app
npm run build

# Build Docker image
cd ../..
docker build -t kilo-frontend:v2 -f frontend/Dockerfile .
docker save kilo-frontend:v2 -o /tmp/kilo-frontend-v2.tar
sudo k3s ctr images import /tmp/kilo-frontend-v2.tar
kubectl set image deployment/kilo-frontend frontend=kilo-frontend:v2 -n kilo-guardian
kubectl rollout status deployment/kilo-frontend -n kilo-guardian
```

### Step 4: Verify Deployment

```bash
# Check all pods are running
kubectl get pods -n kilo-guardian

# Check meds service logs
kubectl logs deployment/kilo-meds -n kilo-guardian --tail=50

# Should see:
# [OCR] Saved image for job {uuid} to /data/prescription_images/{uuid}.jpg
# [OCR] Queued job {uuid} for processing
# [OCR] Starting processing for job {uuid}
# [OCR] Running Tesseract OCR...
# [OCR] Created medication: {name} (ID: {id})
# [OCR] Job {uuid} completed successfully
```

---

## Testing Procedure

### Manual Test
1. Open frontend: http://localhost:30000
2. Navigate to Medications page
3. Click "📷 SCAN PRESCRIPTION"
4. Capture a prescription image
5. Observe:
   - Button shows "⏳ SCANNING..."
   - Wait 15-45 seconds (processing time)
   - Success message appears: "✓ Added [Med Name]!"
   - Medication appears in list

### Expected Logs

**Frontend console:**
```
[OCR] Job submitted: abc-123-def, polling for results...
[OCR] Poll 1: status=pending
[OCR] Poll 2: status=processing
[OCR] Poll 3: status=processing
[OCR] Poll 4: status=completed
```

**Meds service logs:**
```
[OCR] Saved image for job abc-123-def to /data/prescription_images/abc-123-def.jpg
[OCR] Queued job abc-123-def for processing
[OCR] Starting processing for job abc-123-def
[OCR] Preprocessing image...
[OCR] Running Tesseract OCR...
[OCR] Extracted 247 characters of text
[OCR] Created medication: Lisinopril (ID: 5)
[OCR] Job abc-123-def completed successfully
```

### Error Cases to Test

1. **Bad image (no text):**
   - Expected: `status=completed` but `name=""` (empty)
   - Frontend shows: "Could not read medication name..."

2. **Invalid image format:**
   - Expected: HTTP 400 "File must be an image"

3. **Network interruption:**
   - Frontend will continue polling
   - Shows error after 60 polls (3 minutes)

---

## Performance Improvements

### Before (Synchronous)
```
User captures image
  ↓ (wait 15-50s...)
Gateway times out after 30s
  ↓
Frontend shows error
  ↓
Image discarded, no data saved
```

**User Experience:** ❌ Fails, frustrating

### After (Async)
```
User captures image
  ↓ (100ms)
Frontend receives job_id
  ↓ (shows "SCANNING...")
Background processes for 15-50s
  ↓ (polls every 3s)
Frontend receives result
  ↓
Shows "✓ Added [Med]!"
```

**User Experience:** ✅ Reliable, transparent progress

---

## Database Schema Changes

### New Table: `ocr_job`
```sql
CREATE TABLE ocr_job (
    id INTEGER PRIMARY KEY,
    job_id TEXT UNIQUE NOT NULL,  -- UUID
    status TEXT DEFAULT 'pending', -- pending/processing/completed/failed
    created_at TEXT NOT NULL,
    completed_at TEXT,
    image_path TEXT,
    ocr_text TEXT,
    error_message TEXT,
    medication_id INTEGER,
    result_data TEXT  -- JSON
);

CREATE INDEX idx_job_id ON ocr_job(job_id);
```

**Note:** SQLModel will create this table automatically on first startup.

---

## API Changes

### New Endpoints

| Method | Endpoint | Purpose | Response Time |
|--------|----------|---------|---------------|
| POST | `/meds/extract` | Submit image | ~100ms |
| GET | `/meds/extract/{job_id}/status` | Check status | ~10ms |
| GET | `/meds/extract/{job_id}/result` | Get result | ~10ms |

### Response Formats

**POST /meds/extract**
```json
{
  "job_id": "abc-123-def-456",
  "status": "pending",
  "message": "Image received. Processing in background...",
  "poll_url": "/extract/abc-123-def-456/status"
}
```

**GET /meds/extract/{job_id}/status** (pending)
```json
{
  "job_id": "abc-123-def-456",
  "status": "pending",
  "created_at": "2026-01-04T12:34:56"
}
```

**GET /meds/extract/{job_id}/status** (completed)
```json
{
  "job_id": "abc-123-def-456",
  "status": "completed",
  "created_at": "2026-01-04T12:34:56",
  "completed_at": "2026-01-04T12:35:23",
  "result": {
    "id": 5,
    "name": "Lisinopril",
    "dosage": "10 mg",
    "schedule": "Once daily",
    "quantity": 30,
    "prescriber": "Dr Smith",
    "instructions": "Take with food"
  },
  "ocr_text": "Full OCR text here..."
}
```

**GET /meds/extract/{job_id}/status** (failed)
```json
{
  "job_id": "abc-123-def-456",
  "status": "failed",
  "created_at": "2026-01-04T12:34:56",
  "completed_at": "2026-01-04T12:35:10",
  "error": "Image not found: /data/prescription_images/abc-123-def-456.jpg"
}
```

---

## Benefits

### Reliability
- ✅ **No more timeouts:** Processing happens in background
- ✅ **No data loss:** Images persisted to disk
- ✅ **Retry capability:** Can reprocess failed jobs
- ✅ **Audit trail:** Full history of OCR jobs

### User Experience
- ✅ **Faster response:** Immediate acknowledgment (~100ms)
- ✅ **Transparent progress:** Polling shows processing status
- ✅ **Clear feedback:** Success/failure messages
- ✅ **No more "failed to scan" errors** from timeouts

### System Performance
- ✅ **Gateway freed up:** Doesn't block on slow requests
- ✅ **Scalable:** Can handle multiple simultaneous OCR jobs
- ✅ **Resource efficient:** Background workers can be rate-limited

---

## Future Enhancements

### Priority Queue
```python
class OcrJob(SQLModel, table=True):
    priority: int = Field(default=0)  # Higher = process first
```

### Parallel Processing
```python
# Process multiple OCR jobs concurrently
executor = ThreadPoolExecutor(max_workers=3)
background_tasks.add_task(executor.submit, process_ocr_job, job_id)
```

### WebSocket Updates
```python
# Real-time updates instead of polling
@app.websocket("/ws/ocr/{job_id}")
async def ocr_websocket(websocket: WebSocket, job_id: str):
    await websocket.accept()
    while True:
        job = get_job(job_id)
        await websocket.send_json({"status": job.status})
        if job.status in ["completed", "failed"]:
            break
        await asyncio.sleep(1)
```

### AI Enhancement (LLM Integration)
```python
# Use AI Brain to enhance OCR extraction
async def enhance_with_llm(raw_text: str) -> Med:
    response = await httpx.post("http://ai-brain:9004/extract-med", json={"text": raw_text})
    return Med(**response.json())
```

---

## Rollback Plan

If issues occur, rollback to previous version:

```bash
# Rollback meds service
kubectl rollout undo deployment/kilo-meds -n kilo-guardian

# Rollback gateway
kubectl rollout undo deployment/kilo-gateway -n kilo-guardian

# Rollback frontend
kubectl rollout undo deployment/kilo-frontend -n kilo-guardian

# Verify
kubectl get pods -n kilo-guardian
```

---

## Summary

**Changes:**
- ✅ Meds service: Async OCR processing with image persistence
- ✅ Frontend: Polling-based result retrieval
- ✅ Gateway: Increased timeout (30s → 120s)
- ✅ Database: New `ocr_job` table for tracking

**Result:**
- ✅ No more timeout errors
- ✅ Reliable prescription scanning
- ✅ Better user experience
- ✅ Persistent image storage

**Status:** Ready for deployment

---

**Implementation Date:** 2026-01-04
**Implemented By:** Claude Sonnet 4.5 via Claude Code
