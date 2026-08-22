"""Tests for ``scrub_magnet`` and friends. Pure-function tests, no I/O."""
from __future__ import annotations

import unittest
import urllib.parse

from tank_command_bridge.plugins._torrent_common import (
    magnet_is_safe,
    normalise_int,
    normalise_quality,
    normalise_size,
    scrub_magnet,
)


class TestScrubMagnet(unittest.TestCase):
    def test_strips_trackers_keeps_xt_and_dn(self):
        m = ("magnet:?xt=urn:btih:DEADBEEFCAFEBABE1234567890ABCDEF12345678"
             "&dn=Inception+2010+1080p"
             "&tr=udp%3A%2F%2Ftracker.example.com%3A80"
             "&tr=udp%3A%2F%2Ftracker2.example.com%3A80")
        s = scrub_magnet(m)
        # Strong assertion: parse the URL-encoded query string, NOT a
        # substring search (a substring search passes for the wrong reason).
        parsed = urllib.parse.urlparse(s)
        qs = urllib.parse.parse_qs(parsed.query)
        self.assertIn("xt", qs)
        self.assertIn("dn", qs)
        self.assertNotIn("tr", qs,
                         "scrub_magnet leaked a tracker; this is a privacy bug.")
        self.assertEqual(
            qs["xt"][0],
            "urn:btih:DEADBEEFCAFEBABE1234567890ABCDEF12345678",
        )
        self.assertIn("Inception", qs["dn"][0])

    def test_keeps_size_xl(self):
        """``xl`` (length-of-file extension) is also kept."""
        m = ("magnet:?xt=urn:btih:DEADBEEF"
             "&dn=Some+Movie"
             "&xl=1234567890"
             "&tr=udp%3A%2F%2Ftracker.example")
        s = scrub_magnet(m)
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(s).query)
        self.assertIn("xl", qs)
        self.assertIn("dn", qs)
        self.assertEqual(qs["xl"][0], "1234567890")

    def test_passthrough_non_magnet(self):
        self.assertEqual(scrub_magnet("https://example.com/foo.torrent"),
                         "https://example.com/foo.torrent")
        self.assertEqual(scrub_magnet(""), "")


class TestMagnetIsSafe(unittest.TestCase):
    def test_magnet_accepted(self):
        ok, why = magnet_is_safe(
            "magnet:?xt=urn:btih:DEADBEEF&dn=test&tr=udp%3A%2F%2Ffakes")
        self.assertTrue(ok)
        self.assertEqual(why, "magnet")

    def test_https_torrent_accepted(self):
        ok, why = magnet_is_safe("https://example.com/path/file.torrent")
        self.assertTrue(ok)
        self.assertEqual(why, "https_torrent")

    def test_http_torrent_blocked(self):
        ok, why = magnet_is_safe("http://example.com/path/file.torrent")
        self.assertFalse(ok)
        self.assertEqual(why, "plain_http_torrent_rejected_for_mitm",
                         "the rejection reason should be a unique grepable code")

    def test_empty_rejected(self):
        ok, why = magnet_is_safe("")
        self.assertFalse(ok)
        self.assertEqual(why, "empty_uri")


class TestNormalisers(unittest.TestCase):
    def test_size_parsing(self):
        self.assertEqual(normalise_size("1.4 GB"), int(1.4 * 1e9))
        self.assertEqual(normalise_size("812 MiB"), int(812 * 1e6))
        self.assertEqual(normalise_size("totally broken"), 0)

    def test_quality_parsing(self):
        self.assertEqual(normalise_quality("Inception 2010 1080p BluRay"), 1080)
        self.assertEqual(normalise_quality("Anything 4k Remux"),         2160)
        self.assertEqual(normalise_quality("720p WEB-DL"),                720)
        self.assertEqual(normalise_quality("something lower"),             0)

    def test_int_parsing(self):
        self.assertEqual(normalise_int("1,234"), 1234)
        self.assertEqual(normalise_int("1.2k"),  1200)
        self.assertEqual(normalise_int("3.4m"),  3_400_000)
        self.assertEqual(normalise_int("oops"),  0)


if __name__ == "__main__":
    unittest.main()
