"""AIAvatar — animated AI companion avatar widget."""

from __future__ import annotations

import logging
import math
import time
from typing import Optional

from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import (
    QBrush, QColor, QFont, QPainter,
    QPainterPath, QPen, QRadialGradient,
)
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from tank_os.core.emotion_manager import EmotionManager
from tank_os.core.event_bus import Event, EventBus

logger = logging.getLogger("tank_os.widgets.avatar")


class AIAvatar(QWidget):
    """An animated AI face/avatar that reflects the robot's emotional state."""

    # Emotion → (color, eye_shape, mouth_shape)
    EMOTION_STYLES = {
        "happy":     ("#FFD700", "wide",   "smile"),
        "excited":   ("#FF6B35", "wide",   "open"),
        "curious":   ("#00BFFF", "normal", "ooh"),
        "neutral":   ("#4FC3F7", "normal", "neutral"),
        "sad":       ("#5C6BC0", "narrow", "frown"),
        "angry":     ("#FF1744", "narrow", "scowl"),
        "sleepy":    ("#78909C", "half",   "neutral"),
        "surprised": ("#FF4081", "wide",   "open"),
        "loving":    ("#FF80AB", "wide",   "smile"),
    }

    def __init__(self, parent: Optional[QWidget] = None,
                 size: int = 120) -> None:
        super().__init__(parent)
        self._size = size
        self._base_size = size
        self.setFixedSize(size, size)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self._emotion = EmotionManager()
        self._current_emotion = "neutral"
        self._valence = 0.0
        self._arousal = 0.0
        self._intensity = 0.5
        self._pulse = 0.0
        self._blink = 0.0
        self._listening = False

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(50)  # 20 FPS

    def set_listening(self, listening: bool) -> None:
        self._listening = listening

    def _tick(self) -> None:
        self._pulse += 0.05
        self._blink = max(0.0, self._blink - 0.02)
        if self._blink <= 0 and (hash(str(time.time())) % 200) < 3:
            self._blink = 1.0
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        center_x = self._size / 2
        center_y = self._size / 2
        radius = self._size / 2 - 8

        # Get emotion data
        emo_state = self._emotion.current
        name = emo_state.get("name", "neutral")
        intensity = emo_state.get("intensity", 0.5)
        style = self.EMOTION_STYLES.get(name, self.EMOTION_STYLES["neutral"])
        base_color = QColor(style[0])

        # Pulse effect
        pulse = math.sin(self._pulse) * 0.03 * intensity
        pulse_radius = radius * (1 + pulse)

        # Background glow
        glow = QRadialGradient(center_x - 20, center_y - 20, pulse_radius * 1.5)
        glow.setColorAt(0, QColor(base_color.red(), base_color.green(),
                                  base_color.blue(), 40))
        glow.setColorAt(0.6, QColor(base_color.red(), base_color.green(),
                                    base_color.blue(), 20))
        glow.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(center_x - pulse_radius * 1.3,
                                    center_y - pulse_radius * 1.3,
                                    pulse_radius * 2.6, pulse_radius * 2.6))

        # Face circle
        painter.setBrush(QBrush(base_color.darker(150)))
        painter.setPen(QPen(base_color.lighter(120), 2))
        painter.drawEllipse(QRectF(center_x - pulse_radius,
                                    center_y - pulse_radius,
                                    pulse_radius * 2, pulse_radius * 2))

        # Eyes
        eye_spacing = radius * 0.35
        eye_y = center_y - radius * 0.15
        eye_w = radius * 0.22
        eye_h = radius * 0.28

        # Blink effect
        blink_h = eye_h * (1 if self._blink < 0.5 else 0.1)

        for side in [-1, 1]:
            ex = center_x + side * eye_spacing
            # White of eye
            painter.setBrush(QBrush(QColor("#FFFFFF")))
            painter.setPen(QPen(QColor("#333333"), 1))
            painter.drawEllipse(QRectF(ex - eye_w / 2,
                                        eye_y - blink_h / 2,
                                        eye_w, blink_h))

            # Pupil (follows listening state)
            pupil_size = eye_w * 0.5
            pupil_offset_x = math.sin(self._pulse * 0.7 + side) * 2 if self._listening else 0
            pupil_offset_y = math.cos(self._pulse * 0.5) * 1
            painter.setBrush(QBrush(QColor("#1A1A2E")))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QRectF(
                ex - pupil_size / 2 + pupil_offset_x,
                eye_y - pupil_size / 2 + pupil_offset_y,
                pupil_size, pupil_size,
            ))

            # Pupil highlight
            hl_size = pupil_size * 0.35
            painter.setBrush(QBrush(QColor("#FFFFFF")))
            painter.drawEllipse(QRectF(
                ex - pupil_size * 0.1 + pupil_offset_x,
                eye_y - pupil_size * 0.25 + pupil_offset_y,
                hl_size, hl_size,
            ))

        # Mouth
        mouth_y = center_y + radius * 0.35
        mouth_w = radius * 0.4
        mouth_style = style[2]

        painter.setPen(QPen(QColor("#FFFFFF"), 2, Qt.SolidLine, Qt.RoundCap))

        if mouth_style == "smile":
            path = QPainterPath()
            path.moveTo(center_x - mouth_w / 2, mouth_y)
            path.quadTo(center_x, mouth_y + radius * 0.15,
                        center_x + mouth_w / 2, mouth_y)
            painter.drawPath(path)
        elif mouth_style == "open":
            painter.setBrush(QBrush(QColor("#1A1A2E")))
            painter.drawEllipse(QRectF(
                center_x - mouth_w / 2, mouth_y - 6,
                mouth_w, radius * 0.18,
            ))
        elif mouth_style == "frown":
            path = QPainterPath()
            path.moveTo(center_x - mouth_w / 2, mouth_y)
            path.quadTo(center_x, mouth_y - radius * 0.12,
                        center_x + mouth_w / 2, mouth_y)
            painter.drawPath(path)
        elif mouth_style == "scowl":
            painter.setPen(QPen(QColor("#FFFFFF"), 3, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(int(center_x - mouth_w / 2), int(mouth_y),
                             int(center_x + mouth_w / 2), int(mouth_y))
        elif mouth_style == "ooh":
            painter.setBrush(QBrush(QColor("#FFFFFF")))
            painter.drawEllipse(QRectF(
                center_x - 4, mouth_y - 4, 8, 8,
            ))
        else:  # neutral
            painter.drawLine(int(center_x - mouth_w / 2), int(mouth_y),
                             int(center_x + mouth_w / 2), int(mouth_y))

        # Emotion name text
        if name != "neutral" or self._listening:
            painter.setPen(QPen(QColor("#FFFFFF")))
            painter.setFont(QFont("sans-serif", 7))
            text_y = int(center_y + radius * 0.72)
            painter.drawText(
                QRectF(center_x - radius, text_y - 8, radius * 2, 16),
                Qt.AlignCenter,
                "🎙 Listening..." if self._listening else name.title(),
            )

        painter.end()

    @property
    def emotion(self) -> str:
        return self._current_emotion
