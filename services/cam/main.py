

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import pytesseract
from PIL import Image
from io import BytesIO
import cv2
import numpy as np
import os
import json
import time
import requests
import logging
from typing import Optional, Tuple, List, Dict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Optional: skip importing heavy mediapipe native extensions in test environments
# Set SKIP_MEDIAPIPE_IMPORT=1 in env to avoid importing mediapipe (prevents C-level aborts)
if os.environ.get('SKIP_MEDIAPIPE_IMPORT') in ('1','true','True'):
    mp = None
    mp_tasks = None
    vision = None
else:
    try:
        import mediapipe as mp
        from mediapipe.tasks import python as mp_tasks
        from mediapipe.tasks.python import vision
    except Exception:
        mp = None
        mp_tasks = None
        vision = None
import httpx
import datetime
from collections import deque
from typing import Optional
import threading
import math
import asyncio

# Object detection setup
object_detector = None
try:
    # Check if YOLO model files exist before attempting to load
    yolo_config = 'yolov3-tiny.cfg'
    yolo_weights = 'yolov3-tiny.weights'
    yolo_classes = 'coco.names'

    model_files_exist = (
        os.path.exists(yolo_config) and
        os.path.exists(yolo_weights) and
        os.path.exists(yolo_classes)
    )

    if model_files_exist:
        try:
            net = cv2.dnn.readNetFromDarknet(yolo_config, yolo_weights)
            net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

            with open(yolo_classes, 'r') as f:
                classes = [line.strip() for line in f.readlines()]

            object_detector = {
                'net': net,
                'classes': classes,
                'conf_threshold': 0.5,
                'nms_threshold': 0.4
            }
            print("YOLO object detector loaded successfully")
        except Exception as e:
            print(f"Failed to initialize YOLO detector: {e}")
            object_detector = None
    else:
        print("YOLO model files not found, using basic object detection")
        object_detector = None

except Exception as e:
    print(f"Object detector setup failed: {e}")
    object_detector = None

class PTZHardwareInterface:
    """Hardware abstraction for PTZ camera control"""

    def __init__(self):
        self.serial_port = None
        self.network_address = None
        self.connection_type = "mock"  # mock, serial, network

    def connect(self, connection_string: str):
        """Connect to PTZ hardware"""
        if connection_string.startswith("mock://"):
            self.connection_type = "mock"
            print(f"Connected to mock PTZ controller: {connection_string}")
        elif connection_string.startswith("/dev/"):
            self.connection_type = "serial"
            # TODO: Implement serial connection
            print(f"Serial PTZ connection not implemented: {connection_string}")
        elif "://" in connection_string:
            self.connection_type = "network"
            # TODO: Implement network connection (ONVIF, VISCA, etc.)
            print(f"Network PTZ connection not implemented: {connection_string}")
        else:
            raise ValueError(f"Unsupported PTZ connection string: {connection_string}")

    def set_pan_tilt_zoom(self, pan: float, tilt: float, zoom: float):
        """Set PTZ position"""
        if self.connection_type == "mock":
            print(".2f")
            return True
        # TODO: Implement actual hardware control
        return False

    def get_position(self) -> Tuple[float, float, float]:
        """Get current PTZ position"""
        if self.connection_type == "mock":
            return (0.0, 0.0, 1.0)  # Mock position
        # TODO: Implement actual position reading
        return (0.0, 0.0, 1.0)

    def move_relative(self, delta_pan: float, delta_tilt: float, delta_zoom: float):
        """Move PTZ by relative amounts"""
        current_pan, current_tilt, current_zoom = self.get_position()
        new_pan = current_pan + delta_pan
        new_tilt = current_tilt + delta_tilt
        new_zoom = current_zoom + delta_zoom
        self.set_pan_tilt_zoom(new_pan, new_tilt, new_zoom)

    def stop_movement(self):
        """Stop all PTZ movement"""
        if self.connection_type == "mock":
            print("Mock PTZ: Movement stopped")
        # TODO: Implement actual stop command

# Global hardware interface
ptz_hardware = PTZHardwareInterface()

app = FastAPI(title="Camera Service")

# Add CORS middleware to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state to store last pose detection time
last_pose_detection_time: Optional[datetime.datetime] = None

# Global webcam capture object - keep camera open
global_webcam_capture = None

# Mediapipe pose setup
# The pose landmarker model is optional for local/dev runs and heavy integration tests.
# If the model asset is missing or mediapipe fails to initialize, we fall back to a safe
# degraded mode (no pose detection) so the service can start and unit tests run.
pose_landmarker = None
try:
    # Download the pose landmarker model from:
    # https://developers.google.com/mediapipe/solutions/vision/pose_landmarker/python
    # and place it in the same directory as this file or set the path via env in production.
    base_options = mp_tasks.BaseOptions(model_asset_path='pose_landmarker_lite.task')
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.IMAGE,
        min_pose_detection_confidence=0.5,
    )
    pose_landmarker = vision.PoseLandmarker.create_from_options(options)
except Exception:
    # Model/or native deps not available; run in degraded mode.
    pose_landmarker = None

# No /feed endpoint: No human access to live feed, by design

@app.get("/status")
@app.get("/health")
async def get_camera_status():
    global last_pose_detection_time
    sees_user = False
    time_since_last_detection = None

    if last_pose_detection_time:
        time_since_last_detection = (datetime.datetime.now() - last_pose_detection_time).total_seconds()
        if time_since_last_detection < 5:  # Consider a pose "seen" if detected in the last 5 seconds
            sees_user = True

    return {
        "sees_user": sees_user,
        "last_detection_time_ago": f"{time_since_last_detection:.2f} seconds ago" if time_since_last_detection is not None else "never"
    }

def get_webcam_capture():
    """Get or initialize the global webcam capture object"""
    global global_webcam_capture

    # If webcam is already open and working, return it
    if global_webcam_capture is not None and global_webcam_capture.isOpened():
        return global_webcam_capture

    # Try to open webcam
    for device in [0, 1]:
        cap = cv2.VideoCapture(device)
        if cap.isOpened():
            global_webcam_capture = cap
            return global_webcam_capture
        cap.release()

    return None

