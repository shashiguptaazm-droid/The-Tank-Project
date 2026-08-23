"""
anomaly_detector.py - Predictive Robot AI (Features 171-180)
Trajectory prediction, collision-time, failure prediction, anomaly detection
"""
import time
import math
import logging
from typing import Dict, Any, List, Optional, Tuple
from collections import deque

logger = logging.getLogger("tank.ai.predictive")


class PredictiveAI:
    """Features 171-180: Predictive intelligence for safety and maintenance."""

    def __init__(self):
        self.telemetry_history: deque = deque(maxlen=1000)
        self.anomaly_log: List[Dict] = []
        self.prediction_cache: Dict[str, Any] = {}

    # 171-173. Human/object trajectory prediction + collision time
    def predict_trajectory(self, history: List[Tuple[float, float]], steps: int = 10) -> List[Tuple[float, float]]:
        if len(history) < 2:
            return []
        recent = history[-5:]
        vx = [recent[i+1][0] - recent[i][0] for i in range(len(recent)-1)]
        vy = [recent[i+1][1] - recent[i][1] for i in range(len(recent)-1)]
        avg_vx = sum(vx) / len(vx) if vx else 0
        avg_vy = sum(vy) / len(vy) if vy else 0
        last = recent[-1]
        return [(last[0] + avg_vx * i, last[1] + avg_vy * i) for i in range(1, steps + 1)]

    def predict_collision_time(self, robot_path: List[Tuple], object_path: List[Tuple]) -> Optional[float]:
        for i, rp in enumerate(robot_path):
            for j, op in enumerate(object_path):
                dist = math.sqrt((rp[0]-op[0])**2 + (rp[1]-op[1])**2)
                if dist < 0.5:
                    return i * 0.1
        return None

    def predict_obstacle_motion(self, obstacle_vel: Tuple[float, float], horizon: float = 3.0) -> Dict[str, Any]:
        predictions = []
        for t in [0.5, 1.0, 1.5, 2.0, 3.0]:
            if t <= horizon:
                predictions.append({"time": t, "pos": (obstacle_vel[0] * t, obstacle_vel[1] * t)})
        return {"predictions": predictions}

    # 174-175. Obstacle motion prediction + Path risk
    def assess_path_risk(self, path: List[Tuple[float, float]], obstacles: List[Dict]) -> Dict[str, Any]:
        risks = []
        for i, pt in enumerate(path):
            for obs in obstacles:
                ox, oy = obs.get("x", 0), obs.get("y", 0)
                dist = math.sqrt((pt[0]-ox)**2 + (pt[1]-oy)**2)
                if dist < 1.0:
                    risks.append({"step": i, "obstacle": obs, "distance": round(dist, 3)})
        return {"total_risks": len(risks), "max_risk": max((r["distance"] for r in risks), default=999),
                "risks": risks[:5]}

    # 176. Battery runtime prediction
    def predict_battery_runtime(self, voltage_history: List[float], capacity_wh: float = 59.2) -> Dict[str, Any]:
        if len(voltage_history) < 2:
            return {"estimated_minutes": 0}
        recent = voltage_history[-10:]
        v_start = recent[0]
        v_end = recent[-1]
        v_drop = v_start - v_end
        time_span = len(recent) * 5  # assume 5s intervals
        if v_drop <= 0:
            return {"estimated_minutes": 999, "status": "not_discharging"}
        drain_rate = v_drop / time_span
        remaining_v = v_end - 10.5
        remaining_s = remaining_v / drain_rate if drain_rate > 0 else 999
        return {"estimated_minutes": round(remaining_s / 60, 1), "drain_rate": round(drain_rate, 4),
                "current_voltage": v_end}

    # 177-179. Motor/Sensor/Thermal failure prediction
    def predict_motor_failure(self, motor_current_history: List[float], motor_temp_history: List[float]) -> Dict[str, Any]:
        warnings = []
        if len(motor_current_history) > 5:
            avg_current = sum(motor_current_history[-5:]) / 5
            if avg_current > 8.0:
                warnings.append({"type": "overcurrent", "avg": round(avg_current, 2)})
        if len(motor_temp_history) > 5:
            avg_temp = sum(motor_temp_history[-5:]) / 5
            if avg_temp > 70:
                warnings.append({"type": "overheat", "avg_temp": round(avg_temp, 1)})
        return {"warnings": warnings, "healthy": len(warnings) == 0}

    def predict_sensor_failure(self, sensor_health: Dict[str, float]) -> Dict[str, Any]:
        at_risk = []
        for sensor, health in sensor_health.items():
            if health < 0.3:
                at_risk.append({"sensor": sensor, "health": health, "risk": "high"})
            elif health < 0.6:
                at_risk.append({"sensor": sensor, "health": health, "risk": "medium"})
        return {"sensors_at_risk": at_risk, "count": len(at_risk)}

    def predict_thermal_failure(self, temp_history: List[float], threshold: float = 85.0) -> Dict[str, Any]:
        if len(temp_history) < 3:
            return {"risk": "low", "projected_temp": 0}
        recent = temp_history[-10:]
        trend = (recent[-1] - recent[0]) / max(1, len(recent))
        projected = recent[-1] + trend * 60  # 1 minute ahead
        risk = "high" if projected > threshold else "medium" if projected > threshold - 10 else "low"
        return {"risk": risk, "projected_temp_60s": round(projected, 1), "current": recent[-1], "trend": round(trend, 3)}

    # 180. System anomaly prediction
    def record_telemetry(self, data: Dict[str, Any]):
        data["timestamp"] = time.time()
        self.telemetry_history.append(data)

    def detect_anomaly(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        anomalies = []
        if "temperature" in data and data["temperature"] > 80:
            anomalies.append({"type": "thermal", "value": data["temperature"]})
        if "battery_voltage" in data and data["battery_voltage"] < 11:
            anomalies.append({"type": "low_battery", "value": data["battery_voltage"]})
        if "cpu_usage" in data and data["cpu_usage"] > 95:
            anomalies.append({"type": "cpu_overload", "value": data["cpu_usage"]})
        if anomalies:
            for a in anomalies:
                a["timestamp"] = time.time()
                self.anomaly_log.append(a)
            return {"anomalies": anomalies}
        return None

    def get_anomaly_history(self, last_n: int = 10) -> List[Dict]:
        return self.anomaly_log[-last_n:]

    def get_status(self) -> Dict[str, Any]:
        return {
            "telemetry_records": len(self.telemetry_history),
            "anomalies_detected": len(self.anomaly_log),
            "recent_anomalies": self.anomaly_log[-3:],
        }
