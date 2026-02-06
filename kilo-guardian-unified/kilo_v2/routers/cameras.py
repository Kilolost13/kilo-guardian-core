import logging
import time
from typing import Any  # noqa: F401

from fastapi import APIRouter, Response
from fastapi.responses import StreamingResponse

from kilo_v2.camera_service import get_camera_service

logger = logging.getLogger("kilo_v2.routers.cameras")

router = APIRouter()


@router.get("/api/cameras")
async def list_cameras():
    """
    List all detected cameras.
    This is a core feature, always available.
    """
    camera_service = get_camera_service()
    if not camera_service:
        return {"cameras": [], "error": "Camera service not initialized"}

    cameras = camera_service.get_all_cameras()
    return {
        "cameras": [
            {
                "id": info.id,
                "name": info.name,
                "is_active": info.is_active,
                "resolution": info.resolution,
                "fps": info.fps,
            }
            for info in cameras.values()
        ],
        "count": len(cameras),
    }


def gen_camera_frames(camera_id: int):
    logger.info(f"🎥 Starting camera stream for camera {camera_id}")
    frame_count = 0
    last_log_time = time.time()

    while True:
        try:
            camera_service = get_camera_service()
            if not camera_service:
                logger.warning("Camera service not available")
                time.sleep(0.5)
                continue

            frame = camera_service.get_frame(camera_id)
            if frame:
                frame_count += 1
                current_time = time.time()
                if current_time - last_log_time >= 300:
                    logger.info(
                        "Camera %d: %d total frames (active)",
                        camera_id,
                        frame_count,
                    )
                    last_log_time = current_time
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
                time.sleep(0.1)
            else:
                logger.warning("Camera %d: No frame available", camera_id)
                time.sleep(0.5)
        except GeneratorExit:
            logger.info(
                "🎥 Camera %d stream closed (%d total frames)",
                camera_id,
                frame_count,
            )
            break
        except Exception as e:
            logger.error(f"Error streaming camera {camera_id}: {e}")
            time.sleep(1.0)


@router.get("/api/camera/{camera_id}/stream")
async def camera_stream(camera_id: int):
    camera_service = get_camera_service()
    if not camera_service:
        return Response(status_code=503, content="Camera service not available")

    info = camera_service.get_camera_info(camera_id)
    if not info:
        return Response(status_code=404, content=f"Camera {camera_id} not found")

    return StreamingResponse(
        gen_camera_frames(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "keep-alive",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/api/camera/health")
async def camera_health():
    camera_service = get_camera_service()
    if not camera_service:
        return {"status": "error", "message": "Camera service not initialized"}

    return camera_service.health_check()


@router.get("/api/camera/{camera_id}/frame")
async def get_camera_frame(camera_id: int):
    camera_service = get_camera_service()
    if not camera_service:
        return Response(status_code=503, content="Camera service not available")

    frame = camera_service.get_frame(camera_id)
    if not frame:
        return Response(status_code=404, content=f"Camera {camera_id} has no frame")

    return Response(
        content=frame,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )
