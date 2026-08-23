#!/usr/bin/env python3
"""
TankOS GUI — Android TV-style interface for Jetson Nano
Clean grid layout with icons for every feature.
Inspired by Arduino's Android TV interface.
"""
import sys
import os
import json
import time
import serial
import glob
import subprocess
import threading
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QFrame, QStackedWidget,
    QTextEdit, QLineEdit, QScrollArea, QSizePolicy, QProgressBar
)
from PySide6.QtCore import Qt, QTimer, Signal, QSize, QThread
from PySide6.QtGui import QFont, QColor, QPalette, QIcon, QPainter, QBrush, QPen

# ═══════════════════════════════════════════════════════════
#  COLOR SCHEME — Dark theme inspired by Android TV
# ═══════════════════════════════════════════════════════════
COLORS = {
    "bg": "#0a0e1a",
    "card": "#111827",
    "card_hover": "#1e293b",
    "accent": "#00ff88",
    "accent2": "#22d3ee",
    "accent3": "#a78bfa",
    "text": "#f1f5f9",
    "dim": "#64748b",
    "border": "#1e293b",
    "success": "#22c55e",
    "warning": "#eab308",
    "danger": "#ef4444",
    "blue": "#3b82f6",
}

# ═══════════════════════════════════════════════════════════
#  ICON GRID — Every feature as a tile
# ═══════════════════════════════════════════════════════════
TILES = [
    # Row 1: Core
    {"icon": "🤖", "title": "Robot Status", "color": "#00ff88", "action": "robot_status"},
    {"icon": "🧠", "title": "AI Chat", "color": "#a78bfa", "action": "ai_chat"},
    {"icon": "📷", "title": "Camera", "color": "#22d3ee", "action": "camera"},
    {"icon": "🗺️", "title": "Navigation", "color": "#3b82f6", "action": "navigation"},
    # Row 2: Control
    {"icon": "🎮", "title": "Drive", "color": "#eab308", "action": "drive"},
    {"icon": "📡", "title": "Sensors", "color": "#22c55e", "action": "sensors"},
    {"icon": "⚙️", "title": "Motors", "color": "#f97316", "action": "motors"},
    {"icon": "🔋", "title": "Power", "color": "#ef4444", "action": "power"},
    # Row 3: System
    {"icon": "🛡️", "title": "Safety", "color": "#ef4444", "action": "safety"},
    {"icon": "🌐", "title": "Network", "color": "#06b6d4", "action": "network"},
    {"icon": "💬", "title": "SMS", "color": "#8b5cf6", "action": "sms"},
    {"icon": "🔔", "title": "Alerts", "color": "#f59e0b", "action": "alerts"},
    # Row 4: Advanced
    {"icon": "🧬", "title": "Evolution", "color": "#10b981", "action": "evolution"},
    {"icon": "👁️", "title": "AprilTag", "color": "#6366f1", "action": "apriltag"},
    {"icon": "🔌", "title": "USB Devices", "color": "#64748b", "action": "usb"},
    {"icon": "💻", "title": "Terminal", "color": "#00ff88", "action": "terminal"},
]


class TileButton(QPushButton):
    """Android TV-style tile button"""
    def __init__(self, icon, title, color, action, parent=None):
        super().__init__(parent)
        self.action = action
        self.base_color = color
        self.setText(f"{icon}\n{title}")
        self.setMinimumSize(180, 120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['card']};
                color: {COLORS['text']};
                border: 2px solid {color}33;
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
                padding: 12px;
                text-align: center;
            }}
            QPushButton:hover {{
                background: {COLORS['card_hover']};
                border: 2px solid {color};
                transform: scale(1.02);
            }}
            QPushButton:pressed {{
                background: {color}33;
                border: 2px solid {color};
            }}
        """)


class StatusWidget(QFrame):
    """Status bar at the top"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)
        self.setStyleSheet(f"background: {COLORS['card']}; border-bottom: 1px solid {COLORS['border']};")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 5, 20, 5)

        self.cpu_label = QLabel("CPU: --")
        self.cpu_label.setStyleSheet(f"color: {COLORS['accent']}; font-size: 13px;")
        layout.addWidget(self.cpu_label)

        self.ram_label = QLabel("RAM: --")
        self.ram_label.setStyleSheet(f"color: {COLORS['accent2']}; font-size: 13px;")
        layout.addWidget(self.ram_label)

        self.temp_label = QLabel("Temp: --")
        self.temp_label.setStyleSheet(f"color: {COLORS['warning']}; font-size: 13px;")
        layout.addWidget(self.temp_label)

        layout.addStretch()

        self.title = QLabel("🤖 TankOS")
        self.title.setStyleSheet(f"color: {COLORS['accent']}; font-size: 18px; font-weight: bold;")
        layout.addWidget(self.title)

        layout.addStretch()

        self.network_label = QLabel("🌐 Online")
        self.network_label.setStyleSheet(f"color: {COLORS['success']}; font-size: 13px;")
        layout.addWidget(self.network_label)

        self.time_label = QLabel("--:--")
        self.time_label.setStyleSheet(f"color: {COLORS['dim']}; font-size: 13px;")
        layout.addWidget(self.time_label)


class CameraPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {COLORS['card']}; border-radius: 12px;")
        layout = QVBoxLayout(self)
        header = QLabel("📷 USB Camera Feed")
        header.setStyleSheet(f"color: {COLORS['accent']}; font-size: 18px; font-weight: bold; padding: 10px;")
        layout.addWidget(header)

        self.video_label = QLabel("📷 Tap 'Capture' to get a frame")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumHeight(300)
        self.video_label.setStyleSheet(f"background: #000; border-radius: 8px; color: {COLORS['dim']}; font-size: 16px;")
        layout.addWidget(self.video_label)

        btn_row = QHBoxLayout()
        capture_btn = QPushButton("📸 Capture")
        capture_btn.setStyleSheet(f"background: {COLORS['accent']}; color: #000; padding: 10px 20px; border-radius: 8px; font-weight: bold;")
        capture_btn.clicked.connect(self.capture_frame)
        btn_row.addWidget(capture_btn)

        detect_btn = QPushButton("🔍 Detect")
        detect_btn.setStyleSheet(f"background: {COLORS['blue']}; color: #fff; padding: 10px 20px; border-radius: 8px; font-weight: bold;")
        detect_btn.clicked.connect(self.detect_objects)
        btn_row.addWidget(detect_btn)

        layout.addLayout(btn_row)
        self.info_label = QLabel("")
        self.info_label.setStyleSheet(f"color: {COLORS['dim']}; font-size: 12px;")
        layout.addWidget(self.info_label)

    def capture_frame(self):
        try:
            self.video_label.setText("⏳ Capturing...")
            s = serial.Serial("/dev/ttyACM0", 921600, timeout=5)
            time.sleep(0.3)
            s.read(s.in_waiting)
            s.write(b"SNAP\n")
            header = b""
            deadline = time.time() + 5
            while time.time() < deadline:
                c = s.read(1)
                if c:
                    header += c
                    if c == b"\n": break
            h = header.decode("utf-8", errors="replace").strip()
            if h.startswith("FRAME:"):
                parts = h.split(":")
                expected = int(parts[3])
                jpeg = b""
                dl = time.time() + 10
                while len(jpeg) < expected and time.time() < dl:
                    chunk = s.read(min(expected - len(jpeg), 16384))
                    if chunk: jpeg += chunk; dl = time.time() + 2
                s.read(1)
                s.close()
                path = os.path.expanduser("~/The-Tank-Project/data/frame.jpg")
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "wb") as f: f.write(jpeg)
                from PySide6.QtGui import QPixmap
                pixmap = QPixmap(path)
                scaled = pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.video_label.setPixmap(scaled)
                self.info_label.setText(f"✅ {parts[1]}×{parts[2]} — {len(jpeg)} bytes — {datetime.now().strftime('%H:%M:%S')}")
            else:
                s.close()
                self.video_label.setText("❌ No frame received")
        except Exception as e:
            self.video_label.setText(f"❌ {e}")

    def detect_objects(self):
        try:
            self.info_label.setText("🔍 Running YOLO detection...")
            from ultralytics import YOLO
            model = YOLO("yolov8n.pt")
            path = os.path.expanduser("~/The-Tank-Project/data/frame.jpg")
            if not os.path.exists(path):
                self.capture_frame()
            results = model(path, verbose=False)
            objects = []
            for r in results:
                for box in r.boxes:
                    name = r.names[int(box.cls[0])]
                    conf = float(box.conf[0])
                    objects.append(f"{name}({conf:.0%})")
            self.info_label.setText(f"🔍 Detected: {', '.join(objects) if objects else 'none'}")
        except Exception as e:
            self.info_label.setText(f"🔍 {e}")


class AIChatPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {COLORS['card']}; border-radius: 12px;")
        layout = QVBoxLayout(self)
        header = QLabel("🧠 AI Chat — TankOS")
        header.setStyleSheet(f"color: {COLORS['accent3']}; font-size: 18px; font-weight: bold; padding: 10px;")
        layout.addWidget(header)

        self.chat = QTextEdit()
        self.chat.setReadOnly(True)
        self.chat.setStyleSheet(f"background: #000; color: {COLORS['text']}; border-radius: 8px; font-size: 14px; padding: 10px;")
        layout.addWidget(self.chat)

        input_row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Ask Tank anything...")
        self.input.setStyleSheet(f"background: {COLORS['bg']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']}; border-radius: 8px; padding: 10px; font-size: 14px;")
        self.input.returnPressed.connect(self.send_chat)
        input_row.addWidget(self.input)

        send_btn = QPushButton("Send")
        send_btn.setStyleSheet(f"background: {COLORS['accent3']}; color: #fff; padding: 10px 20px; border-radius: 8px; font-weight: bold;")
        send_btn.clicked.connect(self.send_chat)
        input_row.addWidget(send_btn)
        layout.addLayout(input_row)

        self.chat.append("🤖 TankOS AI ready. Ask me anything about the robot.")

    def send_chat(self):
        text = self.input.text().strip()
        if not text: return
        self.input.clear()
        self.chat.append(f"\n🧑 You: {text}")
        self.chat.append("⏳ Thinking...")

        def do_chat():
            try:
                sys.path.insert(0, os.path.expanduser("~/The-Tank-Project"))
                from tank.ai.tool_registry import ToolExecutor
                from tank.ai.tool_caller import ToolCaller
                executor = ToolExecutor()
                caller = ToolCaller(tool_executor=executor)
                response = caller.chat(text)
                QTimer.singleShot(0, lambda: self._show_response(response or "No response"))
            except Exception as e:
                QTimer.singleShot(0, lambda: self._show_response(f"Error: {e}"))

        threading.Thread(target=do_chat, daemon=True).start()

    def _show_response(self, text):
        self.chat.append(f"\n🤖 Tank: {text}")


class SensorsPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {COLORS['card']}; border-radius: 12px;")
        layout = QVBoxLayout(self)
        header = QLabel("📡 Live Sensors")
        header.setStyleSheet(f"color: {COLORS['success']}; font-size: 18px; font-weight: bold; padding: 10px;")
        layout.addWidget(header)

        grid = QGridLayout()
        self.sensors = {}
        sensor_defs = [
            ("🌡️ Temperature", "read_temperature", COLORS["warning"]),
            ("🧭 IMU", "read_imu", COLORS["accent"]),
            ("📏 LiDAR", "read_lidar", COLORS["accent2"]),
            ("🔋 Battery", "read_battery", COLORS["danger"]),
            ("📷 Camera", "USB /dev/ttyACM0", COLORS["accent2"]),
            ("📶 4G Modem", "Quectel EG800AK", COLORS["blue"]),
        ]
        for i, (name, key, color) in enumerate(sensor_defs):
            card = QFrame()
            card.setStyleSheet(f"background: {COLORS['bg']}; border: 1px solid {color}33; border-radius: 8px; padding: 8px;")
            card_layout = QVBoxLayout(card)
            title = QLabel(name)
            title.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold;")
            card_layout.addWidget(title)
            value = QLabel("--")
            value.setStyleSheet(f"color: {COLORS['text']}; font-size: 16px; font-weight: bold;")
            card_layout.addWidget(value)
            self.sensors[key] = value
            grid.addWidget(card, i // 3, i % 3)
        layout.addLayout(grid)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setStyleSheet(f"background: {COLORS['accent']}; color: #000; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        refresh_btn.clicked.connect(self.refresh)
        layout.addWidget(refresh_btn)

    def refresh(self):
        try:
            temp = subprocess.run(["cat", "/sys/class/thermal/thermal_zone0/temp"], capture_output=True, text=True).stdout.strip()
            self.sensors["read_temperature"].setText(f"{int(temp)/1000:.1f}°C")
        except: pass


class TerminalPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {COLORS['card']}; border-radius: 12px;")
        layout = QVBoxLayout(self)
        header = QLabel("💻 Terminal")
        header.setStyleSheet(f"color: {COLORS['accent']}; font-size: 18px; font-weight: bold; padding: 10px;")
        layout.addWidget(header)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setStyleSheet(f"background: #000; color: #00ff88; border-radius: 8px; font-family: monospace; font-size: 13px; padding: 10px;")
        layout.addWidget(self.output)

        input_row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Enter command...")
        self.input.setStyleSheet(f"background: {COLORS['bg']}; color: {COLORS['accent']}; border: 1px solid {COLORS['border']}; border-radius: 8px; padding: 10px; font-family: monospace;")
        self.input.returnPressed.connect(self.run_command)
        input_row.addWidget(self.input)

        run_btn = QPushButton("▶️ Run")
        run_btn.setStyleSheet(f"background: {COLORS['accent']}; color: #000; padding: 10px 20px; border-radius: 8px; font-weight: bold;")
        run_btn.clicked.connect(self.run_command)
        input_row.addWidget(run_btn)
        layout.addLayout(input_row)

        self.output.append("$ TankOS Terminal ready")

    def run_command(self):
        cmd = self.input.text().strip()
        if not cmd: return
        self.input.clear()
        self.output.append(f"\n$ {cmd}")
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            if result.stdout: self.output.append(result.stdout)
            if result.stderr: self.output.append(result.stderr)
        except Exception as e:
            self.output.append(f"Error: {e}")


class MainGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🤖 TankOS — Android TV Interface")
        self.setMinimumSize(1200, 800)
        self.showMaximized()
        self._setup_ui()
        self._start_status_timer()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Status bar
        self.status = StatusWidget()
        main_layout.addWidget(self.status)

        # Content area
        content = QHBoxLayout()
        content.setContentsMargins(16, 16, 16, 16)
        content.setSpacing(16)

        # Left: Tile grid
        tile_frame = QFrame()
        tile_layout = QGridLayout(tile_frame)
        tile_layout.setSpacing(12)
        tile_layout.setContentsMargins(0, 0, 0, 0)

        self.panels = {}
        for i, tile in enumerate(TILES):
            btn = TileButton(tile["icon"], tile["title"], tile["color"], tile["action"])
            btn.clicked.connect(lambda checked, a=tile["action"]: self.show_panel(a))
            tile_layout.addWidget(btn, i // 4, i % 4)

        content.addWidget(tile_frame, stretch=2)

        # Right: Panel area
        self.panel_stack = QStackedWidget()
        self.panel_stack.setStyleSheet(f"background: {COLORS['bg']}; border-radius: 12px;")

        # Create all panels
        self.panel_stack.addWidget(CameraPanel())
        self.panel_stack.addWidget(AIChatPanel())
        self.panel_stack.addWidget(SensorsPanel())
        self.panel_stack.addWidget(TerminalPanel())

        content.addWidget(self.panel_stack, stretch=3)
        main_layout.addLayout(content)

        # Default to camera
        self.panel_stack.setCurrentIndex(0)

    def show_panel(self, action):
        panel_map = {
            "camera": 0, "ai_chat": 1, "sensors": 2, "terminal": 3,
        }
        if action in panel_map:
            self.panel_stack.setCurrentIndex(panel_map[action])

    def _start_status_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_status)
        self.timer.start(2000)
        self._update_status()

    def _update_status(self):
        try:
            temp = subprocess.run(["cat", "/sys/class/thermal/thermal_zone0/temp"], capture_output=True, text=True).stdout.strip()
            self.status.temp_label.setText(f"Temp: {int(temp)/1000:.1f}°C")
        except: pass
        self.status.time_label.setText(datetime.now().strftime("%H:%M:%S"))


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(COLORS["bg"]))
    palette.setColor(QPalette.WindowText, QColor(COLORS["text"]))
    palette.setColor(QPalette.Base, QColor(COLORS["card"]))
    palette.setColor(QPalette.Text, QColor(COLORS["text"]))
    palette.setColor(QPalette.Button, QColor(COLORS["card"]))
    palette.setColor(QPalette.ButtonText, QColor(COLORS["text"]))
    app.setPalette(palette)
    window = MainGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
