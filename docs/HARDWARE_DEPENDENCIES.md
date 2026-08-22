# TankOS Hardware — Software Dependency Map

> **Authoritative reference** mapping every physical hardware component to its
> TankOS software module, required drivers, configuration, and dependency status.
>
> Hardware source-of-truth: `tank_ws/src/tank_meta/content/hardware.json`
> Wiring reference: `WIRING.md`
> BOM + prices: `hardware.md`

---

## 1. Hardware → TankOS Module Mapping

| # | Hardware | TankOS Module(s) | Driver / Library | Interface | Status |
|---|----------|-----------------|-------------------|-----------|--------|
| 1 | **NVIDIA Jetson Orin Nano (8 GB)** | All — Core OS, AIManager, Tank Shell | Linux kernel, rpi-config, GPU drivers | Native | ✅ Core |
| 2 | **7" DSI Touchscreen (800×480)** | TankShell (Qt GUI), TopBar, BottomDock | `vc4-kms-v3d` overlay, PySide6/Qt6 | DSI (15-pin FPC) | 🟡 Planned |
| 3 | **ESP32-S3 (Round Eye Display)** | `tank_vision.eye_lcd_bridge`, EmotionManager | `pyserial`, ESP32-S3 Arduino firmware | UART2 (GPIO8/9) @ 115200 | ✅ Done |
| 4 | **Waveshare 1.28" Round LCD × 2** | Eye expressions, Emotion animations | ESP32 firmware (GC9A101 SPI driver) | SPI → ESP32 → UART | ✅ Done |
| 5 | **1.3" SH1106 OLED (I²C)** | `tank_display` (status face) | `luma.oled`, I²C on GPIO2/3 | I²C (addr 0x3C) | ✅ Done |
| 6 | **DFRobot AI Camera** | `tank_vision` — object detection, YOLO | `ultralytics`, OpenCV, `picamera2` | USB or CSI | 🟡 Planned |
| 7 | **Jetson Camera Module 3 (IMX708)** | `tank_vision.camera_publisher` | `libcamera`, `picamera2`, OpenCV | CSI (15-pin FPC) | ✅ Done |
| 8 | **ProBots Tank Chassis Kit** | `tank_motion` — motor_controller | `gpiozero`, `Jetson.GPIO` or `pigpio` | GPIO (wired) | ✅ Done |
| 9 | **BTS7960 Motor Driver (×2)** | `tank_motion.motor_controller` | PWM + DIR via GPIO (level-shifted) | GPIO 12/13/18/19 | ✅ Done |
| 10 | **PCA9685 Servo Controller** | `tank_motion.pan_tilt_controller` | `adafruit-circuitpython-servokit` | I²C (addr 0x40) | 🟡 Planned |
| 11 | **SG90 Micro Servo (×2, pan/tilt)** | `tank_motion.pan_tilt_controller` | PCA9685 or direct PWM via `pigpio` | PWM (50 Hz) | 🟡 Planned |
| 12 | **MPU6050 IMU** | `tank_sensors.imu_publisher` | `Adafruit_MPU6050` or `smbus` | I²C (addr 0x68) | 🟡 Planned |
| 13 | **BNO055 9-DOF IMU** | `tank_sensors.imu_publisher` | `Adafruit_BNO055` | I²C (addr 0x28) | 🟡 Planned (upgrade) |
| 14 | **HC-SR04 Ultrasonic (×2)** | `tank_sensors` — obstacle detection | `gpiozero` DistanceSensor | GPIO trigger/echo | 🟡 Planned |
| 15 | **TF-Luna/Benewake LiDAR** | `tank_navigation` — obstacle avoidance | `pyserial` or ROS `sensor_msgs` | UART (GPIO14/15) | 🟡 Considering |
| 16 | **RPLidar A1 / LD19** | `tank_navigation.slam_2d_bridge` | `rplidar_ros` / `ldrobot_lidar_ros` | USB serial | 🟡 Planned |
| 17 | **AMG8833 Thermal Camera** | `tank_security` / `tank_vision` — heat detection | `Adafruit_AMG88xx`, OpenCV | I²C (addr 0x69) | 🟡 Experimental |
| 18 | **AS608 Fingerprint Sensor** | `tank_security` — authentication | `adafruit-circuitpython-fingerprint` | UART (GPIO14/15) | 🟡 Planned |
| 19 | **MAX98357A Amplifier** | `tank_text.tts_node` — voice output | `sounddevice`, `numpy` | I²S (GPIO18-21) | 🟡 Planned |
| 20 | **USB Mic / ReSpeaker 4-Mic** | `tank_speech.wake_word_listener` | `sounddevice`, `openWakeWord`, `pyaudio` | USB Audio | 🟡 Planned |
| 21 | **SIM7600G / Quectel EC25 LTE** | `tank_os.NetworkManager` — cellular failover | `ppp`, `NetworkManager`, AT commands | USB (ttyUSBx) | 🟡 Planned |
| 22 | **SIM800L V2 (GSM)** | `tank_os.NetworkManager` — SMS/GSM | `pyserial`, AT commands | UART | 🔴 Experimental |
| 23 | **NVMe SSD (256 GB via M.2 HAT)** | TankOS StorageManager, AI model storage | `nvme` driver, `fstab` auto-mount | PCIe (M.2 HAT+) | ✅ Done |
| 24 | **USB Hub (4-port)** | `tank_os.HardwareManager` — USB detection | Linux `usbhid` | USB | ✅ Done |
| 25 | **Portronics 20K mAh Power Bank** | `tank_health`, PowerManager — PD monitoring | INA219 sensor | USB-C PD | ✅ Done |
| 26 | **4S Li-ion Battery Pack** | Motor power — `tank_health.battery` | INA219 voltage divider | XT60 connector | 🟡 Planned |
| 27 | **ESP32 Boards (extra)** | Wireless sensor bridge, motor controller | `pyserial`, `esptool` | UART / WiFi | 🟡 Planned |
| 28 | **USB TTL CH341A** | Debug / programming interface | `ch341` kernel module | USB → UART | ✅ Done |
| 29 | **GPIO Expansion Board** | Hardware prototyping | `Jetson.GPIO` / `gpiozero` | 40-pin GPIO | ✅ Done |

