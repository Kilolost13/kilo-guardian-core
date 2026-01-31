# 🔍 Proactive System Issues & Fixes

**Date**: January 29, 2026
**Status**: ❌ Multiple issues found

---

## 🚨 Issues Identified

### 1. ❌ All Reminders Marked as "Sent"
**Problem**: Every reminder shows `"sent":true` in the database
**Impact**: APScheduler won't trigger any reminders because it thinks they've all been sent
**Why**: Likely from the "merge and purge" process - database was copied with sent flags still set

**Evidence**:
```json
{
  "id":"4_2026-01-29",
  "original_id":4,
  "text":"Take Adderall",
  "when":"2026-01-29T15:00:00",  # 3pm reminder
  "sent":true  # ← PROBLEM: marked as sent!
}
```

**Fix Required**: Reset `sent=false` for all recurring reminders

---

### 2. ❌ Dashboard Stats All Showing Zero
**Problem**: `/api/ai_brain/stats/dashboard` returns all zeros:
```json
{
  "totalMemories":0,
  "activeHabits":0,
  "upcomingReminders":0,
  "monthlySpending":0,
  "insightsGenerated":0
}
```

**Why**: ai-brain isn't querying microservices or data isn't aggregating properly

---

### 3. ❌ Prometheus Integration Not Working
**Problem**: Admin page shows Prometheus data isn't displaying
**Missing**: Admin token configuration for `/admin/metrics/summary` endpoint

**Evidence**:
```bash
$ curl http://192.168.68.56/api/admin/metrics/summary
{"detail":"Unauthorized"}
```

---

### 4. ⚠️ Financial Data Upload Location Unclear
**Problem**: User uploaded financial data to HP but it's not showing
**Current State**:
- Financial database exists: `/data/financial.db`
- Database has transaction data (verified)
- But user says "uploaded finance info not showing"

**Needs Investigation**: Where was data uploaded? Need to import CSV files?

---

### 5. ❌ No Proactive Bill Alerts
**Problem**: First of month approaching, no proactive bill reminders
**Bills Due Soon**:
- Feb 1: Mortgage ($1,200), Wifi ($52)
- Feb 3: T-Mobile ($186.38)
- Feb 6: Electric ($348.22)

**Why**: All reminders marked as sent=true, scheduler isn't triggering

---

## 🔧 Fixes Needed

### Fix 1: Reset Reminder "Sent" Flags

**SQL to run in reminder database**:
```sql
-- Reset all recurring reminders to not-sent
UPDATE reminder
SET sent = FALSE
WHERE recurring = TRUE;

-- Or reset all reminders
UPDATE reminder
SET sent = FALSE;
```

**After SQL**: Restart `kilo-reminder` pod to reload scheduler

---

### Fix 2: Configure Admin Token

**Option A - Set environment variable**:
```yaml
env:
  - name: ADMIN_TOKEN
    value: "your-secure-token-here"
```

**Option B - Create from secret**:
```bash
kubectl create secret generic admin-token \
  --from-literal=token=your-secure-token \
  -n kilo-guardian
```

**Then update gateway deployment** to use the token

---

### Fix 3: Enable Proactive AI Brain Features

**Configuration needed**:
```yaml
env:
  - name: ENABLE_PROACTIVE_ALERTS
    value: "true"
  - name: PROACTIVE_CHECK_INTERVAL
    value: "300"  # Check every 5 minutes
  - name: AI_BRAIN_CALLBACK_URL
    value: "http://kilo-ai-brain:9004/proactive/trigger"
```

---

### Fix 4: Import Financial Data

**If user has CSV files on HP**, need to:
1. Find the CSV files location
2. Use financial service `/upload` endpoint
3. Or bulk import via database

**Command to find CSVs**:
```bash
ssh kilo@192.168.68.56 "find /home/kilo -name '*.csv' -mtime -30"
```

---

### Fix 5: Enable Nightly Maintenance (Financial Service)

