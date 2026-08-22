"""CLI monkey-tester for tank_command_bridge.

Sends a representative request for every command in the manifest so a
human or CI check can smoke-test the bridge without a coding assistant.

Usage::

    python3 -m tank_command_bridge.scripts.test_commands --base http://localhost:8082 \\
        --token sk-live-...
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
import uuid


def _post(base: str, token: str, name: str, params: dict,
          timeout: float = 6.0) -> tuple:
    url = f"{base.rstrip('/')}/api/cmd/{name}"
    body = json.dumps({"audit_id": str(uuid.uuid4()),
                       "params": params}).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8") or "{}")


CANARY_PARAMS = {
    "estop":     {"state": True},
    "move":      {"vx": 0.1, "wz": 0.0, "duration_s": 0.4},
    "patrol":    {"mode": "stop"},
    "dock":      {"enable": False},
    "telemetry": {},
    "query":     {"kind": "knowledge", "text": "wiring", "k": 2},
    "capture":   {"max_px": 320},
    "chat":      {"text": "ping", "use_external_llm": False},
}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", default="http://localhost:8082")
    p.add_argument("--token", required=True,
                   help="TANK_API_KEY (env TANK_API_KEY will also work)")
    p.add_argument("--commands", nargs="*", default=None,
                   help="optional subset of commands to run")
    p.add_argument("--release_estop_at_end", action="store_true",
                   help="send estop state=false last so the bridge "
                        "won't leave the bench latched")
    args = p.parse_args(argv)

    print(f"test_commands against {args.base}", flush=True)
    cmds = args.commands or list(CANARY_PARAMS.keys())
    failures = 0
    for name in cmds:
        params = CANARY_PARAMS.get(name, {})
        status, body = _post(args.base, args.token, name, params)
        ok = 200 <= status < 300
        print(f"  {name:9s} -> {status} "
              f"{'OK' if ok else 'FAIL'}: {json.dumps(body)[:120]}",
              flush=True)
        if not ok:
            failures += 1

    if args.release_estop_at_end and "estop" in cmds:
        status, body = _post(args.base, args.token, "estop",
                              {"state": False})
        print(f"  estop    -> {status} release: "
              f"{json.dumps(body)[:120]}", flush=True)
        if status >= 300:
            failures += 1

    if failures:
        print(f"\n{failures} command(s) failed", flush=True)
        return 2
    print("\nall commands green", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