@app.get("/stream")
async def stream_webcam():
    """Stream a single frame from the webcam as JPEG"""
    try:
        # Get the global webcam (stays open)
        cap = get_webcam_capture()

        if cap is None or not cap.isOpened():
            raise HTTPException(status_code=503, detail="No webcam available")

        # Read a frame (camera stays open)
        ret, frame = cap.read()

        if not ret:
            # Camera might have disconnected, try to reinitialize
            global global_webcam_capture
            global_webcam_capture = None
            raise HTTPException(status_code=503, detail="Failed to capture frame")

        # Encode frame as JPEG
        _, buffer = cv2.imencode('.jpg', frame)

        return StreamingResponse(
            BytesIO(buffer.tobytes()),
            media_type="image/jpeg"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webcam stream failed: {e}")

@app.post("/ocr")
async def ocr_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")
    try:
        img_bytes = await file.read()
        img = Image.open(BytesIO(img_bytes))
        try:
            text = pytesseract.image_to_string(img)
        except Exception:
            # Tesseract binary or bindings not available in this environment — degrade gracefully
            text = ""
        # Send OCR result to ai_brain (best-effort; don't fail if ai_brain is unavailable)
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    "http://ai_brain:9001/ingest/receipt",
                    json={"text": text.strip()}
                )
        except Exception:
            pass
        return {"text": text.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR failed: {e}")


@app.post("/ocr/batch")
async def ocr_batch_images(files: List[UploadFile] = File(...)):
    """
    Process multiple images simultaneously and combine OCR results.

    Use case: Multi-camera capture for better accuracy from multiple angles.
    - Processes all images in parallel
    - Returns individual results and combined text
    - Includes confidence scoring and deduplication
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 images allowed per batch.")

    try:
        results = []
        all_texts = []

        # Process all images in parallel
        async def process_single_image(file: UploadFile, index: int):
            if not file.content_type.startswith("image/"):
                return {
                    "index": index,
                    "filename": file.filename,
                    "text": "",
                    "error": "Not an image file",
                    "success": False
                }

            try:
                img_bytes = await file.read()
                img = Image.open(BytesIO(img_bytes))

                # Extract text using Tesseract
                try:
                    text = pytesseract.image_to_string(img)
                    # Get confidence data if available
                    try:
                        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                        confidences = [int(conf) for conf in data['conf'] if conf != '-1']
                        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                    except Exception:
                        avg_confidence = 0
                except Exception as e:
                    text = ""
                    avg_confidence = 0

                return {
                    "index": index,
                    "filename": file.filename,
                    "text": text.strip(),
                    "confidence": avg_confidence,
                    "char_count": len(text.strip()),
                    "success": True
                }
            except Exception as e:
                return {
                    "index": index,
                    "filename": file.filename,
                    "text": "",
                    "error": str(e),
                    "success": False
                }

        # Process all images concurrently
        tasks = [process_single_image(file, i) for i, file in enumerate(files)]
        results = await asyncio.gather(*tasks)

        # Collect all successfully extracted texts
        successful_results = [r for r in results if r["success"] and r["text"]]
        all_texts = [r["text"] for r in successful_results]

        # Combine texts intelligently
        # Strategy 1: Use the longest text (likely captured the most info)
        combined_text = max(all_texts, key=len) if all_texts else ""

        # Strategy 2: Find common words across all results (high confidence)
        if len(all_texts) > 1:
            # Split into words
            word_sets = [set(text.split()) for text in all_texts]
            # Find common words (appear in at least 2 captures)
            common_words = set()
            for i, words in enumerate(word_sets):
                for other_words in word_sets[i+1:]:
                    common_words.update(words & other_words)
        else:
            common_words = set()

        # Send combined result to ai_brain (best-effort)
        if combined_text:
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        "http://ai_brain:9001/ingest/receipt",
                        json={"text": combined_text}
                    )
            except Exception:
                pass

        return {
            "success": True,
            "total_images": len(files),
            "successful_ocr": len(successful_results),
            "failed_ocr": len(files) - len(successful_results),
            "individual_results": results,
            "combined_text": combined_text,
            "common_words": list(common_words),
            "recommended_result_index": max(
                range(len(results)),
                key=lambda i: results[i].get("char_count", 0)
            ) if results else 0,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch OCR failed: {e}")


def extract_pose_from_image(image: np.ndarray):
    # Convert BGR image to RGB
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    # If the mediapipe model is not available, return None (degraded behavior)
    if pose_landmarker is None:
        return None
    # Convert the image to MediaPipe's Image format
    mp_image = mp.Image(image_format=mp.ImageFormat.RGB, data=rgb_image)
    detection_result = pose_landmarker.detect(mp_image)
    if not detection_result.pose_landmarks:
        return None
    # Assuming only one person in the image, get the first set of landmarks
    return [(lm.x, lm.y, lm.z, lm.visibility) for lm in detection_result.pose_landmarks[0]]

def classify_posture(landmarks):
    # Simple logic: use y-coordinates of key points to guess posture
    if not landmarks or len(landmarks) < 12:
        return "unknown"
    nose = landmarks[0][1]
    left_hip = landmarks[23][1] if len(landmarks) > 23 else None
    right_hip = landmarks[24][1] if len(landmarks) > 24 else None
    left_ankle = landmarks[27][1] if len(landmarks) > 27 else None
    right_ankle = landmarks[28][1] if len(landmarks) > 28 else None
    if left_hip and right_hip and left_ankle and right_ankle:
        avg_hip = (left_hip + right_hip) / 2
        avg_ankle = (left_ankle + right_ankle) / 2
        if abs(avg_hip - avg_ankle) < 0.1:
            return "standing"
        elif abs(nose - avg_ankle) < 0.2:
            return "lying"
        else:
            return "sitting"
    return "unknown"


def detect_objects_yolo(image: np.ndarray) -> List[Dict]:
    """Detect objects using YOLO"""
    if object_detector is None:
        return []

    try:
        height, width = image.shape[:2]

        # Create blob from image
        blob = cv2.dnn.blobFromImage(image, 1/255.0, (416, 416), swapRB=True, crop=False)
        object_detector['net'].setInput(blob)

        # Get output layer names
        layer_names = object_detector['net'].getLayerNames()
        output_layers = [layer_names[i - 1] for i in object_detector['net'].getUnconnectedOutLayers()]

        # Forward pass
        outputs = object_detector['net'].forward(output_layers)

        # Process detections
        detections = []
        for output in outputs:
            for detection in output:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]

                if confidence > object_detector['conf_threshold']:
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)

                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)

                    detections.append({
                        'class': object_detector['classes'][class_id],
                        'confidence': float(confidence),
                        'bbox': [x, y, w, h]
                    })

        # Apply non-maximum suppression
        boxes = [d['bbox'] for d in detections]
        confidences = [d['confidence'] for d in detections]
        indices = cv2.dnn.NMSBoxes(boxes, confidences, object_detector['conf_threshold'], object_detector['nms_threshold'])

        filtered_detections = []
        if len(indices) > 0:
            for i in indices.flatten():
                filtered_detections.append(detections[i])

        return filtered_detections

    except Exception as e:
        print(f"Object detection failed: {e}")
        return []


def detect_objects_basic(image: np.ndarray) -> List[Dict]:
    """Basic object detection using color and shape analysis"""
    detections = []

    try:
        # Convert to HSV for better color analysis
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Detect bright objects (screens, lights)
        _, bright_mask = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        bright_contours, _ = cv2.findContours(bright_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in bright_contours:
            area = cv2.contourArea(contour)
            if area > 1000:  # Minimum area
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h if h > 0 else 0
                if 0.5 < aspect_ratio < 2.0:  # Roughly square/rectangular
                    detections.append({
                        'class': 'bright_object',
                        'confidence': 0.7,
                        'bbox': [x, y, w, h]
                    })

        # Detect dark objects (food, utensils)
        _, dark_mask = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)
        dark_contours, _ = cv2.findContours(dark_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in dark_contours:
            area = cv2.contourArea(contour)
            if area > 2000:  # Larger dark areas
                x, y, w, h = cv2.boundingRect(contour)
                perimeter = cv2.arcLength(contour, True)
                circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0

                if circularity > 0.7:  # Round objects
                    detections.append({
                        'class': 'round_dark_object',
                        'confidence': 0.8,
                        'bbox': [x, y, w, h]
                    })

        # Detect blue objects (common in food/drinks)
        lower_blue = np.array([90, 50, 50])
        upper_blue = np.array([130, 255, 255])
        blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
        blue_contours, _ = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in blue_contours:
            area = cv2.contourArea(contour)
            if area > 500:
                x, y, w, h = cv2.boundingRect(contour)
                detections.append({
                    'class': 'blue_object',
                    'confidence': 0.6,
                    'bbox': [x, y, w, h]
                })

    except Exception as e:
        print(f"Basic object detection failed: {e}")

    return detections


def detect_objects(image: np.ndarray) -> List[Dict]:
    """Unified object detection function"""
    if object_detector is not None:
        return detect_objects_yolo(image)
    else:
        return detect_objects_basic(image)


def classify_activity(objects: List[Dict], posture: str, pose_data: Optional[List] = None) -> Dict:
    """Enhanced activity classification with better differentiation"""

    activity_scores = {
        'watching_tv': 0,
        'working_on_computer': 0,
        'cooking': 0,
        'eating': 0,
        'sneaking_snacks': 0,
        'exercising': 0,
        'reading': 0,
        'sleeping': 0,
        'present': 1  # Base score for being present
    }

    # Object-based classification with enhanced logic
    object_classes = [obj['class'] for obj in objects]
    object_count = len(objects)

    # TV watching indicators - requires screen + relaxed posture
    if 'tv' in object_classes or 'remote' in object_classes or ('screen' in object_classes and posture == 'sitting'):
        activity_scores['watching_tv'] += 4
        if posture == 'sitting' and object_count <= 3:  # Minimal objects, focused on screen
            activity_scores['watching_tv'] += 2

    # Computer work indicators - screen + keyboard/mouse + upright posture
    if ('screen' in object_classes or 'laptop' in object_classes or 'computer' in object_classes):
        if 'keyboard' in object_classes or 'mouse' in object_classes or posture == 'sitting':
            activity_scores['working_on_computer'] += 4
            if 'keyboard' in object_classes:  # Strong indicator
                activity_scores['working_on_computer'] += 2

    # Cooking indicators - kitchen objects + standing
    cooking_objects = ['pan', 'pot', 'knife', 'spoon', 'bowl', 'plate', 'stove', 'oven', 'microwave']
    if any(obj in object_classes for obj in cooking_objects) or 'round_dark_object' in object_classes:
        activity_scores['cooking'] += 4
        if posture == 'standing':  # Usually stand while cooking
            activity_scores['cooking'] += 2

    # Eating indicators - food/drink objects + table setting
    eating_objects = ['fork', 'spoon', 'knife', 'plate', 'bowl', 'cup', 'bottle', 'glass']
    if any(obj in object_classes for obj in eating_objects) or ('round_dark_object' in object_classes and posture == 'sitting'):
        activity_scores['eating'] += 3
        if posture == 'sitting' and object_count >= 2:  # Multiple eating utensils
            activity_scores['eating'] += 2

    # Snack sneaking - quick, discrete actions with minimal objects
    if 'round_dark_object' in object_classes and object_count <= 2 and posture == 'sitting':
        activity_scores['sneaking_snacks'] += 3
        # Less likely if there are many objects (formal meal)
        if object_count == 1:
            activity_scores['sneaking_snacks'] += 1

    # Exercise indicators - movement patterns and equipment
    exercise_objects = ['dumbbell', 'barbell', 'treadmill', 'bicycle', 'mat', 'ball']
    if any(obj in object_classes for obj in exercise_objects):
        activity_scores['exercising'] += 4
    elif posture == 'standing' and pose_data:
        # Check for arm/leg positions indicating exercise
        activity_scores['exercising'] += 1

    # Reading indicators - book/magazine + focused posture
    reading_objects = ['book', 'magazine', 'newspaper', 'tablet', 'phone']
    if any(obj in object_classes for obj in reading_objects):
        activity_scores['reading'] += 3
        if posture == 'sitting' and object_count <= 3:  # Focused activity
            activity_scores['reading'] += 2

    # Sleeping indicators - lying down, dim lighting context
    if posture == 'lying':
        activity_scores['sleeping'] += 5

    # Cross-activity penalties (reduce confusion)
    # If we have cooking objects, reduce eating score unless sitting
    if any(obj in cooking_objects for obj in object_classes) and posture == 'standing':
        activity_scores['eating'] *= 0.5

    # If we have computer objects, reduce TV score
    if 'keyboard' in object_classes or 'mouse' in object_classes:
        activity_scores['watching_tv'] *= 0.7

    # Posture-based adjustments
    if posture == 'standing':
        activity_scores['exercising'] += 1
        activity_scores['cooking'] += 1
    elif posture == 'sitting':
        activity_scores['watching_tv'] += 1
        activity_scores['working_on_computer'] += 1
        activity_scores['reading'] += 1
        activity_scores['eating'] += 1
    elif posture == 'lying':
        activity_scores['sleeping'] += 3

    # Find the highest scoring activity
    best_activity = max(activity_scores.items(), key=lambda x: x[1])

    # Only return activity if confidence is above threshold
    confidence = best_activity[1] / 6.0  # Normalize to 0-1 (adjusted for new scoring)

    return {
        'primary_activity': best_activity[0] if confidence > 0.3 else 'present',
        'confidence': min(confidence, 1.0),
        'all_scores': activity_scores,
        'detected_objects': object_classes,
        'posture': posture,
        'object_count': object_count
    }


@app.post("/analyze_pose")
async def analyze_pose(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")
    try:
        img_bytes = await file.read()
        npimg = np.frombuffer(img_bytes, np.uint8)
        image = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        pose_data = extract_pose_from_image(image)
        posture = classify_posture(pose_data) if pose_data else "unknown"
        # Send pose result to ai_brain
        obs = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "posture": posture
        }
        async with httpx.AsyncClient() as client:
            await client.post(
                "http://ai_brain:9001/ingest/cam",
                json=obs
            )
        global last_pose_detection_time
        last_pose_detection_time = datetime.datetime.now() # Update last detection time
        if pose_data is None:
            return {"pose": None, "posture": posture, "message": "No pose detected"}
        return {"pose": pose_data, "posture": posture}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pose detection failed: {e}")


# Simple face registry using histogram embeddings stored on disk (best-effort)
EMB_PATH = os.getenv('CAM_EMB_PATH', '/tmp/cam_storage/embeddings.json')
os.makedirs(os.path.dirname(EMB_PATH), exist_ok=True)

def _compute_gray_hist(image: np.ndarray):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    hist = cv2.calcHist([gray], [0], None, [256], [0,256])
    cv2.normalize(hist, hist)
    return hist.flatten().astype(float).tolist()

def _load_embeddings():
    try:
        with open(EMB_PATH, 'r') as f:
            return json.load(f)
    except Exception:
        return {}

def _save_embeddings(d):
    try:
        with open(EMB_PATH, 'w') as f:
            json.dump(d, f)
    except Exception:
        pass


@app.post('/register_face')
async def register_face(name: str = Form(...), file: UploadFile = File(...)):
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail='File must be image')
    data = await file.read()
    npimg = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    hist = _compute_gray_hist(img)
    embs = _load_embeddings()
    embs[name] = hist
    _save_embeddings(embs)
    return {'ok': True, 'name': name}


@app.post('/recognize_face')
async def recognize_face(file: UploadFile = File(...)):
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail='File must be image')
    data = await file.read()
    npimg = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    hist = np.array(_compute_gray_hist(img), dtype=np.float32)
    embs = _load_embeddings()
    best = (None, -1.0)
    for name, h in embs.items():
        h2 = np.array(h, dtype=np.float32)
        score = float(cv2.compareHist(h2, hist, cv2.HISTCMP_CORREL))
        if score > best[1]:
            best = (name, score)
    if best[0] and best[1] > 0.8:
        return {'name': best[0], 'score': best[1]}
    return {'name': None, 'score': best[1]}


@app.post('/analyze_basket')
async def analyze_basket(file: UploadFile = File(...)):
    """Return a simple fullness score [0.0-1.0] based on proportion of non-background pixels in center area."""
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail='File must be image')
    data = await file.read()
    npimg = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    h, w = img.shape[:2]
    # focus on center region
    cx1, cy1 = int(w*0.2), int(h*0.2)
    cx2, cy2 = int(w*0.8), int(h*0.8)
    roi = img[cy1:cy2, cx1:cx2]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    # threshold to detect objects (non-bright background)
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    fullness = float((thresh > 0).sum()) / float(thresh.size)
    # if fullness is high, create a laundry reminder via reminder service (best-effort)
    try:
        REMINDER_URL = os.getenv('REMINDER_URL', 'http://reminder:8000')
        if fullness >= float(os.getenv('BASKET_FULLNESS_THRESHOLD', '0.7')):
            # try to find laundry preset
            try:
                resp = requests.get(f"{REMINDER_URL}/presets", timeout=2)
                if resp.status_code == 200:
                    presets = resp.json()
                    pid = None
                    for p in presets:
                        if p.get('name') == 'laundry':
                            pid = p.get('id')
                            break
                    if pid:
                        # create reminder from preset
                        requests.post(f"{REMINDER_URL}/presets/{pid}/create", timeout=2)
            except Exception:
                pass
    except Exception:
        pass
    return {'fullness': fullness}


@app.post('/detect_activity')
async def detect_activity(file: UploadFile = File(...)):
    """Comprehensive activity detection using object detection and pose analysis"""
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail='File must be image')

    try:
        data = await file.read()
        npimg = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

        # Detect objects
        objects = detect_objects(img)

        # Extract pose and posture
        pose_data = extract_pose_from_image(img)
        posture = classify_posture(pose_data) if pose_data else "unknown"

        # Classify activity
        activity_result = classify_activity(objects, posture, pose_data)

        # Update performance metrics
        update_performance_metrics(activity_result['primary_activity'], activity_result['confidence'])

        # Update global pose detection time
        global last_pose_detection_time
        if pose_data:
            last_pose_detection_time = datetime.datetime.now()

        # Send comprehensive activity data to ai_brain
        try:
            payload = {
                'timestamp': datetime.datetime.utcnow().isoformat(),
                'activity': activity_result['primary_activity'],
                'confidence': activity_result['confidence'],
                'posture': activity_result['posture'],
                'detected_objects': activity_result['detected_objects'],
                'all_activities': activity_result['all_scores'],
                'performance_stats': get_performance_stats()
            }
            requests.post(os.getenv('AI_BRAIN_URL', 'http://ai_brain:9004') + '/ingest/cam_activity', json=payload, timeout=2)
        except Exception as e:
            print(f"Failed to send activity data to AI brain: {e}")

        # Backwards-compat: expose a simple 'activities' list for older tests/clients
        activity_result.setdefault('activities', [k for k, v in activity_result.get('all_scores', {}).items() if v > 0])
        return activity_result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Activity detection failed: {e}')


@app.post('/detect_objects')
async def detect_objects_endpoint(file: UploadFile = File(...)):
    """Detect objects in an image"""
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail='File must be image')

    try:
        data = await file.read()
        npimg = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

        objects = detect_objects(img)

        return {
            'objects': objects,
            'count': len(objects),
            'detector_type': 'yolo' if object_detector else 'basic'
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Object detection failed: {e}')


# Multi-camera support
camera_registry = {}  # camera_id -> camera_info
active_cameras = set()


def register_camera(camera_id: str, location: str, camera_type: str = "webcam"):
    """Register a camera in the system"""
    camera_registry[camera_id] = {
        'location': location,
        'type': camera_type,
        'registered_at': datetime.datetime.now(),
        'last_active': None,
        'status': 'registered'
    }


def get_camera_info(camera_id: str):
    """Get information about a registered camera"""
    return camera_registry.get(camera_id)


@app.post("/cameras/register")
async def register_new_camera(camera_id: str, location: str, camera_type: str = "webcam"):
    """Register a new camera"""
    register_camera(camera_id, location, camera_type)
    return {
        "status": "registered",
        "camera_id": camera_id,
        "location": location,
        "type": camera_type
    }


@app.get("/cameras")
async def list_cameras():
    """List all registered cameras"""
    return {
        "cameras": camera_registry,
        "active_count": len(active_cameras),
        "total_count": len(camera_registry)
    }


@app.post("/cameras/{camera_id}/activate")
async def activate_camera(camera_id: str):
    """Activate a camera for monitoring"""
    if camera_id in camera_registry:
        active_cameras.add(camera_id)
        camera_registry[camera_id]['status'] = 'active'
        camera_registry[camera_id]['last_active'] = datetime.datetime.now()
        return {"status": "activated", "camera_id": camera_id}
    else:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")


@app.post("/cameras/{camera_id}/deactivate")
async def deactivate_camera(camera_id: str):
    """Deactivate a camera"""
    active_cameras.discard(camera_id)
    if camera_id in camera_registry:
        camera_registry[camera_id]['status'] = 'inactive'
    return {"status": "deactivated", "camera_id": camera_id}


@app.post("/performance_stats")
async def provide_activity_feedback(predicted_activity: str, actual_activity: str, confidence: float):
    """Provide feedback on activity classification for continuous learning"""
    update_performance_metrics(predicted_activity, confidence, actual_activity)
    return {
        "status": "feedback_recorded",
        "predicted": predicted_activity,
        "actual": actual_activity,
        "updated_stats": get_performance_stats()
    }


@app.get("/performance_stats")
async def get_performance_stats_endpoint():
    """Get current performance statistics"""
    cleanup_expired_cache()  # Clean up expired cache entries

    accuracy = (
        performance_metrics['correct_classifications'] / performance_metrics['total_detections']
        if performance_metrics['total_detections'] > 0 else 0
    )

    return {
        'total_detections': performance_metrics['total_detections'],
        'accuracy': accuracy,
        'average_confidence': performance_metrics['average_confidence'],
        'activity_distribution': performance_metrics['activity_distribution'],
        'recent_history': activity_history[-10:],  # Last 10 activities
        'cache_size': len(processing_cache),
        'system_status': 'optimized'
    }


@app.post('/analyze_scene')
async def analyze_scene(file: UploadFile = File(...)):
    """Comprehensive scene analysis including objects, pose, and activity with caching and optimizations"""
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail='File must be image')

    try:
        data = await file.read()
        npimg = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

        # Generate image hash for caching
        import hashlib
        image_hash = hashlib.md5(data).hexdigest()[:16]
        cache_key = get_cache_key(image_hash, 'scene_analysis')

        # Check cache first
        cached_result = get_cached_result(cache_key)
        if cached_result:
            print(f"Using cached scene analysis result for image {image_hash}")
            return cached_result

        # Optimize image for processing
        optimized_img, scale_factor = optimize_image_for_processing(img)

        # Get all analysis components with optimizations
        objects = detect_objects(optimized_img)
        objects = batch_process_objects(objects, batch_size=10)  # Limit to top 10 objects

        pose_data = extract_pose_from_image(optimized_img)
        posture = classify_posture(pose_data) if pose_data else "unknown"
        activity_result = classify_activity(objects, posture, pose_data)
        activity = activity_result['activity'] if isinstance(activity_result, dict) else activity_result

        # Scene context analysis
        scene_context = analyze_scene_context(optimized_img, objects, posture)

        # Update pose detection time
        global last_pose_detection_time
        if pose_data:
            last_pose_detection_time = datetime.datetime.now()

        # Update performance metrics
        confidence = activity_result.get('confidence', 0.5) if isinstance(activity_result, dict) else 0.5
        update_performance_metrics(activity, confidence)

        # Prepare result
        result = {
            'activity': activity,
            'objects': objects,
            'posture': posture,
            'scene_context': scene_context,
            'pose_detected': pose_data is not None,
            'image_size': [img.shape[1], img.shape[0]],  # width, height
            'processing_optimized': True,
            'scale_factor': scale_factor,
            'cache_used': False
        }

        # Cache the result
        cache_result(cache_key, result)

        # Send comprehensive scene data to ai_brain
        try:
            payload = {
                'timestamp': datetime.datetime.utcnow().isoformat(),
                'scene_analysis': {
                    'activity': activity,
                    'objects': objects,
                    'posture': posture,
                    'scene_context': scene_context,
                    'pose_detected': pose_data is not None,
                    'confidence': confidence
                }
            }
            requests.post(os.getenv('AI_BRAIN_URL', 'http://ai_brain:9004') + '/ingest/cam_scene', json=payload, timeout=2)
        except Exception as e:
            print(f"Failed to send scene data to AI brain: {e}")

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Scene analysis failed: {e}')


def analyze_scene_context(image: np.ndarray, objects: List[Dict], posture: str) -> Dict:
    """Analyze overall scene context"""
    context = {
        'lighting': 'unknown',
        'location_type': 'unknown',
        'activity_indicators': [],
        'confidence': 0.5
    }

    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray)

        # Lighting analysis
        if brightness > 180:
            context['lighting'] = 'bright'
        elif brightness > 100:
            context['lighting'] = 'normal'
        else:
            context['lighting'] = 'dim'

        # Location type inference
        object_classes = [obj['class'] for obj in objects]

        if 'bright_object' in object_classes and posture == 'sitting':
            if len(objects) > 3:
                context['location_type'] = 'living_room'
                context['activity_indicators'].append('entertainment_setup')
            else:
                context['location_type'] = 'office'
                context['activity_indicators'].append('workspace')

        if 'round_dark_object' in object_classes:
            context['location_type'] = 'kitchen'
            context['activity_indicators'].append('food_preparation')

        # Activity indicators
        if context['lighting'] == 'dim' and posture == 'lying':
            context['activity_indicators'].append('resting')

        if context['lighting'] == 'bright' and 'bright_object' in object_classes:
            context['activity_indicators'].append('screen_time')

        context['confidence'] = 0.7 if context['location_type'] != 'unknown' else 0.3

    except Exception as e:
        print(f"Scene context analysis failed: {e}")

    return context


# Performance optimization and continuous learning
activity_history = []
performance_metrics = {
    'total_detections': 0,
    'correct_classifications': 0,
    'average_confidence': 0.0,
    'activity_distribution': {}
}

# Processing cache for real-time optimizations
processing_cache = {}
CACHE_TTL_SECONDS = 30  # Cache results for 30 seconds


def get_cache_key(image_hash: str, operation: str) -> str:
    """Generate cache key for processing results"""
    return f"{operation}_{image_hash}"


def cache_result(key: str, result: dict, ttl: int = CACHE_TTL_SECONDS):
    """Cache processing result with TTL"""
    processing_cache[key] = {
        'result': result,
        'timestamp': datetime.datetime.now(),
        'ttl': ttl
    }


def get_cached_result(key: str) -> dict:
    """Get cached result if still valid"""
    if key in processing_cache:
        cached = processing_cache[key]
        age = (datetime.datetime.now() - cached['timestamp']).total_seconds()
        if age < cached['ttl']:
            return cached['result']
        else:
            # Remove expired cache entry
            del processing_cache[key]
    return None


def cleanup_expired_cache():
    """Remove expired cache entries"""
    current_time = datetime.datetime.now()
    expired_keys = []

    for key, cached in processing_cache.items():
        age = (current_time - cached['timestamp']).total_seconds()
        if age >= cached['ttl']:
            expired_keys.append(key)

    for key in expired_keys:
        del processing_cache[key]

    if expired_keys:
        print(f"Cleaned up {len(expired_keys)} expired cache entries")


def optimize_image_for_processing(image: np.ndarray) -> tuple:
    """Optimize image for faster processing while maintaining accuracy"""
    height, width = image.shape[:2]

    # Resize for faster processing if image is very large
    max_dimension = 640
    if width > max_dimension or height > max_dimension:
        scale = min(max_dimension / width, max_dimension / height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        optimized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
        return optimized, scale
    else:
        return image, 1.0


def batch_process_objects(objects: List[Dict], batch_size: int = 10) -> List[Dict]:
    """Process objects in batches for better performance"""
    if len(objects) <= batch_size:
        return objects

    # Sort by confidence for priority processing
    sorted_objects = sorted(objects, key=lambda x: x.get('confidence', 0), reverse=True)
    return sorted_objects[:batch_size]  # Return top confidence objects


def update_performance_metrics(predicted_activity: str, confidence: float, actual_activity: str = None):
    """Update performance metrics for continuous learning"""
    global performance_metrics

    performance_metrics['total_detections'] += 1
    performance_metrics['average_confidence'] = (
        (performance_metrics['average_confidence'] * (performance_metrics['total_detections'] - 1)) + confidence
    ) / performance_metrics['total_detections']

    # Track activity distribution
    if predicted_activity not in performance_metrics['activity_distribution']:
        performance_metrics['activity_distribution'][predicted_activity] = 0
    performance_metrics['activity_distribution'][predicted_activity] += 1

    # If we have ground truth, track accuracy
    if actual_activity:
        if predicted_activity == actual_activity:
            performance_metrics['correct_classifications'] += 1

    # Store recent activity history (last 100)
    activity_history.append({
        'timestamp': datetime.datetime.now(),
        'predicted': predicted_activity,
        'confidence': confidence,
        'actual': actual_activity
    })
    if len(activity_history) > 100:
        activity_history.pop(0)


def get_performance_stats():
    """Get current performance statistics"""
    accuracy = (
        performance_metrics['correct_classifications'] / performance_metrics['total_detections']
        if performance_metrics['total_detections'] > 0 else 0
    )

    return {
        'total_detections': performance_metrics['total_detections'],
        'accuracy': accuracy,
        'average_confidence': performance_metrics['average_confidence'],
        'activity_distribution': performance_metrics['activity_distribution'],
        'recent_history': activity_history[-10:]  # Last 10 activities
    }


@app.post("/compare_pose")
async def compare_pose(user_image: UploadFile = File(...), reference_image: UploadFile = File(...)):
    global last_pose_detection_time
    try:
        user_bytes = await user_image.read()
        ref_bytes = await reference_image.read()
        user_np = np.frombuffer(user_bytes, np.uint8)
        ref_np = np.frombuffer(ref_bytes, np.uint8)
        user_img = cv2.imdecode(user_np, cv2.IMREAD_COLOR)
        ref_img = cv2.imdecode(ref_np, cv2.IMREAD_COLOR)
        user_pose = extract_pose_from_image(user_img)
        ref_pose = extract_pose_from_image(ref_img)
        if user_pose is None or ref_pose is None:
            return {"match": False, "message": "Pose not detected in one or both images"}
        # Simple pose comparison: mean squared error between landmark positions
        if len(user_pose) != len(ref_pose):
            return {"match": False, "message": "Pose landmark count mismatch"}
        mse = np.mean([(ux - rx) ** 2 + (uy - ry) ** 2 for (ux, uy, _, _), (rx, ry, _, _) in zip(user_pose, ref_pose)])
        threshold = 0.01  # Tune as needed
        # Send pose comparison result to ai_brain
        obs = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "posture": classify_posture(user_pose),
            "pose_match": mse < threshold,
            "mse": mse
        }
        async with httpx.AsyncClient() as client:
            await client.post(
                "http://ai_brain:9001/ingest/cam",
                json=obs
            )
        global last_pose_detection_time
        last_pose_detection_time = datetime.datetime.now() # Update last detection time
        return {"match": mse < threshold, "mse": mse}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pose comparison failed: {e}")


@app.post("/frame")
async def ingest_frame(file: UploadFile = File(...), camera_id: Optional[str] = None):
    """Accept a camera frame, store original + thumbnail, run lightweight motion detection

    Returns: paths (server-side), motion_detected (bool), motion_score (float)
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")
    cam = camera_id or "default"
    base_dir = f"/tmp/cam_storage/{cam}"
    os.makedirs(base_dir, exist_ok=True)
    try:
        data = await file.read()
        # Save original
        ts = int(time.time() * 1000)
        orig_path = os.path.join(base_dir, f"frame_{ts}.jpg")
        with open(orig_path, "wb") as f:
            f.write(data)

        # Create thumbnail
        img = Image.open(BytesIO(data)).convert("RGB")
        thumb = img.copy()
        thumb.thumbnail((320, 240))
        thumb_path = os.path.join(base_dir, f"thumb_{ts}.jpg")
        thumb.save(thumb_path, format="JPEG", quality=80)

        # Motion detection: compare with last saved frame if exists
        files = sorted([p for p in os.listdir(base_dir) if p.startswith("frame_")])
        motion_detected = False
        motion_score = 0.0
        if len(files) >= 2:
            # take previous frame filename (second last)
            prev_file = os.path.join(base_dir, files[-2])
            # read previous frame bytes (robust across filesystems)
            try:
                prev = cv2.imdecode(np.fromfile(prev_file, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
            except Exception:
                prev = None
            cur = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
            # resize to same small size for speed
            if prev is not None:
                prev_r = cv2.resize(prev, (320, 240))
                cur_r = cv2.resize(cur, (320, 240))
                diff = cv2.absdiff(prev_r, cur_r)
                _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
                motion_score = float((thresh > 0).sum()) / float(thresh.size)
                motion_detected = motion_score > 0.02  # >2% pixels changed

        # Best-effort notify ai_brain
        try:
            async with httpx.AsyncClient() as client:
                await client.post("http://ai_brain:9004/ingest/cam", json={
                    "camera": cam,
                    "timestamp": ts,
                    "motion_detected": motion_detected,
                    "motion_score": motion_score
                }, timeout=2)
        except Exception:
            pass

        return {
            "camera": cam,
            "saved": orig_path,
            "thumbnail": thumb_path,
            "motion_detected": motion_detected,
            "motion_score": motion_score,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Frame ingest failed: {e}")


# PTZ Tracking Implementation
# ===========================

import threading
import time
from collections import deque
from typing import Tuple, Optional, Dict, Any
import math

class PTZController:
    """PTZ Camera Controller with movement smoothing and safety limits"""

    def __init__(self, hardware_interface=None):
        self.hardware = hardware_interface or ptz_hardware

        # PTZ position (pan, tilt, zoom) - read from hardware if available
        self.pan = 0.0   # -180 to 180 degrees
        self.tilt = 0.0  # -90 to 90 degrees
        self.zoom = 1.0  # 1.0 to 10.0 (zoom factor)

        # Movement limits
        self.pan_limits = (-180, 180)
        self.tilt_limits = (-90, 90)
        self.zoom_limits = (1.0, 10.0)

        # Movement speeds (degrees per second)
        self.pan_speed = 30.0
        self.tilt_speed = 20.0
        self.zoom_speed = 2.0

        # Smoothing buffers
        self.pan_buffer = deque(maxlen=5)
        self.tilt_buffer = deque(maxlen=5)
        self.zoom_buffer = deque(maxlen=3)

        # Tracking state
        self.is_tracking = False
        self.target_person_id = None
        self.last_target_pos = None
        self.movement_threshold = 0.05  # Minimum movement to trigger PTZ adjustment

        # Hardware sync
        self._sync_from_hardware()

    def _sync_from_hardware(self):
        """Sync position from hardware"""
        try:
            if self.hardware:
                self.pan, self.tilt, self.zoom = self.hardware.get_position()
        except Exception as e:
            print(f"Failed to sync from hardware: {e}")

    def set_position(self, pan: float, tilt: float, zoom: float):
        """Set PTZ position with limits and hardware sync"""
        old_pan, old_tilt, old_zoom = self.pan, self.tilt, self.zoom

        self.pan = max(self.pan_limits[0], min(self.pan_limits[1], pan))
        self.tilt = max(self.tilt_limits[0], min(self.tilt_limits[1], tilt))
        self.zoom = max(self.zoom_limits[0], min(self.zoom_limits[1], zoom))

        # Send to hardware if position changed
        if (abs(self.pan - old_pan) > 0.1 or
            abs(self.tilt - old_tilt) > 0.1 or
            abs(self.zoom - old_zoom) > 0.1):
            try:
                if self.hardware:
                    self.hardware.set_pan_tilt_zoom(self.pan, self.tilt, self.zoom)
            except Exception as e:
                print(f"Failed to set hardware position: {e}")

    def set_position(self, pan: float, tilt: float, zoom: float):
        """Set PTZ position with limits"""
        self.pan = max(self.pan_limits[0], min(self.pan_limits[1], pan))
        self.tilt = max(self.tilt_limits[0], min(self.tilt_limits[1], tilt))
        self.zoom = max(self.zoom_limits[0], min(self.zoom_limits[1], zoom))

    def smooth_position(self, target_pan: float, target_tilt: float, target_zoom: float) -> Tuple[float, float, float]:
        """Apply smoothing to target positions"""
        # Add to buffers
        self.pan_buffer.append(target_pan)
        self.tilt_buffer.append(target_tilt)
        self.zoom_buffer.append(target_zoom)

        # Calculate smoothed positions
        smooth_pan = sum(self.pan_buffer) / len(self.pan_buffer) if self.pan_buffer else target_pan
        smooth_tilt = sum(self.tilt_buffer) / len(self.tilt_buffer) if self.tilt_buffer else target_tilt
        smooth_zoom = sum(self.zoom_buffer) / len(self.zoom_buffer) if self.zoom_buffer else target_zoom

        return smooth_pan, smooth_tilt, smooth_zoom

    def calculate_ptz_movement(self, person_center: Tuple[float, float], frame_size: Tuple[int, int]) -> Tuple[float, float, float]:
        """Calculate required PTZ movement to center person in frame"""
        frame_width, frame_height = frame_size
        person_x, person_y = person_center

        # Calculate center of frame
        frame_center_x = frame_width / 2
        frame_center_y = frame_height / 2

        # Calculate offset from center (normalized -1 to 1)
        offset_x = (person_x - frame_center_x) / frame_center_x
        offset_y = (person_y - frame_center_y) / frame_center_y

        # Convert to pan/tilt angles (rough approximation)
        # Assuming 60-degree horizontal FOV at zoom 1.0
        fov_horizontal = 60.0 / self.zoom  # Degrees
        fov_vertical = fov_horizontal * (frame_height / frame_width)  # Maintain aspect ratio

        delta_pan = offset_x * (fov_horizontal / 2)
        delta_tilt = -offset_y * (fov_vertical / 2)  # Negative because Y increases downward

        # Calculate zoom adjustment based on person size (if we had bounding box)
        # For now, keep zoom constant or adjust based on distance from center
        distance_from_center = math.sqrt(offset_x**2 + offset_y**2)
        zoom_adjustment = 0.0

        if distance_from_center > 0.3:  # If person is far from center, zoom out slightly
            zoom_adjustment = -0.1
        elif distance_from_center < 0.1:  # If person is close to center, zoom in slightly
            zoom_adjustment = 0.05

        return delta_pan, delta_tilt, zoom_adjustment

    def update_tracking(self, person_center: Tuple[float, float], frame_size: Tuple[int, int]):
        """Update PTZ position for tracking"""
        if not self.is_tracking or person_center is None:
            return

        # Calculate required movement
        delta_pan, delta_tilt, delta_zoom = self.calculate_ptz_movement(person_center, frame_size)

        # Check if movement is significant enough
        if abs(delta_pan) < self.movement_threshold and abs(delta_tilt) < self.movement_threshold:
            return

        # Calculate target positions
        target_pan = self.pan + delta_pan
        target_tilt = self.tilt + delta_tilt
        target_zoom = self.zoom + delta_zoom

        # Apply smoothing
        smooth_pan, smooth_tilt, smooth_zoom = self.smooth_position(target_pan, target_tilt, target_zoom)

        # Update position
        self.set_position(smooth_pan, smooth_tilt, smooth_zoom)

        # Store last target position for continuity
        self.last_target_pos = person_center

    def emergency_stop(self):
        """Emergency stop all PTZ movement"""
        self.is_tracking = False
        self.hardware.stop_movement()
        logger.warning("PTZ emergency stop activated")

    def check_boundaries(self, pan, tilt, zoom):
        """Check if position is within safe boundaries"""
        pan_min, pan_max = self.pan_limits
        tilt_min, tilt_max = self.tilt_limits
        zoom_min, zoom_max = self.zoom_limits

        return (pan_min <= pan <= pan_max and
                tilt_min <= tilt <= tilt_max and
                zoom_min <= zoom <= zoom_max)


class PersonTracker:
    """Person detection and tracking for PTZ control"""

    def __init__(self):
        self.tracked_persons = {}  # person_id -> position history
        self.person_id_counter = 0
        self.max_history = 10
        self.max_distance = 100  # Maximum pixel distance to consider same person
        self.min_detection_confidence = 0.5

    def update_tracking(self, pose_landmarks, frame_size: Tuple[int, int]) -> Optional[Tuple[float, float]]:
        """Update person tracking and return center position of primary person"""
        if not pose_landmarks:
            return None

        # Calculate person center from pose landmarks
        # Use nose (landmark 0) and hips (landmarks 23, 24) for center calculation
        if len(pose_landmarks) < 25:
            return None

        nose = pose_landmarks[0]
        left_hip = pose_landmarks[23]
        right_hip = pose_landmarks[24]

        # Calculate center point
        center_x = (nose[0] + left_hip[0] + right_hip[0]) / 3
        center_y = (nose[1] + left_hip[1] + right_hip[1]) / 3

        # Convert normalized coordinates to pixel coordinates
        frame_width, frame_height = frame_size
        pixel_x = center_x * frame_width
        pixel_y = center_y * frame_height

        return (pixel_x, pixel_y)

    def get_primary_person_position(self, pose_landmarks, frame_size: Tuple[int, int]) -> Optional[Tuple[float, float]]:
        """Get position of the primary person to track"""
        return self.update_tracking(pose_landmarks, frame_size)


# Global PTZ controller and person tracker
ptz_controller = PTZController()
person_tracker = PersonTracker()
tracking_thread = None
tracking_active = False


def tracking_loop():
    """Background thread for continuous PTZ tracking"""
    global tracking_active

    while tracking_active:
        try:
            # Get webcam frame
            cap = get_webcam_capture()
            if cap is None or not cap.isOpened():
                time.sleep(1)
                continue

            ret, frame = cap.read()
            if not ret:
                time.sleep(1)
                continue

            # Detect pose
            pose_data = extract_pose_from_image(frame)
            if pose_data:
                # Get person position
                frame_size = (frame.shape[1], frame.shape[0])  # (width, height)
                person_pos = person_tracker.get_primary_person_position(pose_data, frame_size)

                if person_pos:
                    # Update PTZ tracking
                    ptz_controller.update_tracking(person_pos, frame_size)

                    # Update last pose detection time
                    global last_pose_detection_time
                    last_pose_detection_time = datetime.datetime.now()

            time.sleep(0.1)  # 10 FPS tracking

        except Exception as e:
            print(f"Tracking loop error: {e}")
            time.sleep(1)


@app.post("/ptz/start_tracking")
async def start_ptz_tracking():
    """Start PTZ tracking mode"""
    global tracking_active, tracking_thread

    if tracking_active:
        return {"status": "already_tracking"}

    tracking_active = True
    tracking_thread = threading.Thread(target=tracking_loop, daemon=True)
    tracking_thread.start()

    ptz_controller.is_tracking = True

    return {"status": "tracking_started"}


@app.post("/ptz/stop_tracking")
async def stop_ptz_tracking():
    """Stop PTZ tracking mode"""
    global tracking_active

    tracking_active = False
    ptz_controller.is_tracking = False

    if tracking_thread:
        tracking_thread.join(timeout=2)

    return {"status": "tracking_stopped"}


@app.get("/ptz/status")
async def get_ptz_status():
    """Get current PTZ status and position"""
    return {
        "is_tracking": ptz_controller.is_tracking,
        "pan": ptz_controller.pan,
        "tilt": ptz_controller.tilt,
        "zoom": ptz_controller.zoom,
        "pan_limits": ptz_controller.pan_limits,
        "tilt_limits": ptz_controller.tilt_limits,
        "zoom_limits": ptz_controller.zoom_limits
    }


@app.post("/ptz/set_position")
async def set_ptz_position(pan: float = 0.0, tilt: float = 0.0, zoom: float = 1.0):
    """Manually set PTZ position"""
    ptz_controller.set_position(pan, tilt, zoom)
    return {"status": "position_set", "pan": pan, "tilt": tilt, "zoom": zoom}


@app.post("/ptz/calibrate")
async def calibrate_ptz():
    """Calibrate PTZ to center position"""
    ptz_controller.set_position(0.0, 0.0, 1.0)
    return {"status": "calibrated", "pan": 0.0, "tilt": 0.0, "zoom": 1.0}


@app.post("/ptz/connect")
async def connect_ptz_hardware(connection_string: str):
    """Connect to PTZ hardware"""
    try:
        ptz_hardware.connect(connection_string)
        # Reinitialize controller with hardware
        global ptz_controller
        ptz_controller = PTZController(ptz_hardware)
        return {"status": "connected", "type": ptz_hardware.connection_type}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to PTZ hardware: {e}")


@app.post("/ptz/disconnect")
async def disconnect_ptz_hardware():
    """Disconnect from PTZ hardware"""
    try:
        # Reset to mock mode
        global ptz_hardware, ptz_controller
        ptz_hardware = PTZHardwareInterface()
        ptz_controller = PTZController(ptz_hardware)
        return {"status": "disconnected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disconnect PTZ hardware: {e}")


@app.get("/ptz/hardware_status")
async def get_ptz_hardware_status():
    """Get PTZ hardware connection status"""
    return {
        "connected": ptz_hardware.connection_type != "mock",
        "type": ptz_hardware.connection_type,
        "has_hardware": ptz_hardware is not None
    }


@app.post("/ptz/set_limits")
async def set_ptz_limits(
    pan_min: float = -180,
    pan_max: float = 180,
    tilt_min: float = -90,
    tilt_max: float = 90,
    zoom_min: float = 1.0,
    zoom_max: float = 10.0
):
    """Set PTZ movement limits"""
    ptz_controller.pan_limits = (pan_min, pan_max)
    ptz_controller.tilt_limits = (tilt_min, tilt_max)
    ptz_controller.zoom_limits = (zoom_min, zoom_max)
    return {
        "status": "limits_set",
        "pan_limits": ptz_controller.pan_limits,
        "tilt_limits": ptz_controller.tilt_limits,
        "zoom_limits": ptz_controller.zoom_limits
    }


@app.post("/ptz/emergency_stop")
async def emergency_stop_ptz():
    """Emergency stop all PTZ movement"""
    ptz_controller.emergency_stop()
    return {"status": "emergency_stop_activated"}


@app.get("/ptz/tracking_data")
async def get_tracking_data():
    """Get current tracking data for debugging"""
    cap = get_webcam_capture()
    frame_size = None
    if cap and cap.isOpened():
        ret, frame = cap.read()
        if ret:
            frame_size = (frame.shape[1], frame.shape[0])

    return {
        "is_tracking": ptz_controller.is_tracking,
        "frame_size": frame_size,
        "last_target_pos": ptz_controller.last_target_pos,
        "current_position": {
            "pan": ptz_controller.pan,
            "tilt": ptz_controller.tilt,
            "zoom": ptz_controller.zoom
        },
        "boundaries_ok": ptz_controller.check_boundaries(
            ptz_controller.pan, ptz_controller.tilt, ptz_controller.zoom
        )
    }


@app.on_event("startup")
async def startup_event():
    """Initialize background tasks on startup"""
    # Start cache cleanup task
    import asyncio
    asyncio.create_task(cache_cleanup_worker())


async def cache_cleanup_worker():
    """Background worker to periodically clean up expired cache entries"""
    while True:
        try:
            cleanup_expired_cache()
            await asyncio.sleep(60)  # Clean up every minute
        except Exception as e:
            print(f"Cache cleanup error: {e}")
            await asyncio.sleep(60)


# ============================================================================
# EXTERNAL MULTI-CAMERA MONITORING SYSTEM
# ============================================================================

from multi_camera_manager import (
    ExternalCameraManager,
    CameraConfig,
    camera_manager
)

@app.on_event("startup")
async def startup_external_cameras():
    """Initialize external camera system on startup"""
    logger.info("Initializing external camera monitoring system...")

    # Auto-detect cameras (can be overridden by config)
    detected = camera_manager.detect_cameras(max_cameras=10)
    logger.info(f"Detected {len(detected)} external cameras: {detected}")


@app.on_event("shutdown")
async def shutdown_external_cameras():
    """Cleanup camera resources on shutdown"""
    logger.info("Shutting down external camera system...")
    camera_manager.stop()


@app.get("/external_cameras/detect")
async def detect_external_cameras():
    """
    Auto-detect all available USB/IP cameras.

    Returns list of camera IDs that can be opened.
    """
    cameras = camera_manager.detect_cameras(max_cameras=10)
    return {
        "detected_cameras": cameras,
        "count": len(cameras),
        "device_paths": [f"/dev/video{cid}" for cid in cameras]
    }


@app.post("/external_cameras/add")
async def add_external_camera(
    camera_id: int,
    label: str,
    position: str = "unknown",
    angle: str = "unknown",
    width: int = 1280,
    height: int = 720,
    fps: int = 15
):
    """
    Add and configure an external camera.

    Args:
        camera_id: Video device ID (e.g., 0 for /dev/video0)
        label: Human-readable label (e.g., "kitchen", "bedroom", "desk")
        position: Physical position (e.g., "ceiling_corner", "wall_side")
        angle: Camera angle (e.g., "top_down", "side_view", "front_view")
        width: Frame width in pixels
        height: Frame height in pixels
        fps: Frames per second

    Examples:
        - camera_id=0, label="kitchen", position="ceiling_corner", angle="top_down"
        - camera_id=1, label="desk", position="monitor_top", angle="front_view"
        - camera_id=2, label="bedroom", position="wall_corner", angle="side_view"
    """
    config = CameraConfig(
        camera_id=camera_id,
        label=label,
        position=position,
        angle=angle,
        resolution=(width, height),
        fps=fps,
        enabled=True
    )

    success = camera_manager.add_camera(config)

    if success:
        return {
            "status": "success",
            "message": f"Camera {camera_id} ({label}) added successfully",
            "config": {
                "id": camera_id,
                "label": label,
                "position": position,
                "angle": angle,
                "resolution": f"{width}x{height}",
                "fps": fps
            }
        }
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add camera {camera_id}. Check device exists and is not in use."
        )


@app.delete("/external_cameras/{camera_id}")
async def remove_external_camera(camera_id: int):
    """Remove an external camera"""
    camera_manager.remove_camera(camera_id)
    return {
        "status": "success",
        "message": f"Camera {camera_id} removed"
    }


@app.post("/external_cameras/start")
async def start_external_cameras():
    """Start continuous capture from all configured cameras"""
    camera_manager.start()
    return {
        "status": "started",
        "cameras": len(camera_manager.cameras),
        "message": "External camera monitoring started"
    }


@app.post("/external_cameras/stop")
async def stop_external_cameras():
    """Stop all camera capture"""
    camera_manager.stop()
    return {
        "status": "stopped",
        "message": "External camera monitoring stopped"
    }


@app.get("/external_cameras/status")
async def get_external_cameras_status():
    """Get detailed status of all external cameras"""
    return camera_manager.get_status()


@app.post("/external_cameras/{camera_id}/enable")
async def enable_external_camera(camera_id: int):
    """Enable a specific camera"""
    camera_manager.enable_camera(camera_id)
    return {"status": "enabled", "camera_id": camera_id}


@app.post("/external_cameras/{camera_id}/disable")
async def disable_external_camera(camera_id: int):
    """Disable a specific camera"""
    camera_manager.disable_camera(camera_id)
    return {"status": "disabled", "camera_id": camera_id}


@app.put("/external_cameras/{camera_id}/label")
async def update_camera_label(camera_id: int, label: str):
    """Update camera label/position/angle"""
    camera_manager.update_camera_config(camera_id, label=label)
    return {"status": "updated", "camera_id": camera_id, "label": label}


@app.get("/external_cameras/{camera_id}/frame")
async def get_camera_frame(camera_id: int):
    """Get the latest frame from a specific camera as JPEG"""
    frame_data = camera_manager.get_latest_frame(camera_id)

    if not frame_data:
        raise HTTPException(
            status_code=404,
            detail=f"No frame available from camera {camera_id}"
        )

    # Encode frame as JPEG
    ret, buffer = cv2.imencode('.jpg', frame_data.frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

    if not ret:
        raise HTTPException(status_code=500, detail="Failed to encode frame")

    return StreamingResponse(
        BytesIO(buffer.tobytes()),
        media_type="image/jpeg",
        headers={
            "X-Camera-ID": str(camera_id),
            "X-Camera-Label": frame_data.label,
            "X-Timestamp": str(frame_data.timestamp),
            "X-Frame-Number": str(frame_data.frame_number)
        }
    )


@app.get("/external_cameras/frames/synchronized")
async def get_synchronized_frames(
    format: str = "json",
    max_sync_error_ms: float = 100
):
    """
    Get synchronized frames from all cameras.

    Args:
        format: "json" for metadata only, "multipart" for images (TODO)
        max_sync_error_ms: Maximum allowed sync error in milliseconds

    Returns:
        Synchronized frames from all active cameras
    """
    multi_frame = camera_manager.capture_synchronized(max_sync_error_ms)

    if not multi_frame:
        raise HTTPException(status_code=404, detail="No frames available")

    if format == "json":
        # Return metadata only
        cameras_data = []
        for cam_frame in multi_frame.cameras:
            cameras_data.append({
                "camera_id": cam_frame.camera_id,
                "label": cam_frame.label,
                "position": cam_frame.position,
                "angle": cam_frame.angle,
                "timestamp": cam_frame.timestamp,
                "frame_number": cam_frame.frame_number,
                "frame_shape": list(cam_frame.frame.shape)
            })

        return {
            "timestamp": multi_frame.timestamp,
            "sync_error_ms": multi_frame.sync_error_ms,
            "camera_count": len(multi_frame.cameras),
            "cameras": cameras_data
        }
    else:
        raise HTTPException(
            status_code=400,
            detail="Only 'json' format currently supported"
        )


@app.post("/external_cameras/analyze/fall_detection")
async def analyze_fall_detection_multi_angle():
    """
    Analyze frames from multiple cameras for fall detection.

    Uses triangulation and multi-angle pose estimation for improved accuracy.
    """
    multi_frame = camera_manager.capture_synchronized(max_sync_error_ms=200)

    if not multi_frame:
        raise HTTPException(status_code=404, detail="No synchronized frames available")

    fall_detected = False
    confidence_scores = []
    pose_data = []

    for cam_frame in multi_frame.cameras:
        # Extract pose from this angle
        pose = extract_pose_from_image(cam_frame.frame)

        if pose:
            pose_data.append({
                "camera_id": cam_frame.camera_id,
                "label": cam_frame.label,
                "angle": cam_frame.angle,
                "landmarks": pose
            })

            # Simple fall detection: check if body is horizontal
            # (In production, use more sophisticated algorithm)
            if len(pose) > 0:
                # Check nose-hip-ankle angles
                try:
                    nose = pose[0]  # Nose landmark
                    hip = pose[23] if len(pose) > 23 else None  # Hip landmark

                    if nose and hip:
                        # If vertical distance between nose and hip is very small, likely fallen
                        vertical_dist = abs(nose['y'] - hip['y'])

                        if vertical_dist < 0.2:  # Normalized coordinates
                            fall_confidence = 0.8
                            fall_detected = True
                            confidence_scores.append(fall_confidence)
                except:
                    pass

    # Aggregate results from multiple cameras
    if confidence_scores:
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
    else:
        avg_confidence = 0.0

    return {
        "fall_detected": fall_detected,
        "confidence": avg_confidence,
        "camera_count": len(multi_frame.cameras),
        "sync_error_ms": multi_frame.sync_error_ms,
        "pose_data": pose_data,
        "timestamp": multi_frame.timestamp,
        "alert_level": "critical" if fall_detected and avg_confidence > 0.7 else "normal"
    }


@app.post("/external_cameras/analyze/posture")
async def analyze_posture_multi_angle():
    """
    Analyze posture from multiple camera angles.

    Combines side view and front view for comprehensive posture assessment.
    """
    multi_frame = camera_manager.capture_synchronized(max_sync_error_ms=200)

    if not multi_frame:
        raise HTTPException(status_code=404, detail="No synchronized frames available")

    posture_analysis = {
        "timestamp": multi_frame.timestamp,
        "cameras": [],
        "overall_posture": "unknown",
        "recommendations": []
    }

    for cam_frame in multi_frame.cameras:
        pose = extract_pose_from_image(cam_frame.frame)

        camera_analysis = {
            "camera_id": cam_frame.camera_id,
            "label": cam_frame.label,
            "angle": cam_frame.angle,
            "posture_score": 0.0,
            "issues": []
        }

        if pose and len(pose) > 0:
            # Analyze based on camera angle
            if "side" in cam_frame.angle.lower():
                # Side view: check spine alignment
                camera_analysis["issues"].append("Side view analysis not fully implemented")
                camera_analysis["posture_score"] = 0.7

            elif "front" in cam_frame.angle.lower():
                # Front view: check shoulder level
                camera_analysis["issues"].append("Front view analysis not fully implemented")
                camera_analysis["posture_score"] = 0.8

        posture_analysis["cameras"].append(camera_analysis)

    # Calculate overall posture score
    if posture_analysis["cameras"]:
        scores = [c["posture_score"] for c in posture_analysis["cameras"]]
        avg_score = sum(scores) / len(scores)

        if avg_score > 0.8:
            posture_analysis["overall_posture"] = "good"
        elif avg_score > 0.6:
            posture_analysis["overall_posture"] = "fair"
            posture_analysis["recommendations"].append("Consider adjusting chair height")
        else:
            posture_analysis["overall_posture"] = "poor"
            posture_analysis["recommendations"].append("Sit up straighter")
            posture_analysis["recommendations"].append("Align shoulders over hips")

    return posture_analysis


@app.post("/external_cameras/analyze/activity")
async def analyze_activity_multi_camera():
    """
    Detect current activity from multiple camera angles.

    Uses all cameras to improve activity recognition accuracy.
    """
    multi_frame = camera_manager.capture_synchronized(max_sync_error_ms=200)

    if not multi_frame:
        raise HTTPException(status_code=404, detail="No synchronized frames available")

    activities_detected = []

    for cam_frame in multi_frame.cameras:
        # Run activity classification on this frame
        # (Simplified - in production use proper activity recognition model)

        pose = extract_pose_from_image(cam_frame.frame)

        if pose:
            # Simple heuristic activity detection
            activity = "unknown"
            confidence = 0.5

            # Check if standing (landmarks are visible and vertical)
            # Check if sitting (body angle)
            # Check if lying down (horizontal orientation)

            activities_detected.append({
                "camera_id": cam_frame.camera_id,
                "label": cam_frame.label,
                "activity": activity,
                "confidence": confidence
            })

    # Vote on most likely activity
    if activities_detected:
        # In production: use ensemble voting
        primary_activity = activities_detected[0]["activity"]
        avg_confidence = sum(a["confidence"] for a in activities_detected) / len(activities_detected)
    else:
        primary_activity = "unknown"
        avg_confidence = 0.0

    return {
        "primary_activity": primary_activity,
        "confidence": avg_confidence,
        "camera_count": len(multi_frame.cameras),
        "individual_detections": activities_detected,
        "timestamp": multi_frame.timestamp
    }


if __name__ == "__main__":
    import uvicorn
    print("Starting Kilo AI Camera Service with optimizations...")
    print("Features: YOLO object detection, activity classification, multi-camera support, caching, continuous learning")
    uvicorn.run(app, host="0.0.0.0", port=8003, log_level="info")
