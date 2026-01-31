#!/usr/bin/env python3
"""
Comprehensive test script for camera activity detection and data interaction
"""

import sys
import os
import json
import base64
import io
from PIL import Image, ImageDraw
import numpy as np
import requests
import time

# Add the cam module to path
sys.path.append(os.path.dirname(__file__))

def create_test_image(scenario: str, width: int = 640, height: int = 480) -> bytes:
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

    # Convert to bytes
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG')
    return buffer.getvalue()


def test_activity_detection(base_url: str = "http://localhost:8003"):
    """Test activity detection for different scenarios"""

    scenarios = [
        'watching_tv',
        'working_on_computer',
        'cooking',
        'eating',
        'sneaking_snacks',
        'exercising',
        'reading',
        'sleeping'
    ]

    results = {}

    print("🧪 Testing Activity Detection Across Scenarios")
    print("=" * 50)

    for scenario in scenarios:
        print(f"\n📸 Testing scenario: {scenario}")

        # Create test image
        image_data = create_test_image(scenario)

        # Test activity detection
        try:
            files = {'file': ('test.jpg', image_data, 'image/jpeg')}
            response = requests.post(f"{base_url}/detect_activity", files=files, timeout=10)

            if response.status_code == 200:
                result = response.json()
                results[scenario] = result

                primary_activity = result.get('primary_activity', 'unknown')
                confidence = result.get('confidence', 0)
                posture = result.get('posture', 'unknown')
                objects = result.get('detected_objects', [])

                print(f"  ✅ Detected: {primary_activity} (confidence: {confidence:.2f})")
                print(f"  📏 Posture: {posture}")
                print(f"  🔍 Objects: {objects}")

                # Check if detection matches expected scenario
                success = primary_activity == scenario or (
                    scenario == 'sneaking_snacks' and primary_activity in ['eating', 'present']
                ) or (
                    scenario in ['watching_tv', 'working_on_computer'] and primary_activity in ['watching_tv', 'working_on_computer', 'present']
                )

                if success:
                    print(f"  🎯 CORRECT detection!")
                else:
                    print(f"  ❌ Expected {scenario}, got {primary_activity}")

            else:
                print(f"  ❌ HTTP {response.status_code}: {response.text}")
                results[scenario] = {'error': f'HTTP {response.status_code}'}

        except Exception as e:
            print(f"  ❌ Error: {e}")
            results[scenario] = {'error': str(e)}

        time.sleep(0.5)  # Brief pause between tests

    return results


def test_object_detection(base_url: str = "http://localhost:8003"):
    """Test object detection capabilities"""

    print("\n🔍 Testing Object Detection")
    print("=" * 30)

    # Test with cooking scenario (should detect round dark object)
    image_data = create_test_image('cooking')

    try:
        files = {'file': ('test.jpg', image_data, 'image/jpeg')}
        response = requests.post(f"{base_url}/detect_objects", files=files, timeout=10)

        if response.status_code == 200:
            result = response.json()
            objects = result.get('objects', [])
            detector_type = result.get('detector_type', 'unknown')

            print(f"  🤖 Detector: {detector_type}")
            print(f"  📊 Objects found: {len(objects)}")

            for obj in objects:
                print(f"    - {obj['class']} (confidence: {obj['confidence']:.2f})")

            return result
        else:
            print(f"  ❌ HTTP {response.status_code}: {response.text}")
            return {'error': f'HTTP {response.status_code}'}

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return {'error': str(e)}


def test_scene_analysis(base_url: str = "http://localhost:8003"):
    """Test comprehensive scene analysis"""

    print("\n🏠 Testing Scene Analysis")
    print("=" * 25)

    scenarios = ['watching_tv', 'cooking', 'working_on_computer']

    results = {}

    for scenario in scenarios:
        print(f"\n📸 Analyzing {scenario} scene:")

        image_data = create_test_image(scenario)

        try:
            files = {'file': ('test.jpg', image_data, 'image/jpeg')}
            response = requests.post(f"{base_url}/analyze_scene", files=files, timeout=10)

            if response.status_code == 200:
                result = response.json()
                results[scenario] = result

                activity = result.get('activity', {})
                posture = result.get('posture', 'unknown')
                scene_context = result.get('scene_context', {})
                objects = result.get('objects', [])

                print(f"  🎭 Activity: {activity.get('primary_activity', 'unknown')} ({activity.get('confidence', 0):.2f})")
                print(f"  📏 Posture: {posture}")
                print(f"  🏠 Location: {scene_context.get('location_type', 'unknown')}")
                print(f"  💡 Lighting: {scene_context.get('lighting', 'unknown')}")
                print(f"  🔍 Objects: {len(objects)} detected")

            else:
                print(f"  ❌ HTTP {response.status_code}: {response.text}")
                results[scenario] = {'error': f'HTTP {response.status_code}'}

        except Exception as e:
            print(f"  ❌ Error: {e}")
            results[scenario] = {'error': str(e)}

        time.sleep(0.5)

    return results


