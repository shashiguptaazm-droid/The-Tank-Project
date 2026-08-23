<div align="center">

# 🛡️ The Tank Project

### An autonomous AI robotics platform — Jetson + UNO Q + ESP32 + cloud

[![CI](https://github.com/shashiguptaazm-droid/The-Tank-Project/actions/workflows/ci.yml/badge.svg)](https://github.com/shashiguptaazm-droid/The-Tank-Project/actions)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue)](https://python.org)
[![Jetson](https://img.shields.io/badge/Jetson-Orin%20Nano%20Super-76B900)](https://developer.nvidia.com/embedded/jetson)
[![Arduino UNO Q](https://img.shields.io/badge/Arduino-UNO%20Q%204GB-00979D)](https://docs.arduino.cc/hardware/uno-q)
[![Tests](https://img.shields.io/badge/tests-427%20passed-brightgreen)](https://github.com/shashiguptaazm-droid/The-Tank-Project/actions)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

</div>

---

## What is this?

A **from-scratch autonomous robot operating system** (TankOS) that distributes
intelligence across a Jetson Orin Nano (AI brain), an Arduino UNO Q (system
coordinator), 6× ESP32-S3 nodes (real-time sensors & actuators), and a
cloud VPS — all meshed over Tailscale.

The robot sees (YOLO + LiDAR + depth), understands (LLM routing), remembers
(6-type brain), plans (master orchestrator), and acts (327 typed, safety-gated
modules) — with deterministic hardware-level safety that **no AI can override**.

---

## Architecture

```
User (Android TV / Voice / Web / Telegram)
              │
     ┌────────▼────────┐
     │  Master Loop    │
     │  Observe →      │
     │  Understand →   │   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
     │  Remember →     │   │ AI Router│ │327 Tools │ │ Safety   │ │ Auto-    │
     │  Reason → Plan →│   │ 14+ LLMs │ │18 groups │ │ Gate     │ │ Evolve   │
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

**Three-layer intelligence:** Jetson (brain) → UNO Q (nervous system) → ESP32 nodes (muscles).

---

## Hardware

| Component | What it does | Cost |
|-----------|-------------|------|
| **NVIDIA Jetson Orin Nano Super 8GB** | AI brain — YOLO, SLAM, LLM inference, ROS2 | ₹25,000 |
| **Arduino UNO Q 4GB** | System coordinator — Android TV, safety controller, networking | ₹12,500 |
| **LDROBOT LD19 LiDAR** | 360° distance scanning, 12m range | ~₹3,500 |
| **DFRobot SEN0611 AI Camera** | RGB + night vision, ESP32-S3 onboard | ~₹4,500 |
| **BNO055 IMU** | 9-DOF orientation & motion | ~₹600 |
| **JGB37-520 Motors ×2** | Tracked drive with encoders | ~₹1,200 |
| **BTS7960 Motor Drivers ×2** | 43A PWM bidirectional | ~₹800 |
| **6× ESP32-S3 DevKitC-1** | Distributed sensor/actuator nodes | ₹1,800 |
| **4S Li-ion + power management** | 14.8V battery, buck converters, INA219 monitoring | ₹2,500 |
| **Chassis, wiring, misc** | Chassis, connectors, PCB, standoffs | ~₹11,650 |
| **Total** | | **~₹64,000** |

Detailed BOM → [`hardware.md`](hardware.md) · Wiring diagram → [`WIRING.md`](WIRING.md)

---

## Software stack

| Platform | OS | Key software |
|----------|-----|-------------|
| Jetson | JetPack 6.2 | CUDA 12.6, TensorRT, PyTorch, OpenCV 5, ROS2 Humble, llama.cpp |
| UNO Q | Ubuntu 24.04 + Zephyr RTOS | TankOS Core, Android TV GUI, Device Manager |
| 6× ESP32-S3 | FreeRTOS | Arduino CLI firmware, MQTT/USB transport |
| VPS | Ubuntu 22.04 | Docker, Nextcloud, Aria2, Telegram Bot |

**AI models on-device:** YOLOv8n (TensorRT), Phi-3 Mini (llama.cpp), Whisper Base (PyTorch),
Piper TTS, MiDaS depth, SAM segmentation, Grounding DINO, openWakeWord, Sentence Transformers.

---

## 327 callable modules

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
| Power | 15 | Voltage, current, budget, thermal, low-power |
| Network | 15 | Tailscale mesh, WiFi, LTE, failover |
| Generative AI | 27 | Text, code, missions, images, voice, GUI |
| + 6 more groups | 90 | Tools, hardware, GUI, evolution, safety, OCR |
| **Total** | **327** | |

**Risk classification** — every module is tagged:

| Risk | Examples | Gate |
|------|----------|------|
| 🟢 Read | vision.capture, memory.search | None |
| 🔵 Low | language.translate, voice.speak | Validation |
| 🟡 Medium | motor.set_speed | Safety check |
| 🟠 High | navigation.go_to | Safety + confirmation |
| 🔴 Critical | emergency_stop | **Hardwired — AI cannot override** |

---

## Multi-provider AI routing

TankOS routes each task to the best available model — never hardcoded to a single API.
Selection uses a weighted score: capability match, quality, latency, reliability, cost, privacy, and hardware fit.

```
Task → Score all candidates → Pick best → Fall through chain on failure
         Gemini → Groq → OpenRouter → local Phi-3 → rule-based safety
```

Works offline via local GGUF models on the Jetson.

**24 cloud LLM providers** implemented (11 live on the board): OpenAI, Anthropic, Gemini, Groq, Cerebras, Cohere, Mistral, OpenRouter, DeepSeek, Cloudflare, Replicate, HuggingFace, xAI, Together, DeepInfra, SambaNova, Fireworks, Perplexity, Hyperbolic, Lambda, Voyage, Novita, EndpointAI, Freebuff.

Full catalog in [`docs/100_PROVIDERS.md`](docs/100_PROVIDERS.md).

---

## Auto-evolution engine

Self-improvement with mandatory safety gates:

```
Observe → Find weaknesses → Generate improvement
  → Sandbox → Static check → Tests → Simulation → Benchmark
    → Safety gate (R3+ requires human approval)
      → Canary deploy → Monitor → Promote or rollback
```

| Risk | Level | Approval required |
|------|-------|-------------------|
| R0 | Docs / comments | Auto |
| R1 | UI layout | Auto if reversible |
| R2 | Performance optimization | Tests required |
| R3 | AI behavior / prompts | Simulation + review |
| R4 | Robot behavior / navigation | Hardware-in-loop + human |
| R5 | Safety / e-stop | **Never autonomous** |

---

## Android TV GUI — 500 features

A 21-panel interface spread across three tiers — from drive joystick to VPS management.
See [`PROJECT_STATUS.md`](PROJECT_STATUS.md) for full feature status.

```
TANKOS DASHBOARD (Tier 1)
┌──────────┬──────────┬──────────┬──────────┐
│ 🤖 Robot │ 🧠 AI    │ 📷 Camera│ 🗺️ Nav   │
│ 🎮 Drive │ 📡 IMU   │ ⚙️ Motor │ 🔋 Power │
│ 🛡️ Safety│ 🌐 Net   │ 💬 SMS   │ 🔔 Alert │
│ 🧬 Evolve│ 👁️ Dock  │ 🔌 USB   │ 💻 Terminal│
└──────────┴──────────┴──────────┴──────────┘
```

---

## Quick start

**Prerequisites:** Python 3.12+ (Jetson, UNO Q, or any Linux machine for testing)

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
```

Full hardware setup instructions in the [docs](docs/).

---

## Project stats

| Metric | Value |
|--------|-------|
| Python files (own code) | **848** |
| Lines of code (own) | **~146,000** |
| Core tests passing | **427** |
| Git commits | **81** |
| Callable modules | 327 |
| Hardware components | 25+ |
| ESP32 nodes | 6 |
| Documentation pages | 40+ |

---

## Documentation

| Document | What's in it |
|----------|-------------|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Three-layer architecture deep-dive |
| [`PROJECT_STATUS.md`](PROJECT_STATUS.md) | Live completion status per module |
| [`hardware.md`](hardware.md) | Full BOM with part numbers & pricing |
| [`WIRING.md`](WIRING.md) | Pinouts, I²C addresses, USB layout |
| [`UNOQ_PRIMARY.md`](UNOQ_PRIMARY.md) | UNO Q as competition primary device |
| [`JUDGE.md`](JUDGE.md) | Quick guide for competition judges |
| [`COMPARISON.md`](COMPARISON.md) | How TankOS compares to other approaches |
| [`docs/AI.md`](docs/AI.md) | Full AI pipeline — providers, routing, models |
| [`docs/100_PROVIDERS.md`](docs/100_PROVIDERS.md) | Complete catalog of 100+ AI providers across 10 categories |
| [`docs/COMPLETE_PROJECT.md`](docs/COMPLETE_PROJECT.md) | End-to-end walkthrough |
| [`docs/`](docs/) | 30+ more docs on evolution, GUI, safety, etc. |

---

## License

TankOS is MIT licensed. It uses open-source components under their respective licenses
(YOLOv8 AGPL-3.0, ROS2 Apache 2.0, JetPack NVIDIA proprietary, etc.).

---

<div align="center">

**Built from scratch for autonomous robotics.**

[Report](https://github.com/shashiguptaazm-droid/The-Tank-Project) · APC-2026-RJ-75818 · 2026

</div>