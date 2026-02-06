"""
Drone Control Plugin

Purpose:
- Provide safe, high-level drone commands (simulate-first): arm, takeoff, land,
  waypoint missions, telemetry summary.
- Log actions and telemetry snapshots into Kilo Guardian datastore.
- Stream FPV video from drone camera via WebSocket
- Enable manual RC override control with deadman switch safety

Safety model:
- Defaults to simulation-only unless explicitly enabled via config/env.
- Arming, takeoff, and mission require explicit flags to be true.
- Manual control requires active confirmation token and implements deadman switch.

Dependencies:
- Prefer MAVSDK (async, robust) or DroneKit (ArduPilot). This stub loads
  gracefully without those packages present.
- Optional: OpenCV for video frame processing
"""

import asyncio
import json
import logging
import queue
import threading
import time
from typing import Any, Dict, List, Optional

try:
    from plugins.base_plugin import BasePlugin
except ModuleNotFoundError:
    # Allow direct imports during tests without PluginManager sys.modules shim
    from kilo_v2.plugins.base_plugin import BasePlugin  # type: ignore

try:
    # Attempt MAVSDK import (preferred)
    import mavsdk  # type: ignore
    from mavsdk import System  # type: ignore
    from mavsdk.mission import MissionItem, MissionPlan  # type: ignore

    MAVSDK_AVAILABLE = True
except Exception:
    MAVSDK_AVAILABLE = False
    System = None  # type: ignore
    MissionItem = None  # type: ignore
    MissionPlan = None  # type: ignore

try:
    # Fallback: DroneKit
    import dronekit  # type: ignore

    DRONEKIT_AVAILABLE = True
except Exception:
    DRONEKIT_AVAILABLE = False

try:
    from data_core import KiloDataCore
except Exception:
    KiloDataCore = None  # type: ignore

try:
    import cv2  # type: ignore
    import numpy as np  # type: ignore

    CV2_AVAILABLE = True
except Exception:
    CV2_AVAILABLE = False
    cv2 = None  # type: ignore
    np = None  # type: ignore


logger = logging.getLogger(__name__)

# Global registries for WebSocket clients (managed by server_core)
video_clients = []  # type: List[Any]
telemetry_clients = []  # type: List[Any]


