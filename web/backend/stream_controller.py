"""
OBS Stream Watchdog (Service Version - Enhanced)

This script runs continuously to monitor a YouTube channel's live status.
If the stream is offline, it attempts to start the stream in OBS Studio.

Enhanced with YouTube Broadcast management to handle stream reconnection
issues after OBS restarts.
"""
import os
import sys
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
from obswebsocket import obsws, requests as obsrequests, exceptions
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# --- Basic Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
)

# --- YouTube OAuth2 Scopes ---
SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']

def get_authenticated_youtube_service(client_secret_file, headless=False):
    """
    Authenticates and returns a YouTube API service object with OAuth2.
    Handles token refresh automatically.
    
    Args:
        client_secret_file: Path to the OAuth2 client secret JSON file
        headless: If True, uses console-based auth (for servers/NAS without browser)
    """
    creds = None
    token_file = Path('token.json')
    
    # Load existing credentials if available
    if token_file.exists():
        try:
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        except Exception as e:
            logging.warning(f"Failed to load existing credentials: {e}")
    
    # If credentials don't exist or are invalid, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                logging.info("Refreshing expired credentials...")
                creds.refresh(Request())
            except Exception as e:
                logging.error(f"Failed to refresh credentials: {e}")
                creds = None
        
        if not creds:
            if not Path(client_secret_file).exists():
                logging.error(f"Client secret file not found: {client_secret_file}")
                logging.error("Please download client_secret.json from Google Cloud Console.")
                return None
            
            logging.info("Starting OAuth2 authentication flow...")
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, SCOPES)
            
            # Choose authentication method based on environment
            if headless or os.getenv('OAUTH_HEADLESS', 'false').lower() == 'true':
                # Headless mode - requires pre-authenticated token.json
                logging.error("=" * 70)
                logging.error("AUTHENTICATION REQUIRED")
                logging.error("=" * 70)
                logging.error("")
                logging.error("Running in HEADLESS mode but token.json is missing or invalid.")
                logging.error("")
                logging.error("Please authenticate using one of these methods:")
                logging.error("")
                logging.error("METHOD 1 (Recommended): Use the standalone authentication script")
                logging.error("  1. On a machine with a browser, run: python3 authenticate.py")
                logging.error("  2. Copy the generated token.json to your NAS/server")
                logging.error("  3. Mount it in docker-compose.yml:")
                logging.error("     volumes:")
                logging.error("       - ./token.json:/app/token.json:ro")
                logging.error("")
                logging.error("METHOD 2: Temporarily set OAUTH_HEADLESS=false and run with -it flags")
                logging.error("  docker run -it -e OAUTH_HEADLESS=false ...")
                logging.error("")
                logging.error("See SYNOLOGY.md for detailed instructions.")
                logging.error("=" * 70)
                return None
            else:
                # Browser-based authentication (default)
                try:
                    logging.info("Opening browser for authentication...")
                    creds = flow.run_local_server(host='localhost', port=8080, open_browser=True)
                except Exception as e:
                    logging.error(f"Browser-based authentication failed: {e}")
                    logging.error("")
                    logging.error("=" * 70)
                    logging.error("AUTHENTICATION FAILED")
                    logging.error("=" * 70)
                    logging.error("")
                    logging.error("Please use the standalone authentication script:")
                    logging.error("  1. Run: python3 authenticate.py")
                    logging.error("  2. Copy token.json to the application directory")
                    logging.error("  3. Restart the application")
                    logging.error("")
                    logging.error("See SETUP.md for detailed instructions.")
                    logging.error("=" * 70)
                    return None
        
        # Save credentials for future use
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
        logging.info("Credentials saved to token.json")
    
    return build('youtube', 'v3', credentials=creds)

def get_active_broadcast(youtube_service, channel_id):
    """
    Retrieves the currently active (live or ready) broadcast for the channel.
    Returns the broadcast object or None if not found.
    """
    try:
        # Get broadcasts that are either live or ready
        request = youtube_service.liveBroadcasts().list(
            part='id,snippet,status,contentDetails',
            broadcastStatus='all',
            maxResults=50
        )
        response = request.execute()
        
        if not response.get('items'):
            logging.info("No broadcasts found for the channel.")
            return None
        
        # Filter for broadcasts that are live, ready, or testing
        # Prioritize: live > ready > testing
        priority_order = ['live', 'ready', 'testing']
        
        for priority_status in priority_order:
            for broadcast in response['items']:
                status = broadcast['status']['lifeCycleStatus']
                if status == priority_status:
                    logging.info(f"Found active broadcast: {broadcast['snippet']['title']} (Status: {status})")
                    if len([b for b in response['items'] if b['status']['lifeCycleStatus'] in priority_order]) > 1:
                        logging.warning(f"Multiple active broadcasts found! Using the first '{priority_status}' one.")
                    return broadcast
        
        logging.info("No active or ready broadcasts found.")
        return None
    except HttpError as e:
        logging.error(f"YouTube API error while getting broadcasts: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error while getting broadcasts: {e}")
        return None

