"""
TankOS Extended GUI — 100 Features (401-500)
===============================================
Deep integration with actual VPS infrastructure, testing/simulation,
security, mission planning, knowledge/learning, debugging, and UX.

VPS: medicscholar.medigyaan.com (100.71.127.19)
Services: Aria2 (6800/6888), Nextcloud (8083), MariaDB, Nginx (8889)
Tailscale: Jetson↔UNO Q↔VPS mesh
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class EPanel(Enum):
    VPS = "vps_cloud"
    TESTING = "testing_sim"
    SECURITY_EXT = "security_ext"
    MISSION = "mission_planning"
    KNOWLEDGE = "knowledge_learning"
    DEBUG = "debug_dev"
    UX = "customization_ux"


class EStatus(Enum):
    LIVE = "live"
    SIMULATED = "sim"
    PLANNED = "planned"


@dataclass
class ExtFeature:
    id: int
    name: str
    description: str
    panel: EPanel
    status: EStatus = EStatus.LIVE
    icon: str = ""
    deps: list[str] = field(default_factory=list)
    endpoint: str = ""


class ExtFeatureRegistry:
    def __init__(self):
        self._f: dict[int, ExtFeature] = {}
        self._reg()

    def _add(self, id, name, desc, panel, icon="", deps=None, ep="", status=EStatus.LIVE):
        self._f[id] = ExtFeature(id, name, desc, panel, icon, deps or [], ep, status)

    def _reg(self):
        V = EPanel.VPS; T = EPanel.TESTING; S = EPanel.SECURITY_EXT
        M = EPanel.MISSION; K = EPanel.KNOWLEDGE; D = EPanel.DEBUG; U = EPanel.UX
        SIM = EStatus.SIMULATED; PLN = EStatus.PLANNED

        # ═══ 401-415: VPS & Cloud ═══
        self._add(401, "Aria2 Download Manager", "List/add/pause/resume downloads (ports 6800/6888)", V, "⬇️", ["aria2"], "aria2/status")
        self._add(402, "Nextcloud File Browser", "Upload/download telemetry logs and models (port 8083)", V, "📁", ["nextcloud"], "nextcloud/files")
        self._add(403, "WebDAV Sync Status", "Last sync time + pending files between Jetson↔VPS", V, "🔄", ["webdav"], "webdav/status")
        self._add(404, "MariaDB Telemetry Viewer", "Query tank_telemetry with SQL editor + CSV export", V, "🗄️", ["mariadb"], "db/query")
        self._add(405, "API Key Manager", "View 9 active providers, rotate keys without .env edit", V, "🔑", ["env"], "api_keys/rotate")
        self._add(406, "VPS Service Health", "Docker containers: start/stop/restart (aria2, nextcloud, etc.)", V, "🐳", ["docker"], "vps/health")
        self._add(407, "Model Repository Browser", "Browse VPS models (port 8899), download to Jetson", V, "🤖", ["models"], "vps/models")
        self._add(408, "File Sync Queue", "Files waiting for rsync between Jetson↔VPS", V, "📦", ["rsync"], "sync/queue")
        self._add(409, "Nginx Proxy Status", "Check port 8889 proxy to Tank API, toggle rules", V, "🌐", ["nginx"], "nginx/status")
        self._add(410, "Fail2ban Alert Log", "Banned IPs, login attempts, whitelist from GUI", V, "🛡️", ["fail2ban"], "f2b/log")
        self._add(411, "Remote VPS Terminal", "Embedded SSH to medicscholar for admin tasks", V, "💻", ["ssh"], "vps/terminal")
        self._add(412, "Database Backup/Restore", "One-click MariaDB dump and restore", V, "💾", ["mariadb"], "db/backup")
        self._add(413, "VPN Tunnel Status", "OpenVPN/Tailscale tunnel status + connected clients", V, "🔒", ["vpn"], "vpn/status")
        self._add(414, "Xrdp Session Manager", "Active remote desktop sessions, allow termination", V, "🖥️", ["xrdp"], "xrdp/sessions")
        self._add(415, "FTP File Browser", "Browse /home/shashi/ via vsftpd (port 21)", V, "📂", ["vsftpd"], "ftp/browse")

        # ═══ 416-430: Testing & Simulation ═══
        self._add(416, "Hardware-in-Loop Sim", "Run stack with mock sensors, compare sim vs real", T, "🧪", ["simulation"], "sim/hil")
        self._add(417, "Sensor Injection Panel", "Inject fake IMU/LiDAR/GPS to test navigation", T, "💉", ["simulation"], "sim/inject")
        self._add(418, "Unit Test Runner", "Run pytest on tank core, display pass/fail + logs", T, "✅", ["pytest"], "tests/run")
        self._add(419, "ROS2 Bag Recorder", "Record rosbag sessions for regression testing", T, "🎬", ["rosbag"], "ros2/bag")
        self._add(420, "Scenario Editor", "Create custom test scenarios, run them", T, "📋", ["simulation"], "sim/scenarios")
        self._add(421, "Simulation Speed Control", "Speed up/slow down simulation for rapid iteration", T, "⏩", ["simulation"], "sim/speed")
        self._add(422, "Mock Arduino Bridge", "Simulate UNO Q responses for motor/encoder", T, "🔌", ["simulation"], "sim/arduino")
        self._add(423, "Error Injection", "Simulate sensor failures to test fallback logic", T, "💥", ["simulation"], "sim/errors")
        self._add(424, "Performance Benchmark", "Measure FPS, inference time, loop frequency", T, "📊", ["benchmark"], "bench/run")
        self._add(425, "Regression Suite", "Predefined test cases, report deltas from previous", T, "🔄", ["pytest"], "tests/regression")
        self._add(426, "Visual Ground Truth", "Overlay simulated position on real video", T, "👁️", ["simulation"], "sim/ground_truth")
        self._add(427, "Code Coverage Report", "Show Python lines executed during testing", T, "📈", ["coverage"], "tests/coverage")
        self._add(428, "Stress Test Panel", "CPU/GPU/RAM stress tests, verify thermal limits", T, "🔥", ["stress"], "tests/stress")
        self._add(429, "CI/CD Integration", "Trigger builds/deployments from GUI via GitHub", T, "🚀", ["github"], "cicd/trigger")
        self._add(430, "Snapshot Restore", "Save system state (configs/logs/models), restore later", T, "📸", ["snapshot"], "snapshot/save")

        # ═══ 431-445: Security & Access ═══
        self._add(431, "Multi-User Login", "Login screen with role selection (Admin/Operator/Viewer)", S, "👤", ["auth"], "auth/login")
        self._add(432, "Permission Matrix", "Fine-grained: who can drive, deploy AI, change configs", S, "🔐", ["rbac"], "auth/permissions")
        self._add(433, "Two-Factor Auth (TOTP)", "Setup TOTP for admin accounts", S, "📱", ["totp"], "auth/2fa")
        self._add(434, "Session Activity Monitor", "Active sessions (IP, device, time) with force-logout", S, "📋", ["sessions"], "auth/sessions")
        self._add(435, "Password Change/Recovery", "Self-service password reset", S, "🔑", ["auth"], "auth/password")
        self._add(436, "Scoped API Keys", "Temporary tokens with permissions (read-only telemetry)", S, "🎫", ["api_keys"], "auth/api_keys")
        self._add(437, "Audit Trail Viewer", "Filterable log of all user actions", S, "📋", ["audit"], "auth/audit")
        self._add(438, "IP Whitelist Manager", "Add/remove allowed IPs for web access", S, "🛡️", ["firewall"], "auth/ip_whitelist")
        self._add(439, "Rate Limit Config", "Per-user request limits, monitor throttled requests", S, "⏱️", ["ratelimit"], "auth/ratelimit")
        self._add(440, "SSH Key Management", "Upload/revoke SSH keys for Jetson and UNO Q", S, "🔑", ["ssh_keys"], "auth/ssh_keys")
        self._add(441, "Break-Glass Account", "One-time emergency password, logs usage", S, "🚨", ["emergency"], "auth/breakglass")
        self._add(442, "Login Attempt Alert", "Failed logins + lockout status display", S, "🔔", ["auth"], "auth/attempts")
        self._add(443, "Data Encryption Toggle", "Enable AES-256 for stored telemetry/logs", S, "🔒", ["encryption"], "auth/encryption")
        self._add(444, "Security Compliance Scan", "Scan for misconfigs (open ports, default passwords)", S, "🔍", ["security"], "auth/compliance")
        self._add(445, "Session Timeout Settings", "Configure auto-logout after inactivity", S, "⏰", ["auth"], "auth/timeout")

        # ═══ 446-460: Mission Planning ═══
        self._add(446, "Mission Editor", "Drag-drop blocks: Move, Turn, Wait, Detect, Speak", M, "📋", ["orchestrator"], "mission/editor")
        self._add(447, "Scheduled Missions", "Cron-like interface for timed missions", M, "⏰", ["scheduler"], "mission/schedule")
        self._add(448, "Conditional Triggers", "Visual rule builder: 'If battery<20% → return dock'", M, "🔀", ["rules"], "mission/triggers")
        self._add(449, "Mission Library", "Save, load, share mission templates", M, "📚", ["missions"], "mission/library")
        self._add(450, "Pre-Flight Checklist", "Mandatory steps before mission (LiDAR OK, GPS fix)", M, "✅", ["checklist"], "mission/checklist")
        self._add(451, "Abort Button", "Stop mission, execute pre-defined abort sequence", M, "🛑", ["safety"], "mission/abort")
        self._add(452, "Mission Progress Timeline", "Gantt-style view of steps and execution times", M, "📊", ["timeline"], "mission/timeline")
        self._add(453, "GPS Waypoint Import", "Upload KML/GPX files, convert to waypoints", M, "📍", ["gps"], "mission/import")
        self._add(454, "Patrol Route Generator", "Auto-create patrol from map boundaries + no-go zones", M, "🔄", ["navigation"], "mission/patrol_gen")
        self._add(455, "Search Pattern Selector", "Grid, spiral, lawnmower patterns for area coverage", M, "🔍", ["navigation"], "mission/search_pattern")
        self._add(456, "Docking Procedure", "Go-home with visual feedback (LiDAR + IR)", M, "🔌", ["charging"], "mission/dock")
        self._add(457, "Multi-Mission Queue", "Order multiple missions, execute sequentially", M, "📚", ["orchestrator"], "mission/queue")
        self._add(458, "Mission Pause/Resume", "Pause ongoing mission, resume later", M, "⏸️", ["orchestrator"], "mission/pause")
        self._add(459, "Mission Logs", "Step-by-step log with timestamps for each execution", M, "📋", ["logging"], "mission/logs")
        self._add(460, "Export Mission Report", "Generate PDF with maps, stats, decision logs", M, "📄", ["report"], "mission/report")

        # ═══ 461-475: Knowledge & Learning ═══
        self._add(461, "Knowledge Graph Viewer", "Interactive graph: entities, relationships, properties", K, "🕸️", ["knowledge"], "knowledge/graph")
        self._add(462, "Vector Memory Browser", "View embeddings, search by semantic similarity", K, "🧠", ["sqlite_vec"], "memory/browse")
        self._add(463, "Learning Progress Dashboard", "Training episodes, accuracy, improvement metrics", K, "📈", ["learning"], "learn/progress")
        self._add(464, "Manual Labeling Tool", "Annotate images/sensor data for supervised learning", K, "🏷️", ["labeling"], "learn/label")
        self._add(465, "RL Viewer", "Reward curves, episode lengths, policy changes", K, "🎮", ["rl"], "learn/rl", SIM)
        self._add(466, "Model Versioning", "Rollback to previous YOLO/embedding versions", K, "📦", ["models"], "models/versions")
        self._add(467, "Curriculum Learning", "Difficulty progression for auto-learning tasks", K, "📚", ["learning"], "learn/curriculum")
        self._add(468, "Concept Drift Monitor", "Detect environment changes, trigger re-training", K, "🔄", ["drift"], "learn/drift")
        self._add(469, "Explainability Panel", "SHAP-like feature importance for AI decisions", K, "💡", ["explainability"], "learn/explain")
        self._add(470, "Memory Consolidation", "Merge related memories, show consolidation logs", K, "🧠", ["memory"], "memory/consolidate")
        self._add(471, "Skill Repository", "List learned behaviors: 'avoid obstacles', 'follow ball'", K, "🎯", ["skills"], "learn/skills")
        self._add(472, "Knowledge Query", "NL query: 'What did I see at 2 PM?'", K, "🔍", ["knowledge"], "knowledge/query")
        self._add(473, "Transfer Learning Panel", "Fine-tune pre-trained model on your dataset", K, "🔄", ["training"], "learn/transfer", SIM)
        self._add(474, "Active Learning Suggestions", "AI recommends which data points to label next", K, "🎯", ["active_learning"], "learn/active")
        self._add(475, "Learning Scheduler Calendar", "Visual calendar of scheduled learning tasks", K, "📅", ["scheduler"], "learn/calendar")

        # ═══ 476-490: Debugging & Dev Tools ═══
        self._add(476, "Variable Watcher", "Monitor Python vars (speed, battery) with live updates", D, "👁️", ["debug"], "debug/watch")
        self._add(477, "Code Editor", "Edit Python files with syntax highlighting, hot-reload", D, "📝", ["editor"], "debug/edit")
        self._add(478, "Exception Tracker", "Catch unhandled exceptions with traceback + stack vars", D, "🐛", ["debug"], "debug/exceptions")
        self._add(479, "Performance Profiler", "CPU/GPU per function, visual flame graph", D, "🔥", ["profiler"], "debug/profile")
        self._add(480, "Serial Monitor", "Terminal to /dev/ttyACM0, /dev/ttyUSB0 with baud selection", D, "📡", ["serial"], "debug/serial")
        self._add(481, "ROS2 Debug Console", "Send raw ROS messages to any topic", D, "🔗", ["ros2"], "debug/ros_console")
        self._add(482, "System Journal Viewer", "Tail journalctl -u tank-*, filter by service", D, "📋", ["journalctl"], "debug/journal")
        self._add(483, "Interactive Python Shell", "Execute Python in running robot context", D, "🐍", ["ipython"], "debug/shell")
        self._add(484, "Memory Leak Detector", "Track object allocations, detect growth over time", D, "🔍", ["tracemalloc"], "debug/memory")
        self._add(485, "Log Streaming", "Real-time logs with severity coloring + grep", D, "📄", ["logging"], "debug/logs")
        self._add(486, "State Machine Visualizer", "Show FSM states: IDLE, DRIVING, AI, ERROR", D, "🔄", ["fsm"], "debug/fsm")
        self._add(487, "Watchdog Status", "Heartbeats from critical processes, manual reset", D, "🐕", ["watchdog"], "debug/watchdog")
        self._add(488, "Config Editor", "Edit YAML with auto-complete + error highlighting", D, "⚙️", ["yaml"], "debug/config")
        self._add(489, "Device Tree Viewer", "All connected hardware with bus addresses + drivers", D, "🌳", ["hardware"], "debug/device_tree")
        self._add(490, "RPC Explorer", "List Python core functions with parameters", D, "📞", ["rpc"], "debug/rpc")

        # ═══ 491-500: UX & Customization ═══
        self._add(491, "Custom Color Themes", "Save and share theme files", U, "🎨", ["themes"], "ux/themes")
        self._add(492, "Dashboard Layout Editor", "Drag-drop to rearrange panels, persist layout", U, "🎛️", ["layout"], "ux/layout")
        self._add(493, "Icon Pack Selector", "FontAwesome, Material, custom icon sets", U, "🖼️", ["icons"], "ux/icons")
        self._add(494, "Language Packs", "English, Hindi, Gujarati for the UI", U, "🌐", ["i18n"], "ux/languages")
        self._add(495, "Shortcut Configurator", "Remap all keyboard shortcuts to preferences", U, "⌨️", ["shortcuts"], "ux/shortcuts")
        self._add(496, "Notification Sounds", "Upload custom WAV for E-STOP, mission complete", U, "🔊", ["audio"], "ux/sounds")
        self._add(497, "Resolution Scaling", "Optimize for 4K, 1080p, or small screens", U, "🖥️", ["display"], "ux/resolution")
        self._add(498, "Touch Gesture Config", "Customize swipe actions (swipe left = turn left)", U, "👋", ["gestures"], "ux/gestures")
        self._add(499, "Welcome Wizard", "First-time setup: network, calibration, models", U, "🎓", ["onboarding"], "ux/welcome")
        self._add(500, "User Feedback Widget", "Send feedback/bug reports to dev team via VPS API", U, "💬", ["feedback"], "ux/feedback")

    def get(self, id: int) -> Optional[ExtFeature]:
        return self._f.get(id)

    def by_panel(self, panel: EPanel) -> list[ExtFeature]:
        return [f for f in self._f.values() if f.panel == panel]

    def all(self) -> list[ExtFeature]:
        return sorted(self._f.values(), key=lambda f: f.id)

    def count(self) -> int:
        return len(self._f)

    def stats(self) -> dict:
        panels, statuses = {}, {}
        all_deps = set()
        for f in self._f.values():
            p = f.panel.value if hasattr(f.panel, 'value') else str(f.panel)
            panels[p] = panels.get(p, 0) + 1
            s = f.status.value if hasattr(f.status, 'value') else str(f.status)
            statuses[s] = statuses.get(s, 0) + 1
            all_deps.update(f.deps)
        return {"total": self.count(), "by_panel": panels,
                "by_status": statuses, "unique_deps": len(all_deps),
                "deps": sorted(all_deps)}


EXT_FEATURES = ExtFeatureRegistry()
