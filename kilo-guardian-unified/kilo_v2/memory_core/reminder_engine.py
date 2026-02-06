"""
Reminder Engine: Scheduling, nudging, habit tracking with APScheduler
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

logger = logging.getLogger("ReminderEngine")

# Import notification manager (optional dependency)
try:
    from kilo_v2.notification_manager import (
        NotificationPriority,
        NotificationType,
        get_notification_manager,
    )

    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    NOTIFICATIONS_AVAILABLE = False
    logger.warning("NotificationManager not available")


class ReminderEngine:
    """
    Reminder engine for scheduling and managing reminders, medications, and habits.
    Uses APScheduler for background scheduling.
    """

    def __init__(self, db):
        self.db = db
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()

        # Pending alerts (for frontend to poll)
        self.pending_alerts: List[Dict[str, Any]] = []

        logger.info("ReminderEngine initialized with APScheduler")

        # Schedule periodic check for due reminders
        self.scheduler.add_job(
            self._check_due_reminders,
            "interval",
            minutes=1,
            id="check_reminders",
            replace_existing=True,
        )

        # Schedule periodic check for medications
        self.scheduler.add_job(
            self._check_medications,
            "interval",
            minutes=5,
            id="check_medications",
            replace_existing=True,
        )

        # Load existing reminders from database and schedule them
        self._load_existing_reminders()

    def _load_existing_reminders(self):
        """Load existing unacknowledged reminders from database and schedule them."""
        try:
            reminders = self.db.get_reminders(include_acknowledged=False)
            for reminder in reminders:
                scheduled_time = datetime.fromisoformat(reminder["scheduled_time"])

                # Only schedule if in the future
                if scheduled_time > datetime.now():
                    self._schedule_reminder_job(reminder)

            logger.info(f"Loaded and scheduled {len(reminders)} existing reminders")
        except Exception as e:
            logger.error(f"Failed to load existing reminders: {e}")

    def schedule_reminder(self, reminder_id: int) -> bool:
        """
        Schedule a reminder for future delivery.

        Args:
            reminder_id: Database ID of the reminder

        Returns:
            True if scheduled successfully, False otherwise
        """
        try:
            reminder = self.db.get_reminder(reminder_id)
            if not reminder:
                logger.error(f"Reminder {reminder_id} not found in database")
                return False

            self._schedule_reminder_job(reminder)
            return True
        except Exception as e:
            logger.error(f"Failed to schedule reminder {reminder_id}: {e}")
            return False

    def _schedule_reminder_job(self, reminder: Dict[str, Any]):
        """Internal method to add a reminder job to the scheduler."""
        reminder_id = reminder["id"]
        scheduled_time = datetime.fromisoformat(reminder["scheduled_time"])

        # Handle snoozing
        if reminder.get("snoozed_until"):
            snoozed_until = datetime.fromisoformat(reminder["snoozed_until"])
            if snoozed_until > scheduled_time:
                scheduled_time = snoozed_until

        # Skip if already past
        if scheduled_time <= datetime.now():
            logger.warning(
                f"Reminder {reminder_id} scheduled time is in the past, skipping"
            )
            return

        job_id = f"reminder_{reminder_id}"

        # Check for recurring pattern
        if reminder.get("recurring"):
            trigger = self._parse_recurring_pattern(reminder["recurring"])
            if trigger:
                self.scheduler.add_job(
                    self._fire_reminder,
                    trigger,
                    args=[reminder_id],
                    id=job_id,
                    replace_existing=True,
                )
                logger.info(
                    f"Scheduled recurring reminder {reminder_id}: {reminder['recurring']}"
                )
            else:
                logger.error(f"Invalid recurring pattern: {reminder['recurring']}")
        else:
            # One-time reminder
            self.scheduler.add_job(
                self._fire_reminder,
                DateTrigger(run_date=scheduled_time),
                args=[reminder_id],
                id=job_id,
                replace_existing=True,
            )
            logger.info(
                f"Scheduled one-time reminder {reminder_id} for {scheduled_time}"
            )

    def _parse_recurring_pattern(self, pattern: str) -> Optional[CronTrigger]:
        """
        Parse recurring pattern into CronTrigger.

        Supported formats:
        - "daily": Every day at the scheduled time
        - "weekly": Every week on the same day
        - "hourly": Every hour
        - "every 3 hours": Every N hours
        - "weekdays": Monday-Friday
        - "Mon,Wed,Fri": Specific days of week
        """
        try:
            pattern = pattern.lower().strip()

            if pattern == "daily":
                return CronTrigger(hour="*", minute="0")
            elif pattern == "hourly":
                return CronTrigger(minute="0")
            elif pattern == "weekly":
                return CronTrigger(day_of_week="*", hour="9", minute="0")
            elif pattern == "weekdays":
                return CronTrigger(day_of_week="mon-fri", hour="9", minute="0")
            elif pattern.startswith("every ") and "hour" in pattern:
                # Parse "every N hours"
                parts = pattern.split()
                if len(parts) >= 2 and parts[1].isdigit():
                    hours = int(parts[1])
                    return CronTrigger(hour=f"*/{hours}")
            elif "," in pattern:
                # Days of week: "mon,wed,fri"
                return CronTrigger(day_of_week=pattern, hour="9", minute="0")

            # Default: parse as cron expression
            return CronTrigger.from_crontab(pattern)
        except Exception as e:
            logger.error(f"Failed to parse recurring pattern '{pattern}': {e}")
            return None

    def _fire_reminder(self, reminder_id: int):
        """Fire a reminder alert (called by scheduler)."""
        try:
            reminder = self.db.get_reminder(reminder_id)
            if not reminder:
                logger.warning(f"Reminder {reminder_id} not found when firing")
                return

            if reminder["acknowledged"]:
                logger.info(f"Reminder {reminder_id} already acknowledged, skipping")
                return

            # Add to pending alerts queue
            alert = {
                "id": reminder_id,
                "type": "reminder",
                "text": reminder["text"],
                "priority": reminder.get("priority", "normal"),
                "category": reminder.get("category"),
                "scheduled_time": reminder["scheduled_time"],
                "timestamp": datetime.now().isoformat(),
            }

            self.pending_alerts.append(alert)
            logger.info(f"ALERT: Reminder {reminder_id} - {reminder['text']}")

            # Send notification via NotificationManager
            if NOTIFICATIONS_AVAILABLE:
                try:
                    notification_manager = get_notification_manager()
                    priority_map = {
                        "low": NotificationPriority.LOW,
                        "normal": NotificationPriority.NORMAL,
                        "high": NotificationPriority.HIGH,
                        "urgent": NotificationPriority.URGENT,
                    }
                    priority = priority_map.get(
                        reminder.get("priority", "normal"), NotificationPriority.NORMAL
                    )

                    # Create event loop if not exists
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                    # Send notification (persistent for high/urgent priority)
                    loop.create_task(
                        notification_manager.send_notification(
                            id=f"reminder_{reminder_id}",
                            title=f"Reminder: {reminder.get('category', 'General')}",
                            message=reminder["text"],
                            notification_type=NotificationType.REMINDER,
                            priority=priority,
                            persistent=(
                                priority
                                in [
                                    NotificationPriority.HIGH,
                                    NotificationPriority.URGENT,
                                ]
                            ),
                            metadata={
                                "reminder_id": reminder_id,
                                "category": reminder.get("category"),
                            },
                        )
                    )
                    logger.debug(f"Sent notification for reminder {reminder_id}")
                except Exception as e:
                    logger.warning(
                        f"Failed to send notification for reminder {reminder_id}: {e}"
                    )

        except Exception as e:
            logger.error(f"Failed to fire reminder {reminder_id}: {e}")

    def _check_due_reminders(self):
        """Periodic check for reminders that are due but not yet fired."""
        try:
            now = datetime.now()
            reminders = self.db.get_reminders(include_acknowledged=False)

            for reminder in reminders:
                scheduled_time = datetime.fromisoformat(reminder["scheduled_time"])

                # Check if reminder is overdue and not snoozed
                if scheduled_time <= now:
                    snoozed_until = reminder.get("snoozed_until")
                    if snoozed_until:
                        snoozed_time = datetime.fromisoformat(snoozed_until)
                        if snoozed_time > now:
                            continue  # Still snoozed

                    # Fire the reminder if it hasn't been alerted yet
                    if not self._is_already_alerted(reminder["id"]):
                        self._fire_reminder(reminder["id"])
        except Exception as e:
            logger.error(f"Error checking due reminders: {e}")

    def _check_medications(self):
        """Periodic check for medication schedules."""
        try:
            medications = self.db.get_medications(active_only=True)
            now = datetime.now()

            for med in medications:
                # Parse medication times (e.g., "08:00,14:00,20:00")
                times_str = med["times"]
                times = [t.strip() for t in times_str.split(",")]

                for time_str in times:
                    # Check if this medication time is due
                    try:
                        med_hour, med_minute = map(int, time_str.split(":"))
                        if now.hour == med_hour and now.minute == med_minute:
                            self._fire_medication_reminder(med)
                    except ValueError:
                        logger.error(
                            f"Invalid time format for medication {med['id']}: {time_str}"
                        )

        except Exception as e:
            logger.error(f"Error checking medications: {e}")

    def _fire_medication_reminder(self, medication: Dict[str, Any]):
        """Fire a medication reminder alert."""
        try:
            med_id = medication["id"]

            # Check if already reminded today
            if self._is_medication_reminded_today(med_id):
                return

            alert = {
                "id": f"med_{med_id}",
                "type": "medication",
                "name": medication["name"],
                "dosage": medication["dosage"],
                "text": f"Take {medication['name']} ({medication['dosage']})",
                "priority": "high",
                "timestamp": datetime.now().isoformat(),
            }

            self.pending_alerts.append(alert)
            logger.info(f"ALERT: Medication reminder - {medication['name']}")

            # Send notification via NotificationManager (medications are always high priority)
            if NOTIFICATIONS_AVAILABLE:
                try:
                    notification_manager = get_notification_manager()

                    # Create event loop if not exists
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                    # Medication reminders are always persistent and high priority
                    loop.create_task(
                        notification_manager.send_notification(
                            id=f"med_{med_id}",
                            title="💊 Medication Reminder",
                            message=f"Take {medication['name']} ({medication['dosage']})",
                            notification_type=NotificationType.MEDICATION,
                            priority=NotificationPriority.HIGH,
                            persistent=True,  # Always persistent for medications
                            metadata={
                                "medication_id": med_id,
                                "dosage": medication["dosage"],
                            },
                        )
                    )
                    logger.debug(f"Sent notification for medication {med_id}")
                except Exception as e:
                    logger.warning(
                        f"Failed to send notification for medication {med_id}: {e}"
                    )

        except Exception as e:
            logger.error(f"Failed to fire medication reminder: {e}")

    def _is_already_alerted(self, reminder_id: int) -> bool:
        """Check if reminder is already in pending alerts."""
        return any(alert["id"] == reminder_id for alert in self.pending_alerts)

    def _is_medication_reminded_today(self, med_id: int) -> bool:
        """Check if medication reminder already sent today."""
        today = datetime.now().date()
        return any(
            alert.get("id") == f"med_{med_id}"
            and datetime.fromisoformat(alert["timestamp"]).date() == today
            for alert in self.pending_alerts
        )

    def get_pending_alerts(self) -> List[Dict[str, Any]]:
        """Get all pending alerts for frontend to display."""
        return self.pending_alerts.copy()

    def clear_alert(self, alert_id: Any):
        """Remove an alert from the pending queue."""
        self.pending_alerts = [a for a in self.pending_alerts if a["id"] != alert_id]
        logger.info(f"Cleared alert {alert_id}")

    def snooze_reminder(self, reminder_id: int, minutes: int = 10) -> bool:
        """
        Snooze a reminder for a specified number of minutes.

        Args:
            reminder_id: Database ID of the reminder
            minutes: Number of minutes to snooze (default: 10)

        Returns:
            True if snoozed successfully
        """
        try:
            snooze_until = (datetime.now() + timedelta(minutes=minutes)).isoformat()
            success = self.db.snooze_reminder(reminder_id, snooze_until)

            if success:
                # Remove from pending alerts
                self.clear_alert(reminder_id)

                # Reschedule the reminder
                self.schedule_reminder(reminder_id)

                logger.info(f"Snoozed reminder {reminder_id} for {minutes} minutes")

            return success
        except Exception as e:
            logger.error(f"Failed to snooze reminder {reminder_id}: {e}")
            return False

    def acknowledge_reminder(self, reminder_id: int) -> bool:
        """
        Acknowledge a reminder (mark as completed).

        Args:
            reminder_id: Database ID of the reminder

        Returns:
            True if acknowledged successfully
        """
        try:
            success = self.db.acknowledge_reminder(reminder_id)

            if success:
                # Remove from pending alerts
                self.clear_alert(reminder_id)

                # Remove scheduled job if exists
                job_id = f"reminder_{reminder_id}"
                try:
                    self.scheduler.remove_job(job_id)
                except Exception:
                    pass  # Job may not exist

                logger.info(f"Acknowledged reminder {reminder_id}")

            return success
        except Exception as e:
            logger.error(f"Failed to acknowledge reminder {reminder_id}: {e}")
            return False

    def nudge(self) -> List[Dict[str, Any]]:
        """
        Get all pending items that need user attention (reminders, medications, habits).

        Returns:
            List of items needing attention
        """
        nudge_items = []
        now = datetime.now()

        try:
            # Overdue reminders
            reminders = self.db.get_reminders(include_acknowledged=False)
            for reminder in reminders:
                scheduled_time = datetime.fromisoformat(reminder["scheduled_time"])
                if scheduled_time <= now:
                    nudge_items.append(
                        {
                            "type": "reminder",
                            "id": reminder["id"],
                            "text": reminder["text"],
                            "overdue_by": (now - scheduled_time).total_seconds()
                            / 60,  # minutes
                        }
                    )

            # Habits due today
            habits = self.db.get_habits(active_only=True)
            for habit in habits:
                last_completed = habit.get("last_completed")
                if last_completed:
                    last_time = datetime.fromisoformat(last_completed)
                    hours_since = (now - last_time).total_seconds() / 3600

                    # Check if habit is due based on frequency
                    if self._is_habit_due(habit, hours_since):
                        nudge_items.append(
                            {
                                "type": "habit",
                                "id": habit["id"],
                                "name": habit["name"],
                                "hours_since": hours_since,
                            }
                        )

            logger.info(f"Nudge: {len(nudge_items)} items need attention")
            return nudge_items

        except Exception as e:
            logger.error(f"Error generating nudge items: {e}")
            return []

    def _is_habit_due(self, habit: Dict[str, Any], hours_since_last: float) -> bool:
        """Check if a habit is due based on target frequency."""
        frequency = habit["target_frequency"].lower()

        if frequency == "daily":
            return hours_since_last >= 24
        elif frequency == "twice daily":
            return hours_since_last >= 12
        elif frequency == "weekly":
            return hours_since_last >= 168  # 7 days
        elif frequency == "hourly":
            return hours_since_last >= 1

        # Default: daily
        return hours_since_last >= 24

    def track_habit(self, habit_id: int) -> bool:
        """
        Mark a habit as completed for today.

        Args:
            habit_id: Database ID of the habit

        Returns:
            True if logged successfully
        """
        try:
            self.db.log_habit_completion(habit_id)
            logger.info(f"Logged habit completion for habit {habit_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to track habit {habit_id}: {e}")
            return False

    def shutdown(self):
        """Shutdown the scheduler gracefully."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("ReminderEngine scheduler shut down")
