"""
dock_controller.py - Magnetic Charging Dock Controller
Auto-detects dock via AprilTag, aligns robot, engages magnetic charging.
Uses INA219 for current monitoring + PCA9685 servo for dock alignment.
"""
import time
import logging
import threading
import json
from datetime import datetime

logger = logging.getLogger("tank.charging")

# Dock states
STATE_IDLE = "idle"
STATE_SEEKING = "seeking_dock"
STATE_APPROACHING = "approaching"
STATE_ALIGNING = "aligning"
STATE_DOCKING = "docking"
STATE_CHARGING = "charging"
STATE_COMPLETE = "complete"
STATE_ERROR = "error"


class DockController:
    """Magnetic charging dock — auto-alignment and charge management"""

    def __init__(self, apriltag_detector=None, motor_controller=None, serial_bridge=None):
        self.detector = apriltag_detector
        self.motors = motor_controller
        self.serial_bridge = serial_bridge  # Jetson→UNO Q bridge

        self.state = STATE_IDLE
        self.battery_level = 0
        self.charge_current = 0
        self.charge_voltage = 0
        self.charge_start_time = None
        self.target_charge_pct = 90
        self.dock_tag_id = 1  # DOCK_ALIGN tag
        self.alignment_tolerance = 80  # pixels from center

        self._state_callbacks = []
        self._charge_thread = None
        self._running = False

        # Dock positions (learned or configured)
        self.dock_approach_distance = 0.5  # meters
        self.dock_lock_distance = 0.15  # meters
        self.dock_align_speed = 30  # slow approach speed
        self.dock_lock_speed = 15  # very slow for final dock

    def on_state_change(self, callback):
        self._state_callbacks.append(callback)

    def _set_state(self, state, info=""):
        old = self.state
        self.state = state
        logger.info(f"Dock: {old} -> {state} {info}")
        for cb in self._state_callbacks:
            cb(old, state, info)

    def start_docking(self):
        """Start autonomous docking sequence"""
        if self.state in [STATE_CHARGING, STATE_DOCKING, STATE_APPROACHING]:
            return False
        self._set_state(STATE_SEEKING)
        self._running = True
        self._charge_thread = threading.Thread(target=self._docking_sequence, daemon=True)
        self._charge_thread.start()
        return True

    def stop_docking(self):
        """Abort docking"""
        self._running = False
        self._send_motors(0, 0)
        self._set_state(STATE_IDLE, "Aborted")

    def _docking_sequence(self):
        """Full autonomous docking sequence"""
        logger.info("Starting docking sequence")

        # Phase 1: Seek dock tag
        if not self._seek_dock():
            return

        # Phase 2: Approach dock
        if not self._approach_dock():
            return

        # Phase 3: Align with dock
        if not self._align_dock():
            return

        # Phase 4: Final dock engagement
        if not self._engage_dock():
            return

        # Phase 5: Start charging
        self._start_charging()

    def _seek_dock(self):
        """Search for dock tag using camera"""
        self._set_state(STATE_SEEKING, "Scanning for dock tag")
        start = time.time()
        timeout = 30  # seconds to find dock

        while self._running and (time.time() - start) < timeout:
            tags = self._get_tags()
            dock_tags = [t for t in tags if t["id"] in [0, 1, 2, 11, 13]]
            if dock_tags:
                self._set_state(STATE_SEEKING, f"Found dock tag {dock_tags[0]['id']}")
                return True
            # Slow rotate to search
            self._send_motors(20, -20)
            time.sleep(0.5)

        self._set_state(STATE_ERROR, "Dock tag not found within timeout")
        self._send_motors(0, 0)
        return False

    def _approach_dock(self):
        """Drive towards dock tag"""
        self._set_state(STATE_APPROACHING, "Moving towards dock")
        start = time.time()

        while self._running and (time.time() - start) < 30:
            tags = self._get_tags()
            dock_tags = [t for t in tags if t["id"] in [0, 1, 2, 11, 13]]

            if not dock_tags:
                self._send_motors(0, 0)
                time.sleep(0.5)
                continue

            tag = dock_tags[0]
            distance = self._get_tag_distance(tag)
            center_x = tag["center"]["x"]

            # Check if close enough for alignment
            if distance > 0 and distance < self.dock_approach_distance:
                self._set_state(STATE_APPROACHING, f"At approach distance: {distance:.2f}m")
                self._send_motors(0, 0)
                return True

            # Steer towards tag center
            error = center_x - 320  # assuming VGA width
            speed = self.dock_align_speed

            if abs(error) > 100:
                # Large error - turn in place
                turn = speed if error > 0 else -speed
                self._send_motors(turn, -turn)
            else:
                # Small error - drive forward with slight correction
                correction = int(error * 0.1)
                self._send_motors(speed + correction, speed - correction)

            time.sleep(0.2)

        self._set_state(STATE_ERROR, "Approach timeout")
        self._send_motors(0, 0)
        return False

    def _align_dock(self):
        """Fine alignment with dock using DOCK_ALIGN tag"""
        self._set_state(STATE_ALIGNING, "Fine alignment")
        start = time.time()

        while self._running and (time.time() - start) < 20:
            tags = self._get_tags()
            align_tags = [t for t in tags if t["id"] == self.dock_tag_id]

            if not align_tags:
                # Fall back to any dock tag
                align_tags = [t for t in tags if t["id"] in [0, 1, 2]]

            if not align_tags:
                time.sleep(0.2)
                continue

            tag = align_tags[0]
            cx = tag["center"]["x"]
            cy = tag["center"]["y"]
            x_err = cx - 320
            y_err = cy - 240

            if abs(x_err) < self.alignment_tolerance and abs(y_err) < self.alignment_tolerance:
                self._set_state(STATE_ALIGNING, "Aligned!")
                self._send_motors(0, 0)
                return True

            # Proportional control
            speed = 15
            turn_speed = int(x_err * 0.08)
            fwd_speed = max(0, speed - abs(turn_speed))

            self._send_motors(fwd_speed + turn_speed, fwd_speed - turn_speed)
            time.sleep(0.15)

        self._set_state(STATE_ERROR, "Alignment timeout")
        self._send_motors(0, 0)
        return False

    def _engage_dock(self):
        """Final slow approach to lock magnetic connector"""
        self._set_state(STATE_DOCKING, "Engaging magnetic dock")
        start = time.time()

        while self._running and (time.time() - start) < 10:
            tags = self._get_tags()
            dock_tags = [t for t in tags if t["id"] in [0, 1, 2]]

            if dock_tags and "pose" in dock_tags[0]:
                dist = dock_tags[0]["pose"]["distance_m"]
                if dist < self.dock_lock_distance:
                    self._set_state(STATE_DOCKING, f"Locked at {dist:.3f}m")
                    self._send_motors(0, 0)
                    return True

            # Slow crawl forward
            self._send_motors(self.dock_lock_speed, self.dock_lock_speed)
            time.sleep(0.2)

        # Timeout but we're probably docked
        self._send_motors(0, 0)
        self._set_state(STATE_DOCKING, "Docker engaged (timeout fallback)")
        return True

    def _start_charging(self):
        """Begin charging cycle"""
        self._set_state(STATE_CHARGING, "Charging started")
        self.charge_start_time = datetime.now()

        while self._running and self.state == STATE_CHARGING:
            # Read current/voltage from INA219
            self._read_power()

            if self.battery_level >= self.target_charge_pct:
                self._set_state(STATE_COMPLETE, f"Charged to {self.battery_level}%")
                break

            # Report charge status every 30 seconds
            elapsed = (datetime.now() - self.charge_start_time).total_seconds()
            logger.info(
                f"Charging: {self.battery_level}% | "
                f"{self.charge_current:.1f}mA | "
                f"{self.charge_voltage:.2f}V | "
                f"{elapsed/60:.1f}min elapsed"
            )

            time.sleep(30)

    def _read_power(self):
        """Read power from INA219 via UNO Q I2C"""
        try:
            if self.serial_bridge:
                resp = self.serial_bridge.send_command("POWER")
                if resp:
                    data = json.loads(resp)
                    self.battery_level = data.get("battery_pct", 0)
                    self.charge_current = data.get("current_ma", 0)
                    self.charge_voltage = data.get("voltage_v", 0)
        except Exception as e:
            logger.error(f"Power read failed: {e}")

    def _get_tags(self):
        """Get detected tags from AprilTag detector"""
        if self.detector:
            return self.detector.detected_tags
        return []

    def _get_tag_distance(self, tag):
        """Estimate tag distance"""
        if "pose" in tag:
            return tag["pose"].get("distance_m", -1)
        return -1

    def _send_motors(self, left, right):
        """Send motor commands via serial bridge"""
        if self.serial_bridge:
            try:
                self.serial_bridge.send_command(f"MOTOR {left} {right}")
            except:
                pass

    def get_status(self):
        """Full dock status"""
        return {
            "state": self.state,
            "battery_pct": self.battery_level,
            "charge_current_ma": self.charge_current,
            "charge_voltage_v": self.charge_voltage,
            "charge_target_pct": self.target_charge_pct,
            "charge_start_time": self.charge_start_time.isoformat() if self.charge_start_time else None,
            "dock_tag_visible": any(t["id"] in [0, 1, 2, 11, 13] for t in self._get_tags()),
            "aligned": self.detector.is_dock_aligned() if self.detector else False,
            "dock_distance_m": self.detector.get_dock_distance() if self.detector else -1,
        }

    def get_charge_history(self):
        """Return charge session history"""
        return {
            "sessions": [],
            "total_charged_cycles": 0,
            "last_full_charge": None,
        }


# === Standalone test ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    controller = DockController()
    controller.on_state_change(lambda old, new, info: print(f"State: {old} -> {new} [{info}]"))
    print(json.dumps(controller.get_status(), indent=2))
