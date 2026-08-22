#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
# The Tank Project — Cross-Distro Installer
# ═══════════════════════════════════════════════════════════════════════════
# Usage:
#   bash install.sh [--apply] [--skip-ros] [--skip-pip] [--skip-models]
#
#   --apply        Actually install (default = dry-run)
#   --skip-ros     Skip ROS2 Humble (~2 GB)
#   --skip-pip     Skip Python packages
#   --skip-models  Skip AI model downloads (~8 GB)
#   -h, --help     Show this help
#
# Supported: Ubuntu/Debian · Fedora/RHEL · Arch/Manjaro · openSUSE · Alpine
# Needs:     curl, sudo, python3 (auto-installed if missing)
#
# Quick start:
#   curl -sSL https://raw.githubusercontent.com/shashiguptaazm-droid/The-Tank-Project/main/install.sh | sudo bash -s -- --apply
# ═══════════════════════════════════════════════════════════════════════════
set -euo pipefail

# ── Detect OS ──────────────────────────────────────────────────────────
ID=""; LIKE=""
. /etc/os-release 2>/dev/null || true
ID="${ID,,}" LIKE="${LIKE,,}"

declare -A PM PM_INSTALL PM_UPDATE PM_QUERY
if   command -v apt-get     >/dev/null; then PM="apt"     PM_UPDATE="apt-get update -qq"                                 PM_INSTALL="DEBIAN_FRONTEND=noninteractive apt-get install -y -qq"   PM_QUERY="dpkg -s"
elif command -v dnf         >/dev/null; then PM="dnf"     PM_UPDATE=""                                                     PM_INSTALL="dnf install -y -q"                                        PM_QUERY="rpm -q"
elif command -v yum         >/dev/null; then PM="yum"     PM_UPDATE=""                                                     PM_INSTALL="yum install -y -q"                                        PM_QUERY="rpm -q"
elif command -v pacman      >/dev/null; then PM="pacman"  PM_UPDATE="pacman -Sy --noconfirm"                              PM_INSTALL="pacman -S --noconfirm --needed"                           PM_QUERY="pacman -Qi"
elif command -v zypper      >/dev/null; then PM="zypper"  PM_UPDATE="zypper --non-interactive refresh"                    PM_INSTALL="zypper --non-interactive install -y"                      PM_QUERY="rpm -q"
elif command -v apk         >/dev/null; then PM="apk"     PM_UPDATE="apk update"                                          PM_INSTALL="apk add"                                                  PM_QUERY="apk info -e"
else echo "✗ No supported package manager found. Install Python3 + git manually."; exit 1; fi

# ── Args ────────────────────────────────────────────────────────────────
APPLY=0 SKIP_ROS=0 SKIP_PIP=0 SKIP_MODELS=0
for a in "$@"; do case "$a" in --apply) APPLY=1;; --skip-ros) SKIP_ROS=1;; --skip-pip) SKIP_PIP=1;; --skip-models) SKIP_MODELS=1;; -h|--help) head -19 "$0"; exit 0;; esac; done

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
RED='\033[0;31m'; GRN='\033[0;32m'; YLW='\033[1;33m'; BLD='\033[1m'; NC='\033[0m'
ok()  { echo -e "${GRN}[✓]${NC} $*"; }
warn(){ echo -e "${YLW}[!]${NC} $*"; }
err() { echo -e "${RED}[✗]${NC} $*" >&2; }
run() { echo "  $ $*"; [[ $APPLY -eq 1 ]] && "$@" || true; }

[[ $APPLY -eq 0 ]] && echo -e "${YLW}⚠  DRY-RUN — add --apply to install${NC}\n"
[[ $(id -u) -ne 0 && $APPLY -eq 1 ]] && { err "Run as root: sudo bash $0 --apply"; exit 1; }

# ── STEP 1: Bootstrap core dependencies ────────────────────────────
echo -e "\n${BLD}═══ 1. Bootstrap: $PM ═══${NC}"
[[ -n "${PM_UPDATE}" ]] && run $PM_UPDATE

# Distro-agnostic package list (key=generic, space-separated per-distro name)
_python3="" _git="" _curl="" _ffmpeg="" _sqlite=""
if   [[ $PM == apt ]]; then
    _python3="python3 python3-pip python3-venv"
    _git="git" _curl="curl" _ffmpeg="ffmpeg" _sqlite="sqlite3"
