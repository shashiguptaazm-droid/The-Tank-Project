"""``tank-offload`` CLI \u2014 operator dashboard in a terminal.

The CLI prefers the HTTP API when reachable (so all auth + state
visibility flows through ``secrets.compare_digest``). For the
``dry-run`` subcommand it falls back to a direct policy walk so the
user can introspect *what would have moved* even when the daemon
isn't running.

Usage
-----
::

    # gauge current state
    tank-offload status
    # walk the policy without moving anything
    tank-offload dry-run
    # force a non-priority sweep now
    tank-offload trigger
    # change the emergency threshold at runtime
    tank-offload threshold set 80
    # inspect the credential setup (no secrets logged)
    tank-offload credentials
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from typing import Any, Dict, List, Optional

# Re-use shared helpers when running offline (dry-run path doesn't
# need the FastAPI server).
from tank_offload.policy import ALL_KINDS, OffloadPolicy, PolicyConfig
from tank_offload.offload_store import OffloadStore
from tank_offload import __version__


DEFAULT_BASE = os.environ.get("TANK_OFFLOAD_BASE_URL",
                              "http://127.0.0.1:8085")
DEFAULT_DB = os.environ.get("TANK_OFFLOAD_DB",
                             "/root/the tank project/tank_ws/data/offload_manifest.db")


def _request(method: str, path: str, *, token: Optional[str],
             body: Optional[Dict] = None,
             timeout: float = 10.0) -> Dict[str, Any]:
    import httpx  # type: ignore[import-not-found]
    url = f"{DEFAULT_BASE.rstrip('/')}{path}"
    headers: Dict[str, str] = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    kwargs: Dict[str, Any] = {"timeout": timeout}
    if body is not None:
        kwargs["json"] = body
    with httpx.Client() as client:
        r = client.request(method, url, headers=headers, **kwargs)
    if r.status_code >= 400:
        print(f"HTTP {r.status_code}: {r.text}", file=sys.stderr)
        sys.exit(1)
    if r.headers.get("content-type", "").startswith("application/json"):
        return r.json()
    return {"raw": r.text}


def _resolve_token(args: argparse.Namespace) -> Optional[str]:
    return (args.token or os.environ.get("TANK_API_KEY")
            or os.environ.get("TANK_OFFLOAD_TOKEN"))


# --------------------------------------------------------------------------- #
# Subcommands
# --------------------------------------------------------------------------- #

def cmd_status(args: argparse.Namespace) -> int:
    body = _request("GET", "/api/offload/status",
                    token=_resolve_token(args))
    print(json.dumps(body, indent=2, sort_keys=True))
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    body = _request("GET", f"/api/offload/history?limit={int(args.limit)}",
                    token=_resolve_token(args))
    print(json.dumps(body, indent=2, sort_keys=True))
    return 0


def cmd_manifest(args: argparse.Namespace) -> int:
    body = _request("GET", f"/api/offload/manifest?limit={int(args.limit)}",
                    token=_resolve_token(args))
    print(json.dumps(body, indent=2, sort_keys=True))
    return 0


def cmd_deadletter(args: argparse.Namespace) -> int:
    body = _request("GET", f"/api/offload/deadletter?limit={int(args.limit)}",
                    token=_resolve_token(args))
    print(json.dumps(body, indent=2, sort_keys=True))
    return 0


def cmd_credentials(args: argparse.Namespace) -> int:
    body = _request("GET", "/api/offload/credentials",
                    token=_resolve_token(args))
    print(json.dumps(body, indent=2, sort_keys=True))
    return 0


def cmd_threshold_get(args: argparse.Namespace) -> int:
    body = _request("GET", "/api/offload/threshold",
                    token=_resolve_token(args))
    print(json.dumps(body, indent=2, sort_keys=True))
    return 0


def cmd_threshold_set(args: argparse.Namespace) -> int:
    payload = {"threshold_pct": float(args.value)}
    if args.recover is not None:
        payload["recover_pct"] = float(args.recover)
    body = _request("PUT", "/api/offload/threshold",
                    token=_resolve_token(args), body=payload)
    print(json.dumps(body, indent=2, sort_keys=True))
    return 0


def cmd_trigger(args: argparse.Namespace) -> int:
    path = ("/api/offload/trigger" if not args.emergency
            else "/api/offload/trigger_emergency")
    body = _request("POST", path, token=_resolve_token(args))
    print(json.dumps(body, indent=2, sort_keys=True))
    return 0


def cmd_dry_run(args: argparse.Namespace) -> int:
    """Walk the policy locally; does NOT talk to the server.

    This is the only subcommand that works when the server is
    unreachable \u2014 e.g. on a freshly-flashed Pi before the user
    configures the Nextcloud credentials. Useful for tuning
    thresholds + ages without burning bandwidth.
    """
    policy = OffloadPolicy(PolicyConfig())
    cfg = policy.config
    by_kind = policy.dry_run()
    grand_total_bytes = 0
    grand_total_files = 0
    for kind in ALL_KINDS:
        cs = by_kind[kind]
        print(f"\n=== {kind}  ({len(cs)} file"
              f"{'s' if len(cs) != 1 else ''}) ===")
        if not cs:
            print("  (none)")
            continue
        for c in cs:
            age_days = (args.now - c.mtime) / 86400.0
            print(f"  {c.size_bytes:>10} B  age={age_days:5.1f}d  "
                  f"{c.path}")
            grand_total_bytes += c.size_bytes
        grand_total_files += len(cs)
    print(f"\n--- summary: {grand_total_files} files, "
          f"{grand_total_bytes} bytes "
          f"(\u2248 {grand_total_bytes / (1024 * 1024):.1f} MiB) ---")
    print(f"policy: recordings>{cfg.recording_max_age_days:.0f}d, "
          f"logs>{cfg.log_min_bytes} B, "
          f"data>{cfg.db_snapshot_max_age_days:.0f}d")
    return 0


def cmd_health(args: argparse.Namespace) -> int:
    body = _request("GET", "/api/health", token=None)
    print(json.dumps(body, indent=2, sort_keys=True))
    return 0


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=("tank-offload operator CLI. Hits the daemon "
                     "over HTTP via the TANK_API_KEY bearer; "
                     "dry-run works offline."))
    p.add_argument("--base", default=DEFAULT_BASE,
                   help="Daemon base URL (default %(default)s)")
    p.add_argument("--token", default=None,
                   help="Bearer token (defaults to TANK_API_KEY env)")
    p.add_argument("--version", action="store_true",
                   help="Print installed version and exit")

    sub = p.add_subparsers(dest="cmd", required=False)

    sub.add_parser("status", help="Show current disk % + manifest counts")
    sub.add_parser("health", help="Pings the daemon's /api/health")

    h = sub.add_parser("history", help="Recent uploaded items")
    h.add_argument("--limit", type=int, default=50)
    m = sub.add_parser("manifest", help="All items currently on the VPS")
    m.add_argument("--limit", type=int, default=200)
    d = sub.add_parser("deadletter", help="Items that exhausted retries")
    d.add_argument("--limit", type=int, default=100)
    sub.add_parser("credentials", help="Show redacted credential check")

    g = sub.add_parser("threshold", help="Get / set the emergency threshold")
    gsub = g.add_subparsers(dest="threshold_action", required=True)
    gsub.add_parser("get", help="Print current threshold")
    s = gsub.add_parser("set", help="Set threshold")
    s.add_argument("value", type=float,
                   help="Emergency threshold % (e.g. 80)")
    s.add_argument("--recover", type=float, default=None,
                   help="Recovery % (must be < threshold; default unchanged)")

    t = sub.add_parser("trigger", help="Schedule a sweep / emergency now")
    t.add_argument("--emergency", action="store_true",
                   help="Bypass the threshold + queue an emergency sweep")

    dr = sub.add_parser("dry-run",
                         help="Walk the policy offline (no side-effects)")
    dr.add_argument("--now", type=float, default=None,
                    help="Override wall-clock for reproducibility tests")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(f"tank-offload {__version__}")
        return 0
    if not args.cmd:
        parser.print_help()
        return 0

    dispatch = {
        "status": cmd_status,
        "history": cmd_history,
        "manifest": cmd_manifest,
        "deadletter": cmd_deadletter,
        "credentials": cmd_credentials,
        "trigger": cmd_trigger,
        "dry-run": cmd_dry_run,
        "health": cmd_health,
        "threshold": _dispatch_threshold,
    }
    fn = dispatch.get(args.cmd)
    if fn is None:
        parser.print_help()
        return 2
    return fn(args)


def _dispatch_threshold(args: argparse.Namespace) -> int:
    if args.threshold_action == "get":
        return cmd_threshold_get(args)
    if args.threshold_action == "set":
        return cmd_threshold_set(args)
    print("unknown threshold action", file=sys.stderr)
    return 2


if __name__ == "__main__":                                # pragma: no cover
    raise SystemExit(main())
