"""TankOS Emotion Manager — emotional state, personality, transitions, expression sync."""

from __future__ import annotations
import logging, threading, time
from typing import Any, Dict, List, Optional
from tank_os.core.event_bus import Event, EventBus


class EmotionManager:
    _instance: Optional["EmotionManager"] = None; _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._bus = EventBus()
                cls._instance._current_emotion = "neutral"
                cls._instance._valence = 0.0
                cls._instance._arousal = 0.0
                cls._instance._intensity = 0.5
                cls._instance._decay_s = 8.0
                cls._instance._last_update = time.time()
            return cls._instance

    def initialize(self) -> None:
        self._bus.on("emotion_changed", self._on_emotion_changed)
        logger.info("EmotionManager initialized")

    def _on_emotion_changed(self, event: Event) -> None:
        self._current_emotion = event.data.get("name", "neutral")
        self._valence = event.data.get("valence", 0.0)
        self._arousal = event.data.get("arousal", 0.0)
        self._intensity = event.data.get("intensity", 0.5)

    def set_emotion(self, name: str, valence: float = 0.0, arousal: float = 0.0,
                    intensity: float = 0.5) -> None:
        self._current_emotion = name
        self._valence = valence
        self._arousal = arousal
        self._intensity = intensity
        self._last_update = time.time()
        self._bus.emit(Event("emotion_changed", {
            "name": name, "valence": valence, "arousal": arousal, "intensity": intensity,
        }, source="emotion_manager"))

    @property
    def current(self) -> Dict[str, Any]:
        elapsed = time.time() - self._last_update
        decayed_intensity = self._intensity * (0.5 ** (elapsed / self._decay_s))
        return {"name": self._current_emotion, "valence": self._valence,
                "arousal": self._arousal, "intensity": round(decayed_intensity, 3)}


logger = logging.getLogger("tank_os.emotion_manager")
