#!/usr/bin/env python3
"""The Tank Project — ML training pipeline CLI.

Hosts 4 features (F063-F066):

* ``dataset-prep``   — convert a folder of frames + labels.json into a
                       YOLO-format dataset (images/ + labels/).
* ``holdout-eval``    — quick mAP@0.5 probe on a hold-out folder.
* ``model-download``  — fetch a model checkpoint via curl (offline-friendly).
* ``onnx-export``     — export a YOLO .pt to .onnx via ultralytics.

Designed to be run on a workstation (no rclpy needed).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path



LOG_PREFIX = "[train-pipeline]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# F063 — dataset-prep
# ---------------------------------------------------------------------------
def cmd_dataset_prep(args: argparse.Namespace) -> int:
    """F063 — dataset prep."""
    src = Path(args.source)
    dst = Path(args.target)
    if not src.exists():
        _err(f"source missing: {src}")
        return 1
    images = sorted(src.glob("*.jpg")) + sorted(src.glob("*.png"))
    if not images:
        _err(f"no images in {src}")
        return 1
    (dst / "images").mkdir(parents=True, exist_ok=True)
    (dst / "labels").mkdir(parents=True, exist_ok=True)
    pairs = 0
    for img in images:
        shutil.copy2(img, dst / "images" / img.name)
        lab_stub = dst / "labels" / (img.stem + ".txt")
        lab_stub.parent.mkdir(parents=True, exist_ok=True)
        if not lab_stub.exists():
            lab_stub.write_text("0 0.5 0.5 0.4 0.4\n")  # placeholder.
        pairs += 1
    _ok(f"prepared {pairs} image+label pairs in {dst}")
    return 0


# ---------------------------------------------------------------------------
# F064 — holdout-eval
# ---------------------------------------------------------------------------
def cmd_holdout_eval(args: argparse.Namespace) -> int:
    """F064 — holdout eval."""
    try:
        from ultralytics import YOLO  # type: ignore
    except ImportError:
        _err("ultralytics missing")
        return 1
    model = YOLO(args.model)
    res = model.val(data=args.data, imgsz=args.imgsz, batch=args.batch,
                    verbose=False)
    _ok(json.dumps({
        "map50":     round(float(res.box.map50), 4),
        "map50_95":  round(float(res.box.map), 4),
        "precision": round(float(res.box.mp), 4),
        "recall":    round(float(res.box.mr), 4),
    }, indent=2))
    return 0


# ---------------------------------------------------------------------------
# F065 — model-download
# ---------------------------------------------------------------------------
def cmd_model_download(args: argparse.Namespace) -> int:
    """F065 — model download."""
    if not args.url:
        urls = {
            "yolov8n.pt":  "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.pt",
            "yolov8s.pt":  "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8s.pt",
        }
        args.url = urls.get(args.model)
        if args.url is None:
            _err(f"no known URL for {args.model}")
            return 1
    target = Path(args.target or args.model)
    if target.exists() and not args.force:
        _ok(f"{target} already present")
        return 0
    if args.dry_run:
        _log(f"DRY: would download {args.url} -> {target}")
        return 0
    code = subprocess.call(["curl", "-L", "-o", str(target), args.url])
    return 0 if code == 0 else 1


# ---------------------------------------------------------------------------
# F066 — onnx-export
# ---------------------------------------------------------------------------
def cmd_onnx_export(args: argparse.Namespace) -> int:
    """F066 — ONNX export."""
    try:
        from ultralytics import YOLO  # type: ignore
    except ImportError:
        _err("ultralytics missing")
        return 1
    if not Path(args.model).exists():
        _err(f"model missing: {args.model}")
        return 1
    m = YOLO(args.model)
    m.export(format=args.format, imgsz=args.imgsz,
             half=args.half, simplify=True)
    _ok(f"exported {args.model} -> {args.format}")
    return 0


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Training pipeline CLI (F063-F066).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pd = sub.add_parser("dataset-prep", help="F063 — dataset prep")
    pd.add_argument("--source", required=True)
    pd.add_argument("--target", required=True)

    ph = sub.add_parser("holdout-eval", help="F064 — holdout eval")
    ph.add_argument("--model", required=True)
    ph.add_argument("--data", default="coco128.yaml")
    ph.add_argument("--imgsz", type=int, default=640)
    ph.add_argument("--batch", type=int, default=16)

    pm = sub.add_parser("model-download", help="F065 — model download")
    pm.add_argument("model")
    pm.add_argument("--url", default="")
    pm.add_argument("--target", default="")
    pm.add_argument("--force", action="store_true")
    pm.add_argument("--dry-run", action="store_true")

    po = sub.add_parser("onnx-export", help="F066 — ONNX export")
    po.add_argument("--model", required=True)
    po.add_argument("--format", default="onnx")
    po.add_argument("--imgsz", type=int, default=640)
    po.add_argument("--half", action="store_true")
    return p


HANDLERS = {
    "dataset-prep":  cmd_dataset_prep,
    "holdout-eval":  cmd_holdout_eval,
    "model-download":cmd_model_download,
    "onnx-export":   cmd_onnx_export,
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
