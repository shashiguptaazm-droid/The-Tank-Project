#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
# TankOS — Complete Auto Setup & Verification
# ═══════════════════════════════════════════════════════════════════════════
# Runs entirely offline-ready after first execution. Downloads all models,
# installs all packages, builds all components, and verifies everything.
#
# Usage:
#   sudo bash tankos_setup.sh              # Full setup (interactive)
#   sudo bash tankos_setup.sh --auto       # Unattended setup
#   sudo bash tankos_setup.sh --verify     # Verify only, no downloads
#   sudo bash tankos_setup.sh --download   # Download missing items only
#   sudo bash tankos_setup.sh --status     # Show setup status summary
#
# Exit codes:
#   0 = all good
#   1 = some items failed
#   2 = critical items missing
# ═══════════════════════════════════════════════════════════════════════════

set -euo pipefail
shopt -s nullglob

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TANKOS_DIR="${TANKOS_DIR:-/var/lib/tank_os}"
TANKOS_LOG="${TANKOS_LOG:-/var/log/tank_os}"
DOWNLOAD_LOG="$TANKOS_LOG/setup.log"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

PASS=0; FAIL=0; WARN=0

mkdir -p "$TANKOS_DIR" "$TANKOS_LOG"
_log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$DOWNLOAD_LOG"; }

# ── Helpers ─────────────────────────────────────────────────────────────────

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; _log "[INFO]  $*"; }
ok()      { echo -e "${GREEN}[OK]${NC}    $*"; _log "[OK]    $*"; PASS=$((PASS + 1)); }
fail()    { echo -e "${RED}[FAIL]${NC}  $*"; _log "[FAIL]  $*"; FAIL=$((FAIL + 1)); }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; _log "[WARN]  $*"; WARN=$((WARN + 1)); }
head()    { echo -e "\n${BOLD}━━━ $* ━━━${NC}"; _log "━━━ $* ━━━"; }
title()   { echo -e "\n${CYAN}══════════════════════════════════════════════════════${NC}\n  ${BOLD}$*\n${CYAN}══════════════════════════════════════════════════════${NC}"; _log "══ $* ══"; }

# Resolve a URL through its redirect chain (HuggingFace HF -> cdn-lfs.huggingface.co).
# Why: the cdn sometimes strips the Range header across the redirect, defeating
# curl's `-C -` auto-resume. Pre-resolving lets the GET go straight to the
# byte-range-aware server so a `.part` resume works reliably.
# We use curl's native `-w '%{url_effective}'` instead of awk-parsing the
# last `Location:` header so we don't get fooled by interleaved redirect+auth
# headers with weird formatting.
_resolve_url() {
    local url="$1" final=""
    final=$(curl -sIL -o /dev/null --connect-timeout 15 --max-time 60 \
            -w '%{url_effective}\n' "$url" 2>/dev/null)
    if [[ "$final" == http* ]]; then
        printf '%s\n' "$final"
    else
        # Couldn't resolve through redirects; warn so on-call sees the resume
        # may not work for this URL and fall back to the original URL.
        warn "_resolve_url: curl did not return http URL for $url; using original"
        printf '%s\n' "$url"
    fi
}

# Bytes of free space at a path. Falls back to 0 if df fails.
_free_gb_at() {
    df -BG "$1" 2>/dev/null | awk 'NR==2{print $4}' | tr -d 'G' || echo 0
}

# ── System info ──────────────────────────────────────────────────────────────

detect_arch() {
    local arch
    arch=$(uname -m)
    case "$arch" in
        x86_64)  echo "x86_64" ;;
        aarch64) echo "aarch64" ;;
        *)       echo "$arch" ;;
    esac
}

detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "$ID-$VERSION_ID"
    else
        echo "unknown"
    fi
}

ARCH=$(detect_arch)
OS=$(detect_os)
CPUS=$(nproc)
MEM_GB=$(free -g | awk '/^Mem:/{print $2}')
DISK_GB=$(df -BG "$TANKOS_DIR" 2>/dev/null | awk 'NR==2{print $4}' | tr -d 'G')

# ── Phase 1: System Dependencies ────────────────────────────────────────────

