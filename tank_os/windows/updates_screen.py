"""UpdatesScreen — software update management with check/apply/rollback."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox, QFrame, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QSizePolicy,
    QVBoxLayout, QWidget,
)

from tank_os.core.update_manager import UpdateManager, UpdateInfo
from tank_os.core.event_bus import Event, EventBus
from tank_os.core.notification_manager import NotificationManager

logger = logging.getLogger("tank_os.windows.updates")


class _UpdateCard(QFrame):
    """Single update entry in the list."""

    def __init__(self, info: UpdateInfo, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._info = info
        self.setObjectName("updateCard")
        self.setStyleSheet("""
            #updateCard {
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px;
            }
            #updateCard:hover {
                background: rgba(0,191,255,0.06);
                border-color: rgba(0,191,255,0.2);
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        # Checkbox
        self._check = QCheckBox()
        self._check.setStyleSheet("""
            QCheckBox::indicator {
                width: 18px; height: 18px; border-radius: 4px;
                border: 2px solid #888;
            }
            QCheckBox::indicator:checked {
                background: #00BFFF; border-color: #00BFFF;
            }
        """)
        layout.addWidget(self._check)

        # Info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        source_lbl = QLabel(f"{info.source.upper()}  ·  {info.summary or 'Update available'}")
        source_lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #EEE;")
        info_layout.addWidget(source_lbl)

        version_str = f"{info.version_from} → {info.version_to}"
        if info.requires_reboot:
            version_str += "  (requires reboot)"
        version_lbl = QLabel(version_str)
        version_lbl.setStyleSheet("font-size: 10px; color: #888;")
        info_layout.addWidget(version_lbl)

        layout.addLayout(info_layout, 1)

        if info.size_bytes > 0:
            size_mb = info.size_bytes / (1024 * 1024)
            size_lbl = QLabel(f"{size_mb:.1f} MB")
            size_lbl.setStyleSheet("font-size: 10px; color: #666;")
            layout.addWidget(size_lbl)

    @property
    def is_checked(self) -> bool:
        return self._check.isChecked()

    @property
    def info(self) -> UpdateInfo:
        return self._info


class _HistoryRow(QFrame):
    """One row in the update history table."""

    def __init__(self, entry: Dict[str, Any], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("updateHistoryRow")
        self.setStyleSheet("#updateHistoryRow { border-bottom: 1px solid rgba(255,255,255,0.04); }")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)

        status = "✅" if entry.get("ok") else "❌"
        source = entry.get("source", "?")
        version = f"{entry.get('version_from','?')} → {entry.get('version_to','?')}"
        dry = " [dry]" if entry.get("dry_run") else ""

        text = QLabel(f"{status}  {source}: {version}{dry}")
        text.setStyleSheet("font-size: 10px; color: #AAA;")
        layout.addWidget(text, 1)

        ts = entry.get("ts", 0)
        if ts:
            time_str = time.strftime("%m-%d %H:%M", time.localtime(ts))
            time_lbl = QLabel(time_str)
            time_lbl.setStyleSheet("font-size: 9px; color: #666;")
            layout.addWidget(time_lbl)


