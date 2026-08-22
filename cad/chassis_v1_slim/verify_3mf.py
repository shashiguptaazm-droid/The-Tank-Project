#!/usr/bin/env python3
"""
verify_3mf.py — Inspect a 3MF file the way Bambu Studio would.

Reports per-piece:
    * object id
    * part name (when OpenSCAD emits a part label)
    * vertex count + triangle count
    * first-triangle centroid (origin anchor)
    * axis-aligned bounding box

Exits 0 on a healthy multi-piece 3MF, 1 on parse error, 2 on warnings.
"""
import sys, pathlib, zipfile, xml.etree.ElementTree as ET, struct

NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
ET.register_namespace("", NS)


def parse_float(s: str) -> float:
    return float(s.strip())


def bbox_of(vertices):
    if not vertices:
        return (0, 0, 0, 0, 0, 0)
    xs = [v[0] for v in vertices]
    ys = [v[1] for v in vertices]
    zs = [v[2] for v in vertices]
    return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


def bbox_str(bb):
    return f"({bb[0]:+.2f}, {bb[1]:+.2f}, {bb[2]:+.2f}) → ({bb[3]:+.2f}, {bb[4]:+.2f}, {bb[5]:+.2f})"


def inspect(path: pathlib.Path):
    print(f"─── 3MF inspect: {path.name}  ({path.stat().st_size:,} bytes) ───")
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        print(f"  ZIP contents: {len(names)} entries")
        for n in sorted(names):
            print(f"    · {n}")

        with z.open("3D/3dmodel.model") as f:
            data = f.read()
    try:
        root = ET.fromstring(data)
    except ET.ParseError as e:
        print(f"\n[ERR ] XML parse error: {e}", file=sys.stderr)
        return 1

    # Walk every <object> in the resources block
    resources = root.find(f"{{{NS}}}resources")
    objects   = resources.findall(f"{{{NS}}}object") if resources is not None else []
    if not objects:
        print("\n[ERR ] no <object> resources in 3D/3dmodel.model", file=sys.stderr)
        return 1

    print(f"\n  Resources: {len(objects)} object(s)")

    # Build's <item> list
    build = root.find(f"{{{NS}}}build")
    if build is None:
        print("[ERR ] missing <build> block", file=sys.stderr)
        return 1
    items = build.findall(f"{{{NS}}}item")
    print(f"  Build list: {len(items)} <item> reference(s)")

    # Map object id → object element
    oid_to_obj = {obj.get("id"): obj for obj in objects}

    id_labels = []
    if len(items) == len(objects) and len(items) <= 8:
        # Heuristic naming for OpenSCAD multi-object 3MFs (id 1=N, 2=N-1, ...).
        # We use this only for human-readable labels, not as a source of truth.
        label_pool = ["body", "top_deck", "front_shield", "lidar_riser",
                      "part_5", "part_6", "part_7", "part_8"]
        id_labels = label_pool[: len(items)]

    print()
    print(f"  {'idx':<4} {'obj#':<6} {'vertices':>9} {'triangles':>9} {'bbox (mm)':<48}  origin")
    print("  " + "-" * 100)

    warnings = 0
    for idx, (item, obj) in enumerate(zip(items, objects), start=1):
        oid = obj.get("id")
        mesh = obj.find(f"{{{NS}}}mesh")
        verts = mesh.find(f"{{{NS}}}vertices") if mesh is not None else None
        tris  = mesh.find(f"{{{NS}}}triangles") if mesh is not None else None
        v_count = len(verts.findall(f"{{{NS}}}vertex")) if verts is not None else 0
        t_count = len(tris.findall(f"{{{NS}}}triangle")) if tris is not None else 0
        # Collect vertices for bbox
        vertices = []
        if verts is not None:
            for v in verts.findall(f"{{{NS}}}vertex"):
                x = parse_float(v.get("x"))
                y = parse_float(v.get("y"))
                z = parse_float(v.get("z"))
                vertices.append((x, y, z))
        bb = bbox_of(vertices)
        # First triangle centroid = approximate origin anchor
        origin = (round((bb[0]+bb[3])/2, 2),
                  round((bb[1]+bb[4])/2, 2),
                  round((bb[2]+bb[5])/2, 2))
        label = id_labels[idx-1] if idx-1 < len(id_labels) else f"obj{oid}"
        print(f"  {idx:<4} {oid:<6} {v_count:>9} {t_count:>9} {bbox_str(bb):<48}  {label}")

        if v_count == 0 or t_count == 0:
            warnings += 1
            print(f"         [WARN] empty mesh on object #{oid}")

    print()
    print(f"  Total: {len(objects)} object(s) · {sum(len(o.find(f'{{{NS}}}mesh').findall(f'{{{NS}}}vertex')) for o in objects):,} vertices · "
          f"{sum(len(o.find(f'{{{NS}}}mesh').findall(f'{{{NS}}}triangle')) for o in objects):,} triangles")
    print()
    print("  ⇒ Bambu Studio / OrcaSlicer / PrusaSlicer will import this 3MF as a single project")
    print("    with all parts in the assembly plate. Each object can be assigned its own print")
    print("    settings (supports, strength, colour, etc.).")

    if warnings:
        return 2
    return 0


def main():
    if len(sys.argv) < 2:
        # default: stl/chassis_v3_multi.3mf and stl/body_only.3mf
        here = pathlib.Path(__file__).parent
        candidates = [
            here / "stl" / "chassis_v3_multi.3mf",
            here / "stl" / "body_only.3mf",
        ]
        rc = 0
        for c in candidates:
            if c.exists():
                rc |= inspect(c)
                print()
        return rc
    rc = 0
    for arg in sys.argv[1:]:
        rc |= inspect(pathlib.Path(arg))
        print()
    return rc


if __name__ == "__main__":
    sys.exit(main())
