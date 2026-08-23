"""
TankOS Advanced GUI — 100 Features (201-300)
=============================================
Complete feature registry for the TankOS Android TV-style interface.

Categories:
  201-220: Advanced Control & Teleoperation
  221-240: AI & Advanced Autonomy
  241-260: Telemetry, Monitoring & Diagnostics
  261-275: Mapping, Localization & Navigation
  276-290: UI/UX & Customization
  291-300: Security, Administration & Management
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable


class FeatureCategory(Enum):
    CONTROL = "control"
    AI_AUTONOMY = "ai_autonomy"
    TELEMETRY = "telemetry"
    NAVIGATION = "navigation"
    UI_UX = "ui_ux"
    SECURITY = "security"


class FeatureStatus(Enum):
    ACTIVE = "active"
    BETA = "beta"
    PLANNED = "planned"
    DISABLED = "disabled"


@dataclass
class GUIFeature:
    """Single GUI feature definition."""
    id: int
    name: str
    description: str
    category: FeatureCategory
    status: FeatureStatus = FeatureStatus.ACTIVE
    icon: str = ""
    shortcut: str = ""
    requires_hardware: list[str] = field(default_factory=list)
    requires_ai: bool = False
    panel: str = ""
    widget_type: str = "button"


class FeatureRegistry:
    """Registry of all 300 GUI features."""

    def __init__(self):
        self._features: dict[int, GUIFeature] = {}
        self._register_all()

    def _add(self, id: int, name: str, desc: str, cat: FeatureCategory,
             icon: str = "", shortcut: str = "", hw: list[str] | None = None,
             ai: bool = False, panel: str = "", widget: str = "button",
             status: FeatureStatus = FeatureStatus.ACTIVE):
        self._features[id] = GUIFeature(
            id=id, name=name, description=desc, category=cat,
            icon=icon, shortcut=shortcut, requires_hardware=hw or [],
            requires_ai=ai, panel=panel, widget_type=widget, status=status
        )

    def _register_all(self):
        CTRL = FeatureCategory.CONTROL
        AI = FeatureCategory.AI_AUTONOMY
        TEL = FeatureCategory.TELEMETRY
        NAV = FeatureCategory.NAVIGATION
        UI = FeatureCategory.UI_UX
        SEC = FeatureCategory.SECURITY

        # ═══ 201-220: Advanced Control & Teleoperation ═══
        self._add(201, "Gravity/Inclination Control",
                  "Tilt phone/tablet to steer robot", CTRL,
                  icon="📱", widget="sensor_control", panel="control")
        self._add(202, "Sketch-to-Path",
                  "Draw path on canvas for robot to follow", CTRL,
                  icon="✏️", widget="canvas", panel="control")
        self._add(203, "6-DOF Arm Control",
                  "Sliders for robotic arm control", CTRL,
                  icon="🦾", widget="slider_group", panel="control",
                  hw=["servo", "arm"])
        self._add(204, "Waypoint Queue",
                  "Build and manage sequential waypoints", CTRL,
                  icon="📍", widget="list_editor", panel="control")
        self._add(205, "Velocity Ramp Sliders",
                  "Control linear and angular acceleration", CTRL,
                  icon="⚡", widget="dual_slider", panel="control")
        self._add(206, "Field-Oriented Control",
                  "Drive relative to robot or camera perspective", CTRL,
                  icon="🧭", widget="toggle_group", panel="control")
        self._add(207, "Augmented Reality View",
                  "Overlay digital info on live video", CTRL,
                  icon="🔮", widget="ar_overlay", panel="control",
                  ai=True)
        self._add(208, "Go-To Command",
                  "Click video feed to send robot there", CTRL,
                  icon="👆", widget="click_navigate", panel="control")
        self._add(209, "Multi-Robot Fleet View",
                  "See status of all registered robots", CTRL,
                  icon="🤖", widget="fleet_grid", panel="control")
        self._add(210, "Fleet Broadcasting",
                  "Send command to all robots simultaneously", CTRL,
                  icon="📢", widget="broadcast_panel", panel="control")
        self._add(211, "Teleop Assist Mode",
                  "AI smoothens manual joystick inputs", CTRL,
                  icon="🎮", widget="joystick", panel="control", ai=True)
        self._add(212, "Virtual Follow-Through",
                  "Robot continues briefly after control release", CTRL,
                  icon="🏃", widget="slider", panel="control")
        self._add(213, "Command Stacking",
                  "Queue multiple commands for sequential execution", CTRL,
                  icon="📚", widget="command_queue", panel="control")
        self._add(214, "Relative Movement",
                  "Move N meters in a direction", CTRL,
                  icon="📏", widget="direction_pad", panel="control")
        self._add(215, "Action Groups",
                  "Save and execute groups of actions", CTRL,
                  icon="📋", widget="action_manager", panel="control")
        self._add(216, "Undo/Redo Actions",
                  "Revert last command or action", CTRL,
                  icon="↩️", widget="undo_bar", panel="control")
        self._add(217, "Simulation/Sandbox Mode",
                  "Test commands in simulation before sending", CTRL,
                  icon="🧪", widget="sandbox_panel", panel="control")
        self._add(218, "Digital Twin",
                  "3D model mirroring real-time robot state", CTRL,
                  icon="🧊", widget="3d_viewer", panel="control")
        self._add(219, "Direct Motor Control",
                  "Individual sliders for left/right track", CTRL,
                  icon="⚙️", widget="motor_sliders", panel="control",
                  hw=["motor"])
        self._add(220, "Tank Turn Mode",
                  "One-click pivot in place", CTRL,
                  icon="🔄", widget="button", panel="control",
                  hw=["motor"])

        # ═══ 221-240: AI & Advanced Autonomy ═══
        self._add(221, "LLM Reasoning Panel",
                  "Show AI's thought process behind decisions", AI,
                  icon="🧠", widget="reasoning_viewer", panel="ai", ai=True)
        self._add(222, "Shadow Mode",
                  "Run AI decisions alongside manual control", AI,
                  icon="👥", widget="toggle_panel", panel="ai", ai=True)
        self._add(223, "Validation Gates",
                  "Check robot readiness before AI task", AI,
                  icon="✅", widget="checklist_panel", panel="ai")
        self._add(224, "Explainability Panel",
                  "Plain-English AI explanation", AI,
                  icon="💡", widget="text_viewer", panel="ai", ai=True)
        self._add(225, "Visio-Verbal Commands",
                  "Combine gaze + voice for nuanced commands", AI,
                  icon="👁️", widget="multimodal_panel", panel="ai",
                  ai=True, hw=["camera", "microphone"])
        self._add(226, "Object Following",
                  "Click object in video to follow it", AI,
                  icon="🎯", widget="click_track", panel="ai", ai=True)
        self._add(227, "Person Avoidance",
                  "Toggle active people avoidance mode", AI,
                  icon="🚶", widget="toggle_panel", panel="ai", ai=True)
        self._add(228, "Autonomous Docking",
                  "Find and dock at charging station", AI,
                  icon="🔌", widget="dock_panel", panel="ai",
                  hw=["apriltag", "servo"])
        self._add(229, "Semantic Search",
                  "Ask 'Where did I leave the blue box?'", AI,
                  icon="🔍", widget="search_panel", panel="ai", ai=True)
        self._add(230, "Curious Exploration",
                  "AI explores unseen areas autonomously", AI,
                  icon="🗺️", widget="exploration_panel", panel="ai", ai=True)
        self._add(231, "Sentry Mode",
                  "AI watches for movement/specific objects", AI,
                  icon="🛡️", widget="sentry_panel", panel="ai", ai=True)
        self._add(232, "AI Mood Indicator",
                  "Visual showing robot's current state", AI,
                  icon="😊", widget="mood_display", panel="ai")
        self._add(233, "Prompt Playground",
                  "Test and tune AI prompts in real-time", AI,
                  icon="🎪", widget="prompt_editor", panel="ai", ai=True)
        self._add(234, "Model Performance Stats",
                  "FPS, confidence, inference time display", AI,
                  icon="📊", widget="perf_chart", panel="ai")
        self._add(235, "Training Data Recorder",
                  "Record video + sensor data for retraining", AI,
                  icon="🎬", widget="recorder_panel", panel="ai")
        self._add(236, "AI Memory Viewer",
                  "See what robot remembers about environment", AI,
                  icon="🧠", widget="memory_viewer", panel="ai")
        self._add(237, "Gesture Recognition",
                  "Control robot with hand gestures via camera", AI,
                  icon="✋", widget="gesture_panel", panel="ai",
                  ai=True, hw=["camera"])
        self._add(238, "Voice Command Feedback",
                  "Robot speaks back to confirm actions", AI,
                  icon="🔊", widget="feedback_panel", panel="ai",
                  hw=["speaker"])
        self._add(239, "AI Goal Setting",
                  "Type goal like 'Patrol the perimeter'", AI,
                  icon="🎯", widget="goal_input", panel="ai", ai=True)
        self._add(240, "Mission Planner",
                  "Visual interface for complex AI missions", AI,
                  icon="📋", widget="mission_builder", panel="ai", ai=True)

        # ═══ 241-260: Telemetry & Diagnostics ═══
        self._add(241, "Network Quality Indicators",
                  "Throughput, jitter, packet loss display", TEL,
                  icon="🌐", widget="network_chart", panel="telemetry")
        self._add(242, "Wheel Odometry Plots",
                  "Real-time motion graphs", TEL,
                  icon="📈", widget="chart_panel", panel="telemetry")
        self._add(243, "Mission Progress Meter",
                  "Progress bar for autonomous missions", TEL,
                  icon="⏳", widget="progress_bar", panel="telemetry")
        self._add(244, "GPS Accuracy Indicators",
                  "Signal quality for position/heading", TEL,
                  icon="📡", widget="gps_panel", panel="telemetry")
        self._add(245, "Component Heatmap",
                  "Visualize load across all components", TEL,
                  icon="🌡️", widget="heatmap", panel="telemetry")
        self._add(246, "ROS Node/Topic Browser",
                  "Interactive list of active ROS nodes", TEL,
                  icon="🔗", widget="ros_browser", panel="telemetry")
        self._add(247, "USB Bus Utilization",
                  "Monitor USB device bandwidth", TEL,
                  icon="🔌", widget="usb_monitor", panel="telemetry")
        self._add(248, "Customizable Dashboard",
                  "Drag, drop, resize widgets", TEL,
                  icon="🎛️", widget="dashboard_builder", panel="telemetry")
        self._add(249, "Health KPI Panel",
                  "At-a-glance critical health metrics", TEL,
                  icon="❤️", widget="kpi_grid", panel="telemetry")
        self._add(250, "Diagnostic Self-Test",
                  "Complete hardware/software check-up", TEL,
                  icon="🔍", widget="self_test_panel", panel="telemetry")
        self._add(251, "Alert History",
                  "Log of all past warnings and errors", TEL,
                  icon="🔔", widget="alert_log", panel="telemetry")
        self._add(252, "Comparative Charts",
                  "Overlay two metrics on one graph", TEL,
                  icon="📊", widget="dual_chart", panel="telemetry")
        self._add(253, "3D Telemetry Visualization",
                  "View robot pose in 3D space", TEL,
                  icon="🧊", widget="3d_telemetry", panel="telemetry")
        self._add(254, "Data Export",
                  "Export telemetry as CSV/JSON/PDF", TEL,
                  icon="📤", widget="export_panel", panel="telemetry")
        self._add(255, "Robot Heartbeat",
                  "Visual online/responsive indicator", TEL,
                  icon="💓", widget="heartbeat_display", panel="telemetry")
        self._add(256, "System Uptime Timer",
                  "Track how long robot has been running", TEL,
                  icon="⏱️", widget="timer_display", panel="telemetry")
        self._add(257, "Firmware Version Comparison",
                  "Compare current vs latest firmware", TEL,
                  icon="📦", widget="version_panel", panel="telemetry")
        self._add(258, "Component Status Icons",
                  "Green/Yellow/Red for every subsystem", TEL,
                  icon="🚦", widget="status_grid", panel="telemetry")
        self._add(259, "Log Filtering",
                  "Filter logs by severity/source/keyword", TEL,
                  icon="🔎", widget="log_filter", panel="telemetry")
        self._add(260, "Anomaly Detection Alerts",
                  "Notify when sensor data deviates", TEL,
                  icon="⚠️", widget="anomaly_panel", panel="telemetry",
                  ai=True)

        # ═══ 261-275: Mapping & Navigation ═══
        self._add(261, "Path Progress Meter",
                  "Route completion percentage", NAV,
                  icon="📍", widget="path_progress", panel="navigation")
        self._add(262, "Route Statistics",
                  "Distance, ETA, waypoints display", NAV,
                  icon="📏", widget="route_stats", panel="navigation")
        self._add(263, "No-Go Zones",
                  "Draw areas robot should avoid", NAV,
                  icon="🚫", widget="zone_editor", panel="navigation")
        self._add(264, "Map Layers",
                  "Toggle LiDAR/semantic/WiFi layers", NAV,
                  icon="🗺️", widget="layer_toggle", panel="navigation")
        self._add(265, "Exploration Coverage",
                  "Heatmap of explored areas", NAV,
                  icon="🔥", widget="coverage_heatmap", panel="navigation")
        self._add(266, "Localization Confidence",
                  "Position certainty metric", NAV,
                  icon="🎯", widget="confidence_meter", panel="navigation")
        self._add(267, "Path Replanning",
                  "Manually trigger new path finding", NAV,
                  icon="🔄", widget="replan_button", panel="navigation")
        self._add(268, "Map Annotations",
                  "Add notes/markers/labels to map", NAV,
                  icon="📝", widget="annotation_tool", panel="navigation")
        self._add(269, "Multi-Floor Support",
                  "Switch between map floors", NAV,
                  icon="🏢", widget="floor_switcher", panel="navigation")
        self._add(270, "Map Alignment",
                  "Manually correct robot position on map", NAV,
                  icon="📐", widget="alignment_tool", panel="navigation")
        self._add(271, "Trajectory Prediction",
                  "Show predicted future path", NAV,
                  icon="🔮", widget="prediction_overlay", panel="navigation")
        self._add(272, "Path Recording/Playback",
                  "Record manual drive and replay", NAV,
                  icon="🎥", widget="record_playback", panel="navigation")
        self._add(273, "Path Editing",
                  "Click-drag waypoints to modify path", NAV,
                  icon="✏️", widget="path_editor", panel="navigation")
        self._add(274, "Obstacle Persistence",
                  "Show last-seen obstacle positions", NAV,
                  icon="🧱", widget="obstacle_overlay", panel="navigation")
        self._add(275, "Dynamic Map Updates",
                  "Watch map build in real-time", NAV,
                  icon="🗺️", widget="live_map", panel="navigation")

        # ═══ 276-290: UI/UX & Customization ═══
        self._add(276, "Dark/Light/High-Contrast Themes",
                  "Pre-set themes for environments", UI,
                  icon="🎨", widget="theme_selector", panel="settings")
        self._add(277, "Custom Color Schemes",
                  "Define custom UI colors", UI,
                  icon="🌈", widget="color_picker", panel="settings")
        self._add(278, "Plugin Architecture",
                  "Add new widgets or panels", UI,
                  icon="🧩", widget="plugin_manager", panel="settings")
        self._add(279, "Keyboard Shortcut Sheet",
                  "Popup showing all shortcuts", UI,
                  icon="⌨️", widget="shortcut_popup", panel="settings")
        self._add(280, "Touch-Optimized Controls",
                  "Larger buttons/joysticks for mobile", UI,
                  icon="👆", widget="touch_mode_toggle", panel="settings")
        self._add(281, "Full-Screen Mode",
                  "Immersive video/map display", UI,
                  icon="🖥️", widget="fullscreen_toggle", panel="settings")
        self._add(282, "Multi-Language Support",
                  "Switch interface languages", UI,
                  icon="🌐", widget="language_selector", panel="settings")
        self._add(283, "Touch Gesture Support",
                  "Swipe/pinch/tap gestures", UI,
                  icon="👋", widget="gesture_settings", panel="settings")
        self._add(284, "Haptic Feedback",
                  "Phone vibrations for alerts", UI,
                  icon="📳", widget="haptic_toggle", panel="settings")
        self._add(285, "Notification Preferences",
                  "Choose notification triggers", UI,
                  icon="🔔", widget="notification_config", panel="settings")
        self._add(286, "Collapsible Panels",
                  "Hide/show panels to focus", UI,
                  icon="📁", widget="panel_manager", panel="settings")
        self._add(287, "Always on Top Mode",
                  "Keep control window above others", UI,
                  icon="📌", widget="ontop_toggle", panel="settings")
        self._add(288, "Favorites Bar",
                  "Quick-access buttons for frequent commands", UI,
                  icon="⭐", widget="favorites_bar", panel="settings")
        self._add(289, "UI Scaling",
                  "Adjust size of all UI elements", UI,
                  icon="🔍", widget="scale_slider", panel="settings")
        self._add(290, "Onboarding Tour",
                  "Guided tour for new users", UI,
                  icon="🎓", widget="tour_wizard", panel="settings")

        # ═══ 291-300: Security & Administration ═══
        self._add(291, "Session Management",
                  "View/terminate active user sessions", SEC,
                  icon="👤", widget="session_panel", panel="security")
        self._add(292, "Audit Log",
                  "Detailed who-did-what-when log", SEC,
                  icon="📋", widget="audit_viewer", panel="security")
        self._add(293, "RBAC (Role-Based Access)",
                  "Admin/Operator/Viewer permissions", SEC,
                  icon="🔐", widget="role_manager", panel="security")
        self._add(294, "Break-Glass Account",
                  "Emergency-only special account", SEC,
                  icon="🚨", widget="emergency_account", panel="security")
        self._add(295, "API Key Management",
                  "Generate and revoke API keys", SEC,
                  icon="🔑", widget="api_key_manager", panel="security")
        self._add(296, "IP Whitelisting",
                  "Restrict access to specific IPs", SEC,
                  icon="🛡️", widget="ip_whitelist", panel="security")
        self._add(297, "Rate Limiting Dashboard",
                  "Monitor/configure API request limits", SEC,
                  icon="⏱️", widget="rate_limit_panel", panel="security")
        self._add(298, "Data Retention Policies",
                  "Configure log/telemetry retention", SEC,
                  icon="📆", widget="retention_config", panel="security")
        self._add(299, "Configuration Versioning",
                  "Save/rollback configurations", SEC,
                  icon="📦", widget="config_versioning", panel="security")
        self._add(300, "System Backup & Restore",
                  "One-click backup/restore settings", SEC,
                  icon="💾", widget="backup_restore", panel="security")

    def get_feature(self, id: int) -> Optional[GUIFeature]:
        return self._features.get(id)

    def get_by_category(self, cat: FeatureCategory) -> list[GUIFeature]:
        return [f for f in self._features.values() if f.category == cat]

    def get_by_panel(self, panel: str) -> list[GUIFeature]:
        return [f for f in self._features.values() if f.panel == panel]

    def get_all(self) -> list[GUIFeature]:
        return sorted(self._features.values(), key=lambda f: f.id)

    def get_count(self) -> int:
        return len(self._features)

    def get_stats(self) -> dict:
        cats = {}
        for f in self._features.values():
            cat = f.category.value
            cats[cat] = cats.get(cat, 0) + 1
        return {
            "total": self.get_count(),
            "by_category": cats,
            "active": sum(1 for f in self._features.values() if f.status == FeatureStatus.ACTIVE),
            "requires_ai": sum(1 for f in self._features.values() if f.requires_ai),
            "requires_hardware": sum(1 for f in self._features.values() if f.requires_hardware),
        }


# Global singleton
GUI_FEATURES = FeatureRegistry()
