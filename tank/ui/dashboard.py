"""Tank — Terminal Dashboard.

Real-time system status display for competition demos.
Shows: system status, sensors, detections, decisions, events.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List


def render_dashboard(status: Dict[str, Any], events: List[Dict] = None) -> str:
    """Render a competition-quality terminal dashboard."""
    lines = []
    w = 56

    # Header
    lines.append("╔" + "═" * w + "╗")
    lines.append("║" + " TANK — PHYSICAL AI ROBOT ".center(w) + "║")
    lines.append("╠" + "═" * w + "╣")

    # System status
    state = status.get("state", "UNKNOWN")
    cycle = status.get("cycle", 0)
    state_icon = {"IDLE": "⏸", "OBSERVING": "👁", "DETECTING": "🔍", "ANALYZING": "🧠",
                  "TRACKING": "🎯", "ACTING": "⚡", "VERIFYING": "✓", "SAFE_STOP": "🛑",
                  "ERROR": "❌", "OFFLINE": "📡"}.get(state, "❓")

    lines.append(f"║  State: {state_icon} {state:<20} Cycle: {cycle:<16} ║")
    lines.append("║" + "─" * w + "║")

    # Sensors
    lines.append("║  SENSORS".ljust(w + 1) + "║")
    for sh in status.get("sensors", []):
        name = sh.get("name", "?")[:25]
        s = sh.get("status", "?")
        icon = "🟢" if s == "CONNECTED" else "🔴" if s == "ERROR" else "⚪"
        lines.append(f"║    {icon} {name:<30} {s:<12} ║")

    lines.append("║" + "─" * w + "║")

    # Fusion
    fusion = status.get("fusion", {})
    lines.append("║  SENSOR FUSION".ljust(w + 1) + "║")
    lines.append(f"║    Camera detections: {fusion.get('camera_detections', 0):<31} ║")
    lidar = fusion.get("lidar_distance")
    lines.append(f"║    LiDAR distance: {str(lidar or 'N/A'):<35} ║")
    thermal = "CONFIRMED" if fusion.get("thermal_human") else "clear"
    lines.append(f"║    Thermal: {thermal:<42} ║")

    lines.append("║" + "─" * w + "║")

    # AI
    ai_lat = status.get("ai_latency", 0)
    lines.append(f"║  AI Latency: {ai_lat*1000:.0f}ms{'':<36} ║")

    # Safety
    safety = status.get("safety", {})
    emergency = "ACTIVE" if safety.get("emergency") else "OK"
    lines.append(f"║  Safety: {emergency:<44} ║")

    lines.append("║" + "─" * w + "║")

    # Events (last 5)
    lines.append("║  RECENT EVENTS".ljust(w + 1) + "║")
    if events:
        for ev in events[-5:]:
            ts = time.strftime("%H:%M:%S", time.localtime(ev.timestamp))
            etype = ev.event_type.value[:20]
            lines.append(f"║    {ts} {etype:<20} {ev.source:<12} ║")
    else:
        lines.append("║    (no events yet)".ljust(w + 1) + "║")

    # Footer
    lines.append("╚" + "═" * w + "╝")
    return "\n".join(lines)


def print_dashboard(status: Dict[str, Any], events: List[Dict] = None) -> None:
    print(render_dashboard(status, events))
