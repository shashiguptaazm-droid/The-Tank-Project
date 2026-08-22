#!/usr/bin/env python3
"""torrent_search.py — Real torrent search & download via the Node.js torrent-search-api worker.

Searches across ThePirateBay, LimeTorrents, TorrentProject, EZTV using the
existing edulabs-torrent-cloud search worker. Results include magnet links
and can be auto-added to aria2.

Usage:
  python3 scripts/torrent_search.py "game of thrones"              # search all providers
  python3 scripts/torrent_search.py --provider ThePirateBay "got"  # specific provider
  python3 scripts/torrent_search.py --category TV "game of thrones"
  python3 scripts/torrent_search.py --add 3 "game of thrones"      # search + auto-add result #3
  python3 scripts/torrent_search.py --json "game of thrones"       # raw JSON output
  python3 scripts/torrent_search.py --interactive "game of thrones" # interactive picker
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PREFIX = "[torrent-search]"

ARIA2_RPC = os.environ.get("ARIA2_RPC", "http://127.0.0.1:6800/jsonrpc")
ARIA2_SECRET = os.environ.get("ARIA2_SECRET", "")
WORKER_PATH = "/opt/edulabs-torrent-cloud/torrent-search-worker.cjs"
DEFAULT_PROVIDERS = ["ThePirateBay", "Limetorrents", "TorrentProject", "Eztv"]
VALID_CATEGORIES = ["All", "Movies", "TV", "Games", "Music", "Applications", "Anime", "Books"]


def _ok(msg: str) -> int:
    print(f"{PREFIX} ✅ {msg}", flush=True)
    return 0


def _err(msg: str) -> int:
    print(f"{PREFIX} ❌ {msg}", file=sys.stderr, flush=True)
    return 1


def _info(msg: str) -> None:
    print(f"{PREFIX} {msg}", flush=True)


def _bytes_fmt(n: int | str) -> str:
    """Human-readable byte size from a torrent-search-api size string like '2.1 GB' or number."""
    if isinstance(n, str):
        return n
    if not n or n <= 0:
        return "?"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def search_provider(provider: str, query: str, category: str = "All", limit: int = 12) -> List[Dict[str, Any]]:
    """Search a single torrent provider via the Node.js worker."""
    if not os.path.exists(WORKER_PATH):
        _err(f"Worker not found: {WORKER_PATH}")
        return []

    try:
        result = subprocess.run(
            ["node", WORKER_PATH, "search", provider, query, category, str(limit)],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return []
        data = json.loads(result.stdout or "[]")
        if not isinstance(data, list):
            return []
        return data
    except subprocess.TimeoutExpired:
        return []
    except json.JSONDecodeError:
        return []
    except Exception:
        return []


def search_all(query: str, category: str = "All", limit: int = 12,
               providers: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Search across multiple providers, merge and deduplicate results."""
    if providers is None:
        providers = DEFAULT_PROVIDERS

    all_results: List[Dict[str, Any]] = []
    seen: set = set()
    failed: List[str] = []

    for provider in providers:
        results = search_provider(provider, query, category, limit)
        if results:
            count_before = len(all_results)
            for r in results:
                title = (r.get("title") or "").lower().strip()
                if title and title not in seen:
                    seen.add(title)
                    r["_provider"] = provider
                    all_results.append(r)
            _info(f"{provider}: {len(all_results) - count_before} new results")
        else:
            failed.append(provider)

    if failed:
        _info(f"Unavailable: {', '.join(failed)}")

    # Sort by seeders (desc), then size (desc)
    def _sort_key(r: Dict) -> tuple:
        seeds = r.get("seeds", 0)
        if isinstance(seeds, str):
            try:
                seeds = int(seeds)
            except (ValueError, TypeError):
                seeds = 0
        size = r.get("size", "")
        size_bytes = 0
        if isinstance(size, str):
            size_bytes = _parse_size_str(size)
        return (-(seeds if isinstance(seeds, int) else 0), -size_bytes)

    all_results.sort(key=_sort_key)
    return all_results


