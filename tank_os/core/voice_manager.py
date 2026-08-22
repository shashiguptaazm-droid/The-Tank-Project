"""TankOS Voice Manager — high-level orchestrator over wake/STT/TTS.

This is the *outward-facing*, GUI-bound voice coordinator. It stays
decoupled from low-level engines by importing them via try/except so
that headless benches / CI keep working without ``piper``, ``whisper``
or ``openwakeword`` installed.

States
------
    IDLE               — nothing in the pipeline.
    WAKE_LISTENING     — openWakeWord (or stub) is listening.
    LISTENING          — STT is capturing the user's utterance.
    PROCESSING         — intent router / LLM is producing an answer.
    SPEAKING           — TTS is playing back to the operator.

Events
------
    voice_state_changed   — fired on every state transition.
    voice_listening       — wildcard event every time we enter LISTENING.
    voice_stt_result      — (utterance, confidence) on successful STT.
    voice_tts_started     — when a sentence is queued / started.
    voice_tts_finished    — when the queue empties.
    voice_wake_detected   — wake-word fired (stub gives False).
    voice_error           — provider crashed; carried provider name + exc.

A TTS queue serialises play requests so two ``say("hello")`` calls
don't trample each other.
"""

from __future__ import annotations

import logging
import queue
import sys
import threading
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional

from tank_os.core.event_bus import Event, EventBus, Priority
from tank_os.core.settings_manager import SettingsManager

logger = logging.getLogger("tank_os.voice_manager")


class VoiceState(Enum):
    """Voice pipeline state machine."""

    IDLE = auto()
    WAKE_LISTENING = auto()
    LISTENING = auto()
    PROCESSING = auto()
    SPEAKING = auto()


