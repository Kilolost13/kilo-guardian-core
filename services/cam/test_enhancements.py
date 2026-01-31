#!/usr/bin/env python3
"""
Test script for enhanced camera service features
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

def test_imports():
    """Test that all required modules can be imported"""
    try:
        import cv2
        import numpy as np
        import hashlib
        from fastapi import FastAPI, File, UploadFile, HTTPException
        print("✓ All required modules imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_yolo_loading():
    """Test YOLO model loading (without actually loading to avoid long wait)"""
    try:
        # Check if YOLO files exist
        yolov3_weights = os.path.join(os.path.dirname(__file__), 'yolov3-tiny.weights')
        yolov3_cfg = os.path.join(os.path.dirname(__file__), 'yolov3-tiny.cfg')
        coco_names = os.path.join(os.path.dirname(__file__), 'coco.names')

        if os.path.exists(yolov3_weights) and os.path.exists(yolov3_cfg) and os.path.exists(coco_names):
            print("✓ YOLO model files found")
            return True
        else:
            print("✗ YOLO model files missing")
            return False
    except Exception as e:
        print(f"✗ YOLO test error: {e}")
        return False

def test_cache_functions():
    """Test cache functionality"""
    try:
        from main import get_cache_key, cache_result, get_cached_result, cleanup_expired_cache

        # Test cache key generation
        key = get_cache_key("test_hash", "test_op")
        assert key == "test_op_test_hash"
        print("✓ Cache key generation works")

        # Test caching
        test_data = {"test": "data"}
        cache_result(key, test_data, ttl=1)
        cached = get_cached_result(key)
        assert cached == test_data
        print("✓ Caching functionality works")

        return True
    except Exception as e:
        print(f"✗ Cache test error: {e}")
        return False

def test_performance_metrics():
    """Test performance metrics functionality"""
    try:
        from main import update_performance_metrics, get_performance_stats

        # Test metrics update
        update_performance_metrics("test_activity", 0.8, "test_actual")
        stats = get_performance_stats()

        assert stats['total_detections'] == 1
        assert stats['average_confidence'] > 0
        print("✓ Performance metrics work")

        return True
    except Exception as e:
        print(f"✗ Performance metrics test error: {e}")
        return False

if __name__ == "__main__":
    print("Testing Enhanced Camera Service Features")
    print("=" * 50)

    tests = [
        ("Module Imports", test_imports),
        ("YOLO Files", test_yolo_loading),
        ("Cache Functions", test_cache_functions),
        ("Performance Metrics", test_performance_metrics),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\nTesting {test_name}:")
        if test_func():
            passed += 1

    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Camera service enhancements are ready.")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")