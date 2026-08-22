"""STT node — fill the gap between wake-word and the LLM's intent input.

This node closes the loop that was the most-missed BLOCKER after the
initial tank-project commit:

  openWakeWord → /wake_detected   ─┐
                                 ├──→ STT node  → /intent_text
  /audio (PCM)                ───┘                              │
                                                                  ↓
                                                       llm_node subscribes
                                                       (``/intent_text``)

Without this node the system would halt at ``/wake_detected=True``
forever because nothing typed the wake-word utterance into the
``/intent_text`` topic the LLM is listening on.

Subscribes
    /audio            sensor_msgs/AudioData  (16 kHz mono PCM)
    /wake_detected    std_msgs/Bool

Publishes
    /intent_text      std_msgs/String        transcribed utterance
    /intent_conf      std_msgs/Float32       per-utterance confidence
    /intent_event     std_msgs/String        one-shot JSON event

Parameters
    audio_topic         str   default "/audio"
    wake_topic          str   default "/wake_detected"
    intent_topic        str   default "/intent_text"
    model_size          str   default "tiny.en"
    device              str   default "cpu"
    record_window_s     float default 6.0
    min_audio_ms        int   default 700
    min_confidence      float default 0.35
    language            str   default "en"
    prompt              str   default ""
"""
from __future__ import annotations

import collections
import json
import threading
import time
from typing import Deque, Optional

import numpy as np

try:
    import rclpy                                       # noqa: F401
    from rclpy.node import Node
    from std_msgs.msg import Bool, Float32, String
    from sensor_msgs.msg import AudioData
    _RCLPY_AVAILABLE = True
except ImportError:
    _RCLPY_AVAILABLE = False

    class _NoopPublisher:
        def publish(self, *_a, **_k): return None

    class _NoopLogger:
        def info(self, *_a, **_k): pass
        def warn(self, *_a, **_k): pass
        def error(self, *_a, **_k): pass

    class _StubNode:
        def __init__(self, *_a, **_k): pass
        def declare_parameter(self, *_a, **_k): pass
        def get_parameter(self, *_a, **_k):
            class _P:
                value = ""
            return _P()
        def create_publisher(self, *_a, **_k):
            return _NoopPublisher()
        def create_subscription(self, *_a, **_k):
            class _S:
                pass
            return _S()
        def get_logger(self):
            return _NoopLogger()

    Node = _StubNode                       # type: ignore[assignment]
    AudioData = Bool = Float32 = String = object  # type: ignore[assignment]


# -----------------------------------------------------------------------------
# Engines.
# -----------------------------------------------------------------------------
class WhisperEngine:
    """Lazy wrapper around ``faster-whisper`` (preferred) or ``whisper``."""

    def __init__(self, model_size: str, device: str, language: str) -> None:
        try:
            from faster_whisper import WhisperModel
            self._impl = WhisperModel(model_size, device=device)
            self._kind = "faster_whisper"
        except ImportError:
            import whisper
            self._impl = whisper.load_model(model_size, device=device)
            self._kind = "openai_whisper"
        self._lang = language

    def transcribe(self, audio_int16: np.ndarray, prompt: str) -> tuple[str, float]:
        audio_f32 = audio_int16.astype(np.float32) / 32768.0
        if self._kind == "faster_whisper":
            segs, info = self._impl.transcribe(
                audio_f32, language=self._lang,
                initial_prompt=prompt, beam_size=1, vad_filter=False,
            )
            text = " ".join(s.text.strip() for s in segs).strip()
            return text, float(info.language_probability or 0.0)
        result = self._impl.transcribe(  # type: ignore[attr-defined]
            audio_f32, language=self._lang, initial_prompt=prompt,
            fp16=False,
        )
        return (result.get("text", "") or "").strip(), \
               float(result.get("language", self._lang) == self._lang)


class NullEngine:
    """Always-empty transcription — used by tests and dry-run."""
    def transcribe(self, *_a, **_k) -> tuple[str, float]:
        return "", 0.0


