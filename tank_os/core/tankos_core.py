"""TankOS Core — the canonical robot operating platform.

The fundamental model (30-part architecture plan):

    HUMAN INTERFACE  ──  AI LAYER
               │
         TANKOS CORE
               │
    DEVICE · EVENT · STATE · MISSION · SECURITY · HEALTH
               │
    UNO Q  ·  Jetson  ·  ESP32  ·  STM32  ──  HARDWARE

Rule: applications never directly manipulate hardware — everything goes
through TankOS services. Canonical API surface (one of each):

    tank.device · tank.state · tank.command · tank.mission · tank.health

ONE STATE · ONE EVENT BUS · ONE COMMAND BUS · ONE DEVICE REGISTRY ·
ONE SAFETY AUTHORITY · ONE TOOL REGISTRY · ONE API.

Components (all in this module, deterministic, unit-testable):
- DeviceManager — discovery, register, lifecycle
  (DISCOVERING→INITIALIZING→READY→ACTIVE→DEGRADED→FAULT→RECOVERING→READY).
- StateManager — the single authoritative robot state machine
  (BOOT→SELF_TEST→READY→MANUAL/ASSISTED/AUTONOMOUS/MISSION; any→
  EMERGENCY_STOP/FAULT/SAFE_MODE; SAFE_MODE→RECOVERY→SELF_TEST→READY).
- CommandBus — command ownership (source + priority) with
  validate → safety → execute; never GUI→driver directly.
- HealthManager — health from measurable signals, not an arbitrary number.
- MissionEngine — first-class mission objects with a state machine.
- TankOS API facade — the `tank.*` canonical interface.
"""

from __future__ import annotations

import datetime
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from tank_os.core.event_bus import Event, EventBus


# ---------------------------------------------------------------------------
# Device lifecycle (§5)
# ---------------------------------------------------------------------------
class DeviceState(str, Enum):
    DISCOVERING = "discovering"
    INITIALIZING = "initializing"
    READY = "ready"
    ACTIVE = "active"
    DEGRADED = "degraded"
    FAULT = "fault"
    RECOVERING = "recovering"
    OFFLINE = "offline"


DEVICE_LIFECYCLE = [
    DeviceState.DISCOVERING, DeviceState.INITIALIZING, DeviceState.READY,
    DeviceState.ACTIVE, DeviceState.DEGRADED, DeviceState.FAULT,
    DeviceState.RECOVERING, DeviceState.READY,
]


@dataclass
class Device:
    """One hardware device with a canonical identity (§4)."""

    id: str
    type: str
    controller: str = "unoq"          # stm32 / unoq / jetson / esp32
    status: DeviceState = DeviceState.READY
    firmware: str = "1.0.0"
    health: float = 1.0
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "type": self.type, "controller": self.controller,
            "status": self.status.value, "firmware": self.firmware,
            "health": round(self.health, 2), "meta": self.meta,
        }


# ---------------------------------------------------------------------------
# Robot state machine (§6)
# ---------------------------------------------------------------------------
class RobotState(str, Enum):
    BOOT = "boot"
    SELF_TEST = "self-test"
    READY = "ready"
    MANUAL = "manual"
    ASSISTED = "assisted"
    AUTONOMOUS = "autonomous"
    MISSION = "mission"
    EMERGENCY_STOP = "emergency-stop"
    FAULT = "fault"
    SAFE_MODE = "safe-mode"
    RECOVERY = "recovery"