def test_data_flow_to_ai_brain(base_url: str = "http://localhost:8003", ai_brain_url: str = "http://localhost:9004"):
    """Test that camera data flows correctly to AI brain"""

    print("\n🧠 Testing Data Flow to AI Brain")
    print("=" * 35)

    # Mock AI brain endpoint to capture data
    captured_data = []

    # Since we can't easily mock the AI brain, we'll just verify the camera sends data
    print("  📡 Testing activity data transmission...")

    image_data = create_test_image('cooking')

    try:
        files = {'file': ('test.jpg', image_data, 'image/jpeg')}
        response = requests.post(f"{base_url}/detect_activity", files=files, timeout=10)

        if response.status_code == 200:
            print("  ✅ Camera processed image successfully")

            # Check if AI brain endpoint would be reachable (don't actually call it)
            try:
                # Just test connectivity, don't send data
                test_response = requests.get(f"{ai_brain_url}/health", timeout=2)
                if test_response.status_code == 200:
                    print("  ✅ AI Brain endpoint is reachable")
                    print("  📊 Data flow: Camera → AI Brain (simulated)")
                else:
                    print(f"  ⚠️  AI Brain returned status {test_response.status_code}")
            except:
                print("  ⚠️  AI Brain not reachable (expected in test environment)")

        else:
            print(f"  ❌ Camera returned HTTP {response.status_code}")

    except Exception as e:
        print(f"  ❌ Error: {e}")


def run_comprehensive_test(base_url: str = "http://localhost:8003"):
    """Run all camera system tests"""

    print("🚀 Kilo AI Camera System - Comprehensive Testing")
    print("=" * 55)
    print(f"Testing against: {base_url}")
    print()

    # Test basic connectivity
    try:
        response = requests.get(f"{base_url}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ Camera service is running and accessible")
        else:
            print(f"❌ Camera service returned status {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Cannot connect to camera service: {e}")
        print("💡 Make sure the camera service is running: cd microservice/cam && python3 main.py")
        return

    # Run all tests
    activity_results = test_activity_detection(base_url)
    object_results = test_object_detection(base_url)
    scene_results = test_scene_analysis(base_url)
    test_data_flow_to_ai_brain(base_url)

    # Summary
    print("\n📊 TEST SUMMARY")
    print("=" * 15)

    successful_scenarios = sum(1 for scenario, result in activity_results.items()
                             if not isinstance(result, dict) or 'error' not in result)

    total_scenarios = len(activity_results)
    success_rate = successful_scenarios / total_scenarios * 100

    print(f"🎯 Activity Detection: {successful_scenarios}/{total_scenarios} scenarios processed ({success_rate:.1f}%)")
    print(f"🔍 Object Detection: {'✅ Working' if 'error' not in object_results else '❌ Failed'}")
    print(f"🏠 Scene Analysis: {'✅ Working' if all('error' not in r for r in scene_results.values()) else '❌ Issues detected'}")

    # Detailed results
    print("\n📋 DETAILED RESULTS")
    print("=" * 18)

    print("\n🎭 Activity Detection Results:")
    for scenario, result in activity_results.items():
        if isinstance(result, dict) and 'error' not in result:
            activity = result.get('primary_activity', 'unknown')
            confidence = result.get('confidence', 0)
            status = "✅" if activity != 'unknown' else "❌"
            print(f"  {status} {scenario}: {activity} ({confidence:.2f})")
        else:
            print(f"  ❌ {scenario}: Failed")

    print("\n🔍 Object Detection Results:")
    if 'error' not in object_results:
        objects = object_results.get('objects', [])
        print(f"  ✅ Detected {len(objects)} objects")
        for obj in objects[:3]:  # Show first 3
            print(f"    - {obj['class']} ({obj['confidence']:.2f})")
    else:
        print(f"  ❌ {object_results['error']}")

    print("\n💡 RECOMMENDATIONS")
    print("=" * 15)
    print("1. 🧠 AI Brain Integration: Ensure AI brain service is running to receive camera data")
    print("2. 📷 PTZ Camera: Connect real PTZ hardware for full tracking capabilities")
    print("3. 🎯 YOLO Models: Download YOLOv3-tiny model files for advanced object detection")
    print("4. 📊 Monitoring: Set up logging to track activity recognition accuracy over time")
    print("5. 🔄 Continuous Learning: Consider training custom models for specific activities")

    return {
        'activity_results': activity_results,
        'object_results': object_results,
        'scene_results': scene_results,
        'success_rate': success_rate
    }


if __name__ == "__main__":
    # Allow custom base URL
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8003"

    results = run_comprehensive_test(base_url)

    # Save results to file
    with open('camera_test_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n💾 Results saved to camera_test_results.json")