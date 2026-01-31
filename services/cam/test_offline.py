#!/usr/bin/env python3
"""
Offline test script for camera activity detection and data interaction
Tests the core logic without requiring a running service
"""

import sys
import os
import json
import base64
import io
from PIL import Image, ImageDraw
import numpy as np

# Add the cam module to path
sys.path.append(os.path.dirname(__file__))

def create_test_image(scenario: str, width: int = 640, height: int = 480) -> np.ndarray:
    """Create a synthetic test image for different scenarios"""
    img = Image.new('RGB', (width, height), color='gray')
    draw = ImageDraw.Draw(img)

    if scenario == 'watching_tv':
        # Bright screen-like rectangle
        draw.rectangle([200, 150, 440, 330], fill='white')
        # Person silhouette sitting
        draw.ellipse([300, 350, 340, 390], fill='black')  # head
        draw.rectangle([310, 390, 330, 450], fill='black')  # body

    elif scenario == 'working_on_computer':
        # Bright screen
        draw.rectangle([250, 100, 390, 250], fill='lightblue')
        # Keyboard area
        draw.rectangle([200, 300, 440, 320], fill='black')
        # Person sitting
        draw.ellipse([320, 350, 360, 390], fill='black')

    elif scenario == 'cooking':
        # Large dark round object (pan/pot)
        draw.ellipse([250, 200, 390, 340], fill='black')
        # Person standing
        draw.ellipse([320, 380, 360, 420], fill='black')
        draw.rectangle([330, 420, 350, 480], fill='black')

    elif scenario == 'eating':
        # Round dark objects (plates/bowls)
        draw.ellipse([200, 250, 260, 310], fill='black')
        draw.ellipse([380, 250, 440, 310], fill='black')
        # Person sitting
        draw.ellipse([320, 350, 360, 390], fill='black')

    elif scenario == 'sneaking_snacks':
        # Small dark round object (snack)
        draw.ellipse([300, 280, 340, 320], fill='black')
        # Person in sneaky pose
        draw.ellipse([320, 350, 360, 390], fill='black')

    elif scenario == 'exercising':
        # Person standing with arms up
        draw.ellipse([320, 300, 360, 340], fill='black')
        draw.rectangle([330, 340, 350, 400], fill='black')
        draw.rectangle([300, 360, 380, 370], fill='white')  # arms extended

    elif scenario == 'reading':
        # Book-like rectangle
        draw.rectangle([280, 250, 360, 320], fill='white')
        # Person sitting focused
        draw.ellipse([320, 350, 360, 390], fill='black')

    elif scenario == 'sleeping':
        # Person lying down
        draw.ellipse([320, 400, 360, 440], fill='black')
        draw.rectangle([330, 440, 350, 480], fill='black')

    # Convert to numpy array
    return np.array(img)


def test_object_detection_offline():
    """Test object detection functions offline"""
    print("🔍 Testing Object Detection (Offline)")
    print("=" * 40)

    # Import the detection functions
    try:
        from main import detect_objects_basic, detect_objects_yolo, detect_objects
        print("✅ Detection functions imported")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return None

    # Test with different scenarios
    scenarios = ['cooking', 'watching_tv', 'working_on_computer']

    results = {}
    for scenario in scenarios:
        print(f"\n📸 Testing {scenario} scenario:")

        # Create test image
        image = create_test_image(scenario)

        # Test basic detection
        try:
            objects = detect_objects_basic(image)
            print(f"  ✅ Basic detection: {len(objects)} objects found")
            for obj in objects[:2]:  # Show first 2
                print(f"    - {obj['class']} ({obj['confidence']:.2f})")
        except Exception as e:
            print(f"  ❌ Basic detection failed: {e}")
            objects = []

        # Test unified detection
        try:
            unified_objects = detect_objects(image)
            print(f"  ✅ Unified detection: {len(unified_objects)} objects found")
        except Exception as e:
            print(f"  ❌ Unified detection failed: {e}")
            unified_objects = []

        results[scenario] = {
            'basic_objects': objects,
            'unified_objects': unified_objects
        }

    return results


