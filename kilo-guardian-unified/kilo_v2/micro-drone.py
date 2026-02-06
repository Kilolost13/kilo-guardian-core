import os
import sys
from fastapi import FastAPI, Body
import uvicorn

# Fix path for plugin imports - add current dir so 'plugins' package is found
base_dir = os.path.dirname(__file__)
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from kilo_v2.plugins.drone_control import DroneControl

app = FastAPI(title="Kilo Drone Microservice")
plugin = DroneControl()

@app.post("/api/chat")
async def chat(query: str = Body(..., embed=True)):
    # Drone plugin usually expects to be called via execute()
    result = plugin.execute(query)
    return {"answer": result}

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)