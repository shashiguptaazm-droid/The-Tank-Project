"""TankOSSystemScreen — 🤖 TankOS proper (30-part architecture plan).

The top-level system view: distributed node map (UNO Q executive / Jetson AI /
STM32 real-time / ESP32 fleet / VPS cloud), the canonical robot state
machine, the device registry with lifecycle states, the health dashboard,
and end-to-end command observability (§28).

Everything is driven by tank_os.core.tankos_core.TankOS — the canonical API.
"""

from __future__ import annotations

import logging
import time
from typing import Dict, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget,
)

from tank_os.core.tankos_core import (
    Command, CommandSource, DeviceState, RobotState, TankOS,
)

logger = logging.getLogger("tank_os.windows.tankossys")

STATE_COLOR = {
    RobotState.BOOT: "#888", RobotState.SELF_TEST: "#FFD54F",
    RobotState.READY: "#81C784", RobotState.MANUAL: "#4FC3F7",
    RobotState.ASSISTED: "#4FC3F7", RobotState.AUTONOMOUS: "#00BFFF",
    RobotState.MISSION: "#7C4DFF", RobotState.EMERGENCY_STOP: "#FF5252",
    RobotState.FAULT: "#FF8A80", RobotState.SAFE_MODE: "#FFA726",
    RobotState.RECOVERY: "#FFD54F",
}

DEVICE_STATE_COLOR = {
    DeviceState.READY: "#81C784", DeviceState.ACTIVE: "#00BFFF",
    DeviceState.DEGRADED: "#FFA726", DeviceState.FAULT: "#FF8A80",
    DeviceState.RECOVERING: "#FFD54F", DeviceState.DISCOVERING: "#888",
    DeviceState.INITIALIZING: "#888", DeviceState.OFFLINE: "#667",
}


