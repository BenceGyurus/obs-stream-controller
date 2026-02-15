#!/bin/bash

# OBS Stream Control - OAuth Setup Script
# Ez a script végigvezet az OAuth hitelesítésen és feltölti a token.json-t a NAS-ra

set -e  # Kilép hiba esetén

echo "========================================================================"
echo "OBS Stream Control - OAuth Setup"
echo "========================================================================"
echo ""

# Színek
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Ellenőrizd hogy létezik-e a client_secret.json
if [ ! -f "client_secret.json" ]; then
    echo -e "${RED}ERROR: client_secret.json nem található!${NC}"
    echo ""
    echo "Kérlek töltsd le a Google Cloud Console-ból:"
    echo "1. Menj ide: https://console.cloud.google.com/apis/credentials"
    echo "2. Válaszd ki az OAuth 2.0 Client ID-t"
    echo "3. Töltsd le a JSON fájlt"
    echo "4. Nevezd át 'client_secret.json' névre"
    echo "5. Másold ebbe a mappába: $(pwd)"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ client_secret.json megtalálva${NC}"
echo ""

# 2. Ellenőrizd Python telepítést
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}ERROR: Python3 nincs telepítve!${NC}"
    echo "Telepítsd Python3-at: https://www.python.org/downloads/"
    exit 1
fi

echo -e "${GREEN}✓ Python3 telepítve: $(python3 --version)${NC}"
echo ""

# 3. Hozz létre virtual environment
if [ ! -d "venv" ]; then
    echo "Python virtual environment létrehozása..."
    python3 -m venv venv || {
        echo -e "${RED}ERROR: Nem sikerült virtual environment-et létrehozni!${NC}"
        echo "Próbáld: python3 -m pip install virtualenv"
        exit 1
    }
    echo -e "${GREEN}✓ Virtual environment létrehozva${NC}"
else
    echo -e "${GREEN}✓ Virtual environment már létezik${NC}"
fi
echo ""

# 4. Aktiváld a virtual environment-et
echo "Virtual environment aktiválása..."
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment aktiválva${NC}"
echo ""

# 5. Telepítsd a szükséges library-t
echo "Szükséges library telepítése..."
pip install --quiet google-auth-oauthlib 2>&1 | grep -v "already satisfied" || true
echo -e "${GREEN}✓ google-auth-oauthlib telepítve${NC}"
echo ""

# 6. Futtasd az authenticate.py scriptet
echo "========================================================================"
echo "OAuth hitelesítés indítása..."
echo "========================================================================"
echo ""
echo "A böngésző automatikusan megnyílik."
echo "Jelentkezz be a YouTube fiókodba és engedd meg az engedélyeket."
echo ""

if ! python authenticate.py; then
    echo -e "${RED}ERROR: Hitelesítés sikertelen!${NC}"
    deactivate
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Hitelesítés sikeres!${NC}"
echo ""

# 6. Ellenőrizd hogy létrejött-e a token.json
if [ ! -f "token.json" ]; then
    echo -e "${RED}ERROR: token.json nem jött létre!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ token.json létrejött${NC}"
echo ""

# 7. Kérd be a NAS IP címét
echo "========================================================================"
echo "NAS Konfiguráció"
echo "========================================================================"
echo ""
read -p "Add meg a Synology NAS IP címét (pl: 10.2.34.15): " NAS_IP

if [ -z "$NAS_IP" ]; then
    echo -e "${RED}ERROR: NAS IP cím megadása kötelező!${NC}"
    exit 1
fi

read -p "Add meg a NAS SSH felhasználónevedet (alapértelmezett: admin): " NAS_USER
NAS_USER=${NAS_USER:-admin}

read -p "Add meg a NAS-on a docker-compose.yml mappájának elérési útját (alapértelmezett: /volume1/docker/obs-stream-control): " NAS_PATH
NAS_PATH=${NAS_PATH:-/volume1/docker/obs-stream-control}

