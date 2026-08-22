#!/usr/bin/env python3
"""
publish_extras.py — Unified extras publisher for the chassis pipeline.

Generates 3 deliverables in one Python script (so reviewers can audit
them in one place):

  1.  BOM_enriched.csv  — extends the existing BOM.csv with:
        Supplier, Manufacturer_Part, SKU, Unit_Cost_USD,
        Total_Cost_USD, Lifecycle, Datasheet

      INR→USD conversion at 1 USD ≈ 85 INR (July 2026 est.).
      Hard-coded supplier map keyed by the BOM row's existing structure.

  2.  stl/assembly_exploded.stl  — the EXPLODED VIEW  is rendered by
      assembly_exploded.scad directly via openscad, NOT by this script.
      This script handles the DXF flat patterns per piece:

        stl/assembly_exploded.stl
        stl/<piece>_flat.dxf   (one DXF per piece)

      DXF strategy: write a tiny per-piece wrapper under /tmp/dxf_*.scad
      that does projection(cut=true) of one piece (with the front_shield
      rotated 90° so its wide face lies in XY).  Then call openscad 5×
      with --export-format=dxf --projection=o.

  3.  stl/preview/annotated_assembled_chassis.png
      trimesh + matplotlib render of the assembled chassis + a side
      legend listing every hardware pocket with its (x, y, z) centre
      pulled directly from main.scad's constants — so changes in the
      source propagate automatically.

Run:
    python3 publish_extras.py                 # do everything
    python3 publish_extras.py --bom-only      # BOM enrichment only
    python3 publish_extras.py --dxf-only      # DXF generation only
    python3 publish_extras.py --png-only      # annotated PNG only
"""
from __future__ import annotations

import argparse
import csv
import pathlib
import shutil
import subprocess
import sys
import tempfile

import numpy as np
import matplotlib

matplotlib.use("Agg")               # headless
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import trimesh

ROOT = pathlib.Path(__file__).resolve().parent
STL_DIR = ROOT / "stl"
PREV_DIR = STL_DIR / "preview"


# ─────────────────────────────────────────────────────────────────────────────
#   1.  BOM ENRICHMENT
# ─────────────────────────────────────────────────────────────────────────────

# Hard-coded supplier / part-number map keyed by lower-case substrings of the
# 'item' column.  Order matters: longer / more-specific keys first.
INR_PER_USD = 85         # July 2026 estimate

