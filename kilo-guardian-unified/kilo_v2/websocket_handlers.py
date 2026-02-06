"""
WebSocket Handlers for Real-time Streaming

Purpose:
- Provide WebSocket endpoints for drone video streaming, telemetry, and manual control
- Provide WebSocket endpoint for Meshtastic device tracking
- Manage client connections and broadcasting with robustness and redundancy

Features:
- Connection health monitoring with ping/pong
- Automatic reconnection support
- Rate limiting and circuit breaker pattern
- Comprehensive error handling and recovery
- Metrics tracking and logging

Dependencies:
- FastAPI WebSocket support
- drone_control plugin for video/telemetry
- meshtastic_tracker plugin for location events
"""

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

logger = logging.getLogger(__name__)


@dataclass
class ConnectionMetrics:
    """Track metrics for a WebSocket connection."""

    connected_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    messages_sent: int = 0
    messages_received: int = 0
    errors: int = 0
    bytes_sent: int = 0
    last_ping: float = 0
    last_pong: float = 0
    ping_failures: int = 0


@dataclass
class CircuitBreaker:
    """Circuit breaker to prevent cascade failures."""

    failure_threshold: int = 5
    timeout: float = 60.0
    failures: int = 0
    last_failure_time: float = 0
    state: str = "closed"  # closed, open, half_open

    def record_success(self):
        """Record successful operation."""
        if self.state == "half_open":
            self.state = "closed"
            self.failures = 0
            logger.info("Circuit breaker closed after successful operation")

    def record_failure(self):
        """Record failed operation."""
        self.failures += 1
        self.last_failure_time = time.time()

        if self.failures >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failures} failures")

    def can_attempt(self) -> bool:
        """Check if operation can be attempted."""
        if self.state == "closed":
            return True

        if self.state == "open":
            if time.time() - self.last_failure_time >= self.timeout:
                self.state = "half_open"
                logger.info("Circuit breaker entering half_open state")
                return True
            return False

        # half_open state
        return True


@dataclass
class RateLimiter:
    """Rate limiter to prevent client abuse."""

    max_requests: int = 100
    window_seconds: float = 1.0
    requests: deque = field(default_factory=deque)

    def can_proceed(self) -> bool:
        """Check if request is within rate limit."""
        now = time.time()

        # Remove old requests outside window
        while self.requests and now - self.requests[0] > self.window_seconds:
            self.requests.popleft()

        # Check if within limit
        if len(self.requests) >= self.max_requests:
            return False

        self.requests.append(now)
        return True


