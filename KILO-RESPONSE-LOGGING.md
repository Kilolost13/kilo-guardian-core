# Kilo Response Logging - Quality Monitoring System

**Date:** 2026-02-01
**Status:** ✅ Code Ready - Needs Docker Build
**Purpose:** Track Kilo's responses to detect drift, hallucinations, and quality issues

---

## What This Does

This system automatically logs every response Kilo generates so you can:

1. **Monitor answer quality** - Review what Kilo is actually telling you
2. **Detect drift** - Identify if the model starts saying nonsensical things
3. **Track tool usage** - See which tools are being used for each query
4. **Analyze patterns** - Get statistics on response length, frequency, etc.
5. **Flag problems** - Mark specific responses as problematic for review

---

## Features Implemented

### 1. Automatic Response Logging

Every chat response is now logged to the database with:
- User ID
- User's question (for context)
- Kilo's full response
- Tools used (e.g., `["kubectl_get_pods", "query_reminder_service"]`)
- Response length (character count)
- Model used
- Timestamp
- Flagged status (for marking bad responses)
- Notes field (for review comments)

### 2. New API Endpoints

#### GET `/responses/recent`
Retrieve recent responses for review.

**Parameters:**
- `user_id` (optional) - Filter by specific user
- `limit` (default: 50, max: 500) - Number of responses
- `flagged_only` (default: false) - Only show flagged responses

**Example:**
```bash
curl "http://192.168.68.56:9004/responses/recent?user_id=kyle&limit=20"
```

**Response:**
```json
{
  "count": 20,
  "responses": [
    {
      "id": 1,
      "user_id": "kyle",
      "user_query": "Check K8s pods",
      "response": "Hey Kyle! Here's the latest status...",
      "tools_used": ["kubectl_get_pods"],
      "response_length": 245,
      "model_used": "llama3.1:8b",
      "timestamp": "2026-02-01T21:00:00",
      "flagged": false,
      "notes": null
    }
  ]
}
```

#### POST `/responses/{response_id}/flag`
Flag a response as problematic.

**Parameters:**
- `response_id` - ID of the response to flag
- `notes` (optional) - Why you flagged it

**Example:**
```bash
curl -X POST "http://192.168.68.56:9004/responses/123/flag?notes=Hallucinated+data"
```

#### GET `/responses/stats`
Get statistics for drift detection.

**Parameters:**
- `user_id` (optional) - Filter by user
- `days` (default: 7) - Number of days to analyze

**Example:**
```bash
curl "http://192.168.68.56:9004/responses/stats?days=7"
```

**Response:**
```json
{
  "period_days": 7,
  "total_responses": 143,
  "flagged_responses": 2,
  "flagged_percentage": 1.4,
  "avg_response_length": 287,
  "tool_usage": {
    "kubectl_get_pods": 45,
    "query_reminder_service": 32,
    "query_financial_service": 18
  },
  "user_id": "kyle"
}
```

---

## Files Modified

### 1. `/services/ai_brain/models.py`
Added `KiloResponse` table:

```python
class KiloResponse(SQLModel, table=True):
    """Store Kilo's responses for quality monitoring and drift detection."""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str
    user_query: str  # Store query for context
    response: str  # Kilo's actual response
    tools_used: Optional[str] = Field(default=None)  # JSON list of tools executed
    response_length: int = 0  # Character count
    model_used: Optional[str] = Field(default=None)  # Which LLM model
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    flagged: bool = False  # Manual flag for problematic responses
    notes: Optional[str] = Field(default=None)  # Review notes
```

### 2. `/services/ai_brain/models/__init__.py`
Added `KiloResponse` to exported models list.

### 3. `/services/ai_brain/main.py`
Added:
- Automatic logging after each RAG response
- `/responses/recent` endpoint
- `/responses/{id}/flag` endpoint
- `/responses/stats` endpoint

---

## Deployment Instructions

### Option 1: Quick Deploy (File Copy - Temporary)

**Note:** Changes will be lost on pod restart.

```bash
cd /home/brain_ai/projects/kilo

# Copy files to running pod
POD=$(kubectl get pod -n kilo-guardian -l app=kilo-ai-brain -o jsonpath='{.items[0].metadata.name}')
kubectl cp services/ai_brain/models.py kilo-guardian/$POD:/app/ai_brain/models.py
kubectl cp services/ai_brain/models/__init__.py kilo-guardian/$POD:/app/ai_brain/models/__init__.py
kubectl cp services/ai_brain/main.py kilo-guardian/$POD:/app/ai_brain/main.py

# Restart pod to load changes
kubectl delete pod -n kilo-guardian -l app=kilo-ai-brain
```

### Option 2: Permanent Deploy (Docker Build)

**Recommended for production.**

