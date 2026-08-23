"""
power_intel.py - Power Intelligence System
Features 61-70: Dual INA219, energy calc, runtime estimate, power alarms
"""
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("tank.unoq.power")


class PowerRail:
    """Single power rail monitor."""
    def __init__(self, name: str, i2c_addr: int = 0x40):
        self.name = name
        self.i2c_addr = i2c_addr
        self.voltage = 0.0
        self.current = 0.0
        self.power = 0.0
        self.energy_wh = 0.0
        self.last_read = 0.0
        self.alarm_high_v = 17.0
        self.alarm_low_v = 10.0
        self.alarm_high_a = 10.0
        self.alarms = []

    def update(self, voltage: float, current: float):
        self.voltage = voltage
        self.current = current
        self.power = voltage * current
        dt_h = (time.time() - self.last_read) / 3600.0 if self.last_read > 0 else 0
        self.energy_wh += self.power * dt_h
        self.last_read = time.time()
        self._check_alarms()

    def _check_alarms(self):
        if self.voltage > self.alarm_high_v:
            self.alarms.append({"type": "overvoltage", "value": self.voltage, "time": time.time()})
            logger.warning(f"{self.name}: OVERVOLTAGE {self.voltage:.2f}V")
        if self.voltage < self.alarm_low_v and self.voltage > 0:
            self.alarms.append({"type": "undervoltage", "value": self.voltage, "time": time.time()})
            logger.warning(f"{self.name}: UNDERVOLTAGE {self.voltage:.2f}V")
        if self.current > self.alarm_high_a:
            self.alarms.append({"type": "overcurrent", "value": self.current, "time": time.time()})
            logger.warning(f"{self.name}: OVERCURRENT {self.current:.2f}A")
        if self.current < 0:
            self.alarms.append({"type": "charging", "value": self.current, "time": time.time()})

    def reset_energy(self):
        self.energy_wh = 0.0

    def get_status(self) -> dict:
        return {
            "name": self.name,
            "voltage": round(self.voltage, 3),
            "current": round(self.current, 3),
            "power_w": round(self.power, 2),
            "energy_wh": round(self.energy_wh, 4),
            "alarms": self.alarms[-3:],
        }


class PowerIntelligence:
    """Dual INA219 power monitoring with energy tracking."""

    def __init__(self):
        self.motor_rail = PowerRail("motor", 0x40)
        self.logic_rail = PowerRail("logic", 0x41)
        self.battery_capacity_wh = 59.2
        self.last_battery_pct = 100.0
        self.on_alarm: Optional[callable] = None

    def update_motor(self, voltage: float, current: float):
        self.motor_rail.update(voltage, current)

    def update_logic(self, voltage: float, current: float):
        self.logic_rail.update(voltage, current)

    def get_battery_percentage(self) -> float:
        total_energy = self.motor_rail.energy_wh + self.logic_rail.energy_wh
        pct = max(0, 100 - (total_energy / self.battery_capacity_wh * 100))
        self.last_battery_pct = pct
        return round(pct, 1)

    def estimate_runtime_hours(self) -> float:
        total_power = self.motor_rail.power + self.logic_rail.power
        remaining_wh = self.battery_capacity_wh * self.get_battery_percentage() / 100
        if total_power > 0:
            return round(remaining_wh / total_power, 2)
        return 999.0

    def detect_abnormal_consumption(self) -> bool:
        if self.motor_rail.current > 8.0:
            logger.warning("Abnormal motor current spike")
            return True
        if self.logic_rail.current > 3.0:
            logger.warning("Abnormal logic current spike")
            return True
        return False

    def detect_charging_state(self) -> str:
        total_current = self.motor_rail.current + self.logic_rail.current
        if total_current < 0:
            return "charging"
        elif total_current > 0:
            return "discharging"
        return "idle"

    def get_power_rail_health(self) -> Dict[str, str]:
        health = {}
        for rail in [self.motor_rail, self.logic_rail]:
            if len(rail.alarms) > 0:
                health[rail.name] = "warning"
            else:
                health[rail.name] = "healthy"
        return health

    def get_status(self) -> Dict[str, Any]:
        return {
            "motor_rail": self.motor_rail.get_status(),
            "logic_rail": self.logic_rail.get_status(),
            "battery_pct": self.get_battery_percentage(),
            "runtime_hours": self.estimate_runtime_hours(),
            "abnormal": self.detect_abnormal_consumption(),
            "charging_state": self.detect_charging_state(),
            "rail_health": self.get_power_rail_health(),
            "total_power_w": round(self.motor_rail.power + self.logic_rail.power, 2),
            "total_energy_wh": round(self.motor_rail.energy_wh + self.logic_rail.energy_wh, 4),
        }
