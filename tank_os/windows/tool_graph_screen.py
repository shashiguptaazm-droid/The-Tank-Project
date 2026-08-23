"""ToolGraphScreen — 🧠 AI Tool Graph (tool-calling plan §14).

The dedicated GUI from the plan: USER REQUEST → AI → tool calls
(vision.detect → navigation.plan → safety.validate → robot.goto), each
marked ✓/✗ with latency, plus the AI Tool Composer (§20) readiness demo
and the audit log (§13).

Every tool call shown here goes through the real ToolEngine pipeline
(validate → permission → safety → execute) — never LLM → shell → motor.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from tank_os.core.tool_engine import AgentRole, RiskTier, ToolEngine, build_default_tools

logger = logging.getLogger("tank_os.windows.toolgraph")


class _Node(QFrame):
    """One tool-call node in the flow."""

    def __init__(self, label: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("tgNode")
        self.setStyleSheet("""
            #tgNode { background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.12); border-radius: 10px; }
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(8)
        self._lbl = QLabel(label)
        self._lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #DDD;"
                                " background: transparent;")
        lay.addWidget(self._lbl)
        lay.addStretch()
        self._mark = QLabel("·")
        self._mark.setStyleSheet("font-size: 14px; font-weight: bold; color: #888;"
                                 " background: transparent;")
        lay.addWidget(self._mark)
        self._ms = QLabel("")
        self._ms.setStyleSheet("font-size: 10px; color: #667; font-family: Monospace;"
                               " background: transparent;")
        lay.addWidget(self._ms)

    def set_result(self, ok: bool, ms: float = 0.0, risk: str = "") -> None:
        self._mark.setText("✓" if ok else "✗")
        color = "#81C784" if ok else "#FF8A80"
        self._mark.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {color};"
                                 f" background: transparent;")
        self._ms.setText(f"{ms:.0f}ms" if ms else risk.upper())


