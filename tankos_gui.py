#!/usr/bin/env python3
"""TankOS — Anti-gravity GUI combining vision, LiDAR, face recognition, and AI chat.

Aesthetic inspired by Google's anti-gravity design:
- Dark space theme with floating elements
- Glass-morphism cards
- Smooth animations
- Neon accent colors
- Floating particle effects
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import (Qt, QTimer, Signal, QThread, QPointF, QRectF,
                             QPropertyAnimation, QEasingCurve, QMetaObject, Q_ARG)
from PySide6.QtGui import (QFont, QColor, QPalette, QPainter, QBrush, QPen,
                           QLinearGradient, QRadialGradient, QPixmap, QImage,
                           QPainterPath)
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                                QHBoxLayout, QLabel, QPushButton, QFrame,
                                QTextEdit, QLineEdit, QSplitter, QStackedWidget,
                                QGraphicsDropShadowEffect, QScrollArea)

# ═══════════════════════════════════════════════════════════════════════════
#  Theme — Anti-gravity Google aesthetic
# ═══════════════════════════════════════════════════════════════════════════

class Theme:
    BG = "#0a0a0f"
    BG2 = "#0f1019"
    CARD = "rgba(20, 22, 35, 180)"
    CARD_BORDER = "rgba(100, 120, 255, 40)"
    CARD_HOVER = "rgba(30, 35, 55, 200)"
    GLASS = "rgba(255, 255, 255, 5)"
    TEXT = "#e8eaf6"
    DIM = "#5c6bc0"
    ACCENT = "#00e5ff"
    ACCENT2 = "#7c4dff"
    ACCENT3 = "#00e676"
    NEON_BLUE = "#448aff"
    NEON_PURPLE = "#b388ff"
    NEON_GREEN = "#69f0ae"
    NEON_PINK = "#ff4081"
    GRADIENT_1 = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0a0a2e, stop:1 #1a0a2e)"
    GRADIENT_2 = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00e5ff, stop:1 #7c4dff)"

    @staticmethod
    def card_style(accent="#448aff"):
        return f"""
            QFrame {{
                background: {Theme.CARD};
                border: 1px solid {accent}33;
                border-radius: 16px;
            }}
            QFrame:hover {{
                border: 1px solid {accent}88;
                background: {Theme.CARD_HOVER};
            }}
        """

    @staticmethod
    def glow(color, radius=20):
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(radius)
        glow.setColor(QColor(color))
        glow.setOffset(0, 0)
        return glow


# ═══════════════════════════════════════════════════════════════════════════
#  Floating Particles Background
# ═══════════════════════════════════════════════════════════════════════════

class Particle:
    def __init__(self, x, y, vx, vy, size, color, alpha):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.size = size
        self.color = color
        self.alpha = alpha

    def update(self, w, h):
        self.x += self.vx
        self.y += self.vy
        if self.x < 0: self.x = w
        if self.x > w: self.x = 0
        if self.y < 0: self.y = h
        if self.y > h: self.y = 0


class ParticleBackground(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.particles = []
        self._init_particles()

    def _init_particles(self):
        colors = ["#00e5ff", "#7c4dff", "#00e676", "#ff4081", "#448aff"]
        for _ in range(60):
            self.particles.append(Particle(
                x=0, y=0,
                vx=(__import__("random").random() - 0.5) * 0.5,
                vy=(__import__("random").random() - 0.5) * 0.5,
                size=__import__("random").randint(1, 3),
                color=__import__("random").choice(colors),
                alpha=__import__("random").randint(30, 80),
            ))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Background gradient
        grad = QRadialGradient(w/2, h/2, max(w, h)/2)
        grad.setColorAt(0, QColor("#0a0a1a"))
        grad.setColorAt(0.5, QColor("#050510"))
        grad.setColorAt(1, QColor("#000005"))
        p.fillRect(self.rect(), QBrush(grad))

        # Particles
        for particle in self.particles:
            particle.update(w, h)
            c = QColor(particle.color)
            c.setAlpha(particle.alpha)
            p.setBrush(QBrush(c))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(particle.x, particle.y), particle.size, particle.size)

        # Grid lines (subtle)
        p.setPen(QPen(QColor(255, 255, 255, 8), 0.5))
        for x in range(0, w, 80):
            p.drawLine(x, 0, x, h)
        for y in range(0, h, 80):
            p.drawLine(0, y, w, y)

        p.end()


# ═══════════════════════════════════════════════════════════════════════════
#  Camera Widget with YOLO overlay
# ═══════════════════════════════════════════════════════════════════════════

class CameraWidget(QFrame):
    frame_captured = Signal(str)  # image path

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(Theme.card_style("#00e5ff"))
        self.setMinimumSize(400, 300)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Header
        header = QHBoxLayout()
        title = QLabel("📷 VISION")
        title.setStyleSheet(f"color: {Theme.ACCENT}; font-size: 14px; font-weight: bold; letter-spacing: 2px;")
        header.addWidget(title)
        header.addStretch()
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet(f"color: {Theme.NEON_GREEN}; font-size: 12px;")
        header.addWidget(self.status_dot)
        self.fps_label = QLabel("0 FPS")
        self.fps_label.setStyleSheet(f"color: {Theme.DIM}; font-size: 11px;")
        header.addWidget(self.fps_label)
        layout.addLayout(header)

        # Video feed
        self.video_label = QLabel("Click 'Capture' to start")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumHeight(280)
        self.video_label.setStyleSheet(f"""
            background: #050510;
            border-radius: 8px;
            color: {Theme.DIM};
            font-size: 14px;
        """)
        layout.addWidget(self.video_label)

        # Detection info
        self.detections_label = QLabel("")
        self.detections_label.setStyleSheet(f"color: {Theme.TEXT}; font-size: 12px; padding: 4px;")
        self.detections_label.setWordWrap(True)
        layout.addWidget(self.detections_label)

        # Face info
        self.face_label = QLabel("")
        self.face_label.setStyleSheet(f"color: {Theme.NEON_PURPLE}; font-size: 12px; padding: 4px;")
        layout.addWidget(self.face_label)

        # Capture button
        btn_row = QHBoxLayout()
        self.capture_btn = self._make_btn("⚡ CAPTURE", Theme.ACCENT)
        self.capture_btn.clicked.connect(self._capture)
        btn_row.addWidget(self.capture_btn)

        self.stream_btn = self._make_btn("▶ STREAM", Theme.NEON_GREEN)
        self.stream_btn.clicked.connect(self._toggle_stream)
        btn_row.addWidget(self.stream_btn)
        layout.addLayout(btn_row)

        self._streaming = False
        self._frame_count = 0

    def _make_btn(self, text, color):
        btn = QPushButton(text)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {color}22;
                color: {color};
                border: 1px solid {color}44;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background: {color}44;
                border: 1px solid {color}88;
            }}
            QPushButton:pressed {{
                background: {color}66;
            }}
        """)
        return btn

    def _capture(self):
        self.status_dot.setStyleSheet(f"color: {Theme.ACCENT}; font-size: 12px;")
        self.detections_label.setText("Capturing...")
        self.face_label.setText("")

        # Synchronous capture (avoids QThread crashes)
        result = self._do_capture()
        self._on_capture(result)

    def _do_capture(self):
        result = {}
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from tank_os.shell.terminal.agent_chat import _capture_frame, _run_yolo
            from tank_os.shell.terminal.face_db import FaceDB

            frame = _capture_frame()
            if frame:
                result["image_path"] = frame
                yolo_text = _run_yolo(frame)
                detections = []
                if "Detected:" in yolo_text:
                    det_str = yolo_text.split("Detected:")[1].strip()
                    for part in det_str.split(","):
                        part = part.strip()
                        if "(" in part:
                            name = part.split("(")[0]
                            conf = float(part.split("(")[1].rstrip(")").rstrip("%")) / 100
                            detections.append({"name": name, "confidence": conf})
                result["detections"] = detections
                db = FaceDB()
                result["faces"] = db.recognize_in_frame(frame)
            else:
                result["error"] = "Camera not available"
        except Exception as e:
            result["error"] = str(e)
        return result

    def _on_capture(self, result):
        self._frame_count += 1
        self.fps_label.setText(f"Frame #{self._frame_count}")

        if result.get("image_path"):
            pixmap = QPixmap(result["image_path"])
            if not pixmap.isNull():
                scaled = pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.video_label.setPixmap(scaled)

        # YOLO detections
        detections = result.get("detections", [])
        if detections:
            det_text = " | ".join(f"{d['name']}({d['confidence']:.0%})" for d in detections)
            self.detections_label.setText(f"🎯 {det_text}")
        else:
            self.detections_label.setText("No objects detected")

        # Face recognition
        faces = result.get("faces", [])
        if faces:
            face_parts = []
            for f in faces:
                if f["is_known"]:
                    face_parts.append(f"👤 {f['name']} ({f['confidence']:.0%})")
                else:
                    face_parts.append(f"❓ unknown ({f['confidence']:.0%})")
            self.face_label.setText(" | ".join(face_parts))
        else:
            self.face_label.setText("")

        self.status_dot.setStyleSheet(f"color: {Theme.NEON_GREEN}; font-size: 12px;")
        self.frame_captured.emit(result.get("image_path", ""))

    def _toggle_stream(self):
        self._streaming = not self._streaming
        if self._streaming:
            self.stream_btn.setText("⏸ STOP")
            self._stream_timer = QTimer()
            self._stream_timer.timeout.connect(self._capture)
            self._stream_timer.start(1000)  # 1 FPS
        else:
            self.stream_btn.setText("▶ STREAM")
            if hasattr(self, "_stream_timer"):
                self._stream_timer.stop()


