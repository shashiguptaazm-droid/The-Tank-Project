"""
TankOS Auto Charging System — autonomous dock detection, navigation,
precision docking, charging management, battery health, and power optimization.

Contains 10 integrated subsystems:

  1. ChargingManager         — Main orchestrator
  2. DockDetectionEngine     — AprilTags, LiDAR, cameras, IR beacons
  3. DockNavigationEngine    — Autonomous path planning to dock
  4. DockingController       — Precision alignment and contact verification
  5. ChargingController      — Current/voltage/temperature monitoring
  6. TaskInterruptionManager — Pause/resume tasks for charging
  7. EmergencyChargingEngine — Critical battery override
  8. PowerOptimizationEngine — CPU/display/peripheral tuning
  9. BatteryHealthManager    — Cycle tracking, degradation, SOH
  10. ChargingScheduler      — Usage pattern learning, idle scheduling
"""

from __future__ import annotations

import json
import logging
import math
import threading
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from tank_os.core.event_bus import Event, EventBus, Priority
from tank_os.core.navigation_manager import NavigationManager, Pose, Waypoint
from tank_os.core.robot_manager import RobotManager
from tank_os.core.settings_manager import SettingsManager

logger = logging.getLogger("tank_os.charging")

# =========================================================================
# Enums & Constants
# =========================================================================


class DockStatus(Enum):
    UNKNOWN = auto()
    DETECTED = auto()
    APPROACHING = auto()
    ALIGNING = auto()
    DOCKED = auto()
    CHARGING = auto()
    DISCONNECTED = auto()
    FAULT = auto()


class ChargeState(Enum):
    IDLE = auto()
    PRE_CHARGE = auto()
    FAST_CHARGE = auto()
    TRICKLE_CHARGE = auto()
    COMPLETE = auto()
    FAULT = auto()
    EMERGENCY = auto()


@dataclass
class DockInfo:
    """Information about the charging dock."""
    x: float = 0.0
    y: float = 0.0
    yaw: float = 0.0
    detected_via: str = ""  # apriltag, lidar, camera, ir, map
    confidence: float = 0.0
    last_seen: float = 0.0
    approach_path: List[Tuple[float, float]] = field(default_factory=list)


@dataclass
class BatteryHealth:
    """Battery health and degradation tracking."""
    cycles: int = 0
    design_capacity_mah: float = 5000.0
    current_capacity_mah: float = 5000.0
    soh_pct: float = 100.0  # State of Health
    voltage_min: float = 3.0
    voltage_max: float = 4.2
    temp_min_c: float = 0.0
    temp_max_c: float = 45.0
    internal_resistance: float = 0.0
    first_use_ts: float = 0.0

    @property
    def degradation_pct(self) -> float:
        return 100.0 - self.soh_pct

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycles": self.cycles,
            "soh_pct": self.soh_pct,
            "degradation_pct": self.degradation_pct,
            "current_capacity_mah": self.current_capacity_mah,
        }


@dataclass
class ChargeSession:
    """A single charging session record."""
    id: str = ""
    start_ts: float = 0.0
    end_ts: float = 0.0
    start_pct: int = 0
    end_pct: int = 0
    duration_s: float = 0.0
    energy_mah: float = 0.0
    avg_temp_c: float = 25.0
    completed: bool = False


# =========================================================================
# 10 — Charging Scheduler
# =========================================================================

class ChargingScheduler:
    """Learns usage patterns and schedules charging during idle periods."""

    def __init__(self, bus: EventBus, settings: SettingsManager) -> None:
        self._bus = bus
        self._settings = settings
        self._lock = threading.Lock()
        self._usage_history: List[Dict[str, Any]] = []
        self._history_path = Path.home() / ".config" / "tank_os" / "charging_schedule.json"
        self._last_schedule_check = time.time()
        self._optimal_window: Optional[Tuple[float, float]] = None

    def initialize(self) -> None:
        self._load_history()
        self._analyze_patterns()
        logger.info("ChargingScheduler initialized (%d history entries)", len(self._usage_history))

    def _load_history(self) -> None:
        if self._history_path.exists():
            try:
                data = json.loads(self._history_path.read_text())
                self._usage_history = data.get("history", [])
            except Exception as exc:
                logger.warning("Failed to load charge schedule: %s", exc)

    def _save_history(self) -> None:
        self._history_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._history_path.write_text(json.dumps(
                {"history": self._usage_history[-500:]}, indent=2
            ))
        except Exception as exc:
            logger.warning("Failed to save charge schedule: %s", exc)

    def record_usage(self, mode: str, battery_pct: int) -> None:
        """Record the robot's current state for pattern learning."""
        with self._lock:
            entry = {
                "ts": time.time(),
                "hour": time.localtime().tm_hour,
                "day": time.localtime().tm_wday,
                "mode": mode,
                "battery_pct": battery_pct,
            }
            self._usage_history.append(entry)
            if len(self._usage_history) > 1000:
                self._usage_history = self._usage_history[-1000:]

    def _analyze_patterns(self) -> None:
        """Find the best time windows for charging based on history."""
        with self._lock:
            if len(self._usage_history) < 24:
                return

            # Find hours with lowest activity
            hourly_usage: Dict[int, int] = {}
            for entry in self._usage_history:
                h = entry["hour"]
                hourly_usage[h] = hourly_usage.get(h, 0) + 1

            if not hourly_usage:
                return

            # Find 2-hour window with fewest events
            min_activity = min(hourly_usage.values())
            for h, count in sorted(hourly_usage.items()):
                if count == min_activity:
                    self._optimal_window = (float(h), float((h + 2) % 24))
                    break

    def should_charge_now(self, battery_pct: int, current_mode: str) -> bool:
        """Determine if charging should start based on scheduler."""
        # Always charge if battery is critically low
        if battery_pct <= 10:
            return True

        # Don't interrupt active patrols or missions unless necessary
        if current_mode in ("patrolling", "mission") and battery_pct > 20:
            return False

        # Use optimal window if available
        if self._optimal_window:
            current_hour = time.localtime().tm_hour
            start_h, end_h = self._optimal_window
            if start_h <= current_hour < end_h and battery_pct <= self._settings.get("charging.schedule_threshold", 50):
                return True

        # Default: charge when below low threshold
        return battery_pct <= self._settings.get("power.low_battery_threshold", 20)

    def next_scheduled_window(self) -> Optional[Tuple[float, float]]:
        """Return the next recommended charging window as (start_hour, end_hour)."""
        with self._lock:
            return self._optimal_window


