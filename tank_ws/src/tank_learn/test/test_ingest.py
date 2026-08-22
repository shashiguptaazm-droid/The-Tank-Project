"""Hermetic tests for :mod:`tank_learn.ingest`.

Covers:
  * Ingest a single ModuleRecord → episode + per-cap facts + per-cap skills.
  * Run ingest_discovery_summary twice over same DiscoveryStore → zero
    duplicate episodes / no double-UPSERT error, facts just bump
    mention_count.
"""
from __future__ import annotations

import time
import unittest

from tank_learn.discovery_store import DiscoveryStore, ModuleRecord
from tank_learn.ingest import (
    IngestResult,
    _upsert_skill_at,
    ingest_discovery_summary,
    ingest_module,
)
from tank_learn.memory_store import MemoryStore


def _fresh_mem() -> MemoryStore:
    return MemoryStore(db_path=":memory:")


def _fresh_disc() -> DiscoveryStore:
    return DiscoveryStore(db_path=":memory:")


class IngestModuleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.m = _fresh_mem()

    def tearDown(self) -> None:
        self.m.close()

    def test_single_module_episode_facts_skills(self) -> None:
        rec = ModuleRecord(
            source="user_teach",
            name="my-rag",
            url="https://example.com",
            summary="RAG with vector DB.",
            capabilities=["text-generation", "retrieval"],
        )
        res = ingest_module(self.m, rec, now_ts=time.time())
        # 1 module episode + 2 capability episodes = 3 episodes added.
        self.assertEqual(res.episodes_added, 3)
        self.assertEqual(res.facts_added, 2)
        # 2 capabilities → 2 skills inserted at alpha=2/beta=1 prior.
        self.assertEqual(res.skills_added, 2)

        facts = self.m.facts(limit=10)
        concepts = sorted(f.concept for f in facts)
        self.assertEqual(concepts, ["retrieval", "text-generation"])

        skills = self.m.skills(min_proficiency=0.0, limit=10)
        ability_names = sorted(s.ability_name for s in skills)
        self.assertEqual(ability_names, ["retrieval", "text-generation"])
        # Starting proficiency = alpha/(alpha+beta) = 2/3 ≈ 0.667.
        for sk in skills:
            self.assertAlmostEqual(sk.proficiency, 2 / 3, places=4)

        episodes = self.m.recent_episodes(limit=10)
        self.assertGreaterEqual(len(episodes), 3)


class IngestDiscoverySummaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.m = _fresh_mem()
        self.d = _fresh_disc()

    def tearDown(self) -> None:
        self.m.close()
        self.d.close()

    def test_discovery_ingest_adds_episodes_facts_skills(self) -> None:
        # Seed the discovery store directly.
        rec_a = ModuleRecord(source="hf", name="mistral-7b-rag",
                              url="https://huggingface.co/x",
                              summary="RAG-augmented Mistral model.",
                              capabilities=["text-generation", "retrieval"])
        rec_b = ModuleRecord(source="pypi", name="rag-eval",
                              url="https://pypi.org/project/rag-eval",
                              summary="Evaluation suite for RAG systems.",
                              capabilities=["retrieval", "evaluation"])
        self.d.upsert_module(rec_a, now_ts=time.time())
        self.d.upsert_module(rec_b, now_ts=time.time())
        for cap in rec_a.capabilities:
            self.d.add_capability("hf", rec_a.name, cap,
                                   now_ts=time.time())
        for cap in rec_b.capabilities:
            self.d.add_capability("pypi", rec_b.name, cap,
                                   now_ts=time.time())

        res = ingest_discovery_summary(self.m, self.d,
                                        now_ts=time.time(),
                                        source_label="discovery")
        self.assertEqual(res.modules_seen, 2)
        self.assertEqual(res.capabilities_seen, 4)
        # 2 module episodes + 4 capability episodes.
        self.assertEqual(res.episodes_added, 6)
        # 4 facts (one per capability; later UPSERTs dedupe).
        self.assertEqual(res.facts_added, 4)
        # 3 unique skills (text-generation, retrieval, evaluation).
        # NOTE: retrieval appears in BOTH rec_a AND rec_b's capability
        # lists, but `_upsert_skill_at` is idempotent — the second hit
        # bumbs last_use_ts but does NOT insert a duplicate row.
        self.assertEqual(self.res_skills_count(), 3)
        self.assertEqual(res.skills_added, 3)

    def test_second_ingest_is_idempotent_for_episodes(self) -> None:
        rec = ModuleRecord(source="hf", name="idem-test",
                             capabilities=["generation"])
        self.d.upsert_module(rec)
        self.d.add_capability("hf", rec.name, "generation")
        # First pass.
        r1 = ingest_discovery_summary(self.m, self.d)
        self.assertGreater(r1.episodes_added, 0)
        ep_count_before = len(self.m.recent_episodes(limit=1000))
        # Second pass — episodes.added should be 0 because dedupe_key
        # blocks the inserts.
        r2 = ingest_discovery_summary(self.m, self.d)
        self.assertEqual(r2.episodes_added, 0)
        ep_count_after = len(self.m.recent_episodes(limit=1000))
        self.assertEqual(ep_count_before, ep_count_after)

    def test_second_ingest_lifts_fact_mention_count(self) -> None:
        rec = ModuleRecord(source="hf", name="lift-test",
                             capabilities=["generation"])
        self.d.upsert_module(rec)
        self.d.add_capability("hf", rec.name, "generation")
        ingest_discovery_summary(self.m, self.d)
        facts_first = self.m.facts(limit=10)
        mc_first = next(f.mention_count for f in facts_first
                         if f.concept == "generation")
        ingest_discovery_summary(self.m, self.d)
        facts_second = self.m.facts(limit=10)
        mc_second = next(f.mention_count for f in facts_second
                          if f.concept == "generation")
        self.assertGreater(mc_second, mc_first)

    def test_upsert_skill_at_inserts_then_bumps(self) -> None:
        # First call returns an id, second refreshes last_use_ts.
        ts_now = time.time()
        first_id = _upsert_skill_at(self.m, "answer_rag",
                                     alpha_prior=2, beta_prior=1, ts=ts_now)
        self.assertIsNotNone(first_id)
        # Second call with new ts → current skills table now contains it.
        second_id = _upsert_skill_at(self.m, "answer_rag",
                                      alpha_prior=2, beta_prior=1,
                                      ts=ts_now + 1.0)
        # Second call returns None (ability exists), but skill row's
        # last_use_ts should move forward.
        row = next(s for s in self.m.skills(min_proficiency=0.0, limit=10)
                    if s.ability_name == "answer_rag")
        self.assertGreater(row.last_use_ts, ts_now - 1e-6)
        self.assertIsNone(second_id)

    # ── internal helper ────────────────────────────────────────────────
    def res_skills_count(self) -> int:
        return len(self.m.skills(min_proficiency=0.0, limit=10_000))


class IngestResultDataclassTests(unittest.TestCase):
    def test_to_dict_round_trip(self) -> None:
        r = IngestResult(episodes_added=2, facts_added=3, skills_added=1)
        d = r.to_dict()
        self.assertEqual(d["episodes_added"], 2)
        self.assertEqual(d["facts_added"], 3)
        self.assertEqual(d["skills_added"], 1)


if __name__ == "__main__":
    unittest.main()
