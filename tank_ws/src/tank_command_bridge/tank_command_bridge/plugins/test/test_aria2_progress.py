"""Tests for ``voice.aria2_progress`` covering edge cases + happy paths."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from tank_command_bridge.plugins._aria2_common import Aria2Error
from tank_command_bridge.plugins.aria2_progress import Aria2ProgressPlugin


class TestAria2Progress(unittest.TestCase):
    def test_missing_gid(self):
        out = Aria2ProgressPlugin().run({"gid": ""})
        self.assertFalse(out["_ok"])
        self.assertIn("No download", out["tts_text"])

    def test_completed_status(self):
        fake = {
            "status": "complete", "totalLength": "1000000000",
            "completedLength": "1000000000",
            "downloadSpeed": "0", "uploadSpeed": "0",
            "numSeeders": 5, "connections": 5,
            "files": [{"path": "/downloads/Inception.mp4"}],
        }
        with patch("tank_command_bridge.plugins.aria2_progress.tell_status",
                   return_value=fake):
            out = Aria2ProgressPlugin().run({"gid": "abc"})
        self.assertTrue(out["_ok"])
        self.assertEqual(out["status"], "complete")
        self.assertEqual(out["progress_pct"], 100.0)
        self.assertIn("finished downloading", out["tts_text"])

    def test_active_with_eta(self):
        # 1 GB total, 0.4 GB done, 1 MB/s down → about 600 s = 10 min.
        fake = {
            "status": "active",
            "totalLength":     "1073741824",
            "completedLength": "429496730",
            "downloadSpeed":   "1048576",
            "uploadSpeed":     "0",
            "numSeeders": 8, "connections": 14,
        }
        with patch("tank_command_bridge.plugins.aria2_progress.tell_status",
                   return_value=fake):
            out = Aria2ProgressPlugin().run({"gid": "abc"})
        self.assertTrue(out["_ok"])
        self.assertGreater(out["progress_pct"], 30.0)
        self.assertGreater(out["eta_s"],         60)
        self.assertIn("minute", out["tts_text"])

    def test_error_path(self):
        # Patch with Aria2Error — that's what the plugin's `except`
        # actually catches. (Production realises this because
        # `_aria2_common.rpc()` wraps OSError / URLError into Aria2Error
        # before bubbling up; mocking `tell_status` directly by-passes
        # that wrapper, so the test must use the post-wrapped type.)
        with patch(
            "tank_command_bridge.plugins.aria2_progress.tell_status",
            side_effect=Aria2Error("RPC down"),
        ):
            out = Aria2ProgressPlugin().run({"gid": "abc"})
        self.assertFalse(out["_ok"])
        self.assertIn("couldn't reach aria2", out["tts_text"])
        self.assertIn("RPC down", out["tts_text"])

    def test_extract_title_falls_back_gracefully(self):
        # Malformed payload (bittorrent is a string, file path is None).
        bad = {
            "status": "active",
            "totalLength": "100", "completedLength": "50",
            "downloadSpeed": "0", "uploadSpeed": "0",
            "numSeeders": 0, "connections": 0,
            "bittorrent": "this-is-not-a-dict",
            "files": [{"path": None}],
        }
        with patch(
            "tank_command_bridge.plugins.aria2_progress.tell_status",
            return_value=bad,
        ):
            out = Aria2ProgressPlugin().run({"gid": "abc"})
        self.assertTrue(out["_ok"])
        self.assertIn("the download", out["tts_text"])


if __name__ == "__main__":
    unittest.main()
