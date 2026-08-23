# 🪖 The Tank — Arduino Physical AI Challenge

<p align="center">
  <img src="https://img.shields.io/badge/REGISTRATION-APC--2026--RJ--75818-red?style=for-the-badge&labelColor=0F172A" alt="Registration ID">
</p>

<p align="center">
  <b>An autonomous AI robotic platform with cognitive architecture</b><br>
  <sub>NVIDIA Jetson Orin Nano · Arduino UNO Q · ESP32-S3 Swarm · ROS2 · TankOS</sub>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/competition-Arduino_Physical_AI_Challenge-00979D?style=flat-square" alt="Competition">
  <img src="https://img.shields.io/badge/ai-Jetson_Orin_Nano-76B900?logo=nvidia&logoColor=white&style=flat-square" alt="Jetson">
  <img src="https://img.shields.io/badge/controller-UNO_Q-00979D?logo=arduino&logoColor=white&style=flat-square" alt="Arduino">
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License">
</p>

---

## 🎬 Presentation — GIFs & Infographics

<p align="center">
  <img src="assets/gifs/eyes_expressions.gif" width="360" alt="Tank eyes expressions"/>
  <img src="assets/gifs/network_failover.gif" width="320" alt="Network failover"/>
</p>

<p align="center">
  <a href="assets/infographics/fleet_connectivity.svg"><img src="assets/infographics/fleet_connectivity.svg" width="46%" alt="Fleet connectivity"/></a>
  <a href="assets/infographics/hardware_inventory.svg"><img src="assets/infographics/hardware_inventory.svg" width="46%" alt="Hardware inventory"/></a>
</p>

<p align="center">
  <a href="assets/infographics/esp32_boards.svg"><img src="assets/infographics/esp32_boards.svg" width="46%" alt="3 ESP32 boards"/></a>
  <a href="assets/infographics/tankos_architecture.svg"><img src="assets/infographics/tankos_architecture.svg" width="46%" alt="TankOS architecture"/></a>
</p>

