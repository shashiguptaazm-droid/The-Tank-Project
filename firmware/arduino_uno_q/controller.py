#!/usr/bin/env python3
"""
Arduino UNO Q — Real-Time Body Controller
==========================================
Communicates with Jetson Orin Nano via USB Serial (115200 baud).

Jetson decides WHAT. Arduino guarantees HOW.

Protocol: JSON commands over serial
  Jetson → Arduino: {"cmd": "MOVE", "left": 0.5, "right": 0.5}
  Arduino → Jetson: {"enc_L": 1234, "enc_R": 5678, "imu": {"yaw": 45.2}, "estop": false}

Pin Map (from WIRING.md):
  D2  = Left encoder A (INT0)
  D3  = Left encoder B (INT1)
  D4  = Right motor DIR
  D5  = Right motor PWM
  D6  = Left motor PWM
  D7  = Left motor DIR
  D8  = E-STOP LED
  D9  = E-STOP button (pull-up)
  D18 = Right encoder A
  D19 = Right encoder B
  A4  = I2C SDA
  A5  = I2C SCL

I2C Bus (400kHz):
  0x28 = BNO055 IMU
  0x40 = PCA9685 Servo Driver
  0x70 = SH1106 OLED Display
"""

from __future__ import annotations

import json
import logging
import os
import signal
import struct
import sys
import time
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
logger = logging.getLogger("arduino_controller")

# ─── Configuration ────────────────────────────────────────────────────

BAUD_RATE = 115200
SERIAL_PORT = os.environ.get("TANK_SERIAL_PORT", "/dev/ttyUSB0")
LOOP_HZ = 200  # 200 Hz control loop (5ms period)
ECLIPSE_BUTTON_PIN = 9  # GPIO pin for E-STOP

# ─── Motor Configuration ──────────────────────────────────────────────

@dataclass
class MotorConfig:
    left_pwm_pin: int = 6
    left_dir_pin: int = 7
    right_pwm_pin: int = 5
    right_dir_pin: int = 4
    max_speed: float = 1.0
    pwm_range: int = 255

# ─── Encoder State ─────────────────────────────────────────────────────

@dataclass
class EncoderState:
    left_count: int = 0
    right_count: int = 0
    left_speed: float = 0.0
    right_speed: float = 0.0
    last_left_count: int = 0
    last_right_count: int = 0
    last_time: float = 0.0

# ─── IMU State ─────────────────────────────────────────────────────────

@dataclass
class IMUState:
    yaw: float = 0.0
    pitch: float = 0.0
    roll: float = 0.0
    accel_x: float = 0.0
    accel_y: float = 0.0
    accel_z: float = 0.0
    available: bool = False

# ─── Motor Controller ──────────────────────────────────────────────────

