#!/usr/bin/env python3
"""discover.py — search everywhere + learn from GitHub in one command.

Combines search_everything (torrent, YouTube, web, GitHub) with
ai_github_learner (README extraction, MemoryManager storage).
One command to find AND understand.

Usage:
  python3 scripts/discover.py "sms bomber"
  python3 scripts/discover.py --topic "video downloader" --limit 5
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

PREFIX = "[discover]"
SCRIPTS_DIR = Path(__file__).resolve().parent
SEARCH_SCRIPT = SCRIPTS_DIR / "search_everything.py"
LEARN_SCRIPT = SCRIPTS_DIR / "ai_github_learner.py"


def _info(msg: str) -> None:
    print(f"{PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{PREFIX} ✅ {msg}", flush=True)


def _sep() -> None:
    print(f"\n  {'─'*56}")


def discover(topic: str, limit: int = 5) -> None:
    """Search + learn in one shot."""
    print(f"\n  🔮 Discover: '{topic}'")
    print(f"  {'═'*56}")

    start = time.time()
    search_ok = False
    learn_ok = False

    # ── Step 1: Search everywhere ──
    print(f"\n  🔍 PHASE 1: Searching everywhere...")
    _sep()
    try:
        subprocess.run(
            ["python3", str(SEARCH_SCRIPT), "--all", "--limit", str(limit), topic],
            timeout=60,
        )
        search_ok = True
    except subprocess.TimeoutExpired:
        _info("⚠ Search timed out")
    except Exception as e:
        _info(f"⚠ Search failed: {e}")

    # ── Step 2: Learn from GitHub ──
    print(f"\n  🧠 PHASE 2: Learning from GitHub...")
    _sep()
    try:
        subprocess.run(
            ["python3", str(LEARN_SCRIPT), "--topic", topic, "--limit", str(limit)],
            timeout=60,
        )
        learn_ok = True
    except subprocess.TimeoutExpired:
        _info("⚠ Learning timed out")
    except Exception as e:
        _info(f"⚠ Learning failed: {e}")

    elapsed = time.time() - start

    # ── Summary ──
    print(f"\n  {'═'*56}")
    status = []
    if search_ok: status.append("✅ Search")
    else: status.append("⚠ Search failed")
    if learn_ok: status.append("✅ Learn")
    else: status.append("⚠ Learn failed")
    print(f"  {' | '.join(status)} in {elapsed:.0f}s")
    print(f"  📂 Knowledge saved to tank_ws/data/learned_scripts/")
    print(f"  📋 Search logs:   tank_ws/data/search_logs/")
    print(f"  💡 Query: discover --query '{topic}'")
    print(f"  {'═'*56}\n")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="discover",
        description="Discover — search everywhere + learn from GitHub in one command.",
    )
    p.add_argument("query", nargs="?", default="", help="Topic to discover")
    p.add_argument("--topic", "-t", default="", help="Topic alias")
    p.add_argument("--limit", "-l", type=int, default=5, help="Max results (default: 5)")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    topic = args.query or args.topic
    if not topic:
        print("  Usage: discover <topic>")
        print("  Example: discover sms bomber")
        print("           discover 'video downloader'")
        return 0

    discover(topic, limit=args.limit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
