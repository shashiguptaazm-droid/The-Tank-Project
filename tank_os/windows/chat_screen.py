"""ChatScreen — AI conversation interface."""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from tank_os.core.ai_manager import AIManager
from tank_os.core.event_bus import Event, EventBus
from tank_os.widgets.ai_avatar import AIAvatar

logger = logging.getLogger("tank_os.windows.chat")


class _ChatBubble(QFrame):
    """A single chat message bubble."""

    def __init__(self, text: str, is_user: bool,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        if is_user:
            layout.addStretch()

        bubble = QLabel(text)
        bubble.setWordWrap(True)
        bubble.setMaximumWidth(420)
        bubble.setStyleSheet(self._style(is_user))
        bubble.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        layout.addWidget(bubble)

        if not is_user:
            layout.addStretch()

    def _style(self, is_user: bool) -> str:
        if is_user:
            return """
                background: rgba(0,191,255,0.2);
                border: 1px solid rgba(0,191,255,0.3);
                border-radius: 12px; padding: 8px 14px;
                font-size: 12px; color: #FFFFFF;
            """
        return """
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px; padding: 8px 14px;
            font-size: 12px; color: #DDDDDD;
        """


class ChatScreen(QWidget):
    """Full AI chat interface with message history and input."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._ai = AIManager()
        self._bus = EventBus()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setFixedHeight(50)
        header.setStyleSheet("background: rgba(0,0,0,0.2);")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(12, 8, 12, 8)

        self._avatar = AIAvatar(size=36)
        h_layout.addWidget(self._avatar)

        title = QLabel("💬 AI Assistant")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #FFFFFF;")
        h_layout.addWidget(title)
        h_layout.addStretch()

        self._status_label = QLabel("● Online")
        self._status_label.setStyleSheet("font-size: 11px; color: #00E676;")
        h_layout.addWidget(self._status_label)
        main_layout.addWidget(header)

        # Chat area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: rgba(255,255,255,0.05); width: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,0.2); border-radius: 2px;
            }
        """)

        self._chat_widget = QWidget()
        self._chat_layout = QVBoxLayout(self._chat_widget)
        self._chat_layout.setContentsMargins(12, 8, 12, 8)
        self._chat_layout.setSpacing(4)
        self._chat_layout.addStretch()
        scroll.setWidget(self._chat_widget)
        main_layout.addWidget(scroll, 1)

        # Input area
        input_frame = QFrame()
        input_frame.setFixedHeight(56)
        input_frame.setStyleSheet("background: rgba(0,0,0,0.3);")
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(12, 8, 12, 8)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Type a message...")
        self._input.setStyleSheet("""
            QLineEdit {
                background: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 20px;
                padding: 8px 16px;
                font-size: 13px;
                color: #FFFFFF;
            }
            QLineEdit:focus {
                border: 1px solid rgba(0,191,255,0.5);
            }
        """)
        self._input.returnPressed.connect(self._send_message)
        input_layout.addWidget(self._input, 1)

        send_btn = QPushButton("➤")
        send_btn.setFixedSize(36, 36)
        send_btn.setStyleSheet("""
            QPushButton {
                background: #00BFFF;
                border: none; border-radius: 18px;
                font-size: 16px;
            }
            QPushButton:hover { background: #00D0FF; }
            QPushButton:pressed { background: #0090CC; }
        """)
        send_btn.clicked.connect(self._send_message)
        input_layout.addWidget(send_btn)
        main_layout.addWidget(input_frame)

        # Welcome message
        self._add_message("Hello! I'm your TankOS AI assistant. How can I help you today?", False)

    def _send_message(self) -> None:
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        self._add_message(text, True)
        self._add_thinking()

        # Simulate AI response
        QTimer.singleShot(800, lambda: self._simulate_response(text))

    def _add_thinking(self) -> None:
        self._thinking = _ChatBubble("● ● ●", False)
        self._chat_layout.insertWidget(self._chat_layout.count() - 1, self._thinking)

    def _simulate_response(self, text: str) -> None:
        if hasattr(self, '_thinking') and self._thinking:
            self._thinking.deleteLater()
            self._thinking = None

        response = self._ai.chat(text)
        # Fallback responses if AIManager returns stub
        if response == "AI response" or not response:
            responses = [
                "I understand your request. Let me analyze the situation.",
                "I've processed that. What else can I help with?",
                "Good question! Let me think about the best approach.",
                "I'll take care of that right away.",
                "Interesting! Here's what I know about that...",
            ]
            import random
            response = random.choice(responses)

        self._add_message(response, False)

        # Update avatar
        emo_map = {"hello": "happy", "help": "curious",
                   "thank": "loving", "sad": "sad", "stop": "neutral"}
        for keyword, emotion in emo_map.items():
            if keyword in text.lower():
                from tank_os.core.emotion_manager import EmotionManager
                EmotionManager().set_emotion(emotion)
                break

    def _add_message(self, text: str, is_user: bool) -> None:
        bubble = _ChatBubble(text, is_user)
        self._chat_layout.insertWidget(self._chat_layout.count() - 1, bubble)
