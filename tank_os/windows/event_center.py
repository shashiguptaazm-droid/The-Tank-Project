"""EventCenterScreen — 🚨 Event Center (GUI blueprint).

One unified event stream from the TankOS EventBus history, with category
filters: ALL | SAFETY | AI | HARDWARE | NETWORK | NAVIGATION. Each row is
colour-coded by severity (⚠ warn / ✓ info) with a timestamp.

Also implements the 200-feature plan §2 #20 — **unified chronological event
replay**: record a mission and replay it at 0.25×, 1× and 4× speed with
play/pause and a progress bar. The replay walks the real EventBus history
chronologically and highlights the currently-playing event.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from tank_os.core.event_bus import Event, EventBus

logger = logging.getLogger("tank_os.windows.events")

FILTERS = ["ALL", "SAFETY", "AI", "HARDWARE", "NETWORK", "NAVIGATION"]
SPEEDS = [0.25, 1.0, 4.0]

CATEGORY = {
    "SAFETY": ("estop", "safety", "battery_critical", "battery_low", "cmd_drive"),
    "AI": ("ai", "assistant", "emotion", "mission", "decision", "perception"),
    "HARDWARE": ("hardware", "usb", "esp32", "serial", "mcu"),
    "NETWORK": ("network", "wifi", "tailscale", "latency", "packet"),
    "NAVIGATION": ("nav", "navigation", "path", "waypoint", "patrol", "dock", "odom"),
}

SEV_COLOR = {"warn": "#FFD54F", "error": "#FF8A80", "info": "#9EE7A5"}


class _EventRow(QFrame):
    """One event row in the stream."""

    def __init__(self, event: Event, highlight: bool = False,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        severity = event.data.get("severity", "info") if isinstance(event.data, dict) \
            else "info"
        color = SEV_COLOR.get(severity, "#9EE7A5")
        border = f"3px solid #00BFFF" if highlight else f"3px solid {color}"
        bg = "rgba(0,191,255,0.12)" if highlight else "rgba(255,255,255,0.03)"
        self.setStyleSheet(f"""
            background: {bg}; border-left: {border};
            border-radius: 6px;
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(10)

        ts = datetime.fromtimestamp(event.timestamp).strftime("%H:%M:%S")
        t = QLabel(ts)
        t.setStyleSheet("font-size: 10px; color: #667; font-family: Monospace;")
        lay.addWidget(t)

        tag = QLabel(event.type.upper())
        tag.setStyleSheet("font-size: 9px; font-weight: bold; color: #888;")
        lay.addWidget(tag)

        summary = str(event.data.get("summary", "")) if isinstance(event.data, dict) \
            else str(event.data)
        body = QLabel(summary or event.type)
        body.setStyleSheet("font-size: 11px; color: #DDD;")
        lay.addWidget(body, 1)


def _seed_history(limit: int = 120) -> List[Event]:
    """Return a representative chronological stream when the bus is empty,
    so the screen (and replay) always demonstrate the concept live."""
    try:
        history = EventBus().history(limit=limit)
    except Exception:                                           # noqa: BLE001
        history = []
    if history:
        return history
    now = time.time()
    seeds = [
        ("jetson_connected", "Jetson connected (Tailscale)", "info"),
        ("mission_started", "Mission started: PATROL ZONE A", "info"),
        ("sensor_init", "Camera + LiDAR + IMU online", "info"),
        ("person_detected", "Person detected 2.1 m ahead", "info"),
        ("ai_decision", "Decision: continue forward (conf 0.94)", "info"),
        ("obstacle_detected", "Obstacle detected 1.8 m ahead", "warn"),
        ("speed_reduced", "Speed reduced 0.50 → 0.25 m/s", "info"),
        ("path_replanned", "Path replanned around obstacle", "info"),
        ("navigation_resumed", "Navigation resumed after replan", "info"),
        ("wifi_latency", "Wi-Fi latency increased to 64 ms", "warn"),
        ("battery_low", "Battery at 34% — low warning", "warn"),
        ("motor_temp", "Motor temperature high (68°C)", "warn"),
        ("estop_cleared", "E-stop cleared — motors re-armed", "info"),
    ]
    return [Event(t, {"summary": s, "severity": sev}, timestamp=now - i * 30)
            for i, (t, s, sev) in enumerate(seeds)]


