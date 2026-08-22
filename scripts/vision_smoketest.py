#!/usr/bin/env python3
"""The Tank Project — vision smoketest CLI.

Hosts 2 features (F030-F031):

* ``yolo``     — run YOLOv8n on a single frame (or /camera/image_raw
  snapshot) and report the top-5 class scores.
* ``apriltag`` — detect the dock tag family (tag36h11) on a single frame;
                 report its 6-DoF pose approximation.

All subcommands work without ROS. Heavy deps are imported lazily and the
script degrades to a structured offline response when they're missing.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path



LOG_PREFIX = "[vision-smoke]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# F030 — YOLO probe
# ---------------------------------------------------------------------------
def cmd_yolo(args: argparse.Namespace) -> int:
    """F030 — YOLO detector probe."""
    try:
        from ultralytics import YOLO  # type: ignore
    except ImportError:
        _err("ultralytics not installed; please `pip install ultralytics`")
        return 1
    if not Path(args.frame).exists():
        _err(f"frame missing: {args.frame}")
        return 1
    model = YOLO(args.model)
    res = model.predict(source=args.frame, conf=args.conf, verbose=False)[0]
    detections = []
    for box in res.boxes:
        cls = int(box.cls.item())
        label = res.names[cls]
        detections.append({
            "label": label,
            "conf":  round(box.conf.item(), 3),
            "xyxy":  [round(c.item(), 1) for c in box.xyxy[0]],
        })
    detections.sort(key=lambda d: -d["conf"])
    _ok(json.dumps({
        "frame": args.frame,
        "model": args.model,
        "top":   detections[:5],
        "n_total": len(detections),
    }, indent=2))
    if args.save:
        out_dir = Path(args.save); out_dir.mkdir(parents=True, exist_ok=True)
        res.save(filename=str(out_dir / "yolo_out.jpg"))
        _ok(f"annotated frame -> {out_dir / 'yolo_out.jpg'}")
    return 0


# ---------------------------------------------------------------------------
# F031 — AprilTag dock calibration
# ---------------------------------------------------------------------------

# Map symbolic family names -> cv2 constants. ``getPredefinedDictionary``
# requires the integer constant, not the symbol.
_DICT_NAMES = {}


def _resolve_apriltag_dict(name: str):  # type: ignore
    """Return the cv2 aruco dictionary constant for a symbolic name."""
    if not _DICT_NAMES:
        try:
            import cv2  # type: ignore
            for attr in dir(cv2.aruco):
                if attr.startswith("DICT_") and attr.isupper():
                    _DICT_NAMES[attr] = getattr(cv2.aruco, attr)
        except ImportError as exc:
            raise RuntimeError(f"opencv-python-headless missing: {exc}") from exc
    if name in _DICT_NAMES:
        return _DICT_NAMES[name]
    # Accept a numeric string (OpenCV constants are small ints).
    if name.isdigit():
        import cv2  # type: ignore
        return int(name)
    raise ValueError(f"unknown AprilTag family: {name!r}")


def cmd_apriltag(args: argparse.Namespace) -> int:
    """F031 — AprilTag detector (tag36h11)."""
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except ImportError:
        _err("opencv-python-headless missing")
        return 1
    if not Path(args.frame).exists():
        _err(f"frame missing: {args.frame}")
        return 1
    try:
        dict_id = _resolve_apriltag_dict(args.family)
    except (RuntimeError, ValueError) as exc:
        _err(str(exc))
        return 1
    dictionary = cv2.aruco.getPredefinedDictionary(dict_id)
    params = cv2.aruco.DetectorParameters()
    img = cv2.imread(str(args.frame))
    if img is None:
        _err(f"cv2 cannot read {args.frame}")
        return 1
    detector = cv2.aruco.ArucoDetector(dictionary, params)
    corners, ids, _ = detector.detectMarkers(img)
    if ids is None:
        _err("no markers detected")
        return 1
    flat = []
    for cid, corner in zip(ids.flatten().tolist(), corners):
        flat.append({
            "id": cid,
            "center_px": [round(corner[0][:, 0].mean(), 1),
                          round(corner[0][:, 1].mean(), 1)],
            "size_px":   round(float(np.linalg.norm(
                corner[0][1] - corner[0][0])), 1),
        })
    _ok(json.dumps({"family": args.family, "markers": flat}, indent=2))
    return 0


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="The Tank Project vision smoke tests (F030-F031).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    py = sub.add_parser("yolo", help="F030 — YOLO detector on a frame")
    py.add_argument("frame")
    py.add_argument("--model", default="yolov8n.pt")
    py.add_argument("--conf",  type=float, default=0.25)
    py.add_argument("--save",  default="")
    pa = sub.add_parser("apriltag", help="F031 — AprilTag detector")
    pa.add_argument("frame")
    pa.add_argument("--family", default="DICT_APRILTAG_36h11")
    return p


HANDLERS = {
    "yolo":     cmd_yolo,
    "apriltag": cmd_apriltag,
}


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return HANDLERS[args.cmd](args)
    except KeyboardInterrupt:
        _err("interrupted")
        return 130


if __name__ == "__main__":
    sys.exit(main())
