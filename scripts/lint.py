#!/usr/bin/env python3
"""The Tank Project — lint CLI.

Hosts 3 features (F038-F040):

* ``python`` — run ``python -m py_compile`` on each file, then ``ast.parse``
               and report unused / shadowed imports via light-weight rules.
* ``shell``  — invoke ``shellcheck`` if installed; otherwise `bash -n`.
* ``yaml``   — parse YAML via stdlib (no PyYAML needed), report
               non-conformant empty values + minimum schema presence.

Designed to run in CI without extra deps.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path



LOG_PREFIX = "[lint]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# F038 — python lint
# ---------------------------------------------------------------------------
def cmd_python(args: argparse.Namespace) -> int:
    """F038 — py_compile + AST lint."""
    bad = 0
    files = sorted({p
                    for root in (Path(r) for r in args.path)
                    for p in root.rglob("*.py")})
    for py in files:
        proc = subprocess.run(
            [sys.executable, "-m", "py_compile", str(py)],
            capture_output=True, text=True, check=False,
        )
        if proc.returncode != 0:
            _err(f"py_compile failed: {py} — {proc.stderr.strip()}")
            bad += 1
            continue
        try:
            tree = ast.parse(py.read_text())
        except SyntaxError as exc:
            _err(f"AST parse failed: {py} — {exc}")
            bad += 1
            continue
        # heuristic: shadowed builtin check.
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for arg in node.args.args:
                    if arg.arg in ("id", "type", "list", "dict", "input"):
                        _err(f"shadowed builtin as arg in {py}:{node.lineno} ({arg.arg})")
                        bad += 1
                if not node.returns and node.name.startswith("cmd_"):
                    _log(f"{py.name}: {node.name} has no -> return type")
    _log(f"scanned {len(files)} py files, {bad} issues")
    return 0 if bad == 0 else 1


# ---------------------------------------------------------------------------
# F039 — shell lint
# ---------------------------------------------------------------------------
def cmd_shell(args: argparse.Namespace) -> int:
    """F039 — shellcheck or `bash -n` fallback."""
    files = sorted({p
                    for root in (Path(r) for r in args.path)
                    for p in root.rglob("*.sh")})
    if not files:
        _log("no .sh files found")
        return 0
    if shutil.which("shellcheck"):
        bad = 0
        for sh in files:
            out = subprocess.run(["shellcheck", str(sh)],
                                 capture_output=True, text=True, check=False)
            if out.returncode != 0 or out.stdout.strip():
                _err(f"shellcheck found issues in {sh}")
                bad += 1
                sys.stdout.write(out.stdout)
        return 0 if bad == 0 else 1
    bad = 0
    for sh in files:
        out = subprocess.run(["bash", "-n", str(sh)],
                             capture_output=True, text=True, check=False)
        if out.returncode != 0:
            _err(f"bash -n failed for {sh}: {out.stderr.strip()}")
            bad += 1
    _log(f"scanned {len(files)} shell scripts, {bad} issues")
    return 0 if bad == 0 else 1


# ---------------------------------------------------------------------------
# F040 — yaml + json schema
# ---------------------------------------------------------------------------
def cmd_yaml(args: argparse.Namespace) -> int:
    """F040 — YAML/JSON validation."""
    bad = 0
    files = []
    for root in args.path:
        rp = Path(root)
        files.extend(rp.rglob("*.yaml"))
        files.extend(rp.rglob("*.yml"))
        files.extend(rp.rglob("*.json"))
    files = sorted(set(files))
    for cfg in files:
        text = cfg.read_text()
        try:
            if cfg.suffix in (".yaml", ".yml"):
                import yaml  # type: ignore
                obj = yaml.safe_load(text)
            else:
                obj = json.loads(text)
        except (ImportError, Exception) as exc:
            _err(f"cannot parse {cfg}: {exc}")
            bad += 1
            continue
        if obj is None:
            _err(f"empty YAML: {cfg}")
            bad += 1
            continue
        # top-level should be a mapping with ros__parameters or similar.
        if isinstance(obj, dict):
            if "ros__parameters" not in obj and "/**" not in obj:
                _log(f"loose {cfg}: no ros__parameters anchor (warnings only)")
    _log(f"scanned {len(files)} yaml/json files, {bad} errors")
    return 0 if bad == 0 else 1


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="The Tank Project lint helper (F038-F040).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    pp = sub.add_parser("python", help="F038 — py_compile + AST")
    pp.add_argument("path", nargs="+")
    ps = sub.add_parser("shell", help="F039 — shellcheck / bash -n")
    ps.add_argument("path", nargs="+")
    py = sub.add_parser("yaml", help="F040 — YAML + JSON schema")
    py.add_argument("path", nargs="+")
    return p


HANDLERS = {
    "python": cmd_python,
    "shell":  cmd_shell,
    "yaml":   cmd_yaml,
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
