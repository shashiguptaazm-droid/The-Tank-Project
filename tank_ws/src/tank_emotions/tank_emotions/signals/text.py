"""tank_emotions.signals.text — keyword + marker scan for free-form text.

Lightweight detector that returns a per-emotion score in ``[0, 1]``
plus a ``dominant`` label.  Heavy classification is intentionally
delegated to a downstream LLM or a fine-tuned classifier; this module
is for *fast first-pass* scoring so the runtime can react before the
expensive model is ready.
"""
from __future__ import annotations

import re
from typing import Dict, List


NEGATIONS = ("not", "never", "no", "without", "barely", "hardly", "don't",
             "do not", "isn't", "wasn't", "shouldn't", "won't", "cant",
             "can't", "ain't")


def _is_negated(text: str, span: tuple, window: int = 5) -> bool:
    before = text[:span[0]].lower().split()
    return any(w in NEGATIONS for w in before[-window:])


def score_text(text: str, registry=None) -> Dict[str, float]:
    """Return per-emotion scores for ``text`` using each emotion's
    ``signal_words`` list.

    Word boundaries respected via ``\\b``.  Negations heuristically
    flip scoring (anything inside a negation is dropped to 0).
    """
    from ..taxonomy import discover
    registry = registry or discover()

    scores: Dict[str, float] = {}
    if not text:
        return scores
    lower = text.lower()
    for emo in registry.values():
        hit = 0
        for word in emo.signal_words or []:
            for m in re.finditer(rf"\b{re.escape(word)}\b", lower):
                if _is_negated(lower, m.span()):
                    continue
                hit += 1
        if hit:
            scores[emo.name] = min(1.0, hit / 3.0)
    return scores


def dominant(text: str, registry=None, threshold: float = 0.34) -> str:
    """Return the highest-scoring emotion, or ``'neutral'`` below threshold."""
    scores = score_text(text, registry)
    if not scores:
        return "neutral"
    name, sc = max(scores.items(), key=lambda kv: kv[1])
    return name if sc >= threshold else "neutral"


def annotated(text: str, registry=None) -> List[Dict[str, object]]:
    """Return ``[{emotion, hit}]`` pairs in scanning order.  Useful for
    building a small topic log of which emotion cues fired over time."""
    rows = []
    for emo_name, sc in score_text(text, registry).items():
        rows.append({"emotion": emo_name, "score": sc})
    rows.sort(key=lambda r: -r["score"])
    return rows
