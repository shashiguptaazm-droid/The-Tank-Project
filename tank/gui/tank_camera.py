#!/usr/bin/env python3
"""Tank Camera GUI — Live video feed from DFRobot AI Camera."""
import sys, io, time
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QFrame, QGridLayout, QComboBox, QSlider,
    QGroupBox, QStatusBar)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QFont, QImage, QPixmap
import urllib.request

BG = "#0a0e17"; CARD = "#111827"; BORDER = "#1e3a5f"
GREEN = "#00ff88"; RED = "#ff4444"; CYAN = "#00d4ff"
WHITE = "#e5e7eb"; DIM = "#6b7280"

CAMERA_IP = "192.168.31.176"
STREAM_URL = f"http://{CAMERA_IP}:81/stream"
CAPTURE_URL = f"http://{CAMERA_IP}/capture"
STATUS_URL = f"http://{CAMERA_IP}/status"

class StreamThread(QThread):
    frame_ready = Signal(bytes)
    error = Signal(str)
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.running = True
    def run(self):
        import urllib.request
        while self.running:
            try:
                req = urllib.request.urlopen(self.url, timeout=5)
                buf = b""
                while self.running:
                    chunk = req.read(1024)
                    if not chunk:
                        break
                    buf += chunk
                    # Find JPEG boundaries
                    while b"\xff\xd8" in buf and b"\xff\xd9" in buf:
                        start = buf.index(b"\xff\xd8")
                        end = buf.index(b"\xff\xd9", start) + 2
                        if start < end:
                            self.frame_ready.emit(buf[start:end])
                        buf = buf[end:]
            except Exception as e:
                self.error.emit(str(e))
                time.sleep(2)

class CameraGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📷 Tank Camera — Live Feed")
        self.setMinimumSize(1100, 750)
        self.setStyleSheet(f"background:{BG}; color:{WHITE};")
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Header
        header = QHBoxLayout()
        title = QLabel("📷 TANK CAMERA — DFRobot ESP32-S3 AI Camera V1.1")
        title.setStyleSheet(f"color:{GREEN}; font-size:18px; font-weight:bold;")
        header.addWidget(title)
        header.addStretch()
        self.status_led = QLabel("● Connecting...")
        self.status_led.setStyleSheet(f"color:{YELLOW}; font-size:14px;")
        header.addWidget(self.status_led)
        layout.addLayout(header)

        main = QHBoxLayout()

        # Video feed
        video_frame = QFrame()
        video_frame.setStyleSheet(f"background:#000; border:2px solid {BORDER}; border-radius:8px;")
        vl = QVBoxLayout(video_frame)
        self.video_label = QLabel("Connecting to camera...")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet("color:#666; font-size:16px;")
        vl.addWidget(self.video_label)
        main.addWidget(video_frame, 3)

        # Side panel
        side = QVBoxLayout()

        # Controls
        ctrl = QGroupBox("Controls")
        ctrl.setStyleSheet(f"QGroupBox {{ color:{CYAN}; font-size:13px; font-weight:bold; border:1px solid {BORDER}; border-radius:6px; padding:10px; }}")
        cl = QVBoxLayout(ctrl)
        self.btn_capture = QPushButton("📸 Capture Snapshot")
        self.btn_capture.setStyleSheet(f"QPushButton {{ background:{CARD}; color:{WHITE}; border:1px solid {BORDER}; padding:10px; border-radius:6px; font-size:13px; }} QPushButton:hover {{ background:{GREEN}; color:#000; }}")
        self.btn_capture.clicked.connect(self.capture)
        cl.addWidget(self.btn_capture)
        self.btn_stream = QPushButton("🔄 Reconnect Stream")
        self.btn_stream.setStyleSheet(f"QPushButton {{ background:{CARD}; color:{WHITE}; border:1px solid {BORDER}; padding:10px; border-radius:6px; font-size:13px; }} QPushButton:hover {{ background:{CYAN}; color:#000; }}")
        self.btn_stream.clicked.connect(self.reconnect)
        cl.addWidget(self.btn_stream)
        side.addWidget(ctrl)

        # Info
        info = QGroupBox("Camera Info")
        info.setStyleSheet(f"QGroupBox {{ color:{CYAN}; font-size:13px; font-weight:bold; border:1px solid {BORDER}; border-radius:6px; padding:10px; }}")
        il = QVBoxLayout(info)
        self.info_labels = {}
        for key in ["Camera", "WiFi", "IP", "Uptime", "PSRAM", "Resolution", "FPS"]:
            row = QHBoxLayout()
            k = QLabel(f"{key}:")
            k.setStyleSheet(f"color:{DIM}; font-size:12px;")
            v = QLabel("--")
            v.setStyleSheet(f"color:{WHITE}; font-size:12px;")
            self.info_labels[key] = v
            row.addWidget(k)
            row.addWidget(v)
            il.addLayout(row)
        side.addWidget(info)

        # Quick actions
        actions = QGroupBox("Quick Actions")
        actions.setStyleSheet(f"QGroupBox {{ color:{CYAN}; font-size:13px; font-weight:bold; border:1px solid {BORDER}; border-radius:6px; padding:10px; }}")
        al = QVBoxLayout(actions)
        for name in ["🔍 Detect Objects", "🎯 Track Target", "🌙 Night Vision", "📊 Diagnostics"]:
            btn = QPushButton(name)
            btn.setStyleSheet(f"QPushButton {{ background:{CARD}; color:{WHITE}; border:1px solid {BORDER}; padding:8px; border-radius:6px; font-size:12px; }} QPushButton:hover {{ background:{CYAN}; color:#000; }}")
            al.addWidget(btn)
        side.addWidget(actions)
        side.addStretch()
        main.addLayout(side, 1)

        layout.addLayout(main)

        # Status bar
        sb = QHBoxLayout()
        self.fps_lbl = QLabel("FPS: --")
        self.fps_lbl.setStyleSheet(f"color:{GREEN}; font-size:13px;")
        sb.addWidget(self.fps_lbl)
        sb.addStretch()
        self.frames_lbl = QLabel("Frames: 0")
        self.frames_lbl.setStyleSheet(f"color:{DIM}; font-size:12px;")
        sb.addWidget(self.frames_lbl)
        layout.addLayout(sb)

        self.frame_count = 0
        self.last_frame_time = time.time()
        self.fps_values = []

        # Start stream
        self.stream_thread = StreamThread(STREAM_URL)
        self.stream_thread.frame_ready.connect(self.on_frame)
        self.stream_thread.error.connect(self.on_error)
        self.stream_thread.start()

        # Status timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(3000)
        self.update_status()

    def on_frame(self, jpeg_data):
        self.frame_count += 1
        now = time.time()
        dt = now - self.last_frame_time
        if dt > 0:
            self.fps_values.append(1.0/dt)
            if len(self.fps_values) > 30:
                self.fps_values.pop(0)
            avg_fps = sum(self.fps_values)/len(self.fps_values)
            self.fps_lbl.setText(f"FPS: {avg_fps:.1f}")
        self.last_frame_time = now
        self.frames_lbl.setText(f"Frames: {self.frame_count}")

        pixmap = QPixmap()
        pixmap.loadFromData(jpeg_data)
        if not pixmap.isNull():
            scaled = pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.video_label.setPixmap(scaled)

    def on_error(self, err):
        self.status_led.setText("● Error")
        self.status_led.setStyleSheet(f"color:{RED}; font-size:14px;")

    def capture(self):
        try:
            data = urllib.request.urlopen(CAPTURE_URL, timeout=5).read()
            fname = f"/home/shashi/Desktop/capture_{int(time.time())}.jpg"
            with open(fname, "wb") as f:
                f.write(data)
            self.status_led.setText(f"📸 Saved: {fname.split('/')[-1]}")
            self.status_led.setStyleSheet(f"color:{GREEN}; font-size:14px;")
        except Exception as e:
            self.status_led.setText(f"❌ Capture failed: {e}")
            self.status_led.setStyleSheet(f"color:{RED}; font-size:14px;")

    def reconnect(self):
        if self.stream_thread.isRunning():
            self.stream_thread.running = False
            self.stream_thread.wait(1000)
        self.stream_thread = StreamThread(STREAM_URL)
        self.stream_thread.frame_ready.connect(self.on_frame)
        self.stream_thread.error.connect(self.on_error)
        self.stream_thread.start()
        self.status_led.setText("● Reconnecting...")
        self.status_led.setStyleSheet(f"color:{YELLOW}; font-size:14px;")

    def update_status(self):
        try:
            data = urllib.request.urlopen(STATUS_URL, timeout=3).read()
            import json
            info = json.loads(data)
            self.info_labels["Camera"].setText(info.get("camera", "--"))
            self.info_labels["WiFi"].setText(info.get("wifi", "--"))
            self.info_labels["IP"].setText(info.get("ip", "--"))
            self.info_labels["Uptime"].setText(f"{info.get('uptime', 0)}s")
            self.info_labels["PSRAM"].setText("✅ Yes" if info.get("psram") else "❌ No")
            self.info_labels["Resolution"].setText("640×480")
            self.status_led.setText("● Online")
            self.status_led.setStyleSheet(f"color:{GREEN}; font-size:14px;")
        except:
            self.status_led.setText("● Offline")
            self.status_led.setStyleSheet(f"color:{RED}; font-size:14px;")

    def closeEvent(self, event):
        self.stream_thread.running = False
        self.stream_thread.wait(2000)
        event.accept()

YELLOW = "#ffaa00"
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    win = CameraGUI()
    win.show()
    sys.exit(app.exec())
