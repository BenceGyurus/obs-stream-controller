# Synology NAS Telepítési Útmutató

Ez az útmutató végigvezet az OBS Stream Control telepítésén Synology NAS-on.

---

## Előfeltételek

1. **Synology NAS** Docker támogatással (DSM 7.0+)
2. **Container Manager** csomag telepítve a Package Center-ből
3. **SSH hozzáférés** a NAS-hoz (opcionális, de ajánlott)
4. **OBS Studio** egy másik gépen a hálózaton
5. **Google Cloud OAuth2 credentials** (`client_secret.json`)

---

## 1. NAS Előkészítése

### SSH-n keresztül (Ajánlott)

1. SSH bejelentkezés a NAS-ra:
   ```bash
   ssh admin@YOUR_NAS_IP
   ```

2. Könyvtár létrehozása:
   ```bash
   sudo mkdir -p /volume1/docker/obs-stream-control
   cd /volume1/docker/obs-stream-control
   ```

### File Station-ön keresztül

1. Nyisd meg a **File Station**-t
2. Navigálj a **docker** mappába (ha nincs, hozd létre)
3. Hozz létre egy új mappát: **obs-stream-control**

---

## 2. Fájlok Feltöltése

Töltsd fel a következő fájlokat a `/volume1/docker/obs-stream-control/` mappába:

### 2.1. docker-compose.yml

```yaml
version: '3.8'

services:
  obs-stream-control:
    image: ghcr.io/YOUR_GITHUB_USERNAME/obs-stream-control:latest
    container_name: obs-stream-control
    restart: always
    ports:
      - "8000:8000"
    environment:
      - YOUTUBE_API_KEY=YOUR_API_KEY
      - YOUTUBE_CHANNEL_ID=YOUR_CHANNEL_ID
      - YOUTUBE_CLIENT_SECRET_FILE=/app/client_secret.json
      - OBS_WEBSOCKET_HOST=192.168.1.XXX  # Az OBS gép IP címe
      - OBS_WEBSOCKET_PORT=4455
      - OBS_WEBSOCKET_PASSWORD=YOUR_OBS_PASSWORD
    
    volumes:
      - /volume1/docker/obs-stream-control/client_secret.json:/app/client_secret.json:ro
      - /volume1/docker/obs-stream-control/token.json:/app/token.json
    
    mem_limit: 512m
    
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

**FONTOS:** Cseréld le a következőket:
- `YOUR_GITHUB_USERNAME` → GitHub felhasználóneved
- `YOUR_API_KEY` → YouTube Data API kulcsod
- `YOUR_CHANNEL_ID` → YouTube csatorna ID-d
- `192.168.1.XXX` → Az OBS-t futtató gép IP címe
- `YOUR_OBS_PASSWORD` → OBS WebSocket jelszó

### 2.2. client_secret.json

- Google Cloud Console-ból letöltött OAuth2 credentials fájl
- Töltsd fel változtatás nélkül

### 2.3. token.json (első futtatás után)

- Ez automatikusan létrejön az OAuth hitelesítés után
- Üresen hagyhatod vagy hozz létre egy üres fájlt:
  ```bash
  touch /volume1/docker/obs-stream-control/token.json
  chmod 666 /volume1/docker/obs-stream-control/token.json
  ```

---

## 3. OAuth2 Hitelesítés - Headless Mód (EGYSZERŰ!)

**ÚJ FUNKCIÓ:** Most már nem kell SSH böngésző trükk! A headless mód lehetővé teszi, hogy **bármilyen eszközről** (telefon, laptop, tablet) bejelentkezz, még akkor is, ha a NAS-on fut az alkalmazás.

### 3.1. Első Indítás Docker Compose-zal

```bash
cd /volume1/docker/obs-stream-control
docker-compose up
```

**FONTOS:** Ne használd a `-d` flaget az első alkalommal, mert látni akarod a hitelesítési utasításokat!

### 3.2. Headless OAuth Flow (Böngésző Nélkül a NAS-on)

1. Az alkalmazás elindul és a logokban megjelenik:
   ```
   ======================================================================
   HEADLESS AUTHENTICATION MODE
   ======================================================================
   
   Please complete the following steps on ANY device with a browser:
   
   1. Visit this URL: https://accounts.google.com/o/oauth2/auth?...
   
   2. Log in to your Google account
   
   3. Grant the requested permissions
   
   4. Copy the authorization code
   
   5. Enter the code below:
   
   Enter the authorization code: _
   ```

2. **BÁRMILYEN ESZKÖZRŐL** (telefon, laptop, tablet):
   - Másold ki a megjelenő URL-t
   - Nyisd meg egy böngészőben
   - Jelentkezz be a YouTube fiókodba
   - Engedd meg az engedélyeket

3. A Google megjelenít egy **kódot** (pl. `4/0AY0e-g7...`)

4. **Másold ki ezt a kódot**

5. **Illeszd be** a NAS SSH konzoljába (ahol fut a docker-compose up)

6. Az alkalmazás folytatja:
   ```
   Authentication successful!
   ======================================================================
   Credentials saved to token.json
   ```

7. Állítsd le az alkalmazást (`Ctrl+C`)

8. Most már indíthatod háttérben:
   ```bash
   docker-compose up -d
   ```

### 3.3. Alternatív: SSH-n keresztül (ha nincs docker-compose)

```bash
cd /volume1/docker/obs-stream-control

