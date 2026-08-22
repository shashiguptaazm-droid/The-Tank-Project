# Wiring — Phase 1

Single source of truth for the electrical hookup. Every pin in this table
matches a ROS2 parameter in `tank_bringup/config/*.yaml`, so you can override
on a per-robot basis without touching code.

## GPIO — Arduino UNO Q (real-time controller)

> **All real-time I/O is on the Arduino.** Jetson sends high-level commands over
> USB serial (115200 baud); Arduino handles PWM generation, encoder interrupts,
> and sensor polling deterministically.

| Function          | Pin   | Direction | Notes                                     |
|-------------------|-------|-----------|-------------------------------------------|
| `dir_left_pin`    | D7    | OUT       | H-bridge DIR channel A                    |
| `pwm_left_pin`    | D6    | OUT       | H-bridge PWM channel A (1 kHz, HW PWM)   |
| `dir_right_pin`   | D4    | OUT       | H-bridge DIR channel B                    |
| `pwm_right_pin`   | D5    | OUT       | H-bridge PWM channel B (1 kHz, HW PWM)   |
| `enc_left_a`      | D2    | IN        | Left encoder channel A (INT0)             |
| `enc_left_b`      | D3    | IN        | Left encoder channel B (INT1)             |
| `enc_right_a`     | D18   | IN        | Right encoder channel A                   |
| `enc_right_b`     | D19   | IN        | Right encoder channel B                   |
| `e_stop_led_pin`  | D8    | OUT       | indicates E-STOP latch (high = latched)   |
| `e_stop_in_pin`   | D9    | IN        | Hardware E-STOP button (with pull-up)     |

## I²C bus — Arduino UNO Q (Wire)

| Address | Device                                | Driver                        |
|---------|---------------------------------------|-------------------------------|
| 0x28    | BNO055 IMU                            | `adafruit_bno055`             |
| 0x40    | PCA9685 16-channel 12-bit PWM         | `adafruit_pca9685` + `adafruit_motor.servo` |
| 0x70    | 1.3" OLED (SH1106) — phase 2          | `adafruit_ssd1306` / `luma.oled` |

Arduino UNO Q has I²C on A4 (SDA) / A5 (SCL) plus a Qwiic connector.
All I²C devices connect to the Arduino, not the Jetson.## SPI bus — reserved

| Arduino Pin | Function |
|-------------|----------|
| D11 (MOSI)  | reserved for future SPI peripheral |
| D12 (MISO)  | reserved |
| D13 (SCLK)  | reserved |
| D10 (SS)    | reserved |

## Serial Links

| Link | Baud | Use |
|------|------|-----|
| Jetson ↔ Arduino (USB-C) | 115200 | **Command bridge**: Jetson sends motor commands, receives encoder + sensor telemetry via compact binary protocol |
| Jetson USB ↔ LiDAR | — | RPLidar A1/A2/A3 via USB-UART adapter (`/dev/ttyUSB0`) |
| Jetson USB ↔ ESP32-S3 | — | Eye expression commands (JSON over UART) |

RPLidars default to 115 200 baud and draw about 600 mA during spin-up — make
sure your USB hub is powered. Add a udev rule so the adapter gets a stable
name:

```
# /etc/udev/rules.d/99-rplidar.rules
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", SYMLINK+="rplidar"
```

## I²C contention notes

Both the IMU and the PCA9685 live on the Arduino's I²C bus. Since the Arduino
runs bare-metal (no Linux scheduler jitter), I²C contention is not an issue —
the firmware reads IMU and writes PCA9685 in the same `loop()` iteration.

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
| 5 V                | Arduino UNO Q onboard reg (7-12 V in) or USB-C PD | Arduino, PCA9685, IMU, OLED, sensors |
| 19 V               | Jetson Orin Nano barrel jack PSU    | Jetson, USB peripherals              |

Keep motor power and logic power physically separated on the chassis — run
them on opposite sides of the cable spine.
