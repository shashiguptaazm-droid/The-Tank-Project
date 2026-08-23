"""ConstitutionScreen — 🌟 Robot Constitution + 🧠 AI Debate (originality plan).

Idea #25: a machine-readable set of priorities every AI action passes through
(the policy engine lives in tank_os/core/robot_constitution.py).
Idea #21: the AI Debate — vision / navigation / safety / resource modules
vote on an action; safety wins; the result is fully explainable.
Idea #22: the command chain — every action has a visible source.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from tank_os.core.robot_constitution import ARTICLES, Article, RobotConstitution

logger = logging.getLogger("tank_os.windows.const")

ARTICLE_COLORS = {
    Article.PROTECT_HUMANS: "#FF8A80",
    Article.NEVER_BYPASS_SAFETY: "#FF5252",
    Article.OBEY_AUTHORIZED_HUMANS: "#4CAF50",
    Article.PRESERVE_HARDWARE: "#FFA726",
    Article.COMPLETE_MISSION: "#00BFFF",
    Article.MINIMIZE_ENERGY: "#26A69A",
    Article.ASK_WHEN_UNCERTAIN: "#FFD54F",
    Article.REPORT_FAILURES_HONESTLY: "#9EE7A5",
}


class _ArticleRow(QFrame):
    """One constitution article with a triggered/ok state."""

    def __init__(self, article: Article, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._article = article
        color = ARTICLE_COLORS[article]
        self.setStyleSheet(f"""
            background: rgba(255,255,255,0.03); border-left: 3px solid {color};
            border-radius: 6px;
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 5, 10, 5)
        lay.setSpacing(8)
        num = QLabel(f"{int(article)}.")
        num.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {color};"
                          f" background: transparent;")
        lay.addWidget(num)
        text = QLabel(ARTICLES[article])
        text.setStyleSheet("font-size: 11px; color: #CCC; background: transparent;")
        lay.addWidget(text)
        lay.addStretch()
        self._mark = QLabel("✓")
        self._mark.setStyleSheet("font-size: 12px; font-weight: bold; color: #4CAF50;"
                                 " background: transparent;")
        lay.addWidget(self._mark)

    def set_triggered(self, triggered: bool) -> None:
        if triggered:
            self._mark.setText("⛔")
            self._mark.setStyleSheet("font-size: 12px; font-weight: bold;"
                                     " color: #FF5252; background: transparent;")
        else:
            self._mark.setText("✓")
            self._mark.setStyleSheet("font-size: 12px; font-weight: bold;"
                                     " color: #4CAF50; background: transparent;")


