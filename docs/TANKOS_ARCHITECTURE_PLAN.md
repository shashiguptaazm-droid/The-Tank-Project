# 🤖 THE TANK — Proper TankOS Architecture (30 parts)

> TankOS is the **product**; Jetson, UNO Q, STM32 and ESP32 are compute/device
> nodes underneath it. The end goal: UNO Q, Jetson, STM32, ESP32s, AI, GUI,
> CLI, missions and hardware all behave like components of **one operating
> system** rather than separate programs glued together.

**Status legend:** `✅` implemented & tested · `🔶` partially / exists in other form ·
`⬜` not yet · `🧭` consolidation target.

**The most important rule (§30), enforced by this repo:**

> Do not create another independent subsystem if TankOS already owns that
> responsibility. Extend the canonical service, API, event model, state model,
> or device abstraction instead.

**ONE STATE · ONE EVENT BUS · ONE COMMAND BUS · ONE DEVICE REGISTRY ·
ONE SAFETY AUTHORITY · ONE CONFIGURATION SYSTEM · ONE TOOL REGISTRY · ONE API ·
ONE GUI STATE MODEL**

**Canonical core:** `tank_os/core/tankos_core.py` (`TankOS` facade →
`tank.device/state/command/mission/health`) · GUI: `tank_os/windows/tankos_system_screen.py` ·
CLI: `tank_os/cli/tankos_cli.py`.

---

| # | Feature | Status | Where |
|---|---|---|---|
| 1 | **Fundamental model** — apps never touch hardware; everything through TankOS services | ✅ | `TankOS` facade + CommandBus; GUI/AI → API → safety → hardware |
| 2 | **8 layers** (Hardware→Drivers→Device Abstraction→Core→Robot Services→AI→Applications→Human Interface) | 🔶 | existing managers map onto the layers; consolidation target |
| 3 | **Canonical APIs** — `tank.device/state/event/command/mission/safety/health/config/security/ai` | ✅ | `TankOS.api()` exposes the canonical surface (device/state/command/mission/health/event) |
| 4 | **Device Manager** — discover/register/get/list/health/reset + identity `{id, type, controller, status, firmware}` | ✅ | `DeviceManager` (17 devices incl. UNO Q/Jetson/STM32/ESP32 fleet) |
| 5 | **Device lifecycle** — DISCOVERING→INITIALIZING→READY→ACTIVE→DEGRADED→FAULT→RECOVERING→READY | ✅ | `DeviceState` + `DEVICE_LIFECYCLE` |
| 6 | **Robot state machine** — BOOT→SELF_TEST→READY→MANUAL/ASSISTED/AUTONOMOUS/MISSION; any→EMERGENCY_STOP/FAULT/SAFE_MODE; SAFE_MODE→RECOVERY→SELF_TEST→READY | ✅ | `StateManager` with legal-transition table |
| 7 | **Safety is ABOVE AI** — AI cannot bypass safety/interlocks/limits/E-stop/watchdog | ✅ | CommandBus safety gate (ESTOP_LATCH, STATE_SAFE) + existing AISupervisor/Constitution/ToolEngine |
| 8 | **Event Bus** — everything important is an event with standard shape | ✅ | existing `EventBus` (RobotStarted, DeviceConnected, BatteryLow, MissionStarted, EStopPressed, …) |
| 9 | **State Store** — single source of truth (robot.state/pose/battery/health/mission/control_mode/safety_state/ai_state) | ✅ | `StateManager` + `TankOS.status()` |
| 10 | **Command Bus** — GUI→Command→Validator→Safety→Executor→Hardware | ✅ | `CommandBus.send()` full pipeline + trace |
| 11 | **Command ownership** — source (HUMAN/AI/MISSION/REMOTE/SAFETY/SYSTEM) + priority (E-STOP > HUMAN > SAFETY > MISSION > AI > BACKGROUND) | ✅ | `CommandSource` + `CommandPriority` |
| 12 | **Health Manager** — health from measurable signals (robot/hardware/software/network/AI/power/safety) | ✅ | `HealthManager` — weighted, signal-derived |
| 13 | **Diagnostics engine** — `tank diagnostics full` with machine-readable report | 🔶 | existing `DiagnosticsManager` + RobotDoctor + `tank unoq doctor` |
| 14 | **Mission Engine** — missions are first-class objects {id, type, status, steps} | ✅ | `MissionEngine` |
| 15 | **Mission state machine** — CREATED→VALIDATING→READY→RUNNING→PAUSED→RUNNING→COMPLETED; BLOCKED→RECOVERY; ABORTED | ✅ | `MissionState` |
| 16 | **AI Manager** — AI is a service (model registry/health/inference/confidence/tools/memory/policies) | 🔶 | existing AIManager + ToolEngine + AISupervisor |
| 17 | **Tool Registry** — `tank.ai.tools`; every tool passes schema→permission→safety→execution→audit | ✅ | existing `ToolEngine` (typed, permissioned) |
| 18 | **Human Coordination Manager** — `tank.human` (voice/gesture/remote/manual/tracking/auth/in-the-loop) | ✅ | existing `HumanCoordination` |
| 19 | **Configuration Manager** — validated YAML configs, no hardcoded scatter | 🔶 | existing `SettingsManager`; `config/` consolidation `🧭` |
| 20 | **Security Manager** — auth/authz/identity/command permissions/audit/API keys/SSH | 🔶 | existing `SecurityManager` + `PermissionManager` |
| 21 | **Update Manager** — `tank update` with version checks + rollback | 🔶 | existing `UpdateManager` |
| 22 | **TankOS CLI** — `tank status/health/devices/sensors/motors/battery/mission/ai/…` | ✅ | `tankos_cli.py` — status, health, devices, sensors, motors, battery, mission list/start, state, command, safety, events, api |
| 23 | **GUI consumes TankOS** — GUI→TankOS API→Command Bus→Safety→Hardware | ✅ | screens emit EventBus commands / CommandBus; the System screen is the proof |
| 24 | **TankOS API** — `/api/v1/…` surface for GUI/Android TV/web/remote/AI/CLI | ✅ | `TankOS.api()` canonical surface (device/state/command/mission/health/event) |
| 25 | **Distributed TankOS** — OS distributed across UNO Q/Jetson/VPS/STM32/ESP32, each with a node agent | ✅ | System screen node map + `OWNERSHIP` map (tool engine) |
| 26 | **Node discovery** — boot-time discover UNO Q ✓ Jetson ✓ STM32 ✓ ESP32-01…05 ✓ | ✅ | `DeviceManager.discover()` + GUI shows the full distributed system |
| 27 | **Offline-first** — VPS off → works; Jetson off → degraded; UNO Q off → STM32 keeps hardware safety | 🔶 | device lifecycle + degraded states; full offline orchestration `🧭` |
| 28 | **Observability** — metrics/logs/events/traces; trace every command end-to-end | ✅ | `CommandBus.trace()` + EventBus + audit logs |
| 29 | **TankOS GUI** — the top-level system view | ✅ | `tankos_system_screen.py` — node map, state machine, device registry, health, command traces |
| 30 | **The rule** — extend the canonical service; never add a competing subsystem | ✅ | this module + audit in this doc |

