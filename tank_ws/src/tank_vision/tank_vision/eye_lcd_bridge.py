"""Eye-LCD bridge — translates ROS2 topics into the line-delimited JSON
protocol the ESP32-S3 firmware (firmware/eyes_esp32/eyes_esp32.ino)
expects over UART2.

Subscribes
    /eye_expression       std_msgs/String     manual override ("happy"|
                                               "sad"|"angry"|"scared"|
                                               "neutral")
    /emotion/state        std_msgs/String     auto-pilot from emotion_node
                                               (mapped to ESP32 expressions)
    /eye_target           geometry_msgs/Point (x, y) gaze in NDC [-1, 1]
    /eye_blink            std_msgs/Bool        trigger a manual blink
    /eye_iris_color       std_msgs/Int32       RGB565 integer override
    /eye/animation_play   std_msgs/String      JSON Animation frame-list
                                               (see tank_vision.animations)
                                               — fires ``media_player``
                                               onto the same HAL, so
                                               multi-frame clip replays
                                               over the existing UART
                                               without breaking
                                               ``/eye_expression`` drivers.

Publishes
    /eye_status           std_msgs/String     last heartbeat JSON from ESP32

Mapping
    /emotion/state  ─►  ESP32 expression
    ------------------------------
    "happy"          "happy"            (amber)
    "sad"            "sad"              (deep blue)
    "alert"          "angry"            (red)   — distressed
    "curious"        "neutral"          (hazel) — ey... lets the
                                              gaze-tracking do the work
    "neutral"        "neutral"          (hazel)
"""
from __future__ import annotations

import json
import threading
import time
from typing import Any, Dict, Optional

try:
    import rclpy                                      # noqa: F401
    from rclpy.node import Node
    from geometry_msgs.msg import Point
    from std_msgs.msg import Bool, Int32, String
    _RCLPY_AVAILABLE = True
except ImportError:
    # Bench/CI mode: still allow importing pure-Python helpers
    # (MOOD_TO_EXPR, mood_to_expression, expr_color, NullEyeSerialHal)
    # without rclpy installed. Instantiating EyeLcdBridgeNode will then
    # raise clearly.
    _RCLPY_AVAILABLE = False

    class _StubNode:                                   # type: ignore[no-redef]
        def __init__(self, *a, **k):
            raise ImportError(
                "rclpy is not installed; EyeLcdBridgeNode requires ROS 2 Humble. "
                "Run scripts/provision_pi5.sh --apply on the Pi 5."
            )

    Node = _StubNode           # type: ignore[assignment]
    Point = Bool = Int32 = String = _StubNode  # type: ignore[assignment] — noop

# Lazy imports so benches without onnxruntime / animations still import
# without crashing. The animation path is name-only — wire format is JSON.
try:
    from .animations import (                          # noqa: WPS433
        Animation as _Animation,
        get_animation as _get_builtin_anim,
        list_animations as _list_builtin_anims,
    )
    _ANIMATIONS_AVAILABLE = True
except ImportError:
    _Animation = None  # type: ignore[assignment]
    _ANIMATIONS_AVAILABLE = False

try:
    from .media_player import AsyncPlayer, SerialPlayer  # noqa: WPS433
    _MEDIA_AVAILABLE = True
except ImportError:
    _MEDIA_AVAILABLE = False

DEFAULT_PORT = "/dev/ttyUSB1"
DEFAULT_BAUD = 115_200
QOS = 10

# /emotion/state mood → ESP32 firmware expression.  "alert" maps to
# "angry" so a distressed robot visually flags the operator (red iris).
# "curious" maps to neutral so gaze-tracking can carry the nuance.
MOOD_TO_EXPR = {
    "happy":   "happy",
    "sad":     "sad",
    "alert":   "angry",
    "curious": "neutral",
    "neutral": "neutral",
}


