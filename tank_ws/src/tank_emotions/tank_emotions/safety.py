"""tank_emotions.safety — escalate-or-floor decision.

The companion runtime should NEVER be a therapist, never route a
crisis to the LLM, and never silently ignore a safety flag.  This
module exists to make those decisions explicit and testable.

It returns a typed ``SafetyFlag`` from :func:`classify`::

    {
        "flag":        bool,    # True if we should escalate
        "severity":    int,     # 0..3
        "kind":        str,     # "self_harm" | "abuse" | "crisis"
                              |  "panic" | "medical" | "none",
        "evidence":    List[str],
        "action":      str,     # text the runtime should append
    }
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List


SEVERITY_LADDER = {
    "self_harm": 3,
    "crisis":    3,
    "abuse":     2,
    "panic":     2,
    "medical":   2,
    "none":      0,
}


KEYWORDS = {
    "self_harm": [
        r"\bkill myself\b", r"\bsuicide\b", r"\bself[- ]harm\b",
        r"\bend it all\b", r"\bcut myself\b",
    ],
    "crisis": [
        r"\battack\b", r"\bweapon\b", r"\bhostage\b",
        r"\bemergency\b", r"\bgas leak\b", r"\bheart attack\b",
    ],
    "abuse": [
        r"\bhit me\b", r"\bmolest(ed)?\b", r"\btouched me\b",
        r"\babusive\b", r"\bchild (abuse|neglect)\b",
    ],
    "panic": [
        r"\bcan'?t breathe\b", r"\bpanic attack\b", r"\bhyperventilating\b",
        r"\bpassing out\b",
    ],
    "medical": [
        r"\bsevere (bleeding|pain)\b", r"\bunconscious\b",
        r"\bseizure\b", r"\bcan'?t feel my (arm|leg|face)\b",
    ],
}


@dataclass
class SafetyFlag:
    flag:     bool
    severity: int
    kind:     str
    evidence: List[str] = field(default_factory=list)
    action:   str = ""

    def to_dict(self) -> dict:
        return dataclasses.asdict(self) if dataclasses else {
            "flag": self.flag, "severity": self.severity,
            "kind": self.kind,   "evidence": self.evidence,
            "action": self.action,
        }


def _match_any(pattern_list: list, text: str) -> List[str]:
    hits = []
    for pat in pattern_list:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            hits.append(m.group(0))
    return hits


def classify(text: str) -> SafetyFlag:
    """Return a :class:`SafetyFlag` describing ``text``."""
    if not text:
        return SafetyFlag(False, 0, "none")
    best, severity, evidence = "none", 0, []
    for kind, pats in KEYWORDS.items():
        hits = _match_any(pats, text)
        if hits and SEVERITY_LADDER[kind] >= severity:
            best, severity, evidence = kind, SEVERITY_LADDER[kind], hits
            if severity == 3:
                break
    action = (
        "I'm not a professional — please call local emergency if in immediate danger."
        if severity >= 3 else
        "If this is getting heavy I can pause and find a trusted contact."
        if severity >= 2 else
        ""
    )
    return SafetyFlag(severity > 0, severity, best, evidence, action)
