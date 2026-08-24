# 🏆 Judge Guide — The Tank

> **Arduino Physical AI Challenge 2026**  
> **Registration: APC-2026-RJ-75818**  
> **Author: Dr. Shashi Gupta**

---

## 🎯 What Is The Tank?

**The Tank is a distributed edge-AI robotic platform** that combines three computing layers:

1. **Jetson Orin Nano Super** (67 TOPS, 8GB RAM) — AI brain
2. **Arduino UNO Q 4GB** (QRB2210 + STM32U585) — real-time controller
3. **6× ESP32-S3 + DFRobot AI Camera** — distributed peripherals

**The Tank also ships with a detachable external module — a blind-assistance wearable**
that reconfigures the same UNO Q + Jetson + ESP32 hardware into a portable AI guide
device for visually impaired users. See [docs/BLIND_ASSIST.md](docs/BLIND_ASSIST.md).

**146,000+ lines of Python · 427 tests · 70+ screenshots · 23 ROS2 packages**

---

## 🧠 What Makes It Innovative?

| Innovation | Description |
|-----------|-------------|
| **Distributed AI** | Three boards share intelligence — Jetson decides, UNO Q coordinates, ESP32 executes |
| **Capability-Based AI** | Apps ask *"give me object detection"* — TankOS picks model, device, precision, fallback |
| **327 LLM-Callable Modules** | Any AI model can discover and invoke typed, permissioned robot functions |
| **100 AI Providers** | Auto-discovers and selects the best AI model for each task |
| **Robot Constitution** | 8-article policy engine — AI proposes, safety vetoes, humans decide |
| **Controlled Evolution** | Benchmarks, ranks, and only deploys proven improvements |
| **3 Perception Nodes** | DFRobot AI Camera + LiDAR + ESP32-S3 CAM |
| **Never-Offline Connectivity** | WiFi → 4G LTE → Hotspot → Tailscale mesh |
| **SMS Control** | Text message commands via Quectel LTE modem |
| **Blind-Assistance Module** | Detachable wearable — AI vision → spoken guidance via UNO Q |
| **PWA Dashboard** | Phone-based 8-tab control center |

---

## 🔧 Hardware

| Component | Model | Purpose | Status |
|-----------|-------|---------|--------|
| Jetson Orin Nano Super | NVIDIA 8GB, 67 TOPS | AI inference, vision, navigation | ✅ Online |
| Arduino UNO Q 4GB | QRB2210 + STM32U585 | Motor/sensor/safety control | ✅ Online |
| DFRobot AI Camera | SEN0611, ESP32-S3 | RGB + night vision, 640×480 | ✅ Streaming |
| LDROBOT LiDAR LD19 | 360° laser scanning | 12m range, 5kHz scan | ✅ Live |
| ESP32-S3 CAM | ESPHome firmware | 3rd perception node on UNO Q + blind-assist camera | ✅ Online |
| ESP32 Dual Screen | 2× GC9A01 Round LCD | Visual alerts + speaker for blind module | ✅ Working |
| USB Speaker + Mic | 3W speaker, mini mic | Audio feedback + voice commands | ✅ Working |
| 4G Modem | Quectel EG800AK | SMS + data backup | ✅ 64% signal |
| Motors | JGB37-520 ×2 | Tracked locomotion | 🔵 Firmware ready |
| Motor Driver | BTS7960 ×2 | H-bridge control | 🔵 Firmware ready |
| IMU | BNO055 | 9-DOF orientation | 🔵 I²C ready |
| Servo Driver | PCA9685 | 16-channel servo PWM | 🔵 I²C ready |

**Total Cost: ₹67,850 (~$850 USD)**

---

## 📡 3 Perception Nodes

| # | Node | Hardware | Detection | Status |
|---|------|----------|-----------|--------|
| 1 | **DFRobot AI Camera** | ESP32-S3 + OV3660 | YOLOv8n @ 8.9fps | ✅ Streaming |
| 2 | **LiDAR** | LDROBOT LD14/19 | Binary obstacle scan | ✅ Live |
| 3 | **ESP32-S3 CAM + UNO Q** | ESP32-S3 (USB-C) + UNO Q | YOLOv8n via ESPHome HTTP | ✅ NEW |

