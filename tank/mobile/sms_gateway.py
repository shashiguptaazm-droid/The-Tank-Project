"""
sms_gateway.py - SMS Messaging via mmcli (ModemManager)
Send/receive SMS through the ModemManager D-Bus interface.
Falls back to AT commands if ModemManager is not running.
"""
import subprocess
import time
import threading
import queue
import logging
import glob
import os
from datetime import datetime

logger = logging.getLogger("tank.sms")

MODEM_PORT = "/dev/ttyUSB2"
BAUD = 115200
SUDO_PASS = "1234"


class SMSGateway:
    """Two-way SMS gateway via ModemManager or AT commands"""

    def __init__(self, port=MODEM_PORT, baud=BAUD):
        self.port = port
        self.baud = baud
        self.connected = False
        self.use_mmcli = True
        self.incoming_queue = queue.Queue()
        self._callbacks = []
        self._modem_id = None

    def connect(self):
        """Detect connection method"""
        # Try mmcli first
        try:
            r = subprocess.run(
                ["mmcli", "-m", "0"],
                capture_output=True, text=True, timeout=5,
            )
            if r.returncode == 0 and "EG800" in r.stdout:
                self.use_mmcli = True
                self.connected = True
                self._modem_id = "0"
                logger.info("SMS Gateway: Using mmcli (ModemManager)")
                return True
        except:
            pass

        # Fallback to AT commands
        try:
            import serial
            self.modem = serial.Serial(self.port, self.baud, timeout=3)
            time.sleep(0.3)
            self.modem.read(self.modem.in_waiting)
            self.modem.write(b"AT\r\n")
            time.sleep(0.5)
            resp = self.modem.read(self.modem.in_waiting).decode("utf-8", errors="replace")
            if "OK" in resp:
                self.use_mmcli = False
                self.connected = True
                logger.info("SMS Gateway: Using AT commands")
                return True
            self.modem.close()
        except:
            pass

        logger.error("SMS Gateway: No connection method available")
        return False

    def send_sms(self, phone_number, message):
        """Send an SMS message"""
        if not phone_number.startswith("+"):
            phone_number = "+91" + phone_number

        if self.use_mmcli:
            return self._send_mmcli(phone_number, message)
        else:
            return self._send_at(phone_number, message)

    def _send_mmcli(self, phone, message):
        """Send SMS via mmcli"""
        try:
            # URL encode the message for shell
            safe_msg = message.replace("'", "'\\''")

            # Create SMS
            r = subprocess.run(
                ["bash", "-c",
                 f"echo '{SUDO_PASS}' | sudo -S mmcli -m 0 "
                 f"--messaging-create-sms='number={phone},text={safe_msg}'"],
                capture_output=True, text=True, timeout=10,
            )

            if r.returncode != 0:
                logger.error(f"SMS create failed: {r.stderr}")
                return False, r.stderr

            # Extract SMS path
            for line in r.stdout.split("\n"):
                if "created sms:" in line:
                    sms_path = line.split("created sms:")[1].strip()
                    sms_id = sms_path.split("/")[-1]

                    # Send SMS
                    r2 = subprocess.run(
                        ["bash", "-c",
                         f"echo '{SUDO_PASS}' | sudo -S mmcli -s {sms_id} --send"],
                        capture_output=True, text=True, timeout=15,
                    )

                    if "successfully sent" in r2.stdout:
                        logger.info(f"SMS sent to {phone}")
                        return True, "Sent"
                    else:
                        logger.error(f"SMS send failed: {r2.stdout} {r2.stderr}")
                        return False, r2.stdout + r2.stderr

            return False, "No SMS path found"
        except Exception as e:
            logger.error(f"mmcli send error: {e}")
            return False, str(e)

    def _send_at(self, phone, message):
        """Send SMS via AT commands"""
        try:
            import serial
            if not hasattr(self, 'modem') or not self.modem.is_open:
                self.modem = serial.Serial(self.port, self.baud, timeout=5)
                time.sleep(0.3)
            self.modem.read(self.modem.in_waiting)
            self.modem.write(b"AT+CMGF=1\r\n")
            time.sleep(0.5)
            self.modem.read(self.modem.in_waiting)
            self.modem.write(f'AT+CMGS="{phone}"\r\n'.encode())
            time.sleep(3)
            prompt = self.modem.read(self.modem.in_waiting)
            if b">" in prompt:
                self.modem.write(message.encode() + b"\x1a")
                time.sleep(8)
                resp = self.modem.read(self.modem.in_waiting).decode("utf-8", errors="replace")
                return "CMGS" in resp or "OK" in resp, resp
            return False, "No > prompt"
        except Exception as e:
            return False, str(e)

    def get_signal_quality(self):
        """Get current signal quality"""
        try:
            r = subprocess.run(
                ["mmcli", "-m", "0", "--signal"],
                capture_output=True, text=True, timeout=5,
            )
            for line in r.stdout.split("\n"):
                if "quality:" in line:
                    q = int(line.split(":")[1].strip().replace("%", ""))
                    return {"rssi": q, "quality": f"{q}%"}
        except:
            pass
        return {"rssi": 0, "quality": "unknown"}

    def get_network_info(self):
        """Get network operator info"""
        try:
            r = subprocess.run(
                ["mmcli", "-m", "0"],
                capture_output=True, text=True, timeout=5,
            )
            info = {"operator": "unknown", "technology": "unknown"}
            for line in r.stdout.split("\n"):
                if "operator" in line.lower():
                    info["operator"] = line.split(":")[-1].strip()
                if "lte" in line.lower():
                    info["technology"] = "LTE"
            return info
        except:
            return {"operator": "unknown", "technology": "unknown"}

    def get_battery_status(self):
        """Get battery level"""
        try:
            r = subprocess.run(
                ["mmcli", "-m", "0"],
                capture_output=True, text=True, timeout=5,
            )
            for line in r.stdout.split("\n"):
                if "battery" in line.lower():
                    parts = line.split(":")
                    if len(parts) > 1:
                        pct = parts[1].strip().replace("%", "")
                        try:
                            return {"level": int(pct), "mv": int(pct) * 42}
                        except:
                            pass
        except:
            pass
        return {"level": -1, "mv": 0}

    def on_message(self, callback):
        self._callbacks.append(callback)

    def get_status(self):
        return {
            "connected": self.connected,
            "method": "mmcli" if self.use_mmcli else "AT",
            "signal": self.get_signal_quality(),
            "network": self.get_network_info(),
            "battery": self.get_battery_status(),
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    gw = SMSGateway()
    if gw.connect():
        print("Status:", gw.get_status())
        ok, resp = gw.send_sms("+917860245819", "TankOS SMS test")
        print(f"Send: {ok} {resp}")