class EyeSerialHal:
    """pyserial-backed UART link to the ESP32-S3."""

    def __init__(self, port: str = DEFAULT_PORT, baud: int = DEFAULT_BAUD) -> None:
        import serial
        self._serial = serial.Serial(port, baudrate=baud, timeout=0.05)

    def write_json(self, payload: dict) -> None:
        line = json.dumps(payload) + "\n"
        self._serial.write(line.encode("utf-8"))

    def read_line(self) -> Optional[str]:
        raw = self._serial.readline().decode("utf-8", errors="ignore").strip()
        return raw if raw else None

    def close(self) -> None:
        try:
            self._serial.close()
        except Exception:
            pass


class NullEyeSerialHal:
    """Console-logged HAL, used by tests / dry-runs."""

    def __init__(self) -> None:
        self._log: list[str] = []
        self._last_expr: Optional[str] = None
        self._last_gaze: tuple[float, float] = (0.0, 0.0)
        self._last_color: Optional[int] = None

    def write_json(self, payload: dict) -> None:
        line = json.dumps(payload)
        self._log.append(line)
        if "expr" in payload:
            self._last_expr = payload["expr"]
        if "iris" in payload:
            self._last_color = payload["iris"]
        if "gaze" in payload:
            self._last_gaze = tuple(payload["gaze"])

    def read_line(self) -> Optional[str]:
        return None

    def close(self) -> None:
        pass

    @property
    def log(self) -> list[str]:
        return self._log

    @property
    def last_expr(self) -> Optional[str]:
        return self._last_expr

    @property
    def last_gaze(self) -> tuple[float, float]:
        return self._last_gaze

    @property
    def last_color(self) -> Optional[int]:
        return self._last_color


def mood_to_expression(mood: str) -> str:
    return MOOD_TO_EXPR.get(mood, "neutral")


def expr_color(expr: str) -> int:
    return {
        "happy":   0xFD20,   # amber
        "sad":     0x3F4F,   # deep blue
        "angry":   0xC800,   # red
        "scared":  0xFFFF,   # white
        "neutral": 0x44A4,   # hazel
    }.get(expr, 0x44A4)


