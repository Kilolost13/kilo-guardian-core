# Kilo Guardian - Endpoint Fixes & Recommendations

**Generated:** 2025-12-28
**Status:** Based on comprehensive endpoint audit
**Priority Levels:** 🔴 Critical | 🟡 Important | 🟢 Enhancement

---

## Executive Summary

This document provides a prioritized action plan to resolve all endpoint mismatches and system integration issues identified in the comprehensive audit.

**Current State:**
- ✅ 13/13 services healthy and running
- ⚠️ 5 confirmed endpoint mismatches
- ⚠️ 4 backend services unused by frontend
- ⚠️ Multiple schema inconsistencies

**Estimated Total Effort:** 8-12 hours of development work

---

## 🔴 CRITICAL FIXES (Do These First)

### Fix #1: Reminder Service Endpoint Deployment ⏱️ 2 hours

**Problem:**
- Frontend calls `/reminder/reminders` (GET, POST, DELETE)
- Custom endpoints exist in source code (`services/reminder/main.py:388-480`)
- May not be deployed in current Docker container
- Users cannot create reminders (complete feature breakdown)

**Impact:** **HIGH** - Core feature completely broken

**Root Cause:**
- Docker rebuild reverted service to clean state
- Custom transformation endpoints only in source, not deployed

**Files to Modify:**
- `services/reminder/main.py` (verify lines 388-480 exist)

**Fix Steps:**

1. **Verify source code has custom endpoints:**
   ```bash
   grep -n "GET /reminders" services/reminder/main.py
   grep -n "POST /reminders" services/reminder/main.py
   grep -n "DELETE /reminders" services/reminder/main.py
   ```

2. **If missing, add these endpoints to `services/reminder/main.py`:**

```python
# Add after existing endpoints (around line 388)

@app.get("/reminders")
def get_reminders_frontend_format(request: Request):
    """
    List all reminders with frontend-compatible format.
    Transforms backend schema {text, when, recurrence} to
    frontend schema {title, description, reminder_time, recurring}.
    """
    try:
        with Session(engine) as session:
            reminders = session.exec(select(Reminder)).all()
            result = []
            for r in reminders:
                # Split text into title and description if separator exists
                title = r.text
                description = ""
                if " - " in r.text:
                    parts = r.text.split(" - ", 1)
                    title = parts[0]
                    description = parts[1]

                result.append({
                    "id": r.id,
                    "title": title,
                    "description": description,
                    "reminder_time": r.when,
                    "recurring": bool(r.recurrence),
                    "created_at": None
                })
            return {"reminders": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reminders")
async def create_reminder_frontend_format(request: Request):
    """
    Create reminder using frontend schema.
    Accepts {title, description, reminder_time, recurring}
    Transforms to backend schema {text, when, recurrence}.
    """
    _require_admin(request)

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid JSON body")

    # Extract frontend fields
    title = body.get("title", "")
    description = body.get("description", "")
    reminder_time = body.get("reminder_time", "")
    recurring = body.get("recurring", False)

    if not title or not reminder_time:
        raise HTTPException(status_code=422, detail="title and reminder_time are required")

    # Transform to backend schema
    text = title
    if description:
        text = f"{title} - {description}"

    recurrence = None
    if recurring:
        recurrence = "daily"  # Default recurring frequency

    # Create reminder
    reminder = Reminder(
        text=text,
        when=reminder_time,
        recurrence=recurrence,
        sent=False
    )

    with Session(engine) as session:
        session.add(reminder)
        session.commit()
        session.refresh(reminder)

        # Return in frontend format
        return {
            "id": reminder.id,
            "title": title,
            "description": description,
            "reminder_time": reminder.reminder_time,
            "recurring": recurring,
            "created_at": None
        }


@app.delete("/reminders/{reminder_id}")
async def delete_reminder_frontend_format(reminder_id: int, request: Request):
    """Delete reminder (frontend-compatible path)."""
    _require_admin(request)

    with Session(engine) as session:
        reminder = session.get(Reminder, reminder_id)
        if not reminder:
            raise HTTPException(status_code=404, detail="Reminder not found")

        session.delete(reminder)
        session.commit()

        return {"status": "deleted", "id": reminder_id}
```

3. **Rebuild and restart reminder service:**
   ```bash
   cd /home/kilo/Desktop/Kilo_Ai_microservice
   docker-compose build reminder
   docker-compose up -d reminder
   ```

4. **Verify deployment:**
   ```bash
   curl http://localhost:9002/reminders
   # Should return: {"reminders": [...]}

   curl http://localhost:8000/reminder/reminders
   # Should also work through gateway
   ```

5. **Test frontend:**
   - Open http://localhost:3000/tablet
   - Click "Reminders"
   - Try creating a new reminder
   - Should succeed without 422 errors

