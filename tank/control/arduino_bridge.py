#!/usr/bin/env python3
"""
Jetson ↔ Arduino UNO Q Serial Bridge
======================================
Runs on Jetson Orin Nano. Communicates with Arduino UNO Q via USB Serial.

Architecture:
  Jetson (brain) ←USB Serial 115200→ Arduino (reflexes)

The Jetson sends movement commands and receives sensor feedback.
"""

from __future__ import annotations

import json
import logging
import os
import time
import threading
from dataclasses import dataclass
from typing import Dict, Optional, Callable

logger = logging.getLogger("arduino_bridge")

# ─── Serial Protocol ───────────────────────────────────────────────────

@dataclass
class TelemetryPacket:
    """Data received from Arduino."""
    enc_left: int = 0
    enc_right: int = 0
    speed_left: float = 0.0
    speed_right: float = 0.0
    imu_yaw: float = 0.0
    imu_pitch: float = 0.0
    imu_roll: float = 0.0
    imu_available: bool = False
    battery_voltage: float = 0.0
    battery_current: float = 0.0
    estop: bool = False
    timestamp: float = 0.0


class ArduinoBridge:
    """Serial bridge between Jetson and Arduino UNO Q."""

    def __init__(
        self,
        port: str = None,
        baud: int = 115200,
        on_telemetry: Optional[Callable] = None,
    ):
        self.port = port or os.environ.get(
            "TANK_ARDUINO_PORT", "/dev/ttyACM0"
        )
        self.baud = baud
        self.on_telemetry = on_telemetry
        self.ser = None
        self._connected = False
        self._running = False
        self._thread = None
        self._latest_telemetry = TelemetryPacket()

    def connect(self) -> bool:
        """Open serial connection to Arduino."""
        try:
            import serial
            self.ser = serial.Serial(
                self.port,
                self.baud,
                timeout=0.1,
                write_timeout=1,
            )
            # Wait for Arduino to reset after serial connect
            time.sleep(2)
            self.ser.reset_input_buffer()
            self._connected = True
            logger.info(f"Connected to Arduino: {self.port} @ {self.baud}")
            return True
        except ImportError:
            logger.error("pyserial not installed: pip install pyserial")
            return False
        except FileNotFoundError:
            logger.error(f"Serial port not found: {self.port}")
            return False
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    def start(self):
        """Start background telemetry reader."""
        if not self._connected:
            if not self.connect():
                return
        self._running = True
        self._thread = threading.Thread(
            target=self._reader_loop, daemon=True
        )
        self._thread.start()
        logger.info("Arduino bridge started")

    def stop(self):
        """Stop the bridge."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        if self.ser and self.ser.is_open:
            self.ser.close()
        logger.info("Arduino bridge stopped")

    def _reader_loop(self):
        """Background thread reading telemetry from Arduino."""
        while self._running and self._connected:
            try:
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode().strip()
                    if line:
                        data = json.loads(line)
                        self._parse_telemetry(data)
            except json.JSONDecodeError:
                pass
            except Exception as e:
                logger.warning(f"Read error: {e}")
                time.sleep(0.1)

    def _parse_telemetry(self, data: Dict):
        """Parse telemetry from Arduino JSON."""
        t = TelemetryPacket(
            enc_left=data.get("enc_L", 0),
            enc_right=data.get("enc_R", 0),
            speed_left=data.get("spd_L", 0.0),
            speed_right=data.get("spd_R", 0.0),
            battery_voltage=data.get("battery", {}).get("voltage", 0.0),
            battery_current=data.get("battery", {}).get("current", 0.0),
            estop=data.get("estop", False),
            timestamp=data.get("timestamp", time.time()),
        )
        imu = data.get("imu", {})
        t.imu_yaw = imu.get("yaw", 0.0)
        t.imu_pitch = imu.get("pitch", 0.0)
        t.imu_roll = imu.get("roll", 0.0)
        t.imu_available = imu.get("available", False)

        self._latest_telemetry = t

        if self.on_telemetry:
            self.on_telemetry(t)

    @property
    def telemetry(self) -> TelemetryPacket:
        return self._latest_telemetry

    # ─── Commands to Arduino ───────────────────────────────────────────

    def send_move(self, left: float, right: float):
        """Send movement command: left/right speed (-1.0 to 1.0)."""
        self._send({"cmd": "MOVE", "left": left, "right": right})

    def send_stop(self):
        """Emergency stop."""
        self._send({"cmd": "STOP"})

    def send_servo(self, channel: int, angle: int):
        """Set servo angle."""
        self._send({"cmd": "SERVO", "channel": channel, "angle": angle})

    def send_ping(self):
        """Heartbeat ping."""
        self._send({"cmd": "PING"})

    def send_config(self, **kwargs):
        """Send configuration parameters."""
        self._send({"cmd": "CONFIG", **kwargs})

    def _send(self, data: Dict):
        """Send JSON command to Arduino."""
        if not self._connected:
            return
        try:
            msg = json.dumps(data) + "\n"
            self.ser.write(msg.encode())
        except Exception as e:
            logger.warning(f"Send failed: {e}")

    # ─── High-Level Actions ────────────────────────────────────────────

    def forward(self, speed: float = 0.5):
        """Drive forward."""
        self.send_move(speed, speed)

    def backward(self, speed: float = 0.5):
        """Drive backward."""
        self.send_move(-speed, -speed)

    def turn_left(self, speed: float = 0.5):
        """Turn left (differential drive)."""
        self.send_move(-speed, speed)

    def turn_right(self, speed: float = 0.5):
        """Turn right (differential drive)."""
        self.send_move(speed, -speed)

    def set_head_pan(self, angle: int):
        """Set head pan angle (servo channel 0)."""
        self.send_servo(0, angle)

    def set_head_tilt(self, angle: int):
        """Set head tilt angle (servo channel 1)."""
        self.send_servo(1, angle)

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def is_estop(self) -> bool:
        return self._latest_telemetry.estop


# ─── Integration with Tank System ──────────────────────────────────────

def create_arduino_bridge() -> ArduinoBridge:
    """Create and return an ArduinoBridge instance."""
    return ArduinoBridge()


# ─── Standalone Test ───────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    bridge = ArduinoBridge()
    if bridge.connect():
        bridge.start()
        print("Bridge running. Press Ctrl+C to stop.")

        try:
            while True:
                t = bridge.telemetry
                print(
                    f"enc=[{t.enc_left}, {t.enc_right}] "
                    f"spd=[{t.speed_left:.1f}, {t.speed_right:.1f}] "
                    f"yaw={t.imu_yaw:.1f} "
                    f"bat={t.battery_voltage:.1f}V "
                    f"estop={t.estop}"
                )
                time.sleep(1)
        except KeyboardInterrupt:
            bridge.stop()
    else:
        print("Failed to connect to Arduino")
