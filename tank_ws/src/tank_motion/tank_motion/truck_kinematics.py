"""Skid-steer kinematics for The Tank Project.

Pure Python, no ROS dependencies — kept deliberately standalone so we can
test it with pytest on a developer laptop without bringing up a ROS env.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ChassisGeometry:
    """Physical dimensions of the tracked chassis (SI units)."""
    track_width: float = 0.30            # distance between the two tracks (m)
    wheel_radius: float = 0.05           # drive sprocket radius (m)
    max_linear_velocity: float = 0.8     # m/s
    max_angular_velocity: float = 1.5    # rad/s


def twist_to_track_speeds(linear: float, angular: float,
                          geo: ChassisGeometry) -> tuple[float, float]:
    """Inverse kinematics: Twist -> (v_left, v_right) in m/s.

    Inputs are clamped to the chassis's velocity envelope. If the resulting
    per-track speeds exceed ``max_linear_velocity`` after the angular split
    (possible when the user requests a fast spin at high linear speed), we
    rescale proportionally so neither motor saturates.
    """
    if abs(linear) > geo.max_linear_velocity:
        linear = math.copysign(geo.max_linear_velocity, linear)
    if abs(angular) > geo.max_angular_velocity:
        angular = math.copysign(geo.max_angular_velocity, angular)
    v_left  = linear - angular * geo.track_width / 2.0
    v_right = linear + angular * geo.track_width / 2.0
    max_speed = max(abs(v_left), abs(v_right))
    if max_speed > geo.max_linear_velocity and max_speed > 0.0:
        scale = geo.max_linear_velocity / max_speed
        v_left *= scale
        v_right *= scale
    return v_left, v_right


def track_speeds_to_twist(v_left: float, v_right: float,
                          geo: ChassisGeometry) -> tuple[float, float]:
    """Forward kinematics: (v_left, v_right) -> (linear, angular)."""
    linear  = (v_right + v_left) / 2.0
    angular = (v_right - v_left) / geo.track_width
    return linear, angular


def track_speeds_to_rpm(v_left: float, v_right: float,
                        geo: ChassisGeometry) -> tuple[float, float]:
    """Linear m/s at the sprocket -> angular RPM at the motor shaft."""
    omega_left  = v_left  / geo.wheel_radius
    omega_right = v_right / geo.wheel_radius
    rpm_left  = omega_left  * 60.0 / (2.0 * math.pi)
    rpm_right = omega_right * 60.0 / (2.0 * math.pi)
    return rpm_left, rpm_right


def rpm_to_pwm(rpm: float, max_rpm: float) -> float:
    """RPM -> PWM duty cycle in [-1.0, 1.0].

    Sign encodes direction; the motor-driver HAL interprets negative duty
    as reverse by flipping the DIR pin before applying PWM magnitude.
    """
    if max_rpm <= 0.0:
        return 0.0
    duty = rpm / max_rpm
    return max(-1.0, min(1.0, duty))


def compute_motor_command(linear: float, angular: float,
                          geo: ChassisGeometry,
                          max_rpm: float) -> tuple[float, float, float, float]:
    """End-to-end Twist -> per-motor PWM duty cycles.

    Returns (duty_left, duty_right, v_left, v_right) so the caller's
    telemetry code can publish ``/odom`` and ``/motor_status`` without
    re-running every step.
    """
    v_left, v_right  = twist_to_track_speeds(linear, angular, geo)
    rpm_left, rpm_right = track_speeds_to_rpm(v_left, v_right, geo)
    duty_left  = rpm_to_pwm(rpm_left,  max_rpm)
    duty_right = rpm_to_pwm(rpm_right, max_rpm)
    return duty_left, duty_right, v_left, v_right
