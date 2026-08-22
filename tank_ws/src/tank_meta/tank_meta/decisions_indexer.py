"""Load ``content/decisions.json`` rows into :class:`MetaStore`."""
from __future__ import annotations

import json
import os

from .meta_store import DecisionRow, MetaStore


def load_decisions_file(path: str, store: MetaStore) -> int:
    """Read a decisions.json file and push every row to ``store``.

    Returns number of decisions added. Missing file yields 0.
    """
    if not os.path.exists(path):
        return 0
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    decisions = data.get("decisions") or []
    n = 0
    for d in decisions:
        store.upsert_decision(DecisionRow(
            id=str(d.get("id", "")),
            ts=float(d.get("ts", 0.0)),
            problem=str(d.get("problem", "")),
            reason=str(d.get("reason", "")),
            solution=str(d.get("solution", "")),
            result=str(d.get("result", "")),
        ))
        n += 1
    return n


def append_decision(path: str, decision: DecisionRow) -> int:
    """Append a new decision to ``path`` (and remove the existing one if its
    id is already in the file). Returns the number of decisions now in the file.
    """
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    else:
        data = {"schema_version": 1, "decisions": []}
    rows = [r for r in (data.get("decisions") or [])
            if str(r.get("id", "")) != decision.id]
    rows.append({
        "id":       decision.id,
        "ts":       decision.ts,
        "problem":  decision.problem,
        "reason":   decision.reason,
        "solution": decision.solution,
        "result":   decision.result,
    })
    data["decisions"] = rows
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    return len(rows)
