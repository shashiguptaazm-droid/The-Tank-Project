#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# TankOS — Pi 5 Hardware Prep (legacy wrapper)
# ═══════════════════════════════════════════════════════════════════════
#
# This script now delegates to the unified master installer:
#   tank_os/install.sh
#
# Usage:
#     bash scripts/setup_pi5.sh            # dry run
#     bash scripts/setup_pi5.sh --apply    # full install
#
# The unified installer handles hardware config + ALL dependencies.

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
INSTALLER="$SCRIPT_DIR/tank_os/install.sh"

if [[ -f "$INSTALLER" ]]; then
    exec bash "$INSTALLER" "$@"
else
    echo "[ERROR] Unified installer not found at $INSTALLER"
    echo "Please run: bash tank_os/install.sh --apply"
    exit 1
fi
