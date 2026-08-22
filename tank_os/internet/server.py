"""
Simple Internet — FastAPI Server + Web Dashboard.

Provides a REST API (feature 153) and a full web dashboard (feature 154)
for managing downloads, searching, and browsing the library.

Endpoints:
- GET  /api/health              — Server health
- GET  /api/stats               — Download engine stats
- GET  /api/queue               — Download queue
- GET  /api/active              — Active downloads
- GET  /api/history             — Download history
- POST /api/download            — Add a download
- POST /api/pause/{task_id}     — Pause download
- POST /api/resume/{task_id}    — Resume download
- POST /api/cancel/{task_id}    — Cancel download
- POST /api/retry/{task_id}     — Retry failed download
- POST /api/bandwidth           — Set bandwidth limits
- GET  /api/search              — Search across sources
- GET  /api/library             — Browse library
- POST /api/library/update      — Update library item metadata
- POST /api/rss/add             — Add RSS source
- POST /api/rss/refresh         — Refresh RSS feeds
- POST /api/queue/pause         — Pause queue
- POST /api/queue/resume        — Resume queue
- GET  /                        — Web dashboard UI
- GET  /search                  — Search page
- GET  /library                 — Library browser
- GET  /queue                   — Queue management
- GET  /history                 — Download history
"""

from __future__ import annotations

import json
import logging
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from tank_os.internet.manager import InternetManager
from tank_os.internet.downloader import DownloadCategory, DownloadStatus, DownloadEngine

logger = logging.getLogger("tank_os.internet.server")

_manager: Optional[InternetManager] = None
_start_time: float = 0.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _manager, _start_time
    _start_time = time.time()
    _manager = InternetManager()
    _manager.initialize()
    logger.info("Simple Internet server started")
    yield


app = FastAPI(
    title="Simple Internet — TankOS Universal Downloader",
    version="1.0.0",
    lifespan=lifespan,
)


# ═══════════════════════════════════════════════════════════════════════
# REST API
# ═══════════════════════════════════════════════════════════════════════

@app.get("/api/health")
def api_health() -> dict:
    """Server health check."""
    return {
        "ok": True,
        "uptime": time.time() - _start_time,
        "version": "1.0.0",
    }


@app.get("/api/stats")
def api_stats() -> dict:
    """Get download engine stats."""
    m = _manager
    if not m:
        return {"ok": False, "error": "not initialized"}
    return {"ok": True, **m.get_stats()}


@app.get("/api/queue")
def api_queue() -> dict:
    """Get the download queue."""
    m = _manager
    if not m:
        return {"ok": False, "queue": []}
    queue = m.get_queue()
    return {"ok": True, "count": len(queue), "queue": [_task_to_dict(t) for t in queue]}


@app.get("/api/active")
def api_active() -> dict:
    """Get active downloads."""
    m = _manager
    if not m:
        return {"ok": False, "active": []}
    active = m.get_active()
    return {"ok": True, "count": len(active), "active": [_task_to_dict(t) for t in active]}


@app.get("/api/history")
def api_history(limit: int = Query(50, ge=1, le=500)) -> dict:
    """Get download history."""
    m = _manager
    if not m:
        return {"ok": False, "history": []}
    history = m.get_history(limit)
    return {"ok": True, "count": len(history), "history": history}


@app.post("/api/download")
async def api_download(request: Request) -> dict:
    """Add a new download."""
    m = _manager
    if not m:
        return {"ok": False, "error": "not initialized"}
    try:
        body = await request.json()
    except Exception:
        return {"ok": False, "error": "invalid JSON"}

    url = body.get("url", "").strip()
    if not url:
        return {"ok": False, "error": "missing url"}

    task = m.download(
        url,
        filename=body.get("filename", ""),
        protocol=body.get("protocol", ""),
        category=body.get("category", ""),
        priority=body.get("priority", 5),
        extract_after=body.get("extract", False),
        convert_to=body.get("convert_to", ""),
    )

    if task:
        return {"ok": True, "task": _task_to_dict(task)}
    return {"ok": False, "error": "failed to create download task"}


@app.post("/api/pause/{task_id}")
def api_pause(task_id: str) -> dict:
    """Pause a download."""
    eng = _get_engine()
    if not eng:
        return {"ok": False, "error": "not initialized"}
    ok = eng.pause_download(task_id)
    return {"ok": ok}


