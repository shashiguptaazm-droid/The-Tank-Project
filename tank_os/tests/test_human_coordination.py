"""Tests for the human-coordination and constitution subsystems
(100-feature human-coordination plan + 25-item originality plan).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


# ------------------------------------------------------ human coordination
@pytest.fixture()
def hc():
    from tank_os.core.human_coordination import HumanCoordination
    h = HumanCoordination()
    h.reset()
    yield h


def test_track_person_presence_states(hc) -> None:
    p = hc.track_person(3.0, 0.0, 0.9)
    assert p.id == 1
    assert p.zone == "comfort"  # ≤ 3.0 m comfort zone
    p.update(5.0, 0.0, 0.9, dt=1.0)
    assert p.zone == "outside"
    # approaching (distance decreasing)
    p.update(2.0, 0.0, 0.9, dt=1.0)
    assert p.presence.value == "approaching"
    assert p.velocity_ms < 0
    # danger zone
    p.update(0.4, 0.0, 0.9, dt=1.0)
    assert p.zone == "danger"
    # departing (distance increasing)
    p.update(1.5, 0.0, 0.9, dt=1.0)
    assert p.presence.value == "departing"


def test_follow_stop_modes(hc) -> None:
    from tank_os.core.human_coordination import InteractionMode
    p = hc.track_person(2.0, 10.0, 0.94)
    hc.set_mode(InteractionMode.FOLLOW)
    assert hc.mode().value == "follow"
    assert hc.designated_person().id == p.id
    hc.set_status(p.id, "FOLLOWING")
    assert hc.people()[p.id].status == "FOLLOWING"
    hc.set_mode(InteractionMode.STOP)
    assert hc.mode().value == "stop"


def test_authority_chain_and_estop(hc) -> None:
    assert [a.value for a in hc.controller_priority()] == \
        ["safety", "human", "mission", "autonomy"]
    hc.human_takes_control()
    assert hc.authority().value == "human"
    hc.autonomy_resumes()
    assert hc.authority().value == "autonomy"
    hc.emergency_stop()
    assert hc.authority().value == "safety"
    assert hc.mode().value == "stop"


def test_human_in_the_loop_approve_reject_modify(hc) -> None:
    req = hc.ai_propose("Change route around obstacle", "Obstacle 1.8 m ahead")
    assert req.status == "pending"
    assert len(hc.pending_requests()) == 1
    # reject
    hc.reject(req.id)
    assert req.status == "rejected"
    # propose again → modify
    req2 = hc.ai_propose("Change route", "Replan")
    hc.modify(req2.id, "Change route AND slow to 0.2 m/s")
    assert req2.status == "modified"
    assert req2.modified_command == "Change route AND slow to 0.2 m/s"
    # approve path
    req3 = hc.ai_propose("Continue forward", "Path clear")
    hc.approve(req3.id)
    assert req3.status == "approved"


def test_ask_the_human_route_ambiguity(hc) -> None:
    c = hc.resolve_route_ambiguity(confidence=0.51)
    assert "two possible routes" in c.question
    assert c.options == ["LEFT", "RIGHT"]
    assert len(hc.open_clarifications()) == 1
    hc.answer_clarification(c.id, "LEFT")
    assert c.answer == "LEFT"
    assert len(hc.open_clarifications()) == 0


def test_human_vs_autonomy_priority(hc) -> None:
    assert hc.human_priority_check(0.99, 0.94) == "human"
    assert hc.human_priority_check(0.80, 0.94) == "autonomy"
    assert hc.human_priority_check(0.99, 0.94, safety_conf=1.0) == "safety-veto"


# --------------------------------------------------------- constitution
@pytest.fixture()
def const():
    from tank_os.core.robot_constitution import RobotConstitution
    c = RobotConstitution()
    c.reset()
    yield c


def test_constitution_human_protection_veto(const) -> None:
    v = const.check("move forward", human_near=True)
    assert v.allowed is False
    assert v.article.value == 1
    assert v.triggers and "Protect humans" in v.triggers[0]


def test_constitution_safety_veto(const) -> None:
    v = const.check("drive", collision_risk=0.71)
    assert v.allowed is False
    assert v.article.value == 2
    assert v.triggers and "Never bypass safety" in v.triggers[0]


def test_constitution_battery_preserve(const) -> None:
    v = const.check("mission start", battery_pct=8)
    assert v.allowed is False
    assert v.article.value == 4


def test_constitution_ask_when_uncertain(const) -> None:
    v = const.check("move forward", low_confidence=True)
    assert v.allowed is False
    assert v.article.value == 7


def test_constitution_allows_safe_action(const) -> None:
    v = const.check("move forward", authorized_human=True)
    assert v.allowed is True


def test_ai_debate_safety_wins(const) -> None:
    d = const.debate("MOVE FORWARD", vision_go=True, nav_go=True,
                     safety_go=False, battery_ok=True)
    assert d.final == "STOP"
    assert d.winner == "SAFETY"
    assert any("safety wins" in d.reason.lower() or "vetoes" in d.reason.lower()
               for _ in [0])


def test_ai_debate_all_agree(const) -> None:
    d = const.debate("MOVE FORWARD", vision_go=True, nav_go=True,
                     safety_go=True, battery_ok=True)
    assert d.final.startswith("GO")
    assert len(d.votes) == 4


def test_command_chain_explicit_source(const) -> None:
    assert "EMERGENCY STOP" in const.command_chain_for("safety")
    assert "HUMAN" in const.command_chain_for("human")
    assert const.command_chain_for("ai").startswith("AI")
