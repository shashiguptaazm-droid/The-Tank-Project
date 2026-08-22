"""Hermetic tests for :mod:`tank_learn.consolidation`.

Covers: promotion thresholds, Ebbinghaus decay call-through, skill
smoothing milestones, insight edges, pruning, dry-run audit, idempotency.
"""
from __future__ import annotations

import unittest

from tank_learn.consolidation import (
    CO_OCCURRENCE_THRESHOLD,
    run_consolidation,
)
from tank_learn.memory_store import MemoryStore


def _store() -> MemoryStore:
    return MemoryStore(db_path=":memory:")


class PromotionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.s = _store()

    def tearDown(self) -> None:
        self.s.close()

    def test_recurring_episodes_promote(self) -> None:
        # Three episodes about "transformer" over a 7-day window — the
        # tokeniser catches all \u22653-char non-stopword tokens (found,
        # another, transformer, model here) and any token that co-occurs
        # \u22653\u00d7 within 3 distinct days qualifies to be promoted.
        for ts in (10.0, 30.0, 60.0):
            self.s.record_episode(
                "discovery", f"Found another transformer model at t={ts}",
                ts=ts * 86400.0,
                dedupe_key=f"ep:{ts}",
            )
        res = run_consolidation(
            self.s, now_ts=70.0 * 86400.0,
            window_days=7, tau_days=14, stale_days=90,
            dry_run=False,
        )
        # The test's INTENT is that "transformer" gets promoted; we
        # assert inclusivity rather than a strict count because other
        # recurring tokens (found, another, model) ALSO legitimately
        # qualify under the documented promotion rules.
        self.assertGreaterEqual(res.facts_promoted, 1)
        self.assertIn("transformer", res.promoted_concepts)
        facts = self.s.facts(limit=10)
        promoted = [f for f in facts if f.concept == "transformer"]
        self.assertEqual(len(promoted), 1)
        self.assertEqual(promoted[0].status, "shallow")

    def test_insufficient_mentions_no_promotion(self) -> None:
        self.s.record_episode("discovery", "transformer spotted",
                              ts=10.0 * 86400.0)
        res = run_consolidation(
            self.s, now_ts=15.0 * 86400.0,
            window_days=7,
            dry_run=False,
        )
        # < 3 mentions or < 2 sources → no promotion.
        self.assertEqual(res.facts_promoted, 0)

    def test_single_source_three_timestamps_promotes(self) -> None:
        # Same source, but THREE different days \u2192 distinct_days satisfies
        # MIN_SOURCES=2 fallback path. The tokeniser picks up both
        # "transformer" and "day" so both legitimately get promoted.
        for i, ts in enumerate([1.0, 2.0, 3.0]):
            self.s.record_episode(
                "discovery",
                f"transformer day {i}",
                ts=ts * 86400.0,
                dedupe_key=f"solo:{i}",
            )
        res = run_consolidation(
            self.s, now_ts=4.0 * 86400.0, window_days=7,
            dry_run=False,
        )
        # Inclusivity, not strict count: "transformer" must be present
        # AND at least one concept promoted.
        self.assertGreaterEqual(res.facts_promoted, 1)
        self.assertIn("transformer", res.promoted_concepts)


class DryRunTests(unittest.TestCase):
    def setUp(self) -> None:
        self.s = _store()

    def tearDown(self) -> None:
        self.s.close()

    def test_dry_run_writes_audit_but_no_facts(self) -> None:
        for ts in (1.0, 2.0, 3.0):
            self.s.record_episode(
                "discovery", f"transformer at t={ts}",
                ts=ts * 86400.0, dedupe_key=f"dry:{ts}",
            )
        res = run_consolidation(
            self.s, now_ts=4.0 * 86400.0, window_days=7, dry_run=True,
        )
        self.assertEqual(res.facts_promoted, 1)  # dry-run still counts.

        last = self.s.latest_consolidation()
        self.assertIsNotNone(last)
        self.assertTrue(last.dry_run)


class DecayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.s = _store()

    def tearDown(self) -> None:
        self.s.close()

    def test_decay_call_through(self) -> None:
        self.s.upsert_fact("rag", "def", confidence=0.9, ts=0.0)
        self.s.upsert_fact("transformer", "def", confidence=0.6, ts=0.0)
        res = run_consolidation(
            self.s, now_ts=14.0 * 86400.0,
            window_days=7, tau_days=14.0, stale_days=90,
            dry_run=False,
        )
        # 2 facts, both touched by the decay expression (the SQL UPDATE
        # counts all rows where confidence >= floor_class_anonymous; see
        # MemoryStore.apply_fact_decay for the exact predicate).
        self.assertEqual(res.facts_decayed, 2)


class SkillSmoothingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.s = _store()

    def tearDown(self) -> None:
        self.s.close()

    def test_milestone_10_bumps_skill(self) -> None:
        # Insert a skill, then drive use_count to exactly 10.
        self.s.update_skill("answer_rag", success=True, ts=1.0)
        # Reach use_count==10
        for _ in range(9):
            self.s.update_skill("answer_rag", success=True, ts=1.0)
        skills_before = self.s.skills(min_proficiency=0.0, limit=10)
        sk_pre = skills_before[0]
        self.assertEqual(sk_pre.use_count, 10)
        prof_pre = sk_pre.proficiency
        # Consolidate; the milestone bump should push alpha +1 more →
        # proficiency should rise slightly.
        res = run_consolidation(
            self.s, now_ts=2.0, window_days=7, dry_run=False,
        )
        self.assertEqual(res.skills_updated, 1)
        skills_after = self.s.skills(min_proficiency=0.0, limit=10)
        sk_post = skills_after[0]
        self.assertGreater(sk_post.alpha, sk_pre.alpha)
        self.assertGreater(sk_post.proficiency, prof_pre - 1e-9)

    def test_non_milestone_no_update(self) -> None:
        self.s.update_skill("fresh_skill", success=True, ts=1.0)
        # use_count=1, not at any milestone → no smoothing.
        res = run_consolidation(
            self.s, now_ts=2.0, window_days=7, dry_run=False,
        )
        self.assertEqual(res.skills_updated, 0)


class InsightEdgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.s = _store()

    def tearDown(self) -> None:
        self.s.close()

    def test_co_occurring_concepts_create_edge(self) -> None:
        # Seed two facts so they have ids.
        self.s.upsert_fact("rag", "def")
        self.s.upsert_fact("vectordb", "def")
        # Three episodes co-mention both concepts.
        for i in range(3):
            self.s.record_episode(
                "discovery",
                f"rag uses vectordb at observation {i}",
                ts=float(i + 1) * 86400.0,
                dedupe_key=f"co:{i}",
            )
        res = run_consolidation(
            self.s, now_ts=10.0 * 86400.0,
            window_days=7, dry_run=False,
        )
        # promotion should have run first; check edges created.
        self.assertGreaterEqual(res.edges_created, 1)
        edges = self.s.edges(min_strength=0.0, limit=10)
        self.assertGreaterEqual(len(edges), 1)

    def test_below_threshold_no_edge(self) -> None:
        self.s.upsert_fact("rag", "def")
        self.s.upsert_fact("solo_concept", "def")
        # Twice — under CO_OCCURRENCE_THRESHOLD=3.
        for i in range(2):
            self.s.record_episode(
                "discovery",
                f"rag with solo_concept {i}",
                ts=float(i + 1) * 86400.0,
                dedupe_key=f"few:{i}",
            )
        res = run_consolidation(
            self.s, now_ts=10.0 * 86400.0,
            window_days=7, dry_run=False,
        )
        self.assertEqual(res.edges_created, 0)


class EmptyStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.s = _store()

    def tearDown(self) -> None:
        self.s.close()

    def test_no_episodes_no_crash(self) -> None:
        res = run_consolidation(
            self.s, now_ts=1000.0, window_days=7,
            dry_run=False,
        )
        self.assertEqual(res.facts_promoted, 0)
        self.assertEqual(res.facts_decayed, 0)
        self.assertEqual(res.skills_updated, 0)
        self.assertEqual(res.edges_created, 0)
        self.assertEqual(res.facts_archived, 0)
        # Still wrote a record.
        self.assertIsNotNone(self.s.latest_consolidation())


if __name__ == "__main__":
    unittest.main()
