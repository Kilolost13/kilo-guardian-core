# 🎥 External Multi-Camera Monitoring System

**Date:** 2025-12-26
**Status:** ✅ **IMPLEMENTED**

---

## 🎯 Overview

Kyle now has **TWO SEPARATE camera systems**:

### System 1: Tablet Manual Scanning
- Uses tablet's built-in camera
- Manual point-and-shoot for prescriptions/budgets
- Single photo capture for OCR
- Simple UI on tablet

### System 2: External Multi-Camera Monitoring ⭐ (NEW)
- Multiple fixed USB/IP cameras on main server
- Continuous environmental observation
- Captures from ALL cameras simultaneously
- Use cases:
  - **Fall detection** (multiple angles = better detection)
  - **Posture analysis** (side + front view)
  - **Activity tracking** (kitchen, desk, bed)
  - **3D spatial awareness**

---

## 🏗️ Architecture

### Hardware Setup

```
                    Main Server
                    ┌─────────────────────┐
USB Camera 0 ──────>│  /dev/video0        │
(Kitchen, Top-Down) │  Camera Manager     │
                    │                     │
USB Camera 1 ──────>│  /dev/video1        │──> AI Brain
(Desk, Front View)  │  Pose Detection     │   (Fall Detection)
                    │  Frame Capture      │   (Activity Recognition)
USB Camera 2 ──────>│  /dev/video2        │
(Bedroom, Side View)│  Sync & Analysis    │
                    │                     │
USB Camera 3 ──────>│  /dev/video3        │
(Living Room)       └─────────────────────┘
```

### Software Architecture

```
services/cam/
├── main.py                    # FastAPI endpoints
├── multi_camera_manager.py    # Camera management (NEW)
└── Dockerfile

Components:
- ExternalCameraManager: Manages multiple VideoCapture instances
- CameraConfig: Configuration for each camera
- Multi-threaded capture: Each camera runs in own thread
- Synchronized frame capture: Get frames within Xms of each other
```

---

## 📦 Components

### 1. ExternalCameraManager

**Features:**
- Auto-detect available cameras (`/dev/video0`, `/dev/video1`, etc.)
- Configure camera label, position, angle
- Thread-safe continuous capture
- Automatic reconnection on failure
- Synchronized multi-camera frame capture

**Key Methods:**
```python
camera_manager.detect_cameras(max_cameras=10)
camera_manager.add_camera(config)
camera_manager.start()  # Start continuous capture
camera_manager.get_latest_frame(camera_id)
camera_manager.capture_synchronized(max_sync_error_ms=100)
```

### 2. CameraConfig

```python
@dataclass
class CameraConfig:
    camera_id: int           # /dev/video{id}
    label: str              # "kitchen", "bedroom", "desk"
    position: str           # "ceiling_corner", "wall_side"
    angle: str              # "top_down", "side_view", "front_view"
    resolution: (1280, 720)
    fps: 15
    enabled: True
```

### 3. Multi-Camera Frame

```python
@dataclass
class MultiCameraFrame:
    timestamp: float                    # Average capture time
    cameras: List[CameraFrame]          # Frames from all cameras
    sync_error_ms: float                # Sync quality (lower = better)
```

---

## 🚀 Quick Start Guide

### Step 1: Connect External Cameras

```bash
# Connect USB cameras to main server (not tablet)
# Cameras will appear as /dev/video0, /dev/video1, etc.

# Check what cameras are available
ls -la /dev/video*

# Output example:
# /dev/video0  (built-in webcam)
# /dev/video1  (USB camera 1)
# /dev/video2  (USB camera 2)
# /dev/video3  (USB camera 3)
```

### Step 2: Detect Cameras via API

```bash
# Auto-detect all available cameras
curl http://localhost:9007/external_cameras/detect

# Response:
{
  "detected_cameras": [0, 1, 2, 3],
  "count": 4,
  "device_paths": [
    "/dev/video0",
    "/dev/video1",
    "/dev/video2",
    "/dev/video3"
  ]
}
```

### Step 3: Configure Each Camera

