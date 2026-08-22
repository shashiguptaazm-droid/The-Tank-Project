"""Hermetic tests for :mod:`tank_learn.memory_store`.

Uses :memory: SQLite DB. No network, no rclpy. Mirrors the chassis-test
pattern in :mod:`test.feedback_store` (which we're intentionally NOT
re-running in case those paths have changed; this file is a sibling that
should pass independently).
"""
from __future__ import annotations

import math
import unittest

from tank_learn.memory_store import (
    CONFIDENCE_FLOOR,
    MemoryStore,
    FactEdge,
    SemanticFact,
    Skill,
)


def _fresh() -> MemoryStore:
    return MemoryStore(db_path=":memory:")


class MemoryStoreInitTests(unittest.TestCase):
    def test_init_creates_db_in_memory(self) -> None:
        s = _fresh()
        self.assertEqual(s.schema_version, 1)
        s.close()

    def test_double_close_is_noop(self) -> None:
        s = _fresh()
        s.close()
        s.close()  # second close must NOT raise.


class EpisodeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.s = _fresh()

    def tearDown(self) -> None:
        self.s.close()

    def test_record_episode_basic(self) -> None:
        eid = self.s.record_episode("user_teach", "the cat sat on the mat",
                                     ts=1000.0,
                                     metadata={"kind": "test"})
        self.assertGreater(eid, 0)
        eps = self.s.recent_episodes(limit=5)
        self.assertEqual(len(eps), 1)
        self.assertEqual(eps[0].source, "user_teach")
        self.assertEqual(eps[0].ts, 1000.0)
        self.assertEqual(eps[0].metadata, {"kind": "test"})

    def test_episodes_recent_orders_descending(self) -> None:
        for i in range(5):
            self.s.record_episode("test", f"event {i}", ts=float(i))
        eps = self.s.recent_episodes(limit=5)
        ts_list = [e.ts for e in eps]
        self.assertEqual(ts_list, sorted(ts_list, reverse=True))

    def test_dedupe_key_returns_zero_on_collision(self) -> None:
        first_id = self.s.record_episode("user", "first",
                                          dedupe_key="k1", ts=1.0)
        self.assertGreater(first_id, 0)
        # Second insert with the SAME dedupe_key is a silent no-op:
        # record_episode() returns 0 instead of raising IntegrityError so
        # callers in hot ingest loops don't have to catch exceptions.
        second_id = self.s.record_episode("user", "second",
                                           dedupe_key="k1", ts=2.0)
        self.assertEqual(second_id, 0)
        # Exactly one row in the table.
        self.assertEqual(len(self.s.recent_episodes(limit=10)), 1)

    def test_empty_dedupe_key_allows_multiple(self) -> None:
        for i in range(3):
            self.s.record_episode("test", f"e{i}", dedupe_key="", ts=float(i))
        self.assertEqual(len(self.s.recent_episodes(limit=10)), 3)


class SemanticFactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.s = _fresh()

    def tearDown(self) -> None:
        self.s.close()

    def test_upsert_new_fact(self) -> None:
        fid = self.s.upsert_fact("rag",
            "Retrieval-augmented generation",
            confidence=0.42, ts=100.0)
        facts = self.s.facts(limit=10)
        self.assertEqual(len(facts), 1)
        self.assertEqual(facts[0].concept, "rag")
        self.assertEqual(facts[0].confidence, 0.42)

    def test_upsert_lifts_confidence(self) -> None:
        self.s.upsert_fact("rag", "first def", confidence=0.30,
                            ts=100.0)
        self.s.upsert_fact("rag", "second def", confidence=0.70,
                            ts=200.0)
        facts = self.s.facts(limit=10)
        self.assertEqual(len(facts), 1)
        self.assertEqual(facts[0].confidence, 0.70)  # MAX(0.3, 0.7)
        self.assertEqual(facts[0].mention_count, 2)

    def test_upsert_lower_confidence_is_rejected(self) -> None:
        self.s.upsert_fact("rag", "first def", confidence=0.70)
        self.s.upsert_fact("rag", "second def", confidence=0.50)
        facts = self.s.facts(limit=10)
        # Max() in SQL means the higher value wins — never silently lower.
        self.assertEqual(facts[0].confidence, 0.70)

    def test_invalid_confidence_rejected_at_upsert(self) -> None:
        with self.assertRaises(ValueError):
            self.s.upsert_fact("rag", "def", confidence=2.0)
        with self.assertRaises(ValueError):
            self.s.upsert_fact("rag", "def", confidence=0.01)
        # Below floor (0.05) is invalid.
        with self.assertRaises(ValueError):
            self.s.upsert_fact("rag", "def", confidence=0.04)

    def test_blank_concept_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.s.upsert_fact("", "def")
        with self.assertRaises(ValueError):
            self.s.upsert_fact("   ", "def")

    def test_bump_fact_recall(self) -> None:
        self.s.upsert_fact("rag", "def", confidence=0.5, ts=100.0)
        self.s.bump_fact_recall("rag", ts=200.0)
        facts = self.s.facts(limit=10)
        self.assertEqual(facts[0].last_recalled_ts, 200.0)
        self.assertEqual(facts[0].mention_count, 2)

    def test_apply_decay_floor_respected(self) -> None:
        # Insert fact with confidence 0.5, last_recalled 10 days ago;
        # with tau=14 days, decay_multiplier = exp(-10/14).
        ts_now = 10 * 86400.0
        self.s.upsert_fact("rag", "def", confidence=0.50, ts=0.0)
        touched = self.s.apply_fact_decay(now_ts=ts_now, tau_days=14.0)
        self.assertEqual(touched, 1)
        facts = self.s.facts(limit=10)
        # Floor at 0.05; expected = max(0.05, 0.5 * e^(-10/14))
        expected = max(CONFIDENCE_FLOOR,
                       0.5 * math.exp(-10.0 / 14.0))
        self.assertAlmostEqual(facts[0].confidence, expected, places=3)


