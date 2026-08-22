"""ROS 2 surveillance fusion node.

Purpose
-------
Glues the pure-Python :mod:`tank_patrol.surveillance` to the live
ROS topic graph. Subscribes:

* ``/security/events/motion`` (std_msgs/String JSON; the output of
  :class:`tank_security.motion_node.MotionNode`)
* ``/patrol/state``          (std_msgs/String JSON; written by
  :class:`tank_patrol.patrol_node.PatrolNode`)

Publishes:

* ``/patrol/alert``                (std_msgs/String JSON; for dashboard)
* ``/security/events/intruder``     (std_msgs/String JSON; the same
  shape as ``/security/events/motion`` so
  :class:`tank_security.event_logger.EventLoggerNode` picks it up and
  appends to its JSONL + MQTT pipeline. No duplicate log infra.)

Also keeps a local ``AlertJournal`` rotating JSONL at
``/var/lib/tank/surveillance/<date>.jsonl`` so the CLI tool
``surveillance_review.py`` can review past events without going through
MQTT.

Active-edge distance
--------------------
``distance_from_active_edge_m`` defaults to ``OFF_PATH_SENTINEL_M``
(``999.0``) until ``/plan/current_edge`` publishes. The sentinel is a
*finite* float so the JSON serialisation downstream stays RFC-7159
compliant — ``float('inf')`` would otherwise be emitted as the literal
``Infinity`` token, which strict JSON parsers reject.
"""
from __future__ import annotations

import json
import threading
import time
from typing import Optional

import rclpy
from rclpy.callback_groups import (
    MutuallyExclusiveCallbackGroup,
    ReentrantCallbackGroup,
)
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from std_msgs.msg import String

from .surveillance import (
    AlertJournal,
    AlertSeverity,
    MotionObservation,
    OFF_PATH_SENTINEL_M,
    PatrolAlert,
    classify,
    severity,
    to_observation,
)


QOS = QoSProfile(depth=20, reliability=ReliabilityPolicy.RELIABLE)


class SurveillanceNode(Node):
    def __init__(self) -> None:
        super().__init__("surveillance_node")
        self._lock = threading.Lock()
        self._rate_limit_lock = threading.Lock()
        self._patrol_phase: str = "idle"
        self._patrol_position: tuple = (0.0, 0.0)
        self._journal = AlertJournal()
        self._last_alert_emit_ts_per_label: dict = {}

        # ---- pubs (default callback group, fine — they're cheap) ----
        self._alert_pub = self.create_publisher(String, "/patrol/alert", QOS)
        self._intruder_pub = self.create_publisher(
            String, "/security/events/intruder", QOS)

        # ---- subs: SEPARATE callback groups so a slow disk write in
        # the motion handler doesn't delay /patrol/state updates. Each
        # group is MutuallyExclusive within itself; with main()'s
        # MultiThreadedExecutor they run in parallel threads.
        motion_cbg = MutuallyExclusiveCallbackGroup()
        state_cbg = MutuallyExclusiveCallbackGroup()
        self.create_subscription(
            String, "/security/events/motion",
            self._on_motion, QOS, callback_group=motion_cbg)
        self.create_subscription(
            String, "/patrol/state",
            self._on_patrol_state, QOS, callback_group=state_cbg)

        self.get_logger().info("surveillance_node ready")

    def _on_motion(self, msg: String) -> None:
        try:
            payload = json.loads(msg.data)
        except Exception as exc:
            self.get_logger().warn(f"motion JSON parse: {exc}")
            return
        obs = to_observation(payload)
        if obs is None:
            return
        self._process_observation(obs)

    def _on_patrol_state(self, msg: String) -> None:
        try:
            payload = json.loads(msg.data)
        except Exception:
            return
        with self._lock:
            self._patrol_phase = str(payload.get("phase", "idle"))

    def _process_observation(self, obs: MotionObservation) -> None:
        with self._lock:
            phase = self._patrol_phase

        # Finite sentinel — never infinity. severity() compares > ON_PATH_M.
        distance = OFF_PATH_SENTINEL_M

        sev = severity(obs,
                       patrol_phase=phase,
                       distance_from_active_edge_m=distance)
        bucket = classify(obs)

        # Rate-limit per (label, phase). CRITICAL on a fresh "paused person"
        # burst MUST bypass so operators always see intruder alerts.
        key = f"{bucket}|{phase}"
        now = time.time()
        with self._rate_limit_lock:
            last = self._last_alert_emit_ts_per_label.get(key, 0.0)
            if (now - last) < 15.0 and sev != AlertSeverity.CRITICAL:
                return
            self._last_alert_emit_ts_per_label[key] = now

        alert = PatrolAlert(
            ts=now,
            severity=sev,
            label=bucket,
            observation=obs,
            patrol_phase=phase,
            distance_from_active_edge_m=distance,
            note="",
        )

        try:
            self._journal.append(alert)
        except Exception as exc:
            self.get_logger().warn(f"journal append failed: {exc}")

        self._alert_pub.publish(String(data=json.dumps(alert.to_dict())))

        if sev != AlertSeverity.INFO:
            self._intruder_pub.publish(String(data=json.dumps({
                "ts":           alert.ts,
                "source":       "surveillance_node",
                "category":     bucket,
                "severity":     sev.value,
                "patrol_phase": phase,
                "bbox":         list(obs.bbox),
                "confidence":   obs.confidence,
                "label":        obs.label,
            })))

    def destroy_node(self) -> None:
        try:
            self._journal.close()
        finally:
            super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = SurveillanceNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    import sys
    main(args=sys.argv)
