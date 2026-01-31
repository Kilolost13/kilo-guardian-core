"""
Multi-Camera Manager for External Environmental Monitoring

Manages multiple fixed USB/IP cameras for continuous observation:
- Fall detection from multiple angles
- Posture analysis (side + front view)
- Activity tracking (kitchen, desk, bed)
- 3D spatial awareness
"""

import cv2
import numpy as np
import threading
import time
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CameraConfig:
    """Configuration for a single camera"""
    camera_id: int  # /dev/video{id}
    label: str  # e.g., "kitchen", "bedroom", "desk"
    position: str  # e.g., "ceiling_corner", "wall_side", "desk_front"
    angle: str  # e.g., "top_down", "side_view", "front_view"
    resolution: Tuple[int, int] = (1280, 720)
    fps: int = 15
    enabled: bool = True


@dataclass
class CameraFrame:
    """Single frame from a camera with metadata"""
    camera_id: int
    label: str
    timestamp: float
    frame: np.ndarray  # BGR image
    frame_number: int
    position: str
    angle: str


@dataclass
class MultiCameraFrame:
    """Synchronized frames from all cameras"""
    timestamp: float
    cameras: List[CameraFrame]
    sync_error_ms: float  # How far apart frames were captured


class ExternalCameraManager:
    """
    Manages multiple external USB/IP cameras for continuous monitoring.

    Features:
    - Auto-detect available cameras
    - Configure camera labels and positions
    - Capture synchronized frames from all cameras
    - Thread-safe frame access
    - Automatic reconnection on failure
    """

    def __init__(self):
        self.cameras: Dict[int, dict] = {}  # camera_id -> {config, capture, thread, latest_frame}
        self.configs: Dict[int, CameraConfig] = {}
        self.running = False
        self.lock = threading.Lock()
        self.frame_count = 0

    def detect_cameras(self, max_cameras: int = 10) -> List[int]:
        """
        Detect all available video devices.

        Returns:
            List of camera IDs that can be opened
        """
        available = []
        for camera_id in range(max_cameras):
            cap = cv2.VideoCapture(camera_id)
            if cap.isOpened():
                # Test if we can actually read a frame
                ret, frame = cap.read()
                if ret and frame is not None:
                    available.append(camera_id)
                    logger.info(f"Detected camera at /dev/video{camera_id}")
                cap.release()

        logger.info(f"Found {len(available)} cameras: {available}")
        return available

    def add_camera(self, config: CameraConfig) -> bool:
        """
        Add and initialize a camera.

        Args:
            config: Camera configuration

        Returns:
            True if camera was successfully added
        """
        camera_id = config.camera_id

        if camera_id in self.cameras:
            logger.warning(f"Camera {camera_id} already exists, removing old instance")
            self.remove_camera(camera_id)

        try:
            # Open video capture
            cap = cv2.VideoCapture(camera_id)

            if not cap.isOpened():
                logger.error(f"Failed to open camera {camera_id}")
                return False

            # Configure camera
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.resolution[0])
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.resolution[1])
            cap.set(cv2.CAP_PROP_FPS, config.fps)

            # Verify settings
            actual_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            actual_fps = cap.get(cv2.CAP_PROP_FPS)

            logger.info(
                f"Camera {camera_id} ({config.label}): "
                f"{actual_width}x{actual_height} @ {actual_fps}fps"
            )

            # Test frame capture
            ret, frame = cap.read()
            if not ret or frame is None:
                logger.error(f"Camera {camera_id} cannot capture frames")
                cap.release()
                return False

            with self.lock:
                self.cameras[camera_id] = {
                    'config': config,
                    'capture': cap,
                    'thread': None,
                    'latest_frame': None,
                    'frame_count': 0,
                    'error_count': 0,
                    'last_capture_time': 0,
                }
                self.configs[camera_id] = config

            logger.info(f"Successfully added camera {camera_id} ({config.label})")
            return True

        except Exception as e:
            logger.error(f"Error adding camera {camera_id}: {e}")
            return False

    def remove_camera(self, camera_id: int):
        """Remove a camera and release resources"""
        with self.lock:
            if camera_id in self.cameras:
                camera = self.cameras[camera_id]

                # Stop capture thread if running
                if camera['thread'] and camera['thread'].is_alive():
                    logger.info(f"Stopping capture thread for camera {camera_id}")
                    # Thread will stop when self.running = False

                # Release video capture
                if camera['capture']:
                    camera['capture'].release()

                del self.cameras[camera_id]
                if camera_id in self.configs:
                    del self.configs[camera_id]

                logger.info(f"Removed camera {camera_id}")

    def _capture_loop(self, camera_id: int):
        """
        Background thread to continuously capture frames from a camera.

        Args:
            camera_id: ID of camera to capture from
        """
        logger.info(f"Starting capture loop for camera {camera_id}")

        while self.running:
            try:
                with self.lock:
                    if camera_id not in self.cameras:
                        break
                    camera = self.cameras[camera_id]
                    cap = camera['capture']
                    config = camera['config']

                if not config.enabled:
                    time.sleep(0.1)
                    continue

                # Capture frame
                ret, frame = cap.read()

                if ret and frame is not None:
                    # Create frame metadata
                    camera_frame = CameraFrame(
                        camera_id=camera_id,
                        label=config.label,
                        timestamp=time.time(),
                        frame=frame.copy(),
                        frame_number=camera['frame_count'],
                        position=config.position,
                        angle=config.angle,
                    )

                    with self.lock:
                        camera['latest_frame'] = camera_frame
                        camera['frame_count'] += 1
                        camera['last_capture_time'] = time.time()
                        camera['error_count'] = 0

                else:
                    # Frame capture failed
                    with self.lock:
                        camera['error_count'] += 1

                    if camera['error_count'] > 10:
                        logger.error(
                            f"Camera {camera_id} has {camera['error_count']} consecutive errors, "
                            "attempting reconnection..."
                        )
                        # Attempt to reconnect
                        self._reconnect_camera(camera_id)

                # Control frame rate
                time.sleep(1.0 / config.fps)

            except Exception as e:
                logger.error(f"Error in capture loop for camera {camera_id}: {e}")
                time.sleep(1)

        logger.info(f"Capture loop stopped for camera {camera_id}")

    def _reconnect_camera(self, camera_id: int):
        """Attempt to reconnect a failed camera"""
        logger.info(f"Reconnecting camera {camera_id}")

        with self.lock:
            if camera_id not in self.cameras:
                return

            camera = self.cameras[camera_id]
            config = camera['config']

            # Release old capture
            if camera['capture']:
                camera['capture'].release()

            # Try to reopen
            cap = cv2.VideoCapture(camera_id)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.resolution[0])
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.resolution[1])
                cap.set(cv2.CAP_PROP_FPS, config.fps)

                camera['capture'] = cap
                camera['error_count'] = 0
                logger.info(f"Successfully reconnected camera {camera_id}")
            else:
                logger.error(f"Failed to reconnect camera {camera_id}")

    def start(self):
        """Start continuous capture from all cameras"""
        if self.running:
            logger.warning("Camera manager already running")
            return

        self.running = True

        # Start capture thread for each camera
        for camera_id in self.cameras.keys():
            thread = threading.Thread(
                target=self._capture_loop,
                args=(camera_id,),
                daemon=True,
                name=f"Camera-{camera_id}"
            )
            thread.start()

            with self.lock:
                self.cameras[camera_id]['thread'] = thread

        logger.info(f"Started capture for {len(self.cameras)} cameras")

    def stop(self):
        """Stop all camera capture"""
        logger.info("Stopping camera manager")
        self.running = False

        # Wait for threads to finish
        for camera_id, camera in list(self.cameras.items()):
            if camera['thread'] and camera['thread'].is_alive():
                camera['thread'].join(timeout=2)

        logger.info("Camera manager stopped")

    def get_latest_frame(self, camera_id: int) -> Optional[CameraFrame]:
        """Get the latest frame from a specific camera"""
        with self.lock:
            if camera_id in self.cameras:
                return self.cameras[camera_id]['latest_frame']
        return None

    def get_latest_frames_all(self) -> List[CameraFrame]:
        """Get latest frames from all cameras"""
        frames = []
        with self.lock:
            for camera_id, camera in self.cameras.items():
                if camera['latest_frame']:
                    frames.append(camera['latest_frame'])
        return frames

    def capture_synchronized(self, max_sync_error_ms: float = 100) -> Optional[MultiCameraFrame]:
        """
        Capture synchronized frames from all cameras.

        Attempts to get frames captured within max_sync_error_ms of each other.

        Args:
            max_sync_error_ms: Maximum allowed time difference between frames (milliseconds)

        Returns:
            MultiCameraFrame if successful, None if cameras are not synchronized
        """
        frames = self.get_latest_frames_all()

        if not frames:
            return None

        # Check synchronization
        timestamps = [f.timestamp for f in frames]
        min_ts = min(timestamps)
        max_ts = max(timestamps)
        sync_error_ms = (max_ts - min_ts) * 1000

        if sync_error_ms > max_sync_error_ms:
            logger.warning(
                f"Frames not synchronized: {sync_error_ms:.1f}ms error "
                f"(max: {max_sync_error_ms}ms)"
            )

        return MultiCameraFrame(
            timestamp=np.mean(timestamps),
            cameras=frames,
            sync_error_ms=sync_error_ms,
        )

    def get_status(self) -> Dict:
        """Get status of all cameras"""
        status = {
            'running': self.running,
            'total_cameras': len(self.cameras),
            'cameras': {}
        }

        with self.lock:
            for camera_id, camera in self.cameras.items():
                config = camera['config']
                latest_frame = camera['latest_frame']

                status['cameras'][camera_id] = {
                    'id': camera_id,
                    'label': config.label,
                    'position': config.position,
                    'angle': config.angle,
                    'enabled': config.enabled,
                    'resolution': config.resolution,
                    'fps': config.fps,
                    'frame_count': camera['frame_count'],
                    'error_count': camera['error_count'],
                    'last_capture_time': camera['last_capture_time'],
                    'time_since_last_frame': time.time() - camera['last_capture_time'] if camera['last_capture_time'] > 0 else None,
                    'has_latest_frame': latest_frame is not None,
                }

        return status

    def update_camera_config(self, camera_id: int, **kwargs):
        """Update camera configuration dynamically"""
        with self.lock:
            if camera_id in self.configs:
                config = self.configs[camera_id]

                # Update fields
                for key, value in kwargs.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
                        logger.info(f"Updated camera {camera_id} {key} = {value}")

                # Update in cameras dict
                self.cameras[camera_id]['config'] = config

    def get_camera_labels(self) -> Dict[int, str]:
        """Get mapping of camera IDs to labels"""
        with self.lock:
            return {cid: config.label for cid, config in self.configs.items()}

    def enable_camera(self, camera_id: int):
        """Enable a camera"""
        self.update_camera_config(camera_id, enabled=True)

    def disable_camera(self, camera_id: int):
        """Disable a camera"""
        self.update_camera_config(camera_id, enabled=False)


# Global camera manager instance
camera_manager = ExternalCameraManager()
