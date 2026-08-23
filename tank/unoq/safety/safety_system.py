"""
safety.py - Safety System 2.0
Features 51-60: E-STOP FSM, interlocks, degraded mode, power alarms
"""
import time
import threading
import logging
from typing import Dict, Any, Optional, Callable
from enum import Enum

logger = logging.getLogger("tank.unoq.safety")


class EStopState(Enum):
    ARMED = "armed"
    TRIGGERED = "triggered"
    RESET_PENDING = "reset_pending"
    LOCKED = "locked"


class EStopReason(Enum):
    NONE = "none"
    MANUAL = "manual"
    COMM_LOSS = "comm_loss"
    OVERTEMP = "overtemp"
    LOW_BATTERY = "low_battery"
    SENSOR_FAULT = "sensor_fault"
    MOTOR_FAULT = "motor_fault"
    WATCHDOG = "watchdog"
    SOFTWARE = "software"


class SafetySystem2:
    """Hardware E-STOP state machine with interlocks and degraded mode."""

    def __init__(self):
        self.estop_state = EStopState.ARMED
        self.estop_reason = EStopReason.NONE
        self.estop_timestamp = 0.0
        self.motor_enabled = False
        self.servo_enabled = False
        self.interlock_motor = True
        self.interlock_servo = True
        self.degraded_mode = False
        self.comm_loss_threshold = 3.0
        self.last_comm_time = time.time()
        self.overtemp_threshold = 80.0
        self.low_battery_threshold = 10.5
        self.sensor_failure_count = 0
        self.max_sensor_failures = 3
        self.event_log = []
        self.on_estop: Optional[Callable] = None
        self._lock = threading.Lock()

    def _log_event(self, event: str, severity: str = "warning"):
        entry = {"time": time.time(), "event": event, "severity": severity}
        self.event_log.append(entry)
        if severity == "critical":
            logger.critical(event)
        else:
            logger.warning(event)

    def trigger(self, reason: EStopReason, detail: str = ""):
        with self._lock:
            if self.estop_state == EStopState.TRIGGERED:
                return
            self.estop_state = EStopState.TRIGGERED
            self.estop_reason = reason
            self.estop_timestamp = time.time()
            self.motor_enabled = False
            self.servo_enabled = False
        self._log_event(f"E-STOP TRIGGERED: {reason.value} - {detail}", "critical")
        if self.on_estop:
            try:
                self.on_estop({"reason": reason.value, "time": self.estop_timestamp})
            except Exception:
                pass

    def reset(self, authorized: bool = True) -> bool:
        if not authorized:
            self._log_event("E-STOP reset denied: not authorized")
            return False
        with self._lock:
            if self.estop_state == EStopState.LOCKED:
                self._log_event("E-STOP reset denied: locked")
                return False
            self.estop_state = EStopState.ARMED
            self.estop_reason = EStopReason.NONE
        self._log_event("E-STOP reset: armed")
        return True

    def lock(self):
        with self._lock:
            self.estop_state = EStopState.LOCKED
        self._log_event("E-STOP LOCKED", "critical")

    def enable_motors(self) -> bool:
        with self._lock:
            if self.estop_state != EStopState.ARMED:
                self._log_event("Motor enable denied: E-STOP not armed")
                return False
            self.motor_enabled = True
            self.interlock_motor = False
        return True

    def disable_motors(self):
        with self._lock:
            self.motor_enabled = False
            self.interlock_motor = True

    def enable_servos(self) -> bool:
        with self._lock:
            if self.estop_state != EStopState.ARMED:
                return False
            self.servo_enabled = True
            self.interlock_servo = False
        return True

    def disable_servos(self):
        with self._lock:
            self.servo_enabled = False
            self.interlock_servo = True

    def check_comm_loss(self):
        if time.time() - self.last_comm_time > self.comm_loss_threshold:
            if self.motor_enabled:
                self.trigger(EStopReason.COMM_LOSS, f"No comm for {self.comm_loss_threshold}s")

    def check_overtemp(self, temperature: float):
        if temperature > self.overtemp_threshold:
            self.trigger(EStopReason.OVERTEMP, f"Temp={temperature:.1f}°C")

    def check_low_battery(self, voltage: float):
        if voltage < self.low_battery_threshold:
            self.trigger(EStopReason.LOW_BATTERY, f"Vbat={voltage:.2f}V")

    def check_sensor_fault(self, fault: bool = True):
        if fault:
            self.sensor_failure_count += 1
            if self.sensor_failure_count >= self.max_sensor_failures:
                self.trigger(EStopReason.SENSOR_FAULT, f"{self.sensor_failure_count} failures")
                self.degraded_mode = True

    def check_watchdog(self):
        self.trigger(EStopReason.WATCHDOG, "MCU watchdog timeout")

    def update_comm(self):
        self.last_comm_time = time.time()

    def get_status(self) -> Dict[str, Any]:
        return {
            "estop_state": self.estop_state.value,
            "estop_reason": self.estop_reason.value,
            "estop_time_ago": time.time() - self.estop_timestamp if self.estop_timestamp else None,
            "motor_enabled": self.motor_enabled,
            "servo_enabled": self.servo_enabled,
            "interlock_motor": self.interlock_motor,
            "interlock_servo": self.interlock_servo,
            "degraded_mode": self.degraded_mode,
            "sensor_failures": self.sensor_failure_count,
            "comm_loss_ago": time.time() - self.last_comm_time,
            "event_count": len(self.event_log),
            "recent_events": self.event_log[-5:],
        }
