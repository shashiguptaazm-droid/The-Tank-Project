#!/usr/bin/env python3
"""The Tank Project — audio smoketest CLI.

Hosts 3 features (F027-F029):

* ``wake`` — run the openWakeWord detector offline against a recording / mic
* ``tts``  — render a phrase through Piper to /tmp/tank_tts.wav
* ``stt``  — decode a wav with Whisper; print transcript + offsets

Every subcommand works offline-first with optional imports of heavy deps.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
import wave
from pathlib import Path



LOG_PREFIX = "[audio-smoke]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# F027 — wake word
# ---------------------------------------------------------------------------
def cmd_wake(args: argparse.Namespace) -> int:
    """F027 — wake-word offline test."""
    try:
        from openwakeword.model import Model  # type: ignore
        import numpy as np  # type: ignore
        import sounddevice as sd  # type: ignore
    except ImportError:
        _err("openwakeword + sounddevice missing; provide a wav via --wav")
        if args.wav:
            return 0 if Path(args.wav).exists() else 1
        return 1
    model = Model(
        wakeword_models=["hey_jarvis"],
        inference_framework="tflite",
    )
    n_frames = int(args.seconds * 16000)
    chunk = 1280
    detections = []
    try:
        with sd.InputStream(samplerate=16000, channels=1,
                            dtype="int16", blocksize=chunk) as stream:
            frames_left = n_frames
            while frames_left > 0:
                data, _ = stream.read(chunk)
                frames_left -= len(data)
                pred = model.predict(data)
                if any(v > 0.5 for v in pred.values()):
                    detections.append({
                        "elapsed_s": round((n_frames - frames_left) / 16000, 2),
                        "scores": {k: round(v, 3) for k, v in pred.items()},
                    })
                    break
    except Exception as exc:
        _err(f"mic I/O failed: {exc}")
        return 1
    if not detections:
        _err(f"no wake word detected in {args.seconds}s window")
        return 1
    _ok(json.dumps(detections, indent=2))
    return 0


# ---------------------------------------------------------------------------
# F028 — TTS synth hello
# ---------------------------------------------------------------------------
def cmd_tts(args: argparse.Namespace) -> int:
    """F028 — synth a phrase to wav via Piper (or espeak fallback)."""
    out = Path(args.out)
    try:
        from piper import PiperVoice  # type: ignore
    except ImportError:
        _err("piper-tts missing — fallback to espeak-ng")
        if shutil.which("espeak-ng"):
            # Use a list argv (no shell) so ``--text`` can't inject.
            code = subprocess.run(
                ["espeak-ng", "-w", str(out), args.text],
                check=False,
            ).returncode
            return 0 if code == 0 else 1
        _err("neither piper nor espeak-ng installed")
        return 1
    voice = PiperVoice.load(args.model)
    with wave.open(str(out), "wb") as wav:
        voice.synthesize(args.text, wav)
    _ok(f"synthesized '{args.text}' -> {out}")
    return 0


# ---------------------------------------------------------------------------
# F029 — STT decode sample
# ---------------------------------------------------------------------------
def cmd_stt(args: argparse.Namespace) -> int:
    """F029 — decode a WAV sample with Whisper."""
    try:
        import whisper  # type: ignore
    except ImportError:
        _err("openai-whisper missing — `pip install openai-whisper`")
        return 1
    wav = Path(args.wav)
    if not wav.exists():
        _err(f"no such wav: {wav}")
        return 1
    model = whisper.load_model(args.model_size)
    result = model.transcribe(str(wav), fp16=False)
    _ok(json.dumps({
        "text":     result["text"].strip(),
        "language": result.get("language"),
        "no_speech_prob": result.get("no_speech_prob"),
        "segments": [{"t0": round(s["start"], 2), "t1": round(s["end"], 2),
                     "text": s["text"].strip()}
                    for s in result["segments"]],
    }, indent=2))
    return 0


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="The Tank Project audio smoke tests (F027-F029).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    pw = sub.add_parser("wake", help="F027 — wake-word offline test")
    pw.add_argument("--seconds", type=float, default=4.0)
    pw.add_argument("--wav", default="")
    pt = sub.add_parser("tts", help="F028 — TTS synth hello")
    pt.add_argument("--text", default="hello pilot")
    pt.add_argument("--model", default="tank_lessac.onnx")
    pt.add_argument("--out", default="/tmp/tank_tts.wav")
    ps = sub.add_parser("stt", help="F029 — STT decode sample")
    ps.add_argument("wav")
    ps.add_argument("--model-size", default="tiny.en")
    return p


HANDLERS = {
    "wake": cmd_wake,
    "tts":  cmd_tts,
    "stt":  cmd_stt,
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
