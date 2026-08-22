#!/usr/bin/env python3
"""search_everything.py — Universal search across torrents, YouTube, web, and GitHub.

One command to search everywhere and keep a detailed log of all results.
Results are saved to tank_ws/data/search_logs/ with timestamps for audit trail.

Usage:
  python3 scripts/search_everything.py "game of thrones"          # search all sources
  python3 scripts/search_everything.py --torrent "ubuntu iso"     # torrent only
  python3 scripts/search_everything.py --youtube "tutorial"       # YouTube only
  python3 scripts/search_everything.py --web "NVIDIA Jetson"       # web search only
  python3 scripts/search_everything.py --github "aria2"           # GitHub repos
  python3 scripts/search_everything.py --interactive "debian"     # picker mode
  python3 scripts/search_everything.py --history                  # view search log
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

PREFIX = "[search-everything]"
LOG_DIR = Path(__file__).resolve().parent.parent / "tank_ws" / "data" / "search_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Reuse our existing torrent search
TORRENT_SEARCH_SCRIPT = Path(__file__).resolve().parent / "torrent_search.py"


def _info(msg: str) -> None:
    print(f"{PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{PREFIX} ✅ {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{PREFIX} ❌ {msg}", file=sys.stderr, flush=True)





# ═══════════════════════════════════════════════════════════════════════
# Search Sources
# ═══════════════════════════════════════════════════════════════════════

def search_torrents(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search torrents via the existing Node.js worker."""
    if not TORRENT_SEARCH_SCRIPT.exists():
        _err("torrent_search.py not found — torrent search unavailable")
        return []

    try:
        result = subprocess.run(
            ["python3", str(TORRENT_SEARCH_SCRIPT), "--json", "--limit", str(limit), query],
            capture_output=True, text=True, timeout=30,
        )
        # Strip [torrent-search] log lines, keep JSON content
        clean = "\n".join(
            line for line in result.stdout.split("\n")
            if not line.strip().startswith("[torrent")
        )
        data = json.loads(clean.strip())
        if isinstance(data, list):
            for item in data:
                item["source"] = "torrent"
                item["_provider"] = item.get("_provider", item.get("provider", "unknown"))
            return data[:limit]
        return []
    except Exception as e:
        _err(f"Torrent search failed: {e}")
        return []