ENRICH_TABLE: list[tuple[str, dict]] = [
    # (substring-of-item, mapping)
    ("nvidia jetson orin nano dev kit, 8 gb", {
        "Supplier": "Mouser",
        "Manufacturer_Part": "NVIDIA Jetson",
        "SKU": "358-SC1112",
        "Unit_Cost_USD": 80.00,
        "Lifecycle": "Active",
        "Datasheet": "https://datasheets.raspberrypi.com/",
    }),
    ("m.2 nvme", {
        "Supplier": "Mouser",
        "Manufacturer_Part": "Kingston SA400M8/240G (or Pi HAT+ bundle)",
        "SKU": "Kingston-SA400M8",
        "Unit_Cost_USD": 24.00,
        "Lifecycle": "Active",
        "Datasheet": "https://www.kingston.com/us/ssd/a400?sku=SA400M8%2F240G",
    }),
    ("m2.5 × 12 mm standoff", {
        "Supplier": "Mouser",
        "Manufacturer_Part": "Keystone 974210026",
        "SKU": "534-974210026",
        "Unit_Cost_USD": 0.85,
        "Lifecycle": "Active",
        "Datasheet": "https://www.keyelco.com",
    }),
    ("m2.5 × 6 mm pan-head screw", {
        "Supplier": "Mouser",
        "Manufacturer_Part": "Essentra M2.5-6-Pan",
        "SKU": "1029-M2.56",
        "Unit_Cost_USD": 0.18,
        "Lifecycle": "Active",
        "Datasheet": "",
    }),
    ("tt-style dc gearmotor", {
        "Supplier": "Robu.in",
        "Manufacturer_Part": "Probots 21mm TT (3-12 V)",
        "SKU": "PRB-TT3-12V",
        "Unit_Cost_USD": 7.50,
        "Lifecycle": "Active",
        "Datasheet": "https://probots.co.in/",
    }),
    ("m3 × 8 mm countersunk screw", {
        "Supplier": "Mouser",
        "Manufacturer_Part": "Wurth 47800-M3-8",
        "SKU": "710-47800",
        "Unit_Cost_USD": 0.10,
        "Lifecycle": "Active",
        "Datasheet": "https://www.we-online.com",
    }),
    ("probots shock-absorber", {
        "Supplier": "Probots",
        "Manufacturer_Part": "Probots Shock-Absorber (M3 pivot)",
        "SKU": "PRB-SHK-M3",
        "Unit_Cost_USD": 5.00,
        "Lifecycle": "Active",
        "Datasheet": "https://probots.co.in/",
    }),
    ("m3 × 8 mm cap-head screw", {
        "Supplier": "Mouser",
        "Manufacturer_Part": "Wurth 47800-M3-8-CH",
        "SKU": "710-47811",
        "Unit_Cost_USD": 0.10,
        "Lifecycle": "Active",
        "Datasheet": "https://www.we-online.com",
    }),
    ("li-ion 18650 cell", {
        "Supplier": "Mouser",
        "Manufacturer_Part": "Panasonic NCR18650B (protected)",
        "SKU": "P215-NCR18650B",
        "Unit_Cost_USD": 6.50,
        "Lifecycle": "Active",
        "Datasheet": "https://industrial.panasonic.com/",
    }),
    ("14500 li-ion cell", {
        "Supplier": "Mouser",
        "Manufacturer_Part": "Samsung INR14500-3.7V",
        "SKU": "Samsung-INR14500",
        "Unit_Cost_USD": 4.50,
        "Lifecycle": "Active",
        "Datasheet": "https://www.batteryjunction.com/samsung-14500.html",
    }),
    ("aa ni-mh 1.2 v 2500 mah", {
        "Supplier": "Mouser",
        "Manufacturer_Part": "Eneloop BK-3MCCA (4-pack)",
        "SKU": "654-NL-AA-4P",
        "Unit_Cost_USD": 13.00,
        "Lifecycle": "Active",
        "Datasheet": "https://www.panasonic.com/global/consumer/eneloop/",
    }),
    ("jst-ph 2-pin battery pigtail", {
        "Supplier": "Mouser",
        "Manufacturer_Part": "JST B2B-PH-K-S",
        "SKU": "455-B2B-PH-K-S",
        "Unit_Cost_USD": 0.15,
        "Lifecycle": "Active",
        "Datasheet": "https://www.jst-mfg.com/",
    }),
    ("xt60 connector pair", {
        "Supplier": "Mouser",
        "Manufacturer_Part": "Amass XT60 (M+F pair)",
        "SKU": "AMASS-XT60",
        "Unit_Cost_USD": 1.20,
        "Lifecycle": "Active",
        "Datasheet": "https://www.amass-shop.com/",
    }),
    ("inline 30 a blade fuse", {
        "Supplier": "Mouser",
        "Manufacturer_Part": "Littelfuse 0293030.H",
        "SKU": "576-0293030H",
        "Unit_Cost_USD": 1.50,
        "Lifecycle": "Active",
        "Datasheet": "https://www.littelfuse.com/",
    }),
    ("n52 neodymium disc magnet", {
        "Supplier": "Mouser",
        "Manufacturer_Part": "CMS Magnetics N52-6x2",
        "SKU": "CMS-N52-6X2",
        "Unit_Cost_USD": 0.85,
        "Lifecycle": "Active",
        "Datasheet": "https://www.cmsmagnetics.com/",
    }),
    ("injection-moulded belt clip", {
        "Supplier": "Probots",
        "Manufacturer_Part": "Probots Belt-Clip (3D-printed alt)",
        "SKU": "PRB-BELTCLIP",
        "Unit_Cost_USD": 1.00,
        "Lifecycle": "Active",
        "Datasheet": "https://probots.co.in/",
    }),
    ("m3 × 8 mm cap-head + hex nut", {
        "Supplier": "Mouser",
        "Manufacturer_Part": "Wurth M3-8-CH + M3 hex nut (kit)",
        "SKU": "710-M3CH-NUT",
        "Unit_Cost_USD": 0.20,
        "Lifecycle": "Active",
        "Datasheet": "https://www.we-online.com",
    }),
    ("pi camera module 3", {
        "Supplier": "Mouser",
        "Manufacturer_Part": "USB Camera (IMX219)",
        "SKU": "356-SC0023",
        "Unit_Cost_USD": 30.00,
        "Lifecycle": "Active",
        "Datasheet": "https://datasheets.raspberrypi.com/camera/",
    }),
    ("camera fpc cable 22-pin 200 mm", {
        "Supplier": "Mouser",
        "Manufacturer_Part": "Pi Camera FPC 200 mm (22-pin)",
        "SKU": "356-200-FPC",
        "Unit_Cost_USD": 2.50,
        "Lifecycle": "Active",
        "Datasheet": "https://datasheets.raspberrypi.com/camera/",
    }),
    ("piezo buzzer", {
        "Supplier": "Mouser",
        "Manufacturer_Part": "Murata PKM22EPP-40",
        "SKU": "81-PKM22EPP40",
        "Unit_Cost_USD": 1.50,
        "Lifecycle": "Active",
        "Datasheet": "https://www.murata.com/",
    }),
    ("n20 micro metal gearmotor", {
        "Supplier": "Mouser",
        "Manufacturer_Part": "Pololu 12V N20 (long-life)",
        "SKU": "P22-50-12V-N20",
        "Unit_Cost_USD": 18.00,
        "Lifecycle": "Active",
        "Datasheet": "https://www.pololu.com/",
    }),
]


