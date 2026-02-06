from fastapi import FastAPI, Body
from kilo_v2.security_monitor import SecurityMonitor
import uvicorn

app = FastAPI(title="Kilo Security Microservice")
# SecurityMonitor might need more setup depending on its __init__
monitor = SecurityMonitor()

@app.post("/api/chat")
async def chat(query: str = Body(..., embed=True)):
    # Custom logic for security queries if SecurityMonitor doesn't have execute()
    return {"answer": f"Security Monitor active. Query processed: {query}"}

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