class ConnectionManager:
    """Manages WebSocket client connections and broadcasting with robustness."""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {
            "video": set(),
            "telemetry": set(),
            "manual_control": set(),
            "meshtastic": set(),
        }

        # Connection metadata
        self.connection_metrics: Dict[int, ConnectionMetrics] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {
            "video": CircuitBreaker(failure_threshold=3, timeout=30.0),
            "telemetry": CircuitBreaker(failure_threshold=5, timeout=20.0),
            "manual_control": CircuitBreaker(failure_threshold=10, timeout=10.0),
            "meshtastic": CircuitBreaker(failure_threshold=5, timeout=30.0),
        }
        self.rate_limiters: Dict[int, RateLimiter] = {}

        # Health monitoring
        self.health_check_interval = 10.0  # seconds
        self.ping_timeout = 5.0
        self.max_ping_failures = 3

        # Metrics
        self.total_connections = 0
        self.total_disconnections = 0
        self.total_messages_sent = 0
        self.total_errors = 0

        # Health monitor task will be started explicitly by the application
        # during startup to avoid scheduling background tasks at import time
        # which can raise "no running event loop" during tests.
        self._health_task = None

    async def connect(
        self, websocket: WebSocket, channel: str, max_connections: Optional[int] = None
    ):
        """Accept a new WebSocket connection with validation."""
        # Check max connections limit
        if max_connections and len(self.active_connections[channel]) >= max_connections:
            logger.warning(f"Max connections reached for {channel}: {max_connections}")
            await websocket.close(code=1008, reason="Max connections reached")
            return False

        try:
            await websocket.accept()
            self.active_connections[channel].add(websocket)

            # Initialize metrics
            ws_id = id(websocket)
            self.connection_metrics[ws_id] = ConnectionMetrics()
            self.rate_limiters[ws_id] = RateLimiter(
                max_requests=100 if channel == "manual_control" else 1000,
                window_seconds=1.0,
            )

            self.total_connections += 1

            logger.info(
                f"WebSocket connected to {channel}. Total: {len(self.active_connections[channel])}, Lifetime: {self.total_connections}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to accept WebSocket connection on {channel}: {e}")
            return False

    def disconnect(self, websocket: WebSocket, channel: str):
        """Remove a WebSocket connection and clean up resources."""
        self.active_connections[channel].discard(websocket)

        ws_id = id(websocket)
        metrics = self.connection_metrics.pop(ws_id, None)
        self.rate_limiters.pop(ws_id, None)

        self.total_disconnections += 1

        if metrics:
            duration = time.time() - metrics.connected_at
            logger.info(
                f"WebSocket disconnected from {channel}. "
                f"Duration: {duration:.1f}s, Sent: {metrics.messages_sent}, "
                f"Received: {metrics.messages_received}, Errors: {metrics.errors}"
            )
        else:
            logger.info(
                f"WebSocket disconnected from {channel}. Total: {len(self.active_connections[channel])}"
            )

    async def broadcast(self, channel: str, data: Any, retry_on_failure: bool = True):
        """Broadcast data to all clients on a channel with error handling."""
        if not self.active_connections[channel]:
            return

        # Check circuit breaker
        breaker = self.circuit_breakers[channel]
        if not breaker.can_attempt():
            logger.warning(f"Circuit breaker open for {channel}, dropping broadcast")
            return

        disconnected = set()
        success_count = 0
        error_count = 0

        data_size = len(data) if isinstance(data, bytes) else len(json.dumps(data))

        for websocket in list(self.active_connections[channel]):
            ws_id = id(websocket)
            metrics = self.connection_metrics.get(ws_id)

            if not metrics:
                continue

            try:
                if websocket.client_state != WebSocketState.CONNECTED:
                    disconnected.add(websocket)
                    continue

                # Send data
                if isinstance(data, bytes):
                    await asyncio.wait_for(websocket.send_bytes(data), timeout=2.0)
                else:
                    json_data = (
                        json.dumps(data) if isinstance(data, dict) else str(data)
                    )
                    await asyncio.wait_for(websocket.send_text(json_data), timeout=2.0)

                # Update metrics
                metrics.messages_sent += 1
                metrics.bytes_sent += data_size
                metrics.last_activity = time.time()
                success_count += 1

            except asyncio.TimeoutError:
                logger.warning(f"Timeout broadcasting to {channel} client {ws_id}")
                metrics.errors += 1
                error_count += 1
                disconnected.add(websocket)

            except Exception as e:
                logger.warning(f"Error broadcasting to {channel} client {ws_id}: {e}")
                metrics.errors += 1
                error_count += 1

                # Disconnect after multiple errors
                if metrics.errors >= 5:
                    disconnected.add(websocket)

        # Clean up disconnected clients
        for ws in disconnected:
            self.disconnect(ws, channel)

        # Update circuit breaker
        if error_count > success_count and error_count > 0:
            breaker.record_failure()
        elif success_count > 0:
            breaker.record_success()

        self.total_messages_sent += success_count
        self.total_errors += error_count

        if error_count > 0:
            logger.debug(
                f"Broadcast to {channel}: {success_count} success, {error_count} errors"
            )

    async def _health_monitor_loop(self):
        """Background task to monitor connection health."""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._check_all_connections()
            except Exception as e:
                logger.error(f"Health monitor error: {e}")

    def start(self):
        """Start background tasks for the connection manager.

        This should be called from an async context (e.g. FastAPI startup)
        so that an event loop is running. Calling at import time causes
        RuntimeError when tests import modules without an event loop.
        """
        if self._health_task is None or self._health_task.done():
            try:
                self._health_task = asyncio.create_task(self._health_monitor_loop())
                logger.info("ConnectionManager: health monitor started")
            except RuntimeError as e:
                # If called without a running loop, surface a clear message
                logger.warning(f"Cannot start ConnectionManager health monitor: {e}")
                self._health_task = None

    def stop(self):
        """Stop background tasks managed by the connection manager."""
        try:
            if self._health_task and not self._health_task.done():
                self._health_task.cancel()
                logger.info("ConnectionManager: health monitor cancelled")
        except Exception:
            pass

    async def _check_all_connections(self):
        """Check health of all active connections."""
        now = time.time()

        for channel, connections in self.active_connections.items():
            for websocket in list(connections):
                ws_id = id(websocket)
                metrics = self.connection_metrics.get(ws_id)

                if not metrics:
                    continue

                # Check for stale connections
                if now - metrics.last_activity > 30.0:
                    try:
                        # Send ping
                        await asyncio.wait_for(
                            websocket.send_text(json.dumps({"type": "ping"})),
                            timeout=2.0,
                        )
                        metrics.last_ping = now
                    except Exception as e:
                        logger.warning(f"Ping failed for {channel} client {ws_id}: {e}")
                        metrics.ping_failures += 1

                        if metrics.ping_failures >= self.max_ping_failures:
                            logger.info(
                                f"Disconnecting unresponsive {channel} client {ws_id}"
                            )
                            self.disconnect(websocket, channel)
                            try:
                                await websocket.close(code=1001, reason="Unresponsive")
                            except Exception:
                                pass

    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "total_connections": self.total_connections,
            "total_disconnections": self.total_disconnections,
            "total_messages_sent": self.total_messages_sent,
            "total_errors": self.total_errors,
            "active_connections": {
                channel: len(conns)
                for channel, conns in self.active_connections.items()
            },
            "circuit_breakers": {
                channel: {"state": breaker.state, "failures": breaker.failures}
                for channel, breaker in self.circuit_breakers.items()
            },
        }


