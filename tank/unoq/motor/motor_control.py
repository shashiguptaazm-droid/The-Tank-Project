"""
motor_control.py - UNO Q Motor Control 2.0
Features 31-40: PID, dead-zone compensation, stall detection, track-slip
"""
import time
import math
import threading
import logging
from typing import Dict, Any, Optional, Tuple
from enum import Enum

logger = logging.getLogger("tank.unoq.motor")


class MotorState(Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    STALLED = "stalled"
    FAULT = "fault"
    CALIBRATING = "calibrating"


class PIDController:
    """Per-motor PID controller."""

    def __init__(self, kp=1.0, ki=0.1, kd=0.05, dt=0.05):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.dt = dt
        self.setpoint = 0.0
        self.integral = 0.0
        self.prev_error = 0.0
        self.output = 0.0
        self.integral_limit = 100.0

    def compute(self, measured: float) -> float:
        error = self.setpoint - measured
        self.integral += error * self.dt
        self.integral = max(-self.integral_limit, min(self.integral_limit, self.integral))
        derivative = (error - self.prev_error) / self.dt if self.dt > 0 else 0
        self.output = self.kp * error + self.ki * self.integral + self.kd * derivative
        self.prev_error = error
        return self.output

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0
        self.output = 0.0

    def auto_tune(self, target_speed: float, measured_speeds: list) -> dict:
        if not measured_speeds:
            return {"status": "no_data"}
        avg = sum(measured_speeds) / len(measured_speeds)
        variance = sum((x - avg) ** 2 for x in measured_speeds) / len(measured_speeds)
        overshoot = max(measured_speeds) - target_speed if target_speed > 0 else 0
        settling_time = len(measured_speeds) * self.dt
        if variance < 1.0 and overshoot < target_speed * 0.1:
            self.kp *= 1.1
        elif overshoot > target_speed * 0.3:
            self.kp *= 0.8
        return {
            "target": target_speed,
            "average": avg,
            "variance": variance,
            "overshoot_pct": (overshoot / target_speed * 100) if target_speed else 0,
            "settling_time": settling_time,
            "new_kp": self.kp,
            "new_ki": self.ki,
            "new_kd": self.kd,
        }


class MotorController:
    """Full motor control with PID, dead-zone, stall detection, track-slip."""

    def __init__(self, send_fn=None):
        self.send_fn = send_fn or (lambda x: None)
        self.pid_left = PIDController(kp=2.0, ki=0.5, kd=0.1)
        self.pid_right = PIDController(kp=2.0, ki=0.5, kd=0.1)
        self.state_left = MotorState.STOPPED
        self.state_right = MotorState.STOPPED
        self.left_speed = 0
        self.right_speed = 0
        self.left_encoder = 0
        self.right_encoder = 0
        self.left_encoder_prev = 0
        self.right_encoder_prev = 0
        self.left_rpm = 0.0
        self.right_rpm = 0.0
        self.max_speed = 255
        self.accel_limit = 50
        self.decel_limit = 80
        self.command_timeout_ms = 2000
        self.last_command_time = 0.0
        self.dead_zone_left = 15
        self.dead_zone_right = 15
        self.stall_threshold = 2.0
        self.stall_timer_left = 0.0
        self.stall_timer_right = 0.0
        self.stall_detected_left = False
        self.stall_detected_right = False
        self.motor_fault = False
        self._lock = threading.Lock()
        self.on_stall: Optional[callable] = None
        self.on_fault: Optional[callable] = None

    def set_motors(self, left: int, right: int):
        left = max(-self.max_speed, min(self.max_speed, left))
        right = max(-self.max_speed, min(self.max_speed, right))
        with self._lock:
            left = self._apply_accel_limit(self.left_speed, left)
            right = self._apply_accel_limit(self.right_speed, right)
            left = self._apply_dead_zone(left, self.dead_zone_left)
            right = self._apply_dead_zone(right, self.dead_zone_right)
            self.left_speed = left
            self.right_speed = right
            self.last_command_time = time.time()
        self._send_motor_cmd(left, right)

    def differential_drive(self, speed: int, turn: int):
        left = speed + turn
        right = speed - turn
        self.set_motors(left, right)

    def _apply_accel_limit(self, current: int, target: int) -> int:
        if target > current:
            return min(current + self.accel_limit, target)
        else:
            return max(current - self.decel_limit, target)

    def _apply_dead_zone(self, value: int, dead_zone: int) -> int:
        if abs(value) < dead_zone:
            return 0
        if value > 0:
            return max(0, value - dead_zone)
        return min(0, value + dead_zone)

    def _send_motor_cmd(self, left: int, right: int):
        cmd = f"MOTOR:{left},{right}\n".encode()
        try:
            self.send_fn(cmd)
        except Exception as e:
            logger.error(f"Motor command failed: {e}")

    def update_encoders(self, left_enc: int, right_enc: int):
        with self._lock:
            dt = 0.05
            self.left_rpm = (left_enc - self.left_encoder_prev) / dt * 60.0
            self.right_rpm = (right_enc - self.right_encoder_prev) / dt * 60.0
            self.left_encoder_prev = self.left_encoder
            self.right_encoder_prev = self.right_encoder
            self.left_encoder = left_enc
            self.right_encoder = right_enc
        self._check_stall(left_enc, right_enc)
        self._check_track_slip()

    def _check_stall(self, left_enc: int, right_enc: int):
        now = time.time()
        with self._lock:
            if abs(self.left_speed) > 20 and abs(left_enc - self.left_encoder_prev) < 2:
                if self.stall_timer_left == 0:
                    self.stall_timer_left = now
                elif now - self.stall_timer_left > self.stall_threshold:
                    if not self.stall_detected_left:
                        self.stall_detected_left = True
                        self.state_left = MotorState.STALLED
                        logger.warning("Left motor STALL detected")
                        if self.on_stall:
                            self.on_stall({"motor": "left", "timestamp": now})
            else:
                self.stall_timer_left = 0
                if self.stall_detected_left:
                    self.stall_detected_left = False
                    self.state_left = MotorState.RUNNING

            if abs(self.right_speed) > 20 and abs(right_enc - self.right_encoder_prev) < 2:
                if self.stall_timer_right == 0:
                    self.stall_timer_right = now
                elif now - self.stall_timer_right > self.stall_threshold:
                    if not self.stall_detected_right:
                        self.stall_detected_right = True
                        self.state_right = MotorState.STALLED
                        logger.warning("Right motor STALL detected")
                        if self.on_stall:
                            self.on_stall({"motor": "right", "timestamp": now})
            else:
                self.stall_timer_right = 0
                if self.stall_detected_right:
                    self.stall_detected_right = False
                    self.state_right = MotorState.RUNNING

    def _check_track_slip(self):
        if abs(self.left_speed) > 10 and abs(self.right_speed) > 10:
            slip_ratio = abs(abs(self.left_rpm) - abs(self.right_rpm)) / max(abs(self.left_rpm), abs(self.right_rpm), 1)
            if slip_ratio > 0.4:
                logger.warning(f"Track slip detected: ratio={slip_ratio:.2f}")

    def emergency_stop(self):
        with self._lock:
            self.left_speed = 0
            self.right_speed = 0
        self._send_motor_cmd(0, 0)
        self.state_left = MotorState.STOPPED
        self.state_right = MotorState.STOPPED
        self.pid_left.reset()
        self.pid_right.reset()
        logger.warning("EMERGENCY STOP executed")

    def check_command_timeout(self):
        if self.last_command_time > 0:
            elapsed = (time.time() - self.last_command_time) * 1000
            if elapsed > self.command_timeout_ms:
                if self.left_speed != 0 or self.right_speed != 0:
                    logger.warning(f"Command timeout ({elapsed:.0f}ms), stopping motors")
                    self.emergency_stop()

    def set_speed_limit(self, max_speed: int):
        self.max_speed = max(0, min(255, max_speed))

    def set_acceleration_limit(self, accel: int, decel: int):
        self.accel_limit = accel
        self.decel_limit = decel

    def calibrate_dead_zone(self, motor: str = "both") -> dict:
        self.state_left = MotorState.CALIBRATING if motor in ("left", "both") else self.state_left
        self.state_right = MotorState.CALIBRATING if motor in ("right", "both") else self.state_right
        return {"status": "calibrating", "motor": motor, "test_speeds": [10, 20, 30, 40, 50]}

    def set_pid(self, motor: str, kp: float, ki: float, kd: float):
        pid = self.pid_left if motor == "left" else self.pid_right
        pid.kp = kp
        pid.ki = ki
        pid.kd = kd

    def get_status(self) -> dict:
        return {
            "left_speed": self.left_speed,
            "right_speed": self.right_speed,
            "left_rpm": round(self.left_rpm, 1),
            "right_rpm": round(self.right_rpm, 1),
            "left_encoder": self.left_encoder,
            "right_encoder": self.right_encoder,
            "left_state": self.state_left.value,
            "right_state": self.state_right.value,
            "stall_left": self.stall_detected_left,
            "stall_right": self.stall_detected_right,
            "motor_fault": self.motor_fault,
            "pid_left": {"kp": self.pid_left.kp, "ki": self.pid_left.ki, "kd": self.pid_left.kd},
            "pid_right": {"kp": self.pid_right.kp, "ki": self.pid_right.ki, "kd": self.pid_right.kd},
            "accel_limit": self.accel_limit,
            "decel_limit": self.decel_limit,
            "max_speed": self.max_speed,
            "dead_zone_l": self.dead_zone_left,
            "dead_zone_r": self.dead_zone_right,
        }
