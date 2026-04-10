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

from .stream_controller import check_youtube_live_status

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s', 
    stream=sys.stdout
)

load_dotenv()

class StreamState(BaseModel):
    youtube_is_live: bool = False
    check_interval: int = 900
    last_check_timestamp: Union[datetime, None] = None
    
    youtube_api_key: str = ""
    youtube_channel_id: str = ""
    
    telegram_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_notify_on_status_change: bool = True
    
    last_youtube_is_live: Union[bool, None] = None


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
        logging.info(f"WebSocket connected. Broadcasting current state.")
        await self.broadcast_state()

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_state(self):
        data = state.model_dump(mode='json')
        for connection in list(self.active_connections):
            try:
                await connection.send_json(data)
            except Exception:
                if connection in self.active_connections:
                    self.active_connections.remove(connection)

manager = ConnectionManager()
app = FastAPI()

def send_telegram_message(bot_token: str, chat_id: str, text: str) -> tuple[bool, str, str]:
    if not bot_token or not chat_id:
        return False, "missing_credentials", "Missing token/chat_id"
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        params = {"chat_id": str(chat_id), "text": text, "parse_mode": "HTML"}
        payload = urllib.parse.urlencode(params).encode("utf-8")
        req = urllib.request.Request(url, data=payload, method="POST")
        
        with urllib.request.urlopen(req, timeout=15) as response:
            body = response.read().decode("utf-8")
            data = json.loads(body)
            if response.status == 200 and data.get("ok"):
                logging.info(f"Telegram sent to {chat_id}")
                return True, "sent", ""
            return False, "failed", data.get("description", "Unknown error")
    except Exception as e:
        logging.error(f"Telegram error: {e}")
        return False, "error", str(e)

def load_settings() -> None:
    # 1. Start with ENV as base
    state.youtube_api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    state.youtube_channel_id = os.getenv("YOUTUBE_CHANNEL_ID", "").strip()
    state.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    state.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    state.telegram_enabled = os.getenv("TELEGRAM_ENABLED", "false").lower() == "true"

    # 2. OVERWRITE with settings.json (The "Stickiness" logic)
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as h:
                saved = json.load(h)
            
            # If it's in the file, it's the absolute truth.
            # We use string casting and strip to be safe.
            if "youtube_api_key" in saved: state.youtube_api_key = str(saved["youtube_api_key"]).strip()
            if "youtube_channel_id" in saved: state.youtube_channel_id = str(saved["youtube_channel_id"]).strip()
            if "telegram_bot_token" in saved: state.telegram_bot_token = str(saved["telegram_bot_token"]).strip()
            if "telegram_chat_id" in saved: state.telegram_chat_id = str(saved["telegram_chat_id"]).strip()
            if "telegram_enabled" in saved: state.telegram_enabled = bool(saved["telegram_enabled"])
            if "telegram_notify_on_status_change" in saved: state.telegram_notify_on_status_change = bool(saved["telegram_notify_on_status_change"])
            if "check_interval" in saved: state.check_interval = int(saved["check_interval"])
            
            logging.info(f"Settings loaded from disk. Priority Chat ID: {state.telegram_chat_id}")
        except Exception as e:
            logging.error(f"Failed to load settings.json: {e}")

def save_settings() -> None:
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = state.model_dump(exclude={"youtube_is_live", "last_check_timestamp", "last_youtube_is_live"})
        with open(SETTINGS_FILE, "w", encoding="utf-8") as h:
            json.dump(data, h, indent=2)
        logging.info(f"Settings saved! Current Chat ID: {state.telegram_chat_id}")
    except Exception as e:
        logging.error(f"Failed to save settings: {e}")

async def stream_watchdog():
    logging.info("YouTube Watchdog active.")
    while True:
        try:
            if state.youtube_api_key and state.youtube_channel_id:
                is_live = check_youtube_live_status(state.youtube_api_key, state.youtube_channel_id)
                
                # Notification logic
                if state.telegram_enabled and state.telegram_notify_on_status_change:
                    if state.last_youtube_is_live is True and is_live is False:
                        send_telegram_message(state.telegram_bot_token, state.telegram_chat_id, "🚨 <b>ADÁS MEGÁLLT!</b>")
                    elif state.last_youtube_is_live is False and is_live is True:
                        send_telegram_message(state.telegram_bot_token, state.telegram_chat_id, "✅ <b>ADÁS ÚJRA INDULT!</b>")
                
                state.youtube_is_live = is_live
                state.last_youtube_is_live = is_live
            
            state.last_check_timestamp = datetime.now(timezone.utc)
            history.append(state.model_dump(mode='json'))
            await manager.broadcast_state()

            try:
                await asyncio.wait_for(check_now.wait(), timeout=state.check_interval)
                check_now.clear()
            except asyncio.TimeoutError:
                pass
        except Exception as e:
            logging.error(f"Watchdog loop error: {e}")
            await asyncio.sleep(10)

@app.on_event("startup")
async def startup():
    load_settings()
    asyncio.create_task(stream_watchdog())

@app.post("/api/check-now")
async def api_check():
    check_now.set()
    return {"ok": True}

@app.get("/api/history")
async def api_history():
    return list(history)

@app.post("/api/telegram-test")
async def api_test():
    msg = f"🔔 <b>TESZT</b>\nChat: {state.telegram_chat_id}\nID rögzítve! ✅"
    ok, code, detail = send_telegram_message(state.telegram_bot_token, state.telegram_chat_id, msg)
    return {"ok": ok, "detail": detail}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            updatable = ["youtube_api_key", "youtube_channel_id", "telegram_bot_token", 
                        "telegram_chat_id", "telegram_enabled", "telegram_notify_on_status_change", "check_interval"]
            changed = False
            for key in updatable:
                if key in data:
                    val = data[key]
                    if isinstance(val, str): val = val.strip()
                    setattr(state, key, val)
                    changed = True
            
            if changed:
                save_settings()
                await manager.broadcast_state()
                if any(k in data for k in ["youtube_api_key", "youtube_channel_id"]):
                    check_now.set()
    except Exception:
        manager.disconnect(websocket)

app.mount("/static", StaticFiles(directory="web/frontend/static"), name="static")
app.mount("/locales", StaticFiles(directory="web/frontend/locales"), name="locales")

@app.get("/")
async def index():
    return FileResponse('web/frontend/index.html')

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
