# 🖼️ Visual Assets — The Tank Project

> All diagrams are hand-crafted SVGs. They render natively in GitHub,
> any markdown viewer, and modern browsers.

## Contents

| File | Description |
|------|-------------|
| [`blueprint-master.svg`](blueprint-master.svg) | **Full humanoid robot blueprint** — head, neck, torso, arms, hands, legs, circuit board, rotary joint, component legend. Traced from original hand-drawn schematic. |
| [`architecture.svg`](architecture.svg) | 6-layer system stack: Jetson Orin Nano → Arduino → ROS2 → TankOS Core → Tank Shell → Simple Internet, plus hardware peripherals map |
| [`wiring.svg`](wiring.svg) | Full pinout schematic: Arduino UNO R4 GPIO assignments, I²C bus map, BTS7960 motor driver wiring, Jetson USB connections, serial bridge protocol |
| [`cognitive.svg`](cognitive.svg) | 22-system cognitive architecture: Perception → Attention → Reasoning → Planning → Decision → Learning → Memory → Emotion → Metacognition pipeline |
| [`head-neck-closeup.svg`](head-neck-closeup.svg) | Head sensor array: AI Camera, Depth Camera, Thermal MLX90640, MPU6050, Dual Round Eyes, Speaker, USB-C Hub routing. Neck with linear actuator + 360° rotational joint. |
| [`torso-power-distribution.svg`](torso-power-distribution.svg) | Torso bays: Main Compute (Jetson + Arduino), Storage (M.2 + USB HDD), ESP32 Node Bay, Power Pebble Docks. 4 isolated power rails with INU2604 monitoring. |
| [`arm-hand-actuators.svg`](arm-hand-actuators.svg) | Arm actuator chain: Shoulder (3× linear DC actuators), Upper Arm (connector stack), Elbow, Forearm (ESP32-S3 Hand Manager), 5-finger hand (10 DOF), servo mapping. |

## CAD Assets

3D-printable design files live in [`../cad/chassis_v1_slim/`](../cad/chassis_v1_slim/):

| Format | Contents |
|--------|----------|
| `stl/` | 3D-printable chassis parts (body, top deck, lidar riser, front shield, DSI display mount) |
| `step/` | STEP exports for CAD interchange |
| `*.3mf` | Multi-part 3MF bundles (chassis_v3_multi, body_only) |
| `*.scad` | OpenSCAD parametric sources |
| `*.svg` | Technical drawings (top view, side view) |
| `BOM.csv` | Bill of materials with part numbers, prices, and links |

## Adding Photos

Place real build photos here:
- `build/` — assembly progress shots
- `demo/` — video thumbnails, demo screencaps
- `competition/` — presentation slides, posters

> 📸 **TODO:** Add real hardware photos once the Jetson Orin Nano + Arduino UNO R4 chassis is assembled.