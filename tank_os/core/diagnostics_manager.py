"""TankOS Diagnostics Manager — CPU, RAM, disk, temp, ROS, logs, hardware."""
from __future__ import annotations
import logging, threading, time, os, subprocess
from typing import Any, Dict, List, Optional
from tank_os.core.event_bus import Event, EventBus

logger = logging.getLogger("tank_os.diagnostics_manager")

class DiagnosticsManager:
    _instance: Optional["DiagnosticsManager"] = None; _lock = threading.Lock()
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._bus = EventBus()
                cls._instance._snapshots: List[Dict[str, Any]] = []
            return cls._instance
    def initialize(self) -> None:
        logger.info("DiagnosticsManager initialized")
    def collect(self) -> Dict[str, Any]:
        """Collect a full system diagnostics snapshot."""
        result: Dict[str, Any] = {"timestamp": time.time()}
        result["cpu"] = self._get_cpu()
        result["memory"] = self._get_memory()
        result["disk"] = self._get_disk()
        result["temperature"] = self._get_temperature()
        result["network"] = self._get_network()
        result["ros"] = self._get_ros_status()
        result["uptime"] = self._get_uptime()
        self._snapshots.append(result)
        if len(self._snapshots) > 100: self._snapshots.pop(0)
        return result
    def _get_cpu(self) -> Dict[str, Any]:
        try:
            import psutil; return {"percent": psutil.cpu_percent(interval=0.1), "count": psutil.cpu_count()}
        except ImportError:
            try:
                load = os.getloadavg()
                return {"load_1m": round(load[0], 2), "load_5m": round(load[1], 2), "load_15m": round(load[2], 2)}
            except Exception: return {"error": "unavailable"}
    def _get_memory(self) -> Dict[str, Any]:
        try:
            import psutil; mem = psutil.virtual_memory()
            return {"total_gb": round(mem.total / 1e9, 2), "available_gb": round(mem.available / 1e9, 2), "percent": mem.percent}
        except ImportError:
            try:
                r = subprocess.run(["free", "-b"], capture_output=True, text=True, timeout=3)
                lines = r.stdout.splitlines()
                if len(lines) > 1:
                    parts = lines[1].split()
                    if len(parts) >= 3:
                        total = int(parts[1]); avail = int(parts[3])
                        return {"total_gb": round(total / 1e9, 2), "available_gb": round(avail / 1e9, 2)}
            except Exception: pass
            return {"error": "unavailable"}
    def _get_disk(self) -> Dict[str, Any]:
        try:
            import psutil; d = psutil.disk_usage("/")
            return {"total_gb": round(d.total / 1e9, 2), "used_gb": round(d.used / 1e9, 2), "percent": d.percent}
        except ImportError:
            try:
                r = subprocess.run(["df", "-B1", "/"], capture_output=True, text=True, timeout=3)
                parts = r.stdout.splitlines()[-1].split()
                if len(parts) >= 4:
                    return {"total_gb": round(int(parts[1]) / 1e9, 2), "used_gb": round(int(parts[2]) / 1e9, 2)}
            except Exception: pass
            return {"error": "unavailable"}
    def _get_temperature(self) -> Dict[str, Any]:
        try:
            r = subprocess.run(["vcgencmd", "measure_temp"], capture_output=True, text=True, timeout=2)
            temp = r.stdout.strip().replace("temp=", "").replace("'C", "")
            return {"cpu_c": float(temp)}
        except Exception: pass
        for path in ["/sys/class/thermal/thermal_zone0/temp"]:
            try:
                with open(path) as f: return {"cpu_c": round(int(f.read().strip()) / 1000, 1)}
            except Exception: pass
        return {"error": "unavailable"}
    def _get_network(self) -> Dict[str, Any]:
        try:
            r = subprocess.run(["hostname", "-I"], capture_output=True, text=True, timeout=2)
            ips = r.stdout.strip().split() if r.stdout.strip() else []
            return {"ips": ips}
        except Exception: return {"error": "unavailable"}
    def _get_ros_status(self) -> Dict[str, Any]:
        try:
            import subprocess
            r = subprocess.run(["ros2", "node", "list"], capture_output=True, text=True, timeout=3)
            nodes = [n.strip() for n in r.stdout.splitlines() if n.strip()]
            return {"nodes": nodes, "node_count": len(nodes)}
        except Exception: return {"error": "ROS2 not available"}
    def _get_uptime(self) -> float:
        try:
            with open("/proc/uptime") as f: return float(f.read().split()[0])
        except Exception: return 0.0
    def history(self, limit: int = 10) -> List[Dict[str, Any]]:
        return list(self._snapshots[-limit:])
    def summary(self) -> Dict[str, Any]:
        """Quick health summary string."""
        d = self.collect()
        return {
            "cpu": d.get("cpu", {}).get("percent", "?"),
            "mem": d.get("memory", {}).get("percent", "?"),
            "disk": d.get("disk", {}).get("percent", "?"),
            "temp": d.get("temperature", {}).get("cpu_c", "?"),
            "ros_nodes": d.get("ros", {}).get("node_count", 0),
        }
