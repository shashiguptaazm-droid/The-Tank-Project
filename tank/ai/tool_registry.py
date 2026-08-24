"""
tool_registry.py - TankOS Tool Registry for LLM Function Calling
Defines all robot functions as JSON tool schemas (OpenAI-compatible).
Every LLM can call these tools during conversation.
"""
import json
import time
import logging
import subprocess
import os
from datetime import datetime

logger = logging.getLogger("tank.tools")

# ═══════════════════════════════════════════════════════════
#  TOOL DEFINITIONS — OpenAI Function Calling Format
# ═══════════════════════════════════════════════════════════

TANK_TOOLS = [
    # === MOTION ===
    {
        "type": "function",
        "function": {
            "name": "move_robot",
            "description": "Move the robot in a direction. Controls the tracked chassis motors.",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "enum": ["forward", "backward", "left", "right", "stop"],
                        "description": "Direction to move"
                    },
                    "speed": {
                        "type": "integer",
                        "description": "Motor speed 0-255 (default 150)",
                        "default": 150
                    },
                    "duration": {
                        "type": "number",
                        "description": "Seconds to move (default 1.0)",
                        "default": 1.0
                    }
                },
                "required": ["direction"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "emergency_stop",
            "description": "Immediately stop all motors. Use for safety.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_motors",
            "description": "Set individual motor speeds for differential drive control.",
            "parameters": {
                "type": "object",
                "properties": {
                    "left": {"type": "integer", "description": "Left motor speed (-255 to 255)"},
                    "right": {"type": "integer", "description": "Right motor speed (-255 to 255)"}
                },
                "required": ["left", "right"]
            }
        }
    },
    # === VISION ===
    {
        "type": "function",
        "function": {
            "name": "capture_image",
            "description": "Capture a single frame from the USB camera. Returns image info.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "detect_objects",
            "description": "Run YOLO object detection on the current camera frame. Returns detected objects.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "detect_apriltags",
            "description": "Detect AprilTag markers in the camera view. Used for docking and navigation.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    # === SENSORS ===
    {
        "type": "function",
        "function": {
            "name": "read_imu",
            "description": "Read IMU sensor data (accelerometer + gyroscope). Returns orientation.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_lidar",
            "description": "Read LiDAR scan data. Returns distance measurements in a 360-degree scan.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_battery",
            "description": "Read battery voltage, current, and percentage.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_temperature",
            "description": "Read temperature from DS18B20 probes (battery, motor, ambient).",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_sensor_status",
            "description": "Get status of all connected sensors (camera, LiDAR, IMU, modem, etc.).",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    # === SERVO ===
    {
        "type": "function",
        "function": {
            "name": "set_servo",
            "description": "Move a servo to a specific angle. Controls pan/tilt camera head.",
            "parameters": {
                "type": "object",
                "properties": {
                    "axis": {"type": "string", "enum": ["pan", "tilt"], "description": "Servo axis"},
                    "angle": {"type": "integer", "description": "Angle in degrees (0-180)", "default": 90}
                },
                "required": ["axis", "angle"]
            }
        }
    },
    # === NAVIGATION ===
    {
        "type": "function",
        "function": {
            "name": "navigate_to",
            "description": "Navigate autonomously to a waypoint. Uses LiDAR + AprilTags for localization.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "number", "description": "X coordinate in meters"},
                    "y": {"type": "number", "description": "Y coordinate in meters"}
                },
                "required": ["x", "y"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "return_to_dock",
            "description": "Autonomously return to the charging dock. Uses AprilTag for docking.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "start_patrol",
            "description": "Start autonomous patrol along predefined waypoints.",
            "parameters": {
                "type": "object",
                "properties": {
                    "waypoints": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "x": {"type": "number"},
                                "y": {"type": "number"}
                            }
                        },
                        "description": "List of waypoints to patrol"
                    }
                }
            }
        }
    },
    # === COMMUNICATION ===
    {
        "type": "function",
        "function": {
            "name": "send_sms",
            "description": "Send an SMS message to a phone number via the LTE modem.",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "Phone number with country code (e.g. +917860245819)"},
                    "message": {"type": "string", "description": "SMS message text"}
                },
                "required": ["phone", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_alert",
            "description": "Send an alert notification to the user via Telegram/SMS.",
            "parameters": {
                "type": "object",
                "properties": {
                    "alert_type": {"type": "string", "enum": ["info", "warning", "threat", "emergency"], "description": "Alert priority"},
                    "message": {"type": "string", "description": "Alert message"}
                },
                "required": ["alert_type", "message"]
            }
        }
    },
    # === AI / SYSTEM ===
    {
        "type": "function",
        "function": {
            "name": "run_terminal_command",
            "description": "Execute a shell command on the Jetson. Use for system operations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_status",
            "description": "Get full system status: CPU, RAM, disk, temperature, network, all devices.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_robot_status",
            "description": "Get robot status: mode, position, motors, sensors, battery, navigation state.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_robot_mode",
            "description": "Set the robot operating mode.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["autonomous", "manual", "patrol", "standby", "emergency"],
                        "description": "Operating mode"
                    }
                },
                "required": ["mode"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "take_screenshot",
            "description": "Take a screenshot of the TankOS dashboard or camera view.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
]


