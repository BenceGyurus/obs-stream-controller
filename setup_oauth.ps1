# OBS Stream Control - OAuth Setup Script (PowerShell)
# Ez a script végigvezet az OAuth hitelesítésen és feltölti a token.json-t a NAS-ra

$ErrorActionPreference = "Stop"

Write-Host "========================================================================"
Write-Host "OBS Stream Control - OAuth Setup (PowerShell)"
Write-Host "========================================================================"
Write-Host ""

# Színek
function Write-Success { param($Message) Write-Host $Message -ForegroundColor Green }
function Write-Error { param($Message) Write-Host $Message -ForegroundColor Red }
function Write-Warning { param($Message) Write-Host $Message -ForegroundColor Yellow }

# 1. Ellenőrizd hogy létezik-e a client_secret.json
if (-Not (Test-Path "client_secret.json")) {
    Write-Error "ERROR: client_secret.json nem található!"
    Write-Host ""
    Write-Host "Kérlek töltsd le a Google Cloud Console-ból:"
    Write-Host "1. Menj ide: https://console.cloud.google.com/apis/credentials"
    Write-Host "2. Válaszd ki az OAuth 2.0 Client ID-t"
    Write-Host "3. Töltsd le a JSON fájlt"
    Write-Host "4. Nevezd át 'client_secret.json' névre"
    Write-Host "5. Másold ebbe a mappába: $PWD"
    Write-Host ""
    Read-Host "Nyomj Enter-t a kilépéshez"
    exit 1
}

Write-Success "✓ client_secret.json megtalálva"
Write-Host ""

# 2. Ellenőrizd Python telepítését
try {
    $pythonVersion = python --version 2>&1
    Write-Success "✓ Python telepítve: $pythonVersion"
    Write-Host ""
} catch {
    Write-Error "ERROR: Python nincs telepítve vagy nincs a PATH-ban!"
    Write-Host ""
    Write-Host "Telepítsd Python3-at: https://www.python.org/downloads/"
    Write-Host "FONTOS: A telepítés során pipáld be az 'Add Python to PATH' opciót!"
    Write-Host ""
    Read-Host "Nyomj Enter-t a kilépéshez"
    exit 1
}

# 3. Hozz létre virtual environment
if (-Not (Test-Path "venv")) {
    Write-Host "Python virtual environment létrehozása..."
    try {
        python -m venv venv
        Write-Success "✓ Virtual environment létrehozva"
    } catch {
        Write-Error "ERROR: Nem sikerült virtual environment-et létrehozni!"
        Write-Host ""
        Read-Host "Nyomj Enter-t a kilépéshez"
        exit 1
    }
} else {
    Write-Success "✓ Virtual environment már létezik"
}
Write-Host ""

# 4. Aktiváld a virtual environment-et
Write-Host "Virtual environment aktiválása..."
try {
    & "venv\Scripts\Activate.ps1"
    Write-Success "✓ Virtual environment aktiválva"
} catch {
    Write-Error "ERROR: Nem sikerült aktiválni a virtual environment-et!"
    Write-Host ""
    Write-Warning "Ha 'execution policy' hibát kapsz, futtasd PowerShell-t Administrator módban és add ki:"
    Write-Host "Set-ExecutionPolicy RemoteSigned -Scope CurrentUser"
    Write-Host ""
    Read-Host "Nyomj Enter-t a kilépéshez"
    exit 1
}
Write-Host ""

# 5. Telepítsd a szükséges library-t
Write-Host "Szükséges library telepítése..."
try {
    pip install --quiet google-auth-oauthlib | Out-Null
    Write-Success "✓ google-auth-oauthlib telepítve"
} catch {
    Write-Error "ERROR: Library telepítés sikertelen!"
    Write-Host ""
    deactivate
    Read-Host "Nyomj Enter-t a kilépéshez"
    exit 1
}
Write-Host ""

