import os
import sys
import logging
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
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

load_dotenv()

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
    telegram_enabled: bool = os.getenv("TELEGRAM_ENABLED", "false").lower() == "true"
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
    telegram_notify_on_youtube_offline: bool = os.getenv("TELEGRAM_NOTIFY_ON_YOUTUBE_OFFLINE", "true").lower() == "true"
    telegram_notify_on_obs_offline: bool = os.getenv("TELEGRAM_NOTIFY_ON_OBS_OFFLINE", "true").lower() == "true"
    last_youtube_is_live: Union[bool, None] = None
    last_obs_is_streaming: Union[bool, None] = None


state = StreamState()
check_now = asyncio.Event()
history = deque(maxlen=200)
SETTINGS_FILE = Path(os.getenv("SETTINGS_FILE", "web/backend/settings.json"))

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
        disconnected = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(state.model_dump(mode='json'))
            except Exception:
                disconnected.append(connection)
        
        for connection in disconnected:
            if connection in self.active_connections:
                self.active_connections.remove(connection)

manager = ConnectionManager()
app = FastAPI()

def send_telegram_message(bot_token: str, chat_id: str, text: str) -> tuple[bool, str, str]:
    if not bot_token or not chat_id:
        logging.warning("Telegram notification skipped: bot token or chat id missing.")
        return False, "missing_credentials", "Telegram bot token or chat id missing."
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, method="POST")
        with urllib.request.urlopen(req, timeout=10) as response:
            body = response.read().decode("utf-8")
            data = None
            try:
                data = json.loads(body) if body else None
            except json.JSONDecodeError:
                data = None
            if response.status != 200:
                description = data.get("description") if isinstance(data, dict) else None
                return False, "send_failed", description or f"Telegram API responded with status {response.status}."
            if isinstance(data, dict) and not data.get("ok", True):
                description = data.get("description") or "Telegram API returned ok=false."
                return False, "send_failed", description
        return True, "sent", ""
    except urllib.error.HTTPError as e:
        body = None
        try:
            body = e.read().decode("utf-8")
        except Exception:
            body = None
        description = None
        if body:
            try:
                data = json.loads(body)
                description = data.get("description") if isinstance(data, dict) else None
            except json.JSONDecodeError:
                description = None
        return False, "send_failed", description or str(e)
    except Exception as e:
        logging.warning(f"Failed to send Telegram message: {e}")
        return False, "send_failed", str(e)

def load_settings() -> None:
    if not SETTINGS_FILE.exists():
        return
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        state.telegram_enabled = bool(data.get("telegram_enabled", state.telegram_enabled))
        state.telegram_bot_token = str(data.get("telegram_bot_token", state.telegram_bot_token) or "")
        state.telegram_chat_id = str(data.get("telegram_chat_id", state.telegram_chat_id) or "")
        state.telegram_notify_on_youtube_offline = bool(
            data.get("telegram_notify_on_youtube_offline", state.telegram_notify_on_youtube_offline)
        )
        state.telegram_notify_on_obs_offline = bool(
            data.get("telegram_notify_on_obs_offline", state.telegram_notify_on_obs_offline)
        )
        logging.info(f"Loaded settings from {SETTINGS_FILE}.")
    except Exception as e:
        logging.warning(f"Failed to load settings from {SETTINGS_FILE}: {e}")

