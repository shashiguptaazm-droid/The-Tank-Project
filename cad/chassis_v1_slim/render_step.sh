#!/usr/bin/env bash
# ============================================================================
#  render_step.sh — Render each chassis piece as a STEP file (true solid)
#  ─────────────────────────────────────────────────────────────────────────
#  v3 — fixes FreeCAD PATH 2 Mesh API per code-reviewer
#
#  PATH 1 (preferred): OpenSCAD workbench imports main.scad and exports
#                      per-piece .step via Part.export.  Produces TRUE
#                      BREP solids that CATIA's SaveAs accepts cleanly.
#
#  PATH 2 (fallback):  If PATH 1 fails (FreeCAD's OpenSCAD module missing
#                      or rejects main.scad), re-import the per-piece
#                      STL via Mesh + Part.Shape().makeShapeFromMesh()
#                      (canonical FreeCAD Python API).
#
#  USAGE
#    bash render_step.sh                # 4 per-piece + 1 assembly
#    bash render_step.sh --no-assembly  # 4 per-piece only
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")"

OUT=step
mkdir -p "$OUT"

if ! command -v FreeCADCmd >/dev/null 2>&1; then
    echo "[ERR ] FreeCADCmd not found on PATH"
    echo "        install:  sudo add-apt-repository -y ppa:freecad-maintainers/freecad-stable"
    echo "        sudo apt-get install -y freecad-stable"
    exit 2
fi

FREE_CAD_MAIN=main.scad
ASSEMBLY_SCAD=assembly_preview.scad

# ---------------------------------------------------------------------------
# PATH 1 — True Solid via OpenSCAD workbench
# ---------------------------------------------------------------------------
try_open_alembic () {
    local piece=$1
    local module=$2
    FreeCADCmd -c "
import ImportGui, Part, App, OpenSCAD
OpenSCAD.open('${FREE_CAD_MAIN}', '${module}')
App.ActiveDocument.ActiveObject.Label = '${piece}'
Part.export(App.ActiveDocument.Objects, '${OUT}/${piece}.step')
App.closeDocument('${piece}')
print('PATH1_${piece}_OK')
" 2>&1 | grep -E "PATH1_${piece}_OK|^Err|^ERROR" | tail -1
}

# ---------------------------------------------------------------------------
# PATH 2 — Canonical FreeCAD Mesh + makeShapeFromMesh fallback
#   (per review: 4-liner using FreeCAD Mesh module + tolerance 0.1)
# ---------------------------------------------------------------------------
fallback_stl_to_step () {
    local piece=$1
    FreeCADCmd -c "
import FreeCAD, Part, Mesh, App
m = Mesh.Mesh()
m.read('stl/${piece}.stl')
shape = Part.Shape()
shape.makeShapeFromMesh(m.Topology, 0.1)   # 0.1 mm tolerance
Part.export([shape], '${OUT}/${piece}.step')
App.closeDocument('${piece}')
print('PATH2_${piece}_OK')
" 2>&1 | grep -E "PATH2_${piece}_OK|^Err|^ERROR" | tail -1
}

render_piece () {
    local piece=$1
    local module=$2
    echo "--- $piece via PATH 1 (OpenSCAD) ---"
    if try_open_alembic "$piece" "$module" | grep -q "PATH1_${piece}_OK"; then
        echo "  $piece :: PATH 1 (true solid) OK"
        return 0
    fi
    echo "--- $piece via PATH 2 (Mesh fallback) ---"
    if fallback_stl_to_step "$piece" | grep -q "PATH2_${piece}_OK"; then
        echo "  $piece :: PATH 2 (faceted fallback) OK"
        return 0
    fi
    echo "[WARN] $piece neither path worked"
    return 1
}

render_piece body            piece_body
render_piece top_deck        piece_top_deck
render_piece front_shield    piece_front_shield
render_piece lidar_riser     piece_lidar_riser

# Assembly preview ---------------------------------------------------
if [[ "${1:-}" != "--no-assembly" ]]; then
    if [ -f "$ASSEMBLY_SCAD" ]; then
        echo "--- assembly_preview via PATH 1 (use <>) ---"
        FreeCADCmd -c "
use <${FREE_CAD_MAIN}>
import ImportGui, Part, App
# assembly_preview.scad uses use <main.scad> not include <>,
# so we run it via FreeCAD's regular importer
ImportGui.open('${ASSEMBLY_SCAD}')
App.ActiveDocument.ActiveObject.Label = 'assembly'
Part.export(App.ActiveDocument.Objects, '${OUT}/assembly_preview.step')
App.closeDocument('assembly')
print('PATH1_assembly_OK')
" 2>&1 | grep -E "PATH1_assembly_OK|^Err|^ERROR" | tail -1

        # If assembly preview import fails, fall through to STL STEP path
        if ! [ -f "${OUT}/assembly_preview.step" ]; then
            echo "--- assembly_preview via PATH 2 (STL fallback) ---"
            fallback_stl_to_step assembly_preview
        fi
    else
        echo "[WARN] ${ASSEMBLY_SCAD} not found; skipping assembly preview"
    fi
fi

echo
echo "=== STEP outputs ==="
ls -lh "$OUT"/
echo
echo "=== Quick header check (every STEP starts with ISO-10303-21;) ==="
HEADER_OK=0
HEADER_BAD=0
for f in "$OUT"/*.step; do
    head="$(head -c 15 "$f")"
    if [ "$head" = "ISO-10303-21;" ]; then
        echo "  ✓  $(basename "$f")  (ISO-10303-21)"
        HEADER_OK=$((HEADER_OK+1))
    else
        echo "  ✗  $(basename "$f")  (header: $head)"
        HEADER_BAD=$((HEADER_BAD+1))
    fi
done
echo "summary: $HEADER_OK OK, $HEADER_BAD bad"
