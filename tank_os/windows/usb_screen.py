"""TankOS USB Screen — stub for USB peripheral management."""
from __future__ import annotations
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout


class UsbScreen(QWidget):
    """USB device management screen (stub)."""
    def __init__(self, shell=None, parent=None):
        super().__init__(parent)
        self._shell = shell
        layout = QVBoxLayout(self)
        label = QLabel("🖥️ USB — No devices detected")
        label.setStyleSheet("color: #6b7280; font-size: 18px;")
        layout.addWidget(label)