# 6. Futtasd az authenticate.py scriptet
Write-Host "========================================================================"
Write-Host "OAuth hitelesítés indítása..."
Write-Host "========================================================================"
Write-Host ""
Write-Host "A böngésző automatikusan megnyílik."
Write-Host "Jelentkezz be a YouTube fiókodba és engedd meg az engedélyeket."
Write-Host ""

try {
    python authenticate.py
    if ($LASTEXITCODE -ne 0) { throw "Authentication failed" }
} catch {
    Write-Error "ERROR: Hitelesítés sikertelen!"
    Write-Host ""
    deactivate
    Read-Host "Nyomj Enter-t a kilépéshez"
    exit 1
}

Write-Host ""
Write-Success "✓ Hitelesítés sikeres!"
Write-Host ""

# 7. Ellenőrizd hogy létrejött-e a token.json
if (-Not (Test-Path "token.json")) {
    Write-Error "ERROR: token.json nem jött létre!"
    Write-Host ""
    deactivate
    Read-Host "Nyomj Enter-t a kilépéshez"
    exit 1
}

Write-Success "✓ token.json létrejött"
Write-Host ""

# 8. Kérd be a NAS IP címét
Write-Host "========================================================================"
Write-Host "NAS Konfiguráció"
Write-Host "========================================================================"
Write-Host ""

$NAS_IP = Read-Host "Add meg a Synology NAS IP címét (pl: 10.2.34.15)"
if ([string]::IsNullOrWhiteSpace($NAS_IP)) {
    Write-Error "ERROR: NAS IP cím megadása kötelező!"
    Write-Host ""
    deactivate
    Read-Host "Nyomj Enter-t a kilépéshez"
    exit 1
}

$NAS_USER = Read-Host "Add meg a NAS SSH felhasználónevedet (alapértelmezett: admin)"
if ([string]::IsNullOrWhiteSpace($NAS_USER)) { $NAS_USER = "admin" }

$NAS_PATH = Read-Host "Add meg a NAS-on a docker-compose.yml mappájának elérési útját (alapértelmezett: /volume1/docker/obs-stream-control)"
if ([string]::IsNullOrWhiteSpace($NAS_PATH)) { $NAS_PATH = "/volume1/docker/obs-stream-control" }

Write-Host ""
Write-Host "NAS Beállítások:"
Write-Host "  IP: $NAS_IP"
Write-Host "  Felhasználó: $NAS_USER"
Write-Host "  Mappa: $NAS_PATH"
Write-Host ""

$CONFIRM = Read-Host "Rendben? (y/n)"
if ($CONFIRM -ne "y" -and $CONFIRM -ne "Y") {
    Write-Host "Megszakítva."
    deactivate
    Read-Host "Nyomj Enter-t a kilépéshez"
    exit 0
}

# 9. Másold át a token.json-t a NAS-ra SCP-vel
Write-Host ""
Write-Host "========================================================================"
Write-Host "token.json feltöltése a NAS-ra..."
Write-Host "========================================================================"
Write-Host ""

# Ellenőrizd hogy van-e SCP (Git for Windows része)
try {
    Get-Command scp -ErrorAction Stop | Out-Null
} catch {
    Write-Warning "WARNING: SCP nincs telepítve!"
    Write-Host ""
    Write-Host "Kézzel töltsd fel a token.json-t:"
    Write-Host "1. Nyisd meg a File Station-t a Synology DSM-ben"
    Write-Host "2. Navigálj ide: $NAS_PATH"
    Write-Host "3. Töltsd fel a token.json fájlt innen: $PWD\token.json"
    Write-Host "4. Indítsd újra a Docker containert"
    Write-Host ""
    Write-Host "Vagy telepítsd a Git for Windows-t (tartalmaz SCP-t):"
    Write-Host "https://git-scm.com/download/win"
    Write-Host ""
    deactivate
    Read-Host "Nyomj Enter-t a kilépéshez"
    exit 0
}

