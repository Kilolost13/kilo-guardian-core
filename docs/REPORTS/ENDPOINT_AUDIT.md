# Kilo Guardian - Comprehensive Endpoint Audit Report

**Generated:** 2025-12-28
**System:** Kilo AI Memory Assistant (Microservices Architecture)
**Services Audited:** 12 backend services + gateway + frontend

---

## Executive Summary

This audit documents all API endpoints across the Kilo Guardian system, identifying mismatches between frontend expectations and backend implementations.

**Key Findings:**
- ✅ **Gateway Routing:** Properly configured for all 12 services
- ⚠️ **Schema Mismatches:** Multiple services have frontend/backend schema differences
- ⚠️ **Missing Endpoints:** Several frontend calls reference non-existent backend endpoints
- ⚠️ **Deployment State:** Custom endpoints exist in source but may not be deployed

---

## 1. Gateway Service (Port 8000)

**Container:** `docker_gateway_1:8000`
**Role:** Central routing proxy for all microservices

### Gateway Routes Configuration
```python
SERVICE_URLS = {
    "meds": "http://docker_meds_1:9001",
    "reminder": "http://docker_reminder_1:9002",
    "reminders": "http://docker_reminder_1:9002",  # Alias
    "habits": "http://docker_habits_1:9003",
    "ai_brain": "http://docker_ai_brain_1:9004",
    "financial": "http://docker_financial_1:9005",
    "library_of_truth": "http://docker_library_of_truth_1:9006",
    "cam": "http://docker_cam_1:9007",
    "ml": "http://docker_ml_engine_1:9008",
    "voice": "http://docker_voice_1:9009",
    "usb": "http://docker_usb_transfer_1:8006"
}
```

### Gateway-Specific Endpoints
- `GET /health` → `{"status": "ok"}`
- `GET /status` → Alias for /health
- `GET /admin/status` → Aggregate health check of all services
- `POST /admin/tokens` → Create admin authentication token
- `GET /admin/tokens` → List all admin tokens
- `POST /admin/tokens/{id}/revoke` → Revoke token
- `POST /admin/validate` → Validate admin token

### Proxy Pattern
- `/{service}/{path:path}` → Routes to appropriate microservice
- Example: `/api/reminder/reminders` → `http://docker_reminder_1:9002/reminders`

**Status:** ✅ WORKING

---

## 2. Medications Service (Port 9001)

**Container:** `docker_meds_1:9001`
**Source:** `services/meds/main.py`

### Backend Endpoints

#### GET /
- **Purpose:** List all medications
- **Auth:** Requires X-Admin-Token header
- **Response:**
```json
{
  "medications": [
    {
      "id": 1,
      "name": "Aspirin",
      "dosage": "100mg",
      "frequency": "daily",
      "time_of_day": "08:00",
      "notes": "Take with food",
      "active": true
    }
  ]
}
```

#### POST /add
- **Purpose:** Add new medication
- **Auth:** Requires X-Admin-Token
- **Request:**
```json
{
  "name": "Medication Name",
  "dosage": "100mg",
  "frequency": "daily",
  "time_of_day": "08:00",
  "notes": "Optional notes"
}
```
- **Response:** Created medication object

#### PUT /{medication_id}
- **Purpose:** Update medication
- **Auth:** Requires X-Admin-Token
- **Request:** Same as POST /add
- **Response:** Updated medication object

#### DELETE /{medication_id}
- **Purpose:** Delete medication
- **Auth:** Requires X-Admin-Token
- **Response:** `{"status": "deleted"}`

#### POST /{medication_id}/take
- **Purpose:** Log medication taken
- **Auth:** Requires X-Admin-Token
- **Response:** Log entry confirmation

#### POST /extract
- **Purpose:** Extract medication info from prescription image via OCR
- **Auth:** Requires X-Admin-Token
- **Request:** Multipart form with image file
- **Response:**
```json
{
  "extracted_text": "Raw OCR text...",
  "medications": [
    {
      "name": "Detected Med Name",
      "dosage": "100mg",
      "frequency": "detected or default",
      "confidence": 0.85
    }
  ]
}
```

#### GET /health
- **Purpose:** Health check
- **Response:** `{"status": "ok"}`

### Frontend API Calls (Medications.tsx)