phase_system_packages() {
    title "Phase 1: System Packages"

    local pkgs=(
        python3 python3-pip python3-venv
        build-essential cmake git
        ffmpeg gstreamer1.0-tools
        sqlite3 curl wget unzip
        libopenblas-dev libssl-dev
    )

    for pkg in "${pkgs[@]}"; do
        if dpkg -s "$pkg" &>/dev/null; then
            ok "Package $pkg already installed"
        else
            info "Installing $pkg..."
            if DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "$pkg" 2>/dev/null; then
                ok "Installed $pkg"
            else
                warn "Could not install $pkg (may not be available on $ARCH)"
            fi
        fi
    done
}

# ── Phase 2: Python Dependencies ────────────────────────────────────────────

phase_python_packages() {
    title "Phase 2: Python Packages"

    pip3 install -q "onnxruntime" "faiss-cpu" 2>/dev/null && ok "Installed onnxruntime + faiss-cpu" || warn "pip install onnxruntime/faiss-cpu failed"

    local pkgs=(
        "fastapi" "uvicorn" "httpx"
        "pydantic" "pydantic-settings"
        "jinja2" "aiofiles"
        "httpx" "beautifulsoup4"
        "numpy" "scipy"
    )

    for pkg in "${pkgs[@]}"; do
        if python3 -c "import ${pkg//-/_}" 2>/dev/null; then
            ok "Python $pkg already installed"
        else
            info "Installing $pkg..."
            if pip3 install -q "$pkg" 2>/dev/null; then
                ok "Installed $pkg"
            else
                warn "Could not pip install $pkg"
            fi
        fi
    done
}

# ── Phase 3: AI Models (with auto-resume, disk guards, redirect-resolve) ────

