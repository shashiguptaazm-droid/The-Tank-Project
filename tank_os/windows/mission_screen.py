"""MissionScreen — 🎯 Mission Control (GUI blueprint).

Mission builder with draggable-style node chain (START → waypoints →
actions → RETURN HOME), mission types (patrol / explore / follow /
inspect / search / return-home / perimeter / waypoint / object-search),
and a live "current mission" panel.

Missions are emitted on the EventBus (``mission_start``) — the
navigation/patrol layer executes them; the GUI stays a control surface.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from tank_os.core.event_bus import Event, EventBus

logger = logging.getLogger("tank_os.windows.mission")

MISSION_TYPES = [
    ("PATROL", "🔁"), ("EXPLORE", "🧭"), ("FOLLOW", "👣"), ("INSPECT", "🔍"),
    ("SEARCH", "🔎"), ("RETURN HOME", "🏠"), ("PERIMETER", "⭕"),
    ("WAYPOINT", "📍"), ("OBJECT SEARCH", "🎯"),
]

NODE_STYLES = {
    "START": ("#1B5E20", "#A5D6A7"),
    "WAYPOINT": ("#0D47A1", "#90CAF9"),
    "SCAN AREA": ("#4A148C", "#CE93D8"),
    "DETECT PERSON": ("#B71C1C", "#EF9A9A"),
    "RETURN HOME": ("#1B5E20", "#A5D6A7"),
}


class _Node(QFrame):
    """A mission-builder node card."""

    def __init__(self, text: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        bg, fg = NODE_STYLES.get(text, ("#263238", "#B0BEC5"))
        self.setStyleSheet(f"""
            background: {bg}; border-radius: 10px; padding: 10px 16px;
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {fg}; font-size: 12px; font-weight: bold;")
        lay.addWidget(lbl)


class MissionScreen(QWidget):
    """Mission builder + active mission panel."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._bus = EventBus()
        self._chain: List[str] = [
            "START", "WAYPOINT", "SCAN AREA", "WAYPOINT",
            "DETECT PERSON", "RETURN HOME",
        ]
        self._build_ui()

    # --------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("🎯 Mission Control")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFF;")
        header.addWidget(title)
        header.addStretch()
        self._active = QLabel("NO ACTIVE MISSION")
        self._active.setStyleSheet("""
            background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12);
            border-radius: 10px; padding: 6px 14px; font-size: 11px; font-weight: bold;
            color: #FFD54F;
        """)
        header.addWidget(self._active)
        layout.addLayout(header)

        # Left: mission builder chain
        builder, b_lay = self._panel("MISSION BUILDER")
        b_lay.setSpacing(4)
        self._chain_box = QWidget()
        self._chain_lay = QVBoxLayout(self._chain_box)
        self._chain_lay.setContentsMargins(0, 0, 0, 0)
        self._chain_lay.setSpacing(4)
        self._rebuild_chain()
        b_lay.addWidget(self._chain_box)

        chain_btns = QHBoxLayout()
        for label, icon in [("➕ Waypoint", "📍"), ("🔄 Scan Area", "📡"),
                            ("🔎 Detect Person", "👤"), ("🏠 Return Home", "🏠")]:
            btn = QPushButton(f"{icon} {label}")
            btn.setStyleSheet("""
                QPushButton { background: rgba(0,191,255,0.12);
                    border: 1px solid rgba(0,191,255,0.3); border-radius: 8px;
                    color: #80D8FF; font-size: 10px; font-weight: bold; padding: 6px 10px; }
                QPushButton:hover { background: rgba(0,191,255,0.25); }
            """)
            node = label.split(" ", 1)[1]
            btn.clicked.connect(lambda _=False, n=node: self._add_node(n))
            chain_btns.addWidget(btn)
        chain_btns.addStretch()
        b_lay.addLayout(chain_btns)

        # Right: mission types + start
        right = QVBoxLayout()
        types, t_lay = self._panel("MISSION TYPES")
        t_grid = QGridLayout()
        t_grid.setSpacing(6)
        for i, (name, icon) in enumerate(MISSION_TYPES):
            btn = QPushButton(f"{icon} {name.title()}")
            btn.setStyleSheet("""
                QPushButton { background: rgba(255,255,255,0.05);
                    border: 1px solid rgba(255,255,255,0.12); border-radius: 8px;
                    color: #DDD; font-size: 10px; padding: 8px; }
                QPushButton:hover { background: rgba(0,191,255,0.18); color: #FFF; }
            """)
            btn.clicked.connect(lambda _=False, n=name: self._set_mission(n))
            t_grid.addWidget(btn, i // 3, i % 3)
        t_lay.addLayout(t_grid)
        right.addWidget(types)

        start = QPushButton("▶ START MISSION")
        start.setFixedHeight(46)
        start.setStyleSheet("""
            QPushButton { background: rgba(27,94,32,0.9); color: #FFF;
                font-size: 14px; font-weight: bold; border: none; border-radius: 10px; }
            QPushButton:hover { background: #2E7D32; }
        """)
        start.clicked.connect(self._start_mission)
        right.addWidget(start)
        right.addStretch()

        body = QHBoxLayout()
        body.addWidget(builder, 3)
        body.addLayout(right, 2)
        layout.addLayout(body, 1)

    def _panel(self, title: str):
        """Return (frame, content_layout) — title on top, content below."""
        frame = QFrame()
        frame.setObjectName("missionPanel")
        frame.setStyleSheet("""
            #missionPanel { background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; }
        """)
        outer = QVBoxLayout(frame)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        lbl = QLabel(title)
        lbl.setStyleSheet("font-size: 10px; color: #888; font-weight: bold; padding: 8px 12px;")
        outer.addWidget(lbl)
        content = QVBoxLayout()
        content.setContentsMargins(12, 4, 12, 10)
        outer.addLayout(content)
        return frame, content

    # ------------------------------------------------------------ logic
    def _rebuild_chain(self) -> None:
        while self._chain_lay.count():
            item = self._chain_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for i, node in enumerate(self._chain):
            row = QHBoxLayout()
            if i < len(self._chain) - 1:
                arrow = QLabel("↓")
                arrow.setStyleSheet("color: #666; font-size: 14px;")
                row.addWidget(arrow)
            row.addWidget(_Node(node))
            row.addStretch()
            self._chain_lay.addLayout(row)

    def _add_node(self, node: str) -> None:
        self._chain.insert(max(1, len(self._chain) - 1), node)
        self._rebuild_chain()

    def _set_mission(self, mtype: str) -> None:
        self._active.setText(f"▶ {mtype}")
        self._active.setStyleSheet("""
            background: rgba(27,94,32,0.35); border: 1px solid #4CAF50;
            border-radius: 10px; padding: 6px 14px; font-size: 11px; font-weight: bold;
            color: #A5D6A7;
        """)

    def _start_mission(self) -> None:
        mission = {"type": self._active.text().replace("▶ ", "").strip() or "PATROL",
                   "nodes": list(self._chain)}
        self._bus.emit(Event("mission_start", mission, source="mission_screen"))
        logger.info("Mission started: %s", mission)

    def on_show(self) -> None:
        pass

    def on_hide(self) -> None:
        pass