@dataclass
class VoiceEvent:
    """Lightweight log record for the spoken-side event bus."""

    timestamp: float
    state: VoiceState
    utterance: str = ""
    provider: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class VoiceManager:
    """Singleton high-level voice orchestrator."""

    _instance: Optional["VoiceManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "VoiceManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._bus = EventBus()
                cls._instance._settings = SettingsManager()
                cls._instance._state = VoiceState.IDLE
                cls._instance._listening = False
                cls._instance._tts_queue: "queue.Queue[str]" = queue.Queue()
                cls._instance._tts_thread: Optional[threading.Thread] = None
                cls._instance._events: List[VoiceEvent] = []
                cls._instance._max_events = 50
                cls._instance._lock = threading.Lock()
                # Optional handle to low-level manager
                cls._instance._low_level: Optional[Any] = None
                cls._instance._tts_provider: str = "stub"
                cls._instance._wake_provider: str = "stub"
                cls._instance._stt_provider: str = "stub"
            return cls._instance

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Bind to settings, attempt low-level wiring, start TTS worker.

        Avoids a spurious ``voice_state_changed`` event on the very
        first call — no transition has actually occurred. Consumers
        that want a one-shot ready signal can listen for
        ``voice_manager_ready`` instead.
        """
        self._bind_settings()
        self._try_link_low_level()
        self._start_tts_thread()
        self._bus.emit(Event(
            "voice_manager_ready",
            {"state": self._state.name,
             "tts": self._tts_provider,
             "wake": self._wake_provider,
             "stt": self._stt_provider},
            source="voice_manager",
        ))
        logger.info(
            "VoiceManager initialized — state=%s, tts=%s, wake=%s, stt=%s",
            self._state.name,
            self._tts_provider, self._wake_provider, self._stt_provider,
        )

    def _bind_settings(self) -> None:
        s = self._settings
        self._enabled = bool(s.get("voice.wake_word_enabled", True))
        self._wake_word = str(s.get("voice.wake_word", "hey tank"))
        self._sensitivity = float(s.get("voice.sensitivity", 0.5))
        self._language = str(s.get("voice.language", "en-US"))
        self._tts_rate = float(s.get("audio.tts_rate", 1.0))
        self._tts_pitch = float(s.get("audio.tts_pitch", 1.0))
        self._volume = int(s.get("audio.volume", 80))

    def _try_link_low_level(self) -> None:
        """Link to ``tank_text.voice_manager`` if it is already loaded.

        :class:`VoiceManager` is the outward-facing TankOS surface and
        must never trigger a heavy transitive import — :mod:`tank_text`
        pulls in :mod:`rclpy`, :mod:`piper`, ONNX runtime, and may
        perform ROS discovery at import time. Those happen upstream in
        the ROS bringup, not here. So we only adopt the live module
        if it has already been imported (``"tank_text.voice_manager"
        in sys.modules``); otherwise we stay on the always-available
        stub provider, with the EventBus carrying all signals either
        way. ``__init__`` of either container is deterministic and
        fast.
        """
        if "tank_text.voice_manager" in sys.modules:
            try:
                from tank_text.voice_manager import (
                    PiperSwapper, pick_default_voice,
                )
                self._low_level = PiperSwapper()
                self._low_level.set_voice(pick_default_voice())
                if self._low_level.current and self._low_level.current.loaded:
                    self._tts_provider = "piper"
                else:
                    self._tts_provider = "piper-stub"
            except Exception as exc:
                logger.debug("tank_text voice link failed: %s", exc)
                self._tts_provider = "stub"
        else:
            logger.debug(
                "tank_text.voice_manager not yet loaded; staying on stub")
            self._tts_provider = "stub"
        # Wake + STT are stubbed here; tank_speech / tank_text own the
        # ROS nodes that fire /wake_detected and /intent_text. We
        # surface them via the EventBus as ``voice_wake_detected`` and
        # ``voice_stt_result`` events.
        self._wake_provider = "event-bus"
        self._stt_provider = "event-bus"

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def state(self) -> VoiceState:
        return self._state

    @property
    def is_listening(self) -> bool:
        """Backward-compatible alias used by the original stub."""
        return self._state in (VoiceState.WAKE_LISTENING,
                               VoiceState.LISTENING)

    @property
    def tts_provider(self) -> str:
        return self._tts_provider

    @property
    def wake_provider(self) -> str:
        return self._wake_provider

    @property
    def stt_provider(self) -> str:
        return self._stt_provider

    @property
    def recent_events(self) -> List[VoiceEvent]:
        with self._lock:
            return list(self._events)

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def start_listening(self) -> None:
        """Move into WAKE_LISTENING / LISTENING if wake-word is enabled."""
        if not self._enabled:
            logger.info("Wake-word disabled in settings — stay IDLE")
            return
        self._set_state(VoiceState.WAKE_LISTENING)

    def stop_listening(self) -> None:
        self._set_state(VoiceState.IDLE)

    def pause(self) -> None:
        """Pause the pipeline (e.g. during long-running shell ops)."""
        prev = self._state
        self._set_state(VoiceState.IDLE)
        logger.info("Voice pipeline paused (was %s)", prev.name)

    def on_wake_detected(self, confidence: float = 1.0,
                         source: str = "") -> None:
        """Mark wake-word detection. Caller: tank_speech node / event handler."""
        if not (0.0 <= confidence <= 1.0):
            raise ValueError(f"confidence must be 0..1, got {confidence}")
        if confidence < self._sensitivity:
            logger.debug("Wake confidence %.2f < threshold %.2f — ignored",
                         confidence, self._sensitivity)
            return
        self._record_event(utterance="<wake>",
                           provider=self._wake_provider,
                           metadata={"confidence": confidence})
        self._bus.emit(Event(
            "voice_wake_detected",
            {"confidence": confidence, "source": source},
            source=source or self._wake_provider,
            priority=Priority.HIGH,
        ))
        self._set_state(VoiceState.LISTENING)

    def on_stt_result(self, utterance: str, confidence: float = 1.0,
                      source: str = "") -> None:
        """Called by higher-level pipelines when STT produces a transcript."""
        self._record_event(utterance=utterance,
                           provider=self._stt_provider,
                           metadata={"confidence": confidence})
        self._bus.emit(Event(
            "voice_stt_result",
            {"text": utterance, "confidence": confidence, "source": source},
            source=source or self._stt_provider,
        ))
        self._set_state(VoiceState.PROCESSING)

    def on_processing_complete(self, intent: str = "") -> None:
        """Intent router finished; pipeline ready for TTS or idle."""
        self._record_event(utterance=intent, provider="intent_router")
        if intent:
            self._bus.emit(Event("voice_intent_resolved", {"intent": intent},
                                 source="voice_manager"))
        # Flow returns to WAKE_LISTENING so the next utterance naturally
        # starts. Caller may explicitly stop_listening instead.
        if self._enabled:
            self._set_state(VoiceState.WAKE_LISTENING)
        else:
            self._set_state(VoiceState.IDLE)

    # ------------------------------------------------------------------
    # TTS queue
    # ------------------------------------------------------------------

    def say(self, text: str, *, priority: bool = False) -> int:
        """Enqueue ``text`` for TTS playback. Returns 1 if accepted, 0 if not."""
        if not isinstance(text, str):
            raise TypeError(f"text must be str, got {type(text).__name__}")
        text = text.strip()
        if not text:
            return 0
        if priority:
            # Drain and re-enqueue so priority jumps the line.
            with self._tts_queue.mutex:
                items = list(self._tts_queue.queue)
                self._tts_queue.queue.clear()
            self._tts_queue.put(text)
            for it in items:
                self._tts_queue.put(it)
        else:
            self._tts_queue.put(text)
        self._bus.emit(Event("voice_tts_queued", {"text": text},
                             source="voice_manager"))
        # Kick the worker if we weren't already speaking
        if self._state != VoiceState.SPEAKING:
            self._set_state(VoiceState.SPEAKING)
        return 1

    def say_now(self, text: str) -> int:
        """Priority-jump queue (used for system warnings)."""
        return self.say(text, priority=True)

    def cancel_tts(self) -> int:
        """Drop every queued utterance. Returns number cancelled."""
        dropped = 0
        with self._tts_queue.mutex:
            dropped = len(self._tts_queue.queue)
            self._tts_queue.queue.clear()
        if dropped:
            logger.info("Cancelled %d queued TTS utterances", dropped)
        if self._state == VoiceState.SPEAKING:
            self.on_processing_complete(intent="<cancelled>")
        return dropped

    def _start_tts_thread(self) -> None:
        if self._tts_thread and self._tts_thread.is_alive():
            return
        t = threading.Thread(
            target=self._tts_worker, name="tank_os_voice_tts", daemon=True
        )
        self._tts_thread = t
        t.start()

    def _tts_worker(self) -> None:
        """Drain TTS queue using the linked Piper swapper or stub."""
        while True:
            try:
                text = self._tts_queue.get()
            except Exception:  # pragma: no cover - shouldn't happen
                continue
            if not text:
                continue
            self._bus.emit(Event(
                "voice_tts_started", {"text": text},
                source="voice_manager",
            ))
            try:
                if self._low_level is not None:
                    # pylint: disable-next=broad-except
                    try:
                        self._low_level.synth(text)
                    except Exception as exc:
                        logger.debug("low_level.synth failed: %s", exc)
                # Even when stubbed we honour a small playback delay so
                # the operator sees a visible SPEAKING state change.
                _playback_seconds = max(0.1, min(8.0, len(text) * 0.045))
                time.sleep(_playback_seconds)
            finally:
                self._bus.emit(Event(
                    "voice_tts_finished", {"text": text},
                    source="voice_manager",
                ))
                if self._tts_queue.empty():
                    self.on_processing_complete(intent="<tts-empty>")

    # ------------------------------------------------------------------
    # Settings hot-reload
    # ------------------------------------------------------------------

    def reload_settings(self) -> None:
        prev_enabled = bool(getattr(self, "_enabled", True))
        self._bind_settings()
        if prev_enabled and not self._enabled:
            self.stop_listening()
        elif (not prev_enabled) and self._enabled:
            self.start_listening()
        logger.info("Voice settings reloaded")

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _set_state(self, new_state: VoiceState) -> None:
        if new_state == self._state:
            return
        prev = self._state
        self._state = new_state
        # Backward-compat alias for code that consults the boolean.
        self._listening = new_state in (VoiceState.WAKE_LISTENING,
                                        VoiceState.LISTENING)
        self._record_event(provider="", state=new_state)
        self._bus.emit(Event(
            "voice_state_changed",
            {"previous": prev.name, "state": new_state.name},
            source="voice_manager",
            priority=Priority.NORMAL,
        ))

    def _record_event(self, *, state: Optional[VoiceState] = None,
                      utterance: str = "", provider: str = "",
                      metadata: Optional[Dict[str, Any]] = None) -> None:
        ev = VoiceEvent(
            timestamp=time.time(),
            state=state if state is not None else self._state,
            utterance=utterance, provider=provider,
            metadata=metadata or {},
        )
        with self._lock:
            self._events.append(ev)
            if len(self._events) > self._max_events:
                self._events = self._events[-self._max_events:]
