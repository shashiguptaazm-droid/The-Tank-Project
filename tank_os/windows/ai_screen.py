"""AIScreen — live AI engine dashboard with visual status for all 5 engines.

Shows real-time status of:
- Knowledge Graph: entities, relationships, entity type distribution
- Curiosity Engine: explorations, gaps, discoveries, activity status
- Continuous Learning: patterns, preferences, insights, cycles
- Learning Scheduler: running state, budget, task queue, next task
- Experience Engine: total experiences, today's count, success rate

Auto-refreshes every 5 seconds with a QTimer.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

logger = logging.getLogger("tank_os.windows.ai")


# ── Helper widgets ─────────────────────────────────────────────────────

class _EngineCard(QFrame):
    """A card widget displaying one AI engine's status."""

    def __init__(self, title: str, icon: str, accent: str,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._accent = accent
        self.setObjectName("aiCard")
        self.setStyleSheet(f"""
            #aiCard {{
                background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px; padding: 0px;
            }}
            #aiCard:hover {{
                border: 1px solid {accent}40;
                background: rgba(255,255,255,0.06);
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Header row: icon + title + status badge
        header = QHBoxLayout()
        header.setSpacing(6)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 18px;")
        header.addWidget(icon_lbl)

        self._title = QLabel(title)
        self._title.setStyleSheet("font-size: 13px; font-weight: bold; color: #DDD;")
        header.addWidget(self._title)

        header.addStretch()

        self._badge = QLabel("—")
        self._badge.setStyleSheet(f"""
            font-size: 10px; font-weight: bold; color: {accent};
            background: {accent}18; border-radius: 8px;
            padding: 2px 8px;
        """)
        header.addWidget(self._badge)

        layout.addLayout(header)

        # Separator
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {accent}30;")
        layout.addWidget(sep)

        # Body — stats lines
        self._body = QVBoxLayout()
        self._body.setSpacing(3)
        layout.addLayout(self._body)

        # Stat rows will be added by subclass or populate()
        self._stat_labels: Dict[str, QLabel] = {}

    def add_stat(self, key: str, label: str, icon: str = "·") -> QLabel:
        """Add a stat row to the card. Returns the value label for updates."""
        row = QHBoxLayout()
        row.setSpacing(6)
        row.setContentsMargins(0, 0, 0, 0)

        icon_lbl = QLabel(icon)
        icon_lbl.setFixedWidth(16)
        icon_lbl.setStyleSheet("font-size: 10px; color: #666;")
        row.addWidget(icon_lbl)

        name = QLabel(label)
        name.setStyleSheet("font-size: 11px; color: #999;")
        name.setFixedWidth(80)
        row.addWidget(name)

        value = QLabel("—")
        value.setStyleSheet("font-size: 11px; color: #CCC; font-weight: bold;")
        value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row.addWidget(value, 1)

        self._body.addLayout(row)
        self._stat_labels[key] = value
        return value

    def add_bar(self, key: str, label: str, icon: str = "·",
                color: str = "") -> QLabel:
        """Add a stat row with a progress bar."""
        bar_color = color or self._accent
        row = QHBoxLayout()
        row.setSpacing(6)

        icon_lbl = QLabel(icon)
        icon_lbl.setFixedWidth(16)
        icon_lbl.setStyleSheet("font-size: 10px; color: #666;")
        row.addWidget(icon_lbl)

        name = QLabel(label)
        name.setStyleSheet("font-size: 11px; color: #999;")
        name.setFixedWidth(80)
        row.addWidget(name)

        bar = QProgressBar()
        bar.setFixedHeight(8)
        bar.setTextVisible(False)
        bar.setRange(0, 100)
        bar.setStyleSheet(f"""
            QProgressBar {{
                background: rgba(255,255,255,0.08);
                border: none; border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background: {bar_color};
                border-radius: 4px;
            }}
        """)
        row.addWidget(bar, 1)

        value = QLabel("—")
        value.setFixedWidth(40)
        value.setAlignment(Qt.AlignRight)
        value.setStyleSheet("font-size: 10px; color: #AAA;")
        row.addWidget(value)

        self._body.addLayout(row)
        self._stat_labels[key] = bar
        self._stat_labels[f"{key}_val"] = value
        return value

    def set_stat(self, key: str, text: str) -> None:
        """Update a stat value by key."""
        if key in self._stat_labels:
            self._stat_labels[key].setText(text)

    def set_bar(self, key: str, pct: float, text: str = "") -> None:
        """Update a progress bar by key."""
        if key in self._stat_labels:
            bar = self._stat_labels[key]
            if isinstance(bar, QProgressBar):
                bar.setValue(min(100, max(0, int(pct))))
        val_key = f"{key}_val"
        if val_key in self._stat_labels and text:
            self._stat_labels[val_key].setText(text)

    def set_badge(self, text: str) -> None:
        self._badge.setText(text)


class _KnowledgeCard(_EngineCard):
    """Knowledge Graph status card."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("Knowledge Graph", "📊", "#00E676", parent)
        self.add_stat("entities", "Entities", "🔹")
        self.add_stat("relations", "Relations", "🔗")
        self.add_stat("strength", "Avg Strength", "📈")
        self.add_stat("communities", "Communities", "🏘")
        self.add_stat("person", "People", "👤")
        self.add_stat("place", "Places", "📍")
        self.add_stat("device", "Devices", "📡")
        self.add_stat("object", "Objects", "📦")

    def refresh(self) -> None:
        try:
            from tank_os.ai.knowledge_graph import KnowledgeGraph
            s = KnowledgeGraph().get_stats()
            self.set_stat("entities", str(s["total_entities"]))
            self.set_stat("relations", str(s["total_relationships"]))
            self.set_stat("strength", f"{s['average_strength']:.3f}")
            self.set_stat("communities", str(s["communities"]))
            by_type = s.get("by_type", {})
            self.set_stat("person", str(by_type.get("person", 0)))
            self.set_stat("place", str(by_type.get("place", 0)))
            self.set_stat("device", str(by_type.get("device", 0)))
            self.set_stat("object", str(by_type.get("object", 0)))
            self.set_badge(f"{s['total_entities']} entities")
        except Exception as e:
            logger.debug("Knowledge refresh: %s", e)


class _CuriosityCard(_EngineCard):
    """Curiosity Engine status card."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("Curiosity Engine", "🔍", "#FF6B35", parent)
        self.add_stat("explorations", "Explorations", "🔎")
        self.add_stat("successful", "Successful", "✅")
        self.add_stat("open_gaps", "Open Gaps", "📋")
        self.add_stat("filled_gaps", "Filled Gaps", "✅")
        self.add_stat("discoveries", "Discoveries", "💡")
        self.add_bar("tested_pct", "Tested %", "📊", "#FF6B35")

    def refresh(self) -> None:
        try:
            from tank_os.ai.curiosity_engine import CuriosityEngine
            ce = CuriosityEngine()
            s = ce.get_stats()
            self.set_stat("explorations", str(s["total_explorations"]))
            self.set_stat("successful", str(s["successful"]))
            gaps = s.get("knowledge_gaps", {})
            self.set_stat("open_gaps", str(gaps.get("open", 0)))
            self.set_stat("filled_gaps", str(gaps.get("filled", 0)))
            self.set_stat("discoveries", str(s["discoveries"]["total"]))
            tested = s["discoveries"]["tested"]
            total = s["discoveries"]["total"]
            pct = (tested / max(total, 1)) * 100
            self.set_bar("tested_pct", pct, f"{pct:.0f}%")
            status = "🔍 exploring" if s.get("auto_mode") else "💤 idle"
            self.set_badge(status)
        except Exception as e:
            logger.debug("Curiosity refresh: %s", e)


class _LearningCard(_EngineCard):
    """Continuous Learning Engine status card."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("Learning Engine", "📈", "#00BFFF", parent)
        self.add_stat("patterns", "Patterns", "📐")
        self.add_stat("preferences", "Preferences", "⭐")
        self.add_stat("insights", "Insights", "💡")
        self.add_stat("cycles", "Cycles", "🔄")

    def refresh(self) -> None:
        try:
            from tank_os.ai.continuous_learning import ContinuousLearningEngine
            s = ContinuousLearningEngine().get_summary()
            self.set_stat("patterns", str(s["patterns"]))
            self.set_stat("preferences", str(s["preferences"]))
            self.set_stat("insights", str(s["insights"]))
            self.set_stat("cycles", str(s["cycles"]))
            self.set_badge(f"{s['cycles']} cycles")
        except Exception as e:
            logger.debug("Learning refresh: %s", e)


class _SchedulerCard(_EngineCard):
    """Learning Scheduler status card."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("Scheduler", "⏰", "#FFD600", parent)
        self.add_stat("tasks", "Tasks", "📋")
        self.add_stat("enabled", "Enabled", "🟢")
        self.add_stat("completed", "Completed", "✅")
        self.add_stat("failed", "Failed", "❌")
        self.add_bar("budget", "Budget", "⏱", "#FFD600")

    def refresh(self) -> None:
        try:
            from tank_os.ai.learning_scheduler import LearningScheduler
            ls = LearningScheduler()
            s = ls.get_status()
            b = s.get("budget", {})
            self.set_stat("tasks", str(s["scheduled_tasks"]))
            self.set_stat("enabled", str(s["enabled_tasks"]))
            self.set_stat("completed", str(b.get("tasks_completed", 0)))
            self.set_stat("failed", str(b.get("tasks_failed", 0)))
            used = b.get("used_today_h", 0)
            max_h = b.get("max_daily_h", 4)
            pct = (used / max(max_h, 1)) * 100
            self.set_bar("budget", pct, f"{used:.1f}h")
            running = "🟢 running" if s["running"] else "🔴 stopped"
            self.set_badge(running)
        except Exception as e:
            logger.debug("Scheduler refresh: %s", e)


class _ExperienceCard(_EngineCard):
    """Experience Engine status card."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("Experience Engine", "📝", "#E040FB", parent)
        self.add_stat("total", "Total", "📦")
        self.add_stat("today", "Today", "📅")
        self.add_bar("success_rate", "Success", "📊", "#00E676")

    def refresh(self) -> None:
        try:
            from tank_os.ai.experience_engine import ExperienceEngine
            s = ExperienceEngine().get_summary()
            self.set_stat("total", str(s["total_experiences"]))
            self.set_stat("today", str(s["today_count"]))
            pct = s["success_rate"] * 100
            self.set_bar("success_rate", pct, f"{s['success_rate']:.0%}")
            self.set_badge(f"{s['today_count']} today")
        except Exception as e:
            logger.debug("Experience refresh: %s", e)


# ── The AI Screen ──────────────────────────────────────────────────────

class AIScreen(QWidget):
    """Full AI engine dashboard with 5 live-updating status cards.

    Layout::

        ┌─────────────────────────────────────────┐
        │  🧠  AI Engine Dashboard       [🔄]    │
        ├──────────────┬──────────────┬───────────┤
        │  📊 Knowledge│  🔍 Curiosity│  📈 Learn  │
        │  Graph       │  Engine      │  Engine    │
        ├──────────────┼──────────────┼───────────┤
        │  ⏰ Scheduler│  📝 Experienc│           │
        │              │  Engine      │           │
        └──────────────┴──────────────┴───────────┘
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("aiScreen")

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # ── Header ──
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        title = QLabel("🧠  AI Engine Dashboard")
        title.setStyleSheet("""
            font-size: 20px; font-weight: bold;
            color: #FFFFFF; padding: 2px 0px;
        """)
        header_layout.addWidget(title)

        header_layout.addStretch()

        refresh_btn = QPushButton("🔄 Refresh Now")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0,191,255,0.15);
                border: 1px solid rgba(0,191,255,0.3);
                border-radius: 8px; padding: 8px 18px;
                font-size: 12px; color: #00BFFF; font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(0,191,255,0.25);
                border: 1px solid rgba(0,191,255,0.5);
            }
            QPushButton:pressed {
                background: rgba(0,191,255,0.35);
            }
        """)
        refresh_btn.clicked.connect(self._refresh_all)
        header_layout.addWidget(refresh_btn)

        self._timer_label = QLabel("")
        self._timer_label.setStyleSheet("font-size: 10px; color: #666;")
        header_layout.addWidget(self._timer_label)

        main_layout.addLayout(header_layout)

        # ── Separator ──
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(255,255,255,0.06);")
        main_layout.addWidget(sep)

        # ── Cards Grid (3 columns on wide screens, responsive) ──
        grid = QGridLayout()
        grid.setSpacing(10)

        # Row 0: Knowledge Graph, Curiosity, Learning
        self._knowledge = _KnowledgeCard()
        grid.addWidget(self._knowledge, 0, 0)

        self._curiosity = _CuriosityCard()
        grid.addWidget(self._curiosity, 0, 1)

        self._learning = _LearningCard()
        grid.addWidget(self._learning, 0, 2)

        # Row 1: Scheduler, Experience (third column empty / spacer)
        self._scheduler = _SchedulerCard()
        grid.addWidget(self._scheduler, 1, 0)

        self._experience = _ExperienceCard()
        grid.addWidget(self._experience, 1, 1)

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        grid.addWidget(spacer, 1, 2)

        main_layout.addLayout(grid, 1)

        # ── Auto-refresh timer ──
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_all)
        self._timer.start(5000)  # Every 5 seconds

        # ── Initial refresh ──
        self._refresh_all()
        self._update_timer_label()

    def _refresh_all(self) -> None:
        """Refresh all engine cards."""
        self._knowledge.refresh()
        self._curiosity.refresh()
        self._learning.refresh()
        self._scheduler.refresh()
        self._experience.refresh()

    def _update_timer_label(self) -> None:
        """Update the auto-refresh indicator."""
        if self._timer.isActive():
            interval = self._timer.interval() // 1000
            self._timer_label.setText(f"auto-refresh every {interval}s")
        else:
            self._timer_label.setText("auto-refresh paused")

    def on_enter(self) -> None:
        """Called when screen becomes active — resume auto-refresh."""
        if not self._timer.isActive():
            self._timer.start(5000)
            self._update_timer_label()
        self._refresh_all()

    def on_leave(self) -> None:
        """Called when navigating away — pause auto-refresh."""
        self._timer.stop()
        self._update_timer_label()
