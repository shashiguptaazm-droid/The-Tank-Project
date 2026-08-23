"""
TankOS Runbook GUI — 100 Hardware-Specific Features (301-400)
===============================================================
Tailored to actual hardware:
  - Jetson Orin Nano Super (JetPack 6.2, CUDA, 67 TOPS)
  - Arduino UNO Q 4GB (QRB2210 + STM32U585)
  - 6× ESP32-S3 (motor, sensor, arm, battery, LTE, comms)
  - DFRobot AI Camera (OV3660, USB, http://192.168.31.176:81/stream)
  - LDROBOT LD19 LiDAR (/dev/ttyUSB0, 115200 baud)
  - Quectel EG800AK 4G modem
  - PCA9685 servo driver (I²C 0x40)
  - BTS7960 motor drivers ×2
  - INA219 power monitors ×2
  - BNO055 IMU (I²C 0x28)
  - Tailscale VPN mesh
  - VPS (Hetzner, medicscholar.medigyaan.com)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class Panel(Enum):
    DASHBOARD = "dashboard"
    CAMERA = "camera"
    LIDAR = "lidar"
    MOTOR = "motor"
    AI_LLM = "ai_llm"
    NETWORK = "network"
    ROS2 = "ros2"
    TELEMETRY = "telemetry"


class FeatureStatus(Enum):
    LIVE = "live"        # Working on actual hardware
    SIMULATED = "sim"    # Works in simulation
    PLANNED = "planned"  # Not yet implemented


@dataclass
class RunbookFeature:
    """A single hardware-specific GUI feature."""
    id: int
    name: str
    description: str
    panel: Panel
    status: FeatureStatus = FeatureStatus.LIVE
    icon: str = ""
    hardware_deps: list[str] = field(default_factory=list)
    software_deps: list[str] = field(default_factory=list)
    endpoint: str = ""        # URL or device path
    update_hz: float = 1.0    # Refresh rate
    category: str = ""


class RunbookFeatureRegistry:
    """Registry of all 100 hardware-specific features."""

    def __init__(self):
        self._features: dict[int, RunbookFeature] = {}
        self._register_all()

    def _add(self, id: int, name: str, desc: str, panel: Panel,
             icon: str = "", hw: list[str] | None = None,
             sw: list[str] | None = None, endpoint: str = "",
             hz: float = 1.0, cat: str = "",
             status: FeatureStatus = FeatureStatus.LIVE):
        self._features[id] = RunbookFeature(
            id=id, name=name, description=desc, panel=panel,
            icon=icon, hardware_deps=hw or [], software_deps=sw or [],
            endpoint=endpoint, update_hz=hz, category=cat, status=status
        )

    def _register_all(self):
        D = Panel.DASHBOARD
        C = Panel.CAMERA
        L = Panel.LIDAR
        M = Panel.MOTOR
        A = Panel.AI_LLM
        N = Panel.NETWORK
        R = Panel.ROS2
        T = Panel.TELEMETRY
        S = FeatureStatus.SIMULATED

        # ═══ 301-315: Dashboard & Overview ═══
        self._add(301, "Tailscale Status Bar",
                  "Show Tailscale IPs + live ping latencies for Jetson/UNO Q/VPS",
                  D, icon="🌐", sw=["tailscale"],
                  endpoint="tailscale status", hz=0.5, cat="network")
        self._add(302, "Hardware Inventory",
                  "List 8 USB devices with green/yellow/red status",
                  D, icon="🔌", hw=["usb"],
                  endpoint="lsusb", hz=0.2, cat="hardware")
        self._add(303, "Three-Board Architecture",
                  "Visualize Jetson↔UNO Q↔VPS with live data flow arrows",
                  D, icon="🏗️", sw=["tailscale"],
                  endpoint="network_mesh", hz=1.0, cat="architecture")
        self._add(304, "Deployment Phase",
                  "Show current pipeline step: Sense→Perceive→…→Learn",
                  D, icon="📊", sw=["tankos"],
                  endpoint="orchestrator_state", hz=0.5, cat="pipeline")
        self._add(305, "Competition Progress",
                  "Track demo sequence progress (e.g., 5/5 cycles)",
                  D, icon="🏆", sw=["tankos"],
                  endpoint="mission_progress", hz=0.2, cat="competition")
        self._add(306, "AI Provider Health",
                  "Status + last response time for 9 API providers",
                  D, icon="🧠", sw=["ai_providers"],
                  endpoint="ai_health", hz=0.2, cat="ai")
        self._add(307, "ROS2 Package List",
                  "Display 23 built packages with node/topic details",
                  D, icon="📦", sw=["ros2"],
                  endpoint="ros2 pkg list", hz=0.1, cat="ros2")
        self._add(308, "Network Failover State",
                  "Active connection + failover history log",
                  D, icon="🔄", sw=["networking"],
                  endpoint="failover_state", hz=1.0, cat="network")
        self._add(309, "Storage Overview",
                  "Jetson SD (59GB free), VPS (290GB), USB drives",
                  D, icon="💾", sw=["storage"],
                  endpoint="df -h", hz=0.1, cat="system")
        self._add(310, "Power Rail Monitor",
                  "Voltage/current for AI(19V), Motor(12V), Logic(5V), Pebble Rails",
                  D, icon="⚡", hw=["ina219"],
                  endpoint="power/status", hz=2.0, cat="power")
        self._add(311, "Model Inventory",
                  "All downloaded models with sizes and locations",
                  D, icon="🤖", sw=["models"],
                  endpoint="model_inventory", hz=0.1, cat="ai")
        self._add(312, "Session Timeline",
                  "Chronological log of major system events",
                  D, icon="📅", sw=["tankos"],
                  endpoint="event_log", hz=0.5, cat="logging")
        self._add(313, "System Metrics",
                  "CPU/RAM/GPU (nvidia-smi) for Jetson; CPU/RAM for VPS/UNO Q",
                  D, icon="📈", sw=["nvidia-smi"],
                  endpoint="system_metrics", hz=2.0, cat="system")
        self._add(314, "Temperature Gauges",
                  "Jetson SoC, motor drivers, battery pack temps",
                  D, icon="🌡️", hw=["thermal"],
                  endpoint="thermal/status", hz=1.0, cat="thermal")
        self._add(315, "Quick-Action Panel",
                  "ros2 launch, colcon build, hotspot-start, demo mode buttons",
                  D, icon="🚀", sw=["ros2", "tankos"],
                  endpoint="quick_actions", hz=0, cat="actions")

        # ═══ 316-330: Camera & Vision ═══
        self._add(316, "Multi-Stream Viewer",
                  "Live MJPEG from DFRobot (port 81) + ESP32 CAM (port 145)",
                  C, icon="📷", hw=["camera"],
                  endpoint="http://192.168.31.176:81/stream", hz=15.0, cat="vision")
        self._add(317, "Camera Settings",
                  "Resolution, FPS, exposure, white balance, IR-night mode",
                  C, icon="⚙️", hw=["camera"],
                  endpoint="camera/settings", hz=0, cat="vision")
        self._add(318, "YOLOv8n Overlay",
                  "Toggle bounding boxes, confidence, class labels on feed",
                  C, icon="🎯", hw=["camera"], sw=["yolo"],
                  endpoint="yolo/detect", hz=10.0, cat="vision")
        self._add(319, "Object Tracking",
                  "Click detected object to follow it",
                  C, icon="🔍", hw=["camera", "motor"], sw=["yolo", "tracker"],
                  endpoint="vision/track", hz=10.0, cat="vision")
        self._add(320, "Snapshot & Recording",
                  "Capture JPEG snapshots or record MP4 with timestamps",
                  C, icon="🎬", hw=["camera"],
                  endpoint="camera/record", hz=0, cat="vision")
        self._add(321, "Camera Health",
                  "FPS, PSRAM usage (8MB), sensor temp from /status",
                  C, icon="❤️", hw=["camera"],
                  endpoint="camera/health", hz=1.0, cat="vision")
        self._add(322, "Face Recognition",
                  "Display recognized faces with names",
                  C, icon="👤", hw=["camera"], sw=["face_recognition"],
                  endpoint="vision/faces", hz=5.0, cat="vision", status=S)
        self._add(323, "Gesture Overlay",
                  "Visual feedback for wave, peace sign, stop gestures",
                  C, icon="✋", hw=["camera"], sw=["gesture"],
                  endpoint="vision/gestures", hz=10.0, cat="vision", status=S)
        self._add(324, "Depth Estimation",
                  "Heatmap overlay for distance estimation (stereo)",
                  C, icon="🧊", hw=["camera"], sw=["depth"],
                  endpoint="vision/depth", hz=5.0, cat="vision", status=S)
        self._add(325, "Low-Light Booster",
                  "Manual gain control, IR cut filter toggle (OV3660)",
                  C, icon="🌙", hw=["camera"],
                  endpoint="camera/nightmode", hz=0, cat="vision")
        self._add(326, "Camera Calibration",
                  "Interactive checkerboard detection for lens correction",
                  C, icon="📐", hw=["camera"], sw=["opencv"],
                  endpoint="camera/calibrate", hz=0, cat="vision")
        self._add(327, "PiP (Picture-in-Picture)",
                  "Secondary camera preview in corner overlay",
                  C, icon="🖼️", hw=["camera"],
                  endpoint="camera/pip", hz=15.0, cat="vision")
        self._add(328, "Motion Detection Zones",
                  "Draw regions where motion triggers sentry alerts",
                  C, icon="🚨", hw=["camera"], sw=["motion"],
                  endpoint="vision/motion_zones", hz=10.0, cat="vision")
        self._add(329, "Stream Health Monitor",
                  "Bitrate, packet loss, latency of MJPEG stream",
                  C, icon="📊", hw=["camera"],
                  endpoint="camera/stream_health", hz=2.0, cat="vision")
        self._add(330, "Camera Flash Control",
                  "Toggle onboard LED flash (GPIO 47) on DFRobot",
                  C, icon="💡", hw=["camera"],
                  endpoint="gpio/47", hz=0, cat="vision")

        # ═══ 331-340: LiDAR & Mapping ═══
        self._add(331, "LiDAR Point Cloud",
                  "Render live scans from /dev/ttyUSB0 (LD19) with zoom",
                  L, icon="📡", hw=["lidar"],
                  endpoint="/dev/ttyUSB0", hz=10.0, cat="mapping")
        self._add(332, "Occupancy Grid Map",
                  "SLAM map from tank_sensors alongside camera feed",
                  L, icon="🗺️", hw=["lidar"], sw=["slam"],
                  endpoint="slam/map", hz=5.0, cat="mapping")
        self._add(333, "Robot Pose Overlay",
                  "x/y position + heading arrow on map",
                  L, icon="📍", sw=["slam"],
                  endpoint="slam/pose", hz=10.0, cat="mapping")
        self._add(334, "Path Planning Preview",
                  "A*/Dijkstra path with waypoints and no-go zones",
                  L, icon="🛤️", sw=["navigation"],
                  endpoint="nav/path", hz=2.0, cat="mapping")
        self._add(335, "LiDAR Health Panel",
                  "Baud rate (115200), protocol (aa55), scan freq, point count",
                  L, icon="❤️", hw=["lidar"],
                  endpoint="lidar/health", hz=1.0, cat="mapping")
        self._add(336, "Map Save/Load",
                  "Save current map, load previously saved map",
                  L, icon="💾", sw=["slam"],
                  endpoint="slam/save", hz=0, cat="mapping")
        self._add(337, "Exploration Coverage",
                  "Heatmap of mapped vs unmapped areas",
                  L, icon="🔥", hw=["lidar"], sw=["slam"],
                  endpoint="slam/coverage", hz=2.0, cat="mapping")
        self._add(338, "Obstacle Distance Indicators",
                  "Front/back/left/right distances as numeric + colour bars",
                  L, icon="📏", hw=["lidar"],
                  endpoint="lidar/distances", hz=10.0, cat="mapping")
        self._add(339, "Map Alignment Tool",
                  "Drag robot icon to correct localization drift",
                  L, icon="📐", sw=["slam"],
                  endpoint="slam/align", hz=0, cat="mapping")
        self._add(340, "Multi-Floor Support",
                  "Toggle between different floor maps",
          L, icon="🏢", sw=["slam"],
                  endpoint="slam/floors", hz=0, cat="mapping", status=S)

        # ═══ 341-355: Motor & Control ═══
        self._add(341, "Virtual Joystick",
                  "Differential drive mapping, touch-friendly for mobile",
                  M, icon="🎮", hw=["motor"],
                  endpoint="motor/joystick", hz=20.0, cat="control")
        self._add(342, "Speed Presets",
                  "Slow(0.2) / Medium(0.5) / Fast(1.0) / Turbo(1.5) m/s",
                  M, icon="⚡", hw=["motor"],
                  endpoint="motor/speed", hz=0, cat="control")
        self._add(343, "Emergency STOP",
                  "Large red button, cuts motor power via serial E-STOP",
                  M, icon="🛑", hw=["motor"],
                  endpoint="motor/estop", hz=0, cat="safety")
        self._add(344, "Motor Status Panel",
                  "PWM values, direction, encoder counts from UNO Q",
                  M, icon="⚙️", hw=["motor", "encoder"],
                  endpoint="motor/status", hz=20.0, cat="control")
        self._add(345, "PID Tuning",
                  "Adjust Kp/Ki/Kd for velocity and position in real-time",
                  M, icon="🔧", hw=["motor"],
                  endpoint="motor/pid", hz=0, cat="control")
        self._add(346, "Command Queue",
                  "Display pending actions with clear/reorder",
                  M, icon="📚", sw=["orchestrator"],
                  endpoint="command/queue", hz=1.0, cat="control")
        self._add(347, "Waypoint Manager",
                  "Add/remove/reorder GPS or map-based waypoints",
                  M, icon="📍", sw=["navigation"],
                  endpoint="nav/waypoints", hz=0, cat="navigation")
        self._add(348, "Manual Override",
                  "Hold-to-override AI with manual joystick input",
                  M, icon="🎮", hw=["motor"],
                  endpoint="motor/override", hz=20.0, cat="control")
        self._add(349, "Servo Control",
                  "Set angles for pan/tilt servos via PCA9685 with 3D preview",
                  M, icon="🦾", hw=["servo"],
                  endpoint="servo/set", hz=5.0, cat="control")
        self._add(350, "Motor Calibration",
                  "Step-by-step encoder offsets, max PWM, direction reversing",
                  M, icon="📐", hw=["motor"],
                  endpoint="motor/calibrate", hz=0, cat="control")
        self._add(351, "Odometry Reset",
                  "Reset distance and position to (0,0)",
                  M, icon="🔄", sw=["odometry"],
                  endpoint="odom/reset", hz=0, cat="control")
        self._add(352, "Crab Walk Mode",
                  "Lateral movement with slider (mecanum if equipped)",
                  M, icon="🦀", hw=["motor"],
                  endpoint="motor/crab", hz=10.0, cat="control", status=S)
        self._add(353, "Return to Home",
                  "One-click navigate back to starting coordinates",
                  M, icon="🏠", sw=["navigation"],
                  endpoint="nav/home", hz=0, cat="navigation")
        self._add(354, "Action Macro Recorder",
                  "Record movement sequences for playback",
                  M, icon="🎥", hw=["motor"],
                  endpoint="macro/record", hz=0, cat="control")
        self._add(355, "E-STOP History",
                  "Log of all emergency stop events with timestamps",
                  M, icon="📋", sw=["safety"],
                  endpoint="safety/estop_log", hz=0, cat="safety")

        # ═══ 356-370: AI & LLM Integration ═══
        self._add(356, "LLM Chat Interface",
                  "Type prompts, see streaming responses from TinyLlama/Phi-3",
                  A, icon="💬", sw=["llm"],
                  endpoint="ai/chat", hz=0.5, cat="ai")
        self._add(357, "Voice Command Input",
                  "Push-to-talk with ReSpeaker mic, Whisper STT",
                  A, icon="🎤", hw=["microphone"], sw=["whisper"],
                  endpoint="ai/voice", hz=0, cat="ai")
        self._add(358, "LLM Reasoning Trace",
                  "Show chain-of-thought for transparency",
                  A, icon="🧠", sw=["llm"],
                  endpoint="ai/reasoning", hz=1.0, cat="ai")
        self._add(359, "Model Switcher",
                  "Dropdown: TinyLlama / Phi-3 / cloud providers",
                  A, icon="🔄", sw=["llm", "providers"],
                  endpoint="ai/switch_model", hz=0, cat="ai")
        self._add(360, "AI Memory Browser",
                  "View sqlite-vec vector memory with search/filter",
                  A, icon="🧠", sw=["memory"],
                  endpoint="memory/browse", hz=0.5, cat="ai")
        self._add(361, "Emotion/Status Display",
                  "Robot mood: happy, alert, curious from tank_assistant",
                  A, icon="😊", sw=["assistant"],
                  endpoint="ai/mood", hz=1.0, cat="ai")
        self._add(362, "Wake Word Status",
                  "openWakeWord active indicator + confidence meter",
                  A, icon="🔊", hw=["microphone"], sw=["wakeword"],
                  endpoint="ai/wakeword", hz=5.0, cat="ai")
        self._add(363, "TTS Test Panel",
                  "Type text, hear Piper TTS; volume/voice selection",
                  A, icon="🗣️", sw=["piper"],
                  endpoint="ai/tts", hz=0, cat="ai")
        self._add(364, "YOLO Stats",
                  "Inference time, object count, confidence threshold slider",
                  A, icon="📊", sw=["yolo"],
                  endpoint="yolo/stats", hz=2.0, cat="ai")
        self._add(365, "AI Curiosity Engine",
                  "Curiosity score + novelty factors triggering exploration",
                  A, icon="🔬", sw=["curiosity"],
                  endpoint="ai/curiosity", hz=0.5, cat="ai")
        self._add(366, "Learning Scheduler",
                  "View active learning jobs, progress, enable/disable",
                  A, icon="📚", sw=["learning"],
                  endpoint="ai/learning", hz=0.2, cat="ai")
        self._add(367, "Prompt Templates",
                  "Save/load custom prompts for patrol, search, Q&A",
                  A, icon="📝", sw=["prompts"],
                  endpoint="ai/prompts", hz=0, cat="ai")
        self._add(368, "AI Decision Log",
                  "Recent decisions with reasoning and action taken",
                  A, icon="📋", sw=["orchestrator"],
                  endpoint="ai/decisions", hz=1.0, cat="ai")
        self._add(369, "Knowledge Graph Viewer",
                  "Visualize entities/relationships from tank_meta",
                  A, icon="🕸️", sw=["knowledge"],
                  endpoint="knowledge/graph", hz=0.2, cat="ai", status=S)
        self._add(370, "Cloud AI Failover",
                  "Auto-switch to cloud if local fails; show fallback status",
                  A, icon="🔄", sw=["providers"],
                  endpoint="ai/failover", hz=0.5, cat="ai")

        # ═══ 371-385: Network & Connectivity ═══
        self._add(371, "Network Topology Map",
                  "All Tailscale devices with IPs, roles, active connections",
                  N, icon="🗺️", sw=["tailscale"],
                  endpoint="tailscale/status", hz=1.0, cat="network")
        self._add(372, "Failover Status Widget",
                  "Active connection + signal strength + failover count",
                  N, icon="🔄", sw=["networking"],
                  endpoint="network/failover", hz=1.0, cat="network")
        self._add(373, "LTE Modem Control",
                  "Enable/disable, restart, signal strength (64%)",
                  N, icon="📶", hw=["modem"],
                  endpoint="modem/control", hz=0.5, cat="network")
        self._add(374, "WiFi Scanner",
                  "Nearby networks with signal strength, connect/disconnect",
                  N, icon="📡", sw=["wifi"],
                  endpoint="wifi/scan", hz=0.2, cat="network")
        self._add(375, "VPN Tunnel Health",
                  "Tailscale ping latency + handshake time per peer",
                  N, icon="🔒", sw=["tailscale"],
                  endpoint="tailscale/ping", hz=1.0, cat="network")
        self._add(376, "Port Forward Checker",
                  "Verify ports 8888 (API), 81 (MJPEG) reachable from VPS",
                  N, icon="🔌", sw=["networking"],
                  endpoint="network/ports", hz=0, cat="network")
        self._add(377, "Network Load Graph",
                  "Live throughput Rx/Tx on each interface",
                  N, icon="📈", sw=["networking"],
                  endpoint="network/throughput", hz=2.0, cat="network")
        self._add(378, "Hotspot Control",
                  "Start/stop TANK-HOTSPOT with password display",
                  N, icon="📶", sw=["hostapd"],
                  endpoint="hotspot/control", hz=0, cat="network")
        self._add(379, "4G Data Usage Counter",
                  "Session data usage and remaining quota",
                  N, icon="📊", hw=["modem"],
                  endpoint="modem/usage", hz=0.1, cat="network")
        self._add(380, "DNS Resolution Test",
                  "Check medicscholar.medigyaan.com resolves",
                  N, icon="🔍", sw=["dns"],
                  endpoint="dns/test", hz=0, cat="network")
        self._add(381, "Connection History Log",
                  "All network changes with timestamps",
                  N, icon="📋", sw=["networking"],
                  endpoint="network/history", hz=0, cat="network")
        self._add(382, "Proxy Settings",
                  "Route traffic through VPS for debugging",
                  N, icon="🔗", sw=["proxy"],
                  endpoint="proxy/config", hz=0, cat="network")
        self._add(383, "Remote SSH Access",
                  "One-click terminal to Jetson or UNO Q",
                  N, icon="💻", sw=["ssh"],
                  endpoint="ssh/connect", hz=0, cat="network")
        self._add(384, "OTA Update Channel",
                  "Check for updates via VPS repo",
                  N, icon="📦", sw=["git"],
                  endpoint="ota/check", hz=0, cat="network")
        self._add(385, "Network Diagnostics",
                  "Integrated ping, traceroute, nc with output viewer",
                  N, icon="🔧", sw=["netutils"],
                  endpoint="network/diag", hz=0, cat="network")

        # ═══ 386-395: ROS2 & System Management ═══
        self._add(386, "ROS2 Node Graph",
                  "Visualize active nodes and topics with pub/sub connections",
                  R, icon="🔗", sw=["ros2"],
                  endpoint="ros2/node_graph", hz=1.0, cat="ros2")
        self._add(387, "Topic Monitor",
                  "Select topic (/tank/motor_cmd, /tank/imu) and view live data",
                  R, icon="📡", sw=["ros2"],
                  endpoint="ros2/topic", hz=10.0, cat="ros2")
        self._add(388, "Service Caller",
                  "List and call ROS services with custom arguments",
                  R, icon="📞", sw=["ros2"],
                  endpoint="ros2/service", hz=0, cat="ros2")
        self._add(389, "Launch File Selector",
                  "Choose and run any ROS2 launch file",
                  R, icon="🚀", sw=["ros2"],
                  endpoint="ros2/launch", hz=0, cat="ros2")
        self._add(390, "Colcon Build Interface",
                  "Rebuild workspace with output log streaming",
                  R, icon="🔨", sw=["colcon"],
                  endpoint="colcon/build", hz=0, cat="ros2")
        self._add(391, "Log Viewer",
                  "ROS2 logs (~/.ros/log) with severity filtering",
                  R, icon="📋", sw=["ros2"],
                  endpoint="ros2/logs", hz=0.5, cat="ros2")
        self._add(392, "Parameter Server Editor",
                  "View/modify ROS parameters (YAML) with save/reload",
                  R, icon="⚙️", sw=["ros2"],
                  endpoint="ros2/params", hz=0, cat="ros2")
        self._add(393, "Systemd Service Control",
                  "Start/stop/enable/disable TankOS services",
                  R, icon="🔧", sw=["systemd"],
                  endpoint="systemd/control", hz=0, cat="system")
        self._add(394, "File Manager",
                  "Browse/edit project files with built-in text editor",
                  R, icon="📁", sw=["filesystem"],
                  endpoint="files/browse", hz=0, cat="system")
        self._add(395, "Backup & Restore",
                  "One-click backup to VPS or local USB",
                  R, icon="💾", sw=["backup"],
                  endpoint="backup/run", hz=0, cat="system")

        # ═══ 396-400: Telemetry & Data Logging ═══
        self._add(396, "Realtime Telemetry Dashboard",
                  "Graphs: battery, motor current, speed, IMU, CPU temp",
                  T, icon="📈", hw=["ina219", "imu"],
                  endpoint="telemetry/live", hz=10.0, cat="telemetry")
        self._add(397, "Event History Browser",
                  "Query SQLite tank_telemetry with date filters + CSV export",
                  T, icon="📋", sw=["sqlite"],
                  endpoint="telemetry/history", hz=0, cat="telemetry")
        self._add(398, "Performance Timeline",
                  "Overlay system events on telemetry graphs",
                  T, icon="📊", sw=["telemetry"],
                  endpoint="telemetry/timeline", hz=1.0, cat="telemetry")
        self._add(399, "Mission Replay",
                  "Replay recorded session (sensor + video) for analysis",
                  T, icon="🎥", sw=["replay"],
                  endpoint="replay/load", hz=0, cat="telemetry")
        self._add(400, "Data Annotation Tool",
                  "Label recorded sensor data for supervised learning",
                  T, icon="🏷️", sw=["annotation"],
                  endpoint="annotation/tool", hz=0, cat="telemetry", status=S)

    def get_feature(self, id: int) -> Optional[RunbookFeature]:
        return self._features.get(id)

    def get_by_panel(self, panel: Panel) -> list[RunbookFeature]:
        return [f for f in self._features.values() if f.panel == panel]

    def get_all(self) -> list[RunbookFeature]:
        return sorted(self._features.values(), key=lambda f: f.id)

    def get_count(self) -> int:
        return len(self._features)

    def get_stats(self) -> dict:
        panels = {}
        statuses = {}
        hw_deps = set()
        sw_deps = set()
        for f in self._features.values():
            p = f.panel.value
            panels[p] = panels.get(p, 0) + 1
            s = f.status.value
            statuses[s] = statuses.get(s, 0) + 1
            hw_deps.update(f.hardware_deps)
            sw_deps.update(f.software_deps)
        return {
            "total": self.get_count(),
            "by_panel": panels,
            "by_status": statuses,
            "hardware_deps": sorted(hw_deps),
            "software_deps": sorted(sw_deps),
        }


# Global singleton
RUNBOOK_FEATURES = RunbookFeatureRegistry()
