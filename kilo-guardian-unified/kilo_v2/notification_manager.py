"""
Notification Manager: Handles all user notifications (audio, push, WebSocket)
Supports persistent alerts that repeat until acknowledged.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("NotificationManager")


class NotificationPriority(str, Enum):
    """Notification priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationType(str, Enum):
    """Types of notifications."""

    REMINDER = "reminder"
    MEDICATION = "medication"
    HABIT = "habit"
    ALERT = "alert"
    INFO = "info"


class Notification:
    """Represents a single notification."""

    def __init__(
        self,
        id: str,
        title: str,
        message: str,
        notification_type: NotificationType,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        persistent: bool = False,
        repeat_interval: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.id = id
        self.title = title
        self.message = message
        self.type = notification_type
        self.priority = priority
        self.persistent = persistent  # Repeat until acknowledged
        self.repeat_interval = repeat_interval  # Seconds between repeats
        self.metadata = metadata or {}
        self.created_at = datetime.now()
        self.last_shown_at: Optional[datetime] = None
        self.acknowledged = False
        self.show_count = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert notification to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "type": self.type.value,
            "priority": self.priority.value,
            "persistent": self.persistent,
            "repeat_interval": self.repeat_interval,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "last_shown_at": (
                self.last_shown_at.isoformat() if self.last_shown_at else None
            ),
            "acknowledged": self.acknowledged,
            "show_count": self.show_count,
        }

    def should_show_again(self) -> bool:
        """Check if notification should be shown again."""
        if self.acknowledged:
            return False

        if not self.persistent:
            return self.show_count == 0

        if self.last_shown_at is None:
            return True

        # Check if enough time has passed since last shown
        if self.repeat_interval:
            elapsed = (datetime.now() - self.last_shown_at).total_seconds()
            return elapsed >= self.repeat_interval

        return False


