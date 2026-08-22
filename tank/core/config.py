"""Tank — Centralized Configuration.

Loads config from .env, config.yaml, and environment variables.
Never hard-codes secrets, ports, URLs, or model names.
"""
from __future__ import annotations

import os
import json
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class VPSConfig:
    url: str = "http://localhost:8000"
    api_key: str = ""
    timeout: float = 30.0
    retries: int = 3
    backoff_base: float = 1.0


@dataclass
class SensorConfig:
    camera_device: int = 0
    camera_fps: int = 30
    camera_resolution: tuple = (640, 480)
    lidar_port: str = "/dev/ttyUSB0"
    lidar_baud: int = 115200
    imu_address: int = 0x28
    thermal_address: int = 0x33
    ultrasonic_trig: list = field(default_factory=lambda: [23, 24])
    ultrasonic_echo: list = field(default_factory=lambda: [25, 26])


@dataclass
class AIConfig:
    model: str = "yolov8n.pt"
    confidence_threshold: float = 0.5
    local_model: str = "tinyllama"
    max_tokens: int = 512
    inference_device: str = "cpu"


@dataclass
class ControlConfig:
    motor_pwm_freq: int = 1000
    max_speed: float = 1.0
    safety_timeout: float = 2.0
    estop_pin: int = 9


@dataclass
class TankConfig:
    vps: VPSConfig = field(default_factory=VPSConfig)
    sensors: SensorConfig = field(default_factory=SensorConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    control: ControlConfig = field(default_factory=ControlConfig)
    simulation: bool = False
    demo_mode: bool = False
    log_level: str = "INFO"
    dashboard_port: int = 8080
    api_port: int = 8085

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "TankConfig":
        """Load config from file + env vars. Env vars override file values."""
        cfg = cls()

        # Load from .env
        env_file = PROJECT_ROOT / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))

        # Load from YAML
        if config_path is None:
            config_path = PROJECT_ROOT / "config" / "tank.yaml"
        if config_path.exists():
            with open(config_path) as f:
                data = yaml.safe_load(f) or {}
            _apply_dict(cfg, data)

        # Env overrides
        cfg.simulation = os.getenv("TANK_SIMULATION", "false").lower() == "true"
        cfg.demo_mode = os.getenv("TANK_DEMO_MODE", "false").lower() == "true"
        cfg.log_level = os.getenv("TANK_LOG_LEVEL", cfg.log_level)
        cfg.vps.url = os.getenv("TANK_VPS_URL", cfg.vps.url)
        cfg.vps.api_key = os.getenv("TANK_VPS_API_KEY", cfg.vps.api_key)

        return cfg


def _apply_dict(obj: Any, data: Dict[str, Any]) -> None:
    """Recursively apply a dict to a dataclass."""
    for key, val in data.items():
        if hasattr(obj, key):
            attr = getattr(obj, key)
            if isinstance(val, dict) and hasattr(attr, "__dataclass_fields__"):
                _apply_dict(attr, val)
            else:
                setattr(obj, key, val)


_config: Optional[TankConfig] = None


def get_config() -> TankConfig:
    global _config
    if _config is None:
        _config = TankConfig.load()
    return _config
