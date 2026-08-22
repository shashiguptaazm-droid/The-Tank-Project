"""``voice.follow_me`` / ``voice.stop_follow_me`` + patrol pause/resume.

The follow-me plugin arms the tank's existing vision-based tracker
(``voice.detect_persons`` already exists) so the chassis always turns
toward the closest tracked person. ``stop_follow_me`` disengages.

The patrol pause/resume pair is grouped into a second plugin so a
chassis that's mid-patrol (e.g. ``voice.patrol_start`` is already in
``tank_patrol``) can be paused and resumed by voice.
"""
from __future__ import annotations

from typing import Any, Dict

from . import RobotPlugin
from ._chassis_helpers import NullChassisMotionProvider


def _provider(ctx: Any) -> Any:
    if ctx is not None and hasattr(ctx, "chassis_motion"):
        return ctx.chassis_motion
    return NullChassisMotionProvider()


class FollowMePlugin(RobotPlugin):
    NAME = "voice.follow_me"
    DESCRIPTION = (
        "Arms the chassis to track the closest person the camera sees "
        "and follow them at walking pace. Idempotent — safe to issue "
        "twice."
    )
    PARAMETERS_SCHEMA = {
        "type": "object",
        "properties": {
            "distance_m": {"type": "number",
                            "description": "Target stand-off distance "
                                            "from the person. Default 1.2.",
                            "minimum": 0.4, "maximum": 3.0,
                            "default": 1.2},
        },
    }
    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "engaged": {"type": "boolean"},
            "distance_m": {"type": "number"},
            "tts_text": {"type": "string"},
        },
    }
    TAGS = ["write", "voice", "chassis", "follow"]
    RATE_CLASS = "write"

    def run(self, params: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        prov = _provider(ctx)
        prov.follower_start()
        d = float(params.get("distance_m", 1.2) or 1.2)
        return {"_ok": True,
                "engaged": True,
                "distance_m": round(d, 2),
                "tts_text": f"Following. Staying about {d:.1f} meters back."}


class StopFollowMePlugin(RobotPlugin):
    NAME = "voice.stop_follow_me"
    DESCRIPTION = "Disengage the follow-me tracker and brake."
    PARAMETERS_SCHEMA = {"type": "object", "properties": {}}
    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "disengaged": {"type": "boolean"},
            "tts_text": {"type": "string"},
        },
    }
    TAGS = ["write", "voice", "chassis", "follow"]
    RATE_CLASS = "write"

    def run(self, params: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        prov = _provider(ctx)
        prov.follower_stop()
        from ._chassis_helpers import Twist
        prov.publish_twist(Twist())
        return {"_ok": True,
                "disengaged": True,
                "tts_text": "Stopping follow mode."}


class PausePatrolPlugin(RobotPlugin):
    NAME = "voice.patrol.pause"
    DESCRIPTION = "Pause the autonomous patrol loop if one is active."
    PARAMETERS_SCHEMA = {"type": "object", "properties": {}}
    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "paused": {"type": "boolean"},
            "tts_text": {"type": "string"},
        },
    }
    TAGS = ["write", "voice", "chassis", "patrol"]
    RATE_CLASS = "write"

    def run(self, params: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        prov = _provider(ctx)
        prov.patrol_pause()
        return {"_ok": True, "paused": True,
                "tts_text": "Patrol paused."}


class ResumePatrolPlugin(RobotPlugin):
    NAME = "voice.patrol.resume"
    DESCRIPTION = "Resume an autonomous patrol loop."
    PARAMETERS_SCHEMA = {"type": "object", "properties": {}}
    RESPONSE_SCHEMA = PausePatrolPlugin.RESPONSE_SCHEMA
    TAGS = ["write", "voice", "chassis", "patrol"]
    RATE_CLASS = "write"

    def run(self, params: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        prov = _provider(ctx)
        prov.patrol_resume()
        return {"_ok": True, "paused": False,
                "tts_text": "Patrol resumed."}
