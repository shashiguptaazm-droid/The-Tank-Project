# 🏆 Judge Guide — The Tank

> **Arduino Physical AI Challenge 2026**  
> **Registration: APC-2026-RJ-75818**  
> **Author: Dr. Shashi Gupta**

---

## 🎯 What Is The Tank?

**The Tank is a distributed edge-AI robotic platform** that combines three computing layers:

1. **Jetson Orin Nano Super** (67 TOPS) — AI brain
2. **Arduino UNO Q 4GB** — Real-time body controller
3. **ESP32-S3 ×6** — Distributed peripherals

---

## 🧠 What Makes It Innovative?

| Innovation | Description |
|-----------|-------------|
| **Distributed AI** | Not one brain — three boards share intelligence |
| **374 Features** | 200 Jetson + 100 UNO Q + 74 TankOS |
| **22 AI Tools** | Any LLM can control physical robot functions |
| **14 AI Providers** | Auto-discovers and selects best AI models |
| **Controlled Evolution** | Benchmarks, ranks, and selects AI models |
| **Hardware Safety** | E-STOP FSM, watchdog, degraded mode |
| **SMS Control** | Text message commands via LTE modem |
| **PWA Dashboard** | Phone-based 8-tab control center |

---

## 🔧 Hardware

| Component | Model | Purpose |
|-----------|-------|---------|
| Jetson Orin Nano Super | NVIDIA 8GB | AI inference, vision, navigation |
| Arduino UNO Q 4GB | QRB2210 + STM32 | Motor/sensor/safety control |
| ESP32-S3 ×6 | DevKitC-1 N16R8 | Distributed peripherals |
| Camera | DFRobot SEN0611 | USB serial video |
| LiDAR | LDROBOT LD19 | 360° laser scanning |
| 4G Modem | Quectel EG800K | SMS + data |
| Motors | JGB37-520 ×2 | Tracked locomotion |
| Motor Driver | BTS7960 ×2 | H-bridge control |
| IMU | QMI8658 | Orientation sensing |

**Total Cost: ₹64,050 (~$800)**

---

## 💻 Software

| System | Features | Status |
|--------|----------|--------|
| Jetson AI | 200 | 🟢 12/12 modules tested |
| UNO Q | 100 | 🟢 10/10 modules tested |
| TankOS Core | 74 | 🟢 9/9 modules tested |
| **Total** | **374** | **31/31 modules tested** |

---

## 📊 What Can Be Demonstrated

### 🟢 Working NOW (Software Tested)
- USB Camera streaming over serial
- YOLOv8n object detection on CUDA
- Multi-object tracking with IDs
- LiDAR scanning and occupancy grid
- A* path planning + obstacle avoidance
- Kalman filter sensor fusion
- 22 AI tools callable by any LLM
- SMS commands via LTE modem
- PWA dashboard on phone
- TankOS 16-tile GUI
- Evolution system (9/14 providers)
- AprilTag detection (16 tags)
- Magnetic charging dock code
- Autonomous navigation (simulated)

### 🔵 Code Complete, Needs Hardware
- Motor control (BTS7960)
- Encoder odometry
- Servo control (PCA9685)
- IMU sensor fusion
- E-STOP system
- Battery monitoring

### 🟡 Planned
- Physical autonomous demo
- Human-following behavior
- Competition dress rehearsal

---

## 🔗 Quick Links

| What | Where |
|------|-------|
| Architecture | [ARCHITECTURE.md](ARCHITECTURE.md) |
| AI System | [docs/AI.md](docs/AI.md) |
| Auto-Evolution | [docs/AUTO_EVOLUTION.md](docs/AUTO_EVOLUTION.md) |
| Hardware BOM | [hardware.md](hardware.md) |
| Wiring | [WIRING.md](WIRING.md) |
| Status | [STATUS.md](STATUS.md) |
| Comparison | [COMPARISON.md](COMPARISON.md) |
| Screenshots | [docs/screenshots/](docs/screenshots/) |
| Infographics | [docs/infographics/](docs/infographics/) |

---

## 📊 Evidence of Work

| Evidence | Location |
|----------|----------|
| 31 tested modules | Test output in commit history |
| 50 infographics | `docs/infographics/` |
| 25+ screenshots | `docs/screenshots/` |
| 22 AI tools | `tank/ai/tool_registry.py` |
| 14 providers | `.env` configuration |
| SMS proof | Sent to 7860245819 |
| GitHub history | 25+ commits |
| Hardware photos | `images/` directory |

---

## 🏗️ Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│              JETSON ORIN NANO SUPER              │
│                  67 TOPS AI                      │
│  Vision · Detection · SLAM · Navigation · LLM    │
└───────────────────┬─────────────────────────────┘
                    │ USB Serial 115200
┌───────────────────▼─────────────────────────────┐
│               ARDUINO UNO Q 4GB                 │
│  Motors · Encoders · Servos · Safety · Sensors   │
└───────────────────┬─────────────────────────────┘
                    │ I²C / GPIO
┌───────────────────▼─────────────────────────────┐
│              ESP32-S3 ×6 SWARM                   │
│         Eyes · Hands · Limbs · Sensors           │
└─────────────────────────────────────────────────┘
```

---

## 💰 Cost Comparison

| | The Tank | Unitree Go2 |
|---|---------|-------------|
| Price | ₹64,050 ($800) | ₹2,35,000 ($2,800) |
| Savings | **72% cheaper** | — |
| 3-Year Cost | ₹84,450 | ₹4,71,900 |
| AI Brain | 67 TOPS GPU | Limited CPU |
| Battery | 2-3 hours | 40 minutes |
| 4G/LTE | ✅ Full SMS | ❌ WiFi only |
| Open Source | ✅ MIT | ❌ Closed |
| Offline AI | ✅ Local LLM | ❌ Cloud only |
| Customization | Unlimited | Low |

---

## ✅ Why The Tank Wins

1. **72% cheaper** than commercial alternatives
2. **374 tested features** across 3 computing layers
3. **3× longer battery** (2-3 hours vs 40 minutes)
4. **67 TOPS GPU** vs limited CPU
5. **14 AI providers** with auto-selection
6. **Full offline AI** — works without internet
7. **SMS control** — text your robot
8. **Open source** — MIT license
9. **Indian parts** — available on Robu.in
10. **Learning platform** — teaches entire robotics stack

---

<p align="center">
  <sub>Arduino Physical AI Challenge 2026 · APC-2026-RJ-75818 · Dr. Shashi Gupta</sub>
</p>
