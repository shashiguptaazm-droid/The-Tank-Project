"""Hermetic tests for tank_speech.intent_router.

The new intent_router layer sits between Whisper (stt_node) and the
voice.* plugin dispatch. These tests cover:
* regex + word-boundary confidence scoring
* slot capture from regex named groups
* JSON-wire shape of an IntentRouter match
* graceful fallback to None on grammar miss

ROS is not required — the matcher is pure-Python and is what the ROS
node delegates to.
"""
from __future__ import annotations

import json
import unittest

from tank_speech.intent_router import (
    DEFAULT_GRAMMAR,
    GrammarCommand,
    IntentMatcher,
    score_match,
    _word_boundary,
)


class WordBoundaryTests(unittest.TestCase):

    def test_inside_word_is_rejected(self) -> None:
        # "playmusic" — start is in the middle of a word; should fail.
        self.assertFalse(_word_boundary("playmusic", 2, 4))

    def test_at_string_start_passes(self) -> None:
        self.assertTrue(_word_boundary("play music", 0, 4))

    def test_at_string_end_passes(self) -> None:
        self.assertTrue(_word_boundary("music", 0, 5))


class ScoreMatchTests(unittest.TestCase):

    def test_full_match_scores_high(self) -> None:
        conf, slots = score_match("play some lo-fi music", [
            r"\bplay(?:\s+some)?\s+(?P<query>[\w\s\-']+?)\s+music\b",
        ])
        self.assertGreaterEqual(conf, 0.55)
        self.assertIn("query", slots)
        self.assertIn("lo-fi", slots["query"])

    def test_no_match_returns_zero(self) -> None:
        conf, slots = score_match("jibberish nothing here", [
            r"\bplay\s+(?P<query>\w+)\s+music\b",
        ])
        self.assertEqual(conf, 0.0)
        self.assertEqual(slots, {})

    def test_fuzzy_match_returns_in_range(self) -> None:
        """score_match is bounded — for any input the conf is in [0, 1]."""
        for s in [
            "play lo fi muzic.",          # heavily fuzzy
            "play lo-fi music",          # clean hit
            "jibberish nothing here",    # no hit at all
            "",                          # empty
        ]:
            conf, _ = score_match(s, [
                r"\bplay(?:\s+some)?\s+(?P<query>[\w\s\-']+?)\s+music\b",
            ])
            self.assertIsInstance(conf, float)
            self.assertGreaterEqual(conf, 0.0)
            self.assertLessEqual(conf, 1.0)

    def test_word_boundary_bonus(self) -> None:
        pat = r"\bpause\b"
        a, _ = score_match("pause", [pat])
        b, _ = score_match("apausethat", [pat])
        # Inside-word coverage should still be >0 but conf is lower
        # because of the missing word-boundary bonus.
        self.assertGreater(a, 0.40)
        self.assertLess(b, 0.40)


class IntentMatcherTests(unittest.TestCase):

    def test_default_grammar_matches(self) -> None:
        m = IntentMatcher().match("play some lo-fi music")
        self.assertIsNotNone(m)
        assert m is not None
        self.assertEqual(m["cid"], "play_music")
        self.assertEqual(m["cmd"], "voice.play_music")
        self.assertIn("query", m["slots"])

    def test_play_youtube(self) -> None:
        m = IntentMatcher().match("play lo-fi on youtube")
        self.assertIsNotNone(m)
        assert m is not None
        self.assertEqual(m["cid"], "play_video")

    def test_power_sleep(self) -> None:
        m = IntentMatcher().match("go to sleep")
        self.assertIsNotNone(m)
        assert m is not None
        self.assertEqual(m["cid"], "power_sleep")
        self.assertEqual(m["cmd"], "voice.power")

    def test_unrecognised_falls_through(self) -> None:
        m = IntentMatcher().match("please tell me a joke about turtles")
        self.assertIsNone(m)

    def test_empty_text_falls_through(self) -> None:
        m = IntentMatcher().match("")
        self.assertIsNone(m)

    def test_custom_grammar(self) -> None:
        cmd = GrammarCommand(
            cid="my_test",
            target="voice.test",
            patterns=[r"\bping\b"],
        )
        m = IntentMatcher([cmd]).match("ping")
        self.assertIsNotNone(m)
        assert m is not None
        self.assertEqual(m["cid"], "my_test")

    def test_list_commands_dump(self) -> None:
        cmds = IntentMatcher().list_commands()
        ids = [c["cid"] for c in cmds]
        self.assertIn("play_music", ids)
        self.assertIn("whereami", ids)
        self.assertIn("detect_persons", ids)

    def test_match_payload_is_json_serialisable(self) -> None:
        m = IntentMatcher().match("where are you")
        self.assertIsNotNone(m)
        text = json.dumps(m)
        again = json.loads(text)
        self.assertEqual(again["cid"], "whereami")

    def test_default_grammar_has_no_duplicates(self) -> None:
        cids = [c.cid for c in DEFAULT_GRAMMAR]
        self.assertEqual(len(cids), len(set(cids)),
                         f"duplicate cids: {cids}")


if __name__ == "__main__":
    unittest.main()
