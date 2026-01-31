"""
USB Transfer API Service
Provides REST endpoints for secure USB data transfer operations
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
from dataclasses import asdict

import usb_service
from usb_service import USBDevice, DataExport

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

app = FastAPI(
    title="KILO USB Transfer Service",
    description="Secure USB data transfer for air-gapped AI memory assistant",
    version="1.0.0"
)

# Pydantic models
class AuthRequest(BaseModel):
    password: str = Field(..., min_length=8, description="USB transfer password")

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)

class ExportRequest(BaseModel):
    device_id: str
    data: Dict[str, Any] = Field(..., description="Data to export")

class ImportRequest(BaseModel):
    device_id: str
    import_type: str = Field(default="therapy_progress", description="Type of data to import")

class USBDeviceResponse(BaseModel):
    mount_point: str
    device_id: str
    label: Optional[str]
    size_gb: float
    is_safe: bool
    last_scan: Optional[datetime]

class DataExportResponse(BaseModel):
    id: str
    timestamp: datetime
    data_type: str
    record_count: int
    file_size_mb: float
    checksum: str
    encrypted: bool

# Dependencies
def get_current_session(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Validate session token"""
    token = credentials.credentials
    if not usb_service.validate_session(token):
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return token

# Routes
@app.post("/auth", response_model=dict)
async def authenticate(request: AuthRequest):
    """Authenticate with USB transfer password"""
    success, session_token = usb_service.authenticate(request.password)
    if not success:
        raise HTTPException(status_code=401, detail="Invalid password")

    return {
        "success": True,
        "session_token": session_token,
        "message": "Authentication successful"
    }

@app.post("/auth/change-password")
async def change_password(
    request: ChangePasswordRequest,
    session_token: str = Depends(get_current_session)
):
    """Change USB transfer password"""
    success = usb_service.change_password(
        session_token,
        request.old_password,
        request.new_password
    )

    if not success:
        raise HTTPException(status_code=400, detail="Password change failed")

    return {"success": True, "message": "Password changed successfully"}

@app.get("/devices", response_model=List[USBDeviceResponse])
async def scan_devices(session_token: str = Depends(get_current_session)):
    """Scan for available USB devices"""
    devices = usb_service.scan_usb_devices()
    return [USBDeviceResponse(**asdict(device)) for device in devices]

@app.post("/export")
async def export_data(
    request: ExportRequest,
    background_tasks: BackgroundTasks,
    session_token: str = Depends(get_current_session)
):
    """Export therapy progress data to USB device"""
    success, message = usb_service.export_therapy_progress(
        session_token,
        request.device_id,
        request.data
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {
        "success": True,
        "message": message
    }

@app.post("/import")
async def import_data(
    request: ImportRequest,
    session_token: str = Depends(get_current_session)
):
    """Import data from USB device"""
    success, message, data = usb_service.import_data(
        session_token,
        request.device_id,
        request.import_type
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {
        "success": True,
        "message": message,
        "data": data
    }

@app.get("/exports", response_model=List[DataExportResponse])
async def get_export_history(session_token: str = Depends(get_current_session)):
    """Get export history"""
    exports = usb_service.get_export_history(session_token)
    return [DataExportResponse(**asdict(export)) for export in exports]

@app.post("/cleanup")
async def cleanup_sessions(
    background_tasks: BackgroundTasks,
    session_token: str = Depends(get_current_session)
):
    """Clean up expired sessions (admin only)"""
    background_tasks.add_task(usb_service.cleanup_expired_sessions)
    return {"success": True, "message": "Cleanup initiated"}

@app.get("/status")
async def get_service_status(session_token: str = Depends(get_current_session)):
    """Get service status"""
    return {
        "status": "active",
        "active_sessions": len(usb_service.active_sessions),
        "mounted_devices": len(usb_service.mounted_devices),
        "config_path": str(usb_service.config_path)
    }

# Health check (no auth required)
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "usb_transfer",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)