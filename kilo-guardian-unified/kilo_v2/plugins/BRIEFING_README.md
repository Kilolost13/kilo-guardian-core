# Kilo Guardian Briefing Plugin

Comprehensive daily briefing system that aggregates multiple data sources to provide personalized status updates, reminders, and alerts.

## 🌟 Features

### Core Capabilities
- **🌤️ Weather Forecasts** - Location-based weather from OpenWeatherMap
- **📅 Calendar Integration** - Today's schedule and upcoming events
- **📧 Email Summary** - Unread count with intelligent task matching
- **✅ Life Tracking** - Day-of-week reminders for recurring tasks
- **📰 Personalized News** - Feed aggregation based on wizard preferences
- **💰 Banking Alerts** - Bill reminders and balance warnings (Plaid)
- **🏠 Home State Monitoring** - Sensor anomaly detection and alerts
- **📊 Smart Statistics** - Summary counts and priority indicators

### Intelligent Task Matching

The briefing plugin matches activities from multiple sources:

| Task Type | Email Keywords | Day of Week | Calendar Events |
|-----------|---------------|-------------|-----------------|
| **Bills** | "bill", "payment", "invoice" | Monday | "Payment due" |
| **Laundry** | "laundry", "wash clothes" | Wednesday | - |
| **Groceries** | "grocery", "shopping" | Wednesday | "Store pickup" |
| **Cleaning** | "clean", "vacuum" | Friday | - |
| **Medication** | "prescription", "pills" | Daily | "Take meds" |

### Home State Alerts

Reports critical anomalies such as:
- "⚠️ Back door open for 20 min with no one around"
- "🚨 Unusual activity: 15 motion events in basement"
- "❗ Front door opened 5 times today (unusual)"

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Core requirements (required)
pip install feedparser requests

# Optional integrations
pip install imapclient caldav google-api-python-client plaid-python
```

### 2. Configure API Keys (Optional)

Set environment variables for enhanced features:

```bash
# Weather API (optional, stub used if not set)
export OPENWEATHER_API_KEY="your_api_key_here"

# Banking integration (optional)
export PLAID_CLIENT_ID="your_client_id"
export PLAID_SECRET="your_secret"

# Google Calendar (requires OAuth JSON file)
export GOOGLE_CALENDAR_CREDENTIALS="/path/to/credentials.json"
```

### 3. Complete Setup Wizard

The briefing plugin uses data from the setup wizard:
- **Location** → Weather forecasts
- **News Topics** → Personalized news feeds
- **OAuth Connections** → Email/calendar integration

Access the wizard at: `http://localhost:8000/wizard.html`

### 4. Test the Plugin

```bash
# Start Kilo Guardian
cd /path/to/kilos-bastion-ai
uvicorn kilo_v2.server_core:app --reload

# Request a briefing via chat API
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"query": "morning briefing"}'
```

## 📝 Usage Examples

### Morning Briefing (Full)
**Query:** `"morning briefing"` or `"give me today's briefing"`

Includes:
- ✅ Time-based greeting
- 🌤️ Weather forecast
- 📅 Calendar events (all day)
- 📧 Email summary with task matches
- ✅ Day-of-week reminders (e.g., "Laundry day!")
- 📰 Personalized news headlines
- 💰 Banking alerts (if enabled)
- 🏠 Home state monitoring
- 📊 Summary statistics

### Quick Update
**Query:** `"quick update"` or `"brief me"`

Returns high-priority items only (calendar, urgent emails, critical alerts).

### Specific Sections
- **Calendar:** `"what's on my schedule today"`
- **Home alerts:** `"any home alerts"` or `"home status"`
- **News:** `"give me the news"`
- **Weather:** `"what's the weather"`

## 🔧 Configuration

Edit `kilo_v2/plugins/briefing.json` to customize:

```json
{
  "configuration": {
    "email": {
      "enabled": false,
      "imap_server": "imap.gmail.com",
      "imap_port": 993
    },
    "weather": {
      "enabled": true,
      "provider": "openweathermap"
    },
    "life_tracking": {
      "enabled": true
    },
    "home_monitoring": {
      "enabled": true,
      "door_open_threshold_minutes": 15,
      "motion_threshold_count": 10
    }
  }
}
```

### Customizing Task Patterns

Edit task patterns directly in `briefing.py`:

```python
self.task_patterns = {
    "laundry": ["laundry", "wash clothes", "washing", "dryer"],
    "bills": ["bill", "payment", "invoice", "due", "account"],
    # Add your custom patterns here
    "pet_care": ["vet", "dog food", "cat litter"]
}
```

### Weekly Task Schedule

Customize day-of-week reminders:

```python
self.weekly_tasks = {
    "Monday": ["bills", "planning", "team meeting"],
    "Wednesday": ["laundry", "groceries"],
    "Friday": ["cleaning", "review week"],
    "Sunday": ["meal prep", "family time"]
}
```

## 🔌 Integrations

### Email Integration (IMAP)

1. Enable IMAP in your email provider (Gmail, Outlook, etc.)
2. Generate app-specific password for security
3. Set configuration:

```json
{
  "email": {
    "enabled": true,
    "imap_server": "imap.gmail.com",
    "imap_port": 993,
    "username": "your_email@gmail.com",
    "password": "app_specific_password"
  }
}
```

### Calendar Integration (Google Calendar)

