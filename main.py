"""
OBS Stream Watchdog

Ez a szkript figyeli a megadott YouTube csatorna élő adásának állapotát.
Ha azt észleli, hogy a stream offline, automatikusan megpróbálja elindítani
az OBS Studio-ban futó streamet a obs-websocket plugin segítségével.

A konfigurációs adatok a gyökérkönyvtárban található .env fájlból töltődnek be.
"""
import os
import sys
import logging
from dotenv import load_dotenv
from obswebsocket import obsws, requests as obsrequests, exceptions
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- Alapvető naplózási konfiguráció ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
)

def check_youtube_live_status(api_key, channel_id):
    """
    Ellenőrzi, hogy a megadott YouTube csatorna jelenleg élő adásban van-e.

    Args:
        api_key (str): A YouTube Data API v3 kulcsa.
        channel_id (str): A YouTube csatorna egyedi azonosítója.

    Returns:
        bool: True, ha a csatorna élő adásban van, különben False.
              Hibás API kulcs vagy hiba esetén is False-t ad vissza.
    """
    if not api_key or not channel_id or "YOUR_YOUTUBE" in api_key:
        logging.error("A YouTube API kulcs vagy a csatorna ID nincs beállítva. Ellenőrzés kihagyva.")
        return False

    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        request = youtube.search().list(
            part='snippet',
            channelId=channel_id,
            eventType='live',
            type='video'
        )
        response = request.execute()

        if response['items']:
            logging.info("A YouTube stream jelenleg ÉLŐ ADÁSBAN van.")
            return True
        else:
            logging.info("A YouTube stream jelenleg OFFLINE.")
            return False
    except HttpError as e:
        logging.error(f"Hiba történt a YouTube API-val való kommunikáció során: {e}")
        return False # Biztonsági okokból offline-nak tekintjük
    except Exception as e:
        logging.error(f"Váratlan hiba történt a YouTube állapotának ellenőrzésekor: {e}")
        return False


def start_obs_stream(host, port, password):
    """
    Csatlakozik az OBS-hez a websocketen keresztül és elindítja a streamet.

    Args:
        host (str): Az OBS WebSocket szerver IP címe (pl. 'localhost').
        port (int): Az OBS WebSocket szerver portja (pl. 4455).
        password (str): Az OBS WebSocket szerver jelszava.

    Returns:
        bool: True, ha a parancsot sikeresen elküldte vagy a stream már futott.
              Sikertelen csatlakozás vagy hiba esetén False-t ad vissza.
    """
    try:
        ws = obsws(host, port, password)
        ws.connect()
        logging.info("Sikeresen csatlakozva az OBS WebSockethez.")

        # Ellenőrizzük, hogy a stream már fut-e
        status_response = ws.call(obsrequests.GetStreamStatus())
        if status_response.get_output_active():
             logging.warning("Az OBS stream már aktív. Nincs teendő.")
        else:
            logging.info("Az OBS stream nem aktív. Indítási parancs küldése...")
            ws.call(obsrequests.StartStream())
            logging.info("A StartStream parancs elküldve az OBS-nek.")

        ws.disconnect()
        return True

    except exceptions.ConnectionFailure:
        logging.error("Nem sikerült csatlakozni az OBS WebSockethez. Fut az OBS? Engedélyezve van a websocket plugin és helyes a jelszó?")
        return False
    except Exception as e:
        logging.error(f"Váratlan hiba történt az OBS WebSocket kapcsolat során: {e}")
        return False


def main():
    """
    Fő funkció a szkript futtatásához.

    Betölti a környezeti változókat a .env fájlból, validálja a konfigurációt,
    majd ellenőrzi a YouTube stream állapotát. Ha a stream offline,
    megpróbálja elindítani az OBS-ben.
    """
    load_dotenv()

    # --- Konfiguráció betöltése ---
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
    YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID")
    OBS_HOST = os.getenv("OBS_WEBSOCKET_HOST", "localhost")
    OBS_PORT = os.getenv("OBS_WEBSOCKET_PORT", "4455")
    OBS_PASSWORD = os.getenv("OBS_WEBSOCKET_PASSWORD")

    # --- Konfiguráció validálása ---
    if not all([YOUTUBE_API_KEY, YOUTUBE_CHANNEL_ID, OBS_PASSWORD]):
        logging.error("Egy vagy több kötelező környezeti változó hiányzik.")
        logging.error("Kérlek, add meg a YOUTUBE_API_KEY, YOUTUBE_CHANNEL_ID és OBS_WEBSOCKET_PASSWORD értékeket a .env fájlban.")
        sys.exit(1)

    logging.info("Stream állapotának ellenőrzése...")

    is_live = check_youtube_live_status(YOUTUBE_API_KEY, YOUTUBE_CHANNEL_ID)

    if not is_live:
        logging.info("A stream offline. A stream indítása OBS-en keresztül...")
        start_obs_stream(OBS_HOST, int(OBS_PORT), OBS_PASSWORD)
    else:
        logging.info("A stream már élőben van. Nincs szükség beavatkozásra.")

    logging.info("Ellenőrzés befejezve.")


if __name__ == "__main__":
    main()