#: legal transitions; any state may go to EMERGENCY_STOP / FAULT / SAFE_MODE.
_TRANSITIONS: Dict[RobotState, set] = {
    RobotState.BOOT: {RobotState.SELF_TEST, RobotState.FAULT},
    RobotState.SELF_TEST: {RobotState.READY, RobotState.FAULT},
    RobotState.READY: {RobotState.MANUAL, RobotState.ASSISTED,
                       RobotState.AUTONOMOUS, RobotState.MISSION},
    RobotState.MANUAL: {RobotState.READY, RobotState.ASSISTED,
                        RobotState.AUTONOMOUS, RobotState.MISSION},
    RobotState.ASSISTED: {RobotState.READY, RobotState.MANUAL,
                          RobotState.AUTONOMOUS, RobotState.MISSION},
    RobotState.AUTONOMOUS: {RobotState.READY, RobotState.MANUAL,
                            RobotState.MISSION},
    RobotState.MISSION: {RobotState.READY, RobotState.AUTONOMOUS},
    RobotState.EMERGENCY_STOP: {RobotState.READY, RobotState.SAFE_MODE},
    RobotState.FAULT: {RobotState.RECOVERY},
    RobotState.SAFE_MODE: {RobotState.RECOVERY},
    RobotState.RECOVERY: {RobotState.SELF_TEST, RobotState.READY},
}


# ---------------------------------------------------------------------------
# Command ownership (§11)
# ---------------------------------------------------------------------------
class CommandSource(str, Enum):
    HUMAN = "human"
    AI = "ai"
    MISSION = "mission"
    REMOTE = "remote"
    SAFETY = "safety"
    SYSTEM = "system"


class CommandPriority(int, Enum):
    ESTOP = 100
    HUMAN = 90
    SAFETY = 80
    MISSION = 60
    AI = 40
    BACKGROUND = 10


@dataclass
class Command:
    command: str
    source: CommandSource
    args: dict = field(default_factory=dict)
    priority: CommandPriority = CommandPriority.AI

    def to_dict(self) -> dict:
        return {
            "command": self.command, "source": self.source.value,
            "args": self.args, "priority": int(self.priority),
        }


# ---------------------------------------------------------------------------
# Mission (§14–15)
# ---------------------------------------------------------------------------
class MissionState(str, Enum):
    CREATED = "created"
    VALIDATING = "validating"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    BLOCKED = "blocked"
    RECOVERY = "recovery"
    COMPLETED = "completed"
    ABORTED = "aborted"


@dataclass
class Mission:
    id: str
    type: str
    status: MissionState = MissionState.CREATED
    steps: List[str] = field(default_factory=list)
    progress: int = 0
    created: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "type": self.type, "status": self.status.value,
            "steps": self.steps, "progress": self.progress,
        }


# ---------------------------------------------------------------------------
# DeviceManager (§4–5)
# ---------------------------------------------------------------------------
class DeviceManager:
    """Owns hardware discovery + the canonical device registry."""

    def __init__(self) -> None:
        self._devices: Dict[str, Device] = {}
        self._bus = EventBus()

    def discover(self) -> List[Device]:
        """Boot-time node discovery (§26): UNO Q ✓ Jetson ✓ STM32 ✓ ESP32 fleet."""
        spec = [
            ("unoq", "compute", "unoq", "2.1.0"),
            ("jetson", "compute", "jetson", "5.1.2"),
            ("stm32", "mcu", "stm32", "1.4.2"),
            ("motor.left", "motor", "stm32", "1.4.2"),
            ("motor.right", "motor", "stm32", "1.4.2"),
            ("servo.bank", "servo", "unoq", "1.0.0"),
            ("imu", "imu", "stm32", "1.0.0"),
            ("lidar", "lidar", "unoq", "2.3.0"),
            ("camera", "camera", "jetson", "3.0.1"),
            ("battery", "battery", "unoq", "1.1.0"),
            ("display", "display", "unoq", "1.0.0"),
            ("network", "network", "unoq", "2.0.0"),
            ("esp32.01", "esp32", "esp32", "1.2.0"),
            ("esp32.02", "esp32", "esp32", "1.2.0"),
            ("esp32.03", "esp32", "esp32", "1.2.0"),
            ("esp32.04", "esp32", "esp32", "1.2.0"),
            ("esp32.05", "esp32", "esp32", "1.2.0"),
        ]
        for dev_id, dtype, ctrl, fw in spec:
            self.register(Device(id=dev_id, type=dtype, controller=ctrl,
                                 firmware=fw))
            self._bus.emit(Event("device_connected",
                                 {"summary": f"{dev_id} online", "severity": "info"}))
        return self.list()

    def register(self, device: Device) -> Device:
        self._devices[device.id] = device
        return device

    def unregister(self, dev_id: str) -> None:
        self._devices.pop(dev_id, None)
        self._bus.emit(Event("device_disconnected",
                             {"summary": f"{dev_id} offline", "severity": "warn"}))

    def get(self, dev_id: str) -> Optional[Device]:
        return self._devices.get(dev_id)

    def list(self, device_type: Optional[str] = None) -> List[Device]:
        devs = list(self._devices.values())
        if device_type:
            devs = [d for d in devs if d.type == device_type]
        return devs

    def health(self, dev_id: str) -> Optional[float]:
        d = self._devices.get(dev_id)
        return d.health if d else None

    def reset(self, dev_id: str) -> Optional[Device]:
        d = self._devices.get(dev_id)
        if d is None:
            return None
        d.status = DeviceState.RECOVERING
        d.status = DeviceState.READY
        d.health = 1.0
        self._bus.emit(Event("device_reset",
                             {"summary": f"{dev_id} reset → ready",
                              "severity": "info"}))
        return d

    def set_state(self, dev_id: str, state: DeviceState,
                  health: Optional[float] = None) -> Optional[Device]:
        d = self._devices.get(dev_id)
        if d is None:
            return None
        d.status = state
        if health is not None:
            d.health = max(0.0, min(1.0, health))
        return d


