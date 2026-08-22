"""Pure-Python intent recogniser for The Tank Project.

Sits between ``stt_node`` (Whisper) and the rest of the bridge:

    /intent_text (Whisper)  ─►  /intent_command  (matched grammar)
                            \─►  /llm_prompt     (fall-through)

Why pure-Python instead of Vosk
-------------------------------
* No competing ASR engine — Whisper is already pinned to ``tiny.en`` on
  the Pi 5 and adding a second would compete for CPU.
* Latency is microseconds — a regex + difflib.SequenceMatcher beat a
  50 MB model.
* Local hits ride the *existing* ``voice.*`` plugin manifest, so the
  LLM only runs on grammar miss or free-form chat.
* All grammar is in code (no model download), so benches + CI pass
  hermetically.

Wire shape
----------
``/intent_command`` payload (JSON dumped to std_msgs/String)::

    {"cmd": "voice.play_music",
     "params": {"query": "lo-fi"},
     "slots": {"query": "lo-fi"},
     "raw": "play some lo-fi music",
     "confidence": 0.92,
     "cid": "play_music"}

Confidence is in [0, 1]. The shell bridge dispatches on ``cid`` /
``cmd`` exactly like today; only the upstream parser changed.

Topics
------
* ``/intent_text``            std_msgs/String  (subscribed)
* ``/intent_command``         std_msgs/String  (published on match)
* ``/llm_prompt``             std_msgs/String  (published on miss)
* ``/intent_router/event``    std_msgs/String  (audit trail)
"""
from __future__ import annotations

import json
import re
import threading
import time
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

try:
    import rclpy                                                  # noqa: F401
    from rclpy.node import Node
    from std_msgs.msg import String
    _RCLPY_AVAILABLE = True
except ImportError:
    _RCLPY_AVAILABLE = False
    class _StubNode:                                             # type: ignore[no-redef]
        def __init__(self, *a, **k):
            raise ImportError(
                "rclpy is not installed; IntentRouterNode requires ROS 2 Humble."
            )
    Node = _StubNode
    class _StubString:                                           # type: ignore[no-redef]
        def __init__(self, data: str = "") -> None:
            self.data = data
    String = _StubString


# Canonical zone list — must match `tank_command_bridge.plugins._house_helpers`.
# Keep these two in sync if either side changes.
_KNOWN_ZONES = (
    "kitchen", "bedroom", "living room", "lounge", "office", "lab",
    "garage", "garden", "patio", "hallway", "study", "den", "dining room",
)
_ZONE_REGEX = "|".join(z.replace(" ", r"\s*") for z in _KNOWN_ZONES)


@dataclass
class GrammarCommand:
    """One entry in the default grammar."""

    cid: str                                          # unique command id
    target: str                                       # voice.<plugin_name>
    patterns: List[str]                               # lower-cased regexes
    slots: Dict[str, str] = field(default_factory=dict)
    confidence_floor: float = 0.55
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cid":              self.cid,
            "target":           self.target,
            "patterns":         list(self.patterns),
            "slots":            dict(self.slots),
            "confidence_floor": self.confidence_floor,
            "description":      self.description,
        }


def _word_boundary(text: str, start: int, end: int) -> bool:
    """True iff (start, end) doesn't slice through a word."""
    if start > 0 and text[start - 1].isalnum():
        return False
    if end < len(text) and text[end].isalnum():
        return False
    return True


def _strip_slot_token(pattern: str) -> str:
    """Strip ``(?P<name>...)`` slot noise from a pattern for fuzzy scoring."""
    return re.sub(r"\(\?P<[^>]+>(?:[^)]+)\)", "X", pattern)


def score_match(text: str,
                patterns: List[str]) -> Tuple[float, Dict[str, str]]:
    """Score ``text`` against every pattern, return (conf, slots).

    Confidence is the *maximum* of:
      * character-coverage of the regex hit (len(matched) / len(text))
      * difflib.SequenceMatcher ratio over pattern → matched substring
    plus a small bonus when the hit lands on a word boundary.
    """
    text = text.lower().strip()
    if not text:
        return 0.0, {}
    best_conf, best_slots = 0.0, {}
    for raw in patterns:
        try:
            m = re.search(raw, text)
        except re.error:
            continue
        if not m:
            continue
        mlen = m.end() - m.start()
        coverage = min(1.0, mlen / max(1.0, len(text)))
        sm = SequenceMatcher(
            None,
            m.group(0).lower(),
            _strip_slot_token(raw).lower()[: mlen or 1],
        ).ratio()
        conf = max(coverage, sm)
        if _word_boundary(text, m.start(), m.end()):
            conf += 0.10
        if conf > best_conf:
            best_conf = conf
            best_slots = {k: v.strip()
                          for k, v in m.groupdict().items() if v}
    return min(1.0, best_conf), best_slots


