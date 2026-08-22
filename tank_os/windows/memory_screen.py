"""MemoryScreen — memory browser with search, timeline, and categories."""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from tank_os.core.memory_manager import MemoryManager

logger = logging.getLogger("tank_os.windows.memory")


class MemoryScreen(QWidget):
    """Browse and search robot memories and conversations."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._memory = MemoryManager()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Left: Memory list
        left = QVBoxLayout()
        left.setSpacing(8)

        header = QLabel("🧠 Memory Explorer")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF;")
        left.addWidget(header)

        search_layout = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search memories...")
        self._search.setStyleSheet("""
            QLineEdit {
                background: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 8px; padding: 6px 12px;
                font-size: 12px; color: white;
            }
        """)
        self._search.returnPressed.connect(self._do_search)
        search_layout.addWidget(self._search, 1)

        search_btn = QPushButton("🔍")
        search_btn.setFixedSize(32, 32)
        search_btn.setStyleSheet("""
            QPushButton {
                background: #00BFFF; border: none;
                border-radius: 16px; font-size: 14px;
            }
        """)
        search_btn.clicked.connect(self._do_search)
        search_layout.addWidget(search_btn)
        left.addLayout(search_layout)

        self._list = QListWidget()
        self._list.setStyleSheet("""
            QListWidget {
                background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 8px; color: white;
                font-size: 11px;
            }
            QListWidget::item {
                padding: 8px; border-bottom: 1px solid rgba(255,255,255,0.05);
            }
            QListWidget::item:hover { background: rgba(0,191,255,0.1); }
        """)
        left.addWidget(self._list, 1)
        layout.addLayout(left, 2)

        # Right: Memory stats + controls
        right = QFrame()
        right.setObjectName("memPanel")
        right.setStyleSheet("""
            #memPanel {
                background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px; padding: 8px;
            }
        """)
        right_layout = QVBoxLayout(right)
        right_layout.setSpacing(8)

        right_layout.addWidget(QLabel("📊 Memory Stats"))
        self._stats_label = QLabel("Loading...")
        self._stats_label.setStyleSheet("font-size: 12px; color: #AAAAAA;")
        right_layout.addWidget(self._stats_label)

        right_layout.addWidget(QLabel("📂 Types"))
        self._types_label = QLabel("")
        self._types_label.setStyleSheet("font-size: 11px; color: #888;")
        right_layout.addWidget(self._types_label)

        right_layout.addStretch()

        actions = [
            ("🔄 Refresh", self._refresh_list),
            ("📝 Store Test", self._store_test),
            ("🗑 Clear", self._clear_memory),
        ]
        for text, callback in actions:
            btn = QPushButton(text)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255,255,255,0.08);
                    border: 1px solid rgba(255,255,255,0.15);
                    border-radius: 6px; padding: 6px 12px;
                    font-size: 11px; color: white; text-align: left;
                }
                QPushButton:hover { background: rgba(0,191,255,0.2); }
            """)
            btn.clicked.connect(callback)
            right_layout.addWidget(btn)

        layout.addWidget(right, 1)

        self._refresh_list()

    def _refresh_list(self) -> None:
        self._list.clear()
        entries = self._memory.recall(limit=50)
        for e in entries:
            from datetime import datetime
            ts = datetime.fromtimestamp(e.ts).strftime("%H:%M") if e.ts else "??"
            icon = {"episodic": "💬", "semantic": "📚", "procedural": "⚙️"}.get(e.memory_type, "📝")
            text = f"[{ts}] {icon} {e.content[:80]}{'...' if len(e.content) > 80 else ''}"
            item = QListWidgetItem(text)
            self._list.addItem(item)

        stats = self._memory.types
        self._stats_label.setText(f"Total: {self._memory.count} memories")
        types_str = "\n".join(f"  • {k}: {v}" for k, v in stats.items())
        self._types_label.setText(types_str)

    def _do_search(self) -> None:
        query = self._search.text().strip()
        if query:
            entries = self._memory.recall(query, limit=30)
        else:
            entries = self._memory.recall(limit=50)
        self._list.clear()
        for e in entries:
            icon = {"episodic": "💬", "semantic": "📚", "procedural": "⚙️"}.get(e.memory_type, "📝")
            text = f"{icon} {e.content[:100]}{'...' if len(e.content) > 100 else ''}"
            self._list.addItem(QListWidgetItem(text))

    def _store_test(self) -> None:
        import time
        self._memory.store(f"Test memory at {time.strftime('%H:%M:%S')}",
                           source="memory_screen")
        self._refresh_list()

    def _clear_memory(self) -> None:
        self._memory.clear()
        self._refresh_list()
