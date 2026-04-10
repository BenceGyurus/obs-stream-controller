"""
YouTube Stream Monitor

This script monitors a YouTube channel's live status using the YouTube Data API.
"""
import logging
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def check_youtube_live_status(api_key, channel_id):
    """
    Checks if the specified YouTube channel is currently live.
    Uses a more robust check by looking at both the filtered live search 
    and the latest channel activity if needed.
    """
    if not api_key or not channel_id or "YOUR_YOUTUBE" in api_key:
        logging.error("YouTube API Key or Channel ID is not set. Skipping check.")
        return False
    
    # Clean inputs
    api_key = api_key.strip().strip("'\"")
    channel_id = channel_id.strip().strip("'\"")
    
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        # Strategy 1: Direct search for live events (standard but can be cached)
        request = youtube.search().list(
            part='snippet', 
            channelId=channel_id, 
            eventType='live', 
            type='video',
            maxResults=1
        )
        response = request.execute()
        
        if response.get('items'):
            logging.info(f"YouTube search confirmed LIVE status for {channel_id}.")
            return True
            
        # Strategy 2: Check latest video from the channel if Strategy 1 fails
        # This can sometimes catch a live stream that Strategy 1 missed due to search indexing delays
        request_latest = youtube.search().list(
            part='snippet',
            channelId=channel_id,
            order='date',
            type='video',
            maxResults=3
        )
        response_latest = request_latest.execute()
        
        for item in response_latest.get('items', []):
            if item.get('snippet', {}).get('liveBroadcastContent') == 'live':
                logging.info(f"YouTube latest activity confirmed LIVE status for {channel_id}.")
                return True
                
        logging.info(f"YouTube stream for {channel_id} is currently OFFLINE.")
        return False
        
    except HttpError as e:
        logging.error(f"YouTube API Error: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error checking YouTube status: {type(e).__name__}: {e}")
        return False
