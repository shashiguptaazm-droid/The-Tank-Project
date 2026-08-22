"""pytest for the :mod:`tank_patrol.surveillance` AlertJournal + CLI behaviour.

No ROS dependency; uses a tmp dir for the journal base.
"""
from __future__ import annotations

import json
import os
import time

import pytest


def test_alert_journal_roundtrip(tmp_path, monkeypatch):
    from tank_patrol import surveillance as sv

    monkeypatch.setattr(sv.AlertJournal, "DIR", str(tmp_path), raising=False)
    j = sv.AlertJournal(base_dir=str(tmp_path))
    obs = sv.MotionObservation(
        ts=time.time(),
        source="motion_node",
        bbox=(0.1, 0.2, 0.3, 0.4),
        confidence=0.8,
        label="person",
    )
    alert = sv.PatrolAlert(
        ts=time.time(),
        severity=sv.AlertSeverity.WARNING,
        label="person",
        observation=obs,
        patrol_phase="patrolling",
        distance_from_active_edge_m=5.0,
    )
    p = j.append(alert)
    assert p == os.path.join(str(tmp_path), _today() + ".jsonl")
    j.close()
    j2 = sv.AlertJournal(base_dir=str(tmp_path))
    events = j2.read_day(_today())
    assert len(events) == 1
    assert events[0]["severity"] == "warning"
    assert events[0]["label"] == "person"
    j2.close()


def test_alert_journal_filtering(tmp_path, monkeypatch):
    from tank_patrol import surveillance as sv

    monkeypatch.setattr(sv.AlertJournal, "DIR", str(tmp_path), raising=False)
    j = sv.AlertJournal(base_dir=str(tmp_path))
    base = time.time()
    for i, sev in enumerate(("info", "warning", "critical")):
        j.append(sv.PatrolAlert(
            ts=base + i,
            severity=getattr(sv.AlertSeverity, sev.upper()),
            label="person" if i == 2 else "animal",
            observation=sv.MotionObservation(
                ts=base + i, source="t",
                bbox=(0.1, 0.1, 0.2, 0.2),
                confidence=0.8, label="x",
            ),
            patrol_phase="patrolling",
            distance_from_active_edge_m=0.0,
        ))
    j.close()
    j2 = sv.AlertJournal(base_dir=str(tmp_path))
    evs = j2.read_day(_today())
    sevs = [e["severity"] for e in evs]
    assert set(sevs) == {"info", "warning", "critical"}
    j2.close()


def test_to_observation_handles_bad_payload():
    from tank_patrol.surveillance import to_observation
    obs = to_observation({
        "ts": "not-a-number",     # parser falls back to time.time()
        "bbox": ["a", "b"],       # falls back to (0,0,0,0)
        "confidence": "high",     # falls back to 0
        "source": 42,
    })
    assert obs is not None
    assert obs.bbox == (0.0, 0.0, 0.0, 0.0)
    assert obs.label == ""


def _today() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
