"""Unit tests for the pure-Python skid-steer kinematics.

These tests don't touch ROS or hardware — they exercise the math directly.
Run them from inside the colcon workspace once you've built tank_motion:

    colcon build --packages-select tank_motion
    . install/setup.bash
    python3 -m pytest src/tank_motion/test/test_kinematics.py
"""
import math

import pytest

from tank_motion.truck_kinematics import (
    ChassisGeometry,
    compute_motor_command,
    rpm_to_pwm,
    track_speeds_to_rpm,
    track_speeds_to_twist,
    twist_to_track_speeds,
)


@pytest.fixture
def geo() -> ChassisGeometry:
    return ChassisGeometry(
        track_width=0.30,
        wheel_radius=0.05,
        max_linear_velocity=0.8,
        max_angular_velocity=1.5,
    )


def test_pure_translation(geo):
    v_l, v_r = twist_to_track_speeds(0.5, 0.0, geo)
    assert math.isclose(v_l, 0.5, rel_tol=1e-9)
    assert math.isclose(v_r, 0.5, rel_tol=1e-9)


def test_pure_rotation_clockwise_rotates_to_right(geo):
    v_l, v_r = twist_to_track_speeds(0.0, 1.0, geo)
    assert v_r > 0
    assert v_l < 0
    assert math.isclose(v_r - v_l, geo.track_width, rel_tol=1e-9)


def test_pure_rotation_counter_clockwise_rotates_to_left(geo):
    v_l, v_r = twist_to_track_speeds(0.0, -1.0, geo)
    assert v_l > 0
    assert v_r < 0


def test_kinematics_roundtrip(geo):
    v_l, v_r = twist_to_track_speeds(0.3, -0.7, geo)
    lin, ang = track_speeds_to_twist(v_l, v_r, geo)
    assert math.isclose(lin, 0.3, rel_tol=1e-2)
    assert math.isclose(ang, -0.7, rel_tol=1e-2)


def test_clamp_to_max_linear_velocity():
    slow_geo = ChassisGeometry(max_linear_velocity=0.5)
    v_l, v_r = twist_to_track_speeds(2.0, 0.0, slow_geo)
    assert abs(v_l) <= slow_geo.max_linear_velocity
    assert abs(v_r) <= slow_geo.max_linear_velocity


def test_clamp_to_max_angular_velocity():
    slow_geo = ChassisGeometry(max_angular_velocity=0.5)
    v_l, v_r = twist_to_track_speeds(0.0, 5.0, slow_geo)
    assert abs(v_r - v_l) <= slow_geo.max_angular_velocity * slow_geo.track_width + 1e-9


def test_rpm_to_pwm_zero():
    assert rpm_to_pwm(0.0, 220.0) == 0.0


def test_rpm_to_pwm_half():
    assert rpm_to_pwm(110.0, 220.0) == 0.5
    assert rpm_to_pwm(-110.0, 220.0) == -0.5


def test_rpm_to_pwm_clamp():
    assert rpm_to_pwm(330.0, 220.0) == 1.0
    assert rpm_to_pwm(-330.0, 220.0) == -1.0


def test_rpm_to_pwm_zero_max_rpm_returns_zero():
    assert rpm_to_pwm(100.0, 0.0) == 0.0


def test_track_speeds_to_rpm_basic():
    geo = ChassisGeometry(wheel_radius=0.05)
    rpm_l, rpm_r = track_speeds_to_rpm(0.0, 0.0, geo)
    assert rpm_l == 0.0
    assert rpm_r == 0.0

    rpm_l, _ = track_speeds_to_rpm(0.1, 0.0, geo)
    expected = 0.1 / 0.05 * 60.0 / (2.0 * math.pi)
    assert math.isclose(rpm_l, expected, rel_tol=1e-6)


def test_compute_motor_command_returns_duty_and_velocities(geo):
    duty_l, duty_r, v_l, v_r = compute_motor_command(0.4, 0.2, geo, max_rpm=220.0)
    assert math.isfinite(duty_l)
    assert math.isfinite(duty_r)
    assert abs(duty_l) <= 1.0
    assert abs(duty_r) <= 1.0
    assert math.isfinite(v_l)
    assert math.isfinite(v_r)
