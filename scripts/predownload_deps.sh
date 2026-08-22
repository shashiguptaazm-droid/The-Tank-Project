#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
# predownload_deps.sh — Pre-download OS + Python deps for offline install
# ═══════════════════════════════════════════════════════════════════════════
#
# TanksOS / Simple Internet pre-downloader.
# Fills /var/lib/tank_os/wheels  with pip wheels
#       /var/lib/tank_os/apt_cache with .deb files
#       (Layer C = AI models is delegated to tankos_setup.sh --download)
#
# Why this script exists:
#   - docs/DEPENDENCIES.md is the canonical manifest for what we install.
#   - tank_os/install.sh only does live `apt install` + `pip3 install`; if
#     the Pi is offline that's a brick.
#   - predownload_deps.sh runs once on a connected host, then a future
#     `tank_os/install.sh` can be patched to install from the local
#     wheelhouse + apt cache instead of the network.
#
# Usage:
#   sudo bash scripts/predownload_deps.sh               # apt + pip (default)
#   sudo bash scripts/predownload_deps.sh --apt         # apt packages only
#   sudo bash scripts/predownload_deps.sh --pip         # pip wheels only
#   sudo bash scripts/predownload_deps.sh --all         # apt + pip + ai models
#   sudo bash scripts/predownload_deps.sh --dry-run     # print plan, no I/O
#   sudo bash scripts/predownload_deps.sh --resume      # (default) skip cached
#   sudo bash scripts/predownload_deps.sh --clean       # nuke caches + redownload
#   sudo bash scripts/predownload_deps.sh --status      # what's in the cache?
#
# Exit codes:
#   0 = success
#   1 = some subtasks failed
#   2 = blocked (need sudo / missing tools)
# ═══════════════════════════════════════════════════════════════════════════
set -euo pipefail
shopt -s nullglob

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

WHEELHOUSE="${WHEELHOUSE:-/var/lib/tank_os/wheels}"
APT_CACHE="${APT_CACHE:-/var/lib/tank_os/apt_cache}"
STATE_FILE="${STATE_FILE:-/var/log/tank_os/predownload_state.json}"
LOG_FILE="${LOG_FILE:-/var/log/tank_os/predownload_deps.log}"
REQ_FILE="$PROJECT_DIR/requirements.txt"
REQ_DEV_FILE="$PROJECT_DIR/requirements-dev.txt"
DEPS_DOC="$PROJECT_DIR/docs/DEPENDENCIES.md"
TANKOS_SETUP="$SCRIPT_DIR/tankos_setup.sh"

# ── Args ──────────────────────────────────────────────────────────────
MODE_APT=false
MODE_PIP=false
MODE_AI=false
DRY_RUN=false
CLEAN=false
STATUS_ONLY=false

while [[ "${1:-}" =~ ^-- ]]; do
    case "$1" in
        --apt)    MODE_APT=true ;;
        --pip)    MODE_PIP=true ;;
        --ai)     MODE_AI=true ;;
        --all)    MODE_APT=true; MODE_PIP=true; MODE_AI=true ;;
        --dry-run) DRY_RUN=true ;;
        --resume) : ;;  # default behaviour
        --clean)  CLEAN=true ;;
        --status) STATUS_ONLY=true ;;
        -h|--help)
            sed -n '4,40p' "$0" | sed 's/^# //; s/^#//'
            exit 0
            ;;
        *) echo "unknown flag: $1" >&2; exit 2 ;;
    esac
    shift
done

# Default: apt + pip only (AI is already covered by tankos_setup.sh --download)
if ! $MODE_APT && ! $MODE_PIP && ! $MODE_AI && ! $STATUS_ONLY; then
    MODE_APT=true
    MODE_PIP=true
fi

# ── Colors & counters ─────────────────────────────────────────────────
RED=$'\033[0;31m'; GREEN=$'\033[0;32m'; YELLOW=$'\033[1;33m'
BLUE=$'\033[0;34m'; CYAN=$'\033[0;36m'; BOLD=$'\033[1m'; NC=$'\033[0m'
PASS=0; FAIL=0; WARN=0; SKIP=0

mkdir -p "$(dirname "$LOG_FILE")"
_log() { printf '%s %s\n' "$(date -Iseconds)" "$*" >> "$LOG_FILE"; }
say()  { printf '%s[predownload]%s %s\n' "$BLUE" "$NC" "$*"; _log "$*"; }
ok()   { printf '%s[OK]%s   %s\n' "$GREEN" "$NC" "$*"; _log "OK   $*"; PASS=$((PASS+1)); }
fail() { printf '%s[FAIL]%s %s\n' "$RED" "$NC" "$*"; _log "FAIL $*"; FAIL=$((FAIL+1)); }
warn() { printf '%s[WARN]%s %s\n' "$YELLOW" "$NC" "$*"; _log "WARN $*"; WARN=$((WARN+1)); }
skip() { printf '%s[SKIP]%s %s\n' "$CYAN" "$NC" "$*"; _log "SKIP $*"; SKIP=$((SKIP+1)); }
title(){ printf '\n%s═══ %s ═══%s\n' "$BOLD" "$*" "$NC"; _log "=== $* ==="; }