# -----------------------------------------------------------------------------
# ROS2 node.
# -----------------------------------------------------------------------------
class SttNode(Node):
    def __init__(self, engine: Optional[object] = None) -> None:
        super().__init__("stt_node")
        self._declare_params()
        self._audio_buffer: Deque[bytes] = collections.deque(maxlen=8192)
        self._wake_latched = False
        self._record_started: Optional[float] = None
        self._lock = threading.Lock()
        self._last_published = 0.0

        engine_provided = engine is not None
        ms = str(self.get_parameter("model_size").value)
        dev = str(self.get_parameter("device").value)
        lang = str(self.get_parameter("language").value)
        if engine is not None:
            self._engine = engine
        else:
            try:
                self._engine = WhisperEngine(ms, dev, lang)
                self.get_logger().info(
                    f"whisper ready ({self._engine._kind} model={ms})")
            except Exception as exc:
                self.get_logger().warn(
                    f"whisper unavailable ({exc}); using NullEngine"
                )
                self._engine = NullEngine()
        if not engine_provided and not isinstance(self._engine, NullEngine):
            pass

        self._intent_pub  = self.create_publisher(String,  "intent_text",   10)
        self._conf_pub    = self.create_publisher(Float32, "intent_conf",   10)
        self._event_pub   = self.create_publisher(String,  "intent_event",  10)

        self._audio_sub = self.create_subscription(
            AudioData,
            str(self.get_parameter("audio_topic").value),
            self._on_audio, 10,
        )
        self._wake_sub = self.create_subscription(
            Bool,
            str(self.get_parameter("wake_topic").value),
            self._on_wake, 10,
        )
        # Tick fires often; we only act when wake is latched AND we've
        # collected enough audio to satisfy min_audio_ms.
        self.create_timer(0.1, self._tick)
        self.get_logger().info("stt_node initialised")

    def _declare_params(self) -> None:
        self.declare_parameter("audio_topic",   "/audio")
        self.declare_parameter("wake_topic",    "/wake_detected")
        self.declare_parameter("intent_topic",  "/intent_text")
        self.declare_parameter("model_size",    "tiny.en")
        self.declare_parameter("device",        "cpu")
        self.declare_parameter("language",      "en")
        self.declare_parameter("record_window_s", 6.0)
        self.declare_parameter("min_audio_ms",    700)
        self.declare_parameter("min_confidence",  0.35)
        self.declare_parameter("prompt",          "")

    def _on_audio(self, msg) -> None:
        with self._lock:
            if self._wake_latched:
                self._audio_buffer.append(bytes(msg.data))

    def _on_wake(self, msg) -> None:
        with self._lock:
            if msg.data and not self._wake_latched:
                self._wake_latched = True
                self._record_started = time.monotonic()
                self._audio_buffer.clear()

    def _tick(self) -> None:
        with self._lock:
            if not self._wake_latched:
                return
            window_s = float(self.get_parameter("record_window_s").value)
            if (time.monotonic() - (self._record_started or 0.0)) < window_s:
                return
            raw = b"".join(self._audio_buffer)
            self._audio_buffer.clear()
            self._wake_latched = False
            self._record_started = None

        if not raw:
            return
        audio = np.frombuffer(raw, dtype=np.int16)
        if audio.size == 0:
            return
        audio_ms = int(audio.size / 16)
        min_ms = int(self.get_parameter("min_audio_ms").value)
        if audio_ms < min_ms:
            self.get_logger().warn(
                f"audio too short ({audio_ms} ms < {min_ms} ms); discarded")
            return
        try:
            text, conf = self._engine.transcribe(
                audio, str(self.get_parameter("prompt").value),
            )
        except Exception as exc:
            self.get_logger().warn(
                f"transcribe failed: {exc}", throttle_duration_sec=2.0
            )
            return
        min_conf = float(self.get_parameter("min_confidence").value)
        if not text:
            self.get_logger().info("no speech transcribed; dropped")
            return
        if conf < min_conf:
            self.get_logger().warn(
                f"low-confidence transcription ({conf:.2f} < {min_conf:.2f}): "
                f"{text!r}")
        if hasattr(self, "_intent_pub"):
            self._intent_pub.publish(String(data=text))
            self._conf_pub.publish(Float32(data=float(conf)))
            self._event_pub.publish(String(data=json.dumps({
                "text": text, "conf": round(conf, 3),
                "ts":   time.time(),
            })))
        self._last_published = time.monotonic()


def main(args=None) -> None:
    if not _RCLPY_AVAILABLE:
        print("stt_node: ROS 2 not available — exiting (ROS2 required)")
        return
    rclpy.init(args=args)
    node = SttNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
