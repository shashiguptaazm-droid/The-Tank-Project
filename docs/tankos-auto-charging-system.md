# TankOS Auto Charging System

An autonomous battery charging system with 10 integrated subsystems that detect, navigate, dock, charge, and manage battery health without user intervention.

## 1. Charging Manager (Orchestrator)

The master controller that coordinates all 10 subsystems. Runs a continuous 10-second monitoring loop that:

- Checks battery percentage and charging state
- Detects emergency/critical conditions
- Triggers autonomous charging sequences when needed
- Updates charging telemetry during active charging
- Records usage patterns for the scheduler

## 2. Dock Detection Engine

Uses multiple sensor modalities in priority order:

1. **AprilTag** — QR-style tag on the charging station
2. **LiDAR** — Geometric signature matching
3. **Camera** — YOLO-trained dock detection
4. **IR Beacon** — Signal strength triangulation
5. **Stored Map** — Fallback to saved waypoint position

Each method returns a `DockInfo` with position, yaw, confidence, and detection method.

## 3. Dock Navigation Engine

Autonomously navigates to the charging dock:

- Saves dock position as a persistent waypoint ("charging_dock")
- Uses NavigationManager's path planning
- Falls back to direct navigation if waypoint navigation fails
- Supports replanning when obstacles are encountered

## 4. Docking Controller

Precision alignment and electrical contact:

- **Phase 1**: Navigate to approach point (0.5m from dock)
- **Phase 2**: Iterative alignment using sensor feedback
- **Phase 3**: Final approach at low speed (0.05 m/s)
- **Contact Verification**: Confirms electrical connection via voltage/current change
- Up to 5 alignment attempts before declaring fault

## 5. Charging Controller

Manages the charge cycle:

- **Pre-Charge** (5 seconds) — Initial connection verification
- **Fast Charge** — Bulk charging until 80%
- **Trickle Charge** — Top-off from 80% to target (default 95%)
- **Complete** — Session ends, health recorded
- Monitors: voltage, current, temperature, charge speed

## 6. Task Interruption Manager

Ensures seamless task management around charging:

- Saves robot mode and patrol state before docking
- Pauses patrol and active missions
- Restores all tasks automatically after charging completes
- Maintains saved state for power-loss recovery

## 7. Emergency Charging Engine

Safety-critical overrides:

- **Critical** (≤10%): Forced power optimization, charging sequence initiated
- **Emergency** (≤5%): All non-essential systems shut down, immediate dock forced
- Clears automatically when battery recovers above 20%

## 8. Power Optimization Engine

Extends runtime and prepares for charging:

- **max_performance**: Full brightness (100%), 60 FPS, high AI context
- **balanced**: Medium brightness (60%), 30 FPS, moderate AI
- **max_battery**: Low brightness (20%), 15 FPS, minimal AI, animations disabled
- Estimates remaining runtime based on current draw and profile
- Blanks display during charging

## 9. Battery Health Manager

Tracks long-term battery health:

- Records every charge cycle (start/end pct, duration, energy, temperature)
- Calculates State of Health (SOH) with temperature-accelerated degradation
- Estimates remaining cycles before replacement (70% SOH threshold)
- Provides recommendations: good, declining, replace

## 10. Charging Scheduler

Learns usage patterns for intelligent charging:

- Records hourly/daily usage patterns
- Finds optimal 2-hour charging windows with lowest activity
- Avoids interrupting patrols or missions for non-critical charging
- Schedules background charging during idle periods
- Persists learning across reboots

## Settings

All charging settings are stored in `~/.config/tank_os/settings.json`:

| Key | Default | Description |
|-----|---------|-------------|
| `charging.auto_enabled` | `true` | Enable automatic charging |
| `charging.target_pct` | `95` | Target charge level |
| `charging.schedule_threshold` | `50` | Battery % for scheduled charging |
| `charging.max_duration_minutes` | `120` | Maximum charge session duration |
| `charging.dock_check_interval_s` | `30` | Dock detection frequency |
| `charging.approach_distance_m` | `0.5` | Distance to stop before dock |
| `charging.alignment_tolerance_cm` | `2.0` | Docking alignment tolerance |
| `charging.enable_scheduler` | `true` | Enable usage-based scheduling |
| `charging.enable_emergency` | `true` | Enable emergency charging |

## Events

The charging system emits the following events:

| Event | Data | Source |
|-------|------|--------|
| `charging_sequence_start` | battery_pct, emergency | charging_manager |
| `dock_detected` | x, y, yaw, method, confidence | dock_detection |
| `dock_position_saved` | x, y, yaw | dock_navigation |
| `docking_started` | x, y, method | docking_controller |
| `docking_complete` | x, y, attempts | docking_controller |
| `docking_failed` | attempts, reason | docking_controller |
| `docking_contact_verified` | — | docking_controller |
| `charging_started` | session_id, start_pct | charging_controller |
| `charging_fast` | — | charging_controller |
| `charging_trickle` | pct | charging_controller |
| `charging_complete` | end_pct, duration_s | charging_controller |
| `charging_aborted` | reason | charging_controller |
| `charging_emergency` | level, battery_pct, mode | emergency_charging |
| `charging_emergency_cleared` | — | emergency_charging |
| `charging_cycle_complete` | end_pct | charging_manager |
| `tasks_paused_for_charging` | saved_state | task_interruption |
| `tasks_resumed_after_charging` | restored_state | task_interruption |
| `power_profile_changed` | profile, brightness, animations | power_optimizer |
| `battery_cycle_recorded` | cycles, soh, energy_mah | battery_health |
| `charging_state_changed` | charging, percent | power_manager |

## Public API

```python
# Access the singleton
from tank_os.core.charging_manager import ChargingManager
cm = ChargingManager()
cm.initialize()

# Trigger immediate charging
cm.charge_now()

# Enable/disable auto-charging
cm.enable_auto_charge(True)

# Save dock position
cm.save_dock_position(x=2.5, y=1.0, yaw=0.0)

# Get comprehensive status
status = cm.get_status()
# {
#   "battery_pct": 45,
#   "charging": False,
#   "auto_charge": True,
#   "in_progress": False,
#   "dock_status": "DETECTED",
#   "charge_state": "IDLE",
#   "battery_health": {"cycles": 42, "soh_pct": 97.3, ...},
#   "power_profile": "balanced",
#   "emergency_active": False,
#   "tasks_paused": False,
# }

# Access individual subsystems
cm.dock_detection.detect_dock()
cm.dock_navigation.navigate_to_dock(dock_info)
cm.battery_health.summary()
cm.charging_scheduler.should_charge_now(35, "idle")
```