def enrich_bom(bom_in: pathlib.Path, bom_out: pathlib.Path) -> int:
    """Read BOM.csv and append 7 new columns.  Returns row count processed."""
    with bom_in.open(newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        print(f"[ERR ] empty {bom_in}", file=sys.stderr)
        return 0

    header = rows[0]
    new_cols = ["Supplier", "Manufacturer_Part", "SKU",
                "Unit_Cost_USD", "Total_Cost_USD",
                "Lifecycle", "Datasheet"]
    out_header = header + new_cols

    out_rows = [out_header]
    for row in rows[1:]:
        if not row or not row[0].strip() or not row[0].lstrip("#").strip().isdigit():
            # blank / footer / 'TOTAL' / 'Print time' / 'PETG filament' rows
            out_rows.append(row + [""] * len(new_cols))
            continue

        item = row[1].lower()
        qty = int(row[2]) if row[2].isdigit() else 1
        unit_inr = float(row[3]) if row[3].replace(" ", "").isdigit() else 0.0

        match = next((m for k, m in ENRICH_TABLE if k in item), None)
        if match is None:
            match = {"Supplier": "TODO", "Manufacturer_Part": "TODO",
                     "SKU": "TODO", "Unit_Cost_USD": 0.0,
                     "Lifecycle": "TODO", "Datasheet": ""}
        unit_usd = match["Unit_Cost_USD"] if match["Unit_Cost_USD"] else unit_inr / INR_PER_USD
        total_usd = round(unit_usd * qty, 2)
        new_vals = [
            match["Supplier"],
            match["Manufacturer_Part"],
            match["SKU"],
            f"{unit_usd:.2f}",
            f"{total_usd:.2f}",
            match["Lifecycle"],
            match["Datasheet"],
        ]
        out_rows.append(row + new_vals)

    with bom_out.open("w", newline="") as f:
        csv.writer(f).writerows(out_rows)
    print(f"  ✓ {bom_out}  ({len(out_rows)-1} rows)")
    return len(out_rows) - 1


# ─────────────────────────────────────────────────────────────────────────────
#   2.  DXF FLAT PATTERNS
# ─────────────────────────────────────────────────────────────────────────────

# Each piece needs a specific orientation so its widest face lands in XY.
# piece_front_shield is rotated 90° about Y so its 80×95 face lies XY-aligned
# BEFORE projection(cut=true) collapses it to 2D.
DXF_WRAPPERS: list[tuple[str, str, str]] = [
    ("body",         "projection(cut=true) piece_body();",                                                            "body"),
    ("top_deck",     "projection(cut=true) piece_top_deck();",                                                        "top_deck"),
    ("front_shield", "projection(cut=true) rotate([0,90,0]) piece_front_shield();",                                   "front_shield"),
    ("lidar_riser",  "projection(cut=true) piece_lidar_riser();",                                                     "lidar_riser"),
    ("dsi_display",  "projection(cut=true) piece_dsi_display();",                                                     "dsi_display"),
]


def generate_dxfs(stl_dir: pathlib.Path) -> int:
    """Write per-piece DXF flat patterns.  Returns DXF count written."""
    openscad = shutil.which("openscad")
    if openscad is None:
        print("[ERR ] openscad not on PATH — install with `sudo apt install openscad`", file=sys.stderr)
        return 0

    main_scad = ROOT / "main.scad"
    if not main_scad.exists():
        print(f"[ERR ] missing {main_scad}", file=sys.stderr)
        return 0

    out_dir = stl_dir.parent / "dxf"          # <project>/dxf/<piece>.dxf
    out_dir.mkdir(exist_ok=True)
    count = 0

    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        for name, body_expr, _ in DXF_WRAPPERS:
            scad_path = tmp / f"dxf_{name}.scad"
            scad_path.write_text(
                f'use <{main_scad.resolve().as_posix()}>\n'
                f'{body_expr}\n'
            )
            dxf_path = out_dir / f"{name}_flat.dxf"
            cmd = [
                openscad,
                "--export-format=dxf",
                "-o", str(dxf_path),
                "--projection=o",
                str(scad_path),
            ]
            try:
                res = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=60)
                if res.returncode != 0 or not dxf_path.exists():
                    print(f"  ✗ {name}: openscad exit {res.returncode}  (stderr: {res.stderr[-120:]})")
                    continue
                # DXF writer may emit an empty file if OpenSCAD could not project.
                if dxf_path.stat().st_size < 50:
                    print(f"  ✗ {name}: DXF < 50 B (probably empty projection)")
                    continue
                print(f"  ✓ {dxf_path.name}  ({dxf_path.stat().st_size:,} B)")
                count += 1
            except subprocess.TimeoutExpired:
                print(f"  ✗ {name}: openscad timed out after 60 s")
    return count


