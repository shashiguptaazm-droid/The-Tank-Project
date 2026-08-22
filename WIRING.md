# Wiring — Phase 1

Single source of truth for the electrical hookup. Every pin in this table
matches a ROS2 parameter in `tank_bringup/config/*.yaml`, so you can override
on a per-robot basis without touching code.

## GPIO (BCM numbering — Pi 5 header)

| Function          | Pin  | Direction | Notes                                     |
|-------------------|------|-----------|-------------------------------------------|
| `dir_left_pin`    | 17   | OUT       | H-bridge DIR channel A                    |
| `pwm_left_pin`    | 18   | OUT       | H-bridge PWM channel A (1 kHz)            |
| `dir_right_pin`   | 27   | OUT       | H-bridge DIR channel B                    |
| `pwm_right_pin`   | 22   | OUT       | H-bridge PWM channel B (1 kHz)            |
| `_unused`         | 23   | IN        | reserved for rocker-arm suspension sense |
| `_unused`         | 24   | IN        | reserved for auto-dock IR beacon          |
| `e_stop_led_pin`  | 25   | OUT       | indicates E-STOP latch (high = latched)   |

These are conventional safe pins; change them in `tank_motion.yaml` if you
already have something else plugged in.

## I²C (bus 1, the default)

| Address | Device                                | Driver                        |
|---------|---------------------------------------|-------------------------------|
| 0x28    | BNO055 IMU                            | `adafruit_bno055`             |
| 0x29    | (BNO055 alternate ADDR pin HIGH)      | `adafruit_bno055`             |
| 0x40    | PCA9685 16-channel 12-bit PWM         | `adafruit_pca9685` + `adafruit_motor.servo` |
| 0x70    | 1.3" OLED (SH1106) — phase 2          | `adafruit_ssd1306` / `luma.oled` |
| 0x5A    | Fingerprint sensor (R307 over UART — phase 4, not I²C) |

Bus 1 is on header pins 3 (SDA) and 5 (SCL). Add `dtparam=i2c_arm=on` and
`dtparam=i2c_arm_baudrate=400000` in `/boot/firmware/config.txt` (handled by
`scripts/setup_pi5.sh`).

## SPI (bus 0, reserved)

| Pin (header) | Function |
|--------------|----------|
| 19 (MOSI)    | reserved for future OLED SPI variant |
| 21 (MISO)    | reserved |
| 23 (SCLK)    | reserved |
| 24 (CE0)     | reserved |
| 26 (CE1)     | reserved |

The 1.3" OLED currently uses I²C; SPI is documented in case we swap the OLED
to a larger SPI display in phase 2 without renumbering anything.

## UART

| Header pins | Use                                         |
|-------------|---------------------------------------------|
| 8 / 10      | `/dev/ttyAMA0` — **disabled**, see below    |
| `/dev/ttyUSB0` | LiDAR (RPLidar A1/A2/A3 via USB-UART adapter) |

RPLidars default to 115 200 baud and draw about 600 mA during spin-up — make
sure your USB hub is powered. Add a udev rule so the adapter gets a stable
name (created by `scripts/setup_pi5.sh`):

```
# /etc/udev/rules.d/99-rplidar.rules
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", SYMLINK+="rplidar"
```

## I²C contention order

Both the IMU and the PCA9685 live on bus 1. The IMU is read in
`imu_publisher`'s timer callback; the PCA9685 is written in `pan_tilt_controller`'s
subscription callback. If you see intermittent `OSError: [Errno 121] Remote I/O error`,
add `i2c-bcm2708` combined transactions (`/etc/modprobe.d/i2c.conf`):

```
options i2c-bcm2708 combined=1
```

and reduce the IMU rate to 50 Hz (configurable via `tank_sensors.yaml`).

## E-STOP wiring

The hardware kill switch should be a normally-closed momentary pushbutton in
series with the BMS VBAT trace feeding the motor driver. The BMS itself has
a dedicated E-STOP input (PWMA-Safety harness variant) — wire that in
parallel so an overcurrent event also opens it.

## Power rails

| Rail               | Source                              | Used by                              |
|--------------------|-------------------------------------|--------------------------------------|
| VBAT (≈ 22.2 V)    | 6S Li-ion via BMS                   | Motor driver H-bridge                |
| 12 V               | DC-DC buck from VBAT                | Fans, LiDAR, camera illuminator     |
| 5 V                | USB-C PD (Pi 5 official PSU)        | Pi 5, PCA9685, IMU, OLED, sensors    |
| 3 V3               | Pi 5 internal                       | Pull-ups only — never load it        |

Keep motor power and logic power physically separated on the chassis — run
them on opposite sides of the cable spine.
