"""tank_emotions.taxonomy — auto-discovers every emotion module.

Walk every submodule of :mod:`tank_emotions.emotions`, import its
``DESCRIPTOR`` (or build one from the legacy ``JOY = {...}`` style),
and lift it into a typed ``Emotion`` so the rest of the system can
look up by ``name``.

Frameworks cross-referenced:

* Plutchik's 8 primary emotions (the wheel we use for transitions).
* Ekman's 6 basic emotions (cross-cultural facial-action units).
* Izard's 10 differential emotions (self-conscious subset).
* Geneva Emotion Wheel (4 families).
* Parrott (3-level tree, summarized for primary + secondary).

Each emotion module declares its framework membership via the
``taxonomy`` field.  This module only aggregates them.
"""
from __future__ import annotations

import importlib
import pkgutil
from typing import Dict, Iterable, List, Optional

from .core import Emotion, safe_default_desc


# Module-level cache so repeated lookups don't re-import.
_REGISTRY: Dict[str, Emotion] = {}


def _descriptor_from_module(mod) -> Optional[Emotion]:
    """Lift an emotion-module into a typed ``Emotion``."""
    obj = getattr(mod, "DESCRIPTOR", None)
    if obj is None:
        # legacy style: top-level CAPS dict
        for attr in dir(mod):
            if attr.isupper() and attr not in {"DESCRIPTOR"}:
                obj = getattr(mod, attr)
                break
    if not isinstance(obj, dict):
        return None
    try:
        return Emotion(
            name=obj["name"],
            label=obj.get("label", obj["name"].title()),
            valence=obj.get("valence", 0.0),
            arousal=obj.get("arousal", 0.0),
            intensity=obj.get("intensity", 0.5),
            decay_s=obj.get("decay_s", 12.0),
            safety=obj.get("safety", False),
            taxonomy=obj.get("taxonomy", []),
            signal_words=obj.get("signal_words", []),
            linguistic_markers=obj.get("linguistic_markers", []),
            physiology=obj.get("physiology", []),
            triggers=obj.get("triggers", []),
            companion_response=obj.get("companion_response", {}),
            transitions_out=obj.get("transitions_out", []),
            notes=obj.get("notes", ""),
        )
    except KeyError:
        return None


def discover() -> Dict[str, Emotion]:
    """Walk every submodule under :mod:`tank_emotions.emotions`."""
    if _REGISTRY:
        return _REGISTRY
    pkg = importlib.import_module("tank_emotions.emotions")
    for _, name, _ in pkgutil.iter_modules(pkg.__path__):
        if name.startswith("_") or name == "neutral":
            continue
        mod = importlib.import_module(f"tank_emotions.emotions.{name}")
        emo = _descriptor_from_module(mod)
        if emo is not None:
            _REGISTRY[emo.name] = emo
    return _REGISTRY


def names() -> List[str]:
    return sorted(discover().keys())


def get(name: str) -> Emotion:
    """Lookup by canonical name; fallback to ``safe_default_desc()``."""
    return discover().get(name, safe_default_desc())


def by_taxonomy(framework: str) -> List[Emotion]:
    """Return all emotions tagged with ``framework`` (e.g. ``plutchik``)."""
    out = []
    for emo in discover().values():
        if any(t.get("framework", "").lower() == framework.lower()
               for t in emo.taxonomy):
            out.append(emo)
    return out


def by_category(category: str) -> List[Emotion]:
    """Return all emotions matching the rough quadrant ``category``."""
    from .core import rough_category
    return [e for e in discover().values() if rough_category(e) == category]


def summary_table() -> Iterable[dict]:
    """Yield per-emotion ``{name, label, valence, arousal, safety}`` rows."""
    for emo in discover().values():
        yield {
            "name":    emo.name,
            "label":   emo.label,
            "valence": emo.valence,
            "arousal": emo.arousal,
            "safety":  emo.safety,
        }


# Frameworks intentionally curated to remain small and defensible.
FRAMEWORKS = ("plutchik", "ekman", "izard", "geneva", "parrott")
