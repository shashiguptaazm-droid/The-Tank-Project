"""
mcu_supervisor.py - UNO Q MCU Supervision System
Features 21-30: MPU↔MCU heartbeat, stall detection, crash recovery
"""
import time
import threading
import logging
from typing import Optional, Callable
from enum import IntEnum

logger = logging.getLogger("tank.unoq.mcu")


class MCUFaultCode(IntEnum):
    NONE = 0
    HEARTBEAT_LOST = 1
    STALL_DETECTED = 2
    FIRMWARE_CRASH = 3
    BROWNOUT = 4
    WATCHDOG_RESET = 5
    COMM_ERROR = 6
    OVERTEMP = 7


class MCUSupervisor:
    """Monitors MCU health, heartbeat, and recovers from faults."""

    def __init__(self, send_fn: Optional[Callable] = None, read_fn: Optional[Callable] = None):
        self.send_fn = send_fn or (lambda x: None)
        self.read_fn = read_fn or (lambda: b"")
        self.mcu_heartbeat_count = 0
        self.mpu_heartbeat_count = 0
        self.last_mcu_heartbeat = 0.0
        self.last_mpu_heartbeat = 0.0
        self.mcu_firmware_version = "unknown"
        self.mpu_mcu_firmware_version = "unknown"
        self.fault_code = MCUFaultCode.NONE
        self.reset_reasons = []
        self.stall_count = 0
        self.watchdog_resets = 0
        self.brownout_events = 0
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.heartbeat_interval_ms = 500
        self.stall_threshold_s = 2.0
        self.on_fault: Optional[Callable] = None
        self.on_recovery: Optional[Callable] = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("MCU supervisor started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)

    def _loop(self):
        while self._running:
            try:
                self._send_heartbeat()
                self._check_mcu_heartbeat()
                time.sleep(self.heartbeat_interval_ms / 1000.0)
            except Exception as e:
                logger.error(f"MCU supervisor loop error: {e}")
                self._record_fault(MCUFaultCode.COMM_ERROR, str(e))

    def _send_heartbeat(self):
        self.mpu_heartbeat_count += 1
        self.last_mpu_heartbeat = time.time()
        try:
            self.send_fn(f"HBT:{self.mpu_heartbeat_count}\n".encode())
        except Exception as e:
            logger.warning(f"Heartbeat send failed: {e}")

    def _check_mcu_heartbeat(self):
        if self.last_mcu_heartbeat == 0:
            return
        elapsed = time.time() - self.last_mcu_heartbeat
        if elapsed > self.stall_threshold_s:
            self.stall_count += 1
            logger.warning(f"MCU stall detected (no heartbeat for {elapsed:.1f}s, count={self.stall_count})")
            self._record_fault(MCUFaultCode.STALL_DETECTED, f"stall {elapsed:.1f}s")
            if self.stall_count > 3:
                self._attempt_recovery()

    def process_mcu_message(self, msg: str):
        if msg.startswith("HBT:"):
            parts = msg.split(":")
            if len(parts) >= 2:
                try:
                    self.mcu_heartbeat_count = int(parts[1])
                    self.last_mcu_heartbeat = time.time()
                    self.stall_count = 0
                except ValueError:
                    pass
        elif msg.startswith("FW:"):
            self.mcu_firmware_version = msg[3:]
            logger.info(f"MCU firmware: {self.mcu_firmware_version}")
        elif msg.startswith("RESET:"):
            reason = msg[6:]
            self.reset_reasons.append({"time": time.time(), "reason": reason})
            if "watchdog" in reason.lower():
                self.watchdog_resets += 1
            if "brownout" in reason.lower():
                self.brownout_events += 1
            self._record_fault(MCUFaultCode.FIRMWARE_CRASH, reason)
        elif msg.startswith("FAULT:"):
            code = msg[6:]
            try:
                self.fault_code = MCUFaultCode(int(code))
            except ValueError:
                self.fault_code = MCUFaultCode.COMM_ERROR
            self._record_fault(self.fault_code, msg)

    def _record_fault(self, code: MCUFaultCode, detail: str = ""):
        old_code = self.fault_code
        self.fault_code = code
        logger.error(f"MCU fault: {code.name} - {detail}")
        if self.on_fault:
            try:
                self.on_fault({"code": code, "detail": detail, "timestamp": time.time()})
            except Exception:
                pass

    def _attempt_recovery(self):
        logger.info("Attempting MCU recovery...")
        try:
            self.send_fn(b"RESET:RECOVER\n")
            time.sleep(1)
            self.send_fn(b"STATUS\n")
            self.stall_count = 0
            if self.on_recovery:
                try:
                    self.on_recovery({"timestamp": time.time()})
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"MCU recovery failed: {e}")

    def request_mcu_status(self):
        try:
            self.send_fn(b"STATUS\n")
            self.send_fn(b"VERSION\n")
        except Exception:
            pass

    def get_status(self) -> dict:
        return {
            "mcu_heartbeat_count": self.mcu_heartbeat_count,
            "mpu_heartbeat_count": self.mpu_heartbeat_count,
            "last_mcu_heartbeat_ago": time.time() - self.last_mcu_heartbeat if self.last_mcu_heartbeat else None,
            "mcu_firmware_version": self.mcu_firmware_version,
            "fault_code": self.fault_code.name if self.fault_code else "NONE",
            "stall_count": self.stall_count,
            "watchdog_resets": self.watchdog_resets,
            "brownout_events": self.brownout_events,
            "reset_reasons": self.reset_reasons[-10:],
            "is_healthy": self.fault_code == MCUFaultCode.NONE and self.stall_count == 0,
        }