phase_ai_models() {
    title "Phase 3: AI Model Downloads"

    local models_dir="$TANKOS_DIR/models"
    mkdir -p "$models_dir"/llm "$models_dir/speech/piper/voices" "$models_dir/vision/yolo" "$models_dir/vision/face"

    # Prune stale .part files from prior interrupted runs. A `.part` is
    # considered stale when its corresponding target doesn't exist yet OR
    # the .part is suspiciously small (< 1/4 of the min_mb threshold).
    # This stops the disk-guard from being misled by ghost partials that
    # were never going to be resumed cleanly.
    _prune_stale_parts() {
        local targets=(
            "$models_dir/llm/Phi-3-mini-4k-instruct-q4.gguf"
            "$models_dir/llm/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
            "$models_dir/llm/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
            "$models_dir/llm/Qwen2-VL-7B-Instruct-Q4_K_M.gguf"
            "$models_dir/llm/mmproj-Qwen2-VL-7B-Instruct-f16.gguf"
            "$models_dir/vision/yolo/yolov8n.pt"
            "$models_dir/vision/yolo/yolov8s.pt"
            "$models_dir/vision/face/facenet512_weights.h5"
            "$models_dir/speech/piper/voices/en_US-amy-medium.onnx"
        )
        for t in "${targets[@]}"; do
            local p="${t}.part"
            if [ -f "$p" ] && [ ! -f "$t" ]; then
                local sz_mb=$(( $(stat -c%s "$p" 2>/dev/null || echo 0) / 1048576 ))
                # Below 64 MB for a multi-hundred MB target => not resumable.
                if (( sz_mb < 64 )); then
                    warn "pruning stale .part ($sz_mb MB): $p"
                    rm -f "$p"
                else
                    info "keeping resumable .part ($sz_mb MB): $p"
                fi
            fi
        done
    }
    _prune_stale_parts

    # Per-model expected_min_mb thresholds. When upstream bumps a weight, this
    # needs a bump too; otherwise a "fully downloaded" file gets re-fetched.
    download_model() {
        local url="$1"
        local target="$2"
        local min_mb="$3"
        local label="$4"

        local part="${target}.part"

        # 1. Already completely downloaded?
        if [ -f "$target" ]; then
            local sz_mb
            sz_mb=$(( $(stat -c%s "$target" 2>/dev/null || echo 0) / 1048576 ))
            if (( sz_mb >= min_mb )); then
                local size_bytes; size_bytes=$(stat -c%s "$target")
                ok "${label}: $(numfmt --to=iec "$size_bytes")"
                return 0
            fi
            warn "${label}: target exists but only ${sz_mb} MB (< ${min_mb} MB) — re-downloading"
            rm -f "$target"
        fi
        # Half-finished .part lying around? leave it; `curl -C -` auto-detects it.

        # 2. Disk-space safety: refuse to start a download that would fill /var.
        local free_gb; free_gb=$(_free_gb_at "$TANKOS_DIR")
        # Add 1 GB headroom on top of min_mb so filesystem metadata + OS don't crash.
        local need_gb=$(( (min_mb + 1023) / 1024 + 1 ))
        if (( free_gb < need_gb )); then
            fail "${label}: only ${free_gb} GB free at $TANKOS_DIR, need >= ${need_gb} GB (>=${min_mb} MB)"
            return 1
        fi
        info "${label}: ${free_gb} GB free at $TANKOS_DIR, need ${need_gb} GB"

        # 3. Resolve redirect chain to a direct URL so curl -C - keeps the Range.
        info "Downloading ${label} (resolving redirect)..."
        local final_url
        final_url=$(_resolve_url "$url")
        if [[ "$final_url" != "$url" ]]; then
            _log "[INFO]  ${label}: resolved to ${final_url}"
        fi

        # 4. Curl with auto-resume into .part. stderr still captured in setup.log
        #    for post-mortem on FAILURE only; success path stays quiet.
        local curl_err ec
        curl_err=$(mktemp)
        ec=0
        curl -sfL -C - --connect-timeout 30 --retry 5 --retry-delay 5 \
            -o "$part" "$final_url" 2>"$curl_err" || ec=$?
        _log "[curl] $(basename "$target") exit=$ec"
        if (( ec != 0 )) && [ -s "$curl_err" ]; then
            tail -5 "$curl_err" >> "$DOWNLOAD_LOG" 2>/dev/null || true
        fi
        rm -f "$curl_err"

        if (( ec == 0 )); then
            mv "$part" "$target"
            local size_bytes; size_bytes=$(stat -c%s "$target")
            ok "Downloaded ${label}: $(numfmt --to=iec "$size_bytes")"
            return 0
        fi

        if (( ec == 33 )); then
            # Range Not Satisfiable: server says our .part matches the whole file.
            if [ -s "$part" ]; then
                mv "$part" "$target"
                local size_bytes; size_bytes=$(stat -c%s "$target")
                ok "${label}: already fully downloaded (curl exit 33, range N/S): $(numfmt --to=iec "$size_bytes")"
                return 0
            fi
            # Empty .part + exit 33: re-fetch from scratch (defensive — likely unreachable).
            warn "${label}: curl exit 33 with empty .part — full re-fetch"
            curl_err=$(mktemp)
            local ec2
            ec2=0
            curl -sfL --connect-timeout 30 --retry 5 --retry-delay 5 \
                -o "$target" "$final_url" 2>"$curl_err" || ec2=$?
            _log "[curl-refetch] $(basename "$target") exit=$ec2"
            if (( ec2 != 0 )) && [ -s "$curl_err" ]; then
                tail -5 "$curl_err" >> "$DOWNLOAD_LOG" 2>/dev/null || true
            fi
            rm -f "$curl_err"
            if (( ec2 == 0 )); then
                local size_bytes; size_bytes=$(stat -c%s "$target")
                ok "Downloaded ${label}: $(numfmt --to=iec "$size_bytes")"
                return 0
            fi
            fail "${label}: re-fetch failed (curl exit $ec2)"
            return 1
        fi

        # Real failure; leave the .part in place so the next run resumes.
        fail "${label}: curl exit $ec (partial kept at $part for next-run resume)"
        return 1
    }

    # ── LLMs (each passes its own expected_min_mb threshold) ─────────────────
    head "Large Language Models"
    download_model \
        "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf" \
        "$models_dir/llm/Phi-3-mini-4k-instruct-q4.gguf" \
        2200 "LLM Phi-3-mini-4k-instruct-q4"
    download_model \
        "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf" \
        "$models_dir/llm/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf" \
        650 "LLM tinyllama-1.1b-chat"
    download_model \
        "https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/resolve/main/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf" \
        "$models_dir/llm/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf" \
        950 "LLM qwen2.5-coder-1.5b-instruct"
    download_model \
        "https://huggingface.co/bartowski/Qwen2-VL-7B-Instruct-GGUF/resolve/main/Qwen2-VL-7B-Instruct-Q4_K_M.gguf" \
        "$models_dir/llm/Qwen2-VL-7B-Instruct-Q4_K_M.gguf" \
        3900 "LLM Qwen2-VL-7B-Instruct"
    download_model \
        "https://huggingface.co/bartowski/Qwen2-VL-7B-Instruct-GGUF/resolve/main/mmproj-Qwen2-VL-7B-Instruct-f16.gguf" \
        "$models_dir/llm/mmproj-Qwen2-VL-7B-Instruct-f16.gguf" \
        1200 "LLM mmproj-Qwen2-VL-7B"

    # ── Vision ───────────────────────────────────────────────────────────────
    head "Vision Models"
    download_model \
        "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.pt" \
        "$models_dir/vision/yolo/yolov8n.pt" \
        5 "Vision yolov8n"
    download_model \
        "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8s.pt" \
        "$models_dir/vision/yolo/yolov8s.pt" \
        20 "Vision yolov8s"
    download_model \
        "https://github.com/serengil/deepface_models/releases/download/v1.0/facenet512_weights.h5" \
        "$models_dir/vision/face/facenet512_weights.h5" \
        85 "Vision facenet512"

    # ── Speech ───────────────────────────────────────────────────────────────
    head "Speech Models"
    download_model \
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx" \
        "$models_dir/speech/piper/voices/en_US-amy-medium.onnx" \
        55 "Speech Piper en_US-amy-medium"
}

