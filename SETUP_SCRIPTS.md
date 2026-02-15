# OAuth Setup Scripts

Ezek a scriptek **automatikusan** beállítják az OAuth hitelesítést az OBS Stream Control alkalmazáshoz.

## 🚀 Melyiket használd?

### Mac / Linux
```bash
./setup_oauth.sh
```

### Windows (Command Prompt)
```cmd
setup_oauth.bat
```

### Windows (PowerShell) - **Ajánlott**
```powershell
.\setup_oauth.ps1
```

## 📋 Mit csinálnak?

Mind a három script ugyanazt csinálja:

1. ✅ Ellenőrzi hogy `client_secret.json` létezik
2. ✅ Python virtual environment-et hoz létre
3. ✅ Telepíti a `google-auth-oauthlib` library-t
4. ✅ Megnyitja a böngészőt az OAuth bejelentkezéshez
5. ✅ Létrehozza a `token.json` fájlt
6. ✅ SCP-vel feltölti a NAS-ra
7. ✅ Beállítja a fájl jogosultságokat
8. ✅ Újraindítja a Docker containert

## ⚙️ Előfeltételek

### Mindegyikhez:
- ✅ Python 3.6+ telepítve
- ✅ `client_secret.json` a projekt mappában
- ✅ SSH hozzáférés a NAS-hoz

### Windows-hoz extra:
- ✅ Git for Windows (tartalmaz SCP-t): https://git-scm.com/download/win
- ✅ PowerShell esetén: Execution policy engedélyezve

## 🛠️ Troubleshooting

### PowerShell: "Execution policy" hiba

Futtasd PowerShell-t **Administrator** módban:
```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Windows: SCP nincs telepítve

Telepítsd a Git for Windows-t:
```
https://git-scm.com/download/win
```

Vagy használd WinSCP-t a `token.json` kézi feltöltéséhez.

### Mac/Linux: Permission denied

```bash
chmod +x setup_oauth.sh
```

## 📖 További információ

Részletes útmutató: [QUICKSTART.md](QUICKSTART.md)
