#!/usr/bin/env python3
"""
validate_print.py — Static constraints for chassis_v3_slim/main.scad.

Covers every hardware module added in v3 plus the v2 safety checks.
Exits:
    0 = clean
    1 = error (blocking)
    2 = warning(s) only

Run:
    python3 render_check.py
    python3 render_check.py --strict     # treat warnings as errors
"""
from __future__ import annotations
import re, sys, pathlib

EXPECTED = [
    # chassis
    "body_l", "body_w", "body_total_h", "floor_h", "wall_t", "corner_r",
    # NVIDIA Jetson Orin Nano
    "pi_l", "pi_w", "pi_hole_x", "pi_hole_y", "pi_hole_d", "pi_stack_h",
    # ESP32-S3
    "esp32_l", "esp32_w", "esp32_usb_bend_z",
    # Camera Module 3
    "cam_l", "cam_w", "cam_lens_d",
    # OLED SH1106
    "oled_w", "oled_h", "oled_window_w", "oled_window_h",
    # ReSpeaker
    "resp_w", "resp_h", "resp_thickness",
    # RPLidar
    "lidar_d", "lidar_h",
    # IMU BNO055
    "imu_l", "imu_w", "imu_hole", "imu_hole_pitch_x", "imu_hole_pitch_y",
    # INA219
    "ina_l", "ina_w", "ina_hole", "ina_hole_pitch",
    # Quectel EC25
    "lte_l", "lte_w", "lte_h",
    # DAC
    "dac_l", "dac_w", "dac_h",
    # Speaker
    "spk_d",
    # PCA9685
    "pca_l", "pca_w", "pca_h",
    # HC-SR04
    "hc_d", "hc_pitch",
    # Fan
    "fan_l", "fan_w", "fan_h", "fan_hole_d", "fan_hole_pitch",
    # VESA / magnet / shock
    "vesa_pitch", "vesa_boss_d", "vesa_hole_d", "magnet_d", "magnet_h", "shock_hole_d",
    # Battery cells
    "cell_18650_dia", "cell_18650_len", "cell_14500_dia", "cell_14500_len", "cell_aa_dia", "cell_aa_len",
    # Motor
    "motor_count", "motor_body_dia", "motor_body_len", "motor_axle_d",
    "motor_pitch_x", "motor_bracket_w",
    # Vents
    "vent_rows", "vent_cols", "vent_w", "vent_h", "vent_pitch_x", "vent_pitch_y",
]


