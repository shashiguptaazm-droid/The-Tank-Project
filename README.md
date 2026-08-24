<div align="center">

<img src="assets/presentation/hero_banner.png" width="100%" alt="The Tank — Arduino Physical AI Challenge 2026">

# 🛡️ The Tank Project

### Distributed Edge-AI Robotics Platform · Jetson + UNO Q + ESP32 + Cloud

[![CI](https://github.com/shashiguptaazm-droid/The-Tank-Project/actions/workflows/ci.yml/badge.svg)](https://github.com/shashiguptaazm-droid/The-Tank-Project/actions)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue)](https://python.org)
[![Jetson](https://img.shields.io/badge/Jetson-Orin%20Nano%20Super-76B900)](https://developer.nvidia.com/embedded/jetson)
[![Arduino UNO Q](https://img.shields.io/badge/Arduino-UNO%20Q%204GB-00979D)](https://docs.arduino.cc/hardware/uno-q)
[![Tests](https://img.shields.io/badge/tests-427%20passed-brightgreen)](https://github.com/shashiguptaazm-droid/The-Tank-Project/actions)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Competition](https://img.shields.io/badge/APC-2026--RJ--75818-ff6600)](https://github.com/shashiguptaazm-droid/The-Tank-Project)

</div>

---

## What Is This?

**The Tank** is a complete autonomous robot operating system — built from scratch for
the **Arduino Physical AI Challenge 2026**. It distributes intelligence across three
computing layers:

| Layer | Hardware | Role |
|-------|----------|------|
| 🧠 **AI Brain** | NVIDIA Jetson Orin Nano Super (67 TOPS, 8GB) | YOLOv8n vision, Phi-3 LLM, Whisper STT, ROS2, SLAM |
| ⚡ **Coordinator** | Arduino UNO Q 4GB (QRB2210 + STM32U585) | Motor control, safety, Android TV GUI, networking |
| 📡 **Swarm** | 6× ESP32-S3 + DFRobot AI Camera + LD19 LiDAR | Real-time sensors, dual-eye displays, LTE, peripherals |

The robot **sees** (YOLO + LiDAR + depth), **understands** (LLM routing across 100+ AI providers),
**remembers** (6-type brain), **plans** (master orchestrator), and **acts** (327 typed,
safety-gated modules) — with **deterministic hardware safety that no AI can override**.

### 🦯 Also: Reconfigures into a blind-assistance wearable

The same UNO Q + ESP32 + Jetson hardware becomes a **portable AI guide for visually
impaired users**. A chest-mounted ESP32 camera captures surroundings; the UNO Q
routes frames to the Jetson for YOLO + LLM + OCR analysis; spoken guidance is
delivered through a shoulder-mounted speaker. [See below ↓](#-blind-assistance-external-module)

**APC-2026-RJ-75818 · 146,000+ lines of Python · 427 tests · 55+ infographics · ₹67,850 (~$850)**

---

## 📸 Hardware Gallery — The Build

<p align="center">
  <img src="images/build/20260720_180222.jpg" width="15%" alt="Build day 1">
  <img src="images/build/20260721_193849.jpg" width="15%" alt="Build day 2">
  <img src="images/build/20260801_012257.jpg" width="15%" alt="Build day 3">
  <img src="images/build/20260803_162900.jpg" width="15%" alt="Build day 4">
  <img src="images/build/20260809_232842.jpg" width="15%" alt="Build day 5">
  <img src="images/build/20260813_140304.jpg" width="15%" alt="Build day 6">
</p>

<p align="center">
  <sub>Every photo is the actual hardware — Jetson, UNO Q, ESP32, motors, LiDAR, camera, chassis, wiring</sub>
</p>

### Component Inventory

<p align="center">
  <img src="assets/presentation/hardware_wall.png" width="100%" alt="All 12+ hardware components">
</p>

| # | Component | Model | Purpose | Photo |
|---|-----------|-------|---------|-------|
| 1 | AI Brain | Jetson Orin Nano Super 8GB | 67 TOPS CUDA GPU | [📷](docs/hardware_photos/1_jeton_orin_nano_super.jpg) |
| 2 | System Coordinator | Arduino UNO Q 4GB | QRB2210 + STM32U585 | [📷](docs/hardware_photos/2_arduino_uno_q.jpg) |
| 3 | AI Camera | DFRobot SEN0611 | ESP32-S3, Night Vision | [📷](docs/hardware_photos/3_dfrobot_esp32s3_ai_camera.webp) |
| 4 | ESP32-S3 CAM | ESPHome, WiFi | Remote perception node | [📷](docs/hardware_photos/4_esp32_s3_cam.jpg) |
| 5 | Dual Eye Displays | Waveshare 1.28" GC9A01 | Robot eye expressions | [📷](docs/hardware_photos/5_waveshare_1.28_round_lcd_gc9a01.jpg) |
| 6 | ESP32-S3 DevKitC | N16R8 | 6× swarm nodes | [📷](docs/hardware_photos/6_esp32_s3_devkitc_1.png) |
| 7 | LiDAR | LDROBOT LD19 | 360° × 12m scanning | [📷](docs/hardware_photos/7_ldrobot_ld19.jpg) |
| 8 | 4G LTE Modem | Quectel EG800AK | SMS + cellular backup | [📷](docs/hardware_photos/8_quectel_eg800ak.jpg) |
| 9 | IMU | BNO055 | 9-DOF orientation | [📷](docs/hardware_photos/9_bno055_imu.jpg) |
| 10 | Servo Driver | PCA9685 | 16-channel PWM | [📷](docs/hardware_photos/10_pca9685.jpg) |
| 11 | OLED Display | SH1106 1.3" | Status display | [📷](docs/hardware_photos/11_sh1106_1.3_oled.jpg) |
| 12 | Motor Driver | BTS7960 ×2 | 43A H-Bridge | [📷](docs/hardware_photos/12_bts7960.jpg) |

**Full BOM + pricing → [`hardware.md`](hardware.md) · Wiring map → [`WIRING.md`](WIRING.md) · CAD files → [`cad/`](cad/)**

---

## 🏗️ Architecture

<p align="center">
  <a href="assets/infographics/01_system_overview.svg">
    <img src="assets/infographics/01_system_overview.svg" width="100%" alt="System overview">
  </a>
</p>

```
User (Android TV / Voice / Web / Telegram / SMS)
              │
     ┌────────▼────────┐
     │  Master Loop    │
     │  Observe →      │
     │  Understand →   │   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
     │  Remember →     │   │ AI Router│ │327 Tools │ │ Safety   │ │ Auto-    │
     │  Reason → Plan →│   │ 100+ LLMs│ │18 groups │ │ Gate     │ │ Evolve   │
     │  Validate → Act │   └──────────┘ └──────────┘ └──────────┘ └──────────┘
     └──┬───────┬──────┘
        │       │
   ┌────▼───┐ ┌─▼──────────┐ ┌──────────────┐
   │ Jetson │ │ UNO Q 4GB  │ │ 6× ESP32-S3  │
   │ 8GB    │ │ QRB2210    │ │ FreeRTOS     │
   │ AI +   │ │ STM32U585  │ │ Sensors/IO   │
   │ Vision │ │ Safety MCU │ │ Motors/Servos│
   └────────┘ └────────────┘ └──────────────┘
```

<p align="center">
  <a href="assets/infographics/02_hardware_architecture.svg">
    <img src="assets/infographics/02_hardware_architecture.svg" width="32%" alt="Hardware architecture">
  </a>
  <a href="assets/infographics/tankos_architecture.svg">
    <img src="assets/infographics/tankos_architecture.svg" width="32%" alt="TankOS layers">
  </a>
  <a href="assets/infographics/38_esp32_swarm.svg">
    <img src="assets/infographics/38_esp32_swarm.svg" width="32%" alt="ESP32 swarm">
  </a>
</p>

<p align="center">
  <a href="assets/infographics/unoq_primary_device.svg">
    <img src="assets/infographics/unoq_primary_device.svg" width="32%" alt="UNO Q primary">
  </a>
  <a href="assets/infographics/31_mesh_network.svg">
    <img src="assets/infographics/31_mesh_network.svg" width="32%" alt="Mesh network">
  </a>
  <a href="assets/infographics/fleet_connectivity.svg">
    <img src="assets/infographics/fleet_connectivity.svg" width="32%" alt="Fleet connectivity">
  </a>
</p>

**Three-layer intelligence:** Jetson (brain) → UNO Q (nervous system) → ESP32 nodes (muscles).
Full architecture deep-dive → [`ARCHITECTURE.md`](ARCHITECTURE.md).

---

## 🦯 Blind-Assistance External Module

<p align="center">
  <b>The Tank reconfigures into a wearable AI guide for the visually impaired</b>
</p>

<p align="center">
  <img src="images/blind_assist/20260823_235016.jpg" width="45%" alt="Blind-assistance module setup">
  <img src="images/blind_assist/20260823_235019.jpg" width="45%" alt="Blind-assistance wearable configuration">
</p>

| Feature | How It Works |
|---------|-------------|
| **Real-time scene description** | ESP32 CAM → UNO Q → Tailscale → Jetson/Cloud AI → spoken output |
| **Obstacle detection** | YOLOv8n detects obstacles, LiDAR measures distance → audio alert |
| **Face recognition** | Recognizes known people → speaks their name |
| **Text reading (OCR)** | Reads signs, documents aloud |
| **Voice commands** | "What's around me?" · "Read that sign" · "Find my keys" · "Call emergency" |
| **Emergency alert** | Triple-tap E-STOP → SMS with GPS to contacts |
| **Physical following** | Optional locomotion — AI assistant physically escorts user |
| **Always online** | WiFi → 4G LTE → Hotspot → Tailscale mesh |

### Blind-Assistance Diagrams

<p align="center">
  <a href="assets/infographics/60_blind_assist_front.svg">
    <img src="assets/infographics/60_blind_assist_front.svg" width="49%" alt="Front view — person wearing all module components">
  </a>
  <a href="assets/infographics/63_blind_assist_3d_isometric.svg">
    <img src="assets/infographics/63_blind_assist_3d_isometric.svg" width="49%" alt="3D Isometric — animated signal paths">
  </a>
</p>

<p align="center">
  <a href="assets/infographics/65_blind_assist_exploded_3d.svg">
    <img src="assets/infographics/65_blind_assist_exploded_3d.svg" width="49%" alt="Exploded 3D hardware view — all 10 components">
  </a>
  <a href="assets/infographics/61_blind_assist_side.svg">
    <img src="assets/infographics/61_blind_assist_side.svg" width="49%" alt="Side view — component placement">
  </a>
</p>

<p align="center">
  <a href="assets/infographics/62_blind_assist_pipeline.svg">
    <img src="assets/infographics/62_blind_assist_pipeline.svg" width="49%" alt="Data flow pipeline">
  </a>
  <a href="assets/infographics/64_blind_assist_animated_flow.svg">
    <img src="assets/infographics/64_blind_assist_animated_flow.svg" width="49%" alt="Animated flow chart — SENSE→SPEAK">
  </a>
</p>

### Competition Demo Sequence

<p align="center">
  <a href="assets/infographics/66_blind_assist_demo_sequence.svg">
    <img src="assets/infographics/66_blind_assist_demo_sequence.svg" width="100%" alt="14-step competition demo sequence">
  </a>
</p>

**Module BOM: ₹3,800** (uses UNO Q + Jetson + LTE from core). Full docs → [`docs/BLIND_ASSIST.md`](docs/BLIND_ASSIST.md).
Demo video uploaded August 2026.

---

## 🖥️ Screenshots — Every Feature Tested

<p align="center">
  <img src="assets/presentation/screenshots_wall.png" width="100%" alt="15+ TankOS GUI screens captured live">
</p>

### TankOS GUI (Android TV Interface)

<p align="center">
  <img src="docs/screenshots/gui/40_home_hub.png" width="32%" alt="Home hub">
  <img src="docs/screenshots/gui/41_drive.png" width="32%" alt="Drive">
  <img src="docs/screenshots/gui/43_ai_brain.png" width="32%" alt="AI Brain">
</p>

<p align="center">
  <img src="docs/screenshots/gui/44_robot_health.png" width="32%" alt="Robot Health">
  <img src="docs/screenshots/gui/45_esp32_fleet.png" width="32%" alt="ESP32 Fleet">
  <img src="docs/screenshots/gui/47_competition.png" width="32%" alt="Competition Mode">
</p>

<p align="center">
  <img src="docs/screenshots/gui/46_jetson.png" width="32%" alt="Jetson Dashboard">
  <img src="docs/screenshots/gui/49_sensor_fusion.png" width="32%" alt="Sensor Fusion">
  <img src="docs/screenshots/gui/50_hardware_topology.png" width="32%" alt="Hardware Topology">
</p>

### Terminals & Web UIs

<p align="center">
  <img src="docs/screenshots/25_jetson_terminal.png" width="24%" alt="Jetson terminal">
  <img src="docs/screenshots/02_chat.png" width="24%" alt="AI Chat">
  <img src="docs/screenshots/22_vps_tank_dashboard.png" width="24%" alt="VPS Dashboard">
  <img src="docs/screenshots/24_ariang.png" width="24%" alt="AriaNg">
</p>

**70+ screenshots total.** Full gallery → [`docs/screenshots/README.md`](docs/screenshots/README.md)

---

## 🧠 All 55+ Infographics

<p align="center">
  <sub>Every architecture diagram, pipeline, and comparison chart — all SVG, dark theme</sub>
</p>

| Row | Infographics |
|-----|-------------|
| **System** | [Overview](assets/infographics/01_system_overview.svg) · [Hardware](assets/infographics/02_hardware_architecture.svg) · [GPU](assets/infographics/03_gpu_foundation.svg) · [Camera](assets/infographics/04_camera_intelligence.svg) |
| **Vision** | [Detection](assets/infographics/05_object_detection.svg) · [Tracking](assets/infographics/06_object_tracking.svg) · [Semantic](assets/infographics/07_semantic_vision.svg) · [Depth](assets/infographics/08_depth_spatial.svg) |
| **SLAM & Nav** | [SLAM](assets/infographics/09_slam_mapping.svg) · [Fusion](assets/infographics/10_sensor_fusion.svg) · [Navigation](assets/infographics/11_navigation_ai.svg) · [Predictive](assets/infographics/12_predictive_ai.svg) |
| **AI** | [Vision-Language](assets/infographics/13_vision-language.svg) · [Edge AI](assets/infographics/14_edge-ai_system.svg) · [Orchestrator](assets/infographics/43_ai_orchestrator.svg) · [Models](assets/infographics/48_online_models.svg) |
| **UNO Q** | [Platform](assets/infographics/15_uno_q_platform.svg) · [MCU](assets/infographics/16_mcu_supervision.svg) · [Primary](assets/infographics/unoq_primary_device.svg) · [Tool Registry](assets/infographics/29_tool_registry.svg) |
| **Motion** | [Motors](assets/infographics/17_motor_control_.svg) · [Odometry](assets/infographics/18_odometry.svg) · [Safety](assets/infographics/19_safety_system.svg) · [Safety Chain](assets/infographics/42_safety_chain.svg) |
| **Power & Sensors** | [Power Intel](assets/infographics/20_power_intel.svg) · [Servo](assets/infographics/21_servo_intel.svg) · [Reliability](assets/infographics/22_sensor_reliability.svg) · [Power Rails](assets/infographics/35_power_rails.svg) |
| **Comms** | [TV Launcher](assets/infographics/23_tv_launcher.svg) · [SMS](assets/infographics/24_sms_gateway.svg) · [Telegram](assets/infographics/26_telegram_bot.svg) · [API](assets/infographics/27_api_server.svg) |
| **Network** | [Mesh](assets/infographics/31_mesh_network.svg) · [Fleet](assets/infographics/fleet_connectivity.svg) · [ESP32](assets/infographics/esp32_boards.svg) · [USB](assets/infographics/36_usb_ecosystem.svg) |
| **Ecosystem** | [ROS2](assets/infographics/37_ros2_stack.svg) · [Dashboard](assets/infographics/32_dashboard.svg) · [PWA](assets/infographics/33_pwa_mobile.svg) · [Hardware](assets/infographics/hardware_inventory.svg) |
| **Evolution** | [System](assets/infographics/28_evolution_system.svg) · [Notify](assets/infographics/34_evolution_notify.svg) · [Benchmark](assets/infographics/39_benchmark_suite.svg) · [Registry](assets/infographics/40_model_registry.svg) |
| **AI Pipeline** | [Autonomous](assets/infographics/41_autonomous_pipeline.svg) · [Resource](assets/infographics/44_resource_manager.svg) · [Offline](assets/infographics/49_offline_models.svg) · [TankOS Arch](assets/infographics/tankos_architecture.svg) |
| **Competition** | [Demo](assets/infographics/45_competition_demo.svg) · [Field](assets/infographics/46_field_deployment.svg) · [Comparison](assets/infographics/47_comparison.svg) · [Complete](assets/infographics/50_the_complete_tank.svg) |
| **Blind-Assist** | [Front](assets/infographics/60_blind_assist_front.svg) · [Side](assets/infographics/61_blind_assist_side.svg) · [Pipeline](assets/infographics/62_blind_assist_pipeline.svg) · [3D](assets/infographics/63_blind_assist_3d_isometric.svg) · [Flow](assets/infographics/64_blind_assist_animated_flow.svg) · [Exploded](assets/infographics/65_blind_assist_exploded_3d.svg) · [Demo](assets/infographics/66_blind_assist_demo_sequence.svg) |

---

## 🧰 327 Callable Modules

Every robot function is a **typed, permissioned, LLM-callable module** with automatic fallback:

```
LLM → Module Router → Capability Check → Safety Gate → Executor → Result
```

| Category | Count | Examples |
|----------|-------|----------|
| Perception | 20 | YOLO detect, depth estimate, anomaly spot |
| Navigation | 20 | Go-to waypoint, patrol, obstacle avoid, return home |
| SLAM / World | 20 | Map building, localization, landmark tracking |
| Human interaction | 20 | Detect, track, gesture, follow, safety zones |
| Voice | 20 | STT, TTS, wake word, noise reduction |
| Memory | 20 | Working, episodic, semantic, procedural, spatial |
| AI orchestration | 20 | Ask, reason, plan, route to best provider |
| Actuators | 20 | Motors, servos, arm, emergency stop |
| ESP32 / Sensors | 20 | IMU, thermal, battery, encoder, ultrasonic |
| Generative AI | 27 | Text, code, missions, images, voice, GUI |
| Power | 15 | Voltage, current, budget, thermal, low-power |
| Network | 15 | Tailscale mesh, WiFi, LTE, failover |
| + 5 more groups | 90 | Tools, hardware, GUI, evolution, safety, OCR |
| **Total** | **327** | |

**Risk-gated — AI can never override safety:**

| Risk | Examples | Gate |
|------|----------|------|
| 🟢 Read | vision.capture, memory.search | None |
| 🔵 Low | language.translate, voice.speak | Validation |
| 🟡 Medium | motor.set_speed | Safety check |
| 🟠 High | navigation.go_to | Safety + confirmation |
| 🔴 Critical | emergency_stop | **Hardwired** |

---

## 🌐 100+ AI Providers

TankOS auto-routes each task to the best model — never locked to one API.

```
Task → Score candidates → Pick best → Fall through chain on failure
         Gemini → Groq → OpenRouter → local Phi-3 → rule-based safety
```

**24 cloud providers** (11 live on board): OpenAI, Anthropic, Gemini, Groq, Cerebras, Cohere, Mistral, OpenRouter, DeepSeek, Cloudflare, Replicate, HuggingFace, xAI, Together, DeepInfra, SambaNova, Fireworks, Perplexity, Hyperbolic, Lambda, Voyage, Novita, EndpointAI, Freebuff.

**42 local models** — works fully offline without internet. Full catalog → [`docs/100_PROVIDERS.md`](docs/100_PROVIDERS.md).

---

## 🧬 Auto-Evolution Engine

Self-improvement with mandatory safety gates — the robot benchmarks, ranks, and only deploys proven improvements under human review.

```
Observe → Find weaknesses → Generate improvement
  → Sandbox → Static check → Tests → Simulation → Benchmark
    → Safety gate → Human approval → Canary deploy → Monitor → Promote or rollback
```

9/14 cloud providers configured, 425+ tests guard every change.

---

## 📊 Project Stats

| Metric | Value |
|--------|-------|
| Python files (own code) | **848** |
| Lines of code | **~146,000** |
| Core tests passing | **427** |
| Git commits | **81+** |
| Callable modules | **327** |
| AI providers | **100+** |
| LLM-callable tools | **1,966** |
| GUI screens | **70+** |
| Hardware components | **25+** |
| ESP32 nodes | **6** |
| ROS2 packages | **23** (Jazzy) |
| SVG infographics | **55+** |
| Documentation pages | **40+** |
| Total BOM cost | **₹67,850 (~$850)** |
| Registration | **APC-2026-RJ-75818** |

---

## 🚀 Quick Start

```bash
git clone https://github.com/shashiguptaazm-droid/The-Tank-Project.git
cd The-Tank-Project
pip install -r requirements.txt

# Run core tests (427 pass)
python3 -m pytest tank_os/tests/ -q

# Launch TankOS shell (lightweight)
python3 -m tank_os.shell.main

# Launch Android TV GUI (requires display)
python3 tank/gui/tankos_gui.py

# Blind-assistance module setup
bash scripts/setup_blind_assist.sh
python3 -m tank.blind_assist.main --mode full
```

---

## 📚 Documentation

| Document | Contents |
|----------|----------|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Three-layer architecture deep-dive |
| [`PRESENTATION.md`](PRESENTATION.md) | Visual presentation with photos, GIFs, screenshots |
| [`JUDGE.md`](JUDGE.md) | Quick-start guide for competition judges |
| [`UNOQ_PRIMARY.md`](UNOQ_PRIMARY.md) | UNO Q as competition primary device |
| [`STATUS.md`](STATUS.md) | Live project status with pipeline tracker |
| [`hardware.md`](hardware.md) | Complete BOM with part numbers & pricing |
| [`WIRING.md`](WIRING.md) | Pinouts, I²C addresses, USB layout, blind-module wiring |
| [`COMPARISON.md`](COMPARISON.md) | Tank vs Unitree Go2 / Boston Dynamics Spot |
| [`PHASES.md`](PHASES.md) | Development roadmap |
| [`docs/BLIND_ASSIST.md`](docs/BLIND_ASSIST.md) | 🦯 Blind-assistance wearable module — full docs |
| [`docs/100_PROVIDERS.md`](docs/100_PROVIDERS.md) | 100+ AI providers across 10 categories |
| [`docs/AI.md`](docs/AI.md) | Full AI pipeline — routing, models, evolution |
| [`docs/COMPLETE_PROJECT.md`](docs/COMPLETE_PROJECT.md) | End-to-end project walkthrough |
| [`docs/screenshots/`](docs/screenshots/) | 70+ live screenshots |
| [`docs/infographics/`](assets/infographics/) | 55+ SVG architecture diagrams |
| [`docs/hardware_photos/`](docs/hardware_photos/) | Individual component photos |

---

## 🎬 Animated

<p align="center">
  <img src="assets/gifs/eyes_expressions.gif" width="45%" alt="Robot eye expressions">
  <img src="assets/gifs/network_failover.gif" width="45%" alt="Network failover">
</p>

---

<div align="center">

### Built from scratch for autonomous robotics.

**🏆 Arduino Physical AI Challenge 2026 · APC-2026-RJ-75818 · Dr. Shashi Gupta**

[Report](https://github.com/shashiguptaazm-droid/The-Tank-Project) · [JUDGE.md](JUDGE.md) · [PRESENTATION.md](PRESENTATION.md) · [BLIND_ASSIST.md](docs/BLIND_ASSIST.md)

</div>