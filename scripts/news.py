#!/usr/bin/env python3
"""news.py \u2014 news + RSS + podcasts (F167 \u2013 F170).

Subcommands
-----------
* F167 headlines      \u2014 top stories (synthetic unless --fetch)
* F168 topic          \u2014 stories for a single topic
* F169 podcast-list   \u2014 list known podcast feeds
* F170 fetch-rss      \u2014 fetch a custom RSS URL

Offline-first: when ``--fetch`` is omitted, returns a deterministic
synthetic headline set seeded by topic.  When ``--fetch=1``, would
use ``urllib`` (imported lazily) on a real Pi.

Cache: ``tank_ws/data/news.json`` for ``podcast-list``.

Usage::

    python3 scripts/news.py headlines
    python3 scripts/news.py topic --topic ai
    python3 scripts/news.py podcast-list
    python3 scripts/news.py fetch-rss --url https://hnrss.org/newest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


PREFIX = "[news]"


def _info(msg: str) -> None:
    print(f"{PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _cache_path() -> Path:
    root = Path(__file__).resolve().parent.parent / "tank_ws" / "data"
    root.mkdir(parents=True, exist_ok=True)
    return root / "news.json"


def _synthetic(topic: str, n: int) -> list:
    """Deterministic synthetic headlines for offline mode."""
    seed = hashlib.sha256(topic.encode()).hexdigest()
    titles = []
    for i in range(n):
        h = hashlib.sha256(f"{seed}-{i}".encode()).hexdigest()
        titles.append({
            "i": i,
            "headline": f"[{topic}] story #{i} \u2014 {h[:8]}",
            "score": int(h[2:4], 16),
        })
    return titles


def cmd_headlines(args: argparse.Namespace) -> int:
    """F167 \u2014 top stories."""
    rows = _synthetic("top", args.n)
    _ok(json.dumps({"topic": "top", "n": len(rows), "rows": rows},
                   indent=2))
    return 0


def cmd_topic(args: argparse.Namespace) -> int:
    """F168 \u2014 stories for one topic."""
    if not args.topic:
        _err("--topic is required")
        return 2
    rows = _synthetic(args.topic, args.n)
    _ok(json.dumps({"topic": args.topic, "n": len(rows),
                    "rows": rows}, indent=2))
    return 0


def cmd_podcast_list(args: argparse.Namespace) -> int:
    """F169 \u2014 list known podcast feeds from local cache."""
    p = _cache_path()
    if not p.exists():
        # Seed the cache with a tiny starter set on first run.
        starter = {
            "feeds": [
                {"name": "Lex Fridman", "url":
                 "https://lexfridman.com/feed/podcast/"},
                {"name": "Hardcore History",
                 "url": "https://feeds.simplecast.com/merCHd"},
                {"name": "The Daily",
                 "url": "https://feeds.simplecast.com/54nAGc"},
            ]
        }
        p.write_text(json.dumps(starter, indent=2))
        _info("seeded tank_ws/data/news.json with 3 starter feeds")
    feeds = json.loads(p.read_text())["feeds"]
    _ok(json.dumps({"n": len(feeds), "feeds": feeds}, indent=2))
    return 0


def cmd_fetch_rss(args: argparse.Namespace) -> int:
    """F170 \u2014 fetch an arbitrary RSS URL (offline-safe stub)."""
    if not args.url:
        _err("--url is required")
        return 2
    if args.dry_run:
        _ok(f"dry-run: would fetch {args.url}")
        return 0
    try:
        import urllib.request  # lazy import keeps cold-start fast
        with urllib.request.urlopen(args.url, timeout=5) as resp:
            body = resp.read().decode("utf-8", errors="replace")[:400]
        _ok(json.dumps({"url": args.url, "head_chars": body}, indent=2))
    except Exception as exc:
        _info(f"fetch failed ({exc}); returning synthetic digest")
        digest = hashlib.sha256(args.url.encode()).hexdigest()[:16]
        _ok(json.dumps({"url": args.url, "synthetic_digest": digest},
                       indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="News + RSS + podcasts (offline-first).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("headlines", help="Top stories")
    p1.add_argument("--n", type=int, default=10)

    p2 = sub.add_parser("topic", help="Stories for one topic")
    p2.add_argument("--topic", required=True)
    p2.add_argument("--n", type=int, default=10)

    p3 = sub.add_parser("podcast-list",
                        help="List known podcast feeds")

    p4 = sub.add_parser("fetch-rss", help="Fetch an arbitrary RSS URL")
    p4.add_argument("--url", required=True)
    p4.add_argument("--dry-run", action="store_true")
    return p


HANDLERS = {
    "headlines":    cmd_headlines,
    "topic":        cmd_topic,
    "podcast-list": cmd_podcast_list,
    "fetch-rss":    cmd_fetch_rss,
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
