# YouTube Stream Monitor

A simple, lightweight web application to monitor a YouTube channel's live status and send Telegram notifications when the stream goes offline or comes back online.

## Features

- **YouTube Monitoring**: Checks if a specific channel is live using the YouTube Data API.
- **Telegram Notifications**: 
  - 🚨 Robust alerts when the stream goes offline with "cool" status messages.
  - ✅ Notifications when the stream is back online.
  - 🛠 Test message feature to verify Telegram configuration.
- **Web Interface**:
  - Real-time status dashboard.
  - Configurable check intervals (default is 15 minutes/900 seconds).
  - History chart showing stream status over time.
  - Multi-language support (English, Hungarian).

## Prerequisites

- Python 3.9+
- YouTube Data API Key
- YouTube Channel ID
- Telegram Bot Token and Chat ID (for notifications)

## Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/obs-stream-control.git
   cd obs-stream-control
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and provide your:
   - `YOUTUBE_API_KEY`
   - `YOUTUBE_CHANNEL_ID`
   - `TELEGRAM_BOT_TOKEN` (optional, can be set in UI)
   - `TELEGRAM_CHAT_ID` (optional, can be set in UI)

4. **Run the application**:
   ```bash
   python -m web.backend.main
   ```

5. **Access the dashboard**:
   Open `http://localhost:8000` in your browser.

## Docker Usage

You can also run the monitor using Docker:

```bash
docker-compose up -d
```

## Settings

Settings like the Telegram bot token, chat ID, and check interval can be updated directly from the web interface and are saved to a `settings.json` file.

## License

MIT
