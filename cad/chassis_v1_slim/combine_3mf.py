#!/usr/bin/env python3
"""
combine_3mf.py — Pack the 4 per-piece STL files from `render_all.sh`
                 into a SINGLE multi-object 3MF zip so Bambu Studio,
                 OrcaSlicer, PrusaSlicer etc. import them as 4
                 separately-placeable parts (each with its own print
                 settings) instead of as one merged blob like
                 OpenSCAD's flat `chassis_v3_multi.3mf` export.

Usage:
    python3 combine_3mf.py [--in-dir stl] [--out stl/chassis_v3_multi.3mf]
                            [--parts body top_deck front_shield lidar_riser]

Strategy: read each binary STL (80B header + uint32 N + 50B * N triangles),
construct a 3MF zip with the standard structure:

    [Content_Types].xml
    _rels/.rels
    3D/3dmodel.model    ← <resources><object>/.../<build><item>... each piece as one object
"""
from __future__ import annotations
import argparse, pathlib, struct, sys, zipfile
import xml.etree.ElementTree as ET

# Standard 3MF XML namespaces
NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
ET.register_namespace("", NS)


def parse_binary_stl(path: pathlib.Path):
    """Yield (verts_list, tris_list) from a binary STL.

    verts_list = [(x,y,z), ...]   unique vertices
    tris_list  = [(v0, v1, v2), ...]   indices into verts_list
    """
    data = path.read_bytes()
    if len(data) < 84:
        raise ValueError(f"{path}: too small to be an STL ({len(data)} bytes)")
    tri_count = struct.unpack_from("<I", data, 80)[0]
    vertices: list[tuple[float, float, float]] = []
    triples:  list[tuple[int, int, int]] = []
    vertex_index: dict[tuple[float, float, float], int] = {}
    cursor = 84
    for _ in range(tri_count):
        # 4 floats normal + 9 floats (3 verts × 3 coords) + 2 bytes attr = 50 bytes
        if cursor + 50 > len(data):
            break
        f = struct.unpack_from("<12f", data, cursor)
        v_coords = [(f[3], f[4], f[5]), (f[6], f[7], f[8]), (f[9], f[10], f[11])]
        tri_idx = []
        for v in v_coords:
            # round to 1µm so identical vertices collapse to one index
            key = (round(v[0], 4), round(v[1], 4), round(v[2], 4))
            if key not in vertex_index:
                vertex_index[key] = len(vertices)
                vertices.append(key)
            tri_idx.append(vertex_index[key])
        triples.append(tuple(tri_idx))
        cursor += 50
    return vertices, triples


def build_3dmodel_xml(parts: list[tuple[str, vertices, triples]]):
    """Build 3D/3dmodel.model XML keeping each part as its own <object>."""
    root = ET.Element(f"{{{NS}}}model", attrib={"unit": "millimeter"})
    resources = ET.SubElement(root, f"{{{NS}}}resources")
    build_item_ids = []
    next_id = 1
    for name, verts, tris in parts:
        obj = ET.SubElement(resources, f"{{{NS}}}object",
                            attrib={"id": str(next_id),
                                    "name": name,
                                    "type": "model"})
        mesh = ET.SubElement(obj, f"{{{NS}}}mesh")
        v_el = ET.SubElement(mesh, f"{{{NS}}}vertices")
        for x, y, z in verts:
            ET.SubElement(v_el, f"{{{NS}}}vertex",
                          attrib={"x": f"{x:.4f}", "y": f"{y:.4f}", "z": f"{z:.4f}"})
        t_el = ET.SubElement(mesh, f"{{{NS}}}triangles")
        for a, b, c in tris:
            ET.SubElement(t_el, f"{{{NS}}}triangle",
                          attrib={"v1": str(a), "v2": str(b), "v3": str(c)})
        build_item_ids.append(next_id)
        next_id += 1
    build = ET.SubElement(root, f"{{{NS}}}build")
    for oid in build_item_ids:
        ET.SubElement(build, f"{{{NS}}}item",
                      attrib={"objectid": str(oid),
                              "transform": "1 0 0 0 1 0 0 0 1 0 0 0"})
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="UTF-8", xml_declaration=True).decode("utf-8")


CONTENT_TYPES_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
</Types>
"""

RELS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/relationships/3dmodel"/>
</Relationships>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-dir", type=pathlib.Path, default=pathlib.Path("stl"))
    ap.add_argument("--out", type=pathlib.Path, default=pathlib.Path("stl/chassis_v3_multi.3mf"))
    # When --parts is omitted, auto-discover every per-piece STL that
    # render_all.sh just produced.  Single source of truth = "STLs present
    # in --in-dir", so adding a new piece to render_all.sh PIECES= array
    # automatically propagates into this 3MF with no code change here.
    # Composed views (assembly_preview, body_only) are excluded because
    # combine_3mf.py is meant to package INDIVIDUAL parts for the slicer,
    # not the merged assembly.
    ap.add_argument("--parts", nargs="+", default=None)
    args = ap.parse_args()

    if not args.in_dir.exists():
        print(f"[ERR ] {args.in_dir} not found — run bash render_all.sh first", file=sys.stderr)
        return 1

    if args.parts is None:
        EXCLUDE_FROM_BUILD = {"assembly_preview"}   # composed views are not parts
        auto = sorted(
            p.stem for p in args.in_dir.glob("*.stl")
            if p.stem not in EXCLUDE_FROM_BUILD
        )
        if not auto:
            print(f"[ERR ] no per-piece STLs in {args.in_dir} — run bash render_all.sh first", file=sys.stderr); return 1
        args.parts = auto
        print(f"[auto] discovered {len(args.parts)} per-piece STL(s): {args.parts}")

    parts = []
    for name in args.parts:
        stl = args.in_dir / f"{name}.stl"
        if not stl.exists():
            print(f"[ERR ] {stl} missing", file=sys.stderr); return 1
        size = stl.stat().st_size
        if size < 100:
            print(f"[ERR ] {stl} too small ({size} bytes)", file=sys.stderr); return 1
        verts, tris = parse_binary_stl(stl)
        print(f"  · {name}: {len(verts):,} vertices  {len(tris):,} triangles  ({size:,} bytes)")
        parts.append((name, verts, tris))

    model_xml = build_3dmodel_xml(parts)
    args.out.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(args.out, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES_XML)
        z.writestr("_rels/.rels", RELS_XML)
        z.writestr("3D/3dmodel.model", model_xml)

    out_size = args.out.stat().st_size
    print(f"\n[ok]   {args.out} written ({out_size:,} bytes)")
    print(f"[ok]   {len(parts)} objects in the build list — Bambu Studio will see them as")
    print("       separately-placeable parts in the parts panel.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
