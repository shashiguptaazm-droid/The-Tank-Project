"""Tests for the AISupervisor — confidence arbitration and the
"AI can recommend. Safety can veto." rule (UNO Q AI plan #146–150)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tank_os.core.ai_supervisor import (
    AISupervisor, CommandSource, SourceRole, Verdict, MAX_AI_CONFIDENCE,
)
from tank_os.shell.terminal.safety import CommandSafety


def _fresh() -> AISupervisor:
    sup = AISupervisor()
    sup._sources.clear()
    sup._history.clear()
    sup.configure(safety_classifier=CommandSafety().classify)
    return sup


def _board() -> AISupervisor:
    """The confidence board from the plan's example."""
    sup = _fresh()
    sup.register("jetson", SourceRole.AI, 0.94)
    sup.register("manual", SourceRole.MANUAL, 0.99)
    sup.register("local-parser", SourceRole.AI, 0.87)
    sup.register("hardware-safety", SourceRole.SAFETY, 1.00)
    sup.register("battery-pred", SourceRole.AI, 0.91)
    return sup


def test_plan_example_confidence_table() -> None:
    sup = _board()
    report = sup.report()
    rows = {r["name"]: r["confidence"] for r in report["sources"]}
    assert rows["jetson"] == pytest.approx(0.94)
    assert rows["manual"] == pytest.approx(0.99)
    assert rows["local-parser"] == pytest.approx(0.87)
    assert rows["hardware-safety"] == pytest.approx(1.00)
    assert rows["battery-pred"] == pytest.approx(0.91)


def test_safety_source_can_veto() -> None:
    sup = _board()
    result = sup.arbitrate("rm -rf /", "hardware-safety")
    assert result.verdict in (Verdict.VETO, Verdict.NEEDS_APPROVAL)


def test_unknown_source_is_rejected() -> None:
    sup = _board()
    result = sup.arbitrate("forward 0.5", "stranger")
    assert result.verdict is Verdict.REJECT


def test_dangerous_command_needs_approval_from_ai() -> None:
    sup = _board()
    result = sup.arbitrate("sudo poweroff", "jetson")
    assert result.verdict is Verdict.NEEDS_APPROVAL


def test_highest_confidence_source_wins() -> None:
    sup = _board()
    # manual (0.99) beats local-parser (0.87) -> RECOMMEND for the parser
    result = sup.arbitrate("forward 0.5", "local-parser")
    assert result.verdict is Verdict.RECOMMEND
    assert "manual" in result.reason
    # ...but the same command from manual is ALLOWed
    result2 = sup.arbitrate("forward 0.5", "manual")
    assert result2.verdict is Verdict.ALLOW


def test_ai_confidence_never_reaches_1() -> None:
    sup = _fresh()
    src = sup.register("llm", SourceRole.AI, 1.0)
    assert src.confidence <= MAX_AI_CONFIDENCE


def test_safety_confidence_can_reach_1() -> None:
    sup = _fresh()
    src = sup.register("e-stop", SourceRole.SAFETY, 1.0)
    assert src.confidence == 1.0
    assert sup.safety_veto_active()


def test_update_confidence_reshapes_arbitration() -> None:
    sup = _board()
    # Raise the local parser above manual — it should now win.
    sup.update_confidence("local-parser", 0.995)
    result = sup.arbitrate("forward 0.5", "local-parser")
    assert result.verdict is Verdict.ALLOW


def test_safe_command_from_ai_is_never_vetoed() -> None:
    """Safe commands from an AI source are recommended, never blocked."""
    sup = _board()
    result = sup.arbitrate("echo hello", "jetson")
    assert result.verdict in (Verdict.ALLOW, Verdict.RECOMMEND)
    assert result.verdict is not Verdict.VETO
    assert result.verdict is not Verdict.REJECT


def test_history_records_verdicts() -> None:
    sup = _board()
    sup.arbitrate("forward 0.5", "local-parser")
    sup.arbitrate("sudo poweroff", "jetson")
    history = sup.history()
    assert len(history) == 2
    assert history[0]["verdict"] == "recommend"
    assert history[1]["verdict"] == "needs-approval"
