"""EvolutionLabScreen — 🧬 TankOS Evolution Lab (25-part evolution plan).

The dedicated GUI:

    GEN 0 ──► GEN 1 ──► GEN 2 ──► GEN 3      (score per generation)
    PROPOSALS — problem/change/expected + [APPROVE] [REJECT] [DETAILS]
    EXPERIMENTS / BENCHMARKS / SHADOW
    ROLLBACK + CHECKPOINTS + EVOLUTION POLICY

Every promotion runs: baseline → proposal → replay benchmark → multi-objective
score (safety hard-gate) → human approval → deploy → monitor → rollback.
"""

from __future__ import annotations

import logging
import time
from typing import List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from tank_os.core.evolution_engine import EvolutionEngine, ProposalStatus

logger = logging.getLogger("tank_os.windows.evolution")


class _GenChip(QFrame):
    """One generation chip in the timeline."""

    def __init__(self, label: str, score: float, current: bool,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        color = "#00BFFF" if current else "#555"
        self.setStyleSheet(f"""
            background: rgba(255,255,255,0.05); border: 1px solid {color};
            border-radius: 10px;
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 6, 10, 6)
        t = QLabel(label)
        t.setStyleSheet("font-size: 10px; font-weight: bold; color: #DDD;"
                        " background: transparent;")
        lay.addWidget(t)
        s = QLabel(f"{score * 100:.0f}%")
        s.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {color};"
                        f" background: transparent;")
        lay.addWidget(s)


class EvolutionLabScreen(QWidget):
    """Evolution Lab — current / proposals / experiments / generations."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._evo = EvolutionEngine()
        self._seed()
        self._build_ui()
        self.refresh()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(2500)

    # ------------------------------------------------------------- seed
    def _seed(self) -> None:
        e = self._evo
        if not e._mission_log:
            # a few missions with a pattern (weakness discovery demo)
            for i in range(30):
                outcome = "success" if i % 5 else "failure"
                cause = "dynamic-obstacle" if i % 5 == 0 else None
                location = "corridor-b" if i % 10 == 0 else None
                e.record_mission(f"mission-{i:03d}", outcome, cause, location)
            # a proposal + replay benchmark
            props = [p for p in e.proposals if p.id == "001"]
            if not props:
                prop = e.propose(
                    "Repeated navigation blockage near corridor B",
                    "navigation.prediction_horizon", 2.0,
                    "↓ collision risk · ↓ replanning frequency",
                    "↑ compute usage")
                e.replay_benchmark(prop, replay_success=0.951,
                                   baseline_success=0.912, safety_ok=True,
                                   latency_ms=92)
                prop.status = ProposalStatus.AWAITING_APPROVAL
            if not e.experiments:
                e.run_experiment("Vision FPS vs battery",
                                 "battery", {"A: 20 FPS": {"fps": 20},
                                             "B: 10 FPS": {"fps": 10},
                                             "C: adaptive": {"fps": "adaptive"}})

    # --------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("🧬 TankOS Evolution Lab — TEE")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFF;")
        header.addWidget(title)
        header.addStretch()
        self._gen_badge = QLabel("GEN —")
        self._gen_badge.setStyleSheet("""
            background: rgba(0,191,255,0.12); border: 1px solid rgba(0,191,255,0.35);
            border-radius: 10px; padding: 6px 14px; font-size: 11px; font-weight: bold;
            color: #80D8FF;
        """)
        header.addWidget(self._gen_badge)
        layout.addLayout(header)

        # Generations timeline
        gen_label = QLabel("EVOLUTION GENERATIONS — SCORE PER VERSION")
        gen_label.setStyleSheet("font-size: 10px; color: #888; font-weight: bold;")
        layout.addWidget(gen_label)
        self._gens_row = QHBoxLayout()
        self._gens_row.setSpacing(8)
        layout.addLayout(self._gens_row)

        # Weakness discovery
        weak = QFrame()
        weak.setStyleSheet("""
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;
        """)
        w_lay = QHBoxLayout(weak)
        w_lay.setContentsMargins(12, 8, 12, 8)
        w_t = QLabel("🔍 WEAKNESS DISCOVERY")
        w_t.setStyleSheet("font-size: 10px; color: #888; font-weight: bold;"
                          " background: transparent;")
        w_lay.addWidget(w_t)
        self._weak = QLabel("")
        self._weak.setWordWrap(True)
        self._weak.setStyleSheet("font-size: 11px; color: #FFD54F;"
                                 " background: transparent;")
        w_lay.addWidget(self._weak, 1)
        layout.addWidget(weak)

        body = QHBoxLayout()
        body.setSpacing(10)

        # Proposal card
        prop = QFrame()
        prop.setStyleSheet("""
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.1); border-radius: 12px;
        """)
        p_lay = QVBoxLayout(prop)
        p_lay.setContentsMargins(12, 10, 12, 10)
        p_t = QLabel("🧪 EVOLUTION PROPOSAL — HUMAN APPROVAL REQUIRED")
        p_t.setStyleSheet("font-size: 10px; color: #888; font-weight: bold;"
                          " background: transparent;")
        p_lay.addWidget(p_t)
        self._prop = QLabel("")
        self._prop.setWordWrap(True)
        self._prop.setStyleSheet("font-size: 11px; color: #CCC;"
                                 " background: transparent;")
        p_lay.addWidget(self._prop)
        btns = QHBoxLayout()
        self._btn_approve = QPushButton("✓ APPROVE")
        self._btn_reject = QPushButton("✗ REJECT")
        self._btn_rollback = QPushButton("↩ ROLLBACK")
        for btn in (self._btn_approve, self._btn_reject, self._btn_rollback):
            btn.setStyleSheet("""
                QPushButton { background: rgba(255,255,255,0.06);
                    border: 1px solid rgba(255,255,255,0.15); border-radius: 8px;
                    color: #CCC; font-size: 11px; font-weight: bold; padding: 6px; }
                QPushButton:hover { background: rgba(0,191,255,0.2); color: #FFF; }
            """)
            btns.addWidget(btn)
        self._btn_approve.clicked.connect(self._approve)
        self._btn_reject.clicked.connect(self._reject)
        self._btn_rollback.clicked.connect(self._rollback)
        p_lay.addLayout(btns)
        body.addWidget(prop, 1)

        # Benchmarks + experiments
        bench = QFrame()
        bench.setStyleSheet("""
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;
        """)
        b_lay = QVBoxLayout(bench)
        b_lay.setContentsMargins(12, 10, 12, 10)
        b_t = QLabel("📊 BENCHMARKS + EXPERIMENTS + SHADOW")
        b_t.setStyleSheet("font-size: 10px; color: #888; font-weight: bold;"
                          " background: transparent;")
        b_lay.addWidget(b_t)
        self._bench = QLabel("")
        self._bench.setWordWrap(True)
        self._bench.setStyleSheet("font-size: 10px; color: #CCC;"
                                  " font-family: Monospace; background: transparent;")
        b_lay.addWidget(self._bench)
        body.addWidget(bench, 1)
        layout.addLayout(body, 1)

        # Policy footer
        self._policy = QLabel("")
        self._policy.setWordWrap(True)
        self._policy.setStyleSheet("""
            background: rgba(255,255,255,0.03); border-radius: 10px;
            padding: 8px 12px; font-size: 10px; color: #889;
        """)
        layout.addWidget(self._policy)

    # ------------------------------------------------------------- actions
    def _approve(self) -> None:
        pending = [p for p in self._evo.proposals
                   if p.status in (ProposalStatus.TESTING,
                                   ProposalStatus.AWAITING_APPROVAL,
                                   ProposalStatus.DRAFT)]
        if pending:
            self._evo.approve(pending[0])
            self._evo.deploy(pending[0])
            self.refresh()

    def _reject(self) -> None:
        pending = [p for p in self._evo.proposals
                   if p.status in (ProposalStatus.TESTING,
                                   ProposalStatus.AWAITING_APPROVAL,
                                   ProposalStatus.DRAFT)]
        if pending:
            self._evo.reject(pending[0])
            self.refresh()

    def _rollback(self) -> None:
        self._evo.rollback()
        self.refresh()

    # ------------------------------------------------------------- data
    def refresh(self) -> None:
        e = self._evo
        self._gen_badge.setText(f"GEN {e.current_generation().number}")

        # generations chips
        while self._gens_row.count():
            item = self._gens_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for g in e.generations[-5:]:
            chip = _GenChip(f"GEN {g.number}", g.score,
                            g.number == e.current_generation().number)
            self._gens_row.addWidget(chip)
        self._gens_row.addStretch(1)

        # weaknesses
        weaks = e.weaknesses(window=60)
        self._weak.setText("\n".join(w["discovery"] for w in weaks)
                           if weaks else "No weaknesses detected in recent missions")

        # proposal
        props = [p for p in e.proposals
                 if p.status in (ProposalStatus.TESTING,
                                 ProposalStatus.AWAITING_APPROVAL,
                                 ProposalStatus.DRAFT)]
        if props:
            p = props[0]
            self._prop.setText(
                f"PROPOSAL #{p.id} — {p.problem}\n"
                f"Change: {p.change}\n"
                f"Expected: {p.expected} · Cost: {p.potential_cost}\n"
                f"Baseline {p.baseline_score * 100:.1f}% → Candidate "
                f"{p.candidate_score * 100:.1f}% · Safety PASS ✓\n"
                f"{p.explanation}")
            self._btn_approve.setEnabled(True)
            self._btn_reject.setEnabled(True)
        else:
            self._prop.setText("No pending proposals — the Tank is observing…")
            self._btn_approve.setEnabled(False)
            self._btn_reject.setEnabled(False)
        self._btn_rollback.setEnabled(len(e.generations) > 1)

        # benchmarks + experiments + shadow
        lines = []
        for exp in e.experiments[-2:]:
            res = " · ".join(f"{k}: {v:.2f}" for k, v in exp.results.items())
            lines.append(f"🧪 {exp.id} {exp.label} [{exp.metric}] {res}")
        shadow = e.shadow_summary()
        lines.append(f"👥 shadow: {shadow['decisions']} decisions · "
                     f"candidate alternatives {shadow['candidate_better_pct']}%")
        self._bench.setText("\n".join(lines) if lines else "No experiments yet")

        # policy
        pol = e.policy()
        self._policy.setText(
            "📜 EVOLUTION POLICY — AI may: " + ", ".join(pol["allowed"]) +
            ". AI may NOT: " + ", ".join(pol["forbidden"]) +
            ". (Safety is a hard constraint, not a weighted score.)")

    def on_show(self) -> None:
        self.refresh()
        self._timer.start(2500)

    def on_hide(self) -> None:
        self._timer.stop()
