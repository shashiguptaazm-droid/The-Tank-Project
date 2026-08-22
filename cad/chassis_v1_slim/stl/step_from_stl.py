#!/usr/bin/env python3
"""
step_from_stl.py — Reusable STL → STEP converter

Reads one or more binary-STL files and writes a corresponding `.step` file
using OpenCASCADE via the `OCP` (cadquery-ocp) python bindings.

USAGE:
    python3 step_from_stl.py body.stl                # -> body.step
    python3 step_from_stl.py body.stl --out all.step  # explicit output
    python3 step_from_stl.py *.stl                  # batch

WHY THIS EXISTS:
    OpenSCAD outputs only STL/3MF/DXF.  CATIA V5 prefers STEP for true
    solid import.  FreeCAD's `FreeCADCmd` works on some Ubuntu hosts but
    fails on snap-confinement installs (libQt6 not available).  Cadquery
    (which wraps OCP = the same OpenCASCADE 7.x C++ library FreeCAD
    uses) gives us a CLI path that bypasses Qt entirely.

GEOMETRY NOTE:
    STL→STEP-via-OCC produces a *faceted* (mesh-backed) STEP.  CATIA
    will open it but mark it as "not a true solid" — Boolean, Fillet,
    Draft all error.  True BREP requires routing through the OpenSCAD
    source via FreeCAD's OpenSCAD workbench (see render_step.sh in the
    parent dir).  Use this script for VISUAL REVIEW only.
"""
from __future__ import annotations
import argparse
import glob
import pathlib
import sys

import OCP
from OCP.TopoDS import TopoDS_Shape
from OCP.StlAPI import StlAPI_Reader
from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs


def stl_to_step(stl_path: pathlib.Path, step_path: pathlib.Path) -> tuple[bool, str]:
    """Convert one STL to STEP.  Returns (success, info_text)."""
    if not stl_path.exists():
        return False, f"missing: {stl_path}"
    shape = TopoDS_Shape()
    reader = StlAPI_Reader()
    if not reader.Read(shape, str(stl_path)):
        return False, f"StlAPI_Reader.Read failed for {stl_path}"
    if shape.IsNull():
        return False, f"parsed shape is null for {stl_path}"

    step_path.parent.mkdir(parents=True, exist_ok=True)
    w = STEPControl_Writer()
    w.Transfer(shape, STEPControl_AsIs)
    w.Write(str(step_path))

    # Validate the ISO 10303-21 header (file begins with "ISO-10303-21;\n").
    # Read 12 bytes so the startswith check has the full "ISO-10303-21" prefix.
    with open(step_path) as f:
        head = f.read(12)
    if not head.startswith("ISO-10303-21"):
        return False, f"wrote {step_path} but header is {head!r} (expected ISO-10303-21)"

    size = step_path.stat().st_size
    return True, f"OK  {stl_path.name}  →  {step_path.name}  ({size:,} B)"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="Convert binary STL files to STEP (faceted mesh) using OpenCASCADE.")
    ap.add_argument("inputs", nargs="+", help="binary STL files (globs ok)")
    ap.add_argument("--out-dir", type=pathlib.Path, default=None,
                    help="output directory (default: same dir as each input)")
    ap.add_argument("--out", type=pathlib.Path, default=None,
                    help="output path for single-input mode (default: input stem + .step)")
    args = ap.parse_args(argv)

    # Expand globs
    expanded: list[pathlib.Path] = []
    for inp in args.inputs:
        matches = sorted(glob.glob(inp))
        if matches:
            expanded.extend(pathlib.Path(m) for m in matches)
        else:
            # Maybe it's a literal name with no glob match
            expanded.append(pathlib.Path(inp))

    if args.out is not None and len(expanded) != 1:
        print("[ERR ] --out only valid when converting exactly one input", file=sys.stderr)
        return 2

    rc = 0
    for stl in expanded:
        if args.out is not None:
            step = args.out
        elif args.out_dir is not None:
            step = args.out_dir / (stl.stem + ".step")
        else:
            step = stl.with_suffix(".step")
        ok, msg = stl_to_step(stl.resolve(), step.resolve())
        print(f"  {'✓' if ok else '✗'} {msg}")
        if not ok:
            rc = 1

    if rc == 0:
        print(f"\nOCP backend: {OCP.__file__}")
        print("All STEP files written.  Open them in 3dviewer.net, eDrawings, FreeCAD, or CATIA.")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
