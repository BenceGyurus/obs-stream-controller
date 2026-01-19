"""
OBS Stream Watchdog (Service Version - Simplified)

This script runs continuously to monitor a YouTube channel's live status.
If the stream is offline, it attempts to start the stream in OBS Studio.

This version does NOT set the stream title. The stream will start with
whatever title is currently configured in OBS Studio.
"""
import os
import sys
import logging
from dotenv import load_dotenv
from obswebsocket import obsws, requests as obsrequests, exceptions
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- Basic Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
)

def check_youtube_live_status(api_key, channel_id):
    """Checks if the specified YouTube channel is currently live."""
    if not api_key or not channel_id or "YOUR_YOUTUBE" in api_key:
        logging.error("YouTube API Key or Channel ID is not set. Skipping check.")
        return False
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        request = youtube.search().list(part='snippet', channelId=channel_id, eventType='live', type='video')
        response = request.execute()
        if response['items']:
            logging.info("YouTube stream is currently LIVE.")
            return True
        else:
            logging.info("YouTube stream is currently OFFLINE.")
            return False
    except HttpError as e:
        logging.error(f"An HTTP error occurred with the YouTube API: {e}")
        return False
    except Exception as e:
        logging.error(f"An unexpected error occurred while checking YouTube status: {e}")
        return False

def get_obs_stream_status(host, port, password):
    """Checks if the OBS stream is currently active."""
    try:
        ws = obsws(host, port, password)
        ws.connect()
        status_response = ws.call(obsrequests.GetStreamStatus())
        is_active = False
        if hasattr(status_response, 'datain') and isinstance(status_response.datain, dict):
            is_active = status_response.datain.get("outputActive", False)
        ws.disconnect()
        return is_active
    except exceptions.ConnectionFailure:
        logging.error("Failed to connect to OBS WebSocket to get status.")
        return False
    except Exception as e:
        logging.error(f"An unexpected error occurred with OBS WebSocket while getting status: {e}")
        return False

def start_obs_stream(host, port, password):
    """Connects to OBS via websocket and starts the stream."""
    try:
        ws = obsws(host, port, password)
        ws.connect()
        logging.info("Successfully connected to OBS WebSocket.")
        
        status_response = ws.call(obsrequests.GetStreamStatus())
        
        is_active = False
        if hasattr(status_response, 'datain') and isinstance(status_response.datain, dict):
            is_active = status_response.datain.get("outputActive", False)

        if is_active:
            logging.warning("OBS stream is already active. No action taken.")
        else:
            logging.info("OBS stream is not active. Sending start command...")
            ws.call(obsrequests.StartStream())
            logging.info("StartStream command sent to OBS.")
        
        ws.disconnect()
        return True
    except exceptions.ConnectionFailure:
        logging.error("Failed to connect to OBS WebSocket. Is OBS running and the plugin configured correctly?")
        return False
    except Exception as e:
        logging.error(f"An unexpected error occurred with OBS WebSocket: {e}")
        return False
