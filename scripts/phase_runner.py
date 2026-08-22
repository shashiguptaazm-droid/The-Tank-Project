#!/usr/bin/env python3
"""The Tank Project — phase runner.

Walks each phase from ``PHASES.md`` (P1 through P10½) and inspects
each associated log file — one file at a time — printing PASS / FAIL
/ MISSING for every check.  Designed to be useful both on a fresh
bench (``data/`` empty) and on a running Pi (sqlite + jsonl files
populated by the runtime).

Subcommands
-----------

* ``phases``        — list every registered phase (id + name + files)
* ``logs``          — list ``tank_ws/data/`` content with sizes + table counts
* ``examine FILE``  — peek into a single file (sqlite schema / json / jsonl)
* ``check PHASE``   — run the checks for one phase ID (e.g. ``P6``)
* ``run``           — walk every phase sequentially, OK / FAIL summary
* ``seed``          — create a tiny demo ``log.db`` so ``run`` has data

Usage::

    python3 scripts/phase_runner.py phases
    python3 scripts/phase_runner.py logs
    python3 scripts/phase_runner.py examine tank_ws/data/log.db
    python3 scripts/phase_runner.py check P6½
    python3 scripts/phase_runner.py run
    python3 scripts/phase_runner.py seed        # demo-log.db created
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Tuple


LOG_PREFIX = "[phase-runner]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _data_dir() -> Path:
    return _repo_root() / "tank_ws" / "data"


# ---------------------------------------------------------------------------
# Phase definitions
# ---------------------------------------------------------------------------


@dataclass
class Check:
    """A single check against a single file.  Returns ``(status, note)``."""

    label: str
    path:  Path
    run:   Callable[[Path], tuple]


@dataclass
class Phase:
    pid:    str
    name:   str
    notes:  str
    expected: List[str]
    checks: List[Check] = field(default_factory=list)


def _check_sqlite_tables(table_names: List[str]) -> Callable:
    """Build a check that verifies the file has (at least) the tables."""
    def _run(path: Path) -> tuple:
        if not path.exists():
            return ("MISSING", f"{path.name} absent")
        try:
            with sqlite3.connect(path) as con:
                rows = con.execute("SELECT name FROM sqlite_master "
                                  "WHERE type='table'").fetchall()
                tbls = sorted(r[0] for r in rows)
            missing = [t for t in table_names if t not in tbls]
            if missing:
                return ("FAIL", f"{path.name} missing tables: {missing}")
            return ("PASS", f"{path.name} tables={tbls}")
        except sqlite3.Error as exc:
            return ("FAIL", f"{path.name} open: {exc}")
    return _run


def _check_sqlite_integrity() -> Callable:
    def _run(path: Path) -> tuple:
        if not path.exists():
            return ("MISSING", f"{path.name} absent")
        try:
            with sqlite3.connect(path) as con:
                row = con.execute("PRAGMA integrity_check").fetchone()
            status = row[0] if row else "unknown"
            return ("PASS" if status == "ok" else "FAIL",
                    f"{path.name} integrity={status}")
        except sqlite3.Error as exc:
            return ("FAIL", f"{path.name}: {exc}")
    return _run


def _check_jsonl_nonempty() -> Callable:
    def _run(path: Path) -> tuple:
        if not path.exists():
            return ("MISSING", f"{path.name} absent")
        try:
            with path.open("r") as fh:
                nonblank = sum(1 for ln in fh if ln.strip())
        except OSError as exc:
            return ("FAIL", f"{path.name}: {exc}")
        if nonblank == 0:
            return ("WARN", f"{path.name} is empty")
        return ("PASS", f"{path.name} {nonblank} rows")
    return _run


def _check_json_keys(*keys: str) -> Callable:
    def _run(path: Path) -> tuple:
        if not path.exists():
            return ("MISSING", f"{path.name} absent")
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            return ("FAIL", f"{path.name} json: {exc}")
        if not isinstance(data, dict):
            return ("WARN", f"{path.name} top-level is={type(data).__name__}")
        missing = [k for k in keys if k not in data]
        if missing:
            return ("FAIL", f"{path.name} missing keys: {missing}")
        return ("PASS", f"{path.name} keys OK")
    return _run


def _check_personalize(p: Path) -> tuple:
    """P10½ — persona.json optional on a fresh bench."""
    if not p.exists():
        return ("MISSING", f"{p.name} absent (acceptable for fresh bench)")
    return ("PASS", f"{p.name} present")


def _check_log_security(p: Path) -> tuple:
    """P7 / P9 — log.db topic_logs should carry security & audit rows."""
    if not p.exists():
        return ("MISSING", f"{p.name} absent")
    try:
        with sqlite3.connect(p) as con:
            count = con.execute(
                "SELECT COUNT(*) FROM topic_logs WHERE "
                "topic IN ('/security/events/motion', "
                "'/security/events/intruder', "
                "'/security/recording_path', '/api/cmd/audit')"
            ).fetchone()[0]
    except sqlite3.Error as exc:
        return ("FAIL", f"{p.name}: {exc}")
    if count == 0:
        return ("WARN", f"{p.name} no security/audit rows yet")
    return ("PASS", f"{p.name} {count} security/audit rows")


def _build_phases() -> List[Phase]:
    data = _data_dir()

    def relative(name: str) -> Path:
        return data / name

    phases: List[Phase] = [
        Phase("P1",   "Foundation, motion, vision",
              "verify motor_controller / pan_tilt_controller / camera topics",
              ["memory.db (created on first chat)"],
              [Check("memory_persist", relative("memory.db"),
                     _check_sqlite_tables([]))]),
        Phase("P2",   "Eyes, tracker, mapping",
              "eye_lcd_bridge UART lane, YOLO tracker, SLAM trace",
              ["memory.db"],
              [Check("log_topic_count", relative("log.db"),
                     _check_sqlite_tables(["topic_logs"]))]),
        Phase("P3",   "Networking + storage",
              "WireGuard, Tailscale, NAS mount via /var/tank/media",
              ["memory.db, meta.db, log.db (sustained)"],
              [Check("memory_persist", relative("memory.db"),
                     _check_sqlite_tables([]))]),
        Phase("P4",   "Security + auto-dock + power",
              "tank_dock AprilTag, BMS / hardware_io GPIO strobe",
              ["memory.db, meta.db (decisions/decisions.json)"]),
        Phase("P5",   "Voice + assistant + persistent memory",
              "wake_word_listener → llama.cpp + memory_store",
              ["memory.db"],
              [Check("memory_schema", relative("memory.db"),
                     _check_sqlite_tables([]))]),
        Phase("P5½", "Emotion fan-out (eyes + OLED + dashboard)",
              "tank_display / emotion/state wires",
              ["log.db `/emotion/state` rows"]),
        Phase("P6",   "Coding-agent structured memory",
              "tank_meta code/hardware/decisions/knowledge tables",
              ["meta.db, decisions.json, hardware.json, project.json"],
              [Check("meta_tables", relative("meta.db"),
                     _check_sqlite_tables(
                         ["code_files", "hardware", "decisions",
                          "knowledge"])),
               Check("decisions_json", _repo_root()
                       / "tank_ws" / "src" / "tank_meta" / "content"
                       / "decisions.json",
                     _check_json_keys("schema_version", "decisions"))]),
        Phase("P6½", "Append-only event logger + learner",
              "tank_log topic_logs + topic_summary + learner",
              ["log.db"],
              [Check("log_db_tables", relative("log.db"),
                     _check_sqlite_tables(["topic_logs"])),
               Check("log_db_integrity", relative("log.db"),
                     _check_sqlite_integrity())]),
        Phase("P7",   "Autonomous patrolling + surveillance",
              "tank_patrol + tank_security JSONL",
              ["log.db with security/audit rows"],
              [Check("log_security_events", relative("log.db"),
                     _check_log_security)]),
        Phase("P8",   "Real hardware + on-robot deploy",
              "boot, provision_pi5.sh --apply, robot.launch.py",
              ["meta.db, memory.db populated by robot"]),
        Phase("P9",   "Bidirectional AI ↔ Pi bridge",
              "tank_command_bridge on :8082 + audit log",
              ["log.db `/api/cmd/audit` events"],
              [Check("log_audit", relative("log.db"),
                     _check_sqlite_tables(["topic_logs"]))]),
        Phase("P10",  "Voice task framework (9 sample tasks + registry)",
              "tank_task registry",
              ["memory.db"],
              [Check("memory_persist", relative("memory.db"),
                     _check_sqlite_tables([]))]),
        Phase("P10½", "AI humanness + complete preferences dashboard",
              "tank_personalize prefs.db + persona.json",
              ["prefs.db optional, persona.json optional"],
              [Check("prefs_json", relative("persona.json"),
                     _check_personalize)]),
    ]
    return phases


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


def cmd_phases(_: argparse.Namespace) -> int:
    """F151 — list registered phases."""
    phases = _build_phases()
    print(f"# {len(phases)} phases")
    width = max(len(p.pid) for p in phases)
    for p in phases:
        files = ", ".join(p.expected) if p.expected else "—"
        print(f"  {p.pid:<{width}}  {p.name:<48}  files=[{files}]")
    return 0


def cmd_logs(args: argparse.Namespace) -> int:
    """F152 — list data/ contents with sizes + sqlite table counts."""
    data = _data_dir()
    if not data.is_dir():
        _err(f"data/ missing — {data}")
        return 1
    rows = []
    for path in sorted(data.rglob("*")):
        if path.is_file():
            size = path.stat().st_size
            tables = None
            if path.suffix == ".db":
                try:
                    with sqlite3.connect(path) as con:
                        tables = sorted(
                            r[0] for r in con.execute(
                                "SELECT name FROM sqlite_master "
                                "WHERE type='table'").fetchall())
                except sqlite3.Error as exc:
                    tables = [f"<{exc}>"]
            rows.append({"path": str(path),
                         "size": size,
                         "tables": tables})
    if not rows:
        _ok(json.dumps({"data_dir": str(data),
                        "files": 0,
                        "note": "empty (fresh bench detected)"}, indent=2))
        return 0
    _ok(json.dumps({"data_dir": str(data),
                    "n_files": len(rows),
                    "files": rows[:args.limit]}, indent=2))
    return 0


def cmd_examine(args: argparse.Namespace) -> int:
    """F153 — peek into a single file."""
    if not args.path:
        _err("examine requires a path argument")
        return 2
    path = Path(args.path)
    if not path.exists():
        _err(f"missing: {path}")
        return 1
    if path.is_dir():
        _err(f"{path} is a directory; pass a file path")
        return 1
    if path.suffix == ".db":
        with sqlite3.connect(path) as con:
            tables = sorted(
                r[0] for r in con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"))
            rows_per_table = {t: con.execute(f"SELECT count(*) FROM {t}")
                              .fetchone()[0] for t in tables}
        _ok(json.dumps({"path": str(path),
                        "tables": tables,
                        "row_counts": rows_per_table}, indent=2))
        return 0
    if path.suffix == ".json":
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            _err(f"json: {exc}")
            return 1
        if isinstance(data, dict):
            keys = list(data.keys())
            preview = {k: (str(data[k])[:80] + "…"
                           if len(str(data[k])) > 80 else data[k])
                      for k in keys[:args.head]}
        else:
            preview = (data if isinstance(data, list)
                       else str(data))[:args.head]
        _ok(json.dumps({"path": str(path), "type": "json",
                        "preview": preview}, indent=2,
                       default=str))
        return 0
    if path.suffix == ".jsonl":
        n = 0
        head = []
        with path.open("r") as fh:
            for line in fh:
                if not line.strip():
                    continue
                if n < args.head:
                    head.append(line.rstrip()[:200])
                n += 1
        _ok(json.dumps({"path": str(path), "type": "jsonl",
                        "n_lines": n, "head": head}, indent=2))
        return 0
    if path.suffix in (".log", ".txt"):
        lines = path.read_text().splitlines()
        _ok(json.dumps({"path": str(path), "type": path.suffix,
                        "n_lines": len(lines),
                        "head": lines[:args.head],
                        "tail": lines[-args.head:]}, indent=2))
        return 0
    # Fallback — hexdump first 64 bytes
    raw = path.open("rb").read(64)
    _ok(json.dumps({"path": str(path), "type": path.suffix,
                    "head_bytes_hex": raw.hex()}, indent=2))
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """F155 — run the checks for one phase."""
    pid = args.phase
    phase = next((p for p in _build_phases()
                  if p.pid.lower() == pid.lower()), None)
    if phase is None:
        _err(f"no phase {pid}; try 'python3 scripts/phase_runner.py phases'")
        return 1
    bad, _hard = _run_phase(phase)
    return 0 if bad == 0 else 1


def cmd_run(args: argparse.Namespace) -> int:
    """F156 — walk every phase sequentially.

    Default gate      → exit 0 only when *all* checks are PASS
    (``--soft``)      → tolerate MISSING / WARN (fresh-bench safe),
                        still exit non-zero if any real FAIL surfaces
    """
    phases = _build_phases()
    total_bad  = 0   # PASS, MISSING, WARN, FAIL — anything non-PASS
    total_hard = 0   # only counts status == "FAIL"
    passed_phases = 0
    for phase in phases:
        bad, hard = _run_phase(phase)
        total_bad  += bad
        total_hard += hard
        if bad == 0:
            passed_phases += 1
    print()
    soft_non_fail = total_bad - total_hard
    if total_bad == 0:
        _ok(f"all {len(phases)} phases OK")
    else:
        _err(f"{total_bad} check(s) had issues across {len(phases)} phases "
             f"(hard FAIL={total_hard}, MISSING/WARN={soft_non_fail})")
    if args.soft:
        if total_hard == 0:
            _log(f"--soft: 0 hard FAILs across {passed_phases}/{len(phases)} "
                 f"passing phases → exit 0 (tolerated {soft_non_fail} "
                 f"MISSING/WARN)")
            return 0
        _err(f"--soft: {total_hard} hard FAIL(s) present → exit 1")
        return 1
    return 0 if total_bad == 0 else 1


def _run_phase(phase: Phase) -> Tuple[int, int]:
    """Run all checks for ``phase``.

    Returns ``(bad, hard_fails)``:

    * ``bad``        — 0 if every check returned ``PASS``, otherwise the
      number of non-``PASS`` checks (PASS, MISSING, WARN, FAIL).
    * ``hard_fails`` — 0 if no check returned ``FAIL``; only ``FAIL``
      counts toward this counter (a fresh bench may have MISSING/WARN
      but should never have FAIL).

    Callers decide what to do with the two numbers; ``cmd_check`` exits
    non-zero when ``bad != 0``; ``cmd_run --soft`` exits non-zero only
    when ``hard_fails != 0``.
    """
    width = max(len(c.label) for c in phase.checks) if phase.checks else 0
    print(f"\n— {phase.pid}  {phase.name} —")
    print(f"   note: {phase.notes}")
    bad = 0
    hard = 0
    if not phase.checks:
        print(f"   ({phase.pid} has no file-bound checks — judged by "
              f"the presence of: {phase.expected or ['(none)']})")
    for c in phase.checks:
        status, note = c.run(c.path)
        if status not in ("PASS",):
            bad += 1
        if status == "FAIL":
            hard += 1
        flag = {"PASS": "OK ", "FAIL": "!! ",
                "MISSING": ".. ", "WARN": "?? "}.get(status, "?? ")
        print(f"   [{flag}] {c.label:<{width}}  {note}")
    return (bad, hard)


def cmd_seed(args: argparse.Namespace) -> int:
    """F154 — seed a tiny demo ``log.db`` so `run` has data to inspect."""
    data = _data_dir()
    data.mkdir(parents=True, exist_ok=True)
    db = data / "log.db"
    if db.exists() and not args.force:
        _err(f"{db} already exists — pass --force to overwrite")
        return 1
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE IF NOT EXISTS topic_logs "
                    "(ts REAL NOT NULL, topic TEXT NOT NULL, "
                    "source TEXT, payload_text TEXT)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_ts ON topic_logs(ts)")
        for ts, topic, source, text in [
            (1_700_000_000.0, "/battery/state", "tank_health",
             '{"voltage_mV": 11900, "pct": 0.84}'),
            (1_700_000_005.0, "/emotion/state", "tank_assistant",
             '{"valence": 0.7, "arousal": 0.4, "label": "happy"}'),
            (1_700_000_010.0, "/wake_detected", "tank_speech",
             '{"confidence": 0.91}'),
            (1_700_000_015.0, "/security/events/motion",
             "tank_security", '{"label": "person"}'),
        ]:
            con.execute("INSERT INTO topic_logs VALUES (?,?,?,?)",
                        (ts, topic, source, text))
    _ok(f"seeded {db} with 4 sample rows")
    return 0


# ---------------------------------------------------------------------------
# CLI plumbing
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Phase runner for The Tank Project (each log, one by one).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("phases", help="List every registered phase")

    pl = sub.add_parser("logs", help="List data/ contents with sizes")
    pl.add_argument("--limit", type=int, default=200)

    px = sub.add_parser("examine", help="Peek into a single file")
    px.add_argument("path")
    px.add_argument("--head", type=int, default=5)

    pc = sub.add_parser("check", help="Run the checks for one phase")
    pc.add_argument("phase")

    prun = sub.add_parser("run", help="Walk every phase sequentially")
    prun.add_argument("--soft", action="store_true",
                      help="tolerate MISSING/WARN (fresh-bench safe); "
                           "still exit non-zero if any real FAIL surfaces")

    ps = sub.add_parser("seed",
                        help="Seed a tiny demo log.db so run has data")
    ps.add_argument("--force", action="store_true",
                    help="overwrite existing log.db")
    return p


HANDLERS = {
    "phases":  cmd_phases,
    "logs":    cmd_logs,
    "examine": cmd_examine,
    "check":   cmd_check,
    "run":     cmd_run,
    "seed":    cmd_seed,
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
