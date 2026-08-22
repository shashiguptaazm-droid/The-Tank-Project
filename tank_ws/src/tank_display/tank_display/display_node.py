"""ROS 2 node that draws faces on the 1.3\" OLED.

Subscribes
    /emotion/state        std_msgs/String  ("happy"|"sad"|"alert"|
                                            "curious"|"neutral")

Parameters
    use_luma      bool  default False  (set True on Jetson with panel wired)
    i2c_port      int   default 1
    i2c_address   int   default 0x70   (matches WIRING.md)
    width         int   default 128
    height        int   default 64
    rate_hz       float default 4.0    (redraw throttle)
"""
from __future__ import annotations

import threading
import time
from typing import Optional

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from .faces import render_face
from .oled_hal import open_hal


class DisplayNode(Node):
    def __init__(self, hal=None) -> None:
        super().__init__("display_node")
        self.declare_parameter("use_luma", False)
        self.declare_parameter("i2c_port", 1)
        self.declare_parameter("i2c_address", 0x70)
        self.declare_parameter("width", 128)
        self.declare_parameter("height", 64)
        self.declare_parameter("rate_hz", 4.0)

        hal_provided = hal is not None
        if hal_provided:
            self._hal = hal
        else:
            self._hal = open_hal(
                bool(self.get_parameter("use_luma").value),
                port=int(self.get_parameter("i2c_port").value),
                address=int(self.get_parameter("i2c_address").value),
                width=int(self.get_parameter("width").value),
                height=int(self.get_parameter("height").value),
            )
        if not hal_provided:
            self.get_logger().info(
                f"display_node using {'luma SH1106' if bool(self.get_parameter('use_luma').value) else 'NullHal'}"
            )

        self._lock = threading.Lock()
        self._latest_mood: str = "neutral"
        self._last_render: float = 0.0
        self._rate = max(0.5, float(self.get_parameter("rate_hz").value))

        self.create_subscription(String, "/emotion/state",
                                  self._on_emotion, 10)
        # Periodic redraw — catches "neutral" decay without traffic.
        self.create_timer(1.0 / self._rate, self._tick)

        # Initial paint so the OLED doesn't stay blank.
        self._render("neutral")
        self.get_logger().info("display_node initialised")

    def _on_emotion(self, msg: String) -> None:
        mood = (msg.data or "neutral").strip().lower()
        with self._lock:
            self._latest_mood = mood
            now = time.monotonic()
            last = self._last_render
        # Throttle per emit — a burst of upstream messages shouldn't
        # thrash the SPI bus / luma driver.  Snap-through on the first
        # message after the throttle window.
        if now - last < (1.0 / self._rate):
            return
        self._render(mood)

    def _tick(self) -> None:
        now = time.monotonic()
        with self._lock:
            mood = self._latest_mood
            last = self._last_render
        if now - last < (1.0 / self._rate):
            return
        self._render(mood)

    def _render(self, mood: str) -> None:
        try:
            img = render_face(mood,
                              size=(self._hal.width, self._hal.height))
            self._hal.display(img, mood=mood)
            with self._lock:
                self._last_render = time.monotonic()
        except Exception as exc:
            self.get_logger().warn(
                f"oled render failed: {exc}", throttle_duration_sec=5.0
            )


def main(args=None) -> None:
    rclpy.init(args=args)
    node = DisplayNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            node._hal.close()
        finally:
            node.destroy_node()
            rclpy.shutdown()


if __name__ == "__main__":
    main()
