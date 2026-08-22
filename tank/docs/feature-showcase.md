# Tank — Feature Showcase

> Competition: Arduino Physical AI Challenge 2026
> Registration: APC-2026-RJ-75818

## How to Run

```bash
# Run all 10 features
python3 -m tank.demo.full_showcase

# Slower pacing (for recording)
python3 -m tank.demo.full_showcase --slow

# Single feature
python3 -m tank.demo.full_showcase --feature config
python3 -m tank.demo.full_showcase --feature pipeline
```

## Features Demonstrated

| # | Feature | Module | What it shows |
|---|---------|--------|---------------|
| 1 | Configuration | `tank/core/config.py` | .env + YAML + env vars, no hardcoded secrets |
| 2 | Event Bus | `tank/core/event_bus.py` | 28 event types, pub/sub, history, thread-safe |
| 3 | State Machine | `tank/core/state_machine.py` | 10 states, validated transitions, emergency bypass |
| 4 | Sensor Abstraction | `tank/perception/sensor.py` | Abstract interface, hot-pluggable, mock support |
| 5 | Sensor Fusion | `tank/perception/sensor_fusion.py` | Camera+LiDAR+thermal, uncertainty tracking |
| 6 | AI Engine | `tank/ai/engine.py` | Structured JSON output, never direct motor control |
| 7 | Decision Engine | `tank/core/decision_engine.py` | AI→VALIDATE→SAFETY→DECIDE→ACT pipeline |
| 8 | Safety System | `tank/control/safety.py` | E-stop, watchdog, timeout, sensor failure |
| 9 | Simulation Mode | `tank/simulation/mock_sensors.py` | Full pipeline without hardware |
| 10 | Full Pipeline | `tank/main.py` | SENSE→PERCEIVE→FUSE→AI→DECIDE→ACT→VERIFY |

## Architecture

```
SENSE → PERCEIVE → FUSE → UNDERSTAND → DECIDE → ACT → VERIFY → LEARN/LOG
  │        │        │        │           │        │        │         │
  ▼        ▼        ▼        ▼           ▼        ▼        ▼         ▼
Sensor  Extract  Combine  AI Engine  Decision  Motor   Check    Log
Reads   Detections  Data   analyze()  Engine   Cmds   Result   Event
```

## Key Design Principles

1. **AI never executes directly** — always goes through Decision Engine
2. **Sensor abstraction** — same code for real hardware and simulation
3. **Safety first** — uncertain conditions → SAFE_STOP, not movement
4. **Structured output** — AI returns JSON, never free-form into motors
5. **No single point of failure** — VPS unavailable → OFFLINE_MODE
6. **Observable** — every event logged with timestamp, source, confidence
