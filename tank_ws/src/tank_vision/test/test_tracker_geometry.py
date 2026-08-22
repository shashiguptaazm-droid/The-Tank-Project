"""Tests for the gaze-tracking math used by object_tracker.

Pulled out of the ROS node so it can be exercised under plain pytest
without spinning up ROS.

Run with:

    colcon build --packages-select tank_vision
    . install/setup.bash
    python3 -m pytest src/tank_vision/test/test_tracker_geometry.py
"""
import math

import pytest


def normalize(cx: float, cy: float, width: int, height: int):
    """Same mapping as in object_tracker — extracted for coverage."""
    cx_norm =  2.0 * (cx / width) - 1.0
    cy_norm = -2.0 * (cy / height) + 1.0
    return cx_norm, cy_norm


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def pan_tilt_command(cx_norm: float, cy_norm: float,
                     pan_kp: float = 0.6, tilt_kp: float = 0.6,
                     pan_min: float = -1.5708, pan_max: float = 1.5708,
                     tilt_min: float = -0.7854, tilt_max: float = 0.7854):
    """Mirror the tracker-side P controller, isolated for unit testing."""
    pan  = -pan_kp  * cx_norm
    tilt =  tilt_kp * cy_norm
    return clamp(pan, pan_min, pan_max), clamp(tilt, tilt_min, tilt_max)


def test_normalize_center_is_zero():
    assert normalize(640, 360, 1280, 720) == pytest.approx((0.0, 0.0))


def test_normalize_right_corner():
    cx, cy = normalize(1280, 360, 1280, 720)
    assert math.isclose(cx, 1.0, rel_tol=1e-9)
    assert math.isclose(cy, 0.0, rel_tol=1e-9)


def test_normalize_top_left_flips_signs():
    cx, cy = normalize(0, 0, 1280, 720)
    assert math.isclose(cx, -1.0, rel_tol=1e-9)
    # Top-left = max negative cy after y-flip convention.
    assert math.isclose(cy, 1.0, rel_tol=1e-9)


def test_pan_tilt_command_proportional():
    pan, tilt = pan_tilt_command( 0.5,  0.0)
    assert math.isclose(pan,  -0.30, rel_tol=1e-9)   # target is right of center, so pan left (-) to follow
    assert math.isclose(tilt,  0.0,  rel_tol=1e-9)


def test_pan_tilt_command_clamped_to_joint_limits():
    pan, _ = pan_tilt_command(-2.0, 0.0, pan_kp=1.0, pan_min=-1.0, pan_max=1.0)
    assert pan == 1.0


def test_pan_tilt_zero_when_target_centred():
    pan, tilt = pan_tilt_command(0.0, 0.0)
    assert pan == 0.0 and tilt == 0.0