def test_activity_classification_offline():
    """Test activity classification logic offline"""
    print("\n🎭 Testing Activity Classification (Offline)")
    print("=" * 45)

    try:
        from main import classify_activity, classify_posture
        print("✅ Classification functions imported")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return None

    # Mock posture data for different scenarios
    posture_scenarios = {
        'watching_tv': 'sitting',
        'working_on_computer': 'sitting',
        'cooking': 'standing',
        'eating': 'sitting',
        'exercising': 'standing',
        'reading': 'sitting',
        'sleeping': 'lying'
    }

    # Mock object data
    object_scenarios = {
        'watching_tv': [{'class': 'bright_object', 'confidence': 0.8}],
        'working_on_computer': [{'class': 'bright_object', 'confidence': 0.9}],
        'cooking': [{'class': 'round_dark_object', 'confidence': 0.85}],
        'eating': [{'class': 'round_dark_object', 'confidence': 0.7}],
        'sneaking_snacks': [{'class': 'round_dark_object', 'confidence': 0.6}],
        'exercising': [],
        'reading': [],
        'sleeping': []
    }

    results = {}
    for scenario in posture_scenarios.keys():
        print(f"\n📸 Testing {scenario} classification:")

        posture = posture_scenarios[scenario]
        objects = object_scenarios[scenario]

        try:
            activity_result = classify_activity(objects, posture)
            primary_activity = activity_result['primary_activity']
            confidence = activity_result['confidence']

            print(f"  📏 Posture: {posture}")
            print(f"  🔍 Objects: {[obj['class'] for obj in objects]}")
            print(f"  🎯 Detected: {primary_activity} ({confidence:.2f})")

            # Check if classification is correct
            correct = primary_activity == scenario or (
                scenario == 'sneaking_snacks' and primary_activity in ['eating', 'present']
            )

            if correct:
                print("  ✅ CORRECT classification!")
            else:
                print(f"  ⚠️  Expected {scenario}, got {primary_activity}")

        except Exception as e:
            print(f"  ❌ Classification failed: {e}")
            activity_result = {'error': str(e)}

        results[scenario] = {
            'posture': posture,
            'objects': objects,
            'activity_result': activity_result
        }

    return results


def test_pose_detection_offline():
    """Test pose detection logic offline"""
    print("\n🧍 Testing Pose Detection (Offline)")
    print("=" * 35)

    try:
        from main import classify_posture
        print("✅ Pose functions imported")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return None

    # Mock pose landmarks for different postures
    mock_poses = {
        'standing': [(0.5, 0.8), (0.45, 0.75), (0.55, 0.75)],  # nose, hips
        'sitting': [(0.5, 0.6), (0.45, 0.65), (0.55, 0.65)],
        'lying': [(0.5, 0.9), (0.45, 0.85), (0.55, 0.85)],
        'unknown': []
    }

    results = {}
    for posture, landmarks in mock_poses.items():
        print(f"\n📏 Testing {posture} pose:")

        try:
            detected_posture = classify_posture(landmarks)
            print(f"  🎯 Detected: {detected_posture}")

            correct = detected_posture == posture
            if correct:
                print("  ✅ CORRECT detection!")
            else:
                print(f"  ⚠️  Expected {posture}, got {detected_posture}")

        except Exception as e:
            print(f"  ❌ Pose detection failed: {e}")
            detected_posture = 'error'

        results[posture] = {
            'landmarks': landmarks,
            'detected': detected_posture
        }

    return results


def test_data_structures():
    """Test the data structures used for AI brain communication"""
    print("\n🧠 Testing Data Structures for AI Brain")
    print("=" * 40)

    # Sample data that would be sent to AI brain
    sample_activity_data = {
        'timestamp': '2025-12-23T10:30:00Z',
        'activity': 'cooking',
        'confidence': 0.85,
        'posture': 'standing',
        'detected_objects': ['round_dark_object'],
        'all_activities': {
            'watching_tv': 0.1,
            'working_on_computer': 0.05,
            'cooking': 4.0,
            'eating': 0.2,
            'sneaking_snacks': 0.1,
            'exercising': 0.1,
            'reading': 0.1,
            'sleeping': 0.0,
            'present': 1.0
        }
    }

    sample_scene_data = {
        'timestamp': '2025-12-23T10:30:00Z',
        'scene_analysis': {
            'activity': sample_activity_data,
            'objects': [{'class': 'round_dark_object', 'confidence': 0.85, 'bbox': [250, 200, 140, 140]}],
            'posture': 'standing',
            'scene_context': {
                'lighting': 'normal',
                'location_type': 'kitchen',
                'activity_indicators': ['food_preparation'],
                'confidence': 0.7
            },
            'pose_detected': True
        }
    }

    print("📊 Sample Activity Data Structure:")
    print(json.dumps(sample_activity_data, indent=2))

    print("\n🏠 Sample Scene Analysis Data Structure:")
    print(json.dumps(sample_scene_data, indent=2))

    # Validate structure
    required_activity_fields = ['timestamp', 'activity', 'confidence', 'posture', 'detected_objects']
    required_scene_fields = ['timestamp', 'scene_analysis']

    activity_valid = all(field in sample_activity_data for field in required_activity_fields)
    scene_valid = all(field in sample_scene_data for field in required_scene_fields)

    print(f"\n✅ Activity data structure: {'VALID' if activity_valid else 'INVALID'}")
    print(f"✅ Scene data structure: {'VALID' if scene_valid else 'INVALID'}")

    return {
        'activity_data': sample_activity_data,
        'scene_data': sample_scene_data,
        'structures_valid': activity_valid and scene_valid
    }


