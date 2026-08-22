"""Hermetic tests for the shared house-helper module.

These tests cover zone map persistence, ARP-table mocking, the music
filename match heuristic, and the lazy-binary ``which_or_hint`` /
``shell_mpv`` / ``shell_ytdlp`` / ``shell_cast`` wrappers — all with
injected subprocess stubs so we never spawn real mpv / yt-dlp.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from tank_command_bridge.plugins._house_helpers import (
    DEFAULT_ZONE_MAP_PATH,
    DiscoveredDevice,
    PowerState,
    Zone,
    ZoneMap,
    ZoneMap,
    load_device_cache,
    load_power_state,
    load_zone_map,
    reverse_dns,
    scan_music,
    shell_cast,
    shell_mpv,
    shell_ytdlp,
    which_or_hint,
)


class TestZoneMap(unittest.TestCase):
    def test_round_trip(self):
        zm = ZoneMap(zones=[Zone("kitchen", 1.0, 2.0, 1.5),
                            Zone("living_room", 4.0, 5.0, 2.0)],
                     origin_label="dock")
        payload = zm.to_dict()
        self.assertEqual(payload["origin_label"], "dock")
        self.assertEqual(len(payload["zones"]), 2)
        zm2 = ZoneMap.from_dict(payload)
        self.assertEqual(zm2.get_zone("kitchen").x_m, 1.0)
        self.assertEqual(zm2.get_zone("LIVING_ROOM").y_m, 5.0)

    def test_zone_contains(self):
        z = Zone("kitchen", 0.0, 0.0, 1.0)
        self.assertTrue(z.contains(0.5, 0.5))
        self.assertFalse(z.contains(2.0, 2.0))

    def test_zone_at_returns_zone(self):
        zm = ZoneMap(zones=[Zone("kitchen", 0.0, 0.0, 1.0)])
        self.assertEqual(zm.zone_at(0.5, 0.5).name, "kitchen")
        self.assertIsNone(zm.zone_at(50.0, 50.0))

    def test_load_missing_returns_empty(self, *_):
        # Use a guaranteed-missing tmp path.
        with patch("tank_command_bridge.plugins._house_helpers.DEFAULT_ZONE_MAP_PATH",
                   Path("/nonexistent/zone_map.json")):
            zm = load_zone_map()
        self.assertEqual(zm.zones, [])


class TestScanMusic(unittest.TestCase):
    def test_substring_match_prefers_hit(self):
        # Create a fake music dir.
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "Pink Floyd - Time.mp3").write_bytes(b"x")
            (root / "John Cage - 4 minutes 33 seconds.mp3").write_bytes(b"x")
            hits = scan_music("Time", roots=[root], limit=5)
            self.assertTrue(hits, "scan_music returned no hits")
            self.assertEqual(hits[0].path,
                             str(root / "Pink Floyd - Time.mp3"))

    def test_no_match_returns_empty(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "Song A.mp3").write_bytes(b"x")
            hits = scan_music("zzz_no_match", roots=[root])
            self.assertEqual(hits, [])


class TestARPAndDeviceCache(unittest.TestCase):
    def test_load_device_cache_round_trip(self, *_):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            cache_path = Path(td) / "dev.json"
            cache_path.write_text(json.dumps([
                {"name": "kitchen echo", "address": "10.0.0.7",
                 "port": 8009, "service": "amazon", "source": "mdns"},
            ]))
            devs = load_device_cache(cache_path)
            self.assertEqual(len(devs), 1)
            self.assertEqual(devs[0].service, "amazon")
            self.assertEqual(devs[0].address, "10.0.0.7")


class TestLazyBinaries(unittest.TestCase):
    def test_which_or_hint_missing(self):
        # Patch shutil.which to return None; this exercises the
        # missing-binary path without needing real `mpv` absent.
        with patch("tank_command_bridge.plugins._house_helpers.shutil.which",
                   return_value=None):
            out = which_or_hint("definitely-not-installed")
        self.assertFalse(out["_ok"])
        self.assertIn("install", out["_hint"].lower())

    def test_shell_mpv_returns_hint_when_missing(self):
        with patch("tank_command_bridge.plugins._house_helpers.shutil.which",
                   return_value=None):
            out = shell_mpv("/tmp/test.mp3")
        self.assertFalse(out["_ok"])
        self.assertIn("mpv", out["_hint"])

    def test_shell_ytdlp_returns_url_when_present(self):
        fake_proc = unittest.mock.MagicMock()
        fake_proc.returncode = 0
        fake_proc.stdout = "https://example.com/stream?x=1\n"
        fake_proc.stderr = ""
        with patch(
            "tank_command_bridge.plugins._house_helpers.shutil.which",
            return_value="/usr/local/bin/yt-dlp",
        ), patch(
            "tank_command_bridge.plugins._house_helpers._default_run",
            return_value=fake_proc,
        ):
            out = shell_ytdlp("Pink Floyd Time")
        self.assertTrue(out["_ok"])
        self.assertEqual(out["url"], "https://example.com/stream?x=1")

    def test_shell_cast_falls_back_to_catt(self):
        # Cast targets ``catt`` when cast-now is absent.
        with patch(
            "tank_command_bridge.plugins._house_helpers.shutil.which",
            side_effect=lambda name: "/usr/bin/catt" if name == "catt" else None,
        ), patch(
            "tank_command_bridge.plugins._house_helpers.subprocess.Popen",
        ) as popen_mock:
            popen_mock.return_value.pid = 42424
            out = shell_cast("kitchen echo", "https://example.com/stream")
        self.assertTrue(out["_ok"])
        self.assertEqual(out["binary"], "/usr/bin/catt")

    def test_shell_cast_no_binary_returns_hint(self):
        with patch(
            "tank_command_bridge.plugins._house_helpers.shutil.which",
            return_value=None,
        ):
            out = shell_cast("kitchen echo", "https://example.com/stream")
        self.assertFalse(out["_ok"])
        self.assertIn("cast", out["_hint"].lower())


if __name__ == "__main__":
    unittest.main()
