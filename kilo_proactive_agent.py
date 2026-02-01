#!/usr/bin/env python3
"""
KILO PROACTIVE AGENT - Intelligent Life Management Assistant

This agent doesn't just monitor K3s - it USES your services to help you:
- Track spending and alert on budget issues
- Remind you about medications proactively
- Ask about habits and track completion
- Check upcoming reminders and notify you
- Be your intelligent personal assistant

CAPABILITIES:
- Checks financial spending and budgets
- Monitors medication adherence
- Tracks habit completion
- Reviews upcoming reminders
- Proactively asks you about things that need attention
- Uses LLM to make intelligent decisions about what to bring up
"""

import requests
import time
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict


class KiloProactiveAgent:
    """
    Intelligent agent that uses Kilo services to help manage your life
    """

    def __init__(self,
                 service_base: str = "http://localhost",
                 llm_url: str = "http://localhost:8080",
                 model: str = "phi3-mini",
                 use_k3s_services: bool = True,
                 ai_brain_url: str = None):
        """
        Initialize Kilo Proactive Agent

        Args:
            service_base: Base URL for services (default: http://localhost for local K3s access)
            llm_url: LLM server URL for intelligence
            model: Model name for LLM
            use_k3s_services: If True, use K3s service names (requires running on K3s host)
            ai_brain_url: URL of AI Brain service for chat integration (optional)
        """
        self.service_base = service_base
        self.use_k3s_services = use_k3s_services
        self.llm_url = llm_url
        self.model = model
        self.ai_brain_url = ai_brain_url or os.getenv('AI_BRAIN_URL')
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

        # Service ports (when accessing directly)
        self.service_ports = {
            'reminder': 9002,
            'financial': 9005,
            'habits': 9000,
            'meds': 9001
        }

        # Or K3s service DNS names (when running on cluster host)
        self.service_hosts = {
            'reminder': 'kilo-reminder.kilo-guardian.svc.cluster.local',
            'financial': 'kilo-financial.kilo-guardian.svc.cluster.local',
            'habits': 'kilo-habits.kilo-guardian.svc.cluster.local',
            'meds': 'kilo-meds.kilo-guardian.svc.cluster.local'
        }

        # Track what we've already notified about (avoid spam)
        self.notified_reminders = set()
        self.notified_budgets = set()
        self.last_check_time = {}

    def _get_service_url(self, service: str) -> str:
        """Get the URL for a service"""
        # Check for environment variable first (highest priority)
        env_var = f"{service.upper()}_URL"
        env_url = os.getenv(env_var)
        if env_url:
            return env_url

        # Otherwise use configured method
        if self.use_k3s_services:
            host = self.service_hosts.get(service, f'kilo-{service}')
            port = self.service_ports.get(service, 9000)
            return f"http://{host}:{port}"
        else:
            port = self.service_ports.get(service, 9000)
            return f"{self.service_base}:{port}"

    # ==================== Chat Integration Methods ====================

    def send_to_chat(self, message: str, msg_type: str = "notification", priority: str = "normal"):
        """
        Send a notification to the chat interface

        Args:
            message: The message content
            msg_type: Type of message (reminder, budget, habit, insight, notification)
            priority: Priority level (low, normal, high, urgent)
        """
        if not self.ai_brain_url:
            # No chat integration, just print
            return False

        try:
            payload = {
                "type": msg_type,
                "content": message,
                "priority": priority,
                "metadata": {}
            }

            response = self.session.post(
                f"{self.ai_brain_url}/agent/notify",
                json=payload,
                timeout=5
            )
            response.raise_for_status()
            return True
        except Exception as e:
            # Silently fail - don't break agent if chat is down
            return False

    # ==================== Service Interaction Methods ====================

    def get_all_reminders(self) -> List[Dict]:
        """Get all reminders from reminder service"""
        try:
            url = f"{self._get_service_url('reminder')}/"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"⚠️ Error getting reminders: {e}")
            return []

    def get_financial_summary(self) -> Dict:
        """Get financial summary with spending breakdown"""
        try:
            url = f"{self._get_service_url('financial')}/summary"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"⚠️ Error getting financial summary: {e}")
            return {}

    def get_budgets(self) -> List[Dict]:
        """Get all budgets with spending status"""
        try:
            url = f"{self._get_service_url('financial')}/budgets"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"⚠️ Error getting budgets: {e}")
            return []

    def get_spending_analytics(self) -> Dict:
        """Get detailed spending analytics"""
        try:
            url = f"{self._get_service_url('financial')}/spending/analytics"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"⚠️ Error getting spending analytics: {e}")
            return {}

    def get_medications(self) -> List[Dict]:
        """Get all medications"""
        try:
            url = f"{self._get_service_url('meds')}/"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"⚠️ Error getting medications: {e}")
            return []

    def get_habits(self) -> List[Dict]:
        """Get all habits with today's completion status"""
        try:
            url = f"{self._get_service_url('habits')}/"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"⚠️ Error getting habits: {e}")
            return []

    def mark_habit_complete(self, habit_id: int) -> bool:
        """Mark a habit as completed"""
        try:
            url = f"{self._get_service_url('habits')}/complete/{habit_id}"
            response = self.session.post(url, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"⚠️ Error marking habit complete: {e}")
            return False

    # ==================== Analysis Methods ====================

    def analyze_reminders(self) -> List[str]:
        """Analyze upcoming reminders and generate notifications"""
        notifications = []
        all_reminders = self.get_all_reminders()

        now = datetime.now()

        for reminder in all_reminders:
            reminder_id = reminder.get('id')
            when_str = reminder.get('when', '')
            text = reminder.get('text', '')
            recurrence = reminder.get('recurrence', '')

            if reminder_id in self.notified_reminders:
                continue  # Already notified

            # Parse time (handle various formats)
            try:
                # Remove timezone suffix if present, we'll assume local time
                when_clean = when_str.replace('Z', '').replace('+00:00', '')

                # Try ISO format
                if 'T' in when_clean:
                    reminder_time = datetime.fromisoformat(when_clean)
                else:
                    # Try simple format like "2026-01-16T07:30"
                    reminder_time = datetime.strptime(when_clean, "%Y-%m-%dT%H:%M")

                # For recurring reminders, check if it's today
                if recurrence:
                    # If it's a daily reminder, just check the time today
                    if recurrence == 'daily':
                        reminder_today = now.replace(
                            hour=reminder_time.hour,
                            minute=reminder_time.minute,
                            second=0,
                            microsecond=0
                        )
                        time_until = reminder_today - now

                        # Notify if within next 2 hours
                        if timedelta(0) <= time_until <= timedelta(hours=2):
                            minutes = int(time_until.total_seconds() / 60)
                            notifications.append(
                                f"⏰ REMINDER in {minutes} min: {text} (daily)"
                            )
                            self.notified_reminders.add(reminder_id)
                else:
                    # One-time reminder
                    time_until = reminder_time - now
                    if timedelta(0) <= time_until <= timedelta(hours=2):
                        minutes = int(time_until.total_seconds() / 60)
                        notifications.append(
                            f"⏰ REMINDER in {minutes} min: {text}"
                        )
                        self.notified_reminders.add(reminder_id)
            except Exception as e:
                # Skip reminders we can't parse
                pass

        return notifications

    def analyze_budgets(self) -> List[str]:
        """Analyze budgets and alert on overspending"""
        notifications = []
        budgets = self.get_budgets()

        for budget in budgets:
            category = budget.get('category', 'Unknown')
            monthly_limit = budget.get('monthly_limit', 0)
            spent = budget.get('spent', 0)
            percentage = budget.get('percentage', 0)

            budget_key = f"{category}_{monthly_limit}"

            # Alert at 80%, 90%, 100%+ spending
            if percentage >= 100 and budget_key not in self.notified_budgets:
                notifications.append(
                    f"🚨 BUDGET EXCEEDED: {category} - ${spent:.2f} / ${monthly_limit:.2f} ({percentage:.0f}%)"
                )
                self.notified_budgets.add(budget_key)
            elif percentage >= 90 and budget_key not in self.notified_budgets:
                notifications.append(
                    f"⚠️ BUDGET WARNING: {category} - ${spent:.2f} / ${monthly_limit:.2f} ({percentage:.0f}%)"
                )
                self.notified_budgets.add(budget_key)
            elif percentage >= 80 and budget_key not in self.notified_budgets:
                notifications.append(
                    f"💡 BUDGET HEADS UP: {category} - ${spent:.2f} / ${monthly_limit:.2f} ({percentage:.0f}%)"
                )
                self.notified_budgets.add(budget_key)

        return notifications

    def analyze_habits(self) -> List[str]:
        """Check habits and remind about incomplete ones"""
        notifications = []
        habits = self.get_habits()

        current_hour = datetime.now().hour

        for habit in habits:
            name = habit.get('name', '')
            active = habit.get('active', True)
            completions_today = habit.get('completions_today', 0)
            target_count = habit.get('target_count', 1)

            if not active:
                continue

            # If afternoon/evening and habit not done
            if current_hour >= 14 and completions_today < target_count:
                notifications.append(
                    f"📋 HABIT REMINDER: '{name}' - {completions_today}/{target_count} done today"
                )

        return notifications

    def analyze_spending_trends(self) -> List[str]:
        """Analyze spending patterns and provide insights"""
        notifications = []
        analytics = self.get_spending_analytics()

        insights = analytics.get('insights', [])
        for insight in insights:
            notifications.append(f"💰 {insight}")

        return notifications

    # ==================== Proactive Monitoring Loop ====================

    def check_all_services(self) -> Dict[str, List[str]]:
        """
        Check all services and collect notifications
        Returns dict of notification categories
        """
        notifications = defaultdict(list)

        print("🔍 Checking all services...")

        # Check reminders
        reminder_notes = self.analyze_reminders()
        if reminder_notes:
            notifications['reminders'] = reminder_notes

        # Check budgets
        budget_notes = self.analyze_budgets()
        if budget_notes:
            notifications['budgets'] = budget_notes

        # Check habits
        habit_notes = self.analyze_habits()
        if habit_notes:
            notifications['habits'] = habit_notes

        # Check spending trends (less frequent)
        current_time = datetime.now()
        last_spending_check = self.last_check_time.get('spending')
        if not last_spending_check or (current_time - last_spending_check) > timedelta(hours=6):
            spending_notes = self.analyze_spending_trends()
            if spending_notes:
                notifications['spending'] = spending_notes
            self.last_check_time['spending'] = current_time

        return dict(notifications)

    def print_notifications(self, notifications: Dict[str, List[str]]):
        """Print notifications and send to chat"""
        if not notifications:
            print("✅ All good! Nothing needs your attention right now.\n")
            return

        print("\n" + "="*70)
        print("🔔 KILO HAS THINGS FOR YOU TO KNOW")
        print("="*70 + "\n")

        for category, notes in notifications.items():
            print(f"📌 {category.upper()}:")
            for note in notes:
                print(f"   {note}")

                # Also send to chat if integrated
                if self.ai_brain_url:
                    # Determine message type and priority
                    msg_type = category.rstrip('s')  # reminders -> reminder
                    priority = "high" if "🚨" in note else "normal"
                    self.send_to_chat(note, msg_type=msg_type, priority=priority)
            print()

        print("="*70 + "\n")

    def run_once(self):
        """Run one check cycle"""
        notifications = self.check_all_services()
        self.print_notifications(notifications)

    def run_loop(self, check_interval: int = 300):
        """
        Continuously monitor services and notify about important things

        Args:
            check_interval: How often to check (seconds). Default 5 minutes.
        """
        print(f"🚀 Kilo Proactive Agent Started")
        print(f"📡 Services: {self.service_base} (K3s: {self.use_k3s_services})")
        print(f"🧠 LLM: {self.llm_url}")
        print(f"⏱️  Check interval: {check_interval} seconds ({check_interval//60} minutes)")
        print(f"\nPress Ctrl+C to stop\n")

        try:
            while True:
                notifications = self.check_all_services()
                self.print_notifications(notifications)

                print(f"💤 Next check in {check_interval//60} minutes...")
                print("-"*70 + "\n")
                time.sleep(check_interval)

        except KeyboardInterrupt:
            print("\n\n👋 Stopping Kilo Proactive Agent...")


