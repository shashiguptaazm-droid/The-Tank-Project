"""tank_learn.recall — semantic-recall ranker (pure-Python TF-IDF).

When the ROS speech bridge asks "What do I know about RAG?", the recaller:

  1. Loads the candidate corpus from :class:`MemoryStore` (facts + skills).
  2. Tokenises both query and corpus with the same lowercase+stop-word
     filter used by :mod:`tank_learn.consolidation`.
  3. Builds an in-memory TF-IDF matrix (no torch / sklearn; this runs on
     Jetson SD card with sub-millisecond warm-up).
  4. Scores each candidate with::

        final = 0.50 * cosine(query, candidate)
              + 0.30 * recency_score(candidate)
              + 0.20 * confidence_or_proficiency(candidate)

     where ``recency_score`` is a 30-day half-life exponential decay on
     age; ``confidence_or_proficiency`` is the fact's confidence (or the
     skill's proficiency for skill rows).

  5. Filters by ``tier`` (``facts`` / ``skills`` / ``episodes`` / ``all``)
     and returns the top-``k`` ranked rows with provenance.

Hermetic: no network, no torch, no sklearn. Inputs are passed in by the
caller (the in-store pull is also injected), so unit tests can drive
arbitrary corpora without touching the SQLite file.
"""
from __future__ import annotations

import math
import re
import time
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .memory_store import MemoryStore, SemanticFact, Skill


# ──── tokenisation (mirrors consolidation._tokenize_concepts) ───────────────
_TOKEN_RE = re.compile(r"[a-z0-9_\-]+")
_STOPWORDS = frozenset({
    "the", "and", "for", "with", "from", "this", "that", "into", "onto",
    "are", "was", "were", "has", "had", "have", "but", "not", "you", "your",
    "what", "when", "where", "while", "upon", "over", "under", "some",
    "any", "all", "each", "few", "more", "less", "than", "then", "they",
    "them", "their", "there", "can", "could", "should", "would",
    "about", "because", "between", "after", "before", "again",
})


def tokenize(text: str) -> List[str]:
    """Lowercase + alnum-keep tokeniser; drops stop-words and tokens < 3 chars.

    Accepts ``None`` defensively (treats ``None``, empty string, and
    whitespace-only identically) so callers can pass through optional
    text fields without first null-checking.
    """
    if text is None or not text:
        return []
    out: List[str] = []
    for m in _TOKEN_RE.findall(text.lower()):
        if len(m) < 3 or m in _STOPWORDS:
            continue
        out.append(m)
    return out


# ──── ranking weights (+ top-level tuning parameters) ────────────────────────
W_COSINE = 0.50
W_RECENCY = 0.30
W_CONFIDENCE = 0.20
RECENCY_HALF_LIFE_DAYS = 30.0


# ──── dataclasses for results ────────────────────────────────────────────────
@dataclass
class RecallHit:
    """One ranked hit returned to the operator / dashboard."""
    tier: str           # "facts" | "skills" | "episodes"
    key: str            # concept (facts) | ability_name (skills) | content-snippet
    score: float
    confidence_or_proficiency: float
    snippet: str
    provenance: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier":                     self.tier,
            "key":                      self.key,
            "score":                    round(self.score, 4),
            "confidence_or_proficiency": round(self.confidence_or_proficiency, 4),
            "snippet":                  self.snippet,
            "provenance":               dict(self.provenance),
        }


# ──── TF-IDF matrix (in-memory; no external deps) ────────────────────────────
class _TfIdfMatrix:
    """A minimal TF-IDF store built from a list of tokenised documents."""

    def __init__(self, corpus_tokens: Sequence[List[str]]) -> None:
        self._docs: List[List[str]] = [list(d) for d in corpus_tokens]
        self._df: Counter = Counter()
        self._tf: List[Counter] = []
        for doc in self._docs:
            tf = Counter(doc)
            self._tf.append(tf)
            for term in set(doc):
                self._df[term] += 1
        self._n_docs = max(1, len(self._docs))
        self._idf: Dict[str, float] = {
            term: math.log((1 + self._n_docs) / (1 + df)) + 1.0
            for term, df in self._df.items()
        }

    def cosine(self, query_tokens: List[str], doc_idx: int) -> float:
        if doc_idx < 0 or doc_idx >= len(self._docs):
            return 0.0
        q_tf = Counter(query_tokens)
        d_tf = self._tf[doc_idx]
        if not q_tf or not d_tf:
            return 0.0
        num = 0.0
        q_norm = 0.0
        d_norm = 0.0
        for term, q_count in q_tf.items():
            qw = q_count * self._idf.get(term, 1.0)
            q_norm += qw * qw
            d_count = d_tf.get(term, 0)
            if d_count:
                dw = d_count * self._idf.get(term, 1.0)
                num += qw * dw
        for term, d_count in d_tf.items():
            dw = d_count * self._idf.get(term, 1.0)
            d_norm += dw * dw
        if not q_norm or not d_norm:
            return 0.0
        return num / (math.sqrt(q_norm) * math.sqrt(d_norm))


# ──── score helpers ──────────────────────────────────────────────────────────
def _recency_score(ts: float, *, now_ts: float) -> float:
    """Exponential decay with a 30-day half-life on age."""
    age_days = max(0.0, (now_ts - ts) / 86400.0)
    return 0.5 ** (age_days / RECENCY_HALF_LIFE_DAYS)


def _snippet(text: str, *, n: int = 160) -> str:
    text = (text or "").strip()
    if len(text) <= n:
        return text
    return text[: n - 1].rstrip() + "…"


