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

from tank_os.core.i18n import I18nManager
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

        # ── Language section (i18n — packs hosted on the VPS) ──
        lang_sec = _SettingsSection("🌐 Language", "🌐")
        lang_row = QHBoxLayout()
        lang_row.setSpacing(12)
        lang_lbl = QLabel("Language")
        lang_lbl.setStyleSheet("font-size: 11px; color: #AAAAAA;")
        lang_lbl.setFixedWidth(140)
        lang_row.addWidget(lang_lbl)

        self._lang_combo = QComboBox()
        self._lang_combo.setStyleSheet("""
            QComboBox {
                background: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 6px; padding: 4px 8px;
                font-size: 11px; color: white;
            }
            QComboBox QAbstractItemView {
                background: #1A1A2E; color: white; border: none;
                selection-background-color: #00BFFF;
            }
        """)
        self._lang_status = QLabel("")
        self._lang_status.setStyleSheet("font-size: 10px; color: #888;")
        lang_row.addWidget(self._lang_combo, 1)
        lang_row.addWidget(self._lang_status)
        lang_sec._content.addLayout(lang_row)

        # download/sync button
        sync_row = QHBoxLayout()
        sync_row.setSpacing(12)
        sync_row.addSpacing(152)
        sync_btn = QPushButton("⬇ Sync Language Packs (from VPS)")
        sync_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0,191,255,0.15); border: 1px solid #00BFFF;
                border-radius: 6px; padding: 5px 12px;
                font-size: 11px; color: #7FD8FF;
            }
            QPushButton:hover { background: rgba(0,191,255,0.3); }
        """)
        sync_btn.clicked.connect(self._sync_languages)
        sync_row.addWidget(sync_btn)
        sync_row.addStretch(1)
        lang_sec._content.addLayout(sync_row)
        content_layout.addWidget(lang_sec)

        self._init_language_ui()

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

    # ------------------------------------------------------------------ i18n
    def _init_language_ui(self) -> None:
        """Populate the language combo from the i18n manager + persisted choice."""
        self._i18n = I18nManager()
        self._lang_combo.clear()
        for lang in self._i18n.available():
            label = f"{lang['flag']}  {lang['native']} ({lang['code']})"
            self._lang_combo.addItem(label, lang["code"])
        # select the persisted / current language
        saved = self._settings.get("i18n.language", "en") or "en"
        idx = self._lang_combo.findData(saved)
        self._lang_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._lang_combo.currentIndexChanged.connect(self._on_language_changed)
        self._refresh_lang_status()

    def _on_language_changed(self) -> None:
        code = self._lang_combo.currentData() or "en"
        self._i18n.set_language(code)
        self._settings.set("i18n.language", code)
        self._refresh_lang_status()
        logger.info("Language switched to %s", code)
        try:
            from tank_os.core.event_bus import EventBus, Event  # noqa: PLC0415
            EventBus().emit(Event("language_changed", {"code": code},
                                  source="settings"))
        except Exception:  # noqa: BLE001
            pass

    def _sync_languages(self) -> None:
        self._lang_status.setText("syncing…")
        self._lang_status.setStyleSheet("font-size: 10px; color: #FFD700;")
        try:
            result = self._i18n.sync()
            ok = sum(1 for v in result.values() if v)
            total = len(result)
            self._lang_status.setText(f"✓ {ok}/{total} packs (VPS)")
            self._lang_status.setStyleSheet("font-size: 10px; color: #7FD8FF;")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Language sync failed: %s", exc)
            self._lang_status.setText("✗ sync failed")
            self._lang_status.setStyleSheet("font-size: 10px; color: #FF5252;")
        # re-apply translations to the visible tree
        try:
            from tank_os.core.i18n import translate_widget_tree  # noqa: PLC0415
            translate_widget_tree(self)
        except Exception:  # noqa: BLE001
            pass

    def _refresh_lang_status(self) -> None:
        st = self._i18n.status()
        cached = len(st["cached"])
        self._lang_status.setText(f"{cached} cached · packs on VPS")
        self._lang_status.setStyleSheet("font-size: 10px; color: #888;")

    def _save_all(self) -> None:
        self._settings.save()
        logger.info("Settings saved")