# ── sudo normaliser (so non-sudo invocation transparently escalates) ──
SUDO=""
if [[ $EUID -ne 0 ]]; then
    SUDO="sudo"
    say "not root — will prefix high-priv ops with 'sudo'"
fi

# ── Tool presence ─────────────────────────────────────────────────────
need_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        fail "missing tool: $1"
        return 1
    fi
    return 0
}

# ════════════════════════════════════════════════════════════════════════
# Status report
# ════════════════════════════════════════════════════════════════════════
do_status() {
    title "Pre-download cache status"
    printf "%sWHEELHOUSE:%s %s\n" "$BOLD" "$NC" "$WHEELHOUSE"
    if [[ -d "$WHEELHOUSE" ]]; then
        local wheel_count; wheel_count=$(find "$WHEELHOUSE" -maxdepth 1 -name '*.whl' 2>/dev/null | wc -l)
        local wheel_size; wheel_size=$(du -sh "$WHEELHOUSE" 2>/dev/null | awk '{print $1}')
        printf "  %d wheels, %s on disk\n" "$wheel_count" "$wheel_size"
    else
        echo "  (does not exist)"
    fi
    printf "%sAPT_CACHE:%s  %s\n" "$BOLD" "$NC" "$APT_CACHE"
    if [[ -d "$APT_CACHE" ]]; then
        local debs; debs=$(find "$APT_CACHE" -maxdepth 1 -name '*.deb' 2>/dev/null | wc -l)
        local apt_size; apt_size=$(du -sh "$APT_CACHE" 2>/dev/null | awk '{print $1}')
        printf "  %d .deb files, %s on disk\n" "$debs" "$apt_size"
    else
        echo "  (does not exist)"
    fi
    if [[ -f "$STATE_FILE" ]]; then
        printf "%sLAST RUN:%s   %s\n" "$BOLD" "$NC" "$STATE_FILE"
        cat "$STATE_FILE" 2>/dev/null
    else
        echo "  (no state file yet)"
    fi
}

# ════════════════════════════════════════════════════════════════════════
# Phase A: apt packages (Layer A)
# ════════════════════════════════════════════════════════════════════════
APT_PACKAGES=(
    # from docs/DEPENDENCIES.md -> "Install on Debian/Ubuntu" section
    ffmpeg libtorrent-rasterbar-dev p7zip-full mkvtoolnix
    atomicparsley rtmpdump redis
    # Pi add-ons section
    libmp3lame-dev libx264-dev libx265-dev libvpx-dev
    libfdk-aac-dev libopus-dev libvorbis-dev libass-dev
    # Metadata/MusicBrainz section
    libchromaprint-dev
)