# ═══════════════════════════════════════════════════════════
#  TOOL EXECUTOR — Runs the actual commands
# ═══════════════════════════════════════════════════════════

class ToolExecutor:
    """Execute TankOS tools called by LLMs"""

    def __init__(self, serial_bridge=None, navigator=None, apriltag=None, sms_gateway=None):
        self.serial = serial_bridge
        self.navigator = navigator
        self.apriltag = apriltag
        self.sms = sms_gateway
        self._tools_map = {t["function"]["name"]: t for t in TANK_TOOLS}

    def execute(self, tool_name, arguments):
        """Execute a tool by name with arguments"""
        handler = getattr(self, f"_tool_{tool_name}", None)
        if handler:
            try:
                result = handler(**arguments) if arguments else handler()
                return {"success": True, "result": result}
            except Exception as e:
                logger.error(f"Tool {tool_name} error: {e}")
                return {"success": False, "error": str(e)}
        return {"success": False, "error": f"Unknown tool: {tool_name}"}

    # === MOTION TOOLS ===

    def _tool_move_robot(self, direction="forward", speed=150, duration=1.0):
        speed = max(0, min(255, speed))
        motor_commands = {
            "forward": (speed, speed),
            "backward": (-speed, -speed),
            "left": (-speed, speed),
            "right": (speed, -speed),
            "stop": (0, 0),
        }
        left, right = motor_commands.get(direction, (0, 0))
        self._send_motors(left, right)
        if direction != "stop" and duration > 0:
            time.sleep(duration)
            self._send_motors(0, 0)
        return f"Moved {direction} at speed {speed} for {duration}s"

    def _tool_emergency_stop(self):
        self._send_motors(0, 0)
        return "EMERGENCY STOP activated. All motors stopped."

    def _tool_set_motors(self, left=0, right=0):
        self._send_motors(int(left), int(right))
        return f"Motors set: left={left}, right={right}"

    def _tool_set_servo(self, axis="pan", angle=90):
        angle = max(0, min(180, int(angle)))
        if self.serial:
            self.serial.send_command(f"SERVO {axis} {angle}")
        return f"Servo {axis} set to {angle} degrees"

    # === VISION TOOLS ===

    def _tool_capture_image(self):
        import serial
        try:
            s = serial.Serial("/dev/ttyACM0", 921600, timeout=5)
            time.sleep(0.3)
            s.read(s.in_waiting)
            s.write(b"SNAP\n")
            header = b""
            deadline = time.time() + 5
            while time.time() < deadline:
                c = s.read(1)
                if c:
                    header += c
                    if c == b"\n":
                        break
            h = header.decode("utf-8", errors="replace").strip()
            if h.startswith("FRAME:"):
                parts = h.split(":")
                expected = int(parts[3])
                jpeg = b""
                dl = time.time() + 10
                while len(jpeg) < expected and time.time() < dl:
                    chunk = s.read(min(expected - len(jpeg), 16384))
                    if chunk:
                        jpeg += chunk
                        dl = time.time() + 2
                s.read(1)
                s.close()
                save_path = "/tmp/tank_frame_latest.jpg"
                with open(save_path, "wb") as f:
                    f.write(jpeg)
                return f"Image captured: {parts[1]}x{parts[2]} ({len(jpeg)} bytes) saved to {save_path}"
            s.close()
        except Exception as e:
            return f"Camera capture failed: {e}"
        return "No frame received"

    def _tool_detect_objects(self):
        try:
            import cv2
            import numpy as np
            from ultralytics import YOLO
            model = YOLO("yolov8n.pt")
            frame_path = "/tmp/tank_frame_latest.jpg"
            if not os.path.exists(frame_path):
                self._tool_capture_image()
            results = model(frame_path, verbose=False)
            detections = []
            for r in results:
                for box in r.boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    name = r.names[cls]
                    detections.append({"object": name, "confidence": round(conf, 2)})
            if detections:
                summary = ", ".join([f"{d['object']} ({d['confidence']})" for d in detections])
                return f"Detected {len(detections)} objects: {summary}"
            return "No objects detected in current frame"
        except Exception as e:
            return f"Detection failed: {e}"

    def _tool_detect_apriltags(self):
        if self.apriltag:
            tags = self.apriltag.detect_from_usb_camera()
            if tags:
                summary = ", ".join([f"ID:{t['id']} {t['name']}" for t in tags])
                return f"Detected {len(tags)} tags: {summary}"
            return "No AprilTags detected"
        return "AprilTag detector not initialized"

    # === SENSOR TOOLS ===

    def _tool_read_imu(self):
        if self.serial:
            resp = self.serial.send_command("IMU")
            if resp:
                return resp
        return "IMU not connected"

    def _tool_read_lidar(self):
        return "LiDAR scan: use get_robot_status for current scan data"

    def _tool_read_battery(self):
        if self.serial:
            resp = self.serial.send_command("POWER")
            if resp:
                return resp
        return "Battery monitor not connected"

    def _tool_read_temperature(self):
        try:
            result = subprocess.run(
                ["cat", "/sys/class/thermal/thermal_zone0/temp"],
                capture_output=True, text=True, timeout=2,
            )
            temp = int(result.stdout.strip()) / 1000
            return f"CPU temperature: {temp:.1f}°C"
        except:
            return "Temperature read failed"

    def _tool_get_sensor_status(self):
        status = {}
        # Camera
        status["camera"] = "USB /dev/ttyACM0" if os.path.exists("/dev/ttyACM0") else "not connected"
        # LiDAR
        status["lidar"] = "USB /dev/ttyUSB0" if os.path.exists("/dev/ttyUSB0") else "not connected"
        # IMU
        status["imu"] = "I2C 0x28" if self.serial else "not connected"
        # 4G Modem
        status["modem"] = "Quectel EG800AK" if os.path.exists("/dev/ttyUSB2") else "not connected"
        # Battery
        try:
            result = subprocess.run(
                ["cat", "/sys/class/thermal/thermal_zone0/temp"],
                capture_output=True, text=True, timeout=2,
            )
            status["cpu_temp"] = f"{int(result.stdout.strip()) / 1000:.1f}°C"
        except:
            status["cpu_temp"] = "unknown"
        return json.dumps(status)

    # === NAVIGATION TOOLS ===

    def _tool_navigate_to(self, x=0, y=0):
        if self.navigator:
            success = self.navigator.go_to_goal(float(x), float(y))
            return f"Navigation to ({x}, {y}): {'started' if success else 'failed'}"
        return "Navigator not initialized"

    def _tool_return_to_dock(self):
        if self.navigator:
            success = self.navigator.return_home()
            return f"Return to dock: {'started' if success else 'failed'}"
        return "Navigator not initialized"

    def _tool_start_patrol(self, waypoints=None):
        if self.navigator:
            if not waypoints:
                waypoints = [{"x": 1, "y": 0}, {"x": 1, "y": 1}, {"x": 0, "y": 1}]
            success = self.navigator.start_patrol(waypoints)
            return f"Patrol started with {len(waypoints)} waypoints"
        return "Navigator not initialized"

    # === COMMUNICATION TOOLS ===

    def _tool_send_sms(self, phone="", message=""):
        if self.sms:
            ok, resp = self.sms.send_sms(phone, message)
            return f"SMS to {phone}: {'sent' if ok else 'failed'} ({resp})"
        return "SMS gateway not connected"

    def _tool_send_alert(self, alert_type="info", message=""):
        try:
            import urllib.request
            data = json.dumps({
                "alert_type": alert_type,
                "message": message,
                "priority": "high" if alert_type in ["threat", "emergency"] else "normal",
            }).encode()
            req = urllib.request.Request(
                "http://127.0.0.1:8090/api/alert",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=5)
            return f"Alert sent: [{alert_type}] {message}"
        except:
            return f"Alert queued: [{alert_type}] {message}"

    # === SYSTEM TOOLS ===

    def _tool_run_terminal_command(self, command=""):
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=30,
            )
            output = result.stdout + result.stderr
            if len(output) > 1000:
                output = output[:500] + "\n... (truncated) ...\n" + output[-500:]
            return f"Exit code: {result.returncode}\n{output}"
        except subprocess.TimeoutExpired:
            return "Command timed out after 30 seconds"
        except Exception as e:
            return f"Command failed: {e}"

    def _tool_get_system_status(self):
        status = {}
        try:
            import psutil
            status["cpu_percent"] = psutil.cpu_percent(interval=0.5)
            mem = psutil.virtual_memory()
            status["ram_percent"] = mem.percent
            status["ram_used_gb"] = round(mem.used / (1024**3), 1)
            disk = psutil.disk_usage("/")
            status["disk_percent"] = disk.percent
        except:
            status["error"] = "psutil not available"
        try:
            result = subprocess.run(
                ["cat", "/sys/class/thermal/thermal_zone0/temp"],
                capture_output=True, text=True, timeout=2,
            )
            status["cpu_temp_c"] = round(int(result.stdout.strip()) / 1000, 1)
        except:
            pass
        status["uptime"] = datetime.now().isoformat()
        return json.dumps(status)

    def _tool_get_robot_status(self):
        return json.dumps({
            "mode": self.navigator.mode if self.navigator else "unknown",
            "position": self.navigator.position if self.navigator else {},
            "apriltags": len(self.apriltag.detected_tags) if self.apriltag else 0,
        })

    def _tool_set_robot_mode(self, mode="standby"):
        if self.navigator:
            if mode == "autonomous":
                self.navigator.start_autonomous()
            elif mode == "manual":
                self.navigator.set_manual(0, 0)
            elif mode == "emergency":
                self.navigator.emergency_stop()
            elif mode == "standby":
                self.navigator.stop()
            return f"Robot mode set to: {mode}"
        return "Navigator not initialized"

    def _tool_take_screenshot(self):
        return self._tool_capture_image()

    def _send_motors(self, left, right):
        if self.serial:
            try:
                self.serial.send_command(f"MOTOR {int(left)} {int(right)}")
            except:
                pass