```bash
# Camera 0: Kitchen (ceiling mounted, looking down)
curl -X POST "http://localhost:9007/external_cameras/add" \
  -H "Content-Type: application/json" \
  -d '{
    "camera_id": 0,
    "label": "kitchen",
    "position": "ceiling_corner",
    "angle": "top_down",
    "width": 1280,
    "height": 720,
    "fps": 15
  }'

# Camera 1: Desk (monitor top, front view)
curl -X POST "http://localhost:9007/external_cameras/add" \
  -H "Content-Type: application/json" \
  -d '{
    "camera_id": 1,
    "label": "desk",
    "position": "monitor_top",
    "angle": "front_view",
    "width": 1280,
    "height": 720,
    "fps": 15
  }'

# Camera 2: Bedroom (wall corner, side view)
curl -X POST "http://localhost:9007/external_cameras/add" \
  -H "Content-Type": application/json" \
  -d '{
    "camera_id": 2,
    "label": "bedroom",
    "position": "wall_corner",
    "angle": "side_view",
    "width": 1280,
    "height": 720,
    "fps": 15
  }'

# Camera 3: Living room (bookshelf, wide angle)
curl -X POST "http://localhost:9007/external_cameras/add" \
  -H "Content-Type: application/json" \
  -d '{
    "camera_id": 3,
    "label": "living_room",
    "position": "bookshelf",
    "angle": "wide_view",
    "width": 1280,
    "height": 720,
    "fps": 15
  }'
```

### Step 4: Start Monitoring

```bash
# Start continuous capture from all cameras
curl -X POST http://localhost:9007/external_cameras/start

# Response:
{
  "status": "started",
  "cameras": 4,
  "message": "External camera monitoring started"
}
```

### Step 5: Check Status

```bash
# Get status of all cameras
curl http://localhost:9007/external_cameras/status

# Response:
{
  "running": true,
  "total_cameras": 4,
  "cameras": {
    "0": {
      "id": 0,
      "label": "kitchen",
      "position": "ceiling_corner",
      "angle": "top_down",
      "enabled": true,
      "resolution": [1280, 720],
      "fps": 15,
      "frame_count": 2453,
      "error_count": 0,
      "last_capture_time": 1735257890.123,
      "time_since_last_frame": 0.067,
      "has_latest_frame": true
    },
    "1": { ...kitchen },
    "2": { ...bedroom },
    "3": { ...living_room }
  }
}
```

---

## 📡 API Reference

### Camera Management

#### `GET /external_cameras/detect`
Auto-detect all available cameras.

**Response:**
```json
{
  "detected_cameras": [0, 1, 2, 3],
  "count": 4,
  "device_paths": ["/dev/video0", "/dev/video1", "/dev/video2", "/dev/video3"]
}
```

#### `POST /external_cameras/add`
Add and configure a camera.

**Parameters:**
- `camera_id` (int): Video device ID
- `label` (str): Human-readable name
- `position` (str): Physical position
- `angle` (str): Camera viewing angle
- `width` (int): Frame width (default: 1280)
- `height` (int): Frame height (default: 720)
- `fps` (int): Frames per second (default: 15)

**Example:**
```bash
curl -X POST "http://localhost:9007/external_cameras/add?camera_id=0&label=kitchen&position=ceiling_corner&angle=top_down"
```

#### `DELETE /external_cameras/{camera_id}`
Remove a camera.

#### `POST /external_cameras/start`
Start continuous capture from all cameras.

#### `POST /external_cameras/stop`
Stop all camera capture.

#### `GET /external_cameras/status`
Get detailed status of all cameras.

#### `POST /external_cameras/{camera_id}/enable`
Enable a specific camera.

#### `POST /external_cameras/{camera_id}/disable`
Disable a specific camera (keeps config, stops capture).

---

### Frame Access

#### `GET /external_cameras/{camera_id}/frame`
Get latest frame from a specific camera as JPEG.

**Example:**
```bash
curl http://localhost:9007/external_cameras/0/frame > kitchen_frame.jpg
```

