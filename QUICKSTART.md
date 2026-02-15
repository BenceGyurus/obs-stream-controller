# 🚀 GYORS SETUP - OBS Stream Control OAuth

## Mi ez?

Ez a script **automatikusan** beállítja az OAuth hitelesítést a Synology NAS-odhoz.

---

## ⚡ GYORS START (3 lépés)

### 1️⃣ Töltsd le a `client_secret.json` fájlt

1. Menj ide: https://console.cloud.google.com/apis/credentials
2. Kattints az OAuth 2.0 Client ID-dra (amit létrehoztál)
3. Kattints a **⬇️ DOWNLOAD JSON** gombra
4. Nevezd át **`client_secret.json`** névre
5. Másold ebbe a mappába

### 2️⃣ Futtasd a setup scriptet

**Mac / Linux:**
```bash
./setup_oauth.sh
```

**Windows (CMD):**
```cmd
setup_oauth.bat
```

**Windows (PowerShell):**
```powershell
.\setup_oauth.ps1
```

> **Megjegyzés Windows-hoz:**  
> Ha PowerShell execution policy hibát kapsz, futtasd PowerShell-t **Administrator** módban:
> ```powershell
> Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

### 3️⃣ Kész! ✅

A script:
- ✅ Telepíti a szükséges library-kat
- ✅ Megnyitja a böngészőt az OAuth hitelesítéshez
- ✅ Létrehozza a `token.json` fájlt
- ✅ Feltölti a NAS-ra SCP-vel
- ✅ Beállítja a jogosultságokat
- ✅ Újraindítja a Docker containert

---

## 📋 Részletes lépések

### Előkészületek

```bash
# 1. Klónozd le a repot (ha még nem tetted)
git clone https://github.com/BenceGyurus/obs-stream-controller.git
cd obs-stream-controller

# 2. Másold ide a client_secret.json-t
# (Google Cloud Console-ból letöltve)

# 3. Futtasd a scriptet
./setup_oauth.sh
```

### Mit kérdez a script?

1. **NAS IP címe**: pl. `10.2.34.15`
2. **SSH felhasználónév**: pl. `admin` (alapértelmezett)
3. **Docker mappa elérési útja**: pl. `/volume1/docker/obs-stream-control` (alapértelmezett)
4. **SSH jelszó**: A NAS SSH jelszavad (amikor SCP-vel feltölti a fájlt)
5. **Újraindítás?**: Újraindítsa-e a Docker containert?

---

## 🛠️ Ha valami nem működik

### Problem 1: `client_secret.json not found`

**Megoldás:**
```bash
# Ellenőrizd hogy a fájl létezik
ls -la client_secret.json

# Ha nincs, töltsd le a Google Cloud Console-ból
```

### Problem 2: SSH kapcsolódási hiba

**Megoldás:**
```bash
# Teszteld az SSH kapcsolatot
ssh admin@10.2.34.15

# Ha nem működik, engedélyezd az SSH-t a Synology DSM-ben:
# Control Panel > Terminal & SNMP > Enable SSH service
```

### Problem 3: Permission denied (Mac/Linux)

**Megoldás:**
```bash
# Add meg a futtatási jogot
chmod +x setup_oauth.sh
```

### Problem 4: PowerShell execution policy (Windows)

**Megoldás:**
```powershell
# Futtasd PowerShell-t Administrator módban:
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Problem 5: SCP nincs telepítve (Windows)

**Megoldás:**
```
Telepítsd a Git for Windows-t (tartalmaz SCP-t):
https://git-scm.com/download/win

Vagy használd WinSCP-t a token.json feltöltéséhez.
```

---

## 🔐 Biztonság

- ✅ A `token.json` automatikusan `.gitignore`-ban van (nem kerül git-be)
- ✅ A script csak helyben fut (nem küldi el sehova)
- ✅ SSH kapcsolat titkosított

---

## 📖 További információ

- **Teljes dokumentáció**: [SETUP.md](SETUP.md)
- **Synology specifikus**: [SYNOLOGY.md](SYNOLOGY.md)
- **Problémák**: Nyiss issue-t GitHub-on

---

## ❓ Gyakori kérdések

**Q: Kell-e újra futtatnom ezt minden alkalommal?**  
A: **NEM!** Csak egyszer kell. A `token.json` automatikusan újratermelődik amikor lejár.

**Q: Mi van ha újratelepítem a containert?**  
A: A `token.json` a host gépen marad, nem vész el.

**Q: Működik Mac-en / Linux-on / Windows-on?**  
A: **Mac ✅ | Linux ✅ | Windows ✅**
- Mac/Linux: `./setup_oauth.sh`
- Windows: `setup_oauth.bat` vagy `setup_oauth.ps1`

**Q: Kell hozzá Python?**  
A: **Igen**, Python 3.6+ kell. Ellenőrizd: `python3 --version`

---

## 🎉 Kész!

Ha sikerült, láthatod a logokban:
```
✓ YouTube OAuth2 service initialized
✓ Found active broadcast: Your Stream Title
```

Élvezd! 🚀