def main():
    """Main entry point"""
    import sys

    # Parse arguments
    mode = "loop"  # Default to continuous monitoring
    if len(sys.argv) > 1:
        mode = sys.argv[1]

    agent = KiloProactiveAgent()

    if mode == "once":
        # Run once and exit
        agent.run_once()
    elif mode == "test":
        # Test mode - check services and show data
        print("🧪 TEST MODE - Checking service connectivity\n")

        print("📅 All Reminders:")
        reminders = agent.get_all_reminders()
        for r in reminders[:5]:
            print(f"  - {r.get('text')} at {r.get('when')} (recurrence: {r.get('recurrence', 'none')})")
        print()

        print("💰 Financial Summary:")
        summary = agent.get_financial_summary()
        print(f"  Total Expenses: ${summary.get('total_expenses', 0):.2f}")
        print(f"  Total Income: ${summary.get('total_income', 0):.2f}")
        print(f"  Balance: ${summary.get('balance', 0):.2f}")
        print()

        print("📊 Budgets:")
        budgets = agent.get_budgets()
        for b in budgets:
            print(f"  - {b.get('category')}: ${b.get('spent', 0):.2f} / ${b.get('monthly_limit', 0):.2f} ({b.get('percentage', 0):.0f}%)")
        print()

        print("📋 Habits:")
        habits = agent.get_habits()
        for h in habits:
            print(f"  - {h.get('name')}: {h.get('completions_today', 0)}/{h.get('target_count', 1)} today")
        print()

    else:
        # Continuous monitoring (default)
        agent.run_loop(check_interval=300)  # Check every 5 minutes


if __name__ == "__main__":
    main()
