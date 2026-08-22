"""test_taxonomy — auto-discovery + canonical expected count."""
from __future__ import annotations

import unittest

from tank_emotions import discover, names, get, by_taxonomy, rough_category


PLUTCHIK_PRIMARY = {
    "joy", "trust", "fear", "surprise",
    "sadness", "disgust", "anger", "anticipation",
}


EKMAN_BASIC = {"fear", "surprise", "sadness", "disgust", "anger", "joy"}


SELF_CONSCIOUS = {"pride", "shame", "guilt", "embarrassment"}


KNOWN_COUNT = 24  # 8 plutchik + 5 self-conscious + 11 complex.


class TestTaxonomy(unittest.TestCase):

    def test_count_matches_expected(self):
        self.assertEqual(len(names()), KNOWN_COUNT,
                         f"expected {KNOWN_COUNT}, got {sorted(names())}")

    def test_plutchik_primary_complete(self):
        plutchik = {e.name for e in by_taxonomy("plutchik")}
        primary = {e.name
                   for e in by_taxonomy("plutchik")
                   if any(t.get("rank") == "primary" for t in e.taxonomy)}
        self.assertEqual(primary, PLUTCHIK_PRIMARY)

    def test_ekman_basic_present(self):
        names_set = {e.name for e in by_taxonomy("ekman")}
        # every ekman emotion must also exist
        for k in EKMAN_BASIC:
            self.assertIn(k, names_set)

    def test_self_conscious_subset(self):
        sc = {e.name for e in by_taxonomy("izard")}
        # must at least contain the self-conscious set
        for k in SELF_CONSCIOUS:
            self.assertIn(k, sc)

    def test_lookup_returns_emotion(self):
        emo = get("joy")
        self.assertEqual(emo.name, "joy")
        self.assertGreater(emo.valence, 0.0)

    def test_unknown_returns_safe_default(self):
        emo = get("this-emotion-does-not-exist")
        self.assertEqual(emo.name, "neutral")

    def test_categories_quadrant_basic(self):
        # joy ends up in positive_high_arousal quadrant
        joy = get("joy")
        self.assertEqual(rough_category(joy), "positive_high_arousal")
        # contentment ends up in positive_low_arousal
        contentment = get("contentment")
        self.assertEqual(rough_category(contentment),
                         "positive_low_arousal")
        # fear ends up in negative_high_arousal
        fear = get("fear")
        self.assertEqual(rough_category(fear),
                         "negative_high_arousal")


if __name__ == "__main__":
    unittest.main()