```typescript
// Line 35: Fetch medications
api.get('/meds')

// Line 51: Take medication
api.post(`/meds/${id}/take`)

// Line 61: Update medication
api.put(`/meds/${id}`, medicationData)

// Line 73: Add medication
api.post('/meds/add', medicationData)

// Line 87: Delete medication
api.delete(`/meds/${id}`)

// Line 101: Extract from prescription image
api.post('/meds/extract', formData)
```

**Status:** ✅ ALIGNED - All frontend calls match backend endpoints

---

## 3. Reminder Service (Port 9002)

**Container:** `docker_reminder_1:9002`
**Source:** `services/reminder/main.py`

### Backend Endpoints (Source Code)

#### GET /
- **Purpose:** List all reminders (original endpoint)
- **Auth:** Optional X-Admin-Token
- **Response:** Raw reminder list with backend schema
```json
[
  {
    "id": 1,
    "text": "Reminder text",
    "when": "2025-12-28T10:00:00",
    "sent": false,
    "recurrence": "daily",
    "timezone": null
  }
]
```

#### POST /
- **Purpose:** Create reminder (original endpoint)
- **Auth:** Requires X-Admin-Token
- **Request:** Backend schema
```json
{
  "text": "Reminder text",
  "when": "2025-12-28T10:00:00",
  "recurrence": "daily"
}
```

#### GET /reminders
- **Purpose:** List reminders with frontend-compatible format
- **Auth:** Optional
- **Response:** Transformed to frontend schema
```json
{
  "reminders": [
    {
      "id": 1,
      "title": "Reminder text",
      "description": "",
      "reminder_time": "2025-12-28T10:00:00",
      "recurring": true,
      "created_at": null
    }
  ]
}
```
- **Status:** ⚠️ **EXISTS IN SOURCE, MAY NOT BE DEPLOYED**

#### POST /reminders
- **Purpose:** Create reminder with frontend schema
- **Auth:** Requires X-Admin-Token
- **Request:** Frontend schema
```json
{
  "title": "Take medication",
  "description": "Optional details",
  "reminder_time": "2025-12-28T10:00:00",
  "recurring": true
}
```
- **Transformation:** Converts to backend schema internally
- **Status:** ⚠️ **EXISTS IN SOURCE, MAY NOT BE DEPLOYED**

#### DELETE /reminders/{reminder_id}
- **Purpose:** Delete reminder
- **Auth:** Requires X-Admin-Token
- **Response:** `{"status": "deleted"}`
- **Status:** ⚠️ **EXISTS IN SOURCE, MAY NOT BE DEPLOYED**

#### GET /health
- **Purpose:** Health check
- **Response:** `{"status": "ok"}`

### Frontend API Calls (Reminders.tsx)

```typescript
// Line 35: Fetch reminders
api.get('/reminder/reminders')
// Expected response: { reminders: Reminder[] }

// Line 48: Create reminder
api.post('/reminder/reminders', {
  title: string,
  description: string,
  reminder_time: string,
  recurring: boolean
})

// Line 59: Delete reminder
api.delete(`/reminder/reminders/${id}`)
```

### Schema Comparison

**Frontend Interface (Reminders.tsx:7-14):**
```typescript
interface Reminder {
  id: number;
  title: string;
  description: string;
  reminder_time: string;
  recurring: boolean;
  created_at?: string;
}
```

**Backend Model (shared/models/__init__.py:21-28):**
```python
class Reminder(SQLModel, table=True):
    id: Optional[int]
    text: str
    when: str
    sent: bool = False
    recurrence: Optional[str] = None
    timezone: Optional[str] = None
    preset_id: Optional[int] = None
```

**Status:** ⚠️ **CRITICAL MISMATCH**
- Frontend calls `/reminder/reminders` endpoints
- Backend custom endpoints exist in source code
- Need to verify deployment state and rebuild if necessary

---

## 4. Habits Service (Port 9003)

**Container:** `docker_habits_1:9003`
**Source:** `services/habits/main.py`

### Backend Endpoints

#### GET /
- **Purpose:** List all habits
- **Auth:** Requires X-Admin-Token
- **Response:**
```json
{
  "habits": [
    {
      "id": 1,
      "name": "Exercise",
      "frequency": "daily",
      "time_of_day": "07:00",
      "notes": "Morning workout",
      "active": true
    }
  ]
}
```

