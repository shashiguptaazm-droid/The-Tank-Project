"""SettingsScreen — system settings interface with categories."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QScrollArea, QSizePolicy,
    QSlider, QSpinBox, QVBoxLayout, QWidget,
)

from tank_os.core.settings_manager import SettingsManager
from tank_os.core.theme_engine import ThemeEngine

logger = logging.getLogger("tank_os.windows.settings")


class _SettingsSection(QFrame):
    """A collapsible settings section with config controls."""

    def __init__(self, title: str, icon: str,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("settingsSection")
        self.setStyleSheet("""
            #settingsSection {
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 10px;
                margin-bottom: 4px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)

        header = QLabel(f"{icon}  {title}")
        header.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFFFFF; padding-bottom: 4px;")
        layout.addWidget(header)

        self._content = QVBoxLayout()
        self._content.setSpacing(6)
        layout.addLayout(self._content)

    def add_row(self, label: str, widget: QWidget) -> None:
        row = QHBoxLayout()
        row.setSpacing(12)
        lbl = QLabel(label)
        lbl.setStyleSheet("font-size: 11px; color: #AAAAAA;")
        lbl.setFixedWidth(140)
        row.addWidget(lbl)
        row.addWidget(widget, 1)
        self._content.addLayout(row)


class SettingsScreen(QWidget):
    """System settings organized by category."""

    CATEGORIES: List[tuple] = [
        ("Network", "📡", "network"),
        ("Audio", "🔊", "audio"),
        ("Voice", "🎤", "voice"),
        ("AI", "🤖", "ai"),
        ("Display", "🖥", "display"),
        ("Power", "🔋", "power"),
        ("Privacy", "🔒", "privacy"),
        ("Developer", "🛠", "developer"),
    ]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._settings = SettingsManager()
        self._theme = ThemeEngine()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QLabel("⚙️ Settings")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF;")
        layout.addWidget(header)

        # Scrollable settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical { background: rgba(255,255,255,0.05); width: 4px; }
            QScrollBar::handle:vertical { background: rgba(255,255,255,0.2); border-radius: 2px; }
        """)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(6)

        for icon, name, section in [
            ("📡", "Network", "network"),
            ("🔊", "Audio", "audio"),
            ("🎤", "Voice", "voice"),
            ("🤖", "AI", "ai"),
            ("🖥", "Display", "display"),
            ("🔋", "Power", "power"),
            ("🔒", "Privacy", "privacy"),
            ("🛠", "Developer", "developer"),
        ]:
            sec = _SettingsSection(name, icon)
            section_data = self._settings.get_section(section)
            self._populate_section(sec, section, section_data)
            content_layout.addWidget(sec)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        # Save button
        save_btn = QPushButton("💾 Save All Settings")
        save_btn.setStyleSheet("""
            QPushButton {
                background: #00BFFF; border: none;
                border-radius: 8px; padding: 10px 24px;
                font-size: 13px; font-weight: bold; color: white;
            }
            QPushButton:hover { background: #00D0FF; }
        """)
        save_btn.clicked.connect(self._save_all)
        layout.addWidget(save_btn)

    def _populate_section(self, sec: _SettingsSection,
                          section: str, data: Dict[str, Any]) -> None:
        for key, value in data.items():
            if isinstance(value, bool):
                cb = QCheckBox()
                cb.setChecked(value)
                cb.setStyleSheet("""
                    QCheckBox::indicator {
                        width: 18px; height: 18px; border-radius: 4px;
                        border: 2px solid #888;
                    }
                    QCheckBox::indicator:checked {
                        background: #00BFFF; border-color: #00BFFF;
                    }
                """)
                sec.add_row(key.replace("_", " ").title(), cb)
            elif isinstance(value, str) and len(value) < 30:
                edit = QLineEdit(value)
                edit.setStyleSheet("""
                    QLineEdit {
                        background: rgba(255,255,255,0.08);
                        border: 1px solid rgba(255,255,255,0.15);
                        border-radius: 6px; padding: 4px 8px;
                        font-size: 11px; color: white;
                    }
                """)
                sec.add_row(key.replace("_", " ").title(), edit)
            elif isinstance(value, (int, float)):
                spin = QSpinBox()
                if isinstance(value, float):
                    spin.setSingleStep(10)
                spin.setValue(int(value))
                spin.setRange(0, 100)
                spin.setStyleSheet("""
                    QSpinBox {
                        background: rgba(255,255,255,0.08);
                        border: 1px solid rgba(255,255,255,0.15);
                        border-radius: 6px; padding: 4px; font-size: 11px; color: white;
                    }
                """)
                sec.add_row(key.replace("_", " ").title(), spin)

    def _save_all(self) -> None:
        self._settings.save()
        logger.info("Settings saved")