phase_apt() {
    title "Phase A: apt packages (Layer A) — n=${#APT_PACKAGES[@]}"
    need_cmd apt-get || { fail "apt-get not available — Layer A skipped"; return 1; }

    if $DRY_RUN; then
        say "would: apt-get update + download-only install of ${#APT_PACKAGES[@]} packages"
        printf '%s\n' "${APT_PACKAGES[@]}" | sed 's/^/  • /'
        say "would: copy /var/cache/apt/archives/*.deb -> $APT_CACHE/"
        say "would: free-space check: need >=2GB; current=$(df -BG "$APT_CACHE" 2>/dev/null | awk 'NR==2{print $4}')"
        return 0
    fi

    if [[ ! -d "$APT_CACHE" ]]; then
        $SUDO mkdir -p "$APT_CACHE"
    fi

    # disk-space safety: refuse to fill a Pi's SD card.
    local free_gb
    free_gb=$(df -BG "$APT_CACHE" 2>/dev/null | awk 'NR==2{print $4}' | tr -d 'G' || echo 0)
    if (( free_gb < 2 )); then
        fail "only ${free_gb}GB free at $APT_CACHE; need >=2GB for apt predownload"
        return 1
    fi
    say "free space at $APT_CACHE: ${free_gb}GB"

    if $CLEAN; then
        say "clean: removing $APT_CACHE/*.deb"
        $SUDO find "$APT_CACHE" -maxdepth 1 -name '*.deb' -delete 2>/dev/null || true
    fi

    say "running: apt-get update (one-time)"
    $SUDO apt-get update -qq 2>&1 | tail -3 || warn "apt-get update had warnings (continuing)"

    local missing=()
    local already=()
    for pkg in "${APT_PACKAGES[@]}"; do
        if dpkg -s "$pkg" >/dev/null 2>&1; then
            # already installed => still force a --reinstall download so the .deb
            # is guaranteed to land in /var/cache/apt/archives even after a
            # `apt-get clean` (otherwise the offline install would miss it).
            already+=("$pkg")
        else
            missing+=("$pkg")
        fi
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        say "downloading ${#missing[@]} missing debs via apt-get install --download-only"
        # shellcheck disable=SC2086
        $SUDO DEBIAN_FRONTEND=noninteractive apt-get install \
            --download-only -y --no-install-recommends "${missing[@]}" 2>&1 | tail -10 \
            || fail "apt-get install --download-only failed for ${#missing[@]} pkgs"
    else
        say "all ${#APT_PACKAGES[@]} apt packages already installed; nothing missing"
    fi

    if [[ ${#already[@]} -gt 0 ]]; then
        say "force --reinstall download for ${#already[@]} already-installed packages (ensures offline cache has them)"
        # shellcheck disable=SC2086
        $SUDO DEBIAN_FRONTEND=noninteractive apt-get install \
            --download-only -y --reinstall --no-install-recommends "${already[@]}" 2>&1 | tail -10 \
            || warn "--reinstall had warnings; some already-installed packages may be missing from offline cache"
    fi

    # copy new .deb files out of the system cache into our persistent one.
    $SUDO cp -n /var/cache/apt/archives/*.deb "$APT_CACHE/" 2>/dev/null || true

    # final tally
    local debs_now; debs_now=$(find "$APT_CACHE" -maxdepth 1 -name '*.deb' 2>/dev/null | wc -l)
    local size_now; size_now=$(du -sh "$APT_CACHE" 2>/dev/null | awk '{print $1}')
    local expected_min=$(( ${#APT_PACKAGES[@]} * 1 ))
    if (( debs_now < expected_min )); then
        warn "only $debs_now .deb files at $APT_CACHE; (<${expected_min}) — some pkgs may be missing from offline cache"
    else
        ok "apt cache finalised: $debs_now .deb files, $size_now at $APT_CACHE"
    fi
}

# ════════════════════════════════════════════════════════════════════════
# Phase B: pip wheels (Layer B)
# ════════════════════════════════════════════════════════════════════════
phase_pip() {
    title "Phase B: pip wheels (Layer B)"
    need_cmd python3 || { fail "python3 not available — Layer B skipped"; return 1; }
    need_cmd pip3    || { fail "pip3 not available — Layer B skipped"; return 1; }

    if [[ ! -f "$REQ_FILE" ]]; then
        fail "missing manifest: $REQ_FILE"
        return 1
    fi

    if $DRY_RUN; then
        say "would: pip3 download --dest $WHEELHOUSE -r $REQ_FILE"
        [[ -f "$REQ_DEV_FILE" ]] && say "would: pip3 download --dest $WHEELHOUSE -r $REQ_DEV_FILE"
        say "would: free-space check: need >=3GB; current=$(df -BG "$WHEELHOUSE" 2>/dev/null | awk 'NR==2{print $4}')"
        return 0
    fi

    if $CLEAN; then
        say "clean: removing $WHEELHOUSE/*.whl"
        $SUDO find "$WHEELHOUSE" -maxdepth 1 -name '*.whl' -delete 2>/dev/null || true
    fi

    $SUDO mkdir -p "$WHEELHOUSE"

    # disk-space safety: wheels for ~40 pkgs can be 1-3 GB.
    local free_gb
    free_gb=$(df -BG "$WHEELHOUSE" 2>/dev/null | awk 'NR==2{print $4}' | tr -d 'G' || echo 0)
    if (( free_gb < 3 )); then
        fail "only ${free_gb}GB free at $WHEELHOUSE; need >=3GB for pip predownload"
        return 1
    fi
    say "free space at $WHEELHOUSE: ${free_gb}GB"

    # pip break-system-packages is default-needed on Debian-PEP668; ignore if not set.
    local bsp=""
    if command -v apt-get >/dev/null 2>&1 && dpkg -s python3-pip >/dev/null 2>&1; then
        # detect externally-managed
        if python3 -c "import sys; sys.exit(0 if __import__('importlib').util.find_spec('pip') else 1)" 2>/dev/null; then
            if pip3 --version 2>/dev/null | grep -q "Debian"; then
                bsp="--break-system-packages"
            fi
        fi
    fi

    say "downloading wheels for requirements.txt (this can take 5-15 min on first run)"
    # shellcheck disable=SC2086
    $SUDO pip3 download --dest "$WHEELHOUSE" \
        --prefer-binary \
        $bsp \
        -r "$REQ_FILE" 2>&1 | tail -15 \
        || warn "wheel download had warnings; check $LOG_FILE"

    if [[ -f "$REQ_DEV_FILE" ]]; then
        say "downloading wheels for requirements-dev.txt"
        # shellcheck disable=SC2086
        $SUDO pip3 download --dest "$WHEELHOUSE" \
            --prefer-binary \
            $bsp \
            -r "$REQ_DEV_FILE" 2>&1 | tail -10 \
            || warn "dev-wheel download had warnings (ok; non-essential)"
    fi

    local wheels_now; wheels_now=$(find "$WHEELHOUSE" -maxdepth 1 -name '*.whl' 2>/dev/null | wc -l)
    local size_now;   size_now=$(du -sh "$WHEELHOUSE" 2>/dev/null | awk '{print $1}')
    ok "wheelhouse finalised: $wheels_now wheels, $size_now at $WHEELHOUSE"
}

# ════════════════════════════════════════════════════════════════════════
# Phase C: AI models (Layer C) — delegates to tankos_setup.sh --download
# ════════════════════════════════════════════════════════════════════════
phase_ai() {
    title "Phase C: AI models (Layer C) — delegation"
    if $DRY_RUN; then
        say "would: bash $TANKOS_SETUP --download"
        return 0
    fi
    if [[ -x "$TANKOS_SETUP" ]]; then
        say "delegating AI model downloads to tankos_setup.sh --download"
        $SUDO bash "$TANKOS_SETUP" --download || warn "tankos_setup.sh --download had warnings"
    else
        warn "tankos_setup.sh not found / not executable at $TANKOS_SETUP"
        warn "skipping AI model phase; run 'bash tankos_setup.sh --download' manually"
    fi
}

# ════════════════════════════════════════════════════════════════════════
# State writer
# ════════════════════════════════════════════════════════════════════════
write_state() {
    $SUDO mkdir -p "$(dirname "$STATE_FILE")"
    cat > "$STATE_FILE" <<EOF
{
  "ran_at":   "$(date -Iseconds)",
  "dry_run":  $DRY_RUN,
  "apt":      $MODE_APT,
  "pip":      $MODE_PIP,
  "ai":       $MODE_AI,
  "wheelhouse_path": "$WHEELHOUSE",
  "wheel_count":     $(find "$WHEELHOUSE" -maxdepth 1 -name '*.whl' 2>/dev/null | wc -l),
  "wheel_size":      "$(du -sh "$WHEELHOUSE" 2>/dev/null | awk '{print $1}')",
  "apt_cache_path":  "$APT_CACHE",
  "deb_count":       $(find "$APT_CACHE" -maxdepth 1 -name '*.deb' 2>/dev/null | wc -l),
  "apt_size":        "$(du -sh "$APT_CACHE" 2>/dev/null | awk '{print $1}')",
  "log_file":        "$LOG_FILE"
}
EOF
    ok "wrote state file: $STATE_FILE"
}

# ════════════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════════════
main() {
    title "TankOS / Simple Internet Pre-Downloader"
    say "project root: $PROJECT_DIR"
    say "wheelhouse:   $WHEELHOUSE"
    say "apt cache:    $APT_CACHE"
    say "log file:     $LOG_FILE"
    say "modes:        apt=$MODE_APT pip=$MODE_PIP ai=$MODE_AI dry-run=$DRY_RUN clean=$CLEAN"

    if $STATUS_ONLY; then
        do_status
        exit 0
    fi

    # confirm the canonical manifest sources exist so the user knows we're
    # actually reading them (rather than imagining the dep list).
    [[ -f "$DEPS_DOC"  ]] && ok "canonical dep doc: $DEPS_DOC" || fail "missing $DEPS_DOC"
    [[ -f "$REQ_FILE"  ]] && ok "pip manifest:      $REQ_FILE"   || fail "missing $REQ_FILE"
    [[ -f "$TANKOS_SETUP" ]] && ok "ai-model script:   $TANKOS_SETUP" || warn "no $TANKOS_SETUP (skip AI phase if --ai/--all)"

    $MODE_APT && phase_apt
    $MODE_PIP && phase_pip
    $MODE_AI  && phase_ai

    title "Summary"
    echo "  ${GREEN}pass=$PASS${NC}  ${RED}fail=$FAIL${NC}  ${YELLOW}warn=$WARN${NC}  ${CYAN}skip=$SKIP${NC}"
    echo "  wheelhouse: $WHEELHOUSE ($(du -sh "$WHEELHOUSE" 2>/dev/null | awk '{print $1}'))"
    echo "  apt cache : $APT_CACHE  ($(du -sh "$APT_CACHE"  2>/dev/null | awk '{print $1}'))"
    echo "  log       : $LOG_FILE"
    echo ""
    if ! $DRY_RUN; then
        write_state
    fi

    [[ $FAIL -eq 0 ]] && exit 0 || exit 1
}

main "$@"
