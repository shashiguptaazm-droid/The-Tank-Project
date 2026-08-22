# Tank — Project Status

> Audit date: 2026-08-23 · Competition: Arduino Physical AI Challenge 2026
> Registration: APC-2026-RJ-75818

---

## Current Architecture

```
the tank project/
├── tank/                    ← NEW: Core software platform (competition-grade)
│   ├── core/                Event bus, state machine, config, decision engine
│   ├── perception/          Sensor abstraction + fusion layer
│   ├── ai/                  AI engine, detection, VPS client
│   ├── control/             Motor, servo, safety controller
│   ├── ui/                  Dashboard, telemetry, event log
│   ├── networking/          API, websocket, auth
│   ├── storage/             Events, telemetry, config persistence
│   ├── simulation/          Mock sensors, deterministic demo data
│   ├── tests/               Unit + integration tests
│   └── docs/                Architecture docs
│
├── tank_os/                 ← EXISTING: TankOS GUI + managers (PySide6)
├── tank_ws/src/             ← EXISTING: 26 ROS2 ament_python packages
├── scripts/                 ← EXISTING: 137 Python CLI utilities
├── firmware/                ← EXISTING: ESP32-S3 eye firmware
├── cad/                     ← EXISTING: OpenSCAD chassis + STL exports
├── images/                  ← EXISTING: SVG diagrams (7 diagrams)
├── hardware/                ← EXISTING: Hardware catalog SVG
└── docs/                    ← EXISTING: Architecture docs
```

---

## Languages

| Language | Files | Purpose |
|----------|-------|---------|
| Python | 655 | TankOS, ROS2 packages, scripts, AI |
| Shell | 14 | Installers, provisioning |
| Arduino | 58 | ESP32-S3 eye firmware, sensor tools |
| OpenSCAD | 3 | Parametric chassis design |
| YAML | ~30 | ROS2 launch/config |
| JSON | ~40 | TankOS config, evolution data |

## Frameworks & Libraries

| Framework | Where | Purpose |
|-----------|-------|---------|
| ROS2 Humble | tank_ws/src/ | 26 robot packages (motion, vision, nav, etc.) |
| PySide6/Qt6 | tank_os/shell/ | 13-screen GUI |
| FastAPI | tank_os/agent_framework/ | REST API server (:8085) |
| SQLAlchemy | tank_os/internet/ | Database layer |
| OpenCV | tank_vision | Camera processing |
| YOLOv8 | tank_vision | Object detection |
| llama.cpp | tank_assistant | Local LLM inference |
| Whisper | tank_speech | Speech-to-text |
| Piper TTS | tank_speech | Text-to-speech |
| sentence-transformers | tank_memory | Vector embeddings |
| sqlite-vec | tank_memory | Vector database |

## Entry Points

| Entry Point | File | Purpose |
|-------------|------|---------|
| TankOS GUI | `python3 -m tank_os.shell.main` | Main GUI shell |
| TankOS CLI | `python3 -m tank_os.shell.terminal.cli` | Terminal interface |
| Agent API | `python3 -m tank_os.agent_framework.server` | FastAPI REST (:8085) |
| Command Bridge | `ros2 launch tank_bringup robot.launch.py` | ROS2 robot stack |
| **Tank Platform** | `python3 -m tank.main` | **NEW: Competition platform** |

## Working Features

- ✅ TankOS 13-screen GUI (PySide6/Qt6)
- ✅ 35 AI-powered managers (EventBus, Vision, Memory, Emotion, etc.)
- ✅ 14-provider evolution system with circuit breaker
- ✅ 400+ CLI utilities (diagnostics, calibration, OTA, fleet)
- ✅ 26 ROS2 packages (motion, vision, navigation, speech, memory)
- ✅ ESP32-S3 eye firmware (GC9A01 round LCD)
- ✅ Multi-provider LLM with offline fallback (GGUF)
- ✅ Daily self-evolution cycle
- ✅ Voice interface (Whisper STT + Piper TTS + openWakeWord)
- ✅ 3D-printable chassis (OpenSCAD, STL, 3MF)

## Broken / Incomplete

- ⚠️ ROS2 packages assume Raspberry Pi GPIO (now Arduino)
- ⚠️ motor_controller uses gpiozero (needs Arduino serial bridge)
- ⚠️ Some error messages still reference "Pi 5"
- ⚠️ Camera publisher uses libcamera (needs USB UVC path)
- ⚠️ No unified perception→decision→action pipeline
- ⚠️ No simulation mode for testing without hardware
- ⚠️ No competition demo mode
- ⚠️ No structured event logging
- ⚠️ No VPS AI client (cloud fallback)
- ⚠️ No sensor fusion layer

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| python3 | ≥3.10 | Core runtime |
| rclpy | humble | ROS2 Python client |
| PySide6 | ≥6.5 | GUI framework |
| fastapi | ≥0.100 | REST API |
| uvicorn | ≥0.23 | ASGI server |
| opencv-python | ≥4.8 | Camera/vision |
| ultralytics | ≥8.0 | YOLOv8 detection |
| sentence-transformers | ≥2.2 | Embeddings |
| sqlite-vec | ≥0.1 | Vector DB |
| aiohttp | ≥3.9 | Async HTTP (VPS client) |
| pyserial | ≥3.5 | Arduino serial bridge |

## Known Bugs

1. `tank_motion/motor_controller.py` — gpiozero import fails without Pi GPIO
2. `tank_sensors/imu_publisher.py` — BNO055 requires I²C (Arduino handles this)
3. `tank_vision/camera_publisher.py` — libcamera path hardcoded
4. `tank_display/oled_hal.py` — luma.oled fails on non-Pi systems
5. Some test files reference `provision_pi5.sh`

## Missing Components (Competition-Critical)

1. **Unified perception pipeline** — no sensor abstraction layer
2. **Event-driven architecture** — no central event bus (TankOS has one, but it's GUI-only)
3. **Decision engine** — AI output goes directly to commands
4. **Safety layer** — only ROS2 watchdog, no software safety state machine
5. **VPS client** — no cloud AI fallback
6. **Simulation mode** — can't test without hardware
7. **Demo mode** — no deterministic competition demo
8. **Structured logging** — no event/decision/safety logs
9. **Dashboard** — TankOS GUI exists but no real-time competition dashboard
10. **Sensor fusion** — sensors run independently, no fusion layer

## Competition-Critical Improvements (Priority Order)

1. 🔴 Build `tank/` core platform (event bus, state machine, config)
2. 🔴 Build sensor abstraction + fusion
3. 🔴 Build AI engine + VPS client
4. 🔴 Build decision engine + safety layer
5. 🔴 Build competition dashboard
6. 🔴 Build demo mode + simulation
7. 🟡 Add structured logging + observability
8. 🟡 Add automated tests
9. 🟢 Optimize performance
10. 🟢 Polish + documentation


---

## Declaration

> **This is our original, unpublished work.** The Arduino® UNO™ Q is the primary board. All team members are aware of and consent to this submission. We agree to the Terms & Conditions, including granting Robu.in and Arduino® the right to showcase this project for promotional and educational purposes.

- **Registration ID:** APC-2026-RJ-75818
- **Date:** 22 August 2026