---

## 2. Module Dependency Graph

```
TankOS Layer 3 (Core Managers)
│
├── HardwareManager        ← USB Hub, GPIO Expansion, all USB devices
├── NetworkManager         ← SIM7600G LTE, SIM800L, Wi-Fi, Ethernet
├── StorageManager         ← NVMe SSD, SD Card
├── PowerManager           ← Power Bank, INA219, 4S Li-ion
├── SecurityManager        ← AS608 Fingerprint
├── DiagnosticsManager     ← All sensors (read-only health)
│
├── EmotionManager         ← ESP32-S3 Eyes (expression fan-out)
│
├── RobotManager           ← BTS7960, SG90 Servos, PCA9685
│   └── tank_motion/motor_controller.py
│   └── tank_motion/pan_tilt_controller.py
│
├── VisionManager          ← Jetson Camera, DFRobot AI Cam, AMG8833
│   └── tank_vision/camera_publisher.py
│   └── tank_vision/object_tracker.py (YOLO)
│   └── tank_vision/eye_lcd_bridge.py → ESP32-S3
│
├── NavigationManager      ← RPLidar, TF-Luna, MPU6050/BNO055
│   └── tank_sensors/lidar_publisher.py
│   └── tank_sensors/imu_publisher.py
│   └── tank_navigation/slam_2d_bridge.py
│
├── VoiceManager           ← ReSpeaker Mic, MAX98357A
│   └── tank_speech/wake_word_listener.py
│   └── tank_text/tts_node.py
│
└── DisplayManager         ← 7" DSI Screen, SH1106 OLED
    └── tank_display/       (OLED face)
    └── tank_os/shell/       (Qt GUI / DSI screen)
```