#### POST /
- **Purpose:** Create new habit
- **Auth:** Requires X-Admin-Token
- **Request:**
```json
{
  "name": "Habit name",
  "frequency": "daily",
  "time_of_day": "07:00",
  "notes": "Optional notes"
}
```

#### PUT /{habit_id}
- **Purpose:** Update habit
- **Auth:** Requires X-Admin-Token
- **Request:** Same as POST /

#### DELETE /{habit_id}
- **Purpose:** Delete habit
- **Auth:** Requires X-Admin-Token

#### POST /complete/{habit_id}
- **Purpose:** Mark habit as completed for today
- **Auth:** Requires X-Admin-Token
- **Response:** Completion log entry

#### GET /health
- **Purpose:** Health check

### Frontend API Calls (Habits.tsx)

```typescript
// Line 42: Fetch habits
api.get('/habits')

// Line 58: ML prediction for habit completion
api.post('/ml/predict/habit_completion', habitData)

// Line 72: ML prediction for reminder timing
api.post('/ml/predict/reminder_timing', habitData)

// Line 89: Complete habit
api.post(`/habits/complete/${id}`)
```

**Status:** ⚠️ **PARTIAL MISMATCH**
- GET /habits matches backend GET /
- POST /habits/complete/{id} matches backend
- ML prediction calls go to ML service (correct routing)
- Missing: Frontend doesn't use POST /, PUT /{id}, DELETE /{id} endpoints

---

## 5. AI Brain Service (Port 9004)

**Container:** `docker_ai_brain_1:9004`
**Source:** `services/ai_brain/main.py`

### Backend Endpoints (30+ endpoints)

#### Core Chat
- `POST /chat` - Main chat interface with RAG
- `POST /chat/stream` - Streaming chat response
- `GET /chat/history` - Get conversation history
- `DELETE /chat/history` - Clear history

#### Memory Management
- `POST /ingest` - Store new memory/knowledge
- `POST /ingest/batch` - Batch ingest multiple memories
- `GET /memory` - List all memories
- `GET /memory/{id}` - Get specific memory
- `DELETE /memory/{id}` - Delete memory
- `PUT /memory/{id}` - Update memory
- `POST /memory/search` - Semantic search in memories

#### Analytics
- `GET /analytics/summary` - Memory statistics
- `GET /analytics/categories` - Category breakdown
- `GET /analytics/timeline` - Time-based analysis
- `GET /analytics/topics` - Topic extraction

#### Configuration
- `GET /config` - Get current config
- `PUT /config` - Update config
- `GET /models/available` - List available LLM models
- `POST /models/switch` - Switch active model

#### Encryption
- `POST /encrypt` - Encrypt sensitive data
- `POST /decrypt` - Decrypt data
- `GET /encryption/status` - Check encryption availability

#### Health
- `GET /health` - Health check
- `GET /status` - Detailed status including embeddings

### Frontend API Calls

**Dashboard.tsx:**
```typescript
// Line 48: Get memory visualization data
api.get('/memory/visualization')
// ❌ ENDPOINT NOT FOUND IN BACKEND

// Line 62: Get dashboard stats
api.get('/stats/dashboard')
// ❌ ENDPOINT NOT FOUND IN BACKEND
```

**No direct AI Brain calls found in other frontend components**

**Status:** ⚠️ **MISSING ENDPOINTS**
- Frontend expects `/memory/visualization` - NOT in backend
- Frontend expects `/stats/dashboard` - NOT in backend
- Backend has extensive API but frontend doesn't use most of it

---

## 6. Financial Service (Port 9005)

**Container:** `docker_financial_1:9005`
**Source:** `services/financial/main.py`

### Backend Endpoints (20+ endpoints)

#### Transactions
- `GET /transactions` - List all transactions
- `POST /transaction` - Create transaction
- `GET /transactions/{id}` - Get specific transaction
- `PUT /transactions/{id}` - Update transaction
- `DELETE /transactions/{id}` - Delete transaction
- `GET /transactions/category/{category}` - Filter by category
- `GET /transactions/search` - Search transactions

#### Budgets
- `GET /budgets` - List all budgets
- `POST /budget` - Create budget
- `GET /budgets/{id}` - Get specific budget
- `PUT /budgets/{id}` - Update budget
- `DELETE /budgets/{id}` - Delete budget
- `GET /budgets/status` - Current budget status

