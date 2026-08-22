"""Hermetic tests for voice.play_youtube.

We patch ``shell_ytdlp`` / ``shell_cast`` so no real subprocess runs.
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from tank_command_bridge.plugins.play_youtube import PlayYouTubePlugin


class TestPlayYouTube(unittest.TestCase):
    def test_missing_query(self):
        out = PlayYouTubePlugin().run({"query": ""})
        self.assertFalse(out["_ok"])
        self.assertEqual(out["url"], "")

    def test_extraction_success_no_cast(self):
        with patch(
            "tank_command_bridge.plugins.play_youtube.shell_ytdlp",
            return_value={"_ok": True,
                          "url": "https://stream.example/v.mp4",
                          "query": "Pink Floyd Time"},
        ):
            out = PlayYouTubePlugin().run({"query": "Pink Floyd Time"})
        self.assertTrue(out["_ok"])
        self.assertEqual(out["url"], "https://stream.example/v.mp4")
        self.assertEqual(out["cast"], {})
        self.assertIn("Which device", out["tts_text"])

    def test_extraction_failure(self):
        with patch(
            "tank_command_bridge.plugins.play_youtube.shell_ytdlp",
            return_value={"_ok": False, "_hint": "no internet"},
        ):
            out = PlayYouTubePlugin().run({"query": "Pink Floyd Time"})
        self.assertFalse(out["_ok"])
        self.assertIn("couldn't pull", out["tts_text"])

    def test_cast_target_round_trip(self):
        with patch(
            "tank_command_bridge.plugins.play_youtube.shell_ytdlp",
            return_value={"_ok": True,
                          "url": "https://stream/abc",
                          "query": "x"},
        ), patch(
            "tank_command_bridge.plugins.play_youtube.shell_cast",
            return_value={"_ok": True, "pid": 999, "binary": "/u/c",
                            "device": "kitchen echo",
                            "target": "https://stream/abc"},
        ):
            out = PlayYouTubePlugin().run({
                "query": "Pink Floyd Time",
                "cast_target": "kitchen echo",
            })
        self.assertTrue(out["_ok"])
        self.assertEqual(out["cast"]["device"], "kitchen echo")
        self.assertIn("Casting to kitchen echo", out["tts_text"])


if __name__ == "__main__":
    unittest.main()
