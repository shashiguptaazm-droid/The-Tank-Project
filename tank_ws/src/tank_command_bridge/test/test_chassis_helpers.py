"""Hermetic tests for tank_command_bridge.plugins._chassis_helpers.

The chassis plug-ins (drive, turn, speed, follow) all delegate to
``ChassisMotionProvider``. Tests use :class:`NullChassisMotionProvider`
which records every Twist it would have published.

Coverage:
* :class:`Twist` struct → :meth:`to_dict` / :meth:`is_zero`
* :class:`NullChassisMotionProvider` records publishes, odometry/IMU
  resets, calibrations, speed envelopes, cruise + follower flags.
* :func:`parse_distance_m` and :func:`parse_angle_deg` cover English,
  metric + imperial.
* :func:`safe_drive_seconds` / :func:`safe_rotate_seconds` clamp on
  the operator's safety envelope.
"""
from __future__ import annotations

import unittest

from tank_command_bridge.plugins._chassis_helpers import (
    DEFAULT_MAX_LINEAR_MPS,
    DEFAULT_MAX_ANGULAR_RPS,
    DEFAULT_DISTANCE_TIMEOUT_S,
    DEFAULT_ROTATION_TIMEOUT_S,
    NullChassisMotionProvider,
    Twist,
    clamp,
    parse_angle_deg,
    parse_distance_m,
    safe_drive_seconds,
    safe_rotate_seconds,
)


class TwistTests(unittest.TestCase):

    def test_is_zero(self) -> None:
        self.assertTrue(Twist().is_zero())
        self.assertFalse(Twist(linear_x=0.1).is_zero())
        self.assertFalse(Twist(angular_z=0.1).is_zero())

    def test_to_dict(self) -> None:
        d = Twist(linear_x=0.2, linear_y=0.0, angular_z=0.5).to_dict()
        self.assertEqual(d, {"linear_x": 0.2,
                             "linear_y": 0.0,
                             "angular_z": 0.5})


class NullChassisMotionProviderTests(unittest.TestCase):

    def setUp(self) -> None:
        self.p = NullChassisMotionProvider()

    def test_publish_twist_records(self) -> None:
        self.p.publish_twist(Twist(linear_x=0.2))
        self.p.publish_twist(Twist(linear_x=0.3))
        self.assertEqual(len(self.p.twists), 2)

    def test_current_speed_zero_when_empty(self) -> None:
        self.assertEqual(self.p.current_speed(), (0.0, 0.0))

    def test_current_speed_last_published(self) -> None:
        self.p.publish_twist(Twist(linear_x=0.2, angular_z=0.4))
        self.assertEqual(self.p.current_speed(), (0.2, 0.4))

    def test_reset_odometry(self) -> None:
        self.p.reset_odometry()
        self.p.reset_odometry()
        self.assertEqual(self.p.odometry_resets, 2)

    def test_reset_imu(self) -> None:
        self.p.reset_imu()
        self.assertEqual(self.p.imu_resets, 1)

    def test_run_calibration_returns_meta(self) -> None:
        meta = self.p.run_calibration()
        self.assertTrue(meta["ok"])
        self.assertIn("track_width_m", meta)
        self.assertIn("wheel_radius_m", meta)
        self.assertGreaterEqual(meta["samples"], 1)
        self.assertEqual(self.p.calibrations, 1)

    def test_set_max_linear_clamps(self) -> None:
        # Garbage / out-of-range should clamp, not crash.
        self.p.set_max_linear(0.001)        # below low-water mark
        self.assertGreaterEqual(self.p.max_linear, 0.05)
        self.p.set_max_linear("not-a-float")  # type: ignore[arg-type]
        # midpoint fallback for None / garbage
        self.assertGreater(self.p.max_linear, 0.05)
        self.p.set_max_linear(99.0)
        self.assertLessEqual(
            self.p.max_linear, DEFAULT_MAX_LINEAR_MPS * 2)

    def test_set_max_angular_clamps(self) -> None:
        self.p.set_max_angular(0.01)
        self.assertGreaterEqual(self.p.max_angular, 0.1)
        self.p.set_max_angular(99.0)
        self.assertLessEqual(
            self.p.max_angular, DEFAULT_MAX_ANGULAR_RPS * 2)

    def test_cruise_mode_toggle(self) -> None:
        self.p.set_cruise_mode(True)
        self.assertTrue(self.p.cruise_mode)
        self.p.set_cruise_mode(False)
        self.assertFalse(self.p.cruise_mode)

    def test_follower_toggle(self) -> None:
        self.assertFalse(self.p.follower_active())
        self.p.follower_start()
        self.assertTrue(self.p.follower_active())
        self.p.follower_stop()
        self.assertFalse(self.p.follower_active())

    def test_patrol_pause_resume(self) -> None:
        self.p.patrol_pause()
        self.assertTrue(self.p.patrol_paused)
        self.p.patrol_resume()
        self.assertFalse(self.p.patrol_paused)


