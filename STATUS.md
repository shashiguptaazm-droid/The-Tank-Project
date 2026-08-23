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

- **328 tests passing** (wave-2 consolidation added 6 more tests; verified on VPS).
- **Pass 2 — consolidation shipped:** unified chronological event replay in the Event
  Center (▶ PLAY/⏸ PAUSE, 0.25×/1×/4×, progress + current-event highlight — plan §2
  #20), quantified AI power-saving recommendations on the Power Dashboard (§13 #130,
  e.g. "VLM 5→1 Hz ≈ +~11 min runtime"), and the runnable benchmark suite in Developer
  mode (§17 #162–165 — AI model / vision / navigation / sensor-fusion).
- Screenshots `58–61` + updated `contact_sheet_gui.png` in `docs/screenshots/gui/`.
- Every AI visualization exposes **WHAT / WHY / CONFIDENCE / SAFETY**; screens emit
  EventBus commands only (one GUI → multiple backends; safety stays deterministic).



---

## 14. 👤 Human Coordination AI (100 features) + 🚀 25 Originality Ideas ✅

Trackers: [`docs/HUMAN_COORDINATION_PLAN.md`](docs/HUMAN_COORDINATION_PLAN.md) ·
[`docs/TANK_ORIGINALITY_PLAN.md`](docs/TANK_ORIGINALITY_PLAN.md)

**Shipped this pass (2 core modules + 3 screens, all tested):**

| Module / Screen | What it delivers |
|---|---|
| `tank_os/core/human_coordination.py` | Person registry (distance/direction/velocity/presence/zones/confidence), interaction modes (FOLLOW/STOP/ESCORT/MEET/RETURN…), control authority chain (safety > human > mission > autonomy), human-in-the-loop requests (AI proposes → human APPROVE/MODIFY/REJECT), **"Ask the human"** low-confidence clarifications |
| `tank_os/core/robot_constitution.py` | The **Robot Constitution** policy engine (8 priority articles, vetoes carry the triggered article) + the **AI Debate** (vision/nav/safety/resource vote, safety wins, explainable) + explicit command chain |
| 👤 Human Control Center (`62`) | Person card + FOLLOW/STOP/ESCORT/RETURN buttons, CONTROL AUTHORITY panel, AI REQUEST approve/reject/modify, ASK THE HUMAN LEFT/RIGHT route choice, interaction history |
| 🌟 Constitution + AI Debate (`63`) | 8 articles with live triggered state, debate votes (SAFETY STOP → FINAL STOP), command chain |
| 🧠 Robot Knowledge Map (`64`) | Environment + knowledge-confidence map (North corridor 96% … Stair area 22%), live RobotDoctor health panel |

- **345 tests passing** (17 new: tracking, modes, authority, approve/reject/modify,
  ask-the-human, 5 constitution veto classes, debate, command chain; verified on VPS).
- Screenshots `62–64` + contact sheet (26 screens) in `docs/screenshots/gui/`.



---

## 15. 🧠 Proper AI Tool-Calling Architecture (20-part plan) ✅

Tracker: [`docs/TANK_TOOL_CALLING_PLAN.md`](docs/TANK_TOOL_CALLING_PLAN.md)

**The fundamental rule (enforced):** `Human → AI → Tool Validator → Permission +
Safety → Tool Executor → UNO Q/Jetson/ESP32/STM32 → Result → AI`. Never
`LLM → arbitrary shell command → motor`.

**Shipped this pass:**

| Piece | What it delivers |
|---|---|
| `tank_os/core/tool_engine.py` | Typed, permissioned pipeline: `ToolSpec` registry (risk tiers read-only/low/controlled/high/emergency), agent roles (Observer/Assistant/Navigator/Maintenance/Admin), schema + **sandbox validator** (`max_speed_mps ≤ 0.5`, `distance ≤ 5 m` — rejects invented values), safety interlocks, high-risk `NEEDS_APPROVAL` gate, deterministic emergency path, standardized `ToolResult`, failure recovery (`OBSTACLE_DETECTED → replan`), audit log, tool chaining, discovery/capabilities, ownership map (vision→Jetson, robot→UNO Q, sensor→ESP32, motor→STM32), and the **AI Tool Composer** |
| `tank_os/windows/tool_graph_screen.py` | Live tool graph — USER REQUEST → AI → tool nodes ✓ + audit log + composer readiness demo ("PATROL READINESS: 94%") |
| Binding | Adopts the existing `agent_framework.ToolRegistry` (1,966 script tools discovered) |

- **363 tests passing** (18 new tool-engine tests; verified on VPS).
- Screenshot `65_ai_tool_graph` + 27-screen contact sheet in `docs/screenshots/gui/`.



---

## 16. 🤖 Proper TankOS Architecture (30-part plan) ✅

Tracker: [`docs/TANKOS_ARCHITECTURE_PLAN.md`](docs/TANKOS_ARCHITECTURE_PLAN.md)

TankOS is the product; UNO Q / Jetson / STM32 / ESP32 are nodes underneath it.
**ONE STATE · ONE EVENT BUS · ONE COMMAND BUS · ONE DEVICE REGISTRY · ONE
SAFETY AUTHORITY · ONE CONFIGURATION · ONE TOOL REGISTRY · ONE API.**

**Shipped this pass:**

| Piece | What it delivers |
|---|---|
| `tank_os/core/tankos_core.py` | The canonical core — `TankOS` facade with `tank.device / state / command / mission / health`: **DeviceManager** (17 devices, lifecycle DISCOVERING→…→FAULT→RECOVERING→READY), **StateManager** (robot state machine BOOT→SELF_TEST→READY→MANUAL/ASSISTED/AUTONOMOUS/MISSION, any→EMERGENCY_STOP/FAULT/SAFE_MODE→RECOVERY), **CommandBus** (source+priority: E-STOP>HUMAN>SAFETY>MISSION>AI>BACKGROUND; validate→safety→execute with end-to-end traces), **HealthManager** (health from measurable signals), **MissionEngine** (first-class missions with CREATED→…→COMPLETED/ABORTED) |
| `tank_os/cli/tankos_cli.py` | The **`tank` CLI**: status, health, devices, sensors, motors, battery, mission list/start, state, command, safety (estop/clear), events, api |
| `tank_os/windows/tankos_system_screen.py` | The top-level system GUI — distributed node map (UNO Q/Jetson/STM32/ESP32/VPS), canonical state machine, device registry with lifecycle, health dashboard, command observability |

- **380 tests passing** (17 new; verified on VPS) + CLI verified live.
- Screenshot `66_tankos_system` + 28-screen contact sheet.

4. **Report finalization** — Update DOCX with final specs