Write-Host "Mappa létrehozása a NAS-on (ha nem létezik)..."
try {
    ssh "$NAS_USER@$NAS_IP" "mkdir -p $NAS_PATH"
} catch {
    Write-Error "ERROR: Nem sikerült SSH kapcsolódni a NAS-hoz!"
    Write-Host ""
    Write-Host "Kézzel töltsd fel a token.json-t:"
    Write-Host "1. Nyisd meg a File Station-t a Synology DSM-ben"
    Write-Host "2. Navigálj ide: $NAS_PATH"
    Write-Host "3. Töltsd fel a token.json fájlt innen: $PWD\token.json"
    Write-Host "4. Indítsd újra a Docker containert"
    Write-Host ""
    deactivate
    Read-Host "Nyomj Enter-t a kilépéshez"
    exit 1
}

Write-Host "token.json feltöltése..."
try {
    scp token.json "$NAS_USER@$NAS_IP`:$NAS_PATH/"
    if ($LASTEXITCODE -ne 0) { throw "SCP failed" }
    Write-Success "✓ token.json sikeresen feltöltve!"
} catch {
    Write-Error "ERROR: SCP feltöltés sikertelen!"
    Write-Host ""
    Write-Host "Kézzel töltsd fel a token.json-t:"
    Write-Host "1. Nyisd meg a File Station-t a Synology DSM-ben"
    Write-Host "2. Navigálj ide: $NAS_PATH"
    Write-Host "3. Töltsd fel a token.json fájlt innen: $PWD\token.json"
    Write-Host "4. Indítsd újra a Docker containert"
    Write-Host ""
    deactivate
    Read-Host "Nyomj Enter-t a kilépéshez"
    exit 1
}
Write-Host ""

# 10. Állítsd be a megfelelő jogosultságokat
Write-Host "Fájl jogosultságok beállítása..."
try {
    ssh "$NAS_USER@$NAS_IP" "chmod 666 $NAS_PATH/token.json"
    Write-Success "✓ Jogosultságok beállítva"
} catch {
    Write-Warning "WARNING: Nem sikerült beállítani a jogosultságokat"
}
Write-Host ""

# 11. Kérdezd meg hogy újraindítsa-e a containert
Write-Host "========================================================================"
Write-Host "Docker Container Újraindítása"
Write-Host "========================================================================"
Write-Host ""

$RESTART_CONTAINER = Read-Host "Újraindítsam a Docker containert? (y/n)"
if ($RESTART_CONTAINER -eq "y" -or $RESTART_CONTAINER -eq "Y") {
    Write-Host ""
    Write-Host "Container újraindítása..."
    try {
        ssh "$NAS_USER@$NAS_IP" "cd $NAS_PATH && docker-compose restart"
        if ($LASTEXITCODE -ne 0) { throw "Restart failed" }
        Write-Success "✓ Container újraindítva"
    } catch {
        Write-Warning "WARNING: Nem sikerült újraindítani a containert"
        Write-Host ""
        Write-Host "Kézi újraindítás:"
        Write-Host "1. SSH-zz a NAS-ra: ssh $NAS_USER@$NAS_IP"
        Write-Host "2. cd $NAS_PATH"
        Write-Host "3. docker-compose restart"
    }
}

Write-Host ""
Write-Host "========================================================================"
Write-Success "✓✓✓ SETUP KÉSZ! ✓✓✓"
Write-Host "========================================================================"
Write-Host ""
Write-Host "Következő lépések:"
Write-Host "1. Ellenőrizd a logokat: ssh $NAS_USER@$NAS_IP 'cd $NAS_PATH && docker-compose logs -f'"
Write-Host "2. Nyisd meg a webes felületet: http://$NAS_IP`:8000"
Write-Host "3. Ha minden rendben van, már működnie kell a broadcast reset funkciónak!"
Write-Host ""
Write-Host "Ha problémába ütközöl, nézd meg a SYNOLOGY.md dokumentációt."
Write-Host ""

deactivate
Read-Host "Nyomj Enter-t a kilépéshez"
