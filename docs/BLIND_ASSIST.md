# 🦯 Tank External Module — Blind Assistance System

> **Arduino Physical AI Challenge 2026 · APC-2026-RJ-75818**
> **Author: Dr. Shashi Gupta**
> **Use Case:** AI-powered wearable assistive device for the visually impaired
> **Demo Video:** Uploaded August 2026

---

## 🎯 What This Module Does

The **Tank Blind-Assistance Module** is a wearable, battery-powered external unit that
plugs into the **Arduino UNO Q** and provides real-time AI vision assistance to blind
and visually impaired users. It's a detachable "external module" that extends the
Tank's distributed-AI architecture into a portable, human-worn form factor.

The module captures the user's surroundings through an ESP32 camera, streams
it over LTE/WiFi through the UNO Q, sends it to the Jetson AI brain or cloud
inference via Tailscale VPN, and provides spoken feedback through a speaker and
visual alerts on dual LCD screens.

### Core Features

| Feature | How It Works |
|---------|-------------|
| **Real-time scene description** | ESP32 CAM → UNO Q → Tailscale → Jetson/Cloud AI → spoken output |
| **Obstacle detection & warning** | YOLOv8n detects obstacles, LiDAR measures distance → audio alert |
| **Face recognition** | Recognizes known people → speaks their name |
| **Text reading** | OCR on signs, documents → reads aloud |
| **Navigation assist** | "Door ahead, 3 meters" · "Stairs going down, 5 steps" |
| **Object finding** | "Where are my keys?" → AI scans and guides user |
| **Emergency alert** | Triple-tap → SMS with GPS to emergency contacts |
| **Physical following** | Optional locomotion module — AI assistant physically escorts user |
| **Fully offline capable** | 42 local AI models on Jetson — works without internet |
| **Always online** | WiFi → 4G LTE (Quectel EG800AK) → Hotspot → Tailscale mesh |

---

## 🧱 Hardware Components

### Core Module (Worn by User)

| Component | Model | Qty | Price (₹) | Purpose |
|-----------|-------|-----|-----------|---------|
| **Arduino UNO Q 4GB** | QRB2210 + STM32U585 | 1 | 12,500 | Central processor, AI routing |
| **ESP32-S3 CAM** | ESPHome, WiFi | 1 | 600 | Wearable camera, captures surroundings |
| **ESP32 Dual Screen** | 2× 1.28" Round LCD (GC9A01) | 1 | 500 | Visual alerts + speaker output |
| **USB LTE Modem** | Quectel EG800AK | 1 | 2,500 | 4G cellular internet |
| **Power Bank** | 10,000 mAh USB-C PD | 1 | 1,200 | Portable power (8+ hours) |
| **Speaker** | 3W mini speaker (3.5mm/USB) | 1 | 200 | Audio feedback |
| **Microphone** | USB mini mic | 1 | 300 | Voice commands |
| **Wearable harness** | Belt clip + shoulder mount | 1 | 500 | Ergonomic wear |
| **Jetson Orin Nano Super** | 67 TOPS, 8GB | 1 | 25,000 | AI inference brain (home/backpack) |
| **LDROBOT LiDAR LD19** | 360°, 12m | 1 | 4,500 | Obstacle scanning (optional) |
| **Locomotion base** | Tracked chassis + motors | 1 | 8,000 | Physical following (optional) |
| **Cables & connectors** | USB-C, jumper wires | — | 500 | |
| **Module Total** | | | **₹56,300** | |

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    BLIND USER (WEARABLE MODULE)                   │
│                                                                  │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────────────┐  │
│  │ ESP32-S3    │    │ UNO Q 4GB    │    │ ESP32 Dual Screen  │  │
│  │ CAMERA      │───▶│ (QRB2210 +   │───▶│ + Speaker          │  │
│  │ (chest/     │    │  STM32U585)  │    │ (visual + audio    │  │
│  │  shoulder)  │    │              │    │  feedback)         │  │
│  └─────────────┘    │ ┌──────────┐ │    └────────────────────┘  │
│                     │ │USB LTE   │ │                             │
│  ┌─────────────┐    │ │Modem     │ │    ┌────────────────────┐  │
│  │ Power Bank  │    │ └──────────┘ │    │ Microphone         │  │
│  │ 10,000 mAh  │────│              │◀───│ (voice commands)   │  │
│  └─────────────┘    └──────┬───────┘    └────────────────────┘  │
│                            │                                     │
└────────────────────────────┼─────────────────────────────────────┘
                             │
                    Tailscale VPN Mesh
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼───────┐   ┌───────▼───────┐   ┌───────▼───────┐
│   JETSON      │   │   VPS CLOUD   │   │  EMERGENCY    │
│ Orin Nano     │   │ medicscholar  │   │  CONTACTS     │
│ Super 8GB     │   │               │   │               │
│ 67 TOPS       │   │ Cloud AI      │   │ SMS alerts    │
│               │   │ fallback      │   │ GPS location  │
│ Local AI      │   │               │   │               │
│ YOLO · LLM    │   │ 100 providers │   │               │
│ Whisper · OCR │   │               │   │               │
└───────────────┘   └───────────────┘   └───────────────┘
        │
