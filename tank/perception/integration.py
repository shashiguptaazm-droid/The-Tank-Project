"""Tank — Real Hardware Sensor Integration.

Connects all physical sensors to the main Tank system.
Falls back to simulation for any sensor that fails to connect.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from tank.perception.sensor import SensorInterface, SensorType, SensorReading, SensorStatus
from tank.perception.sensor_fusion import SensorFusion
from tank.perception.thermal import ThermalSensor
from tank.perception.ultrasonic import UltrasonicArray
from tank.perception.lidar import LidarSensor
from tank.perception.imu import IMUSensor
from tank.perception.luminosity import LuminositySensor
from tank.perception.infrared import InfraredSensor
from tank.perception.fingerprint import FingerprintSensor
from tank.perception.pressure import PressureSensor
from tank.perception.power_monitor import PowerMonitor
from tank.perception.cameras.usb_camera import USBCamera
from tank.perception.cameras.luxonis import LuxonisCamera
from tank.perception.cameras.orbbec import OrbbecCamera
from tank.networking.esp32.swarm import create_default_swarm
from tank.simulation.mock_sensors import MockCamera, MockLidar, MockThermal, MockIMU

logger = logging.getLogger("tank.hardware.integration")


class RealCameraSensor(SensorInterface):
    """Wraps USBCamera into the SensorInterface abstraction."""

    def __init__(self, device: int = 0):
        super().__init__("usb_camera", SensorType.CAMERA)
        self._cam = USBCamera(device=device)

    def connect(self) -> bool:
        ok = self._cam.connect()
        if ok:
            self._status = SensorStatus.CONNECTED
        return ok

    def read(self) -> Optional[SensorReading]:
        frame = self._cam.read_frame()
        if frame is None:
            return None
        return SensorReading(
            SensorType.CAMERA, __import__("time").time(),
            {"frame_id": self._cam.frame_count, "detections": []}
        )

    def disconnect(self):
        self._cam.disconnect()
        self._status = SensorStatus.DISCONNECTED


class RealThermalSensor(SensorInterface):
    """Wraps MLX90640 into SensorInterface."""

    def __init__(self):
        super().__init__("mlx90640", SensorType.THERMAL)
        self._sensor = ThermalSensor()

    def connect(self) -> bool:
        ok = self._sensor.connect()
        if ok:
            self._status = SensorStatus.CONNECTED
        return ok

    def read(self) -> Optional[SensorReading]:
        data = self._sensor.read()
        if data is None:
            return None
        return SensorReading(SensorType.THERMAL, __import__("time").time(), data)

    def disconnect(self):
        self._sensor.disconnect()
        self._status = SensorStatus.DISCONNECTED


class RealLidarSensor(SensorInterface):
    """Wraps RPLidar into SensorInterface."""

    def __init__(self, port: str = "/dev/ttyUSB0"):
        super().__init__("rplidar", SensorType.LIDAR)
        self._sensor = LidarSensor(port=port)

    def connect(self) -> bool:
        ok = self._sensor.connect()
        if ok:
            self._status = SensorStatus.CONNECTED
        return ok

    def read(self) -> Optional[SensorReading]:
        points = self._sensor.scan(max_beams=72)
        if points is None:
            return None
        min_point = min(points, key=lambda p: p["distance_m"]) if points else None
        return SensorReading(
            SensorType.LIDAR, __import__("time").time(),
            {"distance_m": min_point["distance_m"] if min_point else 99.0,
             "points": len(points)}
        )

    def disconnect(self):
        self._sensor.disconnect()
        self._status = SensorStatus.DISCONNECTED


class RealIMUSensor(SensorInterface):
    """Wraps BNO055/MPU6050 into SensorInterface."""

    def __init__(self, model: str = "BNO055", address: int = 0x28):
        super().__init__("bno055", SensorType.IMU)
        self._sensor = IMUSensor(model=model, address=address)

    def connect(self) -> bool:
        ok = self._sensor.connect()
        if ok:
            self._status = SensorStatus.CONNECTED
        return ok

    def read(self) -> Optional[SensorReading]:
        data = self._sensor.read_orientation()
        if data is None:
            return None
        return SensorReading(SensorType.IMU, __import__("time").time(), data)

    def disconnect(self):
        self._sensor.disconnect()
        self._status = SensorStatus.DISCONNECTED


class RealUltrasonicSensor(SensorInterface):
    """Wraps HC-SR04 array into SensorInterface."""

    def __init__(self):
        super().__init__("ultrasonic_array", SensorType.ULTRASONIC)
        self._array = UltrasonicArray()

    def connect(self) -> bool:
        ok = self._array.connect()
        if ok:
            self._status = SensorStatus.CONNECTED
        return ok

    def read(self) -> Optional[SensorReading]:
        readings = self._array.read_all()
        min_reading = self._array.read_min_distance()
        return SensorReading(
            SensorType.ULTRASONIC, __import__("time").time(),
            {"readings": readings,
             "min_distance_m": min_reading["distance_m"] if min_reading else None}
        )

    def disconnect(self):
        self._array.disconnect()
        self._status = SensorStatus.DISCONNECTED


def create_real_sensors(config=None) -> List[SensorInterface]:
    """Create real sensors, falling back to mock for any that fail.

    Priority: try real hardware first, fall back to simulation.
    This means the system ALWAYS works — even without all hardware.
    """
    sensors = []

    # Camera
    try:
        cam = RealCameraSensor(device=0)
        if cam.connect():
            sensors.append(cam)
            logger.info("✓ Real USB camera connected")
        else:
            raise RuntimeError("camera connect failed")
    except Exception:
        sensors.append(MockCamera())
        logger.info("→ Mock camera (real unavailable)")

    # Thermal
    try:
        thermal = RealThermalSensor()
        if thermal.connect():
            sensors.append(thermal)
            logger.info("✓ Real MLX90640 thermal connected")
        else:
            raise RuntimeError("thermal connect failed")
    except Exception:
        sensors.append(MockThermal())
        logger.info("→ Mock thermal (real unavailable)")

    # LiDAR
    try:
        lidar = RealLidarSensor(port="/dev/ttyUSB0")
        if lidar.connect():
            sensors.append(lidar)
            logger.info("✓ Real RPLidar connected")
        else:
            raise RuntimeError("lidar connect failed")
    except Exception:
        sensors.append(MockLidar())
        logger.info("→ Mock LiDAR (real unavailable)")

    # IMU
    try:
        imu = RealIMUSensor(model="BNO055", address=0x28)
        if imu.connect():
            sensors.append(imu)
            logger.info("✓ Real BNO055 IMU connected")
        else:
            raise RuntimeError("imu connect failed")
    except Exception:
        sensors.append(MockIMU())
        logger.info("→ Mock IMU (real unavailable)")

    logger.info(f"Sensors initialized: {len(sensors)} total")
    return sensors


def create_full_system(config=None, simulation: bool = True):
    """Create the complete Tank system with all integrations.

    If simulation=True, uses mock sensors.
    If simulation=False, tries real hardware with fallback.
    """
    from tank.core.config import get_config
    from tank.main import TankSystem

    if config is None:
        config = get_config()

    tank = TankSystem(config, simulation=simulation)

    if simulation:
        for s in create_mock_sensors():
            tank.add_sensor(s)
        logger.info("System started in SIMULATION mode")
    else:
        for s in create_real_sensors(config):
            tank.add_sensor(s)
        logger.info("System started in REAL mode (with fallback)")

    # Connect ESP32 swarm
    try:
        swarm = create_default_swarm()
        results = swarm.connect_all()
        connected = sum(1 for v in results.values() if v)
        logger.info(f"ESP32 swarm: {connected}/{len(results)} nodes connected")
    except Exception as e:
        logger.warning(f"ESP32 swarm init failed: {e}")

    return tank