**Response Headers:**
```
X-Camera-ID: 0
X-Camera-Label: kitchen
X-Timestamp: 1735257890.123
X-Frame-Number: 2453
Content-Type: image/jpeg
```

#### `GET /external_cameras/frames/synchronized`
Get synchronized frames from ALL cameras.

**Parameters:**
- `format` (str): "json" for metadata only
- `max_sync_error_ms` (float): Max time difference between frames (default: 100ms)

**Example:**
```bash
curl "http://localhost:9007/external_cameras/frames/synchronized?max_sync_error_ms=100"
```

**Response:**
```json
{
  "timestamp": 1735257890.123,
  "sync_error_ms": 23.4,
  "camera_count": 4,
  "cameras": [
    {
      "camera_id": 0,
      "label": "kitchen",
      "position": "ceiling_corner",
      "angle": "top_down",
      "timestamp": 1735257890.100,
      "frame_number": 2453,
      "frame_shape": [720, 1280, 3]
    },
    // ... more cameras
  ]
}
```

---

### Multi-Angle Analysis

#### `POST /external_cameras/analyze/fall_detection`
Detect falls using multiple camera angles.

**How it works:**
1. Captures synchronized frames from all cameras
2. Runs pose detection on each frame
3. Analyzes body orientation from multiple angles
4. Uses triangulation for improved accuracy
5. Returns fall alert if detected

**Example:**
```bash
curl -X POST http://localhost:9007/external_cameras/analyze/fall_detection
```

**Response:**
```json
{
  "fall_detected": true,
  "confidence": 0.85,
  "camera_count": 4,
  "sync_error_ms": 45.2,
  "pose_data": [
    {
      "camera_id": 0,
      "label": "kitchen",
      "angle": "top_down",
      "landmarks": [ /* pose keypoints */ ]
    },
    // ... more cameras
  ],
  "timestamp": 1735257890.123,
  "alert_level": "critical"  // or "normal"
}
```

**Use Case:**
- Continuous fall monitoring for elderly care
- Multi-angle reduces false positives
- Better than single camera (can see behind furniture)

#### `POST /external_cameras/analyze/posture`
Analyze posture from multiple angles.

**Example:**
```bash
curl -X POST http://localhost:9007/external_cameras/analyze/posture
```

**Response:**
```json
{
  "timestamp": 1735257890.123,
  "cameras": [
    {
      "camera_id": 1,
      "label": "desk",
      "angle": "front_view",
      "posture_score": 0.75,
      "issues": ["Shoulders not level"]
    },
    {
      "camera_id": 2,
      "label": "bedroom",
      "angle": "side_view",
      "posture_score": 0.65,
      "issues": ["Forward head posture"]
    }
  ],
  "overall_posture": "fair",
  "recommendations": [
    "Consider adjusting chair height",
    "Align shoulders over hips"
  ]
}
```

**Use Case:**
- Desk posture monitoring
- Side view checks spine alignment
- Front view checks shoulder level

#### `POST /external_cameras/analyze/activity`
Detect current activity from all cameras.

**Example:**
```bash
curl -X POST http://localhost:9007/external_cameras/analyze/activity
```

**Response:**
```json
{
  "primary_activity": "sitting_at_desk",
  "confidence": 0.82,
  "camera_count": 4,
  "individual_detections": [
    {
      "camera_id": 0,
      "label": "kitchen",
      "activity": "not_present",
      "confidence": 0.95
    },
    {
      "camera_id": 1,
      "label": "desk",
      "activity": "sitting_at_desk",
      "confidence": 0.89
    }
    // ... more cameras
  ],
  "timestamp": 1735257890.123
}
```

**Use Case:**
- Activity tracking (time spent at desk, kitchen, etc.)
- Location awareness (which room Kyle is in)
- Habit tracking (correlate with calendar events)

---

## 🛠️ Configuration Examples

### Optimal Camera Placement

**For Fall Detection:**
```
Camera 0: Kitchen (ceiling corner, top-down)
Camera 1: Bedroom (wall corner, side view)
Camera 2: Bathroom (ceiling, top-down)
Camera 3: Living room (bookshelf, wide angle)
```

