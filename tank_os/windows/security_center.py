"""SecurityCenterScreen — 🔐 Security Center (GUI blueprint).

Shows SSH sessions, connected devices, Tailscale nodes, failed logins, API
requests, suspicious commands and authentication state — derived from the
live SecurityManager + system queries + EventBus history.
"""

from __future__ import annotations

import logging
import subprocess
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget,
)

from tank_os.core.event_bus import EventBus
from tank_os.core.security_manager import SecurityManager

logger = logging.getLogger("tank_os.windows.security")


class _Row(QFrame):
    """A labeled value row."""

    def __init__(self, label: str, icon: str, value: str = "—",
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("secRow")
        self.setStyleSheet("""
            #secRow { background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.1); border-radius: 10px; }
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        ic = QLabel(icon)
        ic.setStyleSheet("font-size: 16px; background: transparent;")
        lay.addWidget(ic)
        lbl = QLabel(label)
        lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #CCC;"
                          " background: transparent;")
        lay.addWidget(lbl)
        lay.addStretch()
        self._value = QLabel(value)
        self._value.setStyleSheet("font-size: 12px; color: #FFF; background: transparent;")
        lay.addWidget(self._value)

    def set_value(self, value: str) -> None:
        self._value.setText(value)


class SecurityCenterScreen(QWidget):
    """Security center — sessions, devices, logins, API, commands."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._sec = SecurityManager()
        self._bus = EventBus()
        self._build_ui()
        self.refresh()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(5000)

    # --------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("🔐 Security Center")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFF;")
        header.addWidget(title)
        header.addStretch()
        self._auth = QLabel("—")
        self._auth.setStyleSheet("""
            background: rgba(76,175,80,0.15); border: 1px solid #4CAF50;
            border-radius: 10px; padding: 6px 14px; font-size: 11px; font-weight: bold;
            color: #A5D6A7;
        """)
        header.addWidget(self._auth)
        layout.addLayout(header)

        grid = QGridLayout()
        grid.setSpacing(10)
        self._rows = {}
        specs = [
            ("SSH SESSIONS", "🔌"), ("CONNECTED DEVICES", "🖧"),
            ("TAILSCALE NODES", "🛰"), ("FAILED LOGINS", "🚫"),
            ("API REQUESTS", "🌐"), ("SUSPICIOUS COMMANDS", "⚠"),
        ]
        for i, (label, icon) in enumerate(specs):
            row = _Row(label, icon)
            self._rows[label] = row
            grid.addWidget(row, i // 2, i % 2)
        layout.addLayout(grid)

        # Status line
        self._status = QLabel("")
        self._status.setWordWrap(True)
        self._status.setStyleSheet("""
            background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08);
            border-radius: 10px; padding: 10px 14px; font-size: 11px; color: #9AA;
        """)
        layout.addWidget(self._status, 1)

    # ------------------------------------------------------------- data
    def refresh(self) -> None:
        # Auth state
        authed = self._sec.is_authenticated
        estop = self._sec.is_estop
        self._auth.setText(
            f"{'🔓 AUTHENTICATED' if authed else '🔒 LOCKED'}"
            + (" · ⛔ E-STOP" if estop else ""))
        color = "#81C784" if authed else "#FFD54F"
        self._auth.setStyleSheet(f"""
            background: rgba(76,175,80,0.12); border: 1px solid {color};
            border-radius: 10px; padding: 6px 14px; font-size: 11px; font-weight: bold;
            color: {color};
        """)

        # SSH sessions
        ssh = self._count_ssh()
        self._rows["SSH SESSIONS"].set_value(str(ssh))

        # Connected devices via USB scan
        try:
            from tank_os.core.usb_detector import list_usb_devices
            devs = list_usb_devices()
            real = sum(1 for d in devs if not d.is_root_hub)
            self._rows["CONNECTED DEVICES"].set_value(f"{real} USB")
        except Exception:                                           # noqa: BLE001
            pass

        # Tailscale nodes
        try:
            r = subprocess.run(["tailscale", "status"], capture_output=True,
                               text=True, timeout=4)
            nodes = len([l for l in r.stdout.splitlines() if l.strip()]) if r.stdout else 0
            self._rows["TAILSCALE NODES"].set_value(str(nodes))
        except Exception:                                           # noqa: BLE001
            self._rows["TAILSCALE NODES"].set_value("—")

        # Failed logins from auth log
        failed = self._count_failed_logins()
        self._rows["FAILED LOGINS"].set_value(str(failed))

        # API requests — recent event-bus volume
        try:
            hist = self._bus.history(limit=200)
            self._rows["API REQUESTS"].set_value(f"{len(hist)} events")
        except Exception:                                           # noqa: BLE001
            pass

        # Suspicious commands — safety-blocked probe count from history
        suspicious = self._count_suspicious()
        self._rows["SUSPICIOUS COMMANDS"].set_value(str(suspicious))

        self._status.setText(
            f"Surveillance: {'● ON' if self._sec.is_surveillance_active else '○ OFF'} · "
            f"E-STOP: {'LATCHED' if estop else 'clear'} · "
            f"Auth: {'token-gated' if not authed else 'unlocked'} · "
            f"Policy: AI can recommend, safety can veto")

    def _count_ssh(self) -> int:
        try:
            r = subprocess.run(["who"], capture_output=True, text=True, timeout=3)
            return len([l for l in r.stdout.splitlines() if l.strip()])
        except Exception:                                           # noqa: BLE001
            return 0

    def _count_failed_logins(self) -> int:
        try:
            r = subprocess.run(
                ["bash", "-c",
                 "grep -c 'Failed password' /var/log/auth.log 2>/dev/null || echo 0"],
                capture_output=True, text=True, timeout=4)
            return int(r.stdout.strip() or 0)
        except Exception:                                           # noqa: BLE001
            return 0

    def _count_suspicious(self) -> int:
        count = 0
        try:
            for evt in self._bus.history(limit=500):
                t = evt.type.lower()
                if any(k in t for k in ("estop", "blocked", "reject", "veto")):
                    count += 1
        except Exception:                                           # noqa: BLE001
            pass
        return count

    def on_show(self) -> None:
        self.refresh()
        self._timer.start(5000)

    def on_hide(self) -> None:
        self._timer.stop()