class NotificationManager:
    """
    Manages all notifications for Kilo Guardian.

    Features:
    - Persistent alerts that repeat until acknowledged
    - Multiple notification channels (WebSocket, audio, push)
    - Priority-based notification handling
    - Configurable repeat intervals
    - Notification history and analytics
    """

    def __init__(self):
        self.active_notifications: Dict[str, Notification] = {}
        self.notification_history: List[Notification] = []
        self.websocket_connections: Set[Any] = (
            set()
        )  # WebSocket connections for real-time push

        # Configuration
        self.config = {
            "audio_enabled": os.getenv("NOTIFICATIONS_AUDIO_ENABLED", "true").lower()
            == "true",
            "push_enabled": os.getenv("NOTIFICATIONS_PUSH_ENABLED", "true").lower()
            == "true",
            "websocket_enabled": os.getenv(
                "NOTIFICATIONS_WEBSOCKET_ENABLED", "true"
            ).lower()
            == "true",
            "default_repeat_interval": int(
                os.getenv("NOTIFICATION_REPEAT_INTERVAL", "300")
            ),  # 5 minutes
            "max_history_size": int(os.getenv("NOTIFICATION_MAX_HISTORY", "1000")),
        }

        # Background task for persistent notifications
        self.notification_task: Optional[asyncio.Task] = None
        self._running = False

        logger.info("NotificationManager initialized")
        logger.info(
            f"Audio: {self.config['audio_enabled']}, "
            f"Push: {self.config['push_enabled']}, "
            f"WebSocket: {self.config['websocket_enabled']}"
        )

    async def start(self):
        """Start the notification manager background task."""
        if self._running:
            logger.warning("NotificationManager already running")
            return

        self._running = True
        self.notification_task = asyncio.create_task(self._notification_loop())
        logger.info("NotificationManager started")

    async def stop(self):
        """Stop the notification manager."""
        self._running = False
        if self.notification_task:
            self.notification_task.cancel()
            try:
                await self.notification_task
            except asyncio.CancelledError:
                pass
        logger.info("NotificationManager stopped")

    async def _notification_loop(self):
        """Background task to handle persistent notifications."""
        while self._running:
            try:
                await self._check_persistent_notifications()
                await asyncio.sleep(10)  # Check every 10 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in notification loop: {e}")
                await asyncio.sleep(10)

    async def _check_persistent_notifications(self):
        """Check for notifications that need to be shown again."""
        for notification in list(self.active_notifications.values()):
            if notification.should_show_again():
                await self._send_notification(notification)

    async def send_notification(
        self,
        id: str,
        title: str,
        message: str,
        notification_type: NotificationType,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        persistent: bool = False,
        repeat_interval: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Notification:
        """
        Send a new notification.

        Args:
            id: Unique notification ID
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            priority: Priority level
            persistent: Whether to repeat until acknowledged
            repeat_interval: Seconds between repeats (uses default if None)
            metadata: Additional metadata

        Returns:
            Notification object
        """
        # Use default repeat interval for persistent notifications if not specified
        if persistent and repeat_interval is None:
            repeat_interval = self.config["default_repeat_interval"]

        notification = Notification(
            id=id,
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
            persistent=persistent,
            repeat_interval=repeat_interval,
            metadata=metadata,
        )

        # Store notification
        self.active_notifications[id] = notification
        self._add_to_history(notification)

        # Send via all enabled channels
        await self._send_notification(notification)

        logger.info(
            f"Sent notification: {id} - {title} (priority: {priority}, persistent: {persistent})"
        )
        return notification

    async def _send_notification(self, notification: Notification):
        """Send notification via all enabled channels."""
        notification.last_shown_at = datetime.now()
        notification.show_count += 1

        # Send via WebSocket to connected clients
        if self.config["websocket_enabled"]:
            await self._send_websocket(notification)

        # Log for audio/push (actual implementation would trigger sounds/system notifications)
        if self.config["audio_enabled"]:
            self._log_audio_notification(notification)

        if self.config["push_enabled"]:
            self._log_push_notification(notification)

    async def _send_websocket(self, notification: Notification):
        """Send notification to all connected WebSocket clients."""
        if not self.websocket_connections:
            return

        message = json.dumps({"event": "notification", "data": notification.to_dict()})

        # Send to all connected clients
        disconnected = set()
        for ws in self.websocket_connections:
            try:
                await ws.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send WebSocket notification: {e}")
                disconnected.add(ws)

        # Remove disconnected clients
        self.websocket_connections -= disconnected

    def _log_audio_notification(self, notification: Notification):
        """Log audio notification (placeholder for actual audio playback)."""
        sound_file = self._get_sound_for_priority(notification.priority)
        logger.info(f"🔊 AUDIO: {notification.title} (sound: {sound_file})")
        # TODO: Implement actual audio playback
        # Example: pygame.mixer.Sound(sound_file).play()

    def _log_push_notification(self, notification: Notification):
        """Log push notification (placeholder for system notifications)."""
        logger.info(f"📲 PUSH: {notification.title} - {notification.message}")
        # TODO: Implement system notifications
        # Example: plyer.notification.notify(title=..., message=...)

    def _get_sound_for_priority(self, priority: NotificationPriority) -> str:
        """Get sound file for notification priority."""
        sound_map = {
            NotificationPriority.LOW: "sounds/notification_low.wav",
            NotificationPriority.NORMAL: "sounds/notification_normal.wav",
            NotificationPriority.HIGH: "sounds/notification_high.wav",
            NotificationPriority.URGENT: "sounds/notification_urgent.wav",
        }
        return sound_map.get(priority, "sounds/notification_normal.wav")

    def acknowledge(self, notification_id: str) -> bool:
        """
        Acknowledge a notification (stops it from repeating).

        Args:
            notification_id: ID of notification to acknowledge

        Returns:
            True if acknowledged, False if not found
        """
        notification = self.active_notifications.get(notification_id)
        if notification:
            notification.acknowledged = True
            logger.info(f"Acknowledged notification: {notification_id}")
            return True
        return False

    def dismiss(self, notification_id: str) -> bool:
        """
        Dismiss and remove a notification.

        Args:
            notification_id: ID of notification to dismiss

        Returns:
            True if dismissed, False if not found
        """
        if notification_id in self.active_notifications:
            del self.active_notifications[notification_id]
            logger.info(f"Dismissed notification: {notification_id}")
            return True
        return False

    def get_active_notifications(self) -> List[Dict[str, Any]]:
        """Get all active notifications."""
        return [
            n.to_dict()
            for n in self.active_notifications.values()
            if not n.acknowledged
        ]

    def get_all_notifications(self) -> List[Dict[str, Any]]:
        """Get all notifications including acknowledged ones."""
        return [n.to_dict() for n in self.active_notifications.values()]

    def get_notification_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get notification history."""
        return [n.to_dict() for n in self.notification_history[-limit:]]

    def _add_to_history(self, notification: Notification):
        """Add notification to history."""
        self.notification_history.append(notification)

        # Trim history if too large
        if len(self.notification_history) > self.config["max_history_size"]:
            self.notification_history = self.notification_history[
                -self.config["max_history_size"] :
            ]

    def register_websocket(self, websocket: Any):
        """Register a WebSocket connection for notifications."""
        self.websocket_connections.add(websocket)
        logger.info(
            f"Registered WebSocket connection (total: {len(self.websocket_connections)})"
        )

    def unregister_websocket(self, websocket: Any):
        """Unregister a WebSocket connection."""
        self.websocket_connections.discard(websocket)
        logger.info(
            f"Unregistered WebSocket connection (total: {len(self.websocket_connections)})"
        )

    def update_config(self, config: Dict[str, Any]):
        """Update notification configuration."""
        self.config.update(config)
        logger.info(f"Updated notification config: {config}")

    def get_config(self) -> Dict[str, Any]:
        """Get current notification configuration."""
        return self.config.copy()

    def get_stats(self) -> Dict[str, Any]:
        """Get notification statistics."""
        return {
            "active_notifications": len(self.active_notifications),
            "active_unacknowledged": len(
                [n for n in self.active_notifications.values() if not n.acknowledged]
            ),
            "total_history": len(self.notification_history),
            "websocket_connections": len(self.websocket_connections),
            "config": self.config,
        }


# Global instance
_notification_manager: Optional[NotificationManager] = None


def get_notification_manager() -> NotificationManager:
    """Get the global notification manager instance."""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager
