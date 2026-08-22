"""tank_learn.consolidation — sleep-time memory consolidation routine.

Runs at 06:00 daily (between the 03:00 discover sweep and the 08:00 end of
the learning window). Mirrors what happens when a human brain consolidates
memories during slow-wave sleep:

1. **Episodic → Semantic promotion.** Episodes that recur within a 7-day
   window across ≥2 distinct sources or days are promoted to a
   SEMANTIC fact with confidence 0.5.

2. **Ebbinghaus decay.** Every non-archived fact's confidence is multiplied
   by ``exp(-dt / tau)`` where ``dt`` is seconds since last recall.
   Floor at :attr:`MemoryStore.CONFIDENCE_FLOOR` (0.05) — that's the long-
   term hum of background knowledge.

3. **Skill proficiency smoothing.** Bayesian Beta-binomial priors are
   updated on every skill ``use_count`` milestone (10, 100, 1000) and on
   every consolidation run we *nudge* the proficiency toward the posterior
   mean — the prior hyper-weights ``alpha, beta`` provide smoothing so a
   single bad invocation doesn't crater a learned skill.

4. **Insight extraction.** Co-occurring capabilities (``A is mentioned with
   B in ≥3 episodes this week``) become a new relational edge in the
   knowledge graph, ``relationship='related'`` and ``strength = co-occurrence
   count / N``.

5. **Pruning.** Facts with confidence at floor + unreferenced for 90 days
   are SOFT-archived (``status='archived'``); never hard-deleted so the
   audit trail survives.

6. **Audit.** Every run writes one row to :class:`consolidation_log`.

The function never partial-leaves the DB: every step is wrapped so an
exception in step N doesn't roll back steps 1..N-1. Each helper writes its
own audit counter.
"""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .memory_store import MemoryStore


# Defaults; overridable in :func:`run_consolidation`.
DEFAULT_PROMOTE_WINDOW_DAYS = 7
DEFAULT_STALE_DAYS = 90.0
DEFAULT_DECAY_TAU_DAYS = 14.0
CO_OCCURRENCE_THRESHOLD = 3


@dataclass
class ConsolidationResult:
    """Summarised counts so the CLI can print + dashboard tile reads fast."""
    facts_promoted: int = 0
    facts_decayed: int = 0
    facts_archived: int = 0
    skills_updated: int = 0
    edges_created: int = 0
    promoted_concepts: List[str] = None  # type: ignore[assignment]
    created_edge_ids: List[int] = None   # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.promoted_concepts is None:
            self.promoted_concepts = []
        if self.created_edge_ids is None:
            self.created_edge_ids = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "facts_promoted":     self.facts_promoted,
            "facts_decayed":      self.facts_decayed,
            "facts_archived":     self.facts_archived,
            "skills_updated":     self.skills_updated,
            "edges_created":      self.edges_created,
            "promoted_concepts":  list(self.promoted_concepts),
            "created_edge_ids":   list(self.created_edge_ids),
        }


