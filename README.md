# OBS Stream Control

A Python application that monitors the status of a YouTube stream and automatically starts the stream in OBS Studio if it goes offline. This version features a modern, real-time, bilingual web dashboard for advanced control and monitoring.

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

### Configuration

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

    # --- IMPORTANT ---
    # If running with Docker, use this special hostname to connect to OBS on your main machine.
    # Do not use 'localhost' or '127.0.0.1'.
    OBS_WEBSOCKET_HOST="host.docker.internal"

    # The port for the OBS WebSocket Server (default is 4455)
    OBS_WEBSOCKET_PORT="4455"

    # The password you set in the OBS WebSocket Server settings
    OBS_WEBSOCKET_PASSWORD="YOUR_OBS_WEBSOCKET_PASSWORD_HERE"
    ```

### Running with Docker (Recommended)

1.  **Build the Docker Image:**
    From the project's root directory, run the build command:
    ```bash
    docker build -t obs-stream-control .
    ```

2.  **Run the Docker Container:**
    This command will start your container, forward the necessary port for the web interface, and securely pass your credentials from the `.env` file.
    ```bash
    docker run --name obs-stream-control-container -p 8000:8000 --env-file .env -d --restart always obs-stream-control
    ```

3.  **Access the Dashboard:**
    Open your web browser and navigate to:
    **http://localhost:8000**

### Managing the Container

-   **View logs:** `docker logs -f obs-stream-control-container`
-   **Stop the container:** `docker stop obs-stream-control-container`
-   **Start the container:** `docker start obs-stream-control-container`
-   **Remove the container:** `docker rm obs-stream-control-container`

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

### Konfiguráció

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

    # --- FONTOS ---
    # Ha Dockerrel futtatod, ezt a speciális hosztnevet használd az OBS-hez való csatlakozáshoz a fő gépeden.
    # Ne használd a 'localhost' vagy '127.0.0.1' címeket.
    OBS_WEBSOCKET_HOST="host.docker.internal"

    # Az OBS WebSocket szerver portja (alapértelmezett: 4455)
    OBS_WEBSOCKET_PORT="4455"

    # A jelszó, amit az OBS WebSocket szerver beállításaiban megadtál
    OBS_WEBSOCKET_PASSWORD="YOUR_OBS_WEBSOCKET_PASSWORD_HERE"
    ```

### Futtatás Dockerrel (Ajánlott)

1.  **Docker Kép Építése:**
    A projekt gyökérkönyvtárából futtassa az építési parancsot:
    ```bash
    docker build -t obs-stream-control .
    ```

2.  **Docker Konténer Futtatása:**
    Ez a parancs elindítja a konténert, továbbítja a webes felülethez szükséges portot, és biztonságosan átadja a hitelesítési adatokat a `.env` fájlból.
    ```bash
    docker run --name obs-stream-control-container -p 8000:8000 --env-file .env -d --restart always obs-stream-control
    ```

3.  **Az Irányítópult Elérése:**
    Nyissa meg a webböngészőt és navigáljon a következő címre:
    **http://localhost:8000**

### A Konténer Kezelése

-   **Napló megtekintése:** `docker logs -f obs-stream-control-container`
-   **Konténer leállítása:** `docker stop obs-stream-control-container`
-   **Konténer indítása:** `docker start obs-stream-control-container`
-   **Konténer eltávolítása:** `docker rm obs-stream-control-container`