# OBS Stream Watchdog

A Python script that monitors the status of a YouTube stream and automatically starts the stream in OBS Studio via `obs-websocket` if it goes offline.

## Prerequisites

Before you begin, ensure you have the following:

1.  **OBS Studio with `obs-websocket` plugin:**
    *   Install the `obs-websocket` plugin. For installation instructions, see the official [obs-websocket releases page](https://github.com/obsproject/obs-websocket/releases).
    *   In OBS, go to **Tools -> WebSocket Server Settings**, enable the server, set a port (default: 4455), and **set a strong password**.

2.  **YouTube Data API Key:**
    *   Go to the [Google Cloud Console](https://console.cloud.google.com/).
    *   Create a project, enable the **"YouTube Data API v3"**, and create an API key.

3.  **Your YouTube Channel ID:**
    *   Find this in your [YouTube advanced account settings](https://www.youtube.com/account_advanced).

4.  **Python 3:** Ensure Python 3 is installed on your system.

## Installation and Configuration

1.  **Clone or download the project files** into a directory on your computer.

2.  **Install Python Dependencies:**
    Open a terminal in the project directory and run:
    ```bash
    pip3 install -r requirements.txt
    ```

3.  **Create and Edit the `.env` file:**
    *   Copy the `.env.example` file to `.env`:
        ```bash
        cp .env.example .env
        ```
    *   Open the new `.env` file and replace the placeholder values with your actual credentials.
        ```ini
        YOUTUBE_API_KEY="YOUR_YOUTUBE_API_KEY_HERE"
        YOUTUBE_CHANNEL_ID="YOUR_YOUTUBE_CHANNEL_ID_HERE"
        OBS_WEBSOCKET_HOST="localhost"
        OBS_WEBSOCKET_PORT="4455"
        OBS_WEBSOCKET_PASSWORD="YOUR_OBS_WEBSOCKET_PASSWORD_HERE"
        ```

## Usage

### Manual Testing (Recommended First)

Before setting up automation, run the script manually to ensure your configuration is correct:

```bash
python3 main.py
```
Check the output for any errors. The script should log whether the stream is LIVE or OFFLINE.

## Deployment: Automated Execution

To avoid exceeding the YouTube API's daily quota, it is critical to run the script at a reasonable interval. **A 15-minute interval is recommended.**

### Option 1: macOS & Linux (using `cron`)

1.  Open your crontab file for editing:
    ```bash
    crontab -e
    ```

2.  Add the following line to schedule the script to run every 15 minutes. Make sure to replace the paths with the absolute paths to your python3 executable and `main.py` script.

    ```cron
    */15 * * * * /usr/bin/python3 /path/to/your/project/obs-stream-control/main.py >> /tmp/obs_stream_control.log 2>&1
    ```
    *   You can find your python3 path by running `which python3`.
    *   The `>> /tmp/obs_stream_control.log 2>&1` part logs all output, which is useful for debugging.

3.  Save and exit the editor.

### Option 2: Windows (using Task Scheduler)

1.  **Open Task Scheduler:** Press `Win + R`, type `taskschd.msc`, and press Enter.

2.  **Create a Basic Task:** In the right-hand Actions pane, click "Create Basic Task...".
    *   **Name:** Give it a name like `OBS Stream Watchdog`.
    *   **Trigger:** Select "Daily" and click Next. Leave the daily time as default.
    *   **Action:** Select "Start a program".

3.  **Configure the Program/Script:**
    *   **Program/script:** Enter the full path to your `pythonw.exe` executable (using `pythonw.exe` prevents a console window from popping up). You can find the path by running `where pythonw.exe` in Command Prompt.
    *   **Add arguments:** Enter the full path to your `main.py` script.
    *   **Start in:** Enter the full path to the project directory where `main.py` and `.env` are located. This is crucial for the script to find the `.env` file.

4.  **Set the Repetition Interval:**
    *   Click "Finish" to create the task.
    *   In the main Task Scheduler library, find your new task, right-click it, and select "Properties".
    *   Go to the **Triggers** tab and click "Edit...".
    *   Under "Advanced settings", check the box for **"Repeat task every:"** and set the value to **"15 minutes"**. Set the duration to **"Indefinitely"**.
    *   Click "OK" on all windows to save.

Your script is now deployed and will run automatically.
# obs-stream-controller
# obs-stream-controller
