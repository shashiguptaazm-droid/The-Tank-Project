"""TankOS Network Manager — Wi-Fi, Ethernet, LTE, Bluetooth, VPN, hotspot mode."""

from __future__ import annotations
import logging, subprocess, threading, re, time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from tank_os.core.event_bus import Event, EventBus


@dataclass
class NetworkInfo:
    ssid: str = ""; signal: int = 0; ip: str = ""
    interface: str = ""; connected: bool = False; type: str = "wifi"


class NetworkManager:
    _instance: Optional["NetworkManager"] = None; _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._bus = EventBus()
                cls._instance._interfaces: Dict[str, NetworkInfo] = {}
            return cls._instance

    def initialize(self) -> None:
        self.scan()
        logger.info("NetworkManager initialized")

    def scan(self) -> Dict[str, NetworkInfo]:
        self._interfaces["wifi"] = self._scan_wifi()
        self._interfaces["eth"] = self._scan_eth()
        self._interfaces["lte"] = self._scan_lte()
        return dict(self._interfaces)

    def _scan_wifi(self) -> NetworkInfo:
        info = NetworkInfo(type="wifi")
        try:
            r = subprocess.run(["iwgetid"], capture_output=True, text=True, timeout=3)
            if r.stdout.strip():
                m = re.search(r'ESSID:"([^"]+)"', r.stdout)
                if m: info.ssid = m.group(1); info.connected = True
            r2 = subprocess.run(["hostname", "-I"], capture_output=True, text=True, timeout=2)
            ips = r2.stdout.strip().split()
            if ips: info.ip = ips[0]
        except Exception: pass
        return info

    def _scan_eth(self) -> NetworkInfo:
        info = NetworkInfo(type="ethernet")
        try:
            r = subprocess.run(["cat", "/sys/class/net/eth0/operstate"],
                             capture_output=True, text=True, timeout=2)
            info.connected = r.stdout.strip() == "up"
        except Exception: pass
        return info

    def _scan_lte(self) -> NetworkInfo:
        info = NetworkInfo(type="lte")
        try:
            for dev_path in ["/dev/ttyUSB2", "/dev/cdc-wdm0"]:
                import os.path
                if os.path.exists(dev_path):
                    info.connected = True
                    break
        except Exception: pass
        return info

    def connect_wifi(self, ssid: str, password: str) -> bool:
        try:
            subprocess.run(["nmcli", "device", "wifi", "connect", ssid,
                          "password", password], capture_output=True, timeout=15)
            self._bus.emit(Event("wifi_connected", {"ssid": ssid}))
            return True
        except Exception: return False

    @property
    def current_ip(self) -> str:
        for info in self._interfaces.values():
            if info.ip: return info.ip
        return ""

    @property
    def is_online(self) -> bool:
        return any(i.connected for i in self._interfaces.values())