class CaptureWorker(QThread):
    result_ready = Signal(dict)

    def run(self):
        result = {}
        try:
            # Capture frame
            sys.path.insert(0, str(Path(__file__).parent))
            from tank_os.shell.terminal.agent_chat import _capture_frame, _run_yolo
            from tank_os.shell.terminal.face_db import FaceDB

            frame = _capture_frame()
            if frame:
                result["image_path"] = frame

                # YOLO
                yolo_text = _run_yolo(frame)
                detections = []
                if "Detected:" in yolo_text:
                    det_str = yolo_text.split("Detected:")[1].strip()
                    for part in det_str.split(","):
                        part = part.strip()
                        if "(" in part:
                            name = part.split("(")[0]
                            conf = float(part.split("(")[1].rstrip(")").rstrip("%")) / 100
                            detections.append({"name": name, "confidence": conf})
                result["detections"] = detections

                # Face recognition
                db = FaceDB()
                result["faces"] = db.recognize_in_frame(frame)
            else:
                result["error"] = "Camera not available"
        except Exception as e:
            result["error"] = str(e)

        self.result_ready.emit(result)


# ═══════════════════════════════════════════════════════════════════════════
#  LiDAR Widget
# ═══════════════════════════════════════════════════════════════════════════

class LidarWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(Theme.card_style("#7c4dff"))
        self.setMinimumSize(300, 250)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        header = QHBoxLayout()
        title = QLabel("📡 LIDAR")
        title.setStyleSheet(f"color: {Theme.ACCENT2}; font-size: 14px; font-weight: bold; letter-spacing: 2px;")
        header.addWidget(title)
        header.addStretch()
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet(f"color: {Theme.NEON_GREEN}; font-size: 12px;")
        header.addWidget(self.status_dot)
        layout.addLayout(header)

        # Distance display
        self.distance_label = QLabel("-- m")
        self.distance_label.setAlignment(Qt.AlignCenter)
        self.distance_label.setStyleSheet(f"""
            color: {Theme.NEON_PURPLE};
            font-size: 48px;
            font-weight: bold;
            font-family: monospace;
            padding: 10px;
        """)
        layout.addWidget(self.distance_label)

        # Direction
        self.direction_label = QLabel("Scanning...")
        self.direction_label.setAlignment(Qt.AlignCenter)
        self.direction_label.setStyleSheet(f"color: {Theme.DIM}; font-size: 14px;")
        layout.addWidget(self.direction_label)

        # Position map (8-direction)
        self.map_label = QLabel("")
        self.map_label.setAlignment(Qt.AlignCenter)
        self.map_label.setStyleSheet(f"color: {Theme.TEXT}; font-size: 11px; font-family: monospace;")
        layout.addWidget(self.map_label)

        # Refresh
        self.refresh_btn = QPushButton("🔄 SCAN")
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Theme.ACCENT2}22;
                color: {Theme.ACCENT2};
                border: 1px solid {Theme.ACCENT2}44;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {Theme.ACCENT2}44; }}
        """)
        self.refresh_btn.clicked.connect(self._scan)
        layout.addWidget(self.refresh_btn)

        # Auto-scan timer
        self._timer = QTimer()
        self._timer.timeout.connect(self._scan)
        self._timer.start(2000)

    def _scan(self):
        self.status_dot.setStyleSheet(f"color: {Theme.ACCENT}; font-size: 12px;")
        result = self._do_scan()
        self._on_scan(result)

    def _do_scan(self):
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from tank_os.shell.terminal.lidar_reader import read_lidar, get_position_map
            scan = read_lidar(timeout_s=1.5)
            if scan and scan.min_distance > 0:
                dist_m = scan.min_distance / 1000.0
                return {
                    "distance": f"{dist_m:.2f} m",
                    "direction": f"Nearest: {scan.nearest_object}",
                    "map": get_position_map(),
                }
            else:
                return {"error": "No objects in range"}
        except Exception as e:
            return {"error": str(e)}

    def _on_scan(self, result):
        if result.get("distance"):
            self.distance_label.setText(result["distance"])
            self.direction_label.setText(result.get("direction", ""))
            self.map_label.setText(result.get("map", ""))
            self.status_dot.setStyleSheet(f"color: {Theme.NEON_GREEN}; font-size: 12px;")
        else:
            self.distance_label.setText("-- m")
            self.direction_label.setText(result.get("error", "No data"))
            self.status_dot.setStyleSheet(f"color: {Theme.NEON_PINK}; font-size: 12px;")


class LidarWorker(QThread):
    result_ready = Signal(dict)

    def run(self):
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from tank_os.shell.terminal.lidar_reader import read_lidar, get_position_map
            scan = read_lidar(timeout_s=1.5)
            if scan and scan.min_distance > 0:
                dist_m = scan.min_distance / 1000.0
                self.result_ready.emit({
                    "distance": f"{dist_m:.2f} m",
                    "direction": f"Nearest: {scan.nearest_object}",
                    "map": get_position_map(),
                })
            else:
                self.result_ready.emit({"error": "No objects in range"})
        except Exception as e:
            self.result_ready.emit({"error": str(e)})


# ═══════════════════════════════════════════════════════════════════════════
#  AI Chat Widget
# ═══════════════════════════════════════════════════════════════════════════

class ChatWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(Theme.card_style("#00e676"))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        header = QHBoxLayout()
        title = QLabel("🤖 AI AGENT")
        title.setStyleSheet(f"color: {Theme.ACCENT3}; font-size: 14px; font-weight: bold; letter-spacing: 2px;")
        header.addWidget(title)
        header.addStretch()
        self.providers_label = QLabel("7 providers")
        self.providers_label.setStyleSheet(f"color: {Theme.DIM}; font-size: 11px;")
        header.addWidget(self.providers_label)
        layout.addLayout(header)

        # Chat area
        self.chat_area = QTextEdit()
        self.chat_area.setReadOnly(True)
        self.chat_area.setStyleSheet(f"""
            QTextEdit {{
                background: #050510;
                color: {Theme.TEXT};
                border: 1px solid {Theme.CARD_BORDER};
                border-radius: 8px;
                padding: 8px;
                font-size: 13px;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }}
        """)
        layout.addWidget(self.chat_area)

        # Input
        input_row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Ask anything...")
        self.input.setStyleSheet(f"""
            QLineEdit {{
                background: {Theme.BG2};
                color: {Theme.TEXT};
                border: 1px solid {Theme.CARD_BORDER};
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 1px solid {Theme.ACCENT3}88;
            }}
        """)
        self.input.returnPressed.connect(self._send)
        input_row.addWidget(self.input)

        self.send_btn = QPushButton("→")
        self.send_btn.setFixedSize(40, 40)
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Theme.ACCENT3}33;
                color: {Theme.ACCENT3};
                border: 1px solid {Theme.ACCENT3}44;
                border-radius: 20px;
                font-size: 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {Theme.ACCENT3}55; }}
        """)
        self.send_btn.clicked.connect(self._send)
        input_row.addWidget(self.send_btn)
        layout.addLayout(input_row)

        self._chat_history = []

    def _send(self):
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self._append("You", text, Theme.ACCENT3)
        self._append("TankOS", "Thinking...", Theme.DIM)

        # Synchronous chat
        reply = self._do_chat(text)
        # Remove "Thinking..." and add real reply
        cursor = self.chat_area.textCursor()
        cursor.movePosition(cursor.End)
        cursor.select(cursor.BlockUnderCursor)
        cursor.removeSelectedText()
        cursor.deletePreviousChar()
        self._append("TankOS", reply, Theme.ACCENT)

    def _do_chat(self, message):
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from tank_os.shell.terminal.agent_chat import (_rotate_chat, _camera_vision,
                                                           _run_shell, _invoke_tool,
                                                           _SYSTEM_PROMPT, _load_tool_catalog)
            import json, re

            system = _SYSTEM_PROMPT + "\n\nAVAILABLE TOOLS:\n" + _load_tool_catalog()
            msgs = [{"role": "system", "content": system}]
            for h in self._chat_history[-10:]:
                msgs.append({"role": h["role"], "content": h["content"]})
            msgs.append({"role": "user", "content": message})

            for _ in range(3):
                resp = _rotate_chat(msgs)
                if not resp or resp.startswith("All providers"):
                    return "LLM unavailable"

                action = None
                clean = re.sub(r"<think>.*?</think>", "", resp, flags=re.DOTALL).strip()
                try: action = json.loads(clean)
                except:
                    s = clean.find("{")
                    e = clean.rfind("}")
                    if s != -1 and e > s:
                        try: action = json.loads(clean[s:e+1])
                        except: pass

                if action is None:
                    self._chat_history.append({"role": "user", "content": message})
                    self._chat_history.append({"role": "assistant", "content": clean})
                    return clean

                at = action.get("action", "")
                if at == "reply":
                    text = action.get("text", "")
                    self._chat_history.append({"role": "user", "content": message})
                    self._chat_history.append({"role": "assistant", "content": text})
                    return text
                elif at == "camera":
                    result = _camera_vision()
                    self._chat_history.append({"role": "assistant", "content": resp})
                    self._chat_history.append({"role": "user", "content": f"[camera] {result}\nDescribe what you see."})
                elif at == "shell":
                    cmd = action.get("cmd", "")
                    result = _run_shell(cmd)
                    self._chat_history.append({"role": "assistant", "content": resp})
                    self._chat_history.append({"role": "user", "content": f"[shell result]\n{result[:2000]}\nDescribe the results."})
                elif at == "tool":
                    tn = action.get("tool", "")
                    args = action.get("args", {})
                    result = _invoke_tool(tn, args)
                    self._chat_history.append({"role": "assistant", "content": resp})
                    self._chat_history.append({"role": "user", "content": f"[tool result]\n{result[:2000]}\nDescribe the results."})
                else:
                    self._chat_history.append({"role": "user", "content": message})
                    self._chat_history.append({"role": "assistant", "content": clean})
                    return clean

            return "Processing complete."
        except Exception as e:
            return f"Error: {e}"

    def _append(self, sender, text, color):
        ts = datetime.now().strftime("%H:%M")
        self.chat_area.append(f'<span style="color:{color}; font-weight:bold;">[{ts}] {sender}:</span> {text}')
        self.chat_area.verticalScrollBar().setValue(self.chat_area.verticalScrollBar().maximum())