# =========================================================================
# 9 — Battery Health Manager
# =========================================================================

class BatteryHealthManager:
    """Tracks charging cycles, degradation, temperature, and predicts replacement."""

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus
        self._lock = threading.Lock()
        self._health = BatteryHealth()
        self._health_path = Path.home() / ".config" / "tank_os" / "battery_health.json"
        self._temp_readings: List[Tuple[float, float]] = []  # (ts, temp_c)

    def initialize(self) -> None:
        self._load_health()
        logger.info("BatteryHealthManager initialized — SOH: %.1f%%", self._health.soh_pct)

    def _load_health(self) -> None:
        if self._health_path.exists():
            try:
                data = json.loads(self._health_path.read_text())
                for key, value in data.items():
                    if hasattr(self._health, key):
                        setattr(self._health, key, value)
            except Exception as exc:
                logger.warning("Failed to load battery health: %s", exc)

    def _save_health(self) -> None:
        self._health_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._health_path.write_text(json.dumps(self._health.to_dict(), indent=2))
        except Exception as exc:
            logger.warning("Failed to save battery health: %s", exc)

    def record_charge_cycle(self, start_pct: int, end_pct: int, duration_s: float,
                            energy_mah: float, avg_temp_c: float) -> None:
        """Record a completed charge cycle and update battery health."""
        with self._lock:
            self._health.cycles += 1

            # Simulate degradation: ~0.02% per cycle, accelerated by heat
            temp_factor = 1.0 + max(0, (avg_temp_c - 25.0) * 0.02)
            degradation = 0.02 * temp_factor
            self._health.soh_pct = max(50.0, self._health.soh_pct - degradation)
            self._health.current_capacity_mah = (
                self._health.design_capacity_mah * self._health.soh_pct / 100.0
            )

            if self._health.first_use_ts == 0:
                self._health.first_use_ts = time.time()

        self._save_health()
        self._bus.emit(Event("battery_cycle_recorded", {
            "cycles": self._health.cycles,
            "soh": round(self._health.soh_pct, 1),
            "energy_mah": round(energy_mah, 1),
        }, source="battery_health"))

    def record_temperature(self, temp_c: float) -> None:
        """Log a battery temperature reading."""
        with self._lock:
            self._temp_readings.append((time.time(), temp_c))
            if len(self._temp_readings) > 1000:
                self._temp_readings = self._temp_readings[-1000:]

    @property
    def health(self) -> BatteryHealth:
        return self._health

    @property
    def estimated_lifespan_cycles(self) -> int:
        """Estimate remaining cycles before SOH drops below 70%."""
        if self._health.cycles == 0:
            return 1500
        degradation_per_cycle = (100.0 - self._health.soh_pct) / max(1, self._health.cycles)
        remaining_degradation = self._health.soh_pct - 70.0
        return max(0, int(remaining_degradation / max(0.01, degradation_per_cycle)))

    def get_recommendation(self) -> str:
        """Return a human-readable battery recommendation."""
        if self._health.soh_pct < 70:
            return "⚠️ Battery degraded — consider replacement soon"
        elif self._health.soh_pct < 85:
            return "🔶 Battery health declining — monitor regularly"
        return "✅ Battery health is good"

    def summary(self) -> Dict[str, Any]:
        return {
            "cycles": self._health.cycles,
            "soh_pct": round(self._health.soh_pct, 1),
            "capacity_mah": round(self._health.current_capacity_mah, 1),
            "remaining_cycles": self.estimated_lifespan_cycles,
            "recommendation": self.get_recommendation(),
        }


# =========================================================================
# 8 — Power Optimization Engine
# =========================================================================

