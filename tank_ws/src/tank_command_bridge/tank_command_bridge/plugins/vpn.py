"""``voice.vpn.{connect,disconnect,status}`` plugin trio.

Wires The Tank Pi to the user's existing WireGuard VPS using the
``wg0-client-Shashi.conf``-style config file at
``/etc/wireguard/wg0.conf`` by default. The plugin stages the
validated config there with mode ``0600`` then runs
``sudo -n wg-quick up wg0``.

Security
~~~~~~~~
* The config parser (:func:`tank_command_bridge.plugins._vpn_helpers.parse_wg_conf`)
  strips ``PrivateKey`` / ``PresharedKey`` before any
  user-facing serialization via :meth:`WgConfig.to_safe_dict`.
* ``conf_path`` is path-traversal-checked against allow-listed roots
  via :func:`tank_command_bridge.plugins._vpn_helpers.validate_conf_path`.
* The subprocess runner uses explicit argv lists — no
  ``shell=True``, no string interpolation. ``sudo -n`` ensures the
  bridge fails fast on a missing NOPASSWD entry rather than hanging.

Idempotency
~~~~~~~~~~~
``voice.vpn.connect`` is idempotent — if ``wg show wg0`` reports
the interface is already up, the plugin records no extra ``up``
call and answers with a friendly TTS line. ``voice.vpn.disconnect``
similarly reports a clean TTS line if the tunnel was already down.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

from . import RobotPlugin
from ._vpn_helpers import (
    DEFAULT_CONF_PATH,
    ALLOWED_CONF_ROOTS,
    WgConfig,
    parse_wg_conf,
    resolve_runner,
    validate_conf_path,
)


# ---------------------------------------------------------------------------
# Shared scaffolding
# ---------------------------------------------------------------------------
class _VpnBasePlugin(RobotPlugin):
    """Shared flag for path-conf validation results."""

    RATE_CLASS = "write"
    TAGS = ["write", "voice", "network", "vpn"]

    def __init__(self) -> None:
        super().__init__()
        self._last_conf_error: str = ""

    def _load_conf(self, conf_path: str) -> Optional[str]:
        try:
            safe_path = validate_conf_path(conf_path)
        except ValueError as exc:
            self._last_conf_error = str(exc)
            return None
        if not os.path.exists(safe_path):
            self._last_conf_error = f"conf_not_found:{safe_path}"
            return None
        try:
            with open(safe_path, "r", encoding="utf-8") as f:
                return f.read()
        except OSError as exc:
            self._last_conf_error = f"conf_read_failed:{exc}"
            return None

    def _parse(self, text: str) -> Optional[WgConfig]:
        try:
            return parse_wg_conf(text)
        except Exception as exc:
            self._last_conf_error = f"conf_parse_failed:{exc}"
            return None


# ---------------------------------------------------------------------------
# voice.vpn.connect
# ---------------------------------------------------------------------------
class VpnConnectPlugin(_VpnBasePlugin):
    """Bring up the WireGuard tunnel to the VPS."""

    NAME = "voice.vpn.connect"
    DESCRIPTION = (
        "Bring up the WireGuard tunnel to the user's VPS using the "
        f"validated ``[Interface]`` / ``[Peer]`` config at "
        f"``{DEFAULT_CONF_PATH}`` by default. Stages the config with "
        "mode 0600 and runs ``sudo -n wg-quick up wg0``. Idempotent — "
        "if the tunnel is already up, returns success without "
        "restarting it."
    )
    PARAMETERS_SCHEMA = {
        "type": "object",
        "properties": {
            "conf_path": {
                "type": "string",
                "description": (
                    "WireGuard client config (absolute or relative to "
                    f"the workspace). Default: ``{DEFAULT_CONF_PATH}``. "
                    f"Must live under one of: {', '.join(ALLOWED_CONF_ROOTS)}."
                ),
                "default": DEFAULT_CONF_PATH,
            },
        },
    }
    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "_ok":               {"type": "boolean"},
            "already_connected": {"type": "boolean"},
            "endpoint":          {"type": "string"},
            "staged_conf":       {"type": "string"},
            "reason":            {"type": "string"},
            "tts_text":          {"type": "string"},
            "config":            {"type": "object"},
        },
    }
    RATE_CLASS = "write"
    TAGS = ["write", "voice", "network", "vpn"]

    def run(self, params: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        runner = resolve_runner(ctx)
        conf_path = (params.get("conf_path") or DEFAULT_CONF_PATH).strip() \
            or DEFAULT_CONF_PATH

        text = self._load_conf(conf_path)
        if text is None:
            return {
                "_ok": False,
                "already_connected": False,
                "endpoint": "",
                "staged_conf": "",
                "reason": self._last_conf_error or "conf_load_failed",
                "tts_text": "I can't find the WireGuard config file.",
                "config": {},
            }
        cfg = self._parse(text)
        if cfg is None:
            return {
                "_ok": False,
                "already_connected": False,
                "endpoint": "",
                "staged_conf": "",
                "reason": self._last_conf_error or "conf_parse_failed",
                "tts_text": "The WireGuard config is malformed.",
                "config": {},
            }

        # Build the redacted config once — used by every return path
        # below. Avoids repeated to_safe_dict() calls and gives a
        # single search-and-grep target for any audit-log work.
        safe_cfg = cfg.to_safe_dict()

        # ---------- idempotency: already up? ---------------------------------
        if runner.is_up():
            try:
                endpoint = runner.show().endpoint
            except (OSError, RuntimeError) as exc:
                # Tunnel was already up before our call AND the user's
                # intent (\"VPN connected\") is already satisfied. Mirror
                # the post-up branch's success-with-observability-gap
                # pattern: _ok=True so audit/dashboard don't trigger
                # spurious retries; reason captures the diagnostic.
                # Distinct label from the post-up branch so audit-log
                # consumers can filter the two structurally different
                # partial-success paths.
                return {
                    "_ok": True,
                    "already_connected": True,
                    "endpoint": "",
                    "staged_conf": "",
                    "reason": f"show_failed_when_already_up:{exc}",
                    "tts_text":
                        "The VPN is up, but I can't see the endpoint "
                        "right now. Try status in a moment.",
                    "config": safe_cfg,
                }
            return {
                "_ok": True,
                "already_connected": True,
                "endpoint": endpoint,
                "staged_conf": "",
                "reason": "already_up",
                "tts_text": "The VPN is already connected.",
                "config": safe_cfg,
            }

        # ---------- stage + bring up ----------------------------------------
        try:
            runner.write_runtime_conf(text)
        except Exception as exc:  # pragma: no cover — depends on env
            return {
                "_ok": False,
                "already_connected": False,
                "endpoint": "",
                "staged_conf": "",
                "reason": f"stage_failed:{exc}",
                "tts_text": "I can't stage the WireGuard config.",
                "config": safe_cfg,
            }

        up = runner.up()
        if not up.ok:
            return {
                "_ok": False,
                "already_connected": False,
                "endpoint": "",
                "staged_conf": "/etc/wireguard/wg0.conf",
                "reason": up.reason or "wg_quick_failed",
                "tts_text": (
                    "WireGuard refused to bring the tunnel up. "
                    "Check sudo and wg-quick."
                ),
                "config": safe_cfg,
            }

        try:
            endpoint = runner.show().endpoint
        except (OSError, RuntimeError) as exc:
            # Tunnel IS up — we just brought it up — but the post-up
            # state read failed. The connect itself succeeded, so we
            # report _ok=True with reason captured for the audit log.
            return {
                "_ok": True,
                "already_connected": False,
                "endpoint": "",
                "staged_conf": "/etc/wireguard/wg0.conf",
                "reason": f"show_failed_after_up:{exc}",
                "tts_text":
                    "Connected to your VPS — I just can't see the "
                    "endpoint right now. Try status in a moment.",
                "config": safe_cfg,
            }
        return {
            "_ok": True,
            "already_connected": False,
            "endpoint": endpoint,
            "staged_conf": "/etc/wireguard/wg0.conf",
            "reason": "",
            "tts_text": "Connected to your VPS.",
            "config": safe_cfg,
        }


# ---------------------------------------------------------------------------
# voice.vpn.disconnect
# ---------------------------------------------------------------------------
class VpnDisconnectPlugin(_VpnBasePlugin):
    """Tear down the WireGuard tunnel to the VPS."""

    NAME = "voice.vpn.disconnect"
    DESCRIPTION = (
        "Tear down the WireGuard tunnel to the VPS — "
        "``sudo -n wg-quick down wg0``. Reports whether the interface "
        "was up before the call (useful for the audit log)."
    )
    PARAMETERS_SCHEMA = {"type": "object", "properties": {}}
    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "_ok":      {"type": "boolean"},
            "was_up":   {"type": "boolean"},
            "endpoint": {"type": "string"},
            "reason":   {"type": "string"},
            "tts_text": {"type": "string"},
        },
    }
    RATE_CLASS = "write"
    TAGS = ["write", "voice", "network", "vpn"]

    def run(self, params: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        runner = resolve_runner(ctx)
        was_up = runner.is_up()
        endpoint = ""
        if was_up:
            # Narrow except: only I/O + runtime failures from the
            # runner are recoverable into a structured failure;
            # everything else still propagates so genuine bugs
            # surface during development.
            try:
                endpoint = runner.show().endpoint
            except (OSError, RuntimeError) as exc:
                return {
                    "_ok": False,
                    "was_up": True,
                    "endpoint": "",
                    "reason": f"show_failed:{exc}",
                    "tts_text":
                        "I can't read the VPN state right now, "
                        "but I'll leave it alone until you retry.",
                }

        if not was_up:
            return {
                "_ok": True,
                "was_up": False,
                "endpoint": "",
                "reason": "not_up",
                "tts_text": "The VPN was already disconnected.",
            }

        down = runner.down()
        if not down.ok:
            return {
                "_ok": False,
                "was_up": True,
                "endpoint": endpoint,
                "reason": down.reason or "wg_quick_failed",
                "tts_text": "I couldn't tear the tunnel down.",
            }
        return {
            "_ok": True,
            "was_up": True,
            "endpoint": endpoint,
            "reason": "",
            "tts_text": "Disconnected from the VPN.",
        }


# ---------------------------------------------------------------------------
# voice.vpn.status
# ---------------------------------------------------------------------------
class VpnStatusPlugin(_VpnBasePlugin):
    """Report the WireGuard tunnel state."""

    NAME = "voice.vpn.status"
    DESCRIPTION = (
        "Report the WireGuard tunnel state to the VPS — connected, "
        "peer ``endpoint``, last-handshake age in seconds, bytes "
        "received and sent. Safe to call repeatedly."
    )
    PARAMETERS_SCHEMA = {"type": "object", "properties": {}}
    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "_ok":               {"type": "boolean"},
            "connected":         {"type": "boolean"},
            "endpoint":          {"type": "string"},
            "latest_handshake_age_s": {"type": "number"},
            "bytes_received":    {"type": "integer"},
            "bytes_sent":        {"type": "integer"},
            "peer_count":        {"type": "integer"},
            "reason":            {"type": "string"},
            "tts_text":          {"type": "string"},
        },
    }
    RATE_CLASS = "read"
    TAGS = ["read", "voice", "network", "vpn"]

    def run(self, params: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        runner = resolve_runner(ctx)
        try:
            show = runner.show()
        except (OSError, RuntimeError) as exc:
            return {
                "_ok": False,
                "connected": False,
                "endpoint": "",
                "latest_handshake_age_s": -1.0,
                "bytes_received": 0,
                "bytes_sent": 0,
                "peer_count": 0,
                "reason": f"runner_error:{exc}",
                "tts_text": "I can't query the VPN right now.",
            }
        if not show.ok:
            reason = show.reason or "wg_show_failed"
            tts_text = (
                "WireGuard tools are not installed on this robot."
                if reason == "wg_cli_missing"
                else "I can't read the VPN state."
            )
            return {
                "_ok": False,
                "connected": False,
                "endpoint": "",
                "latest_handshake_age_s": -1.0,
                "bytes_received": 0,
                "bytes_sent": 0,
                "peer_count": 0,
                "reason": reason,
                "tts_text": tts_text,
            }

        d = show.to_dict()
        d["_ok"] = True
        if d["connected"]:
            age = d["latest_handshake_age_s"]
            age_text = (
                f"{int(age)} seconds ago"
                if age >= 0
                else "never"
            )
            rx_mb = d["bytes_received"] / (1024.0 * 1024.0)
            tx_mb = d["bytes_sent"] / (1024.0 * 1024.0)
            d["tts_text"] = (
                f"VPN is up. Last handshake {age_text}, "
                f"transferred {rx_mb:.1f} megabytes in, "
                f"{tx_mb:.1f} megabytes out."
            )
        else:
            d["tts_text"] = "VPN is down."
        return d


__all__ = [
    "VpnConnectPlugin",
    "VpnDisconnectPlugin",
    "VpnStatusPlugin",
]