---

## 3. Required Software Dependencies

### System Packages (apt)

| Package | For Hardware | Module |
|---------|-------------|--------|
| `libraspberrypi-bin` | Jetson Camera | `tank_vision` |
| `libcamera-apps` | Jetson Camera | `tank_vision` |
| `python3-picamera2` | Jetson Camera | `tank_vision` |
| `i2c-tools` | I²C sensors (MPU6050, BNO055, PCA9685, AMG8833) | All I²C |
| `python3-smbus` | I²C bus access | `tank_sensors` |
| `python3-gpiozero` | GPIO sensors (HC-SR04, BTS7960) | `tank_motion`, `tank_sensors` |
| `python3-serial` | UART devices (ESP32, Fingerprint, LiDAR) | Various |
| `libraspberrypi0` | DSI display | Tank Shell |
| `mesa-utils` | GPU acceleration | All Qt |
| `bluez` | Bluetooth | `tank_os` |
| `p7zip-full` | Archive extraction | PreloadManager |
| `ffmpeg` | Media processing | `tank_vision` |

### Python Packages (pip)

| Package | For Hardware | Module |
|---------|-------------|--------|
| `PySide6` | 7" DSI Screen | Tank Shell (Qt GUI) |
| `opencv-python` | Jetson Camera, DFRobot Camera | `tank_vision` |
| `ultralytics` | DFRobot Camera (YOLO) | `tank_vision` |
| `picamera2` | Jetson Camera Module 3 | `tank_vision` |
| `Adafruit_MPU6050` | MPU6050 IMU | `tank_sensors` |
| `Adafruit_BNO055` | BNO055 IMU | `tank_sensors` |
| `adafruit-circuitpython-servokit` | PCA9685 | `tank_motion` |
| `adafruit-circuitpython-amg88xx` | AMG8833 Thermal | `tank_security` |
| `adafruit-circuitpython-fingerprint` | AS608 Fingerprint | `tank_security` |
| `luma.oled` | SH1106 OLED | `tank_display` |
| `sounddevice` | MAX98357A, ReSpeaker | `tank_speech`, `tank_text` |
| `openWakeWord` | ReSpeaker Mic | `tank_speech` |
| `pyserial` | UART (ESP32, LiDAR, Fingerprint, LTE) | Various |
| `rplidar-ros` | RPLidar A1 | `tank_navigation` |
| `pigpio` | Servo PWM, GPIO | `tank_motion` |
| `numpy` | I²S audio, sensor fusion | Various |

### Firmware

| Hardware | Firmware | Flashed via |
|----------|----------|-------------|
| ESP32-S3 Eyes | `firmware/eyes_esp32/eyes_esp32.ino` | Arduino IDE / esptool |
| PCA9685 | None (I²C registers) | — |
| BTS7960 | None (PWM/DIR logic) | — |

---

## 4. Hardware Status Summary

| Status | Count | Items |
|--------|-------|-------|
| ✅ **Owned + Working** | 10 | RJetson, NVMe, ESP32-S3 Eyes, Round LCDs, OLED, Camera Module 3, Chassis, BTS7960, USB Hub, CH341 |
| 🟡 **Owned — Not Integrated** | 12 | DSI Screen, DFRobot Cam, PCA9685, SG90 Servos, MPU6050, HC-SR04, Fingerprint, ReSpeaker, Power Bank, GPIO Expansion, Extra ESP32 |
| 🟡 **Planned Purchase** | 5 | BNO055, RPLidar, MAX98357A, 4S Li-ion, TF-Luna |
| 🔴 **Experimental** | 2 | AMG8833, SIM800L |

---

## 5. Wiring Reference

