"""NetworkScreen — 📡 Network (GUI blueprint).

Dedicated network screen: Wi-Fi / Ethernet / LTE interface status, current
IP, Tailscale nodes, and fleet connectivity (Jetson, VPS, ESP32) — pulled
from NetworkManager + the fleet docs' live IPs.
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget,
)

from tank_os.core.network_manager import NetworkManager

logger = logging.getLogger("tank_os.windows.network")

FLEET_NODES = [
    ("unoq", "UNO Q", "100.71.127.19", "this board"),
    ("jetson", "JETSON", "100.122.31.46", "tank brain"),
    ("vps", "VPS", "medicscholar.medigyaan.com", "cloud services"),
    ("cam", "ESP32-S3 CAM", "192.168.31.145", "ESPHome camera"),
]


class _IfaceCard(QFrame):
    """One network interface."""

    def __init__(self, name: str, icon: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("netCard")
        self.setStyleSheet("""
            #netCard { background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; }
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(4)
        head = QHBoxLayout()
        ic = QLabel(icon)
        ic.setStyleSheet("font-size: 20px; background: transparent;")
        head.addWidget(ic)
        n = QLabel(name)
        n.setStyleSheet("font-size: 13px; font-weight: bold; color: #FFF;"
                        " background: transparent;")
        head.addWidget(n)
        head.addStretch()
        self._state = QLabel("—")
        self._state.setStyleSheet("font-size: 10px; font-weight: bold;")
        head.addWidget(self._state)
        lay.addLayout(head)
        self._ip = QLabel("—")
        self._ip.setStyleSheet("font-size: 16px; font-weight: bold; color: #80D8FF;"
                               " background: transparent;")
        lay.addWidget(self._ip)
        self._extra = QLabel("")
        self._extra.setStyleSheet("font-size: 10px; color: #9AA; background: transparent;")
        lay.addWidget(self._extra)

    def set_state(self, connected: bool, ip: str, extra: str = "") -> None:
        color = "#81C784" if connected else "#FF8A80"
        bg = "rgba(76,175,80,0.12)" if connected else "rgba(211,47,47,0.12)"
        self._state.setText("● ONLINE" if connected else "○ OFFLINE")
        self._state.setStyleSheet(f"font-size: 10px; font-weight: bold; color: {color};"
                                  f" background: transparent;")
        self.setStyleSheet(f"""
            #netCard {{ background: {bg};
                border: 1px solid {color}; border-radius: 12px; }}
        """)
        self._ip.setText(ip or "no address")
        self._extra.setText(extra)


class NetworkScreen(QWidget):
    """Network dashboard."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._nm = NetworkManager()
        self._build_ui()
        self.refresh()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(4000)

    # --------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("📡 Network")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFF;")
        header.addWidget(title)
        header.addStretch()
        self._online = QLabel("—")
        self._online.setStyleSheet("""
            background: rgba(76,175,80,0.15); border: 1px solid #4CAF50;
            border-radius: 10px; padding: 6px 14px; font-size: 11px; font-weight: bold;
            color: #A5D6A7;
        """)
        header.addWidget(self._online)
        layout.addLayout(header)

        # Interfaces
        ifaces = QGridLayout()
        ifaces.setSpacing(10)
        self._cards = {}
        for i, (name, icon) in enumerate([("WIFI", "📶"), ("ETHERNET", "🔌"),
                                          ("LTE", "📱"), ("TAILSCALE", "🛰")]):
            card = _IfaceCard(name, icon)
            self._cards[name] = card
            ifaces.addWidget(card, i // 2, i % 2)
        layout.addLayout(ifaces)

        # Fleet connectivity
        fleet_label = QLabel("FLEET CONNECTIVITY")
        fleet_label.setStyleSheet("font-size: 10px; color: #888; font-weight: bold;")
        layout.addWidget(fleet_label)

        fleet_grid = QGridLayout()
        fleet_grid.setSpacing(8)
        self._fleet: dict = {}
        for i, (_id, name, addr, note) in enumerate(FLEET_NODES):
            frame = QFrame()
            frame.setObjectName("fleetNode")
            frame.setStyleSheet("""
                #fleetNode { background: rgba(255,255,255,0.04);
                    border: 1px solid rgba(255,255,255,0.1); border-radius: 10px; }
            """)
            lay = QHBoxLayout(frame)
            lay.setContentsMargins(12, 8, 12, 8)
            n = QLabel(f"{name}")
            n.setStyleSheet("font-size: 11px; font-weight: bold; color: #FFF;"
                            " background: transparent;")
            lay.addWidget(n)
            a = QLabel(addr)
            a.setStyleSheet("font-size: 10px; color: #9AA; background: transparent;")
            lay.addWidget(a)
            lay.addStretch()
            st = QLabel("…")
            st.setStyleSheet("font-size: 10px; font-weight: bold;")
            lay.addWidget(st)
            self._fleet[_id] = (frame, st, addr)
            fleet_grid.addWidget(frame, i // 2, i % 2)
        layout.addLayout(fleet_grid, 1)

    # ------------------------------------------------------------- data
    def refresh(self) -> None:
        try:
            self._nm.scan()
            interfaces = self._nm._interfaces
            wifi = interfaces.get("wifi")
            eth = interfaces.get("eth")
            lte = interfaces.get("lte")
            self._cards["WIFI"].set_state(
                bool(wifi and wifi.connected), wifi.ip if wifi else "",
                f"{wifi.ssid} · {wifi.signal}%" if wifi and wifi.ssid else "")
            self._cards["ETHERNET"].set_state(
                bool(eth and eth.connected), eth.ip if eth else "")
            self._cards["LTE"].set_state(
                bool(lte and lte.connected), lte.ip if lte else "")
            self._cards["TAILSCALE"].set_state(
                True, "100.x", "tailscale up" if self._nm.is_online() else "")
            self._online.setText("● ONLINE" if self._nm.is_online() else "○ OFFLINE")
        except Exception as exc:                                    # noqa: BLE001
            logger.debug("network refresh failed: %s", exc)

        # Fleet nodes — best-effort ping via TCP connect to :22
        for _id, (frame, st, addr) in self._fleet.items():
            reachable = self._ping(addr)
            color = "#81C784" if reachable else "#FF8A80"
            st.setText("●" if reachable else "○")
            st.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {color};"
                             f" background: transparent;")

    def _ping(self, addr: str) -> bool:
        import socket
        host = addr.split(":")[0]
        try:
            with socket.create_connection((host, 22), timeout=1.0):
                return True
        except Exception:                                           # noqa: BLE001
            return False

    def on_show(self) -> None:
        self.refresh()
        self._timer.start(4000)

    def on_hide(self) -> None:
        self._timer.stop()
