
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


---

## 📱 Mobile Command Center (v2.0)

### Architecture


### Mobile Access Methods
| Method | URL/Contact | Features |
|--------|-------------|----------|
| 🌐 PWA Dashboard | http://100.71.127.19:8891 | Full control, 8 tabs |
| 📱 Telegram Bot | @tankos_bot | Alerts, commands, photos |
| 💬 SMS Gateway | Send SMS to SIM card | Remote commands |
| 🤖 AI Chat | Via any method above | Natural language commands |

### PWA Dashboard Tabs
1. 🏠 Dashboard — System status, quick actions, alerts
2. 📷 Camera — USB video feed, capture, stream, save
3. 🎮 Drive — Joystick, D-pad, servo controls, speed slider
4. 📡 Sensors — IMU, distance, temp, light, sound, voltage
5. 🧠 AI Chat — Natural language conversation with TankOS
6. 🔔 Alerts — Real-time alert feed
7. 💬 SMS — Send/receive SMS, broadcast alerts
8. 🗺️ LiDAR — Radar view of environment

### SMS Commands
| Command | Description |
|---------|-------------|
| STATUS | Full robot status |
| HELP | List all commands |
| CAMERA | Capture photo |
| MOVE F/B/L/R | Move direction |
| STOP | Emergency stop |
| WHERE | Current position |
| BATTERY | Power status |
| SCAN | LiDAR scan |
| AI <msg> | Chat with AI |
| Any text | AI processes it |

### AI Powers
- Local LLM (Phi-3 or TinyLlama) for offline response
- Cloud AI fallback (OpenRouter, Groq, etc.)
- Automatic threat detection and alerts
- Natural language command processing
- Camera-based object detection
- Smart response formatting for SMS (160 chars)

### Running Services
| Service | Port | Status |
|---------|------|--------|
| Tank Mobile API | 8090 | Running (Jetson) |
| nginx proxy | 8891 | Running (VPS) |
| SMS Gateway | /dev/ttyUSB2 | Active |
| Telegram Bot | API | Active (with token) |
| WebSocket | /ws | Real-time |

### Install Telegram Bot
1. Message @BotFather on Telegram
2. Create new bot: /newbot → TankOS
3. Get token
4. Set env: export TANK_TELEGRAM_TOKEN=your_token
5. Get chat ID: message bot, then visit https://api.telegram.org/bot<TOKEN>/getUpdates

### Open on Phone
http://100.71.127.19:8891
Add to Home Screen for PWA install

