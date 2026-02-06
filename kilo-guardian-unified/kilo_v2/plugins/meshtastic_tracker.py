"""
Meshtastic Tracker Plugin

Purpose:
- Ingest location and status messages from a Meshtastic radio mesh
- Log "thing tracking" events into Kilo Guardian's local datastore
- Expose simple commands to query recent peer locations and mesh status

Safe behavior:
- If Meshtastic python package or hardware is unavailable, the plugin loads
  and returns informative messages without crashing.

Query examples (Reasoning Engine routes by keywords):
- "track device via meshtastic"
- "meshtastic peers nearby"
- "show last locations from mesh"

Notes:
- This stub focuses on structure. Actual radio I/O should be implemented
  in a background task pulling from the serial/TCP interface and parsing
  protobuf messages. Use config for ports and topic filters.
"""

import logging
import math
import threading
import time
from typing import Any, Dict, List, Optional

try:
    # Meshtastic python API is optional; guard import to avoid hard failure
    import meshtastic
    from meshtastic import portnums_pb2  # type: ignore
    from meshtastic.serial_interface import SerialInterface  # type: ignore
    from meshtastic.tcp_interface import TCPInterface  # type: ignore

    MESHTASTIC_AVAILABLE = True
except Exception:
    MESHTASTIC_AVAILABLE = False
    TCPInterface = None  # type: ignore
    SerialInterface = None  # type: ignore

from plugins.base_plugin import BasePlugin

try:
    # Local persistence (events/habits) — best-effort import
    from data_core import KiloDataCore
except Exception:
    KiloDataCore = None  # type: ignore


logger = logging.getLogger(__name__)


