"""Health monitor — battery + CPU/GPU temps + diagnostic snapshot to ROS
and to a Prometheus exporter.

Subscribes
    /battery/state      sensor_msgs/BatteryState       (optional)

Publishes
    /health/state        std_msgs/String      JSON {"cpu_c":..., "bat_v":..., "estop": BOOL, "events_so_far": N}
    /health/prometheus   std_msgs/String      text/plain Prometheus exposition format
    /health/ok           std_msgs/Bool        overall status

Parameters
    watchdog_cpu_c   float  default 75.0   (over -> /health/ok = False)
    watchdog_bat_pct float  default 10.0   (under -> /health/ok = False)
    publish_period_sec float default 5.0
    psutil_path       str    default "/proc"
    vcgencmd_fallback bool   default True
"""
from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from typing import Optional

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import BatteryState
from std_msgs.msg import Bool, String

QOS = 10


class VcgencmdUnavailable(Exception):
    pass


def read_vcgencmd(field: str) -> float:
    """Read Raspberry-Pi vcgencmd-measured temperature / voltage."""
    out = subprocess.check_output(
        ["vcgencmd", "measure_" + field],
        stderr=subprocess.DEVNULL,
    ).decode("ascii").strip()
    # 'temp=42.0'C' or 'volt=0.8500V'
    if "=" not in out:
        raise VcgencmdUnavailable(out)
    value = out.split("=", 1)[1].rstrip("CF")
    return float(value.replace("V", "").replace("'C", "").replace("'F", ""))


class HealthNode(Node):
    def __init__(self) -> None:
        super().__init__("health_node")
        self._declare_params()
        self._host_metrics: dict = {}
        self._battery: Optional[BatteryState] = None
        self._last_tick = 0.0
        self._lock = threading.Lock()
        self.create_subscription(BatteryState, "/battery/state",
                                  self._on_battery, QOS)
        self._state_pub = self.create_publisher(String, "/health/state", QOS)
        self._ok_pub    = self.create_publisher(Bool,  "/health/ok",    QOS)
        self._prom_pub  = self.create_publisher(String, "/health/prometheus", QOS)
        period = max(1.0, float(self.get_parameter("publish_period_sec").value))
        self._timer = self.create_timer(period, self._tick)
        self.get_logger().info("health_node initialised")

    def _declare_params(self) -> None:
        self.declare_parameter("watchdog_cpu_c", 75.0)
        self.declare_parameter("watchdog_bat_pct", 10.0)
        self.declare_parameter("publish_period_sec", 5.0)
        self.declare_parameter("vcgencmd_fallback", True)

    def _on_battery(self, msg: BatteryState) -> None:
        self._battery = msg

    def _tick(self) -> None:
        try:
            self._host_metrics = self._collect_host_metrics()
        except Exception as exc:
            self.get_logger().warn(f"host metrics failed: {exc}",
                                   throttle_duration_sec=5.0)
        cpu_c = float(self._host_metrics.get("cpu_c", -1.0))
        bat_pct = (
            float(self._battery.percentage) if self._battery is not None
            else 100.0
        )
        ok = (
            cpu_c < float(self.get_parameter("watchdog_cpu_c").value)
            or cpu_c < 0
        ) and bat_pct > float(self.get_parameter("watchdog_bat_pct").value)
        state = {
            **self._host_metrics,
            "bat_pct": bat_pct,
            "ok": bool(ok),
            "timestamp": time.time(),
        }
        self._state_pub.publish(String(data=json.dumps(state)))
        self._ok_pub.publish(Bool(data=bool(ok)))
        self._prom_pub.publish(String(data=self._to_prom(state)))

    def _collect_host_metrics(self) -> dict:
        # cpu temp via vcgencmd; voltage via vcgencmd; cpu/mem stats optional
        out: dict = {}
        try:
            out["cpu_c"] = read_vcgencmd("temp")
        except Exception:
            out["cpu_c"] = -1.0
        try:
            out["core_volts"] = read_vcgencmd("volts")
        except Exception:
            out["core_volts"] = -1.0
        # Memory snapshot via /proc
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal"):
                        out["mem_total_kb"] = int(line.split()[1])
                    elif line.startswith("MemAvailable"):
                        out["mem_avail_kb"] = int(line.split()[1])
        except Exception:
            pass
        # Load average
        try:
            with open("/proc/loadavg") as f:
                parts = f.read().split()
                out["load1"] = float(parts[0])
                out["load5"] = float(parts[1])
        except Exception:
            pass
        return out

    def _to_prom(self, state: dict) -> str:
        lines = ["# HELP tank_health_pi CPU temperature C", "# TYPE tank_health_pi gauge"]
        if "cpu_c" in state:
            lines.append(f"tank_health_pi_cpu_c {state['cpu_c']}")
        if "core_volts" in state:
            lines.append(f"tank_health_pi_core_volts {state['core_volts']}")
        if "load1" in state:
            lines.append(f"tank_health_pi_load1 {state['load1']}")
        if "load5" in state:
            lines.append(f"tank_health_pi_load5 {state['load5']}")
        if "bat_pct" in state:
            lines.append(f"tank_health_pi_battery_pct {state['bat_pct']}")
        return "\n".join(lines) + "\n"


def main(args=None) -> None:
    rclpy.init(args=args)
    node = HealthNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