class ConstitutionScreen(QWidget):
    """Robot Constitution + AI Debate."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._const = RobotConstitution()
        self._build_ui()
        self.refresh()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(2500)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("🌟 The Tank Constitution")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFF;")
        header.addWidget(title)
        header.addStretch()
        self._verdict = QLabel("")
        self._verdict.setStyleSheet("""
            background: rgba(76,175,80,0.15); border: 1px solid #4CAF50;
            border-radius: 10px; padding: 6px 14px; font-size: 11px; font-weight: bold;
            color: #A5D6A7;
        """)
        header.addWidget(self._verdict)
        layout.addLayout(header)

        # Left: articles
        left = QFrame()
        left.setStyleSheet("""
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;
        """)
        l_lay = QVBoxLayout(left)
        l_lay.setContentsMargins(12, 10, 12, 10)
        l_lay.setSpacing(4)
        l_t = QLabel("PRIORITY POLICY — EVERY AI ACTION PASSES THROUGH")
        l_t.setStyleSheet("font-size: 10px; color: #888; font-weight: bold;"
                          " background: transparent;")
        l_lay.addWidget(l_t)
        self._rows: dict = {}
        for article in Article:
            row = _ArticleRow(article)
            self._rows[article] = row
            l_lay.addWidget(row)
        self._policy_reason = QLabel("")
        self._policy_reason.setWordWrap(True)
        self._policy_reason.setStyleSheet("""
            background: rgba(255,255,255,0.03); border-radius: 8px;
            padding: 6px 10px; font-size: 11px; color: #FFD54F;
        """)
        l_lay.addWidget(self._policy_reason)
        layout.addWidget(left, 1)

        # Right: AI Debate
        right = QFrame()
        right.setStyleSheet("""
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;
        """)
        r_lay = QVBoxLayout(right)
        r_lay.setContentsMargins(12, 10, 12, 10)
        r_lay.setSpacing(6)
        r_t = QLabel("🧠 AI DEBATE — HIGH-RISK DECISION")
        r_t.setStyleSheet("font-size: 10px; color: #888; font-weight: bold;"
                          " background: transparent;")
        r_lay.addWidget(r_t)
        self._action = QLabel("ACTION: MOVE FORWARD")
        self._action.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFF;"
                                   " background: transparent;")
        r_lay.addWidget(self._action)
        self._votes = QLabel("")
        self._votes.setWordWrap(True)
        self._votes.setStyleSheet("font-size: 12px; color: #DDD; background: transparent;")
        r_lay.addWidget(self._votes)
        self._debate_final = QLabel("")
        self._debate_final.setWordWrap(True)
        self._debate_final.setStyleSheet("""
            background: rgba(0,191,255,0.1); border-radius: 8px;
            padding: 8px 10px; font-size: 12px; font-weight: bold; color: #80D8FF;
        """)
        r_lay.addWidget(self._debate_final)

        chain_t = QLabel("⛓ COMMAND CHAIN")
        chain_t.setStyleSheet("font-size: 10px; color: #888; font-weight: bold;"
                              " background: transparent;")
        r_lay.addWidget(chain_t)
        self._chain = QLabel("")
        self._chain.setWordWrap(True)
        self._chain.setStyleSheet("font-size: 10px; color: #9AA;"
                                  " font-family: Monospace; background: transparent;")
        r_lay.addWidget(self._chain)

        btn = QPushButton("🔄 RE-RUN DEBATE + POLICY CHECK")
        btn.setStyleSheet("""
            QPushButton { background: rgba(0,191,255,0.15);
                border: 1px solid rgba(0,191,255,0.4); border-radius: 8px;
                padding: 8px 14px; color: #80D8FF; font-size: 11px; font-weight: bold; }
            QPushButton:hover { background: rgba(0,191,255,0.28); }
        """)
        btn.clicked.connect(self._rerun)
        r_lay.addWidget(btn)
        r_lay.addStretch(1)
        layout.addWidget(right, 1)

        body = QHBoxLayout()
        body.setSpacing(10)
        body.addWidget(left, 1)
        body.addWidget(right, 1)
        layout.addLayout(body, 1)

    # ------------------------------------------------------------- data
    def _rerun(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        # The debate: an obstacle approaches in waves; safety eventually vetoes.
        t = time.time()
        wave = (int(t) % 6) < 2  # every ~5s an obstacle is near
        collision = 0.71 if wave else 0.08

        debate = self._const.debate(
            "MOVE FORWARD",
            vision_go=not wave, nav_go=not wave, safety_go=not wave,
            battery_ok=True,
            vision_conf=0.9, nav_conf=0.85, safety_conf=1.0, battery_conf=0.91,
        )

        self._action.setText("ACTION: MOVE FORWARD")
        vote_lines = []
        for v in debate.votes:
            color = "#FF8A80" if v.decision == "STOP" else "#81C784"
            vote_lines.append(
                f"<span style='color:{color};font-weight:bold'>{v.module}: "
                f"{v.decision}</span> — {v.reason} (conf {v.confidence:.2f})")
        self._votes.setText("<br>".join(vote_lines))
        final_color = "#FF8A80" if debate.final.startswith("STOP") else "#81C784"
        self._debate_final.setStyleSheet(f"""
            background: rgba(255,255,255,0.06); border-radius: 8px;
            padding: 8px 10px; font-size: 13px; font-weight: bold; color: {final_color};
        """)
        self._debate_final.setText(f"FINAL: {debate.final}\n{debate.reason}")

        # Policy check on the same action
        verdict = self._const.check(
            "move forward", human_near=wave, collision_risk=collision)
        self._const.audit(verdict)

        triggered = set()
        if verdict.article is not None:
            triggered.add(verdict.article)
        for article, row in self._rows.items():
            row.set_triggered(article in triggered)

        if verdict.allowed:
            self._verdict.setText("✓ POLICY OK — ALLOWED")
            self._verdict.setStyleSheet("""
                background: rgba(76,175,80,0.15); border: 1px solid #4CAF50;
                border-radius: 10px; padding: 6px 14px; font-size: 11px; font-weight: bold;
                color: #A5D6A7;
            """)
            self._policy_reason.setText(verdict.reason)
        else:
            self._verdict.setText("⛔ POLICY VETO")
            self._verdict.setStyleSheet("""
                background: rgba(244,67,54,0.15); border: 1px solid #FF5252;
                border-radius: 10px; padding: 6px 14px; font-size: 11px; font-weight: bold;
                color: #FF8A80;
            """)
            self._policy_reason.setText(
                f"{verdict.reason}\nArticle {int(verdict.article)}: "
                f"{ARTICLES.get(verdict.article, '')}")

        # Command chain (idea #22)
        src = "ai" if not verdict.allowed else "human"
        self._chain.setText(self._const.command_chain_for(src))

    def on_show(self) -> None:
        self.refresh()
        self._timer.start(2500)

    def on_hide(self) -> None:
        self._timer.stop()