class MotorController:
    """Handles motor PWM and direction control."""

    def __init__(self, config: MotorConfig):
        self.config = config
        self.left_speed = 0.0
        self.right_speed = 0.0
        self._setup_gpio()

    def _setup_gpio(self):
        """Initialize GPIO pins for motor control."""
        try:
            import RPi.GPIO as GPIO
            self.gpio = GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(self.config.left_pwm_pin, GPIO.OUT)
            GPIO.setup(self.config.left_dir_pin, GPIO.OUT)
            GPIO.setup(self.config.right_pwm_pin, GPIO.OUT)
            GPIO.setup(self.config.right_dir_pin, GPIO.OUT)
            # E-STOP button
            GPIO.setup(ECLIPSE_BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            self.left_pwm = GPIO.PWM(self.config.left_pwm_pin, 1000)
            self.right_pwm = GPIO.PWM(self.config.right_pwm_pin, 1000)
            self.left_pwm.start(0)
            self.right_pwm.start(0)
            self._has_gpio = True
            logger.info("GPIO initialized for motor control")
        except ImportError:
            self._has_gpio = False
            logger.warning("RPi.GPIO not available — motor control simulated")

    def set_motors(self, left: float, right: float):
        """Set motor speeds (-1.0 to 1.0)."""
        self.left_speed = max(-1.0, min(1.0, left))
        self.right_speed = max(-1.0, min(1.0, right))

        if not self._has_gpio:
            return

        # Left motor
        self.gpio.output(self.config.left_dir_pin, self.left_speed >= 0)
        self.left_pwm.ChangeDutyCycle(abs(self.left_speed) * 100)

        # Right motor
        self.gpio.output(self.config.right_dir_pin, self.right_speed >= 0)
        self.right_pwm.ChangeDutyCycle(abs(self.right_speed) * 100)

    def stop(self):
        """Emergency stop — all motors off."""
        self.set_motors(0.0, 0.0)
        if self._has_gpio:
            self.left_pwm.ChangeDutyCycle(0)
            self.right_pwm.ChangeDutyCycle(0)

# ─── Encoder Reader ────────────────────────────────────────────────────

class EncoderReader:
    """Reads quadrature encoder signals via hardware interrupts."""

    def __init__(self):
        self.state = EncoderState()
        self.state.last_time = time.time()

    def _setup_interrupts(self):
        """Setup GPIO interrupts for encoder reading."""
        try:
            import RPi.GPIO as GPIO
            self.gpio = GPIO
            GPIO.setmode(GPIO.BCM)

            # Left encoder (D2 = GPIO4, D3 = GPIO17)
            GPIO.setup(4, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(4, GPIO.BOTH, callback=self._left_a_callback)
            GPIO.add_event_detect(17, GPIO.BOTH, callback=self._left_b_callback)

            # Right encoder (D18 = GPIO12, D19 = GPIO13)
            GPIO.setup(12, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(13, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(12, GPIO.BOTH, callback=self._right_a_callback)
            GPIO.add_event_detect(13, GPIO.BOTH, callback=self._right_b_callback)

            self._has_gpio = True
            logger.info("Encoder interrupts initialized")
        except ImportError:
            self._has_gpio = False
            logger.warning("GPIO not available — encoders simulated")

    def _left_a_callback(self, channel):
        a = self.gpio.input(4)
        b = self.gpio.input(17)
        self.state.left_count += 1 if (a != b) else -1

    def _left_b_callback(self, channel):
        a = self.gpio.input(4)
        b = self.gpio.input(17)
        self.state.left_count += 1 if (a == b) else -1

    def _right_a_callback(self, channel):
        a = self.gpio.input(12)
        b = self.gpio.input(13)
        self.state.right_count += 1 if (a != b) else -1

    def _right_b_callback(self, channel):
        a = self.gpio.input(12)
        b = self.gpio.input(13)
        self.state.right_count += 1 if (a == b) else -1

    def update(self):
        """Calculate encoder speed (ticks per second)."""
        now = time.time()
        dt = now - self.state.last_time
        if dt > 0:
            self.state.left_speed = (self.state.left_count - self.state.last_left_count) / dt
            self.state.right_speed = (self.state.right_count - self.state.last_right_count) / dt
            self.state.last_left_count = self.state.left_count
            self.state.last_right_count = self.state.right_count
            self.state.last_time = now

# ─── I2C Sensor Manager ───────────────────────────────────────────────

class I2CSensorManager:
    """Reads sensors over I2C bus."""

    def __init__(self):
        self.imu = IMUState()
        self.voltage = 0.0
        self.current = 0.0
        self._setup_i2c()

    def _setup_i2c(self):
        """Initialize I2C bus."""
        try:
            import smbus
            self.bus = smbus.SMBus(1)  # /dev/i2c-1
            # Test BNO055 at 0x28
            self.bus.read_byte_data(0x28, 0x00)
            self.imu.available = True
            logger.info("I2C: BNO055 IMU detected at 0x28")
        except Exception as e:
            logger.warning(f"I2C not available: {e}")

    def read_imu(self) -> IMUState:
        """Read orientation from BNO055."""
        if not self.imu.available:
            return self.imu

        try:
            # BNO055 Euler angles register (0x1A, 6 bytes)
            data = self.bus.read_i2c_block_data(0x28, 0x1A, 6)
            self.imu.yaw = struct.unpack('<h', bytes(data[0:2]))[0] / 16.0
            self.imu.pitch = struct.unpack('<h', bytes(data[2:4]))[0] / 16.0
            self.imu.roll = struct.unpack('<h', bytes(data[4:6]))[0] / 16.0
        except Exception as e:
            self.imu.available = False
            logger.warning(f"IMU read failed: {e}")

        return self.imu

    def read_battery(self) -> Dict:
        """Read battery voltage/current from INA219."""
        try:
            # INA219 at 0x40 - bus voltage register
            data = self.bus.read_word_data(0x40, 0x02)
            self.voltage = (data >> 3) * 4 / 1000.0
        except Exception:
            pass
        return {"voltage": self.voltage, "current": self.current}

# ─── Serial Protocol ───────────────────────────────────────────────────

class SerialProtocol:
    """JSON-based serial protocol between Jetson and Arduino."""

    def __init__(self, port: str, baud: int):
        self.port = port
        self.baud = baud
        self.ser = None
        self._connected = False

    def connect(self) -> bool:
        """Open serial connection."""
        try:
            import serial
            self.ser = serial.Serial(
                self.port,
                self.baud,
                timeout=1,
                write_timeout=1,
            )
            self._connected = True
            logger.info(f"Serial connected: {self.port} @ {self.baud}")
            return True
        except ImportError:
            logger.warning("pyserial not available — serial simulated")
            return False
        except Exception as e:
            logger.error(f"Serial connection failed: {e}")
            return False

    def send_telemetry(self, data: Dict):
        """Send telemetry data to Jetson."""
        if not self._connected:
            return
        try:
            msg = json.dumps(data) + "\n"
            self.ser.write(msg.encode())
        except Exception as e:
            logger.warning(f"Serial send failed: {e}")

    def read_command(self) -> Optional[Dict]:
        """Read command from Jetson."""
        if not self._connected:
            return None
        try:
            if self.ser.in_waiting > 0:
                line = self.ser.readline().decode().strip()
                if line:
                    return json.loads(line)
        except json.JSONDecodeError:
            pass
        except Exception as e:
            logger.warning(f"Serial read failed: {e}")
        return None

# ─── E-STOP Handler ────────────────────────────────────────────────────

class EStopHandler:
    """Hardware emergency stop handler."""

    def __init__(self):
        self.triggered = False
        self._has_gpio = False
        try:
            import RPi.GPIO as GPIO
            self.gpio = GPIO
            self._has_gpio = True
        except ImportError:
            pass

    def check(self) -> bool:
        """Check if E-STOP is triggered."""
        if self._has_gpio:
            self.triggered = (self.gpio.input(ECLIPSE_BUTTON_PIN) == GPIO.LOW)
        return self.triggered

    def reset(self):
        """Reset E-STOP (after physical button released)."""
        if self._has_gpio:
            if self.gpio.input(ECLIPSE_BUTTON_PIN) == GPIO.HIGH:
                self.triggered = False

# ─── Main Controller Loop ──────────────────────────────────────────────

class ArduinoController:
    """Main controller loop running at LOOP_HZ."""

    def __init__(self):
        self.motors = MotorController(MotorConfig())
        self.encoders = EncoderReader()
        self.sensors = I2CSensorManager()
        self.serial = SerialProtocol(SERIAL_PORT, BAUD_RATE)
        self.estop = EStopHandler()
        self._running = False

    def start(self):
        """Start the controller."""
        logger.info("Arduino UNO Q Controller starting...")
        self._running = True

        # Connect serial
        self.serial.connect()

        # Setup hardware
        self.encoders._setup_interrupts()

        # Main loop
        logger.info(f"Control loop running at {LOOP_HZ} Hz")
        self._loop()

    def _loop(self):
        """Main control loop."""
        while self._running:
            start = time.time()

            # 1. Check E-STOP
            if self.estop.check():
                self.motors.stop()
                self.estop.triggered = True
            elif self.estop.triggered:
                self.estop.reset()

            # 2. Read encoders
            self.encoders.update()

            # 3. Read sensors
            imu = self.sensors.read_imu()
            battery = self.sensors.read_battery()

            # 4. Read command from Jetson
            cmd = self.serial.read_command()
            if cmd:
                self._execute_command(cmd)

            # 5. Send telemetry
            telemetry = {
                "enc_L": self.encoders.state.left_count,
                "enc_R": self.encoders.state.right_count,
                "spd_L": round(self.encoders.state.left_speed, 2),
                "spd_R": round(self.encoders.state.right_speed, 2),
                "imu": {
                    "yaw": round(imu.yaw, 1),
                    "pitch": round(imu.pitch, 1),
                    "roll": round(imu.roll, 1),
                    "available": imu.available,
                },
                "battery": battery,
                "estop": self.estop.triggered,
                "timestamp": time.time(),
            }
            self.serial.send_telemetry(telemetry)

            # 6. Maintain loop rate
            elapsed = time.time() - start
            sleep_time = (1.0 / LOOP_HZ) - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _execute_command(self, cmd: Dict):
        """Execute a command received from Jetson."""
        cmd_type = cmd.get("cmd", "")

        if cmd_type == "MOVE":
            left = cmd.get("left", 0.0)
            right = cmd.get("right", 0.0)
            self.motors.set_motors(left, right)
            logger.debug(f"MOVE L={left:.2f} R={right:.2f}")

        elif cmd_type == "STOP":
            self.motors.stop()
            logger.info("STOP command received")

        elif cmd_type == "SERVO":
            # TODO: Send to PCA9685 via I2C
            angle = cmd.get("angle", 90)
            channel = cmd.get("channel", 0)
            logger.debug(f"SERVO ch={channel} angle={angle}")

        elif cmd_type == "PING":
            # Heartbeat response
            pass

        elif cmd_type == "STATUS":
            # Force immediate telemetry
            pass

        elif cmd_type == "CONFIG":
            # Update PID or other parameters
            logger.info(f"CONFIG: {cmd}")

    def stop(self):
        """Shutdown controller."""
        self._running = False
        self.motors.stop()
        logger.info("Controller stopped")

# ─── Entry Point ───────────────────────────────────────────────────────

def main():
    controller = ArduinoController()

    def signal_handler(sig, frame):
        controller.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        controller.start()
    except KeyboardInterrupt:
        controller.stop()


if __name__ == "__main__":
    main()
