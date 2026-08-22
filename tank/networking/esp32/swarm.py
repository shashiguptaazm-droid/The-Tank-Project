"""Tank — ESP32 Swarm Communication.

Manages serial communication with multiple ESP32 nodes:
- ESP32 Head Controller (sensors + eye display)
- ESP32 Chest Controller (sonar, IR, temp)
- ESP32 Neck Controller (rotation motors)
- ESP32-S3 Hand Manager L/R (finger servos)

Protocol: JSON over serial @ 115200 baud.
Message format: {"cmd": "read", "pin": 23} → {"ok": true, "val": 42}
"""
from __future__ import annotations

import json
import logging
import os
import time
import random
from typing import Any, Dict, List, Optional

logger = logging.getLogger("tank.networking.esp32")

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


class ESP32Node:
    """Single ESP32 node communication handler."""

    def __init__(self, node_id: str, port: str, role: str = "generic", baud: int = 115200):
        self.node_id = node_id
        self.port = port
        self.role = role
        self.baud = baud
        self._ser = None
        self._connected = False
        self._simulating = False
        self._last_response = 0.0
        self._command_count = 0
        self._error_count = 0

    def connect(self) -> bool:
        if not SERIAL_AVAILABLE:
            logger.info(f"ESP32 {self.node_id} ({self.role}) — simulating (serial lib not available)")
            self._connected = True
            self._simulating = True
            return True
        try:
            self._ser = serial.Serial(self.port, self.baud, timeout=2)
            time.sleep(0.1)
            self._connected = True
            self._simulating = False
            logger.info(f"ESP32 {self.node_id} connected on {self.port}")
            return True
        except Exception as e:
            logger.info(f"ESP32 {self.node_id} ({self.role}) — simulating ({e})")
            self._connected = True
            self._simulating = True
            return True

    def send_command(self, cmd: str, **kwargs) -> Optional[Dict[str, Any]]:
        if not self._connected:
            return None

        if self._simulating:
            self._command_count += 1
            return self._simulate_response(cmd, **kwargs)

        message = json.dumps({"cmd": cmd, **kwargs})
        try:
            self._ser.write((message + "\n").encode())
            response = self._ser.readline().decode().strip()
            self._last_response = time.time()
            self._command_count += 1
            if response:
                return json.loads(response)
        except Exception as e:
            self._error_count += 1
            logger.error(f"ESP32 {self.node_id} command error: {e}")
        return None

    def _simulate_response(self, cmd: str, **kwargs) -> Dict[str, Any]:
        if cmd == "read_analog":
            return {"ok": True, "val": random.randint(0, 4095)}
        elif cmd == "read_digital":
            return {"ok": True, "val": random.randint(0, 1)}
        elif cmd == "set_pwm":
            return {"ok": True, "channel": kwargs.get("channel", 0), "duty": kwargs.get("duty", 0)}
        elif cmd == "read_ultrasonic":
            return {"ok": True, "distance_cm": round(random.uniform(5, 300), 1)}
        elif cmd == "read_temp":
            return {"ok": True, "temp_c": round(random.uniform(20, 38), 1)}
        elif cmd == "servo":
            return {"ok": True, "angle": kwargs.get("angle", 90)}
        elif cmd == "ping":
            return {"ok": True, "uptime_s": random.randint(100, 99999)}
        elif cmd == "status":
            return {"ok": True, "free_mem": random.randint(50000, 200000), "heap": "ok"}
        elif cmd == "read_sensors":
            return {"ok": True, "sensors": {"temp": round(random.uniform(20, 38), 1), "humidity": round(random.uniform(30, 70), 1)}}
        return {"ok": True}

    def disconnect(self) -> None:
        if self._ser:
            self._ser.close()
        self._connected = False

    def health(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "role": self.role,
            "port": self.port,
            "connected": self._connected,
            "simulating": self._simulating,
            "commands": self._command_count,
            "errors": self._error_count,
        }


class ESP32Swarm:
    """Manages all ESP32 nodes as a coordinated swarm."""

    def __init__(self):
        self.nodes: Dict[str, ESP32Node] = {}
        self._connected = False

    def add_node(self, node: ESP32Node) -> None:
        self.nodes[node.node_id] = node

    def connect_all(self) -> Dict[str, bool]:
        results = {}
        for nid, node in self.nodes.items():
            results[nid] = node.connect()
            if results[nid]:
                logger.info(f"Swarm: {nid} ({node.role}) connected")
        self._connected = any(results.values())
        return results

    def broadcast(self, cmd: str, **kwargs) -> Dict[str, Any]:
        responses = {}
        for nid, node in self.nodes.items():
            resp = node.send_command(cmd, **kwargs)
            if resp:
                responses[nid] = resp
        return responses

    def send_to(self, node_id: str, cmd: str, **kwargs) -> Optional[Dict]:
        node = self.nodes.get(node_id)
        if node:
            return node.send_command(cmd, **kwargs)
        return None

    def read_all_sensors(self) -> Dict[str, Any]:
        data = {}
        for nid, node in self.nodes.items():
            if node.role in ("head_sensors", "chest_sensors"):
                resp = node.send_command("read_sensors")
                if resp:
                    data[nid] = resp
        return data

    def set_all_servos(self, angles: Dict[str, int]) -> None:
        for servo_id, angle in angles.items():
            for nid, node in self.nodes.items():
                if node.role in ("hand_control", "neck_motors"):
                    node.send_command("servo", channel=servo_id, angle=angle)

    def disconnect_all(self) -> None:
        for node in self.nodes.values():
            node.disconnect()
        self._connected = False

    def health(self) -> Dict[str, Any]:
        return {
            "total_nodes": len(self.nodes),
            "connected": sum(1 for n in self.nodes.values() if n._connected),
            "simulating": sum(1 for n in self.nodes.values() if n._simulating),
            "nodes": {nid: n.health() for nid, n in self.nodes.items()},
        }


def create_default_swarm() -> ESP32Swarm:
    swarm = ESP32Swarm()
    nodes = [
        ESP32Node("esp32_head", "/dev/ttyUSB1", role="head_sensors"),
        ESP32Node("esp32_chest", "/dev/ttyUSB2", role="chest_sensors"),
        ESP32Node("esp32_neck", "/dev/ttyUSB3", role="neck_motors"),
        ESP32Node("esp32_hand_l", "/dev/ttyUSB4", role="hand_control"),
        ESP32Node("esp32_hand_r", "/dev/ttyUSB5", role="hand_control"),
    ]
    for node in nodes:
        swarm.add_node(node)
    return swarm
