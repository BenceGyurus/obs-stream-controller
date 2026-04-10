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

# Configure logging to be very verbose for debugging
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
    
    youtube_api_key: str = os.getenv("YOUTUBE_API_KEY", "")
    youtube_channel_id: str = os.getenv("YOUTUBE_CHANNEL_ID", "")
    
    telegram_enabled: bool = os.getenv("TELEGRAM_ENABLED", "false").lower() == "true"
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
    telegram_notify_on_status_change: bool = os.getenv("TELEGRAM_NOTIFY_ON_STATUS_CHANGE", "true").lower() == "true"
    
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
        logging.info(f"New WebSocket connection. Total: {len(self.active_connections)}")
        await self.broadcast_state()

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logging.info(f"WebSocket disconnected. Remaining: {len(self.active_connections)}")

    async def broadcast_state(self):
        data = state.model_dump(mode='json')
        disconnected = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(data)
            except Exception:
                disconnected.append(connection)
        
        for connection in disconnected:
            self.disconnect(connection)

manager = ConnectionManager()
app = FastAPI()

def send_telegram_message(bot_token: str, chat_id: str, text: str) -> tuple[bool, str, str]:
    bot_token = bot_token.strip().strip("'\"")
    chat_id = chat_id.strip().strip("'\"")
    
    if not bot_token or not chat_id:
        logging.warning(f"Telegram skipped: token={bool(bot_token)}, chat_id={bool(chat_id)}")
        return False, "missing_credentials", "Bot token or chat id missing."
    
    logging.info(f"Attempting Telegram send to Chat ID: {chat_id}")
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        params = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        payload = urllib.parse.urlencode(params).encode("utf-8")
        req = urllib.request.Request(url, data=payload, method="POST")
        
        with urllib.request.urlopen(req, timeout=15) as response:
            body = response.read().decode("utf-8")
            data = json.loads(body)
            if response.status == 200 and data.get("ok"):
                logging.info(f"Telegram message sent successfully to {chat_id}")
                return True, "sent", ""
            else:
                desc = data.get("description", "Unknown error")
                logging.error(f"Telegram API error: {desc}")
                return False, "send_failed", desc
    except Exception as e:
        logging.error(f"Failed to send Telegram message: {e}")
        return False, "send_failed", str(e)

def load_settings() -> None:
    # 1. Start with defaults/ENV
    state.youtube_api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    state.youtube_channel_id = os.getenv("YOUTUBE_CHANNEL_ID", "").strip()
    state.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    state.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    # 2. Layer settings.json if it exists
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as h:
                data = json.load(h)
            
            # Use JSON values if they are NOT empty, allowing UI overrides to persist
            if data.get("youtube_api_key"): state.youtube_api_key = data["youtube_api_key"]
            if data.get("youtube_channel_id"): state.youtube_channel_id = data["youtube_channel_id"]
            if data.get("telegram_bot_token"): state.telegram_bot_token = data["telegram_bot_token"]
            if data.get("telegram_chat_id"): state.telegram_chat_id = data["telegram_chat_id"]
            
            state.telegram_enabled = bool(data.get("telegram_enabled", state.telegram_enabled))
            state.telegram_notify_on_status_change = bool(data.get("telegram_notify_on_status_change", True))
            state.check_interval = int(data.get("check_interval", 900))
            
            logging.info(f"Settings loaded. Chat ID: {state.telegram_chat_id}")
        except Exception as e:
            logging.error(f"Load settings failed: {e}")

def save_settings() -> None:
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "youtube_api_key": state.youtube_api_key,
            "youtube_channel_id": state.youtube_channel_id,
            "telegram_enabled": state.telegram_enabled,
            "telegram_bot_token": state.telegram_bot_token,
            "telegram_chat_id": state.telegram_chat_id,
            "telegram_notify_on_status_change": state.telegram_notify_on_status_change,
            "check_interval": state.check_interval,
        }
        with open(SETTINGS_FILE, "w", encoding="utf-8") as h:
            json.dump(data, h, indent=2)
        logging.info("Settings saved to disk.")
    except Exception as e:
        logging.error(f"Save settings failed: {e}")

async def stream_watchdog():
    logging.info("Watchdog starting...")
    while True:
        try:
            if state.youtube_api_key and state.youtube_channel_id:
                logging.info(f"Checking YouTube: {state.youtube_channel_id}")
                is_live = check_youtube_live_status(state.youtube_api_key, state.youtube_channel_id)
                
                # IMPORTANT: Status change logic
                if state.telegram_enabled and state.telegram_notify_on_status_change:
                    if state.last_youtube_is_live is True and is_live is False:
                        msg = "🚨 <b>HIBA!</b> A YouTube adás megállt! 😱"
                        send_telegram_message(state.telegram_bot_token, state.telegram_chat_id, msg)
                    elif state.last_youtube_is_live is False and is_live is True:
                        msg = "✅ <b>RENDBEN!</b> Az adás újra élőben! 🎉"
                        send_telegram_message(state.telegram_bot_token, state.telegram_chat_id, msg)
                
                state.youtube_is_live = is_live
                state.last_youtube_is_live = is_live
            else:
                logging.warning("YouTube check skipped: Missing credentials.")

            state.last_check_timestamp = datetime.now(timezone.utc)
            history.append(state.model_dump(mode='json'))
            await manager.broadcast_state()

            try:
                await asyncio.wait_for(check_now.wait(), timeout=state.check_interval)
                check_now.clear()
                logging.info("Triggered immediate check.")
            except asyncio.TimeoutError:
                pass
        except Exception as e:
            logging.error(f"Watchdog error: {e}")
            await asyncio.sleep(10)

@app.on_event("startup")
async def startup():
    load_settings()
    asyncio.create_task(stream_watchdog())

@app.post("/api/check-now")
async def api_check_now():
    check_now.set()
    return {"status": "triggered"}

@app.get("/api/history")
async def api_history():
    return list(history)

@app.post("/api/telegram-test")
async def api_test_tg():
    msg = f"🔔 <b>TESZT</b>\nChat ID: {state.telegram_chat_id}\nIdő: {datetime.now().strftime('%H:%M:%S')}"
    ok, code, detail = send_telegram_message(state.telegram_bot_token, state.telegram_chat_id, msg)
    return {"ok": ok, "detail": detail}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # Update state from UI
            fields = ["youtube_api_key", "youtube_channel_id", "telegram_bot_token", 
                      "telegram_chat_id", "telegram_enabled", "telegram_notify_on_status_change", "check_interval"]
            changed = False
            for f in fields:
                if f in data:
                    val = data[f]
                    if isinstance(val, str): val = val.strip()
                    setattr(state, f, val)
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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