@app.post("/api/resume/{task_id}")
def api_resume(task_id: str) -> dict:
    """Resume a download."""
    eng = _get_engine()
    if not eng:
        return {"ok": False, "error": "not initialized"}
    ok = eng.resume_download(task_id)
    return {"ok": ok}


@app.post("/api/cancel/{task_id}")
def api_cancel(task_id: str) -> dict:
    """Cancel a download."""
    eng = _get_engine()
    if not eng:
        return {"ok": False, "error": "not initialized"}
    ok = eng.cancel_download(task_id)
    return {"ok": ok}


@app.post("/api/retry/{task_id}")
def api_retry(task_id: str) -> dict:
    """Retry a failed download."""
    eng = _get_engine()
    if not eng:
        return {"ok": False, "error": "not initialized"}
    ok = eng.retry_download(task_id)
    return {"ok": ok}


@app.post("/api/bandwidth")
async def api_bandwidth(request: Request) -> dict:
    """Set bandwidth limits (0 = unlimited)."""
    eng = _get_engine()
    if not eng:
        return {"ok": False, "error": "not initialized"}
    try:
        body = await request.json()
    except Exception:
        return {"ok": False, "error": "invalid JSON"}
    eng.set_bandwidth(
        global_bps=body.get("global_bps", 0),
        per_download_bps=body.get("per_download_bps", 0),
    )
    return {"ok": True}


@app.post("/api/queue/pause")
def api_queue_pause() -> dict:
    """Pause the download queue."""
    eng = _get_engine()
    if not eng:
        return {"ok": False, "error": "not initialized"}
    eng.set_queue_paused(True)
    return {"ok": True}


@app.post("/api/queue/resume")
def api_queue_resume() -> dict:
    """Resume the download queue."""
    eng = _get_engine()
    if not eng:
        return {"ok": False, "error": "not initialized"}
    eng.set_queue_paused(False)
    return {"ok": True}


@app.get("/api/search")
def api_search(
    q: str = Query("", description="Search query"),
    source: str = Query("web", description="Search source"),
    limit: int = Query(20, ge=1, le=100),
    category: str = Query("", description="Filter by category"),
    file_type: str = Query("", description="Filter by file type"),
    min_seeders: int = Query(0, ge=0),
) -> dict:
    """Search across torrent sites, web, YouTube, etc."""
    m = _manager
    if not m:
        return {"ok": False, "error": "not initialized"}
    results = m.search(q, source=source, limit=limit)
    return {
        "ok": True,
        "query": q,
        "source": source,
        "count": len(results),
        "results": [r.__dict__ for r in results],
    }


@app.get("/api/search/all")
def api_search_all(q: str = Query("", description="Search query"),
                    limit: int = Query(5, ge=1, le=20)) -> dict:
    """Search all sources simultaneously."""
    m = _manager
    if not m:
        return {"ok": False, "error": "not initialized"}
    results = m.search_all(q, limit=limit)
    return {"ok": True, "query": q, "results": results}


@app.get("/api/library")
def api_library(
    category: str = Query("", description="Filter by category"),
    q: str = Query("", description="Search within library"),
    limit: int = Query(100, ge=1, le=1000),
) -> dict:
    """Browse the media library."""
    m = _manager
    if not m:
        return {"ok": False, "error": "not initialized"}
    items = m.get_library(category=category, query=q, limit=limit)
    return {"ok": True, "count": len(items), "items": items}


@app.post("/api/library/update")
async def api_library_update(request: Request) -> dict:
    """Update library item metadata."""
    m = _manager
    if not m:
        return {"ok": False, "error": "not initialized"}
    try:
        body = await request.json()
    except Exception:
        return {"ok": False, "error": "invalid JSON"}
    item_id = body.get("id", "")
    if not item_id:
        return {"ok": False, "error": "missing id"}
    kwargs = {k: v for k, v in body.items() if k != "id"}
    ok = m.update_library_item(item_id, **kwargs)
    return {"ok": ok}


