"""
YouTube Stream Monitor

This script monitors a YouTube channel's live status using the YouTube Data API.
"""
import logging
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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
        logging.error(f"An unexpected error occurred while checking YouTube status: {type(e).__name__}: {e}")
        return False