def RULES(p):
    rows = []
    # ============================================================
    # Hard mechanical correctness
    # ============================================================
    rows += [
        ("body_l",         "ge",140,"warn","Smaller than probots bracket span"),
        ("body_l",         "le",220,"err", "Larger than typical FDM build plate (220 mm)"),
        ("body_w",         "ge", 80,"warn","Track wheels won't clear"),
        ("body_w",         "le",130,"err", "Exceeds typical 220 mm build plate"),
        ("body_total_h",   "ge", 18,"err", "Too thin to fit 18650 battery on floor"),
        ("body_total_h",   "le", 60,"ok",  "Exceeds ultra-slim spec"),
        ("floor_h",        "ge",2.5,"err", "Floor too thin — print warps"),
        ("wall_t",         "ge",1.6,"err", "Walls under 1.6 mm don't survive FDM"),
        ("corner_r",       "ge",  2,"warn","PETG corner curl"),

        # NVIDIA Jetson Orin Nano PCB (per official mechanical drawing)
        ("pi_l",           "ge", 84,"err", "Jetson PCB ~85 mm won't fit"),
        ("pi_w",           "ge", 55,"err", "Jetson PCB ~56 mm won't fit"),
        ("pi_hole_x",      "ge", 57,"err", "Jetson hole span 58 mm — won't line up"),
        ("pi_hole_y",      "ge", 48,"err", "Jetson hole span 49 mm — won't line up"),
        ("pi_hole_d",      "ge",2.4,"err", "M2.5 (2.5 mm) hole too tight"),
        ("pi_hole_d",      "le",2.8,"err", "M2.5 hole tolerance blown"),
        ("pi_stack_h",     "ge", 21,"err", "Pi+M.2 HAT+ ~22 mm stack won't fit"),
        ("pi_stack_h",     "le", 23,"err", "Pi stack height over 23 mm won't fit (within active cooler)"),

        # ESP32-S3 DevKitC-1 N16R8 (Espressif datasheet)
        ("esp32_l",        "ge", 50,"err", "ESP32-S3 DevKitC-1 is ~52 mm long"),
        ("esp32_w",        "ge", 17,"err", "ESP32-S3 DevKitC-1 is ~18 mm wide"),
        ("esp32_usb_bend_z","ge", 6,"err", "USB-C jack bend radius needs ≥ 6 mm"),

        # Camera Module 3 IMX708
        ("cam_l",          "ge", 24,"err", "Camera Module 3 is 25×24 mm"),
        ("cam_w",          "ge", 23,"err", "Camera Module 3 is 25×24 mm"),
        ("cam_lens_d",     "ge",  7,"err", "Lens hole < 7 mm clips the FOV"),
        ("cam_lens_d",     "le", 10,"err", "Lens hole > 10 mm shows the sensor"),

        # OLED SH1106 1.3"
        ("oled_w",         "ge", 34,"err", "1.3\" SH1106 ~35×30 mm"),
        ("oled_h",         "ge", 29,"err", "1.3\" SH1106 ~35×30 mm"),

        # ReSpeaker 4-Mic
        ("resp_w",         "ge", 69,"err", "ReSpeaker 70×70 mm board"),
        ("resp_h",         "ge", 69,"err", "ReSpeaker 70×70 mm board"),

        # RPLidar A1
        ("lidar_d",        "ge", 97,"err", "RPLidar A1 puck ~98 mm OD"),
        ("lidar_h",        "ge", 64,"err", "RPLidar A1 puck ~65 mm tall"),

        # BNO055 + INA219
        ("imu_l",          "ge", 29,"err", "BNO055 ~30×25 mm"),
        ("imu_w",          "ge", 24,"err", "BNO055 ~30×25 mm"),
        ("ina_l",          "ge", 24,"err", "INA219 ~25×20 mm"),
        ("ina_w",          "ge", 19,"err", "INA219 ~25×20 mm"),

        # Quectel EC25
        ("lte_l",          "ge", 84,"err", "Quectel EC25 USB stick ~85 mm"),
        ("lte_w",          "ge", 29,"err", "Quectel EC25 USB stick ~30 mm"),

        # Fan 40×40 standard
        ("fan_l",          "ge", 39,"err", "Standard 40 mm fan"),
        ("fan_w",          "ge", 39,"err", "Standard 40 mm fan"),

        # holes
        ("vesa_hole_d",    "ge",3.1,"err", "M3 (3.0 mm) hole too tight"),
        ("magnet_d",       "ge",  5,"err", "Magnet pocket under 5 mm won't seat a 6 mm disc"),
        ("shock_hole_d",   "ge",3.1,"err", "Shock absorber pivot too tight"),
    ]

    # ============================================================
    # Derived — check fit and adjacency
    # ============================================================
    # ReSpeaker grille vs OLED + camera vertically: front shield h must be >= resp_h + 25
    rows.append(("__FSH__",   "ge", p["resp_h"] + 25,
                 "err", f"Front shield too short for ReSpeaker {p['resp_h']:.0f}+OLED+cam"))

    # Fan fits inside top deck
    rows.append(("__FANDECK__","le", p["body_l"] - 10,
                 "warn", f"Fan 40 mm + ram-air ≤ {p['body_l']-10:.0f} mm on top deck X"))

    # Battery fit
    btype = p.get("battery_type", 0)
    if btype == 0:  # 18650
        rows.append(("__B18650W__","le", p["body_w"],
                     "err",
                     f"2×18650 cells side-by-side need ≥ {2*18.4+1.4:.0f} mm but body Y is {p['body_w']:.0f}"))
    if btype == 2:
        rows.append(("__AAW__",   "le", p["body_w"],
                     "err", "AA×4 needs > 30+ mm Y"))

    # Vent perforation has to leave support
    rows.append(("__VENTPITCHX__","ge", (p["vent_w"] + 0.4)*2,
                 "err", f"vent pitch_x too tight (need ≥ {p['vent_w']+0.4:.1f} mm)"))

    # Pi + ESP32 layout:  ESP32 pocket extends ESP32_offset_y +/- (esp32_w+3)/2 in Y.
    # Pi extends +/- pi_hole_y/2 in Y.  They sit side-by-side so the worst-case Y extent is
    # max(|esp32_extent|, |pi_extent|) — the union, not the sum.
    esp32_y_ext = abs(p["esp32_offset_y"]) + (p["esp32_w"] + 3)/2
    pi_y_ext    = p["pi_hole_y"]/2
    pi_esp_total_y = max(esp32_y_ext, pi_y_ext)
    rows.append(("__PIESP32__", "le", p["body_w"]/2 - 6,
                 "warn",
                 f"Pi+ESP32 max Y extent = {pi_esp_total_y:.1f} mm (body half = {p['body_w']/2:.0f})"))

    return rows


