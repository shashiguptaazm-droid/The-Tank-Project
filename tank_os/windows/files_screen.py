"""FilesScreen — storage volumes, file browser, disk usage analyzer."""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QProgressBar, QScrollArea, QSizePolicy,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from tank_os.core.storage_manager import StorageManager, StorageVolume
from tank_os.core.event_bus import Event, EventBus

logger = logging.getLogger("tank_os.windows.files")


class _VolumeCard(QFrame):
    """A disk volume summary card."""

    def __init__(self, vol: StorageVolume, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("volumeCard")
        self.setStyleSheet("""
            #volumeCard {
                background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

        # Top row: label + mount
        top = QHBoxLayout()
        mount_lbl = QLabel(vol.mount)
        mount_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #FFF;")
        top.addWidget(mount_lbl)
        top.addStretch()
        dev_lbl = QLabel(vol.device)
        dev_lbl.setStyleSheet("font-size: 9px; color: #666;")
        top.addWidget(dev_lbl)
        layout.addLayout(top)

        # Usage bar
        pct = round(vol.used_gb / max(vol.total_gb, 0.01) * 100, 1)
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(int(pct))
        bar.setTextVisible(True)
        bar.setFormat(f"{pct:.0f}% used")
        bar.setFixedHeight(20)
        color1, color2 = ("#00C853", "#00E676") if pct < 80 else ("#FF8F00", "#FFA000") if pct < 95 else ("#D32F2F", "#F44336")
        bar.setStyleSheet(f"""
            QProgressBar {{
                background: rgba(255,255,255,0.06);
                border: none; border-radius: 10px;
                text-align: center; font-size: 10px;
                color: #FFF;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {color1}, stop:1 {color2});
                border-radius: 10px;
            }}
        """)
        layout.addWidget(bar)

        # Details
        det = QHBoxLayout()
        details = [
            f"Free: {vol.free_gb:.1f} GB",
            f"Used: {vol.used_gb:.1f} GB",
            f"Total: {vol.total_gb:.1f} GB",
        ]
        if vol.fs_type:
            details.append(f"FS: {vol.fs_type}")
        for d in details:
            lbl = QLabel(d)
            lbl.setStyleSheet("font-size: 9px; color: #777;")
            det.addWidget(lbl)
        det.addStretch()
        layout.addLayout(det)


class FilesScreen(QWidget):
    """Storage and file management screen."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._storage = StorageManager()
        self._bus = EventBus()
        self._current_dir: Path = self._storage.data_dir
        self._volume_cards: List[_VolumeCard] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("📁 Files & Storage")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF;")
        header.addWidget(title)
        header.addStretch()

        self._scan_btn = QPushButton("🔄 Rescan")
        self._scan_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 8px; padding: 5px 12px;
                font-size: 11px; color: #CCC;
            }
            QPushButton:hover { background: rgba(0,191,255,0.15); }
        """)
        self._scan_btn.clicked.connect(self._rescan)
        header.addWidget(self._scan_btn)
        layout.addLayout(header)

        # ── Storage volumes section ──
        vol_header = QLabel("💾 Storage Volumes")
        vol_header.setStyleSheet("font-size: 13px; color: #AAA; font-weight: bold;")
        layout.addWidget(vol_header)

        self._vol_layout = QVBoxLayout()
        self._vol_layout.setSpacing(6)
        layout.addLayout(self._vol_layout)

        # ── File browser ──
        file_header = QHBoxLayout()
        file_lbl = QLabel("📄 File Browser")
        file_lbl.setStyleSheet("font-size: 13px; color: #AAA; font-weight: bold;")
        file_header.addWidget(file_lbl)
        file_header.addStretch()

        self._path_lbl = QLabel(str(self._current_dir))
        self._path_lbl.setStyleSheet("font-size: 10px; color: #00BFFF;")
        file_header.addWidget(self._path_lbl)
        layout.addLayout(file_header)

        # Breadcrumb buttons
        bread = QHBoxLayout()
        bread.setSpacing(4)

        up_btn = QPushButton("⬆ Parent")
        up_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px; padding: 4px 10px;
                font-size: 10px; color: #CCC;
            }
            QPushButton:hover { background: rgba(0,191,255,0.15); }
        """)
        up_btn.clicked.connect(self._go_up)
        bread.addWidget(up_btn)

        home_btn = QPushButton("🏠 Home")
        home_btn.setStyleSheet(up_btn.styleSheet())
        home_btn.clicked.connect(lambda: self._navigate_to(Path.home()))
        bread.addWidget(home_btn)

        data_btn = QPushButton("📦 Tank Data")
        data_btn.setStyleSheet(up_btn.styleSheet())
        data_btn.clicked.connect(lambda: self._navigate_to(self._storage.data_dir))
        bread.addWidget(data_btn)

        bread.addStretch()

        self._item_count = QLabel("")
        self._item_count.setStyleSheet("font-size: 9px; color: #666;")
        bread.addWidget(self._item_count)
        layout.addLayout(bread)

        # File list
        self._file_tree = QTreeWidget()
        self._file_tree.setHeaderLabels(["Name", "Size", "Modified"])
        self._file_tree.setColumnWidth(0, 280)
        self._file_tree.setColumnWidth(1, 90)
        self._file_tree.setColumnWidth(2, 150)
        self._file_tree.setStyleSheet("""
            QTreeWidget {
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px;
                color: #CCC;
                font-size: 11px;
            }
            QTreeWidget::item {
                padding: 3px 4px;
            }
            QTreeWidget::item:hover {
                background: rgba(0,191,255,0.1);
            }
            QHeaderView::section {
                background: rgba(255,255,255,0.05);
                border: none; border-bottom: 1px solid rgba(255,255,255,0.08);
                padding: 4px 8px;
                font-size: 10px; font-weight: bold; color: #888;
            }
        """)
        self._file_tree.itemDoubleClicked.connect(self._on_item_double_click)
        layout.addWidget(self._file_tree, 1)

        # ── Disk usage breakdown ──
        usage_header = QLabel("📊 Directory Sizes (Top 10)")
        usage_header.setStyleSheet("font-size: 13px; color: #AAA; font-weight: bold; padding-top: 4px;")
        layout.addWidget(usage_header)

        disk_frame = QFrame()
        disk_frame.setObjectName("diskUsage")
        disk_frame.setStyleSheet("""
            #diskUsage {
                background: rgba(255,255,255,0.02);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 10px;
            }
        """)
        self._disk_layout = QVBoxLayout(disk_frame)
        self._disk_layout.setContentsMargins(12, 8, 12, 8)
        self._disk_layout.setSpacing(2)

        empty_usage = QLabel("  Scan to see directory sizes")
        empty_usage.setStyleSheet("font-size: 10px; color: #555; padding: 4px;")
        self._disk_layout.addWidget(empty_usage)
        layout.addWidget(disk_frame)

        # ── Init ──
        self._populate_volumes()
        self._navigate_to(self._current_dir)

    def _populate_volumes(self) -> None:
        # Clear existing cards
        while self._vol_layout.count():
            item = self._vol_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._volume_cards.clear()

        volumes = self._storage.scan()
        if not volumes:
            empty = QLabel("  No volumes detected")
            empty.setStyleSheet("font-size: 10px; color: #555;")
            self._vol_layout.addWidget(empty)
            return

        for mount, vol in sorted(volumes.items()):
            card = _VolumeCard(vol)
            self._volume_cards.append(card)
            self._vol_layout.addWidget(card)

    def _navigate_to(self, path: Path) -> None:
        self._current_dir = path.resolve()
        self._path_lbl.setText(str(self._current_dir))
        self._file_tree.clear()

        items = 0
        try:
            entries = sorted(self._current_dir.iterdir(),
                             key=lambda p: (not p.is_dir(), p.name.lower()))

            for entry in entries:
                try:
                    stat = entry.stat()
                    name = entry.name
                    size = ""
                    if entry.is_file():
                        size = self._format_size(stat.st_size)
                    mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                    icon = "📁" if entry.is_dir() else "📄"
                    if entry.is_symlink():
                        icon = "🔗"

                    item = QTreeWidgetItem([f"{icon}  {name}", size, mtime])
                    if entry.is_dir():
                        item.setToolTip(0, str(entry))
                    self._file_tree.addTopLevelItem(item)
                    items += 1
                except (PermissionError, OSError):
                    pass
        except (PermissionError, OSError):
            error_item = QTreeWidgetItem(["⚠ Permission denied", "", ""])
            self._file_tree.addTopLevelItem(error_item)
            items = 0

        self._item_count.setText(f"{items} item{'s' if items != 1 else ''}")

    def _on_item_double_click(self, item: QTreeWidgetItem, column: int) -> None:
        name = item.text(0)
        # Strip icon prefix
        pure_name = name[3:] if len(name) > 3 and name[2] == ' ' else name
        target = self._current_dir / pure_name
        if target.is_dir():
            self._navigate_to(target)

    def _go_up(self) -> None:
        parent = self._current_dir.parent
        if parent != self._current_dir:
            self._navigate_to(parent)

    def _rescan(self) -> None:
        self._populate_volumes()
        self._navigate_to(self._current_dir)
        self._scan_disk_usage()

    def _scan_disk_usage(self) -> None:
        """Show directory sizes for top-level items in current dir."""
        # Clear existing
        while self._disk_layout.count():
            item = self._disk_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        try:
            entries = sorted(self._current_dir.iterdir(),
                             key=lambda p: (not p.is_dir(), p.name.lower()))

            sizes: List[tuple[str, int, bool]] = []
            for entry in entries:
                try:
                    if entry.is_dir():
                        total = self._dir_size(entry)
                        sizes.append((entry.name, total, True))
                    elif entry.is_file():
                        sizes.append((entry.name, entry.stat().st_size, False))
                except (PermissionError, OSError):
                    pass

            sizes.sort(key=lambda x: -x[1])
            max_size = max((s[1] for s in sizes[:10]), default=1)

            for name, sz, is_dir in sizes[:10]:
                pct = sz / max(max_size, 1)
                bar_len = int(pct * 20)
                bar = "█" * bar_len + "░" * (20 - bar_len)
                icon = "📁" if is_dir else "📄"
                row = QLabel(f"  {icon} {name:<30}  {bar}  {self._format_size(sz)}")
                row.setStyleSheet("font-size: 10px; color: #AAA;")
                self._disk_layout.addWidget(row)

            if not sizes:
                empty = QLabel("  No items to analyze")
                empty.setStyleSheet("font-size: 10px; color: #555; padding: 4px;")
                self._disk_layout.addWidget(empty)

        except (PermissionError, OSError):
            err = QLabel("  ⚠ Unable to scan directory")
            err.setStyleSheet("font-size: 10px; color: #FF5252; padding: 4px;")
            self._disk_layout.addWidget(err)

    @staticmethod
    def _dir_size(path: Path) -> int:
        """Recursively compute directory size (capped for performance)."""
        total = 0
        try:
            for entry in path.iterdir():
                try:
                    if entry.is_file():
                        total += entry.stat().st_size
                    elif entry.is_dir():
                        total += FilesScreen._dir_size(entry)
                except (PermissionError, OSError):
                    pass
                if total > 500_000_000:  # cap at ~500MB for performance
                    return total
        except (PermissionError, OSError):
            pass
        return total

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

    def on_show(self) -> None:
        self._rescan()

    def on_hide(self) -> None:
        pass
