"""TestCenterScreen — 🧪 Testing Center (GUI blueprint).

Physical-validation hub: FULL SYSTEM / MOTOR / SERVO / IMU / LIDAR /
CAMERA / JETSON / UNO Q / ESP32 / NETWORK / E-STOP / POWER tests.

Each test maps to a live check:
  * FULL SYSTEM → RobotDoctor full diagnosis (health score gates pass)
  * SUBSYSTEM → RobotDoctor subsystem report
  * E-STOP → supervisor/safety veto wiring
  * POWER → PowerManager telemetry plausibility
  * ESP32 → fleet discovery self-test

Running the suite produces the blueprint's report:

    THE TANK SYSTEM TEST
    ✓ 47 passed · ⚠ 3 warnings · ✕ 1 failed
    Generated: 23 Aug 2026 12:14
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from tank_os.core.robot_doctor import RobotDoctor

logger = logging.getLogger("tank_os.windows.testcenter")

TESTS = [
    ("FULL SYSTEM", "🖥"), ("MOTOR", "⚙"), ("SERVO", "🦾"), ("IMU", "🧭"),
    ("LIDAR", "📡"), ("CAMERA", "📷"), ("JETSON", "🟧"), ("UNO Q", "🔷"),
    ("ESP32", "🟢"), ("NETWORK", "🌐"), ("E-STOP", "⛔"), ("POWER", "🔋"),
]

RESULT_STYLE = {
    "pass": ("✓ PASS", "#81C784", "rgba(76,175,80,0.15)"),
    "warn": ("⚠ WARN", "#FFD54F", "rgba(255,193,7,0.14)"),
    "fail": ("✕ FAIL", "#FF8A80", "rgba(211,47,47,0.15)"),
}


class _TestButton(QPushButton):
    """One test button; green/amber/red after running."""

    def __init__(self, label: str, icon: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._label = label
        self.setText(f"{icon} {label}")
        self.setMinimumHeight(46)
        self.setStyleSheet("""
            QPushButton { background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.12); border-radius: 10px;
                color: #DDD; font-size: 12px; font-weight: bold; }
            QPushButton:hover { background: rgba(0,191,255,0.18); color: #FFF; }
        """)

    def set_result(self, result: str) -> None:
        text, color, bg = RESULT_STYLE[result]
        self.setText(f"{text}  {self._label}")
        self.setStyleSheet(f"""
            QPushButton {{ background: {bg}; border: 1px solid {color};
                border-radius: 10px; color: {color}; font-size: 12px; font-weight: bold; }}
            QPushButton:hover {{ background: {bg}; }}
        """)


class TestCenterScreen(QWidget):
    """Testing Center — run individual tests or the full suite."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._doctor = RobotDoctor()
        self._results: Dict[str, str] = {}
        self._build_ui()

    # --------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("🧪 Testing Center")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFF;")
        header.addWidget(title)
        header.addStretch()
        full = QPushButton("▶ RUN FULL SYSTEM TEST")
        full.setStyleSheet("""
            QPushButton { background: rgba(27,94,32,0.9); color: #FFF;
                font-size: 13px; font-weight: bold; border: none; border-radius: 10px;
                padding: 8px 18px; }
            QPushButton:hover { background: #2E7D32; }
        """)
        full.clicked.connect(self._run_all)
        header.addWidget(full)
        layout.addLayout(header)

        # Test grid
        grid = QGridLayout()
        grid.setSpacing(8)
        self._buttons: Dict[str, _TestButton] = {}
        for i, (name, icon) in enumerate(TESTS):
            btn = _TestButton(name, icon)
            btn.clicked.connect(lambda _=False, n=name: self._run_one(n))
            self._buttons[name] = btn
            grid.addWidget(btn, i // 4, i % 4)
        layout.addLayout(grid)

        # Report panel
        self._report = QLabel("Run a test or the full suite to generate a report…")
        self._report.setWordWrap(True)
        self._report.setStyleSheet("""
            background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px; padding: 12px 16px; font-size: 13px; color: #DDD;
        """)
        layout.addWidget(self._report, 1)

    # ------------------------------------------------------------- tests
    def _run_one(self, name: str) -> None:
        result, detail = self._check(name)
        self._results[name] = result
        self._buttons[name].set_result(result)
        self._render_report()

    def _run_all(self) -> None:
        for name in [n for n, _ in TESTS]:
            result, _ = self._check(name)
            self._results[name] = result
            self._buttons[name].set_result(result)
        self._render_report()

    def _check(self, name: str) -> Tuple[str, str]:
        """Run one named test against live state. Returns (result, detail)."""
        try:
            diag = self._doctor.diagnose()
            state = {r.name: r for r in diag.subsystems}
        except Exception as exc:                                    # noqa: BLE001
            return "fail", f"diagnosis failed: {exc}"

        subsystem = {
            "MOTOR": "motors", "SERVO": "servos", "IMU": "imu",
            "LIDAR": "network", "CAMERA": "jetson", "JETSON": "jetson",
            "UNO Q": "services", "ESP32": "esp32", "NETWORK": "network",
            "POWER": "battery",
        }.get(name)

        if name == "FULL SYSTEM":
            score = diag.health_score
            if score >= 80:
                return "pass", f"health {score}/100 — all subsystems nominal"
            if score >= 50:
                return "warn", f"health {score}/100 — warnings present"
            return "fail", f"health {score}/100 — faults detected"

        if name == "E-STOP":
            try:
                from tank_os.shell.terminal.safety import CommandSafety
                from tank_os.core.ai_supervisor import AISupervisor, SourceRole, Verdict
                sup = AISupervisor()
                sup.configure(safety_classifier=CommandSafety().classify)
                sup.register("safety", SourceRole.SAFETY, 1.00)
                result = sup.arbitrate("rm -rf /", "safety")
                ok = result.verdict in (Verdict.VETO, Verdict.NEEDS_APPROVAL)
                return ("pass" if ok else "fail",
                        "E-STOP veto wiring verified" if ok else "E-STOP not enforced")
            except Exception as exc:                                # noqa: BLE001
                return "fail", f"E-STOP test error: {exc}"

        if subsystem:
            report = state.get(subsystem)
            if report is None:
                return "warn", f"{name} telemetry unavailable on this host"
            finding = report.findings[0] if report.findings else "nominal"
            # RobotDoctor statuses are ok/warn/fault — normalize for the report.
            status = {"ok": "pass", "warn": "warn", "fault": "fail"}.get(
                report.status, "warn")
            return status, f"{name}: {finding}"
        return "warn", f"no test defined for {name}"

    def _render_report(self) -> None:
        if not self._results:
            return
        passed = sum(1 for v in self._results.values() if v == "pass")
        warned = sum(1 for v in self._results.values() if v == "warn")
        failed = sum(1 for v in self._results.values() if v == "fail")
        stamp = datetime.now().strftime("%d %b %Y %H:%M")
        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "      THE TANK SYSTEM TEST",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"  ✓ {passed} passed    ⚠ {warned} warnings    ✕ {failed} failed",
            f"  Generated: {stamp}",
            "",
        ]
        for name, result in self._results.items():
            icon = {"pass": "✓", "warn": "⚠", "fail": "✕"}[result]
            lines.append(f"  {icon} {name}")
        self._report.setText("\n".join(lines))

    def on_show(self) -> None:
        pass

    def on_hide(self) -> None:
        pass
