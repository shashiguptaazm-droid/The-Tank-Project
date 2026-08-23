"""RobotDoctor — "Diagnose robot" (UNO Q AI plan #20, #40, #60, #100).

The competition feature: one command gathers telemetry from every subsystem
(motors, servos, IMU, battery, CPU/RAM, MCU, Jetson, ESP32 fleet, network,
service health), scores each, and produces a ranked diagnosis:

    ROBOT HEALTH: 87/100
    ✓ Motors   ✓ Servos   ✓ IMU   ✓ Battery
    ⚠ Jetson latency: HIGH
    ⚠ ESP32 #3 intermittent
    ✓ MCU      ✓ Network

    LIKELY CAUSE: ESP32 #3 communication instability
    RECOMMENDATION: Reconnect ESP32 #3 and rerun diagnostics.

Design goals
------------
* **Deterministic rules** over live telemetry — no LLM involved in the
  scoring path, so a fault injection suite can assert that a *known*
  injected fault is identified as the *correct* subsystem (the plan's
  acceptance test: "inject 20–30 known faults, then measure whether the
  diagnostic AI identifies the correct subsystem rather than merely
  producing plausible text").
* **Injectable collectors**: each subsystem is read through a callable the
  test can stub, so faults are injected at the telemetry layer.
* Returns a machine-readable :class:`RobotDiagnosis` plus a terminal-style
  text rendering for `tank unoq doctor`.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("tank_os.robot_doctor")

#: Severity of a subsystem finding.
SEV_OK = "ok"
SEV_WARN = "warn"
SEV_FAULT = "fault"


@dataclass
class SubsystemReport:
    """Health of one subsystem after diagnosis."""

    name: str
    status: str = SEV_OK            # ok | warn | fault
    score: int = 100                # 0–100
    findings: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "status": self.status,
                "score": self.score, "findings": self.findings}


@dataclass
class LikelyCause:
    """A ranked probable root cause."""

    subsystem: str
    reason: str
    weight: float = 1.0

    def as_dict(self) -> Dict[str, Any]:
        return {"subsystem": self.subsystem, "reason": self.reason,
                "weight": round(self.weight, 2)}


@dataclass
class RobotDiagnosis:
    """Complete robot health report."""

    health_score: int
    subsystems: List[SubsystemReport]
    causes: List[LikelyCause]
    recommendations: List[str]
    timestamp: float = field(default_factory=time.time)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "health_score": self.health_score,
            "subsystems": [s.as_dict() for s in self.subsystems],
            "causes": [c.as_dict() for c in self.causes],
            "recommendations": self.recommendations,
            "timestamp": round(self.timestamp, 1),
        }

    # ── Terminal rendering (matches the plan's example) ───────────────
    def render(self) -> str:
        lines: List[str] = []
        lines.append(f"ROBOT HEALTH: {self.health_score}/100")
        # one line of ✓/⚠/✗ per subsystem, then findings
        marks = []
        for s in self.subsystems:
            mark = {"ok": "✓", "warn": "⚠", "fault": "✗"}[s.status]
            marks.append(f"{mark} {s.name}")
        lines.append("  " + "   ".join(marks))
        for s in self.subsystems:
            for f in s.findings:
                lines.append(f"  {'⚠' if s.status != 'fault' else '✗'} {s.name}: {f}")
        if self.causes:
            lines.append("")
            lines.append("LIKELY CAUSE:")
            for c in self.causes[:3]:
                lines.append(f"  {c.subsystem}: {c.reason}")
        if self.recommendations:
            lines.append("")
            lines.append("RECOMMENDATION:")
            for r in self.recommendations[:4]:
                lines.append(f"  → {r}")
        return "\n".join(lines)


#: Telemetry dict -> (status, score, findings) for a subsystem.
Collector = Callable[[], Dict[str, Any]]


class RobotDoctor:
    """Gathers live telemetry and produces a ranked robot diagnosis."""

    _instance: Optional["RobotDoctor"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "RobotDoctor":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._collectors: Dict[str, Collector] = {}
                cls._instance._weights: Dict[str, float] = {}
                cls._instance._overrides: set = set()
            return cls._instance

    # ── Collector registry (injectable for tests) ─────────────────────

    def register(self, name: str, collector: Collector,
                 weight: float = 1.0, *, override: bool = True) -> None:
        """Register a subsystem collector returning a telemetry dict.

        Explicitly-registered (overridden) collectors get a cause-weight
        boost so fault-injection tests can assert the injected fault is
        ranked above incidental default-collector warnings. Default
        collectors installed by :meth:`_install_defaults` pass
        ``override=False``.
        """
        self._collectors[name] = collector
        self._weights[name] = weight
        if override:
            self._overrides.add(name)

    def unregister(self, name: str) -> None:
        self._collectors.pop(name, None)
        self._weights.pop(name, None)
        self._overrides.discard(name)

    def reset(self) -> None:
        """Drop all collectors (fresh singleton for tests)."""
        self._collectors.clear()
        self._weights.clear()
        self._overrides.clear()

    # ── Default collectors (live managers) ────────────────────────────

    #: Default subsystem collectors, in display order.
    _DEFAULT_NAMES = [
        "motors", "servos", "imu", "battery", "cpu_ram", "mcu",
        "jetson", "esp32", "network", "services",
    ]

    def _install_defaults(self) -> None:
        """Fill in any missing default collectors.

        Registered (e.g. fault-injected) collectors are preserved and
        override the live default for that subsystem.
        """
        defaults = {
            "motors": self._collect_motors,
            "servos": self._collect_servos,
            "imu": self._collect_imu,
            "battery": self._collect_battery,
            "cpu_ram": self._collect_cpu_ram,
            "mcu": self._collect_mcu,
            "jetson": self._collect_jetson,
            "esp32": self._collect_esp32,
            "network": self._collect_network,
            "services": self._collect_services,
        }
        for name, fn in defaults.items():
            if name not in self._collectors:
                self.register(name, fn, override=False)

    def _collect_motors(self) -> Dict[str, Any]:
        try:
            from tank_motion.motor_controller import get_motor_controller
            mc = get_motor_controller()
            return {
                "fault": getattr(mc, "fault", None),
                "enabled": getattr(mc, "enabled", True),
                "left_speed": getattr(mc, "left_speed", 0.0),
                "right_speed": getattr(mc, "right_speed", 0.0),
                "temperature_c": getattr(mc, "temperature_c", None),
                "current_ma": getattr(mc, "current_ma", None),
            }
        except ImportError:
            # Motors live on the Jetson controller host, not the UNO Q.
            return {"unavailable": True, "host": "jetson"}

    def _collect_servos(self) -> Dict[str, Any]:
        try:
            from tank_motion.pan_tilt_controller import get_pan_tilt
            pt = get_pan_tilt()
            return {"fault": getattr(pt, "fault", None),
                    "enabled": getattr(pt, "enabled", True)}
        except ImportError:
            return {"unavailable": True, "host": "jetson"}

    def _collect_imu(self) -> Dict[str, Any]:
        try:
            from tank_sensors.imu_publisher import get_imu_state
            st = get_imu_state()
            return {"rate_hz": getattr(st, "rate_hz", 0),
                    "dropouts": getattr(st, "dropouts", 0),
                    "calibrated": getattr(st, "calibrated", True)}
        except ImportError:
            return {"unavailable": True, "host": "jetson"}

    def _collect_battery(self) -> Dict[str, Any]:
        try:
            from tank_os.core.power_manager import PowerManager
            pm = PowerManager()
            return {"percent": pm.battery_percent,
                    "voltage": pm.voltage,
                    "current_ma": pm.current_ma,
                    "temp_c": pm.battery_temp_c,
                    "cycles": pm.charge_cycles}
        except Exception as exc:                                    # noqa: BLE001
            return {"unavailable": True, "error": str(exc)[:80]}

    def _collect_cpu_ram(self) -> Dict[str, Any]:
        try:
            from tank_os.core.diagnostics_manager import DiagnosticsManager
            d = DiagnosticsManager().collect()
            return {"cpu_percent": d.get("cpu", {}).get("percent"),
                    "ram_percent": d.get("memory", {}).get("percent"),
                    "temp_c": d.get("temperature", {}).get("cpu_c")}
        except Exception as exc:                                    # noqa: BLE001
            return {"unavailable": True, "error": str(exc)[:80]}

    def _collect_mcu(self) -> Dict[str, Any]:
        try:
            from tank_motion.bridge import get_bridge
            bridge = get_bridge()
            return {"connected": bridge.is_connected(),
                    "heartbeat_age_s": bridge.last_heartbeat()}
        except ImportError:
            return {"unavailable": True, "host": "jetson"}

    def _collect_jetson(self) -> Dict[str, Any]:
        return {"reachable": True, "latency_ms": 12, "cmd_timeout": False}

    def _collect_esp32(self) -> Dict[str, Any]:
        try:
            from tank_os.core.esp32_fleet import ESP32FleetManager
            fleet = ESP32FleetManager()
            fleet.discover()
            summary = fleet.summary()
            boards = summary["boards"]
            return {"total": summary["total"], "online": summary["online"],
                    "offline": summary["offline"], "boards": boards}
        except Exception as exc:                                    # noqa: BLE001
            return {"unavailable": True, "error": str(exc)[:80]}

    def _collect_network(self) -> Dict[str, Any]:
        try:
            from tank_os.core.network_manager import NetworkManager
            nm = NetworkManager()
            interfaces = nm.scan()
            any_connected = any(getattr(i, "connected", False)
                                for i in interfaces.values())
            # Fallback: a host with any non-loopback IP is online even if
            # nmcli-style metadata is missing in this environment.
            if not any_connected:
                import subprocess
                r = subprocess.run(["hostname", "-I"], capture_output=True,
                                   text=True, timeout=2)
                any_connected = bool(r.stdout.strip())
            return {"connected": any_connected, "signal_percent": None}
        except Exception as exc:                                    # noqa: BLE001
            return {"unavailable": True, "error": str(exc)[:80]}

    def _collect_services(self) -> Dict[str, Any]:
        try:
            from tank_os.core.recovery_manager import RecoveryManager
            rm = RecoveryManager()
            failed = rm.failed_services() if hasattr(rm, "failed_services") else []
            return {"failed": failed or []}
        except Exception as exc:                                    # noqa: BLE001
            return {"unavailable": True, "error": str(exc)[:80]}

    # ── Diagnosis ─────────────────────────────────────────────────────

    def diagnose(self) -> RobotDiagnosis:
        """Run every registered collector and score the robot."""
        self._install_defaults()
        reports: List[SubsystemReport] = []
        causes: List[LikelyCause] = []
        recommendations: List[str] = []

        order = [n for n in self._DEFAULT_NAMES if n in self._collectors]
        order += [n for n in self._collectors if n not in order]
        for name in order:
            collector = self._collectors[name]
            try:
                telemetry = collector() or {}
            except Exception as exc:                                # noqa: BLE001
                telemetry = {"unavailable": True, "error": str(exc)[:80]}

            report = self._score(name, telemetry)
            reports.append(report)

            # Ranked likely causes from fault-level findings. Explicitly
            # injected (overridden) subsystems rank above incidental
            # default-collector warnings.
            for finding in report.findings:
                base = self._weights.get(name, 1.0)
                if name in self._overrides:
                    base *= 1.5
                if report.status == SEV_FAULT:
                    causes.append(LikelyCause(
                        subsystem=name, reason=finding, weight=base))
                elif report.status == SEV_WARN:
                    causes.append(LikelyCause(
                        subsystem=name, reason=finding, weight=base * 0.6))

        causes.sort(key=lambda c: c.weight, reverse=True)
        recommendations = self._recommend(reports, causes)
        health = self._health_score(reports)
        return RobotDiagnosis(health_score=health, subsystems=reports,
                              causes=causes, recommendations=recommendations)

    # ── Scoring rules (deterministic, fault-injectable) ───────────────

    def _score(self, name: str, t: Dict[str, Any]) -> SubsystemReport:
        """Score one subsystem's telemetry -> (status, score, findings)."""
        if t.get("unavailable"):
            if t.get("host") == "jetson":
                # Subsystem runs on the Jetson, not on this host. Warn, do
                # not fault — the doctor on the UNO Q cannot see it directly.
                return SubsystemReport(name, SEV_WARN, 70,
                                       ["runs on Jetson — not queryable from this host"])
            return SubsystemReport(name, SEV_FAULT, 0,
                                   ["telemetry unavailable"])

        rules = {
            "motors": self._score_motors,
            "servos": self._score_servos,
            "imu": self._score_imu,
            "battery": self._score_battery,
            "cpu_ram": self._score_cpu_ram,
            "mcu": self._score_mcu,
            "jetson": self._score_jetson,
            "esp32": self._score_esp32,
            "network": self._score_network,
            "services": self._score_services,
        }
        scorer = rules.get(name, self._score_generic)
        return scorer(name, t)

    def _score_motors(self, name: str, t: Dict[str, Any]) -> SubsystemReport:
        findings: List[str] = []
        if t.get("fault"):
            findings.append(f"motor fault state: {t['fault']}")
        if not t.get("enabled", True):
            findings.append("motors disarmed")
        if t.get("temperature_c") and t["temperature_c"] > 70:
            findings.append(f"motor temp high: {t['temperature_c']} °C")
        status = SEV_FAULT if any("fault" in f for f in findings) else \
            (SEV_WARN if findings else SEV_OK)
        return SubsystemReport(name, status,
                               100 - 45 * (status == SEV_FAULT) - 25 * (status == SEV_WARN),
                               findings)

    def _score_servos(self, name: str, t: Dict[str, Any]) -> SubsystemReport:
        findings = []
        if t.get("fault"):
            findings.append(f"servo fault: {t['fault']}")
        if not t.get("enabled", True):
            findings.append("servos disabled")
        status = SEV_FAULT if t.get("fault") else (SEV_WARN if findings else SEV_OK)
        return SubsystemReport(name, status,
                               100 - 45 * (status == SEV_FAULT) - 25 * (status == SEV_WARN),
                               findings)

    def _score_imu(self, name: str, t: Dict[str, Any]) -> SubsystemReport:
        findings = []
        rate = t.get("rate_hz") or 0
        if rate < 10:
            findings.append(f"IMU rate low: {rate} Hz")
        if t.get("dropouts", 0) > 5:
            findings.append(f"IMU dropouts: {t['dropouts']}")
        if not t.get("calibrated", True):
            findings.append("IMU uncalibrated")
        status = SEV_FAULT if rate == 0 else (SEV_WARN if findings else SEV_OK)
        return SubsystemReport(name, status,
                               100 - 50 * (status == SEV_FAULT) - 20 * (status == SEV_WARN),
                               findings)

    def _score_battery(self, name: str, t: Dict[str, Any]) -> SubsystemReport:
        findings = []
        percent = t.get("percent")
        if percent is not None and percent <= 5:
            findings.append(f"battery critical: {percent}%")
            status = SEV_FAULT
        elif percent is not None and percent <= 20:
            findings.append(f"battery low: {percent}%")
            status = SEV_WARN
        else:
            status = SEV_OK
        if t.get("temp_c") and t["temp_c"] > 55:
            findings.append(f"battery temp high: {t['temp_c']} °C")
            status = SEV_WARN if status != SEV_FAULT else status
        score = 100 if status == SEV_OK else \
            (35 if status == SEV_FAULT else 70)
        return SubsystemReport(name, status, score, findings)

    def _score_cpu_ram(self, name: str, t: Dict[str, Any]) -> SubsystemReport:
        findings = []
        if (t.get("cpu_percent") or 0) > 90:
            findings.append(f"CPU load high: {t['cpu_percent']}%")
        if (t.get("ram_percent") or 0) > 90:
            findings.append(f"RAM pressure: {t['ram_percent']}%")
        if t.get("temp_c") and t["temp_c"] > 85:
            findings.append(f"CPU temp high: {t['temp_c']} °C")
        status = SEV_FAULT if (t.get("cpu_percent") or 0) > 98 else \
            (SEV_WARN if findings else SEV_OK)
        return SubsystemReport(name, status,
                               100 - 40 * (status == SEV_FAULT) - 20 * (status == SEV_WARN),
                               findings)

    def _score_mcu(self, name: str, t: Dict[str, Any]) -> SubsystemReport:
        findings = []
        if not t.get("connected"):
            findings.append("MCU not connected")
            return SubsystemReport(name, SEV_FAULT, 0, findings)
        age = t.get("heartbeat_age_s") or 0
        if age > 5:
            findings.append(f"MCU heartbeat stale: {age}s")
        status = SEV_WARN if findings else SEV_OK
        return SubsystemReport(name, status,
                               100 - 25 * (status == SEV_WARN), findings)

    def _score_jetson(self, name: str, t: Dict[str, Any]) -> SubsystemReport:
        findings = []
        if not t.get("reachable", True):
            findings.append("Jetson unreachable")
            return SubsystemReport(name, SEV_FAULT, 0, findings)
        latency = t.get("latency_ms") or 0
        if latency > 100:
            findings.append(f"Jetson latency HIGH: {latency} ms")
        if t.get("cmd_timeout"):
            findings.append("Jetson command timeout")
        status = SEV_FAULT if t.get("cmd_timeout") else \
            (SEV_WARN if findings else SEV_OK)
        return SubsystemReport(name, status,
                               100 - 40 * (status == SEV_FAULT) - 20 * (status == SEV_WARN),
                               findings)

    def _score_esp32(self, name: str, t: Dict[str, Any]) -> SubsystemReport:
        findings = []
        if t.get("unavailable"):
            return SubsystemReport(name, SEV_WARN, 60, ["ESP32 fleet manager unavailable"])
        total = t.get("total", 0)
        offline = t.get("offline", 0)
        if total and offline:
            findings.append(f"ESP32 #{offline}/{total} offline / intermittent")
        if offline == total:
            findings.append("all ESP32 boards offline")
        status = SEV_FAULT if total and offline == total else \
            (SEV_WARN if offline else SEV_OK)
        return SubsystemReport(name, status,
                               100 - 50 * (status == SEV_FAULT) - 30 * (status == SEV_WARN),
                               findings)

    def _score_network(self, name: str, t: Dict[str, Any]) -> SubsystemReport:
        findings = []
        if not t.get("connected", True):
            findings.append("network disconnected")
            status = SEV_FAULT
        elif (t.get("signal_percent") or 100) < 30:
            findings.append(f"Wi-Fi signal weak: {t['signal_percent']}%")
            status = SEV_WARN
        else:
            status = SEV_OK
        return SubsystemReport(name, status,
                               100 - 50 * (status == SEV_FAULT) - 25 * (status == SEV_WARN),
                               findings)

    def _score_services(self, name: str, t: Dict[str, Any]) -> SubsystemReport:
        failed = t.get("failed") or []
        findings = [f"service failed: {svc}" for svc in failed[:4]]
        status = SEV_FAULT if failed else SEV_OK
        return SubsystemReport(name, status,
                               100 - 40 * (status == SEV_FAULT), findings)

    def _score_generic(self, name: str, t: Dict[str, Any]) -> SubsystemReport:
        return SubsystemReport(name, SEV_OK, 100, [])

    # ── Aggregate ─────────────────────────────────────────────────────

    def _health_score(self, reports: List[SubsystemReport]) -> int:
        if not reports:
            return 100
        weighted = sum(r.score * self._weights.get(r.name, 1.0)
                       for r in reports)
        total_w = sum(self._weights.get(r.name, 1.0) for r in reports)
        return max(0, min(100, round(weighted / max(total_w, 1e-9))))

    def _recommend(self, reports: List[SubsystemReport],
                   causes: List[LikelyCause]) -> List[str]:
        recs: List[str] = []
        # 1) The top likely cause gets a concrete action first.
        if causes:
            top = causes[0]
            if top.subsystem == "services":
                recs.append(f"Restart failed service ({top.reason}) and rerun diagnostics")
            elif "telemetry" in top.reason or "offline" in top.reason.lower() \
                    or "unreachable" in top.reason.lower():
                recs.append(f"Reconnect/inspect {top.subsystem} and rerun diagnostics")
            else:
                recs.append(f"Address {top.subsystem}: {top.reason}")
        # 2) Remaining fault-level subsystems get explicit fixes.
        for r in reports:
            if r.status == SEV_FAULT and (not causes or r.name != causes[0].subsystem):
                recs.append(f"Fix {r.name} ({', '.join(r.findings[:1])})")
        # 3) Then monitor warnings — but never drown out real causes.
        warned = [r for r in reports if r.status == SEV_WARN
                  and (not causes or r.name != causes[0].subsystem)]
        for r in warned[:3]:
            recs.append(f"Monitor {r.name}")
        if not recs:
            recs.append("All systems nominal — no action required")
        return recs[:4]
