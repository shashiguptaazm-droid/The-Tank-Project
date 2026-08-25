#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
#  🎬 TankOS Terminal Recording — Full Demo
#  Records terminal session to a typescript file
#  Usage: bash scripts/record_demo.sh
# ═══════════════════════════════════════════════════════════════
set -e
cd "$(dirname "$0")/.."

RECORD_FILE="demo_recording_$(date +%Y%m%d_%H%M%S).log"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  🎬 TankOS Terminal Recording Started"
echo "  📁 Output: $RECORD_FILE"
echo "═══════════════════════════════════════════════════════════"
echo ""

script -q -c "python3 scripts/demo_runner.py" "$RECORD_FILE" 2>&1

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ✅ Recording saved to: $RECORD_FILE"
echo "  📏 Size: $(wc -c < "$RECORD_FILE") bytes"
echo "═══════════════════════════════════════════════════════════"
