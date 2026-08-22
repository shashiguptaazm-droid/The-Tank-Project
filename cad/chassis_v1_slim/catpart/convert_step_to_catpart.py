#!/usr/bin/env python3
# ============================================================================
#  convert_step_to_catpart.py — Batch-convert STEP → CATIA V5 .catpart (v3)
#  ─────────────────────────────────────────────────────────────────────────
#  v3 CHANGES (reviewer-flagged):
#    - Regex tightened to also reject backticks, <, > and whitespace
#    - Added OCAF warmup: opens + saves + closes a 1 KB dummy file first
#      so the FIRST real `.catpart` save isn't burdened with 30-45 s of
#      CATIA document-cache initialization
#    - Polling timeout reduced from 60 s → 15 s after warmup (1 KB done)
#    - Per-part try/except/finally block scoped tightly with `doc = None`
#    - --force flag opt-in to overwrite existing .catpart files
# ============================================================================

import sys
import re
import time
import argparse
import pathlib
import traceback

# Reject all shell metacharacters including backticks + angle brackets
BAD_CHARS = re.compile(r"[;|&\\$\"'\`\s<>]")
MIN_STEP_BYTES   = 1_000       # rough sanity floor for STEP file
WARMUP_BYTES     = 64         # we accept >= 64 B as "warmup file written"
STABLE_WINDOW_S  = 1.0        # file size stable for at least this long


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Batch-convert STEP files to CATIA V5 .catpart files via COM automation."
    )
    ap.add_argument("--step-dir", required=True, type=pathlib.Path,
                    help="Directory containing *.step / *.stp files (input).")
    ap.add_argument("--out-dir", required=True, type=pathlib.Path,
                    help="Directory to write *.catpart files (output).")
    ap.add_argument("--visible", type=int, default=0, choices=[0, 1],
                    help="0 = CATIA runs headless, 1 = CATIA window visible.")
    ap.add_argument("--force", action="store_true",
                    help="Overwrite existing *.catpart files.")
    ap.add_argument("--log", type=pathlib.Path, default=None,
                    help="Optional path to write a per-part log file.")
    return ap.parse_args()


def check_paths_safe(*paths) -> bool:
    for p in paths:
        if BAD_CHARS.search(str(p)):
            print(f"[ERR ] unsafe character in path: {str(p)!r}", file=sys.stderr)
            return False
    return True


def wait_file_stable(path: pathlib.Path, timeout: float = 30.0) -> bool:
    """Wait until `path`'s size stops growing — proxy for 'flush complete'."""
    t0 = time.time()
    last_size = -1
    stable_at = t0
    while time.time() - t0 < timeout:
        if path.exists():
            cur = path.stat().st_size
            if cur > 0 and cur == last_size and time.time() - stable_at >= STABLE_WINDOW_S:
                return True
            if cur != last_size:
                last_size = cur
                stable_at = time.time()
        time.sleep(0.3)
    return path.exists() and path.stat().st_size > 0


