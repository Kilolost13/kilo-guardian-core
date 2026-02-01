# Kilo Proactive Agent - Complete Guide

**Date:** 2026-01-31
**Status:** ✅ WORKING

---

## What Is This?

Your Kilo Proactive Agent is an **intelligent personal assistant** that:

✅ **Monitors your reminders** - Tells you about upcoming medication reminders, tasks, etc.
✅ **Tracks spending** - Alerts when you're approaching budget limits
✅ **Watches habits** - Reminds you about incomplete daily habits
✅ **Analyzes trends** - Provides spending insights and patterns

**It's not just monitoring K3s** - it's **USING your services** to help you manage life!

---

## What It Does Right Now

### 1. Reminder Notifications
```
⏰ REMINDER in 90 min: Clean Cat Box (daily)
⏰ REMINDER in 30 min: Take Adderall (daily)
```

The agent checks your reminder service and tells you about:
- Medication reminders (Adderall, Effexor, Buspirone)
- Daily tasks (cat box, laundry, etc.)
- Upcoming events

**Check window:** Next 2 hours

### 2. Budget Alerts
```
🚨 BUDGET EXCEEDED: Food - $780.00 / $750.00 (104%)
⚠️ BUDGET WARNING: Weed - $540.00 / $600.00 (90%)
💡 BUDGET HEADS UP: Gas - $160.00 / $200.00 (80%)
```

The agent monitors your budgets and alerts at:
- 80% - Heads up
- 90% - Warning
- 100%+ - Exceeded

### 3. Habit Reminders
```
📋 HABIT REMINDER: 'Exercise' - 0/1 done today
📋 HABIT REMINDER: 'Take vitamins' - 0/1 done today
```

Checks at 2pm if you haven't completed your daily habits yet.

### 4. Spending Insights
```
💰 Total spending: $189,688.48
💰 Total income: $759,704.99
💰 Spending 📉 decreased by 21.5% from last month
💰 📊 Average transaction: $101.55
```

Provides trends and insights about your spending patterns.

---

## How It Works

```
┌──────────────────────────────────────────────────┐
│  HP SERVER (192.168.68.56)                      │
├──────────────────────────────────────────────────┤
│                                                   │
│  Kilo Proactive Agent                            │
│         ↓                                         │
│         ↓ Every 5 minutes, check:                │
│         ↓                                         │
│  ┌──────────────────────────────────────┐        │
│  │ 📅 Reminder Service (9002)           │        │
│  │    "What's upcoming?"                │        │
│  └──────────────────────────────────────┘        │
│         ↓                                         │
│  ┌──────────────────────────────────────┐        │
│  │ 💰 Financial Service (9005)          │        │
│  │    "How's my spending?"              │        │
│  └──────────────────────────────────────┘        │
│         ↓                                         │
│  ┌──────────────────────────────────────┐        │
│  │ 📋 Habits Service (9000)             │        │
│  │    "What habits am I missing?"       │        │
│  └──────────────────────────────────────┘        │
│         ↓                                         │
│  ┌──────────────────────────────────────┐        │
│  │ 💊 Meds Service (9001)               │        │
│  │    "Any medications due?"            │        │
│  └──────────────────────────────────────┘        │
│                                                   │
│  ↓ Agent analyzes everything                     │
│  ↓ Prints notifications                          │
│                                                   │
└──────────────────────────────────────────────────┘
```

---

## How to Use It

### Quick Test
```bash
ssh kilo@192.168.68.56
~/start-proactive-agent.sh once
```

This runs one check cycle and shows what needs your attention.

### Continuous Monitoring
```bash
ssh kilo@192.168.68.56
~/start-proactive-agent.sh
```

Runs continuously, checking every 5 minutes. Press Ctrl+C to stop.

### Test Service Connectivity
```bash
ssh kilo@192.168.68.56
~/start-proactive-agent.sh test
```

Shows raw data from all services to verify connections.

---

## Running It Automatically

### Option 1: Screen Session (Easy)
```bash
ssh kilo@192.168.68.56
screen -S kilo-agent
~/start-proactive-agent.sh
# Press Ctrl+A, then D to detach

# To reattach:
screen -r kilo-agent
```

### Option 2: Systemd Service (Proper)
Create `/etc/systemd/system/kilo-agent.service`:
```ini
[Unit]
Description=Kilo Proactive Life Management Agent
After=network.target k3s.service
Wants=k3s.service

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
sudo systemctl daemon-reload
sudo systemctl enable kilo-agent
sudo systemctl start kilo-agent

# View logs:
sudo journalctl -u kilo-agent -f
```

---

## Configuration

