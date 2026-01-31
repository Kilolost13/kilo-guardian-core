# Camera Service - External Multi-Camera Monitoring System

This service provides both **manual tablet camera scanning** and **continuous external multi-camera monitoring** for the Kilo AI Memory Assistant.

## Two Camera Systems

### System 1: Tablet Camera (Manual Scanning)
- Uses tablet's built-in camera
- Point-and-shoot interface for prescriptions/budgets
- Single photo capture for OCR
- Accessible via `/capture` endpoint

### System 2: External Multi-Camera Monitoring (NEW)
- Multiple fixed USB/IP cameras positioned around the room
- Continuous capture from all cameras simultaneously
- Use cases:
  - **Fall detection** with multi-angle triangulation
  - **Posture analysis** (side view + front view)
  - **Activity tracking** (kitchen, desk, bed)
  - **3D spatial awareness**
- Accessible via `/external_cameras/*` endpoints

## Quick Start

### 1. Hardware Setup

Connect 2-4 USB cameras to your server. Verify they appear as `/dev/video*` devices:

```bash
ls -la /dev/video*
# Should show:
# /dev/video0
# /dev/video1
# /dev/video2
# /dev/video3
```

Position cameras strategically:
- **Kitchen**: Ceiling corner, top-down view
- **Bedroom**: Wall side, side view
- **Desk**: Monitor top, front view
- **Living Room**: Wall corner, wide angle

### 2. Start the Camera Service

The camera service automatically detects available cameras on startup:

```bash
cd infra/docker
LIBRARY_ADMIN_KEY=your_key docker-compose up cam -d
```

Check the logs to see detected cameras:

```bash
docker-compose logs cam
# Should show:
# Detected 4 external cameras: [0, 1, 2, 3]
```

### 3. Configure Cameras

Use the configuration script to set up all cameras with appropriate labels:

```bash
# Room coverage preset (recommended)
python services/cam/configure_cameras.py --preset room_coverage

# Fall detection preset
python services/cam/configure_cameras.py --preset fall_detection

# Posture monitoring preset
python services/cam/configure_cameras.py --preset posture_monitoring

# Custom labels
python services/cam/configure_cameras.py --labels kitchen,bedroom,desk,living_room

# Detect cameras only (no configuration)
python services/cam/configure_cameras.py --detect-only
```

### 4. Test the System

Run the test suite to verify everything works:

```bash
# Full test suite
python services/cam/test_cameras.py

# Quick tests only (skip analysis)
python services/cam/test_cameras.py --quick

# Save captured frames
python services/cam/test_cameras.py --save-frames

# Test specific camera
python services/cam/test_cameras.py --camera-id 0
```

### 5. Integration with Frontend

The React frontend can access multi-camera features via:

```typescript
import { MultiCameraCapture } from '../components/shared/MultiCameraCapture';

// In your component
<MultiCameraCapture
  onCapture={handleCapture}
  onClose={() => setShowCamera(false)}
  maxCameras={4}
/>
```

## API Reference

### Detection & Configuration

#### Detect Cameras
```bash
curl http://localhost:9007/external_cameras/detect
```

Response:
```json
{
  "detected_cameras": [0, 1, 2, 3],
  "count": 4,
  "device_paths": ["/dev/video0", "/dev/video1", "/dev/video2", "/dev/video3"]
}
```

#### Add Camera
```bash
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
```

#### Start Cameras
```bash
curl -X POST http://localhost:9007/external_cameras/start
```

#### Stop Cameras
```bash
curl -X POST http://localhost:9007/external_cameras/stop
```

### Status & Monitoring

#### Get Status
```bash
curl http://localhost:9007/external_cameras/status
```

Response:
```json
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
      "frame_count": 1523,
      "error_count": 0,
      "time_since_last_frame": 0.067
    }
  }
}
```

### Frame Capture

#### Get Single Camera Frame
```bash
curl http://localhost:9007/external_cameras/0/frame > frame.jpg
```

#### Get Synchronized Frames
```bash
curl http://localhost:9007/external_cameras/frames/synchronized?max_sync_error_ms=100
```

