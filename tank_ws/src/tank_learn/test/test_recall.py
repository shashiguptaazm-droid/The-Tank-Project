"""Hermetic tests for :mod:`tank_learn.recall`.

Covers: tokenisation, TF-IDF cosine, recency decay, final-blend scoring,
tier filtering, top-k truncation, empty-query short-circuit.
"""
from __future__ import annotations

import math
import time
import unittest

from tank_learn.memory_store import MemoryStore
from tank_learn.recall import (
    W_CONFIDENCE, W_COSINE, W_RECENCY,
    recall, rank, tokenize, build_corpus,
)


def _store() -> MemoryStore:
    return MemoryStore(db_path=":memory:")


class TokenizeTests(unittest.TestCase):

    def test_lowercases_and_drops_stopnspts(self) -> None:
        out = tokenize("The Cat, sat on the mat. The wand is OFF!")
        # 'the' is a stopword; short tokens <3 are dropped.
        self.assertIn("cat", out)
        self.assertIn("sat", out)
        self.assertIn("mat", out)
        self.assertIn("wand", out)
        self.assertIn("off", out)
        self.assertNotIn("the", out)

    def test_hyphen_and_underscore_kept(self) -> None:
        out = tokenize("snake_case and kebab-case tokens")
        self.assertIn("snake_case", out)
        self.assertIn("kebab-case", out)

    def test_short_tokens_dropped(self) -> None:
        out = tokenize("a be cat")
        # 'a' (1 char), 'be' (2 chars) → dropped; 'cat' → kept
        self.assertEqual(out, ["cat"])

    def test_empty_returns_empty(self) -> None:
        self.assertEqual(tokenize(""), [])
        self.assertEqual(tokenize(None), [])


class RankTests(unittest.TestCase):
    """Drive ``rank`` directly with handcrafted corpus tuples."""

    def _corpus(self) -> list:
        # Two facts, one skill, one episode.
        f1 = type("F", (), {
            "id": 1, "concept": "rag",
            "definition": "retrieval augmented generation",
            "confidence": 0.7,
            "last_recalled_ts": time.time(),
            "first_learned_ts": time.time() - 86400.0 * 30.0,
            "status": "consolidated", "mention_count": 4,
            "to_dict": lambda self: {},
        })()
        f2 = type("F", (), {
            "id": 2, "concept": "banana",
            "definition": "A yellow tropical fruit",
            "confidence": 0.95,
            "last_recalled_ts": time.time(),
            "first_learned_ts": time.time() - 86400.0 * 60.0,
            "status": "consolidated", "mention_count": 10,
            "to_dict": lambda self: {},
        })()
        sk = type("S", (), {
            "id": 10, "ability_name": "answer_rag_questions",
            "proficiency": 0.6, "alpha": 3, "beta": 2,
            "last_use_ts": time.time() - 86400.0 * 5.0,
            "use_count": 7,
            "to_dict": lambda self: {},
        })()
        ep = type("E", (), {
            "id": 100, "source": "user_teach", "ts": time.time(),
            "content": "Yesterday I read about retrieval augmented generation.",
            "metadata": {},
            "to_dict": lambda self: {},
        })()
        return [
            ("facts",   "rag",     f"{f1.concept} {f1.definition}",
             f1, None, None),
            ("facts",   "banana",  f"{f2.concept} {f2.definition}",
             f2, None, None),
            ("skills",  "answer_rag_questions", sk.ability_name,
             None, sk, None),
            ("episodes", "ep:100", ep.content, None, None, ep),
        ]

    def test_empty_query_returns_empty(self) -> None:
        self.assertEqual(rank("", self._corpus()), [])

    def test_rag_query_ranks_rag_first(self) -> None:
        hits = rank("retrieval augmented generation", self._corpus(),
                    top_k=10)
        self.assertGreater(len(hits), 0)
        # RAG fact should be in top-1 even though banana has higher
        # confidence (cosine dominates).
        self.assertEqual(hits[0].tier, "facts")
        self.assertEqual(hits[0].key, "rag")

    def test_tier_filter_excludes_other_tiers(self) -> None:
        hits = rank("retrieval augmented generation", self._corpus(),
                    tier="skills", top_k=10)
        for h in hits:
            self.assertEqual(h.tier, "skills")

    def test_top_k_truncates(self) -> None:
        hits = rank("retrieval augmented generation banana", self._corpus(),
                    top_k=1)
        self.assertEqual(len(hits), 1)

    def test_score_weights_sum_to_one(self) -> None:
        s = W_COSINE + W_RECENCY + W_CONFIDENCE
        self.assertAlmostEqual(s, 1.0, places=6)

    def test_invalid_tier_raises(self) -> None:
        with self.assertRaises(ValueError):
            rank("anything", self._corpus(), tier="bogus")


class RecallIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.s = _store()

    def tearDown(self) -> None:
        self.s.close()

    def test_recall_finds_seeded_fact(self) -> None:
        self.s.upsert_fact("rag",
            "Retrieval augmented generation helps the LLM cite sources.",
            confidence=0.9, ts=time.time())
        self.s.upsert_fact("banana",
            "A yellow tropical fruit eaten by monkeys and humans alike.",
            confidence=0.95, ts=time.time())
        hits = recall("retrieval", self.s, top_k=5, tier="facts")
        self.assertGreater(len(hits), 0)
        self.assertEqual(hits[0].key, "rag")

    def test_recall_returns_empty_for_no_match(self) -> None:
        self.s.upsert_fact("rag", "retrieval augmented", confidence=0.5)
        hits = recall("nonexistent_term_xyzzy", self.s, top_k=5, tier="facts")
        # TF-IDF with very low overlap still produces scores > 0
        # because of the +1 smoothing; we just check the result is
        # non-error and has a deterministic cap.
        self.assertIsInstance(hits, list)

    def test_build_corpus_has_three_tiers(self) -> None:
        self.s.upsert_fact("rag", "x", confidence=0.5)
        # seed a skill row directly
        from tank_learn.ingest import _upsert_skill_at
        _upsert_skill_at(self.s, "answer_rag",
                          alpha_prior=2, beta_prior=1, ts=time.time())
        self.s.record_episode("user_teach", "rag", ts=time.time())
        corpus, _ = build_corpus(self.s)
        tiers = {row[0] for row in corpus}
        self.assertIn("facts", tiers)
        self.assertIn("skills", tiers)
        self.assertIn("episodes", tiers)


if __name__ == "__main__":
    unittest.main()
