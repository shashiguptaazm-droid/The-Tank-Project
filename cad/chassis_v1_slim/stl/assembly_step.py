#!/usr/bin/env python3
"""
assembly_step.py — Combine the 5 per-piece STLs into a single multi-body STEP
                   positioned at the real assembly coordinates.

Reads the existing 5 per-piece STLs in `stl/` (body, top_deck, front_shield,
lidar_riser, dsi_display), translates each into its true assembly position
(same XYZ math as `assembly_preview.scad` with EXPLODE_GAP=0), applies the
front shield's 90° Y-rotation, and emits a single multi-body STEP file
`stl/assembly.step` containing all 5 pieces as independent root entities.

USAGE:
    python3 assembly_step.py                       # default in: stl/, out: stl/assembly.step
    python3 assembly_step.py --in-dir stl          # custom input
    python3 assembly_step.py --out stl/assembly.step

WHY THIS EXISTS:
    step_from_stl.py writes the 5 per-piece STLs as 5 separate single-piece
    STEP files.  For a CATIA partner, we ALSO want a single STEP file that
    contains the entire chassis assembled — so they can open ONE file and
    see/measure/check-fit all 5 parts together.  Without an assembly STEP,
    the partner would have to import 5 STEPs into CATIA and manually arrange
    them.

GEOMETRY NOTE:
    Same caveat as step_from_stl.py: STL→STEP-via-OCC produces FACETED
    (mesh-backed) STEP bodies.  CATIA will open and display them correctly
    but each body is flagged "not a true solid" — Boolean/Fillet/Draft will
    refuse.  True BREP requires routing through the OpenSCAD source via
    FreeCAD's OpenSCAD workbench (see render_step.sh in the parent dir).
    Use this script for VISUAL REVIEW and STEP-bundle shipment.
"""
from __future__ import annotations
import argparse
import math
import pathlib
import sys

import OCP
from OCP.TopoDS import TopoDS_Shape, TopoDS_Compound
from OCP.BRep import BRep_Builder
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.StlAPI import StlAPI_Reader
from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
from OCP.gp import (
    gp_Trsf, gp_Vec, gp_Quaternion,
)


# ─────────────────────────────────────────────────────────────────────────────
#   ASSEMBLY POSITIONS  (must mirror assembly_preview.scad with EXPLODE_GAP=0)
# ─────────────────────────────────────────────────────────────────────────────

# Geometry from main.scad SECTION A.  Keep these in sync with main.scad —
# duplicated here intentionally to make this script standalone.
body_l          = 185.0
body_w          = 100.0
body_total_h    =  40.0
deck_h          =   5.0
shield_w        =  80.0
shield_h        =  95.0
shield_thickness =  4.0
dsi_riser_h     =   8.0   # stand-off height above top_deck

# Per-piece positions (XYZ in mm world coords) + optional rotation tag.
# "Y+90" means rotate 90° about the Y axis (CCW right-handed → old X becomes
# -Z, old Z becomes +X).  This matches OpenSCAD's `rotate([0, 90, 0])` used
# in assembly_preview.scad to swing the shield's wide face perpendicular to
# the body's +X face.
PIECES: list[tuple[str, tuple[float, float, float], list[tuple[str, float]]]] = [
    # (name, (x, y, z), [(axis, angle rad)])
    ("body",         (0.0,       0.0, 0.0),         []),
    ("top_deck",     (0.0,       0.0, body_total_h), []),
    ("lidar_riser",  (0.0,       0.0, body_total_h + deck_h), []),
    # FRONT_SHIELD: proto-translate so the shield protrudes +X past the
    # body's +X face, then rotate so its 80×95 face points along ±Y.
    ("front_shield",
     (body_l / 2 + shield_thickness / 2, 0.0, body_total_h / 2), [("Y", math.pi / 2)]),
    ("dsi_display",  (0.0, 0.0, body_total_h + deck_h + dsi_riser_h), []),
]


# ─────────────────────────────────────────────────────────────────────────────
#   TRANSFORM HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _axis_unit_vec(axis: str) -> gp_Vec:
    """Return the unit gp_Vec for rotation axis 'X'/'Y'/'Z'."""
    if axis == "X":
        return gp_Vec(1.0, 0.0, 0.0)
    if axis == "Y":
        return gp_Vec(0.0, 1.0, 0.0)
    if axis == "Z":
        return gp_Vec(0.0, 0.0, 1.0)
    raise ValueError(f"unknown rotation axis: {axis!r}")


