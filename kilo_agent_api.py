#!/usr/bin/env python3
"""
Kilo Agent API - Lightweight service for agent-chat integration

This provides REST API endpoints that:
- Receive notifications from the proactive agent
- Store them in memory for the chat frontend to retrieve
- Handle commands from the chat and route to services
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import deque
import httpx
import os
import uvicorn

app = FastAPI(title="Kilo Agent API", version="1.0.0")

# CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== Data Models ====================

class AgentMessage(BaseModel):
    type: str
    content: str
    priority: str = "normal"
    timestamp: datetime = None
    metadata: Dict[str, Any] = {}

    def __init__(self, **data):
        if 'timestamp' not in data or data['timestamp'] is None:
            data['timestamp'] = datetime.now()
        super().__init__(**data)


class AgentCommand(BaseModel):
    command: str
    params: Dict[str, Any] = {}
    user: str = "user"


# ==================== In-Memory Message Queue ====================

class MessageQueue:
    def __init__(self, max_size=100):
        self.messages = deque(maxlen=max_size)

    def add(self, message: AgentMessage):
        self.messages.append(message)

    def get_recent(self, count=10):
        msgs = list(self.messages)
        return msgs[-count:] if len(msgs) > count else msgs

    def get_since(self, since: datetime):
        return [msg for msg in self.messages if msg.timestamp >= since]


message_queue = MessageQueue()

# ==================== Service URLs ====================

def get_service_url(service: str) -> str:
    """Get URL for a Kilo service"""
    # Try environment variable first
    env_var = f"{service.upper()}_URL"
    url = os.getenv(env_var)
    if url:
        return url

    # Default ports
    ports = {
        'reminder': 9002,
        'financial': 9005,
        'habits': 9000,
        'meds': 9001
    }
    port = ports.get(service, 9000)
    return f"http://localhost:{port}"


# ==================== API Endpoints ====================

@app.get("/")
async def root():
    return {
        "service": "Kilo Agent API",
        "status": "running",
        "version": "1.0.0",
        "endpoints": [
            "/agent/notify",
            "/agent/messages",
            "/agent/command",
            "/agent/status"
        ]
    }


@app.post("/agent/notify")
async def notify(message: Dict[str, Any]):
    """Receive notification from proactive agent"""
    try:
        msg = AgentMessage(**message)
        message_queue.add(msg)
        return {"status": "ok", "message": "Notification queued"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/agent/messages")
async def get_messages(since_minutes: int = 5, count: int = 20):
    """Get recent agent messages"""
    since = datetime.now() - timedelta(minutes=since_minutes)
    messages = message_queue.get_since(since)

    return {
        "messages": [
            {
                "type": msg.type,
                "content": msg.content,
                "priority": msg.priority,
                "timestamp": msg.timestamp.isoformat(),
                "metadata": msg.metadata
            }
            for msg in messages[-count:]
        ]
    }


@app.post("/agent/command")
async def execute_command(command: Dict[str, Any]):
    """Execute a command through the agent"""
    try:
        cmd = AgentCommand(**command)
        response = await handle_command(cmd)
        return response
    except Exception as e:
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "data": None
        }


@app.get("/agent/status")
async def get_status():
    """Get agent API status"""
    recent = message_queue.get_recent(5)
    return {
        "status": "ok",
        "queue_size": len(message_queue.messages),
        "recent_count": len(recent),
        "last_message": recent[-1].timestamp.isoformat() if recent else None
    }


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy"}


# ==================== Command Handler ====================

async def handle_command(cmd: AgentCommand) -> Dict[str, Any]:
    """Route command to appropriate service"""
    command_text = cmd.command.lower().strip()

    # Parse intent
    if any(word in command_text for word in ["remind", "reminder"]):
        return await get_reminders()
    elif any(word in command_text for word in ["spend", "money", "budget", "financial"]):
        return await get_spending()
    elif any(word in command_text for word in ["habit"]):
        return await get_habits()
    elif any(word in command_text for word in ["med", "medication"]):
        return await get_medications()
    else:
        return {
            "success": False,
            "message": "I can help with: reminders, spending, habits, or medications",
            "data": None
        }


async def get_reminders():
    """Get user's reminders"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{get_service_url('reminder')}/"
            response = await client.get(url)
            response.raise_for_status()
            reminders = response.json()

            message = "📅 **Your Reminders:**\n"
            for r in reminders[:10]:
                text = r.get('text', '')
                recurrence = r.get('recurrence', 'once')
                message += f"• {text} ({recurrence})\n"

            return {
                "success": True,
                "message": message,
                "data": {"count": len(reminders)}
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error getting reminders: {str(e)}",
            "data": None
        }


async def get_spending():
    """Get spending summary"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{get_service_url('financial')}/summary"
            response = await client.get(url)
            response.raise_for_status()
            summary = response.json()

            expenses = summary.get('total_expenses', 0)
            income = summary.get('total_income', 0)
            balance = summary.get('balance', 0)

            message = f"""💰 **Financial Summary:**
• Expenses: ${abs(expenses):,.2f}
• Income: ${income:,.2f}
• Balance: ${balance:,.2f}
"""
            return {
                "success": True,
                "message": message,
                "data": summary
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error getting finances: {str(e)}",
            "data": None
        }


async def get_habits():
    """Get habits"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{get_service_url('habits')}/"
            response = await client.get(url)
            response.raise_for_status()
            habits = response.json()

            if not habits:
                return {
                    "success": True,
                    "message": "No habits tracked yet.",
                    "data": {"habits": []}
                }

            message = "📋 **Your Habits:**\n"
            for h in habits[:10]:
                name = h.get('name', 'Unknown')
                completions = h.get('completions_today', 0)
                target = h.get('target_count', 1)
                status = "✅" if completions >= target else "⏳"
                message += f"{status} {name} ({completions}/{target})\n"

            return {
                "success": True,
                "message": message,
                "data": {"habits": habits}
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error getting habits: {str(e)}",
            "data": None
        }


async def get_medications():
    """Get medications"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{get_service_url('meds')}/"
            response = await client.get(url)
            response.raise_for_status()
            meds = response.json()

            if not meds:
                return {
                    "success": True,
                    "message": "No medications tracked.",
                    "data": {"medications": []}
                }

            message = "💊 **Your Medications:**\n"
            for m in meds[:10]:
                name = m.get('name', 'Unknown')
                message += f"• {name}\n"

            return {
                "success": True,
                "message": message,
                "data": {"medications": meds}
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error getting medications: {str(e)}",
            "data": None
        }


if __name__ == "__main__":
    port = int(os.getenv("PORT", 9100))
    uvicorn.run(app, host="0.0.0.0", port=port)
