@echo off
REM OBS Stream Control - OAuth Setup Script (Windows)
REM Ez a script vegigvezet az OAuth hitelesitesen es feltolti a token.json-t a NAS-ra

setlocal enabledelayedexpansion

echo ========================================================================
echo OBS Stream Control - OAuth Setup (Windows)
echo ========================================================================
echo.

REM 1. Ellenorizd hogy letezik-e a client_secret.json
if not exist "client_secret.json" (
    echo [ERROR] client_secret.json nem talalhato!
    echo.
    echo Kerlek toltsd le a Google Cloud Console-bol:
    echo 1. Menj ide: https://console.cloud.google.com/apis/credentials
    echo 2. Valaszd ki az OAuth 2.0 Client ID-t
    echo 3. Toltsd le a JSON fajlt
    echo 4. Nevezd at 'client_secret.json' nevre
    echo 5. Masold ebbe a mappaba: %cd%
    echo.
    pause
    exit /b 1
)

echo [OK] client_secret.json megtalálva
echo.

REM 2. Ellenorizd Python telepiteset
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python nincs telepitve vagy nincs a PATH-ban!
    echo.
    echo Telepitsd Python3-at: https://www.python.org/downloads/
    echo FONTOS: A telepites soran pipald be az "Add Python to PATH" opciót!
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python telepitve: %PYTHON_VERSION%
echo.

REM 3. Hozz letre virtual environment
if not exist "venv" (
    echo Python virtual environment letrehozasa...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Nem sikerult virtual environment-et letrehozni!
        echo.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment letrehozva
) else (
    echo [OK] Virtual environment mar letezik
)
echo.

REM 4. Aktivald a virtual environment-et
echo Virtual environment aktiválasa...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] Nem sikerult aktivalni a virtual environment-et!
    echo.
    pause
    exit /b 1
)
echo [OK] Virtual environment aktiválva
echo.

REM 5. Telepitsd a szukseges library-t
echo Szukseges library telepitese...
pip install --quiet google-auth-oauthlib
if %errorlevel% neq 0 (
    echo [ERROR] Library telepites sikertelen!
    echo.
    pause
    exit /b 1
)
echo [OK] google-auth-oauthlib telepitve
echo.

REM 6. Futtasd az authenticate.py scriptet
echo ========================================================================
echo OAuth hitelesites inditasa...
echo ========================================================================
echo.
echo A bongeszo automatikusan megnyílik.
echo Jelentkezz be a YouTube fiokodba es engedd meg az engedelyeket.
echo.

python authenticate.py
if %errorlevel% neq 0 (
    echo [ERROR] Hitelesites sikertelen!
    echo.
    call venv\Scripts\deactivate.bat
    pause
    exit /b 1
)

echo.
echo [OK] Hitelesites sikeres!
echo.

REM 7. Ellenorizd hogy letrejott-e a token.json
if not exist "token.json" (
    echo [ERROR] token.json nem jott letre!
    echo.
    call venv\Scripts\deactivate.bat
    pause
    exit /b 1
)

echo [OK] token.json letrejott
echo.

REM 8. Kerd be a NAS IP cimet
echo ========================================================================
echo NAS Konfiguracio
echo ========================================================================
echo.

set /p NAS_IP="Add meg a Synology NAS IP cimet (pl: 10.2.34.15): "
if "%NAS_IP%"=="" (
    echo [ERROR] NAS IP cim megadasa kotelezo!
    echo.
    call venv\Scripts\deactivate.bat
    pause
    exit /b 1
)

set /p NAS_USER="Add meg a NAS SSH felhasznalonevet (alapertelmezett: admin): "
if "%NAS_USER%"=="" set NAS_USER=admin

set /p NAS_PATH="Add meg a NAS-on a docker-compose.yml mappajanak eleresi utjat (alapertelmezett: /volume1/docker/obs-stream-control): "
if "%NAS_PATH%"=="" set NAS_PATH=/volume1/docker/obs-stream-control

echo.
echo NAS Beallitasok:
echo   IP: %NAS_IP%
echo   Felhasznalo: %NAS_USER%
echo   Mappa: %NAS_PATH%
echo.