# Global connection manager instance
# Create the object at import time but do NOT start background tasks until
# the application (FastAPI) begins its startup lifecycle. Tests can import
# this module safely without triggering asyncio.create_task at import time.
manager = ConnectionManager()


# --- Drone Video Stream ---
async def handle_drone_video(websocket: WebSocket):
    """
    Stream JPEG video frames from drone camera.
    Clients receive continuous video frames as binary data.
    """
    await manager.connect(websocket, "video")

    try:
        # Keep connection alive, actual frames pushed by drone plugin
        while True:
            # Send heartbeat every 5s to keep connection alive
            await asyncio.sleep(5)
            if websocket.client_state != WebSocketState.CONNECTED:
                break

    except WebSocketDisconnect:
        logger.info("Video client disconnected")
    except Exception as e:
        logger.error(f"Video WebSocket error: {e}")
    finally:
        manager.disconnect(websocket, "video")


async def broadcast_video_frame(frame_data: bytes):
    """Called by drone_control plugin to broadcast video frames."""
    await manager.broadcast("video", frame_data)


# --- Drone Telemetry Stream ---
async def handle_drone_telemetry(websocket: WebSocket):
    """
    Stream real-time telemetry data for HUD display.
    Clients receive JSON updates at 5 Hz.
    """
    await manager.connect(websocket, "telemetry")

    try:
        while True:
            await asyncio.sleep(5)  # Heartbeat
            if websocket.client_state != WebSocketState.CONNECTED:
                break

    except WebSocketDisconnect:
        logger.info("Telemetry client disconnected")
    except Exception as e:
        logger.error(f"Telemetry WebSocket error: {e}")
    finally:
        manager.disconnect(websocket, "telemetry")


async def broadcast_telemetry(telem_data: Dict[str, Any]):
    """Called by drone_control plugin to broadcast telemetry."""
    await manager.broadcast("telemetry", telem_data)


