"""HumanControlCenterScreen — 👤 Human Coordination (100-feature plan).

The dedicated GUI from the plan:

    👤 PERSON #01   Distance / Direction / Status / Confidence
       [ FOLLOW ] [ STOP ]        (+ ESCORT, MEET, RETURN modes)

    CONTROL AUTHORITY
       HUMAN ● ACTIVE · AUTONOMY ○ STANDBY · SAFETY ○ ARMED

    AI REQUEST
       "Obstacle detected. Change route?"  [ APPROVE ] [ REJECT ] [ MODIFY ]

    🤔 ASK THE HUMAN (low-confidence route choice)
       "I found two possible routes. Which should I take?"  [ LEFT ] [ RIGHT ]

Driven entirely by the HumanCoordination core — deterministic, testable.
"""

from __future__ import annotations

import logging
import math
import time
from typing import List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)

from tank_os.core.human_coordination import (
    ControlAuthority, HumanCoordination, InteractionMode,
)

logger = logging.getLogger("tank_os.windows.humanctrl")

AUTHORITY_COLOR = {
    ControlAuthority.SAFETY: "#FF8A80",
    ControlAuthority.HUMAN: "#4CAF50",
    ControlAuthority.MISSION: "#00BFFF",
    ControlAuthority.AUTONOMY: "#FFA726",
}


