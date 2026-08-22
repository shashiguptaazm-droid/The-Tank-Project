#!/usr/bin/env python3
"""The Tank Project — gamma lint (deep static lint pass).

Hosts 2 features (F085-F086):

* ``func-len``     — flag functions longer than `--max` lines
* ``dead-imports`` — find imports that are never referenced in the body
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path



LOG_PREFIX = "[gamma-lint]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# F085 — func-len
# ---------------------------------------------------------------------------
def cmd_func_len(args: argparse.Namespace) -> int:
    """F085 — function-length lint."""
    bad = 0
    files = sorted({p for root in args.path for p in Path(root).rglob("*.py")})
    for py in files:
        try:
            tree = ast.parse(py.read_text())
        except SyntaxError as exc:
            _err(f"parse failed: {py} ({exc})")
            bad += 1
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.body:
                    continue
                start = node.body[0].lineno
                end = getattr(node, "end_lineno", start)
                length = end - start + 1
                if length > args.max:
                    _err(f"{py}:{start} {node.name} = {length} lines "
                         f"(> {args.max})")
                    bad += 1
    _log(f"{bad} function(s) longer than {args.max} lines")
    return 0 if bad == 0 else 1


# ---------------------------------------------------------------------------
# F086 — dead-imports
# ---------------------------------------------------------------------------
def cmd_dead_imports(args: argparse.Namespace) -> int:
    """F086 — dead-imports detector."""
    files = sorted({p for root in args.path for p in Path(root).rglob("*.py")})
    bad = 0
    for py in files:
        text = py.read_text()
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        body = "\n".join(text.splitlines())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name.split(".")[0]
                    if name not in body:
                        _err(f"{py}: unused `import {alias.name}`")
                        bad += 1
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name = alias.asname or alias.name
                    if name not in body:
                        _err(f"{py}: unused `from {node.module} import {alias.name}`")
                        bad += 1
    _log(f"{bad} potentially dead import(s)")
    return 0 if bad == 0 else 1


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Gamma lint (F085-F086).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    pf = sub.add_parser("func-len", help="F085 — function-length lint")
    pf.add_argument("path", nargs="+")
    pf.add_argument("--max", type=int, default=60)
    pd = sub.add_parser("dead-imports", help="F086 — dead imports")
    pd.add_argument("path", nargs="+")
    return p


HANDLERS = {
    "func-len":     cmd_func_len,
    "dead-imports": cmd_dead_imports,
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
