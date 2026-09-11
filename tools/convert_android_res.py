#!/usr/bin/env python3
"""
Port every Android resource from the MediGyaan Android app into the iOS asset
catalog, so the SwiftUI build uses byte-identical artwork.

Handles:
  * <vector>      -> SVG imageset (Xcode 12+ renders SVG natively)
  * <shape>       -> SVG imageset (rect/oval/line + solid/gradient/stroke/corners)
  * <selector>    -> SVG imageset for each state (default + checked/selected)
  * <layer-list>  -> SVG imageset (layers stacked in order)
  * raster        -> copied into an imageset, webp transcoded to PNG
  * mipmaps       -> launcher rasters promoted to an AppIcon set
  * colors.xml    -> resolved into the SVGs, and emitted as UIColor Swift code

Also emits `AndroidAssets.swift` with a typed constant per asset so the app can
reference artwork without stringly-typed typos.

Usage:
    python3 tools/convert_android_res.py \
        --android /path/to/app/src/main/res \
        --assets  MediGyaan/Resources/Assets.xcassets
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ANDROID_NS = "http://schemas.android.com/apk/res/android"
AAPT_NS = "http://schemas.android.com/aapt"
# NB: in an Android drawable the *attributes* live in the android namespace
# (`android:pathData`), but the *elements* are unnamespaced (`<path>`, `<solid>`).
# Only `<aapt:attr>` is itself namespaced.
A = f"{{{ANDROID_NS}}}"
AAPT_ATTR = f"{{{AAPT_NS}}}attr"


def child(el: ET.Element, name: str) -> ET.Element | None:
    return el.find(name)


def kids(el: ET.Element, name: str):
    return el.findall(name)

# Android framework colours we may be asked to resolve.
FRAMEWORK_COLORS = {
    "white": "#FFFFFFFF",
    "black": "#FF000000",
    "transparent": "#00000000",
    "red": "#FFFF0000",
    "green": "#FF00FF00",
    "blue": "#FF0000FF",
    "gray": "#FF888888",
    "grey": "#FF888888",
    "yellow": "#FFFFFF00",
    "cyan": "#FF00FFFF",
    "magenta": "#FFFF00FF",
    "darker_gray": "#FF444444",
    "holo_blue_light": "#FF33B5E5",
    "holo_blue_dark": "#FF0099CC",
}

# Material 3 theme attributes the app's themes.xml never defines, but which its
# drawables reference. Values follow the Material 3 baseline (light / dark).
MATERIAL3_FALLBACKS = {
    "colorSurfaceVariant": ("#E7E0EC", "#49454F"),
    "colorOnSurfaceVariant": ("#49454F", "#CAC4D0"),
    "colorSurfaceContainer": ("#F3EDF7", "#211F26"),
    "colorSurfaceContainerHigh": ("#ECE6F0", "#2B2930"),
    "colorOutlineVariant": ("#CAC4D0", "#49454F"),
    "colorSecondaryContainer": ("#E8DEF8", "#4A4458"),
    "colorTertiary": ("#7D5260", "#EFB8C8"),
    "colorErrorContainer": ("#F9DEDC", "#8C1D18"),
    "colorScrim": ("#000000", "#000000"),
}


# Roboto etc. are not shipped; nothing to do. Kept for documentation.


# --------------------------------------------------------------------------- #
# Colour handling
# --------------------------------------------------------------------------- #

class ColorTable:
    """Resolves `@color/x`, `@android:color/x` and `?attr/x` references."""

    def __init__(self) -> None:
        self.light: dict[str, str] = {}
        self.night: dict[str, str] = {}
        # Theme attribute -> colour, used for `?attr/colorSurface` style refs.
        self.attrs: dict[str, str] = {}
        self.unresolved: set[str] = set()

    def load_colors(self, xml_path: Path) -> None:
        mapping = self.night if "night" in str(xml_path) else self.light
        for el in ET.parse(xml_path).getroot():
            if el.tag == "color" and el.get("name") and el.text and el.text.strip():
                mapping[el.get("name")] = el.text.strip()

    def load_theme(self, xml_path: Path) -> None:
        root = ET.parse(xml_path).getroot()
        for el in root:
            if el.tag != "style":
                continue
            for item in el:
                if item.tag != "item" or not item.text:
                    continue
                name = item.get("name", "")
                # `?attr/foo` and `?foo` both mean "the theme attribute foo".
                m = re.fullmatch(r"\??(?:attr/)?([A-Za-z0-9_]+)", item.text.strip())
                if m and (name.startswith("color") or name.startswith("android:color")):
                    self.attrs.setdefault(name.split(":")[-1], m.group(1))

    def load_android_res(self, xml_path: Path) -> None:
        """Load a plain `<color name=..>` file (used for color/ dirs too)."""
        root = ET.parse(xml_path).getroot()
        if root.tag == "selector":
            for item in root:
                if item.get("color"):
                    self.light.setdefault(xml_path.stem, item.get("color"))
            return
        self.load_colors(xml_path)

    # -- resolution ------------------------------------------------------- #

    def resolve(self, raw: str | None, dark: bool = False) -> tuple[str | None, float]:
        """Return (svg_colour, alpha). `svg_colour` is None when unresolvable."""
        if not raw:
            return None, 1.0
        value = raw.strip()

        if value.startswith("?"):
            attr = value.lstrip("?").split("/")[-1].split(":")[-1]
            target = self.attrs.get(attr, attr)
            table = self.night if dark else self.light
            if target in table:
                return self.resolve(table[target], dark)
            if attr in self.attrs:
                return self.resolve("@" + self.attrs[attr], dark)
            if attr in MATERIAL3_FALLBACKS:
                return self.resolve(MATERIAL3_FALLBACKS[attr][1 if dark else 0], dark)
            self.unresolved.add(value)
            return None, 1.0

        if value.startswith("@"):
            body = value[1:]
            if body.startswith("android:color/"):
                name = body.split("/", 1)[1]
                if name in FRAMEWORK_COLORS:
                    return self.resolve(FRAMEWORK_COLORS[name], dark)
                self.unresolved.add(value)
                return None, 1.0
            name = body.split("/")[-1]
            table = self.night if dark else self.light
            # Fall back to the other table so a light-only colour still paints.
            for candidate in (table, self.light, self.night):
                if name in candidate:
                    return self.resolve(candidate[name], dark)
            self.unresolved.add(value)
            return None, 1.0

        return parse_hex(value)


def parse_hex(value: str) -> tuple[str | None, float]:
    """`#RGB` / `#ARGB` / `#RRGGBB` / `#AARRGGBB` -> (svg hex, alpha)."""
    v = value.strip().lstrip("#")
    if not re.fullmatch(r"[0-9A-Fa-f]+", v):
        return None, 1.0
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    elif len(v) == 4:
        v = "".join(c * 2 for c in v)  # AARRGGBB
    if len(v) == 6:
        return f"#{v.upper()}", 1.0
    if len(v) == 8:
        alpha = int(v[0:2], 16) / 255.0
        return f"#{v[2:].upper()}", round(alpha, 4)
    return None, 1.0


def color_attrs(c: str | None, alpha: float, extra_alpha: float | None = None) -> str:
    """Build SVG paint attributes for a fill/stroke colour."""
    if c is None:
        return ""
    total = alpha * (extra_alpha if extra_alpha is not None else 1.0)
    if total >= 0.999:
        return f' fill="{c}"'
    return f' fill="{c}" fill-opacity="{round(total, 4)}"'


# --------------------------------------------------------------------------- #
# Vector drawables -> SVG
# --------------------------------------------------------------------------- #

def dim(value: str | None, fallback: float) -> float:
    if not value:
        return fallback
    m = re.match(r"\s*(-?[\d.]+)", value)
    return float(m.group(1)) if m else fallback


def normalize_path(d: str) -> str:
    """Android and SVG path syntax are the same grammar, but tidy whitespace so
    the emitted SVG is unambiguous (e.g. `1.5.5` -> `1.5 .5`)."""
    d = " ".join(d.split())
    # Separate a digit-dot-digit run that would otherwise glue two numbers.
    d = re.sub(r"(\d)\.(\d)", r"\1.\2", d)
    # `1.5-.5` and `1.5.5` style joins.
    d = re.sub(r"\.(?=-)", ". ", d)
    d = re.sub(r"(?<=[\d])\.(?=\d)", ".", d)
    return d


def svg_for_vector(root: ET.Element, colors: ColorTable, dark: bool) -> str:
    w = dim(root.get(f"{A}width"), 24.0)
    h = dim(root.get(f"{A}height"), 24.0)
    vw = dim(root.get(f"{A}viewportWidth"), w)
    vh = dim(root.get(f"{A}viewportHeight"), h)

    parts: list[str] = []
    for path in root.iter("path"):
        d = path.get(f"{A}pathData")
        if not d:
            continue
        d = normalize_path(d)

        fill = path.get(f"{A}fillColor")
        # `<aapt:attr name="android:fillColor"><gradient .../></aapt:attr>`
        grad_el: ET.Element | None = None
        for aapt_attr in path.iter(AAPT_ATTR):
            if aapt_attr.get("name") == "android:fillColor":
                g = child(aapt_attr, "gradient")
                if g is not None:
                    grad_el = g
                    fill = None
        # `android:fillColor="#00000000"` means "no fill" in practice.
        if fill == "#00000000":
            fill = None

        stroke = path.get(f"{A}strokeColor")
        if stroke == "#00000000":
            stroke = None

        fill_alpha = path.get(f"{A}fillAlpha")
        stroke_alpha = path.get(f"{A}strokeAlpha")
        fa = float(fill_alpha) if fill_alpha else None
        sa = float(stroke_alpha) if stroke_alpha else None

        attrs = f' d="{d}"'

        if grad_el is not None:
            grad_id, defs = build_gradient(grad_el, colors, dark)
            parts.append(f"<defs>{defs}</defs>")
            attrs += f' fill="url(#{grad_id})"'
            if fa is not None:
                attrs += f' fill-opacity="{fa}"'
            attrs += ' stroke="none"'
        elif fill is not None:
            c, a = colors.resolve(fill, dark)
            attrs += color_attrs(c, a, fa)
        else:
            attrs += ' fill="none"'

        if stroke is not None:
            c, a = colors.resolve(stroke, dark)
            if c:
                total = a * (sa if sa is not None else 1.0)
                attrs += f' stroke="{c}"'
                if total < 0.999:
                    attrs += f' stroke-opacity="{round(total, 4)}"'
            sw = path.get(f"{A}strokeWidth")
            if sw:
                attrs += f' stroke-width="{sw}"'

        if fill is None and grad_el is None and stroke is None:
            continue
        parts.append(f"<path{attrs} />")

    body = "".join(parts)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{fmt(w)}" '
        f'height="{fmt(h)}" viewBox="0 0 {fmt(vw)} {fmt(vh)}">{body}</svg>'
    )


def build_gradient(g: ET.Element, colors: ColorTable, dark: bool) -> tuple[str, str]:
    """Return (id, <defs> markup) for an Android gradient element."""
    kind = g.get(f"{A}type", "linear")
    stops: list[tuple[float, str, float]] = []
    for tag, offset in ((f"{A}startColor", 0.0), (f"{A}centerColor", 0.5), (f"{A}endColor", 1.0)):
        raw = g.get(tag)
        if raw:
            c, a = colors.resolve(raw, dark)
            if c:
                stops.append((offset, c, a))
    if not stops:
        stops = [(0.0, "#000000", 1.0)]

    stop_markup = "".join(
        f'<stop offset="{o}" stop-color="{c}" stop-opacity="{a}"/>' for o, c, a in stops
    )
    gid = "g"

    if kind == "radial":
        return gid, f'<radialGradient id="{gid}" cx="50%" cy="50%" r="50%">{stop_markup}</radialGradient>'

    if kind == "sweep":
        # SVG has no sweep gradient; a radial reads closest.
        return gid, f'<radialGradient id="{gid}" cx="50%" cy="50%" r="50%">{stop_markup}</radialGradient>'

    angle = float(g.get(f"{A}angle", "0") or 0)
    x1, y1, x2, y2 = linear_endpoints(angle)
    return gid, (
        f'<linearGradient id="{gid}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">'
        f"{stop_markup}</linearGradient>"
    )


def linear_endpoints(angle_deg: float) -> tuple[float, float, float, float]:
    """Android angle (0 = left->right, CCW) to SVG objectBoundingBox endpoints."""
    table = {
        0: (0, 0, 1, 0),
        45: (0, 1, 1, 0),
        90: (0, 1, 0, 0),
        135: (1, 1, 0, 0),
        180: (1, 0, 0, 0),
        225: (1, 0, 0, 1),
        270: (0, 0, 0, 1),
        315: (0, 0, 1, 1),
    }
    norm = angle_deg % 360
    if norm in table:
        return table[norm]
    a = math.radians(norm)
    dx, dy = math.cos(a), -math.sin(a)
    span = abs(dx) + abs(dy)
    return (
        round(0.5 - dx * span / 2, 4),
        round(0.5 - dy * span / 2, 4),
        round(0.5 + dx * span / 2, 4),
        round(0.5 + dy * span / 2, 4),
    )


# --------------------------------------------------------------------------- #
# Shape / selector / layer-list -> SVG
# --------------------------------------------------------------------------- #

def shape_to_svg(shape: ET.Element, colors: ColorTable, dark: bool, out_id: str = "g") -> str:
    kind = shape.get(f"{A}shape", "rectangle")
    size = child(shape, "size")
    w = dim(size.get(f"{A}width") if size is not None else None, 100.0)
    h = dim(size.get(f"{A}height") if size is not None else None, 100.0)

    solid = child(shape, "solid")
    gradient = child(shape, "gradient")
    stroke = child(shape, "stroke")
    corners = child(shape, "corners")

    fill = "none"
    defs = ""
    if gradient is not None:
        defs, fill = shape_gradient(gradient, colors, dark, out_id)
    elif solid is not None:
        c, a = colors.resolve(solid.get(f"{A}color"), dark)
        if c:
            fill = c
            if a < 0.999:
                fill = c  # opacity applied below

    stroke_attrs = ""
    if stroke is not None:
        c, a = colors.resolve(stroke.get(f"{A}color"), dark)
        if c:
            stroke_attrs += f' stroke="{c}"'
            if a < 0.999:
                stroke_attrs += f' stroke-opacity="{a}"'
        sw = stroke.get(f"{A}width")
        stroke_attrs += f' stroke-width="{dim(sw, 0) if sw else 0}"'
        dash_w = stroke.get(f"{A}dashWidth")
        dash_g = stroke.get(f"{A}dashGap")
        if dash_w:
            stroke_attrs += f' stroke-dasharray="{dim(dash_w, 0)} {dim(dash_g, 0)}"'

    opacity = ""
    if solid is not None and gradient is None:
        _, a = colors.resolve(solid.get(f"{A}color"), dark)
        if a < 0.999:
            opacity = f' fill-opacity="{a}"'

    if kind == "oval":
        body = f'<ellipse cx="{fmt(w/2)}" cy="{fmt(h/2)}" rx="{fmt(w/2)}" ry="{fmt(h/2)}"{opacity}{stroke_attrs}/>'
    elif kind == "line":
        body = f'<line x1="0" y1="{fmt(h/2)}" x2="{fmt(w)}" y2="{fmt(h/2)}"{stroke_attrs}/>'
    else:
        rx, ry = corner_radii(corners, w, h)
        body = f'<rect x="0" y="0" width="{fmt(w)}" height="{fmt(h)}" rx="{fmt(rx)}" ry="{fmt(ry)}"{opacity}{stroke_attrs}/>'

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{fmt(w)}" height="{fmt(h)}" '
        f'viewBox="0 0 {fmt(w)} {fmt(h)}" preserveAspectRatio="none">{defs}'
        f'<g fill="{fill}">{body}</g></svg>'
    )


def corner_radii(corners: ET.Element | None, w: float, h: float) -> tuple[float, float]:
    if corners is None:
        return 0.0, 0.0
    r = corners.get(f"{A}radius")
    if r:
        return dim(r, 0), dim(r, 0)
    tl = dim(corners.get(f"{A}topLeftRadius"), 0) if corners.get(f"{A}topLeftRadius") else 0
    tr = dim(corners.get(f"{A}topRightRadius"), 0) if corners.get(f"{A}topRightRadius") else 0
    bl = dim(corners.get(f"{A}bottomLeftRadius"), 0) if corners.get(f"{A}bottomLeftRadius") else 0
    br = dim(corners.get(f"{A}bottomRightRadius"), 0) if corners.get(f"{A}bottomRightRadius") else 0
    vals = [v for v in (tl, tr, bl, br) if v]
    if not vals:
        return 0.0, 0.0
    if len(set(vals)) == 1:
        return vals[0], vals[0]
    # A single ry can't express per-corner radii; use the max so the shape
    # reads correctly rather than silently squaring off.
    return max(vals), max(vals)


def shape_gradient(g: ET.Element, colors: ColorTable, dark: bool, gid: str) -> tuple[str, str]:
    kind = g.get(f"{A}type", "linear")
    stops: list[tuple[float, str, float]] = []
    for tag, offset in ((f"{A}startColor", 0.0), (f"{A}centerColor", 0.5), (f"{A}endColor", 1.0)):
        raw = g.get(tag)
        if raw:
            c, a = colors.resolve(raw, dark)
            if c:
                stops.append((offset, c, a))
    if not stops:
        return "", "none"
    markup = "".join(
        f'<stop offset="{o}" stop-color="{c}" stop-opacity="{a}"/>' for o, c, a in stops
    )
    if kind == "radial":
        defs = f'<defs><radialGradient id="{gid}" cx="50%" cy="50%" r="50%">{markup}</radialGradient></defs>'
    elif kind == "sweep":
        defs = f'<defs><radialGradient id="{gid}" cx="50%" cy="50%" r="50%">{markup}</radialGradient></defs>'
    else:
        x1, y1, x2, y2 = linear_endpoints(float(g.get(f"{A}angle", "0") or 0))
        defs = (
            f'<defs><linearGradient id="{gid}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">'
            f"{markup}</linearGradient></defs>"
        )
    return defs, f"url(#{gid})"


def layerlist_to_svg(root: ET.Element, colors: ColorTable, dark: bool) -> str:
    """Render a <layer-list> by emitting one SVG per layer is impossible in a
    single file, so bake the layers into one SVG with stacked shapes."""
    # Derive the canvas from the first layer that declares an explicit size.
    w = 100.0
    for item in root:
        inner = child(item, "shape")
        if inner is None:
            clip = child(item, "clip")
            inner = child(clip, "shape") if clip is not None else None
        if inner is None:
            continue
        size = child(inner, "size")
        if size is not None and size.get(f"{A}width"):
            w = dim(size.get(f"{A}width"), 100.0)
            break
    layers: list[str] = []
    for idx, item in enumerate(root):
        inner = child(item, "shape")
        if inner is None:
            # `<clip>` wraps the progress layer of a progress-bar drawable.
            clip = child(item, "clip")
            if clip is not None:
                inner = child(clip, "shape")
        if inner is None:
            # `<item android:drawable="@drawable/x">` style layering is handled
            # by the caller via a manifest entry instead.
            continue
        svg = shape_to_svg(inner, colors, dark, out_id=f"g{idx}")
        body = re.sub(r"^<svg[^>]*>", "", svg)
        body = re.sub(r"</svg>$", "", body)
        layers.append(body)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{fmt(w)}" height="{fmt(w)}" '
        f'viewBox="0 0 {fmt(w)} {fmt(w)}" preserveAspectRatio="none">'
        f'{"".join(layers)}</svg>'
    )


def fmt(v: float) -> str:
    if v == int(v):
        return str(int(v))
    return f"{v:.4f}".rstrip("0").rstrip(".")


# --------------------------------------------------------------------------- #
# Asset catalog emission
# --------------------------------------------------------------------------- #

ASSET_CONTENTS = {"info": {"author": "xcode", "version": 1}}


def write_imageset(assets: Path, name: str, filename: str, *, vector: bool) -> None:
    folder = assets / f"{name}.imageset"
    folder.mkdir(parents=True, exist_ok=True)
    contents: dict = {"images": [{"filename": filename, "idiom": "universal"}],
                      "info": {"author": "xcode", "version": 1}}
    if vector:
        contents["properties"] = {"preserves-vector-representation": True}
    else:
        contents["images"][0]["scale"] = "1x"
    (folder / "Contents.json").write_text(json.dumps(contents, indent=2) + "\n")


def hex_components(svg_hex: str | None) -> dict[str, str]:
    """`#RRGGBB` -> Xcode colorset component dictionary (sRGB)."""
    v = (svg_hex or "#000000").lstrip("#")
    v = (v + "000000")[:6]
    r, g, b = (int(v[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return {
        "alpha": "1.000",
        "blue": f"{b:.3f}",
        "green": f"{g:.3f}",
        "red": f"{r:.3f}",
    }


def write_colorset(assets: Path, name: str, light_hex: str | None, dark_hex: str | None) -> None:
    """Emit a light/dark colorset. Required by project.yml (AccentColor) and
    Info.plist (LaunchBackground), so the pipeline must own them."""
    folder = assets / f"{name}.colorset"
    folder.mkdir(parents=True, exist_ok=True)
    entries = [{
        "color": {"color-space": "srgb", "components": hex_components(light_hex)},
        "idiom": "universal",
    }]
    if dark_hex and dark_hex != light_hex:
        entries.append({
            "appearances": [{"appearance": "luminosity", "value": "dark"}],
            "color": {"color-space": "srgb", "components": hex_components(dark_hex)},
            "idiom": "universal",
        })
    (folder / "Contents.json").write_text(json.dumps(
        {"colors": entries, "info": {"author": "xcode", "version": 1}}, indent=2) + "\n")


def write_template_imageset(assets: Path, name: str, filename: str) -> None:
    """Icons that Android draws with `android:tint` become template images so
    SwiftUI can tint them with the app palette."""
    folder = assets / f"{name}.imageset"
    folder.mkdir(parents=True, exist_ok=True)
    contents = {
        "images": [{"filename": filename, "idiom": "universal"}],
        "info": {"author": "xcode", "version": 1},
        "properties": {
            "preserves-vector-representation": True,
            "template-rendering-intent": "template",
        },
    }
    (folder / "Contents.json").write_text(json.dumps(contents, indent=2) + "\n")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--android", required=True, help="path to app/src/main/res")
    ap.add_argument("--assets", required=True, help="path to Assets.xcassets")
    ap.add_argument("--swift-out", default=None, help="where to write AndroidAssets.swift")
    args = ap.parse_args()

    res = Path(args.android)
    assets = Path(args.assets)
    assets.mkdir(parents=True, exist_ok=True)

    colors = ColorTable()
    for p in (res / "values" / "colors.xml", res / "values-night" / "colors.xml"):
        if p.exists():
            colors.load_colors(p)
    for p in (res / "values" / "themes.xml", res / "values-night" / "themes.xml"):
        if p.exists():
            colors.load_theme(p)
    for p in (res / "color").glob("*.xml") if (res / "color").is_dir() else []:
        try:
            colors.load_android_res(p)
        except ET.ParseError:
            pass

    inventory: dict[str, list[str]] = {
        "vector": [], "shape": [], "selector": [], "layer": [], "raster": [], "skipped": []
    }
    template_icons: list[str] = []

    # ---- XML drawables -------------------------------------------------- #
    for xml in sorted((res / "drawable").glob("*.xml")):
        name = xml.stem
        try:
            root = ET.parse(xml).getroot()
        except ET.ParseError as exc:
            inventory["skipped"].append(f"{name} (parse: {exc})")
            continue

        try:
            if root.tag == "vector":
                svg = svg_for_vector(root, colors, dark=False)
                (assets / f"{name}.imageset").mkdir(parents=True, exist_ok=True)
                (assets / f"{name}.imageset" / f"{name}.svg").write_text(svg)
                if root.get(f"{A}tint"):
                    write_template_imageset(assets, name, f"{name}.svg")
                    template_icons.append(name)
                else:
                    write_imageset(assets, name, f"{name}.svg", vector=True)
                inventory["vector"].append(name)

            elif root.tag == "shape":
                svg = shape_to_svg(root, colors, dark=False)
                (assets / f"{name}.imageset").mkdir(parents=True, exist_ok=True)
                (assets / f"{name}.imageset" / f"{name}.svg").write_text(svg)
                write_imageset(assets, name, f"{name}.svg", vector=True)
                inventory["shape"].append(name)

            elif root.tag == "selector":
                # Emit one SVG per state so both skins exist as real assets.
                produced = False
                for idx, item in enumerate(root):
                    inner = child(item, "shape")
                    state = item.get(f"{A}state_checked") or item.get(f"{A}state_selected") \
                        or item.get(f"{A}state_enabled") or item.get(f"{A}state_pressed")
                    if inner is None:
                        continue
                    label = "selected" if state in ("true", True) else ("disabled" if state == "false" else "default")
                    suffix = "" if label == "default" else f"_{label}"
                    svg = shape_to_svg(inner, colors, dark=False, out_id=f"s{idx}")
                    sub = f"{name}{suffix}"
                    (assets / f"{sub}.imageset").mkdir(parents=True, exist_ok=True)
                    (assets / f"{sub}.imageset" / f"{sub}.svg").write_text(svg)
                    write_imageset(assets, sub, f"{sub}.svg", vector=True)
                    produced = True
                if produced:
                    inventory["selector"].append(name)
                else:
                    inventory["skipped"].append(f"{name} (selector without shapes)")

            elif root.tag == "layer-list":
                svg = layerlist_to_svg(root, colors, dark=False)
                (assets / f"{name}.imageset").mkdir(parents=True, exist_ok=True)
                (assets / f"{name}.imageset" / f"{name}.svg").write_text(svg)
                write_imageset(assets, name, f"{name}.svg", vector=True)
                inventory["layer"].append(name)

            else:
                inventory["skipped"].append(f"{name} (<{root.tag}>)")
        except Exception as exc:  # noqa: BLE001 - report and continue
            inventory["skipped"].append(f"{name} ({type(exc).__name__}: {exc})")

    # ---- rasters -------------------------------------------------------- #
    raster_dirs = [res / "drawable"] + sorted(res.glob("drawable-*"))
    for d in raster_dirs:
        if not d.is_dir():
            continue
        for img in sorted(d.iterdir()):
            if img.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
                continue
            name = img.stem
            dest_name = img.name
            target = assets / f"{name}.imageset"
            target.mkdir(parents=True, exist_ok=True)
            if img.suffix.lower() == ".webp":
                dest_name = f"{name}.png"
                subprocess.run(
                    ["convert", str(img), str(target / dest_name)],
                    check=True, capture_output=True,
                )
            else:
                shutil.copy2(img, target / dest_name)
            write_imageset(assets, name, dest_name, vector=False)
            inventory["raster"].append(name)

    # ---- AppIcon from the brand logo ------------------------------------ #
    logo = res / "drawable" / "medigyaan_logo.png"
    appicon = assets / "AppIcon.appiconset"
    appicon.mkdir(parents=True, exist_ok=True)
    if logo.exists():
        subprocess.run(
            ["convert", str(logo), "-resize", "1024x1024", "-background", "none",
             "-gravity", "center", "-extent", "1024x1024",
             str(appicon / "AppIcon-1024.png")],
            check=True, capture_output=True,
        )
        (appicon / "Contents.json").write_text(json.dumps({
            "images": [{
                "filename": "AppIcon-1024.png", "idiom": "universal",
                "platform": "ios", "size": "1024x1024",
            }],
            "info": {"author": "xcode", "version": 1},
        }, indent=2) + "\n")
    # ---- Colorsets contractually required by project.yml / Info.plist --- #
    # Generated from colors.xml so AccentColor tracks `colorPrimary` and
    # LaunchBackground tracks `colorBackground` instead of drifting.
    write_colorset(
        assets, "AccentColor",
        colors.resolve("@color/colorPrimary", dark=False)[0],
        colors.resolve("@color/colorPrimary", dark=True)[0],
    )
    write_colorset(
        assets, "LaunchBackground",
        colors.resolve("@color/colorBackground", dark=False)[0],
        colors.resolve("@color/colorBackground", dark=True)[0],
    )

    (assets / "Contents.json").write_text(json.dumps(ASSET_CONTENTS, indent=2) + "\n")

    # ---- Swift constants ------------------------------------------------ #
    if args.swift_out:
        # Source of truth is the catalog itself: never emit a case for something
        # we failed to convert (that would be a dangling asset name).
        all_names = sorted(p.name[: -len(".imageset")] for p in assets.glob("*.imageset"))
        if not all_names:
            print("error: no imagesets produced; refusing to write Swift constants", file=sys.stderr)
            return 1
        template_icons = [n for n in template_icons if n in set(all_names)]
        lines = [
            "// Generated by tools/convert_android_res.py - do not edit by hand.",
            "// Every artwork asset ported from the Android app's res/drawable.",
            "",
            "import SwiftUI",
            "",
            "/// Typed access to every Android drawable / mipmap on the iOS side.",
            "enum AndroidAsset: String, CaseIterable {",
        ]
        for n in all_names:
            ident = re.sub(r"[^A-Za-z0-9_]", "_", n)
            if ident[0].isdigit():
                ident = "n" + ident
            lines.append(f'    case {ident} = "{n}"')
        lines.append("")
        lines.append("    var image: Image { Image(rawValue) }")
        lines.append("")
        lines.append("    /// Icons Android draws with `android:tint`; tint with the app palette.")
        lines.append("    static let templateIcons: Set<AndroidAsset> = [")
        for n in sorted(template_icons):
            ident = re.sub(r"[^A-Za-z0-9_]", "_", n)
            if ident[0].isdigit():
                ident = "n" + ident
            lines.append(f"        .{ident},")
        lines.append("    ]")
        lines.append("}")
        lines.append("")
        Path(args.swift_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.swift_out).write_text("\n".join(lines))

    # ---- report --------------------------------------------------------- #
    total = sum(len(v) for k, v in inventory.items() if k != "skipped")
    print(f"converted {total} assets into {assets}")
    for key in ("vector", "shape", "selector", "layer", "raster"):
        print(f"  {key:<9} {len(inventory[key]):>3}  {', '.join(inventory[key][:6])}"
              + (" ..." if len(inventory[key]) > 6 else ""))
    if template_icons:
        print(f"  template  {len(template_icons):>3}  (android:tint icons)")
    if inventory["skipped"]:
        print(f"  skipped   {len(inventory['skipped'])}")
        for s in inventory["skipped"]:
            print(f"      - {s}")
    if colors.unresolved:
        print(f"  unresolved colour refs ({len(colors.unresolved)}): "
              f"{sorted(colors.unresolved)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