class _Stat(QFrame):
    """A stat card with label + value."""

    def __init__(self, label: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("""
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.1); border-radius: 12px;
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        t = QLabel(label)
        t.setStyleSheet("font-size: 9px; color: #888; font-weight: bold;"
                        " background: transparent;")
        lay.addWidget(t)
        self._v = QLabel("—")
        self._v.setStyleSheet("font-size: 15px; font-weight: bold; color: #FFF;"
                              " background: transparent;")
        lay.addWidget(self._v)

    def set(self, value: str, color: str = "#FFF") -> None:
        self._v.setText(value)
        self._v.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {color};"
                              f" background: transparent;")


class HumanControlCenterScreen(QWidget):
    """Human Coordination — people, control authority, human-in-the-loop."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._hc = HumanCoordination()
        self._seed()
        self._build_ui()
        self.refresh()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(2000)

    # --------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("👤 Human Coordination")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFF;")
        header.addWidget(title)
        header.addStretch()
        self._mode_badge = QLabel("MODE: —")
        self._mode_badge.setStyleSheet("""
            background: rgba(0,191,255,0.12); border: 1px solid rgba(0,191,255,0.35);
            border-radius: 10px; padding: 6px 14px; font-size: 11px; font-weight: bold;
            color: #80D8FF;
        """)
        header.addWidget(self._mode_badge)
        layout.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(10)

        # Left: person card
        left = QFrame()
        left.setStyleSheet("""
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.1); border-radius: 14px;
        """)
        l_lay = QVBoxLayout(left)
        l_lay.setContentsMargins(14, 12, 14, 12)
        l_lay.setSpacing(8)
        person_title = QLabel("👤 PERSON")
        person_title.setStyleSheet("font-size: 12px; color: #88F; font-weight: bold;")
        l_lay.addWidget(person_title)
        self._person = QLabel("—")
        self._person.setWordWrap(True)
        self._person.setStyleSheet("font-size: 13px; color: #DDD; background: transparent;")
        l_lay.addWidget(self._person)
        self._conf = QProgressBar()
        self._conf.setRange(0, 100)
        self._conf.setTextVisible(False)
        self._conf.setFixedHeight(10)
        self._conf.setStyleSheet("""
            QProgressBar { background: rgba(255,255,255,0.06);
                border: none; border-radius: 5px; }
            QProgressBar::chunk { background: #00BFFF; border-radius: 5px; }
        """)
        l_lay.addWidget(self._conf)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        for label, mode in (("🟢 FOLLOW", InteractionMode.FOLLOW),
                            ("⛔ STOP", InteractionMode.STOP),
                            ("🛡 ESCORT", InteractionMode.ESCORT),
                            ("🏠 RETURN", InteractionMode.RETURN_TO_OWNER)):
            btn = QPushButton(label)
            btn.setStyleSheet("""
                QPushButton { background: rgba(255,255,255,0.06);
                    border: 1px solid rgba(255,255,255,0.15); border-radius: 8px;
                    color: #CCC; font-size: 11px; font-weight: bold; padding: 6px; }
                QPushButton:hover { background: rgba(0,191,255,0.2); color: #FFF; }
            """)
            btn.clicked.connect(lambda _=False, m=mode: self._set_mode(m))
            btn_row.addWidget(btn)
        l_lay.addLayout(btn_row)

        self._interaction = QLabel("")
        self._interaction.setWordWrap(True)
        self._interaction.setStyleSheet("font-size: 11px; color: #9AA;"
                                        " background: transparent;")
        l_lay.addWidget(self._interaction)
        body.addWidget(left, 3)

        # Right column: authority + requests
        right = QVBoxLayout()
        right.setSpacing(10)

        auth = QFrame()
        auth.setStyleSheet("""
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.1); border-radius: 12px;
        """)
        a_lay = QVBoxLayout(auth)
        a_lay.setContentsMargins(12, 10, 12, 10)
        a_t = QLabel("CONTROL AUTHORITY")
        a_t.setStyleSheet("font-size: 10px; color: #888; font-weight: bold;"
                          " background: transparent;")
        a_lay.addWidget(a_t)
        self._authority: dict = {}
        for name in ("SAFETY", "HUMAN", "MISSION", "AUTONOMY"):
            row = QHBoxLayout()
            lbl = QLabel(name)
            lbl.setFixedWidth(90)
            lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #BBB;"
                              " background: transparent;")
            row.addWidget(lbl)
            dot = QLabel("○")
            dot.setStyleSheet("font-size: 14px; color: #555; background: transparent;")
            row.addWidget(dot)
            row.addStretch()
            a_lay.addLayout(row)
            self._authority[name] = dot
        right.addWidget(auth)

        # AI request card
        req = QFrame()
        req.setStyleSheet("""
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.1); border-radius: 12px;
        """)
        r_lay = QVBoxLayout(req)
        r_lay.setContentsMargins(12, 10, 12, 10)
        r_t = QLabel("🤝 AI REQUEST — HUMAN-IN-THE-LOOP")
        r_t.setStyleSheet("font-size: 10px; color: #888; font-weight: bold;"
                          " background: transparent;")
        r_lay.addWidget(r_t)
        self._req_text = QLabel("No pending requests")
        self._req_text.setWordWrap(True)
        self._req_text.setStyleSheet("font-size: 12px; color: #DDD;"
                                     " background: transparent;")
        r_lay.addWidget(self._req_text)
        req_btns = QHBoxLayout()
        self._btn_approve = QPushButton("✓ APPROVE")
        self._btn_reject = QPushButton("✗ REJECT")
        self._btn_modify = QPushButton("✎ MODIFY")
        for btn in (self._btn_approve, self._btn_reject, self._btn_modify):
            btn.setStyleSheet("""
                QPushButton { background: rgba(255,255,255,0.06);
                    border: 1px solid rgba(255,255,255,0.15); border-radius: 8px;
                    color: #CCC; font-size: 11px; font-weight: bold; padding: 6px; }
                QPushButton:hover { background: rgba(0,191,255,0.2); color: #FFF; }
            """)
            req_btns.addWidget(btn)
        self._btn_approve.clicked.connect(self._approve)
        self._btn_reject.clicked.connect(self._reject)
        self._btn_modify.clicked.connect(self._modify)
        r_lay.addLayout(req_btns)
        right.addWidget(req)

        # Ask-the-human card
        ask = QFrame()
        ask.setStyleSheet("""
            background: rgba(255,167,38,0.08);
            border: 1px solid rgba(255,167,38,0.35); border-radius: 12px;
        """)
        k_lay = QVBoxLayout(ask)
        k_lay.setContentsMargins(12, 10, 12, 10)
        k_t = QLabel("🤔 ASK THE HUMAN — low-confidence clarification")
        k_t.setStyleSheet("font-size: 10px; color: #FFA726; font-weight: bold;"
                          " background: transparent;")
        k_lay.addWidget(k_t)
        self._ask_text = QLabel("No open questions")
        self._ask_text.setWordWrap(True)
        self._ask_text.setStyleSheet("font-size: 12px; color: #F5D9A0;"
                                     " background: transparent;")
        k_lay.addWidget(self._ask_text)
        ask_btns = QHBoxLayout()
        self._btn_left = QPushButton("⬅ LEFT")
        self._btn_right = QPushButton("➡ RIGHT")
        for btn in (self._btn_left, self._btn_right):
            btn.setStyleSheet("""
                QPushButton { background: rgba(255,167,38,0.15);
                    border: 1px solid rgba(255,167,38,0.4); border-radius: 8px;
                    color: #FFCC80; font-size: 11px; font-weight: bold; padding: 6px; }
                QPushButton:hover { background: rgba(255,167,38,0.3); }
            """)
            ask_btns.addWidget(btn)
        self._btn_left.clicked.connect(lambda: self._answer("LEFT"))
        self._btn_right.clicked.connect(lambda: self._answer("RIGHT"))
        k_lay.addLayout(ask_btns)
        right.addWidget(ask)
        body.addLayout(right, 2)
        layout.addLayout(body, 1)

        # History strip
        hist_title = QLabel("INTERACTION HISTORY")
        hist_title.setStyleSheet("font-size: 10px; color: #888; font-weight: bold;")
        layout.addWidget(hist_title)
        self._hist = QLabel("")
        self._hist.setWordWrap(True)
        self._hist.setStyleSheet("""
            background: rgba(255,255,255,0.03); border-radius: 10px;
            padding: 8px 12px; font-size: 10px; color: #889; font-family: Monospace;
        """)
        layout.addWidget(self._hist)

    # ------------------------------------------------------------- data
    def _seed(self) -> None:
        """A lively demo scene — a person walking toward the robot."""
        if not self._hc.people():
            p = self._hc.track_person(2.4, 37.0, 0.94)
            p.status = "FOLLOWING"
        # Seed a demo AI request
        if not self._hc.pending_requests():
            self._hc.ai_propose("Change route around obstacle",
                                "Obstacle detected 1.8 m ahead on planned path.")

    def _set_mode(self, mode: InteractionMode) -> None:
        self._hc.set_mode(mode)
        p = self._hc.designated_person()
        if p:
            self._hc.set_status(p.id, mode.value.upper())

    def _approve(self) -> None:
        pending = self._hc.pending_requests()
        if pending:
            self._hc.approve(pending[0].id)

    def _reject(self) -> None:
        pending = self._hc.pending_requests()
        if pending:
            self._hc.reject(pending[0].id)

    def _modify(self) -> None:
        pending = self._hc.pending_requests()
        if pending:
            self._hc.modify(pending[0].id, "Change route AND slow to 0.2 m/s")

    def _answer(self, choice: str) -> None:
        open_q = self._hc.open_clarifications()
        if open_q:
            self._hc.answer_clarification(open_q[0].id, choice)

    def refresh(self) -> None:
        # Animate the scene: person approaches / oscillates
        t = time.time()
        base = 2.4 - 0.15 * ((int(t) % 4) == 0)
        dist = max(0.8, 2.4 - 0.4 * math.sin(t / 6.0))
        p = self._hc.track_person(dist, 37.0 + 4 * math.sin(t / 9.0), 0.94)
        if self._hc.mode() in (InteractionMode.FOLLOW, InteractionMode.ESCORT):
            p.status = self._hc.mode().value.upper()
        else:
            p.status = p.status or "IDLE"

        # Person card
        mode = self._hc.mode()
        self._mode_badge.setText(f"MODE: {mode.value.upper()}")
        self._person.setText(
            f"ID #{p.id} · Distance: {p.distance_m:.1f} m · "
            f"Direction: {p.direction_deg:.0f}°\n"
            f"Velocity: {p.velocity_ms:+.2f} m/s · Presence: {p.presence.value} · "
            f"Zone: {p.zone}\n"
            f"Status: {p.status} · Confidence: {p.confidence * 100:.0f}%")
        self._conf.setValue(int(p.confidence * 100))

        # Authority dots
        auth = self._hc.authority()
        for name, dot in self._authority.items():
            active = name == auth.value.upper()
            color = AUTHORITY_COLOR.get(auth, "#00BFFF") if active else "#555"
            dot.setText("●" if active else "○")
            dot.setStyleSheet(f"font-size: 14px; color: {color};"
                              f" background: transparent;")

        # Interaction state
        states = []
        for candidate in (InteractionMode.FOLLOW, InteractionMode.STOP,
                          InteractionMode.ESCORT, InteractionMode.RETURN_TO_OWNER):
            states.append("●" if mode == candidate else "○")
        self._interaction.setText(
            f"FOLLOW {states[0]} · STOP {states[1]} · ESCORT {states[2]} · "
            f"RETURN {states[3]}")

        # Requests
        pending = self._hc.pending_requests()
        if pending:
            r = pending[0]
            self._req_text.setText(f'"{r.command}" — {r.reason}')
            self._btn_approve.setEnabled(True)
            self._btn_reject.setEnabled(True)
            self._btn_modify.setEnabled(True)
        else:
            self._req_text.setText("No pending requests — AI acts within policy")
            self._btn_approve.setEnabled(False)
            self._btn_reject.setEnabled(False)
            self._btn_modify.setEnabled(False)

        # Ask-the-human
        open_q = self._hc.open_clarifications()
        if open_q:
            q = open_q[0]
            self._ask_text.setText(f'"{q.question}" (confidence {q.confidence * 100:.0f}%)')
            self._btn_left.setEnabled(True)
            self._btn_right.setEnabled(True)
        else:
            self._ask_text.setText("No open questions — robot acts with confidence")
            self._btn_left.setEnabled(False)
            self._btn_right.setEnabled(False)

        # History
        hist = self._hc.interaction_history(limit=6)
        self._hist.setText("\n".join(hist) if hist else "No interactions yet")

    def on_show(self) -> None:
        self.refresh()
        self._timer.start(2000)

    def on_hide(self) -> None:
        self._timer.stop()
