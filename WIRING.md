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
| USB-A 4 | Quectel EG800K LTE | USB | AT commands |
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

## ⚠️ Safety Notes

1. **Common ground** — All boards MUST share a common GND
2. **E-STOP** — Hardware button cuts power to motors immediately
3. **No Jetson GPIO to motors** — Jetson NEVER touches motor wires
4. **USB serial only** — Jetson ↔ UNO Q communication via USB
5. **Current sensing** — INA219 monitors both motor and logic rails
