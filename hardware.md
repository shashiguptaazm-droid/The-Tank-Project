# 🧰 The Tank Project — Complete Hardware List

> **Source of truth:** `tank_ws/src/tank_meta/content/hardware.json`
> (the file the project's own `tank_meta` indexer introspects, 12 components)
> + `WIRING.md` + `ARCHITECTURE.md` for the implicit physical-build items.
>
> **Prices are approximate for July 2026 in INR (₹) on amazon.in.**
> Treat each band as a planning estimate; listings rotate weekly.
> Every Amazon link below is a *search URL* — never a single ASIN — so it
> never 404s even when a listing changes. Swap `amazon.in → amazon.com`
> for US pricing.
>
> **Currency disclaimer:** Amazon-IN prices include GST; during sales
> (Prime Day, Republic Day) and with SBI / HDFC / ICICI cashback you can
> knock **10–15 %** off the mid-band. The mid-band numbers below are the
> realistic "buy today" prices.
>
> ⚡ **Power architecture (revised):** Jetson Orin Nano powered via 19 V DC barrel jack
> **separately** from a 12 V motor battery → BTS7960 drivers and motors.
> Keeping the motor rail and the Jetson rail on *isolated* grounds prevents
> motor current spikes from sagging Jetson voltage → brownout resets.

---

## 📊 Bill of Materials — at a glance

| Section | Items | Sub-total mid-band |
|---|---|---:|
| 1. Compute / Brains | 5 | ₹ 42,500 |
| 2. Vision / Display | 4 | ₹ 6,200 |
| 3. Motion / Drive Train | 8 | ₹ 9,650 |
| 4. Sensors | 7 | ₹ 9,950 |
| 5. Audio In / Out | 4 | ₹ 4,750 |
| 6. Power / Battery | 2 | ₹ 1,900 |
| 7. Networking / Cellular | 4 | ₹ 5,950 |
| 8. Chassis / Wiring / Safety | 8 | ₹ 6,650 |
| **Grand total mid-band** | **42** | **₹ 88,750** |
| Lower / upper band | | **₹ 76,500 — ₹ 1,06,000** |

> **Money saved vs. earlier draft: ~₹ 9,550** (the 4 removed power items +
> a generic Cytron MDD10A that was already covered by the BTS7960 in hand).
> **Jetson + Arduino upgrade** adds ~₹ 24,000 over the Jetson baseline but
> provides hardware-accelerated CUDA AI inference and real-time motor control.
>
> Add **≈ ₹ 4,500** for a basic toolbox (soldering iron, heat gun, snips,
> screwdrivers, multimeter) if you don't already own one.

---

## 1️⃣ Compute / Brains

| # | Item | Photo / Google-Shopping Description | Driver / Use in The Tank | Price (₹) | Amazon Search Link |
|---|------|--------------------------------------|--------------------------|----------:|--------------------|
| 1 | **NVIDIA Jetson Orin Nano Dev Kit (8 GB)** | Black rectangular carrier board, NVIDIA module on top with heatsink + fan, DisplayPort, 2× MIPI CSI, M.2 slot, USB-C, RJ45, 40-pin GPIO header, 19 V barrel jack | **AI Brain** — runs ROS 2 Humble, all 16 ament_python packages, TankOS GUI, on-device AI inference (CUDA-accelerated llama.cpp, Whisper, YOLOv8n, SDXL) | 25,000 – 35,000 | [amazon.in/s?k=jetson+orin+nano+dev+kit+8gb](https://www.amazon.in/s?k=jetson+orin+nano+dev+kit+8gb) |
| 2 | **Arduino UNO R4 WiFi** | Blue rectangular board, USB-C, 2×15-pin female headers, ESP32-S3 co-processor for Wi-Fi/BLE, 12×8 LED matrix, Qwiic I²C connector, Arm Cortex-M4 @ 48 MHz | **Real-time controller** — motor PWM, encoder tick counting (hardware interrupts), I²C sensor polling, serial bridge (115200 baud) to Jetson. Offloads all deterministic timing from Jetson. | 1,800 – 2,500 | [amazon.in/s?k=arduino+uno+r4+wifi](https://www.amazon.in/s?k=arduino+uno+r4+wifi) |
| 3 | **M.2 NVMe SSD 256 GB** (Samsung 980 / WD SN570 / Crucial P3) | Stick-shaped module ~22 × 80 mm, green PCB, gold contact edge, "NVMe" label | `/var/lib/tank` for vector memory, ROS bags, recordings, sqlite-vec db, AI model cache | 3,500 – 5,500 | [amazon.in/s?k=m.2+nvme+256gb](https://www.amazon.in/s?k=m.2+nvme+256gb) |
| 4 | **ESP32-S3 DevKitC-1** (N16R8) | Narrow black dev board, dual-row pin headers, USB-C on one short edge, tiny PCB antenna trace, Espressif logo | Drives the 2 × round eye displays over SPI, receives JSON over UART from Jetson | 700 – 1,100 | [amazon.in/s?k=esp32-s3+devkitc-1+n16r8](https://www.amazon.in/s?k=esp32-s3+devkitc-1+n16r8) |
| 5 | **MicroSD card 64 GB A2** | Tiny blue/black microSD card, ~15 × 11 mm | Boot drive for Jetson (JetPack 6) | 600 – 900 | [amazon.in/s?k=micro+sd+64gb+a2](https://www.amazon.in/s?k=micro+sd+64gb+a2) |

**Subtotal 1 → ₹ 31,600 – 45,000 (mid ₹ 42,500)**

> ⚡ **Two-board architecture:** Jetson Orin Nano is the *AI brain* (high-level ROS2 nodes,
> AI inference, TankOS GUI). Arduino UNO R4 WiFi is the *real-time controller* (motor PWM,
> encoder interrupts, sensor I²C reads). They communicate over USB serial at 115200 baud
> with a compact binary protocol. This split keeps real-time deadlines on the Arduino
> (sub-millisecond encoder response) while Jetson handles the heavy AI workloads.

---

## 2️⃣ Vision / Display

| # | Item | Photo / Google-Shopping Description | Driver / Use | Price (₹) | Amazon Link |
|---|------|--------------------------------------|--------------|----------:|-------------|
| 7 | **Waveshare 1.28″ Round LCD (GC9A101)** × 2 | Round TFT disc ~32 mm diameter, 240 × 240 px, short FPC tail, "GC9A01" silkscreened | Animated eye expressions (left + right), driven by the ESP32-S3 firmware | 2 × (1,400 – 2,000) = 2,800 – 4,000 | [amazon.in/s?k=waveshare+1.28+round+lcd+gc9a01](https://www.amazon.in/s?k=waveshare+1.28+round+lcd+gc9a01) |
| 8 | **1.3″ SH1106 / SSD1306 OLED (I²C)** | Tiny blue/white OLED ~30 × 35 mm, 4-pin I²C tail, blue glow when on | Status face on chassis front (`tank_display` package) | 350 – 600 | [amazon.in/s?k=1.3+oled+sh1106+i2c](https://www.amazon.in/s?k=1.3+oled+sh1106+i2c) |
| 9 | **USB Camera (IMX219 / IMX477 / C920 webcam)** | Small USB webcam, clip-on mount, UVC-compatible | ROS `tank_vision.camera_publisher` via OpenCV (1280 × 960 @ 30 fps). USB to Jetson — no CSI ribbon needed | 1,200 – 2,500 | [amazon.in/s?k=usb+webcam+1080p](https://www.amazon.in/s?k=usb+webcam+1080p) |
| 10 | **M2.5 / M3 standoff kit (nylon)** | Small black/white hex standoffs, 5/10/15/20 mm lengths, ~50 pcs | Mounts Jetson + Arduino + camera board inside the chassis | 250 – 450 | [amazon.in/s?k=m3+nylon+standoff+kit](https://www.amazon.in/s?k=m3+nylon+standoff+kit) |

**Subtotal 2 → ₹ 4,600 – 7,550 (mid ₹ 6,200)**

---

## 3️⃣ Motion / Drive Train

| # | Item | Photo / Google-Shopping Description | Driver / Use | Price (₹) | Amazon Link |
|---|------|--------------------------------------|--------------|----------:|-------------|
| 12 | **2 × 12 V DC geared motor w/ encoder (e.g. JGB37-520, 30:1 or 60:1)** | Cylindrical black gearbox ~65 × 22 mm, D-shaft, pigtail with 6 wires (motor + encoder A/B) | Left + right drive motor. `tank_motion.motor_controller` w/ BTS7960 | 2 × (650 – 950) = 1,300 – 1,900 | [amazon.in/s?k=jgb37-520+encoder+motor](https://www.amazon.in/s?k=jgb37-520+encoder+motor) |
| 13 | **2 × BTS7960 43 A motor driver (already on hand)** ★ | Big red PCB ~50 × 50 mm with two large terminal blocks and big heatsinks; *one driver per motor* | H-bridge for the two drive motors, PWM + DIR control. **Already purchased — no buy.** | 0 (owned) | — |
| 14 | **Tracked chassis w/ 12 V motors (aluminium, ~15 cm wheelbase)** | Two black rubber tracks, side aluminium plates, motor mounts pre-drilled | The tank's body — bolts the motors, Pi, and battery together | 1,800 – 3,200 | [amazon.in/s?k=tracked+robot+chassis+12v](https://www.amazon.in/s?k=tracked+robot+chassis+12v) |
| 15 | **2 × Tower Pro SG90 micro servo (pan + tilt)** | Tiny blue servo ~23 × 12 mm, 3-wire pigtail (signal/V+/GND), white spline horn on top | Pan-tilt head. `pan_tilt_controller` on GPIO18 + GPIO19 at 50 Hz | 2 × (180 – 280) = 360 – 560 | [amazon.in/s?k=tower+pro+sg90+servo](https://www.amazon.in/s?k=tower+pro+sg90+servo) |
| 16 | **PCA9685 16-channel 12-bit PWM / Servo HAT (I²C 0x40)** | Small purple/blue breakout ~63 × 25 mm, 16 × 3-pin servo headers in two rows | Lets you offload the pan/tilt servos off the Pi's PWM | 450 – 750 | [amazon.in/s?k=pca9685+servo+driver+i2c](https://www.amazon.in/s?k=pca9685+servo+driver+i2c) |
| 17 | **Pan-tilt bracket (2-axis, SG90-compatible, plastic / aluminium)** | Black U-shaped bracket with two axis pivots and mounting flanges | Mechanical mount for the head with the camera + eyes | 250 – 450 | [amazon.in/s?k=pan+tilt+bracket+sg90](https://www.amazon.in/s?k=pan+tilt+bracket+sg90) |
| 18 | **Mushroom-head E-STOP switch (NO/NC, panel-mount, 16 mm)** | Big red mushroom button with yellow guard ring, 2-pin NO/NC terminals | Hardware kill-switch in series with the BMS VBAT trace | 150 – 350 | [amazon.in/s?k=mushroom+emergency+stop+button](https://www.amazon.in/s?k=mushroom+emergency+stop+button) |

**Subtotal 3 → ₹ 4,310 – 7,760 (mid ₹ 9,650)** *(chassis dominates)*
★ = good stock already owned; do not buy.

---

## 4️⃣ Sensors

| # | Item | Photo / Google-Shopping Description | Driver / Use | Price (₹) | Amazon Link |
|---|------|--------------------------------------|--------------|----------:|-------------|
| 19 | **RPLidar A1** *or* **LDROBOT LD19** (360° LiDAR) | Black cylinder ~98 × 65 mm spinning disc on top, USB-A pigtail, or small black puck with motor | `tank_sensors.lidar_publisher` over `/dev/ttyUSB0` @ 115200 baud | 5,000 – 8,500 | [amazon.in/s?k=rplidar+a1](https://www.amazon.in/s?k=rplidar+a1) |
| 20 | **BNO055 9-DOF IMU breakout (Adafruit or generic, I²C 0x28)** | Small purple PCB ~30 × 25 mm with a Bosch BNO055 chip visible, STEMMA-QT port on one side | `tank_sensors.imu_publisher` (orientation as `sensor_msgs/Imu`) | 1,200 – 2,000 | [amazon.in/s?k=bno055+imu+i2c+breakout](https://www.amazon.in/s?k=bno055+imu+i2c+breakout) |
| 21 | **INA219 DC current/voltage sensor (I²C 0x40)** | Small green breakout ~25 × 20 mm with INA219 chip, two screw terminals for the shunt | `tank_health.health_node` battery telemetry (one board per rail: Pi + motor) | 2 × (250 – 450) = 500 – 900 | [amazon.in/s?k=ina219+current+sensor](https://www.amazon.in/s?k=ina219+current+sensor) |
| 22 | **R307 / ZFM-708 fingerprint sensor (UART, optical)** | Small black plastic cube with a metallic fingerprint window, 4-wire UART pigtail (V+/GND/TX/RX) | `tank_security` home-unlock feature (`/dev/ttyAMA0` @ 57600 baud) | 850 – 1,400 | [amazon.in/s?k=r307+fingerprint+sensor](https://www.amazon.in/s?k=r307+fingerprint+sensor) |
| 23 | **Ultrasonic HC-SR04 × 2** (rear / cliff safety) | Two-black-eyes PCB ~45 × 20 mm with twin cylindrical transducers | Front + rear obstacle abort, /scan fusion safety layer | 2 × (120 – 180) = 240 – 360 | [amazon.in/s?k=hc-sr04+ultrasonic+sensor](https://www.amazon.in/s?k=hc-sr04+ultrasonic+sensor) |
| 24 | **DS18B20 waterproof 1-Wire temperature probe (1 m cable, ±0.5 °C)** *(separate, dedicated)* | Stainless-steel M6 cap probe ~30 × 6 mm on a 1 m waterproof PVC cable, 3-wire pigtail (red VCC / black GND / yellow DATA) | **Standalone** temperature for battery + motors + chassis ambient. 1-Wire on GPIO4 (Pi header pin 7), 4.7 kΩ pull-up to 3.3 V. Buy **≥ 3** (one per hot spot). | 120 – 280 *(each)* → 360 – 840 *(3 probes)* | [amazon.in/s?k=ds18b20+waterproof+probe+1m](https://www.amazon.in/s?k=ds18b20+waterproof+probe+1m) |
| 24a | **4.7 kΩ resistor (1-Wire pull-up, through-hole)** *(1 small resistor)* (qty 10 pack) | Tiny axial resistor yellow-violet-red-gold stripes, ~10 pcs in a tape strip | Pull-up resistor for DS18B20 data line to 3.3 V | 30 – 80 | [amazon.in/s?k=4.7k+resistor+pack](https://www.amazon.in/s?k=4.7k+resistor+pack) |

**Subtotal 4 → ₹ 8,180 – 14,080 (mid ₹ 9,950)** *(RPLidar dominates, DS18B20 cluster adds ~₹150 for 3 probes)*

---

## 5️⃣ Audio In / Out

| # | Item | Photo / Google-Shopping Description | Driver / Use | Price (₹) | Amazon Link |
|---|------|--------------------------------------|--------------|----------:|-------------|
| 25 | **ReSpeaker 4-Mic Array (USB, Seeed)** | Black square PCB ~70 × 70 mm with four small MEMS microphones on each corner, glowing centre LED ring | `tank_speech.wake_word_listener` (openWakeWord → `/wake_detected`) | 2,800 – 4,200 | [amazon.in/s?k=respeaker+4+mic+array](https://www.amazon.in/s?k=respeaker+4+mic+array) |
| 26 | **USB Audio Class DAC (e.g. UGreen or Topping)** | Tiny black USB dongle ~60 × 25 mm with a 3.5 mm jack on the other end | `tank_text.tts_node` (Piper ONNX → sounddevice.play) | 400 – 750 | [amazon.in/s?k=usb+audio+dac+3.5mm](https://www.amazon.in/s?k=usb+audio+dac+3.5mm) |
| 27 | **3 W 8 Ω speaker w/ JST-PH pigtail** | Small round 28 mm black speaker with a JST-PH 2.0 mm white connector | Tank's voice output | 150 – 300 | [amazon.in/s?k=3w+8ohm+speaker+jst](https://www.amazon.in/s?k=3w+8ohm+speaker+jst) |
| 28 | **Mini amplified USB speaker (recess-mount)** | Small black rectangular box speaker, ~85 × 45 mm, USB-A plug on a short lead, magnet on the back | For dashboards / docks | 600 – 1,100 | [amazon.in/s?k=mini+usb+speaker+amplified](https://www.amazon.in/s?k=mini+usb+speaker+amplified) |

**Subtotal 5 → ₹ 3,950 – 6,350 (mid ₹ 4,750)** *(Respeaker dominates)*

---

## 6️⃣ Power Architecture (revised)

> ⚡ **Two-rail power.** The Jetson Orin Nano and the BTS7960 motor drivers **must
> not share ground through the same battery**. The intended wiring is:
>
> ```text
> ┌──────────────────┐    19 V DC      ┌──────────────────────┐
> │ Jetson PSU       │ ──────────────► │ NVIDIA Jetson        │
> │ (barrel jack,    │                 │ Orin Nano (8 GB)     │
> │ included in kit) │                 └──────────────────────┘
> └──────────────────┘
>                                                 │
>                                                 │ USB-A
>                                                 ▼
>                                       ┌──────────────────────┐
>                                       │ Arduino UNO R4 WiFi  │
>                                       │ LiDAR, USB Camera    │
>                                       │ ReSpeaker, LTE modem │
>                                       └──────────────────────┘
>
> ┌──────────────────────┐               ┌──────────────────────┐
> │ 12 V motor battery    │ ───────────► │ 2 × BTS7960 drivers │
> │ (SLA or 3S Li-ion,    │   12 V /     │ → 2 × drive motors   │
> │ already on hand)     │   30 A peak  │ (12 V each, encoder)│
> └──────────────────────┘               └──────────────────────┘
> ```
>
> **Why separate rails:** motor inrush (a stalled tank wheel can pull
> 20 A for 50 ms) sags the motor rail. If the Jetson sat on the same rail,
> that sag would trigger an undervoltage → Jetson brownout → ROS nodes
> restart mid-mission. Independent rails = independent brown-outs.

### 6.1 Items actually to buy

| # | Item | Note | Price (₹) | Amazon Link |
|---|------|------|----------:|-------------|
| 29 | **XT60 connector pair + JST-PH 2-pin pigtails** *(kit)* | Yellow male+female barrel pair + JST housings + crimp pins. Connects the 12 V motor battery to the BTS7960 input rail cleanly. | 150 – 350 | [amazon.in/s?k=xt60+connector+pair](https://www.amazon.in/s?k=xt60+connector+pair) |
| 30 | **Inline inline 30 A blade fuse + holder** | ATO/ATC blade fuse holder + a 30 A replacement fuse. Sits between the 12 V motor battery and the BTS7960 rail; cheap insurance against a stalled motor stalling the wiring harness. | 120 – 280 | [amazon.in/s?k=30a+inline+blade+fuse+holder](https://www.amazon.in/s?k=30a+inline+blade+fuse+holder) |

**Subtotal 6 → ₹ 270 – 630 (mid ₹ 1,900 ... with a generous buffer for spares)**

### 6.2 Already on hand (do NOT buy)

- 🟢 **Jetson Orin Nano PSU (19 V barrel jack)** — included with dev kit.
- 🟢 **2 × BTS7960 43 A drivers** — purchased.
- 🟢 **12 V motor battery** — any existing 12 V SLA, 3S Li-ion, RC car pack, or bench supply ≥ 5 Ah works. Re-use what you have before buying.

### 6.3 If you really must start from zero on the motor rail (worst-case only)

| # | Item | Note | Price (₹) | Amazon Link |
|---|------|------|----------:|-------------|
| 30★ | **12 V 5 Ah SLA battery** *(optional, only if you have no 12 V supply)* | Sealed lead-acid, hobby-grade. Cheap, dumb, effective. | 750 – 1,200 | [amazon.in/s?k=12v+5ah+sla+battery](https://www.amazon.in/s?k=12v+5ah+sla+battery) |
| 31★ | **SLA charger 12 V 1 A** *(optional, pairs with 30★)* | Black wall-wart, 2-pin output, simple float charger. | 350 – 650 | [amazon.in/s?k=12v+1a+sla+charger](https://www.amazon.in/s?k=12v+1a+sla+charger) |

★ = only buy if you do not already own a 12 V motor supply. Skip otherwise.

---

## 7️⃣ Networking / Cellular

| # | Item | Photo / Google-Shopping Description | Driver / Use | Price (₹) | Amazon Link |
|---|------|--------------------------------------|--------------|----------:|-------------|
| 32 | **USB Wi-Fi 6 adapter (e.g. TP-Link Archer T2U)** | Small USB-A dongle ~30 × 15 mm with a tiny antenna | Backup Wi-Fi link if Jetson Wi-Fi fails on Jetson metal-shielded chassis | 550 – 900 | [amazon.in/s?k=usb+wifi+6+adapter](https://www.amazon.in/s?k=usb+wifi+6+adapter) |
| 33 | **Quectel EC25** *or* **SIM7600E LTE modem (USB)** | Small black stick ~85 × 30 mm with two SMA antenna ports, USIM slot | Cellular failover when Wi-Fi drops (`tank_scripts/lte_handoff.py`) | 2,800 – 4,500 | [amazon.in/s?k=quectel+ec25+lte](https://www.amazon.in/s?k=quectel+ec25+lte) |
| 34 | **LTE SMA antenna (4G/LTE puck, 5 dBi)** | Small black rubber puck ~50 × 50 mm with a short coaxial lead + SMA male | Antenna for the LTE modem | 250 – 450 | [amazon.in/s?k=lte+4g+antenna+sma](https://www.amazon.in/s?k=lte+4g+antenna+sma) |
| 35 | **Ethernet USB adapter (10/100)** | Tiny white USB-A dongle, RJ45 jack on the other end | Wired backhaul into the home router (preferred over fragile Wi-Fi) | 350 – 600 | [amazon.in/s?k=usb+ethernet+adapter+10](https://www.amazon.in/s?k=usb+ethernet+adapter+10) |

**Subtotal 7 → ₹ 3,950 – 6,450 (mid ₹ 5,950)** *(LTE modem dominates)*

---

## 8️⃣ Chassis / Wiring / Safety Sundries

| # | Item | Photo / Google-Shopping Description | Price (₹) | Amazon Link |
|---|------|--------------------------------------|----------:|-------------|
| 36 | **Silicone wire kit (24/26/28 AWG, 6 colours, ~10 m each)** | Spools of stranded silicone wire in red/black/yellow/blue/green/white | 350 – 650 | [amazon.in/s?k=silicone+wire+kit+24+26+28+awg](https://www.amazon.in/s?k=silicone+wire+kit+24+26+28+awg) |
| 37 | **JST-PH 2-pin / 3-pin / 4-pin connector kit (Dupont-style housings + crimps)** | Plastic housings + metal crimp pins | 300 – 600 | [amazon.in/s?k=jst+ph+connector+kit](https://www.amazon.in/s?k=jst+ph+connector+kit) |
| 38 | **Heat-shrink tubing assortment (black, 2–10 mm)** | Black plastic tubing, ~200 pcs in a clear poly bag | 200 – 350 | [amazon.in/s?k=heat+shrink+tubing+kit](https://www.amazon.in/s?k=heat+shrink+tubing+kit) |
| 39 | **Cable gland + spiral wrap (10 mm bundle, 1 m)** | Black nylon spiral wrap coiled into a flat ring | 200 – 350 | [amazon.in/s?k=spiral+wrap+10mm+cable](https://www.amazon.in/s?k=spiral+wrap+10mm+cable) |
| 40 | **40-pin GPIO ribbon cable + breakout + T-cobbler** | Rainbow ribbon cable with two 40-pin sockets, small T-cobbler PCB | 250 – 450 | [amazon.in/s?k=raspberry+pi+gpio+ribbon+cable](https://www.amazon.in/s?k=raspberry+pi+gpio+ribbon+cable) |
| 41 | **Small breadboard (400-tie, 830-tie × 2)** | White plastic breadboard 165 × 55 mm with red/blue power rails | 2 × (150 – 250) = 300 – 500 | [amazon.in/s?k=breadboard+830+tie](https://www.amazon.in/s?k=breadboard+830+tie) |
| 42 | **M2 / M2.5 / M3 screw + standoff kit (200+ pcs)** | Tubs of small steel screws + nylon standoffs in a clear plastic box | 350 – 600 | [amazon.in/s?k=screw+kit+m2+m3+standoff](https://www.amazon.in/s?k=screw+kit+m2+m3+standoff) |
| 43 | **40 × 40 mm or 25 × 25 mm 12 V cooling fan** | Small black 4-wire PWM fan ~40 × 40 × 10 mm | 250 – 450 | [amazon.in/s?k=40mm+12v+cooling+fan+pwm](https://www.amazon.in/s?k=40mm+12v+cooling+fan+pwm) |

**Subtotal 8 → ₹ 2,200 – 3,950 (mid ₹ 6,650)** *(consumables — order generously)*

---

## 🧾 Final Total

| Quantity tier | Calculation | Sum |
|----------------|-------------|----:|
| **Lower band (cheap-importer)** | All minimums + cheapest compatible variants | **≈ ₹ 53,550** |
| **MID band (what to plan for now)** | Mid of each row | **≈ ₹ 64,450** |
| **Upper band (buying top brand)** | All maximums + branded variants (Sparkfun, Pololu, Seeed) | **≈ ₹ 80,250** |

Plus a once-off **₹ 4,500** for a basic solder/measurement toolkit if you
don't already own one — that brings a *first-time builder* total to **₹ 68,950 mid**.

> Compared to the previous draft (₹ 72,350 mid / ₹ 89,780 upper), the
> simplification saves **≈ ₹ 7,900 mid / ₹ 9,500 upper** — mostly from
> dropping the 4-cell Li-ion pack + charger + dual buck cascade and
> reusing the BTS7960 drivers already in hand.

---

## 📦 CSV — for spreadsheet import

```csv
"#",section,item,low_inr,high_inr,amazon_search_slug
1,Compute,Jetson Orin Nano Dev Kit 8GB,25000,35000,jetson+orin+nano+dev+kit+8gb
2,Compute,Arduino UNO R4 WiFi,1800,2500,arduino+uno+r4+wifi
3,Compute,M.2 NVMe 256GB,3500,5500,m.2+nvme+256gb
4,Compute,ESP32-S3 DevKitC-1 N16R8,700,1100,esp32-s3+devkitc-1+n16r8
5,Compute,MicroSD 64GB A2,600,900,micro+sd+64gb+a2
6,Vision,Waveshare 1.28" round GC9A101 (×2),2800,4000,waveshare+1.28+round+lcd+gc9a01
7,Vision,1.3" SH1106 OLED I²C,350,600,1.3+oled+sh1106+i2c
8,Vision,USB Camera IMX219/C920,1200,2500,usb+webcam+1080p
9,Vision,M2.5/M3 standoff kit,250,450,m3+nylon+standoff+kit
12,Motion,12V DC geared motor w/ encoder (×2),1300,1900,jgb37-520+encoder+motor
13,Motion,"2 × BTS7960 43 A driver (already on hand)",0,0,(no buy)
14,Motion,Tracked chassis w/ 12V motors,1800,3200,tracked+robot+chassis+12v
15,Motion,Tower Pro SG90 servo (×2),360,560,tower+pro+sg90+servo
16,Motion,PCA9685 16-channel servo HAT,450,750,pca9685+servo+driver+i2c
17,Motion,Pan-tilt bracket SG90-compatible,250,450,pan+tilt+bracket+sg90
18,Motion,Mushroom-head E-STOP switch,150,350,mushroom+emergency+stop+button
19,Sensors,RPLidar A1 / LD19,5000,8500,rplidar+a1
20,Sensors,BNO055 9-DOF IMU,1200,2000,bno055+imu+i2c+breakout
21,Sensors,INA219 current/voltage (×2: Pi + motor rail),500,900,ina219+current+sensor
22,Sensors,R307 fingerprint sensor,850,1400,r307+fingerprint+sensor
23,Sensors,HC-SR04 ultrasonic (×2),240,360,hc-sr04+ultrasonic+sensor
24,Sensors,DS18B20 waterproof 1-Wire probe (×3),360,840,ds18b20+waterproof+probe+1m
24a,Sundry,4.7kΩ resistor pack 10pcs,30,80,4.7k+resistor+pack
25,Audio,ReSpeaker 4-Mic Array,2800,4200,respeaker+4+mic+array
26,Audio,USB Audio DAC,400,750,usb+audio+dac+3.5mm
27,Audio,3W 8Ω speaker w/ JST,150,300,3w+8ohm+speaker+jst
28,Audio,Mini amplified USB speaker,600,1100,mini+usb+speaker+amplified
29,Power,XT60 connector pair + JST-PH kit,150,350,xt60+connector+pair
30,Power,Inline 30 A blade fuse + holder,120,280,30a+inline+blade+fuse+holder
31,Network,USB Wi-Fi 6 adapter,550,900,usb+wifi+6+adapter
32,Network,Quectel EC25 LTE modem,2800,4500,quectel+ec25+lte
33,Network,LTE SMA antenna 4G puck,250,450,lte+4g+antenna+sma
34,Network,USB Ethernet adapter,350,600,usb+ethernet+adapter+10
35,Sundry,Silicone wire kit (24/26/28 AWG),350,650,silicone+wire+kit+24+26+28+awg
36,Sundry,JST-PH connector kit,300,600,jst+ph+connector+kit
37,Sundry,Heat-shrink tubing kit,200,350,heat+shrink+tubing+kit
38,Sundry,Spiral cable wrap 10mm,200,350,spiral+wrap+10mm+cable
39,Sundry,40-pin GPIO ribbon + cobbler,250,450,raspberry+pi+gpio+ribbon+cable
40,Sundry,Breadboard (×2),300,500,breadboard+830+tie
41,Sundry,M2/M2.5/M3 screw + standoff kit,350,600,screw+kit+m2+m3+standoff
42,Sundry,40mm 12V cooling fan,250,450,40mm+12v+cooling+fan+pwm
```

---

## 💡 Money-saving notes

* **Skip LTE modem (#32)** for indoor-Wi-Fi-only builds — saves ₹ 2,800–4,500.
* **Use RPLidar A1** instead of A2/S2 if cost matters; the A1 has 2 000 Hz
  sample rate vs A2's 4 000 Hz — fine for 2D SLAM at home scale.
* **Substitute LDROBOT LD19** for RPLidar A1: similar price, similar
  spec, different driver (`ldrobot_lidar_ros`).
* **Generic PCA9685 vs Adafruit** — Adafruit is ~2× the price and brings
  zero functional advantage for hobby use.
* **Skip fingerprint sensor (#22)** if you don't need home-unlock; saves ₹ 1k.
* **Skip OLED (#8)** — the eyes on the round GC9A101 already convey state
  via `tank_display`. Saves ₹ 350–600.
* **Skip SLA + SLA charger (★ 30 / ★ 31)** if you already own any 12 V
  motor supply — saves up to ₹ 1,850.
* **"Buy Indian" alternatives**: Robu.in, Evelta, Sunrom and rhydolabz
  carry the same parts with no customs and faster shipping.
* **Sales calendar** — Republic Day (Jan), Independence Day (Aug) and
  Prime Day (Oct) typically drop prices 10–20 % on robotics SKUs.

---

## ⚠️ Caveats

1. **Power architecture (revised)**: this BOM assumes the user already
   owns a USB-C PD power bank ≥ 27 W and a 12 V motor battery (SLA,
   3S Li-ion, or bench supply). If you have neither, add **★ 30 + ★ 31**
   (SLA + charger, ~₹ 1,150 mid).
2. **Rail isolation**: connect Pi USB-C PD ground and motor battery
   ground **at one star point only** (typically the BTS7960 chassis
   ground). Do not connect two ground returns in series — that creates
   ground-loops that the BTS7960's built-in filtering cannot absorb.
3. **INA219 count**: the revised BOM needs **2** INA219 boards
   (one per rail — Pi + motor) instead of one. The cost delta is
   small but the dashboard's `tank_health` ate it up as 2× row.
4. **Camera variants**: I recommend the **IMX708 (Camera Module 3)** as the
   default because of the huge community. Use **IMX296 global-shutter** if
   you need crisp frames of fast-moving objects (e.g. ball-tracking).
   Amazon-IN rotates weekly.
5. **ESP32 variants**: the firmware pinout is for **ESP32-S3 DevKitC-1
   N16R8**. The plain DevKitC (no `-S3`) or any board without PSRAM
   **won't work** for the GC9A101 driver.
6. **BTS7960 wiring**: the 2 × BTS7960 inputs are 12 V; the modules will
   happily run on 5 V logic for PWM/DIR but the motor rail is fixed at
   whatever the battery delivers. Don't try to drive BTS7960 from a
   Jetson GPIO line WITHOUT level shifting (3.3 V ↔ 5 V). Use a logic
   level shifter or a small transistor buffer.
7. **Prices fluctuate**: every row is a band; treat the mid-band as the
   realistic planning number, the high-band as the worst-case if every
   part is bought the day you need it.
8. **Total assumes a single Jetson + Arduino chassis.** Adding a second tank nearly
   doubles the cost (only the tools can be shared).
9. **Tools not listed** — these are implicit but real: soldering iron
   (₹ 1,200), heat-shrink gun (₹ 400), multimeter (₹ 700), wire snips
   (₹ 250), Phillips/flat drivers (₹ 200). Budget ~₹ 3,000 for these
   if you don't have them.

---

*Compiled from the canonical `tank_ws/src/tank_meta/content/hardware.json`
plus the implicit physical-build inventory in `WIRING.md` and
`ARCHITECTURE.md`. Refresh the price bands whenever sales land or
Amazon-IN replaces a SKU.*

---

## 🧩 Software-Hardware Mapping

> Full dependency reference at [`docs/HARDWARE_DEPENDENCIES.md`](docs/HARDWARE_DEPENDENCIES.md)

| Hardware | TankOS Module | Driver / Interface | Status |
|----------|---------------|-------------------|--------|
| NVIDIA Jetson Orin Nano | TankOS Core + AI + Shell | Native (Layer 1–4) | ✅ |
| Arduino UNO R4 WiFi | RobotManager — `motor_controller` | USB Serial @ 115200 / GPIO | ✅ |
| 7" HDMI/DP Touchscreen | TankShell (Qt GUI) | PySide6 | 🟡 Planned |
| ESP32-S3 Round Eyes | EmotionManager, `eye_lcd_bridge` | UART @ 115200 | ✅ |
| Waveshare 1.28" LCD × 2 | Eye expressions | SPI → ESP32 → UART | ✅ |
| SH1106 OLED (I²C) | `tank_display` (status face) | luma.oled, I²C 0x3C | ✅ |
| DFRobot AI Camera | VisionManager — YOLO, detection | USB, ultralytics | 🟡 Planned |
| USB Camera (IMX219 / C920) | VisionManager — `camera_publisher` | USB UVC, OpenCV | ✅ |
| ProBots Tank Chassis | RobotManager — `motor_controller` | Arduino GPIO + BTS7960 | ✅ |
| BTS7960 × 2 | RobotManager — drive motors | Arduino PWM/DIR | ✅ |
| PCA9685 Servo Controller | RobotManager — `pan_tilt_controller` | I²C 0x40 (Arduino), adafruit-servokit | 🟡 Planned |
| SG90 Servo × 2 | Pan/tilt camera head | PWM 50 Hz via PCA9685 | 🟡 Planned |
| MPU6050 IMU | `tank_sensors.imu_publisher` | I²C 0x68 (Arduino) | 🟡 Planned |
| BNO055 9-DOF IMU | `tank_sensors.imu_publisher` (upgrade) | I²C 0x28 (Arduino) | 🟡 Future |
| HC-SR04 × 2 | Obstacle detection | GPIO trigger/echo | 🟡 Planned |
| TF-Luna LiDAR | NavigationManager — obstacle avoidance | UART | 🟡 Considering |
| RPLidar A1 / LD19 | NavigationManager — SLAM | USB, rplidar_ros | 🟡 Planned |
| AMG8833 Thermal Cam | SecurityManager / Vision AI | I²C 0x69, Adafruit | 🔴 Exp. |
| AS608 Fingerprint | SecurityManager — auth | UART, adafruit-fingerprint | 🟡 Planned |
| MAX98357A Amplifier | `tank_text.tts_node` — voice out | I²S GPIO18-21 | 🟡 Planned |
| ReSpeaker 4-Mic | `tank_speech.wake_word_listener` | USB Audio, openWakeWord | 🟡 Planned |
| SIM7600G / EC25 LTE | NetworkManager — cellular | USB ttyUSBx, PPP | 🟡 Planned |
| NVMe SSD 256 GB | StorageManager + AI models | PCIe (M.2 HAT+) | ✅ |
| USB Hub 4-port | HardwareManager — USB detection | Linux usbhid | ✅ |
| 20K mAh Power Bank | PowerManager + `tank_health` | USB-C PD + INA219 | ✅ |
| 4S Li-ion Pack | Motor power — `tank_health.battery` | XT60, INA219 | 🟡 Planned |
| USB TTL CH341A | Debug / firmware flashing | Linux ch341.ko | ✅ |
| GPIO Expansion Board | Prototyping | 40-pin breakout | ✅ |

**Legend:** ✅ Working | 🟡 Planned (owned) | 🔴 Experimental

### Key Software Dependencies

| Library | For |
|---------|-----|
| PySide6 / Qt6 | Tank Shell GUI + DSI screen |
| OpenCV + ultralytics (YOLO) | Camera vision (Jetson + DFRobot) |
| picamera2 + libcamera | USB Camera |
| luma.oled | SH1106 OLED face |
| adafruit-circuitpython-servokit | PCA9685 servo control |
| openWakeWord | Wake word detection via ReSpeaker |
| sounddevice | Audio I/O (mic + speaker) |
| rplidar_ros | RPLidar SLAM |
