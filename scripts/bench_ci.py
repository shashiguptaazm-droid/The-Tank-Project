#!/usr/bin/env python3
"""The Tank Project — bench / CI helpers.

Hosts 3 features (F082-F084):

* ``bench-runner``  — execute a YAML-declared test suite, summarise results
* ``complexity``    — print cyclomatic complexity (heuristic) per .py file
* ``doc-coverage``  — per-package % of public functions with a docstring
"""
from __future__ import annotations

import argparse
import ast
import json
import shlex
import subprocess
import sys
from pathlib import Path



LOG_PREFIX = "[bench-ci]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# F082 — bench-runner
# ---------------------------------------------------------------------------
def cmd_bench_runner(args: argparse.Namespace) -> int:
    """F082 — bench runner."""
    try:
        import yaml  # type: ignore
    except ImportError:
        _err("PyYAML missing")
        return 1
    suite_path = Path(args.suite)
    if not suite_path.exists():
        _err(f"suite missing: {suite_path}")
        return 1
    suite = yaml.safe_load(suite_path.read_text()) or {}
    cases = suite.get("cases", [])
    if not cases:
        _err("suite has no cases")
        return 1
    passed, failed = 0, 0
    for case in cases:
        cmd = case.get("cmd")
        if not cmd:
            failed += 1
            _err(f"case missing `cmd`: {case.get('name','?')}")
            continue
        # Use shlex + list argv so a malformed cmd can't spawn a shell.
        try:
            argv = shlex.split(cmd)
        except ValueError as exc:
            failed += 1
            _err(f"could not shlex.split({cmd!r}): {exc}")
            continue
        if not argv:
            failed += 1
            _err(f"empty cmd after split: {case.get('name','?')}")
            continue
        rc = subprocess.call(argv)
        if rc == 0:
            passed += 1
        else:
            failed += 1
    _ok(json.dumps({"passed": passed, "failed": failed,
                    "total": len(cases)}, indent=2))
    return 0 if failed == 0 else 1


# ---------------------------------------------------------------------------
# F083 — complexity
# ---------------------------------------------------------------------------
def cmd_complexity(args: argparse.Namespace) -> int:
    """F083 — cyclomatic complexity (heuristic)."""
    files = sorted({p for root in args.path for p in Path(root).rglob("*.py")})
    big = []
    for py in files:
        try:
            tree = ast.parse(py.read_text())
        except SyntaxError as exc:
            _err(f"AST parse failed: {py} ({exc})")
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                n_edges, n_nodes = 1, 1
                for child in ast.walk(node):
                    if isinstance(child, (ast.If, ast.For, ast.While,
                                          ast.ExceptHandler, ast.With,
                                          ast.BoolOp, ast.IfExp,
                                          ast.Assert, ast.Try)):
                        if isinstance(child, ast.BoolOp):
                            n_edges += max(len(child.values) - 1, 0)
                        else:
                            n_edges += 1
                    if isinstance(child, ast.FunctionDef):
                        pass
                cyclomatic = n_edges - n_nodes + 2
                if cyclomatic >= args.threshold:
                    big.append({"file": str(py),
                                "function": node.name,
                                "complexity": cyclomatic})
    big.sort(key=lambda r: -r["complexity"])
    _ok(json.dumps({"threshold": args.threshold, "top": big[:args.top]}, indent=2))
    return 0


# ---------------------------------------------------------------------------
# F084 — doc-coverage
# ---------------------------------------------------------------------------
def cmd_doc_coverage(args: argparse.Namespace) -> int:
    """F084 — docstring coverage."""
    files = sorted({p for root in args.path for p in Path(root).rglob("*.py")})
    total = 0; covered = 0
    by_file = []
    for py in files:
        try:
            tree = ast.parse(py.read_text())
        except SyntaxError:
            continue
        f_total = 0; f_covered = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.ClassDef)):
                if node.name.startswith("_") and not args.include_private:
                    continue
                f_total += 1
                if ast.get_docstring(node):
                    f_covered += 1
        if f_total:
            by_file.append({"file": str(py),
                            "covered": f_covered,
                            "total": f_total,
                            "pct": round(100 * f_covered / f_total, 1)})
            total += f_total; covered += f_covered
    pct = round(100 * covered / max(total, 1), 1)
    _ok(json.dumps({"overall_pct": pct,
                    "covered": covered, "total": total,
                    "by_file": by_file[:args.top]}, indent=2))
    return 0


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Bench / CI helpers (F082-F084).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    pb = sub.add_parser("bench-runner", help="F082 — bench runner")
    pb.add_argument("--suite", required=True)
    pc = sub.add_parser("complexity", help="F083 — complexity")
    pc.add_argument("path", nargs="+")
    pc.add_argument("--threshold", type=int, default=10)
    pc.add_argument("--top", type=int, default=20)
    pd = sub.add_parser("doc-coverage", help="F084 — doc coverage")
    pd.add_argument("path", nargs="+")
    pd.add_argument("--include-private", action="store_true")
    pd.add_argument("--top", type=int, default=20)
    return p


HANDLERS = {
    "bench-runner": cmd_bench_runner,
    "complexity":   cmd_complexity,
    "doc-coverage": cmd_doc_coverage,
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
