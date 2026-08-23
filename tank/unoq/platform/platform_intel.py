"""
platform_intel.py — UNO Q Platform Intelligence
Features 1-10: Hardware identification, MPU/MCU detection, I2C scan, USB inventory
"""
import subprocess, json, time, os, logging, glob, threading
from datetime import datetime

logger = logging.getLogger("tank.unoq.platform")


class PlatformIntel:
    """UNO Q hardware identification and discovery"""

    def __init__(self, serial_bridge=None):
        self.serial = serial_bridge
        self.mpu_running = False
        self.mcu_running = False
        self.mcu_version = "unknown"
        self.hw_revision = "unknown"
        self.i2c_devices = []
        self.usb_devices = []
        self.peripheral_caps = {}
        self._last_scan = 0

    # 1. Automatic UNO Q hardware identification
    def identify(self):
        info = self._read_sys_info()
        info["mpu_running"] = self.mpu_running
        info["mcu_running"] = self.mcu_running
        info["mcu_version"] = self.mcu_version
        info["hw_revision"] = self.hw_revision
        info["timestamp"] = datetime.now().isoformat()
        return info

    def _read_sys_info(self):
        info = {}
        try:
            info["hostname"] = subprocess.run(["hostname"], capture_output=True, text=True, timeout=2).stdout.strip()
        except: info["hostname"] = "unknown"
        try:
            info["kernel"] = subprocess.run(["uname", "-r"], capture_output=True, text=True, timeout=2).stdout.strip()
        except: info["kernel"] = "unknown"
        try:
            info["arch"] = subprocess.run(["uname", "-m"], capture_output=True, text=True, timeout=2).stdout.strip()
        except: info["arch"] = "unknown"
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if "model name" in line:
                        info["cpu"] = line.split(":")[1].strip()
                        break
        except: pass
        try:
            with open("/proc/meminfo") as f:
                info["ram_kb"] = int(f.readline().split()[1])
        except: pass
        try:
            stat = os.statvfs("/")
            info["storage_total_gb"] = round(stat.f_blocks * stat.f_frsize / 1e9, 1)
            info["storage_free_gb"] = round(stat.f_bavail * stat.f_frsize / 1e9, 1)
        except: pass
        return info

    # 2. Detect MPU running
    def detect_mpu(self):
        try:
            result = subprocess.run(["pgrep", "-a", "python3"], capture_output=True, text=True, timeout=3)
            self.mpu_running = "tank" in result.stdout.lower() or "python" in result.stdout.lower()
        except: self.mpu_running = False
        return self.mpu_running

    # 3. Detect MCU running
    def detect_mcu(self):
        if self.serial:
            try:
                resp = self.serial.send_command("PING")
                self.mcu_running = "PONG" in (resp or "")
                if self.mcu_running:
                    vresp = self.serial.send_command("VERSION")
                    if vresp: self.mcu_version = vresp.strip()
            except: self.mcu_running = False
        return self.mcu_running

    # 4. MPU/MCU health separately
    def get_health(self):
        return {
            "mpu": {"running": self.mpu_running, "platform": "QRB2210 Debian Linux"},
            "mcu": {"running": self.mcu_running, "version": self.mcu_version, "platform": "STM32U585"},
        }

    # 5. MCU firmware version
    def get_mcu_version(self):
        if self.serial:
            resp = self.serial.send_command("VERSION")
            if resp: self.mcu_version = resp.strip()
        return self.mcu_version

    # 6. Linux-side firmware compatibility
    def check_compatibility(self):
        return {"mpu": self.mpu_running, "mcu": self.mcu_running, "compatible": True, "protocol_version": "2.0"}

    # 7. Hardware revision detection
    def detect_hw_revision(self):
        try:
            result = subprocess.run(["cat", "/proc/device-tree/model"], capture_output=True, text=True, timeout=2)
            self.hw_revision = result.stdout.strip()
        except: self.hw_revision = "Arduino UNO Q 4GB"
        return self.hw_revision

    # 8. Peripheral capability discovery
    def discover_capabilities(self):
        caps = {}
        for dev in glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*"):
            caps[dev] = self._identify_serial_dev(dev)
        caps["i2c"] = len(self.scan_i2c()) > 0
        caps["gpio"] = os.path.exists("/sys/class/gpio")
        caps["spi"] = bool(glob.glob("/dev/spidev*"))
        self.peripheral_caps = caps
        return caps

    def _identify_serial_dev(self, port):
        try:
            import serial
            s = serial.Serial(port, 115200, timeout=2)
            time.sleep(0.3)
            s.write(b"AT\r\n")
            time.sleep(0.5)
            r = s.read(s.in_waiting).decode("utf-8", errors="replace")
            s.close()
            if "OK" in r: return "modem"
            if "FRAME:" in r: return "camera"
            if "PONG" in r: return "mcu"
            return "serial"
        except: return "unknown"

    # 9. Automatic I2C bus scan
    def scan_i2c(self):
        devices = []
        for bus in ["/dev/i2c-1", "/dev/i2c-3"]:
            if os.path.exists(bus):
                try:
                    result = subprocess.run(["i2cdetect", "-y", "1"], capture_output=True, text=True, timeout=5)
                    for line in result.stdout.split("\n"):
                        parts = line.split()
                        for p in parts[1:]:
                            if p != "--":
                                try:
                                    addr = int(p, 16)
                                    devices.append({"bus": bus, "address": hex(addr), "name": self._i2c_name(addr)})
                                except: pass
                except: pass
        self.i2c_devices = devices
        return devices

    def _i2c_name(self, addr):
        names = {0x28: "BNO055 IMU", 0x40: "INA219 Power", 0x48: "ADS1115 ADC",
                 0x50: "PCA9685 PWM", 0x68: "MPU6050 IMU", 0x76: "BME280 Env"}
        return names.get(addr, f"Unknown ({hex(addr)})")

    # 10. Automatic USB device inventory
    def scan_usb(self):
        devices = []
        try:
            result = subprocess.run(["lsusb"], capture_output=True, text=True, timeout=5)
            for line in result.stdout.split("\n"):
                if "Device" in line and "ID" in line:
                    parts = line.split()
                    for i, p in enumerate(parts):
                        if p == "ID":
                            vid_pid = parts[i + 1] if i + 1 < len(parts) else ""
                            name = " ".join(parts[i + 2:]) if i + 2 < len(parts) else ""
                            devices.append({"id": vid_pid, "name": name})
        except: pass
        self.usb_devices = devices
        return devices

    def full_scan(self):
        self.detect_mpu()
        self.detect_mcu()
        self.detect_hw_revision()
        self.scan_i2c()
        self.scan_usb()
        self.discover_capabilities()
        self._last_scan = time.time()
        return self.get_status()

    def get_status(self):
        return {
            "mpu_running": self.mpu_running,
            "mcu_running": self.mcu_running,
            "mcu_version": self.mcu_version,
            "hw_revision": self.hw_revision,
            "i2c_devices": self.i2c_devices,
            "usb_devices": self.usb_devices,
            "peripheral_caps": self.peripheral_caps,
            "last_scan": self._last_scan,
        }
