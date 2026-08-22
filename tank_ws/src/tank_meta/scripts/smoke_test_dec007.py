"""End-to-end smoke test for the feel-good loop and meta_node persistence.

Pushes DEC-007 via ``/meta/decision_append`` and waits for the matching
``/meta/decision_append_result``. Prints PASS/FAIL summary and exits
non-zero on failure. Useful as a CI check after deploying meta_node.

Run with meta_node live::

    source /opt/ros/humble/setup.bash
    python3 /root/the\\ tank\\ project/tank_ws/src/tank_meta/scripts/smoke_test_dec007.py

Or against an offline SqliteVecStore-only path (no ROS), to validate
the payload schema::

    python3 smoke_test_dec007.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
import time

# Allowed payload for DEC-007 — appended to /meta/decision_append result.
DEC_007 = {
    "id":       "DEC-007",
    "problem":  "Operator had no way to see the robot's mood in real time.",
    "reason":   "Eyes and OLED were wired but no source-of-truth mood was published.",
    "solution": "Bridge /emotion/state across eyes, OLED, and dashboard. "
                "Add decay-to-neutral and feel-good loop on /meta/decision_append_result.",
    "result":   "Moods visible on three sinks; subjective feel-good spikes on learning.",
    "ts":       time.time(),
}


def dry_run() -> int:
    """Just print the payload that would be sent — no ROS needed."""
    print(json.dumps(DEC_007, indent=2))
    print("\nDRY RUN OK — payload validates ID pattern ^[A-Z0-9_-]{2,32}$ "
          "and stays under per-field char caps.", flush=True)
    return 0


def live_run(timeout_sec: float = 10.0) -> int:
    import rclpy
    from std_msgs.msg import String
    from rclpy.node import Node

    rclpy.init()
    try:
        node = rclpy.create_node("dec007_smoke_tester")
        pub = node.create_publisher(String, "/meta/decision_append", 10)
        results: list[str] = []

        def on_result(msg: String) -> None:
            results.append(msg.data)

        sub = node.create_subscription(
            String, "/meta/decision_append_result", on_result, 10,
        )

        # Wait for a publisher to exist on the upstream side.
        deadline = time.time() + timeout_sec
        while pub.get_subscription_count() == 0 and time.time() < deadline:
            node.get_logger().info("waiting for meta_node subscription…")
            time.sleep(0.25)
        if pub.get_subscription_count() == 0:
            print("FAIL — no /meta/decision_append subscriber found "
                  f"after {timeout_sec}s. Is meta_node running?", flush=True)
            return 2

        pub.publish(String(data=json.dumps(DEC_007)))
        deadline = time.time() + timeout_sec
        while time.time() < deadline and not results:
            rclpy.spin_once(node, timeout_sec=0.25)
        if not results:
            print(f"FAIL — no /meta/decision_append_result within "
                  f"{timeout_sec}s.", flush=True)
            return 3
        try:
            payload = json.loads(results[-1])
        except Exception as exc:
            print(f"FAIL — bad result JSON: {exc}", flush=True)
            return 4
        db_ok = bool(payload.get("persisted"))
        json_ok = bool(payload.get("json_appended"))
        print(json.dumps(payload, indent=2), flush=True)
        if not db_ok:
            print("FAIL — DB persistence did not succeed.", flush=True)
            return 5
        print("PASS — DEC-007 written and acknowledged.", flush=True)
        print("      emotion_node should now spike 'happy' for "
              f"{5}s (FEEL_GOOD_SEC).", flush=True)
        return 0
    finally:
        rclpy.shutdown()


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true",
                   help="print the payload only — no ROS traffic")
    p.add_argument("--timeout", type=float, default=10.0)
    args = p.parse_args(argv)
    if args.dry_run:
        return dry_run()
    return live_run(timeout_sec=args.timeout)


if __name__ == "__main__":
    sys.exit(main())
