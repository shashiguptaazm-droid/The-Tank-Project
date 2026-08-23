"""
sensor_reliability.py - Sensor Reliability System
Features 81-90: BNO055 health, I2C fault recovery, quality scoring
"""
import time
import threading
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("tank.unoq.sensor")


class SensorHealth:
    def __init__(self, name: str, interface: str):
        self.name = name
        self.interface = interface
        self.healthy = True
        self.calibrated = False
        self.last_read_time = 0.0
        self.read_count = 0
        self.error_count = 0
        self.dropouts = 0
        self.quality_score = 1.0
        self.calibration_status = "uncalibrated"
        self.fault_type: Optional[str] = None
        self.recovery_count = 0


class SensorReliability:
    """BNO055 health, I2C bus fault recovery, quality scoring."""

    def __init__(self):
        self.sensors: Dict[str, SensorHealth] = {}
        self.i2c_bus_health: Dict[int, Dict] = {1: {"faults": 0, "sda_stuck": False, "scl_stuck": False}}
        self.sda_stuck_threshold = 5
        self.scl_stuck_threshold = 5
        self.on_fault: Optional[callable] = None
        self._lock = threading.Lock()

    def register_sensor(self, name: str, interface: str = "i2c"):
        self.sensors[name] = SensorHealth(name, interface)

    def update_bno055(self, calibration_status: Dict[str, int]):
        sensor = self.sensors.get("bno055")
        if not sensor:
            return
        sensor.last_read_time = time.time()
        sensor.read_count += 1
        sys_cal = calibration_status.get("sys", 0)
        gyro_cal = calibration_status.get("gyro", 0)
        accel_cal = calibration_status.get("accel", 0)
        mag_cal = calibration_status.get("mag", 0)
        if sys_cal >= 3 and gyro_cal >= 3:
            sensor.calibrated = True
            sensor.calibration_status = f"S{sys_cal}G{gyro_cal}A{accel_cal}M{mag_cal}"
        else:
            sensor.calibrated = False
            sensor.calibration_status = f"S{sys_cal}G{gyro_cal}A{accel_cal}M{mag_cal} (uncal)"

    def record_read(self, name: str, success: bool):
        if name not in self.sensors:
            return
        sensor = self.sensors[name]
        sensor.last_read_time = time.time()
        if success:
            sensor.read_count += 1
        else:
            sensor.error_count += 1
            sensor.dropouts += 1
        total = sensor.read_count + sensor.error_count
        if total > 0:
            success_rate = sensor.read_count / total
            sensor.quality_score = max(0.0, success_rate - sensor.dropouts * 0.01)
        if sensor.quality_score < 0.5:
            sensor.healthy = False
            sensor.fault_type = "low_quality"
            logger.warning(f"Sensor {name}: quality={sensor.quality_score:.2f}")

    def check_i2c_bus(self, bus: int = 1):
        bus_health = self.i2c_bus_health.get(bus, {"faults": 0, "sda_stuck": False, "scl_stuck": False})
        if bus_health.get("sda_stuck"):
            bus_health["faults"] += 1
            self._attempt_i2c_recovery(bus)
        if bus_health.get("scl_stuck"):
            bus_health["faults"] += 1
            self._attempt_i2c_recovery(bus)
        self.i2c_bus_health[bus] = bus_health

    def detect_stuck_lines(self, bus: int, sda_state: bool, scl_state: bool):
        bus_health = self.i2c_bus_health.get(bus, {"faults": 0, "sda_stuck": False, "scl_stuck": False})
        if not sda_state:
            bus_health["sda_stuck_count"] = bus_health.get("sda_stuck_count", 0) + 1
            if bus_health["sda_stuck_count"] > self.sda_stuck_threshold:
                bus_health["sda_stuck"] = True
                logger.error(f"I2C bus {bus}: SDA stuck low")
        else:
            bus_health["sda_stuck_count"] = 0
            bus_health["sda_stuck"] = False
        if not scl_state:
            bus_health["scl_stuck_count"] = bus_health.get("scl_stuck_count", 0) + 1
            if bus_health["scl_stuck_count"] > self.scl_stuck_threshold:
                bus_health["scl_stuck"] = True
                logger.error(f"I2C bus {bus}: SCL stuck low")
        else:
            bus_health["scl_stuck_count"] = 0
            bus_health["scl_stuck"] = False
        self.i2c_bus_health[bus] = bus_health

    def _attempt_i2c_recovery(self, bus: int):
        logger.info(f"Attempting I2C bus {bus} recovery: toggle SDA/SCL")
        for sensor in self.sensors.values():
            if sensor.interface == f"i2c{bus}":
                sensor.recovery_count += 1
                sensor.fault_type = "recovering"
        if self.on_fault:
            self.on_fault({"bus": bus, "action": "i2c_recovery"})

    def reinit_device(self, name: str):
        sensor = self.sensors.get(name)
        if sensor:
            sensor.fault_type = None
            sensor.error_count = 0
            sensor.quality_score = 1.0
            sensor.healthy = True
            logger.info(f"Sensor {name} reinitialized")

    def get_sensor_quality(self, name: str) -> float:
        return self.sensors[name].quality_score if name in self.sensors else 0.0

    def get_status(self) -> Dict[str, Any]:
        return {
            "sensors": {
                name: {
                    "healthy": s.healthy,
                    "calibrated": s.calibrated,
                    "calibration_status": s.calibration_status,
                    "quality": round(s.quality_score, 3),
                    "read_count": s.read_count,
                    "error_count": s.error_count,
                    "dropouts": s.dropouts,
                    "fault": s.fault_type,
                    "recovery_count": s.recovery_count,
                }
                for name, s in self.sensors.items()
            },
            "i2c_buses": {
                bus: {
                    "faults": h.get("faults", 0),
                    "sda_stuck": h.get("sda_stuck", False),
                    "scl_stuck": h.get("scl_stuck", False),
                }
                for bus, h in self.i2c_bus_health.items()
            },
        }
