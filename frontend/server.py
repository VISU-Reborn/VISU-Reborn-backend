"""
Simple FastAPI server for VISU emotion frontend
Serves the face-based UI from static/ + templates/ directories
Receives emotion updates from the agent and broadcasts to connected clients
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import json
import asyncio
from datetime import datetime
from pathlib import Path

app = FastAPI(title="VISU Emotion Frontend")

# Resolve paths relative to the project root (one level up from frontend/)
project_root = Path(__file__).resolve().parent.parent
static_dir = project_root / "static"
templates_dir = project_root / "templates"

# Mount static files and set up templates
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
templates = Jinja2Templates(directory=str(templates_dir))

# Current emotion state
current_emotion = {"type": "neutral", "timestamp": datetime.now().isoformat()}

# Pydantic model for emotion data
class EmotionUpdate(BaseModel):
    emotion: str

# Store active WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"✅ Client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"❌ Client disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            print("⚠️ No clients connected to broadcast emotion")
            return
            
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                print(f"❌ Failed to send to client: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

@app.post("/update-emotion")
async def update_emotion(emotion_data: EmotionUpdate):
    """Receive emotion update from VISU agent and broadcast to clients"""
    emotion = emotion_data.emotion.lower()
    timestamp = datetime.now().isoformat()
    
    # Update current state
    current_emotion["type"] = emotion
    current_emotion["timestamp"] = timestamp
    
    print(f"🎭 Received emotion: {emotion}")
    
    # Broadcast to all connected WebSocket clients
    message = {
        "type": "emotion_update",
        "emotion": emotion,
        "timestamp": timestamp
    }
    
    await manager.broadcast(message)
    
    return {"status": "success", "emotion": emotion, "timestamp": timestamp}

@app.get("/api/get_emotion")
async def get_emotion():
    """Return the current emotion state (for polling fallback)"""
    return JSONResponse(content=current_emotion)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time emotion updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/")
async def get_index(request: Request):
    """Serve the face-based emotion display page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "active_connections": len(manager.active_connections),
        "current_emotion": current_emotion["type"],
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting VISU Emotion Frontend Server...")
    print("📱 Open http://localhost:8000 to view the face display")
    print("🔌 Agent should send emotions to http://localhost:8000/update-emotion")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )