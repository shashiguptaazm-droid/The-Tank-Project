"""Hermetic tests for voice.play_music.

We patch ``shell_mpv`` so no real ``mpv`` subprocess ever spawns.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tank_command_bridge.plugins.play_music import PlayMusicPlugin


class TestPlayMusic(unittest.TestCase):
    def test_missing_query(self):
        out = PlayMusicPlugin().run({"query": ""})
        self.assertFalse(out["_ok"])
        self.assertIn("couldn't find", out["tts_text"])

    def test_no_match(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "Song A.mp3").write_bytes(b"x")
            with patch(
                "tank_command_bridge.plugins._house_helpers.DEFAULT_MUSIC_ROOTS",
                (Path(td),),
            ):
                out = PlayMusicPlugin().run({"query": "ZzzNoMatch",
                                              "root": td})
        self.assertFalse(out["_ok"])
        self.assertIn("couldn't find", out["tts_text"])

    def test_happy_path_with_music_root(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "Pink Floyd - Time.mp3"
            target.write_bytes(b"x")
            with patch(
                "tank_command_bridge.plugins.play_music.shell_mpv",
                return_value={"_ok": True, "pid": 12345,
                                "binary": "/usr/bin/mpv"},
            ):
                out = PlayMusicPlugin().run({"query": "Time",
                                              "root": td})
        self.assertTrue(out["_ok"])
        self.assertTrue(out["now_playing"]["path"].endswith("Pink Floyd - Time.mp3"))
        self.assertIn("Playing Time", out["tts_text"])

    def test_mpv_unavailable_returns_hint(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "Pink Floyd - Time.mp3").write_bytes(b"x")
            with patch(
                "tank_command_bridge.plugins.play_music.shell_mpv",
                return_value={"_ok": False, "_hint": "missing binary"},
            ):
                out = PlayMusicPlugin().run({"query": "Time", "root": td})
        self.assertFalse(out["_ok"])
        self.assertIn("couldn't start playback", out["tts_text"])


if __name__ == "__main__":
    unittest.main()
