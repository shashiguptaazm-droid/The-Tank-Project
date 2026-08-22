# Assembly Guide — Chassis v1 Slim

> **Goal:** from filament + fasteners → fully mobile, attachable tank
> chassis with a Raspberry Pi 5 underneath, ready for `ros2 launch
> tank_bringup robot.launch.py`.

---

## 0. Print checklist

* [ ] `openscad -o stl/chassis_v1_slim.stl main.scad`  ← produces STL
* [ ] Slice with the settings in `README.md §4.3` (PETG, 0.20 mm, 4 perimeters, no supports)
* [ ] Confirm brim is enabled (8 mm) – the shock pivot bosses are on
  the bottom corners and lift on the first layer otherwise
* [ ] Print **one** spare belt clip before committing (see §3)

---

## 1. Quick fastener inventory

| Qty | Item | Where it goes |
|---|---|---|
| 4 | M2.5 × 12 mm nylon standoffs | Pi PCB → M.2 HAT+ stack |
| 4 | M2.5 × 6 mm pan-head screws | clamp Pi to chassis bosses |
| 4 | M3 × 8 mm countersunk | motors into the body cradle (countersink() in OpenSCAD) |
| 8 | M3 × 8 mm cap-head | shock-absorber pivot pins (2 per corner × 4 corners) |
| 4 | M3 × 8 mm cap-head + hex nut | VESA deck accessories |
| 4 | N52 6×2 mm disc magnets | press-glue into the four corner pockets |
| 1 | JST-PH 2-pin pigtail | battery output to BMS / buck converter |

A `BOM.csv` line-by-line machine-readable copy ships in this folder.

---

## 2. Step-by-step — Pi stack

```
   ┌──────────────────────┐  ← Pi Camera Module 3 (ribbon toward the front)
   │  Pi 5 + M.2 HAT+     │
   │  + Active Cooler     │
   └─────────┬────────────┘
             │ 4× M2.5 × 12 mm standoff (sets pi_stack_max_h = 22 mm)
   ┌─────────▼────────────┐
   │  Chassis v1 Slim     │  ← sit on top of the Pi bosses
   └──────────────────────┘
```

1. Drop the four Nylon 12 mm standoffs through the M2.5 holes in the Pi PCB.
2. Place the M.2 HAT+ on top, screw down (4× M2.5).
3. Plug the **active cooler** fan header into the Pi 5's J5 fan header.
4. Slide the assembled Pi+stack into the chassis recess, USB-A ports
   facing the rear (gives access from the back).
5. Drive **4× M2.5 × 6 mm pan-head screws** through the chassis bosses
   into the standoffs — hand-tight, do NOT torque (PETG cracks at 0.4 Nm
   on cheap inserts).

> **Tip** — if the stack is too tight, lower `pi_stack_max_h` in `main.scad`
> and re-print.  `pi_stack_max_h = 20` gives 2 mm headroom for cabling.

---

## 3. Belt clip (separate print)

The belt clip cannot print *in situ* (would require supports + overhanging
latches).  Print separately:

1. In OpenSCAD, set `include_belt_clip = false`, comment-out the rear
   boss block, then `render()` just the clip itself — save as
   `extras/belt_clip.stl`.