# ────────────────────────────────────────────────────────────────────────────
# Default grammar — extends the manifest the bridge already exposes.
#
# Order matters: power_sleep comes BEFORE move_zone so "go to sleep"
# routes to the power plugin, not the zone router. Concrete zones are
# whitelisted in move_zone (see _ZONE_REGEX above) so generic verbs
# like "sleep" / "dock" don't accidentally collide.
# ────────────────────────────────────────────────────────────────────────────

DEFAULT_GRAMMAR: List[GrammarCommand] = [
    GrammarCommand(
        cid="play_music",
        target="voice.play_music",
        patterns=[
            r"\bplay(?:\s+some)?\s+(?P<query>[\w\s\-']+?)\s+music\b",
            r"\bplay\s+music(?:\s+(?:called|by|named)\s+(?P<query>[\w\s\-']+))?",
            r"\bstart\s+music(?:\s+(?:called|by|named)\s+(?P<query>[\w\s\-']+))?",
        ],
        slots={"query": "title"},
        description="Play music matching `query` from the local library.",
    ),
    GrammarCommand(
        cid="play_video",
        target="voice.play_youtube",
        patterns=[
            r"\bplay\s+(?P<query>[\w\s\-']+?)\s+on\s+youtube\b",
            r"\byoutube\s+(?P<query>[\w\s\-']+)",
            r"\bplay\s+youtube\s+(?P<query>[\w\s\-']+)",
        ],
        slots={"query": "query"},
        description="Play `query` on YouTube via yt-dlp + cast.",
    ),
    GrammarCommand(
        cid="play_tv",
        target="voice.play_tv",
        patterns=[
            r"\bplay\s+(?P<query>[\w\s\-']+?)\s+on\s+(?P<device>the\s*tv|smart\s*tv|chromecast)\b",
            r"\bplay\s+on\s+(?P<device>tv|smart\s*tv|chromecast)\b",
        ],
        slots={"query": "query", "device": "device"},
        description="Cast media to the named TV.",
    ),
    GrammarCommand(
        cid="pause",
        target="voice.media_pause",
        patterns=[r"\bpause(?:\s+(?:the\s+)?(?:music|video|tv))?\b"],
        description="Pause currently playing media.",
    ),
    GrammarCommand(
        cid="resume",
        target="voice.media_resume",
        patterns=[r"\bresume(?:\s+(?:the\s+)?(?:music|video|tv))?\b"],
        description="Resume paused media.",
    ),
    GrammarCommand(
        cid="stop",
        target="voice.media_stop",
        patterns=[r"\bstop(?:\s+(?:the\s+)?(?:music|video|tv))?\b"],
        description="Stop currently playing media.",
    ),
    GrammarCommand(
        cid="power_sleep",
        target="voice.power",
        patterns=[
            r"\bgo\s+to\s+sleep\b",
            r"\bpower\s+(?:down|off|sleep)\b",
            r"\b(?:sleep|hibernate)\b",
        ],
        description="Switch the tank to sleep mode.",
    ),
    GrammarCommand(
        cid="move_zone",
        target="voice.move_to",
        patterns=[
            rf"\b(?:go|move)\s+to\s+(?:the\s+)?(?P<zone>{_ZONE_REGEX})\b",
        ],
        slots={"zone": "zone"},
        description="Move to a known spatial zone.",
    ),
    GrammarCommand(
        cid="move_relative",
        target="voice.move_to",
        patterns=[
            r"\b(?P<direction>forward|backward|back|left|right|back\s+up)\s+(?P<level>[\w\s]+)\b",
            r"\bturn\s+(?P<direction>left|right)\b",
        ],
        slots={"direction": "direction", "level": "level"},
        description="Move or turn relatively.",
    ),
    GrammarCommand(
        cid="whereami",
        target="voice.whereami",
        patterns=[
            r"\bwhere\s+are\s+you\b",
            r"\bwhere\s+am\s+i\b",
            r"\bcurrent\s+(?:zone|room|location)\b",
        ],
        description="Report current zone.",
    ),
    GrammarCommand(
        cid="detect_persons",
        target="voice.detect_persons",
        patterns=[
            r"\bwho'?s\s+in\s+(?:the\s+)?(?:room|house|here)\b",
            r"\bdetect\s+persons?\b",
            r"\bhow\s+many\s+people\b",
        ],
        description="Run YOLO person detection.",
    ),
    GrammarCommand(
        cid="detect_intruder",
        target="voice.detect_intruder",
        patterns=[
            r"\bis\s+anyone\s+there\s+you\s+don'?t\s+recognise\b",
            r"\bdetect\s+intruder\b",
            r"\bcheck\s+for\s+intruders?\b",
        ],
        description="Check for an unrecognised face.",
    ),
    GrammarCommand(
        cid="play_anim",
        target="voice.eye_play_animation",
        patterns=[
            r"\bplay\s+(?:the\s+)?(?P<title>[\w\-]+)\s+animation\b",
            r"\banimate\s+(?P<title>[\w\-]+)\b",
        ],
        slots={"title": "title"},
        description="Play an eye animation by title.",
    ),
    # ---- chassis motion commands -------------------------------------------
    GrammarCommand(
        cid="drive_forward",
        target="voice.drive_forward",
        patterns=[
            r"\b(?:drive|go|move)\s+forward(?:\s+(?P<distance>[\w\s\-]+))?\b",
            r"\bforward(?:\s+(?P<distance>[\w\s\-]+))?\b",
        ],
        slots={"distance": "distance"},
        description="Drive forward by an optional free-form distance.",
    ),
    GrammarCommand(
        cid="drive_backward",
        target="voice.drive_backward",
        patterns=[
            r"\b(?:drive|go|move)\s+backward(?:\s+(?P<distance>[\w\s\-]+))?\b",
            r"\b(?:reverse|back\s*up)(?:\s+(?P<distance>[\w\s\-]+))?\b",
        ],
        slots={"distance": "distance"},
        description="Drive backward by an optional free-form distance.",
    ),
    GrammarCommand(
        cid="brake",
        target="voice.brake_motion",
        patterns=[
            r"\b(?:brake|stop|hault?|freeze\s+up)\b",
            r"\bemergency\s+(?:brake|stop)\b",
        ],
        description="Halt any chassis motion immediately.",
    ),
    GrammarCommand(
        cid="turn_left",
        target="voice.turn_left",
        patterns=[
            r"\bturn\s+left(?:\s+(?P<angle>[\w\s]+))?",
            r"\bleft(?:\s+(?P<angle>[\w\s]+))?$",
        ],
        slots={"angle": "angle"},
        description="Rotate the chassis anticlockwise.",
    ),
    GrammarCommand(
        cid="turn_right",
        target="voice.turn_right",
        patterns=[
            r"\bturn\s+right(?:\s+(?P<angle>[\w\s]+))?",
            r"\bright(?:\s+(?P<angle>[\w\s]+))?$",
        ],
        slots={"angle": "angle"},
        description="Rotate the chassis clockwise.",
    ),
    GrammarCommand(
        cid="spin",
        target="voice.spin_around",
        patterns=[
            r"\bspin(?:\s+(?:around|in\s+place))?(?:\s+(?P<direction>left|right))?\b",
        ],
        slots={"direction": "direction"},
        description="Rotate the chassis 360° in place.",
    ),
    GrammarCommand(
        cid="set_max_speed",
        target="voice.set_max_speed",
        patterns=[
            r"\bset\s+(?:max|maximum)\s+speed\s+(?P<linear_mps>[\d.]+)(?:\s+m/?s)?",
            r"\bslow\s+down\s+to\s+(?P<linear_mps>[\d.]+)",
        ],
        slots={"linear_mps": "level"},
        description="Configure the chassis speed envelope.",
    ),
    GrammarCommand(
        cid="set_cruise_mode",
        target="voice.set_cruise_mode",
        patterns=[
            r"\b(?:enable|turn\s+on)\s+cruise(?:\s+mode)?\b",
            r"\b(?:disable|turn\s+off)\s+cruise(?:\s+mode)?\b",
        ],
        description="Toggle cruise mode.",
    ),
    GrammarCommand(
        cid="follow_me",
        target="voice.follow_me",
        patterns=[
            r"\bfollow\s+me\b",
            r"\bcome\s+with\s+me\b",
        ],
        description="Arm follow-me tracker.",
    ),
    GrammarCommand(
        cid="stop_follow_me",
        target="voice.stop_follow_me",
        patterns=[
            r"\b(?:stop|cancel)\s+follow(?:ing)?\b",
        ],
        description="Disengage follow-me tracker.",
    ),
    GrammarCommand(
        cid="pause_patrol",
        target="voice.patrol.pause",
        patterns=[r"\bpause\s+(?:the\s+)?patrol\b"],
        description="Pause autonomous patrol.",
    ),
    GrammarCommand(
        cid="resume_patrol",
        target="voice.patrol.resume",
        patterns=[r"\bresume\s+(?:the\s+)?patrol\b"],
        description="Resume autonomous patrol.",
    ),
    # ---- torrent display commands -----------------------------------------
    GrammarCommand(
        cid="torrent_pick",
        target="voice.torrent_pick",
        patterns=[
            r"\b(?:download|grab|get)\s+(?:the\s+)?"
            r"(?P<ord_word>first|second|third|fourth|fifth|sixth|last)"
            r"\s+(?:one|item|result)\b",
            r"\b(?:download|grab|get)\s+(?:result\s+|item\s+)"
            r"(?P<ord>\d+)\b",
        ],
        slots={"ord_word": "level", "ord": "level"},
        description="Pick one of the most recent search results by ordinal.",
    ),
    GrammarCommand(
        cid="torrent_cancel",
        target="voice.torrent_cancel",
        patterns=[
            r"\b(?:cancel|stop|abort)\s+(?:the\s+)?(?:download|torrent)\b",
        ],
        description="Cancel an active torrent.",
    ),
    GrammarCommand(
        cid="show_torrent_results",
        target="voice.show_torrent_results",
        patterns=[
            r"\b(?:show|display|list)\s+(?:me\s+)?(?:the\s+)?torrent\s+results\b",
            r"\bwhat\s+did\s+(?:we|i)\s+(?:find|search)\b",
        ],
        description="Surface the most recent search results.",
    ),
]