def _parse_size_str(s: str) -> int:
    """Parse '2.1 GB' style string to bytes."""
    s = s.strip().upper()
    multipliers = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
    for unit, mult in multipliers.items():
        if s.endswith(unit):
            try:
                return int(float(s[:-len(unit)].strip()) * mult)
            except (ValueError, TypeError):
                return 0
    try:
        return int(s)
    except (ValueError, TypeError):
        return 0


def get_magnet(torrent: Dict[str, Any]) -> str:
    """Extract magnet URI from a torrent result, trying multiple strategies."""
    magnet = torrent.get("magnet", "")
    if isinstance(magnet, str) and magnet.startswith("magnet:"):
        return magnet
    link = torrent.get("link", "")
    if isinstance(link, str) and link.startswith("magnet:"):
        return link
    desc = torrent.get("desc", "")
    if isinstance(desc, str) and "magnet:" in desc:
        import re
        match = re.search(r'magnet:\?[^\s"\'<>]+', desc)
        if match:
            return match.group(0)
    return ""


def get_download_uri(torrent: Dict[str, Any]) -> Tuple[str, str]:
    """Get (uri, kind) from a torrent result. Kind is 'magnet', 'torrent', or ''."""
    magnet = get_magnet(torrent)
    if magnet:
        return (magnet, "magnet")
    link = torrent.get("link", "")
    if isinstance(link, str) and (link.endswith(".torrent") or "/torrent/" in link):
        return (link, "torrent")
    return ("", "")


def aria2_add_uri(uri: str, label: str = "", download_dir: str = "") -> Optional[str]:
    """Add a magnet URI or .torrent URL to aria2 via JSON-RPC. Returns GID or None."""
    import uuid as _uuid

    if not uri:
        _err("Empty URI")
        return None

    try:
        if not ARIA2_SECRET:
            payload: Dict[str, Any] = {
                "jsonrpc": "2.0",
                "id": str(_uuid.uuid4())[:8],
                "method": "aria2.addUri",
                "params": [[uri]],
            }
        else:
            payload = {
                "jsonrpc": "2.0",
                "id": str(_uuid.uuid4())[:8],
                "method": "aria2.addUri",
                "params": [f"token:{ARIA2_SECRET}", [uri]],
            }

        if download_dir:
            payload["params"].append({"dir": download_dir})

        req = urllib.request.Request(
            ARIA2_RPC,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())

        if "error" in result:
            _err(f"aria2 error: {result['error'].get('message', result['error'])}")
            return None

        gid = result.get("result", "")
        label_str = f" ({label[:60]})" if label else ""
        uri_type = "magnet" if uri.startswith("magnet:") else "torrent"
        _ok(f"Added to aria2 ({uri_type}): GID={gid}{label_str}")
        return str(gid)
    except urllib.error.URLError as e:
        _err(f"Cannot reach aria2 at {ARIA2_RPC}: {e}")
        return None
    except Exception as e:
        _err(f"aria2 add failed: {e}")
        return None


def display_results(results: List[Dict[str, Any]], start_idx: int = 1) -> None:
    """Pretty-print torrent search results as a numbered list."""
    if not results:
        print("\n  📭 No results found.\n")
        return

    print()
    print(f"  {'#':<4} {'Title':<45} {'Size':<10} {'S/L':<12} {'Provider'}")
    print(f"  {'─'*4} {'─'*45} {'─'*10} {'─'*12} {'─'*15}")

    for i, r in enumerate(results):
        title = (r.get("title") or "?").strip()[:43]
        size = r.get("size", "?")
        seeds = r.get("seeds", "?")
        leeches = r.get("peers", "?")
        provider = r.get("_provider", r.get("provider", "?"))[:13]
        if isinstance(size, (int, float)):
            size = _bytes_fmt(int(size))
        print(f"  {i + start_idx:<4} {title:<45} {str(size):<10} "
              f"{str(seeds)}/{str(leeches):<9} {provider}")
    print()