┌───────▼───────┐
│  LOCOMOTION   │  (optional)
│  MODULE       │
│  Tracked base │
│  Follow mode  │
│  Obstacle     │
│  avoidance    │
└───────────────┘
```

### Visual Diagrams

| # | Diagram | Description |
|---|---------|-------------|
| 60 | [Front View](../assets/infographics/60_blind_assist_front.svg) | Person wearing all 7 components — chest CAM, belt UNO Q, shoulder screens+speaker, hip LTE+power bank, collar mic, E-STOP |
| 61 | [Side View](../assets/infographics/61_blind_assist_side.svg) | Profile walking pose with component depth map, exploded detail panel, and ₹3,800 BOM |
| 62 | [Data Pipeline](../assets/infographics/62_blind_assist_pipeline.svg) | SENSE → ROUTE → ANALYZE → RETURN → FEEDBACK with full latency breakdown |
| 63 | [3D Isometric](../assets/infographics/63_blind_assist_3d_isometric.svg) | **Animated** 3D view with glowing signal paths, data packet particles, and Jetson cloud callout |
| 64 | [Animated Flow](../assets/infographics/64_blind_assist_animated_flow.svg) | **Animated** step-by-step pipeline: SENSE(5ms) → ROUTE(30ms) → ANALYZE(530ms) → RETURN(30ms) → FEEDBACK(200ms) = ~800ms |
| 65 | [Exploded 3D](../assets/infographics/65_blind_assist_exploded_3d.svg) | All 10 components disassembled in 3D with connector paths, labels, and complete BOM |
| 66 | [Demo Sequence](../assets/infographics/66_blind_assist_demo_sequence.svg) | **Animated** 14-step competition demo with live scene visualization, YOLO output, Phi-3 reasoning, and spoken output panels |

### Data Flow (Frame → Feedback)

```
1. SENSE     ESP32 CAM captures 640×480 JPEG @ 8.9fps
2. SEND      UNO Q receives via WiFi (USB-C)
3. ROUTE     UNO Q sends to Jetson over Tailscale (or LTE fallback)
4. ANALYZE   Jetson: YOLOv8n (objects) + OCR (text) + Face recognition
5. REASON    TankOS AI Executive: "User is approaching stairs. Alert."
6. RETURN    Jetson → UNO Q: structured analysis + audio text
7. SPEAK     UNO Q → Speaker: "⚠️ Stairs ahead, 3 meters. Turn left."
8. DISPLAY   ESP32 Dual Screen: visual warning + direction arrow
9. FOLLOW    (optional) Locomotion module adjusts position
```

---

## 🔌 Connection Diagram

### UNO Q Pin Connections

```
                    ┌─────────────────────────────────────┐
                    │           ARDUINO UNO Q 4GB         │
                    │                                     │