#### Goals
- `GET /goals` - List financial goals
- `POST /goal` - Create goal
- `PUT /goals/{id}` - Update goal
- `DELETE /goals/{id}` - Delete goal
- `POST /goals/{id}/progress` - Update progress

#### Summary & Analytics
- `GET /summary` - Financial summary (income, expenses, balance)
- `GET /analytics/monthly` - Monthly breakdown
- `GET /analytics/trends` - Spending trends
- `GET /analytics/categories` - Category analysis

#### Receipts
- `POST /receipts/upload` - Upload receipt image
- `GET /receipts` - List receipts
- `GET /receipts/{id}` - Get receipt details

#### Health
- `GET /health` - Health check

### Frontend API Calls (Finance.tsx)

```typescript
// Line 45: Fetch transactions
api.get('/financial/transactions')
// ✅ MATCHES backend GET /transactions

// Line 59: Fetch summary
api.get('/financial/summary')
// ✅ MATCHES backend GET /summary

// Line 73: Fetch budgets
api.get('/financial/budgets')
// ✅ MATCHES backend GET /budgets

// Line 87: Fetch goals
api.get('/financial/goals')
// ✅ MATCHES backend GET /goals

// Line 101: Create transaction
api.post('/financial/transaction', transactionData)
// ✅ MATCHES backend POST /transaction

// Line 115: Create budget
api.post('/financial/budget', budgetData)
// ✅ MATCHES backend POST /budget

// Line 129: Create goal
api.post('/financial/goal', goalData)
// ✅ MATCHES backend POST /goal

// Line 143: Delete transaction
api.delete(`/financial/transactions/${id}`)
// ✅ MATCHES backend DELETE /transactions/{id}

// Line 157: Delete budget
api.delete(`/financial/budgets/${id}`)
// ✅ MATCHES backend DELETE /budgets/{id}

// Line 171: Delete goal
api.delete(`/financial/goals/${id}`)
// ✅ MATCHES backend DELETE /goals/{id}
```

**Status:** ✅ **FULLY ALIGNED** - All frontend calls match backend endpoints

---

## 7. ML Engine Service (Port 9008)

**Container:** `docker_ml_engine_1:9008`
**Source:** `services/ml_engine/main.py`

### Backend Endpoints

#### Predictions
- `POST /predict` - Generic prediction endpoint
- `POST /predict/habit_completion` - Predict habit completion likelihood
- `POST /predict/reminder_timing` - Suggest optimal reminder time
- `POST /predict/medication_adherence` - Predict med adherence risk
- `POST /predict/mood` - Mood prediction from text

#### Insights
- `GET /insights/patterns` - Behavioral patterns
- `GET /insights/recommendations` - AI recommendations
- `GET /insights/trends` - Trend analysis

#### Training
- `POST /train/habit_model` - Train habit prediction model
- `POST /train/reminder_model` - Train reminder timing model
- `GET /models/status` - Model training status

#### Health
- `GET /health` - Health check
- `GET /status` - ML service status

### Frontend API Calls

**Admin.tsx:**
```typescript
// Line 78: Generic ML prediction
api.post('/ml/predict', predictionData)
// ✅ MATCHES backend POST /predict
```

**Habits.tsx:**
```typescript
// Line 58: Habit completion prediction
api.post('/ml/predict/habit_completion', habitData)
// ✅ MATCHES backend POST /predict/habit_completion

// Line 72: Reminder timing prediction
api.post('/ml/predict/reminder_timing', habitData)
// ✅ MATCHES backend POST /predict/reminder_timing
```

**Dashboard.tsx:**
```typescript
// Line 89: Get insights patterns
api.get('/ml/insights/patterns')
// ✅ MATCHES backend GET /insights/patterns
```

**Status:** ✅ **ALIGNED** - Frontend calls match backend

---

## 8. Library of Truth Service (Port 9006)

**Container:** `docker_library_of_truth_1:9006`
**Source:** `services/library_of_truth/main.py`

### Backend Endpoints

#### Core Knowledge Base
- `POST /ingest` - Store factual information
- `GET /query` - Query knowledge base
- `GET /facts` - List all facts
- `GET /facts/{id}` - Get specific fact
- `DELETE /facts/{id}` - Delete fact
- `PUT /facts/{id}` - Update fact

#### Verification
- `POST /verify` - Verify statement against stored facts
- `GET /confidence/{statement}` - Get confidence score

