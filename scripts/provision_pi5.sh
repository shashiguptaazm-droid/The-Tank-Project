#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# TankOS — Comprehensive Pi 5 Provisioner (legacy wrapper)
# ═══════════════════════════════════════════════════════════════════════
#
# This script now delegates to the unified master installer:
#   tank_os/install.sh
#
# Usage:
#     bash scripts/provision_pi5.sh            # dry run
#     bash scripts/provision_pi5.sh --apply    # full install
#
# The unified installer handles hardware config + ALL dependencies.

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
INSTALLER="$SCRIPT_DIR/tank_os/install.sh"

if [[ -f "$INSTALLER" ]]; then
    exec bash "$INSTALLER" "$@"
else
    echo "[ERROR] Unified installer not found at $INSTALLER"
    echo "Please run from the project root: bash tank_os/install.sh --apply"
    exit 1
fi
