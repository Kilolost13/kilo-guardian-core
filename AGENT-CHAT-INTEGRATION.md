# Kilo Agent-Chat Integration - Complete Guide

**Status:** ✅ BACKEND WORKING - Frontend integration pending
**Date:** 2026-01-31

---

## What's Working Now

### ✅ Backend Integration Complete

**1. Agent API Service Running**
- Service: `kilo-agent-api` on HP server
- Port: 9200
- Status: Active and running
- Purpose: Bridge between proactive agent and chat frontend

**2. Proactive Agent Sends Notifications**
- Agent checks services every 5 minutes
- Detects reminders, budgets, habits, spending
- Posts notifications to Agent API
- Example messages:
  ```
  ⏰ REMINDER in 58 min: Clean Cat Box (daily)
  ⏰ REMINDER in 118 min: Do Laundry (daily)
  💰 Total spending: $189,688.48
  💰 Spending 📉 decreased by 21.5% from last month
  ```

**3. Message Queue Working**
- Messages stored in memory
- Retrieved via REST API
- Timestamped and categorized
- Last 5 minutes of messages available

---

## API Endpoints Available

All endpoints run on `http://192.168.68.56:9200`

### GET /agent/messages
Get pending agent notifications for display in chat

**Query Parameters:**
- `since_minutes` (default: 5) - Get messages from last N minutes
- `count` (default: 20) - Max messages to return

**Response:**
```json
{
  "messages": [
    {
      "type": "reminder",
      "content": "⏰ REMINDER in 58 min: Clean Cat Box",
      "priority": "normal",
      "timestamp": "2026-01-31T12:01:52.399890",
      "metadata": {}
    }
  ]
}
```

### POST /agent/command
Send command from chat to agent

**Body:**
```json
{
  "command": "show my spending today",
  "params": {},
  "user": "user"
}
```

**Response:**
```json
{
  "success": true,
  "message": "💰 **Financial Summary:**\n• Expenses: $189,688.48\n• Income: $759,704.99\n• Balance: $570,016.51",
  "data": {...}
}
```

**Supported Commands:**
- "show reminders" or "what reminders"
- "show spending" or "my money"
- "show habits" or "my habits"
- "show meds" or "medications"

### GET /agent/status
Get agent API status

**Response:**
```json
{
  "status": "ok",
  "queue_size": 6,
  "recent_count": 5,
  "last_message": "2026-01-31T12:01:52.414118"
}
```

### GET /health
Health check endpoint

---

## How It Works

```
┌──────────────────────────────────────────────────┐
│  Proactive Agent (runs every 5 min)             │
│  - Checks reminders, budgets, habits, spending  │
│  - Detects things that need attention           │
│              ↓                                   │
│  Sends POST to /agent/notify                    │
└──────────────────┬───────────────────────────────┘
                   │
                   ↓
┌──────────────────────────────────────────────────┐
│  Agent API Service (port 9200)                   │
│  - Receives notifications                        │
│  - Stores in memory queue                        │
│  - Provides REST endpoints                       │
└──────────────────┬───────────────────────────────┘
                   │
                   ↓
┌──────────────────────────────────────────────────┐
│  Frontend Dashboard (YOUR TABLET)                │
│  - Polls GET /agent/messages every 30 seconds    │
│  - Displays in chat interface                    │
│  - Sends commands via POST /agent/command        │
└──────────────────────────────────────────────────┘
```

---

## Testing the Integration

### Test 1: Check Messages Are Queued
```bash
curl http://192.168.68.56:9200/agent/messages | jq .
```

Should return recent agent notifications.

### Test 2: Send a Command
```bash
curl -X POST http://192.168.68.56:9200/agent/command \
  -H "Content-Type: application/json" \
  -d '{"command":"show my spending"}'
```

Should return financial summary.

### Test 3: Run Agent and Check Queue
```bash
ssh kilo@192.168.68.56
~/start-proactive-agent.sh once
curl http://localhost:9200/agent/messages | jq .
```

---

## What's Next: Frontend Integration

To complete the integration, the React frontend needs updates:

### Step 1: Add Agent Message Polling

**File:** `/frontend/kilo-react-frontend/src/pages/Dashboard.tsx`

Add polling to fetch agent messages:
```typescript
useEffect(() => {
  const fetchAgentMessages = async () => {
    try {
      const response = await axios.get('/api/agent/messages');
      const agentMessages = response.data.messages;

      // Add to chat as system messages
      agentMessages.forEach(msg => {
        addMessage({
          id: uuidv4(),
          role: 'ai',
          content: msg.content,
          timestamp: new Date(msg.timestamp)
        });
      });
    } catch (error) {
      console.error('Error fetching agent messages:', error);
    }
  };

  // Poll every 30 seconds
  const interval = setInterval(fetchAgentMessages, 30000);
  fetchAgentMessages(); // Initial fetch

  return () => clearInterval(interval);
}, []);
```

### Step 2: Add Command Handling

