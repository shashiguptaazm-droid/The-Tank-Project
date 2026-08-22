"""Hermetic tests for tank_vision.animations.

Animation is the cross-platform eye-display wire format used by:
* eye_lcd_bridge.UART → ESP32-S3 GC9A101 firmware
* (future) JS canvas on an HDMI display

These tests verify the JSON round-trip survives and that every shipped
animation has the expected frame vocabulary.
"""
from __future__ import annotations

import json
import unittest

from tank_vision.animations import (
    Animation,
    CENTER_X, CENTER_Y, EYE_W, EYE_H,
    FrameCommand,
    get_animation,
    get_animation_json,
    list_animations,
)


class FrameCommandTests(unittest.TestCase):

    def test_roundtrip(self) -> None:
        f = FrameCommand("fill", {"color": "#000000"})
        d = f.to_dict()
        again = FrameCommand.from_dict(d)
        self.assertEqual(again.cmd, "fill")
        self.assertEqual(again.args["color"], "#000000")

    def test_unknown_cmd_kept_as_string(self) -> None:
        f = FrameCommand("delayed", {"ms": 100})
        d = f.to_dict()
        again = FrameCommand.from_dict(d)
        self.assertEqual(again.cmd, "delayed")


class AnimationTests(unittest.TestCase):

    def test_roundtrip_full(self) -> None:
        a = Animation(
            name="t", fps=24, loop=True,
            frames=[
                FrameCommand("fill",   {"color": "#000000"}),
                FrameCommand("circle", {"x": 10, "y": 20, "r": 5,
                                 "color": "#FFAA00"}),
                FrameCommand("delay",  {"ms": 100}),
            ],
            description="round-trip fixture",
        )
        s = a.to_json()
        again = Animation.from_json(s)
        self.assertEqual(again.name, "t")
        self.assertEqual(again.fps, 24)
        self.assertEqual(again.loop, True)
        self.assertEqual(len(again.frames), 3)
        self.assertEqual(again.description, "round-trip fixture")

    def test_from_json_raises_on_malformed(self) -> None:
        with self.assertRaises((json.JSONDecodeError, KeyError, TypeError)):
            Animation.from_json("not json at all")

    def test_from_dict_defaults(self) -> None:
        a = Animation.from_dict({"name": "x", "frames": []})
        self.assertEqual(a.fps, 12)
        self.assertFalse(a.loop)
        self.assertEqual(a.description, "")


class BuiltinAnimationsTests(unittest.TestCase):

    EXPECTED = (
        "blink", "wink_left", "smile", "sad",
        "look_left", "look_right", "video_play_rickroll",
    )

    def test_list_animations_includes_expected(self) -> None:
        names = list_animations()
        for n in self.EXPECTED:
            self.assertIn(n, names)

    def test_look_left_and_right_are_distinct(self) -> None:
        a = get_animation("look_left")
        b = get_animation("look_right")
        self.assertIsNotNone(a)
        self.assertIsNotNone(b)
        assert a is not None and b is not None
        self.assertIn("circle", {f.cmd for f in a.frames})
        self.assertIn("circle", {f.cmd for f in b.frames})

    def test_get_animation_returns_none_for_unknown(self) -> None:
        self.assertIsNone(get_animation("never_heard_of"))

    def test_get_animation_json(self) -> None:
        s = get_animation_json("blink")
        self.assertIsInstance(s, str)
        self.assertIn('"name": "blink"', s)

    def test_each_builtin_has_non_empty_frames(self) -> None:
        for n in list_animations():
            a = get_animation(n)
            assert a is not None
            self.assertGreater(len(a.frames), 0,
                               f"{n} has no frames")

    def test_video_play_rickroll_references_video(self) -> None:
        a = get_animation("video_play_rickroll")
        assert a is not None
        cmds = [f.cmd for f in a.frames]
        self.assertIn("text", cmds)
        self.assertIn("video", cmds)


class EyeGeometryTests(unittest.TestCase):

    def test_constants(self) -> None:
        self.assertEqual(EYE_W, 240)
        self.assertEqual(EYE_H, 240)
        self.assertEqual(CENTER_X, 120)
        self.assertEqual(CENTER_Y, 120)


if __name__ == "__main__":
    unittest.main()