Response:
```json
{
  "timestamp": 1678901234.567,
  "sync_error_ms": 23.5,
  "camera_count": 4,
  "cameras": [
    {
      "camera_id": 0,
      "label": "kitchen",
      "position": "ceiling_corner",
      "angle": "top_down",
      "timestamp": 1678901234.555,
      "frame_number": 1523
    }
  ]
}
```

### Analysis

#### Fall Detection
```bash
curl -X POST http://localhost:9007/external_cameras/analyze/fall_detection
```

Response:
```json
{
  "fall_detected": false,
  "confidence": 0.0,
  "camera_count": 4,
  "sync_error_ms": 45.2,
  "pose_data": [
    {
      "camera_id": 0,
      "label": "kitchen",
      "angle": "top_down",
      "landmarks": [...]
    }
  ],
  "alert_level": "normal"
}
```

#### Posture Analysis
```bash
curl -X POST http://localhost:9007/external_cameras/analyze/posture
```

Response:
```json
{
  "posture_score": 75.5,
  "camera_count": 2,
  "posture_quality": "good",
  "recommendations": [
    "Keep shoulders level",
    "Maintain neutral spine"
  ],
  "side_view_analysis": {...},
  "front_view_analysis": {...}
}
```

#### Activity Detection
```bash
curl -X POST http://localhost:9007/external_cameras/analyze/activity
```

Response:
```json
{
  "primary_activity": "working_at_desk",
  "confidence": 0.89,
  "camera_count": 4,
  "detected_activities": {
    "working_at_desk": 0.89,
    "standing": 0.45,
    "sitting": 0.78
  },
  "location": "desk"
}
```

### Camera Control

#### Enable Camera
```bash
curl -X POST http://localhost:9007/external_cameras/0/enable
```

#### Disable Camera
```bash
curl -X POST http://localhost:9007/external_cameras/0/disable
```

#### Update Camera Label
```bash
curl -X PUT "http://localhost:9007/external_cameras/0/label?new_label=kitchen_overhead"
```

## Configuration Presets

### Fall Detection Setup
Optimized for fall detection with multiple angles:

```python
cameras = [
    {"label": "overhead", "position": "ceiling_corner", "angle": "top_down"},
    {"label": "side_view", "position": "wall_side", "angle": "side_view"},
    {"label": "front_view", "position": "wall_front", "angle": "front_view"},
]
```

### Posture Monitoring Setup
Optimized for posture analysis at desk:

```python
cameras = [
    {"label": "desk_side", "position": "desk_side", "angle": "side_view"},
    {"label": "desk_front", "position": "monitor_top", "angle": "front_view"},
]
```

### Room Coverage Setup
Comprehensive monitoring of all rooms:

```python
cameras = [
    {"label": "kitchen", "position": "ceiling_corner", "angle": "top_down"},
    {"label": "bedroom", "position": "wall_side", "angle": "side_view"},
    {"label": "desk", "position": "monitor_top", "angle": "front_view"},
    {"label": "living_room", "position": "wall_corner", "angle": "wide_angle"},
]
```

## Architecture

### Multi-Camera Manager (`multi_camera_manager.py`)

The core camera management system with:

- **CameraConfig**: Configuration dataclass
  - camera_id, label, position, angle
  - resolution, fps, enabled flag

- **CameraFrame**: Single frame with metadata
  - timestamp, frame data, frame number
  - position, angle information

- **MultiCameraFrame**: Synchronized frames
  - All camera frames
  - Sync error metric (ms)
  - Average timestamp

- **ExternalCameraManager**: Main manager class
  - Thread-based continuous capture (one thread per camera)
  - Automatic reconnection on failure
  - Thread-safe frame access
  - Synchronized frame capture

### Threading Model

Each camera runs in its own daemon thread:

```
Main Thread (FastAPI)
├── Camera 0 Thread (continuous capture)
├── Camera 1 Thread (continuous capture)
├── Camera 2 Thread (continuous capture)
└── Camera 3 Thread (continuous capture)
```

Threads continuously capture frames and store them in memory. API endpoints access the latest frames without blocking.