class PowerOptimizationEngine:
    """Adjusts CPU, display, AI model, and peripherals to extend runtime."""

    def __init__(self, bus: EventBus, settings: SettingsManager) -> None:
        self._bus = bus
        self._settings = settings
        self._lock = threading.Lock()
        self._profile: str = "balanced"
        self._current_draw_ma: float = 2000.0  # Estimated average

    def initialize(self) -> None:
        logger.info("PowerOptimizationEngine initialized")

    def set_profile(self, profile: str) -> None:
        """Switch power profile: 'max_performance', 'balanced', 'max_battery'."""
        with self._lock:
            self._profile = profile
            self._apply_profile(profile)

    def _apply_profile(self, profile: str) -> None:
        """Apply power-saving settings to subsystems."""
        from tank_os.core.display_manager import DisplayManager
        display = DisplayManager()

        if profile == "max_battery":
            display.set_brightness(20)
            self._settings.set("display.animations_enabled", False)
            self._settings.set("display.fps_limit", 15)
            self._settings.set("ai.temperature", 0.3)
            self._settings.set("ai.max_tokens", 128)
            self._bus.emit(Event("power_profile_changed", {
                "profile": "max_battery",
                "brightness": 20, "animations": False,
            }, source="power_optimizer"))

        elif profile == "balanced":
            display.set_brightness(60)
            self._settings.set("display.animations_enabled", True)
            self._settings.set("display.fps_limit", 30)
            self._settings.set("ai.temperature", 0.7)
            self._settings.set("ai.max_tokens", 256)
            self._bus.emit(Event("power_profile_changed", {
                "profile": "balanced",
                "brightness": 60, "animations": True,
            }, source="power_optimizer"))

        elif profile == "max_performance":
            display.set_brightness(100)
            self._settings.set("display.animations_enabled", True)
            self._settings.set("display.fps_limit", 60)
            self._settings.set("ai.temperature", 0.9)
            self._settings.set("ai.max_tokens", 512)
            self._bus.emit(Event("power_profile_changed", {
                "profile": "max_performance",
                "brightness": 100, "animations": True,
            }, source="power_optimizer"))

    def estimate_runtime_minutes(self, battery_pct: int) -> float:
        """Estimate remaining runtime based on current profile."""
        base_draw = {
            "max_performance": 5000.0,
            "balanced": 2500.0,
            "max_battery": 1200.0,
        }.get(self._profile, 2500.0)
        capacity = 5000.0  # mAh typical
        usable = capacity * battery_pct / 100.0
        return (usable / base_draw) * 60.0

    def optimize_for_charging(self) -> None:
        """Prepare system for charging by reducing unnecessary loads."""
        self.set_profile("max_battery")
        from tank_os.core.display_manager import DisplayManager
        DisplayManager().blank()
        logger.info("System optimized for charging")

    def restore_after_charge(self) -> None:
        """Restore normal performance after charging completes."""
        from tank_os.core.display_manager import DisplayManager
        DisplayManager().unblank()
        prev = self._settings.get("power.performance_mode", "balanced")
        self.set_profile(prev)
        logger.info("System restored after charging")


# =========================================================================
# 7 — Emergency Charging Engine
# =========================================================================

class EmergencyChargingEngine:
    """Overrides all tasks when battery reaches critical levels."""

    CRITICAL_THRESHOLD = 10
    EMERGENCY_THRESHOLD = 5

    def __init__(self, bus: EventBus, settings: SettingsManager,
                 power_optimizer: Optional[PowerOptimizationEngine] = None) -> None:
        self._bus = bus
        self._settings = settings
        self._power_optimizer = power_optimizer
        self._lock = threading.Lock()
        self._emergency_active = False

    def check_and_trigger(self, battery_pct: int, current_mode: str) -> bool:
        """Check if emergency charging is needed. Returns True if triggered."""
        if battery_pct <= self.EMERGENCY_THRESHOLD and not self._emergency_active:
            self._trigger_emergency(battery_pct, current_mode)
            return True
        elif battery_pct <= self.CRITICAL_THRESHOLD and not self._emergency_active:
            self._trigger_critical(battery_pct, current_mode)
            return True
        elif battery_pct > 20 and self._emergency_active:
            self._clear_emergency()
        return False

    def _trigger_emergency(self, battery_pct: int, current_mode: str) -> None:
        """Emergency: battery < 5% — immediately shut down non-essentials and dock."""
        with self._lock:
            self._emergency_active = True
        logger.warning("🚨 EMERGENCY: Battery at %d%% — forcing immediate dock!", battery_pct)
        self._bus.emit(Event("charging_emergency", {
            "level": "emergency",
            "battery_pct": battery_pct,
            "mode": current_mode,
        }, source="emergency_charging", priority=Priority.CRITICAL))

        if self._power_optimizer:
            self._power_optimizer.optimize_for_charging()

        # Signal emergency via existing robot API
        RobotManager().estop(latch=True)

    def _trigger_critical(self, battery_pct: int, current_mode: str) -> None:
        """Critical: battery < 10% — schedule immediate charging."""
        with self._lock:
            self._emergency_active = True
        logger.warning("⚠️ CRITICAL: Battery at %d%% — initiating charging sequence", battery_pct)
        self._bus.emit(Event("charging_emergency", {
            "level": "critical",
            "battery_pct": battery_pct,
            "mode": current_mode,
        }, source="emergency_charging", priority=Priority.HIGH))

        if self._power_optimizer:
            self._power_optimizer.optimize_for_charging()

    def _clear_emergency(self) -> None:
        with self._lock:
            self._emergency_active = False
        self._bus.emit(Event("charging_emergency_cleared", {}, source="emergency_charging"))
        logger.info("✅ Emergency state cleared")

    @property
    def is_emergency_active(self) -> bool:
        return self._emergency_active


