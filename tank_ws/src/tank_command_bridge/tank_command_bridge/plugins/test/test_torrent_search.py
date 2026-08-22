"""Offline tests for ``voice.torrent_search`` and per-site parsers.

Uses canned HTML fixtures so unit tests are hermetic (no network).
"""
from __future__ import annotations

import unittest
from pathlib import Path

from tank_command_bridge.plugins._sources import leethax1337, limetorrents, rarbg
from tank_command_bridge.plugins._torrent_common import rank_hits
from tank_command_bridge.plugins.torrent_search import TorrentSearchPlugin


FIX_DIR = Path(__file__).resolve().parent / "fixtures"


class TestParsers(unittest.TestCase):
    def test_1337x_parser(self):
        html = (FIX_DIR / "1337x_inception.html").read_text()
        hits = leethax1337.parse_1337x(html, "Inception")
        self.assertEqual(len(hits), 2,
                         f"expected 2 rows (size-less row dropped); got {len(hits)}")
        # Best should be the 1080p one with 412 seeders.
        h0 = max(hits, key=lambda h: h.score())
        self.assertIn("BluRay", h0.title)
        self.assertGreaterEqual(h0.seeders, 400)
        self.assertTrue(h0.magnet.startswith("magnet:?"))

    def test_limetorrents_parser(self):
        html = (FIX_DIR / "limetorrents_matrix.html").read_text()
        hits = limetorrents.parse_limetorrents(html, "Matrix")
        self.assertEqual(len(hits), 2)
        any_2160 = any(h.quality == 2160 for h in hits)
        self.assertTrue(any_2160, "expected at least one 2160p hit")

    def test_rarbg_parser(self):
        html = (FIX_DIR / "rarbg_inception.html").read_text()
        hits = rarbg.parse_rarbg(html, "Inception")
        self.assertEqual(len(hits), 2)
        any_2160 = any(h.quality == 2160 for h in hits)
        self.assertTrue(any_2160)


class TestRanking(unittest.TestCase):
    def test_rank_puts_high_seeders_first(self):
        from tank_command_bridge.plugins._torrent_common import TorrentHit
        hits = [
            TorrentHit(title="low",  size_bytes=int(1e9),  seeders=10,
                       leechers=1, source="rarbg", magnet="magnet:?xt=urn:btih:DEAD1"),
            TorrentHit(title="high", size_bytes=int(1e9),  seeders=999,
                       leechers=0, source="1337x", magnet="magnet:?xt=urn:btih:DEAD2"),
        ]
        ranked = rank_hits(hits, take=2)
        self.assertEqual(ranked[0]["title"], "high")


class TestPluginRun(unittest.TestCase):
    """End-to-end run() that injects canned HTML through the search fns."""

    def test_run_with_injected_html(self):
        canned = (FIX_DIR / "1337x_inception.html").read_text()

        from tank_command_bridge.plugins import _sources, torrent_search
        def _fake_1337x(q, timeout_s=6.0):
            return _sources.leethax1337.parse_1337x(canned, q)
        def _fake_lime(q, timeout_s=6.0):
            return _sources.limetorrents.parse_limetorrents(canned, q)
        def _fake_rarbg(q, timeout_s=6.0):
            return _sources.rarbg.parse_rarbg(canned, q)

        original = dict(torrent_search.inject_search_fns)
        torrent_search.inject_search_fns["1337x"]        = _fake_1337x
        torrent_search.inject_search_fns["limetorrents"]  = _fake_lime
        torrent_search.inject_search_fns["rarbg"]         = _fake_rarbg
        try:
            out = TorrentSearchPlugin().run({"query": "Inception", "limit": 5,
                                              "min_seeders": 0})
            self.assertTrue(out.get("_ok"))
            self.assertGreater(out["total"], 0)
            self.assertTrue(out["hits"])
            # Top hit must carry access_uri (the magnet).
            self.assertIn("access_uri", out["hits"][0])
            # access_uri should be a magnet: URI.
            self.assertTrue(out["hits"][0]["access_uri"].startswith("magnet:?"))
        finally:
            torrent_search.inject_search_fns.clear()
            torrent_search.inject_search_fns.update(original)


if __name__ == "__main__":
    unittest.main()