def search_youtube(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Search YouTube via yt-dlp."""
    results = []
    try:
        import yt_dlp
        ydl_opts = {"quiet": True, "no_warnings": True, "extract_flat": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
            if info and "entries" in info:
                for entry in info["entries"][:limit]:
                    if entry:
                        results.append({
                            "source": "youtube",
                            "title": entry.get("title", "?"),
                            "url": f"https://youtube.com/watch?v={entry.get('id', '')}",
                            "duration": entry.get("duration", 0),
                            "uploader": entry.get("uploader", ""),
                            "views": entry.get("view_count", 0),
                        })
    except ImportError:
        _err("yt-dlp not installed — YouTube search unavailable")
    except Exception as e:
        _err(f"YouTube search failed: {e}")
    return results


def search_web(query: str, limit: int = 8) -> List[Dict[str, Any]]:
    """Search the web via DuckDuckGo (using ddgs library)."""
    results = []
    try:
        from ddgs import DDGS
        for r in DDGS().text(query, max_results=limit):
            results.append({
                "source": "web",
                "title": r.get("title", "?"),
                "url": r.get("href", ""),
                "body": (r.get("body") or "")[:200],
            })
    except ImportError:
        _err("ddgs not installed — web search unavailable. Run: pip install ddgs")
    except Exception as e:
        _err(f"Web search failed: {e}")
    return results


def search_github(query: str, limit: int = 8) -> List[Dict[str, Any]]:
    """Search GitHub repositories via the GitHub API (no auth needed for public)."""
    results = []
    try:
        api_url = (
            f"https://api.github.com/search/repositories"
            f"?q={urllib.parse.quote(query)}&sort=stars&order=desc&per_page={limit}"
        )
        req = urllib.request.Request(
            api_url,
            headers={
                "User-Agent": "TankOS/2.0",
                "Accept": "application/vnd.github.v3+json",
                **({"Authorization": f"token {os.environ['GITHUB_TOKEN']}"}
                   if os.environ.get("GITHUB_TOKEN") else {}),
            },
        )
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())

        for item in data.get("items", [])[:limit]:
            results.append({
                "source": "github",
                "title": item.get("full_name", "?"),
                "url": item.get("html_url", ""),
                "description": (item.get("description") or "")[:200],
                "stars": item.get("stargazers_count", 0),
                "language": item.get("language", ""),
                "updated": item.get("updated_at", ""),
            })
    except Exception as e:
        _err(f"GitHub search failed: {e}")
    return results


# ═══════════════════════════════════════════════════════════════════════
# Logging
# ═══════════════════════════════════════════════════════════════════════

def _cleanup_old_logs(keep: int = 500) -> None:
    """Keep only the most recent N log files to prevent disk filling."""
    logs = sorted(LOG_DIR.glob("search_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in logs[keep:]:
        try:
            old.unlink()
        except OSError:
            pass


def log_search(query: str, results: Dict[str, List[Dict[str, Any]]], duration_ms: float) -> str:
    """Save search results to a timestamped log file. Returns the log path."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"search_{timestamp}_{query[:30].replace(' ', '_')}.json"

    total = sum(len(v) for v in results.values())

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "duration_ms": round(duration_ms, 1),
        "total_results": total,
        "results_by_source": {
            source: {
                "count": len(items),
                "items": items,
            }
            for source, items in results.items()
        },
    }

    log_file.write_text(json.dumps(log_entry, indent=2, default=str))
    _ok(f"Log saved: {log_file.name} ({total} results)")

    # Also append to master CSV log
    csv_log = LOG_DIR / "search_master_log.csv"
    if not csv_log.exists():
        csv_log.write_text("timestamp,query,source,count,duration_ms\n")
    with open(csv_log, "a") as f:
        for source, items in results.items():
            f.write(f"{datetime.now().isoformat()},{query},{source},{len(items)},{duration_ms:.0f}\n")

    # Rotate old logs
    _cleanup_old_logs()

    return str(log_file)


def view_history(limit: int = 20) -> None:
    """View recent search logs."""
    logs = sorted(LOG_DIR.glob("search_*.json"), reverse=True)[:limit]
    if not logs:
        print("  📭 No search logs found.")
        return

    print(f"\n  📋 Recent Search History ({min(len(logs), limit)} entries):\n")
    print(f"  {'Time':<20} {'Query':<35} {'Results':<10} {'File'}")
    print(f"  {'─'*20} {'─'*35} {'─'*10} {'─'*25}")

    for log in logs:
        try:
            data = json.loads(log.read_text())
            ts = data.get("timestamp", "")[:19].replace("T", " ")
            query = (data.get("query", "") or log.stem)[:33]
            total = data.get("total_results", "?")
            print(f"  {ts:<20} {query:<35} {str(total):<10} {log.name[:23]}")
        except Exception:
            print(f"  {'?':<20} {log.stem[:33]:<35} {'?':<10} {log.name[:23]}")
    print()


# ═══════════════════════════════════════════════════════════════════════
# Display
# ═══════════════════════════════════════════════════════════════════════