# ---------------------------------------------------------------------------
# StateManager (§6, §9)
# ---------------------------------------------------------------------------
class StateManager:
    """Single authoritative robot state."""

    def __init__(self) -> None:
        self._state = RobotState.BOOT
        self._bus = EventBus()
        self._history: List[str] = []

    def state(self) -> RobotState:
        return self._state

    def transition(self, target: RobotState) -> bool:
        current = self._state
        if target in (RobotState.EMERGENCY_STOP, RobotState.FAULT,
                      RobotState.SAFE_MODE):
            allowed = True                      # any state may go safe
        else:
            allowed = target in _TRANSITIONS.get(current, set())
        if not allowed:
            return False
        self._state = target
        self._history.append(f"{time.strftime('%H:%M:%S')} → {target.value}")
        if len(self._history) > 50:
            self._history.pop(0)
        self._bus.emit(Event("robot_state",
                             {"summary": f"robot state → {target.value}",
                              "severity": "info"}))
        return True

    def boot_sequence(self) -> None:
        """BOOT → SELF_TEST → READY."""
        self._state = RobotState.BOOT
        self.transition(RobotState.SELF_TEST)
        self.transition(RobotState.READY)

    def history(self, limit: int = 20) -> List[str]:
        return list(self._history[-limit:])

    def can_accept_commands(self) -> bool:
        return self._state in (RobotState.READY, RobotState.MANUAL,
                               RobotState.ASSISTED, RobotState.AUTONOMOUS,
                               RobotState.MISSION)


