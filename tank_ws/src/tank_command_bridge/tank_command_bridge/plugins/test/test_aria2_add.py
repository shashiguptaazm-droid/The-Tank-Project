"""Tests for ``voice.aria2_add`` covering validation + happy path + that
filename/dir overrides are forwarded to aria2 on the wire, not just
echoed back in the response."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from tank_command_bridge.plugins.aria2_add import Aria2AddPlugin


VALID_MAGNET = ("magnet:?xt=urn:btih:DEADBEEFCAFEBABE1234567890ABCDEF12345678"
                "&dn=Inception+2010+1080p")


class TestAria2AddValidation(unittest.TestCase):
    def setUp(self) -> None:
        self.plugin = Aria2AddPlugin()

    def test_missing_magnet(self):
        out = self.plugin.run({"magnet": ""})
        self.assertFalse(out["_ok"])
        self.assertEqual(out["status"], "rejected")
        self.assertEqual(out["options_sent"], {})

    def test_http_torrent_blocked(self):
        out = self.plugin.run({"magnet": "http://example.com/file.torrent"})
        self.assertFalse(out["_ok"])
        self.assertIn("validation_failed", out["validation_note"])
        self.assertEqual(out["options_sent"], {})

    def test_https_torrent_accepted(self):
        fake_gid = "deadbeefcafebabe"
        with patch("tank_command_bridge.plugins.aria2_add.add_uri",
                   return_value=fake_gid) as m:
            out = self.plugin.run(
                {"magnet": "https://example.com/path/file.torrent"})
        self.assertTrue(out["_ok"])
        self.assertEqual(out["gid"], fake_gid)
        self.assertEqual(out["status"], "added")
        # add_uri must have been called with NO options (caller didn't ask).
        _args, kwargs = m.call_args
        self.assertTrue(kwargs.get("options") in (None, {}))

    def test_valid_magnet_happy_path(self):
        with patch("tank_command_bridge.plugins.aria2_add.add_uri",
                   return_value="deadbeef") as m:
            out = self.plugin.run({"magnet": VALID_MAGNET})
        self.assertTrue(out["_ok"])
        self.assertEqual(out["gid"], "deadbeef")
        self.assertEqual(out["validation_note"], "magnet")
        # No filename / dir requested, so nothing should be passed.
        _args, kwargs = m.call_args
        self.assertTrue(kwargs.get("options") in (None, {}))

    def test_options_passed_to_aria2(self):
        """The whole point of this test: filename + dir must reach aria2.

        We mock ``add_uri`` and inspect its kwargs so we KNOW the dict
        was forwarded over the wire — the response snapshot alone would
        also pass even if the bug were present.
        """
        with patch("tank_command_bridge.plugins.aria2_add.add_uri",
                   return_value="abc") as mock_add:
            out = Aria2AddPlugin().run({"magnet": VALID_MAGNET,
                                        "filename": "My.Cool.Movie.mp4",
                                        "dir": "/media/movies"})
        self.assertTrue(out["_ok"])
        # 1. Response snapshot is correct.
        self.assertEqual(out["options_sent"].get("out"), "My.Cool.Movie.mp4")
        self.assertEqual(out["options_sent"].get("dir"), "/media/movies")
        # 2. add_uri was called with the SAME options dict on the wire.
        mock_add.assert_called_once()
        kwargs = mock_add.call_args.kwargs
        opts = kwargs.get("options") or {}
        self.assertEqual(opts.get("out"), "My.Cool.Movie.mp4")
        self.assertEqual(opts.get("dir"), "/media/movies")

    def test_no_options_when_only_magnet_given(self):
        """When the caller only supplies a magnet, add_uri gets options=None."""
        with patch("tank_command_bridge.plugins.aria2_add.add_uri",
                   return_value="abc") as mock_add:
            Aria2AddPlugin().run({"magnet": VALID_MAGNET})
        mock_add.assert_called_once()
        opts = mock_add.call_args.kwargs.get("options")
        self.assertTrue(opts in (None, {}),
                        f"expected None or empty dict, got {opts!r}")


if __name__ == "__main__":
    unittest.main()