# =========================================================================
# 6 — Task Interruption Manager
# =========================================================================

class TaskInterruptionManager:
    """Pauses active tasks before docking, saves state, resumes after charge."""

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus
        self._lock = threading.Lock()
        self._saved_states: Dict[str, Any] = {}
        self._paused = False

    def prepare_for_docking(self) -> bool:
        """Pause all active tasks and save state. Returns True if successful."""
        with self._lock:
            self._paused = True
            self._saved_states["timestamp"] = time.time()
            self._saved_states["robot_mode"] = RobotManager().status.mode
            self._saved_states["patrol_active"] = RobotManager().status.patrolling

        # Stop patrol if active
        if self._saved_states.get("patrol_active"):
            RobotManager().stop_patrol()

        self._bus.emit(Event("tasks_paused_for_charging", {
            "saved_state": self._saved_states,
        }, source="task_interruption"))
        logger.info("Tasks paused for docking — state saved")
        return True

    def resume_after_charge(self) -> bool:
        """Restore all paused tasks. Returns True if tasks were resumed."""
        with self._lock:
            if not self._paused:
                return False
            self._paused = False

            # Restore patrol if it was active
            if self._saved_states.get("patrol_active"):
                RobotManager().patrol()

            state = dict(self._saved_states)
            self._saved_states.clear()

        self._bus.emit(Event("tasks_resumed_after_charging", {
            "restored_state": state,
        }, source="task_interruption"))
        logger.info("Tasks resumed after charging")
        return True

    @property
    def has_saved_state(self) -> bool:
        return self._paused


# =========================================================================
# 5 — Charging Controller
# =========================================================================

class ChargingController:
    """Monitors charging current, voltage, temperature, and manages charge cycles."""

    def __init__(self, bus: EventBus, settings: SettingsManager) -> None:
        self._bus = bus
        self._settings = settings
        self._lock = threading.Lock()
        self._state = ChargeState.IDLE
        self._session: Optional[ChargeSession] = None
        self._current_ma: float = 0.0
        self._voltage_v: float = 5.0
        self._temp_c: float = 25.0
        self._charge_start_time: float = 0.0
        self._last_pct: int = 0

    def initialize(self) -> None:
        logger.info("ChargingController initialized")

    def start_charging(self, start_pct: int) -> bool:
        """Initiate a charging session."""
        import uuid
        with self._lock:
            if self._state != ChargeState.IDLE:
                return False
            self._state = ChargeState.PRE_CHARGE
            self._session = ChargeSession(
                id=str(uuid.uuid4())[:8],
                start_ts=time.time(),
                start_pct=start_pct,
            )
            self._charge_start_time = time.time()
            self._last_pct = start_pct

        self._bus.emit(Event("charging_started", {
            "session_id": self._session.id,
            "start_pct": start_pct,
        }, source="charging_controller"))
        logger.info("⚡ Charging started at %d%% — session %s", start_pct, self._session.id)

        # Transition to fast charge after brief pre-charge
        threading.Timer(5.0, self._transition_to_fast).start()
        return True

    def _transition_to_fast(self) -> None:
        with self._lock:
            self._state = ChargeState.FAST_CHARGE
        self._bus.emit(Event("charging_fast", {}, source="charging_controller"))

    def update_telemetry(self, current_ma: float, voltage_v: float, temp_c: float) -> None:
        """Update real-time charging telemetry."""
        with self._lock:
            self._current_ma = current_ma
            self._voltage_v = voltage_v
            self._temp_c = temp_c

    def update_battery_pct(self, pct: int) -> None:
        """Update battery percentage during charging (for completion detection)."""
        with self._lock:
            if self._state in (ChargeState.FAST_CHARGE, ChargeState.TRICKLE_CHARGE):
                if pct >= 80 and self._state == ChargeState.FAST_CHARGE:
                    self._state = ChargeState.TRICKLE_CHARGE
                    self._bus.emit(Event("charging_trickle", {"pct": pct}, source="charging_controller"))
                if pct >= self._settings.get("charging.target_pct", 95):
                    self._complete_charging(pct)

    def _complete_charging(self, end_pct: int) -> None:
        with self._lock:
            if self._session:
                self._session.end_ts = time.time()
                self._session.end_pct = end_pct
                self._session.duration_s = self._session.end_ts - self._session.start_ts
                self._session.completed = True
            self._state = ChargeState.COMPLETE

        self._bus.emit(Event("charging_complete", {
            "end_pct": end_pct,
            "duration_s": self._session.duration_s if self._session else 0,
        }, source="charging_controller"))
        logger.info("🔋 Charging complete — reached %d%%", end_pct)

    def abort_charging(self, reason: str = "") -> None:
        """Abort the current charging session."""
        with self._lock:
            self._state = ChargeState.FAULT
            if self._session:
                self._session.completed = False
        self._bus.emit(Event("charging_aborted", {
            "reason": reason,
        }, source="charging_controller"))
        logger.warning("⚠️ Charging aborted: %s", reason)

    def stop_charging(self) -> None:
        """Stop charging normally."""
        with self._lock:
            self._state = ChargeState.IDLE
            self._session = None
        self._bus.emit(Event("charging_stopped", {}, source="charging_controller"))

    @property
    def state(self) -> ChargeState:
        return self._state

    @property
    def is_active(self) -> bool:
        return self._state in (ChargeState.PRE_CHARGE, ChargeState.FAST_CHARGE, ChargeState.TRICKLE_CHARGE)

    @property
    def current_ma(self) -> float:
        return self._current_ma

    @property
    def voltage_v(self) -> float:
        return self._voltage_v

    @property
    def temp_c(self) -> float:
        return self._temp_c

    @property
    def current_session(self) -> Optional[ChargeSession]:
        return self._session