2. Print with **PETG**, 0.16 mm layers, 6 perimeters, 100 % infill
   (it's a spring, not a structural part).
3. Slide the clip straight into the rear socket — the two micro-latches
   *click* into the body detents.

---

## 4. Battery + power

1. Slide **2× 18650** (or 1× 14500 / 4× AA — set `battery_type` accordingly)
   into the side bay.
2. Solder the JST-PH pigtail **before** sliding the cells in – the bay is
   one-handed fitting.
3. Connect to your BMS or **buck-boost converter** (TP5000 + TPS63060
   recommended for 3S-1S 5 V out).
4. The battery bay has 4 mm of PCB-clearance above the floor – route the
   battery wires through the front vent slot.

---

## 5. Motors + drivetrain

1. Drop two TT-style motors (3–12 V, 21 mm body OD) into the side bays.
2. Drive **2× M3 × 8 mm countersunk screws** through the chassis cradle
   into the motor's threaded ear-holes.
3. Solder the motor PWM wires to your BTS7960 inputs (or L298N if
   bench-testing). Bring the two motor wires out of the front vent slots.

---

## 6. Optional: shock absorbers

1. Loop the probots 4-spring suspension brackets onto the four pairs of
   pivot bosses.
2. Thread **M3 × 8 mm cap-head** through each bracket pivot.
3. The brackets you already own will work — bolt-pattern matches because
   `motor_pitch_x` and `shock_hole_d` were derived from probots.

---

## 7. First boot

```bash
# Pi 5 side
ssh pilot@tank.lan
sudo systemctl status tank_bringup
ros2 topic list | grep -E 'cmd_vel|odom|pan_tilt'
ros2 run teleop_twist_keyboard teleop_twist_keyboard cmd_vel:=cmd_vel
```

If `cmd_vel → motor_controller` doesn't fire, the 18650 might be empty —
drop the battery voltage to the **2.8 V/cell** low-batt threshold readings
in `tank_health/health_node.py` if necessary.

---

## 8. Maintenance / repair

| Symptom | Probable cause | Fix |
|---|---|---|
| Pi can't be removed | over-tightened M2.5 | back off, hand-tighten only |
| Mounts lifted off the bed | no brim | reprint with 8 mm brim |
| Belt clip loose | wrong PETG (PLA) | PETG has the spring memory; PLA won't latch |
| Motors stutter on first start | badges facing wrong way | reverse polarity on the BTS7960 input |
| Shock pivots scratch the body | vents too close | adjust `corner_r` from 4 → 6 mm |

---

## 9. Photo placeholders

* `[before-print]` — empty bed, PrimaSELECT PETG loaded
* `[first-layer]` — brim forming around the four corner pivots
* `[after-print]` — chassis with Pi seated, USB-A ports at the rear
* `[on-robot]` — fitted onto the probots suspension, ready for `tank_bringup`

---

## 10. Material & orientation risks (PETG)

These are real-world failure modes learned from PETG shrinkage, elasticity, and adhesive limits. Tackle them in this exact order so you don't waste a 6-hour print.

### R1 — Bed adhesion at the shock pivot bosses

The 4 shock-mount bosses sit at the **extreme corners** of the bed. PETG shrinkage curls outer corners up, which can warp the bracket skew and misalign the suspension permanently.

* ✅ **Enable a brim (8 mm)** in the slicer, *all* the way round.
* ✅ First-layer **bed = 80 °C** for PETG; do **not** crank it higher (then PETG sticks too aggressively and tears the build plate when you remove the brim).
* ✅ First-layer **speed = 25 mm/s** even if the rest of the print is 60 mm/s — gives the corners time to fuse with the brim.

### R2 — Belt clip is a spring; choose material AND orientation

The belt clip (separate print, see [§3](#3-belt-clip-separate-print)) is a mechanical spring. In **PLA** it will permanently bend, in **PETG** it has the right elastic memory — but only if the layers run **perpendicular to the bending axis**.

* ✅ Material: **PETG only** (PrimaSELECT, Polymaker, eSun — all work).
* ✅ Infill: **100 %** (it's a 6 cm³ part, no perf penalty).
* ✅ Walls: **6 perimeters** (1.6 mm walls).
* ✅ Layer height **0.16 mm**.
* ✅ Print the clip **flat** on the bed so layers stack vertically along the flex direction — the latches then actuate like an integral spring.

### R3 — N52 magnets pop out of PETG pockets if glued naively

PETG layer lines are chemically inert → super-glue (CA) doesn't bite well; the 6 × 2 mm disc magnets can rip out under pull forces.

* ✅ Score / sand the **inside walls** of each pocket with 120-grit so the glue has tooth.
* ✅ Use **two-part epoxy** (e.g. JB Weld, Gorilla 5-min Epoxy) **OR** rubber-toughened CA glue (e.g. 3M 08001).
* ✅ **Check polarity on the bench** before the epoxy cures (south facing the chassis bottom = stick-to-metal bonus).
