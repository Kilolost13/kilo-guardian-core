"""
Local-only camera snapshots + AI activity recognition (detects activities for TBI users).

Integrates MediaPipe Pose activity recognition to track:
- Medication taking
- Eating/drinking
- Sleeping/resting
- Daily activities (sitting, standing, walking)
- Cooking and personal care

Activities are logged to memory core for "What did I do today?" queries.
"""

import logging
import os
import threading
import time
from datetime import datetime
from typing import Optional

# Assuming BasePlugin is in a sibling directory (plugins) relative to kilo_v2,
# and camera_monitor is in kilo_v2/memory_core.
# This relative import might need adjustment depending on how the
# system path is set up when running.
# A more robust solution might be to ensure kilo_v2 is on the Python path.
# For now, let's assume `kilo_v2.plugins.base_plugin` can be imported.
try:
    from kilo_v2.plugins.base_plugin import BasePlugin
except ImportError:
    # Fallback for direct execution/testing if kilo_v2 is not a package
    import sys

    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
    from plugins.base_plugin import BasePlugin

# Import AI activity recognition
try:
    from kilo_v2.ai_activity_recognition import get_ai_activity_model

    ACTIVITY_RECOGNITION_AVAILABLE = True
except ImportError:
    ACTIVITY_RECOGNITION_AVAILABLE = False
    logging.warning("AI Activity Recognition not available")

# Import memory DB for activity logging
try:
    from kilo_v2.memory_core.db import get_memory_db

    MEMORY_DB_AVAILABLE = True
except ImportError:
    MEMORY_DB_AVAILABLE = False
    logging.warning("Memory DB not available for activity logging")

# Import cv2 for camera capture
try:
    import cv2

    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logging.warning("OpenCV not available. Camera capture disabled.")


logger = logging.getLogger("CameraMonitorPlugin")


class CameraMonitorPlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.is_monitoring = False
        self.monitor_thread = None
        self.camera_index = int(os.getenv("CAMERA_INDEX", 0))
        self.camera_fps = int(os.getenv("CAMERA_FPS", 5))
        self.camera_resolution = tuple(
            map(int, os.getenv("CAMERA_RESOLUTION", "640,480").split(","))
        )
        self.snapshot_dir = os.getenv(
            "CAMERA_SNAPSHOT_DIR", "kilo_data/camera_snapshots"
        )
        os.makedirs(self.snapshot_dir, exist_ok=True)

        # Activity recognition state
        self.activity_model = None
        self.last_logged_activity = None
        self.last_activity_time = None
        self.activity_log_cooldown = int(os.getenv("ACTIVITY_LOG_COOLDOWN_SECONDS", 60))

        # Initialize activity recognition if available
        if ACTIVITY_RECOGNITION_AVAILABLE:
            try:
                self.activity_model = get_ai_activity_model()
                self.log_info("AI Activity Recognition initialized")
            except Exception as e:
                self.log_info(f"Failed to initialize activity recognition: {e}")
                self.activity_model = None

        self.log_info(
            f"CameraMonitorPlugin initialized. Snapshots dir: {self.snapshot_dir}, "
            f"Activity recognition: {'enabled' if self.activity_model else 'disabled'}"
        )

    def get_name(self) -> str:
        return "Camera Monitor"

    def get_keywords(self) -> list[str]:
        return ["camera", "monitor", "snapshot", "surveillance", "security"]

    def run(self, query: str) -> dict:
        # This plugin primarily runs in the background.
        # 'run' could be used for on-demand actions or status checks.
        if "status" in query.lower():
            return self.health()
        elif "take snapshot" in query.lower() or "take photo" in query.lower():
            # In a real implementation, this would trigger an an immediate snapshot
            # For now, it's just a placeholder.
            self.log_info("Command received to take an immediate snapshot.")
            return {
                "status": "success",
                "message": "Triggered immediate snapshot (functionality not fully implemented yet).",
            }
        else:
            return {
                "status": "info",
                "message": "Camera Monitor is running in the background. Ask for 'status' or 'take snapshot'.",
            }

    def start_background_task(self):
        """
        Starts the background camera monitoring thread.
        """
        if not self.is_monitoring:
            self.is_monitoring = True
            self.monitor_thread = threading.Thread(
                target=self._monitor_loop, daemon=True
            )
            self.monitor_thread.start()
            self.log_info("Camera monitoring background task started.")
        else:
            self.log_info("Camera monitoring background task is already running.")

    def _monitor_loop(self):
        """
        The main loop for background camera monitoring with AI activity recognition.

        Captures frames from camera, runs activity detection, and logs activities to memory core.
        """
        self.log_info("Entering camera monitoring loop...")

        # Open camera if CV2 is available
        camera = None
        if CV2_AVAILABLE:
            try:
                camera = cv2.VideoCapture(self.camera_index)
                camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_resolution[0])
                camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_resolution[1])
                self.log_info(
                    f"Camera opened: index={self.camera_index}, resolution={self.camera_resolution}"
                )
            except Exception as e:
                self.log_info(f"Failed to open camera: {e}")
                camera = None

        while self.is_monitoring:
            try:
                # Capture and process frame if camera and activity model are available
                if camera and self.activity_model:
                    ret, frame = camera.read()
                    if ret:
                        # Run activity recognition
                        result = self.activity_model.predict_activity_with_confidence(
                            frame
                        )
                        activity = result.get("activity", "unknown")
                        confidence = result.get("confidence", 0)

                        # Log activity if confidence is high enough
                        if confidence >= 60:
                            self._log_activity_if_changed(activity, confidence)
                    else:
                        self.log_info("Failed to capture frame from camera")
                        time.sleep(5)  # Wait before retrying
                        continue

                    # Sleep to maintain desired FPS
                    time.sleep(1.0 / self.camera_fps)
                else:
                    # No camera or activity model - just sleep
                    self.log_info(
                        "Camera monitoring idle (no camera or activity model)"
                    )
                    time.sleep(30)

            except Exception as e:
                self.log_info(f"Error in camera monitoring loop: {e}", exc_info=True)
                time.sleep(5)

        # Clean up camera
        if camera:
            camera.release()
            self.log_info("Camera released")

        self.log_info("Exiting camera monitoring loop.")

    def _log_activity_if_changed(self, activity: str, confidence: int):
        """
        Log activity to memory core if it has changed or cooldown period has elapsed.

        De-duplication logic:
        - Only log if activity is different from last logged activity
        - OR if cooldown period has elapsed (default: 60 seconds)
        - Prevents spamming memory log with repeated activities

        Args:
            activity: Activity code (e.g., 'sitting', 'medication_taking')
            confidence: Confidence score (0-100)
        """
        now = datetime.now()

        # Check if activity has changed or cooldown has elapsed
        should_log = False
        if self.last_logged_activity != activity:
            # Activity changed - always log
            should_log = True
            reason = "activity changed"
        elif self.last_activity_time is None:
            # First activity detection - always log
            should_log = True
            reason = "first detection"
        elif (
            now - self.last_activity_time
        ).total_seconds() >= self.activity_log_cooldown:
            # Cooldown elapsed - log to confirm user still doing same activity
            should_log = True
            reason = "cooldown elapsed"

        if should_log:
            # Get human-readable activity name
            activity_name = self.activity_model.get_activity_name(activity)

            # Log to memory core
            if MEMORY_DB_AVAILABLE:
                try:
                    db = get_memory_db()
                    event_text = f"User {activity_name.lower()}"
                    db.add_memory_event(event_text=event_text, event_type="activity")
                    self.log_info(
                        f"Logged activity: {activity_name} ({confidence}% confidence, {reason})"
                    )

                    # Update tracking state
                    self.last_logged_activity = activity
                    self.last_activity_time = now
                except Exception as e:
                    self.log_info(f"Failed to log activity to memory core: {e}")
            else:
                # Memory DB not available - just log to console
                self.log_info(
                    f"Activity detected: {activity_name} ({confidence}% confidence) - "
                    f"Memory DB not available for logging"
                )
                self.last_logged_activity = activity
                self.last_activity_time = now

    def health(self) -> dict:
        """
        Reports the health status of the camera monitor.
        """
        if (
            self.is_monitoring
            and self.monitor_thread
            and self.monitor_thread.is_alive()
        ):
            return {"status": "ok", "message": "Camera monitoring is active."}
        else:
            return {
                "status": "warning",
                "message": "Camera monitoring is not active or thread has stopped.",
            }