set /p CONFIRM="Rendben? (y/n): "
if /i not "%CONFIRM%"=="y" (
    echo Megszakitva.
    call venv\Scripts\deactivate.bat
    pause
    exit /b 0
)

REM 9. Masold at a token.json-t a NAS-ra SCP-vel
echo.
echo ========================================================================
echo token.json feltoltese a NAS-ra...
echo ========================================================================
echo.

REM Ellenorizd hogy van-e SCP
where scp >nul 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] SCP nincs telepitve!
    echo.
    echo Kezileg toltsd fel a token.json-t:
    echo 1. Nyisd meg a File Station-t a Synology DSM-ben
    echo 2. Navigalj ide: %NAS_PATH%
    echo 3. Toltsd fel a token.json fajlt innen: %cd%\token.json
    echo 4. Inditsd ujra a Docker containert
    echo.
    echo Vagy telepitsd a Git for Windows-t (tartalmaz SCP-t):
    echo https://git-scm.com/download/win
    echo.
    call venv\Scripts\deactivate.bat
    pause
    exit /b 0
)

echo Mappa letrehozasa a NAS-on (ha nem letezik)...
ssh %NAS_USER%@%NAS_IP% "mkdir -p %NAS_PATH%"
if %errorlevel% neq 0 (
    echo [ERROR] Nem sikerult SSH kapcsolodni a NAS-hoz!
    echo.
    echo Kezileg toltsd fel a token.json-t:
    echo 1. Nyisd meg a File Station-t a Synology DSM-ben
    echo 2. Navigalj ide: %NAS_PATH%
    echo 3. Toltsd fel a token.json fajlt innen: %cd%\token.json
    echo 4. Inditsd ujra a Docker containert
    echo.
    call venv\Scripts\deactivate.bat
    pause
    exit /b 1
)

echo token.json feltoltese...
scp token.json %NAS_USER%@%NAS_IP%:%NAS_PATH%/
if %errorlevel% neq 0 (
    echo [ERROR] SCP feltoltes sikertelen!
    echo.
    echo Kezileg toltsd fel a token.json-t:
    echo 1. Nyisd meg a File Station-t a Synology DSM-ben
    echo 2. Navigalj ide: %NAS_PATH%
    echo 3. Toltsd fel a token.json fajlt innen: %cd%\token.json
    echo 4. Inditsd ujra a Docker containert
    echo.
    call venv\Scripts\deactivate.bat
    pause
    exit /b 1
)

echo [OK] token.json sikeresen feltoltve!
echo.

REM 10. Allitsd be a megfelelo jogosultsagokat
echo Fajl jogosultsagok beallitasa...
ssh %NAS_USER%@%NAS_IP% "chmod 666 %NAS_PATH%/token.json"
echo [OK] Jogosultsagok beallitva
echo.

REM 11. Kerdezd meg hogy ujrainditsa-e a containert
echo ========================================================================
echo Docker Container Ujrainditasa
echo ========================================================================
echo.

set /p RESTART_CONTAINER="Ujrainditjam a Docker containert? (y/n): "
if /i "%RESTART_CONTAINER%"=="y" (
    echo.
    echo Container ujrainditasa...
    ssh %NAS_USER%@%NAS_IP% "cd %NAS_PATH% && docker-compose restart"
    if %errorlevel% neq 0 (
        echo [WARNING] Nem sikerult ujrainditani a containert
        echo.
        echo Kezi ujrainditas:
        echo 1. SSH-zz a NAS-ra: ssh %NAS_USER%@%NAS_IP%
        echo 2. cd %NAS_PATH%
        echo 3. docker-compose restart
    ) else (
        echo [OK] Container ujrainditva
    )
)

echo.
echo ========================================================================
echo [OK] SETUP KESZ!
echo ========================================================================
echo.
echo Kovetkezo lepesek:
echo 1. Ellenorizd a logokat: ssh %NAS_USER%@%NAS_IP% "cd %NAS_PATH% && docker-compose logs -f"
echo 2. Nyisd meg a webes feluletet: http://%NAS_IP%:8000
echo 3. Ha minden rendben van, mar mukodnie kell a broadcast reset funkcionak!
echo.
echo Ha problemaba utkozol, nezd meg a SYNOLOGY.md dokumentaciot.
echo.

call venv\Scripts\deactivate.bat
pause
