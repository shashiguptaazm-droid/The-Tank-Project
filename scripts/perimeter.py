#!/usr/bin/env python3
"""The Tank Project — perimeter / security helpers.

Hosts 4 features (F067-F070):

* ``geofence``    — validate a polygon / add new vertices in JSON
* ``motion-zone`` — render motion zone definitions as ASCII art
* ``night-mode``  — verify a night-mode schedule (start, end hours)
* ``intrusion``   — pull /security/events/intruder from the topic log
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path



LOG_PREFIX = "[perimeter]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# F067 — geofence
# ---------------------------------------------------------------------------
def cmd_geofence(args: argparse.Namespace) -> int:
    """F067 — geofence edit."""
    poly_file = Path(args.path)
    if poly_file.exists():
        poly = json.loads(poly_file.read_text())
    else:
        poly = {"points": []}
    if args.add:
        for pt in args.add:
            x, y = (float(c) for c in pt.split(","))
            poly["points"].append([x, y])
    if args.clear:
        poly["points"] = []
    poly_file.parent.mkdir(parents=True, exist_ok=True)
    poly_file.write_text(json.dumps(poly, indent=2))
    _ok(f"geofence: {len(poly['points'])} vertices -> {poly_file}")
    return 0


# ---------------------------------------------------------------------------
# F068 — motion-zone
# ---------------------------------------------------------------------------
def cmd_motion_zone(args: argparse.Namespace) -> int:
    """F068 — motion-zone plot."""
    poly_file = Path(args.from_)
    if not poly_file.exists():
        _err(f"zone file missing: {poly_file}")
        return 1
    poly = json.loads(poly_file.read_text()).get("points", [])
    if not poly:
        _err("zone has 0 points")
        return 1
    xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
    min_x, max_x = min(xs), max(xs); min_y, max_y = min(ys), max(ys)
    W, H = 60, 18
    grid = [[" "] * W for _ in range(H)]
    for x, y in poly:
        gx = int((x - min_x) / max(max_x - min_x, 1e-6) * (W - 1))
        gy = int((max_y - y) / max(max_y - min_y, 1e-6) * (H - 1))
        if 0 <= gx < W and 0 <= gy < H:
            grid[gy][gx] = "#"
    print(banner := "+" + "-" * W + "+")
    for row in grid:
        print("|" + "".join(row) + "|")
    print(banner)
    _ok(f"rendered {len(poly)} vertices in a {W}x{H} grid")
    return 0


# ---------------------------------------------------------------------------
# F069 — night-mode
# ---------------------------------------------------------------------------
def cmd_night_mode(args: argparse.Namespace) -> int:
    """F069 — night mode schedule validation."""
    def parse(t: str) -> int:
        h, m = t.split(":")
        return int(h) * 60 + int(m)
    start = parse(args.from_)
    end = parse(args.to)
    if start == end:
        _err("start == end (24-hour window needed)")
        return 1
    if start < end:
        span = end - start
    else:
        span = (24 * 60 - start) + end
    _ok(json.dumps({
        "start": args.from_, "end": args.to_,
        "span_min": span, "span_hours": round(span / 60.0, 2),
    }, indent=2))
    return 0


# ---------------------------------------------------------------------------
# F070 — intrusion timeline
# ---------------------------------------------------------------------------
def cmd_intrusion(args: argparse.Namespace) -> int:
    """F070 — intrusion timeline pull."""
    db = _repo_root() / "tank_ws" / "data" / "log.db"
    if not db.exists():
        _err(f"log.db missing: {db}")
        return 1
    with sqlite3.connect(db) as con:
        rows = con.execute(
            "SELECT ts, payload_text FROM topic_logs "
            "WHERE topic = '/security/events/intruder' "
            "ORDER BY ts DESC LIMIT ?", (args.limit,),
        ).fetchall()
    summary = []
    for ts, payload in rows:
        try:
            payload_obj = json.loads(payload or "{}")
            summary.append({
                "ts": ts,
                "label":    payload_obj.get("label", "?"),
                "severity": payload_obj.get("severity", "?"),
                "text":     (payload_obj.get("text", "") or "")[:120],
            })
        except json.JSONDecodeError:
            summary.append({"ts": ts, "raw": (payload or "")[:120]})
    _ok(json.dumps({"hours": args.hours, "events": summary}, indent=2))
    return 0


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Perimeter / security helpers (F067-F070).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pg = sub.add_parser("geofence", help="F067 — geofence editor")
    pg.add_argument("--path", default="tank_ws/data/geofence.json")
    pg.add_argument("--add", nargs="*", metavar="X,Y",
                    help="vertex to add (space-separated)")
    pg.add_argument("--clear", action="store_true")

    pm = sub.add_parser("motion-zone", help="F068 — motion-zone plot")
    pm.add_argument("--from", dest="from_", required=True)

    pn = sub.add_parser("night-mode", help="F069 — night mode schedule")
    pn.add_argument("--from", dest="from_", required=True, help="HH:MM")
    pn.add_argument("--to",   dest="to",   required=True, help="HH:MM")

    pi = sub.add_parser("intrusion", help="F070 — intrusion timeline")
    pi.add_argument("--hours", type=int, default=24)
    pi.add_argument("--limit", type=int, default=200)
    return p


HANDLERS = {
    "geofence":    cmd_geofence,
    "motion-zone": cmd_motion_zone,
    "night-mode":  cmd_night_mode,
    "intrusion":   cmd_intrusion,
}


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return HANDLERS[args.cmd](args)
    except KeyboardInterrupt:
        _err("interrupted")
        return 130


if __name__ == "__main__":
    sys.exit(main())
