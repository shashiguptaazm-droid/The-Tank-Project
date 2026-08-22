# TankOS — Complete Build Specification for Codex

## Mission

Build TankOS, a graphical AI operating environment for The Tank Project.

TankOS is not a replacement Linux kernel. It is a complete operating environment that boots automatically on NVIDIA Jetson Orin Nano and becomes the only interface the user sees.

Linux exists only as the hardware abstraction layer.

The user should never interact with the Jetson desktop.

---

## Primary Goals

TankOS must be:

- AI-first
- Voice-first
- Touch-first
- Offline-first
- ROS2-native
- Modular
- Plugin-based
- Highly animated
- Recoverable
- Production quality

---

## Base Platform

**Operating System:**
- Jetson OS Lite (64-bit)

**Middleware:**
- ROS2 Humble

**Language:**
- Python 3.12+

**GUI:**
- Qt6 / PySide6

**Rendering:**
- OpenGL accelerated where available

**Display:**
- 7-inch DSI touchscreen

---

## Boot Process

```
Power On
    ↓
Pi Firmware
    ↓
Linux Kernel
    ↓
systemd
    ↓
tank-init.service
    ↓
Hardware Detection
    ↓
ROS2 Core
    ↓
TankOS Core
    ↓
Tank Shell
    ↓
Dashboard
```

No Jetson desktop should ever appear.

---

## TankOS Architecture

TankOS consists of four layers.

### Layer 1 — Linux

- Drivers
- Networking
- Audio
- USB
- Bluetooth
- Power

### Layer 2 — ROS2

Existing packages remain unchanged.

- tank_motion
- tank_memory
- tank_assistant
- tank_navigation
- tank_security
- tank_health
- tank_dashboard
- tank_meta
- tank_display
- tank_patrol
- tank_task
- tank_personalize
- tank_command_bridge
- etc.

### Layer 3 — TankOS Core

Contains:

- Application Manager
- Plugin Manager
- Notification Manager
- Permission Manager
- Display Manager
- Theme Manager
- Voice Manager
- Window Manager
- Settings Manager
- Update Manager
- Power Manager
- Hardware Manager
- Event Bus
- AI Manager

### Layer 4 — Tank Shell

Provides graphical interface.

---

## Tank Shell

The shell replaces a desktop environment.

### Main Screens

- Home
- AI Chat
- Camera
- Navigation
- Memory
- Security
- Patrol
- Files
- Diagnostics
- Developer Mode
- Settings
- Power
- Updates

---

## Dashboard

### Top Bar

- Time
- Battery
- WiFi
- LTE
- CPU
- Temperature
- Emotion

### Center

- Camera
- AI Avatar
- Map
- Status

### Bottom Dock

- Chat
- Robot
- Security
- Vision
- Files
- Settings
- Notifications

---

## Window Manager

Supports:

- Floating windows
- Dialogs
- Fullscreen mode
- Touch gestures
- Keyboard
- Mouse
- Controller
- Window animations
- Transparency
- Blur

---

## AI Integration

TankOS communicates only through ROS topics and existing bridge APIs.

Never duplicate logic.

The GUI is presentation only.

Every feature must reuse existing Python modules.

---

## Voice

- Always listening
- Wake word
- Speech recognition
- Intent routing
- Conversation
- Streaming responses
- Interruptible speech

---

## Memory

- Chat history
- Long-term memory
- Vector search
- Knowledge search
- Conversation summaries
- Timeline
- Memory browser

---

## Security

- Live camera
- Motion detection
- Recording
- Playback
- Event history
- Alerts
- Face recognition
- Fingerprint unlock
- Emergency stop

---

## Navigation

- SLAM map
- Robot position
- Waypoint editor
- Patrol routes
- Dock status
- Obstacle display
- LiDAR visualization

---

## Vision

- Live camera
- YOLO detections
- Bounding boxes
- Object list
- Tracking
- AprilTag detection
- Thermal overlay
- Future sensor support

---

## Robot Control

- Joystick
- Touch controls
- Keyboard
- Voice commands
- Gesture controls
- Emergency stop
- Speed selector
- Servo controls
- Camera controls

---

## Settings

- Network
- Audio
- Voice
- AI
- Personality
- Emotions
- Privacy
- Power
- Display
- Developer
- Hardware
- ROS

---

## Plugin System

TankOS loads plugins dynamically.

Every plugin contains:

- manifest.json
- plugin.py
- assets/
- settings/

Plugin API:

- initialize()
- shutdown()
- widget()
- settings()
- commands()
- events()

---

## Event Bus

Everything communicates through a centralized event system.

Examples:

- Battery changed
- Emotion changed
- Wake detected
- Camera connected
- Robot moving
- Memory updated
- Plugin loaded
- Notification received

---

## Notifications

- Animated
- Priority
- Persistent
- Grouped
- Speech capable

---

## Theme Engine

- Dark mode
- Light mode
- Custom themes
- Accent colors
- Animated backgrounds
- Wallpaper
- Icons
- Fonts

---

## Animation Engine

- 60 FPS target
- Transitions
- Fade
- Slide
- Zoom
- Physics
- Spring
- Particle effects
- Robot boot animation
- Emotion animations

---

## Hardware Manager

Detects:

- Displays
- USB devices
- Serial devices
- Cameras
- ESP32
- Sensors
- Power
- Storage
- Battery

Automatically reconnects disconnected hardware.

---

## Diagnostics

- CPU
- RAM
- GPU
- Disk
- Battery
- ROS Nodes
- ROS Topics
- Network
- Latency
- Temperatures
- Logs
- Errors
- Warnings

---

## Developer Mode

- ROS Topic Viewer
- Node Manager
- Package Manager
- Log Viewer
- Shell
- Python Console
- File Explorer
- Bridge Inspector
- API Tester
- Performance Graphs

---

## Recovery

- Safe Mode
- Failsafe boot
- Crash recovery
- Automatic restart
- Watchdog
- Log collection

---

## File Structure

```
tank_os/
├── core/
├── shell/
├── widgets/
├── windows/
├── animations/
├── themes/
├── plugins/
├── services/
├── voice/
├── ai/
├── settings/
├── notifications/
├── diagnostics/
├── recovery/
├── startup/
├── assets/
├── tests/
└── docs/
```

---

## Startup Sequence

1. Initialize logging
2. Load configuration
3. Initialize hardware
4. Start ROS
5. Verify services
6. Initialize plugins
7. Initialize GUI
8. Start AI
9. Start voice
10. Open dashboard
11. Accept user interaction

---

## Coding Rules

- No duplicated functionality.
- Reuse existing ROS packages.
- All communication through ROS or internal event bus.
- Strong typing.
- Thread-safe.
- Async where appropriate.
- Graceful degradation.
- Offline-first.
- Modular.
- Testable.
- Documented.
- Every component must have unit tests.
- No blocking GUI thread.
- Never assume hardware exists.
- Always provide simulation mode.

---

## Final Objective

TankOS should feel like a commercial AI operating system rather than a Jetson application.

The user should believe they are interacting with an intelligent robotic operating system.

Existing ROS packages remain the functional backend.

TankOS becomes the graphical brain that unifies every subsystem into one seamless experience.