echo ""
echo "NAS Beállítások:"
echo "  IP: $NAS_IP"
echo "  Felhasználó: $NAS_USER"
echo "  Mappa: $NAS_PATH"
echo ""
read -p "Rendben? (y/n): " CONFIRM

if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "Megszakítva."
    exit 0
fi

# 8. Másold át a token.json-t a NAS-ra
echo ""
echo "========================================================================"
echo "token.json feltöltése a NAS-ra..."
echo "========================================================================"
echo ""

# Létrehozza a mappát ha nem létezik
echo "Mappa létrehozása a NAS-on (ha nem létezik)..."
ssh ${NAS_USER}@${NAS_IP} "mkdir -p ${NAS_PATH}" || {
    echo -e "${RED}ERROR: Nem sikerült SSH kapcsolódni a NAS-hoz!${NC}"
    echo ""
    echo "Kézi feltöltési instrukciók:"
    echo "1. Nyisd meg a File Station-t a Synology DSM-ben"
    echo "2. Navigálj ide: ${NAS_PATH}"
    echo "3. Töltsd fel a token.json fájlt innen: $(pwd)/token.json"
    echo "4. Indítsd újra a Docker containert"
    exit 1
}

# Másold át a token.json-t
echo "token.json feltöltése..."
scp token.json ${NAS_USER}@${NAS_IP}:${NAS_PATH}/ || {
    echo -e "${RED}ERROR: SCP feltöltés sikertelen!${NC}"
    echo ""
    echo "Kézi feltöltési instrukciók:"
    echo "1. Nyisd meg a File Station-t a Synology DSM-ben"
    echo "2. Navigálj ide: ${NAS_PATH}"
    echo "3. Töltsd fel a token.json fájlt innen: $(pwd)/token.json"
    echo "4. Indítsd újra a Docker containert"
    exit 1
}

echo -e "${GREEN}✓ token.json sikeresen feltöltve!${NC}"
echo ""

# 9. Állítsd be a megfelelő jogosultságokat
echo "Fájl jogosultságok beállítása..."
ssh ${NAS_USER}@${NAS_IP} "chmod 666 ${NAS_PATH}/token.json"
echo -e "${GREEN}✓ Jogosultságok beállítva${NC}"
echo ""

# 10. Kérdezd meg hogy újraindítsa-e a containert
echo "========================================================================"
echo "Docker Container Újraindítása"
echo "========================================================================"
echo ""
read -p "Újraindítsam a Docker containert? (y/n): " RESTART_CONTAINER

if [ "$RESTART_CONTAINER" = "y" ] || [ "$RESTART_CONTAINER" = "Y" ]; then
    echo ""
    echo "Container újraindítása..."
    ssh ${NAS_USER}@${NAS_IP} "cd ${NAS_PATH} && docker-compose restart" || {
        echo -e "${YELLOW}WARNING: Nem sikerült újraindítani a containert${NC}"
        echo ""
        echo "Kézi újraindítás:"
        echo "1. SSH-zz a NAS-ra: ssh ${NAS_USER}@${NAS_IP}"
        echo "2. cd ${NAS_PATH}"
        echo "3. docker-compose restart"
    }
    echo -e "${GREEN}✓ Container újraindítva${NC}"
fi

echo ""
echo "========================================================================"
echo -e "${GREEN}✓✓✓ SETUP KÉSZ! ✓✓✓${NC}"
echo "========================================================================"
echo ""
echo "Következő lépések:"
echo "1. Ellenőrizd a logokat: ssh ${NAS_USER}@${NAS_IP} 'cd ${NAS_PATH} && docker-compose logs -f'"
echo "2. Nyisd meg a webes felületet: http://${NAS_IP}:8000"
echo "3. Ha minden rendben van, már működnie kell a broadcast reset funkciónak!"
echo ""
echo "Ha problémába ütközöl, nézd meg a SYNOLOGY.md dokumentációt."
echo ""
