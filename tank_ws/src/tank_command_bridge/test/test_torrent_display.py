"""Hermetic tests for tank_command_bridge.plugins._torrent_display +
torrent_display.py plugins (TorrentPickPlugin, TorrentCancelPlugin,
ShowTorrentResultsPlugin).
"""
from __future__ import annotations

import unittest
from typing import Any, Dict, List, Optional

from tank_command_bridge.plugins._aria2_common import Aria2Error
from tank_command_bridge.plugins._torrent_display import (
    ACTIVE_DOWNLOADS,
    RECENT_RESULTS,
    ActiveDownloadsStore,
    RecentResultsStore,
    TorrentResult,
)


class _FakeCtx:
    """Plugable ctx used by the torrent_display plugins."""
    def __init__(self, aria2: Any = None,
                 emitted: Optional[List[Dict[str, Any]]] = None) -> None:
        self.aria2 = aria2
        self._emitted = emitted if emitted is not None else []

    def bus_event(self, name: str, payload: Dict[str, Any]) -> None:
        self._emitted.append({"name": name, "payload": payload})


class _FakeAria2:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.added: List[str] = []
        self.removed: List[str] = []

    def add_uri(self, magnet: str, options: Any = None) -> str:
        if self.fail:
            raise Aria2Error("aria2 unreachable")
        gid = f"gid-{len(self.added)+1}"
        self.added.append(gid)
        return gid

    def remove(self, gid: str) -> str:
        self.removed.append(gid)
        return "ok"


class RecentResultsStoreTests(unittest.TestCase):

    def setUp(self) -> None:
        RECENT_RESULTS.clear()

    def test_push_dedupes_by_infohash(self) -> None:
        RECENT_RESULTS.push([
            {"title": "Lo-Fi Beats", "source": "1337x",
             "size_bytes": 1000, "seeders": 5,
             "magnet": "magnet:?xt=urn:btih:HASH1"},
            {"title": "Lo-Fi Beats dup", "source": "rarbg",
             "size_bytes": 1000, "seeders": 4,
             "magnet": "magnet:?xt=urn:btih:HASH1"},
        ])
        self.assertEqual(len(RECENT_RESULTS.list()), 1)
        self.assertEqual(RECENT_RESULTS.list()[0]["source"], "1337x")

    def test_last_query_mem(self) -> None:
        RECENT_RESULTS.push([{"title": "x", "source": "y",
                              "size_bytes": 1, "seeders": 1,
                              "magnet": "magnet:?xt=urn:btih:H"}],
                             query="lo-fi")
        self.assertEqual(RECENT_RESULTS.last_query(), "lo-fi")

    def test_at_returns_none_for_out_of_range(self) -> None:
        RECENT_RESULTS.push([{"title": "x", "source": "y",
                              "size_bytes": 1, "seeders": 1,
                              "magnet": "magnet:?xt=urn:btih:H"}])
        self.assertIsNotNone(RECENT_RESULTS.at(0))
        self.assertIsNone(RECENT_RESULTS.at(99))

    def test_age_s_positive(self) -> None:
        import time
        RECENT_RESULTS.push([{"title": "x", "source": "y",
                              "size_bytes": 1, "seeders": 1,
                              "magnet": "magnet:?xt=urn:btih:H"}])
        time.sleep(0.05)
        self.assertGreater(RECENT_RESULTS.age_s(), 0.0)


class ActiveDownloadsStoreTests(unittest.TestCase):

    def setUp(self) -> None:
        ACTIVE_DOWNLOADS._gids.clear()

    def test_mark_and_done(self) -> None:
        ACTIVE_DOWNLOADS.mark_active("g1", {"title": "x"})
        self.assertTrue(ACTIVE_DOWNLOADS.contains("g1"))
        ACTIVE_DOWNLOADS.mark_done("g1")
        self.assertFalse(ACTIVE_DOWNLOADS.contains("g1"))

    def test_list(self) -> None:
        ACTIVE_DOWNLOADS.mark_active("g1")
        ACTIVE_DOWNLOADS.mark_active("g2")
        self.assertEqual(len(ACTIVE_DOWNLOADS.list()), 2)