def reset_broadcast_connection(youtube_service, broadcast_id):
    """
    Resets a broadcast by transitioning it through states to refresh the connection.
    This helps resolve issues where OBS can't reconnect after a restart.
    
    Returns True if successful, False otherwise.
    """
    try:
        # First, get current broadcast status
        request = youtube_service.liveBroadcasts().list(
            part='status',
            id=broadcast_id
        )
        response = request.execute()
        
        if not response.get('items'):
            logging.error(f"Broadcast {broadcast_id} not found.")
            return False
        
        current_status = response['items'][0]['status']['lifeCycleStatus']
        logging.info(f"Current broadcast status: {current_status}")
        
        # Transition strategy based on current status
        if current_status == 'live':
            # If live, transition to testing first
            logging.info("Transitioning broadcast from 'live' to 'testing'...")
            youtube_service.liveBroadcasts().transition(
                broadcastStatus='testing',
                id=broadcast_id,
                part='status'
            ).execute()
            logging.info("Broadcast transitioned to 'testing'. Waiting for connection reset...")
            
            # Then back to live
            import time
            time.sleep(3)  # Give YouTube servers time to process
            
            logging.info("Transitioning broadcast back to 'live'...")
            youtube_service.liveBroadcasts().transition(
                broadcastStatus='live',
                id=broadcast_id,
                part='status'
            ).execute()
            logging.info("Broadcast transitioned back to 'live'.")
            return True
            
        elif current_status == 'ready':
            # If ready, transition to testing then back
            logging.info("Transitioning broadcast from 'ready' to 'testing'...")
            youtube_service.liveBroadcasts().transition(
                broadcastStatus='testing',
                id=broadcast_id,
                part='status'
            ).execute()
            
            import time
            time.sleep(3)
            
            logging.info("Transitioning broadcast to 'live'...")
            youtube_service.liveBroadcasts().transition(
                broadcastStatus='live',
                id=broadcast_id,
                part='status'
            ).execute()
            logging.info("Broadcast is now 'live'.")
            return True
            
        elif current_status == 'testing':
            # If already testing, just transition to live
            logging.info("Broadcast is in 'testing', transitioning to 'live'...")
            youtube_service.liveBroadcasts().transition(
                broadcastStatus='live',
                id=broadcast_id,
                part='status'
            ).execute()
            logging.info("Broadcast is now 'live'.")
            return True
        
        else:
            logging.warning(f"Broadcast is in unsupported status: {current_status}")
            return False
            
    except HttpError as e:
        logging.error(f"YouTube API error while resetting broadcast: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error while resetting broadcast: {e}")
        return False


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

def start_obs_stream(host, port, password, youtube_service=None, channel_id=None):
    """
    Connects to OBS via websocket and starts the stream.
    If youtube_service is provided, attempts to reset the broadcast connection first.
    """
    try:
        # Step 1: Reset YouTube broadcast if authenticated service is available
        if youtube_service and channel_id:
            logging.info("Attempting to reset YouTube broadcast connection...")
            broadcast = get_active_broadcast(youtube_service, channel_id)
            if broadcast:
                broadcast_id = broadcast['id']
                reset_success = reset_broadcast_connection(youtube_service, broadcast_id)
                if reset_success:
                    logging.info("YouTube broadcast connection reset successfully.")
                else:
                    logging.warning("Failed to reset YouTube broadcast, but continuing with OBS start...")
            else:
                logging.warning("No active broadcast found to reset. OBS may have trouble connecting.")
        
        # Step 2: Connect to OBS and start stream
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

def stop_obs_stream(host, port, password):
    """Connects to OBS via websocket and stops the stream."""
    try:
        ws = obsws(host, port, password)
        ws.connect()
        logging.info("Successfully connected to OBS WebSocket to stop stream.")
        ws.call(obsrequests.StopStream())
        logging.info("StopStream command sent to OBS.")
        ws.disconnect()
        return True
    except exceptions.ConnectionFailure:
        logging.error("Failed to connect to OBS WebSocket to stop stream.")
        return False
    except Exception as e:
        logging.error(f"An unexpected error occurred with OBS WebSocket while stopping stream: {e}")
        return False