1. Create Google Cloud project: https://console.cloud.google.com/
2. Enable Google Calendar API
3. Download OAuth credentials JSON
4. Set environment variable:

```bash
export GOOGLE_CALENDAR_CREDENTIALS="/path/to/credentials.json"
```

5. Mark calendar as connected in wizard OAuth step

### Banking Integration (Plaid)

1. Sign up for Plaid: https://plaid.com/
2. Obtain client ID and secret
3. Set environment variables:

```bash
export PLAID_CLIENT_ID="your_client_id"
export PLAID_SECRET="your_secret"
```

4. Mark banking as connected in wizard OAuth step

### Life Tracking Data

Create a life tracking file at `kilo_data/life_tracking.json`:

```json
{
  "tasks": [
    {
      "name": "Take vitamins",
      "frequency": "daily",
      "completed": false,
      "last_completed": null
    },
    {
      "name": "Water plants",
      "frequency": "weekly",
      "day": "Sunday",
      "completed": false
    }
  ]
}
```

## 📊 Response Format

The briefing plugin returns structured JSON:

```json
{
  "type": "briefing",
  "briefing_type": "morning",
  "timestamp": "2025-12-01T08:30:00",
  "user": "John",
  "sections": [
    {
      "title": "Greeting",
      "content": "Good morning, John!",
      "subtitle": "Sunday, December 1, 2025",
      "icon": "👋",
      "priority": "high"
    },
    {
      "title": "Weather",
      "content": "Temperature: 72°F / 22°C\nConditions: Partly cloudy",
      "icon": "🌤️",
      "priority": "medium"
    },
    {
      "title": "Today's Schedule",
      "content": "2 events today:\n• 9:00 AM - Team standup\n• 2:00 PM - Project review",
      "icon": "📅",
      "priority": "high",
      "count": 2
    },
    {
      "title": "Email Summary",
      "content": "5 unread messages\n⚠️ 3 emails about bills/payments",
      "icon": "📧",
      "priority": "high",
      "unread": 5,
      "task_matches": {"bills": 3}
    },
    {
      "title": "Reminders & Tasks",
      "content": "Tasks for Sunday:\n• Meal Prep\n• Review Week",
      "icon": "✅",
      "priority": "high",
      "count": 2
    },
    {
      "title": "Home Status Alerts",
      "content": "⚠️ Back door open for 20 min",
      "icon": "🏠",
      "priority": "high",
      "count": 1
    },
    {
      "title": "Summary",
      "content": "📊 Briefing Summary:\n• 6 sections\n• 4 high-priority items",
      "icon": "📊",
      "priority": "low",
      "stats": {
        "total_sections": 6,
        "high_priority": 4,
        "total_items": 8
      }
    }
  ]
}
```

## 🎨 Frontend Integration

Display briefings in your UI:

```typescript
// Fetch briefing
const response = await fetch('/api/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'your-api-key'
  },
  body: JSON.stringify({ query: 'morning briefing' })
});

const briefing = await response.json();

// Render sections
briefing.sections.forEach(section => {
  console.log(`${section.icon} ${section.title}`);
  console.log(section.content);
  
  // Apply priority styling
  const cssClass = section.priority === 'high' ? 'urgent' : 'normal';
});
```

## 🔍 Troubleshooting

### "No user preferences found"
Run the setup wizard first: `http://localhost:8000/wizard.html`

### Weather not showing
Set `OPENWEATHER_API_KEY` environment variable or accept stub weather data.

### Email/Calendar not connected
1. Complete OAuth setup in wizard
2. Verify credentials are correct
3. Check that services are marked as "connected" in `preferences.json`

### No home alerts
Ensure `security_monitor.py` is running and generating events in `kilo_data/security_logs/events.json`.

### Plugin not loading
Check `server.log` for errors:
```bash
tail -f server.log | grep -i briefing
```

## 🛠️ Development

### Adding New Data Sources

1. Create a new method in `BriefingPlugin`:

```python
def _get_custom_data(self) -> Optional[dict]:
    """Fetch custom data source."""
    try:
        # Your implementation here
        return {
            "title": "Custom Section",
            "content": "Your content",
            "icon": "🎯",
            "priority": "medium"
        }
    except Exception as e:
        logger.error(f"Custom data error: {e}")
        return None
```

2. Add to `execute()` method:

```python
# In execute() method
custom = self._get_custom_data()
if custom:
    briefing["sections"].append(custom)
```

### Testing Task Matching

```python
# Test email task matching
python -c "
from kilo_v2.plugins.briefing import BriefingPlugin
plugin = BriefingPlugin()

# Simulate email subject
email_subject = 'Your electric bill is due'
for task, keywords in plugin.task_patterns.items():
    if any(kw in email_subject.lower() for kw in keywords):
        print(f'Matched task: {task}')
"
```

## 📚 Additional Resources

- [Setup Wizard Documentation](../../SETUP_WIZARD.md)
- [Plugin Development Guide](../.github/copilot-instructions.md)
- [Security Monitor Integration](../../ATTACK_MONITORING.md)
- [Life Tracker Plugin](./life_tracker.py)

## 🤝 Contributing

To extend the briefing plugin:
1. Follow the existing section structure
2. Handle missing data gracefully (return `None`)
3. Include priority indicators (`high`, `medium`, `low`)
4. Add icons for visual clarity
5. Test with and without wizard setup

## 📄 License

Part of Kilo Guardian - see repository root for license information.