# ────────────────────────────────────────────────────────────────────────────
# Matcher
# ────────────────────────────────────────────────────────────────────────────

class IntentMatcher:
    """Stateless regex + fuzzy matcher over a list of grammar commands."""

    def __init__(self, grammar: Optional[List[GrammarCommand]] = None) -> None:
        self.grammar: List[GrammarCommand] = list(grammar or DEFAULT_GRAMMAR)

    def match(self, text: str) -> Optional[Dict[str, Any]]:
        for cmd in self.grammar:
            conf, slots = score_match(text, cmd.patterns)
            if conf >= cmd.confidence_floor:
                return {
                    "cid":         cmd.cid,
                    "cmd":         cmd.target,
                    "params":      dict(slots),    # alias for the bridge
                    "slots":       dict(slots),
                    "confidence":  round(conf, 3),
                    "raw":         text,
                    "description": cmd.description,
                }
        return None

    def list_commands(self) -> List[Dict[str, Any]]:
        return [c.to_dict() for c in self.grammar]


# ────────────────────────────────────────────────────────────────────────────
# ROS node
# ────────────────────────────────────────────────────────────────────────────

class IntentRouterNode(Node):
    """ROS node that splits '/intent_text' into '/intent_command' or '/llm_prompt'."""

    def __init__(self, matcher: Optional[IntentMatcher] = None) -> None:
        super().__init__("intent_router")
        self._matcher = matcher or IntentMatcher()
        self._lock = threading.Lock()
        self.create_subscription(
            String, "/intent_text", self._on_intent, 10,
        )
        self._cmd_pub = self.create_publisher(
            String, "/intent_command", 10,
        )
        self._llm_pub = self.create_publisher(
            String, "/llm_prompt", 10,
        )
        self._audit_pub = self.create_publisher(
            String, "/intent_router/event", 10,
        )
        self.get_logger().info(
            f"intent_router ready ({len(self._matcher.grammar)} commands loaded)"
        )

    def _on_intent(self, msg: String) -> None:
        text = (msg.data or "").strip()
        if not text:
            return
        m = self._matcher.match(text)
        with self._lock:
            if m is not None:
                self._cmd_pub.publish(String(data=json.dumps(m)))
                self._audit_pub.publish(String(data=json.dumps({
                    "ts": time.time(), "matched": True,
                    "cmd": m["cmd"], "confidence": m["confidence"],
                    "raw": text[:200],
                })))
            else:
                # Fall through to the LLM path unchanged.
                self._llm_pub.publish(String(data=text))
                self._audit_pub.publish(String(data=json.dumps({
                    "ts": time.time(), "matched": False,
                    "raw": text[:200],
                })))


def main(args=None) -> None:
    rclpy.init(args=args)
    node = IntentRouterNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
