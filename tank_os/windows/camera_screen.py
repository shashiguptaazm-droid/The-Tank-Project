"""CameraScreen — full camera viewfinder with detection overlay."""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QVBoxLayout, QWidget,
)

from tank_os.widgets.camera_widget import CameraWidget

logger = logging.getLogger("tank_os.windows.camera")


class CameraScreen(QWidget):
    """Full camera viewfinder screen with controls."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header
        header = QLabel("📷 Camera & Vision")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF;")
        layout.addWidget(header)

        # Camera feed
        self._camera = CameraWidget(show_detections=True)
        self._camera.setMinimumSize(480, 320)
        layout.addWidget(self._camera, 1)

        # Controls
        controls = QHBoxLayout()
        controls.setSpacing(10)

        self._start_btn = QPushButton("▶ Start Camera")
        self._start_btn.setStyleSheet("""
            QPushButton {
                background: #00BFFF; border: none; border-radius: 8px;
                padding: 8px 20px; font-size: 13px; font-weight: bold;
                color: white;
            }
            QPushButton:hover { background: #00D0FF; }
        """)
        self._start_btn.clicked.connect(self._camera.start)
        controls.addWidget(self._start_btn)

        self._stop_btn = QPushButton("■ Stop")
        self._stop_btn.setStyleSheet("""
            QPushButton {
                background: #FF5252; border: none; border-radius: 8px;
                padding: 8px 20px; font-size: 13px; font-weight: bold;
                color: white;
            }
            QPushButton:hover { background: #FF7070; }
        """)
        self._stop_btn.clicked.connect(self._camera.stop)
        controls.addWidget(self._stop_btn)

        self._detect_btn = QPushButton("🔍 Show Detections")
        self._detect_btn.setCheckable(True)
        self._detect_btn.setChecked(True)
        self._detect_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.1);
                border: 1px solid rgba(255,255,255,0.2);
                border-radius: 8px; padding: 8px 20px;
                font-size: 13px; color: white;
            }
            QPushButton:hover { background: rgba(255,255,255,0.2); }
            QPushButton:checked { background: rgba(0,230,118,0.3);
                border: 1px solid rgba(0,230,118,0.5); }
        """)
        self._detect_btn.toggled.connect(self._camera.set_show_detections)
        controls.addWidget(self._detect_btn)

        controls.addStretch()
        layout.addLayout(controls)

        # Detection status
        self._status_label = QLabel("Camera offline")
        self._status_label.setStyleSheet("font-size: 11px; color: #888; padding: 4px;")
        layout.addWidget(self._status_label)

        # info
        info = QLabel("Supports: YOLOv8 object detection, face recognition, AprilTag tracking")
        info.setStyleSheet("font-size: 10px; color: #666; padding: 2px;")
        layout.addWidget(info)