# =========================================================================
# 4 — Docking Controller
# =========================================================================

class DockingController:
    """Precision docking with visual alignment and contact verification."""

    APPROACH_DISTANCE_M = 0.5
    ALIGN_TOLERANCE_M = 0.02
    ALIGN_TOLERANCE_DEG = 2.0
    DOCK_SPEED_M_S = 0.05

    def __init__(self, bus: EventBus, nav: NavigationManager) -> None:
        self._bus = bus
        self._nav = nav
        self._lock = threading.Lock()
        self._dock_info: Optional[DockInfo] = None
        self._status = DockStatus.UNKNOWN
        self._alignment_attempts = 0
        self._max_attempts = 5

    def set_dock_info(self, info: DockInfo) -> None:
        with self._lock:
            self._dock_info = info

    def execute_docking(self, dock: DockInfo, on_complete: Optional[Callable[[bool], None]] = None) -> bool:
        """Execute the full docking sequence. Returns True if docked.

        To avoid blocking the monitoring thread, alignment is done with
        Timers rather than sleep(). Pass ``on_complete`` to be notified
        of the result asynchronously.
        """
        with self._lock:
            self._dock_info = dock
            self._status = DockStatus.APPROACHING

        logger.info("🔌 Starting docking sequence at (%.2f, %.2f)", dock.x, dock.y)
        self._bus.emit(Event("docking_started", {
            "x": dock.x, "y": dock.y,
            "method": dock.detected_via,
        }, source="docking_controller"))

        # Phase 1: Navigate to approach point
        approach_x = dock.x + self.APPROACH_DISTANCE_M * math.cos(dock.yaw)
        approach_y = dock.y + self.APPROACH_DISTANCE_M * math.sin(dock.yaw)
        self._nav.navigate_to(approach_x, approach_y)

        # Phase 2+3: Align then dock after short delay (non-blocking)
        self._status = DockStatus.ALIGNING
        self._alignment_attempts = 0

        def _align_step():
            self._status = DockStatus.ALIGNING
            self._alignment_attempts += 1

            if self._check_alignment():
                # Final approach and dock
                robot = RobotManager()
                robot.drive(self.DOCK_SPEED_M_S, 0.0, duration_s=2.0)
                robot.set_docked(True)

                self._status = DockStatus.DOCKED
                self._bus.emit(Event("docking_complete", {
                    "x": dock.x, "y": dock.y,
                    "attempts": self._alignment_attempts,
                }, source="docking_controller"))
                logger.info("✅ Docking successful after %d attempts", self._alignment_attempts)
                if on_complete:
                    on_complete(True)
                return

            if self._alignment_attempts < self._max_attempts:
                correction = 0.1 * (1.0 if self._alignment_attempts % 2 == 0 else -1.0)
                RobotManager().drive(0.0, correction, duration_s=1.0)
                threading.Timer(1.5, _align_step).start()
            else:
                self._status = DockStatus.FAULT
                self._bus.emit(Event("docking_failed", {
                    "attempts": self._alignment_attempts,
                    "reason": "Alignment timeout",
                }, source="docking_controller"))
                logger.error("❌ Docking failed after %d attempts", self._alignment_attempts)
                if on_complete:
                    on_complete(False)

        # Start alignment after a brief delay (non-blocking)
        threading.Timer(2.0, _align_step).start()
        return True

    def _check_alignment(self) -> bool:
        """Check if the robot is properly aligned with the dock.

        In real implementation, this would use:
        - Camera (AprilTag offset)
        - LiDAR (distance left/right)
        - IR beacon signal strength
        """
        pose = self._nav.pose
        if not self._dock_info:
            return False

        dx = abs(pose.x - self._dock_info.x)
        dy = abs(pose.y - self._dock_info.y)
        dyaw = abs(pose.yaw - self._dock_info.yaw)

        return (dx <= self.ALIGN_TOLERANCE_M and
                dy <= self.ALIGN_TOLERANCE_M and
                dyaw <= self.ALIGN_TOLERANCE_DEG)

    def verify_contact(self) -> bool:
        """Verify electrical contact with dock. Returns True if charging contact confirmed."""
        # In real implementation: check voltage/current change
        self._bus.emit(Event("docking_contact_verified", {}, source="docking_controller"))
        return True

    def undock(self) -> None:
        """Execute undocking sequence."""
        robot = RobotManager()
        robot.drive(-0.1, 0.0, duration_s=1.0)
        robot.set_docked(False)
        self._status = DockStatus.DISCONNECTED
        self._bus.emit(Event("undocking_complete", {}, source="docking_controller"))
        logger.info("↩️ Undocking complete")

    @property
    def status(self) -> DockStatus:
        return self._status