def display_results(results: Dict[str, List[Dict[str, Any]]]) -> None:
    """Pretty-print search results grouped by source."""
    total = sum(len(v) for v in results.values())
    if total == 0:
        print("\n  📭 No results found across any source.\n")
        return

    source_icons = {
        "torrent": "🌊", "youtube": "🎬", "web": "🌐",
        "github": "🐙",
    }

    for source, items in results.items():
        if not items:
            continue
        icon = source_icons.get(source, "📄")
        print(f"\n  ┌─ {icon} {source.upper()} ({len(items)} results)")
        print(f"  │")

        for i, item in enumerate(items[:8]):
            title = (item.get("title") or "?")[:55]
            if source == "torrent":
                size = item.get("size", "?")
                seeds = item.get("seeds", "?")
                provider = item.get("_provider", "?")
                print(f"  │  {i+1}. {title}")
                print(f"  │     {size} | {seeds} seeds | {provider}")
            elif source == "youtube":
                uploader = item.get("uploader", "")
                views = item.get("views", 0)
                print(f"  │  {i+1}. {title}")
                print(f"  │     {uploader} | {views:,} views")
            elif source == "github":
                stars = item.get("stars", 0)
                lang = item.get("language", "")
                desc = (item.get("description") or "")[:80]
                print(f"  │  {i+1}. {title} ⭐{stars:,} [{lang}]")
                if desc:
                    print(f"  │     {desc}")
            elif source == "web":
                url = item.get("url", "")[:65]
                body = (item.get("body") or "")[:80]
                print(f"  │  {i+1}. {title}")
                if body:
                    print(f"  │     {body}")
                print(f"  │     🔗 {url}")
            else:
                url = item.get("url", "")[:60]
                print(f"  │  {i+1}. {title}")
                if url:
                    print(f"  │     {url}")

        if len(items) > 8:
            print(f"  │  ... and {len(items) - 8} more")
        print(f"  └─")

    print(f"\n  📊 Total: {total} results across {len([s for s, i in results.items() if i])} sources\n")


# ═══════════════════════════════════════════════════════════════════════
# Download prompt — inline torrent picker after search results
# ═══════════════════════════════════════════════════════════════════════

def _add_to_aria2(chosen: Dict[str, Any]) -> bool:
    """Add a torrent magnet to aria2. Returns True on success."""
    magnet = chosen.get("magnet", "")
    title = (chosen.get("title") or "Untitled")[:100]
    if not magnet or not magnet.startswith("magnet:"):
        link = chosen.get("link", chosen.get("url", "unknown"))
        print(f"\n  ⚠ No magnet link — use: simple-internet download '{link}'\n")
        return False

    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4())[:8],
        "method": "aria2.addUri",
        "params": [[magnet]],
    }
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:6800/jsonrpc",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        if "error" not in data:
            gid = data.get("result", "")
            print(f"\n  ✅ Added to aria2: GID={gid} ({title})")
            print(f"  🚀 Download started!\n")
            return True
    except Exception:
        pass

    print(f"\n  🔗 Magnet: {magnet[:80]}...")
    print(f"  💡 Add manually: simple-internet download \"{magnet}\"\n")
    return False


def _prompt_torrent_download(torrents: List[Dict[str, Any]]) -> bool:
    """After displaying search results, offer to download a torrent by number."""
    if not torrents:
        return False

    print(f"  🎯 Download a torrent: type the number (1-{len(torrents)}) or press Enter to skip")
    try:
        choice = input("  → ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n")
        return False

    if not choice:
        print()
        return False

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(torrents):
            return _add_to_aria2(torrents[idx])
        print(f"  ❌ Enter 1-{len(torrents)} or press Enter to skip.\n")
    except ValueError:
        print(f"  ❌ Enter a number 1-{len(torrents)} or press Enter to skip.\n")
    return False


# ═══════════════════════════════════════════════════════════════════════
# Interactive picker (torrent only — dedicated mode)
# ═══════════════════════════════════════════════════════════════════════

def interactive_picker(query: str) -> int:
    """Search torrents, show picker, add to aria2. Also show other source hints."""
    results = search_torrents(query, limit=15)

    if not results:
        print("\n  📭 No torrents found.")
        print(f"  💡 Try web search: search_everything.py --web '{query}'")
        return 1

    print(f"\n  🌊 Torrent results for '{query}':\n")
    print(f"  {'#':<4} {'Title':<45} {'Size':<10} {'S/L':<12} {'Provider'}")
    print(f"  {'─'*4} {'─'*45} {'─'*10} {'─'*12} {'─'*15}")

    for i, r in enumerate(results):
        title = (r.get("title") or "?")[:43]
        size = r.get("size", "?")
        seeds = r.get("seeds", "?")
        leeches = r.get("peers", "?")
        provider = r.get("_provider", "?")[:13]
        print(f"  {i+1:<4} {title:<45} {str(size):<10} "
              f"{str(seeds)}/{str(leeches):<9} {provider}")

    print()

    while True:
        try:
            choice = input(f"  🎯 Pick a number (1-{len(results)}) or [q]uit: ").strip().lower()
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
            print(f"  ❌ Enter 1-{len(results)} or 'q' to quit.")

    chosen = results[idx]

    # Try to add to aria2 via shared helper
    if _add_to_aria2(chosen):
        return 0
    return 1


# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="search-everything",
        description="Universal search — torrents, YouTube, web, GitHub. All results logged.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  search-everything "game of thrones"           # search all sources
  search-everything --torrent "ubuntu iso"      # torrent only
  search-everything --youtube "python tutorial" # YouTube only
  search-everything --web "NVIDIA Jetson 5"      # web only
  search-everything --github "aria2 downloader" # GitHub repos
  search-everything --interactive "debian"      # picker mode
  search-everything --history                   # view search log
        """,
    )
    p.add_argument("query", nargs="?", default="", help="Search query")
    p.add_argument("--torrent", "-t", action="store_true", help="Search torrents")
    p.add_argument("--youtube", "-y", action="store_true", help="Search YouTube")
    p.add_argument("--web", "-w", action="store_true", help="Search the web")
    p.add_argument("--github", "-g", action="store_true", help="Search GitHub")
    p.add_argument("--all", "-a", action="store_true", help="Search all sources (default)")
    p.add_argument("--limit", "-l", type=int, default=10, help="Max results per source")
    p.add_argument("--interactive", "-i", action="store_true", help="Interactive picker mode")
    p.add_argument("--history", action="store_true", help="View recent search history")
    p.add_argument("--json", "-j", action="store_true", help="Output raw JSON")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    # ── History mode ──
    if args.history:
        view_history()
        return 0

    if not args.query:
        build_parser().print_help()
        return 0

    # ── Interactive mode ──
    if args.interactive:
        _info(f"Interactive search for: '{args.query}'")
        result = interactive_picker(args.query)
        # Also log
        results = {"torrent": search_torrents(args.query, limit=5)}
        log_search(args.query, results, 0)
        return result

    # ── Determine which sources to search ──
    search_all = args.all or not (args.torrent or args.youtube or args.web or args.github)
    sources = {
        "torrent": args.torrent or search_all,
        "youtube": args.youtube or search_all,
        "web": args.web or search_all,
        "github": args.github or search_all,
    }

    results: Dict[str, List[Dict[str, Any]]] = {}
    start = time.time()

    print(f"\n  🔍 Searching everywhere for: '{args.query}'")
    print(f"  {'─'*50}")

    # Run searches
    if sources["torrent"]:
        _info("Searching torrents...")
        results["torrent"] = search_torrents(args.query, limit=args.limit)
        _ok(f"Torrents: {len(results['torrent'])} found")

    if sources["youtube"]:
        _info("Searching YouTube...")
        results["youtube"] = search_youtube(args.query, limit=min(args.limit, 5))
        _ok(f"YouTube: {len(results['youtube'])} found")

    if sources["web"]:
        _info("Searching web...")
        results["web"] = search_web(args.query, limit=args.limit)
        _ok(f"Web: {len(results['web'])} found")

    if sources["github"]:
        _info("Searching GitHub...")
        results["github"] = search_github(args.query, limit=args.limit)
        _ok(f"GitHub: {len(results['github'])} found")

    duration_ms = (time.time() - start) * 1000

    # ── JSON output ──
    if args.json:
        print(json.dumps(results, indent=2, default=str))
        return 0

    # ── Display ──
    display_results(results)

    # ── Download prompt (torrent picker) ──
    torrents = results.get("torrent", [])
    if torrents and not args.json:
        _prompt_torrent_download(torrents)

    # ── Log ──
    log_path = log_search(args.query, results, duration_ms)
    print(f"  📝 Log: {log_path}")
    print(f"  📋 History: search-everything --history\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
