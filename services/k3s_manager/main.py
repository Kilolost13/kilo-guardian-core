"""
K3s Manager FastAPI Service
Exposes k3s management capabilities as REST API
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from manager import k3s_manager

app = FastAPI(title="Kilo K3s Manager", version="1.0.0")


class ScaleRequest(BaseModel):
    service: str
    replicas: int


class RestartRequest(BaseModel):
    service: str


class LogsRequest(BaseModel):
    service: str
    lines: Optional[int] = 50


class ExecRequest(BaseModel):
    service: str
    command: str


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "k3s-manager"}


@app.get("/cluster/status")
async def get_cluster_status():
    """Get overall cluster health"""
    try:
        status = k3s_manager.get_cluster_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/services")
async def list_services():
    """List all services in kilo-guardian namespace"""
    try:
        services = k3s_manager.list_services()
        return {"services": services, "count": len(services)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/services/scale")
async def scale_service(request: ScaleRequest):
    """Scale a service to specified replicas"""
    try:
        result = k3s_manager.scale_service(request.service, request.replicas)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/services/restart")
async def restart_service(request: RestartRequest):
    """Restart a service (rolling restart)"""
    try:
        result = k3s_manager.restart_service(request.service)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/services/logs")
async def get_logs(request: LogsRequest):
    """Get recent logs from a service"""
    try:
        logs = k3s_manager.get_service_logs(request.service, request.lines)
        return {"service": request.service, "logs": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/services/{service_name}/status")
async def get_pod_status(service_name: str):
    """Get detailed pod status for a service"""
    try:
        status = k3s_manager.get_pod_status(service_name)
        if "error" in status:
            raise HTTPException(status_code=404, detail=status["error"])
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/endpoints")
async def get_endpoints():
    """Get all accessible service endpoints"""
    try:
        endpoints = k3s_manager.get_service_endpoints()
        return {"endpoints": endpoints, "count": len(endpoints)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/services/exec")
async def exec_command(request: ExecRequest):
    """Execute a command in a service pod"""
    try:
        output = k3s_manager.exec_in_pod(request.service, request.command)
        return {"service": request.service, "output": output}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9011)
