"""test_signals — text / face / audio heuristics."""
from __future__ import annotations

import unittest

from tank_emotions import score_text, dominant, score_face, score_audio
from tank_emotions.signals.text import _is_negated


class TestTextSignals(unittest.TestCase):

    def test_dominant_joy_from_text(self):
        self.assertEqual(dominant("I'm ecstatic and thrilled!"),
                         "joy")

    def test_dominant_fear_from_text(self):
        self.assertEqual(dominant("I'm terrified and anxious."),
                         "fear")

    def test_negation_drops_score(self):
        s1 = score_text("I am joyful")
        s2 = score_text("I am not joyful")
        self.assertGreater(sum(s1.values()), sum(s2.values()))

    def test_dominant_returns_neutral_when_empty(self):
        self.assertEqual(dominant(""), "neutral")
        self.assertEqual(dominant(None or ""), "neutral")


class TestFaceSignals(unittest.TestCase):

    def test_face_joy_via_aus(self):
        # AU6 + AU12 alone is joy baseline
        scores = score_face({"AU6": 0.8, "AU12": 0.8})
        self.assertGreater(scores.get("joy", 0.0), 0.0)

    def test_empty_face_does_not_crash(self):
        scores = score_face({})
        self.assertEqual(scores, {})


class TestAudioSignals(unittest.TestCase):

    def test_audio_anger_via_loudness(self):
        scores = score_audio({"loudness_db": -5.0, "rate_wpm": 160,
                              "jitter": 0.4})
        self.assertGreater(scores.get("anger", 0.0), 0.0)

    def test_audio_sadness_via_low_energy(self):
        scores = score_audio({"pitch_hz": 100, "loudness_db": -55,
                              "rate_wpm": 90})
        self.assertGreater(scores.get("sadness", 0.0), 0.0)


class TestTextHelpers(unittest.TestCase):

    def test_negation_detected_in_window(self):
        self.assertTrue(_is_negated("I am not joyful", (9, 15)))
        self.assertFalse(_is_negated("I am joyful", (4, 10)))


if __name__ == "__main__":
    unittest.main()
