#!/usr/bin/env python3
"""Standalone wake-word listener (no ROS2).

Reads from the default microphone via sounddevice, runs openWakeWord,
and prints wake events to stdout.  Useful for bench-testing the model
without bringing up the full ROS stack.

Usage::

    python3 scripts/listen_wake.py
    python3 scripts/listen_wake.py --rate 16000 --threshold 0.55
    python3 scripts/listen_wake.py --list-devices
    python3 scripts/listen_wake.py --file /path/to/test.wav
"""
from __future__ import annotations

import argparse
import sys
import time

import numpy as np


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Standalone wake-word listener")
    p.add_argument("--rate",    type=int,   default=16000)
    p.add_argument("--chunk",   type=int,   default=1280,
                   help="frames per inference window (1280 frames == 80 ms @ 16 kHz)")
    p.add_argument("--model",   type=str,   default="hey_jarvis")
    p.add_argument("--model-path", type=str, default="")
    p.add_argument("--threshold",  type=float, default=0.55)
    p.add_argument("--cooldown",   type=float, default=2.0)
    p.add_argument("--list-devices", action="store_true")
    p.add_argument("--file", type=str, default="",
                   help="if set, feed this wav file instead of the microphone")
    return p.parse_args()


def list_audio_devices() -> int:
    try:
        import sounddevice as sd
    except ImportError:
        print("sounddevice is not installed. pip install sounddevice", file=sys.stderr)
        return 1
    print(sd.query_devices())
    return 0


def build_engine(model: str, model_path: str):
    from openwakeword.model import Model
    if model_path:
        return Model(wakeword_models=[model_path])
    return Model(wakeword_models=[model])


def print_event(label: str, score: float) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {label:6s}  conf={score:5.2f}", flush=True)


def stream_mic(rate: int, chunk: int):
    try:
        import sounddevice as sd
    except ImportError:
        print("sounddevice is not installed. pip install sounddevice", file=sys.stderr)
        sys.exit(1)
    blocksize = chunk
    with sd.RawInputStream(
        samplerate=rate, blocksize=blocksize, dtype="int16", channels=1,
    ) as stream:
        print(f"listening on default mic @ {rate} Hz (chunk {chunk} frames)", flush=True)
        while True:
            data, _overflowed = stream.read(blocksize)
            yield np.frombuffer(data, dtype=np.int16)


def stream_file(path: str, rate: int, chunk: int):
    try:
        from scipy.io import wavfile
    except ImportError:
        print("scipy is required for --file; pip install scipy", file=sys.stderr)
        sys.exit(1)
    actual_rate, samples = wavfile.read(path)
    if samples.dtype != np.int16:
        samples = samples.astype(np.int16)
    if actual_rate != rate:
        print(
            f"warning: wav is {actual_rate} Hz but listener is {rate} Hz; "
            "openWakeWord will mis-classify",
            file=sys.stderr,
        )
    print(f"replaying {path} at {rate} Hz", flush=True)
    i = 0
    while i < len(samples):
        yield samples[i:i + chunk]
        i += chunk


def main() -> int:
    args = parse_args()
    if args.list_devices:
        return list_audio_devices()

    # Build engine + simple inline latch so this CLI has no ROS deps.
    try:
        engine = build_engine(args.model, args.model_path)
    except Exception as exc:
        print(f"failed to load openWakeWord: {exc}", file=sys.stderr)
        return 1

    cooldown_until = 0.0
    last_window_release_at = 0.0
    latched = False
    print(
        f"wake-word ready (model={args.model or args.model_path}, "
        f"threshold={args.threshold:.2f}, cooldown={args.cooldown}s)",
        flush=True,
    )

    src = stream_file(args.file, args.rate, args.chunk) if args.file \
        else stream_mic(args.rate, args.chunk)

    last_print = 0.0
    for audio in src:
        if audio.size == 0:
            continue
        scores = engine.predict(audio)
        if not scores:
            continue
        score = float(max(scores.values()) if isinstance(scores, dict)
                      else float(np.max(scores)))

        now = time.monotonic()
        if (not latched) and score >= args.threshold and now >= cooldown_until:
            latched = True
            last_window_release_at = now + args.cooldown + 1.0
            cooldown_until = last_window_release_at
            print_event("wake", score)
        elif latched and now > last_window_release_at:
            latched = False
        elif (now - last_print) > 1.0 and score > 0.10:
            # ambient chatter — useful for tuning the threshold
            print_event("chatter", score)
            last_print = now


if __name__ == "__main__":
    sys.exit(main())