| Pi GPIO | Hardware | Purpose |
|---------|----------|---------|
| GPIO2/3 (I²C1) | MPU6050, BNO055, PCA9685, SH1106, AMG8833 | Shared I²C bus (0x3C–0x70) |
| GPIO8/9 (UART1) | ESP32-S3 (eyes) | JSON commands to eye display |
| GPIO14/15 (UART0) | AS608 Fingerprint | Authentication |
| GPIO12/13 | BTS7960 (Motor 1) | PWM + DIR |
| GPIO18/19 | BTS7960 (Motor 2) / SG90 Servos | PWM + DIR |
| GPIO23/24 | HC-SR04 (Front) | Trigger + Echo |
| GPIO25/26 | HC-SR04 (Rear) | Trigger + Echo |
| GPIO18-21 (I²S) | MAX98357A Amplifier | Audio output |
| CSI (15-pin) | Jetson Camera Module 3 | Video input |
| DSI (15-pin) | 7" Touchscreen | Display output |
| USB | Hub → ReSpeaker, LTE Modem, LiDAR, DFRobot Cam | Data + Power |
| PCIe (M.2 HAT) | NVMe SSD | Storage |

---

## 6. Configuration Template

```json
{
  "hardware": {
    "display": {
      "dsi": { "enabled": true, "rotation": 0, "touch": true },
      "oled": { "enabled": true, "i2c_addr": "0x3C", "type": "sh1106" }
    },
    "eyes": {
      "enabled": true,
      "uart": "/dev/ttyAMA1",
      "baud": 115200,
      "type": "gc9a101"
    },
    "camera": {
      "primary": { "enabled": true, "interface": "csi", "type": "imx708" },
      "thermal": { "enabled": false, "i2c_addr": "0x69", "type": "amg8833" }
    },
    "motion": {
      "motors": {
        "driver": "bts7960",
        "pins": { "left_pwm": 12, "left_dir": 13, "right_pwm": 18, "right_dir": 19 }
      },
      "servos": {
        "driver": "pca9685",
        "i2c_addr": "0x40",
        "pan_channel": 0,
        "tilt_channel": 1
      }
    },
    "sensors": {
      "imu": { "enabled": false, "type": "mpu6050", "i2c_addr": "0x68" },
      "lidar": { "enabled": false, "interface": "serial", "type": "rplidar_a1" },
      "ultrasonic": {
        "front": { "trigger": 23, "echo": 24 },
        "rear": { "trigger": 25, "echo": 26 }
      }
    },
    "security": {
      "fingerprint": { "enabled": false, "uart": "/dev/ttyAMA0", "type": "as608" }
    },
    "audio": {
      "mic": { "enabled": false, "type": "respeaker_4mic" },
      "speaker": { "enabled": false, "type": "max98357a", "i2s_pins": [18, 19, 20, 21] }
    },
    "network": {
      "lte": { "enabled": false, "interface": "/dev/ttyUSB2", "type": "sim7600g" }
    },
    "power": {
      "ina219_pi": { "enabled": true, "i2c_addr": "0x40" },
      "ina219_motor": { "enabled": false, "i2c_addr": "0x41" }
    }
  }
}
```

---

## 7. Startup Sequence (Hardware Init Order)

```
Boot Step               Hardware Initialized
──────────              ─────────────────────
1. init_logging         (none)
2. load_config          Loads hardware config from settings.json
3. init_hardware        I²C bus, UARTs, SPI, CSI, DSI
                        ├── Detect I²C devices (MPU6050, PCA9685, OLED, etc.)
                        ├── Detect Camera (CSI or USB)
                        ├── Detect ESP32-S3 on UART
                        └── Mount NVMe SSD
4. start_ros            Launch ROS2 nodes for sensors
5. verify_services      Check all hardware is responsive
6. init_plugins         Plugin system
7. init_gui             Qt window (DSI screen), OLED face
8. start_ai             AI Manager + Evolution Bridge
9. start_voice          Mic array, wake word, TTS
10. open_dashboard      Web UI, port 8080
11. accept_input        Ready for user
```
