"""Hermetic tests for the chassis-plugins batch.

Each plug-in delegates to a pluggable :class:`ChassisMotionProvider`;
tests inject a :class:`NullChassisMotionProvider` so we never spin ROS.
"""
from __future__ import annotations

import threading
import unittest
from typing import Any, Dict

from tank_command_bridge.plugins._chassis_helpers import (
    NullChassisMotionProvider,
    Twist,
)
from tank_command_bridge.plugins.chassis_drive import (
    BrakeMotionPlugin,
    DriveBackwardPlugin,
    DriveForwardPlugin,
)
from tank_command_bridge.plugins.chassis_turn import (
    SpinPlugin,
    TurnLeftPlugin,
    TurnRightPlugin,
)
from tank_command_bridge.plugins.chassis_speed import (
    SetCruiseModePlugin,
    SetMaxSpeedPlugin,
)
from tank_command_bridge.plugins.chassis_follow import (
    FollowMePlugin,
    PausePatrolPlugin,
    ResumePatrolPlugin,
    StopFollowMePlugin,
)


def _ctx() -> Any:
    """Return a fresh ctx with its own Null chassis provider."""
    p = NullChassisMotionProvider()
    return _Anypack(p)


class _Anypack:
    def __init__(self, p: Any) -> None:
        self.chassis_motion = p


# ──────────────────────────────────────────────────────────────────────────────
# drive_forward / drive_backward / brake_motion
# ──────────────────────────────────────────────────────────────────────────────

class DriveForwardTests(unittest.TestCase):

    def setUp(self) -> None:
        self.ctx = _ctx()

    def test_default_one_meter(self) -> None:
        out = DriveForwardPlugin().run({}, ctx=self.ctx)
        self.assertTrue(out["_ok"])
        self.assertAlmostEqual(out["distance_m"], 1.0, places=2)
        self.assertGreater(out["twists"], 0)

    def test_two_meters(self) -> None:
        out = DriveForwardPlugin().run(
            {"distance": "two meters"}, ctx=self.ctx)
        self.assertTrue(out["_ok"])
        self.assertAlmostEqual(out["distance_m"], 2.0, places=2)

    def test_speed_override(self) -> None:
        out = DriveForwardPlugin().run(
            {"distance": "1", "speed_mps": 0.5}, ctx=self.ctx)
        self.assertAlmostEqual(out["speed_mps"], 0.5, places=2)

    def test_publish_records_twists(self) -> None:
        before = len(self.ctx.chassis_motion.twists)
        DriveForwardPlugin().run(
            {"distance": "half a meter"}, ctx=self.ctx)
        after = len(self.ctx.chassis_motion.twists)
        self.assertGreater(after, before)


class DriveBackwardTests(unittest.TestCase):

    def test_negative_speed_published(self) -> None:
        ctx = _ctx()
        DriveBackwardPlugin().run(
            {"distance": "one meter"}, ctx=ctx)
        # Last twist is the brake (zero); the prior ones had -speed.
        nonzero = [tw for _, tw in ctx.chassis_motion.twists
                   if not tw.is_zero()]
        self.assertGreater(len(nonzero), 0)
        self.assertLess(nonzero[0].linear_x, 0.0)


class BrakeTests(unittest.TestCase):

    def test_halts_and_zeroes(self) -> None:
        ctx = _ctx()
        # First push some non-zero, then brake.
        ctx.chassis_motion.publish_twist(Twist(linear_x=0.2))
        out = BrakeMotionPlugin().run({}, ctx=ctx)
        self.assertTrue(out["_ok"])
        self.assertTrue(out["halted"])
        _, last = ctx.chassis_motion.twists[-1]
        self.assertTrue(last.is_zero())
        self.assertFalse(ctx.chassis_motion.follower_active())


# ──────────────────────────────────────────────────────────────────────────────
# turn_left / turn_right / spin_around
# ──────────────────────────────────────────────────────────────────────────────

