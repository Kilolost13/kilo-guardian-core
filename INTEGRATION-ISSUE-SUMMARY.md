# Kilo Tools Integration - Current Blocker

**Date:** 2026-02-01
**Status:** 🔴 BLOCKED - LLM requests hanging with tool-augmented prompts

---

## Current Situation

### ✅ Everything Works Individually

1. **Tools work perfectly:**
   ```bash
   execute_tool('kubectl_get_pods') → Returns all 13 pods with real data
   ```

2. **llama.cpp works:**
   ```bash
   curl http://192.168.68.60:11434/health → {"status":"ok"}
   ```

3. **K8s integration works:**
   - AI Brain has RBAC permissions
   - K8s Python client initializes successfully
   - Can query pods, services, logs

4. **Code is deployed:**
   - Tools module in pod
   - RAG enhanced with tools
   - Debug logging added

### 🔴 The Problem

**Chat endpoint hangs completely** when trying to process requests.

**Symptoms:**
- curl request to /chat never returns
- Hangs for 30+ seconds
- No response, no error
- No logs generated (RAG code never executes)

**Testing:**
```bash
curl -X POST http://pod-ip:9004/chat \
  -d '{"user":"kyle","message":"hi","context":[]}'
# Hangs forever, no response
```

---

## Root Cause Analysis

### Theory 1: Database/Session Issue (MOST LIKELY)

The RAG code calls `get_session()` to access the database for memories. If the database is locked, missing, or has issues, the entire request hangs before even getting to tool execution.

**Evidence:**
- No `[RAG]` logs appear (code never runs)
- Health endpoint works fine (doesn't use database)
- Hang happens before LLM call

**Fix:**
- Check database connectivity from pod
- Add timeout to database session
- Make database optional for tool-only queries

### Theory 2: Import/Module Loading Issue

Tools or RAG module might be failing to import properly, causing a hang.

**Evidence:**
- Tools import works when tested directly
- But might fail during FastAPI request handling

**Fix:**
- Test imports during startup, not during request
- Add error handling around imports

### Theory 3: LLM Timeout with Tool Data

If tools execute but create a very long prompt, llama.cpp might timeout.

**Evidence:**
- Circuit breaker was blocking 3658 char prompts earlier
- Tool results can be verbose (JSON with all 13 pods)

**Fix:**
- Summarize tool results before adding to prompt
- Increase llama.cpp timeout
- Make tool results more concise

---

## Immediate Next Steps

### Option A: Bypass Database for Testing

Modify RAG to skip memory retrieval temporarily:

```python
def generate_rag_response_with_tools(..., skip_memory=False):
    if skip_memory:
        memory_results = []
    else:
        memory_results = search_memories(...)
```

This will test if database is the blocker.

### Option B: Add Request Timeout

Add timeout to entire chat endpoint:

```python
@app.post("/chat", timeout=60)
async def chat_json(req: ChatRequest):
    ...
```

This prevents infinite hangs.

### Option C: Simplify First

Create a simpler endpoint that just calls tools without RAG:

```python
@app.post("/query")
async def query_tools(req: dict):
    tools = detect_needed_tools(req["message"])
    results = {t: execute_tool(t) for t in tools}
    return {"tools": results}
```

Test if tools work in HTTP context.

---

## What We Know For Sure

1. ✅ Tools code is correct
2. ✅ K8s access works
3. ✅ llama.cpp works
4. ✅ Deployment successful
5. ❌ Something in the /chat request flow hangs
6. ❌ Never reaches RAG code (no logs)
7. ❌ Likely database or import issue

---

## Quick Diagnostic Commands

### Test Database from Pod
```bash
kubectl exec deployment/kilo-ai-brain -- python -c "
from ai_brain.db import get_session
s = get_session()
print('Database OK')
"
```

### Test RAG Import
```bash
kubectl exec deployment/kilo-ai-brain -- python -c "
from ai_brain.rag import generate_rag_response_with_tools
print('RAG import OK')
"
```

### Test Full Flow
```bash
kubectl exec deployment/kilo-ai-brain -- python -c "
from ai_brain.rag import generate_rag_response_with_tools
from ai_brain.db import get_session
result = generate_rag_response_with_tools(
    'test',
    session=get_session(),
    enable_tools=False
)
print(result['response'])
"
```

---

## Recommended Fix Strategy

1. **First:** Test database connectivity from pod
2. **Second:** Create simple /query endpoint without RAG
3. **Third:** Add timeouts to prevent hangs
4. **Fourth:** Make database optional for tool queries
5. **Fifth:** Test with tools + LLM but no memory

Once we identify the exact blocker, we can fix it properly.

---

## User Impact

**What works:**
- Everything except the chat interface
- Tools can be tested via kubectl exec
- Health endpoint responds

**What doesn't work:**
- Can't chat with Kilo
- Can't get intelligent responses
- Tools not accessible to users

**Workaround:**
- Revert to previous AI Brain image (without tools)
- Chat will work but without K8s/service query features
- Tools can be added later once issue is fixed

---

Back to [[TOOLS-STATUS|Tools Status]] | [[LLM-SERVER-VERIFICATION|LLM Setup]]
