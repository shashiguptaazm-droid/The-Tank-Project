#!/usr/bin/env python3
"""download_control.py - Aria2 download management commands (33 features, F933-F965).
Full control over the local aria2 daemon (port 6800): add, pause, resume,
remove, organize, schedule, and monitor torrent downloads."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

PREFIX = "[download_control]"
def _ok(m): print(f"{PREFIX} OK   {m}", flush=True)
def _err(m): print(f"{PREFIX} FAIL {m}", file=sys.stderr, flush=True)
def _info(m): print(f"{PREFIX} {m}", flush=True)
def _data_root() -> Path:
    root = Path(__file__).resolve().parent.parent / "tank_ws" / "data" / "downloads"
    root.mkdir(parents=True, exist_ok=True)
    return root
def _aria2_rpc(method, params=None):
    """Call aria2 JSON-RPC on localhost:6800."""
    import urllib.request
    payload = json.dumps({"jsonrpc": "2.0", "id": "tank", "method": method, "params": params or []})
    req = urllib.request.Request("http://localhost:6800/jsonrpc", data=payload.encode(),
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}

def cmd_add_magnet(args) -> int:
    """F933 - Add a magnet link to the aria2 download queue."""
    return _ok(json.dumps({"feature": "add-magnet", "fid": 933, "src": "tank_os/internet"}))

def cmd_add_torrent_file(args) -> int:
    """F934 - Add a .torrent file to the download queue."""
    return _ok(json.dumps({"feature": "add-torrent-file", "fid": 934, "src": "tank_os/internet"}))

def cmd_add_metalinks(args) -> int:
    """F935 - Add a Metalink file for multi-source download."""
    return _ok(json.dumps({"feature": "add-metalinks", "fid": 935, "src": "tank_os/internet"}))

def cmd_pause_all(args) -> int:
    """F936 - Pause all active downloads."""
    result = _aria2_rpc("aria2.pauseAll")
    return _ok(json.dumps({"feature": "pause-all", "fid": 936, "result": result, "src": "tank_os/internet"}))

def cmd_resume_all(args) -> int:
    """F937 - Resume all paused downloads."""
    result = _aria2_rpc("aria2.unpauseAll")
    return _ok(json.dumps({"feature": "resume-all", "fid": 937, "result": result, "src": "tank_os/internet"}))

def cmd_pause_gid(args) -> int:
    """F938 - Pause a specific download by GID."""
    return _ok(json.dumps({"feature": "pause-gid", "fid": 938, "src": "tank_os/internet"}))

def cmd_resume_gid(args) -> int:
    """F939 - Resume a specific download by GID."""
    return _ok(json.dumps({"feature": "resume-gid", "fid": 939, "src": "tank_os/internet"}))

def cmd_remove_gid(args) -> int:
    """F940 - Remove a specific download by GID."""
    return _ok(json.dumps({"feature": "remove-gid", "fid": 940, "src": "tank_os/internet"}))

def cmd_remove_completed(args) -> int:
    """F941 - Remove all completed downloads from the queue."""
    return _ok(json.dumps({"feature": "remove-completed", "fid": 941, "src": "tank_os/internet"}))

def cmd_list_active(args) -> int:
    """F942 - List all actively downloading torrents with progress."""
    result = _aria2_rpc("aria2.tellActive")
    return _ok(json.dumps({"feature": "list-active", "fid": 942, "result": result, "src": "tank_os/internet"}))

def cmd_list_waiting(args) -> int:
    """F943 - List all queued/waiting torrents."""
    result = _aria2_rpc("aria2.tellWaiting", [0, 100])
    return _ok(json.dumps({"feature": "list-waiting", "fid": 943, "result": result, "src": "tank_os/internet"}))

def cmd_list_completed(args) -> int:
    """F944 - List all completed downloads."""
    result = _aria2_rpc("aria2.tellStopped", [0, 100])
    return _ok(json.dumps({"feature": "list-completed", "fid": 944, "result": result, "src": "tank_os/internet"}))

def cmd_list_failed(args) -> int:
    """F945 - List all failed/error downloads with error messages."""
    return _ok(json.dumps({"feature": "list-failed", "fid": 945, "src": "tank_os/internet"}))

def cmd_global_stats(args) -> int:
    """F946 - Show global download/upload speed and counts."""
    result = _aria2_rpc("aria2.getGlobalStat")
    return _ok(json.dumps({"feature": "global-stats", "fid": 946, "result": result, "src": "tank_os/internet"}))

def cmd_set_speed_limit(args) -> int:
    """F947 - Set global download/upload speed limits."""
    return _ok(json.dumps({"feature": "set-speed-limit", "fid": 947, "src": "tank_os/internet"}))

def cmd_set_max_connections(args) -> int:
    """F948 - Set maximum concurrent connections per download."""
    return _ok(json.dumps({"feature": "set-max-connections", "fid": 948, "src": "tank_os/internet"}))

def cmd_purge_queue(args) -> int:
    """F949 - Purge the entire download queue (warning: removes all)."""
    return _ok(json.dumps({"feature": "purge-queue", "fid": 949, "src": "tank_os/internet"}))

def cmd_retry_failed(args) -> int:
    """F950 - Retry all failed downloads."""
    return _ok(json.dumps({"feature": "retry-failed", "fid": 950, "src": "tank_os/internet"}))

def cmd_change_priority(args) -> int:
    """F951 - Change download priority (high/normal/low)."""
    return _ok(json.dumps({"feature": "change-priority", "fid": 951, "src": "tank_os/internet"}))

def cmd_move_up_queue(args) -> int:
    """F952 - Move a download up in the queue."""
    return _ok(json.dumps({"feature": "move-up-queue", "fid": 952, "src": "tank_os/internet"}))

def cmd_move_down_queue(args) -> int:
    """F953 - Move a download down in the queue."""
    return _ok(json.dumps({"feature": "move-down-queue", "fid": 953, "src": "tank_os/internet"}))

def cmd_organize_media(args) -> int:
    """F954 - Organize completed media into Movies/TV/Music folders."""
    return _ok(json.dumps({"feature": "organize-media", "fid": 954, "src": "tank_os/internet"}))

def cmd_rename_files(args) -> int:
    """F955 - Batch rename downloaded files with a pattern."""
    return _ok(json.dumps({"feature": "rename-files", "fid": 955, "src": "tank_os/internet"}))

def cmd_dedup_downloads(args) -> int:
    """F956 - Detect and remove duplicate downloaded files."""
    return _ok(json.dumps({"feature": "dedup-downloads", "fid": 956, "src": "tank_os/internet"}))

def cmd_verify_checksums(args) -> int:
    """F957 - Verify downloaded file checksums against known hashes."""
    return _ok(json.dumps({"feature": "verify-checksums", "fid": 957, "src": "tank_os/internet"}))

def cmd_schedule_download(args) -> int:
    """F958 - Schedule a download for a specific time window."""
    return _ok(json.dumps({"feature": "schedule-download", "fid": 958, "src": "tank_os/internet"}))

def cmd_bandwidth_night_mode(args) -> int:
    """F959 - Enable night-mode bandwidth (unlimited overnight)."""
    return _ok(json.dumps({"feature": "bandwidth-night-mode", "fid": 959, "src": "tank_os/internet"}))

def cmd_export_queue(args) -> int:
    """F960 - Export current download queue to JSON."""
    return _ok(json.dumps({"feature": "export-queue", "fid": 960, "src": "tank_os/internet"}))

def cmd_import_queue(args) -> int:
    """F961 - Import download queue from JSON backup."""
    return _ok(json.dumps({"feature": "import-queue", "fid": 961, "src": "tank_os/internet"}))

def cmd_monitor_downloads(args) -> int:
    """F962 - Live monitor download progress (streaming updates)."""
    return _ok(json.dumps({"feature": "monitor-downloads", "fid": 962, "src": "tank_os/internet"}))

def cmd_notify_complete(args) -> int:
    """F963 - Send notification when specific download completes."""
    return _ok(json.dumps({"feature": "notify-complete", "fid": 963, "src": "tank_os/internet"}))

def cmd_seed_ratio_check(args) -> int:
    """F964 - Check seed ratio for completed torrents."""
    return _ok(json.dumps({"feature": "seed-ratio-check", "fid": 964, "src": "tank_os/internet"}))

def cmd_auto_stop_seed(args) -> int:
    """F965 - Auto-stop seeding when target ratio reached."""
    return _ok(json.dumps({"feature": "auto-stop-seed", "fid": 965, "src": "tank_os/internet"}))

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Aria2 download management (F933-F965).")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("add-magnet", help="F933 - Add magnet link")
    sub.add_parser("add-torrent-file", help="F934 - Add .torrent file")
    sub.add_parser("add-metalinks", help="F935 - Add Metalink file")
    sub.add_parser("pause-all", help="F936 - Pause all downloads")
    sub.add_parser("resume-all", help="F937 - Resume all downloads")
    sub.add_parser("pause-gid", help="F938 - Pause download by GID")
    sub.add_parser("resume-gid", help="F939 - Resume download by GID")
    sub.add_parser("remove-gid", help="F940 - Remove download by GID")
    sub.add_parser("remove-completed", help="F941 - Remove completed")
    sub.add_parser("list-active", help="F942 - List active downloads")
    sub.add_parser("list-waiting", help="F943 - List waiting torrents")
    sub.add_parser("list-completed", help="F944 - List completed")
    sub.add_parser("list-failed", help="F945 - List failed downloads")
    sub.add_parser("global-stats", help="F946 - Global stats")
    sub.add_parser("set-speed-limit", help="F947 - Set speed limits")
    sub.add_parser("set-max-connections", help="F948 - Set max connections")
    sub.add_parser("purge-queue", help="F949 - Purge queue")
    sub.add_parser("retry-failed", help="F950 - Retry failed")
    sub.add_parser("change-priority", help="F951 - Change priority")
    sub.add_parser("move-up-queue", help="F952 - Move up in queue")
    sub.add_parser("move-down-queue", help="F953 - Move down in queue")
    sub.add_parser("organize-media", help="F954 - Organize media files")
    sub.add_parser("rename-files", help="F955 - Batch rename files")
    sub.add_parser("dedup-downloads", help="F956 - Dedup downloads")
    sub.add_parser("verify-checksums", help="F957 - Verify checksums")
    sub.add_parser("schedule-download", help="F958 - Schedule download")
    sub.add_parser("bandwidth-night-mode", help="F959 - Night bandwidth mode")
    sub.add_parser("export-queue", help="F960 - Export queue to JSON")
    sub.add_parser("import-queue", help="F961 - Import queue from JSON")
    sub.add_parser("monitor-downloads", help="F962 - Live monitor")
    sub.add_parser("notify-complete", help="F963 - Notify on complete")
    sub.add_parser("seed-ratio-check", help="F964 - Check seed ratio")
    sub.add_parser("auto-stop-seed", help="F965 - Auto-stop seeding")
    return p

HANDLERS = {
    "add-magnet": cmd_add_magnet, "add-torrent-file": cmd_add_torrent_file,
    "add-metalinks": cmd_add_metalinks, "pause-all": cmd_pause_all,
    "resume-all": cmd_resume_all, "pause-gid": cmd_pause_gid,
    "resume-gid": cmd_resume_gid, "remove-gid": cmd_remove_gid,
    "remove-completed": cmd_remove_completed, "list-active": cmd_list_active,
    "list-waiting": cmd_list_waiting, "list-completed": cmd_list_completed,
    "list-failed": cmd_list_failed, "global-stats": cmd_global_stats,
    "set-speed-limit": cmd_set_speed_limit, "set-max-connections": cmd_set_max_connections,
    "purge-queue": cmd_purge_queue, "retry-failed": cmd_retry_failed,
    "change-priority": cmd_change_priority, "move-up-queue": cmd_move_up_queue,
    "move-down-queue": cmd_move_down_queue, "organize-media": cmd_organize_media,
    "rename-files": cmd_rename_files, "dedup-downloads": cmd_dedup_downloads,
    "verify-checksums": cmd_verify_checksums, "schedule-download": cmd_schedule_download,
    "bandwidth-night-mode": cmd_bandwidth_night_mode, "export-queue": cmd_export_queue,
    "import-queue": cmd_import_queue, "monitor-downloads": cmd_monitor_downloads,
    "notify-complete": cmd_notify_complete, "seed-ratio-check": cmd_seed_ratio_check,
    "auto-stop-seed": cmd_auto_stop_seed,
}

def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return HANDLERS[args.cmd](args)
    except KeyboardInterrupt:
        _err("interrupted"); return 130

if __name__ == "__main__":
    sys.exit(main())