ESP32-S3 CAM ──────│ USB-C (data)    USB-A ────── Jetson │
(chest camera)     │                                     │
                    │                                     │
ESP32 Dual  ───────│ USB-C (display) USB-A ────── LTE    │
Screen+Spkr        │                   Modem     Modem   │
                    │                                     │
Power Bank ────────│ USB-C (PD)       I²C ─────── LiDAR  │
(10,000mAh)        │                   (A4/A5)   (opt.)  │
                    │                                     │
Microphone ────────│ USB-A (audio)    D9 ──────── E-STOP │
                    │                                     │
                    │ STM32U585:                          │
                    │ D6/D7 ──────── Left Motor (BTS7960) │
                    │ D4/D5 ──────── Right Motor (BTS7960)│
                    │ D2/D3 ──────── Left Encoder         │
                    │ D18/D19 ────── Right Encoder        │
                    └─────────────────────────────────────┘
```

### USB Port Allocation

| UNO Q Port | Device | Purpose |
|-----------|--------|---------|
| USB-C (power input) | Power Bank 10,000mAh | Main power |
| USB-C (data 1) | ESP32-S3 CAM | Vision input |
| USB-C (data 2) | ESP32 Dual Screen + Speaker | Feedback output |
| USB-A 1 | Quectel EG800AK LTE Modem | Internet |
| USB-A 2 | USB Microphone | Voice commands |
| USB-A 3 | Jetson Orin Nano | AI brain link |
| USB-A 4 | LiDAR LD19 (optional) | Obstacle scanning |

---

## 📡 Network Architecture (Wearable Context)

| Node | Tailscale IP | LAN IP | Role |
|------|-------------|--------|------|
| UNO Q (wearable) | `100.84.235.7` | DHCP | System coordinator |
| Jetson (home/backpack) | `100.122.31.46` | `192.168.31.74` | AI inference |
| VPS (cloud) | `100.71.127.19` | public | Cloud AI fallback |
| ESP32-S3 CAM | — | `192.168.31.145` | Camera (WiFi → UNO Q) |

### Connectivity Fallback Chain

```
WiFi (home/office) → 4G LTE (Quectel, outdoor) → Jetson Hotspot → Tailscale mesh
```

The LTE modem ensures the blind user **never loses AI assistance** — even outdoors
with no WiFi. The Quectel EG800AK supports Indian 4G bands (Airtel/Jio/Vi) and
SMS for emergency alerts.

---

## 🧠 AI Pipeline

### Local Models (Jetson — works offline)

| Model | Size | Task | Latency |
|-------|------|------|---------|
| YOLOv8n | 6 MB | Object detection (80 classes) | ~30ms |
| Phi-3 Mini 4K | 2.3 GB | Scene description, reasoning | ~500ms |
| Whisper base | 150 MB | Voice command recognition | ~200ms |
| Piper TTS | 50 MB | Text-to-speech output | ~100ms |
| OpenCV DNN | — | Face recognition | ~100ms |
| Tesseract OCR | — | Text reading | ~200ms |

### Cloud Providers (when online)

| Provider | Model | Use Case |
|----------|-------|----------|
| Groq | LLaMA 3 70B | Detailed scene narration |
| Gemini | Gemini Flash | Multi-modal (image + text) |
| OpenRouter | Claude 3 Haiku | Complex reasoning, navigation |
| Mistral | Mistral Large | Emergency assessment |

### Scene Analysis Prompts

The UNO Q sends JPEG frames + context to the AI with structured prompts:

```
"You are assisting a blind person. Describe what you see in this image.
Focus on: obstacles (stairs, poles, vehicles), people (known/unknown),
text (signs, door numbers), and actionable guidance.
Format: [OBSTACLES] ... [PEOPLE] ... [TEXT] ... [GUIDANCE] ..."
```

---

## 🗣️ Voice Commands

The user speaks to the USB microphone; Whisper transcribes; the AI acts.

| Command | Response |
|---------|----------|
| "What's around me?" | Describes current scene |
| "Read that sign" | OCR → reads text aloud |
| "Who's that?" | Face recognition → name |
| "Find my keys" | Object search mode |
| "Take me to the door" | Navigation guidance |
| "Call emergency" | SMS to emergency contacts with GPS |
| "Follow me" | Activates locomotion follower |
| "Stop" | Halts locomotion |
| "Battery status" | Reports remaining runtime |
| "What time is it?" | Speaks current time |

---

## 🚨 Emergency System

### Triple-Tap E-STOP

Three quick presses of the hardware E-STOP button (connected to UNO Q pin D9):

1. Sends SMS to emergency contacts: "🚨 EMERGENCY: Blind user needs help. GPS: <lat>, <lng>"
2. Activates speaker alarm at max volume
3. Flashes ESP32 screens red
4. Logs location + timestamp to Jetson

### SMS Recipients

Configured in `~/.blind_assist_contacts`:

```
+91-XXXXXXXXXX  # Primary emergency contact
+91-XXXXXXXXXX  # Family member
+91-XXXXXXXXXX  # Doctor/caregiver
```

---

## 🚶 Locomotion Module (Optional)

For users who want the AI assistant to physically walk with them:

| Component | Model | Function |
|-----------|-------|----------|
| Chassis | Tracked robot base | Mobility |
| Motors | JGB37-520 ×2 | Differential drive |
| Driver | BTS7960 ×2 | Motor control |
| Battery | 4S Li-ion 5000mAh | Power |
| Mode | "Follow me" | Tracks user via camera + LiDAR |

The locomotion module uses the **same Tank base platform** — the blind-assistance
module is simply the **Tank reconfigured for a human use case**, demonstrating
the platform's versatility.

### Follow Modes

| Mode | Behavior |
|------|----------|
| **Escort** | Walks alongside, keeping 1m distance |
| **Lead** | Walks ahead, scanning for obstacles, speaking guidance |
| **Follow** | Walks behind user, carrying items |
| **Patrol** | Independently scans area, reports hazards |
| **Stationary** | Stays put, acts as fixed camera + speaker |

---

## 📦 Setup Instructions

### Quick Start

```bash
# 1. Clone and enter the project
cd "/root/the tank project"

