"""WireGuard VPN runner + config parser for the
``voice.vpn.{connect,disconnect,status}`` plugin trio.

The runner abstraction mirrors :class:`ChassisMotionProvider` so all
three plugins stay hermetic — tests inject :class:`NullWireGuardRunner`
and never touch the host's network stack.

The :class:`WgConfig` dataclass parses the INI-shaped WireGuard config
and exposes a strict :meth:`to_safe_dict` that strips ``PrivateKey``
and ``PresharedKey`` BEFORE any audit log, dashboard, TTS, or LLM
tool-call wire format gets them — the keys never enter the output
dict, full stop.

Security surface
~~~~~~~~~~~~~~~~
* ``conf_path`` is path-traversal-checked against an allowlist of
  workspace-rooted or ``/etc/wireguard``-rooted paths.
* Real-host runner uses ``subprocess.run`` with explicit argv lists
  (no shell, no interpolation) and ``sudo -n`` so it never blocks
  waiting on a password.
* Strict allowlist of keys returned from :meth:`to_safe_dict` —
  admins must explicitly opt-in to expose any new field.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_WG_INTERFACE = "wg0"
DEFAULT_CONF_PATH = "/etc/wireguard/wg0.conf"
DEFAULT_WORKSPACE_ROOT = "/root/the tank project/tank_ws"

# Both directories where ``conf_path`` is permitted — anything else is
# refused so the plugin never reads ``/etc/shadow`` or whatever the
# operator typed in via the LLM function-call surface.
ALLOWED_CONF_ROOTS: Tuple[str, ...] = (DEFAULT_WORKSPACE_ROOT, "/etc/wireguard")

# Keys whose values can be safely echoed back to the operator. Anything
# not in this allowlist is dropped from :meth:`to_safe_dict` as if it
# didn't exist.
_SAFE_INTERFACE_KEYS = frozenset({"Address", "DNS", "MTU"})
_SAFE_PEER_KEYS = frozenset({"Endpoint", "AllowedIPs", "PersistentKeepalive"})

_LINE_RE = re.compile(
    r'^\s*([A-Za-z][A-Za-z0-9_]*)\s*=\s*"?([^"#]*)"?\s*(?:#.*)?$'
)
_SECTION_RE = re.compile(r"^\s*\[([A-Za-z][A-Za-z0-9_]*)\]\s*$")


class WgParseError(ValueError):
    """Raised when a WireGuard config string is malformed."""


# ---------------------------------------------------------------------------
# Parser → dataclasses → safe-dict
# ---------------------------------------------------------------------------
@dataclass
class WgInterface:
    """The ``[Interface]`` section of a wg-quick .conf."""

    private_key: str = ""        # STRIPPED before .to_safe_dict
    address: str = ""
    dns: str = ""
    mtu: str = ""

    def to_safe_dict(self) -> Dict[str, str]:
        out: Dict[str, str] = {}
        if self.address and "Address" in _SAFE_INTERFACE_KEYS:
            out["address"] = self.address
        if self.dns and "DNS" in _SAFE_INTERFACE_KEYS:
            out["dns"] = self.dns
        if self.mtu and "MTU" in _SAFE_INTERFACE_KEYS:
            out["mtu"] = self.mtu
        return out


@dataclass
class WgPeer:
    """A single ``[Peer]`` section."""

    public_key: str = ""
    preshared_key: str = ""      # STRIPPED before .to_safe_dict
    endpoint: str = ""
    allowed_ips: str = ""
    persistent_keepalive: str = ""

    def to_safe_dict(self) -> Dict[str, str]:
        out: Dict[str, str] = {}
        if self.endpoint and "Endpoint" in _SAFE_PEER_KEYS:
            out["endpoint"] = self.endpoint
        if self.allowed_ips and "AllowedIPs" in _SAFE_PEER_KEYS:
            out["allowed_ips"] = self.allowed_ips
        if self.persistent_keepalive \
                and "PersistentKeepalive" in _SAFE_PEER_KEYS:
            out["persistent_keepalive"] = self.persistent_keepalive
        return out


@dataclass
class WgConfig:
    """Parsed WireGuard .conf file. Use :meth:`to_safe_dict` for any
    user-facing serialization."""

    interface: WgInterface = field(default_factory=WgInterface)
    peers: List[WgPeer] = field(default_factory=list)

    def to_safe_dict(self) -> Dict[str, Any]:
        return {
            "interface": self.interface.to_safe_dict(),
            "peers": [p.to_safe_dict() for p in self.peers],
        }


def parse_wg_conf(text: str) -> WgConfig:
    """Parse a WireGuard .conf text blob.

    Lines beginning with ``#`` are comments. Sections are
    ``[Interface]`` / ``[Peer]``. Returns a :class:`WgConfig` whose
    internal fields carry the full raw values (keys included).
    Operators MUST funnel any user-facing serialization through
    :meth:`WgConfig.to_safe_dict` to avoid leaking secrets.
    """
    if text is None:
        raise WgParseError("wg config text is None")
    out = WgConfig()
    cur_iface: Optional[WgInterface] = None
    cur_peer: Optional[WgPeer] = None
    section: Optional[str] = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        ms = _SECTION_RE.match(line)
        if ms:
            lower = ms.group(1).lower()
            if lower == "interface":
                cur_iface = WgInterface()
                cur_peer = None
                out.interface = cur_iface
                section = "interface"
            elif lower == "peer":
                cur_peer = WgPeer()
                cur_iface = None
                out.peers.append(cur_peer)
                section = "peer"
            else:
                cur_iface = None
                cur_peer = None
                section = lower  # unknown — drop its keys silently
            continue
        ml = _LINE_RE.match(line)
        if not ml:
            raise WgParseError(f"unparseable line: {raw!r}")
        key, val = ml.group(1), ml.group(2).strip()
        if section == "interface" and cur_iface is not None:
            if key == "PrivateKey":
                cur_iface.private_key = val
            elif key == "Address":
                cur_iface.address = val
            elif key == "DNS":
                cur_iface.dns = val
            elif key == "MTU":
                cur_iface.mtu = val
        elif section == "peer" and cur_peer is not None:
            if key == "PublicKey":
                cur_peer.public_key = val
            elif key == "PresharedKey":
                cur_peer.preshared_key = val
            elif key == "Endpoint":
                cur_peer.endpoint = val
            elif key == "AllowedIPs":
                cur_peer.allowed_ips = val
            elif key == "PersistentKeepalive":
                cur_peer.persistent_keepalive = val
    return out


def validate_conf_path(
    conf_path: str,
    workspace_root: Optional[str] = None,
) -> str:
    """Resolve ``conf_path`` and confirm it lives under an allowed root.

    Raises :class:`ValueError` on rejection. Returns the resolved
    absolute path on success. ``workspace_root`` is looked up at
    *call-time* from the module global (not at definition-time) so
    tests can monkey-patch :data:`DEFAULT_WORKSPACE_ROOT`.
    """
    if workspace_root is None:
        # Read the module-LEVEL default at call-time so tests can
        # monkey-patch DEFAULT_WORKSPACE_ROOT in-process.
        workspace_root = sys.modules[__name__].DEFAULT_WORKSPACE_ROOT
    abs_path = os.path.abspath(conf_path)
    allowed = (
        os.path.abspath(workspace_root),
        os.path.abspath("/etc/wireguard"),
    )
    for root in allowed:
        if abs_path == root or abs_path.startswith(root + os.sep):
            return abs_path
    raise ValueError(
        f"conf_path {conf_path!r} resolves to {abs_path!r}; "
        f"must be under one of: {', '.join(allowed)}"
    )


# ---------------------------------------------------------------------------
# Runner abstraction
# ---------------------------------------------------------------------------
@dataclass
class WgRunResult:
    ok: bool
    reason: str = ""
    stdout: str = ""
    stderr: str = ""


@dataclass
class WgShowResult:
    """Parsed ``wg show wg0`` output.

    ``ok=False`` + ``reason`` covers the missing-CLI / synth-failed case.
    """

    ok: bool = True
    connected: bool = False
    endpoint: str = ""
    latest_handshake_age_s: float = -1.0
    bytes_received: int = 0
    bytes_sent: int = 0
    peer_count: int = 0
    reason: str = ""
    raw: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "connected": self.connected,
            "endpoint": self.endpoint,
            "latest_handshake_age_s": self.latest_handshake_age_s,
            "bytes_received": self.bytes_received,
            "bytes_sent": self.bytes_sent,
            "peer_count": self.peer_count,
            "reason": self.reason,
        }


class WireGuardRunner:
    """Abstract base — subclass for tests, subprocess, or mocks."""

    def is_up(self) -> bool: ...
    def up(self) -> WgRunResult: ...
    def down(self) -> WgRunResult: ...
    def show(self) -> WgShowResult: ...
    def write_runtime_conf(self, text: str) -> None: ...


class NullWireGuardRunner(WireGuardRunner):
    """Hermetic stand-in — every call is recorded. Used by tests + benches."""

    def __init__(self) -> None:
        self.up_calls: int = 0
        self.down_calls: int = 0
        self.show_calls: int = 0
        self.write_calls: List[str] = []
        self._up_return: WgRunResult = WgRunResult(ok=True, stdout="ok")
        self._down_return: WgRunResult = WgRunResult(ok=True, stdout="ok")
        self._show_return: WgShowResult = WgShowResult(
            ok=True, connected=False,
            endpoint="", latest_handshake_age_s=-1.0,
            bytes_received=0, bytes_sent=0, peer_count=0,
        )
        self._is_up: bool = False
        self._raise_on_show: Optional[BaseException] = None

    # ---------- test-only seed helpers -----------------------------------
    def queue_up(self, res: WgRunResult) -> None:
        self._up_return = res

    def queue_down(self, res: WgRunResult) -> None:
        self._down_return = res

    def queue_show(self, res: WgShowResult) -> None:
        self._show_return = res

    def set_is_up(self, value: bool) -> None:
        self._is_up = value

    def queue_show_raises(self, exc: BaseException) -> None:
        self._raise_on_show = exc

    # ---------- runner interface -----------------------------------------
    def is_up(self) -> bool:
        return self._is_up

    def up(self) -> WgRunResult:
        self.up_calls += 1
        if self._up_return.ok:
            self._is_up = True
        return self._up_return

    def down(self) -> WgRunResult:
        self.down_calls += 1
        if self._down_return.ok:
            self._is_up = False
        return self._down_return

    def show(self) -> WgShowResult:
        self.show_calls += 1
        if self._raise_on_show is not None:
            raise self._raise_on_show
        return self._show_return

    def write_runtime_conf(self, text: str) -> None:
        self.write_calls.append(text)


def parse_wg_show_output(text: str) -> WgShowResult:
    """Parse a ``wg show wg0`` text blob into a :class:`WgShowResult`.

    The output looks like::

        interface: wg0
          public key: <hex>
          private key: <hex>
          listening port: 54368
        peer: <hex>
          endpoint: 213.199.61.156:54368
          allowed ips: 0.0.0.0/0, ::/0
          latest handshake: 23 seconds ago
          transfer: 1.23 MiB received, 4.56 MiB sent
          persistent keepalive: every 25 seconds

    Parsing is line-oriented and tolerant of section reordering.
    ``private key:`` lines are stripped from the parsed ``raw`` field
    as well as ignored for attribute mapping — even `wg show` modes
    that don't redact the private key never get it echoed back
    through this parser.
    """
    if not text or not text.strip():
        return WgShowResult(ok=False, reason="empty_output")
    kept_lines: List[str] = []
    result = WgShowResult(ok=True, raw="")
    in_peer = False
    for line in text.splitlines():
        s = line.strip()
        if not s:
            kept_lines.append(line)
            continue
        if s.startswith("private key:"):
            # STRIP from raw echo as well as ignoring for attribute mapping.
            continue
        kept_lines.append(line)
        if s.startswith("interface:"):
            in_peer = False
            continue
        if s.startswith("peer:"):
            in_peer = True
            result.peer_count += 1
            continue
        if in_peer:
            if s.startswith("endpoint:"):
                result.endpoint = s.split(":", 1)[1].strip()
            elif s.startswith("latest handshake:"):
                result.latest_handshake_age_s = _parse_handshake_age(
                    s.split(":", 1)[1].strip()
                )
            elif s.startswith("transfer:"):
                rx, tx = _parse_transfer(s.split(":", 1)[1].strip())
                result.bytes_received = rx
                result.bytes_sent = tx
    result.raw = "\n".join(kept_lines)
    result.connected = (result.endpoint != "" and result.peer_count > 0)
    return result


def _parse_handshake_age(text: str) -> float:
    """Parse ``23 seconds ago`` / ``5 minutes ago`` / ``1 hour ago`` → seconds."""
    text = text.lower().replace("ago", "").strip()
    parts = text.split()
    if len(parts) >= 2:
        try:
            num = float(parts[0])
        except ValueError:
            return -1.0
        unit = parts[1]
        if unit.startswith("second"):
            return num
        if unit.startswith("minute"):
            return num * 60.0
        if unit.startswith("hour"):
            return num * 3600.0
        if unit.startswith("day"):
            return num * 86400.0
    return -1.0


def _parse_transfer(text: str) -> Tuple[int, int]:
    """Parse ``1.23 MiB received, 4.56 MiB sent`` → ``(bytes_rx, bytes_tx)``."""
    rx = tx = 0
    for chunk in text.split(","):
        chunk = chunk.strip()
        side: Optional[str] = None
        value_str = ""
        if chunk.endswith("received"):
            side = "rx"
            value_str = chunk[: -len("received")].strip()
        elif chunk.endswith("sent"):
            side = "tx"
            value_str = chunk[: -len("sent")].strip()
        else:
            continue
        try:
            num_s, unit = value_str.split()
            mult = {
                "B": 1, "KiB": 1024, "MiB": 1024 ** 2,
                "GiB": 1024 ** 3, "TiB": 1024 ** 4,
            }.get(unit, 1)
            n = int(float(num_s) * mult)
        except (ValueError, KeyError):
            n = 0
        if side == "rx":
            rx = n
        else:
            tx = n
    return (rx, tx)


class SubprocessWireGuardRunner(WireGuardRunner):
    """Real-host runner — explicit argv, no shell, ``sudo -n``."""

    def __init__(
        self,
        interface: str = DEFAULT_WG_INTERFACE,
        runtime_conf: str = DEFAULT_CONF_PATH,
        sudo_bin: str = "/usr/bin/sudo",
        wg_quick_bin: str = "/usr/bin/wg-quick",
        wg_bin: str = "/usr/bin/wg",
        timeout_s: float = 15.0,
    ) -> None:
        self.interface = interface
        self.runtime_conf = runtime_conf
        self.sudo = sudo_bin
        self.wg_quick = wg_quick_bin
        self.wg = wg_bin
        self.timeout_s = timeout_s

    def _run(self, argv: List[str]) -> WgRunResult:
        try:
            cp = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
                check=False,
            )
        except FileNotFoundError as exc:
            return WgRunResult(ok=False,
                               reason=f"binary_missing:{exc.filename}")
        except subprocess.TimeoutExpired:
            return WgRunResult(ok=False, reason="timeout")
        except OSError as exc:
            return WgRunResult(ok=False, reason=f"os_error:{exc}")
        ok = (cp.returncode == 0)
        return WgRunResult(
            ok=ok,
            reason="" if ok else f"exit_code_{cp.returncode}",
            stdout=cp.stdout or "",
            stderr=cp.stderr or "",
        )

    def is_up(self) -> bool:
        # `wg show` reads from a netlink socket that needs CAP_NET_ADMIN
        # (effectively root) on Linux. Use sudo -n so we fail fast on a
        # missing NOPASSWD entry rather than blocking on a password.
        show_result = self._run([
            self.sudo, "-n", self.wg, "show", self.interface,
        ])
        if not show_result.ok:
            return False
        parsed = parse_wg_show_output(show_result.stdout)
        return parsed.connected

    def up(self) -> WgRunResult:
        return self._run([
            self.sudo, "-n", self.wg_quick, "up", self.interface,
        ])

    def down(self) -> WgRunResult:
        return self._run([
            self.sudo, "-n", self.wg_quick, "down", self.interface,
        ])

    def show(self) -> WgShowResult:
        cp = self._run([self.wg, "show", self.interface])
        if not cp.ok:
            reason = "wg_cli_missing" if "binary_missing" in cp.reason \
                else f"wg_show_failed:{cp.reason}"
            return WgShowResult(ok=False, reason=reason)
        return parse_wg_show_output(cp.stdout)

    def write_runtime_conf(self, text: str) -> None:
        target = self.runtime_conf
        Path(target).parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(text)
        os.chmod(target, 0o600)


def resolve_runner(ctx: Any) -> WireGuardRunner:
    """Return ``ctx.vpn`` if it's a :class:`WireGuardRunner`, else a real
    subprocess runner."""
    if ctx is not None and hasattr(ctx, "vpn") \
            and isinstance(ctx.vpn, WireGuardRunner):
        return ctx.vpn
    return SubprocessWireGuardRunner()


__all__ = [
    "DEFAULT_WG_INTERFACE", "DEFAULT_CONF_PATH",
    "DEFAULT_WORKSPACE_ROOT", "ALLOWED_CONF_ROOTS",
    "WgInterface", "WgPeer", "WgConfig",
    "WgParseError", "parse_wg_conf", "validate_conf_path",
    "WireGuardRunner", "NullWireGuardRunner", "SubprocessWireGuardRunner",
    "WgRunResult", "WgShowResult", "parse_wg_show_output",
    "resolve_runner",
]
