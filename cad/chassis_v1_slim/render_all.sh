#!/usr/bin/env bash
# ====================================================================
#  render_all.sh — full chassis_v3 pipeline: per-piece STL + 3MF + STEP
#  + exploded view + annotated PNG + BOM/DXF extras
#  ──────────────────────────────────────────────────────────────────
#  Usage:
#      bash render_all.sh                # full pipeline (all 8 steps)
#      bash render_all.sh --no-step      # skip STEP (faster)
#      bash render_all.sh --check        # just render_check.py
#      bash render_all.sh --no-extras    # skip BOM/DXF/PNG extras (step 8)
#
#  Outputs:
#      stl/                          per-piece STL × 5
#      stl/assembly_preview.stl      flush assembly
#      stl/assembly_exploded.stl     exploded view (40 mm gap per piece)
#      stl/chassis_v3_multi.3mf      multi-object Bambu/Orca bundle
#      stl/body_only.3mf             legacy single-piece fallback
#      stl/chassis_v3.step           (FreeCAD Cmd) parametric CAD
#      stl/preview/                  PNG renders per piece + assembly
#      stl/preview/annotated_assembled_chassis.png  labelled render from step 8
#      BOM_enriched.csv              BOM with Supplier/MPN/SKU/USD columns
#      dxf/<piece>_flat.dxf × 5      per-piece flat patterns (laser-cut refs)
#
#  Tested on OpenSCAD 2021.01.
# ====================================================================

set -euo pipefail
cd "$(dirname "$0")"

PIECES=(body top_deck front_shield lidar_riser dsi_display)
SCAD=main.scad
OUTDIR=stl
PREV_DIR="$OUTDIR/preview"
mkdir -p "$OUTDIR" "$PREV_DIR"

step=true
check_only=false
extras=true
for a in "$@"; do
    case $a in
        --no-step)   step=false ;;
        --no-extras) extras=false ;;
        --check)     check_only=true ;;
        *) echo "unknown arg: $a" ; exit 1 ;;
    esac
done

echo "─── 1. Static parameter check ───"
python3 render_check.py "$SCAD"
if $check_only; then exit 0; fi

if ! command -v openscad >/dev/null 2>&1; then
    echo "[ERR ] openscad not found — apt install openscad then rerun" >&2
    exit 2
fi

echo "─── 2. Render each piece as STL ───"
for piece in "${PIECES[@]}"; do
    flags=""
    for p in "${PIECES[@]}"; do
        if [ "$p" = "$piece" ]; then flags="${flags}RENDER_${p^^}=true;"
        else                          flags="${flags}RENDER_${p^^}=false;"
        fi
    done
    openscad --export-format=binstl \
             -o "$OUTDIR/$piece.stl" \
             -D "$flags" "$SCAD"
    echo "  ✓ $OUTDIR/$piece.stl ($(du -h "$OUTDIR/$piece.stl" | cut -f1))"
done

echo "─── 3. Multi-object 3MF (Bambu Studio recommended) ───"
#  Native OpenSCAD 3mf export flattens to a single merged <object>; we want
#  every per-piece STL to appear as a separate <object> in the build list so
#  the slicer can assign per-object settings.  combine_3mf.py auto-discovers
#  the per-piece STLs in --in-dir (single source of truth = whatever
#  bash render_all.sh produced in step 2 above).
python3 combine_3mf.py --in-dir "$OUTDIR" --out "$OUTDIR/chassis_v3_multi.3mf"
echo "  ✓ $OUTDIR/chassis_v3_multi.3mf ($(du -h "$OUTDIR/chassis_v3_multi.3mf" | cut -f1))"

echo "─── 3b. Verify the 3MF actually has 4 objects in the build list ───"
python3 verify_3mf.py "$OUTDIR/chassis_v3_multi.3mf" | head -25

echo "─── 4. Single-object 3MF (legacy fallback) ───"
openscad --export-format=3mf \
         -D "RENDER_BODY=true;RENDER_TOP_DECK=false;RENDER_FRONT_SHIELD=false;RENDER_LIDAR_RISER=false;" \
         -o "$OUTDIR/body_only.3mf" "$SCAD"