# ── Phase 3½: Python Path Setup ──────────────────────────────────────────────

phase_python_path() {
    title "Phase 3½: Python Path Setup"
    local project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    export PYTHONPATH="/usr/local/lib/python3.12/dist-packages:$project_dir:${PYTHONPATH:-}"
    ok "PYTHONPATH set to $PYTHONPATH"
}

# ── Phase 4: TankOS Module Validation ────────────────────────────────────────

phase_tankos_modules() {
    title "Phase 4: TankOS Module Validation"

    local modules=(
        "tank_os.internet"
        "tank_os.ai"
        "tank_os.core"
        "tank_os.preload"
        "tank_os.shell"
    )

    for mod in "${modules[@]}"; do
        if python3 -c "import $mod" 2>/dev/null; then
            ok "Module $mod loads successfully"
        else
            fail "Module $mod failed to import"
        fi
    done
}

# ── Phase 5: Manifest Verification ───────────────────────────────────────────

phase_manifest_verify() {
    title "Phase 5: Preload Manifest Verification"

    cd "$PROJECT_DIR"
    export PYTHONPATH="/usr/local/lib/python3.12/dist-packages:$PYTHONPATH"

    if python3 -c "from tank_os.preload.manifest import MANIFEST, summary; s=summary(); print(f'Manifest: {s[\"total_items\"]} items, {s[\"total_size_mb\"]} MB, {len(s[\"categories\"])} categories')" 2>/dev/null; then
        ok "Manifest loads successfully"
    else
        fail "Manifest failed to load"
    fi

    local models_dir="$TANKOS_DIR/models"
    local expected=(
        "$models_dir/llm/Phi-3-mini-4k-instruct-q4.gguf"
        "$models_dir/llm/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
        "$models_dir/llm/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
        "$models_dir/llm/Qwen2-VL-7B-Instruct-Q4_K_M.gguf"
        "$models_dir/llm/mmproj-Qwen2-VL-7B-Instruct-f16.gguf"
        "$models_dir/vision/yolo/yolov8n.pt"
        "$models_dir/vision/yolo/yolov8s.pt"
        "$models_dir/vision/face/facenet512_weights.h5"
        "$models_dir/speech/piper/voices/en_US-amy-medium.onnx"
    )

    for f in "${expected[@]}"; do
        if [ -f "$f" ]; then
            local size
            size=$(stat -c%s "$f" 2>/dev/null || echo 0)
            ok "Model $f ($(numfmt --to=iec $size))"
        else
            warn "Model $f not found"
        fi
    done
}

# ── Phase 6: Simple Internet Dashboard ───────────────────────────────────────

