"""Piper TTS node — synthesises assistant replies to audio.

Subscribes
    /assistant_text  std_msgs/String   reply text to speak
    /tts/voice_id    std_msgs/String   hot-swap to a new Piper voice
                                      (e.g. when persona changes)

Publishes
    /audio_out       sensor_msgs/AudioData    raw int16 mono 22 kHz

Parameters
    model_path         str   default ""           static .onnx file
    config_path        str   default ""           matching .onnx.json
    sample_rate        int   default 22050        (set by onnx.json)
    initial_voice_id   str   default "en_US-lessac-medium"
                            catalogue key — if set on boot, voice_manager
                            downloads (if missing) and loads through the
                            PiperSwapper. Empty string → keep static path.

The new ``/tts/voice_id`` subscription lets the persona dashboard swap
voices at runtime without restarting the node. Empty payloads are
ignored. If ``voice_manager`` is unavailable (e.g. CI bench) the swap
degrades gracefully — the static ``model_path`` engine keeps serving.
"""
from __future__ import annotations

import threading
from typing import Any, Optional

import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import AudioData
from std_msgs.msg import String

QOS = 10


class PiperEngineInterface:
    def synth(self, text: str, sample_rate: int) -> bytes:
        """Returns raw int16 mono PCM bytes."""

class StubPiperEngine:
    def synth(self, text: str, sample_rate: int) -> bytes:
        # 0.5 s of silence — placeholder so audio capture has something to fill.
        return (np.zeros(int(0.5 * sample_rate), dtype=np.int16)).tobytes()


class PiperEngine:
    def __init__(self, model_path: str, config_path: str) -> None:
        from piper import PiperVoice
        self._voice = PiperVoice.load(model_path, config_path)

    def synth(self, text: str, sample_rate: int) -> bytes:
        audio = self._voice.synthesize(text)
        # Piper returns AudioChunk objects with .audio as int16 numpy array
        # or .audio_int16_array depending on version.  Take whatever's there.
        if hasattr(audio, "audio_int16_array"):
            raw = audio.audio_int16_array
        else:
            raw = audio.audio
        return np.asarray(raw, dtype=np.int16).tobytes()


# Adapter so a :class:`voice_manager.PiperVoiceHandle` looks like
# the existing :class:`PiperEngineInterface` for the rest of the node.
class _HandleAdapter:
    def __init__(self, handle: Any) -> None:
        self._h = handle

    def synth(self, text: str, sample_rate: int) -> bytes:
        # The swapper already returns int16 mono bytes via its own
        # audio path — re-arranging sample_rate here is moot.
        try:
            return self._h.synth(text)
        except Exception:
            return b"\x00\x00" * int(0.5 * sample_rate)

    @property
    def sample_rate(self) -> int:
        return self._h.sample_rate


class TtsNode(Node):
    def __init__(self, engine: Optional[Any] = None) -> None:
        super().__init__("tts_node")
        self._declare_params()
        self._swapper = None
        self._engine: Any
        engine_provided = engine is not None
        mp = str(self.get_parameter("model_path").value)
        cp = str(self.get_parameter("config_path").value)

        # Path A — static model loaded the way the original tts_node did.
        if engine is None and mp and cp:
            try:
                self._engine = PiperEngine(model_path=mp, config_path=cp)
                self.get_logger().info(f"Piper loaded statically: {mp}")
            except Exception as exc:
                self.get_logger().warn(f"Piper load failed ({exc}); stub")
                self._engine = StubPiperEngine()
        else:
            self._engine = engine or StubPiperEngine()

        # Path B — hot-swap via voice_manager if it's importable. If
        # the swapper can supply a real voice on boot, prefer that.
        try:
            from .voice_manager import PiperSwapper          # noqa: WPS433
            initial = str(self.get_parameter("initial_voice_id").value).strip()
            if initial:
                self._swapper = PiperSwapper()
                try:
                    handle = self._swapper.set_voice(initial)
                    if handle.loaded:
                        self._engine = _HandleAdapter(handle)
                        self.get_logger().info(
                            f"PiperSwapper loaded initial voice: {initial}")
                    else:
                        self.get_logger().warn(
                            f"PiperSwapper stub-mode for {initial} "
                            f"(onnxruntime or model files unavailable); "
                            f"keeping static engine")
                except Exception as exc:
                    self.get_logger().warn(
                        f"PiperSwapper.set_voice({initial}) failed: {exc}; "
                        f"keeping static engine")
        except Exception as exc:
            self.get_logger().warn(
                f"voice_manager unavailable ({exc}); hot-swap disabled")
            self._swapper = None  # type: ignore[assignment]

        self._sample_rate = int(self.get_parameter("sample_rate").value)
        self._lock = threading.Lock()
        self.create_subscription(String, "/assistant_text", self._on_text, QOS)
        self._audio_pub = self.create_publisher(AudioData, "/audio_out", QOS)
        self.create_subscription(String, "/tts/voice_id",
                                  self._on_voice_id, QOS)
        self.get_logger().info("tts_node initialised")

    def _declare_params(self) -> None:
        self.declare_parameter("model_path", "")
        self.declare_parameter("config_path", "")
        self.declare_parameter("sample_rate", 22050)
        self.declare_parameter("initial_voice_id", "en_US-lessac-medium")

    def _on_text(self, msg: String) -> None:
        text = (msg.data or "").strip()
        if not text:
            return
        try:
            pcm = self._engine.synth(text, self._sample_rate)
        except Exception as exc:
            self.get_logger().warn(f"synth failed: {exc}")
            return
        # Wrap int16 PCM into an AudioData msg.
        sample_rate = self._sample_rate
        from sensor_msgs.msg import AudioData as _AD
        ad = _AD()
        ad.data = list(pcm)
        # sensor_msgs/AudioData convention: uint8[] data; ensure layout
        # (compatible with image/audio_common).
        self._audio_pub.publish(ad)

    def _on_voice_id(self, msg: String) -> None:
        """Hot-swap to a new Piper voice. Empty => do nothing."""
        voice_id = (msg.data or "").strip()
        if not voice_id:
            return
        if getattr(self, "_swapper", None) is None:
            self.get_logger().warn(
                "voice_manager unavailable; /tts/voice_id ignored",
                throttle_duration_sec=2.0)
            return
        try:
            handle = self._swapper.set_voice(voice_id)
        except Exception as exc:
            self.get_logger().warn(
                f"voice swap to {voice_id!r} failed: {exc}",
                throttle_duration_sec=2.0)
            return
        # Only swap the engine if Piper actually loaded; stub stays.
        if handle.loaded:
            with self._lock:
                self._engine = _HandleAdapter(handle)
                self._sample_rate = handle.sample_rate
            self.get_logger().info(f"PiperSwapper swapped to {voice_id}")
        else:
            self.get_logger().warn(
                f"voice swap to {voice_id!r} fell back to stub "
                f"(file missing or onnxruntime unavailable)",
                throttle_duration_sec=5.0)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = TtsNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
