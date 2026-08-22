"""Render live sensor state into the JSON the dashboard UI consumes.

The front-end hits ``GET /api/live`` and renders one :class:`LiveTile`
per topic.  :func:`render_tile_grid` is the single seam between the
:class:`SensorState` list (in :mod:`_live_sensor`) and the page.

Status colours:
    ok    -> #16a34a (green)
    warn  -> #ca8a04 (amber)
    alarm -> #dc2626 (red)
"""
from __future__ import annotations

from typing import Any, Dict, List

from ._live_sensor import SensorState


# Theme colour tokens — the front-end leans on these.
COLOR_FOR_STATUS = {
    "ok":    "#16a34a",
    "warn":  "#ca8a04",
    "alarm": "#dc2626",
}


def render_tile(state: SensorState) -> Dict[str, Any]:
    """Render one :class:`SensorState` as a UI-ready tile dict."""
    return {
        "topic":       state.topic,
        "name":        state.name,
        "value":       state.value,
        "units":       state.units,
        "status":      state.status.value,
        "color":       COLOR_FOR_STATUS[state.status.value],
        "hint":        state.hint,
        "last_update": state.last_update,
        "stale_ms":    _stale_ms(state.last_update),
    }


def render_tile_grid(states: List[SensorState]) -> Dict[str, Any]:
    """All tiles + the worst status seen + a coloured barrier flag.

    The page renders one section per status so an operator walking up
    to the dashboard sees the alarm state front-and-centre.
    """
    tiles = [render_tile(s) for s in states]
    worst = "ok"
    for t in tiles:
        if t["status"] == "alarm":
            worst = "alarm"
            break
        if t["status"] == "warn" and worst == "ok":
            worst = "warn"
    return {
        "tiles":        tiles,
        "worst_status": worst,
        "color":        COLOR_FOR_STATUS[worst],
        "count":        len(tiles),
        "alarm_count":  sum(1 for t in tiles if t["status"] == "alarm"),
        "warn_count":   sum(1 for t in tiles if t["status"] == "warn"),
    }


def _stale_ms(last_update: float) -> int:
    """How many ms ago this sensor last published. 0 == not yet seen."""
    if not last_update:
        return 0
    import time
    return int((time.time() - last_update) * 1000)


def render_power(state: Dict[str, Any]) -> Dict[str, Any]:
    """Power-dashboard tile."""
    mode = state.get("mode", "wake")
    return {
        "mode":        mode,
        "color":       "#16a34a" if mode == "wake" else
                       "#ca8a04"  if mode == "sleep" else
                       "#dc2626",
        "since":       state.get("since", 0.0),
        "uptime_sec":  state.get("uptime_sec", 0.0),
        "estop_ok":    bool(state.get("estop_ok", True)),
        "source":      state.get("source", "default"),
        "history_len": len(state.get("history", [])),
    }
