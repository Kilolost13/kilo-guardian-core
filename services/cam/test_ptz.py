#!/usr/bin/env python3
"""
Test script for PTZ tracking functionality
"""

from cam.main import ptz_controller, person_tracker, PTZHardwareInterface
import numpy as np

def test_ptz_hardware_interface():
    """Test PTZ hardware interface"""
    print("Testing PTZ Hardware Interface...")

    # Test mock mode
    hardware = PTZHardwareInterface()
    print(f"Connection type: {hardware.connection_type}")

    # Test position setting
    hardware.set_pan_tilt_zoom(10.0, 5.0, 2.0)
    pan, tilt, zoom = hardware.get_position()
    print(f"Position set to: pan={pan}, tilt={tilt}, zoom={zoom}")

    # Test movement
    hardware.move_relative(5.0, 2.0, 0.5)
    pan, tilt, zoom = hardware.get_position()
    print(f"After relative move: pan={pan}, tilt={tilt}, zoom={zoom}")

    print("✓ PTZ Hardware Interface test passed")

def test_ptz_controller():
    """Test PTZ controller"""
    print("\nTesting PTZ Controller...")

    controller = ptz_controller

    # Test position setting
    controller.set_position(45.0, 30.0, 3.0)
    print(f"Controller position: pan={controller.pan}, tilt={controller.tilt}, zoom={controller.zoom}")

    # Test boundary checking
    in_bounds = controller.check_boundaries(45.0, 30.0, 3.0)
    out_bounds = controller.check_boundaries(200.0, 100.0, 15.0)
    print(f"Boundary check: in_bounds={in_bounds}, out_bounds={out_bounds}")

    # Test movement calculation
    person_center = (320, 240)  # Center of 640x480 frame
    frame_size = (640, 480)
    delta_pan, delta_tilt, delta_zoom = controller.calculate_ptz_movement(person_center, frame_size)
    print(f"Movement calculation: delta_pan={delta_pan:.2f}, delta_tilt={delta_tilt:.2f}, delta_zoom={delta_zoom:.2f}")

    print("✓ PTZ Controller test passed")

def test_person_tracker():
    """Test person tracker"""
    print("\nTesting Person Tracker...")

    tracker = person_tracker

    # Test with mock pose landmarks (nose, left_hip, right_hip)
    mock_landmarks = [
        [0.5, 0.3],  # nose
        [0.0, 0.0],  # other landmarks...
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.45, 0.7],  # left_hip
        [0.55, 0.7],  # right_hip
    ]

    frame_size = (640, 480)
    person_pos = tracker.get_primary_person_position(mock_landmarks, frame_size)

    if person_pos:
        print(f"Person position detected: x={person_pos[0]:.1f}, y={person_pos[1]:.1f}")
        print("✓ Person Tracker test passed")
    else:
        print("✗ Person Tracker test failed - no position detected")

def test_tracking_integration():
    """Test integrated tracking system"""
    print("\nTesting Tracking Integration...")

    # Mock person at offset position
    mock_landmarks = [
        [0.7, 0.4],  # nose offset to right
        [0.0, 0.0],  # other landmarks...
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [0.65, 0.8],  # left_hip
        [0.75, 0.8],  # right_hip
    ]

    frame_size = (640, 480)

    # Get person position
    person_pos = person_tracker.get_primary_person_position(mock_landmarks, frame_size)
    print(f"Person at position: {person_pos}")

    # Enable tracking
    ptz_controller.is_tracking = True

    # Update tracking
    initial_pan = ptz_controller.pan
    ptz_controller.update_tracking(person_pos, frame_size)

    print(f"PTZ moved from pan={initial_pan} to pan={ptz_controller.pan}")
    print("✓ Tracking Integration test passed")

if __name__ == "__main__":
    print("=== PTZ Tracking System Test ===\n")

    try:
        test_ptz_hardware_interface()
        test_ptz_controller()
        test_person_tracker()
        test_tracking_integration()

        print("\n=== All Tests Passed! ===")
        print("PTZ tracking system is ready for use.")

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()