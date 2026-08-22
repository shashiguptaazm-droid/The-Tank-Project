"""Shared helpers for the house / cast voice plugins.

Why this exists
~~~~~~~~~~~~~~~
Eight new plugins (``voice.play_music``, ``voice.play_youtube``,
``voice.play_tv``, ``voice.play_alexa``, ``voice.find_devices``,
``voice.power``, ``voice.move_to``, ``voice.whereami``) all need a
small handful of common primitives:

* A persistent **zone map** for the home — used by ``voice.move_to``,
  ``voice.whereami``, and any other spatial query. Stored in
  :data:`DEFAULT_ZONE_MAP_PATH` so the operator can edit it by hand.
* A passive **LAN device discovery** that reads :file:`/proc/net/arp`
  + a small mdns cache file (which we never *generate* ourselves —
  we ship the cache as an empty list and let the user drop in the
  output of ``avahi-browse --all -t`` if they want richer data).
* **Lazy shell-out wrappers** for ``mpv``, ``yt-dlp``, and
  ``cast-now`` so we don't take a hard dep on them. Each wrapper
  resolves its subprocess runner **at call time** (rather than
  default-binding it) so :func:`unittest.mock.patch` can swap the
  runner at test time.

Designed for hermetic tests: every helper accepts an injectable
``run`` callable so the unit tests never spawn a real ``mpv``.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


# -----------------------------------------------------------------------------
# Paths / defaults
# -----------------------------------------------------------------------------
DEFAULT_ZONE_MAP_PATH = Path("/etc/tank/zone_map.json")
DEFAULT_DEVICE_CACHE_PATH = Path("/var/cache/tank/devices.json")
DEFAULT_MOTION_INTENT_PATH = Path("/var/lib/tank/motion_intent.json")

DEFAULT_MUSIC_ROOTS = (Path("/music"), Path("/srv/music"),
                       Path(os.path.expanduser("~/Music")))

# What we treat as a "music" file. mpv can handle more; this is the
# intersection of what Alexa / Sonos / cast receivers expect.
AUDIO_EXTS = {".mp3", ".flac", ".ogg", ".m4a", ".aac", ".wav", ".opus", ".wma"}

# Tolerated relative direction ranges (clamped before publish).
RELATIVE_MIN_M = 0.05
RELATIVE_MAX_M = 4.0
MAX_FREE_VX_M_S = 0.4
MAX_FREE_WZ_RAD_S = 1.2


# -----------------------------------------------------------------------------
# Zone map
# -----------------------------------------------------------------------------
@dataclass
class Zone:
    """A labelled area in the home with a circular radius from a 2D anchor."""

    name: str
    x_m: float = 0.0
    y_m: float = 0.0
    radius_m: float = 1.5

    def contains(self, x: float, y: float) -> bool:
        dx, dy = x - self.x_m, y - self.y_m
        return (dx * dx + dy * dy) <= (self.radius_m * self.radius_m)


@dataclass
class Waypoint:
    name: str
    x_m: float = 0.0
    y_m: float = 0.0


@dataclass
class ZoneMap:
    zones: List[Zone] = field(default_factory=list)
    waypoints: List[Waypoint] = field(default_factory=list)
    current_pose: Dict[str, float] = field(default_factory=dict)
    origin_label: str = "dock"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "origin_label": self.origin_label,
            "current_pose": dict(self.current_pose),
            "zones": [asdict(z) for z in self.zones],
            "waypoints": [asdict(w) for w in self.waypoints],
        }

    @classmethod
    def from_dict(cls, raw: Any) -> "ZoneMap":
        if not isinstance(raw, dict):
            return cls()
        zm = cls()
        zm.origin_label = str(raw.get("origin_label") or "dock")
        pose = raw.get("current_pose") or {}
        if isinstance(pose, dict):
            zm.current_pose = {
                k: float(v) for k, v in pose.items()
                if isinstance(v, (int, float))
            }
        for z in raw.get("zones") or []:
            if isinstance(z, dict) and isinstance(z.get("name"), str):
                zm.zones.append(Zone(
                    name=z["name"].strip(),
                    x_m=float(z.get("x_m", 0.0)),
                    y_m=float(z.get("y_m", 0.0)),
                    radius_m=float(z.get("radius_m", 1.5)),
                ))
        for w in raw.get("waypoints") or []:
            if isinstance(w, dict) and isinstance(w.get("name"), str):
                zm.waypoints.append(Waypoint(
                    name=w["name"].strip(),
                    x_m=float(w.get("x_m", 0.0)),
                    y_m=float(w.get("y_m", 0.0)),
                ))
        return zm

    def get_zone(self, name: str) -> Optional[Zone]:
        name = (name or "").strip().lower()
        for z in self.zones:
            if z.name.lower() == name:
                return z
        return None

    def get_waypoint(self, name: str) -> Optional[Waypoint]:
        name = (name or "").strip().lower()
        for w in self.waypoints:
            if w.name.lower() == name:
                return w
        return None

    def zone_at(self, x: float, y: float) -> Optional[Zone]:
        for z in self.zones:
            if z.contains(x, y):
                return z
        return None

    def save(self, path: Optional[Path] = None) -> None:
        path = path or DEFAULT_ZONE_MAP_PATH
        parent = path.parent
        if str(parent) and str(parent) != ".":
            parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2))


def load_zone_map(path: Optional[Path] = None) -> ZoneMap:
    """Read the operator-curated zone map from disk. Empty default on miss."""
    if path is None:
        path = DEFAULT_ZONE_MAP_PATH
    if not path.exists():
        return ZoneMap()
    try:
        return ZoneMap.from_dict(json.loads(path.read_text()))
    except (OSError, ValueError):
        return ZoneMap()


# -----------------------------------------------------------------------------
# Power state
# -----------------------------------------------------------------------------
PWR_STATES = ("awake", "sleeping", "rebooting", "soft_restart")
DEFAULT_POWER_STATE_PATH = Path("/var/lib/tank/power_state.json")


@dataclass
class PowerState:
    mode: str = "awake"
    since: float = 0.0
    estop_latched: bool = False
    last_transition_reason: str = ""


def load_power_state(path: Optional[Path] = None) -> PowerState:
    if path is None:
        path = DEFAULT_POWER_STATE_PATH
    if not path.exists():
        return PowerState(since=time.time())
    try:
        raw = json.loads(path.read_text())
    except (OSError, ValueError):
        return PowerState(since=time.time())
    if not isinstance(raw, dict):
        return PowerState(since=time.time())
    mode = str(raw.get("mode", "awake")).strip().lower()
    if mode not in PWR_STATES:
        mode = "awake"
    return PowerState(
        mode=mode,
        since=float(raw.get("since", time.time()) or 0.0),
        estop_latched=bool(raw.get("estop_latched", False)),
        last_transition_reason=str(raw.get("last_transition_reason", ""))[:120],
    )


def save_power_state(state: PowerState,
                     path: Optional[Path] = None) -> None:
    if path is None:
        path = DEFAULT_POWER_STATE_PATH
    parent = path.parent
    if str(parent) and str(parent) != ".":
        parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(state), indent=2))


# -----------------------------------------------------------------------------
# Motion-intent dispatcher (file-based).
#
# The bridge process publishes motion intent to a tiny JSON file the host
# lifecycle script polls every ~200 ms.  This decouples the plugin from
# any in-process publisher and keeps the bridge entirely stateless about
# motion.
# -----------------------------------------------------------------------------
def save_motion_intent(intent: Dict[str, Any],
                       path: Optional[Path] = None) -> None:
    """Persist a motion intent to disk so a polling lifecycle script
    can dispatch it to the actual nav stack."""
    if path is None:
        path = DEFAULT_MOTION_INTENT_PATH
    parent = path.parent
    if str(parent) and str(parent) != ".":
        parent.mkdir(parents=True, exist_ok=True)
    payload = {"intent": intent, "ts": time.time()}
    path.write_text(json.dumps(payload, indent=2))


# -----------------------------------------------------------------------------
# Passive LAN discovery — ARP cache + mdns service file
# -----------------------------------------------------------------------------
DEFAULT_MDNS_SERVICES = (
    "_googlecast._tcp.local.",
    "_airplay._tcp.local.",
    "_sonos._tcp.local.",
    "_workstation._tcp.local.",
    "_ssh._tcp.local.",
    "_http._tcp.local.",
    "_ipp._tcp.local.",
    "_amazon._tcp.local.",
)


@dataclass
class DiscoveredDevice:
    name: str
    address: str
    port: int
    service: str
    source: str


def read_arp_table() -> List[DiscoveredDevice]:
    out: List[DiscoveredDevice] = []
    if not os.path.exists("/proc/net/arp"):
        return out
    try:
        text = Path("/proc/net/arp").read_text()
    except OSError:
        return out
    for line in text.splitlines()[1:]:
        parts = re.split(r"\s+", line.strip())
        if len(parts) < 6:
            continue
        ip, _hw, _flags, _mac, _mask, _dev = parts[:6]
        if ip and _flags and _flags != "0x0":
            out.append(DiscoveredDevice(
                name=reverse_dns(ip) or ip,
                address=ip, port=0, service="lan_neighbour",
                source="arp",
            ))
    return out


def reverse_dns(ip: str, timeout_s: float = 0.6) -> str:
    try:
        return socket.gethostbyaddr(ip)[0]
    except (socket.herror, socket.gaierror, TimeoutError, OSError):
        return ""


def load_device_cache(path: Optional[Path] = None) -> List[DiscoveredDevice]:
    if path is None:
        path = DEFAULT_DEVICE_CACHE_PATH
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text())
    except (OSError, ValueError):
        return []
    out: List[DiscoveredDevice] = []
    for d in raw if isinstance(raw, list) else []:
        if not isinstance(d, dict):
            continue
        out.append(DiscoveredDevice(
            name=str(d.get("name", ""))[:120],
            address=str(d.get("address", "")),
            port=int(d.get("port", 0) or 0),
            service=str(d.get("service", ""))[:32],
            source=str(d.get("source", "mdns"))[:16],
        ))
    return out


def save_device_cache(devices: List[DiscoveredDevice],
                      path: Optional[Path] = None) -> None:
    if path is None:
        path = DEFAULT_DEVICE_CACHE_PATH
    parent = path.parent
    if str(parent) and str(parent) != ".":
        parent.mkdir(parents=True, exist_ok=True)
    payload = [asdict(d) for d in devices]
    path.write_text(json.dumps(payload, indent=2))


def discover_devices(include_arp: bool = True,
                     include_mdns_cache: bool = True) -> List[DiscoveredDevice]:
    seen: Dict[str, DiscoveredDevice] = {}
    if include_arp:
        for d in read_arp_table():
            seen.setdefault(d.address, d)
    if include_mdns_cache:
        for d in load_device_cache():
            seen[d.address] = d
    return list(seen.values())


# -----------------------------------------------------------------------------
# Local music library scan
# -----------------------------------------------------------------------------
@dataclass
class TrackHit:
    """A single music-library hit with a precomputed score.

    The score is stored as a plain float field (not a method) so that
    ``key=lambda h: h.score`` reads the value directly.  Earlier we
    stored the value AND a ``score()`` method on the same dataclass
    which produced ambiguous attribute access — the field shadowed the
    method.
    """
    path: str
    title: str
    artist: str = ""
    duration_s: float = 0.0
    score: float = 0.0


_AUDIO_NAME_RE = re.compile(
    r"^(?P<artist>[^-/]+?)\s*[-/]\s*(?P<title>.+?)(?:\.(?P<ext>mp3|flac|ogg|m4a|aac|wav|opus|wma))$",
    re.IGNORECASE,
)


def scan_music(query: str,
                roots: Optional[List[Path]] = None,
                limit: int = 5) -> List[TrackHit]:
    q = (query or "").strip().lower()
    q_tokens = [t for t in re.split(r"\W+", q) if len(t) >= 2]
    if roots is None:
        roots = [Path(r) for r in DEFAULT_MUSIC_ROOTS
                 if Path(r).exists()]
    hits: List[TrackHit] = []
    for root in roots:
        try:
            iterator = root.rglob("*")
        except OSError:
            continue
        for path in iterator:
            if not path.is_file() or path.suffix.lower() not in AUDIO_EXTS:
                continue
            stem = path.stem
            m = _AUDIO_NAME_RE.match(path.name)
            title = m.group("title").strip() if m else stem
            artist = m.group("artist").strip() if m else ""
            score = _score_match(stem.lower(), q, q_tokens)
            if score <= 0.0 and q:
                continue
            hits.append(TrackHit(path=str(path), title=title,
                                 artist=artist, score=score))
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:limit]


def _score_match(stem_lower: str,
                 q: str, q_tokens: List[str]) -> float:
    if not q:
        return 1.0
    score = 0.0
    if q in stem_lower:
        score += 100.0
    for t in q_tokens:
        if t in stem_lower:
            score += 10.0
    return score


# -----------------------------------------------------------------------------
# Lazy shell-out helpers
#
# IMPORTANT: each `run` parameter is OPTIONAL and resolved at call time
# so :func:`unittest.mock.patch` of ``_default_run`` always takes
# effect. Default-binding the function captures the original reference
# at import time and is immune to later patching.
# -----------------------------------------------------------------------------
SubprocessRun = Callable[..., "subprocess.CompletedProcess[str]"]


def which_or_hint(binary: str, run: Optional[SubprocessRun] = None) -> Dict[str, Any]:
    path = shutil.which(binary)
    if not path:
        return {"_ok": False, "_hint":
                f"missing binary {binary!r} — please install it "
                f"and re-run."}
    runner = run if run is not None else _default_run
    try:
        proc = runner(path, "--version")
        version_line = (proc.stdout or "").splitlines()[0] if proc.stdout else ""
    except (OSError, subprocess.TimeoutExpired):
        version_line = ""
    return {"_ok": True, "path": path, "version": version_line}


def shell_mpv(target: str,
              video: bool = False,
              blocking: bool = False,
              run: Optional[SubprocessRun] = None) -> Dict[str, Any]:
    found = which_or_hint("mpv", run)
    if not found.get("_ok"):
        return found
    args: List[str] = [
        found["path"],
        "--no-terminal",
        "--really-quiet",
    ]
    if not video:
        args.append("--no-video")
    if not blocking:
        args.append("--force-window=no")
    args.append(target)
    try:
        proc = subprocess.Popen(
            args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        return {"_ok": False, "_hint": f"mpv spawn failed: {exc}"}
    return {"_ok": True, "pid": proc.pid, "binary": found["path"]}


def shell_ytdlp(query: str,
                audio_only: bool = False,
                run: Optional[SubprocessRun] = None) -> Dict[str, Any]:
    found = which_or_hint("yt-dlp", run)
    if not found.get("_ok"):
        return found
    args: List[str] = [
        found["path"], "-g", "--no-warnings", "--no-playlist",
    ]
    if audio_only:
        args += ["-f", "bestaudio"]
    else:
        args += ["-f", "best"]
    args.append(query)
    runner = run if run is not None else _default_run
    try:
        proc = runner(args)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"_ok": False, "_hint": f"yt-dlp failed: {exc}"}
    if proc.returncode != 0:
        return {"_ok": False, "_hint":
                (proc.stderr or "").strip()[:300] or "yt-dlp returned non-zero"}
    lines = (proc.stdout or "").splitlines()
    url = lines[0].strip() if lines else ""
    if not url.startswith(("http://", "https://")):
        return {"_ok": False, "_hint": "yt-dlp produced no URL"}
    return {"_ok": True, "url": url, "query": query}


def shell_cast(device: str,
               target: str) -> Dict[str, Any]:
    binary = shutil.which("cast-now") or shutil.which("catt")
    if not binary:
        return {"_ok": False,
                "_hint": "neither cast-now nor catt installed; "
                         "install one to use cast features."}
    args: List[str]
    if binary.endswith("cast-now") or "cast-now" in binary:
        args = [binary, "--device", device, target]
    else:
        args = [binary, "cast", device, target]
    try:
        proc = subprocess.Popen(
            args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        return {"_ok": False, "_hint": f"cast spawn failed: {exc}"}
    return {"_ok": True, "pid": proc.pid, "binary": binary,
            "device": device, "target": target}


# -----------------------------------------------------------------------------
# Subprocess runner.  Tests can ;p this.
# -----------------------------------------------------------------------------
def _default_run(*args, **kwargs) -> "subprocess.CompletedProcess[str]":
    kwargs.setdefault("timeout", 6.0)
    kwargs.setdefault("capture_output", True)
    kwargs.setdefault("text", True)
    # Note: subprocess.run expects *popenargs as a tuple of strings,
    # so we use `*args` to forward the caller's tuple unpacked.
    return subprocess.run(*args, **kwargs)


def clamp_relative_distance(distance_m: float) -> float:
    return float(max(RELATIVE_MIN_M, min(RELATIVE_MAX_M, float(distance_m))))