class DroneControl(BasePlugin):
    def __init__(self):
        super().__init__()
        self._drone = None  # type: Optional[Any]
        self._sim_mode = (
            True  # simulation-first; set False via config to enable real ops
        )
        self._last_health: Dict[str, Any] = {"ok": True, "reason": "initialized"}
        self._telemetry_thread = None  # type: Optional[threading.Thread]
        self._stop_event = threading.Event()
        self._event_loop = None  # type: Optional[asyncio.AbstractEventLoop]
        self._connected = False
        self._armed = False
        self._confirmation_tokens: Dict[str, float] = {}  # token -> expiry timestamp

        # Video streaming
        self._video_thread = None  # type: Optional[threading.Thread]
        self._video_enabled = False

        # Manual control
        self._manual_control_enabled = False
        self._manual_control_queue: queue.Queue = queue.Queue()
        self._manual_control_thread = None  # type: Optional[threading.Thread]
        self._last_manual_input_time = 0.0

        # Telemetry streaming for HUD
        self._latest_telemetry: Dict[str, Any] = {}

    def get_name(self) -> str:
        return "drone_control"

    def get_keywords(self) -> List[str]:
        return [
            "drone",
            "uav",
            "flight",
            "takeoff",
            "mission",
            "waypoint",
            "telemetry",
            "fpv",
            "video",
            "manual control",
            "joystick",
        ]

    def start_background_task(self) -> None:
        # Telemetry streaming and drone connection
        try:
            from kilo_v2 import config as _cfg
        except Exception:
            _cfg = None
        enabled = bool(getattr(_cfg, "DRONE_ENABLE", False)) if _cfg else False
        if not enabled:
            logger.info("Drone plugin disabled by config; background task not started.")
            return

        if not MAVSDK_AVAILABLE:
            logger.warning("MAVSDK not available; drone background task cannot start.")
            return

        if self._telemetry_thread and self._telemetry_thread.is_alive():
            logger.info("Drone telemetry thread already running.")
            return

        # Start async connection and telemetry loop in background thread
        self._telemetry_thread = threading.Thread(
            target=self._background_task_sync, daemon=True
        )
        self._telemetry_thread.start()
        logger.info("Drone background tasks started")

        # Start video streaming if enabled
        video_enabled = (
            bool(getattr(_cfg, "DRONE_VIDEO_ENABLE", False)) if _cfg else False
        )
        if video_enabled:
            # Video will be started in the async event loop
            logger.info("Video streaming will start with drone connection")
        self._stop_event.clear()
        self._telemetry_thread = threading.Thread(
            target=self._telemetry_loop, daemon=True
        )
        self._telemetry_thread.start()
        logger.info("Drone telemetry thread started.")

    def stop_background_task(self) -> None:
        """Stop background telemetry gracefully."""
        self._stop_event.set()
        if self._telemetry_thread:
            self._telemetry_thread.join(timeout=5)
        logger.info("Drone telemetry thread stopped.")

    def _telemetry_loop(self) -> None:
        """Run asyncio event loop for MAVSDK connection and telemetry."""
        try:
            from kilo_v2 import config as _cfg
        except Exception:
            _cfg = None

        self._event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._event_loop)

        try:
            self._event_loop.run_until_complete(self._connect_and_stream(_cfg))
        except Exception as ex:
            logger.error("Drone telemetry loop error: %s", ex)
        finally:
            self._event_loop.close()

    async def _connect_and_stream(self, cfg: Any) -> None:
        """Connect to drone and stream telemetry, video, and prepare manual control with retry logic."""
        endpoint = (
            getattr(cfg, "DRONE_ENDPOINT", "udp://:14540") if cfg else "udp://:14540"
        )
        self._sim_mode = bool(getattr(cfg, "DRONE_SIMULATION", True)) if cfg else True
        video_enabled = (
            bool(getattr(cfg, "DRONE_VIDEO_ENABLE", False)) if cfg else False
        )

        max_retries = 5
        retry_delay = 5.0
        retry_count = 0

        while retry_count < max_retries and not self._stop_event.is_set():
            try:
                logger.info(
                    f"Connecting to drone at {endpoint} (sim_mode={self._sim_mode}, attempt {retry_count + 1}/{max_retries})"
                )

                self._drone = System()
                await self._drone.connect(system_address=endpoint)

                logger.info("Waiting for drone to connect...")

                # Wait for connection with timeout
                connection_timeout = 30.0
                start_time = time.time()

                async for state in self._drone.core.connection_state():
                    if state.is_connected:
                        logger.info("Drone connected successfully!")
                        self._connected = True
                        retry_count = 0  # Reset retry counter on success
                        break

                    # Check timeout
                    if time.time() - start_time > connection_timeout:
                        raise TimeoutError(
                            f"Connection timeout after {connection_timeout}s"
                        )

                if not self._connected:
                    raise ConnectionError("Failed to establish drone connection")

                # Start all streaming tasks concurrently
                tasks = [
                    asyncio.create_task(self._stream_telemetry()),
                    asyncio.create_task(
                        self._stream_telemetry_async()
                    ),  # For HUD WebSocket
                ]

                if video_enabled:
                    tasks.append(asyncio.create_task(self._stream_video_async()))

                # Run all tasks with error handling
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Check for task failures
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"Task {i} failed: {result}")

                # If we get here, connection was lost, attempt reconnection
                if not self._stop_event.is_set():
                    logger.warning("Drone connection lost, attempting to reconnect...")
                    self._connected = False
                    retry_count += 1
                    await asyncio.sleep(retry_delay)

            except TimeoutError as e:
                logger.error(f"Connection timeout: {e}")
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)

            except ConnectionError as e:
                logger.error(f"Connection error: {e}")
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)

            except Exception as ex:
                logger.error(
                    f"Unexpected error in drone connection: {ex}", exc_info=True
                )
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)

        if retry_count >= max_retries:
            logger.error(f"Failed to connect to drone after {max_retries} attempts")
            self._connected = False

    async def _stream_telemetry(self) -> None:
        """Stream telemetry at 1 Hz and log events with error recovery."""
        consecutive_errors = 0
        max_consecutive_errors = 5

        while not self._stop_event.is_set() and self._connected:
            try:
                # Fetch telemetry snapshot
                telem = await self._fetch_telemetry()
                self._log_event_safely("drone_telem", telem)
                logger.debug(
                    "Telemetry: lat=%.6f, alt=%.1f, armed=%s",
                    telem.get("lat", 0),
                    telem.get("alt", 0),
                    telem.get("armed", False),
                )

                # Reset error counter on success
                consecutive_errors = 0

            except Exception as ex:
                consecutive_errors += 1
                logger.warning(
                    f"Telemetry fetch error ({consecutive_errors}/{max_consecutive_errors}): {ex}"
                )

                # If too many consecutive errors, mark connection as lost
                if consecutive_errors >= max_consecutive_errors:
                    logger.error(
                        "Too many consecutive telemetry errors, marking connection as lost"
                    )
                    self._connected = False
                    break

            await asyncio.sleep(1)

    async def _fetch_telemetry(self) -> Dict[str, Any]:
        """Fetch current telemetry from drone."""
        telem = {
            "lat": None,
            "lon": None,
            "alt": None,
            "ground_speed": None,
            "armed": False,
            "mode": "SIM" if self._sim_mode else "UNKNOWN",
            "battery": None,
        }

        if not self._drone:
            return telem

        try:
            # Position
            async for position in self._drone.telemetry.position():
                telem["lat"] = position.latitude_deg
                telem["lon"] = position.longitude_deg
                telem["alt"] = position.relative_altitude_m
                break

            # Armed status
            async for armed in self._drone.telemetry.armed():
                telem["armed"] = armed
                self._armed = armed
                break

            # Flight mode
            async for flight_mode in self._drone.telemetry.flight_mode():
                telem["mode"] = str(flight_mode)
                break

            # Battery
            async for battery in self._drone.telemetry.battery():
                telem["battery"] = battery.remaining_percent
                break

        except Exception as ex:
            logger.debug("Telemetry component error: %s", ex)

        return telem

    def health(self) -> Dict[str, Any]:
        # Respect config
        try:
            from kilo_v2 import config as _cfg
        except Exception:
            _cfg = None
        if _cfg:
            self._sim_mode = bool(getattr(_cfg, "DRONE_SIMULATION", True))
        ok = MAVSDK_AVAILABLE or DRONEKIT_AVAILABLE or self._sim_mode
        reason = (
            "mavsdk or dronekit available"
            if (MAVSDK_AVAILABLE or DRONEKIT_AVAILABLE)
            else ("simulation mode" if self._sim_mode else "no driver available")
        )
        self._last_health = {"ok": ok, "reason": reason, "ts": time.time()}
        return self._last_health

    def execute(self, query: str) -> Dict[str, Any]:
        q = query.lower()
        if "telemetry" in q:
            return self._telemetry_summary()
        if "takeoff" in q:
            # Extract confirmation token if present
            token = self._extract_token(query)
            return self._takeoff(token)
        if "land" in q:
            return self._land()
        if "rtl" in q or "return to launch" in q:
            return self._rtl()
        if any(k in q for k in ["mission", "waypoint", "route"]):
            # Extract waypoints from query (expect JSON)
            waypoints = self._parse_waypoints(query)
            token = self._extract_token(query)
            return self._start_mission(waypoints, token)
        if "arm" in q:
            token = self._extract_token(query)
            return self._arm(token)
        if "disarm" in q:
            return self._disarm()
        if "request token" in q or "get token" in q:
            return self._generate_token()
        if "enable manual" in q or "manual control" in q:
            token = self._extract_token(query)
            return self.enable_manual_control(token)
        if "disable manual" in q:
            return self.disable_manual_control()
        return self.run(query)

    def _extract_token(self, query: str) -> Optional[str]:
        """Extract confirmation token from query string."""
        # Look for token=<value> pattern
        import re

        match = re.search(r"token[=:]\s*([a-zA-Z0-9]+)", query)
        return match.group(1) if match else None

    def _parse_waypoints(self, query: str) -> List[Dict[str, float]]:
        """Extract JSON waypoint list from query."""
        import re

        # Look for JSON array in query
        match = re.search(r"\[.*\]", query, re.DOTALL)
        if match:
            try:
                waypoints = json.loads(match.group(0))
                return waypoints
            except Exception as ex:
                logger.warning("Failed to parse waypoints JSON: %s", ex)
        return []

    def run(self, query: str) -> Dict[str, Any]:
        self._log_event_safely("drone_query", {"query": query, "note": "unrecognized"})
        return {
            "type": "tool_result",
            "tool": self.get_name(),
            "content": {
                "reply": "Drone control ready. Try: 'drone telemetry', 'drone takeoff', 'drone land', 'drone mission'.",
                "drivers": {
                    "mavsdk": MAVSDK_AVAILABLE,
                    "dronekit": DRONEKIT_AVAILABLE,
                },
                "simulation_mode": self._sim_mode,
            },
        }

    # --- Operations -----------------------------------------------------

    def _generate_token(self) -> Dict[str, Any]:
        """Generate a short-lived confirmation token for safety-critical operations."""
        import secrets

        token = secrets.token_hex(8)
        expiry = time.time() + 300  # 5 minutes
        self._confirmation_tokens[token] = expiry
        self._log_event_safely(
            "drone_token_generated", {"token": token, "expiry": expiry}
        )
        return {
            "type": "tool_result",
            "tool": self.get_name(),
            "content": {
                "token": token,
                "expires_in_seconds": 300,
                "note": "Use this token in commands like: 'drone takeoff token=<token>'",
            },
        }

    def _validate_token(self, token: Optional[str]) -> bool:
        """Check if token is valid and not expired."""
        try:
            from kilo_v2 import config as _cfg
        except Exception:
            _cfg = None

        require_confirmation = (
            bool(getattr(_cfg, "DRONE_SAFETY_REQUIRE_CONFIRMATION", True))
            if _cfg
            else True
        )

        if not require_confirmation or self._sim_mode:
            # In sim mode or if confirmation disabled, allow operation
            return True

        if not token:
            return False

        expiry = self._confirmation_tokens.get(token)
        if expiry and time.time() < expiry:
            # Token valid; consume it
            del self._confirmation_tokens[token]
            return True

        return False

    def _arm(self, token: Optional[str]) -> Dict[str, Any]:
        """Arm the drone."""
        if not self._validate_token(token):
            return self._error(
                "Arming requires valid confirmation token. Request one with 'drone request token'."
            )

        if not self._event_loop or not self._drone:
            return self._error("Drone not connected.")

        async def do_arm():
            await self._drone.action.arm()

        asyncio.run_coroutine_threadsafe(do_arm(), self._event_loop).result(timeout=5)
        self._log_event_safely("drone_arm", {"sim": self._sim_mode})
        return {
            "type": "tool_result",
            "tool": self.get_name(),
            "content": {"status": "armed", "simulation": self._sim_mode},
        }

    def _disarm(self) -> Dict[str, Any]:
        """Disarm the drone (no token required for safety)."""
        if not self._event_loop or not self._drone:
            return self._error("Drone not connected.")

        async def do_disarm():
            await self._drone.action.disarm()

        asyncio.run_coroutine_threadsafe(do_disarm(), self._event_loop).result(
            timeout=5
        )
        self._log_event_safely("drone_disarm", {"sim": self._sim_mode})
        return {
            "type": "tool_result",
            "tool": self.get_name(),
            "content": {"status": "disarmed", "simulation": self._sim_mode},
        }

    def _takeoff(self, token: Optional[str]) -> Dict[str, Any]:
        """Takeoff to default altitude."""
        if not self._validate_token(token):
            return self._error(
                "Takeoff requires valid confirmation token. Request one with 'drone request token'."
            )

        if not self._event_loop or not self._drone:
            return self._error("Drone not connected.")

        async def do_takeoff():
            if not self._armed:
                await self._drone.action.arm()
            await self._drone.action.takeoff()

        asyncio.run_coroutine_threadsafe(do_takeoff(), self._event_loop).result(
            timeout=10
        )
        self._log_event_safely("drone_takeoff", {"sim": self._sim_mode})
        return {
            "type": "tool_result",
            "tool": self.get_name(),
            "content": {"status": "takeoff initiated", "simulation": self._sim_mode},
        }

    def _land(self) -> Dict[str, Any]:
        """Land the drone (no token required for safety)."""
        if not self._event_loop or not self._drone:
            return self._error("Drone not connected.")

        async def do_land():
            await self._drone.action.land()

        asyncio.run_coroutine_threadsafe(do_land(), self._event_loop).result(timeout=10)
        self._log_event_safely("drone_land", {"sim": self._sim_mode})
        return {
            "type": "tool_result",
            "tool": self.get_name(),
            "content": {"status": "landing initiated", "simulation": self._sim_mode},
        }

    def _rtl(self) -> Dict[str, Any]:
        """Return to launch (emergency, no token required)."""
        if not self._event_loop or not self._drone:
            return self._error("Drone not connected.")

        async def do_rtl():
            await self._drone.action.return_to_launch()

        asyncio.run_coroutine_threadsafe(do_rtl(), self._event_loop).result(timeout=10)
        self._log_event_safely("drone_rtl", {"sim": self._sim_mode})
        return {
            "type": "tool_result",
            "tool": self.get_name(),
            "content": {"status": "RTL initiated", "simulation": self._sim_mode},
        }

    def _start_mission(
        self, waypoints: List[Dict[str, float]], token: Optional[str]
    ) -> Dict[str, Any]:
        """Upload and start mission with waypoints."""
        if not self._validate_token(token):
            return self._error(
                "Mission requires valid confirmation token. Request one with 'drone request token'."
            )

        if not waypoints:
            return self._error(
                'No waypoints provided. Include JSON array like: [{"lat":47.0,"lon":8.0,"alt":10}, ...]'
            )

        if not self._event_loop or not self._drone:
            return self._error("Drone not connected.")

        # Validate waypoints and enforce geofence/altitude
        try:
            validated = self._validate_waypoints(waypoints)
        except Exception as ex:
            return self._error(f"Waypoint validation failed: {ex}")

        async def do_mission():
            mission_items = []
            for idx, wp in enumerate(validated):
                mission_items.append(
                    MissionItem(
                        wp["lat"],
                        wp["lon"],
                        wp["alt"],
                        10,  # speed m/s
                        True,  # is_fly_through
                        float("nan"),  # gimbal pitch
                        float("nan"),  # gimbal yaw
                        MissionItem.CameraAction.NONE,
                    )
                )

            mission_plan = MissionPlan(mission_items)
            await self._drone.mission.upload_mission(mission_plan)
            await self._drone.action.arm()
            await self._drone.mission.start_mission()

        asyncio.run_coroutine_threadsafe(do_mission(), self._event_loop).result(
            timeout=15
        )
        self._log_event_safely(
            "drone_mission", {"sim": self._sim_mode, "waypoints": validated}
        )
        return {
            "type": "tool_result",
            "tool": self.get_name(),
            "content": {
                "status": "mission started",
                "simulation": self._sim_mode,
                "waypoints": validated,
            },
        }

    def _validate_waypoints(
        self, waypoints: List[Dict[str, float]]
    ) -> List[Dict[str, float]]:
        """Validate waypoints against altitude and geofence constraints."""
        try:
            from kilo_v2 import config as _cfg
        except Exception:
            _cfg = None

        max_alt = float(getattr(_cfg, "DRONE_MAX_ALT", 50.0)) if _cfg else 50.0
        geofence_str = getattr(_cfg, "DRONE_GEOFENCE", "") if _cfg else ""

        validated = []
        for wp in waypoints:
            lat = float(wp.get("lat", 0))
            lon = float(wp.get("lon", 0))
            alt = float(wp.get("alt", 10))

            if alt > max_alt:
                raise ValueError(f"Altitude {alt}m exceeds max {max_alt}m")

            # Optional geofence check (simple bbox for now)
            if geofence_str:
                try:
                    geofence = json.loads(geofence_str)
                    if not self._within_geofence(lat, lon, geofence):
                        raise ValueError(f"Waypoint ({lat}, {lon}) outside geofence")
                except Exception as ex:
                    logger.warning("Geofence parse/check failed: %s", ex)

            validated.append({"lat": lat, "lon": lon, "alt": alt})

        return validated

    @staticmethod
    def _within_geofence(lat: float, lon: float, geofence: Dict[str, Any]) -> bool:
        """Check if point is within geofence bbox."""
        # Simple bounding box: {"min_lat": ..., "max_lat": ..., "min_lon": ..., "max_lon": ...}
        min_lat = geofence.get("min_lat", -90)
        max_lat = geofence.get("max_lat", 90)
        min_lon = geofence.get("min_lon", -180)
        max_lon = geofence.get("max_lon", 180)
        return min_lat <= lat <= max_lat and min_lon <= lon <= max_lon

    def _ensure_driver(self) -> None:
        # Legacy stub; connection now handled in background task
        pass

    def _telemetry_summary(self) -> Dict[str, Any]:
        # Return latest telemetry (fetch from background stream or query now)
        if self._event_loop and self._drone and self._connected:
            try:
                telem = asyncio.run_coroutine_threadsafe(
                    self._fetch_telemetry(), self._event_loop
                ).result(timeout=5)
            except Exception as ex:
                logger.warning("Failed to fetch telemetry: %s", ex)
                telem = {"error": str(ex)}
        else:
            telem = {
                "lat": None,
                "lon": None,
                "alt": None,
                "ground_speed": None,
                "armed": False,
                "mode": "SIM" if self._sim_mode else "DISCONNECTED",
            }

        self._log_event_safely("drone_telem", telem)
        return {
            "type": "tool_result",
            "tool": self.get_name(),
            "content": {
                "telemetry": telem,
                "simulation": self._sim_mode,
                "config": self._config_snapshot(),
            },
        }

    # --- Utils ----------------------------------------------------------

    def _error(self, msg: str) -> Dict[str, Any]:
        return {
            "type": "tool_error",
            "tool": self.get_name(),
            "content": {"error": msg},
        }

    def _log_event_safely(self, event_type: str, content: Dict[str, Any]) -> None:
        if not KiloDataCore:
            return
        try:
            dc = KiloDataCore()
            dc.log_event(event_type=event_type, content=content)
        except Exception as ex:
            logger.debug("KiloDataCore.log_event failed: %s", ex)

    def _config_snapshot(self) -> Dict[str, Any]:
        try:
            from kilo_v2 import config as _cfg

            return {
                "enabled": bool(getattr(_cfg, "DRONE_ENABLE", False)),
                "simulation": bool(getattr(_cfg, "DRONE_SIMULATION", True)),
                "endpoint": getattr(_cfg, "DRONE_ENDPOINT", None),
                "require_confirmation": bool(
                    getattr(_cfg, "DRONE_SAFETY_REQUIRE_CONFIRMATION", True)
                ),
                "max_alt": getattr(_cfg, "DRONE_MAX_ALT", None),
                "video_enabled": bool(getattr(_cfg, "DRONE_VIDEO_ENABLE", False)),
                "manual_control_enabled": bool(
                    getattr(_cfg, "DRONE_MANUAL_CONTROL_ENABLE", False)
                ),
            }
        except Exception:
            return {"enabled": False}

    # --- Video Streaming -----------------------------------------------

    async def _stream_video_async(self):
        """
        Async task: pull video frames from MAVSDK camera or simulate,
        encode to JPEG, broadcast to WebSocket clients.
        """
        try:
            from kilo_v2 import config as _cfg

            quality = int(getattr(_cfg, "DRONE_VIDEO_QUALITY", 80))
            fps = int(getattr(_cfg, "DRONE_VIDEO_FPS", 30))
        except Exception:
            quality = 80
            fps = 30

        frame_delay = 1.0 / fps

        logger.info(
            "Video streaming started (simulation mode)"
            if self._sim_mode
            else "Video streaming started"
        )

        consecutive_errors = 0
        max_errors = 10

        while not self._stop_event.is_set():
            try:
                if not CV2_AVAILABLE:
                    logger.warning("Video streaming disabled: OpenCV not available")
                    await asyncio.sleep(2)
                    continue

                # In simulation, generate test pattern
                if self._sim_mode:
                    frame = self._generate_test_pattern()
                else:
                    # Real drone: use MAVSDK camera plugin
                    # TODO: wire actual camera frames; placeholder keeps loop alive
                    frame = self._generate_test_pattern()

                if frame is None:
                    consecutive_errors += 1
                    if consecutive_errors >= max_errors:
                        logger.error("Video stream halted: no frames available")
                        break
                    await asyncio.sleep(frame_delay)
                    continue

                # Encode to JPEG
                _, jpeg_bytes = cv2.imencode(
                    ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality]
                )
                jpeg_data = jpeg_bytes.tobytes()

                await self._broadcast_video(jpeg_data)
                consecutive_errors = 0
                await asyncio.sleep(frame_delay)

            except Exception as ex:
                consecutive_errors += 1
                logger.error("Video streaming error: %s", ex)
                if consecutive_errors >= max_errors:
                    logger.error("Video stream halted after repeated errors")
                    break
                await asyncio.sleep(1)

    def _generate_test_pattern(self) -> Optional[Any]:
        """Generate a test pattern frame for simulation mode."""
        if not CV2_AVAILABLE:
            return None

        # Create 1280x720 frame with test pattern
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)

        # Draw gradient background
        for y in range(720):
            color = int(y / 720 * 255)
            frame[y, :] = [color, color // 2, 255 - color]

        # Add text overlay
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(
            frame,
            "KILO GUARDIAN - FPV SIM",
            (50, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
        )
        cv2.putText(
            frame,
            timestamp,
            (50, 100),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            1,
        )

        # Draw crosshair
        cv2.line(frame, (640 - 50, 360), (640 + 50, 360), (0, 255, 0), 2)
        cv2.line(frame, (640, 360 - 50), (640, 360 + 50), (0, 255, 0), 2)
        cv2.circle(frame, (640, 360), 30, (0, 255, 0), 2)

        return frame

    async def _broadcast_video(self, jpeg_data: bytes):
        """Broadcast video frame to all connected WebSocket clients."""
        try:
            from kilo_v2.websocket_handlers import broadcast_video_frame

            await broadcast_video_frame(jpeg_data)
        except ImportError:
            # WebSocket handlers not available, just log
            logger.debug(f"Broadcasting video frame: {len(jpeg_data)} bytes")

    # --- Telemetry Streaming for HUD -----------------------------------

    async def _stream_telemetry_async(self):
        """
        Continuously fetch telemetry and broadcast to WebSocket clients.
        Used for real-time HUD overlay.
        """
        try:
            from kilo_v2 import config as _cfg
        except Exception:
            _cfg = None

        logger.info("Telemetry streaming started")

        while not self._stop_event.is_set():
            try:
                telem = await self._fetch_telemetry()
                self._latest_telemetry = telem

                # Broadcast to all telemetry clients
                await self._broadcast_telemetry(telem)

                await asyncio.sleep(0.2)  # 5 Hz updates

            except Exception as ex:
                logger.error("Telemetry streaming error: %s", ex)
                await asyncio.sleep(1)

    async def _broadcast_telemetry(self, telem: Dict[str, Any]):
        """Broadcast telemetry to WebSocket clients."""
        try:
            from kilo_v2.websocket_handlers import broadcast_telemetry

            await broadcast_telemetry(telem)
        except ImportError:
            logger.debug(f"Broadcasting telemetry: alt={telem.get('alt', 0)}m")

    # --- Manual Control ------------------------------------------------

    async def _manual_control_loop_async(self):
        """
        Process manual control inputs from queue.
        Implements deadman switch safety (2s timeout).
        """
        try:
            from kilo_v2 import config as _cfg

            deadman_timeout = float(getattr(_cfg, "DRONE_DEADMAN_TIMEOUT", 2.0))
        except Exception:
            deadman_timeout = 2.0

        logger.info(
            f"Manual control loop started (deadman timeout: {deadman_timeout}s)"
        )

        while not self._stop_event.is_set() and self._manual_control_enabled:
            try:
                # Check deadman switch
                if time.time() - self._last_manual_input_time > deadman_timeout:
                    # No input for timeout period → neutral controls
                    if self._drone and not self._sim_mode:
                        await self._drone.manual_control.set_manual_control_input(
                            pitch=0.0, roll=0.0, yaw=0.0, throttle=0.5
                        )
                    await asyncio.sleep(0.1)
                    continue

                # Get next control input from queue (non-blocking)
                try:
                    cmd = self._manual_control_queue.get_nowait()
                    pitch = float(cmd.get("pitch", 0))  # -1 to +1
                    roll = float(cmd.get("roll", 0))
                    yaw = float(cmd.get("yaw", 0))
                    throttle = float(cmd.get("throttle", 0.5))  # 0 to 1

                    # Clamp values
                    pitch = max(-1.0, min(1.0, pitch))
                    roll = max(-1.0, min(1.0, roll))
                    yaw = max(-1.0, min(1.0, yaw))
                    throttle = max(0.0, min(1.0, throttle))

                    # Send to drone
                    if self._drone and not self._sim_mode:
                        await self._drone.manual_control.set_manual_control_input(
                            pitch=pitch, roll=roll, yaw=yaw, throttle=throttle
                        )

                    self._last_manual_input_time = time.time()

                    logger.debug(
                        f"Manual control: P={pitch:.2f} R={roll:.2f} Y={yaw:.2f} T={throttle:.2f}"
                    )

                except queue.Empty:
                    await asyncio.sleep(0.02)  # 50 Hz polling

            except Exception as ex:
                logger.error("Manual control error: %s", ex)
                await asyncio.sleep(0.1)

    def enable_manual_control(self, token: Optional[str]) -> Dict[str, Any]:
        """Enable manual control mode with token validation."""
        if not self._validate_token(token):
            return self._error(
                "Manual control requires valid confirmation token. Request one with 'drone request token'."
            )

        try:
            from kilo_v2 import config as _cfg

            enabled = bool(getattr(_cfg, "DRONE_MANUAL_CONTROL_ENABLE", False))
        except Exception:
            enabled = False

        if not enabled:
            return self._error(
                "Manual control disabled in configuration. Set DRONE_MANUAL_CONTROL_ENABLE=true"
            )

        if not self._event_loop or not self._drone:
            return self._error("Drone not connected.")

        self._manual_control_enabled = True
        self._last_manual_input_time = time.time()

        # Start manual control loop if not already running
        if (
            not self._manual_control_thread
            or not self._manual_control_thread.is_alive()
        ):
            asyncio.run_coroutine_threadsafe(
                self._manual_control_loop_async(), self._event_loop
            )

        self._log_event_safely("drone_manual_control_enabled", {"sim": self._sim_mode})

        return {
            "type": "tool_result",
            "tool": self.get_name(),
            "content": {
                "status": "manual_control_enabled",
                "simulation": self._sim_mode,
                "deadman_timeout": getattr(self, "_deadman_timeout", 2.0),
                "note": "Send control inputs via WebSocket or API with pitch, roll, yaw, throttle",
            },
        }

    def disable_manual_control(self) -> Dict[str, Any]:
        """Disable manual control mode (emergency stop)."""
        self._manual_control_enabled = False
        self._log_event_safely("drone_manual_control_disabled", {"sim": self._sim_mode})

        return {
            "type": "tool_result",
            "tool": self.get_name(),
            "content": {
                "status": "manual_control_disabled",
                "simulation": self._sim_mode,
            },
        }

    def queue_manual_control(
        self, pitch: float, roll: float, yaw: float, throttle: float
    ) -> None:
        """Queue manual control input (called by WebSocket handler)."""
        if self._manual_control_enabled:
            self._manual_control_queue.put(
                {"pitch": pitch, "roll": roll, "yaw": yaw, "throttle": throttle}
            )
            self._last_manual_input_time = time.time()


def create_plugin() -> BasePlugin:
    return DroneControl()
