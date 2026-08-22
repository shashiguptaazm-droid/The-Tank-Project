"""CLI first-pass for tank_command_bridge (per STATUS.md design rule 8).

Spins up the FastAPI app with a given port + auth. ``--bench`` flag
forces the no-rclpy path so we can test on a Jetson dev machine or in a
CI sandbox without ROS installed.

Usage::

    # production (Jetson)
    TANK_API_KEY=sk-live-... python3 -m tank_command_bridge.scripts.run_bridge --port 8082

    # bench (no rclpy, no real publishers)
    python3 -m tank_command_bridge.scripts.run_bridge --bench --port 8082
"""
from __future__ import annotations

import argparse
import os
import sys


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=8082)
    p.add_argument("--bench", action="store_true",
                   help="force the rclpy-stub path (no real publishers)")
    p.add_argument("--reload", action="store_true")
    args = p.parse_args(argv)

    if args.bench:
        os.environ.setdefault("TANK_API_KEYS", '{"bench-key":"admin"}')
        print("tank_command_bridge CLI — bench mode (no rclpy)", flush=True)
    else:
        if not os.environ.get("TANK_API_KEYS") and not os.environ.get("TANK_API_KEY"):
            print("WARNING: no TANK_API_KEYS / TANK_API_KEY set; the "
                  "bridge will refuse every command until you set one.",
                  flush=True)
        print(f"tank_command_bridge CLI — uvicorn on "
              f"{args.host}:{args.port}", flush=True)

    import uvicorn
    uvicorn.run(
        "tank_command_bridge.app:app",
        host=args.host, port=args.port,
        reload=args.reload, log_level="info",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
