"""
auto_dock.py - Autonomous Docking Integration
Combines AprilTag detection + Magnetic charging dock + Navigation
Full pipeline: Detect dock tag → Navigate → Align → Dock → Charge
"""
import time
import logging
import json
import threading
from datetime import datetime

logger = logging.getLogger("tank.auto_dock")


class AutoDock:
    """Full autonomous docking pipeline"""

    def __init__(self, apriltag=None, navigator=None, dock_controller=None, serial_bridge=None):
        self.apriltag = apriltag
        self.navigator = navigator
        self.dock = dock_controller
        self.serial = serial_bridge

        self.state = "idle"
        self.battery_level = 100
        self.low_battery_threshold = 20
        self.auto_dock_enabled = True
        self.auto_dock_thread = None
        self._running = False
        self._events = []

    def start_monitoring(self):
        """Start continuous battery monitoring — auto-docks when low"""
        self._running = True
        self.auto_dock_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.auto_dock_thread.start()
        logger.info("Auto-dock monitoring started")

    def _monitor_loop(self):
        """Check battery and auto-dock when needed"""
        while self._running:
            time.sleep(30)

            if not self.auto_dock_enabled:
                continue

            # Check battery
            self._read_battery()

            if self.battery_level <= self.low_battery_threshold and self.state == "idle":
                self._log_event("low_battery", f"Battery at {self.battery_level}% — initiating auto-dock")
                self.auto_dock()

            # If charging, check if full
            if self.state == "charging" and self.battery_level >= 95:
                self._log_event("charge_complete", f"Battery at {self.battery_level}% — undocking")
                self.undock()

    def auto_dock(self):
        """Full auto-dock sequence: search → approach → align → dock → charge"""
        if self.state != "idle":
            return False

        self.state = "docking_sequence"
        self._log_event("dock_start", "Auto-dock sequence initiated")

        # Step 1: Navigate towards dock area
        if self.navigator:
            self.navigator.return_home()

            # Wait for arrival or timeout
            start = time.time()
            while time.time() - start < 60:
                if self.navigator.mode in ["idle", "docking"]:
                    break
                time.sleep(1)

        # Step 2: Detect dock tags with AprilTag
        if self.apriltag:
            dock_tags = self.apriltag.get_dock_tags()
            if not dock_tags:
                # Search for dock
                self._log_event("dock_search", "Searching for dock tags...")
                for _ in range(20):
                    if self.serial:
                        self.serial.send_command("MOTOR 15 -15")  # Slow rotate
                    time.sleep(0.5)
                    dock_tags = self.apriltag.get_dock_tags()
                    if dock_tags:
                        break
                if self.serial:
                    self.serial.send_command("MOTOR 0 0")

            if dock_tags:
                self._log_event("dock_found", f"Found dock tag {dock_tags[0]['name']}")
            else:
                self._log_event("dock_not_found", "Dock tags not visible — using return-home")
                self.state = "idle"
                return False

        # Step 3: Engage dock
        if self.dock:
            self.dock.start_docking()
            # Wait for dock state
            start = time.time()
            while time.time() - start < 60:
                if self.dock.state == "charging":
                    self.state = "charging"
                    self._log_event("charging", f"Charging started at {self.battery_level}%")
                    return True
                elif self.dock.state == "error":
                    self._log_event("dock_error", "Docking failed")
                    self.state = "idle"
                    return False
                time.sleep(1)

        self.state = "idle"
        return False

    def undock(self):
        """Undock from charger"""
        self._log_event("undock", "Undocking")
        if self.serial:
            # Reverse to disengage magnetic connector
            self.serial.send_command("MOTOR -30 -30")
            time.sleep(2)
            self.serial.send_command("MOTOR 0 0")
        if self.dock:
            self.dock.stop_docking()
        self.state = "idle"

    def manual_dock(self):
        """Manually trigger docking"""
        return self.auto_dock()

    def manual_undock(self):
        """Manually undock"""
        self.undock()

    def _read_battery(self):
        """Read battery level from INA219 via UNO Q"""
        try:
            if self.serial:
                resp = self.serial.send_command("POWER")
                if resp:
                    data = json.loads(resp)
                    self.battery_level = data.get("battery_pct", self.battery_level)
        except:
            pass

    def _log_event(self, event_type, message):
        event = {
            "type": event_type,
            "message": message,
            "battery": self.battery_level,
            "time": datetime.now().isoformat(),
        }
        self._events.append(event)
        if len(self._events) > 200:
            self._events = self._events[-200:]
        logger.info(f"[{event_type}] {message} (battery: {self.battery_level}%)")

    def get_status(self):
        return {
            "state": self.state,
            "battery_pct": self.battery_level,
            "auto_dock_enabled": self.auto_dock_enabled,
            "low_battery_threshold": self.low_battery_threshold,
            "apriltag_status": self.apriltag.get_status() if self.apriltag else None,
            "dock_status": self.dock.get_status() if self.dock else None,
            "nav_status": self.navigator.get_status() if self.navigator else None,
            "recent_events": self._events[-10:],
        }