def _axis_angle_quaternion(axis: str, angle: float) -> gp_Quaternion:
    """Build a gp_Quaternion using the 4-arg (x,y,z,w) form.

    cadquery-ocp 7.9 does NOT expose the gp_Ax1+angle constructor that the
    OpenCASCADE C++ API has — calling gp_Quaternion(ax, angle) raises
    TypeError: constructor argument mismatch.  The 4-arg form below is
    reliably exposed and produces an equivalent right-hand-rule rotation.
    """
    # axis-angle -> quaternion: (ax*sin(θ/2), ay*sin(θ/2), az*sin(θ/2), cos(θ/2))
    half = angle / 2.0
    s = math.sin(half)
    c = math.cos(half)
    v = _axis_unit_vec(axis)
    return gp_Quaternion(v.X() * s, v.Y() * s, v.Z() * s, c)


def make_rotation_trsf(rotations: list[tuple[str, float]]) -> gp_Trsf:
    """Build a gp_Trsf from a list of (axis-letter, angle-rad) rotations."""
    trsf = gp_Trsf()
    for axis, angle in rotations:
        trsf.SetRotation(_axis_angle_quaternion(axis, angle))
    return trsf


def apply_transform(shape: TopoDS_Shape, trsf: gp_Trsf) -> TopoDS_Shape:
    """Apply a gp_Trsf to a TopoDS_Shape and return the new shape."""
    return BRepBuilderAPI_Transform(shape, trsf, True).Shape()


def read_stl_as_shape(path: pathlib.Path) -> TopoDS_Shape:
    shape = TopoDS_Shape()
    reader = StlAPI_Reader()
    if not reader.Read(shape, str(path.resolve())):
        raise RuntimeError(f"StlAPI_Reader.Read failed for {path}")
    if shape.IsNull():
        raise RuntimeError(f"parsed shape is null for {path}")
    return shape


# ─────────────────────────────────────────────────────────────────────────────
#   MAIN COMBINER
# ─────────────────────────────────────────────────────────────────────────────

def assemble(in_dir: pathlib.Path, out_path: pathlib.Path) -> int:
    """Read all 5 per-piece STLs, position them at assembly coords, write 1 STEP."""
    compound = TopoDS_Compound()
    builder = BRep_Builder()
    builder.MakeCompound(compound)

    pieces_in = []
    for name, (x, y, z), rots in PIECES:
        stl_path = in_dir / f"{name}.stl"
        if not stl_path.exists():
            print(f"  ✗ {stl_path} missing — run 'bash render_all.sh' first", file=sys.stderr)
            return 1
        shape = read_stl_as_shape(stl_path)
        if rots:
            shape = apply_transform(shape, make_rotation_trsf(rots))
        trsf = gp_Trsf()
        trsf.SetTranslation(gp_Vec(x, y, z))
        shape = apply_transform(shape, trsf)
        builder.Add(compound, shape)
        pieces_in.append((name, stl_path.stat().st_size, len(rots) > 0))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    writer = STEPControl_Writer()
    writer.Transfer(compound, STEPControl_AsIs)
    writer.Write(str(out_path.resolve()))

    # Validate ISO 10303-21 header.
    with open(out_path) as f:
        head = f.read(12)
    if not head.startswith("ISO-10303-21"):
        print(f"  ✗ wrote {out_path} but header is {head!r} (expected ISO-10303-21)",
              file=sys.stderr)
        return 2

    size = out_path.stat().st_size
    print(f"\n  ✓ {out_path}  ({size:,} bytes)")
    print(f"  ✓ 5 root bodies in the compound (each as independent shape in the STEP file)")
    print(f"  ✓ OCP backend: {OCP.__file__}")
    print(f"\n  Pieces:")
    for name, sz, rotated in pieces_in:
        print(f"     • {name:<14} ({sz:,} B, {'rotated' if rotated else 'as-is'})")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Combine the 5 per-piece STLs into a single multi-body assembly STEP.")
    ap.add_argument("--in-dir", type=pathlib.Path, default=pathlib.Path("stl"),
                    help="input directory containing body.stl, top_deck.stl, ...")
    ap.add_argument("--out", type=pathlib.Path, default=pathlib.Path("stl/assembly.step"),
                    help="output STEP file path")
    args = ap.parse_args()
    return assemble(args.in_dir.resolve(), args.out.resolve())


if __name__ == "__main__":
    sys.exit(main())
