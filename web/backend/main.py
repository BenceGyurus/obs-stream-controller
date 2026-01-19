import os
import sys
import logging
import asyncio
from datetime import datetime, timezone
from collections import deque
from typing import Union
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

# --- Import existing logic ---
from .stream_controller import check_youtube_live_status, start_obs_stream, get_obs_stream_status

# --- Basic Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)

# --- FastAPI App ---
app = FastAPI()

# --- State Management ---
class StreamState(BaseModel):
    youtube_is_live: bool = False
    obs_is_streaming: bool = False
    check_interval: int = 900
    live_mode: bool = False
    obs_enabled: bool = True
    youtube_enabled: bool = True
    last_check_timestamp: Union[datetime, None] = None

state = StreamState()
check_now = asyncio.Event()
history = deque(maxlen=200) # Store last 200 status updates for the graph

# --- WebSocket Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        await self.broadcast_state()

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast_state(self):
        for connection in self.active_connections:
            await connection.send_json(state.model_dump(mode='json'))

manager = ConnectionManager()

# --- Background Task ---
async def stream_watchdog():
    load_dotenv()
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip("'\"")
    YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "").strip("'\"")
    OBS_HOST = os.getenv("OBS_WEBSOCKET_HOST", "localhost").strip("'\"")
    OBS_PORT = int(os.getenv("OBS_WEBSOCKET_PORT", "4455").strip("'\""))
    OBS_PASSWORD = os.getenv("OBS_WEBSOCKET_PASSWORD", "").strip("'\"")

    if not all([YOUTUBE_API_KEY, YOUTUBE_CHANNEL_ID, OBS_PASSWORD]):
        logging.error("One or more required environment variables are missing. The service will not check streams.")

    while True:
        if state.youtube_enabled:
            logging.info("Checking stream status...")
            try:
                state.youtube_is_live = check_youtube_live_status(YOUTUBE_API_KEY, YOUTUBE_CHANNEL_ID)
                if state.obs_enabled:
                    state.obs_is_streaming = get_obs_stream_status(OBS_HOST, OBS_PORT, OBS_PASSWORD)
                    if not state.youtube_is_live and not state.obs_is_streaming:
                        logging.info("Stream is offline. Attempting to start stream via OBS...")
                        start_obs_stream(OBS_HOST, OBS_PORT, OBS_PASSWORD)
                        # Give OBS a moment to start before checking status again
                        await asyncio.sleep(2)
                        state.obs_is_streaming = get_obs_stream_status(OBS_HOST, OBS_PORT, OBS_PASSWORD)
            except Exception as e:
                logging.error(f"An error occurred during check: {e}")

        state.last_check_timestamp = datetime.now(timezone.utc)
        history.append(state.model_dump(mode='json'))
        
        await manager.broadcast_state()

        interval = 60 if state.live_mode else state.check_interval
        logging.info(f"Check complete. Waiting for {interval} seconds.")
        
        try:
            await asyncio.wait_for(check_now.wait(), timeout=interval)
            check_now.clear()
            logging.info("Change detected or manual check triggered. Checking now.")
        except asyncio.TimeoutError:
            pass

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(stream_watchdog())

# --- API Routes ---
@app.post("/api/check-now", status_code=202)
async def trigger_check_now():
    check_now.set()
    return {"message": "Check triggered"}

@app.get("/api/history")
async def get_history():
    return list(history)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            changed = False
            if "check_interval" in data and data["check_interval"] != state.check_interval:
                state.check_interval = data["check_interval"]
                changed = True
            if "live_mode" in data and data["live_mode"] != state.live_mode:
                state.live_mode = data["live_mode"]
                changed = True
            if "obs_enabled" in data and data["obs_enabled"] != state.obs_enabled:
                state.obs_enabled = data["obs_enabled"]
                changed = True
            if "youtube_enabled" in data and data["youtube_enabled"] != state.youtube_enabled:
                state.youtube_enabled = data["youtube_enabled"]
                if not state.youtube_enabled:
                    state.obs_enabled = False
                changed = True
            
            if changed:
                check_now.set()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# --- Static Files ---
app.mount("/static", StaticFiles(directory="web/frontend/static"), name="static")
app.mount("/locales", StaticFiles(directory="web/frontend/locales"), name="locales")

@app.get("/")
async def read_index():
    return FileResponse('web/frontend/index.html')

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, reload_dirs=["web/backend"])
