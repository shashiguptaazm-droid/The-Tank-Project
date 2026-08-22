CHASSIS v1 SLIM   ·   185 × 100 × 24 mm
──────────────────────────────────────
• 52 % slimmer than the probots stock chassis (50 → 24 mm)
• Drop-in footprint + 4 shock pivots → works with the probots wheels
• 4-way attachment: belt clip · VESA 75×75 / M3 · 4× N52 magnet · shock pivots
• Pi 5 recess @ 22 mm  → fits  Pi 5 + M.2 HAT+ + Active Cooler
• 2× 18650 / 1× 14500 / 4× AA (toggle battery_type in main.scad)
• 2× TT motor bays (drop-in) + countersink screw holes
• 4× VESA bosses → stack extra payload
• 9 cooling vent slots (22 × 1.6 mm)
• Single FDM print, no supports, 0.20 mm layers, PETG / ASA

FILES
─────
main.scad             parametric OpenSCAD source
render_check.py       python3 –constraint-checker (no OpenSCAD needed)
README.md              full design doc
BOM.csv                machine-readable bill of materials
tech_drawing_top.svg   top view
tech_drawing_side.svg  side view
assembly.md            step-by-step build
stl/                   output dir → openscad -o stl/chassis_v1_slim.stl main.scad

QUICK START
───────────
sudo apt install openscad
openscad -o stl/chassis_v1_slim.stl main.scad
python3 render_check.py main.scad        # → 21 pass · 0 warn · 0 err
print:  PETG · 0.20 mm · 4 walls · 30 % infill · no supports · 8 mm brim