**Success Criteria:**
- ✅ GET /reminder/reminders returns reminder list
- ✅ POST /reminder/reminders creates reminder successfully
- ✅ Frontend Reminders page works end-to-end

---

### Fix #2: Dashboard Missing Endpoints ⏱️ 3 hours

**Problem:**
- `Dashboard.tsx:48` calls `GET /memory/visualization` → 404
- `Dashboard.tsx:62` calls `GET /stats/dashboard` → 404
- Dashboard stats section shows loading or errors

**Impact:** **HIGH** - Dashboard doesn't display key metrics

**Solution Options:**

#### Option A: Add Endpoints to AI Brain Service (Recommended)

**Files to Modify:**
- `services/ai_brain/main.py`

**Add these endpoints:**

```python
# Add to services/ai_brain/main.py

@app.get("/memory/visualization")
async def get_memory_visualization(request: Request):
    """
    Get memory data for dashboard visualization.
    Returns aggregated stats about stored memories.
    """
    _require_admin(request)

    with Session(engine) as session:
        # Get total memories
        total_memories = session.exec(select(func.count(Memory.id))).one()

        # Get memories by category (if you have categories)
        # This is a placeholder - adjust based on your Memory model

        return {
            "total_memories": total_memories,
            "recent_memories": [],  # Add logic to get recent memories
            "categories": {},  # Add category breakdown
            "timeline": []  # Add time-based data
        }


@app.get("/stats/dashboard")
async def get_dashboard_stats(request: Request):
    """
    Aggregate stats from all services for dashboard.
    Combines data from meds, reminders, habits, financial, etc.
    """
    import httpx

    stats = {
        "medications": {"total": 0, "taken_today": 0},
        "reminders": {"total": 0, "upcoming": 0},
        "habits": {"total": 0, "completed_today": 0},
        "financial": {"balance": 0, "this_month_spending": 0},
        "ai_memories": {"total": 0}
    }

    async with httpx.AsyncClient(timeout=2.0) as client:
        # Fetch from medications service
        try:
            resp = await client.get("http://docker_meds_1:9001/")
            if resp.status_code == 200:
                data = resp.json()
                stats["medications"]["total"] = len(data.get("medications", []))
        except Exception:
            pass

        # Fetch from reminder service
        try:
            resp = await client.get("http://docker_reminder_1:9002/")
            if resp.status_code == 200:
                reminders = resp.json()
                stats["reminders"]["total"] = len(reminders)
        except Exception:
            pass

        # Fetch from habits service
        try:
            resp = await client.get("http://docker_habits_1:9003/")
            if resp.status_code == 200:
                data = resp.json()
                stats["habits"]["total"] = len(data.get("habits", []))
        except Exception:
            pass

        # Fetch from financial service
        try:
            resp = await client.get("http://docker_financial_1:9005/summary")
            if resp.status_code == 200:
                data = resp.json()
                stats["financial"] = data
        except Exception:
            pass

    return stats
```

**Rebuild steps:**
```bash
docker-compose build ai_brain
docker-compose up -d ai_brain
```

#### Option B: Add Aggregation Endpoint to Gateway

**Files to Modify:**
- `services/gateway/main.py`

**Add endpoint that aggregates from multiple services** (similar to above but in gateway)

**Recommendation:** Use Option A (AI Brain) as it's more semantically correct.

**Success Criteria:**
- ✅ Dashboard loads without errors
- ✅ Stats display real data from services
- ✅ Memory visualization renders

---

### Fix #3: Admin Backup Endpoint ⏱️ 1 hour

**Problem:**
- `Admin.tsx:46` calls `POST /admin/backup` → 404
- Backup button doesn't work

**Impact:** **MEDIUM** - Users can't trigger backups from UI

**Files to Modify:**
- `services/gateway/main.py`

**Add endpoint:**

```python
# Add to services/gateway/main.py

@app.post("/admin/backup")
async def trigger_backup(request: Request):
    """
    Trigger system backup.
    Creates backup of all service databases and uploads to USB if available.
    """
    header = request.headers.get("x-admin-token")
    if not _validate_header_token(header):
        raise HTTPException(status_code=401, detail="Unauthorized")

    import httpx
    import datetime

    backup_id = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    results = {}

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Trigger backup on each service
        for service_name, service_url in SERVICE_URLS.items():
            backup_url = f"{service_url}/backup"
            try:
                resp = await client.post(backup_url, headers={"X-Admin-Token": header})
                results[service_name] = {
                    "status": "success" if resp.status_code < 400 else "failed",
                    "message": resp.text
                }
            except Exception as e:
                results[service_name] = {
                    "status": "error",
                    "message": str(e)
                }

    return {
        "backup_id": backup_id,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "results": results
    }
```

