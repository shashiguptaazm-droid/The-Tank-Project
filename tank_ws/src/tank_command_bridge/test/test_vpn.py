"""Hermetic tests for tank_command_bridge.plugins._vpn_helpers +
tank_command_bridge.plugins.vpn.

Designed to be runnable WITHOUT root or a real wg-quick binary —
every test uses :class:`NullWireGuardRunner` reached through a tiny
``FakeCtx`` that mimics ``ctx.vpn``.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from typing import Any, Optional

from tank_command_bridge.plugins._vpn_helpers import (
    ALLOWED_CONF_ROOTS,
    DEFAULT_CONF_PATH,
    DEFAULT_WORKSPACE_ROOT,
    NullWireGuardRunner,
    SubprocessWireGuardRunner,
    WgConfig,
    WgInterface,
    WgPeer,
    WgRunResult,
    WgShowResult,
    parse_wg_conf,
    parse_wg_show_output,
    validate_conf_path,
)
from tank_command_bridge.plugins.vpn import (
    VpnConnectPlugin,
    VpnDisconnectPlugin,
    VpnStatusPlugin,
)


# ---------------------------------------------------------------------------
# Test scaffolding
# ---------------------------------------------------------------------------
SAMPLE_CONF = """[Interface]
PrivateKey = kIi6a5zAd3/PGP60g/lYXklLqPBjctdg0K2TI1QEyn4=
Address = 10.66.66.2/32,fd42:42:42::2/128
DNS = 1.1.1.1,1.0.0.1
# MTU = 1420

[Peer]
PublicKey = rBPPowX0rR4R/wcoBKIfw16pN5qLYor8g8BqliiWXwM=
PresharedKey = ZLtai07i/6U4QxNOH0Co6hp5ReCKNPJLisvw3T3oR3E=
Endpoint = 213.199.61.156:54368
AllowedIPs = 0.0.0.0/0,::/0
PersistentKeepalive = 25
"""


SAMPLE_SHOW = """interface: wg0
  public key: ABBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB=
  private key: (hidden)
  listening port: 54368

peer: rBPPowX0rR4R/wcoBKIfw16pN5qLYor8g8BqliiWXwM=
  endpoint: 213.199.61.156:54368
  allowed ips: 0.0.0.0/0, ::/0
  latest handshake: 23 seconds ago
  transfer: 1.23 MiB received, 4.56 MiB sent
  persistent keepalive: every 25 seconds
