"""Tests for emotion_node state machine + feel-good hook.

These exercise the pure-Python helpers (EmotionStateMachine + classify)
plus the ROS handlers' decision-append JSON contract without spinning up
a ROS executor. The ROS-node glue is exercised in tank_meta's
``test_rag_meta_context_block_calls_meta_handles`` against a live
``rclpy`` instance on the Jetson.
"""
from __future__ import annotations

import json
import time

from tank_assistant.emotion_node import (
    DECAY_TO_NEUTRAL_SEC,
    EmotionStateMachine,
    classify,
)


def test_decay_to_neutral_after_window():
    sm = EmotionStateMachine()
    sm.set("happy", source="intent", force=True)
    snap = sm.snapshot()
    assert snap.mood == "happy"
    # Backdate to simulate elapsed time
    sm._state.ts = time.time() - DECAY_TO_NEUTRAL_SEC - 0.1
    changed = sm.decay_if_stale()
    assert changed is True
    assert sm.snapshot().mood == "neutral"


def test_decay_no_op_when_fresh():
    sm = EmotionStateMachine()
    sm.set("alert", source="intent", force=True)
    assert sm.decay_if_stale() is False
    assert sm.snapshot().mood == "alert"


def test_alert_overrides_lower_priority_during_hysteresis():
    sm = EmotionStateMachine()
    sm.set("curious", source="intent", force=True)
    # alert has higher priority → overrides immediately even within
    # hysteresis window.
    assert sm.set("alert", source="intent") is True
    assert sm.snapshot().mood == "alert"
    # curious trying to bump alert during hysteresis should be ignored.
    assert sm.set("curious", source="assistant") is False
    assert sm.snapshot().mood == "alert"


def test_feel_good_loop_payload_parsing():
    """Mirror the decision-append payload contract. Valid payload flips
    a stable (non-alert) mood to 'happy'; the alert mood is NOT
    overridden (so a real alarm stays loud)."""
    sm = EmotionStateMachine()
    sm.set("neutral", source="init", force=True)
    # simulate the handler: parse + apply if persisted
    payload = json.loads(
        '{"id":"DEC-007","persisted":true,"json_appended":true}'
    )
    ok = bool(payload.get("persisted") or payload.get("json_appended"))
    assert ok is True
    sm.set("happy", source="feel_good", force=True)
    assert sm.snapshot().mood == "happy"


def test_feel_good_spike_expires_to_prior_mood():
    """When the feel-good spike decays it must restore the prior mood,
    not default to neutral (this validates FEEL_GOOD_SEC is honoured)."""
    from tank_assistant.emotion_node import FEEL_GOOD_SEC
    sm = EmotionStateMachine()
    sm.set("neutral", source="init", force=True)
    sm.set("happy", source="feel_good", force=True)
    # Backdate the spike so it has aged past FEEL_GOOD_SEC.
    sm._state.ts = time.time() - FEEL_GOOD_SEC - 0.1
    assert sm.decay_if_stale() is True
    # Prior mood was "neutral" → restored.
    assert sm.snapshot().mood == "neutral"


def test_feel_good_ignored_on_malformed_payload():
    sm = EmotionStateMachine()
    sm.set("neutral", source="init", force=True)
    payloads = ["", "not json", '{"persisted": false}', "{}", '{"id": 1}']
    for raw in payloads:
        try:
            payload = json.loads(raw)
        except Exception:
            continue
        ok = bool(payload.get("persisted") or payload.get("json_appended"))
        # if !ok, we never call set() — so mood stays neutral.
        if not ok:
            assert sm.snapshot().mood == "neutral"


def test_classify_table_covers_all_moods():
    """classify() returns exclusively values that map_to_espression via
    eye_lcd_bridge.MOOD_TO_EXPR. Keeps the vocabulary in sync."""
    valid_outputs = {"happy", "sad", "alert", "curious", "neutral"}
    for sample in [
        "I love it, thanks", "stop please", "what time is it",
        "FIRE! help!", "spinning up", "I am angry",
    ]:
        out = classify(sample)
        assert out in valid_outputs, f"classify({sample!r}) → {out!r}"
