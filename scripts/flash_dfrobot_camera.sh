#!/bin/bash
# flash_dfrobot_camera.sh — Flash DFRobot ESP32-S3 AI Camera with video firmware
# Usage: sudo bash flash_dfrobot_camera.sh [PORT]
# Default port: /dev/ttyACM0

set -e

PORT="${1:-/dev/ttyACM0}"
FW_DIR="/home/shashi/The-Tank-Project/firmware/usb_video_camera"
MERGED="${FW_DIR}/USBVideoCamera.ino.merged.bin"
OFFSET=0x0

echo "🔧 DFRobot Camera Flash Tool"
echo ""

# Check if merged.bin exists
if [ ! -f "$MERGED" ]; then
    echo "❌ Merged firmware not found: $MERGED"
    echo "   Build it first in Arduino IDE: Sketch → Export compiled Binary"
    echo "   Then copy the .merged.bin from build output to $FW_DIR"
    exit 1
fi

# Check if port exists
if [ ! -e "$PORT" ]; then
    echo "❌ Camera not found at $PORT"
    echo "   Available ports:"
    ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null || echo "   (none)"
    exit 1
fi

# Check esptool
if ! python3 -m esptool version &>/dev/null; then
    echo "📦 Installing esptool..."
    pip3 install --break-system-packages esptool 2>&1 | tail -1
fi

SIZE=$(stat -c%s "$MERGED")
echo ""
echo "   Camera port:  $PORT"
echo "   Firmware:     $MERGED"
echo "   Size:         $SIZE bytes"
echo "   ESP32-S3:     OV3660 sensor + IMU + LED flash"
echo ""

# Flash it
echo "⚡ Erasing flash..."
python3 -m esptool --chip esp32s3 --port "$PORT" erase_flash 2>&1 | tail -3

echo ""
echo "⚡ Writing firmware..."
python3 -m esptool --chip esp32s3 --port "$PORT" \
    --baud 921600 write_flash $OFFSET "$MERGED" 2>&1 | tail -10

echo ""
echo "✅ Flash complete! Camera should now respond to:"
echo "   echo SNAP | minicom -D $PORT -b 921600"
echo ""
echo "   Test from Python:"
echo "   cd ~/The-Tank-Project && python3 -c 'from tank_os.shell.terminal.agent_chat import _camera_vision; print(_camera_vision())'"