docker run -it --rm \
  -v /volume1/docker/obs-stream-control/client_secret.json:/app/client_secret.json \
  -v /volume1/docker/obs-stream-control/token.json:/app/token.json \
  -e YOUTUBE_API_KEY=YOUR_API_KEY \
  -e YOUTUBE_CHANNEL_ID=YOUR_CHANNEL_ID \
  -e YOUTUBE_CLIENT_SECRET_FILE=/app/client_secret.json \
  -e OAUTH_HEADLESS=true \
  -e OBS_WEBSOCKET_HOST=192.168.1.XXX \
  -e OBS_WEBSOCKET_PORT=4455 \
  -e OBS_WEBSOCKET_PASSWORD=YOUR_OBS_PASSWORD \
  ghcr.io/YOUR_USERNAME/obs-stream-control:latest
```

Kövesd ugyanazokat a lépéseket mint fent.

---

## 4. Éles Indítás

### Container Manager UI-ból (Egyszerű)

1. Nyisd meg a **Container Manager** alkalmazást
2. Menj a **Project** fülre
3. Kattints a **Create** gombra
4. Projekt név: `obs-stream-control`
5. Útvonal: `/volume1/docker/obs-stream-control`
6. Állítsd be a **docker-compose.yml** fájlt
7. Kattints a **Create** gombra

### SSH-ból (Haladó)

```bash
cd /volume1/docker/obs-stream-control
docker-compose up -d
```

---

## 5. Ellenőrzés

### Logok Megtekintése

**Container Manager UI:**
- Menj a **Container** fülre
- Válaszd ki az `obs-stream-control` konténert
- Kattints a **Details** → **Log** fülre

**SSH:**
```bash
docker logs -f obs-stream-control
```

### Dashboard Elérése

Böngészőben nyisd meg:
```
http://YOUR_NAS_IP:8000
```

---

## 6. Gyakori Problémák és Megoldások

### "NanoCPUs can not be set" hiba

**Megoldás:** A `docker-compose.yml`-ben ne használj `deploy` szekciót CPU limitekkel. Használd helyette:
```yaml
mem_limit: 512m
```

### "host.docker.internal" nem működik

**Megoldás:** Synology-n ez nem támogatott. Használj valódi IP címet:
```yaml
- OBS_WEBSOCKET_HOST=192.168.1.100
```

### OBS nem csatlakozik

**Ellenőrzési lista:**
1. Az OBS WebSocket szerver engedélyezve van?
2. A port nyitva van a tűzfalon? (4455)
3. Az IP cím helyes?
4. A jelszó helyes?

**Teszt:**
```bash
# Synology-ról próbálj kapcsolódni az OBS-hez
telnet 192.168.1.100 4455
```

### OAuth token lejárt

**Megoldás:** Töröld a `token.json` fájlt és futtasd újra az OAuth flow-t:
```bash
rm /volume1/docker/obs-stream-control/token.json
# Futtasd újra a 3. lépést
```

### Konténer nem indul

**Logok ellenőrzése:**
```bash
docker logs obs-stream-control
```

**Jogosultságok ellenőrzése:**
```bash
ls -la /volume1/docker/obs-stream-control/
# A fájloknak olvashatónak kell lenniük
```

---

## 7. Karbantartás

### Frissítés Új Verzióra

```bash
cd /volume1/docker/obs-stream-control
docker-compose pull
docker-compose up -d
```

### Újraindítás

```bash
docker-compose restart
```

### Leállítás

```bash
docker-compose down
```

### Teljes Törlés

```bash
docker-compose down
docker rmi ghcr.io/YOUR_USERNAME/obs-stream-control:latest
rm -rf /volume1/docker/obs-stream-control
```

---

## 8. Teljesítmény Optimalizálás

### Memória Limit Beállítása

A `docker-compose.yml`-ben:
```yaml
mem_limit: 512m  # Növeld ha szükséges
```

### Automatikus Újraindítás

```yaml
restart: always  # Már be van állítva
```

---

## 9. Biztonsági Megjegyzések

1. **HTTPS használata:** Fontos adatoknál használj reverse proxy-t (pl. Synology Application Portal)
2. **Tűzfal:** Csak a szükséges portokat nyisd meg (8000, 4455)
3. **Credentials:** A `client_secret.json` és `token.json` fájlok érzékeny adatok - ne oszd meg!

---

## 10. Támogatás

- Részletes dokumentáció: [README.md](README.md)
- Setup útmutató: [SETUP.md](SETUP.md)
- GitHub Issues: Nyiss issue-t a repository-ban

---

**Jó streamelést! 🎥**