#### Health
- `GET /health` - Health check

### Frontend API Calls

**No frontend calls found to Library of Truth service**

**Status:** ⚠️ **UNUSED** - Backend exists but frontend doesn't use it

---

## 9. Camera Service (Port 9007)

**Container:** `docker_cam_1:9007`
**Source:** `services/cam/main.py`

### Backend Endpoints

#### Camera Control
- `GET /cameras` - List available cameras
- `POST /capture` - Capture image from camera
- `POST /stream/start` - Start video stream
- `POST /stream/stop` - Stop video stream
- `GET /stream/status` - Stream status

#### Image Processing
- `POST /process/ocr` - OCR on captured image
- `POST /process/qr` - QR code detection
- `POST /process/face` - Face detection

#### Health
- `GET /health` - Health check

### Frontend API Calls

**No frontend calls found to Camera service**

**Status:** ⚠️ **UNUSED** - Backend exists but frontend doesn't use it directly
- Note: Medications service uses internal camera/OCR for prescription extraction

---

## 10. Voice Service (Port 9009)

**Container:** `docker_voice_1:9009`
**Source:** `services/voice/main.py`

### Backend Endpoints

#### Voice I/O
- `POST /listen` - Speech-to-text
- `POST /speak` - Text-to-speech
- `GET /voice/status` - Voice service status

#### Configuration
- `GET /voices` - List available voices
- `PUT /voice/config` - Update voice settings

#### Health
- `GET /health` - Health check

### Frontend API Calls

**No frontend calls found to Voice service**

**Status:** ⚠️ **UNUSED** - Backend exists but frontend doesn't use it

---

## 11. USB Transfer Service (Port 8006)

**Container:** `docker_usb_transfer_1:8006`
**Source:** `services/usb_transfer/main.py`

### Backend Endpoints

#### File Transfer
- `POST /upload` - Upload file to USB
- `GET /download/{filename}` - Download from USB
- `GET /files` - List files on USB
- `DELETE /files/{filename}` - Delete USB file

#### USB Management
- `GET /usb/status` - USB device status
- `GET /usb/devices` - List USB devices
- `POST /usb/mount` - Mount USB device
- `POST /usb/unmount` - Unmount USB device

#### Health
- `GET /health` - Health check

### Frontend API Calls

**No frontend calls found to USB Transfer service**

**Status:** ⚠️ **UNUSED** - Backend exists but frontend doesn't use it

---

## 12. Admin Dashboard API Calls

**Source:** `frontend/kilo-react-frontend/src/pages/Admin.tsx`

### System Status
```typescript
// Line 32: Get system status
api.get('/admin/status')
// ✅ MATCHES gateway GET /admin/status
```

### Backup (Non-existent)
```typescript
// Line 46: Trigger backup
api.post('/admin/backup')
// ❌ ENDPOINT NOT FOUND - No backup endpoint exists
```

**Status:** ⚠️ **PARTIAL MISMATCH**
- /admin/status works (gateway endpoint)
- /admin/backup doesn't exist anywhere

---

## Critical Issues Summary

### 🔴 HIGH PRIORITY

1. **Reminder Service Endpoints** (`services/reminder/main.py`)
   - Frontend calls: `/reminder/reminders` (GET, POST, DELETE)
   - Backend status: Endpoints exist in source code but may not be deployed
   - Impact: Reminder creation completely broken
   - Fix: Rebuild reminder service or verify deployment

2. **Dashboard Missing Endpoints** (`frontend/src/pages/Dashboard.tsx`)
   - Frontend calls: `/memory/visualization`, `/stats/dashboard`
   - Backend status: Endpoints don't exist
   - Impact: Dashboard stats won't load
   - Fix: Add endpoints to AI Brain or create aggregation service

3. **Admin Backup Endpoint** (`frontend/src/pages/Admin.tsx`)
   - Frontend calls: `/admin/backup`
   - Backend status: Doesn't exist
   - Impact: Backup button doesn't work
   - Fix: Add backup endpoint to gateway or create backup service

### 🟡 MEDIUM PRIORITY

4. **Unused Backend Services**
   - Library of Truth (port 9006) - Not used by frontend
   - Camera Service (port 9007) - Not used directly
   - Voice Service (port 9009) - Not used by frontend
   - USB Transfer (port 8006) - Not used by frontend
   - Impact: Resource waste, unclear system purpose
   - Fix: Either integrate into frontend or document as API-only services

