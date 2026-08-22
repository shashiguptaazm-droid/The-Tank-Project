"""Wake-word listener for The Tank Project.

Wraps `openWakeWord <https://github.com/dscripka/openWakeWord>`_ in a
ROS2 node so a hot-word detection on a 16 kHz mono audio stream can
trigger the rest of the pipeline (Whisper ASR -> intent -> LLM assistant).

How it works
------------
1. Subscribes ``/audio`` (sensor_msgs/AudioData carrying PCM bytes).
2. Pushes raw int16 samples into a rolling buffer.
3. Every ~80 ms, drains the buffer and runs ``Model.predict`` to get the
   latest wake-word confidence in [0, 1].
4. When that confidence exceeds ``threshold`` AND the cooldown has
   elapsed, the node publishes a latched ``/wake_detected`` ``Bool`` of
   ``True``. The latch stays True for ``window_sec`` seconds so
   downstream components can decide when to start ASR.
5. When the window expires, the latch is cleared with ``False`` so
   latched subscribers don't hang forever.

The state machine lives in ``wake_state.py`` so it is independently
unit-tested.

Subscribes
    /audio                sensor_msgs/AudioData  (16 kHz mono PCM)

Publishes
    /wake_detected        std_msgs/Bool          latched
    /wake_confidence      std_msgs/Float32       per-tick (for debugging)
    /wake_event           std_msgs/String        one-shot ("wake at ...")

Parameters
    audio_topic           str     default /audio
    model_path            str     default ""      (uses openWakeWord built-ins)
    model_name            str     default "hey_jarvis"
    threshold             float   default 0.55
    cooldown_sec          float   default 2.0
    window_sec            float   default 5.0
    inference_hz          float   default 12.5    (=> 80 ms window)
"""
from __future__ import annotations

import collections
import threading
import time
from typing import Deque, Optional

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import AudioData
from std_msgs.msg import Bool, Float32, String

from .wake_state import WakeLatch, WakeLatchConfig

QOS_AUDIO = QoSProfile(depth=20, reliability=ReliabilityPolicy.RELIABLE)
QOS_LATCH = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
DEFAULT_INFERENCE_HZ = 12.5


# ---------------------------------------------------------------------------
# HAL: openWakeWord wrapper.  Lazy-imported so py_compile + tests don't fail
# on machines where openWakeWord / tflite-runtime isn't installed.
# ---------------------------------------------------------------------------
class WakeWordEngine:
    def __init__(self, model_path: str = "", model_name: str = "hey_jarvis"):
        from openwakeword.model import Model
        kwargs = {}
        if model_path:
            kwargs["wakeword_models"] = [model_path]
        else:
            kwargs["wakeword_models"] = [model_name]
        self._model = Model(**kwargs)

    def push(self, audio_int16: np.ndarray) -> float:
        if audio_int16.size == 0:
            return 0.0
        scores = self._model.predict(audio_int16)
        if not scores:
            return 0.0
        # openWakeWord returns a dict {wakeword_name: score}
        return float(max(scores.values()) if isinstance(scores, dict) else float(np.max(scores)))

    def reset(self) -> None:
        try:
            self._model.reset()
        except Exception:
            pass


class NullWakeWordEngine:
    """Always returns 0.0 — used by tests and dry-runs."""
    def push(self, audio_int16: np.ndarray) -> float:
        return 0.0
    def reset(self) -> None:
        pass


# ---------------------------------------------------------------------------
# ROS2 node.
# ---------------------------------------------------------------------------
class WakeWordListenerNode(Node):
    def __init__(
        self,
        engine: Optional[WakeWordEngine] = None,
    ) -> None:
        super().__init__("wake_word_listener")
        self._declare_params()
        cfg = WakeLatchConfig(
            threshold=float(self.get_parameter("threshold").value),
            cooldown_sec=float(self.get_parameter("cooldown_sec").value),
            window_sec=float(self.get_parameter("window_sec").value),
        )
        self._latch = WakeLatch(cfg)
        self._lock  = threading.Lock()
        self._buf: Deque[bytes] = collections.deque(maxlen=128)

        engine_provided = engine is not None
        mp = str(self.get_parameter("model_path").value)
        mn = str(self.get_parameter("model_name").value)
        self._engine = engine or WakeWordEngine(model_path=mp, model_name=mn)
        if not engine_provided:
            self.get_logger().info(
                f"openWakeWord ready (model={mn or mp}, threshold={cfg.threshold:.2f})"
            )

        self._wake_pub   = self.create_publisher(Bool,    "wake_detected",   QOS_LATCH)
        self._score_pub  = self.create_publisher(Float32, "wake_confidence", QOS_LATCH)
        self._event_pub  = self.create_publisher(String,  "wake_event",      QOS_LATCH)
        self._audio_sub  = self.create_subscription(
            AudioData,
            str(self.get_parameter("audio_topic").value),
            self._on_audio,
            QOS_AUDIO,
        )
        # Periodic inference loop.  Cheaper than running on every callback.
        hz = max(1.0, float(self.get_parameter("inference_hz").value))
        self._timer = self.create_timer(1.0 / hz, self._tick)
        self.get_logger().info("wake_word_listener initialised")

    # --------------------- parameters ---------------------
    def _declare_params(self) -> None:
        self.declare_parameter("audio_topic",   "/audio")
        self.declare_parameter("model_path",    "")
        self.declare_parameter("model_name",    "hey_jarvis")
        self.declare_parameter("threshold",     0.55)
        self.declare_parameter("cooldown_sec",  2.0)
        self.declare_parameter("window_sec",    5.0)
        self.declare_parameter("inference_hz",  DEFAULT_INFERENCE_HZ)

    # --------------------- callbacks ----------------------
    def _on_audio(self, msg: AudioData) -> None:
        with self._lock:
            self._buf.append(bytes(msg.data))

    def _tick(self) -> None:
        with self._lock:
            if not self._buf:
                return
            raw = b"".join(self._buf)
            self._buf.clear()
        try:
            audio = np.frombuffer(raw, dtype=np.int16)
        except Exception as exc:
            self.get_logger().warn(
                f"audio decode failed: {exc}", throttle_duration_sec=2.0
            )
            return
        if audio.size == 0:
            return
        try:
            score = self._engine.push(audio)
        except Exception as exc:
            self.get_logger().warn(
                f"openWakeWord inference failed: {exc}", throttle_duration_sec=2.0
            )
            return
        self._score_pub.publish(Float32(data=float(score)))
        state = self._latch.step(score, time.monotonic())
        if state == "wake" and not self._last_latched_state:
            # rising edge — emit a one-shot event
            self._event_pub.publish(String(
                data=f"wake conf={score:.2f} t={time.monotonic():.2f}"
            ))
        self._wake_pub.publish(Bool(data=(state == "wake")))
        self._last_latched_state = (state == "wake")

    # Catch-all safety net for engine cleanup
    _last_latched_state: bool = False  # type: ignore[assignment]


def main(args=None) -> None:
    rclpy.init(args=args)
    node = WakeWordListenerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
