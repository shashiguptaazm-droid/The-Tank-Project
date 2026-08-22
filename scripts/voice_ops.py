#!/usr/bin/env python3
"""The Tank Project — voice + multimodal ops CLI.

Hosts 3 features (F075-F077):

* ``voice-rotate``    — list available Piper voices, set the LLM_TTS_VOICE
* ``sentiment-warmup``— feed a labelled corpus through a tiny sentiment
                        scorer and dump evaluation metrics
* ``emotion-wheel``   — render an ASCII Plutchik-style emotion wheel

Designed to be run on a workstation.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path



LOG_PREFIX = "[voice-ops]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# F075 — voice-rotate
# ---------------------------------------------------------------------------
def cmd_voice_rotate(args: argparse.Namespace) -> int:
    """F075 — voice rotate."""
    voices_dir = Path(args.voices_dir or "tank_ws/voices")
    if not voices_dir.is_dir():
        _err(f"voices dir missing: {voices_dir}")
        return 1
    voices = sorted(p.stem for p in voices_dir.glob("*.onnx"))
    if not voices:
        _err(f"no .onnx in {voices_dir}")
        return 1
    _ok(json.dumps({"installed": voices, "active": args.voice}, indent=2))
    env_path = Path(args.env_file or "tank_ws/data/tank_env.json")
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env = {}
    if env_path.exists():
        env = json.loads(env_path.read_text())
    env["LLM_TTS_VOICE"] = args.voice
    env_path.write_text(json.dumps(env, indent=2))
    _ok(f"set LLM_TTS_VOICE={args.voice} -> {env_path}")
    return 0


# ---------------------------------------------------------------------------
# F076 — sentiment-warmup
# ---------------------------------------------------------------------------
def cmd_sentiment_warmup(args: argparse.Namespace) -> int:
    """F076 — sentiment warmup."""
    try:
        from textblob import TextBlob  # type: ignore
    except ImportError:
        _err("TextBlob missing — install with `pip install textblob`")
        return 1
    corpus = Path(args.corpus)
    if not corpus.exists():
        _err(f"corpus missing: {corpus}")
        return 1
    scores = []
    for line in corpus.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        b = TextBlob(line)
        scores.append({"text": line[:120],
                       "polarity": round(b.sentiment.polarity, 3),
                       "subjectivity": round(b.sentiment.subjectivity, 3)})
    pos = sum(1 for s in scores if s["polarity"] > 0.2)
    neu = sum(1 for s in scores if -0.2 <= s["polarity"] <= 0.2)
    neg = sum(1 for s in scores if s["polarity"] < -0.2)
    _ok(json.dumps({
        "n": len(scores),
        "pos": pos, "neu": neu, "neg": neg,
        "avg_polarity":   round(sum(s["polarity"] for s in scores) / max(len(scores), 1), 3),
    }, indent=2))
    return 0


# ---------------------------------------------------------------------------
# F077 — emotion-wheel
# ---------------------------------------------------------------------------
def cmd_emotion_wheel(args: argparse.Namespace) -> int:
    """F077 — emotion wheel (ASCII)."""
    emotions = [
        ("joy",     0.9,  0.7),
        ("trust",   0.6,  0.8),
        ("fear",   -0.7,  0.6),
        ("surprise", 0.3, 0.9),
        ("sadness", -0.6, -0.4),
        ("disgust", -0.8,  0.2),
        ("anger",  -0.7,  0.8),
        ("anticipation", 0.4, 0.4),
    ]
    W, H = 60, 18
    grid = [[" "] * W for _ in range(H)]
    cx, cy = W // 2, H // 2
    for label, vx, vy in emotions:
        gx = int(cx + vx * (W // 2 - 2))
        gy = int(cy - vy * (H // 2 - 2))
        if 0 <= gx < W and 0 <= gy < H:
            grid[gy][gx] = "*"
            if len(label) <= 8 and 0 <= gx - len(label) // 2 < W - len(label):
                for i, ch in enumerate(label):
                    grid[gy][gx - len(label) // 2 + i] = ch
    print("+" + "-" * W + "+")
    for row in grid:
        print("|" + "".join(row) + "|")
    print("+" + "-" * W + "+")
    _ok("plutchik-ish wheel rendered")
    return 0


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Voice / multimodal ops CLI (F075-F077).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    pv = sub.add_parser("voice-rotate", help="F075 — voice rotate")
    pv.add_argument("--voices-dir", default="")
    pv.add_argument("--voice", default="tank_amy")
    pv.add_argument("--env-file", default="")
    ps = sub.add_parser("sentiment-warmup", help="F076 — sentiment warmup")
    ps.add_argument("--corpus", default="tank_ws/data/sentiment_corpus.txt")
    pw = sub.add_parser("emotion-wheel", help="F077 — emotion wheel")
    return p


HANDLERS = {
    "voice-rotate":     cmd_voice_rotate,
    "sentiment-warmup": cmd_sentiment_warmup,
    "emotion-wheel":    cmd_emotion_wheel,
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
