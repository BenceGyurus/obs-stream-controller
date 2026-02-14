# OBS Stream Control

A Python application that monitors the status of a YouTube stream and automatically starts the stream in OBS Studio if it goes offline. This version features a modern, real-time, bilingual web dashboard for advanced control and monitoring.

**NEW:** Enhanced with YouTube Broadcast Management to automatically handle stream reconnection issues after OBS restarts!

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/obs-stream-control.git
cd obs-stream-control

# 2. Setup environment variables
cp .env.example .env
# Edit .env with your credentials

# 3. Add your OAuth credentials
# Download client_secret.json from Google Cloud Console to project root

# 4. Start with Docker Compose
docker-compose up -d

# 5. Access dashboard
# Open http://localhost:8000 in your browser
```

For detailed setup instructions, see [SETUP.md](SETUP.md)

---

## English

### Features

-   **Modern Dashboard UI:** A sleek, real-time web interface to monitor and control the application.
-   **Bilingual Support:** Switch between English and Hungarian on the fly.
-   **Real-time Status:** See the live status of your YouTube and OBS streams.
-   **Uptime History Graph:** Visualize the uptime of your YouTube and OBS streams over the last 200 checks.
-   **Dynamic Controls:**
    -   Enable or disable YouTube checking and OBS control with modern switches.
    -   Set a custom check interval.
    -   Toggle "Live Mode" for rapid 1-minute checks.
-   **Manual Check:** Trigger a manual status check at any time.
-   **Next Check Countdown:** A timer shows you exactly when the next automatic check will occur.
-   **YouTube Broadcast Reset:** Automatically resets YouTube broadcast connection when OBS restarts, eliminating the need to manually re-enter stream keys.

### Configuration

#### Step 1: YouTube API Setup

1.  **Get a YouTube Data API Key:**
    -   Go to [Google Cloud Console](https://console.cloud.google.com/)
    -   Create a new project or select an existing one
    -   Enable the YouTube Data API v3
    -   Create credentials (API Key) for read-only operations

2.  **Set up OAuth2 for Broadcast Management (Required for auto-reconnection):**
    -   In the same Google Cloud project, create OAuth 2.0 Client ID
    -   Application type: "Desktop app" or "Web application"
    -   Download the client secret JSON file
    -   Save it as `client_secret.json` in the project root directory

#### Step 2: Environment Configuration

1.  **Copy `.env.example` to `.env`:**
    ```bash
    cp .env.example .env
    ```

2.  **Edit the `.env` file** and fill in your actual credentials.

    ```ini
    # Your YouTube Data API Key from Google Cloud Console
    YOUTUBE_API_KEY="YOUR_YOUTUBE_API_KEY_HERE"

    # Your YouTube Channel ID
    YOUTUBE_CHANNEL_ID="YOUR_YOUTUBE_CHANNEL_ID_HERE"

    # Path to your OAuth2 client secret file (for broadcast management)
    YOUTUBE_CLIENT_SECRET_FILE="client_secret.json"

    # --- IMPORTANT ---
    # If running with Docker, use this special hostname to connect to OBS on your main machine.
    # Do not use 'localhost' or '127.0.0.1'.
    OBS_WEBSOCKET_HOST="host.docker.internal"

    # The port for the OBS WebSocket Server (default is 4455)
    OBS_WEBSOCKET_PORT="4455"

    # The password you set in the OBS WebSocket Server settings
    OBS_WEBSOCKET_PASSWORD="YOUR_OBS_WEBSOCKET_PASSWORD_HERE"
    ```

#### Step 3: First Run - OAuth2 Authentication

On the first run, the application will open a browser window for OAuth2 authentication:
1. Log in to your YouTube account
2. Grant the requested permissions
3. The credentials will be saved to `token.json` for future use

**Note:** Make sure to add `client_secret.json` and `token.json` to your `.gitignore` to keep your credentials secure!

### Running with Docker (Recommended)

#### Using Docker Compose (Easiest)

1.  **Make sure you have `docker-compose.yml` in your project root** (included in the repository)

2.  **Edit the `docker-compose.yml`** and replace `YOUR_USERNAME` with your GitHub username:
    ```yaml
    image: ghcr.io/YOUR_USERNAME/obs-stream-control:latest
    ```

3.  **Start the application:**
    ```bash
    docker-compose up -d
    ```

4.  **View logs:**
    ```bash
    docker-compose logs -f
    ```

5.  **Stop the application:**
    ```bash
    docker-compose down
    ```

#### Using Pre-built Image from GHCR (Manual Docker Run)

1.  **Pull the latest image:**
    ```bash
    docker pull ghcr.io/YOUR_USERNAME/obs-stream-control:latest
    ```

2.  **Run the container:**
    ```bash
    docker run --name obs-stream-control-container \
      -p 8000:8000 \
      --env-file .env \
      -v $(pwd)/client_secret.json:/app/client_secret.json \
      -v $(pwd)/token.json:/app/token.json \
      -d --restart always \
      ghcr.io/YOUR_USERNAME/obs-stream-control:latest
    ```

#### Building Locally

1.  **Build the Docker Image:**
    From the project's root directory, run the build command:
    ```bash
    docker build -t obs-stream-control .
    ```

2.  **Run the Docker Container:**
    This command will start your container, forward the necessary port for the web interface, and securely pass your credentials from the `.env` file.
    ```bash
    docker run --name obs-stream-control-container \
      -p 8000:8000 \
      --env-file .env \
      -v $(pwd)/client_secret.json:/app/client_secret.json \
      -v $(pwd)/token.json:/app/token.json \
      -d --restart always \
      obs-stream-control
    ```

3.  **Access the Dashboard:**
    Open your web browser and navigate to:
    **http://localhost:8000**

### Managing the Container

-   **View logs:** `docker logs -f obs-stream-control-container`
-   **Stop the container:** `docker stop obs-stream-control-container`
-   **Start the container:** `docker start obs-stream-control-container`
-   **Remove the container:** `docker rm obs-stream-control-container`

### How Broadcast Reset Works

When OBS restarts (e.g., after a Windows update), the YouTube broadcast can enter a state where it won't accept new connections with the same stream key. This application solves this by:

1. **Detecting** when OBS needs to reconnect
2. **Resetting** the YouTube broadcast state via the YouTube API
3. **Transitioning** the broadcast through states (live → testing → live) to refresh the connection
4. **Starting** the OBS stream with a fresh connection

This eliminates the need to manually re-enter the stream key in OBS after every restart!

---

## Magyar (Hungarian)

### Funkciók

-   **Modern Irányítópult:** Egy letisztult, valós idejű webes felület az alkalmazás figyeléséhez és vezérléséhez.
-   **Kétnyelvű Támogatás:** Váltson angol és magyar nyelv között menet közben.
-   **Valós Idejű Állapot:** Kövesse élőben a YouTube és OBS streamek állapotát.
-   **Előzmény Grafikon:** Vizualizálja a YouTube és OBS streamek üzemidejét az utolsó 200 ellenőrzés alapján.
-   **Dinamikus Vezérlők:**
    -   Engedélyezze vagy tiltsa le a YouTube-ellenőrzést és az OBS-vezérlést modern kapcsolókkal.
    -   Állítson be egyéni ellenőrzési intervallumot.
    -   Kapcsolja be az "Élő Módot" a gyors, 1 perces ellenőrzésekhez.
-   **Manuális Ellenőrzés:** Bármikor indíthat manuális állapot-ellenőrzést.
-   **Következő Ellenőrzés Visszaszámláló:** Egy időzítő mutatja, hogy pontosan mikor következik a következő automatikus ellenőrzés.
-   **YouTube Broadcast Reset:** Automatikusan visszaállítja a YouTube élő adás kapcsolatát, amikor az OBS újraindul, így nincs szükség a stream kulcs manuális újraillesztésére.

### Konfiguráció

#### 1. Lépés: YouTube API Beállítása

1.  **YouTube Data API Kulcs megszerzése:**
    -   Látogass el a [Google Cloud Console](https://console.cloud.google.com/) oldalra
    -   Hozz létre egy új projektet vagy válassz ki egy meglévőt
    -   Engedélyezd a YouTube Data API v3-at
    -   Hozz létre hitelesítő adatokat (API Key) a csak olvasási műveletekhez

2.  **OAuth2 beállítása a Broadcast Menedzsmenthez (Kötelező az auto-újracsatlakozáshoz):**
    -   Ugyanabban a Google Cloud projektben hozz létre OAuth 2.0 Client ID-t
    -   Alkalmazás típusa: "Desktop app" vagy "Web application"
    -   Töltsd le a client secret JSON fájlt
    -   Mentsd el `client_secret.json` néven a projekt gyökérkönyvtárába

#### 2. Lépés: Környezeti Változók Konfigurálása

1.  **Másolja a `.env.example` fájlt `.env` néven:**
    ```bash
    cp .env.example .env
    ```

2.  **Szerkessze a `.env` fájlt** és adja meg a saját hitelesítési adatait.

    ```ini
    # A Google Cloud Console-ból származó YouTube Data API kulcsod
    YOUTUBE_API_KEY="YOUR_YOUTUBE_API_KEY_HERE"

    # A YouTube csatornaazonosítód
    YOUTUBE_CHANNEL_ID="YOUR_YOUTUBE_CHANNEL_ID_HERE"

    # Az OAuth2 client secret fájl elérési útja (broadcast menedzsmenthez)
    YOUTUBE_CLIENT_SECRET_FILE="client_secret.json"

    # --- FONTOS ---
    # Ha Dockerrel futtatod, ezt a speciális hosztnevet használd az OBS-hez való csatlakozáshoz a fő gépeden.
    # Ne használd a 'localhost' vagy '127.0.0.1' címeket.
    OBS_WEBSOCKET_HOST="host.docker.internal"

    # Az OBS WebSocket szerver portja (alapértelmezett: 4455)
    OBS_WEBSOCKET_PORT="4455"

    # A jelszó, amit az OBS WebSocket szerver beállításaiban megadtál
    OBS_WEBSOCKET_PASSWORD="YOUR_OBS_WEBSOCKET_PASSWORD_HERE"
    ```

#### 3. Lépés: Első Futtatás - OAuth2 Hitelesítés

Az első futtatáskor az alkalmazás megnyit egy böngészőablakot az OAuth2 hitelesítéshez:
1. Jelentkezz be a YouTube fiókodba
2. Add meg a kért engedélyeket
3. A hitelesítési adatok mentésre kerülnek a `token.json` fájlba a jövőbeni használathoz

**Megjegyzés:** Ügyelj rá, hogy a `client_secret.json` és `token.json` fájlokat add hozzá a `.gitignore` fájlhoz a biztonság érdekében!

### Futtatás Dockerrel (Ajánlott)

#### Docker Compose Használata (Legegyszerűbb)

1.  **Győződj meg róla, hogy a `docker-compose.yml` fájl a projekt gyökérkönyvtárában van** (része a repository-nak)

2.  **Szerkeszd a `docker-compose.yml` fájlt** és cseréld le a `YOUR_USERNAME` részt a GitHub felhasználónevedre:
    ```yaml
    image: ghcr.io/YOUR_USERNAME/obs-stream-control:latest
    ```

3.  **Indítsd el az alkalmazást:**
    ```bash
    docker-compose up -d
    ```

4.  **Naplók megtekintése:**
    ```bash
    docker-compose logs -f
    ```

5.  **Alkalmazás leállítása:**
    ```bash
    docker-compose down
    ```

#### Előre Elkészített Image Használata a GHCR-ről (Manuális Docker Run)

1.  **A legújabb image letöltése:**
    ```bash
    docker pull ghcr.io/YOUR_USERNAME/obs-stream-control:latest
    ```

2.  **Konténer futtatása:**
    ```bash
    docker run --name obs-stream-control-container \
      -p 8000:8000 \
      --env-file .env \
      -v $(pwd)/client_secret.json:/app/client_secret.json \
      -v $(pwd)/token.json:/app/token.json \
      -d --restart always \
      ghcr.io/YOUR_USERNAME/obs-stream-control:latest
    ```

#### Helyi Build

1.  **Docker Kép Építése:**
    A projekt gyökérkönyvtárából futtassa az építési parancsot:
    ```bash
    docker build -t obs-stream-control .
    ```

2.  **Docker Konténer Futtatása:**
    Ez a parancs elindítja a konténert, továbbítja a webes felülethez szükséges portot, és biztonságosan átadja a hitelesítési adatokat a `.env` fájlból.
    ```bash
    docker run --name obs-stream-control-container \
      -p 8000:8000 \
      --env-file .env \
      -v $(pwd)/client_secret.json:/app/client_secret.json \
      -v $(pwd)/token.json:/app/token.json \
      -d --restart always \
      obs-stream-control
    ```

3.  **Az Irányítópult Elérése:**
    Nyissa meg a webböngészőt és navigáljon a következő címre:
    **http://localhost:8000**

### A Konténer Kezelése

-   **Napló megtekintése:** `docker logs -f obs-stream-control-container`
-   **Konténer leállítása:** `docker stop obs-stream-control-container`
-   **Konténer indítása:** `docker start obs-stream-control-container`
-   **Konténer eltávolítása:** `docker rm obs-stream-control-container`

### Hogyan Működik a Broadcast Reset?

Amikor az OBS újraindul (pl. Windows frissítés után), a YouTube élő adás olyan állapotba kerülhet, hogy nem fogad új kapcsolatokat ugyanazzal a stream kulccsal. Ez az alkalmazás a következőképpen oldja meg ezt:

1. **Észleli**, amikor az OBS-nek újra kell csatlakoznia
2. **Visszaállítja** a YouTube broadcast állapotát a YouTube API-n keresztül
3. **Átviszi** az élő adást különböző állapotokon (live → testing → live) a kapcsolat frissítéséhez
4. **Elindítja** az OBS streamet egy friss kapcsolattal

Ez kiküszöböli annak szükségességét, hogy minden OBS újraindítás után manuálisan újra be kelljen illeszteni a stream kulcsot!