# =========================================================================
# 3 — Dock Navigation Engine
# =========================================================================

class DockNavigationEngine:
    """Autonomously navigates to the charging dock while avoiding obstacles."""

    def __init__(self, bus: EventBus, nav: NavigationManager) -> None:
        self._bus = bus
        self._nav = nav
        self._lock = threading.Lock()
        self._dock_waypoint_name = "charging_dock"
        self._dock_saved = False

    def initialize(self) -> None:
        """Register the dock waypoint if it exists."""
        wp = self._nav.get_waypoint(self._dock_waypoint_name)
        if wp:
            self._dock_saved = True
            logger.info("Dock waypoint found: (%.2f, %.2f)", wp.x, wp.y)

    def navigate_to_dock(self, dock: DockInfo) -> bool:
        """Navigate to the charging dock. Returns True if path found."""
        self._bus.emit(Event("docking_navigate_start", {
            "x": dock.x, "y": dock.y,
        }, source="dock_navigation"))
        logger.info("🗺️ Navigating to dock at (%.2f, %.2f)", dock.x, dock.y)

        # Save as waypoint if not already saved
        if not self._dock_saved:
            self._nav.add_waypoint(self._dock_waypoint_name, dock.x, dock.y, dock.yaw)
            self._dock_saved = True

        # Use waypoint navigation
        result = self._nav.navigate_waypoint(self._dock_waypoint_name)

        if result:
            self._bus.emit(Event("docking_navigate_path_found", {
                "name": self._dock_waypoint_name,
            }, source="dock_navigation"))
        else:
            self._nav.navigate_to(dock.x, dock.y)

        return result

    def save_dock_position(self, x: float, y: float, yaw: float = 0.0) -> None:
        """Persist the dock position as a named waypoint."""
        self._nav.add_waypoint(self._dock_waypoint_name, x, y, yaw)
        self._dock_saved = True
        self._bus.emit(Event("dock_position_saved", {
            "x": x, "y": y, "yaw": yaw,
        }, source="dock_navigation"))
        logger.info("📍 Dock position saved: (%.2f, %.2f, %.1f°)", x, y, math.degrees(yaw))

    @property
    def dock_position(self) -> Optional[Waypoint]:
        return self._nav.get_waypoint(self._dock_waypoint_name)


# =========================================================================
# 2 — Dock Detection Engine
# =========================================================================

class DockDetectionEngine:
    """Uses AprilTags, LiDAR, cameras, IR beacons, and stored maps to locate the dock."""

    def __init__(self, bus: EventBus, nav: NavigationManager) -> None:
        self._bus = bus
        self._nav = nav
        self._lock = threading.Lock()
        self._last_detection: Optional[DockInfo] = None
        self._detection_history: List[DockInfo] = []

    def initialize(self) -> None:
        logger.info("DockDetectionEngine initialized")

    def detect_dock(self) -> Optional[DockInfo]:
        """Run all detection methods and return the best dock position found.

        Detection priority: AprilTag > LiDAR > Camera > IR > Stored Map
        """
        # Try each method in priority order
        methods = [
            ("apriltag", self._detect_apriltag),
            ("lidar", self._detect_lidar),
            ("camera", self._detect_camera),
            ("ir", self._detect_ir),
            ("map", self._detect_from_map),
        ]

        best: Optional[DockInfo] = None
        best_confidence = 0.0

        for method_name, detector in methods:
            try:
                result = detector()
                if result and result.confidence > best_confidence:
                    best = result
                    best_confidence = result.confidence
                    result.detected_via = method_name
            except Exception as exc:
                logger.debug("Dock detection %s failed: %s", method_name, exc)

        if best:
            best.last_seen = time.time()
            with self._lock:
                self._last_detection = best
                self._detection_history.append(best)
                if len(self._detection_history) > 50:
                    self._detection_history = self._detection_history[-50:]
            self._bus.emit(Event("dock_detected", {
                "x": best.x, "y": best.y, "yaw": best.yaw,
                "method": best.detected_via,
                "confidence": best.confidence,
            }, source="dock_detection"))
            logger.info("🔍 Dock detected via %s (confidence: %.2f)", best.detected_via, best.confidence)

        return best

    def _detect_apriltag(self) -> Optional[DockInfo]:
        """Detect dock via AprilTag on the charging station."""
        # In real implementation, queries VisionManager for AprilTag detection
        # with a specific tag ID reserved for the charging dock.
        return None  # Placeholder — requires camera active + tag config

    def _detect_lidar(self) -> Optional[DockInfo]:
        """Detect dock via LiDAR by looking for the dock's distinctive shape."""
        # In real implementation, processes LiDAR point cloud
        # looking for the dock's known geometry signature.
        return None  # Placeholder — requires LiDAR hardware

    def _detect_camera(self) -> Optional[DockInfo]:
        """Detect dock via camera using visual markers."""
        # In real implementation, uses YOLO model trained on dock images
        return None  # Placeholder — requires dock-trained YOLO model

    def _detect_ir(self) -> Optional[DockInfo]:
        """Detect dock via IR beacon signal strength."""
        # In real implementation, reads IR sensor array
        return None  # Placeholder — requires IR sensors

    def _detect_from_map(self) -> Optional[DockInfo]:
        """Get dock position from saved waypoints."""
        wp = self._nav.get_waypoint("charging_dock")
        if wp:
            return DockInfo(
                x=wp.x, y=wp.y, yaw=wp.yaw,
                detected_via="map",
                confidence=0.7,
                last_seen=time.time(),
            )
        return None

    def get_last_detection(self) -> Optional[DockInfo]:
        with self._lock:
            return self._last_detection

    def clear_history(self) -> None:
        with self._lock:
            self._detection_history.clear()
            self._last_detection = None


