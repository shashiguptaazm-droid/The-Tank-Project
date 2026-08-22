"""Tank — Hardware Component Registry.

Complete inventory of every physical component on the robot,
organized by body section. Maps hardware IDs to drivers.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger("tank.hardware")


class BodySection(Enum):
    HEAD = "HEAD"
    NECK = "NECK"
    TORSO = "TORSO"
    LEFT_ARM = "LEFT_ARM"
    RIGHT_ARM = "RIGHT_ARM"
    LEFT_HAND = "LEFT_HAND"
    RIGHT_HAND = "RIGHT_HAND"
    LEFT_LEG = "LEFT_LEG"
    RIGHT_LEG = "RIGHT_LEG"
    POWER = "POWER"
    COMPUTE = "COMPUTE"
    NETWORKING = "NETWORKING"


class ComponentStatus(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ERROR = "ERROR"
    SIMULATED = "SIMULATED"


@dataclass
class Component:
    id: str
    name: str
    section: BodySection
    bus: str
    address: Optional[str] = None
    driver: str = ""
    status: ComponentStatus = ComponentStatus.INACTIVE
    specs: Dict = field(default_factory=dict)
    quantity: int = 1
    notes: str = ""


REGISTRY: Dict[str, Component] = {}


def register(c: Component) -> None:
    REGISTRY[c.id] = c


# ── HEAD (7 components) ─────────────────────────────────────────

register(Component(
    id="cam_stereo", name="Luxonis L-1-4 Sided Stereo Camera",
    section=BodySection.HEAD, bus="usb", driver="tank.perception.cameras.luxonis",
    specs={"resolution": "1280x800", "fps": 30, "depth": True, "fov": "120°"},
    notes="USB-C depth + RGB stereo camera"
))

register(Component(
    id="cam_depth", name="Orbbec 3D Camera",
    section=BodySection.HEAD, bus="usb", driver="tank.perception.cameras.orbbec",
    specs={"resolution": "640x480", "fps": 30, "depth_range": "0.2-10m"},
    notes="USB-C structured light depth camera"
))

register(Component(
    id="cam_ai", name="AI Camera Module",
    section=BodySection.HEAD, bus="usb", address="/dev/video0",
    driver="tank.perception.cameras.usb_camera",
    specs={"resolution": "640x480", "fps": 30},
    notes="USB webcam for YOLO detection"
))

register(Component(
    id="sensor_thermal", name="MLX90640 Thermal Sensor",
    section=BodySection.HEAD, bus="i2c", address="0x33",
    driver="tank.perception.thermal",
    specs={"resolution": "32x24", "fov": "110°", "refresh": "4Hz"},
    notes="Far-infrared thermal array camera"
))

register(Component(
    id="sensor_luminosity", name="Luminosity / Light Sensor",
    section=BodySection.HEAD, bus="i2c", address="0x29",
    driver="tank.perception.luminosity",
    specs={"range": "0.1-40000 lux"},
    notes="Ambient light measurement"
))

register(Component(
    id="sensor_imu_head", name="MPU6050 6-Axis IMU",
    section=BodySection.HEAD, bus="i2c", address="0x68",
    driver="tank.perception.imu",
    specs={"axes": 6, "accel_range": "±16g", "gyro_range": "±2000°/s"},
    notes="Head orientation tracking"
))

register(Component(
    id="eye_display", name="3D Eye Display Module",
    section=BodySection.HEAD, bus="usb",
    driver="tank.ui.eye_display",
    specs={"type": "OLED", "size": "1.3 inch"},
    notes="Animated eye expressions via USB"
))


# ── NECK (2 components) ─────────────────────────────────────────

register(Component(
    id="neck_rotator", name="360° Rotational Joint Motor",
    section=BodySection.NECK, bus="pwm",
    driver="tank.control.motors.servo",
    specs={"type": "servo", "rotation": "360°", "torque": "15kg/cm"},
    notes="Continuous rotation neck pan"
))

register(Component(
    id="neck_linear", name="Neck Linear Actuator",
    section=BodySection.NECK, bus="pwm",
    driver="tank.control.motors.linear_actuator",
    specs={"type": "linear", "stroke": "50mm"},
    notes="Vertical tilt via linear actuator"
))


# ── TORSO — Upper (5 components) ───────────────────────────────

register(Component(
    id="sonar_array", name="Ultrasonic Sensor Array",
    section=BodySection.TORSO, bus="gpio",
    driver="tank.perception.ultrasonic",
    specs={"sensors": 4, "range": "2-400cm", "accuracy": "3mm"},
    address="GPIO[23,24,25,26]",
    notes="HC-SR04 ×4 for 360° obstacle detection"
))

register(Component(
    id="mp3_module", name="Small MP3 Player Module",
    section=BodySection.TORSO, bus="serial",
    driver="tank.control.audio.mp3_player",
    specs={"format": "MP3/WAV", "storage": "microSD"},
    notes="Audio playback for speech/sounds"
))

register(Component(
    id="ir_sensors", name="Infrared Sensor Module",
    section=BodySection.TORSO, bus="gpio",
    driver="tank.perception.infrared",
    specs={"sensors": 2, "range": "2-30cm"},
    notes="Proximity detection (near-field)"
))

register(Component(
    id="led_rgb", name="RGB LED Strip Module",
    section=BodySection.TORSO, bus="pwm",
    driver="tank.control.led.strip",
    specs={"type": "WS2812B", "count": 30},
    notes="Status indication / expressions"
))

register(Component(
    id="display_touch", name="7\" Touchscreen Display",
    section=BodySection.TORSO, bus="hdmi",
    driver="tank.ui.touchscreen",
    specs={"size": "7 inch", "resolution": "1024x600", "touch": True},
    notes="Main UI display"
))


# ── TORSO — Internal (7 components) ────────────────────────────

register(Component(
    id="lidar", name="RPLidar A1/A2",
    section=BodySection.TORSO, bus="serial", address="/dev/ttyUSB0",
    driver="tank.perception.lidar",
    specs={"range": "0.15-12m", "scan_rate": "8Hz", "points": 360},
    notes="360° 2D LiDAR scanner"
))

register(Component(
    id="bno055", name="BNO055 9-DOF IMU",
    section=BodySection.TORSO, bus="i2c", address="0x28",
    driver="tank.perception.imu",
    specs={"axes": 9, "fusion": "sensor_fusion", "accuracy": "±1°"},
    notes="Body orientation — absolute heading"
))

register(Component(
    id="ina219_power", name="INA219 Current/Voltage Sensor",
    section=BodySection.TORSO, bus="i2c", address="0x40",
    driver="tank.perception.power_monitor",
    specs={"range": "26V/3.2A", "resolution": "0.1mA"},
    notes="Power rail monitoring"
))

register(Component(
    id="esp32_head", name="ESP32 Head Controller",
    section=BodySection.TORSO, bus="serial", address="/dev/ttyUSB1",
    driver="tank.networking.esp32.swarm",
    specs={"chip": "ESP32-S3", "role": "head_sensors"},
    notes="Manages head sensor reads, eye display"
))

register(Component(
    id="esp32_chest", name="ESP32 Chest Controller",
    section=BodySection.TORSO, bus="serial", address="/dev/ttyUSB2",
    driver="tank.networking.esp32.swarm",
    specs={"chip": "ESP32-S3", "role": "chest_sensors"},
    notes="Manages sonar, IR, temperature sensors"
))

register(Component(
    id="esp32_neck", name="ESP32 Neck Controller",
    section=BodySection.TORSO, bus="serial", address="/dev/ttyUSB3",
    driver="tank.networking.esp32.swarm",
    specs={"chip": "ESP32", "role": "neck_motors"},
    notes="Controls neck rotation and tilt"
))

register(Component(
    id="r307_fingerprint", name="R307 Fingerprint Sensor",
    section=BodySection.TORSO, bus="serial",
    driver="tank.perception.fingerprint",
    specs={"capacity": 300, "speed": "<1s"},
    notes="Biometric authentication"
))


# ── ARMS (6 components per arm) ─────────────────────────────────

for side in ["LEFT", "RIGHT"]:
    prefix = side.lower()
    section = BodySection.LEFT_ARM if side == "LEFT" else BodySection.RIGHT_ARM

    register(Component(
        id=f"{prefix}_arm_shoulder", name=f"{side} Shoulder Rotator",
        section=section, bus="pwm",
        driver="tank.control.motors.linear_actuator",
        specs={"type": "linear", "stroke": "80mm", "force": "100N"},
        notes=f"{side} shoulder elevation via linear actuator"
    ))

    register(Component(
        id=f"{prefix}_arm_bicep", name=f"{side} Bicep Linear Actuator",
        section=section, bus="pwm",
        driver="tank.control.motors.linear_actuator",
        specs={"type": "linear", "stroke": "60mm"},
        notes=f"{side} elbow flexion"
    ))

    register(Component(
        id=f"{prefix}_arm_forearm", name=f"{side} Forearm Servo",
        section=section, bus="pwm",
        driver="tank.control.motors.servo",
        specs={"type": "servo", "rotation": "180°"},
        notes=f"{side} forearm rotation"
    ))

    register(Component(
        id=f"{prefix}_arm_ham", name=f"{side} HAMMER Actuator Module",
        section=section, bus="i2c",
        driver="tank.control.motors.hammer",
        specs={"type": "electromagnetic"},
        notes=f"{side} electromagnetic connector"
    ))

    register(Component(
        id=f"{prefix}_arm_hub", name=f"{side} USB-C Hub Module",
        section=section, bus="usb",
        driver="tank.networking.usb_hub",
        specs={"ports": 4, "usb_version": "3.0"},
        notes=f"{side} arm USB expansion"
    ))

    register(Component(
        id=f"{prefix}_arm_esp32", name=f"{side} ESP32-S3 Hand Manager",
        section=section, bus="serial",
        driver="tank.networking.esp32.swarm",
        specs={"chip": "ESP32-S3", "role": "hand_control", "pwm_channels": 10},
        notes=f"{side} hand finger control (5 servos)"
    ))


# ── HANDS (5 fingers + 1 thumb per hand) ───────────────────────

for side in ["LEFT", "RIGHT"]:
    prefix = side.lower()

    for finger_name in ["index", "middle", "ring", "pinky"]:
        register(Component(
            id=f"{prefix}_hand_{finger_name}",
            name=f"{side} {finger_name.title()} Servo",
            section=BodySection.LEFT_HAND if side == "LEFT" else BodySection.RIGHT_HAND,
            bus="pwm",
            driver="tank.control.motors.finger",
            specs={"type": "micro_servo", "model": "SG90", "rotation": "180°", "torque": "1.8kg/cm"},
            notes=f"5-finger hand: {finger_name}"
        ))

    register(Component(
        id=f"{prefix}_hand_thumb",
        name=f"{side} Thumb Servo",
        section=BodySection.LEFT_HAND if side == "LEFT" else BodySection.RIGHT_HAND,
        bus="pwm",
        driver="tank.control.motors.finger",
        specs={"type": "micro_servo", "model": "SG90", "rotation": "180°", "torque": "1.8kg/cm"},
        notes="Opposable thumb"
    ))


# ── LEGS (2 actuators + foot sensor per leg) ───────────────────

for side in ["LEFT", "RIGHT"]:
    prefix = side.lower()
    section = BodySection.LEFT_LEG if side == "LEFT" else BodySection.RIGHT_LEG

    register(Component(
        id=f"{prefix}_leg_hip",
        name=f"{side} Hip Linear Actuator",
        section=section, bus="pwm",
        driver="tank.control.motors.linear_actuator",
        specs={"type": "linear", "stroke": "100mm", "force": "200N"},
        notes=f"{side} hip flexion/extension"
    ))

    register(Component(
        id=f"{prefix}_leg_knee",
        name=f"{side} Knee Linear Actuator",
        section=section, bus="pwm",
        driver="tank.control.motors.linear_actuator",
        specs={"type": "linear", "stroke": "80mm", "force": "200N"},
        notes=f"{side} knee flexion/extension"
    ))

    register(Component(
        id=f"{prefix}_leg_ankle",
        name=f"{side} Ankle Servo",
        section=section, bus="pwm",
        driver="tank.control.motors.servo",
        specs={"type": "servo", "rotation": "180°", "torque": "15kg/cm"},
        notes=f"{side} ankle dorsiflexion/plantarflexion"
    ))

    register(Component(
        id=f"{prefix}_leg_foot_sensor",
        name=f"{side} Foot Pressure Pad",
        section=section, bus="adc",
        driver="tank.perception.pressure",
        specs={"type": "FSR", "range": "0.1-10kg"},
        notes=f"{side} foot ground contact detection"
    ))


# ── POWER SYSTEM ────────────────────────────────────────────────

register(Component(
    id="power_management", name="Power Management Distribution Circuit",
    section=BodySection.POWER, bus="gpio",
    driver="tank.control.power.distribution",
    specs={"rails": 4, "max_current": "30A"},
    notes="Galvanically isolated power distribution"
))

register(Component(
    id="power_jetson_psu", name="Jetson 19V Barrel Jack PSU",
    section=BodySection.POWER, bus="power",
    specs={"voltage": 19, "current": "4.75A", "connector": "barrel"},
    notes="Main compute power"
))

register(Component(
    id="power_bank_1", name="Pebble Power Bank #1",
    section=BodySection.POWER, bus="power",
    specs={"capacity": "10000mAh", "output": "5V/2A"},
    notes="ESP32 swarm power"
))

register(Component(
    id="power_bank_2", name="Pebble Power Bank #2",
    section=BodySection.POWER, bus="power",
    specs={"capacity": "10000mAh", "output": "5V/2A"},
    notes="Display + audio power"
))

register(Component(
    id="power_bank_3", name="Pebble Power Bank #3",
    section=BodySection.POWER, bus="power",
    specs={"capacity": "10000mAh", "output": "5V/2A"},
    notes="Backup / sensor power"
))

register(Component(
    id="power_fuse", name="30A Blade Fuse",
    section=BodySection.POWER, bus="power",
    specs={"rating": "30A", "type": "blade"},
    notes="Main motor rail protection"
))

register(Component(
    id="power_xt60", name="XT60 Connector",
    section=BodySection.POWER, bus="power",
    specs={"current_rating": "60A"},
    notes="Main battery connection"
))


# ── COMPUTE ─────────────────────────────────────────────────────

register(Component(
    id="compute_jetson", name="NVIDIA Jetson Orin Nano",
    section=BodySection.COMPUTE, bus="pcie",
    specs={"gpu": "1024-core Ampere", "cpu": "6-core Arm Cortex-A78AE", "ram": "8GB",
           "storage": "NVMe 256GB", "ai": "40 TOPS"},
    notes="Main AI brain — CUDA inference, ROS2, TankOS GUI"
))

register(Component(
    id="compute_arduino", name="Arduino UNO Q (ABX00173)",
    section=BodySection.COMPUTE, bus="serial",
    specs={
        "type": "Single Board Computer",
        "ram": "4GB DDR4",
        "cpu": "Quad-core Arm Cortex-A53 @ 1.5GHz",
        "mcu": "Renesas RA4M1 (co-processor)",
        "wifi": "802.11ac",
        "bluetooth": "BLE 5.0",
        "gpio": 14,
        "pwm": 6,
        "usb": "USB-C (power + data)",
        "storage": "microSD",
        "os": "Linux (Debian-based)",
        "i2c": "Wire (A4/A5) + Qwiic",
        "interfaces": "I²C, SPI, UART, USB, GPIO",
    },
    notes="Real-time motor/sensor controller + Linux SBC for edge processing"
))


# ── AUDIO ───────────────────────────────────────────────────────

register(Component(
    id="mic_array", name="ReSpeaker 4-Mic Array",
    section=BodySection.HEAD, bus="usb",
    specs={"mics": 4, "sample_rate": 16000, "beamforming": True},
    notes="Far-field voice capture"
))

register(Component(
    id="speaker_main", name="3W Main Speaker",
    section=BodySection.TORSO, bus="usb",
    specs={"power": "3W", "impedance": "8Ω"},
    notes="Primary audio output"
))

register(Component(
    id="speaker_usb", name="USB Speaker",
    section=BodySection.TORSO, bus="usb",
    specs={"power": "2W"},
    notes="Secondary / backup speaker"
))


# ── NETWORKING ──────────────────────────────────────────────────

register(Component(
    id="wifi_module", name="WiFi 6 USB Adapter",
    section=BodySection.NETWORKING, bus="usb",
    specs={"standard": "802.11ax", "band": "2.4/5GHz"},
    notes="High-speed wireless"
))

register(Component(
    id="ethernet", name="Gigabit Ethernet",
    section=BodySection.NETWORKING, bus="ethernet",
    specs={"speed": "1Gbps"},
    notes="Wired VPS connection"
))

register(Component(
    id="lte_modem", name="4G LTE USB Modem",
    section=BodySection.NETWORKING, bus="usb",
    specs={"bands": "global LTE", "fallback": True},
    notes="Cellular backup connectivity"
))


# ── Utility Functions ──────────────────────────────────────────

def get_components_by_section(section: BodySection) -> List[Component]:
    return [c for c in REGISTRY.values() if c.section == section]


def get_all_components() -> List[Component]:
    return list(REGISTRY.values())


def get_component_count() -> int:
    return len(REGISTRY)


def print_registry() -> None:
    for section in BodySection:
        components = get_components_by_section(section)
        if not components:
            continue
        print(f"\n{'='*60}")
        print(f"  {section.value}")
        print(f"{'='*60}")
        for c in components:
            status_icon = "🟢" if c.status == ComponentStatus.ACTIVE else "⚪"
            print(f"  {status_icon} {c.id:<25} {c.name}")
            print(f"     Bus: {c.bus:<8} Address: {c.address or 'N/A'}")
            if c.specs:
                for k, v in c.specs.items():
                    print(f"     {k}: {v}")
            print()


if __name__ == "__main__":
    print_registry()
    print(f"\nTotal components: {get_component_count()}")
