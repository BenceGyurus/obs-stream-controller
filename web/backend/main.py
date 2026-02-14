import os
import sys
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from collections import deque
from typing import Union
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

from .stream_controller import (
    check_youtube_live_status, 
    start_obs_stream, 
    get_obs_stream_status, 
    stop_obs_stream,
    get_authenticated_youtube_service
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)

app = FastAPI()

class StreamState(BaseModel):
    youtube_is_live: bool = False
    obs_is_streaming: bool = False
    check_interval: int = 900
    live_mode: bool = False
    live_mode_timeout: int = 15
    live_mode_end_timestamp: Union[datetime, None] = None
    obs_enabled: bool = True
    youtube_enabled: bool = True
    last_check_timestamp: Union[datetime, None] = None

state = StreamState()
check_now = asyncio.Event()
history = deque(maxlen=200)

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

async def stream_watchdog():
    load_dotenv()
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip("'\"")
    YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "").strip("'\"")
    YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET_FILE", "client_secret.json").strip("'\"")
    OBS_HOST = os.getenv("OBS_WEBSOCKET_HOST", "localhost").strip("'\"")
    OBS_PORT = int(os.getenv("OBS_WEBSOCKET_PORT", "4455").strip("'\""))
    OBS_PASSWORD = os.getenv("OBS_WEBSOCKET_PASSWORD", "").strip("'\"")

    if not all([YOUTUBE_API_KEY, YOUTUBE_CHANNEL_ID, OBS_PASSWORD]):
        logging.error("One or more required environment variables are missing.")
    
    # Try to get authenticated YouTube service for broadcast management
    youtube_service = None
    try:
        logging.info("Attempting to authenticate with YouTube API...")
        youtube_service = get_authenticated_youtube_service(YOUTUBE_CLIENT_SECRET)
        if youtube_service:
            logging.info("Successfully authenticated with YouTube API for broadcast management.")
        else:
            logging.warning("YouTube OAuth2 authentication failed. Broadcast reset will not be available.")
    except Exception as e:
        logging.warning(f"Could not initialize YouTube OAuth2 service: {e}")
        logging.warning("Stream will work without broadcast reset feature.")

    while True:
        if state.live_mode and state.live_mode_end_timestamp and datetime.now(timezone.utc) > state.live_mode_end_timestamp:
            logging.info(f"Live mode timeout of {state.live_mode_timeout} minutes reached. Disabling live mode.")
            state.live_mode = False
            state.live_mode_end_timestamp = None
            check_now.set() # Trigger a check to immediately apply the new interval

        if state.youtube_enabled:
            logging.info("Checking stream status...")
            try:
                state.youtube_is_live = check_youtube_live_status(YOUTUBE_API_KEY, YOUTUBE_CHANNEL_ID)
                if state.obs_enabled:
                    state.obs_is_streaming = get_obs_stream_status(OBS_HOST, OBS_PORT, OBS_PASSWORD)
                    if not state.youtube_is_live:
                        if state.obs_is_streaming:
                            logging.warning("YouTube offline, OBS streaming. Zombie stream? Restarting OBS stream.")
                            stop_obs_stream(OBS_HOST, OBS_PORT, OBS_PASSWORD)
                            await asyncio.sleep(5)
                        logging.info("Attempting to start OBS stream.")
                        # Use the enhanced start function with broadcast reset
                        start_obs_stream(
                            OBS_HOST, 
                            OBS_PORT, 
                            OBS_PASSWORD,
                            youtube_service=youtube_service,
                            channel_id=YOUTUBE_CHANNEL_ID if youtube_service else None
                        )
                        await asyncio.sleep(2)
                        state.obs_is_streaming = get_obs_stream_status(OBS_HOST, OBS_PORT, OBS_PASSWORD)
            except Exception as e:
                logging.error(f"Error during check: {e}")

        state.last_check_timestamp = datetime.now(timezone.utc)
        history.append(state.model_dump(mode='json'))
        await manager.broadcast_state()

        interval = 60 if state.live_mode else state.check_interval
        logging.info(f"Check complete. Waiting for {interval} seconds.")
        
        try:
            await asyncio.wait_for(check_now.wait(), timeout=interval)
            check_now.clear()
            logging.info("Change detected or manual check. Triggering immediate check.")
        except asyncio.TimeoutError:
            pass

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(stream_watchdog())

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
            if "live_mode_timeout" in data and data["live_mode_timeout"] != state.live_mode_timeout:
                state.live_mode_timeout = data["live_mode_timeout"]
                if state.live_mode:
                    state.live_mode_end_timestamp = datetime.now(timezone.utc) + timedelta(minutes=state.live_mode_timeout)
                changed = True
            if "live_mode" in data and data["live_mode"] != state.live_mode:
                state.live_mode = data["live_mode"]
                if state.live_mode:
                    state.live_mode_end_timestamp = datetime.now(timezone.utc) + timedelta(minutes=state.live_mode_timeout)
                    logging.info(f"Live mode enabled for {state.live_mode_timeout} minutes.")
                else:
                    state.live_mode_end_timestamp = None
                changed = True
            if "check_interval" in data and data["check_interval"] != state.check_interval:
                state.check_interval = data["check_interval"]
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

app.mount("/static", StaticFiles(directory="web/frontend/static"), name="static")
app.mount("/locales", StaticFiles(directory="web/frontend/locales"), name="locales")

@app.get("/")
async def read_index():
    return FileResponse('web/frontend/index.html')

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, reload_dirs=["web/backend"])