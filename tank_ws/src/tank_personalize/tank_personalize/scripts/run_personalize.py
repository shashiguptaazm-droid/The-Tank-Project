"""Standalone CLI launcher for the tank_personalize FastAPI server.

This is the "scripts first" entry point (STATUS.md §9 design rule 8) —
it lets you bench-test the server without a ROS 2 environment.

Examples
--------
::

    # local Jetson, with full auth + ROS bridge thread
    TANK_API_KEY=wJALw9x...
    python3 -m tank_personalize.scripts.run_personalize

    # headless bench, no auth, no ROS
    python3 -m tank_personalize.scripts.run_personalize --open --no-ros \\
        --port 8088

    # query the dashboard bundle for debugging
    python3 -m tank_personalize.scripts.preview_prompt
"""
from __future__ import annotations

import argparse
import os
import sys


def main(argv: list = None) -> int:
    parser = argparse.ArgumentParser(
        description="Launch the tank_personalize FastAPI server "
                    "(persona + preferences + memory + dashboard).")
    parser.add_argument("--host", default="0.0.0.0",
                        help="Bind address (default %(default)s)")
    parser.add_argument("--port", type=int, default=8084,
                        help="TCP port (default %(default)s)")
    parser.add_argument("--no-ros", action="store_true",
                        help="Skip ROS bridge thread — bench-only flag.")
    parser.add_argument("--open", action="store_true",
                        help="Disable bearer auth (TANK_PERSONALIZE_OPEN=1).")
    parser.add_argument("--log-level", default="info",
                        help="uvicorn log level (default %(default)s)")
    args = parser.parse_args(argv)

    if args.no_ros:
        os.environ["TANK_PERSONALIZE_NO_ROS"] = "1"
    if args.open:
        os.environ["TANK_PERSONALIZE_OPEN"] = "1"

    try:
        import uvicorn                                  # type: ignore[import-not-found]
    except ImportError:
        print("uvicorn not installed; install with "
              "`pip install 'tank_personalize[server]'`", file=sys.stderr)
        return 2

    uvicorn.run("tank_personalize.app:app",
                host=args.host, port=args.port,
                log_level=args.log_level)
    return 0


if __name__ == "__main__":                                # pragma: no cover
    raise SystemExit(main())
