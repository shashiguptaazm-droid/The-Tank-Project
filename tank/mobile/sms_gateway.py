"""
sms_gateway.py - SMS Messaging via Quectel LTE Modem
Send/receive SMS through the AT command interface on /dev/ttyUSB2
"""
import serial
import time
import threading
import queue
import logging
from datetime import datetime

logger = logging.getLogger("tank.sms")

MODEM_PORT = "/dev/ttyUSB2"
BAUD = 115200


class SMSGateway:
    """Two-way SMS gateway over Quectel EG800AK AT commands"""

    def __init__(self, port=MODEM_PORT, baud=BAUD):
        self.port = port
        self.baud = baud
        self.modem = None
        self.running = False
        self.incoming_queue = queue.Queue()
        self._callbacks = []
        self._reader_thread = None

    def connect(self):
        try:
            self.modem = serial.Serial(self.port, self.baud, timeout=3)
            time.sleep(0.5)
            self.modem.read(self.modem.in_waiting)

            # Init sequence
            for cmd in ["AT", "ATE0", "AT+CMGF=1", "AT+CNMI=2,2,0,0,0", "AT+CMEE=2"]:
                self._send(cmd)
                time.sleep(0.3)

            logger.info(f"SMS Gateway connected on {self.port}")
            return True
        except Exception as e:
            logger.error(f"Modem connection failed: {e}")
            return False

    def _send(self, cmd, timeout=3):
        if not self.modem:
            return ""
        self.modem.read(self.modem.in_waiting)
        self.modem.write((cmd + "\r\n").encode())
        time.sleep(0.3)
        resp = b""
        deadline = time.time() + timeout
        while time.time() < deadline:
            chunk = self.modem.read(1024)
            if chunk:
                resp += chunk
            else:
                break
        return resp.decode("utf-8", errors="replace").strip()

    def send_sms(self, phone_number, message):
        """Send an SMS message"""
        if not phone_number.startswith("+"):
            phone_number = "+91" + phone_number

        # Set text mode
        self._send("AT+CMGF=1")
        time.sleep(0.2)

        # Send SMS
        self.modem.write(f'AT+CMGS="{phone_number}"\r\n'.encode())
        time.sleep(0.5)
        self.modem.write(message.encode() + b"\x1a")  # Ctrl+Z to send
        time.sleep(3)

        resp = self._send("")
        success = "OK" in resp or "CMGS" in resp
        logger.info(f"SMS to {phone_number}: {'OK' if success else 'FAILED'}")
        return success, resp

    def get_signal_quality(self):
        """Get current signal quality"""
        resp = self._send("AT+CSQ")
        for line in resp.split("\n"):
            if "+CSQ" in line:
                try:
                    parts = line.split(":")[1].strip().split(",")
                    rssi = int(parts[0])
                    # Convert to dBm: rssi * 2 - 113
                    dbm = rssi * 2 - 113 if rssi > 0 else -113
                    return {"rssi": rssi, "dbm": dbm, "quality": f"{rssi}/31"}
                except:
                    pass
        return {"rssi": 0, "dbm": -113, "quality": "unknown"}

    def get_network_info(self):
        """Get network operator info"""
        resp = self._send("AT+COPS?")
        info = {"operator": "unknown", "technology": "unknown"}
        for line in resp.split("\n"):
            if "+COPS" in line:
                try:
                    parts = line.split(":")[1].strip().split(",")
                    info["operator"] = parts[2].strip('"')
                    tech_map = {"7": "LTE", "2": "2G", "3": "3G"}
                    info["technology"] = tech_map.get(parts[3].strip(), "unknown")
                except:
                    pass
        return info

    def get_battery_status(self):
        """Get battery level"""
        resp = self._send("AT+CBC")
        for line in resp.split("\n"):
            if "+CBC" in line:
                try:
                    parts = line.split(":")[1].strip().split(",")
                    return {"level": int(parts[0]), "mv": int(parts[1])}
                except:
                    pass
        return {"level": -1, "mv": 0}

    def on_message(self, callback):
        """Register callback for incoming SMS"""
        self._callbacks.append(callback)

    def start_listening(self):
        """Start background thread to listen for incoming SMS"""
        self.running = True

        def _listen():
            logger.info("SMS listener started")
            while self.running:
                try:
                    if self.modem and self.modem.in_waiting:
                        data = self.modem.read(self.modem.in_waiting).decode(
                            "utf-8", errors="replace"
                        )
                        # Parse incoming SMS: +CMT: "+91...","...",,"26/08/23,07:30:00+22"\nMessage body
                        if "+CMT:" in data:
                            lines = data.split("\n")
                            for i, line in enumerate(lines):
                                if "+CMT:" in line:
                                    try:
                                        phone = line.split('"')[1]
                                        body = lines[i + 1].strip() if i + 1 < len(lines) else ""
                                        msg = {
                                            "phone": phone,
                                            "message": body,
                                            "timestamp": datetime.now().isoformat(),
                                        }
                                        self.incoming_queue.put(msg)
                                        for cb in self._callbacks:
                                            cb(msg)
                                        logger.info(f"Incoming SMS from {phone}: {body[:50]}")
                                    except Exception as e:
                                        logger.error(f"Parse error: {e}")
                    time.sleep(0.5)
                except Exception as e:
                    if self.running:
                        logger.error(f"Listener error: {e}")
                    time.sleep(1)

        self._reader_thread = threading.Thread(target=_listen, daemon=True)
        self._reader_thread.start()

    def stop(self):
        self.running = False
        if self.modem:
            try:
                self.modem.close()
            except:
                pass

    def get_status(self):
        """Full modem status"""
        return {
            "connected": self.modem is not None and self.modem.is_open,
            "signal": self.get_signal_quality(),
            "network": self.get_network_info(),
            "battery": self.get_battery_status(),
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    gw = SMSGateway()
    if gw.connect():
        print("Modem status:", gw.get_status())
    gw.stop()
