"""Hermetic tests for the remaining house plugins.

Each test patches the lazy shell-out helpers so no real ``mpv`` /
``cast-now`` / PythonOS/catt / etc subprocess spawns.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tank_command_bridge.plugins.find_devices import FindDevicesPlugin
from tank_command_bridge.plugins.move_to import MoveToPlugin
from tank_command_bridge.plugins.play_alexa import PlayAlexaPlugin
from tank_command_bridge.plugins.play_tv import PlayTvPlugin
from tank_command_bridge.plugins.power import PowerPlugin
from tank_command_bridge.plugins.whereami import WhereAmIPlugin


class TestPlayTv(unittest.TestCase):
    def test_missing_args(self):
        out = PlayTvPlugin().run({"tv_name": ""})
        self.assertFalse(out["_ok"])
        self.assertIn("need both", out["tts_text"])

    def test_cast_success(self):
        with patch(
            "tank_command_bridge.plugins.play_tv.shell_cast",
            return_value={"_ok": True, "pid": 777,
                            "binary": "/usr/bin/cast-now"},
        ):
            out = PlayTvPlugin().run({
                "tv_name": "living room TV",
                "url": "https://stream/abc",
            })
        self.assertTrue(out["_ok"])
        self.assertIn("Casting to living room TV", out["tts_text"])

    def test_cast_failure(self):
        with patch(
            "tank_command_bridge.plugins.play_tv.shell_cast",
            return_value={"_ok": False, "_hint": "no catt"},
        ):
            out = PlayTvPlugin().run({
                "tv_name": "living room TV",
                "url": "https://stream/abc",
            })
        self.assertFalse(out["_ok"])
        self.assertIn("couldn't cast", out["tts_text"])


class TestPlayAlexa(unittest.TestCase):
    def test_missing_text(self):
        out = PlayAlexaPlugin().run({"text": ""})
        self.assertFalse(out["_ok"])
        self.assertEqual(out["target_device"], None)

    def test_no_device_returns_helpful(self):
        # No devices cached.
        with patch(
            "tank_command_bridge.plugins.play_alexa.load_device_cache",
            return_value=[],
        ):
            out = PlayAlexaPlugin().run({"text": "set timer 5 minutes"})
        self.assertFalse(out["_ok"])
        self.assertEqual(out["target_device"], None)
        self.assertIn("No Alexa", out["tts_text"])

    def test_with_device_returns_preview(self):
        fake = [
            type("D", (), {"name": "echo kitchen", "address": "10.0.0.7",
                              "port": 8009, "service": "amazon",
                              "source": "mdns"})(),
        ]
        with patch(
            "tank_command_bridge.plugins.play_alexa.load_device_cache",
            return_value=fake,
        ):
            # Default — no LWA token, so should NOT be sent.
            out = PlayAlexaPlugin().run({"text": "set timer 5 minutes"})
        self.assertTrue(out["_ok"])
        self.assertFalse(out["sent"])
        self.assertEqual(out["target_device"]["name"], "echo kitchen")
        self.assertIn("say", out["preview"].lower())

    def test_force_send_with_token_marks_sent(self):
        fake = [
            type("D", (), {"name": "echo kitchen", "address": "10.0.0.7",
                              "port": 8009, "service": "amazon",
                              "source": "mdns"})(),
        ]
        with patch(
            "tank_command_bridge.plugins.play_alexa.load_device_cache",
            return_value=fake,
        ), patch.dict(
            "os.environ", {"TANK_ALEXA_LWA_TOKEN": "fake-token"}, clear=False,
        ):
            out = PlayAlexaPlugin().run({
                "text": "set timer 5 minutes",
                "force_send": True,
            })
        self.assertTrue(out["sent"])
        self.assertIn("Sent", out["tts_text"])


class TestFindDevices(unittest.TestCase):
    def test_returns_arp_entries(self):
        fake = [
            type("D", (), {"name": "raspi-tank", "address": "10.0.0.5",
                              "port": 0, "service": "lan_neighbour",
                              "source": "arp"})(),
        ]
        with patch(
            "tank_command_bridge.plugins.find_devices.read_arp_table",
            return_value=fake,
        ), patch(
            "tank_command_bridge.plugins.find_devices.load_device_cache",
            return_value=[],
        ):
            out = FindDevicesPlugin().run({"include_arp": True,
                                             "include_mdns_cache": False})
        self.assertTrue(out["_ok"])
        self.assertEqual(len(out["devices"]), 1)
        self.assertEqual(out["devices"][0]["address"], "10.0.0.5")

    def test_overlay_mdns_metadata(self):
        arp_d = type("D", (), {"name": "", "address": "10.0.0.7",
                                "port": 0, "service": "lan_neighbour",
                                "source": "arp"})()
        mdns_d = type("D", (), {"name": "kitchen echo", "address": "10.0.0.7",
                                  "port": 8009, "service": "amazon",
                                  "source": "mdns"})()
        with patch(
            "tank_command_bridge.plugins.find_devices.read_arp_table",
            return_value=[arp_d],
        ), patch(
            "tank_command_bridge.plugins.find_devices.load_device_cache",
            return_value=[mdns_d],
        ):
            out = FindDevicesPlugin().run({"include_arp": True,
                                             "include_mdns_cache": True})
        self.assertEqual(out["devices"][0]["service"], "amazon")
        self.assertEqual(out["devices"][0]["name"], "kitchen echo")

    def test_service_filter(self):
        arp_d = type("D", (), {"name": "a", "address": "10.0.0.5",
                                "port": 0, "service": "lan_neighbour",
                                "source": "arp"})()
        mdns_d = type("D", (), {"name": "b", "address": "10.0.0.7",
                                  "port": 8009, "service": "amazon",
                                  "source": "mdns"})()
        # Patch what the plugin ACTUALLY calls.
        with patch(
            "tank_command_bridge.plugins.find_devices.read_arp_table",
            return_value=[arp_d],
        ), patch(
            "tank_command_bridge.plugins.find_devices.load_device_cache",
            return_value=[mdns_d],
        ):
            out = FindDevicesPlugin().run({
                "service_filter": ["amazon"],
            })
        names = [d["address"] for d in out["devices"]]
        self.assertEqual(names, ["10.0.0.7"])


class TestPower(unittest.TestCase):
    def test_unknown_mode(self):
        out = PowerPlugin().run({"mode": "teleport"})
        self.assertFalse(out["_ok"])
        self.assertEqual(out["new_mode"], "awake")

    def test_estop_latched_refuses_sleep(self):
        out = PowerPlugin().run({"mode": "sleep", "estop_latched": True})
        self.assertFalse(out["_ok"])
        self.assertIn("e-stop", out["tts_text"])

    def test_low_battery_refuses_reboot(self):
        out = PowerPlugin().run({"mode": "reboot",
                                    "estop_latched": False,
                                    "battery_pct": 12.0})
        self.assertFalse(out["_ok"])
        self.assertIn("thirty percent", out["tts_text"])

    def test_happy_path_persists_state(self):
        with tempfile.TemporaryDirectory() as td:
            fake_path = Path(td) / "power.json"
            with patch(
                "tank_command_bridge.plugins.power.DEFAULT_POWER_STATE_PATH",
                fake_path,
            ):
                out = PowerPlugin().run({"mode": "wake", "reason": "test"})
        self.assertTrue(out["_ok"])
        self.assertEqual(out["new_mode"], "wake")
        self.assertTrue(fake_path.exists())
        loaded = json.loads(fake_path.read_text())
        self.assertEqual(loaded["mode"], "wake")


class TestMoveTo(unittest.TestCase):
    def test_estop_refuses(self):
        out = MoveToPlugin().run({"mode": "relative",
                                    "direction": "forward",
                                    "distance_m": 1.0,
                                    "estop_latched": True})
        self.assertFalse(out["_ok"])
        self.assertIn("e-stop", out["tts_text"])

    def test_relative_forward_returns_intent(self):
        out = MoveToPlugin().run({"mode": "relative",
                                    "direction": "forward",
                                    "distance_m": 0.5})
        self.assertTrue(out["_ok"])
        self.assertGreater(out["intent"]["vx"], 0.0)
        self.assertAlmostEqual(out["intent"]["vz"] if "vz" in out["intent"]
                                else out["intent"]["wz"], 0.0)
        self.assertEqual(out["intent"]["duration_s"], 2.0)
        self.assertIn("forward", out["tts_text"])

    def test_relative_unknown_direction(self):
        out = MoveToPlugin().run({"mode": "relative",
                                    "direction": "diagonal",
                                    "distance_m": 0.5})
        self.assertFalse(out["_ok"])

    def test_zone_mode_requires_zone(self):
        out = MoveToPlugin().run({"mode": "zone", "zone": "",
                                    "estop_latched": False})
        self.assertFalse(out["_ok"])
        self.assertIn("zone", out["tts_text"].lower())

    def test_zone_mode_unknown_name_with_xml(self):
        # Write a small zone map and load it.
        with tempfile.TemporaryDirectory() as td:
            map_path = Path(td) / "zone_map.json"
            map_path.write_text(json.dumps({
                "zones":    [{"name": "kitchen", "x_m": 0, "y_m": 0,
                                  "radius_m": 2.0}],
                "waypoints": [],
                "origin_label": "dock",
                "current_pose": {"x": 0.0, "y": 0.0},
            }))
            with patch(
                "tank_command_bridge.plugins.move_to.DEFAULT_ZONE_MAP_PATH",
                map_path,
            ):
                out = MoveToPlugin().run({"mode": "zone", "zone": "kitchen"})
                self.assertTrue(out["_ok"])
                self.assertEqual(out["intent"]["target_zone"], "kitchen",
                                  "should resolve to the kitchen zone")
                out_missing = MoveToPlugin().run(
                    {"mode": "zone", "zone": "shed"})
                self.assertFalse(out_missing["_ok"])


class TestWhereAmI(unittest.TestCase):
    def test_unknown_zone_by_default(self):
        with tempfile.TemporaryDirectory() as td:
            map_path = Path(td) / "zone_map.json"
            map_path.write_text(json.dumps({
                "zones": [{"name": "kitchen", "x_m": 0,
                            "y_m": 0, "radius_m": 1.0}],
                "waypoints": [],
                "current_pose": {"x": 100.0, "y": 100.0},
                "origin_label": "dock",
            }))
            with patch(
                "tank_command_bridge.plugins.whereami.DEFAULT_ZONE_MAP_PATH",
                map_path,
            ):
                out = WhereAmIPlugin().run({})
        self.assertEqual(out["zone"], "unknown zone")
        self.assertIn("not sure", out["tts_text"])

    def test_resolved_in_kitchen(self):
        with tempfile.TemporaryDirectory() as td:
            map_path = Path(td) / "zone_map.json"
            map_path.write_text(json.dumps({
                "zones": [{"name": "kitchen", "x_m": 0,
                            "y_m": 0, "radius_m": 1.0}],
                "waypoints": [],
                "current_pose": {"x": 0.5, "y": 0.5},
                "origin_label": "dock",
            }))
            with patch(
                "tank_command_bridge.plugins.whereami.DEFAULT_ZONE_MAP_PATH",
                map_path,
            ):
                out = WhereAmIPlugin().run({})
        self.assertEqual(out["zone"], "kitchen")
        self.assertIn("kitchen", out["tts_text"])

    def test_override_only(self):
        with tempfile.TemporaryDirectory() as td:
            map_path = Path(td) / "zone_map.json"
            map_path.write_text(json.dumps({
                "zones": [{"name": "kitchen", "x_m": 0,
                            "y_m": 0, "radius_m": 1.0}],
                "waypoints": [],
                "current_pose": {"x": 0.5, "y": 0.5},
                "origin_label": "dock",
            }))
            with patch(
                "tank_command_bridge.plugins.whereami.DEFAULT_ZONE_MAP_PATH",
                map_path,
            ):
                out = WhereAmIPlugin().run({
                    "x_m": 100.0, "y_m": 100.0,
                    "use_override_only": True,
                })
        self.assertEqual(out["zone"], "unknown zone")


if __name__ == "__main__":
    unittest.main()