### Check Interval
Edit `kilo_proactive_agent.py`, line ~407:
```python
agent.run_loop(check_interval=300)  # 300 seconds = 5 minutes
```

### Notification Timing
Edit reminder check window (line ~204):
```python
if timedelta(0) <= time_until <= timedelta(hours=2):  # Change hours
```

### Budget Alert Thresholds
Edit budget analysis (line ~249):
```python
if percentage >= 100:  # Exceeded
if percentage >= 90:   # Warning
if percentage >= 80:   # Heads up
```

---

## Example Output

```
🔧 Service ClusterIPs:
  Reminder: 10.43.144.204:9002
  Financial: 10.43.216.158:9005
  Habits: 10.43.142.9:9000
  Meds: 10.43.214.225:9001

🔍 Checking all services...

======================================================================
🔔 KILO HAS THINGS FOR YOU TO KNOW
======================================================================

📌 REMINDERS:
   ⏰ REMINDER in 90 min: Clean Cat Box (daily)
   ⏰ REMINDER in 120 min: Take Adderall (daily)

📌 BUDGETS:
   ⚠️ BUDGET WARNING: Food - $675.00 / $750.00 (90%)
   💡 BUDGET HEADS UP: Weed - $480.00 / $600.00 (80%)

📌 HABITS:
   📋 HABIT REMINDER: 'Exercise' - 0/1 done today

📌 SPENDING:
   💰 Total spending: $189,688.48
   💰 Total income: $759,704.99
   💰 Spending 📉 decreased by 21.5% from last month

======================================================================

💤 Next check in 5 minutes...
----------------------------------------------------------------------
```

---

## Your Services and Their Data

### Reminders You Have
- Take Adderall (daily, 7:30am and 3:00pm)
- Take Effexor (daily, 7:30am and 3:00pm)
- Take Buspirone (daily, 7:30am, 3:00pm, 9:00pm)
- Clean Cat Box (recurring)
- Other custom reminders

### Budgets You Track
- Mortgage: $640/month
- Child Support: $800/month
- Alimony: $400/month
- Food: $750/month
- Weed: $600/month
- Electric: $250/month
- WiFi: $52/month
- Streaming: $100/month
- Car Insurance: $250/month
- Phone: $165/month
- Pets: $150/month
- Water: $40/month
- People Supplies: $100/month

### Current Financial Summary
- Total Expenses: $189,688.48
- Total Income: $759,704.99
- Balance: $570,016.51

---

## What's Next

### Phase 2: Add LLM Intelligence
Currently the agent uses simple logic. Next step is to add LLM decision-making so it can:
- Understand complex spending patterns
- Suggest budget adjustments based on trends
- Correlate reminders with habits
- Learn your preferences over time

**To enable:**
1. Start llama.cpp server with Phi-3 model
2. Agent will use LLM for smarter analysis

### Phase 3: Interactive Mode
Add ability to:
- Respond to agent questions
- Mark habits complete via agent
- Add reminders through agent
- Get spending breakdowns on demand

### Phase 4: Notification Integration
Send notifications to:
- Slack/Discord
- Email
- SMS
- Desktop notifications (via SSH)
- Web UI

---

## Files

**On HP Server:**
- `~/kilo_proactive_agent.py` - Main agent code
- `~/start-proactive-agent.sh` - Launcher script with ClusterIP discovery

**On Beelink:**
- `/home/brain_ai/projects/kilo/kilo_proactive_agent.py` - Source code
- `/home/brain_ai/projects/kilo/start-proactive-agent.sh` - Launcher source
- `/home/brain_ai/projects/kilo/PROACTIVE-AGENT-GUIDE.md` - This file

---

## Troubleshooting

### Agent can't connect to services
```bash
# Check if K3s is running
ssh kilo@192.168.68.56 'sudo kubectl get pods -n kilo-guardian'

# Check if services are accessible
ssh kilo@192.168.68.56 'curl -s http://10.43.144.204:9002/status'
```

### No notifications showing
- Agent only notifies once per item (to avoid spam)
- Restart agent to reset notification tracking
- Check if reminders are actually within 2-hour window

### Services returning empty data
- Financial service might have no transactions this month
- Habits service might have no habits defined yet
- This is normal if you haven't added data to those services

---

## Summary

You now have a **working, functional, intelligent agent** that:

✅ Monitors your actual life data (not just system health)
✅ Uses your K3s services for their intended purposes
✅ Proactively notifies you about important things
✅ Tracks spending, reminders, habits, and medications
✅ Runs continuously in the background
✅ Can be extended with LLM intelligence

**Your agent is ALIVE and WORKING!** 🎉

---

Back to [[README|Kilo Project Docs]]