elif [[ $PM == dnf || $PM == yum ]]; then
    _python3="python3 python3-pip"
    _git="git" _curl="curl" _ffmpeg="ffmpeg-free" _sqlite="sqlite"
elif [[ $PM == pacman ]]; then
    _python3="python python-pip"
    _git="git" _curl="curl" _ffmpeg="ffmpeg" _sqlite="sqlite"
elif [[ $PM == zypper ]]; then
    _python3="python3 python3-pip"
    _git="git" _curl="curl" _ffmpeg="ffmpeg" _sqlite="sqlite3"
elif [[ $PM == apk ]]; then
    _python3="python3 py3-pip py3-venv"
    _git="git" _curl="curl" _ffmpeg="ffmpeg" _sqlite="sqlite"
fi

# Install each group
for group in "$_python3" "$_git" "$_curl" "$_ffmpeg" "$_sqlite"; do
    [[ -z "${group// }" ]] && continue
    pkgs=($group)
    missing=()
    for p in "${pkgs[@]}"; do
        # Check if binary or package already installed
        command -v "$p" >/dev/null 2>&1 && continue
        $PM_QUERY "$p" >/dev/null 2>&1 && continue
        missing+=("$p")
    done
    if [[ ${#missing[@]} -eq 0 ]]; then
        ok "${pkgs[*]}"
    else
        run $PM_INSTALL ${missing[*]}
    fi
done

# ── STEP 2: Python packages ────────────────────────────────────────────
[[ $SKIP_PIP -eq 1 ]] || {
    echo -e "\n${BLD}═══ 2. Python packages ═══${NC}"
    PIP="pip3 install --break-system-packages 2>/dev/null || pip3 install"
    for req in "$PROJECT_DIR/requirements.txt" "$PROJECT_DIR/requirements-dev.txt"; do
        [[ -f "$req" ]] || continue
        run bash -c "$PIP -r \"$req\" || $PIP -r \"$req\""
        ok "$(basename "$req")"
    done
}

# ── STEP 3: ROS2 Humble (optional, Ubuntu/Debian only) ─────────────────
[[ $SKIP_ROS -eq 1 ]] || {
    echo -e "\n${BLD}═══ 3. ROS2 Humble ═══${NC}"
    if command -v ros2 >/dev/null 2>&1; then
        ok "ROS2 already installed: $(ros2 --version 2>&1)"
    elif [[ $PM == "apt" ]]; then
        run curl -fsSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key | gpg --dearmor -o /usr/share/keyrings/ros-archive-keyring.gpg 2>/dev/null
        run bash -c '. /etc/os-release && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $VERSION_CODENAME main" > /etc/apt/sources.list.d/ros2.list'
        run apt-get update -qq
        run DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ros-humble-ros-base python3-colcon-common-extensions python3-rosdep
        [[ -f /opt/ros/humble/setup.bash ]] && echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
        ok "ROS2 Humble installed"
    else
        warn "ROS2 auto-install only on Ubuntu/Debian — install manually or use --skip-ros"
    fi
}

# ── STEP 4: AI Models (optional) ───────────────────────────────────────
[[ $SKIP_MODELS -eq 1 ]] || {
    echo -e "\n${BLD}═══ 4. AI Models ═══${NC}"
    if [[ -f "$PROJECT_DIR/tank_os/core/preload_manager.py" ]]; then
        run python3 -c "from tank_os.core.preload_manager import PreloadManager; pm=PreloadManager(); pm.initialize(); pm.download_required()"
        ok "AI models download triggered (background, ~8 GB)"
    else
        warn "PreloadManager not found — skipping AI models"
    fi
}

# ── Done ────────────────────────────────────────────────────────────────
echo -e "\n${GRN}${BLD}═══ Tank Project installed ═══${NC}"
echo "  Run:  cd \"$PROJECT_DIR\" && python3 -m tank_os.shell.main"
echo "  GUI:  TANKOS_QT=1 python3 -m tank_os.shell.main"
[[ $SKIP_ROS -eq 0 && $PM == "apt" ]] && echo "  ROS:  source /opt/ros/humble/setup.bash && cd tank_ws && colcon build --symlink-install"
echo ""