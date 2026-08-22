#!/usr/bin/env bash
# =============================================================================
#  render_assembly_preview.sh  --  render FULL assembled tank chassis
#  Output: stl/assembly_preview.stl + 4-angle PNG matrix in stl/preview/
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")"

OUTDIR=stl
PREV_DIR="$OUTDIR/preview"
mkdir -p "$OUTDIR" "$PREV_DIR"

echo "─── 1. Single assembly STL ───"
rm -f "$OUTDIR/assembly_preview.stl"
openscad --export-format=binstl \
         --camera=300,250,200,55,0,25,400 \
         -o "$OUTDIR/assembly_preview.stl" \
         assembly_preview.scad
STL_SIZE=$(du -h "$OUTDIR/assembly_preview.stl" | cut -f1)
echo "  ✓ $OUTDIR/assembly_preview.stl ($STL_SIZE)"

echo "─── 2. 4-angle PNG matrix ───"
iso_camera="300,250,200,55,0,25,400"
front_camera="0,80,30,70,0,0,300"
rightside_camera="200,250,30,55,90,0,300"
topdown_camera="0,0,150,0,0,0,300"

for entry in "iso:$iso_camera" "front:$front_camera" "rightside:$rightside_camera" "topdown:$topdown_camera"; do
  ang="${entry%%:*}"
  cam="${entry#*:}"
  openscad --projection=p --imgsize=1024,768 \
           --camera="$cam" \
           --colorscheme=Tomorrow \
           -o "$PREV_DIR/assembly_${ang}.png" \
           assembly_preview.scad 2>&1 | tail -1
  echo "  ✓ $PREV_DIR/assembly_${ang}.png"
done

echo "─── 3. Summary ───"
ls -lh "$OUTDIR"/assembly_preview.stl "$PREV_DIR"/assembly_*.png 2>/dev/null
echo
echo "→ Open the STL in a slicer:"
echo "    Bambu Studio / OrcaSlicer / PrusaSlicer  →  File → Open  →  stl/assembly_preview.stl"
echo "→ View a PNG:"
echo "    xdg-open  $PREV_DIR/assembly_iso.png"
