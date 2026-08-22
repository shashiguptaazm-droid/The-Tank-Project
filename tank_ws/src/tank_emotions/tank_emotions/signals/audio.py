"""tank_emotions.signals.audio — pitch/loudness/breath heuristics.

Input is a dict::

    {
        "pitch_hz":       float,   # fundamental
        "loudness_db":    float,
        "speech_rate_wpm":float,
        "jitter":         float,   # 0..1
        "breath_count":   int,
    }

Per-emotion scores in ``[0, 1]``.
"""
from __future__ import annotations

from typing import Dict


def score_audio(features: Dict[str, float]) -> Dict[str, float]:
    feat = features or {}
    pitch      = feat.get("pitch_hz", 0.0)
    loudness   = feat.get("loudness_db", -40.0)
    rate       = feat.get("speech_rate_wpm", 120.0)
    breath     = float(feat.get("breath_count", 5))
    jitter     = feat.get("jitter", 0.0)

    out: Dict[str, float] = {}

    # Joy / anticipation tend to be high pitch + loud + bright
    out["joy"] = min(1.0,
        max(0.0, (pitch - 150) / 200) * 0.5
      + max(0.0, (loudness - (-30)) / 30) * 0.5)
    out["anticipation"] = out["joy"] * 0.85

    # Anger — loud + fast + jitter
    out["anger"] = min(1.0,
          max(0.0, (loudness - (-20)) / 20) * 0.5
        + max(0.0, (rate - 130) / 80) * 0.3
        + max(0.0, jitter) * 0.6)

    # Fear / surprise — high pitch, fast, breath
    out["fear"] = min(1.0,
          max(0.0, (pitch - 180) / 160) * 0.4
        + max(0.0, (rate - 130) / 80) * 0.3
        + max(0.0, breath - 8) / 8 * 0.3)

    out["surprise"] = min(1.0,
          max(0.0, (pitch - 180) / 160) * 0.5
        + max(0.0, (rate - 140) / 80) * 0.3
        + max(0.0, (breath - 5) / 8) * 0.2)

    # Sadness / melancholy — low energy, low pitch, slow
    out["sadness"] = min(1.0,
          max(0.0, (-loudness - 30) / 30) * 0.4
        + max(0.0, (110 - pitch) / 80) * 0.4
        + max(0.0, (110 - rate) / 60) * 0.3)

    out["melancholy"] = out["sadness"] * 0.8
    out["relief"] = max(0.0, 0.6 - out["fear"])
    out["contentment"] = min(1.0, 0.6 * max(0.0, (-loudness + 30) / 30)
                            + max(0.0, (90 - rate) / 80) * 0.4)
    return {k: round(v, 3) for k, v in out.items() if v > 0.0}