phase_internet_dashboard() {
    title "Phase 6: Simple Internet Dashboard"

    export PYTHONPATH="/usr/local/lib/python3.12/dist-packages:$PYTHONPATH"

    if python3 -c "from tank_os.internet.server import app; print(f'{len(app.routes)} routes')" 2>/dev/null; then
        ok "Internet Dashboard server loads"
    else
        fail "Internet Dashboard failed to load"
    fi

    if python3 -c "from tank_os.internet.cli import build_parser; p=build_parser(); print(f'{len(p._subparsers._group_actions[0].choices)} commands')" 2>/dev/null; then
        ok "Internet CLI loads"
    else
        fail "Internet CLI failed to load"
    fi

    if python3 -c "from tank_os.internet.voice_plugin import PLUGINS; print(f'{len(PLUGINS)} voice plugins')" 2>/dev/null; then
        ok "Internet Voice plugins load"
    else
        fail "Internet Voice plugins failed to load"
    fi
}

# ── Phase 7: Project Structure ───────────────────────────────────────────────

phase_project_structure() {
    title "Phase 7: Project Structure Verification"

    local files=(
        "$PROJECT_DIR/README.md"
        "$PROJECT_DIR/ARCHITECTURE.md"
        "$PROJECT_DIR/STATUS.md"
        "$PROJECT_DIR/tank_os/internet/server.py"
        "$PROJECT_DIR/tank_os/internet/downloader.py"
        "$PROJECT_DIR/tank_os/internet/search.py"
        "$PROJECT_DIR/tank_os/internet/manager.py"
        "$PROJECT_DIR/tank_os/internet/cli.py"
        "$PROJECT_DIR/tank_os/internet/voice_plugin.py"
        "$PROJECT_DIR/tank_os/preload/manifest.py"
        "$PROJECT_DIR/tank_os/preload/downloader.py"
        "$PROJECT_DIR/docker-compose.yml"
    )

    for f in "${files[@]}"; do
        if [ -f "$f" ]; then
            ok "File exists: $f"
        else
            warn "File missing: $f"
        fi
    done
}

# ── Summary ──────────────────────────────────────────────────────────────────

print_summary() {
    title "Setup Complete"
    echo -e "  Architecture:          ${BOLD}$ARCH${NC}"
    echo -e "  OS:                   ${BOLD}$OS${NC}"
    echo -e "  CPUs:                 ${BOLD}$CPUS${NC}"
    echo -e "  RAM:                  ${BOLD}${MEM_GB}G${NC}"
    echo -e "  Free Disk:            ${BOLD}${DISK_GB}G${NC}"
    echo -e "  Data Directory:       ${BOLD}$TANKOS_DIR${NC}"
    echo -e "  Log:                  ${BOLD}$DOWNLOAD_LOG${NC}"
    echo ""
    echo -e "  ${GREEN}✓ Pass: $PASS${NC}  ${RED}✗ Fail: $FAIL${NC}  ${YELLOW}⚠ Warn: $WARN${NC}"
    echo ""

    if [ "$FAIL" -eq 0 ] && [ "$WARN" -eq 0 ]; then
        echo -e "  ${GREEN}${BOLD}✅ Everything perfect — TankOS is ready!${NC}"
        echo ""
        echo -e "  Start the dashboard:"
        echo -e "    ${CYAN}python3 -m tank_os.internet.server${NC}"
        echo ""
        echo -e "  Or use the CLI:"
        echo -e "    ${CYAN}python3 -m tank_os.internet.cli stats${NC}"
        echo ""
        echo -e "  Open in browser:"
        echo -e "    ${CYAN}http://localhost:8900${NC}"
    elif [ "$FAIL" -gt 0 ]; then
        echo -e "  ${RED}${BOLD}$FAIL items failed — check $DOWNLOAD_LOG${NC}"
    else
        echo -e "  ${YELLOW}${BOLD}$WARN warnings — non-critical items missing${NC}"
    fi
}

# ── Main ─────────────────────────────────────────────────────────────────────

main() {
    local mode="${1:-full}"

    case "$mode" in
        --verify)
            phase_python_path
            phase_tankos_modules
            phase_manifest_verify
            phase_internet_dashboard
            phase_project_structure
            ;;
        --download)
            phase_ai_models
            ;;
        --status)
            phase_python_path
            phase_manifest_verify
            phase_internet_dashboard
            phase_project_structure
            print_summary
            exit 0
            ;;
        --auto|full|*)
            phase_system_packages
            phase_python_packages
            phase_ai_models
            phase_python_path
            phase_tankos_modules
            phase_manifest_verify
            phase_internet_dashboard
            phase_project_structure
            ;;
    esac

    print_summary

    if [ "$FAIL" -gt 0 ]; then
        exit 1
    fi
    exit 0
}

main "$@"