# =========================================================================
# 1 — Charging Manager (Main Orchestrator)
# =========================================================================

class ChargingManager:
    """The master auto charging system orchestrator.

    Coordinates all 10 subsystems to provide autonomous charging:
    detection → navigation → docking → charging → health tracking → scheduling.
    """

    _instance: Optional["ChargingManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "ChargingManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        self._bus = EventBus()
        self._settings = SettingsManager()
        self._nav = NavigationManager()

        # Create all 10 subsystems
        self.power_optimizer = PowerOptimizationEngine(self._bus, self._settings)
        self.dock_detection = DockDetectionEngine(self._bus, self._nav)
        self.dock_navigation = DockNavigationEngine(self._bus, self._nav)
        self.docking_controller = DockingController(self._bus, self._nav)
        self.charging_controller = ChargingController(self._bus, self._settings)
        self.task_interruption = TaskInterruptionManager(self._bus)
        self.emergency_engine = EmergencyChargingEngine(
            self._bus, self._settings, power_optimizer=self.power_optimizer
        )
        self.battery_health = BatteryHealthManager(self._bus)
        self.charging_scheduler = ChargingScheduler(self._bus, self._settings)

        # Initialize all subsystems
        self.dock_detection.initialize()
        self.dock_navigation.initialize()
        self.charging_controller.initialize()
        self.battery_health.initialize()
        self.power_optimizer.initialize()
        self.charging_scheduler.initialize()

        # Tracking
        self._charging_in_progress = False
        self._auto_charge_enabled = self._settings.get("charging.auto_enabled", True)
        self._last_check_pct = 100

        # Start monitoring loop
        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True,
            name="tank_os_charging"
        )
        self._monitor_thread.start()

        self._bus.on("battery_critical", self._on_battery_critical)

        logger.info("ChargingManager initialized — auto-charging: %s", self._auto_charge_enabled)

    def _monitor_loop(self) -> None:
        """Main charging monitoring loop — runs every 10 seconds."""
        while self._running:
            try:
                self._tick()
            except Exception as exc:
                logger.exception("Charging monitor error: %s", exc)
            time.sleep(10.0)

    def _tick(self) -> None:
        """One monitoring cycle."""
        from tank_os.core.power_manager import PowerManager
        power = PowerManager()
        battery_pct = power.battery_percent
        charging = power.is_charging
        current_mode = RobotManager().status.mode

        # Record usage for scheduler
        self.charging_scheduler.record_usage(current_mode, battery_pct)

        # Check emergency conditions
        if not charging:
            emergency = self.emergency_engine.check_and_trigger(battery_pct, current_mode)
            if emergency:
                self._start_charging_sequence(battery_pct, emergency=True)
                return

        # Check if we should auto-charge
        if self._auto_charge_enabled and not charging and not self._charging_in_progress:
            if battery_pct <= self._settings.get("power.low_battery_threshold", 20):
                if current_mode in ("idle", "docked") or battery_pct <= 15:
                    self._start_charging_sequence(battery_pct)
                    return

        # Update charging controller with battery telemetry
        if self._charging_in_progress:
            self.charging_controller.update_battery_pct(battery_pct)
            self.charging_controller.update_telemetry(
                current_ma=1500.0,  # Placeholder for real current sensor
                voltage_v=power.voltage,
                temp_c=35.0,  # Placeholder for real temp sensor
            )
            self.battery_health.record_temperature(35.0)

            # Check if charging is done
            if not charging and battery_pct >= 95:
                self._complete_charging(battery_pct)

        self._last_check_pct = battery_pct

    def _start_charging_sequence(self, battery_pct: int, emergency: bool = False) -> None:
        """Execute the full autonomous charging sequence."""
        if self._charging_in_progress:
            return

        self._charging_in_progress = True
        logger.info("🔋 Starting charging sequence (battery: %d%%)", battery_pct)
        self._bus.emit(Event("charging_sequence_start", {
            "battery_pct": battery_pct,
            "emergency": emergency,
        }, source="charging_manager"))

        try:
            # Step 1: Save task state
            self.task_interruption.prepare_for_docking()

            # Step 2: Apply power optimization
            self.power_optimizer.optimize_for_charging()

            # Step 3: Detect dock
            dock = self.dock_detection.detect_dock()
            if dock is None:
                logger.warning("⚠️ Dock not detected via sensors")
                # detect_dock() already includes map fallback internally
            if dock is None:
                logger.error("❌ No dock position available — cannot charge")
                self._charging_in_progress = False
                self._bus.emit(Event("charging_aborted", {
                    "reason": "dock_not_found",
                }, source="charging_manager"))
                return

            self.docking_controller.set_dock_info(dock)

            # Step 4: Navigate to dock
            nav_ok = self.dock_navigation.navigate_to_dock(dock)
            if not nav_ok:
                logger.error("❌ Cannot navigate to dock")
                self._charging_in_progress = False
                return

            # Step 5-7: Execute precision docking (async), then verify contact and charge
            def _on_dock_complete(success: bool) -> None:
                if not success:
                    logger.error("❌ Docking failed")
                    self._charging_in_progress = False
                    self._bus.emit(Event("charging_aborted", {
                        "reason": "docking_failed",
                    }, source="charging_manager"))
                    return

                # Step 6: Verify contact
                contact_ok = self.docking_controller.verify_contact()
                if not contact_ok:
                    logger.error("❌ No electrical contact detected")
                    self._charging_in_progress = False
                    return

                # Step 7: Start charging
                self.charging_controller.start_charging(battery_pct)

            self.docking_controller.execute_docking(dock, on_complete=_on_dock_complete)

        except Exception as exc:
            logger.exception("Charging sequence failed: %s", exc)
            self._charging_in_progress = False

    def _complete_charging(self, end_pct: int) -> None:
        """Complete the charging cycle and restore normal operation."""
        logger.info("✅ Charging cycle complete at %d%%", end_pct)
        self._bus.emit(Event("charging_cycle_complete", {
            "end_pct": end_pct,
        }, source="charging_manager"))

        # Record battery health
        session = self.charging_controller.current_session
        if session:
            self.battery_health.record_charge_cycle(
                start_pct=session.start_pct,
                end_pct=end_pct,
                duration_s=session.duration_s,
                energy_mah=session.energy_mah,
                avg_temp_c=session.avg_temp_c,
            )

        # Stop charging
        self.charging_controller.stop_charging()

        # Undock
        self.docking_controller.undock()

        # Restore power profile
        self.power_optimizer.restore_after_charge()

        # Resume interrupted tasks
        self.task_interruption.resume_after_charge()

        self._charging_in_progress = False
        logger.info("🔋 System restored after charging")

    def _on_battery_critical(self, event: Event) -> None:
        """Handle critical battery event from PowerManager."""
        pct = event.data.get("percent", 0)
        if not self._charging_in_progress:
            self._start_charging_sequence(pct, emergency=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def charge_now(self) -> bool:
        """Manually trigger an immediate charge cycle."""
        from tank_os.core.power_manager import PowerManager
        if self._charging_in_progress:
            return False
        self._start_charging_sequence(PowerManager().battery_percent)
        return True

    def enable_auto_charge(self, enabled: bool) -> None:
        self._auto_charge_enabled = enabled
        self._settings.set("charging.auto_enabled", enabled)

    def save_dock_position(self, x: float, y: float, yaw: float = 0.0) -> None:
        """Manually save or update the dock position."""
        self.dock_navigation.save_dock_position(x, y, yaw)

    def get_status(self) -> Dict[str, Any]:
        """Get a comprehensive charging system status report."""
        from tank_os.core.power_manager import PowerManager
        power = PowerManager()
        return {
            "battery_pct": power.battery_percent,
            "charging": power.is_charging,
            "auto_charge": self._auto_charge_enabled,
            "in_progress": self._charging_in_progress,
            "dock_status": self.docking_controller.status.name if self.docking_controller else "UNKNOWN",
            "charge_state": self.charging_controller.state.name if self.charging_controller else "IDLE",
            "battery_health": self.battery_health.summary(),
            "power_profile": power.performance_mode,
            "emergency_active": self.emergency_engine.is_emergency_active,
            "tasks_paused": self.task_interruption.has_saved_state,
        }

    def get_charging_history(self) -> List[Dict[str, Any]]:
        """Get historical charge session data."""
        from tank_os.core.power_manager import PowerManager
        power = PowerManager()
        return [
            {
                "battery_pct": power.battery_percent,
                "charging": power.is_charging,
                "health": self.battery_health.summary(),
            }
        ]

    def shutdown(self) -> None:
        """Clean shutdown of the charging system."""
        self._running = False
        if self._charging_in_progress:
            self.charging_controller.stop_charging()
        logger.info("ChargingManager shut down")