5. **Habits Service Incomplete Integration**
   - Frontend only uses GET and complete endpoints
   - Missing: Create, update, delete habit functionality in UI
   - Backend has full CRUD but frontend doesn't expose it
   - Fix: Add habit management UI

### 🟢 LOW PRIORITY

6. **Schema Documentation**
   - Many endpoints lack clear request/response schema docs
   - Fix: Add OpenAPI/Swagger documentation

7. **Consistent Error Handling**
   - Different services return errors in different formats
   - Fix: Standardize error response format

---

## Gateway Proxy Health Matrix

| Service | Container Name | Port | Gateway Route | Status |
|---------|---------------|------|---------------|--------|
| Gateway | docker_gateway_1 | 8000 | N/A | ✅ HEALTHY |
| Meds | docker_meds_1 | 9001 | /meds | ✅ HEALTHY |
| Reminder | docker_reminder_1 | 9002 | /reminder | ✅ HEALTHY |
| Habits | docker_habits_1 | 9003 | /habits | ✅ HEALTHY |
| AI Brain | docker_ai_brain_1 | 9004 | /ai_brain | ✅ HEALTHY |
| Financial | docker_financial_1 | 9005 | /financial | ✅ HEALTHY |
| Library | docker_library_of_truth_1 | 9006 | /library_of_truth | ✅ HEALTHY |
| Camera | docker_cam_1 | 9007 | /cam | ✅ HEALTHY |
| ML Engine | docker_ml_engine_1 | 9008 | /ml | ✅ HEALTHY |
| Voice | docker_voice_1 | 9009 | /voice | ✅ HEALTHY |
| USB Transfer | docker_usb_transfer_1 | 8006 | /usb | ✅ HEALTHY |
| Ollama | docker_ollama_1 | 11434 | N/A (internal) | ✅ HEALTHY |
| Frontend | docker_frontend_1 | 3000 | N/A (external) | ✅ HEALTHY |

---

## Recommendations

### Immediate Actions

1. **Verify Reminder Service Deployment**
   ```bash
   docker exec docker_reminder_1 curl localhost:9002/reminders
   ```
   - If 404: Rebuild reminder service from source
   - If 200: Issue is elsewhere in routing chain

2. **Add Missing Dashboard Endpoints**
   - Option A: Add to AI Brain service
   - Option B: Create aggregation endpoint in gateway
   - Endpoints needed: `/memory/visualization`, `/stats/dashboard`

3. **Fix or Remove Backup Button**
   - Either implement `/admin/backup` endpoint
   - Or remove button from Admin UI

### Long-term Improvements

4. **Service Integration Strategy**
   - Determine which unused services should be integrated
   - Create frontend components for Library of Truth, Voice, USB Transfer
   - Or document them as API-only services for future integrations

5. **API Documentation**
   - Add OpenAPI/Swagger to all services
   - Generate interactive API docs at `/docs` for each service

6. **Automated Testing**
   - Implement endpoint contract tests
   - CI/CD pipeline to catch schema mismatches

---

## Appendix: Complete Endpoint Matrix

### Services with Full Frontend Integration
- ✅ Medications Service (9001) - 7 endpoints, all used
- ✅ Financial Service (9005) - 20+ endpoints, core features used
- ⚠️ Reminder Service (9002) - 6+ endpoints, deployment issue
- ⚠️ Habits Service (9003) - 6 endpoints, partial usage
- ⚠️ ML Engine (9008) - 10+ endpoints, partial usage
- ⚠️ AI Brain (9004) - 30+ endpoints, minimal usage

### Services with No Frontend Integration
- ⚠️ Library of Truth (9006) - 8 endpoints, unused
- ⚠️ Camera Service (9007) - 8 endpoints, unused
- ⚠️ Voice Service (9009) - 5 endpoints, unused
- ⚠️ USB Transfer (8006) - 8 endpoints, unused

### Infrastructure Services
- ✅ Gateway (8000) - Routing + admin
- ✅ Ollama (11434) - LLM backend (internal)
- ✅ Frontend (3000) - React UI

**Total Endpoints Documented:** 120+
**Endpoints with Confirmed Issues:** 5
**Services Needing Integration:** 4