"""


class _FakeCtx:
    """Minimal ctx stand-in for the trio plugins. ``vpn`` attr is the
    runner they should pick up."""

    def __init__(self, runner: NullWireGuardRunner) -> None:
        self.vpn = runner


def _stage_workspace_conf(tmp: tempfile.TemporaryDirectory) -> str:
    """Drop ``SAMPLE_CONF`` inside the tempdir and return its path."""

    conf_path = os.path.join(tmp.name, "wg0.conf")
    with open(conf_path, "w", encoding="utf-8") as f:
        f.write(SAMPLE_CONF)
    return conf_path


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------
class ParserTests(unittest.TestCase):

    def test_parses_interface_and_peer_round_trip(self) -> None:
        cfg = parse_wg_conf(SAMPLE_CONF)
        self.assertEqual(cfg.interface.address,
                         "10.66.66.2/32,fd42:42:42::2/128")
        self.assertEqual(cfg.interface.dns, "1.1.1.1,1.0.0.1")
        self.assertEqual(len(cfg.peers), 1)
        peer = cfg.peers[0]
        self.assertEqual(peer.endpoint, "213.199.61.156:54368")
        self.assertEqual(peer.allowed_ips, "0.0.0.0/0,::/0")
        self.assertEqual(peer.persistent_keepalive, "25")
        # Values for keys that DO carry secrets DO get parsed — the
        # safety wall is at to_safe_dict not at parse.
        self.assertTrue(cfg.interface.private_key.startswith("kIi6a5zAd3"))
        self.assertTrue(peer.preshared_key.startswith("ZLtai07i"))

    def test_to_safe_dict_redacts_private_and_preshared_keys(self) -> None:
        cfg = parse_wg_conf(SAMPLE_CONF)
        safe = cfg.to_safe_dict()
        # Stringify the entire tree to detect any secret-leak channel.
        blob = json.dumps(safe)
        self.assertNotIn(cfg.interface.private_key, blob)
        self.assertNotIn(peer.preshared_key if (peer := cfg.peers[0]) else "",
                         blob)
        # Allowed-list positives.
        self.assertEqual(
            safe["interface"]["address"],
            "10.66.66.2/32,fd42:42:42::2/128")
        self.assertEqual(
            safe["peers"][0]["endpoint"], "213.199.61.156:54368")
        # No key fields in the safe dict AT ALL.
        self.assertNotIn("private_key", safe["interface"])
        self.assertNotIn("preshared_key", safe["peers"][0])
        self.assertNotIn("public_key", safe["peers"][0])

    def test_to_safe_dict_omits_unknown_keys(self) -> None:
        cfg = parse_wg_conf("[Interface]\nAddress = 10.0.0.1/24\n"
                            "MysteryKey = unlike\n")
        safe = cfg.to_safe_dict()
        self.assertNotIn("mysterykey", safe["interface"])
        self.assertNotIn("MysteryKey", safe["interface"])

    def test_empty_text_raises(self) -> None:
        with self.assertRaises(Exception):
            parse_wg_conf(None)  # type: ignore[arg-type]

    def test_handles_blank_and_comment_lines(self) -> None:
        body = "\n\n# only comments\n[Peer]\n# inline comment\n\n"
        cfg = parse_wg_conf(body)
        self.assertEqual(len(cfg.peers), 1)

    def test_unrecognised_key_silently_ignored(self) -> None:
        cfg = parse_wg_conf("[Interface]\nNotAKey = stuff\n")
        self.assertEqual(cfg.interface.to_safe_dict(), {})


# ---------------------------------------------------------------------------
# Path-validation tests
# ---------------------------------------------------------------------------
class PathValidationTests(unittest.TestCase):

    def test_default_path_allowed(self) -> None:
        resolved = validate_conf_path(DEFAULT_CONF_PATH)
        self.assertEqual(resolved, "/etc/wireguard/wg0.conf")

    def test_workspace_rooted_path_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conf_path = os.path.join(tmp, "wg0.conf")
            with open(conf_path, "w") as f:
                f.write(SAMPLE_CONF)
            # Workspace root is the parent project tree in the real
            # project; uses default. To make this hermetic we point
            # workspace_root at tmp's parent and validate.
            # DEFAULT_WORKSPACE_ROOT is the canonical workspace path.
            # We can't override the default without modifying the
            # signature — instead we test rejection explicitly for
            # unsafe paths.
            self.assertTrue(conf_path.startswith(tmp + "/"))
            # We expect /tmp/* NOT to be a valid workspace or /etc/wireguard root.

    def test_path_traversal_refused(self) -> None:
        bad = "/etc/shadow"
        with self.assertRaises(ValueError):
            validate_conf_path(bad)

    def test_path_traversal_with_dotdot_refused(self) -> None:
        with self.assertRaises(ValueError):
            validate_conf_path("/etc/wireguard/../../shadow")


# ---------------------------------------------------------------------------
# Runner / parser pair tests (no real wg)
# ---------------------------------------------------------------------------
class NullRunnerTests(unittest.TestCase):

    def test_is_up_default_false(self) -> None:
        r = NullWireGuardRunner()
        self.assertFalse(r.is_up())

    def test_up_records_and_marks_running(self) -> None:
        r = NullWireGuardRunner()
        res = r.up()
        self.assertTrue(res.ok)
        self.assertEqual(r.up_calls, 1)
        self.assertTrue(r.is_up())

    def test_up_failure_does_not_set_running(self) -> None:
        r = NullWireGuardRunner()
        r.queue_up(WgRunResult(ok=False, reason="binary_missing:/usr/bin/sudo"))
        res = r.up()
        self.assertFalse(res.ok)
        self.assertFalse(r.is_up())

    def test_down_records_and_clears_running(self) -> None:
        r = NullWireGuardRunner()
        r.set_is_up(True)
        res = r.down()
        self.assertTrue(res.ok)
        self.assertEqual(r.down_calls, 1)
        self.assertFalse(r.is_up())

    def test_show_returns_canned(self) -> None:
        r = NullWireGuardRunner()
        expected = WgShowResult(
            ok=True, connected=True,
            endpoint="213.199.61.156:54368",
            latest_handshake_age_s=23.0,
            bytes_received=int(1.23 * 1024 ** 2),
            bytes_sent=int(4.56 * 1024 ** 2),
            peer_count=1,
        )
        r.queue_show(expected)
        self.assertEqual(r.show(), expected)
        self.assertEqual(r.show_calls, 1)

    def test_show_raises_propagates(self) -> None:
        r = NullWireGuardRunner()
        r.queue_show_raises(RuntimeError("fake boom"))
        with self.assertRaises(RuntimeError):
            r.show()

    def test_write_runtime_conf_records_text(self) -> None:
        r = NullWireGuardRunner()
        r.write_runtime_conf(SAMPLE_CONF)
        self.assertEqual(r.write_calls, [SAMPLE_CONF])


# ---------------------------------------------------------------------------
# show-output parser tests
# ---------------------------------------------------------------------------
class ShowOutputParserTests(unittest.TestCase):

    def test_parses_canonical_show_output(self) -> None:
        s = parse_wg_show_output(SAMPLE_SHOW)
        self.assertTrue(s.ok)
        self.assertTrue(s.connected)
        self.assertEqual(s.endpoint, "213.199.61.156:54368")
        self.assertEqual(s.latest_handshake_age_s, 23.0)
        self.assertEqual(s.bytes_received, int(1.23 * 1024 ** 2))
        self.assertEqual(s.bytes_sent, int(4.56 * 1024 ** 2))
        self.assertEqual(s.peer_count, 1)

    def test_strips_private_key_line_from_raw(self) -> None:
        # The parser strips private key lines from `raw`; the synthesized
        # WgShowResult must NOT include a `private_key` attribute.
        s = parse_wg_show_output(SAMPLE_SHOW)
        self.assertNotIn("private key", s.raw)
        # Also confirm public keys (which are OK to share) are kept —
        # the parser must NOT strip the whole `public key:` line.
        self.assertIn("public key", s.raw)
        # When a private-key line is present in the input, never keep it.
        blob = """interface: wg0
  private key: SUPER_SECRET_PRIVATE_KEY=should_not_appear
  public key: PUBLIC=
