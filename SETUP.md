# OBS Stream Control - Részletes Beállítási Útmutató

Ez az útmutató lépésről lépésre végigvezet az OBS Stream Control beállításán, különös tekintettel az új YouTube Broadcast Reset funkcióra.

---

## 1. Előfeltételek

### Szükséges Szoftverek
- **OBS Studio** (v28.0 vagy újabb) - [Letöltés](https://obsproject.com/)
- **OBS WebSocket Plugin** (általában beépített a modern OBS verziókban)
- **Docker** (ha Docker környezetben futtatod) - [Letöltés](https://www.docker.com/)
- **Python 3.9+** (ha helyi környezetben futtatod)

### YouTube Követelmények
- Aktív YouTube csatorna streaming jogosultsággal
- Google Cloud Console hozzáférés

---

## 2. Google Cloud Console Beállítása

### 2.1. Projekt Létrehozása

1. Látogass el a [Google Cloud Console](https://console.cloud.google.com/) oldalra
2. Jelentkezz be a Google fiókodba
3. Kattints a projekt választóra (felső menüsor)
4. Kattints az **"Új projekt"** gombra
5. Add meg a projekt nevét (pl. "OBS Stream Control")
6. Kattints a **"Létrehozás"** gombra

### 2.2. YouTube Data API v3 Engedélyezése

1. A projekt kiválasztása után menj a **"API-k és szolgáltatások" > "Könyvtár"** menüpontra
2. Keresd meg a **"YouTube Data API v3"** API-t
3. Kattints rá, majd kattints az **"Engedélyezés"** gombra

### 2.3. API Kulcs Létrehozása (Olvasási műveletekhez)

1. Menj az **"API-k és szolgáltatások" > "Hitelesítő adatok"** menüpontra
2. Kattints a **"+ HITELESÍTŐ ADATOK LÉTREHOZÁSA"** gombra
3. Válaszd az **"API-kulcs"** opciót
4. Másold ki és mentsd el az API kulcsot (később szükség lesz rá)
5. *(Opcionális)* Korlátozd az API kulcsot:
   - Kattints a kulcs neve melletti ceruzára
   - "Alkalmazás-korlátozások": válaszd az "IP-címek" opciót és add hozzá a szervered IP címét
   - "API-korlátozások": válaszd a "Kulcs korlátozása kiválasztott API-kra" opciót
   - Válaszd ki a "YouTube Data API v3"-at
   - Mentsd el a változtatásokat

### 2.4. OAuth 2.0 Kliens Létrehozása (Broadcast Menedzsmenthez)

1. Ugyanabban a **"Hitelesítő adatok"** oldalon kattints a **"+ HITELESÍTŐ ADATOK LÉTREHOZÁSA"** gombra
2. Válaszd az **"OAuth kliens-azonosító"** opciót
3. Ha még nem konfiguráltad az OAuth-hozzájárulási képernyőt:
   - Kattints a **"HOZZÁJÁRULÁSI KÉPERNYŐ KONFIGURÁLÁSA"** gombra
   - Válaszd a **"Külső"** felhasználó típust (vagy "Belső" ha G Suite fiókod van)
   - Add meg az alkalmazás nevét (pl. "OBS Stream Control")
   - Add meg a támogatási e-mail címet (a saját e-mail címed)
   - Töltsd ki a többi kötelező mezőt
   - Mentsd el
4. Térj vissza a **"Hitelesítő adatok létrehozása" > "OAuth kliens-azonosító"** menüpontra
5. Alkalmazás típusa: válaszd a **"Asztali alkalmazás"** opciót
6. Név: add meg a kliens nevét (pl. "OBS Stream Control Desktop")
7. **Fontos:** Az "Engedélyezett átirányítási URI-k" részhez add hozzá:
   - `http://0.0.0.0:8080/` (hálózati hozzáféréshez)
   - `http://localhost:8080/` (helyi hozzáféréshez)
8. Kattints a **"Létrehozás"** gombra
9. **Fontos:** Töltsd le a JSON fájlt a megjelenő ablakból
10. Nevezd át a letöltött fájlt **`client_secret.json`** névre
11. Helyezd a `client_secret.json` fájlt a projekt gyökérkönyvtárába

### 2.5. OAuth Scopes Hozzáadása

1. Menj vissza az **"OAuth-hozzájárulási képernyő"** beállításokhoz
2. Kattints a **"HATÓKÖRÖK HOZZÁADÁSA VAGY ELTÁVOLÍTÁSA"** gombra
3. Add hozzá a következő scope-ot:
   - `https://www.googleapis.com/auth/youtube.force-ssl`
4. Mentsd el a változtatásokat

---

## 3. OBS Studio Beállítása

### 3.1. OBS WebSocket Szerver Engedélyezése

1. Nyisd meg az OBS Studio-t
2. Menj a **Eszközök > WebSocket szerver beállításai** menüpontra
3. Jelöld be a **"WebSocket szerver engedélyezése"** opciót
4. Állíts be egy **szerver portot** (alapértelmezett: 4455)
5. Állíts be egy erős **jelszót**
6. Kattints az **"OK"** gombra
7. **Jegyezd fel a portot és jelszót** - később szükség lesz rájuk!

### 3.2. YouTube Stream Beállítások

1. Menj a **Beállítások > Stream** menüpontra
2. Szolgáltatás: válaszd a **"YouTube - RTMPS"** opciót
3. Szerver: `rtmps://a.rtmp.youtube.com:443/live2`
4. Stream kulcs: illeszd be a YouTube-ról kapott **állandó stream kulcsot**
   - A YouTube stream kulcsot a YouTube Studio > Élő adás > Stream beállításai menüpontban találod
5. Kattints az **"Alkalmaz"** majd **"OK"** gombra

---

## 4. Projekt Beállítása

### 4.1. Fájlok Letöltése/Klónozása

```bash
git clone https://github.com/YOUR_USERNAME/obs-stream-control.git
cd obs-stream-control
```

### 4.2. Környezeti Változók Konfigurálása

1. Másold le a `.env.example` fájlt `.env` néven:
   ```bash
   cp .env.example .env
   ```

2. Szerkeszd a `.env` fájlt egy szövegszerkesztővel:
   ```ini
   # YouTube Data API Key (a 2.3. lépésben létrehozott kulcs)
   YOUTUBE_API_KEY="AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

   # YouTube Channel ID (a csatornád ID-ja)
   # Megtalálható: YouTube Studio > Beállítások > Csatorna > Speciális beállítások
   YOUTUBE_CHANNEL_ID="UCxxxxxxxxxxxxxxxxxx"

   # OAuth2 client secret fájl neve/útvonala
   YOUTUBE_CLIENT_SECRET_FILE="client_secret.json"

   # OBS WebSocket beállítások (a 3.1. lépésben beállított értékek)
   OBS_WEBSOCKET_HOST="host.docker.internal"  # Docker esetén
   # vagy
   # OBS_WEBSOCKET_HOST="localhost"  # Helyi futtatás esetén
   
   OBS_WEBSOCKET_PORT="4455"
   OBS_WEBSOCKET_PASSWORD="a_te_obs_jelszavad"
   ```

3. Ellenőrizd, hogy a `client_secret.json` fájl a projekt gyökérkönyvtárában van

---

## 5. Első Futtatás és OAuth Hitelesítés

### Docker Compose Módszer (Ajánlott - Legegyszerűbb)

1. Szerkeszd a `docker-compose.yml` fájlt és cseréld le a `YOUR_USERNAME` részt:
   ```yaml
   image: ghcr.io/YOUR_GITHUB_USERNAME/obs-stream-control:latest
   ```
   Vagy használd a helyi build-et:
   ```yaml
   # Kommenteld ki az image sort és használd a build-et:
   build: .
   # image: ghcr.io/YOUR_USERNAME/obs-stream-control:latest
   ```

2. Első indítás (OAuth hitelesítéshez interaktív módban):
   ```bash
   docker-compose run --rm obs-stream-control
   ```

3. Az alkalmazás megnyit egy böngészőablakot vagy kiír egy URL-t a konzolra
4. Látogass el az URL-re és jelentkezz be a YouTube fiókodba
5. Engedd meg az alkalmazásnak a kért jogosultságokat
6. A hitelesítés sikeres lesz, és létrejön a `token.json` fájl
7. Állítsd le a konténert (Ctrl+C)

8. Éles indítás (háttérben):
   ```bash
   docker-compose up -d
   ```

9. Logok megtekintése:
   ```bash
   docker-compose logs -f
   ```

10. Leállítás:
    ```bash
    docker-compose down
    ```

### Docker Manuális Módszer

#### Ha helyben build-eled:

1. Build-eld a Docker image-et:
   ```bash
   docker build -t obs-stream-control .
   ```

2. Első indítás (OAuth hitelesítéshez):
   ```bash
   docker run -it --rm \
     -p 8000:8000 \
     --env-file .env \
     -v $(pwd)/client_secret.json:/app/client_secret.json \
     -v $(pwd)/token.json:/app/token.json \
     obs-stream-control
   ```

3. Az alkalmazás megnyit egy böngészőablakot vagy kiír egy URL-t a konzolra
4. Látogass el az URL-re és jelentkezz be a YouTube fiókodba
5. Engedd meg az alkalmazásnak a kért jogosultságokat
6. A hitelesítés sikeres lesz, és létrejön a `token.json` fájl
7. Állítsd le a konténert (Ctrl+C)

8. Éles indítás (háttérben):
   ```bash
   docker run --name obs-stream-control-container \
     -p 8000:8000 \
     --env-file .env \
     -v $(pwd)/client_secret.json:/app/client_secret.json \
     -v $(pwd)/token.json:/app/token.json \
     -d --restart always \
     obs-stream-control
   ```

#### Ha GHCR image-et használsz:

1. Húzd le az image-et:
   ```bash
   docker pull ghcr.io/YOUR_USERNAME/obs-stream-control:latest
   ```

2. Kövesd ugyanazokat a lépéseket mint fent, de használd a teljes image nevet:
   ```bash
   docker run -it --rm \
     -p 8000:8000 \
     --env-file .env \
     -v $(pwd)/client_secret.json:/app/client_secret.json \
     -v $(pwd)/token.json:/app/token.json \
     ghcr.io/YOUR_USERNAME/obs-stream-control:latest
   ```

### Helyi Python Környezetben

1. Telepítsd a függőségeket:
   ```bash
   pip install -r requirements.txt
   ```

2. Futtasd az alkalmazást:
   ```bash
   cd web/backend
   python -m uvicorn main:app --host 0.0.0.0 --port 8000
   ```

3. Kövesd az OAuth hitelesítési lépéseket (mint Docker esetén)

---

## 6. Használat és Tesztelés

### 6.1. Dashboard Elérése

1. Nyisd meg a böngészőt és menj a `http://localhost:8000` címre
2. Látni fogod a modern dashboard-ot a stream állapotokkal

### 6.2. OBS Újraindítás Teszt

**A broadcast reset funkció teszteléséhez:**

1. Győződj meg róla, hogy van egy aktív YouTube élő adásod (lehet "ready" vagy "live" állapotban)
2. Indítsd el az OBS streamet normál módon
3. Ellenőrizd, hogy a YouTube-on megjelenik az élő kép
4. **Állítsd le az OBS-t teljesen** (ne csak a streamet, hanem az egész alkalmazást)
5. **Indítsd újra az OBS-t**
6. A dashboard automatikusan észleli, hogy az OBS nem streamel
7. Az alkalmazás:
   - Reset-eli a YouTube broadcast állapotát (live → testing → live)
   - Elindítja az OBS streamet
8. Néhány másodperc múlva az OBS automatikusan újracsatlakozik és a stream folytatódik

### 6.3. Logok Megtekintése

Docker esetén:
```bash
docker logs -f obs-stream-control-container
```

A logokban látnod kell a következő üzeneteket amikor működik:
```
INFO - Attempting to reset YouTube broadcast connection...
INFO - Found active broadcast: [Broadcast neve] (Status: live)
INFO - Current broadcast status: live
INFO - Transitioning broadcast from 'live' to 'testing'...
INFO - Broadcast transitioned to 'testing'. Waiting for connection reset...
INFO - Transitioning broadcast back to 'live'...
INFO - Broadcast transitioned back to 'live'.
INFO - YouTube broadcast connection reset successfully.
INFO - OBS stream is not active. Sending start command...
INFO - StartStream command sent to OBS.
```

---

## 7. Hibaelhárítás

### "Client secret file not found"
- Ellenőrizd, hogy a `client_secret.json` fájl a megfelelő helyen van
- Docker esetén ellenőrizd a volume mount-ot a `docker run` parancsban

### "Failed to refresh credentials"
- Töröld a `token.json` fájlt
- Futtasd újra az alkalmazást az OAuth flow újraindításához

### "No active broadcast found"
- Győződj meg róla, hogy van egy "ready" vagy "live" állapotú YouTube élő adásod
- Ellenőrizd a YouTube Studio-ban az élő adás állapotát

### OBS nem csatlakozik automatikusan
- Ellenőrizd az OBS WebSocket beállításokat (port, jelszó)
- Docker esetén használd a `host.docker.internal` host nevet
- Ellenőrizd a tűzfal beállításokat

### YouTube API hibák
- Ellenőrizd, hogy az API kulcs és OAuth scope-ok helyesek-e
- Nézd meg a Google Cloud Console quota használatát

---

## 8. CI/CD és GHCR Használat

A repository automatikusan build-eli és publikálja a Docker image-et a GitHub Container Registry-be minden push után a main/master branch-re.

### Image Használata GHCR-ről:

```bash
docker pull ghcr.io/YOUR_USERNAME/obs-stream-control:latest

docker run --name obs-stream-control-container \
  -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/client_secret.json:/app/client_secret.json \
  -v $(pwd)/token.json:/app/token.json \
  -d --restart always \
  ghcr.io/YOUR_USERNAME/obs-stream-control:latest
```

**Megjegyzés:** A `YOUR_USERNAME` helyére a GitHub felhasználóneved kerül.

---

## 9. Biztonság

### Fontos Biztonsági Megjegyzések:

1. **SOHA ne commit-eld a következő fájlokat:**
   - `.env`
   - `client_secret.json`
   - `token.json`
   - Ezek a `.gitignore` fájlban vannak, de extra figyelj rájuk!

2. **API kulcs korlátozások:**
   - Korlátozd az API kulcsot csak a szükséges API-kra
   - Használj IP korlátozásokat ahol lehetséges

3. **OBS WebSocket jelszó:**
   - Használj erős jelszót
   - Ne oszd meg senkivel

4. **Docker secrets:**
   - Production környezetben használj Docker secrets-et vagy titkosított environment változókat

---

## 10. További Támogatás

Ha problémád van:
1. Nézd meg a logokat részletes hibaüzenetekért
2. Ellenőrizd ezt az útmutatót újra
3. Nyiss egy issue-t a GitHub repository-ban
4. Csatold a releváns log részleteket (érzékeny adatok eltávolítása után!)

Boldog streamelést! 🎥✨