class TorrentPickPluginTests(unittest.TestCase):
    """Voice pick + auto-confirm path with the Null-safe aria2 fallback."""

    def setUp(self) -> None:
        RECENT_RESULTS.clear()
        ACTIVE_DOWNLOADS._gids.clear()
        RECENT_RESULTS.push([
            {"title": "Cyanide & Happiness Ep 1", "source": "1337x",
             "size_bytes": 100_000_000, "seeders": 88,
             "magnet": "magnet:?xt=urn:btih:AAAA&dn=Cyanide%20Ep1&tr=tracker"},
        ], query="cyanide")
        from tank_command_bridge.plugins.torrent_display import (
            TorrentPickPlugin,
        )
        self._plugin_cls = TorrentPickPlugin

    def test_pick_first_word(self) -> None:
        out = self._plugin_cls().run(
            {"ordinal_word": "first"}, ctx=None)
        self.assertTrue(out["_ok"])
        self.assertTrue(out["queued_for_aria2"])
        self.assertEqual(out["ordinal"], 1)
        self.assertIn("gid", out["aria2"])
        self.assertEqual(len(ACTIVE_DOWNLOADS.list()), 1)

    def test_pick_ordinal_int(self) -> None:
        out = self._plugin_cls().run(
            {"ordinal": 1}, ctx=None)
        self.assertTrue(out["_ok"])

    def test_pick_no_results(self) -> None:
        RECENT_RESULTS.clear()
        out = self._plugin_cls().run({"ordinal_word": "first"}, ctx=None)
        self.assertFalse(out["_ok"])
        self.assertIn("no recent", out["tts_text"].lower())

    def test_pick_with_real_aria2_failure_does_not_crash(self) -> None:
        ctx = _FakeCtx(aria2=_FakeAria2(fail=True))
        out = self._plugin_cls().run({"ordinal_word": "first"}, ctx=ctx)
        self.assertTrue(out["_ok"])
        # Auto-confirm attempted, queued=False on error, no gid added
        self.assertFalse(out["queued_for_aria2"])
        self.assertIn("error", out["aria2"])

    def test_pick_last_word(self) -> None:
        out = self._plugin_cls().run({"ordinal_word": "last"}, ctx=None)
        self.assertTrue(out["_ok"])
        self.assertEqual(out["ordinal"], 1)


class TorrentCancelPluginTests(unittest.TestCase):

    def setUp(self) -> None:
        RECENT_RESULTS.clear()
        ACTIVE_DOWNLOADS._gids.clear()
        ACTIVE_DOWNLOADS.mark_active(
            "g42", {"title": "thing",
                    "magnet": "magnet:?xt=urn:btih:DEADBEEF&dn=thing"})
        from tank_command_bridge.plugins.torrent_display import (
            TorrentCancelPlugin,
        )
        self._plugin_cls = TorrentCancelPlugin

    def test_cancel_by_gid(self) -> None:
        out = self._plugin_cls().run({"gid": "g42"}, ctx=None)
        self.assertTrue(out["_ok"])
        self.assertTrue(out["cancelled"])
        self.assertFalse(ACTIVE_DOWNLOADS.contains("g42"))

    def test_cancel_by_magnet_resolves_gid(self) -> None:
        out = self._plugin_cls().run({
            "magnet": "magnet:?xt=urn:btih:DEADBEEF&dn=thing"}, ctx=None)
        self.assertTrue(out["_ok"])
        self.assertEqual(out["matched_gid"], "g42")
        self.assertFalse(ACTIVE_DOWNLOADS.contains("g42"))

    def test_cancel_unknown(self) -> None:
        ACTIVE_DOWNLOADS._gids.clear()
        out = self._plugin_cls().run({"gid": "nope"}, ctx=None)
        self.assertFalse(out["_ok"])


class ShowTorrentResultsPluginTests(unittest.TestCase):

    def setUp(self) -> None:
        RECENT_RESULTS.clear()
        from tank_command_bridge.plugins.torrent_display import (
            ShowTorrentResultsPlugin,
        )
        self._plugin_cls = ShowTorrentResultsPlugin

    def test_show_empty(self) -> None:
        out = self._plugin_cls().run({}, ctx=None)
        self.assertTrue(out["_ok"])
        self.assertEqual(out["shown"], 0)
        self.assertIn("no recent", out["tts_text"].lower())

    def test_show_with_results(self) -> None:
        RECENT_RESULTS.push([
            {"title": "Lo-Fi Beats", "source": "1337x",
             "size_bytes": 1000, "seeders": 5,
             "magnet": "magnet:?xt=urn:btih:H"}], query="lo-fi")
        out = self._plugin_cls().run({}, ctx=None)
        self.assertEqual(out["shown"], 1)
        self.assertIn("Showing 1", out["tts_text"])

    def test_show_emits_bus_event(self) -> None:
        RECENT_RESULTS.push([
            {"title": "Lo-Fi Beats", "source": "1337x",
             "size_bytes": 1000, "seeders": 5,
             "magnet": "magnet:?xt=urn:btih:H"}], query="lo-fi")
        events: List[Dict[str, Any]] = []
        ctx = _FakeCtx(emitted=events)
        self._plugin_cls().run({}, ctx=ctx)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["name"], "torrent_results_shown")


if __name__ == "__main__":
    unittest.main()
