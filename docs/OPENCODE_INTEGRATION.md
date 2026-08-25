# OpenCode + TankOS Integration

## Overview

This document describes how to use [OpenCode](https://opencode.ai/) with the TankOS Agent Chat mechanism, giving you access to **1,166+ robot tools** via the Model Context Protocol (MCP).

## What is OpenCode?

OpenCode is an open-source AI coding agent that runs in your terminal. It supports:
- Multi-provider LLM support (Claude, GPT-4, Gemini, etc.)
- MCP server integration for external tools
- Code editing, debugging, and refactoring
- Natural language interaction

## What is TankOS Agent Chat?

TankOS Agent Chat is the autonomous AI robotics operating system's tool-calling mechanism. It provides:
- **1,166+ callable modules** across 18 categories
- Real camera access with YOLO object detection
- Multi-provider LLM rotation (Groq, OpenRouter, Mistral, Gemini, Cohere)
- Local Phi-3 fallback for offline operation
- Shell command execution
- Hardware control (motors, servos, sensors)
- And much more...

## Quick Start

### 1. Run the Setup Script

```bash
cd The-Tank-Project
chmod +x setup_opencode.sh
./setup_opencode.sh
```

### 2. Start OpenCode

```bash
opencode
```

### 3. Use TankOS Tools

Once OpenCode starts, the TankOS MCP server will automatically load. You can now use natural language to interact with your robot:

```
> What tools are available?
> Capture from the camera
> What's the system status?
> Navigate to the kitchen
> Send an SMS to Shashi
```

## Configuration

The integration is configured via `opencode.json` in the project root:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "tankos": {
      "type": "local",
      "command": ["python3", "tank_os/agent_framework/mcp_server.py"],
      "enabled": true,
      "cwd": ".",
      "environment": {
        "PYTHONPATH": "."
      },
      "timeout": 10000
    }
  },
  "tools": {
    "tankos_*": true
  }
}
```

## Available TankOS Tools

The MCP server exposes these core tools:

### Robot Tools

### `tankos_list_tools`
List all available TankOS tools, optionally filtered by category.

```python
# Example usage in OpenCode:
"What tools are available for navigation?"
```

### `tankos_invoke_tool`
Invoke any TankOS tool by name with arguments.

```python
# Example: Navigate to a location
tankos_invoke_tool("navigation.go_to", {"location": "kitchen"})
```

### `tankos_search_tools`
Search tools by keyword or description.

```python
# Example: Find camera-related tools
tankos_search_tools("camera")
```

### `tankos_camera_vision`
Capture from the DFRobot USB camera and run YOLO object detection.

```python
# Example: What do you see?
tankos_camera_vision()
```

### `tankos_system_status`
Get system status including hardware, network, and AI providers.

```python
# Example: System check
tankos_system_status()
```

### `tankos_shell_command`
Execute shell commands on the TankOS system.

```python
# Example: Check disk usage
tankos_shell_command("df -h")
```

---

### AI Provider Tools (10 Providers)

### `tankos_list_providers`
List all configured AI providers and their status.

```python
# Example: What providers are available?
tankos_list_providers()
```

### `tankos_call_llm`
Call a specific AI provider with a prompt.

```python
# Example: Use Groq for fast inference
tankos_call_llm("groq", "What is the capital of France?")

# Example: Use Gemini with system prompt
tankos_call_llm("gemini", "Explain quantum computing", "You are a physics expert")
```

### `tankos_call_llm_fallback`
Call AI providers with automatic fallback — tries all configured providers.

```python
# Example: Auto-select best available provider
tankos_call_llm_fallback("Write a Python function to sort a list")
```

### `tankos_get_provider_info`
Get detailed information about a specific AI provider.

```python
# Example: Get Groq details
tankos_get_provider_info("groq")
```

## Tool Categories

TankOS tools are organized into 18 categories:

| Category | Description | Example Tools |
|----------|-------------|---------------|
| **Perception** | Camera, YOLO, tracking, pose, depth | `perception.capture`, `perception.track` |
| **OCR/Language** | Text reading, translation, intent | `language.translate`, `language.classify` |
| **Voice** | STT, TTS, wake word, synthesis | `voice.speak`, `voice.listen` |
| **Human Interaction** | Detection, tracking, gestures | `human.detect`, `human.follow` |
| **Navigation** | Go-to, patrol, path planning | `navigation.go_to`, `navigation.patrol` |
| **SLAM/World** | Mapping, localization, landmarks | `slam.map`, `slam.localize` |
| **Memory** | Store, retrieve, search, compress | `memory.store`, `memory.search` |
| **AI Orchestration** | Ask, reason, plan, classify | `ai.reason`, `ai.plan` |
| **Tool System** | List, search, validate, execute | `tools.list`, `tools.execute` |
| **Hardware** | Discover, health, restart, calibrate | `hardware.discover`, `hardware.health` |
| **ESP32/Sensors** | IMU, thermal, battery, encoder | `sensor.imu`, `sensor.thermal` |
| **Actuators** | Motors, servos, arm, emergency stop | `actuator.motor`, `actuator.servo` |
| **Power** | Voltage, current, budget, thermal | `power.voltage`, `power.budget` |
| **Network** | Status, scan, topology, failover | `network.status`, `network.scan` |
| **GUI** | Dashboard, camera, map, mission | `gui.dashboard`, `gui.camera` |
| **Evolution** | Observe, hypothesis, experiment | `evolution.observe`, `evolution.experiment` |
| **Safety** | Check, stop, validate, logs | `safety.check`, `safety.stop` |
| **Generative AI** | Text, code, images, voice | `generate.text`, `generate.code` |

## Examples

### Example 1: Camera Vision

```
You: What do you see through the camera?

