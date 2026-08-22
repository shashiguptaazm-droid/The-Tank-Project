"""Notification service — listens to /security/events/* topics and writes
an append-only JSONL log; broadcasts to MQTT if available.

Subscribes
    /security/events/motion        std_msgs/String
    /security/events/intruder      std_msgs/String
    /security/events/alert         std_msgs/String
    /security/events/dock_charge   std_msgs/String

Publishes
    /security/event_log       std_msgs/String    last appended line

Parameters
    log_path            str   default "/var/tank/logs/security.jsonl"
    mqtt_publish        bool  default False
    mqtt_broker         str   default "tcp://localhost:1883"
    mqtt_topic_prefix   str   default "tank/security"
"""
from __future__ import annotations

import datetime
import json
import os
import threading
from typing import Optional

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

QOS = 10


class EventLoggerNode(Node):
    def __init__(self) -> None:
        super().__init__("event_logger")
        self._declare_params()
        lp = str(self.get_parameter("log_path").value)
        os.makedirs(os.path.dirname(lp) or ".", exist_ok=True)
        self._log_path = lp
        self._mqtt_publish = bool(self.get_parameter("mqtt_publish").value)
        self._mqtt_client = None
        if self._mqtt_publish:
            try:
                import paho.mqtt.client as mqtt
                self._mqtt_client = mqtt.Client()
                broker = str(self.get_parameter("mqtt_broker").value)
                self._mqtt_client.connect(broker, keepalive=60)
                self._mqtt_client.loop_start()
            except Exception as exc:
                self.get_logger().warn(f"MQTT unavailable ({exc}); continuing without")
                self._mqtt_client = None

        self._lock = threading.Lock()
        for topic in ("motion", "intruder", "alert", "dock_charge"):
            self.create_subscription(
                String, f"/security/events/{topic}",
                lambda msg, t=topic: self._on_event(t, msg),
                QOS,
            )
        self._last_pub = self.create_publisher(String, "/security/event_log", QOS)
        self.get_logger().info(f"event_logger writing to {lp}")

    def _declare_params(self) -> None:
        self.declare_parameter("log_path", "/var/tank/logs/security.jsonl")
        self.declare_parameter("mqtt_publish", False)
        self.declare_parameter("mqtt_broker", "tcp://localhost:1883")
        self.declare_parameter("mqtt_topic_prefix", "tank/security")

    def _on_event(self, kind: str, msg: String) -> None:
        record = {
            "ts":    datetime.datetime.utcnow().isoformat() + "Z",
            "kind":  kind,
            "value": msg.data,
        }
        line = json.dumps(record) + "\n"
        with self._lock:
            try:
                with open(self._log_path, "a") as fh:
                    fh.write(line)
                if self._mqtt_client is not None:
                    prefix = str(self.get_parameter("mqtt_topic_prefix").value)
                    self._mqtt_client.publish(
                        f"{prefix}/{kind}", msg.data or "",
                    )
            except Exception as exc:
                self.get_logger().warn(f"log write failed: {exc}")
        self._last_pub.publish(String(data=line.strip()))


def main(args=None) -> None:
    rclpy.init(args=args)
    node = EventLoggerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
