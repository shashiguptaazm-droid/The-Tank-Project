# Arduino UNO Q — Serial Protocol

## Overview
Jetson ↔ Arduino communicate via USB Serial at 115200 baud using JSON messages.

## Command Format (Jetson → Arduino)

### MOVE
{"cmd": "MOVE", "left": 0.5, "right": 0.5}
- left/right: -1.0 (full reverse) to 1.0 (full forward)

### STOP
{"cmd": "STOP"}
- Emergency stop all motors

### SERVO
{"cmd": "SERVO", "channel": 0, "angle": 90}
- channel: 0-15 (PCA9685)
- angle: 0-180 degrees

### PING
{"cmd": "PING"}
- Heartbeat

### CONFIG
{"cmd": "CONFIG", "key": "value"}
- Update parameters

## Telemetry Format (Arduino → Jetson)

{"enc_L": 1234, "enc_R": 5678, "spd_L": 150.0, "spd_R": 148.5,
 "imu": {"yaw": 45.2, "pitch": 1.3, "roll": 0.2, "available": true},
 "battery": {"voltage": 11.8, "current": 2.1},
 "estop": false, "timestamp": 1724389200.0}

## Pin Map

| Pin | Function | Direction |
|-----|----------|-----------|
| D2  | Left encoder A | IN |
| D3  | Left encoder B | IN |
| D4  | Right motor DIR | OUT |
| D5  | Right motor PWM | OUT |
| D6  | Left motor PWM | OUT |
| D7  | Left motor DIR | OUT |
| D8  | E-STOP LED | OUT |
| D9  | E-STOP button | IN |
| D18 | Right encoder A | IN |
| D19 | Right encoder B | IN |
| A4  | I2C SDA | IN/OUT |
| A5  | I2C SCL | IN/OUT |

## I2C Bus (400kHz)

| Address | Device |
|---------|--------|
| 0x28 | BNO055 IMU |
| 0x40 | PCA9685 Servo Driver |
| 0x70 | SH1106 OLED Display |