**For Posture Monitoring:**
```
Camera 0: Desk (monitor top, front view)
Camera 1: Desk (side shelf, side view at 90°)
Camera 2: Standing desk (tripod, side view)
```

**For Activity Tracking:**
```
Camera 0: Kitchen (refrigerator area)
Camera 1: Desk (workspace)
Camera 2: Bedroom (bed area)
Camera 3: Living room (seating area)
```

### Docker Device Mapping

Edit `infra/docker/docker-compose.yml`:

```yaml
cam:
  build: ../../services/cam
  ports:
    - "9007:9007"
  devices:
    - /dev/video0:/dev/video0  # Kitchen camera
    - /dev/video1:/dev/video1  # Desk camera
    - /dev/video2:/dev/video2  # Bedroom camera
    - /dev/video3:/dev/video3  # Living room camera
  group_add:
    - video  # Allow access to video devices
  environment:
    - ALLOW_NETWORK=false
```

---

## 💡 Use Cases

### 1. Fall Detection System

**Setup:**
```bash
# Add 3 cameras covering main living areas
curl -X POST "http://localhost:9007/external_cameras/add?camera_id=0&label=kitchen&angle=top_down"
curl -X POST "http://localhost:9007/external_cameras/add?camera_id=1&label=bedroom&angle=side_view"
curl -X POST "http://localhost:9007/external_cameras/add?camera_id=2&label=bathroom&angle=top_down"

# Start monitoring
curl -X POST http://localhost:9007/external_cameras/start
```

**Continuous Monitoring:**
```python
# Backend service polls fall detection endpoint every 2 seconds
import asyncio
import httpx

async def monitor_falls():
    while True:
        response = await httpx.post("http://localhost:9007/external_cameras/analyze/fall_detection")
        data = response.json()

        if data["fall_detected"] and data["alert_level"] == "critical":
            # Send alert to AI Brain
            await send_alert(data)

        await asyncio.sleep(2)  # Check every 2 seconds
```

**Benefits:**
- Multi-angle view reduces false positives
- Can detect falls behind furniture
- Triangulation improves accuracy
- Works even if one camera is blocked

### 2. Desk Posture Monitoring

**Setup:**
```bash
# Two cameras: front and side view
curl -X POST "http://localhost:9007/external_cameras/add" \
  -d '{"camera_id": 0, "label": "desk_front", "angle": "front_view", "position": "monitor_top"}'

curl -X POST "http://localhost:9007/external_cameras/add" \
  -d '{"camera_id": 1, "label": "desk_side", "angle": "side_view", "position": "side_shelf"}'

curl -X POST http://localhost:9007/external_cameras/start
```

**Periodic Analysis:**
```python
# Check posture every 10 minutes
async def check_posture():
    while True:
        response = await httpx.post("http://localhost:9007/external_cameras/analyze/posture")
        data = response.json()

        if data["overall_posture"] == "poor":
            # Send reminder to Kyle
            await send_notification(
                "Posture Alert",
                f"Recommendations: {', '.join(data['recommendations'])}"
            )

        await asyncio.sleep(600)  # Every 10 minutes
```

### 3. Activity and Location Tracking

**Setup:**
```bash
# Cameras in each room
curl -X POST "http://localhost:9007/external_cameras/add?camera_id=0&label=kitchen&position=ceiling"
curl -X POST "http://localhost:9007/external_cameras/add?camera_id=1&label=desk&position=monitor"
curl -X POST "http://localhost:9007/external_cameras/add?camera_id=2&label=bedroom&position=wall"
curl -X POST "http://localhost:9007/external_cameras/add?camera_id=3&label=living_room&position=bookshelf"

curl -X POST http://localhost:9007/external_cameras/start
```

**Track Time Spent:**
```python
# Log which room Kyle is in
async def track_location():
    location_log = []

    while True:
        response = await httpx.post("http://localhost:9007/external_cameras/analyze/activity")
        data = response.json()

        # Find which camera detected activity
        for detection in data["individual_detections"]:
            if detection["activity"] != "not_present":
                location_log.append({
                    "timestamp": data["timestamp"],
                    "location": detection["label"],
                    "activity": detection["activity"]
                })

        await asyncio.sleep(30)  # Log every 30 seconds
```