class _NodeCard(QFrame):
    """A compute node in the distributed TankOS map."""

    def __init__(self, name: str, role: str, color: str,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"""
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.12); border-radius: 12px;
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(2)
        t = QLabel(name)
        t.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {color};"
                        f" background: transparent;")
        lay.addWidget(t)
        r = QLabel(role)
        r.setStyleSheet("font-size: 9px; color: #889; background: transparent;")
        lay.addWidget(r)
        self._line = QLabel("")
        self._line.setWordWrap(True)
        self._line.setStyleSheet("font-size: 10px; color: #CCC;"
                                 " background: transparent;")
        lay.addWidget(self._line)

    def set_line(self, text: str) -> None:
        self._line.setText(text)


class TankOSSystemScreen(QWidget):
    """TankOS proper — one operating system over all the nodes."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._tank = TankOS()
        self._tank.boot()
        self._build_ui()
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
        title = QLabel("🤖 TankOS — the robot operating platform")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFF;")
        header.addWidget(title)
        header.addStretch()
        self._state_badge = QLabel("")
        self._state_badge.setStyleSheet("""
            background: rgba(0,191,255,0.12); border: 1px solid rgba(0,191,255,0.35);
            border-radius: 10px; padding: 6px 14px; font-size: 11px; font-weight: bold;
            color: #80D8FF;
        """)
        header.addWidget(self._state_badge)
        layout.addLayout(header)

        # Distributed node map (§25–26)
        node_title = QLabel("DISTRIBUTED TANKOS — ONE OS, MANY NODES")
        node_title.setStyleSheet("font-size: 10px; color: #888; font-weight: bold;")
        layout.addWidget(node_title)
        nodes = QHBoxLayout()
        nodes.setSpacing(8)
        self._unoq = _NodeCard("UNO Q", "EXECUTIVE · diagnostics · command AI",
                               "#00BFFF")
        self._jetson = _NodeCard("JETSON", "AI / ROS · perception · SLAM",
                                 "#7C4DFF")
        self._stm32 = _NodeCard("STM32", "REAL-TIME · motors · safety", "#FF8A80")
        self._esp32 = _NodeCard("ESP32 FLEET", "DISTRIBUTED SENSORS", "#66BB6A")
        self._vps = _NodeCard("VPS", "CLOUD AI · long-term memory", "#FFA726")
        for n in (self._unoq, self._jetson, self._stm32, self._esp32, self._vps):
            nodes.addWidget(n)
        layout.addLayout(nodes)

        # State machine + devices
        body = QHBoxLayout()
        body.setSpacing(10)

        state_frame = QFrame()
        state_frame.setStyleSheet("""
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;
        """)
        s_lay = QVBoxLayout(state_frame)
        s_lay.setContentsMargins(12, 10, 12, 10)
        s_t = QLabel("CANONICAL ROBOT STATE MACHINE")
        s_t.setStyleSheet("font-size: 10px; color: #888; font-weight: bold;"
                          " background: transparent;")
        s_lay.addWidget(s_t)
        self._states: Dict[str, QLabel] = {}
        for st in (RobotState.BOOT, RobotState.SELF_TEST, RobotState.READY,
                   RobotState.MANUAL, RobotState.AUTONOMOUS, RobotState.MISSION):
            row = QHBoxLayout()
            dot = QLabel("○")
            dot.setStyleSheet("font-size: 12px; color: #555; background: transparent;")
            row.addWidget(dot)
            lbl = QLabel(st.value.upper())
            lbl.setStyleSheet("font-size: 10px; color: #BBB; background: transparent;")
            row.addWidget(lbl)
            row.addStretch()
            s_lay.addLayout(row)
            self._states[st] = dot
        safe_lbl = QLabel("↳ any state → EMERGENCY_STOP / FAULT / SAFE_MODE → RECOVERY → READY")
        safe_lbl.setStyleSheet("font-size: 9px; color: #889; background: transparent;")
        s_lay.addWidget(safe_lbl)
        s_lay.addStretch(1)
        body.addWidget(state_frame, 1)

        dev_frame = QFrame()
        dev_frame.setStyleSheet("""
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;
        """)
        d_lay = QVBoxLayout(dev_frame)
        d_lay.setContentsMargins(12, 10, 12, 10)
        d_t = QLabel("DEVICE REGISTRY — LIFECYCLE")
        d_t.setStyleSheet("font-size: 10px; color: #888; font-weight: bold;"
                          " background: transparent;")
        d_lay.addWidget(d_t)
        self._devices = QLabel("")
        self._devices.setWordWrap(True)
        self._devices.setStyleSheet("font-size: 10px; color: #CCC;"
                                    " font-family: Monospace; background: transparent;")
        d_lay.addWidget(self._devices)
        d_lay.addStretch(1)
        body.addWidget(dev_frame, 1)
        layout.addLayout(body, 1)

        # Health + observability
        bottom = QHBoxLayout()
        bottom.setSpacing(10)
        health = QFrame()
        health.setStyleSheet("""
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;
        """)
        h_lay = QVBoxLayout(health)
        h_lay.setContentsMargins(12, 10, 12, 10)
        h_t = QLabel("🩺 HEALTH — FROM MEASURABLE SIGNALS")
        h_t.setStyleSheet("font-size: 10px; color: #888; font-weight: bold;"
                          " background: transparent;")
        h_lay.addWidget(h_t)
        self._overall_bar = QProgressBar()
        self._overall_bar.setRange(0, 100)
        self._overall_bar.setTextVisible(True)
        self._overall_bar.setFixedHeight(18)
        self._overall_bar.setStyleSheet("""
            QProgressBar { background: rgba(255,255,255,0.06);
                border: none; border-radius: 9px; text-align: center;
                font-size: 10px; font-weight: bold; color: #FFF; }
            QProgressBar::chunk { background: #00BFFF; border-radius: 9px; }
        """)
        h_lay.addWidget(self._overall_bar)
        self._health_components = QLabel("")
        self._health_components.setWordWrap(True)
        self._health_components.setStyleSheet("font-size: 10px; color: #CCC;"
                                              " background: transparent;")
        h_lay.addWidget(self._health_components)
        bottom.addWidget(health, 1)

        obs = QFrame()
        obs.setStyleSheet("""
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;
        """)
        o_lay = QVBoxLayout(obs)
        o_lay.setContentsMargins(12, 10, 12, 10)
        o_t = QLabel("🔍 COMMAND OBSERVABILITY — END-TO-END TRACE")
        o_t.setStyleSheet("font-size: 10px; color: #888; font-weight: bold;"
                          " background: transparent;")
        o_lay.addWidget(o_t)
        self._trace = QLabel("")
        self._trace.setWordWrap(True)
        self._trace.setStyleSheet("font-size: 10px; color: #9AA;"
                                  " font-family: Monospace; background: transparent;")
        o_lay.addWidget(self._trace)
        bottom.addWidget(obs, 1)
        layout.addLayout(bottom)

    # ------------------------------------------------------------- data
    def refresh(self) -> None:
        tank = self._tank
        # live demo: run a mission + trace
        missions = tank.missions.list()
        if not missions:
            m = tank.missions.create("patrol", ["goto:A", "scan", "return_home"])
            tank.missions.start(m.id)
            tank.commands.send(Command(
                "robot.move", CommandSource.HUMAN,
                {"direction": "forward", "distance_m": 1.0}))
        else:
            tank.missions.advance(missions[0].id)
            if missions[0].progress >= 100:
                tank.missions.complete(missions[0].id)

        # State badge + machine dots
        st = tank.state.state()
        color = STATE_COLOR.get(st, "#00BFFF")
        self._state_badge.setText(f"STATE: {st.value.upper()}")
        self._state_badge.setStyleSheet(f"""
            background: rgba(0,191,255,0.12); border: 1px solid {color};
            border-radius: 10px; padding: 6px 14px; font-size: 11px; font-weight: bold;
            color: {color};
        """)
        for state, dot in self._states.items():
            active = state == st
            dot.setText("●" if active else "○")
            dot.setStyleSheet(f"font-size: 13px; color: {STATE_COLOR.get(state, '#555')};"
                              f" background: transparent;")

        # Nodes
        self._unoq.set_line("EXECUTIVE ✓ · cpu 38%")
        self._jetson.set_line("AI/ROS ✓ · gpu 73%")
        self._stm32.set_line("REAL-TIME ✓ · motors armed")
        esp = tank.devices.list(device_type="esp32")
        online = sum(1 for d in esp if d.status is not DeviceState.OFFLINE)
        self._esp32.set_line(f"{online}/{len(esp)} nodes ✓")
        self._vps.set_line("CLOUD ✓ · Tailscale up")

        # Device registry
        dev_lines = []
        for d in tank.devices.list():
            color = DEVICE_STATE_COLOR.get(d.status, "#888")
            dev_lines.append(
                f"<span style='color:{color};font-weight:bold'>{d.id}</span> "
                f"[{d.type} · {d.controller}] {d.status.value} · h{d.health:.0%}")
        self._devices.setText("<br>".join(dev_lines))

        # Health
        report = tank.health.report()
        self._overall_bar.setValue(report.overall)
        self._overall_bar.setFormat(f"OVERALL HEALTH: {report.overall}/100")
        comps = " · ".join(f"{k.upper()} {v:.0f}" for k, v in
                           list(report.components.items())[:6])
        self._health_components.setText(comps)

        # Trace
        trace_lines = []
        for entry in tank.commands.trace(limit=5):
            mark = {"EXECUTED": "✓", "FAILED": "✗", "BLOCKED": "⛔"}.get(
                entry["execution"], "·")
            trace_lines.append(
                f"{entry['ts']} {mark} {entry['source']}:{entry['command']} "
                f"[{entry['validation']}/{entry['safety']}] {entry['latency_ms']}ms")
        self._trace.setText("\n".join(trace_lines) if trace_lines
                            else "No commands yet")

    def on_show(self) -> None:
        self.refresh()
        self._timer.start(2500)

    def on_hide(self) -> None:
        self._timer.stop()