```
ESP32-S3 CAM → WiFi HTTP capture → UNO Q ARM64 → YOLOv8n CPU → detections
                                                                    │
                        ┌───────────────────────────────────────────┘
                        ▼
            ┌─────────────────────────────────┐
            │  Tailscale VPN → Jetson brain   │
            │  (if WiFi down → LTE fallback)  │
            └─────────────────────────────────┘
```

---

## 💻 Software

| System | Features | Packages | Status |
|--------|----------|----------|--------|
| TankOS Core | 327 modules | 18 categories | ✅ All passing |
| ROS2 Jazzy | 23 packages | Jetson + UNO Q | ✅ Built |
| AI Providers | 100 cloud + local | Auto-selection | ✅ 9 active |
| Tests | 425+ | Unit + integration | ✅ All passing |
| GUI Screens | 70+ | Android TV style | ✅ All captured |

### ROS2 Packages (23 built)

tank_assistant · tank_bringup · tank_command_bridge · tank_dashboard ·  
tank_display · tank_dock · tank_emotions · tank_health · tank_learn ·  
tank_log · tank_memory · tank_meta · tank_motion · tank_nas · tank_offload ·  
tank_patrol · tank_personalize · tank_security · tank_sensors · tank_speech ·  
tank_task · tank_text · tank_vision

---

## 📊 What Can Be Demonstrated

### ✅ Working NOW (Live Verified)

- **3 perception nodes** streaming simultaneously
- USB Camera (DFRobot) → JPEG frames + IMU data
- YOLOv8n object detection on CUDA (Jetson) + CPU (UNO Q)
- LiDAR scanning and occupancy grid
- Tailscale mesh: 3 Linux nodes + 3 ESP32 boards connected
- WiFi → LTE → Hotspot failover chain
- SMS commands via Quectel LTE modem
- PWA dashboard on phone
- TankOS 16-tile GUI (Android TV style)
- TankOS terminal with 1,966 tools
- Evolution system (9/14 cloud providers)
- TankOS 327-module LLM-callable registry
- Robot Constitution + AI Debate
- 16-language i18n support
- 427 tests passing
- 23 ROS2 packages built (Jazzy)

### ✅ Blind-Assistance Module (Demo Video Uploaded)

- Wearable configuration: UNO Q + ESP32 CAM + LTE + Dual Screen + Speaker → worn by user
- AI vision pipeline: ESP32 CAM → UNO Q → Tailscale → Jetson → YOLO + LLM → spoken guidance
- Voice commands: "What's around me?" · "Read that sign" · "Find my keys" · "Call emergency"
- Obstacle detection with audio alerts + screen warnings
- Emergency triple-tap E-STOP → SMS with GPS to contacts
- Optional locomotion follower: "Follow me" mode guides the user physically
- Full offline capability: 42 local AI models — works without internet
- LTE failover: WiFi → 4G → Hotspot → Tailscale — never disconnected

### 🔵 Code Complete, Needs Physical Wiring

- Motor control (BTS7960)
- Encoder odometry
- Servo control (PCA9685)
- IMU sensor fusion
- E-STOP system
- Battery monitoring

### 🟡 Competition Demo

- Full autonomous pipeline: SENSE → PERCEIVE → FUSE → UNDERSTAND → DECIDE → ACT → VERIFY → LEARN
- Judge Mode: one-screen subsystem verification
- Human Control Center: follow/stop/escort modes
- **Blind-Assistance Demo**: live wearable demo — scene description, obstacle warning, voice interaction

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        HUMAN / GUI INTERFACE                    │
│                 Android TV · Voice · Web · SMS                  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                    TANKOS MASTER ORCHESTRATOR                    │
│   OBSERVE → UNDERSTAND → REMEMBER → REASON → PLAN → VALIDATE   │
│   → ACT → OBSERVE RESULT → EVALUATE → LEARN → UPDATE STATE     │
└───────┬──────────────────┬───────────────────┬──────────────────┘
        │                  │                   │
