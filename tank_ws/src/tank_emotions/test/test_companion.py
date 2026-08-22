"""test_companion — every emotion has a plan; safety flag maps to escalate stance."""
from __future__ import annotations

import unittest

from tank_emotions import (
    discover, get, companion_plan, classify_safety, empathy_prefix,
    fallback_reply, safe_floor_for, instruction_text,
)


class TestCompanion(unittest.TestCase):

    def test_every_emotion_has_a_companion_plan(self):
        for emo in discover().values():
            plan = companion_plan(emo)
            self.assertTrue(plan.stance,
                            f"{emo.name} returned empty stance")
            self.assertTrue(plan.tone,
                            f"{emo.name} returned empty tone")

    def test_safety_flag_implies_safety_in_plan(self):
        # Fear, sadness, anger, shame are flagged safety
        for name in {"fear", "sadness", "anger", "shame"}:
            emo = get(name)
            plan = companion_plan(emo)
            self.assertTrue(plan.safety, f"{name} should be SAFETY")
            self.assertIn("SAFETY", instruction_text(plan))

    def test_empathy_prefix_aligns_with_tone(self):
        emo = get("joy")
        plan = companion_plan(emo)
        prefix = empathy_prefix(plan)
        # warm -> starts with "of course — "
        self.assertTrue(prefix.startswith("of course"),
                        prefix)

    def test_safe_floor_zero_for_low_safety(self):
        emo = get("joy")
        plan = companion_plan(emo)
        self.assertIsNone(safe_floor_for(plan))

    def test_fallback_reply_includes_safety_when_needed(self):
        emo = get("fear")
        plan = companion_plan(emo)
        reply = fallback_reply("I can't breathe", plan)
        self.assertIn("trusted contact", reply.lower())

    def test_safety_classifier_flags_self_harm(self):
        flag = classify_safety("I want to kill myself")
        self.assertTrue(flag.flag)
        self.assertEqual(flag.kind, "self_harm")
        self.assertEqual(flag.severity, 3)


if __name__ == "__main__":
    unittest.main()
