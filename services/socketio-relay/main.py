"""
Simple Socket.IO relay service for Kilo AI
Provides WebSocket support for real-time frontend updates
"""
import socketio
import uvicorn
from fastapi import FastAPI
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Socket.IO Relay")

# Create Socket.IO server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=True,
    engineio_logger=False,
    ping_timeout=60,
    ping_interval=25
)

# Wrap with ASGI app
socket_app = socketio.ASGIApp(
    socketio_server=sio,
    other_asgi_app=app
)

@app.get("/health")
@app.get("/status")
async def health():
    return {"status": "ok", "service": "socketio-relay"}

@sio.event
async def connect(sid, environ):
    """Handle client connection"""
    logger.info(f"✅ Socket.IO client connected: {sid}")
    await sio.emit('connected', {
        'status': 'ok',
        'message': 'Connected to Kilo AI',
        'timestamp': time.time()
    }, room=sid)

@sio.event
async def disconnect(sid):
    """Handle client disconnection"""
    logger.info(f"❌ Socket.IO client disconnected: {sid}")

@sio.event
async def ping(sid, data=None):
    """Handle ping from client"""
    logger.debug(f"📡 Ping from {sid}")
    await sio.emit('pong', {
        'timestamp': time.time(),
        'data': data
    }, room=sid)

@sio.event
async def subscribe(sid, channel):
    """Subscribe to a channel for updates"""
    logger.info(f"🔔 Client {sid} subscribed to {channel}")
    await sio.emit('subscribed', {
        'channel': channel,
        'timestamp': time.time()
    }, room=sid)

@sio.event
async def message(sid, data):
    """Handle generic messages"""
    logger.info(f"💬 Message from {sid}: {data}")
    await sio.emit('message_received', {
        'status': 'ok',
        'timestamp': time.time()
    }, room=sid)

if __name__ == "__main__":
    uvicorn.run(
        socket_app,
        host="0.0.0.0",
        port=9010,
        log_level="info"
    )
