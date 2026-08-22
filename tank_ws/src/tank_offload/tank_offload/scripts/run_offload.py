"""Standalone launcher for the tank_offload FastAPI server.

Examples
--------
::

    # production \u2014 ROS bridge thread + bearer auth
    TANK_API_KEY=wJALw9x\u2026 \\
    TANK_NEXTCLOUD_URL=https://vps.x/remote.php/dav/files/alice \\
    TANK_NEXTCLOUD_USER=alice \\
    TANK_NEXTCLOUD_PASSWORD=\u2026 \\
    python3 -m tank_offload.scripts.run_offload

    # bench \u2014 no auth, no ROS, on a different port
    python3 -m tank_offload.scripts.run_offload --port 8088 --open --no-ros
"""
from __future__ import annotations

import argparse
import os
import sys


def main(argv: list = None) -> int:
    parser = argparse.ArgumentParser(
        description="Launch the tank_offload FastAPI server.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8085)
    parser.add_argument("--no-ros", action="store_true",
                        help="Skip ROS bridge thread \u2014 bench-only.")
    parser.add_argument("--open", action="store_true",
                        help="Disable bearer auth (TANK_OFFLOAD_OPEN=1).")
    parser.add_argument("--log-level", default="info")
    args = parser.parse_args(argv)

    if args.no_ros:
        os.environ["TANK_OFFLOAD_NO_ROS"] = "1"
    if args.open:
        os.environ["TANK_OFFLOAD_OPEN"] = "1"

    try:
        import uvicorn                                  # type: ignore[import-not-found]
    except ImportError:
        print("uvicorn not installed; pip install 'tank_offload[server]'",
              file=sys.stderr)
        return 2
    uvicorn.run("tank_offload.app:app",
                host=args.host, port=args.port,
                log_level=args.log_level)
    return 0


if __name__ == "__main__":                                # pragma: no cover
    raise SystemExit(main())