### Frame Synchronization

Synchronized capture algorithm:

1. Get latest frame from each camera
2. Extract timestamps
3. Calculate time difference between oldest and newest
4. Return sync_error_ms metric
5. If sync_error > threshold, warn user

Typical sync error: 10-50ms
Acceptable sync error: <100ms
Warning threshold: 100ms

## Troubleshooting

### No Cameras Detected

```bash
# Check if cameras are connected
ls -la /dev/video*

# Check camera permissions
sudo chmod 666 /dev/video*

# Test camera with v4l2
v4l2-ctl --list-devices
v4l2-ctl --device=/dev/video0 --all

# Check Docker device mapping
docker-compose exec cam ls -la /dev/video*
```

### Camera Failed to Open

```bash
# Check if another process is using the camera
lsof /dev/video0

# Kill processes using the camera
fuser -k /dev/video0

# Restart camera service
docker-compose restart cam
```

### High Sync Error

If `sync_error_ms` is consistently >100ms:

1. Reduce camera resolution (1280x720 instead of 1920x1080)
2. Reduce FPS (10 instead of 15)
3. Use faster USB ports (USB 3.0)
4. Reduce number of active cameras

### Frames Not Updating

```bash
# Check camera status
curl http://localhost:9007/external_cameras/status

# Look for:
# - frame_count increasing
# - error_count = 0
# - time_since_last_frame < 1 second

# Check logs
docker-compose logs cam --tail=100
```

### Fall Detection Always Returns False

1. Verify pose data is being extracted:
   ```bash
   curl -X POST http://localhost:9007/external_cameras/analyze/fall_detection | jq '.pose_data'
   ```

2. Check if MediaPipe is detecting landmarks

3. Test with a person in camera view

4. Ensure lighting is adequate

## Performance Optimization

### Recommended Settings

**For 4 cameras on Beelink SER7-9:**
- Resolution: 1280x720
- FPS: 10-15
- Sync threshold: 100ms

**For 2 cameras:**
- Resolution: 1920x1080
- FPS: 15-30
- Sync threshold: 50ms

### Resource Usage

Typical CPU usage per camera at 1280x720@15fps:
- Capture thread: 5-10% CPU
- MediaPipe pose detection: 15-25% CPU per analysis
- Total for 4 cameras: 40-60% CPU during analysis

Memory usage:
- ~50MB per camera thread
- ~200MB for MediaPipe models
- Total for 4 cameras: ~400MB

## Integration with AI Brain

The camera service automatically sends analysis results to the AI Brain for:

1. **Memory Creation**: Fall events, posture changes, activity patterns
2. **Context Awareness**: Current location, activity, posture
3. **Health Monitoring**: Fall history, posture trends
4. **Alert Generation**: Fall detection triggers immediate alert

Example AI Brain integration:

```python
# Fall detected -> Create memory in AI Brain
if fall_detected:
    httpx.post(
        f"{AI_BRAIN_URL}/memories",
        json={
            "content": f"Fall detected at {timestamp} with {confidence:.0%} confidence",
            "tags": ["fall", "alert", "health"],
            "confidential": False
        }
    )
```

## Files

- `main.py`: FastAPI service with all endpoints
- `multi_camera_manager.py`: Core camera management system
- `configure_cameras.py`: Configuration helper script
- `test_cameras.py`: Test suite
- `README_CAMERA_SERVICE.md`: This file
- `EXTERNAL_MULTI_CAMERA_MONITORING.md`: Comprehensive documentation

## Next Steps

1. **Setup**: Configure cameras using `configure_cameras.py`
2. **Test**: Run `test_cameras.py` to verify setup
3. **Monitor**: Check status regularly with `/external_cameras/status`
4. **Integrate**: Connect to AI Brain for continuous monitoring
5. **Optimize**: Adjust resolution/FPS based on performance

## Support

For issues or questions:
- Check logs: `docker-compose logs cam`
- Run tests: `python test_cameras.py`
- Review documentation: `EXTERNAL_MULTI_CAMERA_MONITORING.md`
- Check camera devices: `ls -la /dev/video*`
