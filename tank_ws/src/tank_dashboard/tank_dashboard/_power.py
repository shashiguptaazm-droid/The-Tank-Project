"""Power-control state for the dashboard.

Mirrors ``tank_command_bridge.plugins.power`` so the operator has
both a UI button row and a programmatic state. The dashboard
talks to the same JSON file on disk so there's no double
source-of-truth.

Three modes today::

    "sleep"  — motors + camera off, wake-word listener still on
    "wake"   — full availability, the default after boot
    "reboot" — issues ``reboot now`` after a short confirmation

Persisted to ``/var/lib/tank/power_state.json`` so a watchdog outside
the dashboard can reapply it after a reboot.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional


DEFAULT_POWER_STATE_PATH = Path(
    os.environ.get("TANK_POWER_STATE", "/var/lib/tank/power_state.json")
)


class PowerMode(str, Enum):
    SLEEP = "sleep"
    WAKE = "wake"
    REBOOT = "reboot"


@dataclass
class PowerState:
    mode: str = "wake"               # one of PowerMode
    since: float = 0.0               # epoch seconds
    estop_ok: bool = True            # E-stop overridden by power.plugin?
    uptime_sec: float = 0.0
    source: str = "default"          # "user"|"api"|"default"|"watchdog"
    history: list = field(default_factory=list)   # last 20 actions

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["mode"] = str(self.mode)
        return d


def load_power_state(path: Optional[Path] = None) -> PowerState:
    p = Path(path or DEFAULT_POWER_STATE_PATH)
    if not p.is_file():
        return PowerState(mode="wake", since=time.time(), source="default")
    try:
        with p.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return PowerState(mode="wake", since=time.time(), source="default")
    return PowerState(
        mode=str(data.get("mode", "wake")),
        since=float(data.get("since", time.time())),
        estop_ok=bool(data.get("estop_ok", True)),
        uptime_sec=float(data.get("uptime_sec", 0.0)),
        source=str(data.get("source", "default")),
        history=list(data.get("history", []))[-20:],
    )


def save_power_state(state: PowerState, path: Optional[Path] = None) -> bool:
    """Persist to disk; returns True on success, False on permission errors.

    Caller decides what to do when False (UI shows a banner, watchdog
    falls back to defaults, etc).
    """
    p = Path(path or DEFAULT_POWER_STATE_PATH)
    try:
        if str(p.parent) and str(p.parent) != ".":
            p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as fh:
            json.dump(state.to_dict(), fh)
        return True
    except OSError:
        return False


def apply_mode(state: PowerState, mode: str, source: str = "api") -> PowerState:
    """Transition ``state.mode`` → ``mode`` and append history."""
    m = mode.strip().lower()
    if m not in {x.value for x in PowerMode}:
        return state
    state.history.append({"from": state.mode, "to": m,
                          "by": source, "ts": time.time()})
    state.mode = m
    state.since = time.time()
    state.source = source
    return state
