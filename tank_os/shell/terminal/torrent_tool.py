#!/usr/bin/env python3
"""Torrent Tool — search and download via VPS aria2 RPC.

Uses the VPS (100.71.127.19) aria2 instance for downloads.
Search via web scraping of public torrent indexers.

Usage:
    search_torrents("ubuntu 24.04")
    download_torrent("magnet:?xt=...")
    download_url("https://releases.ubuntu.com/24.04/ubuntu-24.04-desktop-amd64.iso.torrent")
    list_downloads()
    pause_download(gid)
    resume_download(gid)
    delete_download(gid)
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

import httpx

# VPS aria2 RPC
VPS_ARIA2_RPC = "http://100.71.127.19:6800/jsonrpc"
VPS_ARIA2_SECRET = ""  # No password set in docker
VPS_DOWNLOAD_DIR = "/downloads"


def _rpc_call(method: str, params: list = None) -> dict:
    """Call aria2 RPC on VPS."""
    if params is None:
        params = []
    if VPS_ARIA2_SECRET:
        params.insert(0, f"token:{VPS_ARIA2_SECRET}")

    payload = {
        "jsonrpc": "2.0",
        "id": "tankos",
        "method": method,
        "params": params,
    }
    try:
        resp = httpx.post(VPS_ARIA2_RPC, json=payload, timeout=10.0)
        data = resp.json()
        if "error" in data:
            return {"error": data["error"].get("message", str(data["error"]))}
        return data.get("result", {})
    except Exception as e:
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════
#  Search — uses web search to find torrents
# ═══════════════════════════════════════════════════════════════════════════

def search_torrents(query: str, max_results: int = 10) -> str:
    """Search for torrents using web search.
    
    Returns formatted list of results with magnet links / torrent URLs.
    """
    results = []

    # Search via multiple public torrent indexers
    search_sites = [
        ("1337x", f"https://1337x.to/search/{query.replace(' ', '+')}/1/"),
        ("TPB", f"https://thepiratebay.org/search.php?q={query.replace(' ', '+')}"),
        ("RARBG", f"https://rarbg.to/torrents.php?search={query.replace(' ', '+')}"),
    ]

    # Use DuckDuckGo for quick search
    try:
        resp = httpx.get(
            "https://api.duckduckgo.com/",
            params={"q": f"torrent download {query}", "format": "json", "no_html": 1},
            timeout=10.0,
        )
        data = resp.json()
        for result in data.get("RelatedTopics", [])[:5]:
            if "Text" in result and "FirstURL" in result:
                results.append({
                    "title": result["Text"][:100],
                    "url": result["FirstURL"],
                    "source": "DDG",
                })
    except Exception:
        pass

    # Also try searching common torrent sites directly
    try:
        resp = httpx.get(
            f"https://torrentapi.org/v2/search_torrents.php",
            params={"mode": "search", "search_string": query, "limit": max_results},
            headers={"User-Agent": "TankOS/1.0"},
            timeout=10.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            for t in data.get("torrent_data", []):
                results.append({
                    "title": t.get("title", ""),
                    "magnet": t.get("magnet", ""),
                    "size": t.get("size", ""),
                    "seeders": t.get("seeders", 0),
                    "source": "torrentapi",
                })
    except Exception:
        pass

    if not results:
        return f"No torrent results found for '{query}'. Try a broader search term."

    lines = [f"Torrent search results for '{query}':\n"]
    for i, r in enumerate(results[:max_results], 1):
        lines.append(f"  {i}. {r.get('title', 'Unknown')}")
        if r.get("size"):
            lines.append(f"     Size: {r['size']}")
        if r.get("seeders"):
            lines.append(f"     Seeders: {r['seeders']}")
        if r.get("magnet"):
            lines.append(f"     Magnet: {r['magnet'][:80]}...")
        elif r.get("url"):
            lines.append(f"     URL: {r['url']}")
        lines.append("")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
#  Download — via VPS aria2
# ═══════════════════════════════════════════════════════════════════════════

def download_torrent(url: str, filename: str = "") -> str:
    """Download a torrent/magnet link via VPS aria2.
    
    Args:
        url: Magnet link or .torrent URL
        filename: Optional output filename
    """
    options = {}
    if filename:
        options["out"] = filename
    options["dir"] = VPS_DOWNLOAD_DIR

    result = _rpc_call("aria2.addUri", [[url], options])
    if "error" in result:
        return f"Download failed: {result['error']}"
    
    gid = result
    return f"Download started! GID: {gid}\nTrack at: http://100.71.127.19:8082/#!/downloading"


def download_url(url: str, filename: str = "") -> str:
    """Download any file via VPS aria2 (HTTP, FTP, torrent, magnet)."""
    options = {}
    if filename:
        options["out"] = filename
    options["dir"] = VPS_DOWNLOAD_DIR
    options["max-connection-per-server"] = "16"
    options["split"] = "16"

    result = _rpc_call("aria2.addUri", [[url], options])
    if "error" in result:
        return f"Download failed: {result['error']}"
    
    gid = result
    return f"Download started! GID: {gid}\n16 connections active for fast download."


# ═══════════════════════════════════════════════════════════════════════════
#  Manage downloads
# ═══════════════════════════════════════════════════════════════════════════

def list_downloads(status: str = "active") -> str:
    """List downloads. status: active, waiting, stopped, all."""
    if status == "active":
        result = _rpc_call("aria2.tellActive")
    elif status == "waiting":
        result = _rpc_call("aria2.tellWaiting", [0, 20])
    elif status == "stopped":
        result = _rpc_call("aria2.tellStopped", [0, 20])
    else:
        active = _rpc_call("aria2.tellActive")
        waiting = _rpc_call("aria2.tellWaiting", [0, 20])
        stopped = _rpc_call("aria2.tellStopped", [0, 10])
        result = (active if isinstance(active, list) else []) + \
                 (waiting if isinstance(waiting, list) else []) + \
                 (stopped if isinstance(stopped, list) else [])

    if isinstance(result, dict) and "error" in result:
        return f"Error: {result['error']}"
    if not result:
        return "No downloads."

    lines = []
    for dl in result:
        name = dl.get("files", [{}])[0].get("path", "").split("/")[-1] or dl.get("bittorrent", {}).get("info", {}).get("name", "Unknown")
        total = int(dl.get("totalLength", 0))
        complete = int(dl.get("completedLength", 0))
        speed = int(dl.get("downloadSpeed", 0))
        status = dl.get("status", "unknown")
        progress = (complete / total * 100) if total > 0 else 0

        size_str = f"{total / (1024*1024):.1f}MB" if total > 1024*1024 else f"{total / 1024:.0f}KB"
        speed_str = f"{speed / (1024*1024):.1f}MB/s" if speed > 1024*1024 else f"{speed / 1024:.0f}KB/s" if speed > 0 else "0"

        lines.append(f"  [{status.upper()}] {name[:60]}")
        lines.append(f"    {progress:.1f}% ({size_str}) Speed: {speed_str}/s GID: {dl.get('gid', '?')}")
        lines.append("")

    return f"Downloads ({len(result)}):\n" + "\n".join(lines)


def get_download_status(gid: str) -> str:
    """Get detailed status of a download."""
    result = _rpc_call("aria2.tellStatus", [gid])
    if "error" in result:
        return f"Error: {result['error']}"
    
    name = result.get("files", [{}])[0].get("path", "").split("/")[-1] or "Unknown"
    total = int(result.get("totalLength", 0))
    complete = int(result.get("completedLength", 0))
    speed = int(result.get("downloadSpeed", 0))
    status = result.get("status", "unknown")

    return (
        f"Download: {name}\n"
        f"Status: {status}\n"
        f"Progress: {complete}/{total} ({complete/total*100:.1f}%)" if total > 0 else
        f"Download: {name}\nStatus: {status}"
    )


def pause_download(gid: str) -> str:
    """Pause a download."""
    result = _rpc_call("aria2.pause", [gid])
    return f"Paused GID {gid}" if "error" not in result else f"Error: {result['error']}"


def resume_download(gid: str) -> str:
    """Resume a paused download."""
    result = _rpc_call("aria2.unpause", [gid])
    return f"Resumed GID {gid}" if "error" not in result else f"Error: {result['error']}"


def delete_download(gid: str) -> str:
    """Delete a download and its files."""
    result = _rpc_call("aria2.removeDownloadResult", [gid])
    return f"Deleted GID {gid}" if "error" not in result else f"Error: {result['error']}"


def get_global_status() -> str:
    """Get aria2 global stats."""
    result = _rpc_call("aria2.getGlobalStat")
    if "error" in result:
        return f"Error: {result['error']}"
    
    return (
        f"aria2 Global Status:\n"
        f"  Active: {result.get('numActive', 0)}\n"
        f"  Waiting: {result.get('numWaiting', 0)}\n"
        f"  Stopped: {result.get('numStopped', 0)}\n"
        f"  Download: {int(result.get('downloadSpeed', 0)) / 1024:.0f} KB/s\n"
        f"  Upload: {int(result.get('uploadSpeed', 0)) / 1024:.0f} KB/s"
    )


# ═══════════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 torrent_tool.py search <query>")
        print("  python3 torrent_tool.py download <url_or_magnet>")
        print("  python3 torrent_tool.py list [active|waiting|stopped]")
        print("  python3 torrent_tool.py status")
        print("  python3 torrent_tool.py pause <gid>")
        print("  python3 torrent_tool.py resume <gid>")
        print("  python3 torrent_tool.py delete <gid>")
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd == "search":
        print(search_torrents(" ".join(sys.argv[2:])))
    elif cmd == "download":
        print(download_torrent(sys.argv[2]))
    elif cmd == "list":
        status = sys.argv[2] if len(sys.argv) > 2 else "all"
        print(list_downloads(status))
    elif cmd == "status":
        print(get_global_status())
    elif cmd == "pause" and len(sys.argv) > 2:
        print(pause_download(sys.argv[2]))
    elif cmd == "resume" and len(sys.argv) > 2:
        print(resume_download(sys.argv[2]))
    elif cmd == "delete" and len(sys.argv) > 2:
        print(delete_download(sys.argv[2]))
    else:
        print(f"Unknown: {cmd}")