class ToolGraphScreen(QWidget):
    """AI Tool Graph — the tool-using robot executive, visualized."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._engine = ToolEngine()
        build_default_tools(self._engine)
        self._engine.set_role(AgentRole.NAVIGATOR)
        self._build_ui()
        self._demo()
        self.refresh()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(2500)

    # --------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("🧠 AI Tool Graph — typed, permissioned tool-calling")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFF;")
        header.addWidget(title)
        header.addStretch()
        self._role_badge = QLabel("role: —")
        self._role_badge.setStyleSheet("""
            background: rgba(0,191,255,0.12); border: 1px solid rgba(0,191,255,0.35);
            border-radius: 10px; padding: 6px 14px; font-size: 11px; font-weight: bold;
            color: #80D8FF;
        """)
        header.addWidget(self._role_badge)
        layout.addLayout(header)

        # Flow visualization
        flow_label = QLabel("LIVE TOOL CALL FLOW — AI NEVER TOUCHES HARDWARE DIRECTLY")
        flow_label.setStyleSheet("font-size: 10px; color: #888; font-weight: bold;")
        layout.addWidget(flow_label)
        self._flow_box = QWidget()
        self._flow_lay = QVBoxLayout(self._flow_box)
        self._flow_lay.setContentsMargins(0, 0, 0, 0)
        self._flow_lay.setSpacing(5)
        layout.addWidget(self._flow_box)

        # Composer + audit
        body = QHBoxLayout()
        body.setSpacing(10)
        comp = QFrame()
        comp.setStyleSheet("""
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.1); border-radius: 12px;
        """)
        c_lay = QVBoxLayout(comp)
        c_lay.setContentsMargins(12, 10, 12, 10)
        c_t = QLabel("🎬 AI TOOL COMPOSER — 'Prepare the robot for autonomous patrol'")
        c_t.setStyleSheet("font-size: 10px; color: #888; font-weight: bold;"
                          " background: transparent;")
        c_lay.addWidget(c_t)
        self._plan = QLabel("")
        self._plan.setWordWrap(True)
        self._plan.setStyleSheet("font-size: 11px; color: #CCC;"
                                 " background: transparent;")
        c_lay.addWidget(self._plan)
        self._readiness = QProgressBar()
        self._readiness.setRange(0, 100)
        self._readiness.setTextVisible(True)
        self._readiness.setFixedHeight(16)
        self._readiness.setStyleSheet("""
            QProgressBar { background: rgba(255,255,255,0.06);
                border: none; border-radius: 8px; text-align: center;
                font-size: 10px; font-weight: bold; color: #FFF; }
            QProgressBar::chunk { background: #00BFFF; border-radius: 8px; }
        """)
        c_lay.addWidget(self._readiness)
        run_btn = QPushButton("🔄 RE-RUN COMPOSER")
        run_btn.setStyleSheet("""
            QPushButton { background: rgba(0,191,255,0.15);
                border: 1px solid rgba(0,191,255,0.4); border-radius: 8px;
                padding: 7px 12px; color: #80D8FF; font-size: 11px; font-weight: bold; }
            QPushButton:hover { background: rgba(0,191,255,0.28); }
        """)
        run_btn.clicked.connect(self._demo)
        c_lay.addWidget(run_btn)
        body.addWidget(comp, 1)

        audit = QFrame()
        audit.setStyleSheet("""
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.1); border-radius: 12px;
        """)
        a_lay = QVBoxLayout(audit)
        a_lay.setContentsMargins(12, 10, 12, 10)
        a_t = QLabel("📜 TOOL AUDIT LOG (§13)")
        a_t.setStyleSheet("font-size: 10px; color: #888; font-weight: bold;"
                          " background: transparent;")
        a_lay.addWidget(a_t)
        self._audit = QLabel("")
        self._audit.setWordWrap(True)
        self._audit.setStyleSheet("font-size: 10px; color: #9AA;"
                                  " font-family: Monospace; background: transparent;")
        a_lay.addWidget(self._audit)
        body.addWidget(audit, 1)
        layout.addLayout(body, 1)

    # ------------------------------------------------------------- demo
    def _demo(self) -> None:
        e = self._engine
        # Tool chain (plan §9): readiness workflow
        chain = [
            {"tool": "robot.get_health"},
            {"tool": "robot.get_battery"},
            {"tool": "robot.get_sensor_status"},
            {"tool": "robot.get_jetson_status"},
            {"tool": "robot.get_network_status"},
            {"tool": "robot.get_active_mission"},
        ]
        e.run_chain(chain, agent="ai")
        # A controlled movement + a sandbox rejection demo
        e.execute("robot.move", {"direction": "forward", "distance_m": 1.0,
                                 "max_speed_mps": 0.25}, agent="ai")
        e.execute("robot.move", {"direction": "forward", "distance_m": 1.0,
                                 "max_speed_mps": 100}, agent="ai")
        e.execute("system.reboot", agent="ai")

    def _render_flow(self, calls: List[str]) -> None:
        while self._flow_lay.count():
            item = self._flow_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        user = _Node("👤 USER REQUEST")
        user.set_result(True)
        self._flow_lay.addWidget(user)
        ai = _Node("🧠 AI — 'is the robot ready for patrol?'")
        ai.set_result(True)
        self._flow_lay.addWidget(ai)
        for call in calls:
            spec = self._engine.get(call)
            node = _Node(f"▸ {call}")
            if spec:
                node.set_result(True, risk=spec.risk.value)
            self._flow_lay.addWidget(node)

    def refresh(self) -> None:
        e = self._engine
        self._role_badge.setText(f"role: {e.role().value}")

        # Flow: last successful chain
        audit = e.audit_log(limit=20)
        calls = []
        for entry in audit:
            if entry.execution in ("SUCCESS", "FAILED", "NEEDS_APPROVAL"):
                calls.append(entry.tool)
        calls = calls[-6:] or ["robot.get_health", "robot.get_battery",
                               "robot.get_sensor_status", "robot.get_jetson_status",
                               "robot.get_network_status"]
        self._render_flow(calls)

        # Audit lines
        lines = []
        for entry in reversed(e.audit_log(limit=8)):
            mark = {"SUCCESS": "✓", "FAILED": "✗", "BLOCKED": "⛔",
                    "NEEDS_APPROVAL": "⚠"}.get(entry.execution, "·")
            lines.append(
                f"{entry.ts} {mark} {entry.tool}  [v:{entry.validation} "
                f"s:{entry.safety}] {entry.latency_ms:.0f}ms")
        self._audit.setText("\n".join(lines) if lines else "No tool calls yet")

    def _show_composer(self) -> None:
        result = self._engine.compose("prepare for autonomous patrol")
        steps = "\n".join(f"▸ {s}" for s in result["plan"])
        self._plan.setText(steps)
        self._readiness.setValue(result["readiness_pct"])
        self._readiness.setFormat(f"PATROL READINESS: {result['readiness_pct']}%")

    def on_show(self) -> None:
        self.refresh()
        self._show_composer()
        self._timer.start(2500)

    def on_hide(self) -> None:
        self._timer.stop()