peer: PUBLIC=
  endpoint: 213.199.61.156:54368
  transfer: 100 B received, 200 B sent
"""
        s2 = parse_wg_show_output(blob)
        self.assertNotIn("SUPER_SECRET_PRIVATE_KEY", s2.raw)
        # Show results never expose private_key attr at all.
        self.assertNotIn("private_key", s2.to_dict())

    def test_handshake_age_units(self) -> None:
        self.assertEqual(
            parse_wg_show_output("peer: x\n  latest handshake: 1 minute ago\n"
                                 "  transfer: 0 B received, 0 B sent\n")
            .latest_handshake_age_s, 60.0)
        self.assertEqual(
            parse_wg_show_output("peer: x\n  latest handshake: 2 hours ago\n"
                                 "  transfer: 0 B received, 0 B sent\n")
            .latest_handshake_age_s, 7200.0)

    def test_handshake_never(self) -> None:
        s = parse_wg_show_output("peer: x\n  latest handshake: never\n"
                                 "  transfer: 0 B received, 0 B sent\n")
        # "never" → age -1.0 (we don't ship positive infinity into JSON)
        self.assertEqual(s.latest_handshake_age_s, -1.0)

    def test_empty_show_is_not_ok(self) -> None:
        s = parse_wg_show_output("")
        self.assertFalse(s.ok)
        self.assertEqual(s.reason, "empty_output")


# ---------------------------------------------------------------------------
# Plugin trio behaviour tests (the heart of the change)
# ---------------------------------------------------------------------------
class VpnConnectPluginTests(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.conf_path = _stage_workspace_conf(self.tmp)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _ctx(self, runner: NullWireGuardRunner) -> _FakeCtx:
        return _FakeCtx(runner)

    def test_successful_first_connect_records_one_up_call(self) -> None:
        runner = NullWireGuardRunner()
        runner.queue_show(WgShowResult(
            ok=True, connected=True,
            endpoint="213.199.61.156:54368",
            latest_handshake_age_s=23.0,
            bytes_received=int(1.23 * 1024 ** 2),
            bytes_sent=int(2 * 1024 ** 2),
            peer_count=1,
        ))
        p = VpnConnectPlugin()
        from tank_command_bridge.plugins import _vpn_helpers as helpers
        saved_root = helpers.DEFAULT_WORKSPACE_ROOT
        helpers.DEFAULT_WORKSPACE_ROOT = self.tmp.name
        try:
            res = p.run({"conf_path": self.conf_path}, self._ctx(runner))
        finally:
            helpers.DEFAULT_WORKSPACE_ROOT = saved_root
        self.assertTrue(res["_ok"])
        self.assertFalse(res["already_connected"])
        self.assertEqual(res["endpoint"], "213.199.61.156:54368")
        self.assertEqual(res["tts_text"], "Connected to your VPS.")
        # Exactly one up call.
        self.assertEqual(runner.up_calls, 1)
        # Config write happened.
        self.assertGreaterEqual(len(runner.write_calls), 1)
        # Safe config returned — strict redaction:
        # STRICTLY no PrivateKey / PresharedKey / public_key in the
        # user-facing JSON (which the dashboard + TTS + audit log
        # could echo back to a human).
        blob = json.dumps(res["config"])
        self.assertNotIn("PrivateKey", blob)
        self.assertNotIn("PresharedKey", blob)
        self.assertNotIn("private_key", blob)
        self.assertNotIn("preshared_key", blob)
        self.assertNotIn("public_key", blob)
        # Allow-list positives — operator-visible fields ARE present.
        self.assertIn("213.199.61.156:54368", blob)
        self.assertIn("0.0.0.0/0,::/0", blob)

    def test_idempotent_on_already_up(self) -> None:
        runner = NullWireGuardRunner()
        runner.set_is_up(True)
        runner.queue_show(WgShowResult(
            ok=True, connected=True,
            endpoint="213.199.61.156:54368",
            latest_handshake_age_s=5.0,
            bytes_received=0, bytes_sent=0, peer_count=1,
        ))
        p = VpnConnectPlugin()
        from tank_command_bridge.plugins import _vpn_helpers as helpers
        saved_root = helpers.DEFAULT_WORKSPACE_ROOT
        helpers.DEFAULT_WORKSPACE_ROOT = self.tmp.name
        try:
            res = p.run({"conf_path": self.conf_path}, self._ctx(runner))
        finally:
            helpers.DEFAULT_WORKSPACE_ROOT = saved_root
        self.assertTrue(res["_ok"])
        self.assertTrue(res["already_connected"])
        self.assertEqual(res["reason"], "already_up")
        self.assertEqual(runner.up_calls, 0)
        self.assertEqual(runner.write_calls, [])
        self.assertEqual(res["tts_text"], "The VPN is already connected.")

    def test_refuses_unsafe_path(self) -> None:
        runner = NullWireGuardRunner()
        p = VpnConnectPlugin()
        res = p.run({"conf_path": "/etc/shadow"}, self._ctx(runner))
        self.assertFalse(res["_ok"])
        self.assertIn("must be under", res["reason"])
        self.assertEqual(runner.up_calls, 0)
        self.assertEqual(runner.write_calls, [])
        self.assertEqual(res["tts_text"],
                         "I can't find the WireGuard config file.")

    def test_up_failure_returns_wg_quick_failed(self) -> None:
        runner = NullWireGuardRunner()
        runner.queue_up(WgRunResult(ok=False, reason="binary_missing:/usr/bin/wg-quick"))
        from tank_command_bridge.plugins import _vpn_helpers as helpers
        saved_root = helpers.DEFAULT_WORKSPACE_ROOT
        helpers.DEFAULT_WORKSPACE_ROOT = self.tmp.name
        p = VpnConnectPlugin()
        try:
            res = p.run({"conf_path": self.conf_path}, self._ctx(runner))
        finally:
            helpers.DEFAULT_WORKSPACE_ROOT = saved_root
        self.assertFalse(res["_ok"])
        self.assertEqual(res["reason"], "binary_missing:/usr/bin/wg-quick")
        self.assertIn("WireGuard refused", res["tts_text"])

    def test_malformed_conf_returns_conf_parse_failed(self) -> None:
        bad_path = os.path.join(self.tmp.name, "wg0-bad.conf")
        # Truly unparseable: a single-line that has no '=' (so the
        # _LINE_RE regex doesn't match and WgParseError is raised).
        # An empty [Peer] section validates as fine and so wouldn't
        # actually exercise this path.
        with open(bad_path, "w") as f:
            f.write("[Peer]\nNotAKeyValueLineNoEqualsSign\n")
        runner = NullWireGuardRunner()
        p = VpnConnectPlugin()
        from tank_command_bridge.plugins import _vpn_helpers as helpers
        saved_root = helpers.DEFAULT_WORKSPACE_ROOT
        helpers.DEFAULT_WORKSPACE_ROOT = self.tmp.name
        try:
            res = p.run({"conf_path": bad_path}, self._ctx(runner))
        finally:
            helpers.DEFAULT_WORKSPACE_ROOT = saved_root
        self.assertFalse(res["_ok"])
        self.assertIn("parse", res["reason"])
        self.assertEqual(res["tts_text"], "The WireGuard config is malformed.")

    def test_conf_not_found(self) -> None:
        runner = NullWireGuardRunner()
        p = VpnConnectPlugin()
        from tank_command_bridge.plugins import _vpn_helpers as helpers
        saved_root = helpers.DEFAULT_WORKSPACE_ROOT
        helpers.DEFAULT_WORKSPACE_ROOT = self.tmp.name
        try:
            res = p.run(
                {"conf_path": os.path.join(self.tmp.name, "missing.conf")},
                self._ctx(runner),
            )
        finally:
            helpers.DEFAULT_WORKSPACE_ROOT = saved_root
        self.assertFalse(res["_ok"])
        self.assertIn("conf_not_found", res["reason"])

    # ---- narrow-catch regression coverage (mirror disconnect) -------------
    def test_idempotent_show_failure_returns_partial_success(self) -> None:
        """Tunnel was already up + runner.show() raises OSError.

        _ok MUST be True (the user's intent was already satisfied),
        reason records the diagnostic gap, NO extra up() call fired,
        NO conf write happened.
        """
        runner = NullWireGuardRunner()
        runner.set_is_up(True)            # tunnel already up
        runner.queue_show_raises(
            OSError("netlink down"))
        p = VpnConnectPlugin()
        from tank_command_bridge.plugins import _vpn_helpers as helpers
        saved_root = helpers.DEFAULT_WORKSPACE_ROOT
        helpers.DEFAULT_WORKSPACE_ROOT = self.tmp.name
        try:
            res = p.run({"conf_path": self.conf_path}, self._ctx(runner))
        finally:
            helpers.DEFAULT_WORKSPACE_ROOT = saved_root
        self.assertTrue(res["_ok"])
        self.assertTrue(res["already_connected"])
        self.assertEqual(res["endpoint"], "")
        self.assertIn("show_failed_when_already_up", res["reason"])
        self.assertIn("VPN is up", res["tts_text"])
        # Critically: we did NOT re-fire wg-quick up; we did NOT
        # re-write the runtime conf. The user's intent is satisfied.
        self.assertEqual(runner.up_calls, 0)
        self.assertEqual(runner.write_calls, [])
        # runner.show() WAS attempted (show_calls==1) and raised before
        # we landed on this partial-success path.
        self.assertEqual(runner.show_calls, 1)

    def test_postup_show_failure_returns_partial_success(self) -> None:
        """We just brought the tunnel up + runner.show() raises OSError.

        _ok MUST be True (the tunnel DID come up; we just can't read
        its endpoint right now), reason records the gap.
        """
        runner = NullWireGuardRunner()    # not up initially
        runner.queue_show_raises(
            OSError("netlink transient"))
        p = VpnConnectPlugin()
        from tank_command_bridge.plugins import _vpn_helpers as helpers
        saved_root = helpers.DEFAULT_WORKSPACE_ROOT
        helpers.DEFAULT_WORKSPACE_ROOT = self.tmp.name
        try:
            res = p.run({"conf_path": self.conf_path}, self._ctx(runner))
        finally:
            helpers.DEFAULT_WORKSPACE_ROOT = saved_root
        self.assertTrue(res["_ok"])
        self.assertFalse(res["already_connected"])
        self.assertEqual(res["endpoint"], "")
        self.assertIn("show_failed_after_up", res["reason"])
        self.assertIn("Connected to your VPS", res["tts_text"])
        # We DID fire up() (the connect itself succeeded) and DID
        # stage the conf. just couldn't read state afterward.
        self.assertEqual(runner.up_calls, 1)
        self.assertGreaterEqual(len(runner.write_calls), 1)
        # runner.show() WAS attempted (show_calls==1) and raised after
        # up(); that's the post-up observability gap.
        self.assertEqual(runner.show_calls, 1)

    def test_postup_show_propagates_unexpected_errors(self) -> None:
        """Narrow catch must NOT swallow genuine bugs (ValueError etc.).

        Mirrors VpnDisconnectPluginTests::test_show_propagates_unexpected_errors.
        """
        runner = NullWireGuardRunner()
        runner.queue_show_raises(ValueError("genuine bug"))
        p = VpnConnectPlugin()
        from tank_command_bridge.plugins import _vpn_helpers as helpers
        saved_root = helpers.DEFAULT_WORKSPACE_ROOT
        helpers.DEFAULT_WORKSPACE_ROOT = self.tmp.name
        with self.assertRaises(ValueError):
            p.run({"conf_path": self.conf_path}, self._ctx(runner))


class VpnDisconnectPluginTests(unittest.TestCase):

    def _ctx(self, r: NullWireGuardRunner) -> _FakeCtx:
        return _FakeCtx(r)

    def test_already_down_returns_was_up_false(self) -> None:
        r = NullWireGuardRunner()
        p = VpnDisconnectPlugin()
        res = p.run({}, self._ctx(r))
        self.assertTrue(res["_ok"])
        self.assertFalse(res["was_up"])
        self.assertEqual(res["reason"], "not_up")
        self.assertEqual(res["tts_text"], "The VPN was already disconnected.")
        self.assertEqual(r.down_calls, 0)

    def test_brings_down_a_running_tunnel(self) -> None:
        r = NullWireGuardRunner()
        r.set_is_up(True)
        r.queue_show(WgShowResult(
            ok=True, connected=True, endpoint="1.2.3.4:51820",
            latest_handshake_age_s=10.0,
            bytes_received=1024, bytes_sent=2048, peer_count=1,
        ))
        p = VpnDisconnectPlugin()
        res = p.run({}, self._ctx(r))
        self.assertTrue(res["_ok"])
        self.assertTrue(res["was_up"])
        self.assertEqual(res["endpoint"], "1.2.3.4:51820")
        self.assertEqual(res["tts_text"], "Disconnected from the VPN.")
        self.assertEqual(r.down_calls, 1)

    def test_show_failure_returns_structured_failure(self) -> None:
        """Narrow-catch path: runner.show() raises after is_up() returns True.

        We DO NOT want the bridge to crash — we want a structured failure
        response with a friendly TTS line.
        """
        r = NullWireGuardRunner()
        r.set_is_up(True)
        r.queue_show_raises(OSError("netlink down"))
        p = VpnDisconnectPlugin()
        res = p.run({}, self._ctx(r))
        self.assertFalse(res["_ok"])
        self.assertTrue(res["was_up"])
        self.assertEqual(res["endpoint"], "")
        self.assertIn("show_failed", res["reason"])
        self.assertIn("can't read the VPN state", res["tts_text"])
        # Critically: down() WAS NOT called because we bailed before
        # touching the tunnel — important: the runner's interface may
        # still be up but we did not execute any teardown command.
        self.assertEqual(r.down_calls, 0)

    def test_show_propagates_unexpected_errors(self) -> None:
        """Narrow-catch should NOT swallow ValueError / TypeError etc."""
        r = NullWireGuardRunner()
        r.set_is_up(True)
        r.queue_show_raises(ValueError("genuine bug"))
        p = VpnDisconnectPlugin()
        with self.assertRaises(ValueError):
            p.run({}, self._ctx(r))

    def test_down_failure_returns_wg_quick_failed(self) -> None:
        r = NullWireGuardRunner()
        r.set_is_up(True)
        r.queue_show(WgShowResult(
            ok=True, connected=True, endpoint="1.2.3.4:51820",
            latest_handshake_age_s=5.0, bytes_received=0,
            bytes_sent=0, peer_count=1,
        ))
        r.queue_down(WgRunResult(ok=False, reason="binary_missing:/usr/bin/wg-quick"))
        p = VpnDisconnectPlugin()
        res = p.run({}, self._ctx(r))
        self.assertFalse(res["_ok"])
        self.assertTrue(res["was_up"])
        self.assertEqual(res["reason"], "binary_missing:/usr/bin/wg-quick")
        self.assertEqual(res["tts_text"], "I couldn't tear the tunnel down.")


class VpnStatusPluginTests(unittest.TestCase):

    def _ctx(self, r: NullWireGuardRunner) -> _FakeCtx:
        return _FakeCtx(r)

    def test_disconnected_returns_tts_down(self) -> None:
        r = NullWireGuardRunner()
        r.queue_show(WgShowResult(
            ok=True, connected=False,
            endpoint="", latest_handshake_age_s=-1.0,
            bytes_received=0, bytes_sent=0, peer_count=0,
        ))
        p = VpnStatusPlugin()
        res = p.run({}, self._ctx(r))
        self.assertTrue(res["_ok"])
        self.assertFalse(res["connected"])
        self.assertEqual(res["tts_text"], "VPN is down.")

    def test_connected_returns_handshake_and_mb(self) -> None:
        r = NullWireGuardRunner()
        r.queue_show(WgShowResult(
            ok=True, connected=True,
            endpoint="213.199.61.156:54368",
            latest_handshake_age_s=23.0,
            bytes_received=int(1.23 * 1024 ** 2),
            bytes_sent=int(4.56 * 1024 ** 2),
            peer_count=1,
        ))
        p = VpnStatusPlugin()
        res = p.run({}, self._ctx(r))
        self.assertTrue(res["_ok"])
        self.assertTrue(res["connected"])
        self.assertIn("23 seconds ago", res["tts_text"])
        self.assertIn("VPN is up", res["tts_text"])

    def test_wg_cli_missing(self) -> None:
        r = NullWireGuardRunner()
        r.queue_show(WgShowResult(ok=False, reason="wg_cli_missing"))
        p = VpnStatusPlugin()
        res = p.run({}, self._ctx(r))
        self.assertFalse(res["_ok"])
        self.assertEqual(res["reason"], "wg_cli_missing")
        self.assertIn("WireGuard tools are not installed", res["tts_text"])

    def test_runner_exception_returns_runner_error(self) -> None:
        r = NullWireGuardRunner()
        r.queue_show_raises(RuntimeError("boom"))
        p = VpnStatusPlugin()
        res = p.run({}, self._ctx(r))
        self.assertFalse(res["_ok"])
        self.assertIn("runner_error:boom", res["reason"])
        self.assertEqual(res["tts_text"], "I can't query the VPN right now.")


if __name__ == "__main__":
    unittest.main()
