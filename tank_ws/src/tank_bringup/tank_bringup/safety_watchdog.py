"""Software safety watchdog for The Tank Project.

Responsibilities
----------------
1. **Latched ``/estop`` topic** (``std_msgs/Bool``). Any publisher can drop it
   to ``True`` (operator UI, collision detector, low-battery monitor,
   external kill button — see ``/estop_external``). Once ``True``, the latch
   is sticky even if the source sets it back to ``False``; only:
     a. ``/estop_external`` going ``False`` AND
     b. a fresh operator heartbeat
   releases it. (The hardware kill switch breaks VBAT physically, so the
   relay-side wiring always wins regardless of this software state.)
2. **Heartbeat monitor**. ``/operator/ping`` (``std_msgs/Int32``) is fed by
   the operator UI. If it goes stale beyond ``heartbeat_timeout_sec``, the
   watchdog latches ``/estop``.

The relay-side hardware kill switch (NC pushbutton breaking the motor
driver's VBAT trace) is independent of this node — we only enforce
software discipline here.
"""
from __future__ import annotations

import time
from typing import Optional

import rclpy
from rclpy.node import Node

from std_msgs.msg import Bool, Int32

DEFAULT_TIMEOUT_SEC = 1.5
TICK_HZ = 10.0
QOS = 10


class SafetyWatchdogNode(Node):
    def __init__(self, timeout_sec: float = DEFAULT_TIMEOUT_SEC) -> None:
        super().__init__("safety_watchdog")
        self.declare_parameter("heartbeat_timeout_sec", timeout_sec)
        self._last_heartbeat  = time.monotonic()
        self._latched         = False
        self._external_estop  = False

        self._pub         = self.create_publisher(Bool, "estop", QOS)
        self._hb_sub      = self.create_subscription(Int32, "operator/ping",
                                                     self._on_ping, QOS)
        self._external_sub = self.create_subscription(Bool, "estop_external",
                                                      self._on_external, QOS)
        self._timer = self.create_timer(1.0 / TICK_HZ, self._tick)
        self.get_logger().info(
            "safety_watchdog initialised; heartbeat timeout "
            f"{float(self.get_parameter('heartbeat_timeout_sec').value):.2f}s"
        )

    def _on_ping(self, _msg: Int32) -> None:
        self._last_heartbeat = time.monotonic()

    def _on_external(self, msg: Bool) -> None:
        if msg.data and not self._external_estop:
            self._latch("external estop request")
        self._external_estop = msg.data

    def _latch(self, reason: str) -> None:
        self._latched = True
        self.get_logger().error(f"E-STOP LATCHED: {reason}")

    def _tick(self) -> None:
        age     = time.monotonic() - self._last_heartbeat
        timeout = float(self.get_parameter("heartbeat_timeout_sec").value)
        if age > timeout and not self._latched:
            self._latch(f"heartbeat stale ({age:.2f}s > {timeout:.2f}s)")
        # Latch is sticky. The published value only goes back to False if
        # neither heartbeat nor an external source is asserting estop.
        released = (not self._latched) and (not self._external_estop)
        self._pub.publish(Bool(data=not released))


def main(args: Optional[list] = None) -> None:
    rclpy.init(args=args)
    node = SafetyWatchdogNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
