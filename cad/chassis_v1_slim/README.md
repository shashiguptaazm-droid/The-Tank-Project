# Ultra-Slim Portable & Attachable Chassis — v1

> **For:** Raspberry Pi 5 (drop-in)
> **Butt of:** `probots.co.in` tank-chassis shock-absorber pattern
> **Goal:** keep the bog-standard tracking footprint, shed 50 % of the body
> height, and turn the chassis into a portable, attachable platform you can
> clip to a belt, sit on a fridge with magnets, or stack accessories on
> via a VESA-style deck.

| Metric | probots stock | **chassis_v1_slim** |
|---|---:|---:|
| Length | 185 mm | **185 mm** (drop-in) |
| Width | 97 mm | **100 mm** (slight clearance) |
| Height | 50 mm | **24 mm** *(52 % slimmer)* |
| Wall thickness | ~1.6 mm ABS | **2.4 mm PETG/ASA** |
| Print volume required | ≤ 200 mm³ | **185 × 100 × 24 mm** |
| Pi 5 mounting | none | **4 × M2.5 at 58 × 49 mm** |
| Battery | 18650 × 2 | configurable (18650 × 2 · 14500 × 1 · AA × 4) |
| Motors | TT × 2 | **drop-in bracket, M3 countersink** |
| Attachment | none | **belt clip + VESA + 4-corner magnet + shock pivots** |
| OpenSCAD parametric | n/a | ✅ 40 constants at the top of `main.scad` |

---

## 1. Why "ultra-slim" matters

The probots chassis wastes about 30 mm of vertical space on top of an
empty hull just to seat a couple of TT motors that only need ~24 mm of
axial room. The slim chassis flattens that envelope by:

1. **Mounting motors inside the side rails** rather than in a free-floating pocket.
2. **Recessing the Pi** flush with the body, so the PCB + M.2 HAT+ stack
   sits *below* the top deck instead of above it.
