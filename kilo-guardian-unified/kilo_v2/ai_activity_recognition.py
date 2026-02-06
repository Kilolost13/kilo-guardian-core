"""
AI Activity Recognition for Kilo Guardian Memory Assistant.

Uses MediaPipe Pose for lightweight, CPU-friendly activity detection.
Optimized for TBI users to track daily activities:
- Medication taking
- Eating/drinking
- Sleeping/resting
- Sitting/standing/walking
- Cooking
- Personal care

Hardware Requirements:
- CPU only (no GPU needed)
- Works on i5-3470 and similar low-end hardware
- Real-time capable (~30 FPS on modest CPUs)
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import numpy as np

logger = logging.getLogger("ActivityRecognition")

# Try to import MediaPipe (optional dependency)
try:
    import mediapipe as mp

    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    logger.warning(
        "⚠️ MediaPipe not installed. Activity recognition will use fallback mode."
    )
    logger.warning("Install with: pip install mediapipe")


class AIActivityRecognitionModel:
    """
    AI-powered activity recognition using MediaPipe Pose.

    Technical decisions:
    1. MediaPipe Pose - Lightweight, CPU-friendly, no GPU needed
    2. Rule-based classification - Deterministic, explainable, no training needed
    3. Pose landmark analysis - Extract skeleton, analyze angles and positions
    4. Activity confidence scoring - Fuzzy logic for uncertain cases
    """

    # Activity labels (TBI-relevant activities)
    ACTIVITIES = {
        "medication_taking": "Taking Medication",
        "eating": "Eating",
        "drinking": "Drinking",
        "sleeping": "Sleeping/Lying Down",
        "sitting": "Sitting",
        "standing": "Standing",
        "walking": "Walking",
        "cooking": "Cooking",
        "personal_care": "Personal Care",
        "unknown": "Unknown Activity",
    }

    def __init__(self):
        """Initialize the activity recognition model."""
        self.pose_detector = None
        self.last_activity = "unknown"
        self.activity_confidence = 0.0
        self.pose_history = []  # Track poses over time for better detection
        self.max_history = 30  # Keep last 30 frames (~1 second at 30fps)

        if MEDIAPIPE_AVAILABLE:
            try:
                # Initialize MediaPipe Pose
                mp_pose = mp.solutions.pose
                self.pose_detector = mp_pose.Pose(
                    static_image_mode=False,
                    model_complexity=0,  # Fastest model (0=lite, 1=full, 2=heavy)
                    smooth_landmarks=True,
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5,
                )
                logger.info("✅ MediaPipe Pose initialized (CPU mode, lite model)")
            except Exception as e:
                logger.error(f"❌ Failed to initialize MediaPipe: {e}")
                self.pose_detector = None
        else:
            logger.warning("MediaPipe not available - using fallback detection")

    def predict_activity(self, frame: Any) -> str:
        """
        Predict activity from video frame.

        Args:
            frame: numpy array (BGR image from camera)

        Returns:
            Activity label string
        """
        result = self.predict_activity_with_confidence(frame)
        return result["activity"]

    def predict_activity_with_confidence(self, frame: Any) -> Dict[str, Any]:
        """
        Predict activity with confidence score.

        Args:
            frame: numpy array (BGR image from camera)

        Returns:
            Dictionary with:
                - activity: Activity label
                - confidence: Confidence score (0-100)
                - details: Additional detection details
        """
        if self.pose_detector is None or not MEDIAPIPE_AVAILABLE:
            # Fallback mode
            return {
                "activity": "unknown",
                "confidence": 0,
                "details": "MediaPipe not available",
            }

        try:
            # Convert BGR to RGB (MediaPipe uses RGB)
            import cv2

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Run pose detection
            results = self.pose_detector.process(rgb_frame)

            if not results.pose_landmarks:
                # No person detected
                return {
                    "activity": "unknown",
                    "confidence": 0,
                    "details": "No person detected in frame",
                }

            # Extract pose landmarks
            landmarks = results.pose_landmarks.landmark

            # Analyze pose and classify activity
            activity_scores = self._analyze_pose(landmarks, frame.shape)

            # Get best activity
            best_activity = max(activity_scores.items(), key=lambda x: x[1])
            activity_name = best_activity[0]
            confidence = best_activity[1]

            # Update history
            self._update_history(activity_name, confidence)

            # Apply temporal smoothing (reduce jitter)
            smoothed_activity = self._get_smoothed_activity()

            self.last_activity = smoothed_activity
            self.activity_confidence = confidence

            return {
                "activity": smoothed_activity,
                "confidence": int(confidence),
                "details": f"Detected via pose analysis",
                "raw_scores": activity_scores,
            }

        except Exception as e:
            logger.error(f"Activity recognition error: {e}", exc_info=True)
            return {
                "activity": "unknown",
                "confidence": 0,
                "details": f"Error: {str(e)}",
            }

    def _analyze_pose(
        self, landmarks, frame_shape: Tuple[int, int, int]
    ) -> Dict[str, float]:
        """
        Analyze pose landmarks to classify activity.

        Returns dictionary of activity -> confidence scores.
        """
        scores = {activity: 0.0 for activity in self.ACTIVITIES.keys()}

        # Get key landmarks (MediaPipe Pose landmark indices)
        nose = landmarks[0]
        left_shoulder = landmarks[11]
        right_shoulder = landmarks[12]
        left_elbow = landmarks[13]
        right_elbow = landmarks[14]
        left_wrist = landmarks[15]
        right_wrist = landmarks[16]
        left_hip = landmarks[23]
        right_hip = landmarks[24]
        left_knee = landmarks[25]
        right_knee = landmarks[26]
        left_ankle = landmarks[27]
        right_ankle = landmarks[28]

        # Calculate average hip and shoulder positions
        hip_y = (left_hip.y + right_hip.y) / 2
        shoulder_y = (left_shoulder.y + right_shoulder.y) / 2
        nose_y = nose.y

        # Calculate torso angle (for sitting/standing/lying detection)
        torso_vertical = abs(shoulder_y - hip_y)

        # Rule 1: Sleeping/Lying Down
        # Torso is nearly horizontal (minimal Y difference between shoulders and hips)
        if torso_vertical < 0.15:
            scores["sleeping"] = 85

        # Rule 2: Sitting
        # Torso vertical, knees bent, hips low
        elif torso_vertical > 0.15 and hip_y > 0.6:
            # Check knee bend
            left_knee_bend = self._calculate_angle(left_hip, left_knee, left_ankle)
            right_knee_bend = self._calculate_angle(right_hip, right_knee, right_ankle)
            avg_knee_bend = (left_knee_bend + right_knee_bend) / 2

            if 70 < avg_knee_bend < 130:  # Knees are bent
                scores["sitting"] = 75

        # Rule 3: Standing
        # Torso vertical, legs mostly straight, hips high
        elif torso_vertical > 0.15 and 0.3 < hip_y < 0.6:
            scores["standing"] = 70

        # Rule 4: Medication Taking / Eating / Drinking
        # Hand near face
        left_hand_near_face = self._distance(left_wrist, nose) < 0.2
        right_hand_near_face = self._distance(right_wrist, nose) < 0.2

        if left_hand_near_face or right_hand_near_face:
            # Check if standing/sitting (not lying down)
            if torso_vertical > 0.15:
                scores["medication_taking"] = 65
                scores["eating"] = 60
                scores["drinking"] = 60

        # Rule 5: Walking
        # Alternating leg movement (would need temporal analysis, simplified here)
        # For now, detect if one leg is forward (simplified)
        left_leg_forward = left_ankle.z < right_ankle.z - 0.1
        right_leg_forward = right_ankle.z < left_ankle.z - 0.1

        if (left_leg_forward or right_leg_forward) and torso_vertical > 0.15:
            scores["walking"] = 55

        # Rule 6: Cooking
        # Hands at waist/chest level, standing
        hands_mid_level = (left_wrist.y > hip_y and left_wrist.y < shoulder_y) or (
            right_wrist.y > hip_y and right_wrist.y < shoulder_y
        )

        if hands_mid_level and scores["standing"] > 50:
            scores["cooking"] = 50

        # If no strong signal, mark as unknown
        if max(scores.values()) < 40:
            scores["unknown"] = 80

        return scores

    def _calculate_angle(self, point1, point2, point3) -> float:
        """
        Calculate angle between three points (in degrees).

        Args:
            point1, point2, point3: Landmark objects with x, y, z

        Returns:
            Angle in degrees
        """
        # Convert to numpy arrays
        p1 = np.array([point1.x, point1.y, point1.z])
        p2 = np.array([point2.x, point2.y, point2.z])
        p3 = np.array([point3.x, point3.y, point3.z])

        # Vectors
        v1 = p1 - p2
        v2 = p3 - p2

        # Angle
        cosine = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        angle = np.arccos(np.clip(cosine, -1.0, 1.0))

        return np.degrees(angle)

    def _distance(self, point1, point2) -> float:
        """Calculate Euclidean distance between two landmarks."""
        dx = point1.x - point2.x
        dy = point1.y - point2.y
        dz = point1.z - point2.z
        return np.sqrt(dx**2 + dy**2 + dz**2)

    def _update_history(self, activity: str, confidence: float):
        """Add activity to history for temporal smoothing."""
        self.pose_history.append(
            {
                "activity": activity,
                "confidence": confidence,
                "timestamp": datetime.now(),
            }
        )

        # Keep only recent history
        if len(self.pose_history) > self.max_history:
            self.pose_history.pop(0)

    def _get_smoothed_activity(self) -> str:
        """
        Get activity using temporal smoothing to reduce jitter.

        Uses majority voting over recent frames.
        """
        if len(self.pose_history) < 5:
            # Not enough history, return latest
            return self.pose_history[-1]["activity"] if self.pose_history else "unknown"

        # Count activity occurrences in recent history
        activity_counts = {}
        recent_frames = self.pose_history[-10:]  # Last 10 frames

        for frame in recent_frames:
            activity = frame["activity"]
            activity_counts[activity] = activity_counts.get(activity, 0) + 1

        # Return most common activity
        return max(activity_counts.items(), key=lambda x: x[1])[0]

    def get_activity_name(self, activity_code: str) -> str:
        """Convert activity code to human-readable name."""
        return self.ACTIVITIES.get(activity_code, "Unknown Activity")

    def log_activity(self, activity: str, confidence: float):
        """
        Log detected activity (can be connected to memory core).

        Args:
            activity: Activity code
            confidence: Confidence score
        """
        if confidence > 60:  # Only log confident detections
            activity_name = self.get_activity_name(activity)
            logger.info(
                f"Activity detected: {activity_name} ({confidence}% confidence)"
            )

            # TODO: Integrate with memory core to log activity
            # from kilo_v2.memory_core.db import get_memory_db
            # db = get_memory_db()
            # db.add_memory_event(
            #     event_text=f"User {activity_name.lower()}",
            #     event_type="activity"
            # )


# Singleton instance
_ai_model_instance: Optional[AIActivityRecognitionModel] = None


def get_ai_activity_model() -> AIActivityRecognitionModel:
    """Get the global AI activity recognition model instance."""
    global _ai_model_instance
    if _ai_model_instance is None:
        _ai_model_instance = AIActivityRecognitionModel()
    return _ai_model_instance


# Test function
if __name__ == "__main__":
    import sys

    import cv2

    print("Testing AI Activity Recognition...")
    print("Press 'q' to quit\n")

    # Initialize model
    model = get_ai_activity_model()

    if not MEDIAPIPE_AVAILABLE:
        print("ERROR: MediaPipe not available. Install with: pip install mediapipe")
        sys.exit(1)

    # Open webcam
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("ERROR: Could not open webcam")
        sys.exit(1)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Predict activity
        result = model.predict_activity_with_confidence(frame)

        # Display result on frame
        activity_name = model.get_activity_name(result["activity"])
        text = f"{activity_name}: {result['confidence']}%"
        cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        cv2.imshow("Activity Recognition Test", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
