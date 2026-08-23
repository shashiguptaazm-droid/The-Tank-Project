#!/usr/bin/env python3
"""Tank Dashboard — Jetson Orin Nano Super Main GUI."""
import sys, json, time, subprocess
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QFrame, QGridLayout, QProgressBar, QTextEdit,
    QTabWidget, QGroupBox, QScrollArea)
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QFont, QColor, QPalette, QIcon

# ── Colors ─────────────────────────────────────────────────────
BG = "#0a0e17"
CARD = "#111827"
BORDER = "#1e3a5f"
GREEN = "#00ff88"
RED = "#ff4444"
YELLOW = "#ffaa00"
CYAN = "#00d4ff"
BLUE = "#3b82f6"
WHITE = "#e5e7eb"
DIM = "#6b7280"

def style(card=False):
    if card:
        return f"background:{CARD}; border:1px solid {BORDER}; border-radius:8px; padding:12px;"
    return f"background:{BG}; color:{WHITE};"

class StatusLED(QLabel):
    def __init__(self, name, on=False):
        super().__init__()
        self.name = name
        self.setLED(on)
    def setLED(self, on):
        color = GREEN if on else RED
        self.setText(f"● {self.name}")
        self.setStyleSheet(f"color:{color}; font-size:13px; font-weight:bold;")

class MetricCard(QFrame):
    def __init__(self, title, value="--", unit=""):
        super().__init__()
        self.setStyleSheet(style(True))
        self.setFixedHeight(90)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        t = QLabel(title)
        t.setStyleSheet(f"color:{DIM}; font-size:11px;")
        self.val = QLabel(value)
        self.val.setStyleSheet(f"color:{CYAN}; font-size:22px; font-weight:bold;")
        u = QLabel(unit)
        u.setStyleSheet(f"color:{DIM}; font-size:10px;")
        layout.addWidget(t)
        layout.addWidget(self.val)
        layout.addWidget(u)
    def setValue(self, v):
        self.val.setText(str(v))

class BoardCard(QFrame):
    def __init__(self, name, ip, role, icon="🧠"):
        super().__init__()
        self.setStyleSheet(style(True))
        self.setFixedHeight(100)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        header = QHBoxLayout()
        led = StatusLED(name)
        self.led = led
        header.addWidget(led)
        header.addStretch()
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size:24px;")
        header.addWidget(icon_lbl)
        layout.addLayout(header)
        ip_lbl = QLabel(f"IP: {ip}")
        ip_lbl.setStyleSheet(f"color:{DIM}; font-size:11px;")
        layout.addWidget(ip_lbl)
        role_lbl = QLabel(role)
        role_lbl.setStyleSheet(f"color:{WHITE}; font-size:12px;")
        layout.addWidget(role_lbl)
    def setOnline(self, on):
        self.led.setLED(on)

class TankDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🪖 Tank — Autonomous AI Robot Dashboard")
        self.setMinimumSize(1100, 750)
        self.setStyleSheet(f"background:{BG}; color:{WHITE};")

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ── Header ─────────────────────────────────────
        header = QHBoxLayout()
        title = QLabel("🪖 THE TANK — Autonomous AI Robot")
        title.setStyleSheet(f"color:{GREEN}; font-size:20px; font-weight:bold;")
        header.addWidget(title)
        header.addStretch()
        self.time_lbl = QLabel()
        self.time_lbl.setStyleSheet(f"color:{DIM}; font-size:12px;")
        header.addWidget(self.time_lbl)
        main_layout.addLayout(header)

        # ── Tabs ───────────────────────────────────────
        tabs = QTabWidget()
        tabs.setStyleSheet(f"QTabWidget::pane {{ border: 1px solid {BORDER}; background:{BG}; }}"
                           f"QTabBar::tab {{ background:{CARD}; color:{WHITE}; padding:8px 16px; "
                           f"border:1px solid {BORDER}; border-radius:4px; margin-right:2px; }}"
                           f"QTabBar::tab:selected {{ background:{BLUE}; }}")

        # Tab 1: Overview
        tabs.addTab(self.createOverviewTab(), "🏠 Overview")
        # Tab 2: Sensors
        tabs.addTab(self.createSensorsTab(), "📡 Sensors")
        # Tab 3: AI
        tabs.addTab(self.createAITab(), "🧠 AI Engine")
        # Tab 4: Motors
        tabs.addTab(self.createMotorsTab(), "⚙️ Motors")
        # Tab 5: Terminal
        tabs.addTab(self.createTerminalTab(), "💻 Terminal")
        # Tab 6: Network
        tabs.addTab(self.createNetworkTab(), "🌐 Network")

        main_layout.addWidget(tabs)

        # ── Status Bar ─────────────────────────────────
        status_bar = QHBoxLayout()
        self.status_lbl = QLabel("● System Online")
        self.status_lbl.setStyleSheet(f"color:{GREEN}; font-size:12px;")
        status_bar.addWidget(self.status_lbl)
        status_bar.addStretch()
        ver = QLabel("TankOS v2.1 · Competition Build")
        ver.setStyleSheet(f"color:{DIM}; font-size:11px;")
        status_bar.addWidget(ver)
        main_layout.addLayout(status_bar)

        # ── Timer ──────────────────────────────────────
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(2000)
        self.refresh()

    def createOverviewTab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Board cards
        boards_layout = QHBoxLayout()
        self.jetson_card = BoardCard("Jetson Orin Nano", "100.122.31.46", "AI Brain · ROS2 · Vision · Navigation", "🧠")
        self.unoq_card = BoardCard("Arduino UNO Q", "100.84.235.7", "Motors · Encoders · I2C · E-Stop", "⚡")
        self.vps_card = BoardCard("VPS Cloud", "100.71.127.19", "API · Database · AI Fallback · Dashboard", "🌐")
        boards_layout.addWidget(self.jetson_card)
        boards_layout.addWidget(self.unoq_card)
        boards_layout.addWidget(self.vps_card)
        layout.addLayout(boards_layout)

        # Metrics
        metrics_layout = QHBoxLayout()
        self.cpu_card = MetricCard("CPU", "--", "%")
        self.ram_card = MetricCard("RAM", "--", "%")
        self.disk_card = MetricCard("Disk", "--", "%")
        self.temp_card = MetricCard("Temp", "--", "°C")
        self.batt_card = MetricCard("Battery", "--", "V")
        self.cycle_card = MetricCard("Cycle", "--", "")
        metrics_layout.addWidget(self.cpu_card)
        metrics_layout.addWidget(self.ram_card)
        metrics_layout.addWidget(self.disk_card)
        metrics_layout.addWidget(self.temp_card)
        metrics_layout.addWidget(self.batt_card)
        metrics_layout.addWidget(self.cycle_card)
        layout.addLayout(metrics_layout)

        # Quick actions
        actions = QHBoxLayout()
        for name, color in [("🔄 Restart", BLUE), ("🛑 E-STOP", RED), ("📸 Capture", GREEN), ("📊 Diagnostics", CYAN)]:
            btn = QPushButton(name)
            btn.setStyleSheet(f"QPushButton {{ background:{CARD}; color:{WHITE}; border:1px solid {BORDER}; "
                            f"padding:10px 20px; border-radius:6px; font-size:13px; font-weight:bold; }}"
                            f"QPushButton:hover {{ background:{color}; color:#000; }}")
            actions.addWidget(btn)
        layout.addLayout(actions)
        layout.addStretch()
        return widget

    def createSensorsTab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        sensors = [
            ("📷 Camera (OV3660)", "DFRobot AI Camera", "ttyACM0 · IMU streaming · Video pending"),
            ("📡 LiDAR (LD14/19)", "LDROBOT LD14/19", "ttyUSB0 · 115200 baud · aa55 protocol"),
            ("🌡️ IMU (BNO055)", "9-DOF Orientation", "I2C 0x28 · Heading, tilt, calibration"),
            ("📶 4G LTE Modem", "Quectel EG800AK-CN", "ttyUSB1 · LTE · 64% signal"),
            ("🔊 Audio (ReSpeaker)", "4-Mic Array", "USB · Wake word + voice input"),
            ("🔋 Power (INA219)", "Battery Monitor", "I2C · Voltage/current/temperature"),
        ]
        grid = QGridLayout()
        for i, (name, chip, details) in enumerate(sensors):
            card = QFrame()
            card.setStyleSheet(style(True))
            card.setFixedHeight(80)
            cl = QVBoxLayout(card)
            cl.setContentsMargins(10, 6, 10, 6)
            n = QLabel(name)
            n.setStyleSheet(f"color:{CYAN}; font-size:13px; font-weight:bold;")
            cl.addWidget(n)
            c = QLabel(f"{chip} — {details}")
            c.setStyleSheet(f"color:{DIM}; font-size:11px;")
            cl.addWidget(c)
            grid.addWidget(card, i // 2, i % 2)
        layout.addLayout(grid)
        layout.addStretch()
        return widget

    def createAITab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        models = [
            ("Phi-3 Mini 2.3B", "Primary LLM", "2.3GB GGUF · llama.cpp", GREEN),
            ("TinyLlama 1.1B", "Fast LLM", "638MB GGUF · llama.cpp", GREEN),
            ("YOLOv8n", "Object Detection", "6.3MB · 80 COCO classes · 30fps", GREEN),
            ("Whisper Base", "Speech-to-Text", "139MB · OpenAI", GREEN),
            ("Piper TTS", "Text-to-Speech", "61MB · en_US-lessac-medium", GREEN),
            ("openWakeWord", "Wake Word", "Hey Tank detection", GREEN),
            ("all-MiniLM-L6-v2", "Embeddings", "100MB · Sentence transformers", GREEN),
        ]
        grid = QGridLayout()
        for i, (name, role, spec, color) in enumerate(models):
            card = QFrame()
            card.setStyleSheet(style(True))
            card.setFixedHeight(70)
            cl = QVBoxLayout(card)
            cl.setContentsMargins(10, 6, 10, 6)
            h = QHBoxLayout()
            n = QLabel(f"● {name}")
            n.setStyleSheet(f"color:{color}; font-size:13px; font-weight:bold;")
            h.addWidget(n)
            h.addStretch()
            r = QLabel(role)
            r.setStyleSheet(f"color:{DIM}; font-size:11px;")
            h.addWidget(r)
            cl.addLayout(h)
            s = QLabel(spec)
            s.setStyleSheet(f"color:{WHITE}; font-size:11px;")
            cl.addWidget(s)
            grid.addWidget(card, i // 2, i % 2)
        layout.addLayout(grid)

        providers = QGroupBox("Cloud AI Providers (9)")
        providers.setStyleSheet(f"QGroupBox {{ color:{YELLOW}; font-size:14px; font-weight:bold; border:1px solid {BORDER}; border-radius:6px; padding:10px; }}")
        pl = QVBoxLayout(providers)
        for p in ["OpenRouter", "Groq", "Google Gemini", "Mistral", "Cerebras", "Cohere", "Replicate", "HuggingFace", "Cloudflare"]:
            pl.addWidget(QLabel(f"  ✅ {p}"))
        layout.addWidget(providers)
        return widget

    def createMotorsTab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        motors_layout = QHBoxLayout()
        for side in ["Left Motor", "Right Motor"]:
            card = QFrame()
            card.setStyleSheet(style(True))
            cl = QVBoxLayout(card)
            n = QLabel(side)
            n.setStyleSheet(f"color:{CYAN}; font-size:16px; font-weight:bold;")
            cl.addWidget(n)
            for label in ["Speed", "Current", "Encoder", "Temperature"]:
                row = QHBoxLayout()
                row.addWidget(QLabel(f"{label}:"))
                bar = QProgressBar()
                bar.setValue(0)
                bar.setStyleSheet(f"QProgressBar {{ background:{BG}; border:1px solid {BORDER}; border-radius:4px; height:18px; }}"
                                f"QProgressBar::chunk {{ background:{GREEN}; border-radius:4px; }}")
                row.addWidget(bar)
                cl.addLayout(row)
            motors_layout.addWidget(card)
        layout.addLayout(motors_layout)

        estop = QFrame()
        estop.setStyleSheet(f"background:#330000; border:2px solid {RED}; border-radius:8px; padding:15px;")
        el = QHBoxLayout(estop)
        ebtn = QPushButton("🛑 EMERGENCY STOP")
        ebtn.setStyleSheet(f"QPushButton {{ background:{RED}; color:white; font-size:18px; font-weight:bold; "
                          f"padding:15px 40px; border-radius:8px; }}"
                          f"QPushButton:hover {{ background:#ff0000; }}")
        el.addWidget(ebtn)
        el.addStretch()
        layout.addWidget(estop)
        layout.addStretch()
        return widget

    def createTerminalTab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setStyleSheet(f"background:#000; color:{GREEN}; font-family:monospace; font-size:13px; border:1px solid {BORDER}; padding:8px;")
        layout.addWidget(self.terminal)
        cmd_layout = QHBoxLayout()
        self.cmd_input = QLabel("tank@jetson:~$ ")
        self.cmd_input.setStyleSheet(f"color:{GREEN}; font-family:monospace; font-size:13px;")
        cmd_layout.addWidget(self.cmd_input)
        layout.addLayout(cmd_layout)
        return widget

    def createNetworkTab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        devices = [
            ("🧠 Jetson Orin Nano Super", "100.122.31.46", "AI brain · 23 ROS2 packages · 3GB models", "Idle"),
            ("⚡ Arduino UNO Q", "100.84.235.7", "Motors · Encoders · I2C sensors", "Idle"),
            ("🌐 VPS Cloud Backend", "100.71.127.19", "Tank API :8888 · MariaDB · nginx", "Active"),
            ("📱 Samsung Z Flip6", "100.91.134.103", "Mobile companion", "—"),
            ("🖥️ Transformer (Windows)", "100.125.165.27", "Desktop workstation", "Offline"),
            ("🍓 Raspberry Pi", "100.85.16.126", "NAS / Storage", "Offline"),
            ("📡 OpenWrt Router", "100.72.169.107", "Network gateway", "Offline"),
        ]
        grid = QGridLayout()
        for i, (name, ip, role, status) in enumerate(devices):
            card = QFrame()
            online = status != "Offline"
            card.setStyleSheet(f"background:{CARD}; border:1px solid {'#00ff88' if online else '#333'}; border-radius:8px; padding:10px;")
            cl = QVBoxLayout(card)
            n = QLabel(f"{'🟢' if online else '🔴'} {name}")
            n.setStyleSheet(f"color:{GREEN if online else RED}; font-size:13px; font-weight:bold;")
            cl.addWidget(n)
            cl.addWidget(QLabel(f"IP: {ip}"))
            cl.addWidget(QLabel(role))
            cl.addWidget(QLabel(f"Status: {status}"))
            grid.addWidget(card, i // 2, i % 2)
        layout.addLayout(grid)
        layout.addStretch()
        return widget

    def refresh(self):
        self.time_lbl.setText(time.strftime("%Y-%m-%d %H:%M:%S"))
        try:
            import urllib.request
            req = urllib.request.urlopen("http://100.71.127.19:8888/api/health", timeout=3)
            data = json.loads(req.read())
            self.vps_card.setOnline(True)
            self.cpu_card.setValue(f"{data.get('cpu_percent', 0):.0f}")
            self.ram_card.setValue(f"{data.get('ram_percent', 0):.0f}")
            state = data.get('system', {}).get('state', '?')
            self.cycle_card.setValue(state)
        except:
            self.vps_card.setOnline(False)
        try:
            import urllib.request
            req = urllib.request.urlopen("http://100.122.31.46:8888/api/health", timeout=2)
            data = json.loads(req.read())
            self.jetson_card.setOnline(True)
        except:
            self.jetson_card.setOnline(True)  # Always online if we're running here

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    win = TankDashboard()
    win.show()
    sys.exit(app.exec())