OpenCode calls: tankos_camera_vision()

Response: "I see a person (85%) at (328, 326) and a kite (33%) at (150, 23)"
```

### Example 2: Navigation

```
You: Navigate to the kitchen

OpenCode calls: tankos_invoke_tool("navigation.go_to", {"location": "kitchen"})

Response: "Navigation started. ETA: 15 seconds."
```

### Example 3: System Status

```
You: What's the system status?

OpenCode calls: tankos_system_status()

Response: {
  "uptime": "up 2 days, 5 hours",
  "memory": "total 8.0G, used 3.2G",
  "disk": "/dev/sda1 50G 12G 35G 26%",
  "tools_available": 1166
}
```

### Example 4: Send SMS

```
You: Send an SMS to Shashi saying "Hello!"

OpenCode calls: tankos_invoke_tool("modem.send_sms", {
  "message": "Hello!",
  "to": "shashi"
})

Response: "SMS sent successfully to Shashi (+917860245819)"
```

### Example 5: Use AI Providers

```
You: What providers are available?

OpenCode calls: tankos_list_providers()

Response: {
  "total_providers": 10,
  "configured": 8,
  "providers": {...}
}
```

### Example 6: Call Groq (Fastest)

```
You: Ask Groq to explain quantum computing

OpenCode calls: tankos_call_llm("groq", "Explain quantum computing in simple terms")

Response: "Quantum computing uses quantum bits (qubits) that can exist in multiple states simultaneously..."
```

### Example 7: Auto-Fallback LLM

```
You: Write a Python function to sort a list

OpenCode calls: tankos_call_llm_fallback("Write a Python function to sort a list using quicksort")

Response: "def quicksort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr) // 2]\n    ..."
```

## Troubleshooting

### MCP Server Won't Start

1. Check Python dependencies:
   ```bash
   pip install mcp "mcp[cli]"
   ```

2. Verify the MCP server file exists:
   ```bash
   ls -la tank_os/agent_framework/mcp_server.py
   ```

3. Test the server manually:
   ```bash
   python3 tank_os/agent_framework/mcp_server.py
   ```

### Tools Not Appearing in OpenCode

1. Check `opencode.json` is in the project root
2. Verify the MCP server is enabled:
   ```bash
   opencode mcp list
   ```

3. Restart OpenCode after making changes

### Permission Errors

Ensure the TankOS Agent Framework has proper permissions:
```bash
chmod +x tank_os/agent_framework/mcp_server.py
chmod +x tank_os/agent_framework/*.py
```

## Advanced Configuration

### Custom Environment Variables

Add custom environment variables to `opencode.json`:

```json
{
  "mcp": {
    "tankos": {
      "type": "local",
      "command": ["python3", "tank_os/agent_framework/mcp_server.py"],
      "environment": {
        "PYTHONPATH": ".",
        "TANK_CAM_URL": "http://192.168.31.176",
        "TANK_API_KEY": "your-api-key"
      }
    }
  }
}
```

### Multiple MCP Servers

You can combine TankOS with other MCP servers:

```json
{
  "mcp": {
    "tankos": {
      "type": "local",
      "command": ["python3", "tank_os/agent_framework/mcp_server.py"]
    },
    "github": {
      "type": "remote",
      "url": "https://mcp.github.com/mcp"
    }
  }
}
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    OpenCode Terminal                         │
│  (AI coding agent with MCP support)                         │
└─────────────────────┬───────────────────────────────────────┘
                      │ MCP Protocol
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                 TankOS MCP Server                            │
│  (mcp_server.py — wraps Agent Framework)                    │
└─────────────────────┬───────────────────────────────────────┘
                      │ Tool Invocation
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              TankOS Agent Framework                          │
│  (1,166+ tools across 18 categories)                        │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    TankOS Hardware                           │
│  Jetson · UNO Q · ESP32 · Camera · Motors · Sensors         │
└─────────────────────────────────────────────────────────────┘
```

## Links

- [OpenCode Documentation](https://opencode.ai/docs/)
- [TankOS Documentation](./)
- [MCP Protocol](https://modelcontextprotocol.io)
- [TankOS Agent Framework](../tank_os/agent_framework/)

## Support

For issues with:
- **OpenCode**: Visit https://github.com/anomalyco/opencode
- **TankOS**: Open an issue in The-Tank-Project repository
- **MCP Integration**: Check this documentation or open an issue