# ---------------------------------------------------------------------------
# CommandBus (§10–11)
# ---------------------------------------------------------------------------
class CommandBus:
    """Commands flow GUI/AI → validate → safety → execute. Never direct."""

    def __init__(self, state: StateManager, devices: DeviceManager) -> None:
        self._state = state
        self._devices = devices
        self._bus = EventBus()
        self._executors: Dict[str, Callable] = {}
        self._log: List[dict] = []
        self._estop_latch = False

    def register_executor(self, command: str, fn: Callable) -> None:
        self._executors[command] = fn

    def send(self, command: Command) -> dict:
        """validate → safety → execute; returns a trace record."""
        entry = {"ts": datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3],
                 "command": command.command,
                 "source": command.source.value,
                 "priority": int(command.priority),
                 "validation": "PASS", "safety": "PASS",
                 "execution": "EXECUTED", "latency_ms": 0.0}
        t0 = time.time()

        # 1. validate
        if command.command not in self._executors:
            entry["validation"] = "FAIL"
            entry["execution"] = "REJECTED_UNKNOWN"
        # 2. safety authority (§7, §30)
        if self._estop_latch and not command.command.startswith("safety."):
            entry["safety"] = "ESTOP_LATCH"
            entry["execution"] = "BLOCKED"
        elif not self._state.can_accept_commands():
            entry["safety"] = "STATE_SAFE"
            entry["execution"] = "BLOCKED"

        if entry["execution"] == "EXECUTED":
            try:
                result = self._executors[command.command](command)
                entry["result"] = result
            except Exception as exc:                                # noqa: BLE001
                entry["execution"] = "FAILED"
                entry["result"] = str(exc)

        entry["latency_ms"] = round((time.time() - t0) * 1000, 1)
        self._log.append(entry)
        self._bus.emit(Event("command",
                             {"summary": f"{command.source.value}: "
                              f"{command.command} → {entry['execution']}",
                              "severity": "info"}))
        return entry

    def estop(self, latch: bool = True) -> None:
        """§6/§11 — E-STOP priority: > HUMAN > SAFETY > MISSION > AI."""
        self._estop_latch = latch
        self._state.transition(RobotState.EMERGENCY_STOP)
        self._bus.emit(Event("estop",
                             {"summary": "E-STOP latched" if latch else
                              "E-STOP cleared", "severity": "warn"}))

    def estop_clear(self) -> None:
        self._estop_latch = False
        self._state.transition(RobotState.SAFE_MODE)
        self._state.transition(RobotState.RECOVERY)
        self._state.transition(RobotState.SELF_TEST)
        self._state.transition(RobotState.READY)

    def trace(self, command_id: Optional[str] = None, limit: int = 30) -> List[dict]:
        """§28 — observability: trace every command end-to-end."""
        return list(self._log[-limit:])


# ---------------------------------------------------------------------------
# HealthManager (§12)
# ---------------------------------------------------------------------------
@dataclass
class HealthReport:
    overall: int
    components: Dict[str, float]

    def to_dict(self) -> dict:
        return {"overall": self.overall,
                "components": {k: round(v, 1) for k, v in self.components.items()}}


class HealthManager:
    """Health computed from measurable signals — never an arbitrary number."""

    def __init__(self, devices: DeviceManager) -> None:
        self._devices = devices

    def report(self) -> HealthReport:
        devs = self._devices.list()
        by_type: Dict[str, List[float]] = {}
        for d in devs:
            by_type.setdefault(d.type, []).append(d.health)
        components = {}
        for dtype, scores in by_type.items():
            components[dtype] = sum(scores) / len(scores) * 100.0
        # Weighted overall (motors + sensors + compute + power + network)
        weights = {"motor": 0.25, "compute": 0.2, "camera": 0.1, "lidar": 0.1,
                   "imu": 0.1, "battery": 0.1, "network": 0.05, "esp32": 0.1}
        total_w = 0.0
        acc = 0.0
        for dtype, score in components.items():
            w = weights.get(dtype, 0.05)
            acc += score * w
            total_w += w
        overall = int(acc / total_w) if total_w else 0
        return HealthReport(overall, components)


