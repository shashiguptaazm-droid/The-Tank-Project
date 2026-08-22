"""CameraWidget — live camera feed with detection overlays."""

from __future__ import annotations

import logging
from typing import Any, Optional

from PySide6.QtCore import Qt, QTimer, QByteArray, QBuffer
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QFont
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from tank_os.core.vision_manager import VisionManager, Detection

logger = logging.getLogger("tank_os.widgets.camera")


class CameraWidget(QWidget):
    """Displays a live camera feed with optional YOLO detection overlays."""

    def __init__(self, parent: Optional[QWidget] = None,
                 show_detections: bool = True) -> None:
        super().__init__(parent)
        self._vision = VisionManager()
        self._show_detections = show_detections
        self._pixmap: Optional[QPixmap] = None
        self._detections: list[Detection] = []
        self._camera_active = False
        self.setMinimumSize(320, 240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignCenter)
        self._image_label.setStyleSheet("background: #000000; border-radius: 8px;")
        self._image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self._image_label)

        self._status_label = QLabel("📷 Camera Offline")
        self._status_label.setAlignment(Qt.AlignCenter)
        self._status_label.setStyleSheet(
            "color: #888; font-size: 14px; padding: 8px;"
        )
        self._status_label.hide()
        layout.addWidget(self._status_label)

        # Poll camera every 100ms
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.setInterval(100)

    def start(self) -> None:
        """Begin camera capture and display."""
        if not self._vision.is_camera_active:
            if self._vision.start_camera():
                self._camera_active = True
                self._status_label.hide()
                self._timer.start()
                logger.info("Camera started")
            else:
                self._status_label.setText("📷 Camera Error")
                self._status_label.show()
        else:
            self._camera_active = True
            self._timer.start()

    def stop(self) -> None:
        """Stop camera display."""
        self._timer.stop()
        self._image_label.clear()
        self._status_label.setText("📷 Camera Offline")
        self._status_label.show()

    def _refresh(self) -> None:
        if not self._camera_active:
            return
        try:
            frame = self._vision.capture_frame()
            if frame:
                img = QImage.fromData(QByteArray(frame))
                self._pixmap = QPixmap.fromImage(img)
                self._update_display()

            if self._show_detections:
                self._detections = self._vision.detections

        except Exception as exc:
            logger.debug("Camera refresh: %s", exc)

    def _update_display(self) -> None:
        if self._pixmap is None:
            return

        scaled = self._pixmap.scaled(
            self._image_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

        if self._show_detections and self._detections:
            # Paint detections onto the pixmap
            painter = QPainter(scaled)
            painter.setRenderHint(QPainter.Antialiasing)
            scale_x = scaled.width() / self._pixmap.width()
            scale_y = scaled.height() / self._pixmap.height()

            for det in self._detections:
                x = int(det.x * scale_x)
                y = int(det.y * scale_y)
                w = int(det.w * scale_x)
                h = int(det.h * scale_y)

                painter.setPen(QPen(QColor("#00FF00"), 2))
                painter.drawRect(x, y, w, h)

                painter.setFont(QFont("sans-serif", 9))
                painter.setPen(QPen(QColor("#FFFFFF")))
                painter.drawText(x + 4, y - 6, f"{det.label} {det.confidence:.2f}")
            painter.end()

        self._image_label.setPixmap(scaled)

    def set_show_detections(self, enabled: bool) -> None:
        self._show_detections = enabled

    @property
    def is_active(self) -> bool:
        return self._camera_active
