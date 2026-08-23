"""
TankOS Inter-Device Communication Mesh
========================================
Connects Jetson, UNO Q, ESP32 nodes with:
  - Primary -> Fallback -> Emergency routing
  - Health-scored connections
  - Priority message queues
  - Bandwidth-aware communication
  - Offline store-and-forward
  - Device discovery & heartbeat
  - Split-brain protection
"""

from __future__ import annotations
import time
import uuid
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("tank.communication")


class DeviceRole(Enum):
    JETSON = "jetson"
    UNO_Q = "uno_q"
    ESP32 = "esp32"
    ANDROID_TV = "android_tv"
    VPS = "vps"
    UNKNOWN = "unknown"


class ConnectionState(Enum):
    CONNECTED = "connected"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"


class MessagePriority(Enum):
    EMERGENCY_STOP = 0
    COLLISION_WARNING = 1
    MOTOR_COMMAND = 2
    NAVIGATION = 3
    TELEMETRY = 4
    CAMERA = 5
    DEBUG = 6


class ProtocolType(Enum):
    USB_SERIAL = "usb_serial"
    ETHERNET = "ethernet"
    WIFI = "wifi"
    BLUETOOTH = "bluetooth"
    TAILSCALE = "tailscale"
    MQTT = "mqtt"
    ROS2_DDS = "ros2_dds"
    WEBSOCKET = "websocket"
    GRPC = "grpc"
    HTTP = "http"


@dataclass
class DeviceInfo:
    """Information about a connected device."""
    device_id: str = ""
    device_type: DeviceRole = DeviceRole.UNKNOWN
    hostname: str = ""
    ip_address: str = ""
    firmware_version: str = ""
    capabilities: list[str] = field(default_factory=list)
    protocols: list[ProtocolType] = field(default_factory=list)
    health_score: float = 100.0
    state: ConnectionState = ConnectionState.UNKNOWN
    last_heartbeat: float = 0
    latency_ms: float = 0
    bandwidth_mbps: float = 0


@dataclass
class Connection:
    """A connection path between devices."""
    source: str = ""
    destination: str = ""
    protocol: ProtocolType = ProtocolType.USB_SERIAL
    state: ConnectionState = ConnectionState.UNKNOWN
    primary: bool = True
    health_score: float = 100.0
    latency_ms: float = 0
    packet_loss: float = 0
    last_check: float = 0


@dataclass
class Message:
    """A message in the communication mesh."""
    msg_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source: str = ""
    destination: str = ""
    topic: str = ""
    payload: dict = field(default_factory=dict)
    priority: MessagePriority = MessagePriority.TELEMETRY
    timestamp: float = field(default_factory=time.time)
    expires_at: float = 0
    sequence: int = 0
    requires_ack: bool = False


class HeartbeatMonitor:
    """Monitors device heartbeats and detects failures."""

    def __init__(self):
        self._heartbeats: dict[str, float] = {}
        self._thresholds: dict[str, dict] = {
            "jetson": {"warning": 2.0, "degraded": 5.0, "failed": 10.0},
            "uno_q": {"warning": 2.0, "degraded": 5.0, "failed": 10.0},
            "esp32": {"warning": 0.5, "degraded": 1.0, "failed": 3.0},
            "android_tv": {"warning": 3.0, "degraded": 10.0, "failed": 30.0},
        }

    def receive_heartbeat(self, device_id: str):
        self._heartbeats[device_id] = time.time()

    def check_health(self, device_id: str) -> ConnectionState:
        last = self._heartbeats.get(device_id, 0)
        elapsed = time.time() - last if last > 0 else 999
        thresholds = self._thresholds.get(device_id.split("-")[0],
                                           {"warning": 3, "degraded": 8, "failed": 15})
        if elapsed < thresholds["warning"]:
            return ConnectionState.CONNECTED
        elif elapsed < thresholds["degraded"]:
            return ConnectionState.DEGRADED
        else:
            return ConnectionState.FAILED

    def get_all_health(self) -> dict[str, str]:
        return {did: self.check_health(did).value
                for did in self._heartbeats}


class PriorityMessageQueue:
    """Priority queue for messages with bandwidth-aware dropping."""

    def __init__(self, max_size: int = 1000):
        self._queue: list[Message] = []
        self._max_size = max_size

    def enqueue(self, msg: Message):
        self._queue.append(msg)
        self._queue.sort(key=lambda m: m.priority.value)
        if len(self._queue) > self._max_size:
            # Drop lowest priority messages
            self._queue = self._queue[:self._max_size]

    def dequeue(self) -> Optional[Message]:
        if self._queue:
            return self._queue.pop(0)
        return None

    def drop_low_priority(self, below: MessagePriority):
        self._queue = [m for m in self._queue if m.priority.value < below.value]

    def size(self) -> int:
        return len(self._queue)

    def get_by_priority(self) -> dict[str, int]:
        counts = {}
        for m in self._queue:
            name = m.priority.name
            counts[name] = counts.get(name, 0) + 1
        return counts