class EventCenterScreen(QWidget):
    """Unified EventBus stream with filters + chronological replay."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._bus = EventBus()
        self._filter = "ALL"
        self._history: List[Event] = []
        self._replay_idx = 0
        self._replay_playing = False
        self._replay_speed = 1.0
        self._replay_start = 0.0
        self._replay_anchor = 0.0
        self._build_ui()
        self.refresh()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(3000)

        self._replay_timer = QTimer(self)
        self._replay_timer.timeout.connect(self._tick_replay)
        self._replay_timer.start(200)

    # --------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("🚨 Event Center")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFF;")
        header.addWidget(title)
        header.addStretch()
        self._replay_state = QLabel("")
        self._replay_state.setStyleSheet("""
            background: rgba(0,191,255,0.12); border: 1px solid rgba(0,191,255,0.35);
            border-radius: 10px; padding: 6px 14px; font-size: 11px; font-weight: bold;
            color: #80D8FF;
        """)
        header.addWidget(self._replay_state)
        layout.addLayout(header)

        # Filter chips
        chips = QHBoxLayout()
        chips.setSpacing(6)
        for f in FILTERS:
            btn = QPushButton(f)
            btn.setFixedSize(86, 28)
            btn.setStyleSheet("""
                QPushButton { background: rgba(255,255,255,0.05);
                    border: 1px solid rgba(255,255,255,0.12); border-radius: 8px;
                    color: #BBB; font-size: 10px; font-weight: bold; }
                QPushButton:hover { background: rgba(0,191,255,0.2); color: #FFF; }
            """)
            btn.clicked.connect(lambda _=False, f=f: self._set_filter(f))
            chips.addWidget(btn)
        chips.addStretch()
        layout.addLayout(chips)

        # Scrollable stream
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: 1px solid rgba(255,255,255,0.08);
                border-radius: 12px; }
        """)
        self._stream_box = QWidget()
        self._stream_lay = QVBoxLayout(self._stream_box)
        self._stream_lay.setContentsMargins(8, 8, 8, 8)
        self._stream_lay.setSpacing(4)
        self._stream_lay.addStretch()
        self._scroll.setWidget(self._stream_box)
        layout.addWidget(self._scroll, 1)

        # Replay bar
        replay = QFrame()
        replay.setStyleSheet("""
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.1); border-radius: 12px;
        """)
        r_lay = QHBoxLayout(replay)
        r_lay.setContentsMargins(12, 8, 12, 8)
        r_lay.setSpacing(10)
        r_lay.addWidget(QLabel("▶ REPLAY"))

        self._btn_play = QPushButton("⏸ PAUSE" if self._replay_playing else "▶ PLAY")
        self._btn_play.setFixedSize(96, 30)
        self._btn_play.setStyleSheet("""
            QPushButton { background: rgba(0,191,255,0.15);
                border: 1px solid rgba(0,191,255,0.4); border-radius: 8px;
                color: #80D8FF; font-size: 11px; font-weight: bold; }
            QPushButton:hover { background: rgba(0,191,255,0.28); }
        """)
        self._btn_play.clicked.connect(self._toggle_replay)
        r_lay.addWidget(self._btn_play)

        self._btn_speed = QPushButton(f"{self._replay_speed:.2g}×")
        self._btn_speed.setFixedSize(64, 30)
        self._btn_speed.setStyleSheet("""
            QPushButton { background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.15); border-radius: 8px;
                color: #CCC; font-size: 11px; font-weight: bold; }
            QPushButton:hover { background: rgba(255,255,255,0.12); }
        """)
        self._btn_speed.clicked.connect(self._cycle_speed)
        r_lay.addWidget(self._btn_speed)

        self._progress = QProgressBar()
        self._progress.setRange(0, 1000)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(10)
        self._progress.setStyleSheet("""
            QProgressBar { background: rgba(255,255,255,0.06);
                border: none; border-radius: 5px; }
            QProgressBar::chunk { background: #00BFFF; border-radius: 5px; }
        """)
        r_lay.addWidget(self._progress, 1)

        self._progress_lbl = QLabel("0/0")
        self._progress_lbl.setStyleSheet("font-size: 10px; color: #889;"
                                         " font-family: Monospace;")
        r_lay.addWidget(self._progress_lbl)
        layout.addWidget(replay)

    def _set_filter(self, f: str) -> None:
        self._filter = f
        self.refresh()

    # ------------------------------------------------------------- replay
    def _toggle_replay(self) -> None:
        if not self._replay_playing:
            if self._replay_idx >= len(self._history) or self._replay_idx == 0:
                self._replay_idx = 0
            self._replay_playing = True
            self._replay_anchor = time.time()
            self._replay_start = time.time()
        else:
            self._replay_playing = False
            self._btn_play.setText("▶ PLAY")
        self._update_replay_badge()
        self.refresh()

    def _cycle_speed(self) -> None:
        idx = SPEEDS.index(self._replay_speed)
        self._replay_speed = SPEEDS[(idx + 1) % len(SPEEDS)]
        self._btn_speed.setText(f"{self._replay_speed:.2g}×")
        # Anchor so speed change doesn't jump position
        if self._replay_playing and self._replay_idx > 0:
            self._replay_anchor = time.time()

    def _tick_replay(self) -> None:
        if not self._replay_playing:
            return
        if not self._history:
            self._replay_playing = False
            return
        # Advance by wall-clock elapsed * speed, split across event gaps.
        elapsed = (time.time() - self._replay_anchor) * self._replay_speed
        idx = self._replay_idx
        while idx < len(self._history) - 1:
            gap = self._history[idx + 1].timestamp - self._history[idx].timestamp
            gap = max(gap, 0.5)  # at least 0.5s wall per event so 4× stays watchable
            if elapsed >= gap:
                elapsed -= gap
                idx += 1
            else:
                break
        else:
            idx = len(self._history) - 1
        if idx != self._replay_idx:
            self._replay_idx = idx
            self.refresh()

        if self._replay_idx >= len(self._history) - 1:
            self._replay_playing = False
            self._btn_play.setText("▶ PLAY")
            self._update_replay_badge()
            self.refresh()

    def _update_replay_badge(self) -> None:
        if self._replay_playing:
            self._replay_state.setText(
                f"▶ REPLAYING · {self._replay_speed:.2g}× · "
                f"{self._replay_idx + 1}/{len(self._history)}")
        else:
            self._replay_state.setText(
                f"⏸ REPLAY READY · {self._replay_speed:.2g}×")

    # ------------------------------------------------------------- data
    def _matches(self, event: Event) -> bool:
        if self._filter == "ALL":
            return True
        for cat, keys in CATEGORY.items():
            if self._filter == cat and any(k in event.type.lower() for k in keys):
                return True
        return False

    def refresh(self) -> None:
        if not self._replay_playing:
            self._history = _seed_history(120)

        # Remove all rows (keep the trailing stretch)
        while self._stream_lay.count() > 1:
            item = self._stream_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        history = self._history
        total = len(history)
        shown = 0
        for i, event in enumerate(history):
            if not self._matches(event):
                continue
            self._stream_lay.insertWidget(
                self._stream_lay.count() - 1,
                _EventRow(event, highlight=(self._replay_playing and i == self._replay_idx)))
            shown += 1
            if shown >= 60:
                break

        if shown == 0:
            empty = QLabel("No events in this category yet…")
            empty.setStyleSheet("color: #667; font-size: 12px; padding: 12px;")
            self._stream_lay.insertWidget(0, empty)

        # Progress
        if total:
            frac = (self._replay_idx + 1) / total
            self._progress.setValue(int(frac * 1000))
            self._progress_lbl.setText(f"{min(self._replay_idx + 1, total)}/{total}")
        else:
            self._progress.setValue(0)
            self._progress_lbl.setText("0/0")
        self._update_replay_badge()

    def on_show(self) -> None:
        self.refresh()
        self._timer.start(3000)

    def on_hide(self) -> None:
        self._timer.stop()
