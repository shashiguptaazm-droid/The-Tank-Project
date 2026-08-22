"""tank_emotions.transitions — pairwise plausibility of a->b.

Works as a typed graph where every emotion can declare its
``transitions_out`` in the descriptor.  The runtime also has a fallback
valence / arousal heuristic so unknown transitions are still scored.

Returned ``Plausibility`` is ``(score, reason)`` where ``score`` is in
``[0.0, 1.0]``.  Use ``score >= 0.5`` as a sane "happy to play".
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from .core import Emotion


@dataclass
class Plausibility:
    a: str
    b: str
    score: float
    reason: str

    def to_dict(self) -> dict:
        return {"a": self.a, "b": self.b,
                "score": round(self.score, 3), "reason": self.reason}


_DECLARED = {}    # name -> list[str]
_DECLARED_TXT = {}  # name -> list[str]


def score(a: Emotion, b: Emotion) -> Plausibility:
    """Plausibility of moving from emotion ``a`` to ``b``."""
    # explicit declaration beats heuristic
    declared = set(a.transitions_out or [])
    if b.name in declared:
        return Plausibility(a.name, b.name, 0.95,
                            f"declared in {a.name}.transitions_out")

    # Heuristic valence / arousal axis transitions.
    v_delta = b.valence - a.valence
    a_delta = b.arousal - a.arousal
    within = (
        (abs(v_delta) <= 0.7 and abs(a_delta) <= 0.7)
        or a.companion_response == b.companion_response
    )
    if not within:
        return Plausibility(a.name, b.name, 0.10,
                            "too far in valence & arousal")

    # cope transitions: negative -> low arousal positive (relief lineage)
    if a.valence <= -0.2 and b.valence >= 0.2 and a.arousal > b.arousal:
        return Plausibility(a.name, b.name, 0.75,
                            "typical cope-up (relief / hope)")

    # decay transitions: high arousal -> low arousal same valence
    if (a.valence * b.valence > 0
            and b.arousal < a.arousal
            and abs(a.valence - b.valence) < 0.4):
        return Plausibility(a.name, b.name, 0.65, "decay-to-quiet")

    # neighboring quadrants only if mild
    if abs(v_delta) >= 0.5 and abs(a_delta) >= 0.5:
        return Plausibility(a.name, b.name, 0.30, "large axis swing")

    return Plausibility(a.name, b.name, 0.55, "neighbouring quadrant")


def plausible_pairs(emotions: list, threshold: float = 0.5) -> list:
    """All (a,b) pairs whose score is >= threshold, sorted desc."""
    pairs = []
    for a in emotions:
        for b in emotions:
            if a.name == b.name:
                continue
            p = score(a, b)
            if p.score >= threshold:
                pairs.append(p)
    return sorted(pairs, key=lambda p: -p.score)
