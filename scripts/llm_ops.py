#!/usr/bin/env python3
"""The Tank Project — LLM operations CLI.

Hosts 4 features (F101-F104):

* ``token-budget``    — split a token budget across system / context / reply
* ``prompt-cache``    — derive a stable fingerprint for a prompt plan
* ``scheduler``       — parse + sanity-check a cron expression
* ``model-load``      — smoke test loading a GGUF model with llama-cpp

Stdlib-first; falls back to DRY mode if llama-cpp is missing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path



LOG_PREFIX = "[llm-ops]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# F101 — token-budget
# ---------------------------------------------------------------------------
def cmd_token_budget(args: argparse.Namespace) -> int:
    """F101 — token budget planner."""
    b = max(args.budget, 64)
    sys_part = max(args.system_share, 0.05)
    ctx_part = max(args.context_share, 0.1)
    rep_part = max(1.0 - sys_part - ctx_part, 0.05)
    plan = {
        "total":       b,
        "system_pct":  round(sys_part * 100, 1),
        "context_pct": round(ctx_part * 100, 1),
        "reply_pct":   round(rep_part * 100, 1),
        "system_tok":  int(b * sys_part),
        "context_tok": int(b * ctx_part),
        "reply_tok":   int(b * rep_part),
    }
    _ok(json.dumps(plan, indent=2))
    return 0


# ---------------------------------------------------------------------------
# F102 — prompt-cache fingerprint
# ---------------------------------------------------------------------------
def cmd_prompt_cache(args: argparse.Namespace) -> int:
    """F102 — prompt cache fingerprint."""
    parts = []
    for rule in args.rule.split("+"):
        rule = rule.strip().lower()
        if "system" in rule:
            parts.append("v1")
        elif "doc" in rule:
            parts.append("d")
        elif "summary" in rule:
            parts.append("s")
    fp_raw = f"{args.rule}|{args.cache_dir}|{args.budget}".encode()
    fp = "pc_" + hashlib.sha256(fp_raw).hexdigest()[:16]
    _ok(json.dumps({
        "rule":    args.rule,
        "parts":   parts,
        "fingerprint": fp,
    }, indent=2))
    return 0


# ---------------------------------------------------------------------------
# F103 — scheduler (cron parser)
# ---------------------------------------------------------------------------
def cmd_scheduler(args: argparse.Namespace) -> int:
    """F103 — sanity-check a cron expression (5 fields)."""
    expr = args.cron.strip().split()
    if len(expr) != 5:
        _err(f"cron needs 5 fields, got {len(expr)}")
        return 1
    names = ("minute", "hour", "dom", "month", "dow")
    ranges = ((0, 59), (0, 23), (1, 31), (1, 12), (0, 6))
    bad = []
    for name, value, (lo, hi) in zip(names, expr, ranges):
        if value == "*":
            continue
        for v in value.split(","):
            if "/" in v:
                v, step = v.split("/", 1)
                try:
                    int(step)
                except ValueError:
                    bad.append(f"{name} step {step!r}")
            if "-" in v:
                a, b = v.split("-", 1)
                try:
                    a, b = int(a), int(b)
                except ValueError:
                    bad.append(f"{name} range {v!r}")
                    continue
                if not (lo <= a <= hi and lo <= b <= hi):
                    bad.append(f"{name} range {v} out of [{lo},{hi}]")
            else:
                try:
                    n = int(v)
                except ValueError:
                    bad.append(f"{name} token {v!r}")
                    continue
                if not (lo <= n <= hi):
                    bad.append(f"{name}={n} out of [{lo},{hi}]")
    if bad:
        _err(f"cron malformed: {bad}")
        return 1
    _ok(f"cron OK: {args.cron!r}")
    return 0


# ---------------------------------------------------------------------------
# F104 — model-load
# ---------------------------------------------------------------------------
def cmd_model_load(args: argparse.Namespace) -> int:
    """F104 — model load smoke test."""
    p = Path(args.path)
    if not p.exists():
        _err(f"model missing: {p}")
        return 1
    try:
        size = p.stat().st_size
    except OSError as exc:
        _err(f"stat failed: {exc}")
        return 1
    if size < 1024 * 1024:
        _err(f"suspiciously small: {size} bytes")
        return 1
    try:
        from llama_cpp import Llama  # type: ignore
        if args.dry_run:
            _log(f"DRY: would Llama(model_path={p!r}, n_ctx={args.ctx})")
            return 0
        m = Llama(model_path=str(p), n_ctx=args.ctx, verbose=False)
        out = m("ping", max_tokens=4)
        _ok(f"loaded {p.name} — first 4 tokens = {out['choices'][0]['text']!r}")
    except ImportError:
        _log(f"llama-cpp missing — would load {p} (size {size // 1024**2} MB)")
    return 0


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="LLM ops CLI (F101-F104).")
    sub = p.add_subparsers(dest="cmd", required=True)

    pb = sub.add_parser("token-budget", help="F101 — token budget")
    pb.add_argument("--budget", type=int, default=4096)
    pb.add_argument("--system-share", type=float, default=0.15)
    pb.add_argument("--context-share", type=float, default=0.70)

    pc = sub.add_parser("prompt-cache", help="F102 — prompt cache fingerprint")
    pc.add_argument("--rule", default="system+doc+summary")
    pc.add_argument("--cache-dir", default="/tmp/pcache")
    pc.add_argument("--budget", type=int, default=4096)

    ps = sub.add_parser("scheduler", help="F103 — cron parser")
    ps.add_argument("--cron", required=True)

    pm = sub.add_parser("model-load", help="F104 — model load smoke")
    pm.add_argument("path")
    pm.add_argument("--ctx", type=int, default=2048)
    pm.add_argument("--dry-run", action="store_true")
    return p


HANDLERS = {
    "token-budget":  cmd_token_budget,
    "prompt-cache":  cmd_prompt_cache,
    "scheduler":     cmd_scheduler,
    "model-load":    cmd_model_load,
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