class ChatWorker(QThread):
    reply_ready = Signal(str)

    def __init__(self, message, history):
        super().__init__()
        self.message = message
        self.history = history

    def run(self):
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from tank_os.shell.terminal.agent_chat import (_rotate_chat, _camera_vision,
                                                           _run_shell, _invoke_tool,
                                                           _SYSTEM_PROMPT, _load_tool_catalog)
            import json, re

            system = _SYSTEM_PROMPT + "\n\nAVAILABLE TOOLS:\n" + _load_tool_catalog()
            msgs = [{"role": "system", "content": system}]
            for h in self.history[-10:]:
                msgs.append({"role": h["role"], "content": h["content"]})
            msgs.append({"role": "user", "content": self.message})

            for _ in range(3):
                resp = _rotate_chat(msgs)
                if not resp or resp.startswith("All providers"):
                    self.reply_ready.emit("LLM unavailable")
                    return

                action = None
                clean = re.sub(r"<think>.*?</think>", "", resp, flags=re.DOTALL).strip()
                try:
                    action = json.loads(clean)
                except:
                    s = clean.find("{")
                    e = clean.rfind("}")
                    if s != -1 and e > s:
                        try: action = json.loads(clean[s:e+1])
                        except: pass

                if action is None:
                    self.reply_ready.emit(clean)
                    self.history.append({"role": "user", "content": self.message})
                    self.history.append({"role": "assistant", "content": clean})
                    return

                at = action.get("action", "")
                if at == "reply":
                    text = action.get("text", "")
                    self.reply_ready.emit(text)
                    self.history.append({"role": "user", "content": self.message})
                    self.history.append({"role": "assistant", "content": text})
                    return
                elif at == "camera":
                    result = _camera_vision()
                    self.history.append({"role": "assistant", "content": resp})
                    self.history.append({"role": "user", "content": f"[camera] {result}\nDescribe what you see."})
                elif at == "shell":
                    cmd = action.get("cmd", "")
                    result = _run_shell(cmd)
                    self.history.append({"role": "assistant", "content": resp})
                    self.history.append({"role": "user", "content": f"[shell result]\n{result[:2000]}\nDescribe the results."})
                elif at == "tool":
                    tn = action.get("tool", "")
                    args = action.get("args", {})
                    result = _invoke_tool(tn, args)
                    self.history.append({"role": "assistant", "content": resp})
                    self.history.append({"role": "user", "content": f"[tool result]\n{result[:2000]}\nDescribe the results."})
                else:
                    self.reply_ready.emit(clean)
                    return

            self.reply_ready.emit("Processing complete.")
        except Exception as e:
            self.reply_ready.emit(f"Error: {e}")