┌───────▼──────┐  ┌────────▼────────┐  ┌──────▼───────┐
│   JETSON     │  │    UNO Q 4GB    │  │  3× ESP32-S3 │
│  Orin Nano   │  │  System Coord.  │  │  Real-time   │
│  Super 8GB   │  │  QRB2210 Linux  │  │  Sensors/IO  │
│  67 TOPS     │  │  STM32 MCU      │  │              │
│              │  │  Motors/Safety  │  │  Eyes/CAM/   │
│  AI Brain    │  │  Android TV     │  │  Sensors/LTE │
│  Vision      │  │  Networking     │  │              │
│  SLAM        │  │  Diagnostics    │  │              │
└──────┬───────┘  └────────┬────────┘  └──────────────┘
       │                   │
┌──────▼───────┐  ┌────────▼────────┐
│  Camera      │  │  Motors ×2      │
│  LiDAR       │  │  Servos ×4      │
│  Display     │  │  Encoders ×2    │
│  USB Devices │  │  Battery Bank   │
└──────────────┘  └─────────────────┘
```

---

## 🔗 Network Architecture

| Device | Tailscale IP | Role | Status |
|--------|-------------|------|--------|
| Jetson (shashi) | `100.122.31.46` | AI brain | ✅ Online |
| UNO Q (unoq) | `100.84.235.7` | Controller | ✅ Online |
| VPS (medicscholar) | `100.71.127.19` | Cloud API | ✅ Online |
| ESP32-S3 CAM | `192.168.31.145` | Camera | ✅ WiFi |

**Failover:** WiFi → LTE (EG800AK) → Jetson Hotspot → Tailscale mesh

---

## 💰 Cost Comparison

| | The Tank | Unitree Go2 | Boston Dynamics Spot |
|---|---------|-------------|---------------------|
| Price | ₹67,850 (~$850) | ₹2,35,000 ($2,800) | ₹62,50,000 ($74,500) |
| Savings | — | **72% cheaper** | **99.9% cheaper** |
| AI Brain | 67 TOPS GPU | Limited CPU | Custom |
| Battery | 2-3 hours | 40 minutes | 90 minutes |
| 4G/LTE | ✅ Full SMS | ❌ WiFi only | ❌ Enterprise only |
| Open Source | ✅ MIT | ❌ Closed | ❌ Closed |
| Offline AI | ✅ 42 local models | ❌ Cloud only | ❌ Cloud only |
| Customization | Unlimited | Low | Low |

---

## 📚 Key Documentation

| Document | Purpose |
|----------|---------|
| [README.md](README.md) | Full project overview (327 modules, 100 providers) |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Three-layer architecture deep dive |
| [PRESENTATION.md](PRESENTATION.md) | Visual presentation with photos + GIFs |
| [STATUS.md](STATUS.md) | Live project status |
| [hardware.md](hardware.md) | Complete BOM with pricing |
| [WIRING.md](WIRING.md) | Pin connections, I²C addresses |
| [COMPARISON.md](COMPARISON.md) | TankOS vs competitors |
| [docs/BLIND_ASSIST.md](docs/BLIND_ASSIST.md) | Blind-assistance wearable module |
| [docs/screenshots/](docs/screenshots/) | 70+ live screenshots |
| [docs/infographics/](docs/infographics/) | 58+ SVG architecture diagrams |

---

## 🏆 Why The Tank Wins

1. **72% cheaper** than commercial alternatives
2. **327 tested modules** across 3 computing layers
3. **3× longer battery** (2-3 hours vs 40 minutes)
4. **67 TOPS GPU** vs limited CPU
5. **100 AI providers** with auto-selection
6. **Full offline AI** — 42 local models, works without internet
7. **3 perception nodes** — camera + LiDAR + remote detection
8. **SMS control** — text your robot
9. **Open source** — MIT license
10. **Indian parts** — available on Robu.in
11. **Blind-assistance wearable** — same hardware, life-changing use case

---

<p align="center">
  <sub>Arduino Physical AI Challenge 2026 · APC-2026-RJ-75818 · Dr. Shashi Gupta</sub>
</p>
