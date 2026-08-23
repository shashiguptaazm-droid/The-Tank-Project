"""
unoq_manager.py - UNO Q TankOS Integration Manager
Feature 11-20: UNO Q as first-class TankOS device
- State reporting to /health/status
- Diagnostics integration
- EventBus events
- SQLite telemetry
- Configuration management
"""
import time
import json
import logging
import sqlite3
import threading
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
from enum import Enum

logger = logging.getLogger("tank.unoq.manager")


class UNOQState(Enum):
    OFFLINE = "offline"
    BOOTING = "booting"
    CONNECTED = "connected"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAULT = "fault"
    RECOVERY = "recovery"
    SHUTDOWN = "shutdown"


class UNOQManager:
    """First-class TankOS manager for UNO Q hardware."""

    def __init__(self, serial_port="/dev/ttyACM1", baud=115200, db_path="tank_telemetry.db"):
        self.serial_port = serial_port
        self.baud = baud
        self.state = UNOQState.OFFLINE
        self.state_changed_at = time.time()
        self.db_path = db_path
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.telemetry_cache: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._conn = None
        self._init_db()

    def _init_db(self):
        try:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            c = self._conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS unoq_telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                state TEXT,
                cpu REAL,
                ram REAL,
                temp REAL,
                mcu_heartbeat INTEGER,
                motor_l_speed INTEGER,
                motor_r_speed INTEGER,
                battery_voltage REAL,
                battery_current REAL,
                imu_ax REAL, imu_ay REAL, imu_az REAL,
                encoder_l INTEGER, encoder_r INTEGER,
                e_stop INTEGER,
                fault_code INTEGER
            )''')
            c.execute('''CREATE TABLE IF NOT EXISTS unoq_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                event_type TEXT,
                source TEXT,
                message TEXT,
                severity TEXT
            )''')
            self._conn.commit()
        except Exception as e:
            logger.error(f"DB init failed: {e}")

    # --- EventBus ---
    def on(self, event_type: str, handler: Callable):
        with self._lock:
            if event_type not in self.event_handlers:
                self.event_handlers[event_type] = []
            self.event_handlers[event_type].append(handler)

    def emit_event(self, event_type: str, source: str, message: str, severity: str = "info"):
        event = {
            "timestamp": time.time(),
            "type": event_type,
            "source": source,
            "message": message,
            "severity": severity,
        }
        logger.info(f"[EVENT] {event_type} from {source}: {message}")
        # Store in DB
        try:
            if self._conn:
                self._conn.execute(
                    "INSERT INTO unoq_events (timestamp, event_type, source, message, severity) VALUES (?, ?, ?, ?, ?)",
                    (event["timestamp"], event_type, source, message, severity)
                )
                self._conn.commit()
        except Exception:
            pass
        # Dispatch to handlers
        with self._lock:
            handlers = self.event_handlers.get(event_type, [])
            for h in handlers:
                try:
                    h(event)
                except Exception as e:
                    logger.error(f"Event handler error: {e}")
        return event

    # --- State management ---
    def set_state(self, new_state: UNOQState):
        old = self.state
        self.state = new_state
        self.state_changed_at = time.time()
        self.emit_event("state_change", "unoq_manager", f"{old.value} -> {new_state.value}",
                        "warning" if new_state in (UNOQState.FAULT, UNOQState.DEGRADED) else "info")

    # --- Diagnostics ---
    def get_diagnostics(self) -> Dict[str, Any]:
        uptime = time.time() - self.state_changed_at if self.state == UNOQState.HEALTHY else 0
        return {
            "unoq_state": self.state.value,
            "serial_port": self.serial_port,
            "baud": self.baud,
            "uptime_seconds": uptime,
            "db_events": self._count_events(),
            "telemetry_records": self._count_telemetry(),
        }

    def _count_events(self) -> int:
        try:
            if self._conn:
                r = self._conn.execute("SELECT COUNT(*) FROM unoq_events").fetchone()
                return r[0] if r else 0
        except Exception:
            pass
        return 0

    def _count_telemetry(self) -> int:
        try:
            if self._conn:
                r = self._conn.execute("SELECT COUNT(*) FROM unoq_telemetry").fetchone()
                return r[0] if r else 0
        except Exception:
            pass
        return 0

    # --- Telemetry ---
    def store_telemetry(self, data: Dict[str, Any]):
        try:
            if self._conn:
                self._conn.execute('''INSERT INTO unoq_telemetry
                    (timestamp, state, cpu, ram, temp, mcu_heartbeat,
                     motor_l_speed, motor_r_speed, battery_voltage, battery_current,
                     imu_ax, imu_ay, imu_az, encoder_l, encoder_r, e_stop, fault_code)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
                    time.time(), data.get("state", self.state.value),
                    data.get("cpu", 0), data.get("ram", 0), data.get("temp", 0),
                    data.get("mcu_heartbeat", 0),
                    data.get("motor_l", 0), data.get("motor_r", 0),
                    data.get("battery_v", 0), data.get("battery_a", 0),
                    data.get("imu_ax", 0), data.get("imu_ay", 0), data.get("imu_az", 0),
                    data.get("encoder_l", 0), data.get("encoder_r", 0),
                    data.get("e_stop", 0), data.get("fault_code", 0)
                ))
                self._conn.commit()
        except Exception as e:
            logger.error(f"Telemetry store failed: {e}")
        self.telemetry_cache = data

    def get_health_status(self) -> Dict[str, Any]:
        cache = self.telemetry_cache
        return {
            "component": "uno_q",
            "state": self.state.value,
            "uptime": time.time() - self.state_changed_at,
            "battery_voltage": cache.get("battery_v", 0),
            "cpu_temp": cache.get("temp", 0),
            "mcu_heartbeat": cache.get("mcu_heartbeat", 0),
            "e_stop": cache.get("e_stop", False),
            "fault_code": cache.get("fault_code", 0),
            "diagnostics": self.get_diagnostics(),
        }

    # --- Configuration ---
    def get_config(self) -> Dict[str, Any]:
        return {
            "serial_port": self.serial_port,
            "baud": self.baud,
            "heartbeat_interval_ms": 500,
            "command_timeout_ms": 2000,
            "watchdog_timeout_ms": 5000,
            "max_motor_speed": 255,
            "max_servo_angle": 180,
        }

    def shutdown(self):
        self.set_state(UNOQState.SHUTDOWN)
        if self._conn:
            self._conn.close()
        logger.info("UNOQManager shutdown complete")