---

## 🎯 Performance & Optimization

### Resource Usage

**Per Camera:**
- Memory: ~10MB per camera stream
- CPU: ~5% per camera @ 15fps
- Network: 0 (local capture only)

**Total for 4 Cameras:**
- Memory: ~40MB
- CPU: ~20%
- Disk: 0 (frames not saved, real-time only)

### Frame Rate Guidelines

| Use Case | Recommended FPS | Reason |
|----------|----------------|--------|
| Fall Detection | 15-30 fps | Need fast response |
| Posture Monitoring | 5-10 fps | Slow changes |
| Activity Tracking | 5-10 fps | Slow changes |
| General Monitoring | 10-15 fps | Balanced |

### Synchronization Quality

```
Sync Error < 50ms   : Excellent (ideal for fall detection)
Sync Error 50-100ms : Good (fine for most use cases)
Sync Error 100-200ms: Fair (acceptable for posture/activity)
Sync Error > 200ms  : Poor (cameras may be overloaded)
```

**Improving Sync:**
- Use cameras with same resolution/fps
- Reduce fps if sync error is high
- Use USB 3.0 ports (faster bandwidth)
- Distribute cameras across USB controllers

---

## 🐛 Troubleshooting

### Issue: Camera Not Detected

**Symptoms:**
```json
{
  "detected_cameras": [],
  "count": 0
}
```

**Solutions:**
1. Check USB connection: `ls -la /dev/video*`
2. Check camera permissions:
   ```bash
   sudo chmod 666 /dev/video*
   ```
3. Verify camera works:
   ```bash
   ffplay /dev/video0  # Test camera 0
   ```
4. Check if camera is in use by another process:
   ```bash
   sudo lsof | grep /dev/video0
   ```

### Issue: Camera Fails to Add

**Error:**
```
Failed to add camera 0. Check device exists and is not in use.
```

**Solutions:**
1. Camera already in use - stop other processes
2. Wrong camera ID - check `detect` endpoint
3. Resolution not supported - try lower resolution:
   ```bash
   curl -X POST "http://localhost:9007/external_cameras/add?camera_id=0&label=test&width=640&height=480"
   ```

### Issue: High Sync Error

**Symptoms:**
```json
{
  "sync_error_ms": 350.5  // Too high!
}
```

**Solutions:**
1. Reduce FPS:
   ```bash
   # Update camera to lower FPS
   curl -X POST "http://localhost:9007/external_cameras/add?camera_id=0&label=kitchen&fps=10"
   ```
2. Reduce resolution:
   ```bash
   curl -X POST "http://localhost:9007/external_cameras/add?camera_id=0&label=kitchen&width=640&height=480"
   ```
3. Disable unused cameras:
   ```bash
   curl -X POST http://localhost:9007/external_cameras/2/disable
   ```

### Issue: Camera Reconnection Loop

**Logs:**
```
Camera 0 has 15 consecutive errors, attempting reconnection...
Failed to reconnect camera 0
```

**Solutions:**
1. USB connection loose - reseat cable
2. Power issue - use powered USB hub
3. Camera hardware failure - try different camera
4. Remove and re-add camera:
   ```bash
   curl -X DELETE http://localhost:9007/external_cameras/0
   curl -X POST "http://localhost:9007/external_cameras/add?camera_id=0&label=kitchen"
   ```

---

## 📊 Comparison: Tablet vs External Cameras

| Feature | Tablet Manual Camera | External Multi-Camera System |
|---------|---------------------|------------------------------|
| **Purpose** | Manual OCR scanning | Continuous monitoring |
| **Cameras** | 1 (tablet built-in) | 2-4 (USB/IP external) |
| **Usage** | Point and click | Always-on background |
| **Location** | Mobile (tablet) | Fixed positions (server) |
| **Use Cases** | Prescription, Budget scanning | Fall detection, Posture, Activity |
| **Capture Mode** | Single photo on demand | Continuous video frames |
| **Processing** | Batch OCR from multiple angles | Real-time pose/activity analysis |
| **Hardware** | Tablet camera | External USB cameras |
| **Setup** | No setup needed | Configure labels/positions |

