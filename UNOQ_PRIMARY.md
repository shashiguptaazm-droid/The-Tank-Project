# ⚡ Arduino UNO Q — Primary Device

> **Competition requirement: UNO Q is the primary device**  
> **Registration: APC-2026-RJ-75818**

---

## 🎯 Why UNO Q Is Primary

The competition mandates the **Arduino UNO Q** as the primary device. In our architecture, the UNO Q serves as the **System Coordinator** — the central hub that connects everything.

```
┌─────────────────────────────────────────────────────┐
│                UNO Q 4GB                            │
│          SYSTEM COORDINATOR                         │
│                                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐│
│  │  QRB2210    │  │  STM32U585   │  │  TankOS    ││
│  │  Linux MPU  │  │  Real-time   │  │  Control   ││
│  │             │  │  MCU         │  │  Plane     ││
│  └──────┬──────┘  └──────┬───────┘  └─────┬──────┘│
│         │                │                 │        │
│         └────────────────┼─────────────────┘        │
│                          │                          │
└──────────────────────────┼──────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
    ┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐
    │  JETSON   │   │  ESP32s   │   │ ANDROID   │
    │  AI Brain │   │  Sensors  │   │    TV     │
    │  Vision   │   │  Actuators│   │   GUI     │
    │  Nav2/SLAM│   │  Real-time│   │  Display  │
    └───────────┘   └───────────┘   └───────────┘
```

---

## 🏗️ UNO Q Dual-Layer Architecture

The UNO Q has two processors in one board:

### Linux Side (QRB2210)
| Function | Description |
|----------|-------------|
| **TankOS Integration** | Connects to Jetson via Ethernet/USB |
| **System Coordination** | Routes commands between all devices |
| **Android TV GUI** | Runs the 10-foot robot interface |
| **Networking** | WiFi, Bluetooth, Tailscale mesh |
| **Device Discovery** | Finds and manages all connected devices |
| **Telemetry** | Collects and forwards sensor data |
| **Configuration** | Stores robot settings and preferences |
| **Diagnostics** | Health monitoring and fault detection |

### MCU Side (STM32U585)
| Function | Description |
|----------|-------------|
| **Motor PWM** | BTS7960 driver control |
| **Encoder Reading** | Quadrature encoder decoding |
| **Servo Control** | PCA9685 I²C servo driver |
| **IMU Reading** | BNO055/QMI8658 orientation |
| **E-STOP** | Hardware emergency stop |
| **Battery Monitor** | INA219 voltage/current |
| **Safety Watchdog** | Timeout and fault detection |
| **Deterministic I/O** | Real-time hardware control |

---

## 🔗 UNO Q Communication Map

| To Device | Protocol | Purpose |
|-----------|----------|---------|
| **Jetson** | Ethernet/USB | AI commands, vision data |
| **ESP32 ×6** | WiFi/USB | Sensor data, actuator commands |
| **Android TV** | DisplayPort/USB-C | GUI output |
| **Camera** | USB | Video feed (primary receiver) |
| **LiDAR** | USB-UART | Laser scan data |
| **LTE Modem** | USB-Serial | SMS, internet backup |
| **Phone** | Tailscale/WiFi | PWA dashboard |

---

## 📊 UNO Q as Competition Primary

### What the judges see:

1. **UNO Q boots** → Android TV GUI appears
2. **UNO Q discovers** → Jetson, ESP32s, sensors
3. **UNO Q coordinates** → All subsystems ready
4. **Human interacts** → Voice/Gesture/Touch via UNO Q
5. **UNO Q routes** → Commands to Jetson for AI
6. **Jetson reasons** → Returns decisions to UNO Q
7. **UNO Q executes** → Motors, servos via STM32
8. **UNO Q reports** → Status to Android TV + Phone

### Why this satisfies "UNO Q as primary":

- **Boot sequence starts on UNO Q**
- **All device connections pass through UNO Q**
- **Human interface runs on UNO Q**
- **Safety controller lives on UNO Q STM32**
- **Jetson is the AI brain, but UNO Q is the body coordinator**
- **ESP32s report to UNO Q, not directly to Jetson**

---

## 🔧 UNO Q Capabilities (100 Features)

| Category | Count | Key Features |
|----------|-------|-------------|
| Platform Intel | 10 | HW detection, I²C scan, USB inventory |
| TankOS Integration | 10 | EventBus, diagnostics, telemetry SQLite |
| MCU Supervision | 10 | Heartbeat, stall detection, watchdog |
| Motor Control | 10 | PID, dead-zone, stall, track-slip |
| Odometry | 10 | Velocity, noise filter, calibration |
| Safety | 10 | E-STOP FSM, interlocks, degraded mode |
| Power Intel | 10 | Dual INA219, energy calc, runtime |
| Servo Intel | 10 | PCA9685, calibration, collision protect |
| Sensor Reliability | 10 | BNO055 health, I²C recovery, quality |
| TV Launcher | 10 | 10-tile Android TV interface |

---

## 🎬 Competition Demo Flow

```
1. UNO Q boots → Android TV dashboard appears
2. UNO Q pings Jetson → "AI brain online"
3. UNO Q scans ESP32s → "5/6 nodes connected"
4. UNO Q initializes motors → "Motion ready"
5. UNO Q starts camera → "Vision active"
6. Human: "Patrol the room"
7. UNO Q → Jetson: "Generate patrol plan"
8. Jetson → UNO Q: "Route: A→B→C→D→A"
9. UNO Q validates safety → "Approved"
10. UNO Q → ESP32 motors: "Execute path"
11. UNO Q monitors → Reports to Android TV
12. UNO Q detects person → "Human detected"
13. UNO Q → Jetson: "Analyze scene"
14. Jetson → UNO Q: "Person at 3m, safe"
15. UNO Q continues patrol → Mission complete
16. UNO Q → Phone SMS: "Mission 42 complete"
```

---

## 🏆 Why UNO Q Wins as Primary

| Criterion | How UNO Q Delivers |
|-----------|-------------------|
| **System Coordinator** | Central hub connecting all devices |
| **Real-time Control** | STM32 MCU for deterministic motor/safety |
| **Human Interface** | Android TV GUI for interaction |
| **Device Management** | Discovers and manages Jetson, ESP32s |
| **Safety Controller** | Hardware E-STOP, watchdog, interlocks |
| **Networking** | WiFi, Bluetooth, Tailscale mesh |
| **AI Gateway** | Routes AI requests to Jetson |
| **Diagnostics** | Full system health monitoring |
| **Offline Capability** | Continues operating if Jetson fails |
| **Competition Compliance** | Primary device per requirements |

---

<p align="center">
  <sub>Arduino Physical AI Challenge 2026 · APC-2026-RJ-75818 · UNO Q is Primary</sub>
</p>