@app.post("/api/rss/add")
async def api_rss_add(request: Request) -> dict:
    """Add an RSS source for automated downloads."""
    m = _manager
    if not m:
        return {"ok": False, "error": "not initialized"}
    try:
        body = await request.json()
    except Exception:
        return {"ok": False, "error": "invalid JSON"}
    url = body.get("url", "").strip()
    if not url:
        return {"ok": False, "error": "missing url"}
    ok = m.add_rss_source(url, name=body.get("name", ""), filters=body.get("filters"))
    return {"ok": ok}


@app.post("/api/rss/refresh")
def api_rss_refresh() -> dict:
    """Refresh all RSS feeds."""
    m = _manager
    if not m:
        return {"ok": False, "error": "not initialized"}
    count = m.refresh_rss()
    return {"ok": True, "new_items": count}


@app.post("/api/scan")
def api_scan() -> dict:
    """Scan download directories and update library."""
    m = _manager
    if not m:
        return {"ok": False, "error": "not initialized"}
    count = m.scan_library()
    return {"ok": True, "new_files": count}


@app.get("/api/search/history")
def api_search_history() -> dict:
    """Get search history."""
    m = _manager
    if not m:
        return {"ok": False, "history": []}
    return {"ok": True, "history": m.get_search_history()}


# ═══════════════════════════════════════════════════════════════════════
# Web Dashboard — HTML pages
# ═══════════════════════════════════════════════════════════════════════

