#!/usr/bin/env python3
"""
Quick-start configuration script for external cameras.

This script helps you configure all external cameras with appropriate
labels, positions, and angles.

Usage:
    python configure_cameras.py --config kitchen,bedroom,desk,living_room
    python configure_cameras.py --detect-only
    python configure_cameras.py --help
"""

import argparse
import sys
import httpx
from typing import List, Dict

# Default camera configurations for common setups
PRESET_CONFIGS = {
    "fall_detection": [
        {"label": "overhead", "position": "ceiling_corner", "angle": "top_down"},
        {"label": "side_view", "position": "wall_side", "angle": "side_view"},
        {"label": "front_view", "position": "wall_front", "angle": "front_view"},
    ],
    "posture_monitoring": [
        {"label": "desk_side", "position": "desk_side", "angle": "side_view"},
        {"label": "desk_front", "position": "monitor_top", "angle": "front_view"},
    ],
    "room_coverage": [
        {"label": "kitchen", "position": "ceiling_corner", "angle": "top_down"},
        {"label": "bedroom", "position": "wall_side", "angle": "side_view"},
        {"label": "desk", "position": "monitor_top", "angle": "front_view"},
        {"label": "living_room", "position": "wall_corner", "angle": "wide_angle"},
    ],
}


class CameraConfigurator:
    def __init__(self, base_url: str = "http://localhost:9007"):
        self.base_url = base_url
        self.client = httpx.Client(timeout=10.0)

    def detect_cameras(self) -> List[int]:
        """Detect all available cameras"""
        try:
            response = self.client.get(f"{self.base_url}/external_cameras/detect")
            response.raise_for_status()
            data = response.json()
            return data["detected_cameras"]
        except Exception as e:
            print(f"Error detecting cameras: {e}")
            return []

    def add_camera(
        self,
        camera_id: int,
        label: str,
        position: str = "unknown",
        angle: str = "unknown",
        width: int = 1280,
        height: int = 720,
        fps: int = 15
    ) -> bool:
        """Add and configure a camera"""
        try:
            response = self.client.post(
                f"{self.base_url}/external_cameras/add",
                params={
                    "camera_id": camera_id,
                    "label": label,
                    "position": position,
                    "angle": angle,
                    "width": width,
                    "height": height,
                    "fps": fps,
                }
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error adding camera {camera_id}: {e}")
            return False

    def start_cameras(self) -> bool:
        """Start all configured cameras"""
        try:
            response = self.client.post(f"{self.base_url}/external_cameras/start")
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error starting cameras: {e}")
            return False

    def get_status(self) -> Dict:
        """Get status of all cameras"""
        try:
            response = self.client.get(f"{self.base_url}/external_cameras/status")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting status: {e}")
            return {}


def main():
    parser = argparse.ArgumentParser(
        description="Configure external cameras for Kilo AI monitoring system"
    )
    parser.add_argument(
        "--preset",
        choices=["fall_detection", "posture_monitoring", "room_coverage", "custom"],
        default="room_coverage",
        help="Preset configuration to use"
    )
    parser.add_argument(
        "--labels",
        type=str,
        help="Comma-separated camera labels (e.g., 'kitchen,bedroom,desk,living_room')"
    )
    parser.add_argument(
        "--detect-only",
        action="store_true",
        help="Only detect cameras without configuring them"
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default="http://localhost:9007",
        help="Base URL of camera service"
    )
    parser.add_argument(
        "--resolution",
        type=str,
        default="1280x720",
        help="Camera resolution (e.g., '1920x1080', '1280x720')"
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=15,
        help="Frames per second"
    )

    args = parser.parse_args()

    # Parse resolution
    width, height = map(int, args.resolution.split('x'))

    configurator = CameraConfigurator(base_url=args.base_url)

    # Detect available cameras
    print("🔍 Detecting cameras...")
    detected_cameras = configurator.detect_cameras()

    if not detected_cameras:
        print("❌ No cameras detected. Please check:")
        print("   1. USB cameras are connected")
        print("   2. Camera service is running")
        print("   3. /dev/video* devices are accessible")
        sys.exit(1)

    print(f"✅ Found {len(detected_cameras)} camera(s): {detected_cameras}")

    if args.detect_only:
        print("\nDetected cameras:")
        for cam_id in detected_cameras:
            print(f"  - /dev/video{cam_id}")
        sys.exit(0)

    # Get configuration
    if args.labels:
        # Custom labels provided
        labels = args.labels.split(',')
        configs = [
            {"label": label.strip(), "position": "unknown", "angle": "unknown"}
            for label in labels
        ]
    elif args.preset in PRESET_CONFIGS:
        # Use preset configuration
        configs = PRESET_CONFIGS[args.preset]
    else:
        print("❌ Invalid preset or no labels provided")
        sys.exit(1)

    # Ensure we have enough cameras
    if len(detected_cameras) < len(configs):
        print(f"⚠️  Warning: Need {len(configs)} cameras but only {len(detected_cameras)} detected")
        print("   Configuring only the available cameras")
        configs = configs[:len(detected_cameras)]

    # Configure each camera
    print(f"\n⚙️  Configuring {len(configs)} camera(s) with preset '{args.preset}'...")
    for i, config in enumerate(configs):
        camera_id = detected_cameras[i]
        label = config["label"]
        position = config["position"]
        angle = config["angle"]

        print(f"   Camera {camera_id}: {label} ({position}, {angle})")

        success = configurator.add_camera(
            camera_id=camera_id,
            label=label,
            position=position,
            angle=angle,
            width=width,
            height=height,
            fps=args.fps
        )

        if success:
            print(f"   ✅ Camera {camera_id} configured successfully")
        else:
            print(f"   ❌ Failed to configure camera {camera_id}")

    # Start cameras
    print("\n🚀 Starting cameras...")
    if configurator.start_cameras():
        print("✅ All cameras started successfully")
    else:
        print("❌ Failed to start cameras")
        sys.exit(1)

    # Show status
    print("\n📊 Camera Status:")
    status = configurator.get_status()
    if status:
        print(f"   Running: {status.get('running', False)}")
        print(f"   Total cameras: {status.get('total_cameras', 0)}")
        print("\n   Individual cameras:")
        for cam_id, cam_status in status.get('cameras', {}).items():
            print(f"      Camera {cam_id} ({cam_status['label']}):")
            print(f"         Position: {cam_status['position']}")
            print(f"         Angle: {cam_status['angle']}")
            print(f"         Resolution: {cam_status['resolution'][0]}x{cam_status['resolution'][1]}")
            print(f"         FPS: {cam_status['fps']}")
            print(f"         Frames captured: {cam_status['frame_count']}")
            print(f"         Status: {'Active' if cam_status['has_latest_frame'] else 'No frames yet'}")
    else:
        print("   ❌ Could not retrieve status")

    print("\n✨ Configuration complete!")
    print("\n💡 Next steps:")
    print("   - Test fall detection: curl -X POST http://localhost:9007/external_cameras/analyze/fall_detection")
    print("   - Test posture analysis: curl -X POST http://localhost:9007/external_cameras/analyze/posture")
    print("   - Get synchronized frames: curl http://localhost:9007/external_cameras/frames/synchronized")
    print("   - View camera status: curl http://localhost:9007/external_cameras/status")


if __name__ == "__main__":
    main()
