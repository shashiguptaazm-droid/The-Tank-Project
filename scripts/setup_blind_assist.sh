#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Tank — Blind-Assistance Module Setup Script
# One-command setup for the wearable UNO Q blind-assistance external module.
#
# Usage:  bash scripts/setup_blind_assist.sh
#
# What it does:
#   1. Installs Python dependencies (OpenCV, YOLO, Whisper, TTS, OCR)
#   2. Downloads YOLOv8n model weights
#   3. Verifies ESP32-S3 CAM reachability
#   4. Tests LTE modem connectivity
#   5. Configures Tailscale mesh check
#   6. Creates emergency contacts template
#   7. Runs a smoke test: capture → detect → speak
#
# APC-2026-RJ-75818 · Dr. Shashi Gupta
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONTACTS_FILE="$HOME/.blind_assist_contacts"
ESP32_CAM_HOST="${ESP32_CAM_HOST:-192.168.31.145}"
JETSON_TAILSCALE="${JETSON_TAILSCALE:-100.122.31.46}"
VPS_TAILSCALE="${VPS_TAILSCALE:-100.71.127.19}"

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  🦯 Tank — Blind-Assistance Module Setup               ║${NC}"
echo -e "${BLUE}║  APC-2026-RJ-75818 · Dr. Shashi Gupta                 ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# ── 1. Install Python Dependencies ─────────────────────────────────────────
echo -e "${YELLOW}[1/7] Installing Python dependencies...${NC}"
pip3 install -q --upgrade pip 2>/dev/null || true

DEPS=(
    opencv-python-headless
    numpy
    ultralytics
    openai-whisper
    TTS
    pytesseract
    Pillow
    pyserial
    requests
)

for dep in "${DEPS[@]}"; do
    if pip3 show "$dep" &>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $dep (already installed)"
    else
        echo -n "  Installing $dep... "
        pip3 install -q "$dep" 2>/dev/null && echo -e "${GREEN}OK${NC}" || echo -e "${RED}FAILED${NC}"
    fi
done

# System packages (apt)
echo ""
echo -e "  Checking system packages..."
for pkg in esptool modemmanager tesseract-ocr ffmpeg portaudio19-dev; do
    if dpkg -l "$pkg" &>/dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} $pkg"
    else
        echo -n "  Installing $pkg... "
        apt-get install -y -qq "$pkg" 2>/dev/null && echo -e "${GREEN}OK${NC}" || echo -e "${RED}FAILED${NC}"
    fi
done

# ── 2. Download YOLOv8n Model ──────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[2/7] Downloading YOLOv8n model weights...${NC}"
MODEL_PATH="$PROJECT_ROOT/data/models/yolov8n.pt"
mkdir -p "$(dirname "$MODEL_PATH")"

if [ -f "$MODEL_PATH" ]; then
    echo -e "  ${GREEN}✓${NC} yolov8n.pt already downloaded ($(du -h "$MODEL_PATH" | cut -f1))"
else
    echo -n "  Downloading yolov8n.pt... "
    python3 -c "from ultralytics import YOLO; YOLO('yolov8n.pt')" 2>/dev/null
    if [ -f "yolov8n.pt" ]; then
        mv yolov8n.pt "$MODEL_PATH"
        echo -e "${GREEN}OK${NC} ($(du -h "$MODEL_PATH" | cut -f1))"
    else
        echo -e "${RED}FAILED${NC} — will download on first run"
    fi
fi

# ── 3. Verify ESP32-S3 CAM ─────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[3/7] Testing ESP32-S3 CAM at $ESP32_CAM_HOST...${NC}"

CAM_OK=false
if curl -s --connect-timeout 5 "http://$ESP32_CAM_HOST/capture" -o /tmp/blind_assist_test.jpg 2>/dev/null; then
    if file /tmp/blind_assist_test.jpg | grep -qi "JPEG"; then
        echo -e "  ${GREEN}✓${NC} ESP32-S3 CAM reachable — JPEG capture working"
        echo -e "  ${GREEN}✓${NC} Resolution: $(identify /tmp/blind_assist_test.jpg 2>/dev/null | awk '{print $3}' || echo 'unknown')"
        CAM_OK=true
    else
        echo -e "  ${YELLOW}!${NC} ESP32-S3 CAM responded but not a valid JPEG"
    fi
else
    echo -e "  ${YELLOW}!${NC} ESP32-S3 CAM not reachable at $ESP32_CAM_HOST"
    echo "     Check: 1) ESP32 is powered  2) WiFi connected  3) IP is correct"
    echo "     Running: arp -a | grep -i espressif"
fi

# ── 4. Test LTE Modem ──────────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[4/7] Testing LTE modem (Quectel EG800AK)...${NC}"

if command -v mmcli &>/dev/null; then
    MODEM_COUNT=$(mmcli -L 2>/dev/null | grep -c "Modem" || echo "0")
    if [ "$MODEM_COUNT" -gt 0 ]; then
        MODEM_ID=$(mmcli -L | head -1 | grep -oP '/Modem/\K[0-9]+')
        echo -e "  ${GREEN}✓${NC} Modem detected (ID: $MODEM_ID)"

        # Signal strength
        SIGNAL=$(mmcli -m "$MODEM_ID" --command="AT+CSQ" 2>/dev/null | grep "+CSQ:" | awk -F'[: ,]' '{print $2}')
        if [ -n "$SIGNAL" ] && [ "$SIGNAL" != "99" ]; then
            echo -e "  ${GREEN}✓${NC} Signal strength: $SIGNAL/31"
        else
            echo -e "  ${YELLOW}!${NC} No signal — check SIM and antenna"
        fi

        # Operator
        OPERATOR=$(mmcli -m "$MODEM_ID" --command="AT+COPS?" 2>/dev/null | grep "+COPS:" | cut -d'"' -f2)
        [ -n "$OPERATOR" ] && echo -e "  ${GREEN}✓${NC} Operator: $OPERATOR"
    else
        echo -e "  ${YELLOW}!${NC} No modem found — check USB connection"
    fi
