# 🤖 The Tank — Overall GUI Blueprint

> The TankOS GUI should feel like a **robot operating system**, not a pile
> of separate dashboards. One GUI → multiple backends: `TankOS → ROS 2 →
> Hardware API → EventBus → SQLite`. This page maps the 15-mode blueprint
> to the live TankOS screens and tracks what's shipped.

**Status legend:** `✅` shipped (live screen) · `🔶` partial / existing screen ·
`⬜` not yet · `🧭` consolidation target.

**Architecture rule (enforced):** the GUI never touches PWM/safety directly —
it emits commands on the EventBus; the robot layer + `AISupervisor` decide.
Voice and AI go through `Voice → intent → safety validation → action`, never
`Voice → motor PWM`.

---

## 🎯 The core-7 experience (shipped this pass)

```
HOME → DRIVE → MISSION → MAP → VISION → AI → HEALTH
```

Every screen reachable in **≤ 2 clicks** via the Home launcher grid and the
bottom dock.

| Screen | Dock | Blueprint § | Status |
|--------|------|-------------|--------|
| Home hub | 🏠 | Main Home | ✅ 8-tile launcher + live view |
| Drive | 🕹 | Drive UI | ✅ NEW `drive_screen.py` |
| Mission | 🎯 | Mission Control | ✅ NEW `mission_screen.py` |
| Map | 🗺 | Live Map | ✅ `navigation_screen.py` (existing) |
| Vision | 📷 | Vision | ✅ `camera_screen.py` (existing) |
| AI Brain | 🧠 | AI Brain | ✅ NEW `ai_brain_screen.py` |
| Robot Health | 🩺 | Robot Health | ✅ NEW `health_screen.py` |

## 🗺 The full 15-mode map

| # | Mode | Screen | Status | Notes |
|---|------|--------|--------|-------|
| 1 | Home | `home` | ✅ | **8 launcher tiles** (DRIVE/AI/MAP/VISION/MISSION/SENSORS/SYSTEM/TV) + camera, avatar, live map, health |
| 2 | Drive | `drive` | ✅ NEW | Virtual joystick · track L/R · velocity · heading · odometry · motor current/temp · E-stop · 5 modes (MANUAL/ASSISTED/AUTONOMOUS/PRECISION/EMERGENCY) |
| 3 | Mission | `mission` | ✅ NEW | Mission builder chain (START→WAYPOINT→SCAN→DETECT→RETURN) · 9 mission types · START MISSION → EventBus |
| 4 | Live Map | `navigation` | 🔶 | Existing nav screen (pose, waypoints, map widget) — LiDAR overlay 🧭 |
| 5 | Vision | `camera` | 🔶 | Existing camera + detections — FPS/latency/object list 🧭 |
| 6 | AI Brain | `brain` | ✅ NEW | CURRENT MISSION · PERCEPTION (live health rows) · DECISION · RISK · CONFIDENCE · ACTION + **"Why?" button** with plain-language explanation |
| 7 | Sensors | `diagnostics` | 🔶 | Existing diagnostics — sensor topology diagram 🧭 |
| 8 | Robot Health | `health` | ✅ NEW | 10-subsystem board from live **RobotDoctor** · overall score · tap tile → findings · Run Diagnosis |
| 9 | Power | `power` | 🔶 | Existing power screen — per-device consumption 🧭 |
| 10 | Hardware | `usb` | 🔶 | Existing USB tree — hardware topology graph 🧭 |
| 11 | Network | `settings`/`diagnostics` | 🔶 | Existing — dedicated network screen 🧭 |
| 12 | ESP32 Fleet | `fleet` | ✅ NEW | Live **ESP32FleetManager** board cards (host/serial/path/heartbeats/firmware/telemetry) + online summary |
| 13 | Jetson | `jetson` | ✅ NEW | GPU/CPU/RAM/VRAM bars · temp · power · AI pipeline FPS (YOLO/TRACK/DEPTH/SLAM) |
| 14 | TV / Media | `files` + web | 🔶 | UNO Q TV kiosk (`cloud-stack :8200`) — see `docs/UNOQ_ANDROID_TV.md` |
| 15 | Developer | `developer` | ✅ | Existing dev screen |

