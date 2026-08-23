<![CDATA[<div align="center">

# 🛡️ THE TANK PROJECT

### TankOS — Autonomous AI Robotics Operating System

**An original, from-scratch autonomous robot operating system** that distributes intelligence across Jetson, UNO Q, ESP32, and cloud — with 327 callable modules, 100 AI providers, self-evolving capabilities, and a full Android TV interface.

---

[![CI](https://github.com/shashiguptaazm-droid/The-Tank-Project/actions/workflows/ci.yml/badge.svg)](https://github.com/shashiguptaazm-droid/The-Tank-Project/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Jetson](https://img.shields.io/badge/Jetson-Orin%20Nano%20Super-76B900.svg)](https://developer.nvidia.com/embedded/jetson)
[![UNO Q](https://img.shields.io/badge/Arduino-UNO%20Q%204GB-00979D.svg)](https://docs.arduino.cc/hardware/uno-q)
[![Features](https://img.shields.io/badge/Features-327-purple.svg)](#327-callable-modules)
[![AI Providers](https://img.shields.io/badge/AI%20Providers-100-orange.svg)](#100-ai-providers)
[![Cost](https://img.shields.io/badge/Total%20Cost-₹64%2C050-red.svg)](#bill-of-materials)
[![Commit Activity](https://img.shields.io/github/commit-activity/m/shashiguptaazm-droid/The-Tank-Project)](https://github.com/shashiguptaazm-droid/The-Tank-Project)

</div>

---

## 📖 Table of Contents

- [What Is TankOS?](#-what-is-tankos)
- [System Architecture](#-system-architecture)
- [Hardware Stack](#-hardware-stack)
- [Software Stack](#-software-stack)
- [327 Callable Modules](#327-callable-modules)
- [100 AI Providers](#100-ai-providers)
- [TankOS Brain (Memory System)](#-tankos-brain-memory-system)
- [Master Orchestrator](#-master-orchestrator)
- [HumanSense (Human Interaction)](#-humansense-human-interaction)
- [Device Communication Mesh](#-device-communication-mesh)
- [AI Selection Router](#-ai-selection-router)
- [Auto-Evolution Engine](#-auto-evolution-engine)
- [Generative AI Subsystem](#-generative-ai-subsystem)
- [Android TV GUI](#-android-tv-gui)
- [Quick Start](#-quick-start)
- [Project Statistics](#-project-statistics)
- [Bill of Materials](#bill-of-materials)
- [Competitor Comparison](#-competitor-comparison)
- [Documentation](#-documentation)
- [Software Credits](#-software-credits)
- [License](#-license)

---

## 🎯 What Is TankOS?

TankOS is a **complete, from-scratch autonomous robot operating system** designed to:

1. **Run entirely on a robot** — not a laptop, not a cloud service, but embedded on Jetson + UNO Q + ESP32
2. **Make every LLM callable by robot** — 327 typed, permissioned modules that any AI model can discover and invoke
3. **Self-improve safely** — auto-evolution engine that benchmarks, tests, simulates, and only deploys proven improvements
4. **Work offline** — 42 local AI models ensure the robot keeps functioning without internet
5. **Coordinate distributed devices** — Jetson (AI brain), UNO Q (system coordinator), ESP32 (real-time sensors/actuators) work as one unified system

### What makes it different from a chatbot-in-a-robot:

| Chatbot in a Robot | TankOS |
|---------------------|--------|
| LLM sends text to API, robot moves blindly | LLM calls typed, validated, safety-gated tool modules |
| Single cloud AI dependency | 100 providers, automatic fallback, 42 local models |
| No safety layer | Deterministic safety gate — AI cannot bypass emergency stop |
| No memory | 6-type brain: working, episodic, semantic, procedural, spatial, evolution |
| Static behavior | Auto-evolution: benchmarks → experiments → proven improvements |
| One device | Distributed mesh: Jetson + UNO Q + 6× ESP32 + Android TV + VPS |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        HUMAN / GUI INTERFACE                           │
│                    Android TV · Voice · Web · Telegram                  │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────────┐
│                    TANKOS MASTER ORCHESTRATOR                           │
│                                                                        │
│   OBSERVE → UNDERSTAND → REMEMBER → REASON → PLAN → VALIDATE          │
│   → ACT → OBSERVE RESULT → EVALUATE → LEARN → UPDATE STATE            │
│                                                                        │
│   ┌─────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐  │
│   │ AI Router   │ │ 327 Modules  │ │ Safety Gate  │ │ Auto-Evolve  │  │
│   │ 100 providers│ │ 18 categories│ │ Deterministic│ │ Self-improve │  │
│   └─────────────┘ └──────────────┘ └──────────────┘ └──────────────┘  │
└───────┬──────────────────┬───────────────────┬──────────────────────────┘
        │                  │                   │
┌───────▼──────┐  ┌────────▼────────┐  ┌──────▼───────┐
│   JETSON     │  │    UNO Q 4GB    │  │  6× ESP32-S3 │
│  Orin Nano   │  │  System Coord.  │  │  Real-time   │
│  Super 8GB   │  │  QRB2210 Linux  │  │  Sensors/IO  │
│              │  │  STM32 MCU      │  │              │
│  AI Brain    │  │  Motors/Safety  │  │  IMU/GPIO/   │
│  Vision      │  │  Android TV     │  │  Servo/LTE   │
│  SLAM        │  │  Networking     │  │  Battery     │
│  Navigation  │  │  Diagnostics    │  │  Thermal     │
└──────┬───────┘  └────────┬────────┘  └──────────────┘
       │                   │
┌──────▼───────┐  ┌────────▼────────┐
│  Camera      │  │  Motors ×2      │
│  LiDAR       │  │  Servos ×4      │
│  Display     │  │  Encoders ×2    │
│  USB Devices │  │  Battery Bank   │
└──────────────┘  └─────────────────┘
```

### Three-Layer Intelligence

| Layer | Device | Role | Analogy |
|-------|--------|------|---------|
| **Intelligence** | Jetson Orin Nano Super | "What should happen?" | Brain |
| **Coordination** | Arduino UNO Q 4GB | "Coordinate everything" | Nervous System |
| **Execution** | 6× ESP32-S3 | "Execute safely and precisely" | Muscles |

---

## 🔩 Hardware Stack

### Core Compute

| Device | Role | Specs | Cost |
|--------|------|-------|------|
| **NVIDIA Jetson Orin Nano Super** | AI Brain | 8GB RAM, 67 TOPS, CUDA, TensorRT | ₹25,000 |
| **Arduino UNO Q 4GB** | System Coordinator | QRB2210 Linux + STM32U585 MCU | ₹12,500 |
| **VPS (Hetzner)** | Cloud Backup AI | 4 vCPU, 8GB RAM | ₹750/mo |

### Vision & Perception

| Sensor | Purpose | Specs |
|--------|---------|-------|
| DFRobot SEN0611 AI Camera | RGB + Night Vision | ESP32-S3, USB, 640×480 |
| LDROBOT LD19 LiDAR | 360° Distance Scanning | 12m range, 5kHz scan |
| BNO055 IMU | Orientation & Motion | 9-DOF, I²C, accelerometer |

### Motion & Actuation

| Component | Purpose | Specs |
|-----------|---------|-------|
| BTS7960 Motor Driver ×2 | Track Motor Control | 43A, PWM, bidirectional |
| JGB37-520 Motors ×2 | Tracked Drive | 12V, encoder-equipped |
| PCA9685 Servo Driver | Servo Control | 16-channel, I²C |
| SG90 Micro Servos ×4 | Manipulator/Head | 180° rotation |

### ESP32 Sensor Nodes

| Node | Purpose |
|------|---------|
| ESP32-S3 Motor | Motor control + encoder reading |
| ESP32-S3 Sensor | IMU + thermal + ultrasonic |
| ESP32-S3 Arm | Servo + manipulator |
| ESP32-S3 Battery | INA219 dual current sensing |
| ESP32-S3 LTE | Quectel EG800AK 4G + SMS |
| ESP32-S3 Comms | WiFi mesh + I²C gateway |

### Power System

| Component | Purpose |
|-----------|---------|
| 4S 18650 Li-ion Pack | 14.8V, 3400mAh primary |
| LM2596 DC/DC Buck | 12V rail for motors |
| AMS1117-5V | 5V rail for Jetson |
| AMS1117-3.3V | 3.3V rail for sensors |
| INA219 ×2 | Real-time power monitoring |

**Total Hardware Cost: ₹64,050 (~$800 USD)**

---

## 💻 Software Stack

### Compute Platforms

| Platform | OS | Software |
|----------|-----|----------|
| Jetson Orin Nano | JetPack 6.2 (Ubuntu 22.04) | CUDA 12.6, TensorRT, PyTorch, OpenCV 5, ROS 2 Humble |
| Arduino UNO Q | Ubuntu 24.04 (QRB2210) + Zephyr RTOS (STM32U585) | TankOS Core, Android TV, Device Manager |
| ESP32-S3 ×6 | FreeRTOS | Arduino CLI firmware, MQTT/USB transport |
| VPS | Ubuntu 22.04 | Nextcloud, Aria2, Web Terminal, Telegram Bot |
| Android TV | Custom PWA | TankOS Dashboard, 16 Feature Tiles |

### AI Models Running on Jetson

| Model | Purpose | Framework |
|-------|---------|-----------|
| YOLOv8n | Object Detection | TensorRT |
| Phi-3 Mini 4K | Local LLM | llama.cpp |
| TinyLlama 1.1B | Lightweight LLM | llama.cpp |
| Whisper Base | Speech-to-Text | PyTorch |
| Piper TTS | Text-to-Speech | Native |
| openWakeWord | Wake Word Detection | PyTorch |
| MiDaS | Depth Estimation | ONNX Runtime |
| SAM (Segment Anything) | Image Segmentation | ONNX Runtime |
| Grounding DINO | Open-Vocabulary Detection | ONNX Runtime |
| Sentence Transformers | Embeddings | PyTorch |

---

## 🧩 327 Callable Modules

Every robot function is a **typed, permissioned, LLM-callable module** with automatic fallback.

```
LLM → Module Router → Capability Check → Safety Gate → Executor → Result
```

### Module Categories

| # | Category | Modules | Description |
|---|----------|---------|-------------|
| 1 | **Perception** | 20 | Camera, YOLO, tracking, pose, depth, anomaly detection |
| 2 | **OCR / Language** | 20 | Text reading, intent classification, entity extraction, translation |
| 3 | **Voice** | 20 | STT, TTS, wake word, noise reduction, speech synthesis |
| 4 | **Human Interaction** | 20 | Detection, tracking, gesture, following, escort, attention |
| 5 | **Navigation** | 20 | Go-to, patrol, path planning, obstacle avoidance, return-home |
| 6 | **SLAM / World Model** | 20 | Mapping, localization, landmarks, rooms, world state |
| 7 | **Memory** | 20 | Store, retrieve, search, compress, deduplicate, episodic |
| 8 | **AI Orchestration** | 20 | Ask, reason, plan, classify, extract, route, fallback |
| 9 | **Tool System** | 20 | List, search, validate, execute, chain, parallel, simulate |
| 10 | **Hardware / Device** | 20 | Discover, health, restart, firmware, calibrate, self-test |
| 11 | **ESP32 / Sensors** | 20 | IMU, thermal, battery, encoder, ultrasonic, GPIO |
| 12 | **Actuators / Robot** | 20 | Motors, servos, arm, emergency stop, safe state |
| 13 | **Power** | 15 | Voltage, current, budget, overload, thermal, low-power |
| 14 | **Network** | 15 | Status, scan, topology, failover, publish/subscribe |
| 15 | **GUI** | 10 | Dashboard, camera, map, mission, AI, diagnostics |
| 16 | **Evolution** | 10 | Observe, hypothesis, experiment, benchmark, rollback |
| 17 | **Safety / Diagnostics** | 10 | Check, stop, validate, logs, reports, export |
| 18 | **Generative AI** | 27 | Text, code, robot missions, images, voice, GUI generation |
| | **TOTAL** | **327** | |

### How a Module Call Works

```python
# LLM sees this schema:
{
  "name": "navigation.go_to",
  "description": "Navigate to a known location",
  "parameters": {
    "location": {"type": "string"}
  }
}

# LLM generates:
result = tankos.call("navigation.go_to", {"location": "kitchen"})

# TankOS internally:
# 1. Validates arguments against schema
# 2. Checks safety (battery OK? motors healthy? no e-stop?)
# 3. Routes to Jetson (primary) or UNO Q (fallback)
# 4. Executes through ROS2 / direct motor control
# 5. Returns structured result with latency + success status
```

### Risk Classification

| Risk Level | Examples | Requirement |
|------------|----------|-------------|
| 🟢 **Read** | vision.capture, memory.search | None |
| 🔵 **Low** | language.translate, voice.speak | Basic validation |
| 🟡 **Medium** | motor.set_speed, navigation.pause | Safety check |
| 🟠 **High** | navigation.go_to, human.follow | Safety + confirmation |
| 🔴 **Critical** | safety.stop, actuator.emergency_stop | Hardwired, cannot be overridden by AI |

---

## 🌐 100 AI Providers

TankOS routes to the **best AI model** for each task — never hardcoded to one provider.

### Provider Breakdown

| Category | Providers | Examples |
|----------|-----------|----------|
| **Major LLMs** | 15 | OpenAI, Anthropic, Gemini, Groq, OpenRouter, Mistral, Cerebras, Cohere, Together, DeepInfra, SambaNova, Fireworks, Replicate, HuggingFace, Cloudflare |
| **Vision & OCR** | 10 | Google Vision, Azure, AWS Rekognition, Tesseract, EasyOCR, PaddleOCR, Surya, TrOCR, docTR, Marker |
| **Speech (STT/TTS)** | 10 | Whisper API, Deepgram, AssemblyAI, Google STT, Azure, Coqui, Piper, Google TTS, ElevenLabs |
| **Embeddings & Search** | 10 | OpenAI, Voyage, Jina, Nomic, Sentence Transformers, GTE-Qwen, SerpAPI, Brave, Tavily, DuckDuckGo |
| **Image Generation** | 10 | DALL-E 3, SDXL, Stable Diffusion 3, Flux, ComfyUI, Fooocus, Ideogram, Picogen, Segmind |
| **Video AI** | 10 | Runway, Pika, Kling, MiniMax, Luma, HeyGen, Synthesia, Hailuo, D-ID, Warp |
| **Coding AI** | 10 | Copilot, Cursor, Codestral, Codeium, Phind, Sweep, Aider, Continue.dev, Tabnine, Amazon Q |
| **Robotics AI** | 10 | NVIDIA Isaac, YOLO, TIMM, MediaPipe, OpenPose, MMPose, Depth Anything, SAM, Grounding DINO, OWL-ViT |
| **Local LLMs** | 10 | llama.cpp, Ollama, vLLM, TensorRT-LLM, Phi-3, TinyLlama, Qwen 2.5, Gemma 2, DeepSeek-R1, MLLama |
| **Translation** | 5 | Google Translate, DeepL, Argos, IndicTrans, OpenTydi |
| | **100** | |

### Provider Selection Scoring

```
score = capability_match × 0.25
      + quality × 0.25
      + latency_score × 0.20
      + reliability × 0.20
      + cost × 0.10
      + privacy × 0.10
      + hardware_fit × 0.10
      - network_penalty
      - failure_penalty
```

### Fallback Chain

```
Primary Provider → Fallback 1 → Fallback 2 → Local Model → Rule-Based
     Gemini      →   Groq     →  OpenRouter  → Phi-3 Mini  →  Safety Rules
```

---

## 🧠 TankOS Brain (Memory System)

Six types of memory, inspired by human cognition:

| Memory Type | Purpose | Storage Tier |
|-------------|---------|-------------|
| **Working Memory** | Current task context, live events | RAM (real-time) |
| **Episodic Memory** | Mission history, events with timestamps | NVMe (hot) |
| **Semantic Memory** | Facts, knowledge, learned information | NVMe (warm) |
| **Procedural Memory** | Skills, behaviors, learned procedures | NVMe (warm) |
| **Spatial Memory** | Maps, rooms, landmarks, routes | NVMe (warm) |
| **Evolution Memory** | Experiments, failures, improvements | NVMe (cold) |

### Memory Compression Pipeline

```
100 GB raw experience → 10 GB events → 1 GB summaries → 100 MB knowledge → 10 MB policies
```

This means memory **quality** grows faster than storage consumption.

---

## 🎯 Master Orchestrator

The brain loop that coordinates everything:

```
┌─────────────────────────────────────────────────────────────┐
│                    MASTER BRAIN LOOP                         │
│                                                              │
│  1. OBSERVE    → Normalize any input (text/voice/camera)    │
│  2. UNDERSTAND → Classify intent, extract entities           │
│  3. REMEMBER   → Retrieve relevant context from memory      │
│  4. REASON     → Route to best AI model for reasoning        │
│  5. PLAN       → Generate structured action plan             │
│  6. VALIDATE   → Safety gate checks battery/motors/obstacles│
│  7. ACT        → Execute through 327-module registry         │
│  8. OBSERVE    → Check execution result                      │
│  9. EVALUATE   → Score success/failure                       │
│ 10. LEARN      → Store in memory for future improvement      │
└─────────────────────────────────────────────────────────────┘
```

### Universal Event Format

Every input becomes a normalized event:

```json
{
  "event_id": "a3f2b1c0",
  "source": "android_tv",
  "type": "text",
  "timestamp": 1787500000,
  "payload": {
    "raw_text": "Navigate to the kitchen",
    "intent": "navigation",
    "entities": {"location": "kitchen"},
    "language": "en"
  },
  "priority": 2,
  "user_initiated": true
}
```

---

## 🧍 HumanSense (Human Interaction)

Dedicated subsystem for detecting, tracking, and interacting with humans.

### Interaction Pipeline

```
Camera → Detect → Track → Understand Intent → Coordinate → Respond → Remember
```

### Human State Machine

```
UNKNOWN → DETECTED → OBSERVING → APPROACHING → AVAILABLE → INTERACTING → LEAVING
```

### Safety Zones

| Zone | Distance | Behavior |
|------|----------|----------|
| 🟢 **Interaction** | 1.0–2.0 m | Offer interaction, voice greeting |
| 🟡 **Caution** | 0.5–1.0 m | Reduce speed, prepare to stop |
| 🔴 **Critical** | < 0.5 m | Emergency stop, safe state |

### Supported Gestures

| Gesture | Action |
|---------|--------|
| 👋 Wave | Greet / acknowledge |
| ✋ Stop | Emergency stop |
| ☝ Point | Look at direction |
| 👍 Confirm | Accept action |
| 👎 Reject | Cancel action |

---

## 🔗 Device Communication Mesh

Inter-device communication with automatic failover:

```
┌──────────────────────────────────────────────────────┐
│                   DEVICE MESH                         │
│                                                       │
│  ┌─────────┐    Ethernet     ┌──────────────┐        │
│  │ UNO Q   │◄──────────────►│   Jetson     │        │
│  │ (Coord) │    USB Serial   │  (AI Brain)  │        │
│  └────┬────┘                 └──────────────┘        │
│       │                                               │
│  ┌────▼────┐   USB/WiFi    ┌──────────────┐         │
│  │ ESP32   │◄─────────────►│  Android TV  │         │
│  │ (×6)    │               └──────────────┘         │
│  └─────────┘                                         │
└──────────────────────────────────────────────────────┘
```

### Communication Features

| Feature | Details |
|---------|---------|
| **Primary → Fallback → Emergency** | 3-level connection hierarchy |
| **Heartbeat Monitoring** | Jetson (2s), UNO Q (2s), ESP32 (250ms) |
| **Priority Queues** | P0 Emergency → P6 Debug, bandwidth-aware |
| **Offline Buffer** | Store-and-forward when connections drop |
| **Split-Brain Protection** | One device owns each action type |
| **Health Scoring** | Latency + packet loss + error rate → health score |

---

## 🧠 AI Selection Router

Policy-driven model selection — never hardcoded to one provider.

### Task-Dependent Weight Profiles

| Task | Priority Weights |
|------|-----------------|
| **Emergency Robotics** | Safety 30% + Latency 25% + Reliability 25% |
| **Navigation** | Latency 30% + Reliability 25% + Safety 20% |
| **Conversation** | Quality 30% + Latency 25% + Reliability 20% |
| **Coding** | Quality 35% + Reasoning 25% + Context 15% |
| **Vision** | Quality 30% + Latency 25% + Privacy 15% |
| **Offline Mode** | Locality 35% + Latency 25% + Reliability 20% |

### Selection Example

```
User: "What's in front of me?"
  → Task: vision.question_answering
  → Requires: camera + vision + language
  → Privacy: normal
  → Network: available

Candidates scored:
  Jetson-VLM      → Score 92 (local, fast, private, free)
  Gemini Vision   → Score 87 (high quality, cloud)
  Cloud VLM       → Score 82 (good, cloud)

Selected: Jetson-VLM (local + fast + private)
```

---

## 🧬 Auto-Evolution Engine

Controlled self-improvement — **evolves through evidence, not self-confidence**.

### Evolution Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    EVOLUTION ENGINE                          │
│                                                              │
│  OBSERVE → FIND WEAKNESSES → PRIORITIZE → GENERATE          │
│                                                              │
│  → SANDBOX → STATIC VALIDATION → SECURITY CHECK             │
│  → AUTOMATED TESTS → SIMULATION → BENCHMARK                  │
│                                                              │
│  → SAFETY GATE (risk ≥ R3: requires human approval)         │
│  → CANARY DEPLOY → MONITOR → PROMOTE or ROLLBACK            │
└─────────────────────────────────────────────────────────────┘
```

### Risk Classification

| Risk | Level | Examples | Approval |
|------|-------|----------|----------|
| R0 | Documentation | README, comments | Auto |
| R1 | UI | Dashboard layout | Auto if reversible |
| R2 | Optimization | Performance, caching | Tests required |
| R3 | AI Behavior | Model selection, prompts | Simulation + evaluation |
| R4 | Robot Behavior | Navigation, motion | Hardware-in-loop + approval |
| R5 | Safety | Emergency stop, limits | **NEVER autonomous** |

### Evolution Score

```
EVOLUTION SCORE = reliability + task_success + AI_accuracy
                + navigation_quality + responsiveness + battery_efficiency
                - latency - crashes - errors - power_consumption
```

---

## 🎨 Generative AI Subsystem

TankOS generates content, code, UI, robot behaviors, documentation, and more.

| Category | Features | Examples |
|----------|----------|----------|
| 📝 **Text Generation** | 5 | Reports, documents, summaries, structured text |
| 💻 **Code Generation** | 6 | Python, Arduino, ROS2, Docker, tests, APIs |
| 🤖 **Robot Behavior** | 4 | Mission plans, patrol routes, behavior trees, recovery |
| 🎨 **Image Generation** | 3 | Infographics, thumbnails, visualizations |
| 🔊 **Voice Generation** | 2 | Speech output, announcements |
| 🖥️ **GUI Generation** | 3 | Dashboards, widgets, layouts from NL |
| 🧬 **Self-Evolution** | 4 | Plugins, ROS2 nodes, tools, tests |

### Generation Pipeline (Safe)

```
GENERATE → SANDBOX → STATIC ANALYSIS → UNIT TEST → SIMULATION
→ SECURITY CHECK → HUMAN APPROVAL → DEPLOY
```

**TankOS never directly deploys LLM-generated code to production.**

---

## 📺 Android TV GUI — 100 Advanced Features

TankOS has a **100-feature Android TV-style interface** organized into 6 panels:

### Panel Overview

| Panel | Features | Description |
|-------|----------|-------------|
| 🎮 **Control & Teleoperation** | 20 | Gravity, sketch, arm, AR, digital twin, fleet, sandbox |
| 🧠 **AI & Autonomy** | 20 | Reasoning, shadow mode, explainability, sentry, mission planner |
| 📊 **Telemetry & Diagnostics** | 20 | Network QoS, odometry, ROS browser, heatmap, self-test |
| 🗺️ **Navigation & Mapping** | 15 | No-go zones, map layers, trajectory, path editing, coverage |
| ⚙️ **Settings & Customization** | 15 | Themes, plugins, languages, haptics, onboarding |
| 🔒 **Security & Admin** | 10 | RBAC, audit log, API keys, backup/restore |

### Highlight Features

| # | Feature | Description |
|---|---------|-------------|
| 201 | Gravity Control | Tilt phone to steer robot |
| 207 | AR View | Overlay digital info on live video |
| 218 | Digital Twin | 3D model mirroring real-time state |
| 221 | LLM Reasoning Panel | Show AI thought process |
| 229 | Semantic Search | "Where did I leave the blue box?" |
| 248 | Custom Dashboard | Drag-drop-resize widgets |
| 263 | No-Go Zones | Draw avoidance areas on map |
| 275 | Dynamic Map | Watch map build in real-time |
| 293 | RBAC | Admin/Operator/Viewer permissions |
| 300 | Backup/Restore | One-click system backup |

```
┌─────────────────────────────────────────────────────────┐
│                   TANKOS DASHBOARD                       │
├─────────────┬─────────────┬─────────────┬───────────────┤
│ 🤖 Robot    │ 🧠 AI Chat  │ 📷 Camera   │ 🗺️ Navigation│
│ Status      │ LLM Control │ Live + YOLO │ Path Planning │
├─────────────┼─────────────┼─────────────┼───────────────┤
│ 🎮 Drive    │ 📡 Sensors  │ ⚙️ Motors   │ 🔋 Power     │
│ Joystick    │ IMU/LiDAR  │ Left/Right  │ Battery %     │
├─────────────┼─────────────┼─────────────┼───────────────┤
│ 🛡️ Safety   │ 🌐 Network  │ 💬 SMS      │ 🔔 Alerts    │
│ E-STOP      │ Tailscale   │ LTE/4G     │ Real-time    │
├─────────────┼─────────────┼─────────────┼───────────────┤
│ 🧬 Evolution│ 👁️ AprilTag │ 🔌 USB      │ 💻 Terminal  │
│ AI Improve  │ Dock Detect │ Devices     │ Full Shell   │
└─────────────┴─────────────┴─────────────┴───────────────┘

ADVANCED PANELS:
┌─────────────────────────────────────────────────────────┐
│ 🎮 Control  │ 🧠 AI  │ 📊 Telemetry │ 🗺️ Map │ ⚙️ Set │ 🔒 Sec │
│─────────────────────────────────────────────────────────│
│ • Gravity Steering    • AR View       • Digital Twin      │
│ • Sketch-to-Path      • Fleet Control • No-Go Zones      │
│ • 6-DOF Arm           • Shadow Mode   • Custom Dashboard │
│ • Command Stacking    • Sentry Mode   • RBAC             │
│ • Simulation Mode     • Mission Planner • Backup/Restore │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Jetson Orin Nano Super with JetPack 6.2
- Arduino UNO Q 4GB
- ESP32-S3 DevKitC-1 × 6
- Python 3.12+

### On Jetson

```bash
# Clone
git clone https://github.com/shashiguptaazm-droid/The-Tank-Project.git
cd The-Tank-Project

# Install dependencies
pip install -r requirements.txt

# Test all subsystems
PYTHONPATH=. python3 tests/test_all_subsystems.py

# Launch TankOS
python3 tank/main.py
```

### On UNO Q

```bash
# Flash ESP32 firmware
cd tank/networking/esp32/
arduino-cli upload -b esp32:esp32:esp32s3 --port /dev/ttyUSB0 firmware/

# Launch TankOS coordinator
cd ~/The-Tank-Project
python3 tank/unoq/tv/tv_launcher.py
```

### Launch Android TV Dashboard

```bash
python3 tank/gui/tankos_gui.py
```

### Launch Web Dashboard (Port 8090)

```bash
python3 tank/networking/api.py
# Open http://<jetson-ip>:8090
```

---

## 📊 Project Statistics

| Metric | Value |
|--------|-------|
| **Callable Modules** | 327 |
| **AI Providers** | 100 (58 cloud + 42 local) |
| **Python Files** | 127 |
| **Total Lines of Code** | 18,285 |
| **Git Commits** | 68 |
| **SVG Infographics** | 51 |
| **Documentation Files** | 30 |
| **Screenshots** | 79 |
| **Test Cases** | 213 |
| **Hardware Components** | 25 core |
| **ESP32 Nodes** | 6 |
| **Total Cost** | ₹64,050 (~$800) |

### Module Distribution

```
Perception        ████████████████████ 20
OCR/Language      ████████████████████ 20
Voice             ████████████████████ 20
Human             ████████████████████ 20
Navigation        ████████████████████ 20
SLAM/World        ████████████████████ 20
Memory            ████████████████████ 20
AI Orchestration  ████████████████████ 20
Tool System       ████████████████████ 20
Hardware          ████████████████████ 20
ESP32/Sensors     ████████████████████ 20
Actuators         ████████████████████ 20
Power             ███████████████      15
Network           ███████████████      15
GUI               ██████████           10
Evolution         ██████████           10
Safety/Diagnostics██████████           10
Generative AI     ███████████████████████████ 27
                                  TOTAL: 327
```

---

## 💰 Bill of Materials

| Category | Components | Cost (₹) |
|----------|-----------|----------|
| **Compute** | Jetson Orin Nano Super + UNO Q 4GB + VPS | ₹38,250 |
| **Vision** | DFRobot AI Camera + LDROBOT LD19 | ₹8,000 |
| **Sensors** | BNO055 IMU + INA219×2 + PCA9685 + Quectel LTE | ₹2,100 |
| **Communication** | Tailscale + Quectel EG800AK | ₹1,200 |
| **Power** | 4S Li-ion + DC/DC Buck + regulators | ₹2,500 |
| **Chassis** | Tracked robot chassis + brackets | ₹3,200 |
| **ESP32 Nodes** | 6× ESP32-S3 DevKitC-1 N16R8 | ₹1,800 |
| **Wiring & Misc** | Connectors, cables, PCB, standoffs | ₹7,000 |
| | **GRAND TOTAL** | **₹64,050 (~$800)** |

### Compared to Commercial Alternatives

| Robot | Cost | TankOS Savings |
|-------|------|----------------|
| Unitree Go2 | $2,799 (~₹2,35,000) | **97% cheaper** |
| Boston Dynamics Spot | $74,500 (~₹62,50,000) | **99.9% cheaper** |
| Agilex Scout | $45,000 (~₹37,80,000) | **99.8% cheaper** |
| **TankOS** | **₹64,050 (~$800)** | **Best value** |

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [`README.md`](README.md) | This file — complete project overview |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Three-layer architecture deep dive |
| [`JUDGE.md`](JUDGE.md) | Competition judge quick guide |
| [`hardware.md`](hardware.md) | Complete BOM with pricing |
| [`WIRING.md`](WIRING.md) | Pin connections, I²C addresses, USB layout |
| [`STATUS.md`](STATUS.md) | Live project status |
| [`COMPARISON.md`](COMPARISON.md) | TankOS vs competitors |
| [`PROJECT_STATUS.md`](PROJECT_STATUS.md) | Feature completion status |
| [`UNOQ_PRIMARY.md`](UNOQ_PRIMARY.md) | UNO Q as primary device (competition) |
| [`docs/AI.md`](docs/AI.md) | Complete AI pipeline documentation |
| [`docs/AUTO_EVOLUTION.md`](docs/AUTO_EVOLUTION.md) | Evolution system deep dive |
| [`docs/100_PROVIDERS.md`](docs/100_PROVIDERS.md) | All 100 AI providers listed |
| [`docs/REQUIRED_LLMS.md`](docs/REQUIRED_LLMS.md) | LLM provider requirements |
| [`docs/DEPENDENCIES.md`](docs/DEPENDENCIES.md) | All software dependencies |
| [`docs/HARDWARE_DEPENDENCIES.md`](docs/HARDWARE_DEPENDENCIES.md) | Hardware-specific dependencies |
| [`docs/COMPLETE_PROJECT.md`](docs/COMPLETE_PROJECT.md) | Full project walkthrough |
| [`docs/infographics/`](docs/infographics/) | 51 SVG architecture diagrams |
| [`docs/screenshots/`](docs/screenshots/) | 79 live screenshots |

---

## 🏆 Competition Readiness

### What Judges See (First 60 Seconds)

1. ✅ **Hero banner** with NVIDIA badge and system overview
2. ✅ **Architecture diagram** — 3-layer Jetson/UNO Q/ESP32
3. ✅ **Feature count** — 327 modules, 100 providers, 10+ subsystems
4. ✅ **Live screenshots** — dashboard, camera, YOLO, sensors
5. ✅ **Cost comparison** — ₹64,050 vs ₹2,35,000+ (Unitree)
6. ✅ **AI pipeline** — how intelligence flows from camera to action
7. ✅ **Safety architecture** — deterministic, cannot be overridden by AI
8. ✅ **Evolution system** — self-improving with proven benchmarks
9. ✅ **Judge guide** — [`JUDGE.md`](JUDGE.md) for quick navigation
10. ✅ **CI/CD badges** — automated build and test status

### UNO Q as Primary Device

TankOS satisfies the competition requirement by making UNO Q the **system coordinator**:

| UNO Q Role | What It Does |
|-----------|-------------|
| Boot first | Powers on before Jetson |
| Device Discovery | Finds and manages all connected devices |
| Safety Controller | E-STOP FSM on STM32 MCU |
| Android TV GUI | 10-foot robot interface |
| Network Gateway | WiFi, Bluetooth, Tailscale mesh |
| AI Gateway | Routes AI requests to Jetson |
| Diagnostics | Full system health monitoring |

---

## 🙏 Software Credits

TankOS builds on these amazing open-source projects:

### 🧠 AI & Machine Learning

| Software | Developer | License |
|----------|-----------|---------|
| [NVIDIA JetPack 6](https://developer.nvidia.com/embedded/jetpack) | NVIDIA | Proprietary |
| [LLaMA 3.1 8B](https://ai.meta.com/llama/) | Meta AI | Llama 3.1 Community |
| [Phi-3 Mini 4K](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct) | Microsoft | MIT |
| [TinyLlama 1.1B](https://huggingface.co/TinyLlama/TinyLlama-1.1B-intermediate-step-1431k-3T) | TinyLlama Team | Apache 2.0 |
| [llama.cpp](https://github.com/ggerganov/llama.cpp) | Georgi Gerganov | MIT |
| [YOLOv8n](https://github.com/ultralytics/ultralytics) | Ultralytics | AGPL-3.0 |
| [Whisper](https://github.com/openai/whisper) | OpenAI | MIT |
| [Piper TTS](https://github.com/rhasspy/piper) | Rhasspy | MIT |
| [openWakeWord](https://github.com/dscripka/openWakeWord) | Daniel Scripka | Apache 2.0 |

### 🤖 Robotics

| Software | Developer | License |
|----------|-----------|---------|
| [ROS 2 Humble](https://docs.ros.org/en/humble/) | ROS.org | Apache 2.0 |
| [Arduino CLI](https://github.com/arduino/arduino-cli) | Arduino | Apache 2.0 |
| [esptool](https://github.com/espressif/esptool) | Espressif | GPL-2.0 |
| [OpenCV 5.0](https://opencv.org/) | OpenCV Team | Apache 2.0 |
| [Nav2](https://docs.nav2.org/) | ROS Navigation | Apache 2.0 |

### 🌐 Networking

| Software | Developer | License |
|----------|-----------|---------|
| [Tailscale](https://tailscale.com/) | Tailscale | BSD-3 |
| [ModemManager](https://www.freedesktop.org/wiki/Software/ModemManager/) | freedesktop.org | LGPL-2.1 |
| [nginx](https://nginx.org/) | nginx.org | BSD-2 |
| [FastAPI](https://fastapi.tiangolo.com/) | Sebastián Ramírez | MIT |

### 🖥️ Frontend

| Software | Developer | License |
|----------|-----------|---------|
| [PySide6](https://doc.qt.io/qtforpython-6/) | Qt Company | LGPL-3.0 |

---

## 📜 Licenses

| Component | License | Notes |
|-----------|---------|-------|
| TankOS | MIT | Original work |
| LLaMA 3.1 | Llama 3.1 Community | Commercial use allowed |
| YOLOv8 | AGPL-3.0 | Ultralytics terms apply |
| Whisper | MIT | OpenAI |
| ROS 2 | Apache 2.0 | ROS Foundation |
| OpenCV | Apache 2.0 | OpenCV Team |
| FastAPI | MIT | Sebastián Ramírez |
| PySide6 | LGPL-3.0 | Qt Company |

---

## 🔬 Originality Statement

TankOS is an **original, from-scratch operating system** for autonomous robots. The following subsystems are original creations:

1. **327-Module Registry** — typed, permissioned, LLM-callable capability system
2. **Master Orchestrator** — 10-step brain loop with safety validation
3. **AI Selection Router** — policy-driven multi-provider scoring
4. **TankOS Brain** — 6-type memory system with importance-based tiering
5. **Auto-Evolution Engine** — controlled self-improvement with safety gates
6. **HumanSense** — gesture + proximity + intent interaction subsystem
7. **Device Mesh** — distributed Jetson/UNO Q/ESP32 communication with failover
8. **Generative AI Pipeline** — safe generation → validation → deployment flow
9. **UNO Q TV Launcher** — Android TV interface with 16 robot feature tiles
10. **Tool Calling System** — LLM-to-hardware bridge with schema validation

TankOS **uses** open-source tools (YOLO, Whisper, ROS2, etc.) as **components** — but the operating system that connects them is original.

---

<div align="center">

### Built with ❤️ for autonomous robotics

**[The Tank Project](https://github.com/shashiguptaazm-droid/The-Tank-Project)** · TankOS v1.0 · 2026

</div>
]]>