When user sends a message, check if it's an agent command:
```typescript
const handleSendMessage = async (message: string) => {
  // Check if message is agent command
  const agentKeywords = ['remind', 'spending', 'habit', 'med', 'budget'];
  const isAgentCommand = agentKeywords.some(kw =>
    message.toLowerCase().includes(kw)
  );

  if (isAgentCommand) {
    // Send to agent
    const response = await axios.post('/api/agent/command', {
      command: message,
      user: 'user'
    });

    addMessage({
      id: uuidv4(),
      role: 'ai',
      content: response.data.message,
      timestamp: new Date()
    });
  } else {
    // Send to regular AI chat
    // ... existing chat logic
  }
};
```

### Step 3: Update Gateway Routing

**File:** Gateway service configuration

Add proxy rules:
```
/api/agent/* → http://192.168.68.56:9200/agent/*
```

Or access directly from frontend:
```typescript
const AGENT_API_URL = 'http://192.168.68.56:9200';
```

---

## Services Status

### On HP Server (192.168.68.56)

**Running Services:**
- ✅ Agent API (port 9200) - systemd service
- ✅ Proactive Agent - can run manually or as systemd service
- ✅ All Kilo services (reminder, financial, habits, meds)

**Service Files:**
- `/etc/systemd/system/kilo-agent-api.service` - Agent API
- `/home/kilo/kilo_agent_api.py` - API code
- `/home/kilo/kilo_proactive_agent.py` - Agent code
- `/home/kilo/start-proactive-agent.sh` - Agent launcher

**Commands:**
```bash
# Check Agent API status
sudo systemctl status kilo-agent-api

# View Agent API logs
sudo journalctl -u kilo-agent-api -f

# Run proactive agent once
~/start-proactive-agent.sh once

# Run proactive agent continuously
~/start-proactive-agent.sh

# Test API
curl http://localhost:9200/agent/status
```

---

## Example User Experience (After Frontend Integration)

### Scenario 1: Proactive Reminder

**Agent detects reminder coming up:**
```
🤖 KILO: ⏰ REMINDER in 30 min: Take Adderall
```

**You can respond:**
```
You: Thanks! Can you show my meds?

🤖 KILO: 💊 **Your Medications:**
• Adderall - daily, 7:30am & 3:00pm
• Effexor - daily, 7:30am & 3:00pm
• Buspirone - daily, 7:30am, 3:00pm, 9:00pm
```

### Scenario 2: Budget Alert

**Agent detects budget issue:**
```
🤖 KILO: ⚠️ BUDGET WARNING: Food - $675/$750 (90%)
```

**You can ask:**
```
You: Show my full spending

🤖 KILO: 💰 **Financial Summary:**
• Expenses: $189,688.48
• Income: $759,704.99
• Balance: $570,016.51

🚨 **Over Budget:** 0 categories
⚠️ **Warning:** 1 category near limit
```

### Scenario 3: Habit Check

**Agent reminds in afternoon:**
```
🤖 KILO: 📋 HABIT REMINDER: 'Exercise' - 0/1 done today
```

**You can:**
```
You: Show my habits

🤖 KILO: 📋 **Your Habits:**
✅ Take vitamins (1/1)
⏳ Exercise (0/1)
⏳ Drink water (2/8)
```

---

## Auto-Start Configuration

### Option 1: Run Proactive Agent as Systemd Service

Create `/etc/systemd/system/kilo-agent.service`:
```ini
[Unit]
Description=Kilo Proactive Life Management Agent
After=network.target kilo-agent-api.service
Requires=kilo-agent-api.service

[Service]
Type=simple
User=kilo
WorkingDirectory=/home/kilo
ExecStart=/home/kilo/start-proactive-agent.sh
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable kilo-agent
sudo systemctl start kilo-agent
```

### Option 2: Screen Session (Temporary)

```bash
ssh kilo@192.168.68.56
screen -S kilo-agent
~/start-proactive-agent.sh

# Detach: Ctrl+A then D
# Reattach: screen -r kilo-agent
```

---

## Troubleshooting

### Agent messages not showing?
```bash
# Check Agent API is running
sudo systemctl status kilo-agent-api

# Check for recent messages
curl http://localhost:9200/agent/messages

# Run agent manually
~/start-proactive-agent.sh once
```

### Commands not working?
```bash
# Test command directly
curl -X POST http://localhost:9200/agent/command \
  -H "Content-Type: application/json" \
  -d '{"command":"show reminders"}'
```

### Services not accessible?
```bash
# Check K3s services
sudo kubectl get pods -n kilo-guardian
sudo kubectl get svc -n kilo-guardian

# Test service directly
curl http://10.43.144.204:9002/
```

---

## Summary

### ✅ What's Complete
1. Agent API service running on port 9200
2. Proactive agent sends notifications to API
3. Message queue working and storing notifications
4. REST endpoints ready for frontend
5. Command handling implemented

### 🔄 What's Pending
1. Frontend React code to poll `/agent/messages`
2. Frontend command routing to `/agent/command`
3. UI styling for agent messages vs regular chat
4. Gateway routing configuration (or direct access)

### 🎯 Result
Once frontend is updated, you'll have:
- **Proactive notifications** in chat from the agent
- **Interactive commands** to query your data
- **All accessible from your tablet** via the dashboard
- **Real-time updates** every 30-60 seconds

---

**Your agent is now integrated with chat at the API level!**
**The backend is complete and working.**
**Frontend updates will make it visible to you on the tablet.**

Back to [[README|Kilo Project Docs]]
