"""ROS 2 node that *listens to* every notable system-level topic and
writes each payload into :class:`tank_log.log_store.LogStore`.

Note: this is an *event-stream* logger, not a vector store. It subscribes
to a curated list of small, structured topics. We deliberately skip
``/camera/image_raw`` and ``/scan`` because writing image-matrix bytes
to sqlite would balloon the database.

Topic list (defaults; all settable via the ``topics_to_listen`` parameter,
which is a JSON list of strings):

* ``/wake_detected``                      std_msgs/Bool
* ``/wake_confidence``                    std_msgs/Float32
* ``/intent_text``                        std_msgs/String
* ``/assistant_text``                     std_msgs/String
* ``/assistant/context``                  std_msgs/String
* ``/cmd_vel``                            geometry_msgs/Twist
* ``/estop``                              std_msgs/Bool
* ``/security/events/motion``             std_msgs/String
* ``/security/recording_path``            std_msgs/String
* ``/battery/state``                      sensor_msgs/BatteryState
* ``/health/state``                       std_msgs/String
* ``/health/ok``                          std_msgs/Bool
* ``/dock/pose``                          geometry_msgs/PoseStamped
* ``/dock/charge_cmd``                    std_msgs/Bool
* ``/memory/status``                      std_msgs/String
* ``/memory/recall_result``               std_msgs/String
* ``/meta/code_search_result``            std_msgs/String
* ``/meta/decision_search_result``        std_msgs/String
* ``/meta/decision_append_result``        std_msgs/String

Parameters
    db_path          str   default ``<repo>/tank_ws/data/log.db``
    topics_to_listen str   default ``''``; if non-empty must be JSON list of topic names
    source_label     str   default ``log_node``
"""
from __future__ import annotations

import json
import os
import threading
import time
from typing import List, Optional

import rclpy
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from std_msgs.msg import Bool, Float32, String

from .log_store import LogStore


QOS = QoSProfile(depth=50, reliability=ReliabilityPolicy.RELIABLE)

DEFAULT_TOPICS = [
    "/wake_detected",
    "/wake_confidence",
    "/intent_text",
    "/assistant_text",
    "/assistant/context",
    "/cmd_vel",
    "/estop",
    "/security/events/motion",
    "/security/recording_path",
    "/battery/state",
    "/health/state",
    "/health/ok",
    "/dock/pose",
    "/dock/charge_cmd",
    "/memory/status",
    "/memory/recall_result",
    "/memory/recent_snapshot",
    "/meta/code_search_result",
    "/meta/decision_search_result",
    "/meta/decision_append_result",
    "/meta/hardware_lookup_result",
]


class LogNode(Node):
    def __init__(self, store: Optional[LogStore] = None,
                 topics: Optional[List[str]] = None) -> None:
        super().__init__("log_node")
        self._declare_params()
        db_path = str(self.get_parameter("db_path").value)
        self._store = store or LogStore(db_path=db_path)
        self._source = str(self.get_parameter("source_label").value)
        self._lock = threading.Lock()
        self._truncation_warns: int = 0    # monotonic counter for /log/stats

        # Load topic list — env-supplied override wins, else defaults.
        override = str(self.get_parameter("topics_to_listen").value or "")
        if override.strip():
            try:
                topics = json.loads(override)
            except Exception as exc:
                self.get_logger().warn(
                    f"topics_to_listen not JSON: {exc}; using defaults"
                )
                topics = None
        if topics is None:
            topics = list(DEFAULT_TOPICS)

        # Subscribe as std_msgs/String for every default topic — works
        # uniformly for the topics that are typed elsewhere too.
        self._subscribed_topics: List[str] = []
        cbg = MutuallyExclusiveCallbackGroup()
        for t in topics:
            try:
                self.create_subscription(
                    String, t,
                    lambda msg, _t=t: self._on_string(_t, msg),
                    QOS, callback_group=cbg,
                )
                self._subscribed_topics.append(t)
            except Exception as exc:
                self.get_logger().warn(f"could not subscribe {t}: {exc}")

        # Probe the live topic graph after subscriptions exist (deferred 1.0s)
        # so we can warn on subscribed-but-absent topics.
        self._probe_timer = self.create_timer(1.0, self._probe_topic_graph_once)

        # Health / tail publishers.
        self._stats_pub = self.create_publisher(String, "/log/stats", QOS)
        self._tail_pub = self.create_publisher(String, "/log/tail", QOS)
        self.create_timer(10.0, self._publish_stats)
        self.create_timer(2.0, self._publish_tail)

        self.get_logger().info(
            f"log_node ready — db={db_path} "
            f"subs={len(self._subscribed_topics)} "
            f"existing_logs={self._store.count()}"
        )

    def _declare_params(self) -> None:
        repo = "/root/the tank project"
        self.declare_parameter(
            "db_path", f"{repo}/tank_ws/data/log.db")
        self.declare_parameter("topics_to_listen", "")
        self.declare_parameter("source_label", "log_node")

    # ------------- subscriber helpers ----------------
    def _on_string(self, topic: str, msg: String) -> None:
        self._append(topic, "std_msgs/String", msg.data)

    def _append(self, topic: str, msgtype: str, payload) -> None:
        ts = time.time()
        try:
            truncated = self._store.append(
                ts=ts,
                topic=topic,
                msgtype=msgtype,
                source=self._source,
                payload=_safe_stringify(payload),
            )
            if truncated:
                with self._lock:
                    self._truncation_warns += 1
        except Exception as exc:
            self.get_logger().warn(f"append failed for {topic}: {exc}")

    # ------------- startup: probe graph ----------------
    def _probe_topic_graph_once(self) -> None:
        # Fire-and-forget one-shot probe and disable itself.
        try:
            self._probe_topic_graph_once.__func__
            self._probe_timer.cancel()
        except Exception:
            return
        try:
            present = {name for name, _types in self.get_topic_names_and_types()}
        except Exception as exc:
            self.get_logger().warn(f"topic graph probe failed: {exc}")
            return
        missing = [t for t in self._subscribed_topics if t not in present]
        if missing:
            self.get_logger().warn(
                f"{len(missing)}/{len(self._subscribed_topics)} subscribed "
                f"topics are absent from the live graph: {missing[:5]}{'...' if len(missing) > 5 else ''}"
            )
        else:
            self.get_logger().info(
                f"all {len(self._subscribed_topics)} subscribed topics are live"
            )

    # ------------- timers ----------------
    def _publish_stats(self) -> None:
        try:
            stats = self._store.health()
            stats["subscribed"] = len(self._subscribed_topics)
            with self._lock:
                stats["truncated_payloads"] = self._truncation_warns
            self._stats_pub.publish(String(data=json.dumps(stats)))
        except Exception as exc:
            self.get_logger().warn(f"stats publish failed: {exc}")

    def _publish_tail(self) -> None:
        try:
            rows = self._store.recent(limit=10)
            payload = json.dumps([r.to_dict() for r in rows])
            self._tail_pub.publish(String(data=payload))
        except Exception as exc:
            self.get_logger().warn(f"tail publish failed: {exc}")


def _safe_stringify(obj) -> str:
    try:
        return json.dumps(obj, default=str, ensure_ascii=False)
    except Exception:
        try:
            return str(obj)
        except Exception:
            return "<unserializable>"


def main(args=None) -> None:
    rclpy.init(args=args)
    node = LogNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            node._store.close()
        finally:
            node.destroy_node()
            rclpy.shutdown()


if __name__ == "__main__":
    main()
