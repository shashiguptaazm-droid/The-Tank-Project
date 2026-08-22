"""
Simple Internet — CLI Tool (feature 152).

Headless command-line interface for managing downloads, searching,
and controlling the Simple Internet engine.

Usage:
  simple-internet download <url>                  Add a download
  simple-internet queue                           Show download queue
  simple-internet active                          Show active downloads
  simple-internet history                         Show download history
  simple-internet pause <id>                      Pause download
  simple-internet resume <id>                     Resume download
  simple-internet cancel <id>                     Cancel download
  simple-internet retry <id>                      Retry download
  simple-internet search <query>                  Search (torrent/web/yt)
  simple-internet search --source=web <query>     Search specific source
  simple-internet library                         Show media library
  simple-internet library --category=music        Filter library
  simple-internet scan                            Scan for new files
  simple-internet stats                           Show engine stats
  simple-internet server                          Start web dashboard
  simple-internet rss-add <url>                   Add RSS source
  simple-internet rss-refresh                     Refresh all RSS feeds
  simple-internet serve                           Start the web server

Global flags:
  --api=<url>     Connect to remote server (e.g. http://tank:8900)
  --quiet         Suppress extra output
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap
import urllib.request
import urllib.parse
from typing import Any, Dict, List, Optional


def _api_call(base: str, method: str, path: str,
              data: Optional[Dict] = None) -> Dict[str, Any]:
    """Make an API call to the Simple Internet server."""
    url = f"{base.rstrip('/')}{path}"
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers,
                                  method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read())
            return {"ok": False, "error": err.get("detail", str(e))}
        except Exception:
            return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _local_engine() -> Any:
    """Get or initialize local engine."""
    from tank_os.internet.manager import InternetManager
    m = InternetManager()
    if not m._initialized:
        m.initialize()
    return m


# ═══════════════════════════════════════════════════════════════════════
# Formatters
# ═══════════════════════════════════════════════════════════════════════

def _fmt_size(bytes_val: int) -> str:
    if not bytes_val:
        return "—"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_val < 1024:
            return f"{bytes_val:.1f}{unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f}PB"


def _fmt_time(ts: float) -> str:
    if not ts:
        return "—"
    import datetime
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def _print_table(rows: List[List[str]], headers: List[str]) -> None:
    """Print a simple ASCII table."""
    if not rows:
        print("  (empty)")
        return
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))
    sep = "  " + "─" * (sum(col_widths) + 3 * (len(headers) - 1)) + "  "
    header_line = "  " + " │ ".join(h.ljust(w) for h, w in zip(headers, col_widths))
    print(header_line)
    print(sep)
    for row in rows:
        line = "  " + " │ ".join(c.ljust(w) for c, w in zip(row, col_widths))
        print(line)


# ═══════════════════════════════════════════════════════════════════════
# Commands
# ═══════════════════════════════════════════════════════════════════════

def cmd_download(args, api) -> int:
    url = args.url
    if api:
        r = _api_call(api, "POST", "/api/download", {"url": url, "priority": args.priority or 5})
        if r.get("ok"):
            task = r.get("task", {})
            print(f"✅ Added: {task.get('filename', url)[:50]}")
            print(f"   ID: {task.get('id', '')}  Protocol: {task.get('protocol', '')}")
        else:
            print(f"❌ {r.get('error', 'Failed')}")
            return 1
    else:
        m = _local_engine()
        task = m.download(url, priority=args.priority or 5)
        if task:
            print(f"✅ Added: {task.filename} ({task.protocol})")
            print(f"   ID: {task.id}")
        else:
            print("❌ Failed to add download")
            return 1
    return 0


def cmd_queue(args, api) -> int:
    if api:
        r = _api_call(api, "GET", "/api/queue")
        if not r.get("ok"):
            print(f"❌ {r.get('error', 'Failed')}")
            return 1
        items = r.get("queue", [])
    else:
        m = _local_engine()
        items = [_task_to_dict(t) for t in m.get_queue()]

    if not items:
        print("📭 Queue is empty")
        return 0

    rows = []
    for i in items:
        rows.append([
            i.get("filename", "?")[:35],
            i.get("protocol", ""),
            str(i.get("status", "")),
            _fmt_size(i.get("size_bytes", 0)),
            f"{i.get('progress', 0):.0f}%",
            i.get("id", "")[:8],
        ])
    _print_table(rows, ["Filename", "Proto", "Status", "Size", "Prog", "ID"])
    return 0


def cmd_active(args, api) -> int:
    if api:
        r = _api_call(api, "GET", "/api/active")
        if not r.get("ok"):
            print(f"❌ {r.get('error', 'Failed')}")
            return 1
        items = r.get("active", [])
    else:
        m = _local_engine()
        items = [_task_to_dict(t) for t in m.get_active()]

    if not items:
        print("📭 No active downloads")
        return 0

    rows = []
    for i in items:
        rows.append([
            i.get("filename", "?")[:35],
            _fmt_size(i.get("size_bytes", 0)),
            f"{i.get('progress', 0):.0f}%",
            _fmt_size(int(i.get("speed_bps", 0))) + "/s",
            i.get("id", "")[:8],
        ])
    _print_table(rows, ["Filename", "Size", "Progress", "Speed", "ID"])
    return 0


def cmd_history(args, api) -> int:
    limit = args.limit or 50
    if api:
        r = _api_call(api, "GET", f"/api/history?limit={limit}")
        if not r.get("ok"):
            print(f"❌ {r.get('error', 'Failed')}")
            return 1
        items = r.get("history", [])
    else:
        m = _local_engine()
        items = m.get_history(limit)

    if not items:
        print("📭 No download history")
        return 0

    rows = []
    for i in items:
        rows.append([
            i.get("filename", "?")[:35],
            i.get("category", ""),
            i.get("status", ""),
            _fmt_size(i.get("size_bytes", 0)),
            _fmt_time(i.get("completed", 0)),
        ])
    _print_table(rows, ["Filename", "Type", "Status", "Size", "Completed"])
    return 0


def cmd_pause(args, api) -> int:
    task_id = args.id
    if api:
        r = _api_call(api, "POST", f"/api/pause/{task_id}")
        ok = r.get("ok", False)
    else:
        from tank_os.internet.downloader import DownloadEngine
        eng = DownloadEngine()
        ok = eng.pause_download(task_id)
    print("✅ Paused" if ok else "❌ Failed to pause")
    return 0 if ok else 1


def cmd_resume(args, api) -> int:
    task_id = args.id
    if api:
        r = _api_call(api, "POST", f"/api/resume/{task_id}")
        ok = r.get("ok", False)
    else:
        from tank_os.internet.downloader import DownloadEngine
        eng = DownloadEngine()
        ok = eng.resume_download(task_id)
    print("✅ Resumed" if ok else "❌ Failed to resume")
    return 0 if ok else 1


def cmd_cancel(args, api) -> int:
    task_id = args.id
    if api:
        r = _api_call(api, "POST", f"/api/cancel/{task_id}")
        ok = r.get("ok", False)
    else:
        from tank_os.internet.downloader import DownloadEngine
        eng = DownloadEngine()
        ok = eng.cancel_download(task_id)
    print("✅ Cancelled" if ok else "❌ Failed to cancel")
    return 0 if ok else 1


def cmd_retry(args, api) -> int:
    task_id = args.id
    if api:
        r = _api_call(api, "POST", f"/api/retry/{task_id}")
        ok = r.get("ok", False)
    else:
        from tank_os.internet.downloader import DownloadEngine
        eng = DownloadEngine()
        ok = eng.retry_download(task_id)
    print("✅ Retrying" if ok else "❌ Failed to retry")
    return 0 if ok else 1


def cmd_search(args, api) -> int:
    query = args.query
    source = args.source or "web"
    limit = args.limit or 20

    if api:
        r = _api_call(api, "GET",
                       f"/api/search?q={urllib.parse.quote(query)}&source={source}&limit={limit}")
        if not r.get("ok"):
            print(f"❌ {r.get('error', 'Failed')}")
            return 1
        items = r.get("results", [])
    else:
        m = _local_engine()
        items = [r.__dict__ for r in m.search(query, source=source, limit=limit)]

    if not items:
        print(f"📭 No results for '{query}'")
        return 0

    rows = []
    for i in items:
        rows.append([
            (i.get("title", "") or "?")[:40],
            i.get("source", ""),
            _fmt_size(i.get("size_bytes", 0)),
            str(i.get("seeders", "—")),
            (i.get("magnet", "") or i.get("url", "") or "")[:40],
        ])
    _print_table(rows, ["Title", "Source", "Size", "Seeds", "URL/Magnet"])
    return 0


def cmd_library(args, api) -> int:
    category = args.category or ""
    query = args.query or ""

    if api:
        params = f"?limit=100"
        if category:
            params += f"&category={category}"
        if query:
            params += f"&q={urllib.parse.quote(query)}"
        r = _api_call(api, "GET", f"/api/library{params}")
        if not r.get("ok"):
            print(f"❌ {r.get('error', 'Failed')}")
            return 1
        items = r.get("items", [])
    else:
        m = _local_engine()
        items = m.get_library(category=category, query=query)

    if not items:
        print("📭 Library is empty")
        return 0

    rows = []
    for i in items:
        rows.append([
            i.get("filename", "?")[:35],
            i.get("category", ""),
            _fmt_size(i.get("size_bytes", 0)),
            i.get("artist", "—")[:15],
            str(i.get("rating", 0)),
        ])
    _print_table(rows, ["Filename", "Type", "Size", "Artist", "Rating"])
    return 0


def cmd_scan(args, api) -> int:
    if api:
        r = _api_call(api, "POST", "/api/scan")
        if r.get("ok"):
            print(f"✅ Scanned: {r.get('new_files', 0)} new files")
        else:
            print(f"❌ {r.get('error', 'Failed')}")
            return 1
    else:
        m = _local_engine()
        count = m.scan_library()
        print(f"✅ Scanned: {count} new files")
    return 0


def cmd_stats(args, api) -> int:
    if api:
        r = _api_call(api, "GET", "/api/stats")
        if not r.get("ok"):
            print(f"❌ {r.get('error', 'Failed')}")
            return 1
        s = r
    else:
        m = _local_engine()
        s = m.get_stats()

    print("📊 Simple Internet — Statistics")
    print(f"  Active downloads:  {s.get('active_downloads', 0)}")
    print(f"  Queued:            {s.get('queued', 0)}")
    print(f"  Library files:     {s.get('library_files', 0)}")
    print(f"  RSS sources:       {s.get('rss_sources', 0)}")
    print(f"  Rules:             {s.get('automation_rules', 0)}")
    return 0


def cmd_server(args, api=None) -> int:
    """Start the web dashboard server."""
    host = args.host or "0.0.0.0"
    port = args.port or 8900
    from tank_os.internet.server import main
    return main(host=host, port=port)


def cmd_rss_add(args, api) -> int:
    url = args.url
    name = args.name or ""
    if api:
        r = _api_call(api, "POST", "/api/rss/add",
                       {"url": url, "name": name})
        if r.get("ok"):
            print("✅ RSS source added")
        else:
            print(f"❌ {r.get('error', 'Failed')}")
            return 1
    else:
        m = _local_engine()
        if m.add_rss_source(url, name=name):
            print("✅ RSS source added")
        else:
            print("❌ Failed to add RSS source")
            return 1
    return 0


def cmd_rss_refresh(args, api) -> int:
    if api:
        r = _api_call(api, "POST", "/api/rss/refresh")
        if r.get("ok"):
            print(f"✅ RSS refreshed: {r.get('new_items', 0)} new items")
        else:
            print(f"❌ {r.get('error', 'Failed')}")
            return 1
    else:
        m = _local_engine()
        count = m.refresh_rss()
        print(f"✅ RSS refreshed: {count} new items")
    return 0


from tank_os.internet.server import _task_to_dict  # noqa: F401


# ═══════════════════════════════════════════════════════════════════════
# Argument Parser
# ═══════════════════════════════════════════════════════════════════════

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="simple-internet",
        description="Simple Internet — Universal Downloader & Search Tool for TankOS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              simple-internet download "magnet:?xt=urn:btih:..."
              simple-internet search "ubuntu 24.04" --source=torrent
              simple-internet search "raspberry pi tutorial" --source=youtube
              simple-internet queue
              simple-internet active
              simple-internet history
              simple-internet library --category=video
              simple-internet serve
              simple-internet --api=http://tank:8900 stats
        """),
    )

    parser.add_argument("--api", help="Connect to remote server (e.g. http://tank:8900)")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress extra output")

    sub = parser.add_subparsers(dest="command", help="Command to execute")

    # download
    p = sub.add_parser("download", help="Add a download")
    p.add_argument("url", help="URL to download (HTTP, magnet, torrent, YouTube)")
    p.add_argument("--priority", type=int, default=5, help="Priority (1-10, lower = higher)")

    # queue
    sub.add_parser("queue", help="Show download queue")

    # active
    sub.add_parser("active", help="Show active downloads")

    # history
    p = sub.add_parser("history", help="Show download history")
    p.add_argument("--limit", type=int, default=50, help="Number of entries")

    # pause / resume / cancel / retry
    for name in ["pause", "resume", "cancel", "retry"]:
        p = sub.add_parser(name, help=f"{name.capitalize()} a download")
        p.add_argument("id", help="Task ID")

    # search
    p = sub.add_parser("search", help="Search the internet")
    p.add_argument("query", help="Search query")
    p.add_argument("--source", "-s", default="web",
                    choices=["web", "torrent", "youtube", "soundcloud", "images", "news"],
                    help="Search source")
    p.add_argument("--limit", "-l", type=int, default=20, help="Max results")

    # library
    p = sub.add_parser("library", help="Browse media library")
    p.add_argument("--category", "-c", default="",
                    choices=["", "video", "music", "document", "image", "ebook"])
    p.add_argument("--query", "-q", default="", help="Search within library")

    # scan
    sub.add_parser("scan", help="Scan for new files")

    # stats
    sub.add_parser("stats", help="Show engine statistics")

    # server
    p = sub.add_parser("serve", help="Start web dashboard")
    p.add_argument("--host", default="0.0.0.0", help="Bind address")
    p.add_argument("--port", type=int, default=8900, help="Bind port")

    # rss
    p = sub.add_parser("rss-add", help="Add RSS source")
    p.add_argument("url", help="RSS feed URL")
    p.add_argument("--name", default="", help="Friendly name")

    p = sub.add_parser("rss-refresh", help="Refresh RSS feeds")

    return parser


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

COMMANDS = {
    "download": cmd_download,
    "queue": cmd_queue,
    "active": cmd_active,
    "history": cmd_history,
    "pause": cmd_pause,
    "resume": cmd_resume,
    "cancel": cmd_cancel,
    "retry": cmd_retry,
    "search": cmd_search,
    "library": cmd_library,
    "scan": cmd_scan,
    "stats": cmd_stats,
    "serve": cmd_server,
    "rss-add": cmd_rss_add,
    "rss-refresh": cmd_rss_refresh,
}


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    api = args.api

    handler = COMMANDS.get(args.command)
    if handler:
        return handler(args, api)

    print(f"Unknown command: {args.command}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
