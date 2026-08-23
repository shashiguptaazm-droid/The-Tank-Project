#!/bin/bash
# Flash Waveshare ESP32-S3-LCD-1.28 board
# Usage: ./flash.sh /dev/ttyUSBx
PORT=${1:-/dev/ttyUSB4}
echo "Flashing Waveshare Eyes firmware to $PORT"
echo "Plug in the Waveshare board via USB-C, then run:"
echo "  ./flash.sh /dev/ttyUSBx"
echo ""
echo "Press BOOT button on board, then RESET, then run this."
python3 -m esptool --chip esp32s3 --port $PORT --baud 921600 \
  --before usb-reset --after hard-reset write-flash -z \
  0x0 WaveshareEyes.ino.bootloader.bin \
  0x8000 WaveshareEyes.ino.partitions.bin \
  0x10000 WaveshareEyes.ino.bin