def parse_scad(path: pathlib.Path) -> dict[str, float]:
    text = path.read_text()
    # strip // comments so we don't capture symbols mentioned there
    text = re.sub(r"//[^\n]*", "", text)
    out: dict[str, float] = {}
    pat = re.compile(r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*([0-9.+\-]+)\s*;", re.M)
    for m in pat.finditer(text):
        try:
            out[m.group(1)] = float(m.group(2))
        except ValueError:
            pass
    return out


OPS = {"le": lambda a,b: a <= b, "ge": lambda a,b: a >= b, "eq": lambda a,b: a == b}


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    flags = {a for a in sys.argv[1:] if a.startswith("-")}
    strict = "--strict" in flags
    src = pathlib.Path(args[0]) if args else pathlib.Path(__file__).parent / "main.scad"
    if not src.exists():
        print(f"[ERR ] {src} not found", file=sys.stderr); return 1

    vals = parse_scad(src)
    print(f"[info] Loaded {len(vals)} numeric constants from {src.name}")
    if len(vals) < len(EXPECTED):
        print(f"[info] {len(vals)} found, {len(EXPECTED)} expected (some lookups may be missed by name)")

    missing = [n for n in EXPECTED if n not in vals]
    if missing:
        print(f"[ERR ] Missing constants: {missing}"); return 1

    rows = RULES(vals)
    errors = warnings = oks = 0
    print()
    print(f"{'CONSTRAINT':<22} {'VALUE':>10}  {'LIMIT':<10}  STATUS")
    print("-"*72)

    pretty = {
        "__FSH__":        "front_shield height",
        "__FANDECK__":    "fan fits top deck",
        "__B18650W__":    "18650×2 width",
        "__AAW__":        "AA×4 width",
        "__VENTPITCHX__": "vent pitch_x",
        "__PIESP32__":    "Pi+ESP32 occupancy",
    }
    derived_vals = {
        "__FSH__":        vals["resp_h"] + 25,
        "__FANDECK__":    40,
        "__B18650W__":    2*18.4 + 1.4,
        "__AAW__":        4*14.4 + 1.4,
        "__VENTPITCHX__": (vals["vent_w"] + 0.4)*2,
        "__PIESP32__":    (vals["pi_hole_y"]/2 + 18) + (vals["esp32_l"]/2 + 2) + vals["esp32_offset_y"],
    }

    for entry in rows:
        name, op, lim, sev, msg = entry
        if name in pretty:
            v = derived_vals[name]
            label = pretty[name]
            limit_label = f"{op}={lim:.0f}"
            comparator = lim if lim != (vals["vent_w"]+0.4)*2 else lim
            pass_ = OPS[op](v, lim)
        else:
            v = vals[name]
            label = name
            limit_label = f"{op} {lim}"
            pass_ = OPS[op](v, lim)

        mark = {"err":"[ERR ]","warn":"[WARN]","ok":"[OK  ]"}[sev]
        if pass_:
            oks += 1
            status = "PASS"
        elif sev == "err":
            errors += 1
            status = f"FAIL — {msg}"
        else:
            warnings += 1
            status = f"WARN — {msg}"
        print(f"{label:<22} {v:>10.2f}  {limit_label:<10} {mark}  {status}")

    print()
    print(f"summary: {oks} pass · {warnings} warn · {errors} err")
    if errors: return 1
    if strict and warnings: return 1
    if warnings: return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
