# 🔌 WIRING GUIDE — The Tank

> **Authoritative wiring for competition submission**

---

## 🔗 Jetson ↔ UNO Q Connection

| Jetson Pin | UNO Q Pin | Wire | Protocol |
|-----------|-----------|------|----------|
| USB-C (power) | — | USB-C cable | 5V/4A power |
| USB-A (data) | USB-C (data) | USB cable | Serial 115200 |
| — | GND | Common ground | Reference |

---

## ⚡ UNO Q STM32 Pin Map

### Motors (BTS7960)
| UNO Q Pin | Function | Wire | Destination |
|-----------|----------|------|-------------|
| D6 | Left Motor PWM | Orange | BTS7960 RPWM |
| D7 | Left Motor DIR | Yellow | BTS7960 LPWM |
| D4 | Right Motor PWM | Orange | BTS7960 RPWM |
| D5 | Right Motor DIR | Yellow | BTS7960 LPWM |

### Encoders
| UNO Q Pin | Function | Wire | Destination |
|-----------|----------|------|-------------|
| D2 | Left Encoder A | Green | JGB37-520 ENA |
| D3 | Left Encoder B | Blue | JGB37-520 ENB |
| D18 | Right Encoder A | Green | JGB37-520 ENA |
| D19 | Right Encoder B | Blue | JGB37-520 ENB |

### I²C Bus
| UNO Q Pin | Function | Wire | Destination |
|-----------|----------|------|-------------|
| A4 (SDA) | I²C Data | White | BNO055 + PCA9685 + INA219 |
| A5 (SCL) | I²C Clock | Black | BNO055 + PCA9685 + INA219 |
| 5V | Power | Red | Sensor VCC |
| GND | Ground | Black | Sensor GND |

### Safety
| UNO Q Pin | Function | Wire | Destination |
|-----------|----------|------|-------------|
| D9 | E-STOP Input | Red | Emergency button |
| D8 | E-STOP LED | Yellow | Status LED |

---

## 📡 I²C Addresses

| Device | Address | Board | Function |
|--------|---------|-------|----------|
| BNO055 | 0x28 | UNO Q | IMU |
| PCA9685 | 0x40 | UNO Q | Servo PWM |
| INA219 (motor) | 0x40 | UNO Q | Motor current |
| INA219 (logic) | 0x41 | UNO Q | Logic current |

---

## 📷 USB Connections to Jetson

| USB Port | Device | Cable | Protocol |
|----------|--------|-------|----------|
| USB-A 1 | LDROBOT LD19 LiDAR | USB-UART | 115200 baud |
| USB-A 2 | DFRobot AI Camera | USB-C | Serial 921600 |
| USB-A 3 | Arduino UNO Q | USB-C | Serial 115200 |
| USB-A 4 | Quectel EG800AK LTE | USB | AT commands |
| USB-C | Power (5V/4A) | USB-C | Power delivery |

---

## 🔋 Battery Wiring

```
4S Li-ion Pack (14.8V)
    │
    ├── (+) → BTS7960 VM (motor power)
    ├── (+) → DC/DC Buck → 5V (Jetson USB-C)
    ├── (+) → DC/DC Buck → 5V (UNO Q logic)
    ├── (+) → LDO → 3.8V (LTE modem)
    └── (-) → Common GND (all boards)
```

---

## 🦯 Blind-Assistance External Module Wiring

> See [docs/BLIND_ASSIST.md](docs/BLIND_ASSIST.md) for full module documentation.

### UNO Q ↔ Wearable Peripherals

| UNO Q Port | Peripheral | Cable | Protocol |
|-----------|------------|-------|----------|
| USB-C (PD) | Power Bank 10,000mAh | USB-C | 5V/3A PD |
| USB-C (data 1) | ESP32-S3 CAM (chest camera) | USB-C | WiFi/Serial |
| USB-C (data 2) | ESP32 Dual Screen + Speaker | USB-C | JSON/UART |
| USB-A 1 | Quectel EG800AK LTE Modem | USB-A | AT commands |
| USB-A 2 | USB Mini Microphone | USB-A | Audio input |
| USB-A 3 | Jetson Orin Nano (AI brain) | USB-C to USB-A | Serial 115200 |
| USB-A 4 | LDROBOT LD19 LiDAR (optional) | USB-UART | 115200 baud |

### ESP32 Dual Screen Pin Map (to GC9A01 ×2 + Speaker)

| ESP32-S3 Pin | Function | Wire | Destination |
|-------------|----------|------|-------------|
| GPIO 4 | Left LCD CS | Yellow | GC9A01 #1 CS |
| GPIO 5 | Right LCD CS | Orange | GC9A01 #2 CS |
| GPIO 6 | SPI SCK | Green | Both LCDs SCK |
| GPIO 7 | SPI MOSI | Blue | Both LCDs SDA |
| GPIO 8 | DC | Purple | Both LCDs DC |
| GPIO 9 | RST | Gray | Both LCDs RST |
| GPIO 10 | Backlight | White | Both LCDs BL |
| GPIO 11 | Speaker PWM | Red | 3W Speaker + |
| GND | Common GND | Black | All devices |

### E-STOP (Emergency Button)

| UNO Q Pin | Function | Wire | Destination |
|-----------|----------|------|-------------|
| D9 | E-STOP Input (pull-up) | Red | Momentary button (NC) |
| GND | Ground | Black | Button GND |
| D8 | Status LED | Yellow | Red LED + 220Ω → GND |

**Triple-tap within 2 seconds** triggers emergency SMS + alarm.

---

## ⚠️ Safety Notes

1. **Common ground** — All boards MUST share a common GND
2. **E-STOP** — Hardware button cuts power to motors immediately; triple-tap triggers emergency SMS in blind-assist mode
3. **No Jetson GPIO to motors** — Jetson NEVER touches motor wires
4. **USB serial only** — Jetson ↔ UNO Q communication via USB
5. **Current sensing** — INA219 monitors both motor and logic rails
6. **Power bank must support USB-C PD 5V/3A** — insufficient power causes camera dropouts
7. **LTE modem needs active SIM** — test with `mmcli -m 0 --command="AT+CSQ"` before demo
