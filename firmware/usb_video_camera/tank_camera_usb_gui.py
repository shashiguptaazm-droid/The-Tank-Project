#!/usr/bin/env python3
"""
tank_camera_usb_gui.py - Tank USB Camera Viewer
Live video feed from DFRobot AI Camera over USB serial.
No WiFi needed — direct USB connection.
"""
import sys
import time
import serial
import glob
import threading
import struct
import os
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSpinBox, QGroupBox, QFrame,
    QStatusBar, QSplitter, QTabWidget, QTextEdit, QMessageBox
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QThread
from PySide6.QtGui import QImage, QPixmap, QFont, QColor, QPalette, QIcon

BAUD = 921600
SAVE_DIR = os.path.expanduser("~/The-Tank-Project/data/frames")


class CameraWorker(QThread):
    """Background thread for camera frame capture"""
    frame_ready = Signal(bytes, int, int, int)  # jpeg_data, width, height, size
    status_update = Signal(str)
    error = Signal(str)
    imu_update = Signal(float, float, float, float, float, float)

    def __init__(self, port):
        super().__init__()
        self.port = port
        self.running = False
        self.streaming = False
        self.serial_conn = None
        self._lock = threading.Lock()

    def connect_camera(self):
        try:
            self.serial_conn = serial.Serial(self.port, BAUD, timeout=10)
            time.sleep(0.5)
            self.serial_conn.read(self.serial_conn.in_waiting)
            self.status_update.emit(f"Connected to {self.port}")
            return True
        except Exception as e:
            self.error.emit(f"Connection failed: {e}")
            return False

    def send_command(self, cmd):
        with self._lock:
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.write(f"{cmd}\n".encode())

    def snap_frame(self):
        """Capture a single JPEG frame"""
        with self._lock:
            if not self.serial_conn or not self.serial_conn.is_open:
                return None, 0, 0, 0

            self.serial_conn.read(self.serial_conn.in_waiting)
            self.serial_conn.write(b"SNAP\n")

        # Read header
        header = b""
        deadline = time.time() + 5
        with self._lock:
            while time.time() < deadline:
                c = self.serial_conn.read(1)
                if not c:
                    continue
                header += c
                if c == b"\n":
                    break

        header_str = header.decode("utf-8", errors="replace").strip()
        if not header_str.startswith("FRAME:"):
            return None, 0, 0, 0

        parts = header_str.split(":")
        width = int(parts[1])
        height = int(parts[2])
        expected_size = int(parts[3])

        # Read exact JPEG bytes
        jpeg_data = b""
        deadline = time.time() + 10
        with self._lock:
            while len(jpeg_data) < expected_size and time.time() < deadline:
                remaining = expected_size - len(jpeg_data)
                chunk = self.serial_conn.read(min(remaining, 16384))
                if chunk:
                    jpeg_data += chunk
                    deadline = time.time() + 2
            # Read trailing newline
            self.serial_conn.read(1)

        return jpeg_data, width, height, expected_size

    def read_imu(self):
        """Read IMU data from camera"""
        with self._lock:
            if not self.serial_conn:
                return
            self.serial_conn.read(self.serial_conn.in_waiting)
            self.serial_conn.write(b"IMU\n")
            time.sleep(0.3)
            data = self.serial_conn.read(200).decode("utf-8", errors="replace")

        for line in data.split("\n"):
            line = line.strip()
            if line.startswith("IMU:"):
                parts = line.split(":")
                if len(parts) >= 7:
                    try:
                        vals = [float(x) for x in parts[1:7]]
                        self.imu_update.emit(*vals)
                    except:
                        pass

    def run(self):
        if not self.connect_camera():
            return

        self.running = True
        while self.running:
            if self.streaming:
                jpeg, w, h, size = self.snap_frame()
                if jpeg and len(jpeg) > 500:
                    self.frame_ready.emit(jpeg, w, h, size)
                else:
                    time.sleep(0.1)
            else:
                time.sleep(0.2)

    def stop(self):
        self.running = False
        self.wait(3000)
        if self.serial_conn:
            try:
                self.serial_conn.close()
            except:
                pass


class TankCameraGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔭 Tank USB Camera — DFRobot AI Camera v1.1")
        self.setMinimumSize(900, 700)
        self.setMinimumSize(800, 600)
        self.camera_worker = None
        self.frame_count = 0
        self.recording = False
        self.capture_dir = SAVE_DIR
        os.makedirs(self.capture_dir, exist_ok=True)

        self._setup_ui()
        self._setup_styles()
        self._detect_camera()
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_status)
        self._update_timer.start(1000)

        # IMU read timer
        self._imu_timer = QTimer()
        self._imu_timer.timeout.connect(self._read_imu)
        self._imu_timer.start(500)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(6)

        # === TOP BAR ===
        top_bar = QHBoxLayout()
        
        title = QLabel("🔭 TANK USB CAMERA")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #00ff88;")
        top_bar.addWidget(title)
        
        top_bar.addStretch()
        
        self.status_label = QLabel("⚫ Disconnected")
        self.status_label.setStyleSheet("font-size: 12px; color: #ff6b6b;")
        top_bar.addWidget(self.status_label)
        
        self.fps_label = QLabel("0 FPS")
        self.fps_label.setStyleSheet("font-size: 12px; color: #ffd93d;")
        top_bar.addWidget(self.fps_label)
        
        self.frame_count_label = QLabel("Frames: 0")
        self.frame_count_label.setStyleSheet("font-size: 12px; color: #6bcb77;")
        top_bar.addWidget(self.frame_count_label)
        
        main_layout.addLayout(top_bar)

        # === MAIN CONTENT ===
        content = QHBoxLayout()
        
        # Left: Video feed
        video_frame = QFrame()
        video_frame.setStyleSheet("QFrame { background: #1a1a2e; border: 2px solid #333; border-radius: 8px; }")
        video_layout = QVBoxLayout(video_frame)
        
        self.video_label = QLabel("📷 No Signal\nConnect camera via USB")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("font-size: 24px; color: #666; background: #0d0d1a; min-height: 400px;")
        self.video_label.setMinimumSize(640, 480)
        video_layout.addWidget(self.video_label)
        
        content.addWidget(video_frame, stretch=3)
        
        # Right: Controls + Info
        right_panel = QVBoxLayout()
        
        # Connection
        conn_group = QGroupBox("🔌 Connection")
        conn_layout = QVBoxLayout()
        
        self.port_combo = QComboBox()
        self.port_combo.addItems(glob.glob("/dev/ttyACM*") + ["/dev/ttyACM0"])
        conn_layout.addWidget(self.port_combo)
        
        btn_row = QHBoxLayout()
        self.connect_btn = QPushButton("🟢 Connect")
        self.connect_btn.clicked.connect(self._toggle_connection)
        btn_row.addWidget(self.connect_btn)
        
        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setMaximumWidth(40)
        self.refresh_btn.clicked.connect(self._detect_camera)
        btn_row.addWidget(self.refresh_btn)
        conn_layout.addLayout(btn_row)
        
        conn_group.setLayout(conn_layout)
        right_panel.addWidget(conn_group)
        
        # Capture Controls
        capture_group = QGroupBox("📷 Controls")
        capture_layout = QVBoxLayout()
        
        self.snap_btn = QPushButton("📸 Single Capture")
        self.snap_btn.clicked.connect(self._snap_single)
        capture_layout.addWidget(self.snap_btn)
        
        stream_row = QHBoxLayout()
        self.stream_btn = QPushButton("▶️ Start Stream")
        self.stream_btn.clicked.connect(self._toggle_stream)
        stream_row.addWidget(self.stream_btn)
        
        self.record_btn = QPushButton("🔴 Record")
        self.record_btn.clicked.connect(self._toggle_record)
        stream_row.addWidget(self.record_btn)
        capture_layout.addLayout(stream_row)
        
        capture_group.setLayout(capture_layout)
        right_panel.addWidget(capture_group)
        
        # Resolution
        res_group = QGroupBox("📐 Resolution")
        res_layout = QHBoxLayout()
        
        self.res_combo = QComboBox()
        self.res_combo.addItems(["QVGA (320×240)", "VGA (640×480)", "SVGA (800×600)", "XGA (1024×768)"])
        self.res_combo.setCurrentIndex(1)
        self.res_combo.currentIndexChanged.connect(self._change_resolution)
        res_layout.addWidget(self.res_combo)
        
        res_group.setLayout(res_layout)
        right_panel.addWidget(res_group)
        
        # IMU
        imu_group = QGroupBox("🧭 IMU Data")
        imu_layout = QVBoxLayout()
        
        self.imu_label = QLabel("Acc: ---.--- / ---.--- / ---.---\nGyr: ---.--- / ---.--- / ---.---")
        self.imu_label.setStyleSheet("font-family: monospace; font-size: 11px;")
        imu_layout.addWidget(self.imu_label)
        
        imu_group.setLayout(imu_layout)
        right_panel.addWidget(imu_group)
        
        # Info
        info_group = QGroupBox("ℹ️ Info")
        info_layout = QVBoxLayout()
        
        self.info_label = QLabel("Protocol: USB Serial 921600 baud\nNo WiFi required\nDirect USB connection")
        self.info_label.setStyleSheet("font-size: 10px; color: #aaa;")
        self.info_label.setWordWrap(True)
        info_layout.addWidget(self.info_label)
        
        info_group.setLayout(info_layout)
        right_panel.addWidget(info_group)
        
        right_panel.addStretch()
        content.addLayout(right_panel, stretch=1)
        
        main_layout.addLayout(content)

        # === BOTTOM: Log ===
        log_group = QGroupBox("📋 Log")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(80)
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("font-family: monospace; font-size: 10px; background: #0d0d1a; color: #00ff88;")
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)

    def _setup_styles(self):
        self.setStyleSheet("""
            QMainWindow { background: #16213e; }
            QGroupBox { 
                font-weight: bold; color: #e0e0e0; border: 1px solid #333; 
                border-radius: 6px; margin-top: 8px; padding-top: 16px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QPushButton { 
                padding: 6px 12px; border-radius: 4px; font-weight: bold;
                background: #0f3460; color: #e0e0e0; border: 1px solid #1a5276;
            }
            QPushButton:hover { background: #1a5276; }
            QPushButton:pressed { background: #2980b9; }
            QComboBox, QSpinBox { 
                padding: 4px; background: #1a1a2e; color: #e0e0e0; 
                border: 1px solid #333; border-radius: 4px;
            }
            QLabel { color: #e0e0e0; }
        """)

    def _detect_camera(self):
        self.port_combo.clear()
        ports = sorted(glob.glob("/dev/ttyACM*"))
        if not ports:
            ports = ["/dev/ttyACM0"]
        self.port_combo.addItems(ports)
        self._log(f"Found {len(ports)} serial port(s): {ports}")

    def _log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {msg}")

    def _toggle_connection(self):
        if self.camera_worker and self.camera_worker.is_running:
            self.camera_worker.stop()
            self.camera_worker = None
            self.connect_btn.setText("🟢 Connect")
            self.status_label.setText("⚫ Disconnected")
            self.status_label.setStyleSheet("font-size: 12px; color: #ff6b6b;")
            self._log("Disconnected")
        else:
            port = self.port_combo.currentText()
            self.camera_worker = CameraWorker(port)
            self.camera_worker.frame_ready.connect(self._on_frame)
            self.camera_worker.status_update.connect(self._on_status)
            self.camera_worker.error.connect(self._on_error)
            self.camera_worker.imu_update.connect(self._on_imu)
            self.camera_worker.start()
            self.connect_btn.setText("🔴 Disconnect")
            self.status_label.setText("🟡 Connecting...")
            self.status_label.setStyleSheet("font-size: 12px; color: #ffd93d;")
            self._log(f"Connecting to {port}...")

    def _on_frame(self, jpeg_data, width, height, size):
        self.frame_count += 1
        self.frame_count_label.setText(f"Frames: {self.frame_count}")
        
        # Decode JPEG to QImage
        img = QImage.fromData(jpeg_data)
        if not img.isNull():
            pixmap = QPixmap.fromImage(img)
            scaled = pixmap.scaled(
                self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.video_label.setPixmap(scaled)
        
        # Record if active
        if self.recording:
            fname = os.path.join(
                self.capture_dir,
                f"rec_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
            )
            with open(fname, "wb") as f:
                f.write(jpeg_data)
            self._log(f"💾 Recorded frame #{self.frame_count}")

    def _on_status(self, msg):
        self.status_label.setText(f"🟢 {msg}")
        self.status_label.setStyleSheet("font-size: 12px; color: #6bcb77;")
        self._log(msg)

    def _on_error(self, msg):
        self.status_label.setText(f"🔴 {msg}")
        self.status_label.setStyleSheet("font-size: 12px; color: #ff6b6b;")
        self._log(f"ERROR: {msg}")

    def _on_imu(self, ax, ay, az, gx, gy, gz):
        self.imu_label.setText(
            f"Acc: {ax:+.3f} / {ay:+.3f} / {az:+.3f} g\n"
            f"Gyr: {gx:+.1f} / {gy:+.1f} / {gz:+.1f} °/s"
        )

    def _snap_single(self):
        if not self.camera_worker or not self.camera_worker.serial_conn:
            self._log("⚠️ Not connected")
            return
        
        def do_snap():
            jpeg, w, h, size = self.camera_worker.snap_frame()
            if jpeg and len(jpeg) > 500:
                fname = os.path.join(
                    self.capture_dir,
                    f"snap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                )
                with open(fname, "wb") as f:
                    f.write(jpeg)
                self._log(f"📸 Captured {len(jpeg)} bytes → {fname}")
                self.camera_worker.frame_ready.emit(jpeg, w, h, size)
            else:
                self._log("❌ Capture failed")
        
        threading.Thread(target=do_snap, daemon=True).start()

    def _toggle_stream(self):
        if not self.camera_worker:
            return
        self.camera_worker.streaming = not self.camera_worker.streaming
        if self.camera_worker.streaming:
            self.stream_btn.setText("⏸️ Stop Stream")
            self._log("▶️ Streaming started")
        else:
            self.stream_btn.setText("▶️ Start Stream")
            self._log("⏸️ Streaming stopped")

    def _toggle_record(self):
        self.recording = not self.recording
        if self.recording:
            self.record_btn.setText("⏹️ Stop Recording")
            self._log("🔴 Recording started")
        else:
            self.record_btn.setText("🔴 Record")
            self._log("⏹️ Recording stopped")

    def _change_resolution(self, idx):
        if not self.camera_worker:
            return
        res_map = {0: 5, 1: 8, 2: 9, 3: 10}
        cmd = f"RES {res_map.get(idx, 8)}"
        self.camera_worker.send_command(cmd)
        self._log(f"📐 Resolution: {self.res_combo.currentText()}")

    def _read_imu(self):
        if self.camera_worker and self.camera_worker.serial_conn:
            threading.Thread(
                target=self.camera_worker.read_imu, daemon=True
            ).start()

    def _update_status(self):
        pass

    def closeEvent(self, event):
        if self.camera_worker:
            self.camera_worker.stop()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    dark = QPalette()
    dark.setColor(QPalette.Window, QColor(22, 33, 62))
    dark.setColor(QPalette.WindowText, QColor(224, 224, 224))
    dark.setColor(QPalette.Base, QColor(26, 26, 46))
    dark.setColor(QPalette.AlternateBase, QColor(22, 33, 62))
    dark.setColor(QPalette.ToolTipBase, QColor(224, 224, 224))
    dark.setColor(QPalette.ToolTipText, QColor(224, 224, 224))
    dark.setColor(QPalette.Text, QColor(224, 224, 224))
    dark.setColor(QPalette.Button, QColor(15, 52, 96))
    dark.setColor(QPalette.ButtonText, QColor(224, 224, 224))
    dark.setColor(QPalette.BrightText, QColor(255, 0, 0))
    dark.setColor(QPalette.Link, QColor(42, 130, 218))
    dark.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark.setColor(QPalette.HighlightedText, QColor(35, 35, 35))
    app.setPalette(dark)
    
    window = TankCameraGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
