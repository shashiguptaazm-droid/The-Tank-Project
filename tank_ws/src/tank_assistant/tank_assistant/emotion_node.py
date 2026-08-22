"""Robot personality / emotion engine.

A minimal valence-arousal emotion model. Maps intent / assistant context
to a discrete mood, **with smoothing**: a mood decays back to "neutral"
after ``DECAY_TO_NEUTRAL_SEC`` seconds of inactivity, and a successful
``/meta/decision_append_result`` injects a 5-second "happy" spike so the
robot visibly reacts to its own learning (the "feel-good loop").

Subscribes
    /intent_text                  std_msgs/String
    /assistant_text               std_msgs/String
    /meta/decision_append_result  std_msgs/String JSON  (feel-good hook)

Publishes
    /emotion/state                std_msgs/String  ("happy"|"sad"|"alert"|
                                                    "curious"|"neutral")

Other display nodes (eyes, OLED, dashboard) subscribe to ``/emotion/state``
and apply their own topic→expression mapping. See
``tank_vision/eye_lcd_bridge.py`` and ``tank_display/display_node.py``.

The classifier is intentionally lightweight (token-bucket intent). LLM
projects can swap in VADER or a fine-tuned classifier by replacing
:class:`classify`.
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass

try:
    import rclpy                                      # noqa: F401
    from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
    from rclpy.node import Node
    from std_msgs.msg import String
    _RCLPY_AVAILABLE = True
except ImportError:
    # rclpy not installed (e.g. dev sandbox / CI). Stub the symbols so the
    # pure-Python state machine below remains importable for pytest.
    # Instantiation will raise clearly if anyone tries to spin up the
    # ROS node on such a host.
    _RCLPY_AVAILABLE = False

    class _StubNode:                                   # type: ignore[no-redef]
        def __init__(self, *a, **k):
            raise ImportError(
                "rclpy is not installed; EmotionNode requires ROS 2 Humble. "
                "Run scripts/provision_pi5.sh --apply on the Jetson."
            )

    class _StubString:                                 # type: ignore[no-redef]
        def __init__(self, *a, **k):
            raise ImportError(
                "std_msgs is not installed; EmotionNode requires ROS 2 Humble."
            )

    Node = _StubNode           # type: ignore[assignment]
    String = _StubString       # type: ignore[assignment]
    MutuallyExclusiveCallbackGroup = object  # type: ignore[assignment] — noop


# --------------------------------------------------------------------------- #
# classifier — kept verbatim from the previous version so existing tests &
# rag_node still hold.  Additions below: state + decay + feel-good hook.
# --------------------------------------------------------------------------- #

POSITIVE_TOKENS = {
    "love", "thanks", "thank", "good", "great", "nice", "please",
    "happy", "good morning", "good night", "appreciate", "wonderful",
}
NEGATIVE_TOKENS = {
    "stop", "no", "bad", "wrong", "angry", "mad", "hate", "shut up",
    "leave me alone", "annoying",
}
CURIOUS_TOKENS = {
    "what", "why", "how", "when", "where", "tell me", "explain",
    "are you", "can you", "could you", "do you",
}
ALERT_TOKENS = {
    "alert", "warning", "danger", "intruder", "alarm", "fire", "leak",
    "fall", "help", "911",
}

# Higher = harder to override. Used for hysteresis on classified intents.
MOOD_PRIORITY = {"alert": 4, "sad": 3, "happy": 2, "curious": 1, "neutral": 0}


def classify(text: str) -> str:
    low = text.lower()
    if any(tok in low for tok in ALERT_TOKENS):
        return "alert"
    if any(tok in low for tok in NEGATIVE_TOKENS):
        return "sad"
    if any(tok in low for tok in CURIOUS_TOKENS):
        return "curious"
    if any(tok in low for tok in POSITIVE_TOKENS):
        return "happy"
    return "neutral"


# --------------------------------------------------------------------------- #
# state machine — a tiny dataclass plus decay
# --------------------------------------------------------------------------- #

# After this many seconds without a fresh classification, mood drifts
# back to "neutral". Long enough to look intentional; short enough not
# to feel "stuck".
DECAY_TO_NEUTRAL_SEC = 8.0

# Feel-good spike duration when /meta/decision_append succeeds.
FEEL_GOOD_SEC = 5.0

# Min age before a lower-priority classification replaces the current mood.
HYSTERESIS_SEC = 2.0


@dataclass
class EmotionState:
    mood: str = "neutral"
    ts: float = 0.0          # last set time (time.time())
    source: str = "init"     # "intent"|"assistant"|"feel_good"|"decay"
    valence: float = 0.0     # -1..+1, rough sentiment proxy
    arousal: float = 0.0     # 0..1, intensity proxy

    def age(self) -> float:
        return time.time() - self.ts


def _valence_for(mood: str) -> float:
    return {
        "happy":   0.8,
        "alert":  -0.4,
        "sad":    -0.7,
        "curious": 0.2,
        "neutral": 0.0,
    }.get(mood, 0.0)


def _arousal_for(mood: str) -> float:
    return {
        "happy":   0.6,
        "alert":   0.9,
        "sad":     0.4,
        "curious": 0.5,
        "neutral": 0.2,
    }.get(mood, 0.0)


class EmotionStateMachine:
    """Minimal thread-safe state machine."""

    def __init__(self) -> None:
        self._state = EmotionState()
        self._prior_mood: str = "neutral"   # restored after feel-good spikes
        self._lock = threading.Lock()

    def snapshot(self) -> EmotionState:
        with self._lock:
            return EmotionState(
                mood=self._state.mood,
                ts=self._state.ts,
                source=self._state.source,
                valence=self._state.valence,
                arousal=self._state.arousal,
            )

    def set(self, mood: str, source: str = "intent",
            force: bool = False) -> bool:
        """Try to set mood. ``force=True`` bypasses hysteresis (used by
        the feel-good hook and by decay). Returns True if applied."""
        mood = mood if mood in MOOD_PRIORITY else "neutral"
        with self._lock:
            current_age = self._state.age()
            same = self._state.mood == mood
            if same:
                # Refresh the timestamp so it doesn't decay immediately.
                self._state.ts = time.time()
                self._state.source = source
                return False
            if not force:
                # Higher or equal priority overrides instantly.
                new_p = MOOD_PRIORITY[mood]
                cur_p = MOOD_PRIORITY[self._state.mood]
                if new_p < cur_p and current_age < HYSTERESIS_SEC:
                    # Lower-priority mood during hysteresis → ignore.
                    return False
            if self._state.source != "feel_good":
                # Remember the underlying mood so the feel-good spike can
                # restore it after FEEL_GOOD_SEC elapses.
                self._prior_mood = self._state.mood
            self._state.mood = mood
            self._state.ts = time.time()
            self._state.source = source
            self._state.valence = _valence_for(mood)
            self._state.arousal = _arousal_for(mood)
            return True

    def decay_if_stale(self, threshold: float = DECAY_TO_NEUTRAL_SEC) -> bool:
        """If current mood is older than ``threshold``, force-neutral.
        Respects FEEL_GOOD_SEC for spikes: a feel-good "happy" mood
        decays after FEEL_GOOD_SEC, not DECAY_TO_NEUTRAL_SEC.
        Returns True if mood changed."""
        with self._lock:
            if self._state.mood == "neutral":
                return False
            effective_threshold = (
                FEEL_GOOD_SEC
                if self._state.source == "feel_good"
                else threshold
            )
            if self._state.age() < effective_threshold:
                return False
            if self._state.source == "feel_good":
                # Restore the prior mood — not always neutral.
                next_mood = self._prior_mood
            else:
                next_mood = "neutral"
            self._state.mood = next_mood
            self._state.ts = time.time()
            self._state.source = "decay"
            self._state.valence = _valence_for(next_mood)
            self._state.arousal = _arousal_for(next_mood)
            return True


# --------------------------------------------------------------------------- #
# ROS node
# --------------------------------------------------------------------------- #


class EmotionNode(Node):
    def __init__(self) -> None:
        super().__init__("emotion_node")
        self._machine = EmotionStateMachine()
        self._machine.set("neutral", source="init", force=True)

        # Multi-subscriber guard per design rule 1.
        cbg = MutuallyExclusiveCallbackGroup()

        self.create_subscription(String, "/intent_text",
                                  self._on_intent, 10, callback_group=cbg)
        self.create_subscription(String, "/assistant_text",
                                  self._on_assistant, 10, callback_group=cbg)
        self.create_subscription(String, "/meta/decision_append_result",
                                  self._on_decision_result, 10,
                                  callback_group=cbg)

        self._state_pub = self.create_publisher(String, "/emotion/state", 10)
        # 2 Hz decay + publish so downstream sees updates promptly.
        self.create_timer(0.5, self._tick)
        self.get_logger().info("emotion_node initialised")

    # ------------------- handlers -------------------
    def _on_intent(self, msg: String) -> None:
        mood = classify(msg.data or "")
        self._machine.set(mood, source="intent")

    def _on_assistant(self, msg: String) -> None:
        mood = classify(msg.data or "")
        # Assistant copy down-weights so it can't trap us.
        snap = self._machine.snapshot()
        if snap.mood == "alert":
            return
        self._machine.set(mood, source="assistant")

    def _on_decision_result(self, msg: String) -> None:
        try:
            payload = json.loads(msg.data or "{}")
        except Exception as exc:
            self.get_logger().warn(
                f"decision_append_result: bad json: {exc}",
                throttle_duration_sec=20.0,
            )
            return
        ok = bool(payload.get("persisted") or payload.get("json_appended"))
        if not ok:
            return
        applied = self._machine.set("happy", source="feel_good", force=True)
        if applied:
            self.get_logger().info(
                f"feel-good spike: decision {payload.get('id', '?')} succeeded"
            )

    # ------------------- tick -------------------
    def _tick(self) -> None:
        # Decay stale moods first so the publish reflects fresh state.
        self._machine.decay_if_stale()
        snap = self._machine.snapshot()
        self._state_pub.publish(String(data=snap.mood))


def main(args=None) -> None:
    rclpy.init(args=args)
    node = EmotionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
