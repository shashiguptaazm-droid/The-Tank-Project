"""BottomDock — navigation dock at the bottom of Tank Shell."""

from __future__ import annotations

import logging
from typing import Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from tank_os.core.event_bus import Event, EventBus

logger = logging.getLogger("tank_os.widgets.dock")


class _DockButton(QPushButton):
    """A single dock button with icon, label, active highlight."""

    def __init__(self, icon: str, label: str, screen: str,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._screen = screen
        self._active = False
        self.setFixedSize(64, 56)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 4, 2, 2)
        layout.setSpacing(1)

        self._icon_label = QLabel(icon)
        self._icon_label.setAlignment(Qt.AlignCenter)
        self._icon_label.setStyleSheet("font-size: 20px;")
        layout.addWidget(self._icon_label)

        self._text_label = QLabel(label)
        self._text_label.setAlignment(Qt.AlignCenter)
        self._text_label.setStyleSheet("font-size: 9px;")
        layout.addWidget(self._text_label)

        self.setStyleSheet(self._style_normal())

    def _style_normal(self) -> str:
        return """
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.1);
            }
            QPushButton:pressed {
                background: rgba(255,255,255,0.15);
            }
        """

    def _style_active(self) -> str:
        return """
            QPushButton {
                background: rgba(0,191,255,0.2);
                border: 1px solid rgba(0,191,255,0.4);
                border-radius: 8px;
            }
            QPushButton:hover {
                background: rgba(0,191,255,0.3);
            }
        """

    def set_active(self, active: bool) -> None:
        self._active = active
        self.setStyleSheet(self._style_active() if active else self._style_normal())
        self._icon_label.setStyleSheet(
            "font-size: 20px; color: #00BFFF;" if active else "font-size: 20px;"
        )
        self._text_label.setStyleSheet(
            "font-size: 9px; color: #00BFFF; font-weight: bold;" if active
            else "font-size: 9px;"
        )

    @property
    def screen(self) -> str:
        return self._screen


class BottomDock(QFrame):
    """Bottom navigation dock with screen buttons."""

    screen_changed = Signal(str)

    DOCK_ITEMS: List[Tuple[str, str, str]] = [
        # GUI blueprint core-7 experience + key extras (≤2 clicks)
        ("🏠", "Home", "home"),
        ("🕹", "Drive", "drive"),
        ("🎯", "Mission", "mission"),
        ("🗺", "Map", "navigation"),
        ("📷", "Vision", "camera"),
        ("🧠", "AI", "brain"),
        ("🩺", "Health", "health"),
        ("🟢", "ESP32", "fleet"),
        ("🟧", "Jetson", "jetson"),
        ("🏆", "Compete", "competition"),
        ("🚨", "Events", "events"),
        ("📡", "Sensors", "sensors"),
        ("🧩", "Topology", "topology"),
        ("🧪", "Tests", "test-center"),
        ("🔋", "Power", "power-dash"),
        ("📊", "Analytics", "analytics"),
        ("🔐", "Security", "security"),
        ("📺", "TV", "tv"),
        ("💬", "Chat", "chat"),
        ("⚙️", "Settings", "settings"),
        # 200-feature GUI+AI plan
        ("🎛", "AI Cmd", "ai-command"),
        ("🚧", "Safety", "ai-safety"),
        ("👨⚖️", "Judge", "judge"),
        ("🌐", "Dist AI", "distributed-ai"),
        # Human coordination + originality
        ("👤", "Human", "human"),
        ("🌟", "Const", "constitution"),
        ("🧠", "Know Map", "knowledge-map"),
        # Tool-calling architecture
        ("🔧", "Tools", "tool-graph"),
        # TankOS proper
        ("🤖", "System", "system"),
        # Evolution
        ("🧬", "Evolve", "evolution"),
    ]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("bottomDock")
        self.setFixedHeight(72)
        self._bus = EventBus()
        self._current_screen = "home"
        self._buttons: Dict[str, _DockButton] = {}

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 4, 16, 4)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignCenter)

        for icon, label, screen in self.DOCK_ITEMS:
            btn = _DockButton(icon, label, screen)
            btn.clicked.connect(lambda _s=screen: self._on_dock_click(_s))
            self._buttons[screen] = btn
            layout.addWidget(btn)

    def _on_dock_click(self, screen: str) -> None:
        self.set_active(screen)
        self.screen_changed.emit(screen)

    def set_active(self, screen: str) -> None:
        self._current_screen = screen
        for s, btn in self._buttons.items():
            btn.set_active(s == screen)
