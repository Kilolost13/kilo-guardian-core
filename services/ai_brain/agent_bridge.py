"""
Agent Bridge - Connects Proactive Agent to Chat Interface

This module allows the proactive agent to:
- Post notifications to the chat interface
- Receive commands from users through chat
- Query services on behalf of the user
- Maintain conversation state
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import asyncio
from collections import deque
import httpx


# ==================== Data Models ====================

class AgentMessage(BaseModel):
    """Message from proactive agent to chat"""
    type: str  # "reminder", "budget", "habit", "insight", "notification"
    content: str
    priority: str = "normal"  # "low", "normal", "high", "urgent"
    timestamp: datetime = None
    metadata: Dict[str, Any] = {}

    def __init__(self, **data):
        if 'timestamp' not in data or data['timestamp'] is None:
            data['timestamp'] = datetime.now()
        super().__init__(**data)


class AgentCommand(BaseModel):
    """Command from user to agent via chat"""
    command: str
    params: Dict[str, Any] = {}
    user: str = "user"


class AgentResponse(BaseModel):
    """Response from agent to user"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


# ==================== Agent Message Queue ====================

class AgentMessageQueue:
    """
    Queue for agent messages waiting to be displayed in chat
    Thread-safe, in-memory queue with TTL
    """

    def __init__(self, max_size: int = 100, ttl_hours: int = 24):
        self.messages = deque(maxlen=max_size)
        self.ttl = timedelta(hours=ttl_hours)
        self._lock = asyncio.Lock()

    async def add_message(self, message: AgentMessage):
        """Add a message from the agent"""
        async with self._lock:
            self.messages.append(message)
            # Clean up old messages
            await self._cleanup()

    async def get_pending_messages(self, since: datetime = None) -> List[AgentMessage]:
        """Get all pending messages since a given time"""
        async with self._lock:
            if since is None:
                since = datetime.now() - timedelta(minutes=5)

            return [
                msg for msg in self.messages
                if msg.timestamp >= since
            ]

    async def get_recent_messages(self, count: int = 10) -> List[AgentMessage]:
        """Get the N most recent messages"""
        async with self._lock:
            messages = list(self.messages)
            return messages[-count:] if len(messages) > count else messages

    async def _cleanup(self):
        """Remove expired messages"""
        cutoff = datetime.now() - self.ttl
        # Keep only messages newer than TTL
        expired_count = sum(1 for msg in self.messages if msg.timestamp < cutoff)
        for _ in range(expired_count):
            if self.messages and self.messages[0].timestamp < cutoff:
                self.messages.popleft()

    async def clear(self):
        """Clear all messages"""
        async with self._lock:
            self.messages.clear()


# ==================== Agent Command Handler ====================