# 2. Run the blind-assistance setup script
bash scripts/setup_blind_assist.sh

# 3. Configure emergency contacts
nano ~/.blind_assist_contacts

# 4. Start the module
python3 -m tank.blind_assist.main
```

### What the setup script does

1. Installs dependencies: OpenCV, YOLOv8, Whisper, TTS, OCR
2. Downloads YOLOv8n model weights
3. Flashes ESP32-S3 CAM with ESPHome firmware
4. Configures Tailscale mesh between UNO Q ↔ Jetson ↔ VPS
5. Tests LTE modem connectivity (AT commands)
6. Calibrates microphone and speaker
7. Runs a smoke test: capture → detect → speak

### Manual Component Setup

#### ESP32-S3 CAM (Camera Firmware)

```bash
# Flash ESPHome firmware to ESP32-S3 CAM
cd firmware/esp32_cam
esptool.py --port /dev/ttyUSB0 --baud 460800 write_flash \
  0x0 bootloader.bin \
  0x8000 partitions.bin \
  0x10000 esp32_cam_esphome.bin

# Verify
curl http://192.168.31.145/capture -o /tmp/test.jpg
file /tmp/test.jpg  # Should report: JPEG image data
```

#### ESP32 Dual Screen (Display + Speaker Firmware)

```bash
# Flash to second ESP32-S3 with dual-screen firmware
cd firmware/esp32_dual_screen
esptool.py --port /dev/ttyUSB1 --baud 460800 write_flash \
  0x0 bootloader.bin \
  0x8000 partitions.bin \
  0x10000 esp32_dual_screen.bin

# Test: send expression command
echo '{"eyes":"alert","color":"red","text":"OBSTACLE","speak":"Watch out"}' \
  > /dev/ttyUSB1