class SkillTests(unittest.TestCase):
    def setUp(self) -> None:
        self.s = _fresh()

    def tearDown(self) -> None:
        self.s.close()

    def test_update_skill_first_insert(self) -> None:
        sid = self.s.update_skill("answer_rag_questions", success=True, ts=1.0)
        skills = self.s.skills(min_proficiency=0.0, limit=10)
        self.assertEqual(len(skills), 1)
        sk = skills[0]
        self.assertEqual(sk.ability_name, "answer_rag_questions")
        self.assertEqual(sk.alpha, 2)   # prior=1 + 1 success
        self.assertEqual(sk.beta, 1)    # prior=1 + 0 failures
        self.assertEqual(sk.use_count, 1)

    def test_update_skill_success_then_failure(self) -> None:
        self.s.update_skill("answer_rag_questions", success=True, ts=1.0)
        self.s.update_skill("answer_rag_questions", success=False, ts=2.0)
        skills = self.s.skills(min_proficiency=0.0, limit=10)
        sk = skills[0]
        self.assertEqual(sk.alpha, 2)
        self.assertEqual(sk.beta, 2)
        self.assertEqual(sk.use_count, 2)
        # proficiency = alpha / (alpha + beta) = 2 / 4 = 0.5
        self.assertAlmostEqual(sk.proficiency, 0.5, places=4)

    def test_update_skill_blank_ability_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.s.update_skill("", success=True)
        with self.assertRaises(ValueError):
            self.s.update_skill("   ", success=True)

    def test_skills_filter_by_min_proficiency(self) -> None:
        # Create two skills with very different outcomes.
        self.s.update_skill("always_works", success=True)
        self.s.update_skill("always_works", success=True)
        self.s.update_skill("always_works", success=True)
        self.s.update_skill("rarely_works", success=False)
        self.s.update_skill("rarely_works", success=False)
        self.s.update_skill("rarely_works", success=False)
        skills = self.s.skills(min_proficiency=0.4, limit=10)
        ability_names = sorted(s.ability_name for s in skills)
        self.assertEqual(ability_names, ["always_works"])


class EdgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.s = _fresh()

    def tearDown(self) -> None:
        self.s.close()

    def test_add_edge_basic(self) -> None:
        fa = self.s.upsert_fact("rag", "def", confidence=0.5)
        fb = self.s.upsert_fact("vector_db", "def", confidence=0.5)
        eid = self.s.add_edge(fa, fb, relationship="uses", strength=0.8)
        self.assertGreater(eid, 0)
        edges = self.s.edges(min_strength=0.0, limit=10)
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].relationship, "uses")

    def test_add_edge_self_loop_rejected(self) -> None:
        fid = self.s.upsert_fact("solo", "def", confidence=0.5)
        eid = self.s.add_edge(fid, fid)
        self.assertEqual(eid, 0)
        self.assertEqual(len(self.s.edges(limit=10)), 0)

    def test_add_edge_lifts_strength(self) -> None:
        fa = self.s.upsert_fact("a", "def")
        fb = self.s.upsert_fact("b", "def")
        self.s.add_edge(fa, fb, relationship="related", strength=0.3)
        self.s.add_edge(fa, fb, relationship="related", strength=0.8)
        edges = self.s.edges(min_strength=0.0, limit=10)
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].strength, 0.8)

    def test_recall_candidates_empty_store(self) -> None:
        facts, skills = self.s.recall_candidates()
        self.assertEqual(facts, [])
        self.assertEqual(skills, [])

    def test_recall_candidates_with_content(self) -> None:
        self.s.upsert_fact("rag", "Retrieval-augmented generation",
                           confidence=0.7)
        self.s.update_skill("answer_rag", success=True)
        facts, skills = self.s.recall_candidates()
        self.assertEqual(len(facts), 1)
        self.assertEqual(len(skills), 1)


class ConsolidationLogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.s = _fresh()

    def tearDown(self) -> None:
        self.s.close()

    def test_record_and_read_latest(self) -> None:
        self.s.record_consolidation(
            facts_promoted=3, facts_decayed=42, dry_run=False,
            note="window=7d", now_ts=100.0)
        latest = self.s.latest_consolidation()
        self.assertIsNotNone(latest)
        self.assertEqual(latest.facts_promoted, 3)
        self.assertEqual(latest.facts_decayed, 42)
        self.assertFalse(latest.dry_run)
        self.assertEqual(latest.note, "window=7d")

    def test_latest_consolidation_on_empty_store(self) -> None:
        self.assertIsNone(self.s.latest_consolidation())


class StaleArchiveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.s = _fresh()

    def tearDown(self) -> None:
        self.s.close()

    def test_archive_stale_facts(self) -> None:
        # Insert facts with confidence at floor + ts older than threshold.
        long_ago = 1e9
        self.s.upsert_fact("stale_one", "old", confidence=0.05, ts=long_ago)
        self.s.upsert_fact("stale_two", "old", confidence=0.05, ts=long_ago)
        self.s.upsert_fact("fresh", "def", confidence=0.5, ts=long_ago)
        archived = self.s.archive_stale_facts(
            now_ts=long_ago + 100 * 86400, stale_days=90,
        )
        self.assertEqual(archived, 2)
        facts = self.s.facts(limit=10)
        statuses = {f.concept: f.status for f in facts}
        self.assertEqual(statuses["stale_one"], "archived")
        self.assertEqual(statuses["stale_two"], "archived")
        self.assertEqual(statuses["fresh"], "shallow")


if __name__ == "__main__":
    unittest.main()