```bash
cd /home/brain_ai/projects/kilo

# Build new Docker image
docker build -t kilo-ai-brain:response-logging \
             -f services/ai_brain/Dockerfile \
             services/ai_brain

# Tag as latest
docker tag kilo-ai-brain:response-logging kilo-ai-brain:latest

# Import to K3s
docker save kilo-ai-brain:latest -o /tmp/kilo-ai-brain.tar
sudo k3s ctr images import /tmp/kilo-ai-brain.tar
rm /tmp/kilo-ai-brain.tar

# Restart deployment
kubectl rollout restart deployment/kilo-ai-brain -n kilo-guardian

# Wait for ready
kubectl wait --for=condition=ready pod -l app=kilo-ai-brain -n kilo-guardian --timeout=60s

echo "✅ Response logging deployed!"
```

---

## Usage Examples

### Monitor Recent Responses

```bash
# Get last 10 responses
curl "http://192.168.68.56:9004/responses/recent?limit=10" | jq '.responses[] | {id, query: .user_query, response: .response[:100]}'

# Get only flagged responses
curl "http://192.168.68.56:9004/responses/recent?flagged_only=true" | jq
```

### Flag a Bad Response

```bash
# Flag response #42 as problematic
curl -X POST "http://192.168.68.56:9004/responses/42/flag" \
  -d "notes=Model hallucinated pod names that don't exist"
```

### Check Statistics

```bash
# Last 7 days
curl "http://192.168.68.56:9004/responses/stats" | jq

# Last 30 days
curl "http://192.168.68.56:9004/responses/stats?days=30" | jq
```

### Python Script Example

```python
import requests
import json

# Get recent responses
r = requests.get("http://192.168.68.56:9004/responses/recent?limit=50")
data = r.json()

print(f"Total responses: {data['count']}")

# Check for concerning patterns
for resp in data['responses']:
    if resp['response_length'] < 50:
        print(f"⚠️ Very short response #{resp['id']}: {resp['response']}")

    if "I don't know" in resp['response'] and len(resp['tools_used']) > 0:
        print(f"⚠️ Response #{resp['id']} had tools but still said 'I don't know'")
```

---

## Detecting Drift & Quality Issues

### Signs of Model Drift

1. **Increasing "I don't know" responses** even with tools available
2. **Decreasing average response length** (model getting less verbose)
3. **Contradictory responses** to similar questions
4. **Hallucinated data** (making up pod names, services, etc.)
5. **Tool misuse** (using wrong tools for queries)

### Monitoring Checklist

- [ ] Review flagged responses weekly
- [ ] Check response stats for unusual patterns
- [ ] Compare tool usage over time
- [ ] Spot-check random responses for accuracy
- [ ] Verify responses against actual data (pods, services, etc.)

---

## Database Schema

The `kilo_response` table is created automatically on startup:

```sql
CREATE TABLE kilo_response (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR NOT NULL,
    user_query VARCHAR NOT NULL,
    response VARCHAR NOT NULL,
    tools_used VARCHAR,  -- JSON array
    response_length INTEGER DEFAULT 0,
    model_used VARCHAR,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    flagged BOOLEAN DEFAULT 0,
    notes VARCHAR
);

CREATE INDEX idx_kilo_response_user ON kilo_response(user_id);
CREATE INDEX idx_kilo_response_timestamp ON kilo_response(timestamp DESC);
CREATE INDEX idx_kilo_response_flagged ON kilo_response(flagged);
```

Location: `/data/ai_brain.db` (inside pod)

---

## Privacy Note

**User queries ARE logged** in this system (for context), unlike the general chat logs which only log Kilo's responses. This is necessary to detect hallucinations and quality issues by comparing queries to responses.

If privacy is a concern:
- User queries are only stored locally in the pod
- Not transmitted anywhere outside the cluster
- Can be disabled by commenting out the logging code in `main.py`

---

## Troubleshooting

### Responses Not Being Logged

Check if the table was created:
```bash
kubectl exec -n kilo-guardian deployment/kilo-ai-brain -- python -c "
from ai_brain.db import get_session
from ai_brain.models import KiloResponse
s = get_session()
print('Table exists, count:', s.query(KiloResponse).count())
"
```

### ImportError for KiloResponse

Verify the model is in models.py:
```bash
kubectl exec -n kilo-guardian deployment/kilo-ai-brain -- grep "class KiloResponse" /app/ai_brain/models.py
```

If missing, the Docker image needs to be rebuilt.

### Endpoint Returns 404

Check if the new code is deployed:
```bash
kubectl exec -n kilo-guardian deployment/kilo-ai-brain -- grep "responses/recent" /app/ai_brain/main.py
```

If missing, copy main.py and restart pod.

---

## Next Steps

1. **Deploy** using Option 2 (Docker build) for permanence
2. **Test** by chatting with Kilo on the tablet
3. **Verify** logging with `/responses/recent`
4. **Monitor** responses regularly for quality
5. **Flag** any problematic responses you find

---

## Related Files

- [[TOOLS-WORKING.md]] - Tools integration that this monitors
- [[KILO-INTELLIGENCE-TEST.md]] - Quality tests to run
- Implementation: `services/ai_brain/main.py` (lines 569-605, 1632-1747)

---

**Ready to deploy!** 🚀

Once the Docker image is built and deployed, Kilo will automatically start logging all responses for quality monitoring.