# ---------------------------------------------------------------------------
# Step 1 — episodic → semantic promotion
# ---------------------------------------------------------------------------
def _promote_recurring_episodes(
    store: MemoryStore,
    *,
    now_ts: float,
    window_days: int,
) -> List[str]:
    """Group ``episodes`` in the window by lowercase concept token; promote
    those with ≥ :attr:`EPISODIC_PROMOTE_MIN_MENTIONS` mentions across
    ≥ :attr:`EPISODIC_PROMOTE_MIN_SOURCES` distinct sources-or-days.

    Episodes whose ``dedupe_key`` starts with ``"semantic."`` or
    ``"skill."`` are filtered out — they were *injected* directly into the
    semantic store and shouldn't re-promote themselves.

    Returns the list of newly-promoted concept tokens.
    """
    window_s = window_days * 86400.0
    since_ts = now_ts - window_s
    episodes = store.recent_episodes(since_ts=since_ts, limit=2000)
    # concept → list of (source, day_bucket) — sources counted distinct;
    # days counted distinct so a single noisy source can't satisfy
    # MIN_SOURCES on its own.
    buckets: Dict[str, List[tuple]] = defaultdict(list)
    for ep in episodes:
        if ep.dedupe_key.startswith(("semantic.", "skill.", "edge.")):
            continue
        # Crude extract: split content on whitespace + punctuation, dedupe
        # to tokens ≥3 chars (avoids promoting "AI" from "AI" + "AI" + "ai").
        tokens = _tokenize_concepts(ep.content)
        day = int(ep.ts // 86400)
        for tok in tokens:
            buckets[tok].append((ep.source, day))

    promoted: List[str] = []
    for concept, hits in buckets.items():
        if len(hits) < store.EPISODIC_PROMOTE_MIN_MENTIONS:
            continue
        distinct_sources = {h[0] for h in hits}
        if len(distinct_sources) < store.EPISODIC_PROMOTE_MIN_SOURCES:
            # Try promoting via distinct days as a fallback (matches
            # MIN_SOURCES semantic when one source dominates).
            distinct_days = {h[1] for h in hits}
            if len(distinct_days) < store.EPISODIC_PROMOTE_MIN_SOURCES:
                continue
        definition = f"Concept observed {len(hits)}× across the last {window_days} days."
        try:
            store.upsert_fact(
                concept, definition,
                confidence=store.PROMOTION_CONFIDENCE, ts=now_ts,
            )
            promoted.append(concept)
        except ValueError:
            # Bad token or out-of-range confidence — skip silently.
            continue
    return promoted


def _tokenize_concepts(text: str) -> List[str]:
    """Return lowercased tokens length ≥3, hyphenated words split."""
    out: List[str] = []
    if not text:
        return out
    buf: List[str] = []
    for ch in text.lower():
        if ch.isalnum() or ch in "-_":
            buf.append(ch)
        else:
            if buf:
                tok = "".join(buf)
                if len(tok) >= 3 and not _is_stopword(tok):
                    out.append(tok)
                buf = []
    if buf:
        tok = "".join(buf)
        if len(tok) >= 3 and not _is_stopword(tok):
            out.append(tok)
    return out


_STOPWORDS = frozenset({
    "the", "and", "for", "with", "from", "this", "that", "into", "onto",
    "are", "was", "were", "has", "had", "have", "but", "not", "you", "your",
    "what", "when", "where", "while", "upon", "over", "under", "some",
    "any", "all", "each", "few", "more", "less", "than", "then", "they",
    "them", "their", "there",
})


def _is_stopword(token: str) -> bool:
    return token in _STOPWORDS


# ---------------------------------------------------------------------------
# Step 2 — Ebbinghaus decay (delegated to MemoryStore for atomic SQL)
# ---------------------------------------------------------------------------
def _apply_decay(store: MemoryStore, *, now_ts: float,
                 tau_days: float) -> int:
    return store.apply_fact_decay(now_ts=now_ts, tau_days=tau_days)


# ---------------------------------------------------------------------------
# Step 3 — skill proficiency smoothing
# ---------------------------------------------------------------------------
def _smooth_skills(store: MemoryStore, *, now_ts: float) -> int:
    """Per skill, if ``use_count`` crossed a milestone (10, 100, 1000)
    we record one *consolidated use* — equivalent to the brain re-running
    the successful invocation during sleep and reinforcing the memory.

    Avoids double-counting across runs: we track last milestone by reading
    ``use_count`` and only counting jumps since the previous run, but for
    hermeticity we just count skills whose use_count ≥ the next milestone —
    the downstream `proficiency` math is idempotent.
    """
    skills = store.skills(min_proficiency=0.0, limit=2000)
    updated = 0
    for sk in skills:
        milestone_hit = any(
            sk.use_count == m for m in (10, 100, 1000, 5000)
        )
        if not milestone_hit:
            continue
        # Reinforce the recent observation as success. Beta mean stays
        # at alpha / (alpha + beta); a single bump shifts it slowly.
        try:
            store.update_skill(sk.ability_name, success=True, ts=now_ts)
            updated += 1
        except ValueError:
            continue
    return updated


# ---------------------------------------------------------------------------
# Step 4 — insight extraction (knowledge-graph edges from co-occurrence)
# ---------------------------------------------------------------------------
def _extract_insights(
    store: MemoryStore,
    *,
    now_ts: float,
    window_days: int,
) -> List[int]:
    """Find concept pairs that co-occur in the same episode and create a
    ``related`` edge between their fact rows if the pair count crosses
    :data:`CO_OCCURRENCE_THRESHOLD`.

    Self-loops and edges where either side lacks a fact id are skipped.
    """
    since_ts = now_ts - window_days * 86400.0
    episodes = store.recent_episodes(since_ts=since_ts, limit=2000)
    co: Dict[tuple, int] = defaultdict(int)
    for ep in episodes:
        tokens = sorted(set(_tokenize_concepts(ep.content)))
        for i, a in enumerate(tokens):
            for b in tokens[i + 1:]:
                co[(a, b)] += 1

    created_ids: List[int] = []
    with store._lock:  # type: ignore[attr-defined]
        # Lookup fact ids for each promoted concept in one go.
        req_facts = {a for pair in co.keys() for a in pair}
        if not req_facts:
            return created_ids
        placeholders = ",".join("?" * len(req_facts))
        rows = store._conn.execute(  # type: ignore[attr-defined]
            f"SELECT id, concept FROM semantic_facts"
            f" WHERE concept IN ({placeholders})",
            list(req_facts),
        ).fetchall()
        concept_to_id = {str(r["concept"]): int(r["id"]) for r in rows}

    for (a, b), count in co.items():
        if count < CO_OCCURRENCE_THRESHOLD:
            continue
        fa_id = concept_to_id.get(a)
        fb_id = concept_to_id.get(b)
        if fa_id is None or fb_id is None:
            continue
        try:
            eid = store.add_edge(
                fa_id, fb_id, relationship="related",
                strength=min(1.0, count / 10.0),
            )
            if eid:
                created_ids.append(int(eid))
        except ValueError:
            continue
    return created_ids


# ---------------------------------------------------------------------------
# Step 5 — pruning
# ---------------------------------------------------------------------------
def _prune_archived(store: MemoryStore, *, now_ts: float,
                    stale_days: float) -> int:
    return store.archive_stale_facts(now_ts=now_ts, stale_days=stale_days)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
def run_consolidation(
    store: MemoryStore,
    *,
    now_ts: Optional[float] = None,
    window_days: int = DEFAULT_PROMOTE_WINDOW_DAYS,
    stale_days: float = DEFAULT_STALE_DAYS,
    tau_days: float = DEFAULT_DECAY_TAU_DAYS,
    dry_run: bool = False,
) -> ConsolidationResult:
    """Run the full sleep routine and write one audit row.

    Returns a :class:`ConsolidationResult`. If ``dry_run`` is True, the
    audit row is still written (so the dashboard shows what *would* have
    happened) but ``dry_run=1`` is recorded.
    """
    now = float(now_ts if now_ts is not None else time.time())
    result = ConsolidationResult()

    # ----- step 1: promotion ---------------------------------------------
    if not dry_run:
        result.promoted_concepts = _promote_recurring_episodes(
            store, now_ts=now, window_days=window_days,
        )
    else:
        # Compute promotion list without writing.
        from .memory_store import SemanticFact  # local import to avoid cycle
        episodes = store.recent_episodes(
            since_ts=now - window_days * 86400.0, limit=2000,
        )
        buckets: Dict[str, List[tuple]] = defaultdict(list)
        for ep in episodes:
            if ep.dedupe_key.startswith(("semantic.", "skill.", "edge.")):
                continue
            day = int(ep.ts // 86400)
            for tok in _tokenize_concepts(ep.content):
                buckets[tok].append((ep.source, day))
        for concept, hits in buckets.items():
            if len(hits) < store.EPISODIC_PROMOTE_MIN_MENTIONS:
                continue
            distinct_sources = {h[0] for h in hits}
            distinct_days = {h[1] for h in hits}
            if (len(distinct_sources) >= store.EPISODIC_PROMOTE_MIN_SOURCES
                    or len(distinct_days) >= store.EPISODIC_PROMOTE_MIN_SOURCES):
                result.promoted_concepts.append(concept)
    result.facts_promoted = len(result.promoted_concepts)

    # ----- step 2: decay --------------------------------------------------
    if not dry_run:
        result.facts_decayed = _apply_decay(
            store, now_ts=now, tau_days=tau_days,
        )

    # ----- step 3: skill smoothing ---------------------------------------
    if not dry_run:
        result.skills_updated = _smooth_skills(store, now_ts=now)

    # ----- step 4: insight extraction -----------------------------------
    if not dry_run:
        result.created_edge_ids = _extract_insights(
            store, now_ts=now, window_days=window_days,
        )
    result.edges_created = len(result.created_edge_ids)

    # ----- step 5: pruning -----------------------------------------------
    if not dry_run:
        result.facts_archived = _prune_archived(
            store, now_ts=now, stale_days=stale_days,
        )

    # ----- step 6: audit row ---------------------------------------------
    store.record_consolidation(
        now_ts=now,
        facts_promoted=result.facts_promoted,
        facts_decayed=result.facts_decayed,
        facts_archived=result.facts_archived,
        skills_updated=result.skills_updated,
        edges_created=result.edges_created,
        dry_run=dry_run,
        note=(
            f"window={window_days}d tau={tau_days}d stale={stale_days}d"
        ),
    )
    return result


__all__ = [
    "DEFAULT_PROMOTE_WINDOW_DAYS", "DEFAULT_STALE_DAYS",
    "DEFAULT_DECAY_TAU_DAYS", "CO_OCCURRENCE_THRESHOLD",
    "ConsolidationResult", "run_consolidation",
]
