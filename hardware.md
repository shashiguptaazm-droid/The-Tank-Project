# 🔧 HARDWARE — The Tank

> **Complete Bill of Materials (BOM)**

---

## 📊 Component Summary

| Category | Count | Status |
|----------|-------|--------|
| Compute | 3 | Jetson + UNO Q + VPS |
| Vision | 2 | DFRobot Camera + LDROBOT LiDAR |
| Motion | 4 | 2×BTS7960 + 2×JGB37-520 Motors |
| Sensors | 5 | IMU + INA219×2 + PCA9685 + LTE |
| Communication | 2 | Tailscale + Quectel LTE |
| Power | 2 | 4S Li-ion + DC/DC Buck |
| Chassis | 1 | Tracked robot chassis |
| ESP32 | 6 | ESP32-S3 DevKitC-1 N16R8 |
| **TOTAL** | **25** | **Core components** |

---

## 🧠 Compute

| Component | Model | Specs | Price (₹) |
|-----------|-------|-------|-----------|
| Jetson Orin Nano Super | NVIDIA | 8GB, 67 TOPS, JetPack 6.2 | 25,000 |
| Arduino UNO Q 4GB | Arduino | QRB2210 + STM32U585 | 12,500 |
| VPS | Hetzner | 4 vCPU, 8GB RAM | 750/mo |
| **Subtotal** | | | **38,250** |

---

## 👁️ Vision

| Component | Model | Specs | Price (₹) |
|-----------|-------|-------|-----------|
| AI Camera | DFRobot SEN0611 | ESP32-S3, USB, Night Vision | 3,500 |
| LiDAR | LDROBOT LD19 | 360°, 12m, 5kHz | 4,500 |
| **Subtotal** | | | **8,000** |

---

## 🛞 Motion

| Component | Model | Specs | Price (₹) |
|-----------|-------|-------|-----------|
| Motor Driver | BTS7960 ×2 | 43A, H-Bridge | 600 |
| DC Motor | JGB37-520 ×2 | 12V, geared, encoder | 1,200 |
| Servo Driver | PCA9685 | 16-ch PWM | 300 |
| **Subtotal** | | | **2,100** |

---

## 📡 Sensors

| Component | Model | Interface | Price (₹) |
|-----------|-------|-----------|-----------|
| IMU | QMI8658 | I²C | 500 |
| Battery Monitor | INA219 ×2 | I²C | 400 |
| Servo Controller | PCA9685 | I²C | 300 |
| **Subtotal** | | | **1,200** |

---

## 📶 Communication

| Component | Model | Specs | Price (₹) |
|-----------|-------|-------|-----------|
| 4G LTE Modem | Quectel EG800K | Airtel SIM | 2,500 |
| Tailscale | Software | Mesh VPN | Free |
| **Subtotal** | | | **2,500** |

---

## 🔋 Power

| Component | Model | Specs | Price (₹) |
|-----------|-------|-------|-----------|
| Battery | 4S Li-ion | 14.8V, 5000mAh | 3,000 |
| DC/DC Buck | XL4015 | 12V→5V/5A | 200 |
| **Subtotal** | | | **3,200** |

---

## 🤖 ESP32 Swarm

| Component | Model | Qty | Price (₹) |
|-----------|-------|-----|-----------|
| ESP32-S3 DevKitC-1 | N16R8 | 6 | 1,800 |
| **Subtotal** | | | **1,800** |

---

## 🦯 Blind-Assistance External Module

> Detachable wearable module that extends the Tank for visually impaired users.
> See [docs/BLIND_ASSIST.md](docs/BLIND_ASSIST.md) for full documentation.

| Component | Model | Specs | Price (₹) |
|-----------|-------|-------|-----------|
| ESP32-S3 CAM | ESPHome, WiFi | 640×480, 8.9fps, night vision | 600 |
| ESP32 Dual Screen | 2× GC9A01 Round LCD | 240×240, speaker driver | 500 |
| Speaker | 3W mini | 3.5mm / USB | 200 |
| Microphone | USB mini mic | Voice command input | 300 |
| Power Bank | 10,000 mAh USB-C PD | 8+ hour runtime | 1,200 |
| Wearable Harness | Belt + shoulder mount | Ergonomic wear | 500 |
| Cables & Connectors | USB-C, jumpers | | 500 |
| **Module Subtotal** | | | **3,800** |

**Module uses UNO Q + Jetson + LTE from core BOM.** Total effective cost when used as blind-assistance device: **₹56,300**.

---

## 💰 Total Cost

| Category | Amount (₹) |
|----------|------------|
| Compute | 38,250 |
| Vision | 8,000 |
| Motion | 2,100 |
| Sensors | 1,200 |
| Communication | 2,500 |
| Power | 3,200 |
| ESP32 | 1,800 |
| Chassis | 5,000 |
| Blind-Assist Module | 3,800 |
| Misc (wires, connectors) | 2,000 |
| **GRAND TOTAL (with blind module)** | **₹67,850 (~$850)** |

---

## 📦 Component Images

See `images/` directory for hardware photos (including `20260823_235016.jpg` and `20260823_235019.jpg` — blind-assistance module setup) and `assets/infographics/` for visual documentation.