class ParseDistanceTests(unittest.TestCase):

    def test_empty(self) -> None:
        self.assertEqual(parse_distance_m(""), 1.0)

    def test_meters_default(self) -> None:
        self.assertAlmostEqual(parse_distance_m("a meter"), 1.0)

    def test_half_meter(self) -> None:
        self.assertAlmostEqual(parse_distance_m("half a meter"), 0.5)

    def test_two_meters(self) -> None:
        self.assertAlmostEqual(parse_distance_m("two meters"), 2.0)

    def test_metric_units(self) -> None:
        self.assertAlmostEqual(parse_distance_m("50 cm"), 0.5)
        self.assertAlmostEqual(parse_distance_m("250 mm"), 0.25)
        self.assertAlmostEqual(parse_distance_m("2500 mm"), 2.5)

    def test_imperial_units(self) -> None:
        # 1 ft = 0.3048 m
        self.assertAlmostEqual(parse_distance_m("5 ft"), 5 * 0.3048,
                               places=4)
        self.assertAlmostEqual(parse_distance_m("10 in"), 10 * 0.0254,
                               places=4)

    def test_numeric_fallback(self) -> None:
        # "1.5" with no unit → 1.5 m
        self.assertAlmostEqual(parse_distance_m("1.5"), 1.5)


class ParseAngleTests(unittest.TestCase):

    def test_empty(self) -> None:
        self.assertEqual(parse_angle_deg(""), 90.0)

    def test_ninety(self) -> None:
        self.assertAlmostEqual(parse_angle_deg("90"), 90.0)
        self.assertAlmostEqual(parse_angle_deg("ninety"), 90.0)

    def test_one_eighty(self) -> None:
        self.assertAlmostEqual(parse_angle_deg("one eighty"), 180.0)

    def test_with_unit(self) -> None:
        self.assertAlmostEqual(parse_angle_deg("45 degrees"), 45.0)


class ClampTests(unittest.TestCase):

    def test_in_range(self) -> None:
        self.assertEqual(clamp(2.0, 0.0, 5.0), 2.0)

    def test_low(self) -> None:
        self.assertEqual(clamp(-1.0, 0.0, 5.0), 0.0)

    def test_high(self) -> None:
        self.assertEqual(clamp(99.0, 0.0, 5.0), 5.0)

    def test_garbage_returns_midpoint(self) -> None:
        self.assertEqual(clamp("nope", 0.0, 4.0), 2.0)


class SafetyEnvelopeTests(unittest.TestCase):

    def test_safe_drive_seconds_scales(self) -> None:
        t1 = safe_drive_seconds(1.0, 0.1)
        t2 = safe_drive_seconds(2.0, 0.1)
        self.assertAlmostEqual(t2, 2 * t1, places=2)

    def test_safe_drive_clamps_speed(self) -> None:
        # Asking for too-fast gives the safety envelope lower bound.
        t = safe_drive_seconds(1.0, 5.0)
        self.assertGreater(t, 0)
        self.assertLessEqual(t, DEFAULT_DISTANCE_TIMEOUT_S)

    def test_safe_rotate_clamps_angle(self) -> None:
        t = safe_rotate_seconds(720.0, 0.5)
        self.assertGreater(t, 0)
        self.assertLessEqual(t, DEFAULT_ROTATION_TIMEOUT_S)


if __name__ == "__main__":
    unittest.main()