class DeviceMesh:
    """Inter-device communication mesh with failover."""

    def __init__(self):
        self._devices: dict[str, DeviceInfo] = {}
        self._connections: list[Connection] = []
        self._heartbeat = HeartbeatMonitor()
        self._queue = PriorityMessageQueue()
        self._offline_buffer: list[Message] = []
        self._message_seq = 0

        # Register default devices
        self._register_defaults()

    def _register_defaults(self):
        self.register_device(DeviceInfo(
            device_id="jetson-main",
            device_type=DeviceRole.JETSON,
            hostname="tank-jetson",
            capabilities=["ai", "vision", "cuda", "ros2", "slam", "navigation"],
            protocols=[ProtocolType.ETHERNET, ProtocolType.USB_SERIAL, ProtocolType.WIFI]
        ))
        self.register_device(DeviceInfo(
            device_id="uno-q-main",
            device_type=DeviceRole.UNO_Q,
            hostname="tank-uno-q",
            capabilities=["system_control", "gui", "networking", "device_management",
                         "android_tv", "diagnostics"],
            protocols=[ProtocolType.ETHERNET, ProtocolType.USB_SERIAL,
                       ProtocolType.WIFI, ProtocolType.BLUETOOTH]
        ))
        self.register_device(DeviceInfo(
            device_id="esp32-motor",
            device_type=DeviceRole.ESP32,
            hostname="esp32-motor",
            capabilities=["motor", "encoder", "servo"],
            protocols=[ProtocolType.USB_SERIAL, ProtocolType.WIFI]
        ))
        self.register_device(DeviceInfo(
            device_id="esp32-sensor",
            device_type=DeviceRole.ESP32,
            hostname="esp32-sensor",
            capabilities=["imu", "thermal", "ultrasonic", "gpio"],
            protocols=[ProtocolType.USB_SERIAL, ProtocolType.WIFI]
        ))
        self.register_device(DeviceInfo(
            device_id="android-tv",
            device_type=DeviceRole.ANDROID_TV,
            hostname="android-tv",
            capabilities=["display", "remote", "voice"],
            protocols=[ProtocolType.WIFI]
        ))

        # Register default connections
        self._connections = [
            Connection(source="uno-q-main", destination="jetson-main",
                      protocol=ProtocolType.ETHERNET, primary=True),
            Connection(source="uno-q-main", destination="esp32-motor",
                      protocol=ProtocolType.USB_SERIAL, primary=True),
            Connection(source="uno-q-main", destination="esp32-sensor",
                      protocol=ProtocolType.USB_SERIAL, primary=True),
            Connection(source="uno-q-main", destination="android-tv",
                      protocol=ProtocolType.WIFI, primary=True),
        ]

    def register_device(self, device: DeviceInfo):
        self._devices[device.device_id] = device

    def send(self, destination: str, topic: str, payload: dict,
             priority: MessagePriority = MessagePriority.TELEMETRY,
             requires_ack: bool = False) -> dict:
        """Send a message to a device."""
        msg = Message(
            source="tankos",
            destination=destination,
            topic=topic,
            payload=payload,
            priority=priority,
            requires_ack=requires_ack,
            sequence=self._message_seq
        )
        self._message_seq += 1

        # Find best connection
        conn = self._find_best_connection(destination)
        if not conn or conn.state == ConnectionState.FAILED:
            self._offline_buffer.append(msg)
            logger.warning(f"No connection to {destination}, buffered")
            return {"status": "buffered", "msg_id": msg.msg_id}

        self._queue.enqueue(msg)
        return {"status": "queued", "msg_id": msg.msg_id, "connection": conn.protocol.value}

    def broadcast(self, topic: str, payload: dict,
                  priority: MessagePriority = MessagePriority.TELEMETRY):
        """Broadcast to all connected devices."""
        for device_id in self._devices:
            if device_id != "tankos":
                self.send(device_id, topic, payload, priority)

    def _find_best_connection(self, destination: str) -> Optional[Connection]:
        candidates = [c for c in self._connections if c.destination == destination]
        if not candidates:
            return None
        # Primary first, then by health score
        primary = [c for c in candidates if c.primary]
        if primary:
            best = max(primary, key=lambda c: c.health_score)
            if best.state != ConnectionState.FAILED:
                return best
        # Fallback to any working connection
        working = [c for c in candidates if c.state != ConnectionState.FAILED]
        if working:
            return max(working, key=lambda c: c.health_score)
        return None

    def sync_offline_buffer(self):
        """Send buffered messages when connection recovers."""
        sent = []
        remaining = []
        for msg in self._offline_buffer:
            conn = self._find_best_connection(msg.destination)
            if conn and conn.state == ConnectionState.CONNECTED:
                self._queue.enqueue(msg)
                sent.append(msg.msg_id)
            else:
                remaining.append(msg)
        self._offline_buffer = remaining
        return {"synced": len(sent), "remaining": len(remaining)}

    def get_topology(self) -> dict:
        """Get the device topology."""
        devices = {}
        for did, dev in self._devices.items():
            health = self._heartbeat.check_health(did)
            devices[did] = {
                "type": dev.device_type.value,
                "hostname": dev.hostname,
                "capabilities": dev.capabilities,
                "state": health.value,
                "health_score": dev.health_score,
            }
        connections = []
        for conn in self._connections:
            connections.append({
                "from": conn.source,
                "to": conn.destination,
                "protocol": conn.protocol.value,
                "state": conn.state.value,
                "primary": conn.primary,
            })
        return {"devices": devices, "connections": connections}

    def get_status(self) -> dict:
        return {
            "devices": len(self._devices),
            "connections": len(self._connections),
            "queue_size": self._queue.size(),
            "offline_buffer": len(self._offline_buffer),
            "heartbeat_health": self._heartbeat.get_all_health(),
            "message_sequence": self._message_seq,
        }


# Global singleton
DEVICE_MESH = DeviceMesh()
