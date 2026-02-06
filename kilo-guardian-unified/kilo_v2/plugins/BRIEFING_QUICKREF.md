# Briefing Plugin - Quick Reference

## 🚀 Quick Start

```bash
# Install dependencies
pip install feedparser requests

# Start server
uvicorn kilo_v2.server_core:app --reload

# Test briefing
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"query": "morning briefing"}'
```

## 📝 Query Examples

| Query | Result |
|-------|--------|
| `"morning briefing"` | Full briefing with all sections |
| `"quick update"` | High-priority items only |
| `"what's happening today"` | Calendar + reminders focus |
| `"any home alerts"` | Security monitoring only |
| `"what's the weather"` | Weather forecast |

## 🔌 Data Sources

### ✅ Currently Working (Stubs)
- Weather (returns stub data if no API key)
- Calendar (shows connection instructions)
- Email (shows connection instructions)
- News (uses wizard preferences)
- Life Tracking (reads from `kilo_data/life_tracking.json`)
- Home Monitoring (reads from `kilo_data/security_logs/events.json`)

### 🔧 Requires Setup
- Weather API: Set `OPENWEATHER_API_KEY`
- Email: Configure IMAP in `briefing.json`
- Calendar: Google OAuth credentials
- Banking: Plaid API credentials

## 📊 Response Sections

1. **Greeting** - Time-based personalized greeting
2. **Weather** - Forecast for user's location
3. **Calendar** - Today's events
4. **Email** - Unread count with task matches
5. **Reminders** - Day-of-week tasks
6. **News** - Personalized headlines
7. **Banking** - Bills and alerts
8. **Home Status** - Security monitoring
9. **Summary** - Statistics

## 🎯 Task Matching

The plugin matches tasks across sources:

```python
# Example: "Bills" task matching
Email subject: "Your electric bill is due" → bills
Calendar event: "Payment due" → bills
Day of week: Monday → bills (configured)
Life tracking: "Review finances" → bills
```

## 🏠 Home Alerts

Automatically detects:
- Doors open > 15 minutes
- Unusual motion patterns (>10 events in basement/garage/attic)
- Sensor anomalies

## ⚙️ Configuration

Edit `kilo_v2/plugins/briefing.json`:

```json
{
  "configuration": {
    "email": {"enabled": false},
    "calendar": {"enabled": false},
    "weather": {"enabled": true},
    "life_tracking": {"enabled": true},
    "home_monitoring": {"enabled": true}
  }
}
```

## 🧪 Testing

```bash
# Run briefing via API
curl -X POST http://localhost:8001/api/plugins/execute \
  -H "X-API-Key: YOUR-KEY" \
  -H "Content-Type: application/json" \
  -d '{"plugin":"briefing","query":"give me todays briefing"}'
```

## 📂 File Locations

```
kilo_v2/plugins/
  briefing.py                  # Main plugin
  briefing.json                # Config
  BRIEFING_README.md           # Full docs
  BRIEFING_IMPLEMENTATION_SUMMARY.md  # Implementation details

kilo_v2/user_data/
  preferences.json             # Wizard data (auto-created)

kilo_data/
  life_tracking.json           # Tasks & habits
  security_logs/
    events.json                # Home monitoring
```

## ⚡ Priority Levels

- 🔴 **High**: Calendar events, bills, security alerts
- 🟡 **Medium**: Weather, email summary, news
- 🟢 **Low**: Statistics, summaries

## 🔍 Troubleshooting

| Issue | Solution |
|-------|----------|
| No user preferences found | Run setup wizard at `/wizard.html` |
| Weather not showing | Set `OPENWEATHER_API_KEY` or accept stub |
| Plugin not loading | Check `server.log` for errors |
| No home alerts | Ensure security monitor is running |

## 📚 Documentation

- **Full Guide**: `kilo_v2/plugins/BRIEFING_README.md`
- **Implementation Details**: `kilo_v2/plugins/BRIEFING_IMPLEMENTATION_SUMMARY.md`
- **Plugin System**: `.github/copilot-instructions.md`

## 💡 Tips

1. **Complete wizard first** - Provides name, location, interests
2. **Create life tracking data** - Customize daily tasks
3. **Enable API integrations** - Connect email, calendar, banking
4. **Check health endpoint** - `GET /api/plugins` to see plugin status
5. **Use query variations** - "briefing", "update", "status" all work

## 🎨 Frontend Integration

```typescript
// Fetch and display briefing
const response = await fetch('/api/chat', {
  method: 'POST',
  body: JSON.stringify({ query: 'morning briefing' })
});

const briefing = await response.json();

briefing.sections.forEach(section => {
  displaySection(section.icon, section.title, section.content);
});
```

---

**Need Help?** See full documentation in `BRIEFING_README.md`