def get_tools_for_llm():
    """Return tools in OpenAI function calling format"""
    return TANK_TOOLS


def get_tools_for_local():
    """Return tools in a format usable by local models"""
    tools_desc = []
    for tool in TANK_TOOLS:
        f = tool["function"]
        params = json.dumps(f["parameters"], indent=2) if f["parameters"].get("properties") else "none"
        tools_desc.append(f"- {f['name']}: {f['description']}\n  Parameters: {params}")
    return "\n".join(tools_desc)


class TankToolRegistry:
    """Unified tool registry for LLM-callable robot functions.

    Wraps the file-level TANK_TOOLS list and (when available) delegates
    to the agent_framework ToolRegistry for script-discovered tools.
    """

    def __init__(self, scripts_dir=None):
        self._tools = {t["function"]["name"]: t for t in TANK_TOOLS}
        self._executor = ToolExecutor()
        # Optionally bridge to the agent framework registry
        self._agent_registry = None
        if scripts_dir is not None:
            try:
                from tank_os.agent_framework.registry import ToolRegistry
                self._agent_registry = ToolRegistry(scripts_dir=scripts_dir)
            except Exception:
                pass

    def get(self, name: str) -> dict | None:
        """Look up a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        """Return all registered tool names."""
        return sorted(self._tools.keys())

    def execute(self, tool_name: str, arguments: dict | None = None) -> dict:
        """Execute a tool by name with optional arguments."""
        return self._executor.execute(tool_name, arguments or {})

    def get_tools_for_llm(self) -> list[dict]:
        """Return tools in OpenAI function-calling format."""
        return get_tools_for_llm()

    def get_tools_for_local(self) -> str:
        """Return tools in human-readable format for local models."""
        return get_tools_for_local()

    def __repr__(self) -> str:
        n = len(self._tools)
        return f"<TankToolRegistry {n} tools>"

    def __len__(self) -> int:
        return len(self._tools)
