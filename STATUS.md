# 🏆 STATUS — The Tank

> **Competition:** Arduino Physical AI Challenge 2026  
> **Registration:** APC-2026-RJ-75818  
> **Author:** Dr. Shashi Gupta

---

## ✅ What Works NOW

| Feature | How | Verified |
|---------|-----|----------|
| USB Camera streaming | DFRobot AI Camera → Jetson | ✅ JPEG frames |
| YOLOv8n detection | CUDA GPU inference | ✅ Objects detected |
| LiDAR scanning | LDROBOT LD19 via USB | ✅ 360° points |
| SMS commands | Quectel LTE modem | ✅ Messages sent |
| PWA Dashboard | 8-tab mobile control | ✅ Phone access |
| Tailscale mesh | 9 devices connected | ✅ All online |
| Evolution system | 9/14 cloud providers | ✅ AI ranking |
| Tool calling | 22 TankOS tools | ✅ LLM integration |
| AprilTag detection | 16 tags defined | ✅ Dock + nav |
| Autonomous navigation | A* + VFH avoidance | ✅ Simulated |
| Magnetic charging dock | 5-phase sequence | ✅ Code complete |
| TankOS GUI | 16-tile launcher | ✅ Android TV style |
| UNO Q TV launcher | 10-tile launcher | ✅ On Jetson desktop |
| Mobile PWA | Dashboard on phone | ✅ Deployed |

---

## 🔵 Implemented, Awaiting Physical Validation

| Feature | Code | Physical |
|---------|------|----------|
| Motor control (BTS7960) | ✅ | 🔵 Need motors |
| Encoder odometry | ✅ | 🔵 Need encoders |
| IMU (QMI8658/BNO055) | ✅ | 🔵 I²C connected |
| Servo control (PCA9685) | ✅ | 🔵 Need servos |
| E-STOP system | ✅ | 🔵 Need button |
| Battery monitoring | ✅ | 🔵 Need INA219 |
| Track slip detection | ✅ | 🔵 Need tracks |

---

## 📊 Pipeline Status

```
SENSE → PERCEIVE → FUSE → AI → DECIDE → ACT → VERIFY
  🟢      🟢        🟢     🟢     🟢      🔵     🟢
 Camera  YOLO    Kalman   LLM   Nav2    Motors  Vision
 LiDAR   Track   EKF    Tools  A*     Servos   Verify
 IMU     Detect  Grid   Chat   VFH    Safety   Status
```

---

## 🔑 API Keys (Evolution System)

| Provider | Key | Status |
|----------|-----|--------|
| OpenRouter | ✅ | Configured |
| Groq | ✅ | Configured |
| Gemini | ✅ | Configured |
| Mistral | ✅ | Configured |
| Cerebras | ✅ | Configured |
| Cohere | ✅ | Configured |
| Replicate | ✅ | Configured |
| HuggingFace | ✅ | Configured |
| Cloudflare | ✅ | Configured |
| OpenAI | ⬜ | Optional |
| Anthropic | ⬜ | Optional |
| Together | ⬜ | Optional |
| DeepInfra | ⬜ | Optional |
| SambaNova | ⬜ | Optional |

---

## 🖥 TankOS GUI Blueprint (robot-OS upgrade)

> Full blueprint + audit: [`docs/TANKOS_GUI_BLUEPRINT.md`](docs/TANKOS_GUI_BLUEPRINT.md) · screenshots in [`docs/screenshots/gui/`](docs/screenshots/gui/).

- ✅ **Core-7 live:** Home hub (8-tile launcher, ≤2 clicks) → Drive (joystick + E-stop + 5 modes)
  → Mission (builder + 9 types) → Map → Vision → AI Brain (decision + **Why?**) → Robot Health
- ✅ **Extras live:** ESP32 Fleet · Jetson dashboard (GPU/CPU/RAM/VRAM/AI FPS) · 🏆 Competition Mode
  (10-step DEMO) · 🚨 Event Center (filtered stream)
- ✅ **Wave 2 — 9 more screens** (`tank_os/windows/`): Sensor Fusion topology, Hardware Topology,
  Testing Center (12 tests → report), Power Dashboard (runtime/mission-cost/efficiency), Network,
  Security Center, Data/Analytics (11 sparklines), TV launcher, AI timeline — one GUI → EventBus →
  TankOS/ROS2/Hardware backends
- ✅ **17 new screens total**; 18 tests (`test_gui_blueprint_screens.py`) — full suite **318 passing**

## 🏗️ Next Steps

1. **Physical motor test** — Connect BTS7960 + motors + encoders
2. **Full pipeline demo** — Camera → YOLO → Navigation → Motors
3. **Competition dress rehearsal** — Full autonomous demo


---

## 13. 🧠 200-Item GUI + AI Features Plan ✅

Living tracker: [`docs/TANKOS_AI_200_PLAN.md`](docs/TANKOS_AI_200_PLAN.md) — 20 groups × 10 features,
each mapped to code with ✅/🔶/⬜/🧭 audit status.

**Shipped this pass (4 new screens, all tested):**

| Screen | Plan items | File |
|---|---|---|
| 🧠 AI Command Center | §1 #1–10 (live decision feed, confidence/uncertainty/latency meters, rejected actions, reasoning, active model) | `tank_os/windows/ai_command_center.py` |
| 🔥 AI Safety Center | §16 #151–160 (real-time risk, collision probability, human proximity, **safety veto visualization** — AI COMMAND → ANALYSIS → ❌ VETOED) | `tank_os/windows/ai_safety_center.py` |
| 🏆 Judge Mode | §20 #200 (one-screen AI system board: PERCEPTION/DECISION/LOCALIZATION/SAFETY/COMPUTE/POWER + live subsystem checks from RobotDoctor) | `tank_os/windows/judge_screen.py` |
| 🌐 Distributed-AI | §15 #141–150 (AI task-distribution map JETSON/UNO Q/ESP32, model locations, latency comparison, Jetson-offline → UNO Q fallback) | `tank_os/windows/distributed_ai_screen.py` |

- **322 tests passing** (4 new GUI smoke tests added; verified on VPS).
- Screenshots `58–61` + updated `contact_sheet_gui.png` in `docs/screenshots/gui/`.
- Every AI visualization exposes **WHAT / WHY / CONFIDENCE / SAFETY**; screens emit
  EventBus commands only (one GUI → multiple backends; safety stays deterministic).

4. **Report finalization** — Update DOCX with final specs