**Add to financial deployment**:
```yaml
env:
  - name: ENABLE_NIGHTLY_MAINTENANCE
    value: "true"
  - name: NIGHTLY_CRON
    value: "0 2 * * *"  # 2am daily
```

---

## 📋 Services Configuration Summary

### Reminder Service
**Current Issues**:
- ❌ All reminders marked as sent
- ✅ APScheduler code present and correct
- ✅ Reminders configured in database
- ❌ Scheduler not triggering because sent=true

**Environment Variables Needed**:
```
AI_BRAIN_CALLBACK_URL=http://kilo-ai-brain:9004/events
HABITS_URL=http://kilo-habits:9000
NOTIFICATION_URL=<external notification service if any>
```

### Financial Service
**Current State**:
- ✅ Database exists with data
- ✅ PVC mounted at `/data`
- ❌ Nightly maintenance not enabled
- ⚠️ User's uploaded CSV data needs importing

**Environment Variables Needed**:
```
ENABLE_NIGHTLY_MAINTENANCE=true
NIGHTLY_CRON=0 2 * * *
```

### AI Brain Service
**Current State**:
- ✅ Connected to llama.cpp on Beelink
- ❌ Not querying microservices for dashboard stats
- ❌ Proactive features not enabled

**Environment Variables Needed**:
```
ENABLE_PROACTIVE=true
PROACTIVE_INTERVAL=300
DASHBOARD_STATS_ENABLED=true
```

### Gateway Service
**Current State**:
- ✅ Routing working
- ❌ Admin endpoints require token (not set)
- ❌ Prometheus metrics aggregation not accessible

**Environment Variables Needed**:
```
ADMIN_TOKEN=<secure-token>
ADMIN_TOKEN_LIST=<comma-separated-tokens>
PROMETHEUS_URL=http://prometheus-kube-prometheus-prometheus.monitoring:9090
```

---

## 🎯 Immediate Actions Required

### Priority 1: Fix Reminder System (3pm alerts)
1. Reset `sent=false` in reminder database
2. Restart kilo-reminder pod
3. Verify scheduler triggers

### Priority 2: Enable Proactive AI Features
1. Configure AI brain with proactive settings
2. Set up bill alert triggers for Feb 1st
3. Test proactive notifications

### Priority 3: Fix Admin Dashboard
1. Set ADMIN_TOKEN in gateway
2. Test `/admin/metrics/summary` endpoint
3. Verify Prometheus data displays

### Priority 4: Import Financial Data
1. Locate uploaded CSV files
2. Import into financial database
3. Verify data shows in frontend

---

## 🔍 Discovery: Existing Proactive Systems

Found comprehensive proactive infrastructure:

**ML Engine**:
- Cron job: 3am nightly model training
- Habit timing predictions
- Optimal reminder time suggestions

**Reminder Service**:
- APScheduler with CronTrigger, DateTrigger, IntervalTrigger
- Preset reminders: laundry, drink_water, shower, brush_teeth, take_meds
- Circuit breaker pattern for resilience
- Integration with habits, camera, meds, ai-brain

**Financial Service**:
- Nightly maintenance at 2am (if enabled)
- Auto-categorization of transactions
- Prometheus metrics instrumentation

**Gateway Service**:
- Admin metrics aggregation
- Circuit breaker monitoring
- Service health checks

---

## ✅ What's Working

- ✅ 12/12 pods running
- ✅ Reminder database has all reminders configured
- ✅ Financial database has transaction data
- ✅ APScheduler code is correct
- ✅ Proactive infrastructure exists in code
- ✅ Bill reminders are configured

---

## ❌ What's Broken

- ❌ All reminders marked as sent=true (scheduler won't trigger)
- ❌ Admin token not configured (can't access metrics)
- ❌ Proactive features not enabled via environment
- ❌ Dashboard stats returning zeros
- ❌ User's uploaded financial data not imported

---

**Root Cause**: Configuration and database state issues from "merge and purge" - services are running but not configured/enabled properly.