# ---------------------------------------------------------------------------
# MissionEngine (§14–15)
# ---------------------------------------------------------------------------
class MissionEngine:
    """Missions are first-class objects with a state machine."""

    def __init__(self, state: StateManager, commands: CommandBus) -> None:
        self._state = state
        self._commands = commands
        self._missions: Dict[str, Mission] = {}
        self._bus = EventBus()

    def create(self, mission_type: str,
               steps: Optional[List[str]] = None) -> Mission:
        mission = Mission(id=f"{mission_type}_{uuid.uuid4().hex[:4]}",
                          type=mission_type,
                          steps=steps or ["goto:A", "scan", "goto:B", "scan",
                                          "return_home"])
        mission.status = MissionState.VALIDATING
        self._missions[mission.id] = mission
        self._bus.emit(Event("mission_created",
                             {"summary": f"mission {mission.id} created",
                              "severity": "info"}))
        return mission

    def start(self, mission_id: str) -> Optional[Mission]:
        m = self._missions.get(mission_id)
        if m is None:
            return None
        m.status = MissionState.RUNNING
        self._state.transition(RobotState.MISSION)
        self._commands.send(Command("mission.start", CommandSource.MISSION,
                                    {"id": mission_id},
                                    CommandPriority.MISSION))
        self._bus.emit(Event("mission_started",
                             {"summary": f"mission {mission_id} started",
                              "severity": "info"}))
        return m

    def pause(self, mission_id: str) -> Optional[Mission]:
        m = self._missions.get(mission_id)
        if m and m.status == MissionState.RUNNING:
            m.status = MissionState.PAUSED
        return m

    def resume(self, mission_id: str) -> Optional[Mission]:
        m = self._missions.get(mission_id)
        if m and m.status == MissionState.PAUSED:
            m.status = MissionState.RUNNING
        return m

    def cancel(self, mission_id: str) -> Optional[Mission]:
        m = self._missions.get(mission_id)
        if m and m.status in (MissionState.RUNNING, MissionState.PAUSED,
                              MissionState.BLOCKED, MissionState.RECOVERY):
            m.status = MissionState.ABORTED
        return m

    def complete(self, mission_id: str) -> Optional[Mission]:
        m = self._missions.get(mission_id)
        if m:
            m.status = MissionState.COMPLETED
            m.progress = 100
            self._bus.emit(Event("mission_completed",
                                 {"summary": f"mission {mission_id} completed",
                                  "severity": "info"}))
        return m

    def advance(self, mission_id: str) -> Optional[Mission]:
        m = self._missions.get(mission_id)
        if m and m.status == MissionState.RUNNING:
            m.progress = min(100, m.progress + 10)
        return m

    def list(self) -> List[Mission]:
        return list(self._missions.values())

    def block(self, mission_id: str, reason: str) -> Optional[Mission]:
        m = self._missions.get(mission_id)
        if m and m.status == MissionState.RUNNING:
            m.status = MissionState.BLOCKED
            self._bus.emit(Event("mission_blocked",
                                 {"summary": f"mission {mission_id} blocked: "
                                  f"{reason}", "severity": "warn"}))
        return m


# ---------------------------------------------------------------------------
# TankOS API facade (§3, §24)
# ---------------------------------------------------------------------------
class TankOS:
    """The canonical API — applications never touch hardware directly."""

    def __init__(self) -> None:
        self.devices = DeviceManager()
        self.state = StateManager()
        self.commands = CommandBus(self.state, self.devices)
        self.health = HealthManager(self.devices)
        self.missions = MissionEngine(self.state, self.commands)
        self.bus = EventBus()
        self._register_builtin_commands()

    def _register_builtin_commands(self) -> None:
        self.commands.register_executor("robot.stop", lambda c: {"motors": "stopped"})
        self.commands.register_executor("robot.move", lambda c: {
            "direction": c.args.get("direction"), "ok": True})
        self.commands.register_executor("robot.set_speed", lambda c: {
            "max_speed_mps": c.args.get("max_speed_mps")})
        self.commands.register_executor("display.show", lambda c: {
            "screen": c.args.get("screen", "dashboard")})
        self.commands.register_executor("mission.start", lambda c: {
            "mission": c.args.get("id")})

    def boot(self) -> None:
        """Full boot: discover nodes → self-test → ready."""
        self.state.transition(RobotState.SELF_TEST)
        self.devices.discover()
        self.state.transition(RobotState.READY)

    def status(self) -> dict:
        return {
            "state": self.state.state().value,
            "devices": len(self.devices.list()),
            "devices_online": sum(1 for d in self.devices.list()
                                  if d.status in (DeviceState.READY,
                                                  DeviceState.ACTIVE)),
            "health": self.health.report().overall,
            "missions": [m.to_dict() for m in self.missions.list()],
            "command_trace": self.commands.trace(limit=5),
        }

    def api(self) -> dict:
        """§3 — the canonical surface."""
        return {
            "tank.device": ["discover", "register", "unregister", "get", "list",
                            "health", "reset"],
            "tank.state": ["state", "transition", "history"],
            "tank.command": ["send", "estop", "trace"],
            "tank.mission": ["create", "start", "pause", "resume", "cancel",
                             "complete", "list"],
            "tank.health": ["report"],
            "tank.event": ["emit", "history"],
        }
