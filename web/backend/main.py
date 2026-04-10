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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)

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
        await self.broadcast_state()

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
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
        payload = urllib.parse.urlencode({"chat_id": chat_id, "text": text, "parse_mode": "HTML"}).encode("utf-8")
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
        
        state.youtube_api_key = str(data.get("youtube_api_key", state.youtube_api_key) or "")
        state.youtube_channel_id = str(data.get("youtube_channel_id", state.youtube_channel_id) or "")
        
        state.telegram_enabled = bool(data.get("telegram_enabled", state.telegram_enabled))
        state.telegram_bot_token = str(data.get("telegram_bot_token", state.telegram_bot_token) or "")
        state.telegram_chat_id = str(data.get("telegram_chat_id", state.telegram_chat_id) or "")
        state.telegram_notify_on_status_change = bool(
            data.get("telegram_notify_on_status_change", state.telegram_notify_on_status_change)
        )
        state.check_interval = int(data.get("check_interval", state.check_interval))
        logging.info(f"Loaded settings from {SETTINGS_FILE}.")
    except Exception as e:
        logging.warning(f"Failed to load settings from {SETTINGS_FILE}: {e}")

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
        with open(SETTINGS_FILE, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
        logging.info(f"Saved settings to {SETTINGS_FILE}.")
    except Exception as e:
        logging.warning(f"Failed to save settings to {SETTINGS_FILE}: {e}")

async def stream_watchdog():
    logging.info("Stream watchdog task started.")
    while True:
        try:
            if state.youtube_api_key and state.youtube_channel_id:
                logging.info("Checking stream status...")
                try:
                    state.youtube_is_live = check_youtube_live_status(state.youtube_api_key, state.youtube_channel_id)
                except Exception as e:
                    logging.error(f"Error checking YouTube status: {e}")

                if state.telegram_enabled and state.telegram_notify_on_status_change:
                    # Status changed from Online to Offline
                    if state.last_youtube_is_live is True and state.youtube_is_live is False:
                        message = (
                            "🚨 <b>HIBA AZ ÉLŐ ADÁSBAN!</b>\n\n"
                            "A YouTube élő adás jelenleg <b>OFFLINE</b> állapotban van! 😱\n"
                            "Valami gáz van, nézz rá minél előbb! 🏃‍♂️💨\n\n"
                            f"⏰ Időpont: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
                        )
                        ok, code, detail = send_telegram_message(state.telegram_bot_token, state.telegram_chat_id, message)
                        if not ok:
                            logging.warning(f"Telegram alert failed ({code}): {detail}")
                    
                    # Status changed from Offline to Online
                    elif state.last_youtube_is_live is False and state.youtube_is_live is True:
                        message = (
                            "✅ <b>ÚJRA ÉLŐBEN!</b>\n\n"
                            "A YouTube élő adás újra <b>ONLINE</b>! 🎉\n"
                            "Minden a legnagyobb rendben, mehet a show! 🎤🎸\n\n"
                            f"⏰ Időpont: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
                        )
                        ok, code, detail = send_telegram_message(state.telegram_bot_token, state.telegram_chat_id, message)
                        if not ok:
                            logging.warning(f"Telegram alert failed ({code}): {detail}")
            else:
                logging.warning("YouTube API Key or Channel ID missing. Skipping check.")

            state.last_youtube_is_live = state.youtube_is_live
            state.last_check_timestamp = datetime.now(timezone.utc)
            history.append(state.model_dump(mode='json'))
            await manager.broadcast_state()

            interval = state.check_interval
            logging.info(f"Check complete. Waiting for {interval} seconds.")
            
            try:
                await asyncio.wait_for(check_now.wait(), timeout=interval)
                check_now.clear()
                logging.info("Manual check triggered. Running immediate check.")
            except asyncio.TimeoutError:
                pass
        except Exception as e:
            logging.error(f"Unexpected error in stream_watchdog loop: {e}")
            await asyncio.sleep(10)

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
        return {"ok": False, "code": "disabled", "detail": "Telegram alerts are disabled"}
    if not state.telegram_bot_token or not state.telegram_chat_id:
        return {"ok": False, "code": "missing_credentials", "detail": "Telegram bot token or chat id missing"}
    
    message = (
        "🔔 <b>TESZT ÜZENET</b>\n\n"
        "Ez egy teszt üzenet a Stream Monitor rendszertől.\n"
        "A Telegram értesítések megfelelően működnek! 👍\n\n"
        f"⏰ Időpont: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )
    ok, code, detail = send_telegram_message(state.telegram_bot_token, state.telegram_chat_id, message)
    return {"ok": ok, "code": code, "detail": detail}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            changed = False
            settings_changed = False
            
            if "youtube_api_key" in data:
                state.youtube_api_key = str(data["youtube_api_key"])
                changed = True
                settings_changed = True
            
            if "youtube_channel_id" in data:
                state.youtube_channel_id = str(data["youtube_channel_id"])
                changed = True
                settings_changed = True
            
            if "check_interval" in data and data["check_interval"] != state.check_interval:
                state.check_interval = int(data["check_interval"])
                changed = True
                settings_changed = True
            
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
                
            if "telegram_notify_on_status_change" in data:
                state.telegram_notify_on_status_change = bool(data["telegram_notify_on_status_change"])
                changed = True
                settings_changed = True
            
            if changed:
                if settings_changed:
                    save_settings()
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
