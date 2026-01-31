#!/usr/bin/env python3
"""
Test script for external multi-camera monitoring system.

This script verifies that the camera system is working correctly by testing:
- Camera detection
- Frame capture from all cameras
- Synchronized frame capture
- Fall detection analysis
- Posture analysis

Usage:
    python test_cameras.py
    python test_cameras.py --save-frames
    python test_cameras.py --camera-id 0
"""

import argparse
import httpx
import time
import sys
from pathlib import Path
import base64


class CameraTester:
    def __init__(self, base_url: str = "http://localhost:9007"):
        self.base_url = base_url
        self.client = httpx.Client(timeout=30.0)

    def test_detection(self) -> bool:
        """Test camera detection"""
        print("\n🔍 Test 1: Camera Detection")
        print("-" * 50)
        try:
            response = self.client.get(f"{self.base_url}/external_cameras/detect")
            response.raise_for_status()
            data = response.json()

            cameras = data["detected_cameras"]
            count = data["count"]

            print(f"✅ Detection successful")
            print(f"   Found {count} camera(s): {cameras}")
            for cam_id in cameras:
                print(f"      - /dev/video{cam_id}")

            return count > 0
        except Exception as e:
            print(f"❌ Detection failed: {e}")
            return False

    def test_status(self) -> bool:
        """Test camera status endpoint"""
        print("\n📊 Test 2: Camera Status")
        print("-" * 50)
        try:
            response = self.client.get(f"{self.base_url}/external_cameras/status")
            response.raise_for_status()
            status = response.json()

            running = status.get("running", False)
            total = status.get("total_cameras", 0)

            print(f"✅ Status retrieved")
            print(f"   Running: {running}")
            print(f"   Total cameras: {total}")

            if total > 0:
                print("\n   Camera details:")
                for cam_id, cam_status in status.get("cameras", {}).items():
                    print(f"      Camera {cam_id} ({cam_status['label']}):")
                    print(f"         Position: {cam_status['position']}")
                    print(f"         Angle: {cam_status['angle']}")
                    print(f"         Enabled: {cam_status['enabled']}")
                    print(f"         Frames captured: {cam_status['frame_count']}")
                    print(f"         Errors: {cam_status['error_count']}")

                    if cam_status.get('time_since_last_frame') is not None:
                        print(f"         Last frame: {cam_status['time_since_last_frame']:.2f}s ago")

            return running and total > 0
        except Exception as e:
            print(f"❌ Status check failed: {e}")
            return False

    def test_individual_frame(self, camera_id: int, save_frame: bool = False) -> bool:
        """Test getting frame from individual camera"""
        print(f"\n📷 Test 3: Individual Frame Capture (Camera {camera_id})")
        print("-" * 50)
        try:
            response = self.client.get(f"{self.base_url}/external_cameras/{camera_id}/frame")
            response.raise_for_status()

            # Check headers
            headers = response.headers
            cam_label = headers.get("X-Camera-Label", "unknown")
            timestamp = headers.get("X-Timestamp", "unknown")

            print(f"✅ Frame captured successfully")
            print(f"   Camera label: {cam_label}")
            print(f"   Timestamp: {timestamp}")
            print(f"   Image size: {len(response.content)} bytes")

            if save_frame:
                output_path = Path(f"camera_{camera_id}_test.jpg")
                output_path.write_bytes(response.content)
                print(f"   💾 Saved to: {output_path}")

            return True
        except Exception as e:
            print(f"❌ Frame capture failed: {e}")
            return False

    def test_synchronized_frames(self) -> bool:
        """Test synchronized frame capture"""
        print("\n🎯 Test 4: Synchronized Frame Capture")
        print("-" * 50)
        try:
            response = self.client.get(
                f"{self.base_url}/external_cameras/frames/synchronized",
                params={"format": "json", "max_sync_error_ms": 100}
            )
            response.raise_for_status()
            data = response.json()

            timestamp = data["timestamp"]
            sync_error = data["sync_error_ms"]
            cam_count = data["camera_count"]
            cameras = data["cameras"]

            print(f"✅ Synchronized capture successful")
            print(f"   Cameras synchronized: {cam_count}")
            print(f"   Sync error: {sync_error:.2f}ms")
            print(f"   Average timestamp: {timestamp}")

            if sync_error > 100:
                print(f"   ⚠️  Warning: Sync error exceeds 100ms threshold")

            print("\n   Individual camera frames:")
            for cam in cameras:
                print(f"      Camera {cam['camera_id']} ({cam['label']}):")
                print(f"         Position: {cam['position']}")
                print(f"         Angle: {cam['angle']}")
                print(f"         Timestamp: {cam['timestamp']}")
                print(f"         Frame #: {cam['frame_number']}")

            return True
        except Exception as e:
            print(f"❌ Synchronized capture failed: {e}")
            return False

    def test_fall_detection(self) -> bool:
        """Test fall detection analysis"""
        print("\n🚨 Test 5: Fall Detection Analysis")
        print("-" * 50)
        try:
            response = self.client.post(
                f"{self.base_url}/external_cameras/analyze/fall_detection"
            )
            response.raise_for_status()
            data = response.json()

            fall_detected = data["fall_detected"]
            confidence = data["confidence"]
            cam_count = data["camera_count"]
            sync_error = data["sync_error_ms"]
            alert_level = data["alert_level"]
            pose_count = len(data.get("pose_data", []))

            print(f"✅ Fall detection analysis complete")
            print(f"   Cameras analyzed: {cam_count}")
            print(f"   Sync error: {sync_error:.2f}ms")
            print(f"   Fall detected: {fall_detected}")
            print(f"   Confidence: {confidence:.2f}")
            print(f"   Alert level: {alert_level}")
            print(f"   Pose data points: {pose_count}")

            if fall_detected:
                print("   ⚠️  FALL DETECTED - This would trigger an alert")
            else:
                print("   ✅ No fall detected - Normal status")

            return True
        except Exception as e:
            print(f"❌ Fall detection analysis failed: {e}")
            return False

    def test_posture_analysis(self) -> bool:
        """Test posture analysis"""
        print("\n🧍 Test 6: Posture Analysis")
        print("-" * 50)
        try:
            response = self.client.post(
                f"{self.base_url}/external_cameras/analyze/posture"
            )
            response.raise_for_status()
            data = response.json()

            posture_score = data.get("posture_score", 0)
            cam_count = data.get("camera_count", 0)
            posture_quality = data.get("posture_quality", "unknown")

            print(f"✅ Posture analysis complete")
            print(f"   Cameras analyzed: {cam_count}")
            print(f"   Posture score: {posture_score:.2f}/100")
            print(f"   Quality: {posture_quality}")

            if "recommendations" in data:
                print("\n   Recommendations:")
                for rec in data["recommendations"]:
                    print(f"      - {rec}")

            return True
        except Exception as e:
            print(f"❌ Posture analysis failed: {e}")
            return False

    def test_activity_detection(self) -> bool:
        """Test activity detection"""
        print("\n🏃 Test 7: Activity Detection")
        print("-" * 50)
        try:
            response = self.client.post(
                f"{self.base_url}/external_cameras/analyze/activity"
            )
            response.raise_for_status()
            data = response.json()

            primary_activity = data.get("primary_activity", "unknown")
            confidence = data.get("confidence", 0)
            cam_count = data.get("camera_count", 0)

            print(f"✅ Activity detection complete")
            print(f"   Cameras analyzed: {cam_count}")
            print(f"   Primary activity: {primary_activity}")
            print(f"   Confidence: {confidence:.2f}")

            if "detected_activities" in data:
                print("\n   All detected activities:")
                for activity, score in data["detected_activities"].items():
                    print(f"      - {activity}: {score:.2f}")

            return True
        except Exception as e:
            print(f"❌ Activity detection failed: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Test external multi-camera monitoring system"
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default="http://localhost:9007",
        help="Base URL of camera service"
    )
    parser.add_argument(
        "--camera-id",
        type=int,
        help="Test specific camera ID only"
    )
    parser.add_argument(
        "--save-frames",
        action="store_true",
        help="Save captured frames to disk"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick tests only (skip analysis)"
    )

    args = parser.parse_args()

    tester = CameraTester(base_url=args.base_url)

    print("=" * 50)
    print("🧪 External Multi-Camera System Test Suite")
    print("=" * 50)

    # Run tests
    results = {}

    # Test 1: Detection
    results["detection"] = tester.test_detection()
    if not results["detection"]:
        print("\n❌ Camera detection failed. Cannot proceed with other tests.")
        print("\n💡 Troubleshooting:")
        print("   1. Check if camera service is running: docker-compose ps cam")
        print("   2. Check if cameras are connected: ls -la /dev/video*")
        print("   3. Check if cameras are configured: curl http://localhost:9007/external_cameras/status")
        sys.exit(1)

    # Small delay to let cameras initialize
    time.sleep(1)

    # Test 2: Status
    results["status"] = tester.test_status()

    # Test 3: Individual frame (if camera ID specified or test all)
    if args.camera_id is not None:
        results["individual_frame"] = tester.test_individual_frame(
            args.camera_id,
            save_frame=args.save_frames
        )
    else:
        # Test camera 0 by default
        results["individual_frame"] = tester.test_individual_frame(
            0,
            save_frame=args.save_frames
        )

    # Test 4: Synchronized frames
    results["synchronized"] = tester.test_synchronized_frames()

    if not args.quick:
        # Test 5: Fall detection
        results["fall_detection"] = tester.test_fall_detection()

        # Test 6: Posture analysis
        results["posture"] = tester.test_posture_analysis()

        # Test 7: Activity detection
        results["activity"] = tester.test_activity_detection()

    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name.replace('_', ' ').title()}: {status}")

    print(f"\n   Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Camera system is working correctly.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
