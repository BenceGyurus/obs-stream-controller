# Broadcast Selection Guide

This guide explains how to select which YouTube broadcast to use for the stream reset feature.

## Auto-Detection (Default)

By default, the application automatically detects your active broadcast using the following priority:

1. **LIVE** broadcasts (currently streaming)
2. **READY** broadcasts (scheduled and ready to go live)
3. **TESTING** broadcasts (in testing mode)

If multiple broadcasts exist in the same status, the first one is used.

## Manual Broadcast Selection

If auto-detection doesn't work or you want to use a specific broadcast, you can manually specify the broadcast ID.

### Finding Your Broadcast ID

#### Method 1: Check the Logs

1. Run the application once with auto-detection
2. Look at the logs - if no active broadcasts are found, the app will list ALL available broadcasts:

```
WARNING - No active broadcasts found (LIVE/READY/TESTING). All broadcasts:
WARNING -   - My Stream Title (ID: abc123xyz456, Status: complete)
WARNING -   - Another Stream (ID: def789ghi012, Status: revoked)
```

3. Copy the broadcast ID you want to use

#### Method 2: YouTube Studio

1. Go to [YouTube Studio](https://studio.youtube.com)
2. Click on **Live** in the left sidebar
3. Select your broadcast
4. Look at the URL - the broadcast ID is the last part:
   ```
   https://studio.youtube.com/video/abc123xyz456/livestreaming
                                  ^^^^^^^^^^^^^^
                                  This is your broadcast ID
   ```

#### Method 3: YouTube API Explorer

1. Go to [YouTube API Explorer](https://developers.google.com/youtube/v3/docs/liveBroadcasts/list)
2. Set `part` to `id,snippet,status`
3. Set `mine` to `true`
4. Click **Execute**
5. Find your broadcast in the response and copy its `id`

### Setting the Broadcast ID

#### Option 1: Environment Variable (Recommended)

Add to your `.env` file:

```bash
YOUTUBE_BROADCAST_ID="abc123xyz456"
```

Or in `docker-compose.yml`:

```yaml
environment:
  - YOUTUBE_BROADCAST_ID=abc123xyz456
```

#### Option 2: Command Line

When running Docker:

```bash
docker run -e YOUTUBE_BROADCAST_ID="abc123xyz456" ...
```

When running locally:

```bash
export YOUTUBE_BROADCAST_ID="abc123xyz456"
python -m web.backend.main
```

## Troubleshooting

### "Broadcast ID not found"

**Cause:** The specified broadcast ID doesn't exist or you don't have access to it.

**Solution:**
- Double-check the broadcast ID is correct
- Make sure you're authenticated with the correct Google account
- Verify the broadcast exists in YouTube Studio

### "No active broadcasts found"

**Cause:** All your broadcasts are in COMPLETE or REVOKED status.

**Solutions:**

1. **Create a new broadcast** in YouTube Studio or OBS
2. **Use an existing broadcast** by setting `YOUTUBE_BROADCAST_ID`
3. **Use persistent stream key** instead of broadcast-based streaming:
   - Go to YouTube Studio → Settings → Stream
   - Create a persistent stream key
   - Use this key in OBS instead of creating broadcasts

### Multiple Active Broadcasts Warning

**Cause:** You have multiple broadcasts in LIVE, READY, or TESTING status.

**What happens:** The app uses the first one found (prioritizing LIVE > READY > TESTING).

**Solution:** If you want to use a specific broadcast, set `YOUTUBE_BROADCAST_ID`.

## When to Use Manual Selection

Use manual broadcast selection when:

- Auto-detection picks the wrong broadcast
- You have multiple active broadcasts
- Your broadcast is in an unsupported status (like COMPLETE) but you still want to use it
- You're debugging broadcast issues

## Examples

### Docker Compose

```yaml
version: '3.8'
services:
  obs-stream-control:
    image: ghcr.io/yourname/obs-stream-control:latest
    environment:
      - YOUTUBE_API_KEY=${YOUTUBE_API_KEY}
      - YOUTUBE_CHANNEL_ID=${YOUTUBE_CHANNEL_ID}
      - YOUTUBE_BROADCAST_ID=abc123xyz456  # Specific broadcast
      - OBS_WEBSOCKET_HOST=host.docker.internal
      - OBS_WEBSOCKET_PORT=4455
      - OBS_WEBSOCKET_PASSWORD=${OBS_WEBSOCKET_PASSWORD}
```

### .env File

```bash
# YouTube API Configuration
YOUTUBE_API_KEY="AIzaSyABC123..."
YOUTUBE_CHANNEL_ID="UCxyz789..."

# Manual broadcast selection
YOUTUBE_BROADCAST_ID="abc123xyz456"

# OBS WebSocket
OBS_WEBSOCKET_HOST="host.docker.internal"
OBS_WEBSOCKET_PORT="4455"
OBS_WEBSOCKET_PASSWORD="your_password"
```

### Local Development

```bash
# Set environment variable
export YOUTUBE_BROADCAST_ID="abc123xyz456"

# Run the application
python -m web.backend.main
```

## Broadcast Statuses

Understanding YouTube broadcast statuses:

| Status | Description | Auto-Selected? |
|--------|-------------|----------------|
| **live** | Currently streaming | ✅ Yes (Priority 1) |
| **ready** | Scheduled, ready to go live | ✅ Yes (Priority 2) |
| **testing** | Test mode | ✅ Yes (Priority 3) |
| **complete** | Stream ended | ❌ No (use manual selection) |
| **revoked** | Cancelled/deleted | ❌ No (use manual selection) |
| **created** | Just created, not ready | ❌ No |

## Related Documentation

- [MULTIPLE_BROADCASTS.md](MULTIPLE_BROADCASTS.md) - How the app handles multiple broadcasts
- [SETUP.md](SETUP.md) - Complete setup guide including broadcast management
- [SYNOLOGY.md](SYNOLOGY.md) - Synology NAS specific instructions
