"""tank_emotions — a comprehensive catalog of human emotions.

Re-exports the typed schema, the auto-discovered registry, and the
companion helpers.  Reading this top-level file should be enough to
write a downstream companion runtime::

    from tank_emotions import discover, companion_plan, score_text
    registry = discover()
    emo = registry["joy"]
    print(companion_plan(emo).stance)
    print(score_text("I'm ecstatic!"))
"""
from __future__ import annotations

from .core import Emotion, rough_category, safe_default_desc
from .taxonomy import discover, names, get, by_taxonomy, by_category, \
    summary_table, FRAMEWORKS
from .transitions import score as transition_score, plausible_pairs, \
    Plausibility
from .decay import DecayedEmotion, decay_to, fresh, should_relax
from .companion import plan as companion_plan, CompanionPlan, \
    instruction_text
from .dialogue import empathy_prefix, safe_floor_for, fallback_reply
from .safety import classify as classify_safety, SafetyFlag
from .wheel import render_ascii as render_plutchik_wheel, \
    grid_to_string as plutchik_grid_to_string, Poles as PlutchikPoles
from .signals import score_text, score_face, score_audio, \
    dominant, annotated


def __getattr__(name):
    """Lazy module-level convenience — ALL_EMOTIONS / __all__."""
    if name == "ALL_EMOTIONS":
        return tuple(sorted(discover().keys()))
    if name == "__all__":
        return ("Emotion", "rough_category", "discover", "names",
                "get", "by_taxonomy", "by_category", "summary_table",
                "transition_score", "plausible_pairs", "Plausibility",
                "decay_to", "fresh", "should_relax", "CompanionPlan",
                "companion_plan", "instruction_text", "empathy_prefix",
                "safe_floor_for", "fallback_reply", "classify_safety",
                "SafetyFlag", "render_plutchik_wheel",
                "plutchik_grid_to_string", "PlutchikPoles",
                "score_text", "score_face", "score_audio",
                "dominant", "annotated", "FRAMEWORKS")
    raise AttributeError(name)


__version__ = "0.1.0"