def save_settings() -> None:
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "telegram_enabled": state.telegram_enabled,
            "telegram_bot_token": state.telegram_bot_token,
            "telegram_chat_id": state.telegram_chat_id,
            "telegram_notify_on_youtube_offline": state.telegram_notify_on_youtube_offline,
            "telegram_notify_on_obs_offline": state.telegram_notify_on_obs_offline,
        }
        with open(SETTINGS_FILE, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
        logging.info(f"Saved settings to {SETTINGS_FILE}.")
    except Exception as e:
        logging.warning(f"Failed to save settings to {SETTINGS_FILE}: {e}")

async def stream_watchdog():
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip("'\"")
    YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "").strip("'\"")
    YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET_FILE", "client_secret.json").strip("'\"")
    YOUTUBE_BROADCAST_ID = os.getenv("YOUTUBE_BROADCAST_ID", "").strip("'\"") or None
    YOUTUBE_BROADCAST_RESET = os.getenv("YOUTUBE_BROADCAST_RESET", "false").lower() == "true"
    YOUTUBE_FORCE_PUBLIC_ON_RESET = os.getenv("YOUTUBE_FORCE_PUBLIC_ON_RESET", "false").lower() == "true"
    OAUTH_HEADLESS = os.getenv("OAUTH_HEADLESS", "false").lower() == "true"
    OBS_HOST = os.getenv("OBS_WEBSOCKET_HOST", "localhost").strip("'\"")
    OBS_PORT = int(os.getenv("OBS_WEBSOCKET_PORT", "4455").strip("'\""))
    OBS_PASSWORD = os.getenv("OBS_WEBSOCKET_PASSWORD", "").strip("'\"")

    if not all([YOUTUBE_API_KEY, YOUTUBE_CHANNEL_ID, OBS_PASSWORD]):
        logging.error("One or more required environment variables are missing.")
    
    # Try to get authenticated YouTube service for broadcast management
    youtube_service = None
    if YOUTUBE_BROADCAST_RESET:
        try:
            logging.info("Attempting to authenticate with YouTube API...")
            youtube_service = get_authenticated_youtube_service(
                YOUTUBE_CLIENT_SECRET, 
                headless=OAUTH_HEADLESS
            )
            if youtube_service:
                logging.info("Successfully authenticated with YouTube API for broadcast management.")
                if YOUTUBE_BROADCAST_ID:
                    logging.info(f"Using manually specified broadcast ID: {YOUTUBE_BROADCAST_ID}")
            else:
                logging.warning("YouTube OAuth2 authentication failed. Broadcast reset will not be available.")
        except Exception as e:
            logging.warning(f"Could not initialize YouTube OAuth2 service: {e}")
            logging.warning("Stream will work without broadcast reset feature.")
    else:
        logging.info("Broadcast reset is DISABLED (YOUTUBE_BROADCAST_RESET=false). OBS will start without resetting YouTube broadcast.")

    logging.info("Stream watchdog task started.")
    while True:
        try:
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
                            # Use the enhanced start function with broadcast reset (if enabled)
                            start_obs_stream(
                                OBS_HOST, 
                                OBS_PORT, 
                                OBS_PASSWORD,
                                youtube_service=youtube_service if YOUTUBE_BROADCAST_RESET else None,
                                channel_id=YOUTUBE_CHANNEL_ID if (youtube_service and YOUTUBE_BROADCAST_RESET) else None,
                                broadcast_id=YOUTUBE_BROADCAST_ID if YOUTUBE_BROADCAST_RESET else None,
                                force_public=YOUTUBE_FORCE_PUBLIC_ON_RESET
                            )
                            await asyncio.sleep(2)
                            state.obs_is_streaming = get_obs_stream_status(OBS_HOST, OBS_PORT, OBS_PASSWORD)
                except Exception as e:
                    logging.error(f"Error during check: {e}")

            if state.telegram_enabled:
                youtube_went_offline = (
                    state.youtube_enabled
                    and state.telegram_notify_on_youtube_offline
                    and state.last_youtube_is_live is True
                    and state.youtube_is_live is False
                )
                obs_went_offline = (
                    state.obs_enabled
                    and state.telegram_notify_on_obs_offline
                    and state.last_obs_is_streaming is True
                    and state.obs_is_streaming is False
                )

                if youtube_went_offline or obs_went_offline:
                    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                    lines = ["Stream status alert:", f"Time: {timestamp}"]
                    if youtube_went_offline:
                        lines.append("- YouTube stream is OFFLINE")
                    if obs_went_offline:
                        lines.append("- OBS stream is OFFLINE")
                    message = "\n".join(lines)
                    ok, code, detail = send_telegram_message(state.telegram_bot_token, state.telegram_chat_id, message)
                    if not ok:
                        logging.warning(f"Telegram alert failed ({code}): {detail}")

            state.last_youtube_is_live = state.youtube_is_live
            state.last_obs_is_streaming = state.obs_is_streaming

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
        except Exception as e:
            logging.error(f"Unexpected error in stream_watchdog loop: {e}")
            await asyncio.sleep(10) # Wait a bit before retrying to avoid rapid-fire errors

@app.on_event("startup")
async def startup_event():
    load_settings()
    asyncio.create_task(stream_watchdog())

@app.post("/api/check-now", status_code=202)
async def trigger_check_now():
    check_now.set()
    return {"message": "Check triggered"}

@app.get("/api/history")
async def get_history():
    return list(history)

@app.post("/api/telegram-test")
async def telegram_test():
    if not state.telegram_enabled:
        logging.info("Telegram test blocked: alerts disabled.")
        return {"ok": False, "code": "disabled", "detail": "Telegram alerts are disabled"}
    if not state.telegram_bot_token or not state.telegram_chat_id:
        logging.info("Telegram test blocked: missing credentials.")
        return {"ok": False, "code": "missing_credentials", "detail": "Telegram bot token or chat id missing"}
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    message = f"Telegram test message\nTime: {timestamp}"
    ok, code, detail = send_telegram_message(state.telegram_bot_token, state.telegram_chat_id, message)
    if ok:
        logging.info("Telegram test sent successfully.")
    else:
        logging.warning(f"Telegram test failed ({code}): {detail}")
    return {"ok": ok, "code": code, "detail": detail}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            changed = False
            settings_changed = False
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
            if "telegram_enabled" in data:
                state.telegram_enabled = bool(data["telegram_enabled"])
                changed = True
                settings_changed = True
            if "telegram_bot_token" in data:
                state.telegram_bot_token = str(data["telegram_bot_token"])
                changed = True
                settings_changed = True
            if "telegram_chat_id" in data:
                state.telegram_chat_id = str(data["telegram_chat_id"])
                changed = True
                settings_changed = True
            if "telegram_notify_on_youtube_offline" in data:
                state.telegram_notify_on_youtube_offline = bool(data["telegram_notify_on_youtube_offline"])
                changed = True
                settings_changed = True
            if "telegram_notify_on_obs_offline" in data:
                state.telegram_notify_on_obs_offline = bool(data["telegram_notify_on_obs_offline"])
                changed = True
                settings_changed = True
            
            if changed:
                if settings_changed:
                    save_settings()
                # Broadcast the updated state back immediately to confirm
                await manager.broadcast_state()
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
