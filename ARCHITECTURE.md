# 🏗️ ARCHITECTURE — The Tank

> **Complete system architecture for competition submission**

---

## 🧠 Three-Layer Architecture

```
┌─────────────────────────────────────────────────┐
│              JETSON ORIN NANO SUPER              │
│                  8GB · 67 TOPS                   │
│                                                 │
│  GPU Foundation │ Camera │ Detection │ Tracking  │
│  Semantic │ Depth │ SLAM │ Fusion │ Navigation   │
│  Predictive │ VLM │ Edge-AI │ Resource Manager  │
│  ROS2 Humble │ Nav2 │ SLAM Toolbox │ TF2        │
│  TankOS │ Tool Registry │ Evolution │ SMS/GSM   │
└───────────────────┬─────────────────────────────┘
                    │ USB Serial 115200
┌───────────────────▼─────────────────────────────┐
│               ARDUINO UNO Q 4GB                 │
│        QRB2210 Linux + STM32U585 MCU            │
│                                                 │
│  Linux Side:          │  MCU Side:              │
│  TankOS Integration   │  Motor PWM (BTS7960)    │
│  TV Launcher          │  Encoder Acquisition    │
│  Network Bridge       │  Servo Control (PCA9685)│
│  Diagnostics          │  IMU (BNO055)           │
│  Telemetry (SQLite)   │  Safety / E-STOP        │
│  EventBus             │  Battery (INA219)        │
│  Configuration        │  Watchdog               │
└───────────────────┬─────────────────────────────┘
                    │ I²C / GPIO / UART
┌───────────────────▼─────────────────────────────┐
│              ESP32-S3 ×6 SWARM                   │
│                                                 │
│  Node 1: Eye Displays (left + right)            │
│  Node 2: Hand Controller (gripper)              │
│  Node 3: Limb Sensor Array                      │
│  Node 4: Environment Sensors                    │
│  Node 5: Audio Processing                       │
│  Node 6: Backup / Future Expansion              │
└─────────────────────────────────────────────────┘
```

---

## 📡 Communication Map

| Source | Destination | Protocol | Baud/Rate | Purpose |
|--------|------------|----------|-----------|---------|
| Jetson | UNO Q | USB Serial | 115200 | Motor commands |
| UNO Q | Jetson | USB Serial | 115200 | Encoder/sensor data |
| Jetson | LiDAR | USB-UART | 115200 | Laser scans |
| Jetson | Camera | USB Serial | 921600 | JPEG frames |
| Jetson | LTE Modem | USB-Serial | AT cmds | SMS/data |
| UNO Q | BNO055 | I²C | 400kHz | IMU data |
| UNO Q | PCA9685 | I²C | 400kHz | Servo PWM |
| UNO Q | INA219 ×2 | I²C | 400kHz | Battery/power |
| UNO Q | ESP32 | I²C/GPIO | 400kHz | Peripheral data |
| Jetson | VPS | Tailscale | 1Gbps | Cloud AI/dashboard |
| Phone | VPS | HTTPS | 4G/5G | PWA dashboard |

---

## 🧠 AI Pipeline

```
Camera (USB)  LiDAR (USB)  IMU (I²C)  Encoders (GPIO)
     │              │           │            │
     ▼              ▼           ▼            ▼
 Camera Intel   LiDAR Proc  IMU Driver  Encoder Read
     │              │           │            │
     ▼              ▼           ▼            ▼
 YOLO Detect   Occupancy   Kalman Filt  Odometry
     │          Grid          │            │
     ▼              │         ▼            │
 Multi-Track        │    Sensor Fusion ◄───┘
     │              │         │
     ▼              ▼         ▼
 Scene Class    Nav2 SLAM  Decision Engine
     │              │         │
     ▼              ▼         ▼
 VLM Describe   Path Plan  Tool Caller
     │              │         │
     ▼              ▼         ▼
 Vision-Lang    Waypoints  Motor Cmd
     │              │         │
     ▼              ▼         ▼
 Chat/Plan    Avoidance   UNO Q → Motors
```

---

## 🔋 Power Architecture

```
4S Li-ion Battery (14.8V nominal / 16.8V full)
         │
         ├── BTS7960 → DC Motors (tracked)
         ├── DC/DC → Jetson (5V/4A USB-C)
         ├── DC/DC → UNO Q (5V logic)
         ├── Direct → LTE Modem (3.8V via regulator)
         └── Direct → ESP32 nodes (3.3V via regulator)
```

---

## 📦 Software Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| OS | Ubuntu 22.04 (JetPack 6) | JetPack 6.2 |
| CUDA | NVIDIA CUDA | 12.6 |
| TensorRT | NVIDIA TensorRT | 10.3 |
| cuDNN | NVIDIA cuDNN | 9.3 |
| VPI | NVIDIA VPI | 3.2 |
| ROS2 | ROS2 Humble | Latest |
| Nav2 | ROS Navigation | Latest |
| SLAM | SLAM Toolbox | Latest |
| Python | CPython | 3.10+ |
| OpenCV | OpenCV | 4.x+ |
| YOLO | Ultralytics YOLOv8 | Latest |
| LLM | llama.cpp | Latest |
| FastAPI | FastAPI | Latest |

---

## 📊 Feature Summary

| Board | Features | Modules | Status |
|-------|----------|---------|--------|
| Jetson Orin Nano Super | 200 | 12 AI modules | 🟢 12/12 tested |
| Arduino UNO Q 4GB | 100 | 10 system modules | 🟢 10/10 tested |
| TankOS Core | 74 | 9 core modules | 🟢 9/9 tested |
| **Total** | **374** | **31 modules** | **31/31 tested** |

---

## 🏆 Competition Hierarchy

> **Jetson decides WHAT the robot should do;**  
> **UNO Q deterministically controls WHAT the hardware physically does;**  
> **ESP32-S3 nodes handle distributed peripheral functions.**

This clean separation makes the architecture:
- **Modular** — each board has a clear responsibility
- **Testable** — each layer can be validated independently
- **Scalable** — new sensors/actuators just add to the appropriate layer
- **Safe** — E-STOP hardware safety above both Jetson and UNO Q
