#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
# TankOS — Unified Master Installer
# ═══════════════════════════════════════════════════════════════════════════
# SINGLE COMMAND for Jetson Orin Nano + Arduino setup:
#
#     bash tank_os/install.sh --apply
#
# This replaces setup_pi5.sh + provision_pi5.sh + old install.sh
# Detects hardware, installs everything, downloads AI models, enables service.
#
# Dry-run:   bash tank_os/install.sh             (shows what would run)
# Full:      bash tank_os/install.sh --apply      (does everything)
# Headless:  bash tank_os/install.sh --apply --noninteractive
# No models: bash tank_os/install.sh --apply --skip-models
#
# Safe to re-run — fully idempotent. Pass --apply again to repair any gaps.

set -euo pipefail

# ── Options ─────────────────────────────────────────────────────────────
APPLY=0
NONINTERACTIVE=0
SKIP_MODELS=0
for arg in "$@"; do
  case "$arg" in
    --apply)                APPLY=1 ;;
    --noninteractive|-y|-f) NONINTERACTIVE=1 ;;
    --skip-models)          SKIP_MODELS=1 ;;
    --help|-h)
      sed -n '3,14p' "$0"
      exit 0
      ;;
  esac
done

# ── Paths ───────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="/var/log/tankos-install.log"

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()  { echo -e "${GREEN}[✓]${NC} $*" | tee -a "$LOG_FILE"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*" | tee -a "$LOG_FILE"; }
err()   { echo -e "${RED}[✗]${NC} $*" | tee -a "$LOG_FILE" >&2; }
step()  { echo -e "\n${CYAN}══════ ${BOLD}$*${NC}${CYAN} ══════${NC}" | tee -a "$LOG_FILE"; }
header(){ echo -e "${CYAN}━━━ $* ━━━${NC}" | tee -a "$LOG_FILE"; }
dry()   { echo -e "  ${YELLOW}DRY:${NC} $*"; }

run() {
    echo "  $ $*" | tee -a "$LOG_FILE"
    if [[ $APPLY -eq 1 ]]; then
        "$@" 2>&1 | tee -a "$LOG_FILE" || warn "Command returned non-zero: $*"
    fi
}

# ── Banner ──────────────────────────────────────────────────────────────
clear 2>/dev/null || true
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  ${BOLD}TankOS — Unified Master Installer v2.0${NC}${CYAN}                ║${NC}"
echo -e "${CYAN}║  ${BOLD}Single command. Everything included.${NC}${CYAN}                ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

if [[ $APPLY -eq 0 ]]; then
    echo -e "${YELLOW}⚠  DRY RUN — pass --apply to actually install${NC}"
    echo -e "${YELLOW}   Full command: bash $(basename "$0") --apply${NC}\n"
fi

if [[ $(id -u) -ne 0 ]]; then
    err "Must run as root!"
    echo "  sudo bash tank_os/install.sh --apply"
    exit 1
fi

mkdir -p "$(dirname "$LOG_FILE")"
echo "=== TankOS Installer Log $(date -u) ===" > "$LOG_FILE"

# ═══════════════════════════════════════════════════════════════════════════
# STEP 1: Platform detection
# ═══════════════════════════════════════════════════════════════════════════
step "1/12 — Platform & System Detection"

IS_PI=false
PI_MODEL="unknown"
if [[ -f /proc/device-tree/model ]] && grep -qi "NVIDIA Jetson" /proc/device-tree/model 2>/dev/null; then
    IS_PI=true
    PI_MODEL=$(cat /proc/device-tree/model 2>/dev/null || echo "Unknown board")
    info "Platform: $PI_MODEL"
else
    info "Platform: $(uname -m) Linux (not Pi — some hardware features unavailable)"
fi

PYTHON=$(command -v python3 || echo "")
if [[ -z "$PYTHON" ]]; then
    err "Python 3 not found!"
    exit 1
fi
info "Python: $($PYTHON --version 2>&1)"

ARCH=$(uname -m)
info "Architecture: $ARCH"

TOTAL_RAM=$(awk '/MemTotal/ {printf "%.0f", $2/1024}' /proc/meminfo 2>/dev/null || echo "?")
DISK_FREE=$(df -h / | awk 'NR==2 {print $4}')
info "RAM: ${TOTAL_RAM}MB  |  Free disk: ${DISK_FREE}"

# Warn if low disk space (< 20 GB should raise concern)
if [[ $APPLY -eq 1 ]]; then
    DISK_KB=$(df / | awk 'NR==2 {print $4}')
    if [[ $DISK_KB -lt 20000000 ]]; then
        warn "Low disk space (${DISK_FREE}) — AI models need 10+ GB"
    fi
fi

# ═══════════════════════════════════════════════════════════════════════════
# STEP 2: Configure hardware (I2C, SPI, UART)
# ═══════════════════════════════════════════════════════════════════════════
step "2/12 — Hardware Configuration (I2C / SPI / UART)"

CONFIG=""
if [[ -f /boot/firmware/config.txt ]]; then
    CONFIG="/boot/firmware/config.txt"
elif [[ -f /boot/config.txt ]]; then
    CONFIG="/boot/config.txt"
fi

if [[ -n "$CONFIG" ]] && $IS_PI; then
    info "Config file: $CONFIG"

    # Ensure dtparams exist (check + add if missing)
    for param in "dtparam=i2c_arm=on" "dtparam=spi=on" "dtoverlay=disable-bt"; do
        if grep -q "$param" "$CONFIG" 2>/dev/null; then
            info "  Already set: $param"
        else
            if [[ $APPLY -eq 1 ]]; then
                echo "$param" >> "$CONFIG"
                info "  Added: $param"
            else
                dry "Append '$param' to $CONFIG"
            fi
        fi
    done

    # I2C baud rate
    if ! grep -q "i2c_arm_baudrate" "$CONFIG" 2>/dev/null; then
        if [[ $APPLY -eq 1 ]]; then
            echo "dtparam=i2c_arm_baudrate=400000" >> "$CONFIG"
            info "  Added: i2c baud rate 400kHz"
        else
            dry "Set I2C baud rate to 400kHz"
        fi
    fi

    # Disable BT HCI
    if [[ $APPLY -eq 1 ]]; then
        systemctl disable hciuart 2>/dev/null || true
    fi
else
    warn "No Pi config.txt found — skipping hardware config"
fi

# I2C combined-transactions modprobe
if [[ ! -f /etc/modprobe.d/tank_i2c.conf ]]; then
    if [[ $APPLY -eq 1 ]]; then
        echo "options i2c-bcm2708 combined=1" > /etc/modprobe.d/tank_i2c.conf
        info "I2C combined-transactions enabled"
    else
        dry "Create /etc/modprobe.d/tank_i2c.conf"
    fi
fi

# RPLidar udev rule
if [[ ! -f /etc/udev/rules.d/99-tank-rplidar.rules ]]; then
    if [[ $APPLY -eq 1 ]]; then
        cat > /etc/udev/rules.d/99-tank-rplidar.rules <<'UDEV'
# Slamtec RPLidar (CP210x USB-UART)
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", SYMLINK+="rplidar"
UDEV
        udevadm control --reload-rules 2>/dev/null || true
        udevadm trigger 2>/dev/null || true
        info "RPLidar udev rule created"
    else
        dry "Create udev rule for RPLidar"
    fi
fi

# ═══════════════════════════════════════════════════════════════════════════
# STEP 3: System packages (apt)
# ═══════════════════════════════════════════════════════════════════════════
step "3/12 — System Packages (apt)"

APT_PKGS=(
    # Core tools
    build-essential git curl wget tmux vim htop
    # Python
    python3-pip python3-venv python3-dev python3-full
    # Qt6 / GUI
    python3-pyqt6 python3-pyqt6.qtopengl python3-pyqt6.qtquick
    libqt6opengl6-dev qt6-base-dev qt6-wayland
    libgl1-mesa-dev libgles2-mesa-dev libxcb-cursor0
    xvfb
    # Multimedia
    ffmpeg gstreamer1.0-tools gstreamer1.0-plugins-good vlc-bin
    # Database
    sqlite3
    # Networking
    openssh-server wireguard wireguard-tools
    # I2C / hardware
    i2c-tools
    # Docker
    docker.io docker-compose-v2
    # Web
    nginx
    # Monitoring
    prometheus-node-exporter
)

# Only install if --apply
if [[ $APPLY -eq 1 ]]; then
    header "Updating apt cache..."
    apt-get update -qq
    header "Installing ${#APT_PKGS[@]} system packages..."
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${APT_PKGS[@]}" && \
        info "${#APT_PKGS[@]} system packages installed" || \
        warn "Some apt packages failed (check output above)"
else
    dry "apt-get install ${APT_PKGS[*]}"
fi

# ═══════════════════════════════════════════════════════════════════════════
# STEP 4: ROS2 Humble
# ═══════════════════════════════════════════════════════════════════════════
step "4/12 — ROS2 Humble Middleware"

if command -v ros2 >/dev/null 2>&1; then
    info "ROS2 already installed: $(ros2 --version 2>&1 || true)"
else
    if [[ $APPLY -eq 1 ]]; then
        header "Installing ROS2 Humble..."
        # Add ROS2 key
        curl -fsSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key 2>/dev/null | \
            gpg --dearmor -o /usr/share/keyrings/ros-archive-keyring.gpg 2>/dev/null || true
        # Add apt source
        UBUNTU_CODENAME=$(. /etc/os-release && echo "$UBUNTU_CODENAME")
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
http://packages.ros.org/ros2/ubuntu $UBUNTU_CODENAME main" > /etc/apt/sources.list.d/ros2.list
        apt-get update -qq
        DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
            ros-humble-ros-base \
            ros-humble-robot-state-publisher \
            ros-humble-slam-toolbox \
            python3-colcon-common-extensions \
            python3-rosdep && \
            info "ROS2 Humble installed" || \
            warn "ROS2 install had issues (check output above)"
    else
        dry "Install ROS2 Humble (ros-base + slam-toolbox + colcon)"
    fi
fi

# ═══════════════════════════════════════════════════════════════════════════
# STEP 5: Python packages (pip)
# ═══════════════════════════════════════════════════════════════════════════
step "5/12 — Python Packages (pip)"

# Helper: pip install with --break-system-packages fallback
pip_install() {
    local pkg="$1"
    if pip3 install --break-system-packages "$pkg" 2>/dev/null; then
        return 0
    fi
    pip3 install "$pkg" 2>/dev/null
}

PIP_PKGS=(
    # GUI
    "PySide6>=6.6"
    # Core
    "Pillow>=10.0"
    psutil
    numpy
    # Robotics hardware
    gpiozero
    lgpio
    adafruit-blinka
    pyserial
    adafruit-circuitpython-pca9685
    adafruit-circuitpython-motor
    adafruit-circuitpython-ssd1306
    # Vision
    opencv-python-headless
    ultralytics
    apriltag
    # Speech
    sounddevice
    noisereduce
    # AI / LLM
    sentence-transformers
    # Web / API
    fastapi
    uvicorn
    pydantic
    python-multipart
)

if [[ $APPLY -eq 1 ]]; then
    header "Installing ${#PIP_PKGS[@]} pip packages..."
    SUCCESS=0
    FAILED=0
    for pkg in "${PIP_PKGS[@]}"; do
        if pip_install "$pkg" >/dev/null 2>&1; then
            SUCCESS=$((SUCCESS + 1))
        else
            warn "  Failed: $pkg"
            FAILED=$((FAILED + 1))
        fi
    done
    info "Pip packages: $SUCCESS installed, $FAILED failed"

    # Optional heavier packages (don't fail if unavailable)
    for pkg in openai-whisper piper-tts openwakeword; do
        if pip_install "$pkg" >/dev/null 2>&1; then
            info "  Optional: $pkg installed"
        else
            warn "  Optional skipped: $pkg (install manually if needed)"
        fi
    done
else
    dry "pip3 install ${PIP_PKGS[*]} openai-whisper piper-tts openwakeword"
fi

# ═══════════════════════════════════════════════════════════════════════════
# STEP 6: Python environment (PYTHONPATH)
# ═══════════════════════════════════════════════════════════════════════════
step "6/12 — Python Environment Configuration"

if [[ $APPLY -eq 1 ]]; then
    # PYTHONPATH in /etc/environment
    PYTHON_PATH_ENTRY="/usr/local/lib/python3.12/dist-packages:$PROJECT_DIR"
    if ! grep -q "$PROJECT_DIR" /etc/environment 2>/dev/null; then
        echo "PYTHONPATH=$PYTHON_PATH_ENTRY" >> /etc/environment
        info "PYTHONPATH set in /etc/environment"
    else
        info "PYTHONPATH already configured"
    fi

    # Profile script for SSH users
    cat > /etc/profile.d/tankos.sh <<'PROFILE'
export PYTHONPATH="/usr/local/lib/python3.12/dist-packages:/root/the tank project:$PYTHONPATH"
export TANKOS_QT=1
PROFILE
    chmod +x /etc/profile.d/tankos.sh
    info "Shell profile /etc/profile.d/tankos.sh created"
else
    dry "Set PYTHONPATH in /etc/environment + create /etc/profile.d/tankos.sh"
fi

# ═══════════════════════════════════════════════════════════════════════════
# STEP 7: Data directories
# ═══════════════════════════════════════════════════════════════════════════
step "7/12 — Preload Manager Data Directories"

if [[ $APPLY -eq 1 ]]; then
    mkdir -p /var/lib/tank_os/models/{speech,vision,llm,navigation}
    mkdir -p /var/lib/tank_os/assets
    mkdir -p /var/lib/tank_os/cache
    mkdir -p /var/lib/tank_os/wheels
    mkdir -p /var/lib/tank_os/logs
    mkdir -p /var/lib/tank_os/firmware
    mkdir -p /var/cache/tank_os/preload
    info "Data directories created"
else
    dry "mkdir -p /var/lib/tank_os/models/{speech,vision,llm,navigation} ..."
fi

# ═══════════════════════════════════════════════════════════════════════════
# STEP 8: TankOS configuration
# ═══════════════════════════════════════════════════════════════════════════
step "8/12 — TankOS Configuration"

if [[ $APPLY -eq 1 ]]; then
    mkdir -p /root/.config/tank_os
    mkdir -p /root/.config/tank_os/backups

    if [[ ! -f /root/.config/tank_os/settings.json ]]; then
        cat > /root/.config/tank_os/settings.json <<'SETTINGS'
{
  "display": { "brightness": 80, "theme": "dark", "fullscreen": true },
  "power": { "performance_mode": "balanced", "low_battery_threshold": 20 },
  "charging": { "auto_enabled": true, "target_pct": 95 },
  "audio": { "volume": 80, "tts_enabled": true },
  "developer": { "simulation_mode": false }
}
SETTINGS
        info "Default settings created"
    else
        info "Settings file already exists"
    fi
else
    dry "mkdir -p /root/.config/tank_os + create default settings.json"
fi

# ═══════════════════════════════════════════════════════════════════════════
# STEP 9: Optional services (Tailscale, Samba, MQTT)
# ═══════════════════════════════════════════════════════════════════════════
step "9/12 — Optional Network Services"

# Tailscale
if ! command -v tailscale >/dev/null 2>&1; then
    if [[ $APPLY -eq 1 ]]; then
        header "Installing Tailscale..."
        curl -fsSL https://tailscale.com/install.sh 2>/dev/null | sh 2>/dev/null || \
            warn "Tailscale install failed (network?)"
    else
        dry "Install Tailscale VPN"
    fi
fi

# Mosquitto MQTT
if [[ $APPLY -eq 1 ]]; then
    if ! systemctl is-enabled mosquitto >/dev/null 2>&1; then
        DEBIAN_FRONTEND=noninteractive apt-get install -y -qq mosquitto mosquitto-clients 2>/dev/null && \
            systemctl enable mosquitto 2>/dev/null || true
        info "MQTT broker (Mosquitto) enabled"
    else
        info "MQTT broker already running"
    fi
fi

# Samba media share
if [[ $APPLY -eq 1 ]]; then
    mkdir -p /var/tank/media
    if command -v smbd >/dev/null 2>&1; then
        info "Samba available — share at /var/tank/media"
    fi
fi

# ═══════════════════════════════════════════════════════════════════════════
# STEP 10: AI Model Downloads (via PreloadManager)
# ═══════════════════════════════════════════════════════════════════════════
step "10/12 — AI Model Downloads (PreloadManager)"

if [[ $SKIP_MODELS -eq 1 ]]; then
    info "Model download SKIPPED (--skip-models)"
elif [[ $APPLY -eq 1 ]]; then
    header "Running PreloadManager to download missing AI models..."
    header "This downloads ~8 GB of models (first time). Resume supported."

    # Run PreloadManager download in background with progress tracking
    cd "$PROJECT_DIR"

    # Run PreloadManager download
    export PYTHONPATH="/usr/local/lib/python3.12/dist-packages:$PROJECT_DIR:$PYTHONPATH"
    export TANKOS_QT=0
    export PROJECT_DIR

    # Quick network check before starting model download
    if python3 -c "import urllib.request; urllib.request.urlopen('https://huggingface.co', timeout=5)" 2>/dev/null; then
        header "Network OK — starting model downloads"
    else
        warn "No network connectivity — model downloads skipped. Run with internet later."
        header "Skipping model downloads (offline mode)"
        SKIP_MODELS=1
    fi

    # Download all downloadable items
    if [[ $SKIP_MODELS -eq 0 ]]; then
python3 << 'PYEOF' 2>&1 | tee -a /var/log/tankos-install.log
import sys, os, logging, time
sys.path.insert(0, os.environ.get('PROJECT_DIR', '/root/the tank project'))
os.environ['TANKOS_QT'] = '0'
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

from tank_os.core.preload_manager import PreloadManager
from tank_os.preload.manifest import downloadable_items

pm = PreloadManager()
pm.initialize()
r = pm.report()

print(f'\n  PreloadManager initialized.')
print(f'  Installed: {r.downloaded}/{r.total_items}')
print(f'  Downloaded: {r.downloaded_mb:.1f} MB')    print(f'  Total needed: {r.total_size_mb:.1f} MB')

# Get all items that need downloading (filter using report status)
installed_ids = {iid for iid, status in r.items.items() if status == 'installed'}
items = [i for i in downloadable_items() if i.url and i.id not in installed_ids]
if not items:
    print('\n  ✅ All models already downloaded!')
else:
    print(f'\n  Need to download {len(items)} items ({sum(i.size_mb for i in items):.0f} MB):')
    for i in items:
        print(f'    • {i.name} ({i.size_mb:.0f} MB)')

    print('\n  Starting download (this may take 10-30 minutes)...')
    print('  Downloads resume automatically if interrupted.\n')
    sys.stdout.flush()

    start = time.time()
    pr = pm.download_all()
    elapsed = time.time() - start

    print(f'\n  Download completed in {elapsed/60:.1f} minutes')
    print(f'  Result: {pr.downloaded} OK, {pr.failed} failed, {pr.skipped} skipped')
    pm.print_report()
PYEOF
        info "AI model download complete"
    fi
else
    dry "PreloadManager: download all AI models (8+ GB)"
fi

# ═══════════════════════════════════════════════════════════════════════════
# STEP 11: Systemd service
# ═══════════════════════════════════════════════════════════════════════════
step "11/12 — Systemd Autostart Service"

SERVICE_SRC="$SCRIPT_DIR/startup/tank-init.service"
SERVICE_DST="/etc/systemd/system/tank-init.service"

if [[ -f "$SERVICE_SRC" ]]; then
    if [[ $APPLY -eq 1 ]]; then
        cp "$SERVICE_SRC" "$SERVICE_DST"
        # Update WorkingDirectory in service to match actual project path
        sed -i "s|WorkingDirectory=.*|WorkingDirectory=$PROJECT_DIR|" "$SERVICE_DST"
        sed -i "s|PYTHONPATH=.*|PYTHONPATH=/usr/local/lib/python3.12/dist-packages:$PROJECT_DIR\"|" "$SERVICE_DST"
        systemctl daemon-reload
        systemctl enable tank-init.service 2>/dev/null
        systemctl set-default graphical.target 2>/dev/null || true
        info "tank-init.service installed and enabled"
    else
        dry "Install $SERVICE_DST + enable + set graphical.target"
    fi
else
    warn "Service file not found at $SERVICE_SRC"
fi

# ═══════════════════════════════════════════════════════════════════════════
# STEP 12: Verification
# ═══════════════════════════════════════════════════════════════════════════
step "12/12 — Installation Verification"

if [[ $APPLY -eq 1 ]]; then
    ERRORS=0
    TOTAL_CHECKS=9
    PASSED=0

    check_pass() { PASSED=$((PASSED + 1)); info "$1"; }
    check_fail() { ERRORS=$((ERRORS + 1)); warn "$1"; }

    # 1. Python
    PY_VER=$($PYTHON --version 2>&1)
    echo "$PY_VER" | grep -q "3\." && check_pass "Python $PY_VER" || check_fail "Python check failed"

    # 2. ROS2
    if command -v ros2 >/dev/null 2>&1; then
        check_pass "ROS2: $(ros2 --version 2>&1 | head -1)"
    else
        check_fail "ROS2 not installed (run install again with network)"
    fi

    # 3. PySide6
    export PYTHONPATH="/usr/local/lib/python3.12/dist-packages:$PROJECT_DIR:$PYTHONPATH"
    if QT_QPA_PLATFORM=offscreen python3 -c "from PySide6.QtCore import Qt; print(f'Qt {Qt.__version__}')" 2>/dev/null; then
        check_pass "PySide6 / Qt6: OK"
    else
        check_fail "PySide6 import failed — GUI mode will use simulation fallback"
    fi

    # 4. tank_os core modules
    if python3 -c "from tank_os.core.event_bus import EventBus; print('tank_os.core: OK')" 2>/dev/null; then
        check_pass "tank_os.core modules: OK"
    else
        check_fail "tank_os.core import failed"
    fi

    # 5. Preload Manager
    if python3 -c "from tank_os.core.preload_manager import PreloadManager; pm=PreloadManager(); pm.initialize(); r=pm.report(); print(f'Installed: {r.downloaded}/{r.total_items}')" 2>/dev/null; then
        check_pass "PreloadManager: OK"
    else
        check_fail "PreloadManager import failed"
    fi

    # 6. All widgets
    if python3 -c "
from tank_os.widgets.top_bar import TopBar
from tank_os.widgets.bottom_dock import BottomDock
from tank_os.widgets.ai_avatar import AIAvatar
from tank_os.widgets.camera_widget import CameraWidget
from tank_os.widgets.battery_widget import BatteryWidget
from tank_os.widgets.clock_widget import LiveClock
from tank_os.widgets.map_widget import MapWidget
from tank_os.widgets.status_widget import StatusWidget
from tank_os.widgets.notifications_overlay import NotificationsOverlay
print('9 widgets: OK')
" 2>/dev/null; then
        check_pass "All 9 widgets import: OK"
    else
        check_fail "Some widgets failed to import"
    fi

    # 7. Hardware interfaces
    if python3 -c "
import lgpio
import smbus
print('Hardware IO: OK')
" 2>/dev/null; then
        check_pass "Hardware I/O libraries: OK"
    else
        check_fail "Some hardware libraries not available (expected on non-Pi)"
    fi

    # 8. AI runtimes
    if python3 -c "
import numpy
import cv2
print(f'numpy: {numpy.__version__}')
print(f'opencv: {cv2.__version__}')
" 2>/dev/null; then
        check_pass "AI runtimes (numpy, opencv): OK"
    else
        check_fail "Some AI runtimes missing"
    fi

    # 9. I2C bus
    if command -v i2cdetect >/dev/null 2>&1; then
        check_pass "I2C tools: OK"
    else
        check_fail "i2c-tools not found"
    fi

    # ── Summary ──────────────────────────────────────────────────────────
    echo ""
    if [[ $ERRORS -eq 0 ]]; then
        echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║  ${BOLD}✅  TankOS Fully Installed and Verified!${NC}${GREEN}            ║${NC}"
        echo -e "${GREEN}║  ${BOLD}$PASSED/$TOTAL_CHECKS checks passed${NC}${GREEN}                         ║${NC}"
        echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
    else
        echo -e "${YELLOW}╔══════════════════════════════════════════════════════════╗${NC}"
        echo -e "${YELLOW}║  ${BOLD}⚠  Installed with $ERRORS issue(s) — $PASSED/$TOTAL_CHECKS passed${NC}${YELLOW}     ║${NC}"
        echo -e "${YELLOW}╚══════════════════════════════════════════════════════════╝${NC}"
    fi

    echo ""
    echo -e "  ${BOLD}Quick start:${NC}"
    echo -e "  ${GREEN}▶${NC}  Simulation mode:       python3 -m tank_os.shell.main"
    echo -e "  ${GREEN}▶${NC}  Qt GUI mode:           TANKOS_QT=1 python3 -m tank_os.shell.main"
    echo -e "  ${GREEN}▶${NC}  Boot at startup:       systemctl start tank-init.service"
    echo -e "  ${GREEN}▶${NC}  View logs:             journalctl -u tank-init.service -f"
    echo ""
    echo -e "  ${BOLD}Files:${NC}"
    echo -e "     Config:  /root/.config/tank_os/settings.json"
    echo -e "     Models:  /var/lib/tank_os/models/"
    echo -e "     Logs:    /var/log/tankos-install.log"
    echo ""

    # If Pi, suggest reboot for config.txt changes
    if $IS_PI; then
        echo -e "  ${YELLOW}⚠  Reboot recommended to apply hardware config changes.${NC}"
        echo -e "     Run:  sudo reboot"
        echo ""
    fi
fi

# ── Done ─────────────────────────────────────────────────────────────────
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" | tee -a "$LOG_FILE"
echo -e "${GREEN}  Installer complete.${NC}" | tee -a "$LOG_FILE"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" | tee -a "$LOG_FILE"