# ──── public ranker ──────────────────────────────────────────────────────────
def build_corpus(
    store: MemoryStore,
    *,
    since_ts: Optional[float] = None,
    include_episodes: bool = True,
    include_skills: bool = True,
) -> Tuple[List[Tuple[str, str, str,
                     Optional[SemanticFact],
                     Optional[Skill],
                     Optional[Any]]], List[Dict[str, Any]]]:
    """Pull fact + skill (+optional episode) corpus from the store.

    Returns ``(corpus, episode_meta)``:

    * ``corpus`` — list of ``(tier, key, doc_text, fact, skill, episode)``
                   tuples. Either ``fact`` or ``skill`` (or ``episode``) is
                   set; the others are None.
    * ``episode_meta`` — auxiliary metadata list (id, ts, source) used by
      the ranker to fill in provenance. Same length as episode rows.
    """
    facts, skills = store.recall_candidates()
    corpus: List[Tuple[str, str, str,
                       Optional[SemanticFact],
                       Optional[Skill],
                       Optional[Any]]] = []

    for fact in facts:
        text = f"{fact.concept} {fact.definition}".strip()
        corpus.append(("facts", fact.concept, text, fact, None, None))
    if include_skills:
        for skill in skills:
            text = (
                f"{skill.ability_name} skill "
                f"proficiency {skill.proficiency:.2f}"
            )
            corpus.append(("skills", skill.ability_name, text, None, skill, None))
    if include_episodes:
        episodes = store.recent_episodes(since_ts=since_ts, limit=200)
        for episode in episodes:
            text = episode.content
            corpus.append(
                ("episodes", f"ep:{episode.id}", text, None, None, episode),
            )

    return corpus, []


def rank(
    query: str,
    corpus: Sequence[Tuple[str, str, str,
                           Optional[SemanticFact],
                           Optional[Skill],
                           Optional[Any]]],
    *,
    top_k: int = 10,
    tier: str = "all",
    now_ts: Optional[float] = None,
) -> List[RecallHit]:
    """Score and rank ``corpus`` against ``query``.

    ``tier`` filter is applied AFTER scoring so the ranker can still
    pick cross-tier synergies (e.g., a skill semantically close to a fact).
    """
    tier = (tier or "all").lower().strip()
    if tier not in ("all", "facts", "skills", "episodes"):
        raise ValueError(
            f"tier must be all|facts|skills|episodes (got {tier!r})"
        )
    top_k = max(1, min(int(top_k), 100))
    now = float(now_ts if now_ts is not None else time.time())
    q_tokens = tokenize(query)
    if not q_tokens:
        return []

    docs = [c[2] for c in corpus]
    doc_tokens = [tokenize(d) for d in docs]
    matrix = _TfIdfMatrix(doc_tokens)

    hits: List[RecallHit] = []
    for idx, (tier_name, key, doc_text, fact, skill, episode) in enumerate(corpus):
        cosine = matrix.cosine(q_tokens, idx)
        # Confidence / proficiency + recency anchor.
        if fact is not None:
            conf = float(fact.confidence)
            anchor_ts = float(fact.last_recalled_ts)
            provenance: Dict[str, Any] = {
                "fact_id":           fact.id,
                "concept":           fact.concept,
                "mention_count":     fact.mention_count,
                "status":            fact.status,
                "first_learned_ts":  fact.first_learned_ts,
            }
            snippet_text = fact.definition
        elif skill is not None:
            conf = float(skill.proficiency)
            anchor_ts = float(skill.last_use_ts)
            provenance = {
                "skill_id":      skill.id,
                "ability":       skill.ability_name,
                "alpha":         skill.alpha,
                "beta":          skill.beta,
                "use_count":     skill.use_count,
            }
            snippet_text = (
                f"Ability: {skill.ability_name} "
                f"(proficiency {skill.proficiency:.2f})"
            )
        elif episode is not None:
            conf = 0.5  # episodes have no native confidence
            anchor_ts = float(episode.ts)
            provenance = {
                "episode_id":    episode.id,
                "source":        episode.source,
                "ts":            episode.ts,
                "content":       _snippet(episode.content, n=240),
            }
            snippet_text = _snippet(episode.content, n=240)
        else:
            continue
        recency = _recency_score(anchor_ts, now_ts=now)
        final = (
            W_COSINE * float(cosine)
            + W_RECENCY * float(recency)
            + W_CONFIDENCE * float(conf)
        )
        hits.append(RecallHit(
            tier=tier_name,
            key=key,
            score=final,
            confidence_or_proficiency=conf,
            snippet=_snippet(snippet_text),
            provenance=provenance,
        ))
    hits.sort(key=lambda h: h.score, reverse=True)
    if tier != "all":
        hits = [h for h in hits if h.tier == tier]
    return hits[:top_k]


def recall(
    query: str,
    store: MemoryStore,
    *,
    top_k: int = 10,
    tier: str = "all",
    include_episodes: bool = True,
    include_skills: bool = True,
) -> List[RecallHit]:
    """Convenience wrapper: pull corpus from ``store`` and rank in one call."""
    corpus, _ = build_corpus(
        store,
        include_episodes=include_episodes,
        include_skills=include_skills,
    )
    return rank(query, corpus, top_k=top_k, tier=tier)


__all__ = [
    "W_COSINE", "W_RECENCY", "W_CONFIDENCE", "RECENCY_HALF_LIFE_DAYS",
    "tokenize", "RecallHit",
    "build_corpus", "rank", "recall",
]