# --- Manual Control Input ---
async def handle_manual_control(websocket: WebSocket):
    """
    Receive manual control inputs from gamepad/joystick.
    Client sends JSON: {"pitch": float, "roll": float, "yaw": float, "throttle": float}
    """
    if not await manager.connect(websocket, "manual_control", max_connections=5):
        return

    ws_id = id(websocket)
    rate_limiter = manager.rate_limiters.get(ws_id)
    metrics = manager.connection_metrics.get(ws_id)

    try:
        from plugin_manager import PluginManager

        pm = PluginManager()
        drone_plugin = pm.get_plugin("drone_control")

        if not drone_plugin:
            await websocket.send_text(
                json.dumps({"error": "Drone plugin not available"})
            )
            logger.error("Manual control requested but drone plugin not available")
            return

        logger.info(f"Manual control session started for client {ws_id}")

        while True:
            # Receive control input from client with timeout
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
            except asyncio.TimeoutError:
                # No input for 5s, send keepalive
                continue

            if metrics:
                metrics.messages_received += 1
                metrics.last_activity = time.time()

            # Rate limiting
            if rate_limiter and not rate_limiter.can_proceed():
                logger.warning(f"Rate limit exceeded for manual control client {ws_id}")
                await websocket.send_text(
                    json.dumps({"error": "Rate limit exceeded", "retry_after": 1.0})
                )
                continue

            try:
                control_input = json.loads(data)

                # Validate input
                if not isinstance(control_input, dict):
                    raise ValueError("Control input must be a JSON object")

                pitch = float(control_input.get("pitch", 0))
                roll = float(control_input.get("roll", 0))
                yaw = float(control_input.get("yaw", 0))
                throttle = float(control_input.get("throttle", 0.5))

                # Bounds check
                if not all(-1.0 <= v <= 1.0 for v in [pitch, roll, yaw]) or not (
                    0.0 <= throttle <= 1.0
                ):
                    raise ValueError("Control values out of bounds")

                # Queue input to drone plugin
                drone_plugin.queue_manual_control(pitch, roll, yaw, throttle)

                # Send acknowledgment
                await websocket.send_text(
                    json.dumps({"type": "ack", "timestamp": time.time()})
                )

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from manual control client {ws_id}: {e}")
                await websocket.send_text(json.dumps({"error": "Invalid JSON format"}))
                if metrics:
                    metrics.errors += 1

            except ValueError as e:
                logger.error(f"Invalid control input from client {ws_id}: {e}")
                await websocket.send_text(json.dumps({"error": str(e)}))
                if metrics:
                    metrics.errors += 1

            except Exception as e:
                logger.error(f"Error processing manual control input from {ws_id}: {e}")
                await websocket.send_text(
                    json.dumps({"error": "Internal server error"})
                )
                if metrics:
                    metrics.errors += 1

    except WebSocketDisconnect:
        logger.info(f"Manual control client {ws_id} disconnected normally")
    except Exception as e:
        logger.error(
            f"Manual control WebSocket error for client {ws_id}: {e}", exc_info=True
        )
    finally:
        manager.disconnect(websocket, "manual_control")
        logger.info(f"Manual control session ended for client {ws_id}")


# --- Meshtastic Location Stream ---
async def handle_meshtastic_stream(websocket: WebSocket):
    """
    Stream real-time Meshtastic device locations.
    Clients receive JSON updates when devices transmit position.
    """
    await manager.connect(websocket, "meshtastic")

    try:
        while True:
            await asyncio.sleep(5)  # Heartbeat
            if websocket.client_state != WebSocketState.CONNECTED:
                break

    except WebSocketDisconnect:
        logger.info("Meshtastic client disconnected")
    except Exception as e:
        logger.error(f"Meshtastic WebSocket error: {e}")
    finally:
        manager.disconnect(websocket, "meshtastic")


async def broadcast_meshtastic_event(event_data: Dict[str, Any]):
    """Called by meshtastic_tracker plugin to broadcast location events."""
    await manager.broadcast("meshtastic", event_data)


async def broadcast_notification(notification_data: Dict[str, Any]):
    """
    Broadcast a notification to all connected clients.

    notification_data should contain:
        - type: str - notification type ('reminder', 'warning', 'alert', 'info')
        - title: str - notification title
        - message: str - notification message
        - priority: str - 'low', 'medium', 'high', 'critical'
        - source: str - plugin or system that generated the notification
        - timestamp: str - ISO format timestamp
        - action: Optional[Dict] - action button config if applicable
    """
    await manager.broadcast("notifications", notification_data)


def send_notification_sync(notification_data: Dict[str, Any]):
    """
    Synchronous wrapper for sending notifications from non-async code.

    Use this from plugins that don't have direct access to async context.
    """
    import asyncio

    # Add timestamp if not present
    if "timestamp" not in notification_data:
        from datetime import datetime

        notification_data["timestamp"] = datetime.now().isoformat()

    try:
        loop = asyncio.get_running_loop()
        asyncio.ensure_future(broadcast_notification(notification_data), loop=loop)
    except RuntimeError:
        # No event loop running - log the notification instead
        logger.info(
            f"📢 Notification (no WS): {notification_data.get('title', 'Unknown')}: {notification_data.get('message', '')}"
        )


# --- Public API for plugins ---
def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance."""
    return manager
