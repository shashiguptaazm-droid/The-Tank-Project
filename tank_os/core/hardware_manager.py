"""
TankOS Hardware Manager — detects, monitors, and reconnects hardware.

Detects displays, USB devices, serial devices, cameras, ESP32, sensors,
storage, and battery. Emits events on connection/disconnection changes.
"""
from __future__ import annotations

import glob
import logging
import os
import re
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from tank_os.core.event_bus import Event, EventBus

logger = logging.getLogger("tank_os.hardware_manager")


@dataclass
class HardwareDevice:
    """Describes a detected hardware device."""
    name: str
    device_type: str  # camera, serial, display, audio, storage, etc.
    path: str = ""
    connected: bool = True
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class HardwareManager:
    """Singleton that probes and monitors hardware."""

    _instance: Optional["HardwareManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "HardwareManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._devices: Dict[str, HardwareDevice] = {}
                cls._instance._poll_thread: Optional[threading.Thread] = None
                cls._instance._running = False
                cls._instance._bus = EventBus()
            return cls._instance

    def initialize(self) -> None:
        """Run initial hardware scan."""
        self._scan_all()
        self._start_monitoring()
        self._bus.emit(Event("hardware_initialized", {
            "devices": [d.name for d in self._devices.values()],
        }, source="hardware_manager"))

    def _scan_all(self) -> None:
        """Detect all known hardware types."""
        self._detect_cameras()
        self._detect_serial()
        self._detect_displays()
        self._detect_audio()
        self._detect_storage()
        self._detect_network()

    def _detect_cameras(self) -> None:
        for dev in glob.glob("/dev/video*"):
            self._devices[f"camera:{dev}"] = HardwareDevice(
                name=f"Camera {dev}",
                device_type="camera",
                path=dev,
                connected=os.path.exists(dev),
            )
        # Pi Camera
        try:
            result = subprocess.run(
                ["libcamera-hello", "--list-cameras"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                self._devices["camera:libcamera"] = HardwareDevice(
                    name="Pi Camera (libcamera)",
                    device_type="camera",
                    path="libcamera",
                    connected=True,
                )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    def _detect_serial(self) -> None:
        for dev in glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyAMA*"):
            desc = "USB Serial" if "USB" in dev.upper() or "ACM" in dev.upper() else "UART"
            self._devices[f"serial:{dev}"] = HardwareDevice(
                name=f"{desc} {dev}",
                device_type="serial",
                path=dev,
                connected=os.path.exists(dev),
            )
        # ESP32 detection via lsusb
        try:
            result = subprocess.run(
                ["lsusb"], capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                if "0403" in line or "FTDI" in line.upper() or "CP2102" in line.upper() or "ESP32" in line.upper():
                    self._devices[f"usb:{line[:10].strip()}"] = HardwareDevice(
                        name=f"USB Device: {line.strip()}",
                        device_type="serial",
                        path=line.split()[-1] if len(line.split()) > 5 else "",
                        connected=True,
                        description=line.strip(),
                    )
        except FileNotFoundError:
            pass

    def _detect_displays(self) -> None:
        # DSI display
        dsi_path = Path("/sys/class/drm")
        if dsi_path.exists():
            displays = list(dsi_path.glob("card*-DSI*"))
            for d in displays:
                self._devices[f"display:{d.name}"] = HardwareDevice(
                    name=f"DSI Display ({d.name})",
                    device_type="display",
                    path=str(d),
                    connected=True,
                )
        # HDMI
        try:
            result = subprocess.run(
                ["tvservice", "--status"], capture_output=True, text=True, timeout=5
            )
            if "HDMI" in result.stdout:
                self._devices["display:hdmi"] = HardwareDevice(
                    name="HDMI Display",
                    device_type="display",
                    connected=True,
                )
        except FileNotFoundError:
            pass

    def _detect_audio(self) -> None:
        try:
            result = subprocess.run(
                ["aplay", "-l"], capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                if "card" in line.lower():
                    self._devices[f"audio:output:{id(line)}"] = HardwareDevice(
                        name=f"Audio Output: {line.strip()}",
                        device_type="audio",
                        connected=True,
                        description=line.strip(),
                    )
        except FileNotFoundError:
            pass

    def _detect_storage(self) -> None:
        try:
            result = subprocess.run(
                ["df", "-h"], capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                if "/dev/" in line and "boot" not in line.lower():
                    parts = line.split()
                    if len(parts) >= 6:
                        self._devices[f"storage:{parts[0]}"] = HardwareDevice(
                            name=f"Storage: {parts[0]}",
                            device_type="storage",
                            path=parts[0],
                            connected=True,
                            description=f"{parts[1]} total, {parts[2]} used, {parts[3]} free",
                            metadata={
                                "size": parts[1],
                                "used": parts[2],
                                "available": parts[3],
                                "mount": parts[5],
                            },
                        )
        except FileNotFoundError:
            pass

    def _detect_network(self) -> None:
        try:
            result = subprocess.run(
                ["iwconfig", "2>/dev/null"], capture_output=True, text=True, timeout=5, shell=True
            )
            for line in result.stdout.splitlines():
                if "ESSID:" in line:
                    ssid = re.search(r'ESSID:"([^"]+)"', line)
                    if ssid:
                        self._devices["network:wifi"] = HardwareDevice(
                            name=f"WiFi: {ssid.group(1)}",
                            device_type="network",
                            connected=True,
                            metadata={"ssid": ssid.group(1)},
                        )
        except FileNotFoundError:
            pass
        # Check LTE modem
        for dev in glob.glob("/dev/ttyUSB*") + glob.glob("/dev/cdc-wdm*"):
            self._devices[f"network:lte:{dev}"] = HardwareDevice(
                name=f"LTE Modem ({dev})",
                device_type="network",
                path=dev,
                connected=True,
            )

    def _start_monitoring(self) -> None:
        """Start background polling for hardware changes."""
        if self._poll_thread and self._poll_thread.is_alive():
            return
        self._running = True
        self._poll_thread = threading.Thread(
            target=self._monitor_loop, daemon=True,
            name="tank_os_hw_monitor"
        )
        self._poll_thread.start()

    def _monitor_loop(self) -> None:
        """Poll hardware every 5 seconds for changes."""
        while self._running:
            before = {n: d.connected for n, d in self._devices.items()}
            self._scan_all()
            after = {n: d.connected for n, d in self._devices.items()}
            for name in after:
                if name not in before:
                    self._bus.emit(Event("hardware_connected", {
                        "name": name,
                        "device": after[name],
                    }, source="hardware_manager"))
                elif before[name] != after[name]:
                    if after[name]:
                        self._bus.emit(Event("hardware_reconnected", {
                            "name": name,
                        }, source="hardware_manager"))
            for name in before:
                if name not in after:
                    self._bus.emit(Event("hardware_disconnected", {
                        "name": name,
                    }, source="hardware_manager"))
            time.sleep(5.0)

    def stop_monitoring(self) -> None:
        self._running = False

    def get_device(self, name: str) -> Optional[HardwareDevice]:
        return self._devices.get(name)

    def get_devices(self, device_type: Optional[str] = None) -> List[HardwareDevice]:
        if device_type:
            return [d for d in self._devices.values() if d.device_type == device_type]
        return list(self._devices.values())

    def device_types(self) -> List[str]:
        return sorted(set(d.device_type for d in self._devices.values()))

    def count(self) -> int:
        return len(self._devices)