class EyeLcdBridgeNode(Node):
    """Two-source expression controller — auto-pilot + manual override.

    The ``/eye/animation_play`` subscriber accepts a JSON Animation
    (from in-process callers or the LLM via the bridge) and replays it
    via the same HAL using an asynchronous, non-blocking player so the
    ROS callback returns within microseconds.
    """

    def __init__(self, hal: Optional[EyeSerialHal] = None) -> None:
        super().__init__("eye_lcd_bridge")
        self.declare_parameter("port", DEFAULT_PORT)
        self.declare_parameter("baud", DEFAULT_BAUD)

        hal_provided = hal is not None
        self._hal = hal or EyeSerialHal(
            port=str(self.get_parameter("port").value),
            baud=int(self.get_parameter("baud").value),
        )
        if not hal_provided:
            self.get_logger().info(
                f"Using EyeSerialHal on {self.get_parameter('port').value}"
            )

        self._lock = threading.Lock()
        # Internal cached expression state — the latest known mood closes
        # over either auto-pilot or manual topic.
        self._cached_expr: str = "neutral"
        self._cached_expr_ts: float = 0.0
        self._cached_expr_src: str = "default"

        # Async player used by /eye/animation_play. The inner plays via
        # the same HAL as expressions, so the firmware sees a single
        # interleaved JSON stream that LLM + animator both write to.
        self._anim_player = None
        if _MEDIA_AVAILABLE:
            try:
                self._anim_player = AsyncPlayer(SerialPlayer(self._hal))
            except Exception as exc:
                self.get_logger().warn(
                    f"media_player unavailable ({exc}); "
                    f"/eye/animation_play disabled")
                self._anim_player = None

        self.create_subscription(String, "/eye_expression",
                                  self._on_expr_override, QOS)
        self.create_subscription(String, "/emotion/state",
                                  self._on_emotion, QOS)
        self.create_subscription(Point, "eye_target",       self._on_gaze,  QOS)
        self.create_subscription(Bool,  "eye_blink",        self._on_blink, QOS)
        self.create_subscription(Int32, "eye_iris_color",   self._on_color, QOS)
        self.create_subscription(String, "/eye/animation_play",
                                  self._on_animation_play, QOS)
        self._status_pub = self.create_publisher(String, "eye_status", QOS)
        self._timer = self.create_timer(0.25, self._heartbeat)
        self.get_logger().info("eye_lcd_bridge initialised")

    # --------------- handlers ---------------
    def _on_expr_override(self, msg: String) -> None:
        expr = (msg.data or "").strip().lower()
        if expr not in ("happy", "sad", "angry", "scared", "neutral"):
            self.get_logger().warn(
                f"eye_expression ignored unknown expr: {expr!r}",
                throttle_duration_sec=2.0,
            )
            return
        self._apply_expr(expr, source="manual")

    def _on_emotion(self, msg: String) -> None:
        mood = (msg.data or "").strip().lower()
        expr = mood_to_expression(mood)
        self._apply_expr(expr, source=f"emotion/{mood}")

    def _on_gaze(self, msg: Point) -> None:
        self._safe_send({
            "gaze": [round(float(msg.x), 3), round(float(msg.y), 3)],
        })

    def _on_blink(self, msg: Bool) -> None:
        if msg.data:
            self._safe_send({"blink": True})

    def _on_color(self, msg: Int32) -> None:
        self._safe_send({"iris": int(msg.data)})

    def _on_animation_play(self, msg: String) -> None:
        """Parse JSON Animation and replay over the HAL asynchronously.

        Accepts either a *built-in name* (``"blink"``, ``"smile"``,
        ``"video_play_rickroll"``) or a full inline Animation JSON.
        Bad payloads log a warning and are dropped.
        """
        raw = (msg.data or "").strip()
        if not raw:
            return
        if not _ANIMATIONS_AVAILABLE or self._anim_player is None:
            self.get_logger().warn(
                "/eye/animation_play ignored: animations or "
                "media_player not importable",
                throttle_duration_sec=2.0)
            return
        anim = None
        if raw.startswith("{"):
            try:
                anim = _Animation.from_json(raw)
            except Exception as exc:
                self.get_logger().warn(
                    f"/eye/animation_play bad JSON: {exc}",
                    throttle_duration_sec=2.0)
                return
        else:
            anim = _get_builtin_anim(raw)
            if anim is None:
                self.get_logger().warn(
                    f"/eye/animation_play unknown name: {raw!r}",
                    throttle_duration_sec=2.0)
                return
        try:
            self._anim_player.play_async(anim)
        except Exception as exc:
            self.get_logger().warn(
                f"/eye/animation_play dispatch failed: {exc}",
                throttle_duration_sec=2.0)

    # --------------- helpers ---------------
    def _apply_expr(self, expr: str, source: str) -> None:
        """Apply a new expression with tagged monotonic timestamps.
        Caller wins on strictly-greater ts to avoid two callbacks with
        identical monotonic() overwriting each other (rare but possible
        on fast ticks)."""
        now = time.monotonic()
        send = False
        with self._lock:
            if now > self._cached_expr_ts:
                self._cached_expr = expr
                self._cached_expr_ts = now
                self._cached_expr_src = source
                send = True
        if send:
            self._safe_send({"expr": expr, "iris": expr_color(expr)})

    def _safe_send(self, payload: dict) -> None:
        try:
            self._hal.write_json(payload)
        except Exception as exc:
            self.get_logger().warn(
                f"eye uart write failed: {exc}", throttle_duration_sec=2.0
            )

    def _heartbeat(self) -> None:
        try:
            line = self._hal.read_line()
            if line is not None:
                self._status_pub.publish(String(data=line))
        except Exception:
            pass


def main(args=None) -> None:
    rclpy.init(args=args)
    node = EyeLcdBridgeNode()
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