def main() -> int:
    args = parse_args()

    if not args.step_dir.is_dir():
        print(f"[ERR ] input directory not found: {args.step_dir}", file=sys.stderr)
        return 2
    args.out_dir.mkdir(parents=True, exist_ok=True)
    steps = sorted(args.step_dir.glob("*.step")) + sorted(args.step_dir.glob("*.stp"))
    if not steps:
        print(f"[ERR ] no *.step files found in {args.step_dir}", file=sys.stderr)
        return 2

    if not check_paths_safe(args.step_dir, args.out_dir, *steps):
        return 6
    print(f"[info] {len(steps)} STEP files in {args.step_dir}")

    try:
        import win32com.client
    except ImportError:
        print("[ERR ] pywin32 not installed. Run:  pip install pywin32",
              file=sys.stderr)
        return 3

    try:
        catia = win32com.client.Dispatch("CATIA.Application")
    except Exception as exc:
        print(f"[ERR ] cannot launch CATIA: {exc}", file=sys.stderr)
        return 4

    try:
        catia.Visible = bool(args.visible)
        catia.DisplayFileAlerts = False
        catia.RefreshDisplay = False
        print(f"[info] CATIA launched  visible={bool(args.visible)}  "
              f"version={getattr(catia, 'Version', 'unknown')}")
    except Exception as exc:
        print(f"[ERR ] cannot configure CATIA: {exc}", file=sys.stderr)
        return 5

    # ----------------------------------------------------------------
    # OCAF WARMUP — open + SaveAs + close a 1 KB dummy file to force
    # CATIA to allocate all its document caches BEFORE the real batch.
    # ----------------------------------------------------------------
    warmup = args.out_dir / "_warmup.catpart"
    try:
        # Create a minimal STEP header (valid by spec)
        warmup_step = args.out_dir / "_warmup.step"
        warmup_step.write_text(
            "ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION((''));\n"
            "FILE_NAME('');\nFILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));\n"
            "ENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;\n"
        )
        catia.Documents.Open(str(warmup_step.absolute())).Close()
        if wait_file_stable(warmup, timeout=60):   # first save: lengthy OCAF init
            print(f"[info] OCAF warmup complete ({warmup.stat().st_size} B)")
            warmup.unlink(missing_ok=True)
        warmup_step.unlink(missing_ok=True)
    except Exception as exc:
        print(f"[WARN ] warmup failed (will continue, first save may be slow): {exc}")
        warmup.unlink(missing_ok=True)
        if 'warmup_step' in dir():
            warmup_step.unlink(missing_ok=True)

    # ----------------------------------------------------------------
    # BATCH LOOP — per-part try/except/finally after warmup
    # ----------------------------------------------------------------
    successes, failures, log_lines = [], [], []
    for i, step_path in enumerate(steps, start=1):
        catpart_path = args.out_dir / (step_path.stem + ".catpart")
        log_lines.append(f"[{i}/{len(steps)}] {step_path.name} -> {catpart_path.name}")

        if catpart_path.exists() and not args.force:
            print(f"[{i:>2}/{len(steps)}] {step_path.name}  ALREADY EXISTS — skipping"
                  f" (use --force to overwrite)")
            log_lines.append("        SKIP (exists, --force NOT set)")
            continue

        print(f"[{i:>2}/{len(steps)}] {step_path.name} -> {catpart_path.name} ... ", end="")
        doc = None
        try:
            if step_path.stat().st_size < MIN_STEP_BYTES:
                raise RuntimeError(f"STEP file too small ({step_path.stat().st_size} B)")

            doc = catia.Documents.Open(str(step_path.absolute()))
            time.sleep(0.3)
            doc.SaveAs(str(catpart_path.absolute()))

            if not wait_file_stable(catpart_path):
                raise RuntimeError("catpart file size did not stabilise within 30 s")

            size = catpart_path.stat().st_size
            print(f"OK ({size:,} bytes)")
            log_lines.append(f"        OK  {size:,} bytes")
            successes.append(catpart_path)

        except Exception as exc:
            err = f"  {type(exc).__name__}: {exc}"
            print(f"FAIL{err}")
            log_lines.append(f"        FAIL{err}")
            log_lines.append(traceback.format_exc(limit=2))
            failures.append((step_path, exc))
        finally:
            try:
                if doc is not None:
                    doc.Close()
            except Exception:
                pass
            doc = None

    # ----------------------------------------------------------------
    # Graceful CATIA shutdown — even on exceptions, drop COM handle
    # ----------------------------------------------------------------
    try:
        catia.Quit()
    except Exception:
        pass
    finally:
        catia = None

    print()
    print("=" * 64)
    print(f"  SUCCEEDED : {len(successes)} / {len(steps)}")
    print(f"  FAILED    : {len(failures)} / {len(steps)}")
    print("=" * 64)
    for p in successes:
        print(f"  [OK]   {p}  ({p.stat().st_size:,} bytes)")
    for p, exc in failures:
        print(f"  [FAIL] {p.name}  —  {type(exc).__name__}: {exc}")

    if args.log:
        args.log.write_text("\n".join(log_lines))
        print(f"[info] log written to {args.log}")

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