3. **Side-loading the battery** so it lives in a horizontal bay that does
   not require a removable lid (the user's battery cap sits in a side rail).

Net result: 24 mm body height with the Pi 5 *fully populated with the
M.2 HAT+* still inside the chassis outline.

---

## 2. Files in this folder

| File | Purpose |
|---|---|
| `main.scad` | Parametric OpenSCAD source — edit top constants to retune |
| `render_check.py` | Pure-Python validator that runs against the constants (no OpenSCAD needed) |
| `README.md` | This document |
| `BOM.csv` | Machine-readable bill of materials |
| `tech_drawing_top.svg` | Top view technical drawing |
| `tech_drawing_side.svg` | Side view technical drawing |
| `assembly.md` | Step-by-step assembly guide |
| `stl/` | Output directory – `openscad -o stl/chassis_v1_slim.stl main.scad` |

---

## 3. How to render

### 3.1 Quick check (preview)
```bash
sudo apt install openscad           # one-time
openscad --camera=10,40,90,55,0,15,200 main.scad     # open GUI
```

### 3.2 Export to STL (for slicing)
```bash
openscad -o stl/chassis_v1_slim.stl main.scad
```

### 3.3 Render any parametric variant
Edit the top-of-file constants (e.g. `chassis_total_h = 28;`) and re-render.

### 3.4 Run the static printability check
```bash
python3 render_check.py             # passes 21/21 with stock constants
```
Output today:
```
summary: 21 pass · 0 warn · 0 err
target  : 185×100×24 mm  vs probots 185×97×50 mm  (48% as tall)
```

---

## 4. Design philosophy

### 4.1 Drop-in compatible footprint

The **185 × 100 mm** footprint is **deliberately the same as the
probots bracket pattern** so you can swap the top deck for motors,
wheels, or tracks without redesigning anything underneath. The 4
shock-absorber pivot holes (`include_shock = true`) accept M3 bolts
at the same coords as the probots brackets – your existing wheels
and springs work **unchanged**.

### 4.2 "Attachable" implemented four ways

| Mechanism | Where | Use case |
|---|---|---|
| **Belt clip** | rear, snap-fit | portable on a hip or backpack strap |
| **VESA-style deck** | top, 75×75 mm / M3 | stack a robotic arm, LiDAR turret, payload box |
| **Magnet pockets** | 4 corners, underside, 6×2 mm N52 | stick to a fridge, white-board, server rack |
| **Shock-absorber pivots** | 4 corners, M3 pairs | reuse the probots springs + wheels |

### 4.3 Printability – flat-orientation, PETG-friendly

* Max overhang angle: **45°** – no support material needed.
* Min wall thickness: **2.4 mm** – survives most FDM tensions.
* Corner radius: **4 mm** – no sharp internal corners that lift on PETG.
* No bridge > **22 mm** (vent slot length is 22 mm, height 1.6 mm, ties at both ends).

Recommended print settings (for a Creality Ender-3 v3 SE or any 220³ FDM):

| Setting | Value |
|---|---|
| Layer height | **0.20 mm** |
| Print speed | **60 mm/s** outer wall |
| Material | **PETG** (recommended) / ASA / ABS+ |
| Infill | **30 % grid** (60 % around the motor bays + 100 % under screws) |
| Walls / perimeters | **4** (≥ 2.4 mm thick) |
| Top / bottom layers | **5 / 4** |
| Bed temp | **80 °C** (PETG) / **105 °C** (ASA) |
| Hot end temp | **235 °C** (PETG) / **245 °C** (ASA) |
| Brim | **8 mm** recommended for first print |
| Supports | **none** required |
| Orientation | as designed – bottom flat, top up |

### 4.4 Optional sub-modules (toggle in source)

```openscad
include_belt_clip = true;   // rear 28×70 mm snap-fit cavity
include_vesa      = true;   // 75×75 mm VESA deck on the top
include_magnets   = true;   // four N52 6×2 disc-magnet pockets
include_shock     = true;   // probots shock-absorber pivot bosses
include_vents     = true;   // nine 22×1.6 mm side slots for cooling
```

Set any to `false` to suppress the corresponding features (e.g. for a
bench-top build with no need for magnets).

---

## 5. Forest of modules

Open `main.scad` and read top-down:

* **Parameters** — every dimension lives at the top, all in mm.
* **Derived constants** — recomputed once, used everywhere.
* **Utility modules** — `rrect_2d`, `rbox`, `countersink`, `hole_grid`.
* **Sub-systems** — `pi_recess`, `battery_bay`, `motor_bays`, `vesa_pattern`,
  `belt_clip_socket`, `magnet_pockets`, `vent_slots`, `shock_mounts`.
* **Assembly** — `chassis_body()` unions the positives, subtracts the negatives,
  and is the single `render()` root.

The explosion helper (`explode = 25` in the debugger block) lifts the top
deck off the base so you can visually confirm clearances in the GUI
without re-modelling.

---

## 6. Compatibility matrix

| You have … | Will the slim chassis accept it? |
|---|---|
| probots TT motors (yellow) | ✅ — drop-in the bracket cavity |
| probots shock-absorbers + tracks | ✅ — `include_shock = true` |
| Raspberry Pi 5 + M.2 HAT+ + Active Cooler | ✅ — `pi_stack_max_h = 22 mm` |
| Raspberry Pi Camera Module 3 (IMX708) | ✅ — front clearance > 6 mm |
| ESP32-S3 eyes (UART) | ✅ — wiring routed through rear slot |
| ReSpeaker 4-Mic array | ✅ — front slot above Pi recess |
| 18650 × 2 (any chemistry) | ✅ — `battery_type = 0` |
| 14500 × 1 (in series 3.7 V sources) | ✅ — `battery_type = 1` |
| AA × 4 (Ni-MH) | ✅ — `battery_type = 2` |
| N20 micro metal gearmotor | ⚠️ — slightly fussy, set `motor_body_dia = 12` |

---

## 7. Limitations & TODO

* **Single-piece print.** The chassis is one body; no assembly required for
  the chassis itself, only for the **belt clip** (printed as a separate
  piece — see `assembly.md` §3).
* **No electronics cover.** The Pi sits recess-mount; for outdoors, 3D-print
  or laser-cut a top deck cover (Q1 of next iteration).
* **No AprilTag dock station included** — that's a different file.
* **Belt clip is printed separately** because printing a clip in-situ
  violates the 45° overhang budget. File: `extras/belt_clip.scad` (TODO).

---

## 8. Where this fits in the tank project

This file lives at `the tank project/cad/chassis_v1_slim/` — parallel to
PHASES.md, but focused on the **physical** layer. Once the chassis is
printed and the Pi mounts cleanly, the existing
`tank_ws/src/tank_motion/`, `tank_vision/`, `tank_sensors/` packages
plug straight in.

| Phase | What this chassis unlocks |
|---|---|
| P8 – Real hardware on-robot deploy | ✅  the missing physical box for the entire stack |
| P9 – Bidirectional AI ↔ Pi bridge | ✅  the chassis **is** the Pi the bridge talks to |
| P10½ – AI humanness | ✅  portable enough to demo to test users without a lab |