> 📄 Docs: [`docs/FLEET_INVENTORY.md`](docs/FLEET_INVENTORY.md) (live device audit) ·
> 📺 **UNO Q → Android TV:** [`docs/UNOQ_ANDROID_TV.md`](docs/UNOQ_ANDROID_TV.md) — TV kiosk, ADB remote, media hub · screenshots in [`docs/screenshots/tv/`](docs/screenshots/tv/)
>
> 🟦 **UNO Q Master Plan:** [`docs/UNOQ_MASTER_PLAN.md`](docs/UNOQ_MASTER_PLAN.md) — 400-item upgrade tracker (top-20 audited) · every feature ships with [`docs/FEATURE_PROOF_TEMPLATE.md`](docs/FEATURE_PROOF_TEMPLATE.md) proof
>
> 🎬 **Presentation:** [`PRESENTATION.md`](PRESENTATION.md) — the full deck with hero banner, hardware wall, fleet map, and screenshots
>
> [`docs/HARDWARE_DEPENDENCIES.md §8`](docs/HARDWARE_DEPENDENCIES.md#8-hardware-photo-gallery) (photo gallery) ·
> [`assets/README.md`](assets/README.md) (media index)


## 1. Project Title

**The Tank** — An Autonomous AI Robotic Platform with Cognitive Architecture

---

## 2. Project Overview

The Tank is an autonomous AI robotic platform built for the **Arduino Physical AI Challenge 2026**. It combines a **NVIDIA Jetson Orin Nano Super** (AI brain, 67 TOPS INT8) with an **Arduino UNO Q** (real-time controller with Qualcomm QRB2210 + STM32U585 MCU) and a network of **ESP32-S3 nodes** (5 distributed peripheral controllers). The platform sees, hears, speaks, and **discovers new capabilities through automated model evaluation** — running a complete 22-system cognitive architecture.

**Registration ID: APC-2026-RJ-75818**

---

## 3. Project Vision

We envision a future where personal robots are not just tools — they're companions that grow, learn, and adapt. The Tank demonstrates that a fully autonomous, emotionally-aware robot is achievable with off-the-shelf components and open-source software. Every interaction makes it smarter. Every day it discovers new capabilities.

---

## 4. Problem Statement

Current personal robots face three critical limitations:

1. **Brittleness** — Single-point-of-failure AI. One API outage and the robot is braindead.
2. **No Learning** — Robots today execute the same commands forever. They never improve.
3. **No Emotional Intelligence** — Robots are cold, transactional, and frustrating to interact with.

The Tank solves all three: multi-provider AI with automatic fallback, daily self-evolution, and a 22-system cognitive architecture that includes emotion, curiosity, metacognition, and personality.

---

## 5. Proposed Solution

A three-board architecture that cleanly separates concerns:

| Board | Role | Why | Photo |
|-------|------|-----|-------|
| **Jetson Orin Nano Super** | AI Brain | 67 TOPS INT8, runs ROS2 Jazzy, llama.cpp, Whisper, YOLOv8n, TankOS GUI | ![Jetson](docs/hardware_photos/1_jeton_orin_nano_super.jpg) |
| **Arduino UNO Q** | Real-time Controller | Qualcomm QRB2210 Linux + STM32U585 MCU for deterministic motor/encoder/I2C | ![Arduino](docs/hardware_photos/2_arduino_uno_q.jpg) |
| **ESP32-S3 ×5** | Distributed Peripheral Nodes | Eyes, hands — each node handles its own domain independently | ![ESP32-S3](docs/hardware_photos/6_esp32_s3_devkitc_1.png) |

They communicate via USB serial at 115200 baud with a compact JSON protocol. The Jetson never touches a motor wire. The Arduino never runs an inference. Clean separation = reliable system.

---

## 6. Key Features

- 🧠 **22-System Cognitive Architecture** — Perception, Attention, Reasoning, Planning, Decision, Learning, Memory, Emotion, Metacognition, and more
- 🔄 **14-Provider AI Brain** with automatic circuit-breaker fallback
- 📅 **Daily Self-Evolution** — learns, discovers new abilities, improves responses
- 🎭 **Emotional Intelligence** — valence/arrousal/dominance emotion model, facial expression on round LCD eyes
- 🗣️ **Voice Interface** — Whisper STT + Piper TTS + openWakeWord
- 👁️ **Multi-Sensor Fusion** — LiDAR, IMU, thermal camera, depth camera, ultrasonic
- 🔒 **Hybrid AI** — local models (llama.cpp) provide primary offline operation; 14 cloud providers are optional fallback/enhancement
- 📱 **TankOS GUI** — 13 full-screen apps on a 7" touchscreen
- 🔧 **400+ CLI Utilities** — diagnostics, calibration, fleet management

---

## 7. Innovation

The Tank's key innovations:

1. **Self-Evolving AI Brain** — The robot runs a daily evolution cycle that discovers new LLM models from 14 provider APIs, tests them, and adds them to its rotation. The system discovers, evaluates, and rotates among available model providers.

2. **Circuit-Breaker Resilience** — Each AI provider has a health state machine (CLOSED → OPEN → HALF_OPEN). Three failures open the circuit; periodic probes test recovery. Zero downtime.

3. **Cognitive Metacognition** — The robot knows when it doesn't know something. Its metacognition system monitors confidence levels and triggers exploration (curiosity engine) when uncertainty is high.

4. **Distributed ESP32 Swarm** — Instead of running everything on one board, the Tank distributes peripheral control across 5 ESP32-S3 nodes. Eyes and hands each have their own microcontroller, reducing latency and wiring complexity.


---

## 8. Feature Status Legend

| Symbol | Meaning |
|--------|---------|
| 🟢 | **Working** — tested and functional |
| 🔵 | **Implemented / Needs Validation** — code exists, needs hardware testing |
| 🟡 | **In Progress** — actively being developed |
| 🔴 | **Planned** — designed but not yet built |

### Current Status

| System | Status | Evidence |
|--------|--------|----------|
| Event Bus | 🟢 | 19/19 tests passing |
| State Machine | 🟢 | Validated transitions |
| Decision Engine | 🟢 | AI→validate→safety→decide pipeline |
| Sensor Fusion | 🔵 | Software implemented; simulation tested |
| Safety System | 🔵 | Software implemented; hardware validation pending |
| Mock Sensors | 🟢 | Simulation mode fully working |
| ESP32 Swarm | 🟢 | 5-node distributed peripheral control |
| SQLite Storage | 🟢 | Event/telemetry logging |
| Terminal Dashboard | 🟢 | Competition-quality display |
| Hardware Registry | 🟢 | 41 components cataloged |
| Full Pipeline | 🔵 | Software implemented; physical hardware integration pending |
| USB Camera Driver | 🔵 | OpenCV code ready, needs hardware |
| LiDAR Driver | 🔵 | rplidar SDK ready, needs hardware |
| Thermal Sensor | 🔵 | MLX90640 I2C driver ready |
| IMU Driver | 🔵 | BNO055 I2C driver ready (via Arduino UNO Q) |
| Servo Control | 🔵 | PCA9685 I2C servo driver ready (via Arduino UNO Q) |
| Linear Actuator | 🔵 | BTS7960 H-bridge ready |
| Finger Control | 🔵 | SG90 servo code ready |
| VPS AI Client | 🔵 | HTTPS+auth+retry ready |
| Tracked Locomotion | 🟡 | Motor firmware implemented; physical validation pending |
| Hand Control | 🟡 | Firmware implemented; physical validation pending |
| Competition Demo | 🔵 | Demo software prepared; hardware validation pending |


## 8. Objectives

| Phase | Objective | Status |
|-------|-----------|--------|
| P1 | Foundation — motion, vision, basic ROS2 | ✅ |
| P2 | Eyes, tracker, SLAM | ✅ |
| P5 | Voice + assistant + memory | ✅ |
| P9 | AI ↔ robot bidirectional bridge | ✅ |
| P11 | TankOS GUI — 13 apps | ✅ |
| P12 | Future expansion — humanoid locomotion, manipulation | 🔴 Planned |
| P13 | Hand dexterity — 5-finger grip, force sensing | 🔄 In Progress |
| P14 | Competition integration + demo | 📋 Planned |

---

## 9. Use Cases

- 🏠 **Home Companion** — Emotional support, voice interaction, daily reminders
- 🔒 **Security Robot** — Patrol routes, intrusion detection, visitor logging
- 🧪 **Lab Assistant** — Object manipulation, instrument reading, data collection
- 🎓 **Education Platform** — Teaching robotics, AI, and cognitive science
- 🏥 **Elderly Care** — Medication reminders, fall detection, companionship

---

## 10. System Overview

```
┌─────────────────────────────────────────────────────┐
│                    TANKOS (GUI)                      │
│  Home · Chat · Camera · Nav · Memory · Security ·   │
│  Patrol · Files · Diagnostics · Developer · Settings │
├─────────────────────────────────────────────────────┤
│                 TANKOS CORE (35 managers)            │
│  EventBus · Vision · Memory · Emotion · Security ·  │
│  Voice · Evolution Bridge · Local LLM · Preload      │
├─────────────────────────────────────────────────────┤
│                   ROS2 HUMBLE (23 packages)          │
│  motion · vision · nav · speech · memory · assistant │
│  security · health · dashboard · meta · display      │
├─────────────────────────────────────────────────────┤
│         Jetson Orin Nano    │   Arduino UNO Q       │
│         (AI inference)      │   (real-time I/O)      │
│         USB serial 115200   │   PWM · I²C · INT      │
└────────────────────┬────────┴───────────┬───────────┘
                     │                    │
              ┌──────┴──────┐      ┌──────┴──────┐
              │ ESP32-S3 ×5 │      │  Sensors    │
              │ Eyes·Hands  │      │ LiDAR·IMU  │
              │ Limbs·Feet  │      │ Camera·Mic  │
              └─────────────┘      └─────────────┘
```

---

## 11. System Architecture

See the full diagrams in [`images/`](images/):

- [`architecture.svg`](images/architecture.svg) — 6-layer stack
- [`cognitive.svg`](images/cognitive.svg) — 22-system cognitive architecture
- [`wiring.svg`](images/wiring.svg) — full pinout schematic

---

## 12. AI Architecture

```
Perception → Attention → Reasoning → Planning → Decision → Action
     ↑                                                    │
     └──────── Memory ← Learning ← Reflection ←──────────┘
                    │
               Emotion · Metacognition · Curiosity · Personality
```

22 cognitive systems integrated. The AI plans, reflects, and evolves through automated model discovery. The AI doesn't just respond — it plans, reflects, and improves.

---

## 13. Hardware Architecture

Three-board distributed architecture:

- **Jetson Orin Nano Super 8GB** — AI compute (CUDA 67 TOPS), M.2 NVMe 256GB, JetPack 6
- **Arduino UNO Q** — Real-time motor/sensor I/O (Qualcomm QRB2210 + STM32U585 MCU)
- **ESP32-S3 ×5** — Distributed nodes (eyes, hands, limbs, sensors)

See [`hardware/catalog.svg`](hardware/catalog.svg) for the full 41-component visual catalog.

---

## 14. Software Architecture

| Layer | Name | Description |
|-------|------|-------------|
| **L5** | Simple Internet | REST API, universal downloader, 400+ CLI commands |
| **L4** | Tank Shell | PySide6/Qt6 — 13 full-screen apps |
| **L3** | TankOS Core | 35 AI managers, EventBus, Evolution Bridge |
| **L2** | ROS2 Jazzy | 23 ament_python packages |
| **L1** | Arduino | Bare-metal motor/sensor firmware |

---

## 15. Hardware Components

41 components across 8 sections. Full catalog: [`hardware/catalog.svg`](hardware/catalog.svg). Real product photos for every verified component: [`docs/hardware_photos/`](docs/hardware_photos/PHOTOS_README.md) — build photos: [`images/build/`](images/build/).

### Compute (5)
- NVIDIA Jetson Orin Nano Super Developer Kit (8GB) — AI brain  ![Jetson](docs/hardware_photos/1_jeton_orin_nano_super.jpg)
- Arduino UNO Q — real-time controller  ![Arduino](docs/hardware_photos/2_arduino_uno_q.jpg)
- M.2 NVMe SSD 256GB — storage
- ESP32-S3 DevKitC-1 (N16R8) ×5 — distributed nodes  ![ESP32-S3](docs/hardware_photos/6_esp32_s3_devkitc_1.png)
- MicroSD 64GB A2 — boot drive

### Vision & Display (4)
- Waveshare 1.28" Round LCD (GC9A01) ×2 — eyes  ![Round LCD](docs/hardware_photos/5_waveshare_1.28_round_lcd_gc9a01.jpg)
- SH1106 OLED 1.3" — status face  ![SH1106](docs/hardware_photos/11_sh1106_1.3_oled.jpg)
- USB Camera (IMX219/C920) — vision
- M2.5/M3 standoff kit — mounting

### Motion (7)
- 12V DC geared motors ×2 (JGB37-520, 30:1) — drive
- BTS7960 43A motor drivers ×2 — H-bridge  ![BTS7960](docs/hardware_photos/12_bts7960.jpg)
- Tracked chassis (aluminium) — body
- SG90 micro servos ×2 — pan/tilt
- PCA9685 16ch PWM — servo controller  ![PCA9685](docs/hardware_photos/10_pca9685.jpg)
- Pan-tilt bracket — head mount
- Mushroom E-STOP switch — safety

### Sensors (7)
- RPLidar A1 — 360° LiDAR (12m range)  ![LD19](docs/hardware_photos/7_ldrobot_ld19.jpg)
- BNO055 9-DOF IMU — orientation  ![BNO055](docs/hardware_photos/9_bno055_imu.jpg)
- INA219 current/voltage ×2 — battery telemetry
- R307 fingerprint sensor — security
- HC-SR04 ultrasonic ×2 — obstacle detection
- DS18B20 waterproof probes ×3 — temperature
- 4.7kΩ resistors ×10 — pull-ups

### Audio (4)
- ReSpeaker 4-Mic Array — wake word + STT
- USB Audio DAC — TTS output
- 3W 8Ω speaker — voice output
- Mini amplified USB speaker — dock

### Power (6)
- Jetson 19V barrel jack PSU — AI rail
- 20000mAh power banks ×3 — ESP32 rail
- 5000mAh power pebbles ×3 — limb nodes
- XT60 connectors — motor rail
- 30A blade fuse — safety
- INU2604 volt meters ×3 — monitoring

### Networking (4)
- WiFi 6 USB adapter — backup link
- Gigabit Ethernet — primary (Jetson native)
- Powered USB 3.0 hub — peripheral bus
- 4G LTE modem — optional cellular

### Chassis & Wiring (4)
- 3D-printed parts (OpenSCAD source) — structure
- Rubber tubing wire loom — cable management
- 22 AWG power sink cables — hard ports
- Servo horns (cross + circle) — mechanical linkage


---

## 15. ROS Architecture (23 packages)

**Communication Model:** Publish/Subscribe + Services + Actions

### Core Topics

| Topic | Type | Publisher | Subscriber | Rate |
|-------|------|-----------|------------|------|
| `/cmd_vel` | geometry_msgs/Twist | Nav2 / teleop | motor_controller | 20Hz |
| `/scan` | sensor_msgs/LaserScan | lidar_publisher | SLAM / Nav2 | 5.5Hz |
| `/imu/data` | sensor_msgs/Imu | imu_publisher | localization | 100Hz |
| `/camera/image_raw` | sensor_msgs/Image | camera_publisher | yolo_detector | 30fps |
| `/camera/detections` | std_msgs/String | yolo_detector | decision_engine | 30fps |
| `/thermal/human` | std_msgs/Bool | thermal_publisher | perception_fusion | 4Hz |
| `/cmd_motor` | std_msgs/String | decision_engine | motor_controller | on_event |
| `/cmd_servo` | std_msgs/String | decision_engine | servo_controller | on_event |
| `/emotion/state` | std_msgs/String | emotion_manager | eye_display | 2Hz |
| `/voice/input` | std_msgs/String | whisper_stt | intent_parser | on_speech |
| `/voice/output` | std_msgs/String | piper_tts | audio_output | on_text |
| `/health/status` | std_msgs/String | health_monitor | dashboard | 1Hz |
| `/event/log` | std_msgs/String | event_bus_bridge | storage_node | on_event |

### Services

| Service | Type | Server | Purpose |
|---------|------|--------|---------|
| `/tank/diagnostics` | tank_msgs/Diagnostics | health_node | Full system check |
| `/tank/config` | tank_msgs/Config | config_manager | Get/set parameters |
| `/tank/evolution` | tank_msgs/Evolution | evolution_bridge | Trigger model update |
| `/tank/security` | tank_msgs/Security | security_manager | Arm/disarm patrol |

### Actions

| Action | Type | Server | Purpose |
|--------|------|--------|---------|
| `/tank/navigate` | tank_msgs/Navigate | nav_manager | Waypoint following |
| `/tank/patrol` | tank_msgs/Patrol | patrol_manager | Route patrol |
| `/tank/search` | tank_msgs/Search | search_manager | Object finding |


## 16. Bill of Materials

| Section | Items | Mid-Band (₹) |
|---------|-------|-------------|
| Compute | 5 | 42,500 |
| Vision/Display | 4 | 6,200 |
| Motion | 7 | 9,650 |
| Sensors | 7 | 9,950 |
| Audio | 4 | 4,750 |
| Power | 6 | 3,550 |
| Networking | 4 | 3,950 |
| Chassis | 4 | 1,700 |
| **Total** | **41** | **₹82,250** |

Full BOM with Robu.in links: [`hardware.md`](hardware.md)

---

## 17. Component Specifications

| Component | Spec | Role |
|-----------|------|------|
| Jetson Orin Nano | 8GB RAM, 1024 CUDA cores, 67 TOPS | AI inference, ROS2, TankOS |
| Arduino UNO Q | Qualcomm QRB2210 + STM32U585, STM32U585 MCU, WiFi/BLE | Motor PWM, encoder INT, I²C |
| ESP32-S3 | 16MB Flash, 8MB PSRAM, USB-C | Eye display, hand control, limb I/O |
| RPLidar A1 | 360°, 12m, 8000 pts/sec, USB | SLAM, mapping, obstacle detection |
| BNO055 | 9-DOF, I²C 0x28, fusion engine | Orientation, heading, tilt |
| BTS7960 | 43A, dual H-bridge, PWM+DIR | Motor driver (2× for dual drive) |
| GC9A01 | 1.28", 240×240, SPI, round LCD | Animated eye expressions |
| ReSpeaker 4-Mic | MEMS ×4, far-field, USB | Wake word + voice input |

---

## 18. Wiring Diagram

See [`images/wiring.svg`](images/wiring.svg) for the full schematic.

**Arduino UNO Q Pin Map:**

| Pin | Function | Direction |
|-----|----------|-----------|
| D2 | Left encoder A (INT0) | IN |
| D3 | Left encoder B (INT1) | IN |
| D4 | Right motor DIR | OUT |
| D5 | Right motor PWM | OUT |
| D6 | Left motor PWM | OUT |
| D7 | Left motor DIR | OUT |
| D8 | E-STOP LED | OUT |
| D9 | E-STOP button (pull-up) | IN |
| D18 | Right encoder A | IN |
| D19 | Right encoder B | IN |
| A4 | I²C SDA | IN/OUT |
| A5 | I²C SCL | IN/OUT |

**I²C Bus (400kHz):**
- 0x28 — BNO055 IMU
- 0x40 — PCA9685 Servo Driver
- 0x70 — SH1106 OLED Display

---

## 19. Circuit Schematic

The Tank uses 4 separately managed power rails:

| Rail | Voltage | Powers |
|------|---------|--------|
| AI Rail | 19V DC | Jetson Orin Nano, Touchscreen |
| Motor Rail | 4S Li-ion (14.8V) | BTS7960 drivers, DC motors, rotary joints |
| Logic Rail | 5V USB-C PD | ESP32-S3 nodes, sensors, Arduino |
| Pebble Rail | 5V (per-node) | 3× 5000mAh power pebbles |

All rails are isolated to prevent motor inrush from brownout-ing the Jetson.

---

## 20. PCB Design

The Tank uses off-the-shelf breakout boards rather than custom PCBs:

- **Jetson carrier board** (included with dev kit)
- **Arduino UNO Q** (standard form factor)
- **ESP32-S3 DevKitC-1** (breadboard-compatible)
- **PCA9685 servo driver** (I²C breakout)
- **INA219 current sensors** (I²C breakout)
- **BTS7960 motor drivers** (43A H-bridge modules)

Custom wiring via 22 AWG power sink cables with hard-port connectors.

---

## 21. Mechanical Design

See [`cad/chassis_v1_slim/`](cad/chassis_v1_slim/) for full CAD files.

- **Body**: OpenSCAD parametric design, 3D-printable in PETG/PLA
- **Joints**: 6 rotary joints with linear DC actuators
- **Hands**: 5-finger gripper, 10 DOF, TPU flexible joints
- **Feet**: Pressure sensors for balance feedback

---

## 22. Chassis Design

The chassis is designed in OpenSCAD with full parametric control:

- **Top Deck**: 185×100mm — Jetson + Arduino + ESP32 + PCA9685 + fan
- **Body**: 24mm cavity — battery pebbles, wire loom
- **Neck**: Linear actuator (Z-axis) + 360° rotational joint
- **Shoulder mounts**: 3× linear actuator hardpoints per side

STL exports, STEP interchange, and 3MF multi-part bundles available in [`cad/chassis_v1_slim/stl/`](cad/chassis_v1_slim/stl/).

---

## 23. Motor & Drive System

- **Drive**: 2× JGB37-520 DC geared motors (30:1, 12V) with quadrature encoders
- **Control**: BTS7960 H-bridge drivers (43A each), PWM at 1kHz
- **Pan/Tilt**: 2× SG90 micro servos (50Hz PWM via PCA9685)
- **Locomotion**: Tracked chassis with 2× JGB37-520 geared DC motors
- **Hand**: 5× micro servos (2 DOF per finger, 10 DOF total)

---

## 24. Power System

```
┌──────────────────┐    19V DC      ┌──────────────────┐
│ Jetson PSU       │ ─────────────► │ Jetson Orin Nano │
└──────────────────┘                └──────────────────┘
                                              │ USB-A
                                              ▼
┌──────────────────┐                ┌──────────────────┐
│ 4S Li-ion (14.8V)       │ ─────────────► │ BTS7960 ×2      │
│ Motor Battery    │   12V/30A      │ → Drive Motors   │
└──────────────────┘                └──────────────────┘

┌──────────────────┐                ┌──────────────────┐
│ 20000mAh Banks   │ ─────────────► │ ESP32 Nodes ×5   │
│ ×3 (USB-C PD)    │   5V/3A each   │ + Sensors        │
└──────────────────┘                └──────────────────┘
```

---

## 25. Battery & Power Management

- **Jetson**: 19V barrel jack PSU (included with dev kit)
- **Motors**: 4S Li-ion (14.8V) 3S pack with BMS, XT60 connectors, 30A fuse
- **ESP32 Nodes**: 3× 20000mAh power banks (USB-C PD 27W)
- **Power Pebbles**: 3× 5000mAh with INU2604 volt meters, replaceable USB-C
- **Monitoring**: INA219 sensors on each rail → health_node telemetry
- **Safety**: Mushroom E-STOP in series with BMS VBAT

---

## 26. Sensors

| Sensor | Type | Range | Bus | Purpose |
|--------|------|-------|-----|---------|
| RPLidar A1 | LiDAR 360° | 12m | USB | SLAM, mapping |
| BNO055 | IMU 9-DOF | — | I²C | Orientation, heading |
| INA219 ×2 | Current/Volt | 3.2A | I²C | Battery telemetry |
| HC-SR04 ×2 | Ultrasonic | 4m | GPIO | Obstacle detection |
| DS18B20 ×3 | Temperature | ±0.5°C | 1-Wire | Battery/motor heat |
| MLX90640 | Thermal 32×24 | 2m | I²C | Human presence |
| BNO055 | IMU 9-DOF | UNO Q | I²C | Orientation, heading |
| R307 | Fingerprint | — | UART | Security unlock |

---

## 27. Camera System

- **Primary**: USB Camera (IMX219/C920) → Jetson USB-A
  - 1280×960 @ 30fps, OpenCV UVC
  - Used for: YOLOv8n object detection, face recognition, visual odometry
- **Depth**: Intel RealSense (optional) → Jetson USB-C
  - 3D point cloud, obstacle distance
- **Thermal**: MLX90640 → I²C 0x33
  - 32×24 thermal array, human presence detection
- **Eyes**: 2× GC9A01 Round LCD 1.28" → ESP32-S3 SPI
  - Animated expressions, mood visualization

---

## 28. LiDAR / Distance Sensing

- **RPLidar A1**: 360° scanning LiDAR, 12m range, 8000 points/sec
  - USB-UART at 115200 baud
  - Feeds `/scan` topic for SLAM Toolbox and Nav2
- **HC-SR04 ×2**: Ultrasonic distance sensors
  - Front + rear obstacle abort
  - GPIO Trig/Echo on Arduino
- **Depth Camera**: Intel RealSense (optional)
  - 3D point cloud for complex navigation

---

## 29. IMU & Orientation

- **BNO055** (primary): 9-DOF, hardware fusion engine
  - I²C 0x28, outputs quaternion + euler angles
  - Feeds `/imu/data` topic
- **BNO055** (primary IMU): 9-DOF, orientation fusion engine
  - I²C 0x68, head stabilization
- **Arduino UNO Q**: Reads both IMUs via I²C, sends fused orientation to Jetson

---

## 30. Arduino Implementation

The Arduino UNO Q handles **all real-time I/O**:

```cpp
// Core loop (runs at ~1kHz)
void loop() {
  // Read encoders (hardware interrupt counters)
  int32_t leftTicks = encoderLeft.read();
  int32_t rightTicks = encoderRight.read();

  // Read IMU via I²C
  readBNO055(&orientation);

  // Read ultrasonic sensors
  float frontDist = readHC-SR04(TRIG_FRONT, ECHO_FRONT);

  // Send telemetry to Jetson
  Serial.println(encodeTelemetry(leftTicks, rightTicks, orientation, frontDist));

  // Receive commands from Jetson
  if (Serial.available()) {
    Command cmd = decodeCommand(Serial.read());
    setMotorPins(cmd.leftPWM, cmd.leftDIR, cmd.rightPWM, cmd.rightDIR);
    setPanTilt(cmd.panAngle, cmd.tiltAngle);
  }
}
```

---

## 31. ESP32 Implementation

5 ESP32-S3 nodes, each handling its own domain:

| Node | Location | Handles |
|------|----------|---------|
| ESP32-S3 #1 | Head | Eye displays (2× GC9A01), head IMU |
| ESP32-S3 #2 | Left arm | Shoulder actuators, arm sensors |
| ESP32-S3 #3 | Right arm | Shoulder actuators, arm sensors |
| ESP32-S3 #4 | Left hand | 5-finger servo PWM, force sensors |
| ESP32-S3 #5 | Right hand | 5-finger servo PWM, force sensors |
| ESP32-S3 #6 | Legs | Rotary joint encoders, foot pressure |

Each node communicates with Jetson via USB serial or ESP-NOW mesh.

---

## 32. AI / Machine Learning

**Runtime AI Models (all on-device):**

| Model | Size | Purpose |
|-------|------|---------|
| llama.cpp (Phi-3 2.3B) | ~2.3GB | Primary LLM for conversation |
| TinyLlama 1.1B | ~1.1GB | Fallback LLM (always available) |
| Whisper tiny/base | ~150MB | Speech-to-text |
| Piper TTS | ~50MB | Text-to-speech |
| YOLOv8n | ~6MB | Object detection |
| openWakeWord | ~20MB | Wake word detection |
| Face Recognition | ~30MB | Known person identification |
| Sentence Transformers | ~100MB | Semantic memory embeddings |

**Evolution System**: 14 cloud providers as backup (Groq, Mistral, Cohere, etc.) with automatic circuit-breaker fallback.

---

## 33. Computer Vision

- **Object Detection**: YOLOv8n (nano) — 80-class real-time detection at 30fps
- **Face Recognition**: DeepFace — enrollment + matching for known persons
- **Thermal Imaging**: MLX90640 — human presence detection in darkness
- **Visual Odometry**: Essential matrix estimation from consecutive frames
- **Stereo Depth**: Optional Intel RealSense for 3D point clouds
- **License Plate OCR**: EasyOCR — vehicle identification
- **Activity Recognition**: Pose estimation — sitting/walking/falling

---

## 34. Object Detection

YOLOv8n runs on the Jetson at 30fps:

```python
from ultralytics import YOLO
model = YOLO("yolov8n.pt")  # 6MB nano model
results = model(frame, conf=0.5)
for box in results[0].boxes:
    print(f"Detected: {model.names[int(box.cls)]} at {box.xyxy}")
```

Detects 80 COCO classes: person, car, dog, cat, bottle, chair, etc.

---

## 35. Autonomous Navigation

**SLAM Stack:**
- RPLidar A1 → `/scan` topic
- SLAM Toolbox → 2D occupancy grid map
- RTAB-Map → 3D point cloud map (optional)

**Path Planning:**
- Nav2 — ROS2 navigation stack
- A* global planner + DWA local planner
- Behavior tree for complex missions

**Locomotion:**
- Linear actuators for leg extension
- Rotary joints for hip/knee/ankle
- Pressure sensors in feet for balance feedback

---

## 36. Obstacle Avoidance

Multi-layer safety:

1. **LiDAR** — 360° scan, costmap inflation, Nav2 planner
2. **Ultrasonic** — HC-SR04 front/rear, instant abort at <30cm
3. **E-STOP** — Hardware mushroom button, kills all motors instantly
4. **Watchdog** — Software heartbeat, auto-stop if communication lost
5. **IMU** — Tilt detection, auto-stabilize if falling

---

## 37. Communication System

| Link | Protocol | Speed | Use |
|------|----------|-------|-----|
| Jetson ↔ Arduino | USB Serial | 115200 baud | Motor commands + telemetry |
| Jetson ↔ LiDAR | USB-UART | 115200 baud | Scan data |
| Jetson ↔ ESP32 Eyes | USB Serial | 115200 baud | Eye expression JSON |
| Arduino ↔ I²C Bus | I²C | 400kHz | IMU, servo, OLED |
| ESP32 ↔ ESP32 | ESP-NOW | — | Wireless mesh (optional) |
| Jetson ↔ WiFi | WiFi 6 / Ethernet | 1Gbps | Cloud backup, OTA |

---

## 38. Control System

**Low-level (Arduino, 1kHz loop):**
- Encoder quadrature counting → odometry
- PWM motor control → velocity command
- I²C sensor polling → orientation

**Mid-level (ROS2, 10-50Hz):**
- `/cmd_vel` → motor_controller → odometry
- `/scan` → lidar_publisher → costmap
- `/imu/data` → imu_publisher → localization

**High-level (TankOS, event-driven):**
- AI decision → intent → speech/motion
- Emotion state → eye expression + voice tone
- Mission planner → waypoint sequence

---

## 39. Remote Control

- **ROS2 teleop**: `teleop_twist_keyboard` over WiFi/Ethernet
- **TankOS Chat**: AI conversational control via 7" touchscreen
- **Voice**: Wake word → Whisper STT → intent parser → action
- **Web Dashboard**: FastAPI REST API + WebSocket at port 8080
- **Tailscale VPN**: Secure remote access from anywhere

---

## 40. Software Setup

```bash
# Install everything in one command
bash install.sh --apply

# Or install without AI models (faster)
bash install.sh --apply --skip-models

# Skip ROS2 (if not needed)
bash install.sh --apply --skip-ros
```

Supported: Ubuntu/Debian, Fedora, Arch, openSUSE, Alpine.

---

## 41. Hardware Setup

1. Mount Jetson + Arduino on top deck (M2.5 standoffs)
2. Wire BTS7960 drivers to Arduino D4-D7 (DIR + PWM)
3. Connect encoders to Arduino D2-D3 (INT0/INT1) and D18-D19
4. Wire I²C bus: BNO055 (0x28), PCA9685 (0x40), OLED (0x70)
5. Connect LiDAR to Jetson USB
6. Plug USB camera into Jetson USB-A
7. Mount ESP32-S3 nodes in head, arms, hands, legs
8. Connect power rails: 19V Jetson, 12V motors, 5V ESP32

See [`WIRING.md`](WIRING.md) for detailed pinout.

---

## 42. Installation

```bash
# Clone
git clone git@github.com:shashiguptaazm-droid/The-Tank-Project.git
cd The-Tank-Project

# Install
sudo bash install.sh --apply

# Build ROS2 workspace
cd tank_ws && source /opt/ros/humble/setup.bash
colcon build --symlink-install
```

---

## 43. Configuration

```bash
# TankOS settings
cat tank_os/settings/config.json

# ROS2 parameters
cat tank_ws/src/tank_bringup/config/*.yaml

# Evolution provider keys
cat .env  # GROQ_API_KEY=xxx, MISTRAL_API_KEY=xxx, etc.
```

---

## 44. How to Run

```bash
# Launch TankOS GUI
TANKOS_QT=1 python3 -m tank_os.shell.main

# Launch simulation mode (no display)
python3 -m tank_os.shell.main

# Launch ROS2 robot
source /opt/ros/humble/setup.bash
cd tank_ws && source install/setup.bash
ros2 launch tank_bringup robot.launch.py

# Run daily evolution
python3 scripts/daily_evolution.py
```

---

## 45. Testing & Validation

- **87 pytest cases** across 10 packages
- **93/93 py_compile** passes
- **400+ CLI smoke tests** (every `--help` verified)
- **bash -n** syntax check on all shell scripts

```bash
cd tank_ws && python3 -m pytest --tb=short
```

---

## 46. Performance & Results

| Metric | Value |
|--------|-------|
| AI inference (Phi-3 Q4) | ~15 tokens/sec (Jetson) |
| Object detection (YOLOv8n) | 30 fps @ 640×480 |
| LiDAR scan rate | 5.5 Hz (8000 pts/sec) |
| Motor control loop | 1 kHz (Arduino) |
| Voice round-trip | ~1.2s (Whisper + LLM + Piper) |
| Boot to ready | ~12s (TankOS auto-start) |
| Battery life | ~2.5 hours (active), ~8 hours (idle) |

---

## 47. Demo

```bash
# Quick demo: chat with the robot
python3 -m tank_os.shell.main
# → Click "AI Chat" → type "Hello, who are you?"

# Voice demo: say "Hey Tank" → ask a question
# Camera demo: click "Camera" → see YOLO detections live
```

Demo video and presentation slides: [`images/competition/`](images/competition/)

---

## 48. Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| Motor inrush brownouts Jetson | 4 separately managed power rails |
| Single AI provider failure | 14-provider rotation with circuit breaker |
| Real-time motor timing on Linux | Arduino UNO Q handles all real-time I/O |
| 5 ESP32 nodes need coordination | ESP-NOW mesh + Jetson USB serial bridge |
| 8.6GB AI models on 256GB SSD | PreloadManager with lazy download + background fetch |
| Walking balance | Pressure sensors in feet + IMU feedback loop |


---

## 46. Known Limitations

| Limitation | Impact | Mitigation | Status |
|-----------|--------|------------|--------|
| No real hardware photos yet | Competition presentation | Blueprints + SVG diagrams | 🔵 Placeholder |
| Walking gait not optimized | Unstable locomotion | IMU feedback loop + pressure sensors | 🟡 In progress |
| 5-finger grasp uncalibrated | Weak object manipulation | Force-torque sensor tuning | 🟡 In progress |
| No demo video | Competition demo | Script ready, needs recording | 🔴 Planned |
| VPS has no real deployment | Cloud AI unavailable | Local llama.cpp fallback works | 🟡 Configured |
| No custom PCB | Wiring complexity | Breakout boards + wire loom | 🔵 Planned |
| Single-person recognition | Limited face DB | DeepFace enrollment system ready | 🔵 Planned |
| No OTA update system | Manual updates | rsync/scp over SSH works | 🔵 Planned |
| No battery management BMS | Manual monitoring | INA219 sensors + health_node | 🔵 Planned |
| Competition deadline pressure | Feature scope | Focus on core demo pipeline | 🟡 Active |


## 49. Future Improvements

- [ ] Gait optimization with reinforcement learning
- [ ] Dexterous manipulation (force-torque sensors in fingers)
- [ ] Multi-robot fleet coordination
- [ ] Custom PCB (consolidate ESP32 nodes)
- [ ] Solar charging for extended outdoor operation
- [ ] ROS2 Iron migration (long-term support)

---

## 50. Team & Contributors

**The Tank Project** — An open-source robot built for the Arduino Physical AI Challenge 2026.

| Role | Responsibility |
|------|---------------|
| **System Architect** | Overall design, hardware integration, competition strategy |
| **AI Engineer** | Evolution system, LLM integration, cognitive architecture |
| **Embedded Developer** | Arduino firmware, ESP32 nodes, motor control |
| **ROS2 Developer** | 23 ament_python packages, Nav2, SLAM |
| **Mechanical Designer** | Chassis CAD, 3D printing, assembly |
| **Software Engineer** | TankOS GUI, 400+ CLI utilities, testing |

> Built with ❤️ for the **Arduino Physical AI Challenge 2026**

---

<p align="center">
  <b>Registration ID: APC-2026-RJ-75818</b><br>
  <sub>The Tank Project · MIT Licensed · github.com/shashiguptaazm-droid/The-Tank-Project</sub>
</p>

---

## 52. Declaration

> **This is our original, unpublished work.** The Arduino® UNO™ Q is the primary board. All team members are aware of and consent to this submission. We agree to the Terms & Conditions, including granting Robu.in and Arduino® the right to showcase this project for promotional and educational purposes.

**Team:** Shashi Gupta (Team Lead)
**Registration ID:** APC-2026-RJ-75818
**Date:** 22 August 2026


---

## License

MIT License — see [LICENSE](LICENSE)


---

## 51. Competition Summary

**What is The Tank?**
The Tank is a autonomous AI robotic platform that demonstrates **Physical AI** — the integration of sensing, perception, reasoning, and physical action in a real-world robot.

**What is demonstrated:**
1. **SENSE** — 10 sensor types (camera, LiDAR, thermal, IMU, ultrasonic, etc.) read the environment
2. **PERCEIVE** — Object detection (YOLOv8n) and classification runs at 30fps
3. **FUSE** — Multiple sensors are combined into a unified world model with uncertainty tracking
4. **UNDERSTAND** — AI engine analyzes the situation using structured reasoning
5. **DECIDE** — Deterministic decision engine validates AI output through safety checks
6. **ACT** — Motor/servo commands execute physical movement
7. **VERIFY** — Action results are checked against expectations
8. **LEARN/LOG** — Events are stored in SQLite for analysis and improvement

**What makes it technically innovative:**
- **41-component hardware registry** with body-section organization
- **5-node ESP32 swarm** for distributed control (head, chest, neck, 2× hand)
- **Circuit-breaker resilience** — 14 AI providers with automatic failover
- **Self-evolving AI** — discovers new models daily, tests them, adds to rotation
- **Deterministic state machine** — 10 states with validated transitions
- **Safety-first design** — E-stop, watchdog, action timeout, sensor failure handling
- **Full simulation mode** — entire stack works without hardware for testing
- **19/19 automated tests** covering every critical subsystem

**Registration: APC-2026-RJ-75818**


---

## 🙏 Credits — Software & Open Source

> Built with these amazing open-source projects. Every badge links to the developer.

### 🧠 AI & Machine Learning

| | Software | Developer | Used For |
|---|----------|-----------|----------|
| <img src='https://img.shields.io/badge/NVIDIA-Jetson_Orin-76B900?style=flat-square&logo=nvidia&logoColor=white' width='24'> | NVIDIA JetPack 6 | NVIDIA | CUDA inference, GPU |
| <img src='https://img.shields.io/badge/Meta-LLaMA-3.1-0467DF?style=flat-square&logo=meta&logoColor=white' width='24'> | LLaMA 3.1 8B | Meta AI | Local LLM |
| <img src='https://img.shields.io/badge/Microsoft-Phi--3-0078D4?style=flat-square&logo=microsoft&logoColor=white' width='24'> | Phi-3 Mini | Microsoft | Small local LLM |
| <img src='https://img.shields.io/badge/TinyLlama-1.1B-FF6F00?style=flat-square' width='24'> | TinyLlama | TinyLlama | Ultra-light LLM |
| <img src='https://img.shields.io/badge/llama.cpp-GGUF-000000?style=flat-square' width='24'> | llama.cpp | ggerganov | CPU inference |
| <img src='https://img.shields.io/badge/Ultralytics-YOLOv8-00D4AA?style=flat-square&logo=opencv&logoColor=white' width='24'> | YOLOv8n | Ultralytics | Object detection |
| <img src='https://img.shields.io/badge/OpenAI-Whisper-412991?style=flat-square&logo=openai&logoColor=white' width='24'> | Whisper | OpenAI | Speech-to-text |
| <img src='https://img.shields.io/badge/Piper-TTS-4CAF50?style=flat-square' width='24'> | Piper TTS | rhasspy | Text-to-speech |
| <img src='https://img.shields.io/badge/openWakeWord-FF9800?style=flat-square' width='24'> | openWakeWord | dscripka | Wake word detection |

### 🤖 Robotics

| | Software | Developer | Used For |
|---|----------|-----------|----------|
| <img src='https://img.shields.io/badge/ROS2-Humble-223344?style=flat-square&logo=ros&logoColor=white' width='24'> | ROS2 Humble | ROS.org | Robot middleware |
| <img src='https://img.shields.io/badge/Arduino-CLI-00979D?style=flat-square&logo=arduino&logoColor=white' width='24'> | Arduino CLI | Arduino | ESP32 firmware |
| <img src='https://img.shields.io/badge/esptool-ESP32-000000?style=flat-square' width='24'> | esptool | espressif | Flash programming |
| <img src='https://img.shields.io/badge/OpenCV-5.0-5C3EE8?style=flat-square&logo=opencv&logoColor=white' width='24'> | OpenCV 5.0 | opencv.jp | Camera, ArUco, vision |
| <img src='https://img.shields.io/badge/Nav2-Planning-223344?style=flat-square&logo=ros&logoColor=white' width='24'> | Nav2 | ROS Navigation | Path planning |

### 🌐 Networking

| | Software | Developer | Used For |
|---|----------|-----------|----------|
| <img src='https://img.shields.io/badge/Tailscale-Mesh-000000?style=flat-square&logo=tailscale&logoColor=white' width='24'> | Tailscale | Tailscale | Mesh VPN |
| <img src='https://img.shields.io/badge/ModemManager-4G-FF0000?style=flat-square' width='24'> | ModemManager | freedesktop | LTE modem |
| <img src='https://img.shields.io/badge/nginx-Proxy-009639?style=flat-square&logo=nginx&logoColor=white' width='24'> | nginx | nginx.org | Reverse proxy |
| <img src='https://img.shields.io/badge/FastAPI-REST-009688?style=flat-square&logo=fastapi&logoColor=white' width='24'> | FastAPI | tiangolo | REST API server |

### 🖥️ Frontend

| | Software | Developer | Used For |
|---|----------|-----------|----------|
| <img src='https://img.shields.io/badge/PySide6-Qt6-41CD52?style=flat-square&logo=qt&logoColor=white' width='24'> | PySide6 | Qt Company | Desktop GUI |
| <img src='https://img.shields.io/badge/PWA-Mobile-5A0FC8?style=flat-square' width='24'> | PWA Dashboard | Custom | Mobile control |
| <img src='https://img.shields.io/badge/Telegram-Bot-0088CC?style=flat-square&logo=telegram&logoColor=white' width='24'> | Telegram Bot | Telegram | Notifications |

### 🛠️ Dev Tools

| | Software | Developer | Used For |
|---|----------|-----------|----------|
| <img src='https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white' width='24'> | Python 3.12 | python.org | Core language |
| <img src='https://img.shields.io/badge/Git-VCS-F05032?style=flat-square&logo=git&logoColor=white' width='24'> | Git | git-scm | Version control |
| <img src='https://img.shields.io/badge/GitHub-Hosting-181717?style=flat-square&logo=github&logoColor=white' width='24'> | GitHub | github.com | Code hosting |
| <img src='https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white' width='24'> | SQLite | sqlite.org | Local database |

### 🏆 Hardware Stack



### 📜 Licenses

| Component | License |
|-----------|---------|
| TankOS Core | MIT |
| LLaMA 3.1 | Llama 3.1 Community |
| YOLOv8 | AGPL-3.0 |
| Whisper | MIT |
| ROS2 | Apache 2.0 |
| OpenCV | Apache 2.0 |
| FastAPI | MIT |
| PySide6 | LGPL-3 |

*Generated by TankOS · Updated August 2026*