class UpdatesScreen(QWidget):
    """System updates screen — check, select, apply, and view history."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._update_mgr = UpdateManager()
        self._bus = EventBus()
        self._update_cards: List[_UpdateCard] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("🔄 Updates")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF;")
        header.addWidget(title)
        header.addStretch()

        self._channel_badge = QLabel("stable")
        self._channel_badge.setStyleSheet("""
            background: rgba(0,191,255,0.12);
            color: #00BFFF; border: 1px solid rgba(0,191,255,0.25);
            border-radius: 10px; padding: 3px 10px;
            font-size: 10px; font-weight: bold;
        """)
        header.addWidget(self._channel_badge)
        layout.addLayout(header)

        # ── Status bar ──
        status_frame = QFrame()
        status_frame.setObjectName("updateStatus")
        status_frame.setStyleSheet("""
            #updateStatus {
                background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px;
            }
        """)
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(14, 8, 14, 8)
        status_layout.setSpacing(16)

        self._status_icon = QLabel("✓")
        self._status_icon.setStyleSheet("font-size: 20px; color: #00E676; font-weight: bold;")
        status_layout.addWidget(self._status_icon)

        self._status_text = QLabel("System is up to date")
        self._status_text.setStyleSheet("font-size: 12px; color: #CCC;")
        status_layout.addWidget(self._status_text, 1)

        self._check_btn = QPushButton("🔍 Check for Updates")
        self._check_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0,191,255,0.15);
                border: 1px solid rgba(0,191,255,0.3);
                border-radius: 8px; padding: 6px 14px;
                font-size: 11px; color: #00BFFF; font-weight: bold;
            }
            QPushButton:hover { background: rgba(0,191,255,0.25); }
        """)
        self._check_btn.clicked.connect(self._check_updates)
        status_layout.addWidget(self._check_btn)

        self._last_check = QLabel("Last: never")
        self._last_check.setStyleSheet("font-size: 10px; color: #666;")
        status_layout.addWidget(self._last_check)

        layout.addWidget(status_frame)

        # ── Available updates list ──
        list_header = QLabel("Available Updates")
        list_header.setStyleSheet("font-size: 13px; color: #AAA; font-weight: bold;")
        layout.addWidget(list_header)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical { background: rgba(255,255,255,0.03); width: 4px; }
            QScrollBar::handle:vertical { background: rgba(255,255,255,0.15); border-radius: 2px; }
        """)

        self._list_content = QWidget()
        self._list_layout = QVBoxLayout(self._list_content)
        self._list_layout.setSpacing(6)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.addStretch()

        self._scroll.setWidget(self._list_content)
        layout.addWidget(self._scroll, 1)

        # Select all bar
        select_bar = QHBoxLayout()
        self._select_all_cb = QCheckBox("Select All")
        self._select_all_cb.setStyleSheet("""
            QCheckBox { font-size: 11px; color: #AAA; }
            QCheckBox::indicator {
                width: 16px; height: 16px; border-radius: 3px;
                border: 2px solid #888;
            }
            QCheckBox::indicator:checked {
                background: #00BFFF; border-color: #00BFFF;
            }
        """)
        self._select_all_cb.stateChanged.connect(self._on_select_all)
        select_bar.addWidget(self._select_all_cb)
        select_bar.addStretch()

        self._apply_btn = QPushButton("⬇ Apply Selected")
        self._apply_btn.setStyleSheet("""
            QPushButton {
                background: #00C853; border: none;
                border-radius: 8px; padding: 8px 18px;
                font-size: 12px; font-weight: bold; color: white;
            }
            QPushButton:hover { background: #00E676; }
            QPushButton:disabled { background: #333; color: #666; }
        """)
        self._apply_btn.setEnabled(False)
        self._apply_btn.clicked.connect(self._apply_selected)
        select_bar.addWidget(self._apply_btn)
        layout.addLayout(select_bar)

        # ── History section ──
        hist_header = QLabel("Update History")
        hist_header.setStyleSheet("font-size: 13px; color: #AAA; font-weight: bold; padding-top: 4px;")
        layout.addWidget(hist_header)

        hist_frame = QFrame()
        hist_frame.setObjectName("updateHistory")
        hist_frame.setStyleSheet("""
            #updateHistory {
                background: rgba(255,255,255,0.02);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 10px;
            }
        """)
        self._hist_layout = QVBoxLayout(hist_frame)
        self._hist_layout.setContentsMargins(8, 6, 8, 6)
        self._hist_layout.setSpacing(0)
        layout.addWidget(hist_frame)

        # ── Event subscriptions ──
        self._bus.on("update_check_completed", self._on_check_done)
        self._bus.on("update_applying", self._on_applying)
        self._bus.on("update_completed", self._on_apply_done)
        self._bus.on("update_failed", self._on_apply_fail)

        # Init
        self._refresh()

    def _check_updates(self) -> None:
        self._status_text.setText("Checking for updates...")
        self._status_icon.setText("⏳")
        self._check_btn.setEnabled(False)
        self._check_btn.setText("Checking...")
        # Run in background via timer so UI stays responsive
        QTimer.singleShot(100, self._do_check)

    def _do_check(self) -> None:
        try:
            updates = self._update_mgr.check()
            self._populate_list(updates)
            if updates:
                self._status_icon.setText("⚠")
                self._status_text.setText(f"{len(updates)} update(s) available")
            else:
                self._status_icon.setText("✓")
                self._status_text.setText("System is up to date")
                NotificationManager().info("Updates", "System is up to date")
        except Exception as exc:
            self._status_icon.setText("✗")
            self._status_text.setText(f"Check failed: {exc}")
        finally:
            self._check_btn.setEnabled(True)
            self._check_btn.setText("🔍 Check for Updates")
            self._update_last_check()

    def _populate_list(self, updates: List[UpdateInfo]) -> None:
        # Clear existing cards
        for card in self._update_cards:
            self._list_layout.removeWidget(card)
            card.deleteLater()
        self._update_cards.clear()

        for u in updates:
            card = _UpdateCard(u)
            self._update_cards.append(card)
            # Insert before stretch
            self._list_layout.insertWidget(self._list_layout.count() - 1, card)

        self._select_all_cb.setChecked(False)
        self._apply_btn.setEnabled(len(self._update_cards) > 0)
        self._refresh_history()

    def _on_select_all(self, state: int) -> None:
        checked = state == Qt.Checked.value  if hasattr(Qt.Checked, 'value') else state == Qt.Checked
        for card in self._update_cards:
            card._check.setChecked(checked)

    def _apply_selected(self) -> None:
        selected = [card for card in self._update_cards if card.is_checked]
        if not selected:
            NotificationManager().warning("Updates", "No updates selected")
            return

        self._apply_btn.setEnabled(False)
        self._apply_btn.setText("Applying...")
        self._status_text.setText(f"Applying {len(selected)} update(s)...")
        successful = 0
        for card in selected:
            ok = self._update_mgr.apply(card.info.id)
            if ok:
                successful += 1
            else:
                logger.warning("Failed to apply update: %s", card.info.id)

        NotificationManager().info(
            "Updates",
            f"Applied {successful}/{len(selected)} update(s)"
        )
        self._refresh()

    def _on_check_done(self, event: Event) -> None:
        count = event.data.get("count", 0)
        if count == 0:
            self._status_icon.setText("✓")
            self._status_text.setText("System is up to date")

    def _on_applying(self, event: Event) -> None:
        self._status_text.setText(f"Applying: {event.data.get('id','?')}")

    def _on_apply_done(self, event: Event) -> None:
        self._refresh()

    def _on_apply_fail(self, event: Event) -> None:
        self._status_text.setText(f"Update failed: {event.data.get('error','?')}")
        self._refresh()

    def _refresh(self) -> None:
        self._update_mgr.available()
        self._update_last_check()
        self._refresh_history()
        self._check_btn.setEnabled(True)
        self._check_btn.setText("🔍 Check for Updates")
        self._apply_btn.setText("⬇ Apply Selected")

    def _refresh_history(self) -> None:
        # Clear existing history rows
        while self._hist_layout.count():
            item = self._hist_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        entries = self._update_mgr.history(limit=10)
        if not entries:
            empty = QLabel("  No update history yet")
            empty.setStyleSheet("font-size: 10px; color: #555; padding: 4px;")
            self._hist_layout.addWidget(empty)
        else:
            for entry in reversed(entries):
                row = _HistoryRow(entry)
                self._hist_layout.addWidget(row)

    def _update_last_check(self) -> None:
        lc = self._update_mgr.last_checked()
        if lc > 0:
            self._last_check.setText(f"Last: {time.strftime('%H:%M:%S', time.localtime(lc))}")
        else:
            self._last_check.setText("Last: never")

    def on_show(self) -> None:
        self._refresh()

    def on_hide(self) -> None:
        pass