HTML_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Simple Internet — TankOS Downloader</title>
<style>
:root {
  --bg: #0d1117; --bg2: #161b22; --bg3: #21262d;
  --fg: #e6edf3; --fg2: #8b949e; --accent: #58a6ff;
  --success: #3fb950; --warning: #d29922; --danger: #f85149;
  --border: #30363d; --radius: 6px;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--bg); color: var(--fg); line-height: 1.6;
  min-height: 100vh;
}
nav {
  background: var(--bg2); border-bottom: 1px solid var(--border);
  padding: 0 24px; display: flex; align-items: center; height: 56px; gap: 24px;
  position: sticky; top: 0; z-index: 100;
}
nav h1 { font-size: 18px; font-weight: 600; color: var(--accent); }
nav a { color: var(--fg2); text-decoration: none; font-size: 14px; padding: 4px 8px; border-radius: var(--radius); transition: all .15s; }
nav a:hover, nav a.active { color: var(--fg); background: var(--bg3); }
.container { max-width: 1200px; margin: 0 auto; padding: 24px; }
.card {
  background: var(--bg2); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 20px; margin-bottom: 16px;
}
.card h2 { font-size: 16px; font-weight: 600; margin-bottom: 12px; }
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; }
.stat { text-align: center; padding: 16px; background: var(--bg3); border-radius: var(--radius); }
.stat .value { font-size: 28px; font-weight: 700; color: var(--accent); }
.stat .label { font-size: 12px; color: var(--fg2); margin-top: 4px; }
.btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 8px 16px; border: 1px solid var(--border); border-radius: var(--radius);
  background: var(--bg3); color: var(--fg); font-size: 13px; cursor: pointer;
  transition: all .15s; text-decoration: none;
}
.btn:hover { background: var(--border); }
.btn-primary { background: var(--accent); color: #fff; border-color: var(--accent); }
.btn-primary:hover { filter: brightness(1.15); }
.btn-danger { background: var(--danger); color: #fff; border-color: var(--danger); }
.btn-success { background: var(--success); color: #fff; border-color: var(--success); }
input, select {
  background: var(--bg3); border: 1px solid var(--border); color: var(--fg);
  padding: 8px 12px; border-radius: var(--radius); font-size: 14px;
  width: 100%; outline: none; transition: border-color .15s;
}
input:focus, select:focus { border-color: var(--accent); }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { text-align: left; padding: 8px 12px; color: var(--fg2); font-weight: 500; border-bottom: 1px solid var(--border); }
td { padding: 8px 12px; border-bottom: 1px solid var(--border); }
.progress-bar { height: 4px; background: var(--bg3); border-radius: 2px; overflow: hidden; }
.progress-bar .fill { height: 100%; background: var(--accent); border-radius: 2px; transition: width .5s; }
.progress-bar .fill.done { background: var(--success); }
.progress-bar .fill.fail { background: var(--danger); }
.badge {
  display: inline-block; padding: 2px 8px; border-radius: 10px;
  font-size: 11px; font-weight: 500;
}
.badge-video { background: #1f6feb33; color: #58a6ff; }
.badge-music { background: #3fb95033; color: #3fb950; }
.badge-torrent { background: #d2992233; color: #d29922; }
.badge-document { background: #8b949e33; color: #8b949e; }
.status-queued { color: var(--fg2); }
.status-downloading { color: var(--accent); }
.status-completed { color: var(--success); }
.status-failed { color: var(--danger); }
.status-paused { color: var(--warning); }
.flex { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.flex-between { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.empty { text-align: center; padding: 40px; color: var(--fg2); }
.toast {
  position: fixed; bottom: 24px; right: 24px; padding: 12px 24px;
  border-radius: var(--radius); background: var(--bg3); border: 1px solid var(--border);
  color: var(--fg); font-size: 14px; z-index: 1000;
  opacity: 0; transform: translateY(10px); transition: all .3s;
}
.toast.show { opacity: 1; transform: translateY(0); }
.toast.success { border-color: var(--success); }
.toast.error { border-color: var(--danger); }
@media (max-width: 768px) {
  .container { padding: 12px; }
  nav { padding: 0 12px; gap: 12px; }
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
</head>
<body>
<nav>
  <h1>⬇ Simple Internet</h1>
  <a href="/" class="active">Dashboard</a>
  <a href="/search">Search</a>
  <a href="/queue">Downloads</a>
  <a href="/library">Library</a>
  <a href="/history">History</a>
</nav>
<div class="container">
"""

HTML_FOOT = """
</div>
<script>
async function api(path, opts={}) {
  const res = await fetch(path, { headers: {'Content-Type':'application/json'}, ...opts });
  return res.json();
}
function toast(msg, type='') {
  const t = document.createElement('div');
  t.className = 'toast show ' + type;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => { t.classList.remove('show'); setTimeout(() => t.remove(), 300); }, 3000);
}
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def dashboard():
    """Main dashboard."""
    m = _manager
    stats = m.get_stats() if m else {}
    active = m.get_active() if m else []

    active_rows = ""
    for t in active[:10]:
        pct = int(t.progress)
        status_class = "status-" + t.status.value
        active_rows += f"""<tr>
          <td>{t.filename[:40]}</td>
          <td><span class="badge badge-{t.category.value}">{t.category.value}</span></td>
          <td class="{status_class}">{t.status.value}</td>
          <td>{_fmt_size(t.size_bytes)}</td>
          <td style="width:200px">
            <div class="progress-bar"><div class="fill" style="width:{pct}%"></div></div>
            <small>{pct}%</small>
          </td>
          <td>{_fmt_speed(t.speed_bps)}</td>
          <td class="flex">
            <button class="btn btn-danger" onclick="cancel('{t.id}')" style="padding:4px 8px;font-size:11px;">✕</button>
          </td>
        </tr>"""

    return HTMLResponse(HTML_HEAD + f"""
    <div class="stats-grid">
      <div class="stat"><div class="value">{stats.get('active_downloads', 0)}</div><div class="label">Active</div></div>
      <div class="stat"><div class="value">{stats.get('queued', 0)}</div><div class="label">Queued</div></div>
      <div class="stat"><div class="value">{stats.get('library_files', 0)}</div><div class="label">Library Files</div></div>
      <div class="stat"><div class="value">{stats.get('rss_sources', 0)}</div><div class="label">RSS Feeds</div></div>
    </div>

    <div class="card">
      <div class="flex-between">
        <h2>Add Download</h2>
      </div>
      <div class="flex" style="margin-top:8px;">
        <input id="dl-url" placeholder="Paste URL (HTTP, magnet, torrent, YouTube, etc.)" style="flex:1;">
        <button class="btn btn-primary" onclick="addDownload()">+ Download</button>
      </div>
    </div>

    <div class="card">
      <div class="flex-between">
        <h2>Active Downloads</h2>
        <div class="flex">
          <button class="btn" onclick="reload()">↻ Refresh</button>
        </div>
      </div>
      {f'<table><thead><tr><th>File</th><th>Type</th><th>Status</th><th>Size</th><th>Progress</th><th>Speed</th><th></th></tr></thead><tbody>{active_rows}</tbody></table>' if active_rows else '<div class="empty">No active downloads</div>'}
    </div>

    <script>
    function addDownload() {{
      const url = document.getElementById('dl-url').value;
      if (!url) return toast('Enter a URL', 'error');
      api('/api/download', {{
        method: 'POST',
        body: JSON.stringify({{ url, priority: 5 }})
      }}).then(r => {{
        if (r.ok) {{ toast('Download queued', 'success'); document.getElementById('dl-url').value = ''; }}
        else toast(r.error || 'Failed', 'error');
      }});
    }}
    function cancel(id) {{
      if (!confirm('Cancel this download?')) return;
      api('/api/cancel/' + id, {{ method: 'POST' }}).then(r => {{
        if (r.ok) {{ toast('Cancelled', 'success'); reload(); }}
      }});
    }}
    function reload() {{ window.location.reload(); }}
    setInterval(() => {{ window.location.reload(); }}, 10000);
    </script>
    """ + HTML_FOOT)


@app.get("/search", response_class=HTMLResponse)
def search_page():
    """Search page."""
    return HTMLResponse(HTML_HEAD + """
    <div class="card">
      <h2>Search</h2>
      <div class="flex" style="margin-top:8px;">
        <input id="sq" placeholder="Search torrents, web, YouTube, images..." style="flex:1;" onkeydown="if(event.key==='Enter') doSearch()">
        <select id="ss">
          <option value="web">Web</option>
          <option value="youtube">YouTube</option>
          <option value="soundcloud">SoundCloud</option>
          <option value="torrent">Torrent</option>
          <option value="images">Images</option>
        </select>
        <button class="btn btn-primary" onclick="doSearch()">🔍 Search</button>
      </div>
    </div>
    <div id="results"></div>
    <script>
    async function doSearch() {
      const q = document.getElementById('sq').value;
      const s = document.getElementById('ss').value;
      if (!q) return;
      const res = await api('/api/search?q=' + encodeURIComponent(q) + '&source=' + s + '&limit=20');
      const container = document.getElementById('results');
      if (!res.ok || !res.results.length) {
        container.innerHTML = '<div class="card empty">No results found</div>';
        return;
      }
      let html = '<div class="card"><table><thead><tr><th>Title</th><th>Source</th><th>Size</th><th>Seeds</th><th></th></tr></thead><tbody>';
      for (const r of res.results) {
        const size = r.size_bytes ? (r.size_bytes / 1048576).toFixed(0) + ' MB' : '';
        var dlUrl = r.magnet || r.url || '';
        html += '<tr><td>' + (r.title || '').slice(0, 60) + '</td><td>' + r.source + '</td><td>' + size + '</td><td>' + (r.seeders || '') + '</td>';
        html += '<td><button class="btn btn-success" style="padding:4px 8px;font-size:11px;" onclick="dl(\\u0027' + dlUrl.replace(/'/g, '\\u0027') + '\\u0027)">⬇</button></td></tr>';
      }
      html += '</tbody></table></div>';
      container.innerHTML = html;
    }
    async function dl(url) {
      if (!url) return toast('No download URL', 'error');
      const r = await api('/api/download', { method: 'POST', body: JSON.stringify({url}) });
      if (r.ok) toast('Download started', 'success'); else toast(r.error || 'Failed', 'error');
    }
    </script>
    """ + HTML_FOOT)


@app.get("/queue", response_class=HTMLResponse)
def queue_page():
    """Download queue management page."""
    m = _manager
    queue = m.get_queue() if m else []
    stats = m.get_stats() if m else {}

    def _action_buttons(t):
        """Generate action buttons HTML for a task row."""
        btns = []
        if t.status == DownloadStatus.DOWNLOADING:
            btns.append('<button class="btn" style="padding:4px 8px;font-size:11px;" onclick="pause(\'%s\')">⏸</button>' % t.id)
        if t.status == DownloadStatus.PAUSED:
            btns.append('<button class="btn" style="padding:4px 8px;font-size:11px;" onclick="resume(\'%s\')">▶</button>' % t.id)
        if t.status == DownloadStatus.FAILED:
            btns.append('<button class="btn" style="padding:4px 8px;font-size:11px;" onclick="retry(\'%s\')">↻</button>' % t.id)
        btns.append('<button class="btn btn-danger" style="padding:4px 8px;font-size:11px;" onclick="cancel(\'%s\')">✕</button>' % t.id)
        return ' '.join(btns)

    rows = ""
    for t in queue:
        pct = int(t.progress)
        status_class = "status-" + t.status.value
        fill_class = " done" if t.status == DownloadStatus.COMPLETED else (" fail" if t.status == DownloadStatus.FAILED else "")
        rows += f"""<tr>
          <td>{t.filename[:45]}</td>
          <td><span class="badge badge-{t.category.value}">{t.category.value}</span></td>
          <td class="{status_class}">{t.status.value}</td>
          <td>{_fmt_size(t.size_bytes)}</td>
          <td style="width:150px">
            <div class="progress-bar"><div class="fill{fill_class}" style="width:{pct}%"></div></div>
            <small>{pct}%</small>
          </td>
          <td>{_fmt_speed(t.speed_bps)}</td>
          <td class="flex">
            {_action_buttons(t)}
          </td>
        </tr>"""

    return HTMLResponse(HTML_HEAD + f"""
    <div class="flex-between" style="margin-bottom:16px;">
      <h2>Download Queue</h2>
      <div class="flex">
        <button class="btn" onclick="pauseQueue()">⏸ Pause Queue</button>
        <button class="btn btn-primary" onclick="resumeQueue()">▶ Resume Queue</button>
        <button class="btn" onclick="reload()">↻ Refresh</button>
      </div>
    </div>

    <div class="card">
      <div class="stats-grid" style="margin-bottom:16px;">
        <div class="stat"><div class="value">{stats.get('active_downloads', 0)}</div><div class="label">Active</div></div>
        <div class="stat"><div class="value">{stats.get('queued', 0)}</div><div class="label">Queued</div></div>
      </div>
      {f'<table><thead><tr><th>File</th><th>Type</th><th>Status</th><th>Size</th><th>Progress</th><th>Speed</th><th></th></tr></thead><tbody>{rows}</tbody></table>' if rows else '<div class="empty">Queue is empty</div>'}
    </div>

    <script>
    function pause(id) {{ api('/api/pause/' + id, {{method:'POST'}}).then(r => {{if(r.ok) reload()}}); }}
    function resume(id) {{ api('/api/resume/' + id, {{method:'POST'}}).then(r => {{if(r.ok) reload()}}); }}
    function cancel(id) {{ if(!confirm('Cancel?')) return; api('/api/cancel/' + id, {{method:'POST'}}).then(r => {{if(r.ok) reload()}}); }}
    function retry(id) {{ api('/api/retry/' + id, {{method:'POST'}}).then(r => {{if(r.ok) reload()}}); }}
    function pauseQueue() {{ api('/api/queue/pause', {{method:'POST'}}).then(r => {{if(r.ok) toast('Queue paused'); reload()}}); }}
    function resumeQueue() {{ api('/api/queue/resume', {{method:'POST'}}).then(r => {{if(r.ok) toast('Queue resumed'); reload()}}); }}
    function reload() {{ window.location.reload(); }}
    setInterval(() => {{ window.location.reload(); }}, 5000);
    </script>
    """ + HTML_FOOT)


@app.get("/library", response_class=HTMLResponse)
def library_page(category: str = "", q: str = ""):
    """Library browser page."""
    m = _manager
    items = m.get_library(category=category, query=q, limit=200) if m else []

    cat_options = ""
    for cat in ["", "video", "music", "document", "image", "ebook", "archive", "software"]:
        sel = " selected" if cat == category else ""
        cat_options += f'<option value="{cat}"{sel}>{cat or "All"}</option>'

    rows = ""
    for item in items:
        rows += f"""<tr>
          <td>{item.get('filename', '')[:45]}</td>
          <td><span class="badge badge-{item.get('category', 'other')}">{item.get('category', 'other')}</span></td>
          <td>{_fmt_size(item.get('size_bytes', 0))}</td>
          <td>{item.get('artist', '') or '—'}</td>
          <td>
            <input type="number" min="1" max="5" value="{item.get('rating', 0)}"
                   onchange="rate('{item.get('id', '')}', this.value)" style="width:60px;">
          </td>
        </tr>"""

    return HTMLResponse(HTML_HEAD + f"""
    <div class="card">
      <h2>Media Library</h2>
      <div class="flex" style="margin-top:8px;">
        <input id="lq" placeholder="Search library..." value="{q}" style="flex:1;">
        <select id="lc">{cat_options}</select>
        <button class="btn btn-primary" onclick="searchLib()">🔍 Search</button>
        <button class="btn" onclick="scanLib()">🔎 Scan</button>
      </div>
    </div>

    <div class="card">
      {f'<table><thead><tr><th>Filename</th><th>Type</th><th>Size</th><th>Artist</th><th>Rating</th></tr></thead><tbody>{rows}</tbody></table>' if rows else '<div class="empty">Library is empty. Add downloads or scan existing files.</div>'}
    </div>

    <script>
    function searchLib() {{
      const q = document.getElementById('lq').value;
      const c = document.getElementById('lc').value;
      window.location.href = '/library?q=' + encodeURIComponent(q) + '&category=' + c;
    }}
    function scanLib() {{
      api('/api/scan', {{method:'POST'}}).then(r => {{ if(r.ok) toast('Scanned: ' + r.new_files + ' new files', 'success'); reload(); }});
    }}
    async function rate(id, val) {{
      await api('/api/library/update', {{method:'POST', body: JSON.stringify({{id, rating: parseInt(val)}})}});
      toast('Rating updated', 'success');
    }}
    function reload() {{ window.location.reload(); }}
    </script>
    """ + HTML_FOOT)


@app.get("/history", response_class=HTMLResponse)
def history_page():
    """Download history page."""
    m = _manager
    items = m.get_history(limit=100) if m else []

    rows = ""
    for item in items:
        status = item.get("status", "")
        status_class = "status-" + status.replace(" ", "")
        rows += f"""<tr>
          <td>{item.get('filename', '')[:45]}</td>
          <td><span class="badge badge-{item.get('category', 'other')}">{item.get('category', 'other')}</span></td>
          <td class="{status_class}">{status}</td>
          <td>{_fmt_size(item.get('size_bytes', 0))}</td>
          <td>{_fmt_time(item.get('completed', 0))}</td>
        </tr>"""

    return HTMLResponse(HTML_HEAD + f"""
    <div class="card">
      <h2>Download History</h2>
    </div>
    <div class="card">
      {f'<table><thead><tr><th>File</th><th>Type</th><th>Status</th><th>Size</th><th>Completed</th></tr></thead><tbody>{rows}</tbody></table>' if rows else '<div class="empty">No download history yet</div>'}
    </div>
    """ + HTML_FOOT)


# ═══════════════════════════════════════════════════════════════════════
# Utility
# ═══════════════════════════════════════════════════════════════════════

def _get_engine() -> Optional[DownloadEngine]:
    """Get the singleton download engine."""
    m = _manager
    if m and m._downloader:
        return m._downloader
    return None


def _task_to_dict(t: Any) -> Dict[str, Any]:
    """Convert a DownloadTask to a dict for JSON serialization."""
    return {
        "id": t.id,
        "url": t.url,
        "filename": t.filename,
        "category": t.category.value if hasattr(t.category, "value") else str(t.category),
        "status": t.status.value if hasattr(t.status, "value") else str(t.status),
        "protocol": t.protocol,
        "size_bytes": t.size_bytes,
        "downloaded_bytes": t.downloaded_bytes,
        "speed_bps": t.speed_bps,
        "progress": t.progress,
        "priority": t.priority,
        "error": t.error,
        "eta_seconds": t.eta_seconds,
        "created": t.created,
        "completed": t.completed,
    }


def _fmt_size(bytes_val: int) -> str:
    """Format bytes to human-readable string."""
    if not bytes_val:
        return ""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} PB"


def _fmt_speed(bps: float) -> str:
    """Format speed to human-readable."""
    if not bps:
        return ""
    return _fmt_size(int(bps)) + "/s"


def _fmt_time(ts: float) -> str:
    """Format timestamp to date string."""
    if not ts:
        return ""
    import datetime
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


# ═══════════════════════════════════════════════════════════════════════
# CLI Runner
# ═══════════════════════════════════════════════════════════════════════

def main(host: str = "0.0.0.0", port: int = 8900) -> int:
    """Run the Simple Internet web server."""
    import uvicorn
    print(f"🌐 Simple Internet Dashboard: http://{host}:{port}")
    print(f"📡 API: http://{host}:{port}/api/health")
    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