class TurnTests(unittest.TestCase):

    def test_turn_left_positive_angular(self) -> None:
        ctx = _ctx()
        TurnLeftPlugin().run({}, ctx=ctx)
        signed = [(tw.linear_x, tw.angular_z)
                  for _, tw in ctx.chassis_motion.twists
                  if tw.angular_z != 0]
        self.assertTrue(all(z > 0 for _, z in signed),
                        f"all angular_z should be positive for LEFT; got {signed}")

    def test_turn_right_negative_angular(self) -> None:
        ctx = _ctx()
        TurnRightPlugin().run({}, ctx=ctx)
        signed = [(tw.linear_x, tw.angular_z)
                  for _, tw in ctx.chassis_motion.twists
                  if tw.angular_z != 0]
        self.assertTrue(all(z < 0 for _, z in signed),
                        f"all angular_z should be negative for RIGHT; got {signed}")

    def test_turn_with_angle(self) -> None:
        ctx = _ctx()
        TurnLeftPlugin().run({"angle": "180 degrees"}, ctx=ctx)
        self.assertGreater(len(ctx.chassis_motion.twists), 0)


class SpinTests(unittest.TestCase):

    def test_spin_default_left(self) -> None:
        ctx = _ctx()
        out = SpinPlugin().run({}, ctx=ctx)
        self.assertTrue(out["_ok"])
        self.assertEqual(out["angle_deg"], 360.0)

    def test_spin_right_flips_sign(self) -> None:
        ctx = _ctx()
        SpinPlugin().run({"direction": "right"}, ctx=ctx)
        signed = [tw.angular_z for _, tw in ctx.chassis_motion.twists
                  if tw.angular_z != 0]
        self.assertTrue(all(z < 0 for z in signed),
                        f"all angular_z should be negative for spin-right")


# ──────────────────────────────────────────────────────────────────────────────
# set_max_speed / set_cruise_mode
# ──────────────────────────────────────────────────────────────────────────────

class SetMaxSpeedTests(unittest.TestCase):

    def test_set_within_envelope(self) -> None:
        ctx = _ctx()
        out = SetMaxSpeedPlugin().run(
            {"linear_mps": 0.25, "angular_rps": 0.6}, ctx=ctx)
        self.assertTrue(out["_ok"])
        self.assertFalse(out["warnings"])
        self.assertAlmostEqual(out["applied_linear_mps"], 0.25, places=3)

    def test_clamps_and_warns(self) -> None:
        ctx = _ctx()
        out = SetMaxSpeedPlugin().run(
            {"linear_mps": 99.0, "angular_rps": 99.0}, ctx=ctx)
        self.assertTrue(out["_ok"])
        self.assertTrue(len(out["warnings"]) >= 1)

    def test_garbage_value_clamps(self) -> None:
        ctx = _ctx()
        out = SetMaxSpeedPlugin().run(
            {"linear_mps": "not-a-float"}, ctx=ctx)
        self.assertTrue(out["_ok"])


class SetCruiseModeTests(unittest.TestCase):

    def test_enable(self) -> None:
        ctx = _ctx()
        SetCruiseModePlugin().run({"enabled": True}, ctx=ctx)
        self.assertTrue(ctx.chassis_motion.cruise_mode)

    def test_disable(self) -> None:
        ctx = _ctx()
        SetCruiseModePlugin().run({"enabled": False}, ctx=ctx)
        self.assertFalse(ctx.chassis_motion.cruise_mode)


# ──────────────────────────────────────────────────────────────────────────────
# follow_me / stop_follow_me / pause_patrol / resume_patrol
# ──────────────────────────────────────────────────────────────────────────────

class FollowMeTests(unittest.TestCase):

    def test_follow_engages(self) -> None:
        ctx = _ctx()
        out = FollowMePlugin().run({"distance_m": 1.0}, ctx=ctx)
        self.assertTrue(out["_ok"])
        self.assertTrue(out["engaged"])
        self.assertTrue(ctx.chassis_motion.follower_active())

    def test_stop_follow_disengages(self) -> None:
        ctx = _ctx()
        ctx.chassis_motion.follower_start()
        out = StopFollowMePlugin().run({}, ctx=ctx)
        self.assertTrue(out["_ok"])
        self.assertFalse(ctx.chassis_motion.follower_active())

    def test_idempotent_follow(self) -> None:
        ctx = _ctx()
        FollowMePlugin().run({}, ctx=ctx)
        # Calling again is a no-op but still succeeds.
        out = FollowMePlugin().run({}, ctx=ctx)
        self.assertTrue(out["_ok"])


class PatrolTests(unittest.TestCase):

    def test_pause_resume(self) -> None:
        ctx = _ctx()
        PausePatrolPlugin().run({}, ctx=ctx)
        self.assertTrue(ctx.chassis_motion.patrol_paused)
        ResumePatrolPlugin().run({}, ctx=ctx)
        self.assertFalse(ctx.chassis_motion.patrol_paused)


if __name__ == "__main__":
    unittest.main()
