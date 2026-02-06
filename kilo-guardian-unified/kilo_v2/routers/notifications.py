"""
Notification API Router
Endpoints for managing notifications, WebSocket connections, and notification preferences.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from kilo_v2.notification_manager import get_notification_manager

router = APIRouter()
logger = logging.getLogger("NotificationsRouter")


# ===== Request/Response Models =====


class NotificationCreate(BaseModel):
    """Model for creating a notification."""

    id: str
    title: str
    message: str
    notification_type: str  # reminder, medication, habit, alert, info
    priority: str = "normal"  # low, normal, high, urgent
    persistent: bool = False
    repeat_interval: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class NotificationConfigUpdate(BaseModel):
    """Model for updating notification configuration."""

    audio_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    websocket_enabled: Optional[bool] = None
    default_repeat_interval: Optional[int] = None


# ===== Notification Endpoints =====


@router.get("/notifications", response_model=List[dict])
def get_active_notifications():
    """Get all active (unacknowledged) notifications."""
    try:
        notification_manager = get_notification_manager()
        return notification_manager.get_active_notifications()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notifications/all", response_model=List[dict])
def get_all_notifications():
    """Get all notifications including acknowledged ones."""
    try:
        notification_manager = get_notification_manager()
        return notification_manager.get_all_notifications()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notifications/history", response_model=List[dict])
def get_notification_history(limit: int = Query(100, ge=1, le=1000)):
    """Get notification history."""
    try:
        notification_manager = get_notification_manager()
        return notification_manager.get_notification_history(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notifications", response_model=dict)
async def create_notification(notification: NotificationCreate):
    """
    Create and send a new notification.

    This endpoint allows manual creation of notifications for testing
    or external integrations.
    """
    try:
        notification_manager = get_notification_manager()

        # Convert string types to enums
        from kilo_v2.notification_manager import NotificationPriority, NotificationType

        type_map = {
            "reminder": NotificationType.REMINDER,
            "medication": NotificationType.MEDICATION,
            "habit": NotificationType.HABIT,
            "alert": NotificationType.ALERT,
            "info": NotificationType.INFO,
        }

        priority_map = {
            "low": NotificationPriority.LOW,
            "normal": NotificationPriority.NORMAL,
            "high": NotificationPriority.HIGH,
            "urgent": NotificationPriority.URGENT,
        }

        notification_type = type_map.get(
            notification.notification_type.lower(), NotificationType.INFO
        )
        priority = priority_map.get(
            notification.priority.lower(), NotificationPriority.NORMAL
        )

        result = await notification_manager.send_notification(
            id=notification.id,
            title=notification.title,
            message=notification.message,
            notification_type=notification_type,
            priority=priority,
            persistent=notification.persistent,
            repeat_interval=notification.repeat_interval,
            metadata=notification.metadata,
        )

        return {"status": "ok", "notification_id": notification.id, "sent": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notifications/{notification_id}/acknowledge", response_model=dict)
def acknowledge_notification(notification_id: str):
    """Acknowledge a notification (stops it from repeating)."""
    try:
        notification_manager = get_notification_manager()
        success = notification_manager.acknowledge(notification_id)
        if not success:
            raise HTTPException(status_code=404, detail="Notification not found")
        return {
            "status": "ok",
            "notification_id": notification_id,
            "acknowledged": True,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notifications/{notification_id}/dismiss", response_model=dict)
def dismiss_notification(notification_id: str):
    """Dismiss and remove a notification."""
    try:
        notification_manager = get_notification_manager()
        success = notification_manager.dismiss(notification_id)
        if not success:
            raise HTTPException(status_code=404, detail="Notification not found")
        return {"status": "ok", "notification_id": notification_id, "dismissed": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Configuration Endpoints =====


@router.get("/notifications/config", response_model=dict)
def get_notification_config():
    """Get current notification configuration."""
    try:
        notification_manager = get_notification_manager()
        return notification_manager.get_config()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notifications/config", response_model=dict)
def update_notification_config(config: NotificationConfigUpdate):
    """Update notification configuration."""
    try:
        notification_manager = get_notification_manager()

        # Build config dict from non-None values
        config_updates = {}
        if config.audio_enabled is not None:
            config_updates["audio_enabled"] = config.audio_enabled
        if config.push_enabled is not None:
            config_updates["push_enabled"] = config.push_enabled
        if config.websocket_enabled is not None:
            config_updates["websocket_enabled"] = config.websocket_enabled
        if config.default_repeat_interval is not None:
            config_updates["default_repeat_interval"] = config.default_repeat_interval

        notification_manager.update_config(config_updates)

        return {"status": "ok", "config": notification_manager.get_config()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Statistics Endpoint =====


@router.get("/notifications/stats", response_model=dict)
def get_notification_stats():
    """Get notification system statistics."""
    try:
        notification_manager = get_notification_manager()
        return notification_manager.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== WebSocket Endpoint =====


@router.websocket("/notifications/ws")
async def websocket_notifications(websocket: WebSocket):
    """
    WebSocket endpoint for real-time notifications.

    Clients connect to this endpoint to receive notifications in real-time.
    Notifications are sent as JSON messages with the following format:
    {
        "event": "notification",
        "data": {
            "id": "reminder_123",
            "title": "Medication Reminder",
            "message": "Take aspirin",
            ...
        }
    }
    """
    await websocket.accept()
    notification_manager = get_notification_manager()
    notification_manager.register_websocket(websocket)

    logger.info("WebSocket client connected for notifications")

    try:
        # Keep connection alive and listen for client messages
        while True:
            # Wait for messages from client (e.g., acknowledgements)
            data = await websocket.receive_text()
            logger.debug(f"Received WebSocket message: {data}")

            # Handle client messages (e.g., acknowledge notifications)
            # Format: {"action": "acknowledge", "notification_id": "reminder_123"}
            try:
                import json

                message = json.loads(data)
                action = message.get("action")

                if action == "acknowledge":
                    notification_id = message.get("notification_id")
                    if notification_id:
                        notification_manager.acknowledge(notification_id)
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "event": "acknowledged",
                                    "notification_id": notification_id,
                                }
                            )
                        )

                elif action == "dismiss":
                    notification_id = message.get("notification_id")
                    if notification_id:
                        notification_manager.dismiss(notification_id)
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "event": "dismissed",
                                    "notification_id": notification_id,
                                }
                            )
                        )

            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from WebSocket: {data}")

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
        notification_manager.unregister_websocket(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        notification_manager.unregister_websocket(websocket)
        raise