**Alternative (Quick Fix):**
Remove backup button from frontend if backup functionality isn't critical:

**Files to Modify:**
- `frontend/kilo-react-frontend/src/pages/Admin.tsx`

**Remove or comment out:**
```typescript
// Lines around 46 - remove backup button
// <Button onClick={handleBackup}>Trigger Backup</Button>
```

**Success Criteria:**
- ✅ Backup button either works or is removed
- ✅ No console errors when using Admin page

---

## 🟡 IMPORTANT FIXES (Do Next)

### Fix #4: Complete Habits UI Integration ⏱️ 2 hours

**Problem:**
- Backend has full CRUD for habits (GET, POST, PUT, DELETE)
- Frontend only uses GET and POST /complete
- No UI to create, edit, or delete habits

**Impact:** **MEDIUM** - Feature incomplete, users can't manage habits

**Files to Modify:**
- `frontend/kilo-react-frontend/src/pages/Habits.tsx`

**Add missing UI components:**

1. **Add "Create Habit" form** (similar to Reminders.tsx form)
2. **Add Edit button** to each habit card
3. **Add Delete button** to each habit card
4. **Add API calls:**

```typescript
// Add to Habits.tsx

const handleAddHabit = async (e: React.FormEvent) => {
  e.preventDefault();
  try {
    await api.post('/habits', habitForm);
    fetchHabits();
  } catch (error) {
    console.error('Failed to add habit:', error);
  }
};

const handleUpdateHabit = async (id: number, data: any) => {
  try {
    await api.put(`/habits/${id}`, data);
    fetchHabits();
  } catch (error) {
    console.error('Failed to update habit:', error);
  }
};

const handleDeleteHabit = async (id: number) => {
  try {
    await api.delete(`/habits/${id}`);
    fetchHabits();
  } catch (error) {
    console.error('Failed to delete habit:', error);
  }
};
```

**Success Criteria:**
- ✅ Users can create new habits from UI
- ✅ Users can edit existing habits
- ✅ Users can delete habits

---

### Fix #5: Integrate Unused Backend Services ⏱️ 4-8 hours

**Problem:**
- 4 services running but not used by frontend:
  - Library of Truth (port 9006)
  - Camera Service (port 9007)
  - Voice Service (port 9009)
  - USB Transfer (port 8006)

**Impact:** **MEDIUM** - Resource waste, unclear system purpose

**Solution Options:**

#### Option A: Integrate into Frontend

Create frontend components for each service:

**Library of Truth Integration:**
- Add "Knowledge Base" page
- Allow users to store/query factual information
- Use for medication facts, health info, etc.

**Voice Integration:**
- Add voice input button to chat interface
- Add text-to-speech for AI responses
- Accessibility feature for hands-free use

**USB Transfer Integration:**
- Add "Data Export" section in Admin page
- Allow backup to USB drive
- Enable offline data transfer

**Camera Integration:**
- Already partially integrated (prescription scanning)
- Could add: QR code scanning, document capture

#### Option B: Document as API-Only Services

If these services are for future features or external integrations:

**Files to Create:**
- `docs/API_ONLY_SERVICES.md`

**Document:**
- Purpose of each service
- API documentation
- When they should be used
- Future integration plans

#### Recommendation:
- **Voice Service**: Integrate (improves UX significantly)
- **USB Transfer**: Integrate (needed for backup)
- **Library of Truth**: Document for future (nice-to-have)
- **Camera**: Already integrated via meds service

**Success Criteria:**
- ✅ All running services have clear purpose
- ✅ Unused services either integrated or documented

---

## 🟢 ENHANCEMENTS (Optional)

### Enhancement #1: Add API Documentation ⏱️ 4 hours

**Current State:** No OpenAPI/Swagger docs

**Benefit:** Easier development, better testing, auto-generated client code

**Implementation:**

Add to each service's `main.py`:

```python
# Add to all services
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=f"{app.title} - API Docs"
    )

# Add detailed docstrings to all endpoints
# Example:
@app.get("/")
def list_items():
    """
    List all items.

    Returns:
        List of items with full details

    Raises:
        HTTPException: 401 if unauthorized
    """
    pass
```

**Access docs at:** `http://localhost:9001/docs` (for each service)

---

### Enhancement #2: Standardize Error Responses ⏱️ 2 hours

**Current State:** Different services return errors in different formats

**Benefit:** Easier error handling in frontend

**Implementation:**

Create `shared/error_handlers.py`:

```python
from fastapi import HTTPException
from fastapi.responses import JSONResponse

class StandardError:
    @staticmethod
    def format(status_code: int, message: str, details: dict = None):
        return JSONResponse(
            status_code=status_code,
            content={
                "error": True,
                "status_code": status_code,
                "message": message,
                "details": details or {}
            }
        )

# Use in all services:
# raise HTTPException(status_code=404, detail=StandardError.format(404, "Not found"))
```

---

### Enhancement #3: Add Endpoint Contract Tests ⏱️ 6 hours

**Current State:** Manual testing only

**Benefit:** Catch schema mismatches before deployment

**Implementation:**

Create `tests/test_contracts.py`:

```python
import pytest
import httpx

@pytest.mark.asyncio
async def test_reminder_frontend_contract():
    """Test that reminder endpoints match frontend expectations."""
    async with httpx.AsyncClient() as client:
        # Test GET /reminders returns correct format
        resp = await client.get("http://localhost:9002/reminders")
        assert resp.status_code == 200
        data = resp.json()
        assert "reminders" in data

        if len(data["reminders"]) > 0:
            reminder = data["reminders"][0]
            assert "id" in reminder
            assert "title" in reminder
            assert "description" in reminder
            assert "reminder_time" in reminder
            assert "recurring" in reminder

# Add tests for all services
```

Run with: `pytest tests/test_contracts.py`

---

## Implementation Priority Matrix

| Fix | Priority | Effort | Impact | Order |
|-----|----------|--------|--------|-------|
| #1 Reminder Endpoints | 🔴 Critical | 2h | High | 1 |
| #2 Dashboard Endpoints | 🔴 Critical | 3h | High | 2 |
| #3 Admin Backup | 🔴 Critical | 1h | Medium | 3 |
| #4 Habits UI | 🟡 Important | 2h | Medium | 4 |
| #5 Unused Services | 🟡 Important | 4-8h | Medium | 5 |
| #6 API Docs | 🟢 Enhancement | 4h | Low | 6 |
| #7 Error Standards | 🟢 Enhancement | 2h | Low | 7 |
| #8 Contract Tests | 🟢 Enhancement | 6h | Low | 8 |

**Total Critical Fixes:** 6 hours
**Total Important Fixes:** 6-10 hours
**Total Enhancements:** 12 hours

---

## Quick Start: Fix Critical Issues Now

Execute these commands to fix the top 3 critical issues:

```bash
# 1. Fix Reminder Service
cd /home/kilo/Desktop/Kilo_Ai_microservice

# Verify endpoints exist in source
grep -A 20 "GET /reminders" services/reminder/main.py

# If missing, add them (see Fix #1 above), then:
docker-compose build reminder
docker-compose up -d reminder

# Test
curl http://localhost:9002/reminders
curl http://localhost:8000/reminder/reminders

# 2. Add Dashboard Endpoints to AI Brain
# Edit services/ai_brain/main.py (see Fix #2 above)
# Then rebuild:
docker-compose build ai_brain
docker-compose up -d ai_brain

# 3. Add Backup Endpoint or Remove Button
# Option A: Edit services/gateway/main.py (see Fix #3)
# Option B: Edit frontend/src/pages/Admin.tsx to remove button
docker-compose build gateway  # if edited gateway
docker-compose build frontend # if edited frontend
docker-compose up -d

# 4. Run test suite
./scripts/test-endpoints.sh
```

---

## Testing Your Fixes

After implementing each fix, run the automated test suite:

```bash
./scripts/test-endpoints.sh
```

Expected results after all critical fixes:
- ✅ Reminder endpoints: PASS
- ✅ Dashboard endpoints: PASS
- ✅ Admin backup: PASS (or button removed)
- ✅ All health checks: PASS

---

## Long-term Recommendations

1. **Implement CI/CD Pipeline**
   - Run `test-endpoints.sh` on every commit
   - Fail build if critical endpoints broken
   - Auto-deploy on passing tests

2. **Add Schema Validation Layer**
   - Use Pydantic models shared between frontend/backend
   - Generate TypeScript interfaces from Python models
   - Prevent schema drift

3. **Service Integration Roadmap**
   - Follow `INTEGRATION_ROADMAP.md` for cross-service features
   - Prioritize: Meds → Reminders → Habits → AI Brain
   - Estimated: 16 weeks total

4. **Monitoring and Alerting**
   - Set up health check monitoring
   - Alert on service failures
   - Track API error rates

5. **Documentation**
   - Maintain ENDPOINT_AUDIT.md as living document
   - Update after any API changes
   - Review quarterly

---

## Support and Questions

If you encounter issues while implementing these fixes:

1. Check logs: `docker-compose logs [service_name]`
2. Test directly: `curl http://localhost:[port]/endpoint`
3. Verify routing: `curl http://localhost:8000/[service]/endpoint`
4. Check ENDPOINT_AUDIT.md for endpoint details
5. Run `./scripts/test-endpoints.sh` for full diagnostic

---

**Document Version:** 1.0
**Last Updated:** 2025-12-28
**Next Review:** After implementing critical fixes