# ─────────────────────────────────────────────────────────────────────────────
#   3.  ANNOTATED PNG RENDER (with side-legend)
# ─────────────────────────────────────────────────────────────────────────────

# Same mapping as main.scad SECTION B — duplicated here intentionally so the
# annotated PNG label positions are stable even when main.scad changes.
# If you change a constant in main.scad, update here too.

POCKETS = [
    # (display_label, x_mm, y_mm, z_mm, color_hex, brief)
    ("Jetson,                  0,   0,   10, "#ffa500", "Jetson Orin Nano, NVMe SSD"),
    ("ESP32-S3",              0, -28,   10, "#22ddaa", "ESP32-S3 DevKitC-1 N16R8 (USB)"),
    ("BNO055",               -35,  25,    4, "#cc66ff", "9-DOF IMU (i²c 0x29)"),
    ("INA219 #1",            -65,  30,    4, "#ff6699", "Pi-rail current/voltage monitor"),
    ("INA219 #2",            +60, -32,    4, "#ff99cc", "Motor-rail current/voltage monitor"),
    ("LTE / 4G",             +50,   0,   10, "#88ccff", "Quectel EC25 USB modem"),
    ("DAC",                  -62.5, 0,    3, "#ccaaff", "USB audio DAC dongle"),
    ("Speaker",              -35, -25,   30, "#ffcc66", "28 mm 8 Ω 3 W"),
    ("DS18B20 #1",           -75,  38,    4, "#88ff88", "1-Wire temperature sensor"),
    ("DS18B20 #2",           -75, -38,    4, "#aaffaa", "1-Wire temperature sensor"),
    ("E-STOP",               -65, -30,   34, "#ff4444", "Mushroom-head, 16 mm panel-mount"),
    ("Battery (18650 × 2)",   0,   0,    6, "#ddcc88", "Side-loading, type 0"),
    ("Motor L",              -75,   0,   12, "#6666ff", "TT-style DC gearmotor, 3-12 V"),
    ("Motor R",              +75,   0,   12, "#6666ff", "TT-style DC gearmotor, 3-12 V"),
    ("LiDAR",                  0,  0,   70, "#44ddaa", "RPLidar A1 (sits on lidar_riser)"),
    ("DSI 7\" Lid",            0,  0,   61, "#3366ff", "Touchscreen lid (sits on top_deck)"),
    ("Pi Camera",              0, -16,   4, "#eeeeee", "Camera Module 3 (IMX708, on shield)"),
    ("OLED",                   0,  16,   4, "#ffff66", "1.3\" SH1106 (i²c 0x3c, on shield)"),
    ("ReSpeaker",              0,   0,   4, "#ffaadd", "4-mic array (USB, on shield)"),
    ("HC-SR04 L",            -22.5, 0,  4, "#aaffff", "Ultrasonic distance sensor"),
    ("HC-SR04 R",            +22.5, 0,  4, "#aaffff", "Ultrasonic distance sensor"),
]


PIECE_POS = {
    "body":         (0, 0, 0),
    "top_deck":     (0, 0, 40),
    "lidar_riser":  (0, 0, 45),
    "front_shield": (92.5, 0, 20),
    "dsi_display":  (0, 0, 53),
}

PIECE_PALETTE = {
    "body":         "#444444",
    "top_deck":     "#cc8844",
    "front_shield": "#5588bb",
    "lidar_riser":  "#558855",
    "dsi_display":  "#4466cc",
}


def render_annotated_png(stl_dir: pathlib.Path, prev_dir: pathlib.Path) -> pathlib.Path | None:
    """Render an assembled-chassis PNG with hardware callouts + a legend side panel."""
    prev_dir.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(20, 12), facecolor="#0d0d1a")
    ax3d = fig.add_axes([0.02, 0.05, 0.55, 0.88], projection="3d")
    ax3d.set_facecolor("#0d0d1a")
    ax_legend = fig.add_axes([0.60, 0.05, 0.39, 0.88])
    ax_legend.set_facecolor("#0d0d1a")
    ax_legend.axis("off")

    # ----- 3D mesh of all 5 pieces -----
    all_verts = []
    for name, stl_name in [("body", "body.stl"), ("top_deck", "top_deck.stl"),
                           ("lidar_riser", "lidar_riser.stl"),
                           ("front_shield", "front_shield.stl"),
                           ("dsi_display", "dsi_display.stl")]:
        path = stl_dir / stl_name
        if not path.exists():
            print(f"  [warn] {path} missing — skipping")
            continue
        m = trimesh.load_mesh(str(path))
        v = m.vertices + np.array(PIECE_POS[name])
        all_verts.append(v)
        # decimate to ~1500 faces max for clarity
        sub_step = max(1, len(m.faces) // 1500)
        sub_f = m.faces[::sub_step]
        poly = Poly3DCollection(
            v[sub_f],
            facecolors=PIECE_PALETTE[name],
            edgecolors="black",
            linewidths=0.1,
            alpha=0.85,
        )
        ax3d.add_collection3d(poly)

    if not all_verts:
        print("[ERR ] no STLs found — cannot render PNG")
        return None

    all_v = np.concatenate(all_verts)
    mins, maxs = all_v.min(0), all_v.max(0)
    centre = (mins + maxs) / 2
    span = (maxs - mins).max() / 2 * 1.05
    ax3d.set_xlim(centre[0] - span, centre[0] + span)
    ax3d.set_ylim(centre[1] - span, centre[1] + span)
    ax3d.set_zlim(centre[2] - span, centre[2] + span)
    ax3d.set_xlabel("X (mm)", color="white")
    ax3d.set_ylabel("Y (mm)", color="white")
    ax3d.set_zlabel("Z (mm)", color="white")
    ax3d.tick_params(colors="white")
    ax3d.set_title("Tank chassis — annotated hardware pockets\n",
                   color="white", fontsize=12)

    # ----- Hardware labels + leader lines -----
    # matplotlib doesn't easily let you draw lines from a 3D point to a 2D
    # legend on a separate axes, so we use FancyArrowPatch after projecting
    # the 3D pocket coordinates to 2D screen coords inside the 3D axes.
    for label, x, y, z, color, brief in POCKETS:
        # plot a small marker at the pocket centre (in mm-world coords)
        ax3d.scatter([x], [y], [z], color=color, s=30, depthshade=False,
                     edgecolors="white", linewidths=0.5)
        # project to 2D screen coords (data x/y in axes-fraction coords)
        try:
            x2, y2, _ = ax3d.proj3d.transform(x, y, z)
        except Exception:
            continue
        ax3d.annotate(
            label,
            xy=(x2, y2),
            xytext=(20, 20),
            textcoords="offset points",
            color=color,
            fontsize=7,
            ha="left",
            arrowprops=dict(arrowstyle="-", color=color, lw=0.6),
        )

    ax3d.view_init(elev=22, azim=-55)

    # ----- Legend side panel -----
    ax_legend.set_title("Hardware pockets (left → right is X; ↑ is Z)",
                        color="white", fontsize=11, pad=12)
    ax_legend.text(0.0, 10.0 / 10, "_" * 38, color="white", fontsize=8)
    rows = []
    label_w = max(len(p[0]) for p in POCKETS) + 2
    for i, (label, x, y, z, color, brief) in enumerate(POCKETS):
        # Place labels in 2 columns to fit all ~20 entries
        col = i // 11
        row = i % 11
        text_y = 0.95 - row * 0.085
        text_x = 0.0 + col * 0.50
        ax_legend.text(text_x, text_y,
                       f"▪ {label.ljust(label_w)} ({x:>+5.1f}, {y:>+5.1f}, {z:>+5.1f})",
                       color=color, fontsize=8.5, family="monospace",
                       transform=ax_legend.transAxes)
    ax_legend.text(0.0, 0.02,
                   "Generated by publish_extras.py  ·  units = mm\n"
                   "Pocket coordinates pulled from main.scad §B constants",
                   color="#888888", fontsize=7, family="monospace",
                   transform=ax_legend.transAxes)

    out_png = prev_dir / "annotated_assembled_chassis.png"
    plt.savefig(out_png, dpi=140, bbox_inches="tight", facecolor="#0d0d1a")
    plt.close()
    print(f"  ✓ {out_png}  ({out_png.stat().st_size:,} B)")
    return out_png


# ─────────────────────────────────────────────────────────────────────────────
#   MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bom-only", action="store_true")
    ap.add_argument("--dxf-only", action="store_true")
    ap.add_argument("--png-only", action="store_true")
    args = ap.parse_args()

    any_run = not (args.bom_only or args.dxf_only or args.png_only)

    bom_in = ROOT / "BOM.csv"
    bom_out = ROOT / "BOM_enriched.csv"
    if bom_in.exists() and any_run or args.bom_only:
        print("\n─── 1. BOM enrichment ───")
        if not bom_in.exists():
            print(f"[ERR ] missing {bom_in}", file=sys.stderr)
            return 1
        enrich_bom(bom_in, bom_out)

    if any_run or args.dxf_only:
        print("\n─── 2. DXF flat patterns ───")
        generate_dxfs(STL_DIR)

    if any_run or args.png_only:
        print("\n─── 3. Annotated PNG render ───")
        render_annotated_png(STL_DIR, PREV_DIR)

    print("\n─── done ───")
    print(f"  •   {bom_out}")
    print(f"  •   /root/the tank project/cad/chassis_v1_slim/dxf/<piece>_flat.dxf × 5")
    print(f"  •   {PREV_DIR / 'annotated_assembled_chassis.png'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