def interactive_picker(query: str, category: str = "All",
                       providers: Optional[List[str]] = None) -> int:
    """Search, display interactive picker, and add selected result to aria2.

    Returns 0 on success, 1 on failure/cancel.
    """
    _info(f"Searching for: '{query}' ({category})...")
    results = search_all(query, category=category, limit=20, providers=providers)

    if not results:
        print("\n  📭 No torrents found. Try different keywords.\n")
        return 1

    display_results(results)

    while True:
        try:
            choice = input(
                f"  🎯 Pick a number (1-{len(results)}) or [q]uit: "
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  (cancelled)\n")
            return 1

        if choice in ("q", "quit", "exit", ""):
            print("  (cancelled)\n")
            return 1

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(results):
                break
            print(f"  ❌ Enter 1-{len(results)} or 'q' to quit.")
        except ValueError:
            print(f"  ❌ Enter a number (1-{len(results)}) or 'q' to quit.")

    chosen = results[idx]
    title = (chosen.get("title") or "Untitled")[:100]
    uri, kind = get_download_uri(chosen)

    print(f"\n  📥 Selected: {title}")

    if not uri:
        print("  ⚠ No magnet/torrent link found for this result.")
        print(f"  Link: {chosen.get('link', chosen.get('desc', 'unknown'))}")
        print("  Try adding manually via the web UI.\n")
        return 1

    gid = aria2_add_uri(uri, label=title)
    if gid:
        print("  🚀 Download started! Track with: simple-internet active\n")
        return 0
    else:
        print(f"  🔗 URI: {uri[:80]}...")
        print(f'  Add manually: simple-internet download "{uri}"\n')
        return 1


# ── CLI argument parser ─────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="torrent-search",
        description="Search torrent sites and optionally add results to aria2.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  torrent-search "game of thrones"
  torrent-search --provider ThePirateBay --category TV "got s01"
  torrent-search --interactive "ubuntu 24.04"
  torrent-search --json "debian iso"
  torrent-search --add 1 "game of thrones s08e01"
        """,
    )
    p.add_argument("query", nargs="?", default="", help="Search query")
    p.add_argument("--provider", "-p", default="",
                   help=f"Torrent provider (default: all). Options: {', '.join(DEFAULT_PROVIDERS)}")
    p.add_argument("--category", "-c", default="All",
                   help=f"Category filter. Options: {', '.join(VALID_CATEGORIES)}")
    p.add_argument("--limit", "-l", type=int, default=15, help="Max results per provider")
    p.add_argument("--json", "-j", action="store_true", help="Output raw JSON")
    p.add_argument("--interactive", "-i", action="store_true", help="Interactive picker mode")
    p.add_argument("--add", "-a", type=int, metavar="N",
                   help="Search and auto-add result #N to aria2 (1-indexed)")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if not args.query:
        build_parser().print_help()
        return 0

    providers = [args.provider] if args.provider else DEFAULT_PROVIDERS

    # ── JSON mode: just dump results ──
    if args.json:
        results = search_all(args.query, category=args.category,
                            limit=args.limit, providers=providers)
        for r in results:
            if not r.get("magnet"):
                r["magnet"] = get_magnet(r)
        print(json.dumps(results, indent=2, default=str))
        return 0

    # ── Auto-add mode ──
    if args.add is not None:
        results = search_all(args.query, category=args.category,
                            limit=max(args.add, args.limit), providers=providers)
        if not results:
            _err("No results found")
            return 1
        idx = args.add - 1
        if idx < 0 or idx >= len(results):
            _err(f"Index {args.add} out of range (1-{len(results)})")
            return 1
        chosen = results[idx]
        uri, kind = get_download_uri(chosen)
        if not uri:
            _err(f"No magnet/torrent link for result #{args.add}")
            return 1
        title = (chosen.get("title") or "Untitled")[:100]
        gid = aria2_add_uri(uri, label=title)
        return 0 if gid else 1

    # ── Interactive mode ──
    if args.interactive:
        return interactive_picker(args.query, category=args.category, providers=providers)

    # ── Default: search and display ──
    results = search_all(args.query, category=args.category,
                        limit=args.limit, providers=providers)
    display_results(results)
    return 0


if __name__ == "__main__":
    sys.exit(main())
