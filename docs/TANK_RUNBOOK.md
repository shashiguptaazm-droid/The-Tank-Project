
---

## 📷 USB Video Camera (No WiFi Required)

### DFRobot AI Camera v1.1 — USB Serial Video Stream

**Problem:** WiFi drops caused intermittent video loss.
**Solution:** New firmware streams JPEG frames over USB serial — no WiFi needed.

### Firmware: USBVideoCamera.ino
- **Location:** firmware/usb_video_camera/USBVideoCamera.ino
- **Protocol:** USB Serial @ 921600 baud
- **Resolution:** VGA 640×480 (default), up to XGA 1024×768
- **Features:** Frame capture, continuous streaming, IMU data, LED control

### Serial Commands (Jetson → Camera):
| Command | Response | Description |
|---------|----------|-------------|
| SNAP | FRAME:640:480:10210 + JPEG | Single frame capture |
| STREAM | OK:Streaming started | Continuous streaming |
| STOP | OK:Streaming stopped | Stop streaming |
| RES 8 | OK:Resolution set to VGA | Change resolution |
| IMU | IMU:ax:ay:az:gx:gy:gz | IMU data |
| STATUS | STATUS:frames=N streaming=0 | Camera status |
| LED 1 | OK:LED ON | Toggle LED |
| HELP | COMMANDS:... | List commands |

### Frame Protocol:
1. Host sends: `SNAP\n`
2. Camera responds: `FRAME:width:height:datasize\n`
3. Camera sends: `<JPEG binary data>`
4. Camera terminates: `\n`

### Python Capture Script:
```bash
# Single capture
python3 ~/The-Tank-Project/firmware/usb_video_camera/tank_usb_camera.py

# Save multiple frames
python3 ~/The-Tank-Project/firmware/usb_video_camera/tank_usb_camera.py save 10
```

### GUI Viewer:
```bash
python3 ~/Desktop/tank_camera_usb.py
```

### Verified Working:
- ✅ USB serial connection on /dev/ttyACM0
- ✅ Frame capture: 10210 bytes (valid JPEG)
- ✅ 640×480 resolution
- ✅ 921600 baud USB serial
- ✅ No WiFi dependency
- ✅ IMU data available (QMI8658)

### Flash Command:
```bash
cd ~/The-Tank-Project/firmware/dfrobot_camera
python3 -m esptool --port /dev/ttyACM0 --baud 460800 write_flash \
  0x0 USBVideoCamera.ino.bootloader.bin \
  0x8000 USBVideoCamera.ino.partitions.bin \
  0x10000 USBVideoCamera.ino.bin
```