```

#### LTE Modem Setup

```bash
# Verify modem detected
ls /dev/ttyUSB2 /dev/ttyUSB3

# Test connectivity
mmcli -L                              # List modems
mmcli -m 0 --simple-connect=apn=airtelgprs.com  # Connect
mmcli -m 0 --command="AT+CSQ"         # Signal strength
```

---

## 🏃 Running the Module

### Full System Start

```bash
# Terminal 1: Start Jetson AI brain (if not already running)
ssh jetson "cd /opt/tank && python3 -m tank.ai_server"

# Terminal 2: Start blind-assistance on UNO Q
cd "/root/the tank project"
python3 -m tank.blind_assist.main --mode full

# Terminal 3 (optional): Locomotion follower
python3 -m tank.blind_assist.locomotion --mode follow
```

### Modes

```bash
python3 -m tank.blind_assist.main --mode full        # All features
python3 -m tank.blind_assist.main --mode vision-only # Camera + AI only
python3 -m tank.blind_assist.main --mode nav-only    # Navigation only
python3 -m tank.blind_assist.main --mode read-only   # OCR/reading only
python3 -m tank.blind_assist.main --mode emergency   # Emergency beacon only
```

### Verification

```bash
# Smoke test: should capture frame, detect objects, speak result
python3 -c "
from tank.blind_assist.main import BlindAssist
ba = BlindAssist(mode='vision-only')
result = ba.process_one_frame()
print(f'Objects: {result.objects}')
print(f'Guidance: {result.guidance}')
print(f'Audio: {result.audio_text}')
"
```

---

## 📊 Competition Demo Flow (Blind-Assistance)

```
1. UNO Q boots from power bank → BlindAssist mode
2. ESP32 CAM starts streaming → "Camera active"
3. LTE modem connects → "Internet ready"
4. Tailscale mesh established → "AI brain connected"
5. User speaks: "What's around me?"
6. ESP32 CAM captures frame → sends over Tailscale
7. Jetson YOLOv8n: detects person, door, chair, stairs
8. Phi-3: "You are in a hallway. Door ahead at 5 meters.
   Person approaching from left. Chair to your right."
9. UNO Q → Speaker: "Door ahead, five meters. Person approaching from left."
10. ESP32 screens: door icon + person icon + distance indicators
11. User: "Take me to the door"
12. Locomotion module activates Follow mode → guides user
13. User reaches door → "You have arrived at the door"
14. Demo complete — all systems verified
```

---

## 🧪 Testing

```bash
# Unit tests
python3 -m pytest tank/blind_assist/tests/ -v

# Integration tests
python3 scripts/test_blind_assist.py --integration

# Hardware loop test (requires physical devices)
python3 scripts/test_blind_assist.py --hardware

# End-to-end: capture → detect → speak
python3 scripts/test_blind_assist.py --e2e
```

---

## 📈 Why This Shows UNO Q as Primary

The blind-assistance module **proves the UNO Q is the primary device** because:

1. **All peripherals connect through UNO Q** — camera, screen, speaker, mic, LTE
2. **UNO Q coordinates the full pipeline** — SENSE → ROUTE → ANALYZE → SPEAK
3. **UNO Q handles safety** — E-STOP, emergency SMS, battery monitoring
4. **UNO Q manages connectivity** — WiFi ↔ LTE failover, Tailscale routing
5. **Jetson is a compute resource** — the UNO Q decides when and how to use it
6. **UNO Q continues without Jetson** — falls back to cloud AI over LTE if Jetson unreachable
7. **User interaction is UNO Q-native** — voice in, speech out, all through UNO Q

---

## 📸 Photos

Hardware photos from the demo setup (August 23, 2026):

- `20260823_235016.jpg` — Module with UNO Q, ESP32 CAM, LTE modem, dual screen
- `20260823_235019.jpg` — Full wearable configuration

---

<p align="center">
  <sub>The Tank · Blind-Assistance External Module · APC-2026-RJ-75818 · Dr. Shashi Gupta</sub>
</p>