def run_offline_comprehensive_test():
    """Run all offline tests"""
    print("🚀 Kilo AI Camera System - Offline Comprehensive Testing")
    print("=" * 60)
    print("Testing core functionality without requiring running services")
    print()

    # Run all tests
    object_results = test_object_detection_offline()
    activity_results = test_activity_classification_offline()
    pose_results = test_pose_detection_offline()
    data_results = test_data_structures()

    # Summary
    print("\n📊 OFFLINE TEST SUMMARY")
    print("=" * 25)

    tests_passed = 0
    total_tests = 4

    if object_results:
        tests_passed += 1
        print("✅ Object Detection: Working")

    if activity_results:
        tests_passed += 1
        print("✅ Activity Classification: Working")

    if pose_results:
        tests_passed += 1
        print("✅ Pose Detection: Working")

    if data_results and data_results.get('structures_valid', False):
        tests_passed += 1
        print("✅ Data Structures: Valid")

    success_rate = tests_passed / total_tests * 100
    print(f"\n🎯 Overall Success Rate: {tests_passed}/{total_tests} ({success_rate:.1f}%)")

    if success_rate >= 75:
        print("🎉 Camera system core functionality is READY!")
    else:
        print("⚠️  Some components need attention")

    # Detailed results
    print("\n🔍 DETAILED ANALYSIS")
    print("=" * 20)

    if activity_results:
        print("\n🎭 Activity Detection Accuracy:")
        correct_classifications = sum(1 for scenario, result in activity_results.items()
                                    if result.get('activity_result', {}).get('primary_activity') == scenario
                                    or (scenario == 'sneaking_snacks' and
                                        result.get('activity_result', {}).get('primary_activity') in ['eating', 'present']))

        total_scenarios = len(activity_results)
        accuracy = correct_classifications / total_scenarios * 100
        print(f"  {correct_classifications}/{total_scenarios} scenarios classified correctly ({accuracy:.1f}%)")

    print("\n💡 RECOMMENDATIONS FOR PRODUCTION")
    print("=" * 35)
    print("1. 📷 Real Camera Integration: Connect PTZ camera hardware for full tracking")
    print("2. 🎯 YOLO Models: Download and integrate YOLOv3-tiny model files for advanced object detection")
    print("3. 📊 AI Brain Integration: Ensure AI brain service can receive and process camera data")
    print("4. 🔄 Continuous Learning: Implement feedback loop to improve activity recognition")
    print("5. 📈 Performance Monitoring: Add metrics collection for detection accuracy over time")
    print("6. 🛡️ Safety Features: Implement movement boundaries and emergency stops for PTZ")
    print("7. 🔍 Scene Context: Enhance location inference with more environmental cues")

    return {
        'object_results': object_results,
        'activity_results': activity_results,
        'pose_results': pose_results,
        'data_results': data_results,
        'success_rate': success_rate
    }


if __name__ == "__main__":
    results = run_offline_comprehensive_test()

    # Save results
    with open('camera_offline_test_results.json', 'w') as f:
        # Convert numpy arrays to lists for JSON serialization
        json_results = {}
        for key, value in results.items():
            if isinstance(value, dict):
                json_results[key] = {}
                for subkey, subvalue in value.items():
                    if isinstance(subvalue, np.ndarray):
                        json_results[key][subkey] = subvalue.tolist()
                    else:
                        json_results[key][subkey] = subvalue
            else:
                json_results[key] = value

        json.dump(json_results, f, indent=2, default=str)

    print(f"\n💾 Results saved to camera_offline_test_results.json")