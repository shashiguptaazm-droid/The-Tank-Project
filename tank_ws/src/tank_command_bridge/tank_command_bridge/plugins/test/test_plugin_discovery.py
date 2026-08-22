"""Tests for the auto-discovery machinery in :mod:`plugins.__init__`.

Verifies:
* every entry-pointed module loads and instantiates;
* DISPATCH + RATE_CLASS are mutated in place;
* COMMANDS gets a matching entry that the LLM tool-introspect path sees.
"""
from __future__ import annotations

import unittest

from tank_command_bridge.plugins import (
    PLUGIN_PATHS, PluginLoadError, _discover_plugins,
    _make_example_params,
    _register_voice_plugins,
    _register_voice_plugins_manifest,
)


class TestDiscovery(unittest.TestCase):
    def test_each_entry_point_loads(self):
        plugins = _discover_plugins()
        self.assertEqual(len(plugins), len(PLUGIN_PATHS))
        names = sorted(p.NAME for p in plugins)
        self.assertIn("voice.torrent_search",   names)
        self.assertIn("voice.aria2_add",        names)
        self.assertIn("voice.aria2_progress",   names)

    def test_register_voice_plugins_updates_dispatch(self):
        dispatch: dict = {}
        rate: dict = {}
        registered = _register_voice_plugins(dispatch, rate)
        self.assertGreaterEqual(len(registered), 3)
        for name in ("voice.torrent_search", "voice.aria2_add",
                     "voice.aria2_progress"):
            self.assertIn(name, dispatch)
            self.assertIn(name, rate)
            self.assertTrue(callable(dispatch[name]))

    def test_register_voice_plugins_manifest(self):
        commands: dict = {}
        registered = _register_voice_plugins_manifest(commands)
        self.assertEqual(len(set(registered)), len(registered),
                         "no duplicate plugin registration")
        for name in ("voice.torrent_search", "voice.aria2_add",
                     "voice.aria2_progress"):
            self.assertIn(name, commands)
            self.assertIn("parameters", commands[name])
            self.assertIn("response", commands[name])
            self.assertIn("example", commands[name])

    def test_bad_path_raises(self):
        from tank_command_bridge.plugins import _discover_plugins_with
        with self.assertRaises(PluginLoadError):
            _discover_plugins_with([("tank_command_bridge.plugins.does_not_exist",
                                      "Nope")])

    def test_make_example_params(self):
        schema = {
            "type": "object",
            "properties": {
                "query":   {"type": "string"},
                "limit":   {"type": "integer"},
                "flag":    {"type": "boolean"},
            },
        }
        out = _make_example_params(schema)
        self.assertEqual(out, {"query": "", "limit": 0, "flag": False})


if __name__ == "__main__":
    unittest.main()