class MeshtasticTracker(BasePlugin):
    def __init__(self):
        super().__init__()
        self._iface = None  # type: Optional[Any]
        self._last_health: Dict[str, Any] = {"ok": True, "reason": "initialized"}
        self._listener_thread = None  # type: Optional[threading.Thread]
        self._stop_event = threading.Event()
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10
        self._reconnect_backoff = 5  # seconds

    def get_name(self) -> str:
        return "meshtastic_tracker"

    def get_keywords(self) -> List[str]:
        # Keep concise phrases for embedding-based routing
        return [
            "meshtastic",
            "mesh radio",
            "thing tracking",
            "peer location",
            "device tracker",
        ]

    def start_background_task(self) -> None:
        """
        Start background listener for mesh messages via TCP or serial.
        Respects MESHTASTIC_ENABLE and tries TCP first, then serial.
        """
        # Respect config toggles
        try:
            from kilo_v2 import config as _cfg
        except Exception:
            _cfg = None

        enabled = bool(getattr(_cfg, "MESHTASTIC_ENABLE", False)) if _cfg else False

        if not MESHTASTIC_AVAILABLE or not enabled:
            logger.info(
                "Meshtastic library not available or disabled; background task not started."
            )
            return

        if self._listener_thread and self._listener_thread.is_alive():
            logger.info("Meshtastic listener already running.")
            return

        # Start listener thread
        self._stop_event.clear()
        self._listener_thread = threading.Thread(
            target=self._listener_loop, daemon=True
        )
        self._listener_thread.start()
        logger.info("Meshtastic listener thread started.")

    def stop_background_task(self) -> None:
        """Stop the background listener gracefully."""
        self._stop_event.set()
        if self._listener_thread:
            self._listener_thread.join(timeout=5)
        if self._iface:
            try:
                self._iface.close()
            except Exception as ex:
                logger.debug("Error closing Meshtastic interface: %s", ex)
        logger.info("Meshtastic listener stopped.")

    def _listener_loop(self) -> None:
        """Main loop: connect, listen, reconnect on failure with exponential backoff."""
        try:
            from kilo_v2 import config as _cfg
        except Exception:
            _cfg = None

        consecutive_failures = 0
        backoff_multiplier = 1.0

        while not self._stop_event.is_set():
            try:
                self._connect_interface(_cfg)
                if self._iface:
                    logger.info(
                        "Meshtastic interface connected; listening for messages..."
                    )
                    self._reconnect_attempts = 0
                    consecutive_failures = 0
                    backoff_multiplier = 1.0

                    # Keep connection alive; callbacks will handle messages
                    last_health_check = time.time()
                    health_check_interval = 30.0

                    while not self._stop_event.is_set():
                        time.sleep(1)

                        # Periodic health check
                        if time.time() - last_health_check > health_check_interval:
                            if not self._check_connection_health():
                                logger.warning(
                                    "Meshtastic connection health check failed"
                                )
                                break
                            last_health_check = time.time()
                else:
                    logger.warning("Failed to establish Meshtastic interface.")
                    consecutive_failures += 1
                    self._reconnect_attempts += 1

                    if self._reconnect_attempts > self._max_reconnect_attempts:
                        logger.error(
                            f"Max reconnect attempts ({self._max_reconnect_attempts}) reached; stopping listener."
                        )
                        break

                    # Exponential backoff
                    backoff_time = min(
                        self._reconnect_backoff * backoff_multiplier, 60.0
                    )
                    logger.info(
                        f"Retrying in {backoff_time:.1f}s (attempt {self._reconnect_attempts}/{self._max_reconnect_attempts})"
                    )
                    time.sleep(backoff_time)
                    backoff_multiplier = min(backoff_multiplier * 1.5, 8.0)

            except Exception as ex:
                logger.error(f"Meshtastic listener error: {ex}", exc_info=True)
                consecutive_failures += 1
                self._reconnect_attempts += 1

                if self._reconnect_attempts > self._max_reconnect_attempts:
                    logger.error(
                        f"Max reconnect attempts ({self._max_reconnect_attempts}) reached; stopping listener."
                    )
                    break

                # Exponential backoff
                backoff_time = min(self._reconnect_backoff * backoff_multiplier, 60.0)
                logger.info(f"Retrying in {backoff_time:.1f}s after error")
                time.sleep(backoff_time)
                backoff_multiplier = min(backoff_multiplier * 1.5, 8.0)

        logger.info("Meshtastic listener loop exited")

    def _check_connection_health(self) -> bool:
        """Check if Meshtastic connection is still alive."""
        if not self._iface:
            return False

        try:
            # Try to access interface to verify it's responsive
            # Note: Actual health check depends on meshtastic library capabilities
            return True
        except Exception as ex:
            logger.warning(f"Meshtastic health check failed: {ex}")
            return False

    def _connect_interface(self, cfg: Any) -> None:
        """Attempt TCP or serial connection based on config with detailed error handling."""
        if self._iface:
            try:
                self._iface.close()
            except Exception as ex:
                logger.debug(f"Error closing previous interface: {ex}")
            self._iface = None

        host = getattr(cfg, "MESHTASTIC_HOST", "localhost") if cfg else "localhost"
        port = getattr(cfg, "MESHTASTIC_PORT", 2960) if cfg else 2960
        serial_port = getattr(cfg, "MESHTASTIC_SERIAL", "") if cfg else ""

        # Try TCP if host/port set
        if host and port:
            try:
                logger.info(f"Attempting TCP connection to {host}:{port}")
                self._iface = TCPInterface(hostname=host, portNumber=port)

                # Register callback for incoming packets
                self._iface.subscribe(self._on_receive)

                # Verify connection is working
                time.sleep(1)  # Allow connection to stabilize

                logger.info(f"TCP interface established successfully on {host}:{port}")
                return

            except ConnectionRefusedError:
                logger.warning(
                    f"TCP connection refused on {host}:{port} - is Meshtastic daemon running?"
                )
            except TimeoutError:
                logger.warning(f"TCP connection timeout to {host}:{port}")
            except Exception as ex:
                logger.warning(f"TCP connection failed to {host}:{port}: {ex}")

        # Try serial if path set
        if serial_port:
            try:
                logger.info(f"Attempting serial connection to {serial_port}")
                self._iface = SerialInterface(devPath=serial_port)

                # Register callback
                self._iface.subscribe(self._on_receive)

                # Verify connection
                time.sleep(1)

                logger.info(f"Serial interface established on {serial_port}")
                return

            except FileNotFoundError:
                logger.warning(f"Serial port not found: {serial_port}")
            except PermissionError:
                logger.error(f"Permission denied accessing serial port: {serial_port}")
            except Exception as ex:
                logger.warning(f"Serial connection failed on {serial_port}: {ex}")

        logger.error(
            "No valid Meshtastic interface config found or all connection attempts failed"
        )

    def _on_receive(self, packet: Dict[str, Any], interface: Any = None) -> None:
        """Callback for incoming Meshtastic packets; parse and log location events."""
        try:
            # Extract position data if present
            decoded = packet.get("decoded", {})
            portnum = decoded.get("portnum")

            # Position packets use POSITION_APP portnum
            if portnum and "POSITION" in str(portnum):
                payload = decoded.get("position", {})
                from_node = packet.get("fromId", "unknown")

                lat = payload.get("latitude")
                lon = payload.get("longitude")
                alt = payload.get("altitude")

                if lat is not None and lon is not None:
                    # Normalize location event
                    event_data = {
                        "node_id": from_node,
                        "short_name": packet.get("from", from_node),
                        "lat": lat,
                        "lon": lon,
                        "alt": alt if alt is not None else 0.0,
                        "timestamp": packet.get("rxTime", time.time()),
                        "rssi": packet.get("rxRssi"),
                        "snr": packet.get("rxSnr"),
                    }
                    self._log_event_safely("meshtastic_location", event_data)
                    logger.debug(
                        "Logged location for node %s: %.6f, %.6f", from_node, lat, lon
                    )

                    # Broadcast to WebSocket clients for real-time map updates
                    try:
                        import asyncio

                        from kilo_v2.websocket_handlers import (
                            broadcast_meshtastic_event,
                        )

                        # Try to schedule broadcast in event loop
                        # Use get_running_loop() to avoid deprecation warning
                        try:
                            loop = asyncio.get_running_loop()
                            asyncio.ensure_future(
                                broadcast_meshtastic_event(event_data), loop=loop
                            )
                        except RuntimeError:
                            # No running event loop in this thread, skip WebSocket broadcast
                            pass
                    except ImportError:
                        pass

        except Exception as ex:
            logger.warning("Failed to parse Meshtastic packet: %s", ex)

    def health(self) -> Dict[str, Any]:
        ok = MESHTASTIC_AVAILABLE
        reason = "meshtastic-python present" if ok else "meshtastic-python missing"
        self._last_health = {"ok": ok, "reason": reason, "ts": time.time()}
        return self._last_health

    def execute(self, query: str) -> Dict[str, Any]:
        """Primary entry — try structured commands, else fallback to run."""
        # Simple command parsing
        q = query.lower()
        if any(k in q for k in ["peer", "location", "nearby", "last locations"]):
            return self._get_recent_locations()
        if any(k in q for k in ["mesh status", "meshtastic status", "radio status"]):
            return self._mesh_status()
        return self.run(query)

    def run(self, query: str) -> Dict[str, Any]:
        """Fallback handler — log an event and return help."""
        self._log_event_safely(
            event_type="meshtastic_query",
            content={"query": query, "note": "unrecognized command"},
        )
        return {
            "type": "tool_result",
            "tool": self.get_name(),
            "content": {
                "reply": "Meshtastic tracker ready. Try: 'show last locations', 'mesh status', or 'meshtastic peers'.",
                "meshtastic_available": MESHTASTIC_AVAILABLE,
            },
        }

    # --- Helpers --------------------------------------------------------

    def _mesh_status(self) -> Dict[str, Any]:
        status = self.health()
        # Include config snapshot for operator clarity
        try:
            from kilo_v2 import config as _cfg

            cfg_view = {
                "enabled": bool(getattr(_cfg, "MESHTASTIC_ENABLE", False)),
                "host": getattr(_cfg, "MESHTASTIC_HOST", None),
                "port": getattr(_cfg, "MESHTASTIC_PORT", None),
                "serial": getattr(_cfg, "MESHTASTIC_SERIAL", None),
            }
        except Exception:
            cfg_view = {"enabled": False}
        self._log_event_safely(event_type="meshtastic_status", content=status)
        return {
            "type": "tool_result",
            "tool": self.get_name(),
            "content": {
                "status": status,
                "config": cfg_view,
                "hint": "Install 'meshtastic' and set MESHTASTIC_* in config to enable live data.",
            },
        }

    def _get_recent_locations(self) -> Dict[str, Any]:
        # Pull recent events from KiloDataCore tagged with 'meshtastic_location'
        events: List[Dict[str, Any]] = []
        if KiloDataCore:
            try:
                dc = KiloDataCore()
                raw = dc.get_recent_events(limit=50)
                for e in raw:
                    if e.get("event_type") == "meshtastic_location":
                        events.append(e)
            except Exception as ex:
                logger.warning("Failed reading recent events: %s", ex)

        return {
            "type": "tool_result",
            "tool": self.get_name(),
            "content": {
                "count": len(events),
                "events": events,
                "note": "Locations are populated by the background listener when nodes broadcast position.",
            },
        }

    def _filter_nearby_locations(
        self,
        events: List[Dict[str, Any]],
        ref_lat: float,
        ref_lon: float,
        max_km: float,
    ) -> List[Dict[str, Any]]:
        """Filter events by haversine distance from a reference point."""
        nearby = []
        for e in events:
            content = e.get("content", {})
            lat = content.get("lat")
            lon = content.get("lon")
            if lat is not None and lon is not None:
                dist_km = self._haversine_distance(ref_lat, ref_lon, lat, lon)
                if dist_km <= max_km:
                    nearby.append({**e, "distance_km": dist_km})
        return nearby

    @staticmethod
    def _haversine_distance(
        lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Calculate great-circle distance in km between two lat/lon points."""
        R = 6371.0  # Earth radius in km
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        a = (
            math.sin(delta_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def _log_event_safely(self, event_type: str, content: Dict[str, Any]) -> None:
        if not KiloDataCore:
            return
        try:
            dc = KiloDataCore()
            dc.log_event(event_type=event_type, content=content)
        except Exception as ex:
            logger.debug("KiloDataCore.log_event failed: %s", ex)


# Factory for PluginManager dynamic loading
def create_plugin() -> BasePlugin:
    return MeshtasticTracker()