# ═══════════════════════════════════════════════════════════════════════════
#  Status Bar
# ═══════════════════════════════════════════════════════════════════════════

class StatusBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setStyleSheet(f"""
            QFrame {{
                background: rgba(10, 10, 20, 200);
                border-bottom: 1px solid {Theme.CARD_BORDER};
            }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 4, 16, 4)

        self.title = QLabel("TANK OS")
        self.title.setStyleSheet(f"color: {Theme.ACCENT}; font-size: 14px; font-weight: bold; letter-spacing: 3px;")
        layout.addWidget(self.title)

        layout.addStretch()

        self.status = QLabel("● Systems Online")
        self.status.setStyleSheet(f"color: {Theme.NEON_GREEN}; font-size: 12px;")
        layout.addWidget(self.status)

        self.time_label = QLabel("")
        self.time_label.setStyleSheet(f"color: {Theme.DIM}; font-size: 12px;")
        layout.addWidget(self.time_label)

        # Timer
        self._timer = QTimer()
        self._timer.timeout.connect(self._update)
        self._timer.start(1000)
        self._update()

    def _update(self):
        self.time_label.setText(datetime.now().strftime("%H:%M:%S"))


# ═══════════════════════════════════════════════════════════════════════════
#  Main Window
# ═══════════════════════════════════════════════════════════════════════════

class TankOSWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TankOS — Autonomous AI Robot")
        self.setMinimumSize(1400, 900)

        # Background
        self._bg = ParticleBackground(self)
        self._bg.lower()

        self.showMaximized()

        # Central widget
        central = QWidget()
        central.setStyleSheet("background: transparent;")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Status bar
        main_layout.addWidget(StatusBar())

        # Content
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(16)

        # Left: Camera + LiDAR
        left = QVBoxLayout()
        left.setSpacing(16)

        self.camera = CameraWidget()
        left.addWidget(self.camera, stretch=3)

        self.lidar = LidarWidget()
        left.addWidget(self.lidar, stretch=1)

        content_layout.addLayout(left, stretch=3)

        # Right: Chat
        right = QVBoxLayout()
        self.chat = ChatWidget()
        right.addWidget(self.chat)
        content_layout.addLayout(right, stretch=2)

        main_layout.addWidget(content, stretch=1)

        # Welcome
        self.chat._append("TankOS", "Welcome! I can see through the camera, detect faces, measure distances with LiDAR, and control the robot. Ask me anything!", Theme.ACCENT)

        # Auto-start everything
        QTimer.singleShot(1000, self._auto_start)

    def _auto_start(self):
        """Auto-start camera stream, LiDAR scan, and perception."""
        # Auto camera stream
        self._stream_timer = QTimer()
        self._stream_timer.timeout.connect(self.camera._capture)
        self._stream_timer.start(2000)  # capture every 2s
        self.camera.stream_btn.setText("⏸ STOP")
        self.camera._streaming = True

        # Perception pipeline
        try:
            from tank_os.shell.terminal.perception import PerceptionPipeline
            self._perception = PerceptionPipeline(
                motion_threshold=0.02,
                lidar_threshold_mm=2000,
                cooldown_s=30,
            )
            self._perception.on_event(self._on_perception_event)
            self._perception.start()
            self.chat._append("System", "Auto-perception started — motion + LiDAR monitoring active", Theme.ACCENT3)
        except Exception as e:
            self.chat._append("System", f"Perception: {e}", Theme.NEON_PINK)

    def _start_perception(self):
        try:
            from tank_os.shell.terminal.perception import PerceptionPipeline
            self._perception = PerceptionPipeline(
                motion_threshold=0.02,
                lidar_threshold_mm=2000,
                cooldown_s=30,
            )
            self._perception.on_event(self._on_perception_event)
            self._perception.start()
            self.chat._append("System", "Auto-perception started — motion + LiDAR monitoring active", Theme.ACCENT3)
        except Exception as e:
            self.chat._append("System", f"Perception init: {e}", Theme.NEON_PINK)

    def closeEvent(self, event):
        if hasattr(self, '_perception'):
            self._perception.stop()
        event.accept()

    def _on_perception_event(self, event):
        ts = time.strftime("%H:%M:%S", time.localtime(event.timestamp))
        sms_status = "sent" if event.sms_sent else f"failed: {event.sms_error}"
        msg = (
            f"[{ts}] Alert! Motion={event.motion_score:.3f} "
            f"LiDAR={event.lidar_distance/1000:.2f}m\n"
            f"AI: {event.ai_interpretation}\n"
            f"SMS: {sms_status}"
        )
        # Thread-safe: use QTimer to update UI from main thread
        QTimer.singleShot(0, lambda m=msg: self.chat._append("ALERT", m, Theme.NEON_PINK))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._bg.setGeometry(self.rect())


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))

    # Dark palette
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(Theme.BG))
    palette.setColor(QPalette.WindowText, QColor(Theme.TEXT))
    palette.setColor(QPalette.Base, QColor(Theme.BG2))
    palette.setColor(QPalette.Text, QColor(Theme.TEXT))
    palette.setColor(QPalette.Button, QColor(Theme.CARD))
    palette.setColor(QPalette.ButtonText, QColor(Theme.TEXT))
    app.setPalette(palette)

    window = TankOSWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