echo "  ✓ $OUTDIR/body_only.3mf"

if $step; then
    echo "─── 5. STEP export via FreeCAD Cmd (optional) ───"
    if command -v FreeCADCmd >/dev/null 2>&1; then
        FreeCADCmd -c "
ImportGui.open('$OUTDIR/body.stl')
ImportGui.open('$OUTDIR/top_deck.stl')
ImportGui.open('$OUTDIR/front_shield.stl')
ImportGui.open('$OUTDIR/lidar_riser.stl')
ImportGui.open('$OUTDIR/dsi_display.stl')
Part.export(App.ActiveDocument.Objects, '$OUTDIR/chassis_v3.step')
" 2>&1 | tail -3
        echo "  ✓ $OUTDIR/chassis_v3.step"
    else
        echo "  · FreeCADCmd not installed — skipping STEP."
        echo "    Install with:  sudo apt install freecad"
    fi
else
    echo "─── 5. STEP export: skipped (--no-step) ───"
fi

echo "─── 6. PNG previews for docs / PR description ───"
bash preview_pieces.sh || true    # some OpenSCAD GUI segfaults are known; ignore

echo "─── 7. Exploded-view STL ───"
# Renders assembly_exploded.scad (which `use <main.scad>`s and lifts each
# piece by 40 mm on its assembly axis).  Useful for PR descriptions and
# clearance spot-check before sending to the CATIA partner.
# `|| true` mirrors step 6: under `set -euo pipefail`, any openscad non-zero
# exit (parse error etc.) must NOT abort the rest of the pipeline.
if [ -f assembly_exploded.scad ]; then
    openscad --export-format=binstl \
             --camera=400,350,300,45,0,30,500 \
             -o "$OUTDIR/assembly_exploded.stl" \
             assembly_exploded.scad 2>&1 | tail -3 || true
    if [ -s "$OUTDIR/assembly_exploded.stl" ]; then
        echo "  ✓ $OUTDIR/assembly_exploded.stl ($(du -h "$OUTDIR/assembly_exploded.stl" | cut -f1))"
    else
        echo "  · exploded render produced no STL (openscad error above)"
    fi
else
    echo "  · assembly_exploded.scad missing — skipping"
fi

echo "─── 8. Publish extras (BOM enrichment + per-piece DXF + annotated PNG) ───"
# Runs publish_extras.py which creates:
#   • BOM_enriched.csv                   (Supplier, MPN, SKU, USD$ columns)
#   • dxf/<piece>_flat.dxf × 5           (2D laser-cut reference patterns)
#   • stl/preview/annotated_assembled_chassis.png  (labelled hardware map)
# Gated by --no-extras for fast re-renders when you only want STL/3MF.
if [ ! -f publish_extras.py ]; then
    echo "  · publish_extras.py missing — skipping"
elif ! $extras; then
    echo "  · --no-extras → skipping BOM/DXF/annotated PNG"
else
    python3 publish_extras.py 2>&1 | tail -25 || true    # never fail the build
fi

echo
echo "─── Final summary ───"
ls -lh "$OUTDIR"
test -f BOM_enriched.csv && ls -lh BOM_enriched.csv
test -d dxf && ls -lh dxf/
echo
echo "Per-slice recommendation:"
echo "  … Bambu Studio  →  open stl/chassis_v3_multi.3mf  (multi-object: 4 parts in parts panel)"
echo "  … OrcaSlicer    →  open stl/chassis_v3_multi.3mf  (assign per-piece settings)"
echo "  … PrusaSlicer   →  open stl/chassis_v3.step      (parametric CAD)"
echo "  … Cura          →  drop the 4 stl/*.stl files into the bed as a group"
echo
echo "For documentation / peer review:"
echo "  … Exploded view       →  open stl/assembly_exploded.stl"
echo "  … Annotated render    →  open stl/preview/annotated_assembled_chassis.png"
echo "  … BOM with costs      →  cat BOM_enriched.csv"
echo "  … Laser-cut ref DXF   →  open dxf/<piece>_flat.dxf"
