"""tank_emotions.signals — multi-modal cue detectors.

* :mod:`text`   — keyword / marker scan over free-form text.
* :mod:`face`   — Action Unit (Ekman FACS) heuristics.
* :mod:`audio`  — pitch / loudness / breath heuristics.
"""
from .text import score_text, dominant, annotated
from .face import score_face
from .audio import score_audio

__all__ = ["score_text", "score_face", "score_audio",
           "dominant", "annotated"]
