#!/bin/bash
# flash_voicecam.sh — compile + flash VoiceCam.ino to the DFRobot camera.
# Safe to run under nohup: logs to /tmp/voicecam_flash.log, survives SSH drops.
set -x
export PATH=$PATH:$HOME/bin
cd ~/The-Tank-Project || exit 1

SKETCH=firmware/dfrobot_camera/VoiceCam
BUILD=$SKETCH/build
FQBN='esp32:esp32:esp32s3:CDCOnBoot=cdc,FlashSize=16M,PSRAM=opi,PartitionScheme=huge_app'

# 1) Compile
arduino-cli compile \
  --fqbn "$FQBN" \
  --library ~/Arduino/libraries/esp32-camera \
  --output-dir "$BUILD" \
  "$SKETCH" || exit 1

ls -la "$BUILD"

# 2) Flash
PORT="${1:-/dev/ttyACM0}"
ESPTOOL_PY=""
if python3 -m esptool version >/dev/null 2>&1; then
  ESPTOOL_PY="python3 -m esptool"
elif [ -f ~/.arduino15/packages/esp32/tools/esptool_py/*/esptool.py ]; then
  ESPTOOL_PY="python3 $(echo ~/.arduino15/packages/esp32/tools/esptool_py/*/esptool.py)"
else
  echo "FATAL: esptool not found" >&2
  exit 1
fi

$ESPTOOL_PY --chip esp32s3 --port "$PORT" --baud 921600 \
  --before usb-reset --after hard-reset write-flash -z \
  0x0     "$BUILD/VoiceCam.ino.bootloader.bin" \
  0x8000  "$BUILD/VoiceCam.ino.partitions.bin" \
  0x10000 "$BUILD/VoiceCam.ino.bin" || exit 1

echo "FLASH_OK"
