#!/bin/bash
# TankOS — Start background download of all manifest items
# This script returns immediately; download runs in background.
# Check progress: tail -f /var/log/tank_os/download_output.log

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# scripts are at tank_os/scripts/, project root is 2 levels up
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="/var/log/tank_os"
LOG_FILE="$LOG_DIR/download_output.log"
PID_FILE="/var/run/tank_os_download.pid"

# Create log directory
mkdir -p "$LOG_DIR"

# Kill previous instance if running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Killing previous download process (PID: $OLD_PID)..."
        kill "$OLD_PID" 2>/dev/null || true
        sleep 1
    fi
    rm -f "$PID_FILE"
fi

# Start download in background
cd "$PROJECT_DIR"
export PYTHONPATH="/usr/local/lib/python3.12/dist-packages:$PYTHONPATH"

echo "Starting TankOS download in background..."
echo "  Project: $PROJECT_DIR"
echo "  Log:     $LOG_FILE"
echo ""

nohup python3 -u "$SCRIPT_DIR/download_everything.py" --concurrent 3 > "$LOG_FILE" 2>&1 &
PID=$!
echo "$PID" > "$PID_FILE"
disown "$PID"

echo "Download started (PID: $PID)"
echo ""
echo "Commands to monitor:"
echo "  tail -f $LOG_FILE          # Watch progress live"
echo "  grep 'ERROR\|FAILED\|✅' $LOG_FILE  # Quick status"
echo "  ps aux | grep download     # Check if running"
echo "  python3 \"$SCRIPT_DIR/download_everything.py\" --status  # Check via API"