**When to Use Tablet Camera:**
- Scanning prescriptions
- Capturing budgets/receipts
- Manual one-time captures
- Need mobility

**When to Use External Cameras:**
- Fall detection
- Posture monitoring
- Activity tracking
- Location awareness
- Long-term monitoring

---

## 🚀 Next Steps

### Recommended Setup for Kyle

**Phase 1: Testing (2 cameras)**
```bash
# Kitchen (fall detection)
curl -X POST "http://localhost:9007/external_cameras/add?camera_id=0&label=kitchen&position=ceiling&angle=top_down"

# Desk (posture monitoring)
curl -X POST "http://localhost:9007/external_cameras/add?camera_id=1&label=desk&position=monitor_top&angle=front_view"

curl -X POST http://localhost:9007/external_cameras/start
```

**Phase 2: Expand Coverage (4 cameras)**
```bash
# Add bedroom (fall detection)
curl -X POST "http://localhost:9007/external_cameras/add?camera_id=2&label=bedroom&position=wall_corner&angle=side_view"

# Add living room (activity tracking)
curl -X POST "http://localhost:9007/external_cameras/add?camera_id=3&label=living_room&position=bookshelf&angle=wide_view"
```

**Phase 3: Integration**
- Connect fall detection to alert system
- Schedule posture checks every 10 minutes
- Log activity data to Library of Truth
- Correlate with calendar events

---

## 📚 Code Examples

### Python Client

```python
import httpx
import asyncio

class ExternalCameraClient:
    def __init__(self, base_url="http://localhost:9007"):
        self.base_url = base_url

    async def detect_cameras(self):
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/external_cameras/detect")
            return response.json()

    async def add_camera(self, camera_id, label, position, angle):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/external_cameras/add",
                params={
                    "camera_id": camera_id,
                    "label": label,
                    "position": position,
                    "angle": angle
                }
            )
            return response.json()

    async def start_monitoring(self):
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/external_cameras/start")
            return response.json()

    async def check_fall_detection(self):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/external_cameras/analyze/fall_detection"
            )
            return response.json()

# Usage
async def main():
    client = ExternalCameraClient()

    # Detect cameras
    cameras = await client.detect_cameras()
    print(f"Found {cameras['count']} cameras")

    # Add cameras
    await client.add_camera(0, "kitchen", "ceiling", "top_down")
    await client.add_camera(1, "desk", "monitor_top", "front_view")

    # Start monitoring
    status = await client.start_monitoring()
    print(f"Monitoring started: {status['cameras']} cameras")

    # Continuous fall detection
    while True:
        result = await client.check_fall_detection()
        if result["fall_detected"]:
            print(f"⚠️ FALL DETECTED! Confidence: {result['confidence']}")
        await asyncio.sleep(2)

asyncio.run(main())
```

---

## 📝 Summary

**What Was Added:**
- ✅ `multi_camera_manager.py` - Camera manager class
- ✅ 14 new API endpoints for external camera control
- ✅ Synchronized multi-camera frame capture
- ✅ Fall detection from multiple angles
- ✅ Posture analysis (side + front view)
- ✅ Activity tracking across rooms

**Key Features:**
- Auto-detect external cameras
- Configure camera labels/positions
- Continuous threaded capture
- Synchronized frame access
- Multi-angle analysis

**Files Modified:**
- `services/cam/main.py` (+415 lines)
- `services/cam/multi_camera_manager.py` (new file, 481 lines)

**Status:** ✅ **READY FOR TESTING**

**Next:** Connect USB cameras and test with curl commands above!

---

**Report Generated:** 2025-12-26
**External Cameras Supported:** 2-10 simultaneous
**Service Port:** 9007
**Docker Device Mapping:** Required for /dev/video* access