class AgentCommandHandler:
    """
    Handles commands sent from chat to the proactive agent
    Routes commands to appropriate service endpoints
    """

    def __init__(self, service_base_url: str = "http://localhost"):
        self.service_base_url = service_base_url
        self.service_ports = {
            'reminder': 9002,
            'financial': 9005,
            'habits': 9003,
            'meds': 9001
        }

    def _get_service_url(self, service: str) -> str:
        """Get URL for a service"""
        port = self.service_ports.get(service, 9000)
        return f"{self.service_base_url}:{port}"

    async def handle_command(self, command: AgentCommand) -> AgentResponse:
        """
        Route command to appropriate handler
        """
        cmd = command.command.lower().strip()

        # Parse intent
        if any(word in cmd for word in ["remind", "reminder", "reminders"]):
            return await self._handle_reminder_command(cmd, command.params)
        elif any(word in cmd for word in ["spend", "spending", "budget", "money", "financial"]):
            return await self._handle_financial_command(cmd, command.params)
        elif any(word in cmd for word in ["habit", "habits", "done", "complete"]):
            return await self._handle_habit_command(cmd, command.params)
        elif any(word in cmd for word in ["med", "meds", "medication", "medications"]):
            return await self._handle_med_command(cmd, command.params)
        else:
            return AgentResponse(
                success=False,
                message="I didn't understand that command. Try asking about reminders, spending, habits, or medications."
            )

    async def _handle_reminder_command(self, cmd: str, params: Dict) -> AgentResponse:
        """Handle reminder-related commands"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Get all reminders
                url = f"{self._get_service_url('reminder')}/"
                response = await client.get(url)
                response.raise_for_status()
                reminders = response.json()

                # Filter for upcoming today
                now = datetime.now()
                upcoming = []
                for r in reminders:
                    # Parse and check if upcoming
                    when = r.get('when', '')
                    text = r.get('text', '')
                    recurrence = r.get('recurrence', '')
                    if recurrence == 'daily':
                        upcoming.append(f"• {text} (daily)")

                if upcoming:
                    message = "📅 **Your Reminders:**\n" + "\n".join(upcoming[:10])
                else:
                    message = "No upcoming reminders found."

                return AgentResponse(
                    success=True,
                    message=message,
                    data={"count": len(upcoming)}
                )

        except Exception as e:
            return AgentResponse(
                success=False,
                message=f"Error getting reminders: {str(e)}"
            )

    async def _handle_financial_command(self, cmd: str, params: Dict) -> AgentResponse:
        """Handle financial/spending commands"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Get summary
                url = f"{self._get_service_url('financial')}/summary"
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

                # Also get budget status
                budget_url = f"{self._get_service_url('financial')}/budgets"
                budget_response = await client.get(budget_url)
                if budget_response.status_code == 200:
                    budgets = budget_response.json()
                    over_budget = [b for b in budgets if b.get('percentage', 0) >= 100]
                    warning = [b for b in budgets if 90 <= b.get('percentage', 0) < 100]

                    if over_budget:
                        message += f"\n🚨 **Over Budget:** {len(over_budget)} categories"
                    if warning:
                        message += f"\n⚠️ **Warning:** {len(warning)} categories near limit"

                return AgentResponse(
                    success=True,
                    message=message,
                    data=summary
                )

        except Exception as e:
            return AgentResponse(
                success=False,
                message=f"Error getting financial data: {str(e)}"
            )

    async def _handle_habit_command(self, cmd: str, params: Dict) -> AgentResponse:
        """Handle habit-related commands"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Check if marking complete
                if "done" in cmd or "complete" in cmd:
                    habit_id = params.get('habit_id')
                    if not habit_id:
                        return AgentResponse(
                            success=False,
                            message="Which habit? Try: 'mark habit 1 done'"
                        )

                    url = f"{self._get_service_url('habits')}/complete/{habit_id}"
                    response = await client.post(url)
                    response.raise_for_status()

                    return AgentResponse(
                        success=True,
                        message=f"✅ Habit marked complete!"
                    )

                # Otherwise list habits
                url = f"{self._get_service_url('habits')}/"
                response = await client.get(url)
                response.raise_for_status()
                habits = response.json()

                if not habits:
                    return AgentResponse(
                        success=True,
                        message="No habits tracked yet."
                    )

                message = "📋 **Your Habits:**\n"
                for h in habits[:10]:
                    name = h.get('name', 'Unknown')
                    completions = h.get('completions_today', 0)
                    target = h.get('target_count', 1)
                    status = "✅" if completions >= target else "⏳"
                    message += f"{status} {name} ({completions}/{target})\n"

                return AgentResponse(
                    success=True,
                    message=message,
                    data={"habits": habits}
                )

        except Exception as e:
            return AgentResponse(
                success=False,
                message=f"Error with habits: {str(e)}"
            )

    async def _handle_med_command(self, cmd: str, params: Dict) -> AgentResponse:
        """Handle medication commands"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"{self._get_service_url('meds')}/"
                response = await client.get(url)
                response.raise_for_status()
                meds = response.json()

                if not meds:
                    return AgentResponse(
                        success=True,
                        message="No medications tracked."
                    )

                message = "💊 **Your Medications:**\n"
                for m in meds[:10]:
                    name = m.get('name', 'Unknown')
                    schedule = m.get('schedule', 'As needed')
                    message += f"• {name} - {schedule}\n"

                return AgentResponse(
                    success=True,
                    message=message,
                    data={"medications": meds}
                )

        except Exception as e:
            return AgentResponse(
                success=False,
                message=f"Error getting medications: {str(e)}"
            )


# ==================== Global Instances ====================

# Shared message queue
agent_queue = AgentMessageQueue()

# Command handler
agent_handler = AgentCommandHandler()
