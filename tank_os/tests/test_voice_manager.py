"""pytest suite for :mod:`tank_os.core.voice_manager`."""
from __future__ import annotations

import threading
import time

import pytest

from tank_os.core.settings_manager import SettingsManager
from tank_os.core.voice_manager import VoiceManager, VoiceState


def test_initialize_emits_ready_without_state_transition(
    silence_tts_worker, event_catcher,
):
    catcher = event_catcher("voice_manager_ready",
                            "voice_state_changed")
    vm = VoiceManager()
    assert vm.state is VoiceState.IDLE
    vm.initialize()
    # Ready event fired once — but no spurious state change.
    assert len(catcher.of("voice_manager_ready")) == 1
    assert catcher.count("voice_state_changed") == 0
    # Providers are resolved to the stub/event-bus defaults in sandbox.
    assert vm.wake_provider == "event-bus"
    assert vm.stt_provider == "event-bus"
    assert vm.state is VoiceState.IDLE


def test_invalid_confidence_rejected(silence_tts_worker):
    vm = VoiceManager()
    vm.initialize()
    with pytest.raises(ValueError):
        vm.on_wake_detected(confidence=1.5)
    with pytest.raises(ValueError):
        vm.on_wake_detected(confidence=-0.01)


def test_wake_below_threshold_is_ignored(silence_tts_worker, event_catcher):
    catcher = event_catcher("voice_wake_detected")
    vm = VoiceManager()
    vm.initialize()
    vm.start_listening()  # → WAKE_LISTENING
    vm.on_wake_detected(confidence=0.1)  # default sensitivity is 0.5
    assert vm.state is VoiceState.WAKE_LISTENING
    assert catcher.count("voice_wake_detected") == 0


def test_wake_promotes_to_listening(silence_tts_worker, event_catcher):
    catcher = event_catcher("voice_wake_detected",
                            "voice_state_changed")
    vm = VoiceManager()
    vm.initialize()
    vm.start_listening()
    vm.on_wake_detected(confidence=1.0, source="tank_speech")
    assert vm.state is VoiceState.LISTENING
    assert len(catcher.of("voice_wake_detected")) == 1
    transitions = [e.data.get("state")
                   for e in catcher.of("voice_state_changed")]
    assert transitions.count("WAKE_LISTENING") == 1
    assert transitions.count("LISTENING") == 1


def test_say_enqueue_and_priority_jump(silence_tts_worker, event_catcher):
    catcher = event_catcher("voice_tts_queued")
    vm = VoiceManager()
    vm.initialize()
    assert vm.say("first") == 1
    assert vm.say("second") == 1
    assert vm.say_now("urgent") == 1
    order = []
    while not vm._tts_queue.empty():
        order.append(vm._tts_queue.get_nowait())
    assert order == ["urgent", "first", "second"]
    assert catcher.count("voice_tts_queued") == 3


def test_say_empty_or_whitespace_dropped(silence_tts_worker, event_catcher):
    catcher = event_catcher("voice_tts_queued")
    vm = VoiceManager()
    vm.initialize()
    assert vm.say("") == 0
    assert vm.say("   ") == 0
    assert vm.say("\n\t") == 0
    assert catcher.count("voice_tts_queued") == 0


def test_say_non_string_raises_type_error(silence_tts_worker):
    vm = VoiceManager()
    vm.initialize()
    with pytest.raises(TypeError):
        vm.say(123)  # type: ignore[arg-type]


def test_cancel_tts_drops_queued_items(silence_tts_worker):
    vm = VoiceManager()
    vm.initialize()
    vm.say("a")
    vm.say("b")
    vm.say("c")
    assert vm.cancel_tts() == 3
    assert vm._tts_queue.empty()


def test_stt_result_moves_to_processing(silence_tts_worker, event_catcher):
    catcher = event_catcher("voice_stt_result", "voice_state_changed")
    vm = VoiceManager()
    vm.initialize()
    vm.start_listening()
    vm.on_wake_detected(confidence=1.0)
    vm.on_stt_result("hello tank", confidence=0.91, source="whisper")
    assert vm.state is VoiceState.PROCESSING
    [event] = catcher.of("voice_stt_result")
    assert event.data["text"] == "hello tank"
    assert event.data["confidence"] == 0.91


def test_processing_complete_returns_to_listen_when_enabled(
    silence_tts_worker, event_catcher,
):
    catcher = event_catcher("voice_intent_resolved")
    vm = VoiceManager()
    vm.initialize()
    vm.start_listening()
    vm.on_processing_complete(intent="greet")
    assert vm.state is VoiceState.WAKE_LISTENING
    assert len(catcher.of("voice_intent_resolved")) == 1


def test_processing_complete_idle_when_disabled(
    silence_tts_worker, event_catcher,
):
    vm = VoiceManager()
    vm.initialize()
    SettingsManager().set("voice.wake_word_enabled", False)
    vm.reload_settings()
    vm.on_processing_complete(intent="done")
    assert vm.state is VoiceState.IDLE


def test_reload_settings_disables_when_flag_off(silence_tts_worker):
    vm = VoiceManager()
    vm.initialize()
    vm.start_listening()  # WAKE_LISTENING
    SettingsManager().set("voice.wake_word_enabled", False)
    vm.reload_settings()
    assert vm.state is VoiceState.IDLE


def test_recent_events_bounded():
    vm = VoiceManager()
    for i in range(80):
        vm._record_event(utterance=f"u{i}")
    assert len(vm.recent_events) == vm._max_events == 50
    assert vm.recent_events[-1].utterance == "u79"


def test_state_change_emits_with_priority(silence_tts_worker,
                                           event_catcher):
    catcher = event_catcher("voice_state_changed")
    vm = VoiceManager()
    vm.initialize()
    vm.start_listening()
    vm.stop_listening()
    transitions = [e.data.get("state")
                   for e in catcher.of("voice_state_changed")]
    assert transitions[:2] == ["WAKE_LISTENING", "IDLE"]


def test_async_wake_then_stt_threaded_invariant(silence_tts_worker):
    """Concurrent wake/stt events from different threads converge to a
    deterministic end-state without crashing the state machine."""
    vm = VoiceManager()
    vm.initialize()
    vm.start_listening()  # → WAKE_LISTENING
    vm.on_wake_detected(confidence=1.0)  # → LISTENING
    def _worker():
        for i in range(20):
            vm.on_stt_result(f"u{i}")                   # → PROCESSING
            time.sleep(0.001)
            vm.on_processing_complete(intent=f"i{i}")  # → WAKE_LISTENING (enabled)
    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout=2.0)
    # With wake still enabled, processing_complete always returns to
    # WAKE_LISTENING — the only invariant the manager guarantees.
    assert vm.state is VoiceState.WAKE_LISTENING