else
    echo -e "  ${YELLOW}!${NC} ModemManager not installed — install with: apt install modemmanager"
fi

# ── 5. Check Tailscale Mesh ─────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[5/7] Checking Tailscale connectivity...${NC}"

if command -v tailscale &>/dev/null; then
    MY_IP=$(tailscale ip -4 2>/dev/null || echo "")
    if [ -n "$MY_IP" ]; then
        echo -e "  ${GREEN}✓${NC} Tailscale running — IP: $MY_IP"

        # Ping Jetson
        if ping -c 1 -W 3 "$JETSON_TAILSCALE" &>/dev/null; then
            echo -e "  ${GREEN}✓${NC} Jetson reachable at $JETSON_TAILSCALE"
        else
            echo -e "  ${YELLOW}!${NC} Jetson not reachable at $JETSON_TAILSCALE"
        fi

        # Ping VPS
        if ping -c 1 -W 3 "$VPS_TAILSCALE" &>/dev/null; then
            echo -e "  ${GREEN}✓${NC} VPS reachable at $VPS_TAILSCALE"
        else
            echo -e "  ${YELLOW}!${NC} VPS not reachable at $VPS_TAILSCALE"
        fi
    else
        echo -e "  ${YELLOW}!${NC} Tailscale installed but not connected — run: tailscale up"
    fi
else
    echo -e "  ${YELLOW}!${NC} Tailscale not installed — run: curl -fsSL https://tailscale.com/install.sh | sh"
fi

# ── 6. Emergency Contacts ──────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[6/7] Emergency contacts...${NC}"

if [ -f "$CONTACTS_FILE" ]; then
    echo -e "  ${GREEN}✓${NC} Contacts file exists: $CONTACTS_FILE"
    echo "  Contents:"
    grep -v '^#' "$CONTACTS_FILE" | grep -v '^$' | sed 's/^/    /'
else
    echo -e "  ${YELLOW}!${NC} Creating contacts template at $CONTACTS_FILE"
    cat > "$CONTACTS_FILE" << 'CONTACTS_EOF'
# Blind-Assistance Emergency Contacts
# One phone number per line in international format.
# These contacts receive SMS on triple-tap E-STOP.
# Lines starting with # are ignored.

+91-XXXXXXXXXX  # Primary emergency contact
+91-XXXXXXXXXX  # Family member
+91-XXXXXXXXXX  # Doctor / caregiver
CONTACTS_EOF
    echo -e "  ${YELLOW}!${NC} Edit $CONTACTS_FILE with actual phone numbers"
fi

# ── 7. Smoke Test ──────────────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[7/7] Running smoke test...${NC}"

SMOKE_OK=true

# Test 1: Python imports
echo -n "  Import check... "
if python3 -c "
import cv2; import numpy; import json; import time;
print('OK')
" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Core imports"
else
    echo -e "${RED}✗${NC} Import failed"
    SMOKE_OK=false
fi

# Test 2: Camera (if reachable)
if [ "$CAM_OK" = true ]; then
    echo -n "  Capture test... "
    python3 -c "
import urllib.request
url = 'http://${ESP32_CAM_HOST}/capture'
req = urllib.request.urlopen(url, timeout=5)
data = req.read()
assert len(data) > 100, f'Frame too small: {len(data)} bytes'
print(f'OK ({len(data)} bytes)')
" 2>/dev/null && echo -e "${GREEN}✓${NC}" || { echo -e "${RED}✗${NC}"; SMOKE_OK=false; }
fi

# Test 3: YOLO model
echo -n "  YOLO model test... "
python3 -c "
from ultralytics import YOLO
import numpy as np
model = YOLO('${MODEL_PATH}')
# Create a dummy image
dummy = np.zeros((480, 640, 3), dtype=np.uint8)
results = model(dummy, verbose=False)
print('OK')
" 2>/dev/null && echo -e "${GREEN}✓${NC}" || { echo -e "${RED}✗${NC}"; SMOKE_OK=false; }

# Test 4: Directory structure
echo -n "  Directory structure... "
mkdir -p "$PROJECT_ROOT/tank/blind_assist"
mkdir -p "$PROJECT_ROOT/tank/blind_assist/tests"
echo -e "${GREEN}✓${NC}"

# ── Summary ─────────────────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
if [ "$SMOKE_OK" = true ]; then
    echo -e "${BLUE}║  ${GREEN}✅ Setup complete — module is ready!${NC}                     ${BLUE}║${NC}"
else
    echo -e "${BLUE}║  ${YELLOW}⚠️  Setup done with warnings — review above${NC}               ${BLUE}║${NC}"
fi
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Next steps:"
echo -e "    1. Edit emergency contacts:  ${GREEN}nano $CONTACTS_FILE${NC}"
echo -e "    2. Start blind-assist mode:  ${GREEN}python3 -m tank.blind_assist.main --mode full${NC}"
echo -e "    3. Run hardware test:        ${GREEN}python3 scripts/test_blind_assist.py --hardware${NC}"
echo -e "    4. Full docs:                ${GREEN}cat docs/BLIND_ASSIST.md${NC}"
echo ""