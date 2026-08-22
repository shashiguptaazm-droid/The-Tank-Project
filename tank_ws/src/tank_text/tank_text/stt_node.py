"""Whisper STT node.

Subscribes to the rolling ``/audio`` topic; when ``/wake_detected``
latches True (handled externally by wake_word_listener), this node
captures the next ``window_sec`` of audio and runs Whisper-tiny.float16
on it. The transcribed text is published as /intent_text.

Heavy lifting (Whisper encode) lives in a thread to keep the ROS
executor responsive.

Subscribes
    /audio             sensor_msgs/AudioData   raw int16 mono 16 kHz
    /wake_detected     std_msgs/Bool           latched
    /wake_window_reset std_msgs/Bool          optional — tell node to
                                              drop buffer and re-arm

Publishes
    /intent_text       std_msgs/String         Whisper output

Parameters
    model_size         str   default "tiny.en"   (Whisper model name)
    language           str   default "en"
    window_sec         float default 5.0          (Capture duration)
    target_sample_rate int   default 16000
"""
from __future__ import annotations

import collections
import threading
import time
from typing import Deque, Optional

import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import AudioData
from std_msgs.msg import Bool, String

QOS = 10


class WhisperEngineInterface:
    def transcribe(self, audio_float32: np.ndarray, sample_rate: int) -> str: ...


class StubWhisperEngine:
    """Returns a deterministic stub transcript for tests."""
    def transcribe(self, audio_float32, sample_rate):
        return "[stub whisper] hello world"


class WhisperEngine:
    def __init__(self, model_size: str = "tiny.en") -> None:
        import whisper
        self._model = whisper.load_model(model_size)

    def transcribe(self, audio_float32, sample_rate):
        # whisper.transcribe expects float32 in [-1, 1] — convert.
        result = self._model.transcribe(
            audio_float32,
            language=self._language,
            fp16=False,        # Pi 5 CPU path
        )
        return (result.get("text") or "").strip()


class SttNode(Node):
    def __init__(self, whisper_engine: Optional[WhisperEngineInterface] = None) -> None:
        super().__init__("stt_node")
        self._declare_params()

        engine_provided = whisper_engine is not None
        mp = str(self.get_parameter("model_size").value)
        if whisper_engine is None and mp and mp != "stub":
            try:
                self._engine = WhisperEngine(model_size=mp)
                self._engine._language = str(self.get_parameter("language").value)
                self.get_logger().info(f"Whisper loaded: {mp}")
            except Exception as exc:
                self.get_logger().warn(f"Whisper load failed ({exc}); stub")
                self._engine = StubWhisperEngine()
        else:
            self._engine = whisper_engine or StubWhisperEngine()

        self._lock = threading.Lock()
        self._buf: Deque[bytes] = collections.deque(maxlen=64)
        self._capture_window_sec = float(self.get_parameter("window_sec").value)
        self._sample_rate = int(self.get_parameter("target_sample_rate").value)
        self._capturing = False
        self._capture_started = 0.0

        self.create_subscription(AudioData, "/audio",
                                  self._on_audio, QOS)
        self.create_subscription(Bool, "/wake_detected",
                                  self._on_wake, QOS)
        self.create_subscription(Bool, "/wake_window_reset",
                                  self._on_reset, QOS)
        self._intent_pub = self.create_publisher(String, "/intent_text", QOS)

        # 100 ms cap to /audio after window expires — call _on_audio_capture_done
        self._timer = self.create_timer(0.1, self._check_window)
        self.get_logger().info("stt_node initialised")

    def _declare_params(self) -> None:
        self.declare_parameter("model_size", "tiny.en")
        self.declare_parameter("language", "en")
        self.declare_parameter("window_sec", 5.0)
        self.declare_parameter("target_sample_rate", 16000)

    def _on_audio(self, msg: AudioData) -> None:
        if not self._capturing:
            return
        with self._lock:
            self._buf.append(bytes(msg.data))

    def _on_wake(self, msg: Bool) -> None:
        if msg.data and not self._capturing:
            with self._lock:
                self._buf.clear()
            self._capturing = True
            self._capture_started = time.monotonic()
            self.get_logger().info("stt: capture window opened")

    def _on_reset(self, msg: Bool) -> None:
        if msg.data:
            self._capturing = False
            with self._lock:
                self._buf.clear()

    def _check_window(self) -> None:
        if self._capturing and self._capture_started:
            elapsed = time.monotonic() - self._capture_started
            if elapsed >= self._capture_window_sec:
                self._capturing = False
                self.get_logger().info("stt: capture window closed")
                self._flush()

    def _flush(self) -> None:
        with self._lock:
            raw = b"".join(self._buf)
            self._buf.clear()
        if not raw:
            return
        audio_int16 = np.frombuffer(raw, dtype=np.int16)
        if audio_int16.size == 0:
            return
        # Normalize to [-1, 1]
        if audio_int16.dtype == np.int16:
            audio = audio_int16.astype(np.float32) / 32768.0
        else:
            audio = audio_int16.astype(np.float32)
        try:
            text = self._engine.transcribe(audio, self._sample_rate)
        except Exception as exc:
            self.get_logger().warn(f"transcribe failed: {exc}")
            return
        if not text:
            return
        self._intent_pub.publish(String(data=text))


def main(args=None) -> None:
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