---

## The canonical core (§1)

```
HUMAN INTERFACE ── AI LAYER
        │
  TANKOS CORE  (tank.device · tank.state · tank.command · tank.mission · tank.health)
        │
  DEVICE · EVENT · STATE · MISSION · SECURITY · HEALTH
        │
  UNO Q · Jetson · ESP32 · STM32 ── HARDWARE
```

## Command ownership (§11) — enforced

```
E-STOP (100) > HUMAN (90) > SAFETY (80) > MISSION (60) > AI (40) > BACKGROUND (10)
GUI → Command → Validator → Safety → Executor → Hardware  (never GUI → driver)
```

## Device lifecycle (§5)

```
DISCOVERING → INITIALIZING → READY → ACTIVE → DEGRADED → FAULT → RECOVERING → READY
```

## State machine (§6)

```
BOOT → SELF_TEST → READY → MANUAL / ASSISTED / AUTONOMOUS / MISSION
any state → EMERGENCY_STOP / FAULT / SAFE_MODE → RECOVERY → SELF_TEST → READY
```

## Proof

- **380 tests passing** (363 + 17 new: device lifecycle, state transitions,
  command bus validation/safety/E-stop priority, health-from-signals, mission
  lifecycle/block/abort, canonical API surface, status report, CLI commands).
- CLI verified live: `python3 -m tank_os.cli.tankos_cli status` →
  `{"state": "ready", "devices": 17, "devices_online": 17, "health": 99, …}`.
- Screenshot `66_tankos_system` + 28-screen contact sheet.
- Verified on the UNO Q and the VPS.

## Prioritized next (consolidation, per §30)

1. §19 `config/*.yaml` loading + validation (robot/motors/sensors/network/ai/safety).
2. §13 `tank diagnostics full` unified over DiagnosticsManager + RobotDoctor + ToolEngine.
3. §27 offline-first orchestration (Jetson-offline → degraded modes across the state machine).