## Plus the blueprint's extra modes (shipped)

| Mode | Screen | Status |
|------|--------|--------|
| 🏆 Competition Mode | `competition` | ✅ NEW — one clean screen: THE TANK title, live subsystem checklist (✓/✗), battery, mission, status, confidence + **DEMO MODE** button (10-step walkthrough) |
| 🚨 Event Center | `events` | ✅ NEW — unified EventBus stream with filters (ALL/SAFETY/AI/HARDWARE/NETWORK/NAVIGATION), colour-coded rows |
| 🎬 AI Explainability | `brain` | ✅ "Why?" button renders the decision rationale |
| 🧪 Testing Center | `tank unoq self-test` + `doctor --inject` | 🔶 CLI; GUI tab 🧭 |
| 📊 Data / Analytics | `diagnostics` | 🔶 history exists; graphs 🧭 |
| 🔐 Security Center | `security` | 🔶 existing |
| 🎙 Voice Interface | `voice` | 🔶 existing — goes through intent → safety → action |

---

## Design language

Dark industrial + minimal neon accents + large typography. Professional
primary UI; futuristic styling only as a secondary layer. One visual
language across all screens (consistent card style: `rgba(255,255,255,0.04)`
panels, `#00BFFF` accents, `#0D0D1A` background).

## One GUI → multiple backends

```
TANK GUI (TankOS shell)
        │
   ┌────┴────┐
   │ GUI API │  ← EventBus commands (cmd_drive, mission_start, estop…)
   └────┬────┘
        │
  ┌─────┼─────────┐
  ↓     ↓         ↓
TankOS  ROS 2  Hardware API
  │     │         │
  ↓     ↓         ↓
UNO Q  JETSON   ESP32
  │     └────┬────┘
  └──────────┼─────────┘
             ↓
        EVENT BUS
             ↓
      SQLite / Logs
```

The GUI stays decoupled from individual devices: it emits events, managers
(`RobotDoctor`, `ESP32FleetManager`, `PowerManager`, `AISupervisor`) do the
work, and the EventBus + SQLite keep history.

## Screenshots (captured live)

| # | Screen | File |
|---|--------|------|
| 40 | Home hub (8 tiles) | [`docs/screenshots/gui/40_home_hub.png`](screenshots/gui/40_home_hub.png) |
| 41 | Drive | [`docs/screenshots/gui/41_drive.png`](screenshots/gui/41_drive.png) |
| 42 | Mission Control | [`docs/screenshots/gui/42_mission.png`](screenshots/gui/42_mission.png) |
| 43 | AI Brain | [`docs/screenshots/gui/43_ai_brain.png`](screenshots/gui/43_ai_brain.png) |
| 44 | Robot Health | [`docs/screenshots/gui/44_robot_health.png`](screenshots/gui/44_robot_health.png) |
| 45 | ESP32 Fleet | [`docs/screenshots/gui/45_esp32_fleet.png`](screenshots/gui/45_esp32_fleet.png) |
| 46 | Jetson Dashboard | [`docs/screenshots/gui/46_jetson.png`](screenshots/gui/46_jetson.png) |
| 47 | Competition Mode | [`docs/screenshots/gui/47_competition.png`](screenshots/gui/47_competition.png) |
| 48 | Event Center | [`docs/screenshots/gui/48_event_center.png`](screenshots/gui/48_event_center.png) |

Contact sheet: [`docs/screenshots/gui/contact_sheet_gui.png`](screenshots/gui/contact_sheet_gui.png)

## Proof

* **10 new tests** (`test_gui_blueprint_screens.py`) — every screen builds
  and paints offscreen; home has the 8 tiles; dock exposes core-7 + extras.
* **Full suite: 310 passing** (300 + 10 new).
* Shell navigation verified for all 8 new screens + home-tile EventBus
  navigation.
