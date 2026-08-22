#!/usr/bin/env bash
# ====================================================================
#  preview_pieces.sh — render each piece as a 2D PNG via OpenSCAD GUI
#  ──────────────────────────────────────────────────────────────────
#  Outputs: stl/preview/<piece>.png  (PNG renders from a fixed camera
#           position so all 4 pieces are visually comparable).
#           stl/preview/all_combined.png  (4 pieces side-by-side).
#
#  This is the equivalent of "drop into Bambu Studio" — it produces
#  real PNG images you can paste into a slide deck or attach to a
#  Pull Request for review without installing the slicer.
# ====================================================================

set -euo pipefail
cd "$(dirname "$0")"

PIECES=(body top_deck front_shield lidar_riser)
SCAD=main.scad
OUTDIR=stl/preview
mkdir -p "$OUTDIR"

# Camera positions tuned per piece (eye-distance auto, ortho false).
declare -A CAMERA=(
    [body]="40,40,90,55,0,15,260"
    [top_deck]="10,40,90,55,0,15,260"
    [front_shield]="-30,40,90,55,25,30,180"
    [lidar_riser]="10,40,90,55,0,35,260"
)

# Render the four pieces at offset 0 (no translate) for the PNG previews
# so the camera positions above actually look at the geometry.
for piece in "${PIECES[@]}"; do
    flags=""
    for p in "${PIECES[@]}"; do
        if [ "$p" = "$piece" ]; then
            flags="${flags}RENDER_${p^^}=true;"
        else
            flags="${flags}RENDER_${p^^}=false;"
        fi
    done
    cam="${CAMERA[$piece]}"
    openscad --camera="$cam" --projection=p \
             --imgsize=800,600 \
             --colorscheme=Tomorrow \
             -o "$OUTDIR/$piece.png" \
             -D "$flags" "$SCAD" 2>&1 | tail -1
    echo "  ✓ stl/preview/$piece.png"
done

# Build the combined preview by rendering all 4 simultaneously at their
# default main.scad offsets (--enable=chassis_assembly which is what
# main.scad's bottom call does), so we see the assembly footprint.
echo
echo "── Combined 4-piece preview (assembly) ──"
openscad --camera="40,40,90,55,0,15,400" \
         --projection=p --imgsize=1200,400 \
         --colorscheme=Tomorrow \
         -o "$OUTDIR/all_combined.png" \
         -D 'RENDER_BODY=true;RENDER_TOP_DECK=true;RENDER_FRONT_SHIELD=true;RENDER_LIDAR_RISER=true;RENDER_OFFSET_X=220;' \
         "$SCAD" 2>&1 | tail -1
echo "  ✓ stl/preview/all_combined.png"

echo
echo "── Summary ──"
ls -lh "$OUTDIR"
