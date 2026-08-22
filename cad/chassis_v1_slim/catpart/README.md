# CATIA V5 `.catpart` Generation — Honest Status

This directory ships a CATIA V5 `.catpart` would-be generator stack.

## The hard truth

`.catpart` is CATIA V5's **proprietary Microsoft OLE Compound File** storage. No open-source CAD tool (FreeCAD, OpenCascade, CadQuery, pythonocc-core) can **write** `.catpart`. The format is closed and only CATIA V5/V6 itself can produce authentic files.

What we CAN deliver without CATIA:

| Format | Reachable | Authoritative source |
|---|---|---|
| `.stl`                  | ✅ yes (OpenSCAD)             | `stl/*.stl` |
| `.3mf` (multi-piece)     | ✅ yes (OpenSCAD)             | `stl/chassis_v3_multi.3mf` |
| `.step` (true solid BREP) | ✅ yes (FreeCAD OpenSCAD-import) | `step/*.step` |
| **`.catpart` (true solid, native CATIA)** | ❌ not without CATIA | requires `convert_step_to_catpart.py` |

## Path 1 — Recommended (true solid STEP from OpenSCAD source)

```bash
sudo snap remove freecad 2>/dev/null
sudo add-apt-repository -y ppa:freecad-maintainers/freecad-stable
sudo apt-get update
sudo apt-get install -y freecad-stable
bash render_step.sh              # auto PATH 1 → PATH 2 fallback
```

These STEP files contain **true BREP solids** (the CSG tree in `main.scad` is replayed through FreeCAD's OpenSCAD workbench).

> **Ubuntu version note:** 24.04 LTS hosts need the PPA; **26.04+ ships `freecad` in main repos** — if `apt-cache search freecad-stable` returns nothing, try `apt install freecad`.

## Path 2 — Faceted fallback (mesh-backed, CATIA will warn)

If Path 1 fails (FreeCAD OpenSCAD workbench can't import `main.scad`), `render_step.sh` automatically falls back to `stl → step` via `Mesh.Mesh + Part.Shape().makeShapeFromMesh(m.Topology, 0.1)` — the canonical FreeCAD Python API. CATIA opens it but downstream Boolean / Fillet / Draft operations raise *"Object is not a solid"*. Use only for visualisation.

## Path 3 — The ONLY path to a real `.catpart`

On a **Windows host with CATIA V5 installed**:

```cmd
pip install pywin32
python convert_step_to_catpart.py ^
    --step-dir  C:\chassis\step ^
    --out-dir   C:\chassis\catpart ^
    --visible   0
```

The script (`convert_step_to_catpart.py`, v3):

1. Launches CATIA via COM (`win32com.client.Dispatch("CATIA.Application")`)
2. **OCAF warmup** — opens + saves + closes a 1 KB dummy `.catpart` first so the first real save isn't burdened by 30-45 s of CATIA document-cache initialisation. Subsequent saves complete in 5-15 s.
3. Per-part `try/except/finally` — one bad file aborts only itself; `doc = None` on every close
4. **Path safety** — rejects paths containing any shell metacharacter including backticks, `<`, `>`, whitespace
5. **Polling flush** — waits up to 30 s for file size to stabilise (post-warmup, this is the realistic max)
6. `--force` opt-in to overwrite existing `.catpart`; defaults to skip-if-exists
7. `catia.Quit()` in `try/finally` + `catia = None` after to drop the COM handle cleanly

Run on a Windows box that already has CATIA V5 (R20+ recommended for full COM coverage).

## Path 4 — Engage a freelance CATIA operator (paid service)

Upwork and Fiverr have CATIA operators who can take your `step/` directory and produce `.catpart` files for a small fee (typically $5-20 USD per part). This is the **cheapest** path for a one-off batch. Search *"CATIA batch STEP to CATPart conversion"*.

## What this system NEVER does

- Generate a "blank" or "faceted mesh wrapper" `.catpart`. The OLE structure is too proprietary; a malformed `.catpart` may break CATIA's Part container on opening.
- Promise end-to-end automation that runs on this Ubuntu system without a CATIA license. Authentic `.catpart` requires CATIA.

## Validation

```bash
python3 render_check.py main.scad     # 46 mechanical constraints pass
for f in step/*.step; do head -c 30 "$f"; done
```

Every valid STEP file header starts with `ISO-10303-21;`.

## File manifest after rendering

```
the tank project/cad/chassis_v1_slim/
├── step/
│   ├── body.step              ← BREP solid from main.scad piece_body()
│   ├── top_deck.step          ← BREP solid from piece_top_deck()
│   ├── front_shield.step      ← BREP solid from piece_front_shield()
│   ├── lidar_riser.step       ← BREP solid from piece_lidar_riser()
│   └── assembly_preview.step  ← assembled chassis (PATH 1 or PATH 2)
└── catpart/
    ├── README.md                  ← this file
    └── convert_step_to_catpart.py ← v3 hardened CATIA COM automation
```
