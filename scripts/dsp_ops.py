#!/usr/bin/env python3
"""The Tank Project — DSP ops CLI.

Hosts 3 features (F134-F136):

* ``waveform``     — load a .wav and dump an ASCII waveform + RMS
* ``vad-detect``   — voice-activity detection on a .wav (energy-based)
* ``eq-profile``   — emit a JSON EQ profile for the audio chain
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import wave
from pathlib import Path



LOG_PREFIX = "[dsp-ops]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _read_wav(path: Path) -> tuple:
    try:
        with wave.open(str(path), "rb") as fh:
            n_channels = fh.getnchannels()
            sampwidth  = fh.getsampwidth()
            framerate  = fh.getframerate()
            n_frames   = fh.getnframes()
            raw = fh.readframes(n_frames)
    except (wave.Error, OSError) as exc:
        return (None,) * 4 + (str(exc),)
    # 16-bit assumed; degrade gracefully
    if sampwidth == 2:
        fmt = "<h"
    elif sampwidth == 1:
        fmt = "<B"
    elif sampwidth == 4:
        fmt = "<i"
    else:
        return (None,) * 4 + (f"unsupported sampwidth {sampwidth}",)
    import struct
    samples = list(struct.unpack(f"{fmt}{n_channels * n_frames}", raw))
    return n_channels, sampwidth, framerate, n_frames, samples


# ---------------------------------------------------------------------------
# F134 — waveform
# ---------------------------------------------------------------------------
def cmd_waveform(args: argparse.Namespace) -> int:
    """F134 — waveform + RMS."""
    path = Path(args.wav)
    n_ch, sw, fr, n_frames, samples = _read_wav(path)
    if samples is None:
        _err(f"could not read {path}: {n_ch}")
        return 1
    if not samples:
        _err(f"empty file: {path}")
        return 1
    if sw == 2:
        scale = 32768.0
    elif sw == 1:
        scale = 128.0
    else:
        scale = 2147483648.0
    norm = [s / scale for s in samples]
    rms = math.sqrt(sum(s * s for s in norm) / max(len(norm), 1))
    peak = max(abs(s) for s in norm)
    bins = args.bins
    width = min(len(norm), 24)
    bar_width = (len(norm) // bins) if bins else len(norm)
    rows = []
    for i in range(0, len(norm), max(bar_width, 1)):
        chunk = norm[i:i + max(bar_width, 1)]
        if not chunk:
            continue
        avg = sum(chunk) / len(chunk)
        idx = int(round((avg + 1) / 2 * (width - 1)))
        rows.append([" "] * width)
        h = " "
        sym = "*" if avg > 0 else "-"
        rows[-1][idx] = sym
    ascii_rows = "".join("".join(r) for r in rows[:80])
    _ok(json.dumps({
        "channels": n_ch,
        "rate_hz":  fr,
        "frames":   n_frames,
        "rms":      round(rms, 3),
        "peak":     round(peak, 3),
        "ascii":    ascii_rows[:240],
    }, indent=2))
    return 0


# ---------------------------------------------------------------------------
# F135 — vad-detect
# ---------------------------------------------------------------------------
def cmd_vad_detect(args: argparse.Namespace) -> int:
    """F135 — voice activity detection."""
    path = Path(args.wav)
    n_ch, sw, fr, n_frames, samples = _read_wav(path)
    if samples is None:
        _err(f"could not read {path}: {n_ch}")
        return 1
    if sw == 2:
        scale = 32768.0
    elif sw == 1:
        scale = 128.0
    else:
        scale = 2147483648.0
    frame_size = int(fr * 0.02)  # 20 ms windows
    voiced = []
    for i in range(0, len(samples), frame_size):
        chunk = samples[i:i + frame_size]
        if not chunk:
            continue
        energy = sum((s / scale) ** 2 for s in chunk) / len(chunk)
        if energy > args.threshold:
            voiced.append((i / fr, (i + len(chunk)) / fr))
    _ok(json.dumps({
        "rate_hz":   fr,
        "threshold": args.threshold,
        "n_segments": len(voiced),
        "first_segment": voiced[0] if voiced else None,
    }, indent=2))
    return 0


# ---------------------------------------------------------------------------
# F136 — eq-profile
# ---------------------------------------------------------------------------
def cmd_eq_profile(args: argparse.Namespace) -> int:
    """F136 — emit EQ profile JSON."""
    if args.bands < 1:
        _err("--bands must be >= 1")
        return 1
    profile = {"name": args.name,
               "bands": [{"freq_hz": int(200 * (2 ** i)),
                          "gain_db":  0.0} for i in range(args.bands)]}
    out = Path(args.out or "tank_ws/data/eq_profile.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(profile, indent=2))
    _ok(f"wrote {out}")
    return 0


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="DSP ops CLI (F134-F136).")
    sub = p.add_subparsers(dest="cmd", required=True)
    pw = sub.add_parser("waveform", help="F134 — waveform")
    pw.add_argument("wav")
    pw.add_argument("--bins", type=int, default=80)
    pv = sub.add_parser("vad-detect", help="F135 — voice activity detection")
    pv.add_argument("wav")
    pv.add_argument("--threshold", type=float, default=0.005)
    pe = sub.add_parser("eq-profile", help="F136 — EQ profile")
    pe.add_argument("--name", default="speech_phone")
    pe.add_argument("--bands", type=int, default=5)
    pe.add_argument("--out", default="")
    return p


HANDLERS = {
    "waveform":   cmd_waveform,
    "vad-detect": cmd_vad_detect,
    "eq-profile": cmd_eq_profile,
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
