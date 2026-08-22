"""tank_learn.memory_store — persistent long-term memory for The Tank OS.

Cognitive-architecture model (mirrors the human learning literature)::

    episodic memory   →  ONE-OFF events with provenance  ("on 2026-07-22 03:12
                          the overnight learner discovered Mistral-7B-RAG
                          on HuggingFace")
    semantic memory   →  CONSOLIDATED facts with confidence  ("RAG =
                          retrieval-augmented generation",  confidence=0.78)
    procedural memory →  SKILLS/ABILITIES with proficiency  ("can answer
                          torrents questions: proficiency=0.87")
    knowledge graph   →  EDGES between facts  ("RAG --uses--> vector DB")
    consolidation log →  PER-RUN audit of the sleep routine

Mirrors :mod:`tank_learn.feedback_store` chassis:

* Single persistent ``sqlite3.Connection`` per :class:`MemoryStore`.
* :class:`threading.Lock` serializes all reads + writes.
* ``PRAGMA journal_mode=WAL`` + ``synchronous=NORMAL`` + ``busy_timeout=5000``.
* ``isolation_level=None`` → autocommit per statement, no implicit transactions.

No rclpy / network dep — pure Python so the dashboard uvicorn pool, the
ROS feedback node, and the systemd consolidation timer can all open the
same DB file in any order without surprises.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# Default location sits beside tank_feedback.db / tank_discoveries.db.
# Override via MemoryStore(db_path=...) for tests + benches.
DEFAULT_DB_PATH = "/root/the tank project/tank_ws/data/tank_memory.db"

SCHEMA_VERSION = 1


# ---------------------------------------------------------------------------
# Dataclass snapshots
# ---------------------------------------------------------------------------
@dataclass
class Episode:
    """One episodic memory row — specific event with provenance."""

    id: int
    source: str           # "discovery" | "user_teach" | "voice_command" | ...
    content: str          # free-text event description
    ts: float             # time.time() UTC seconds
    dedupe_key: str = ""  # mirrors episodes.dedupe_key; "" means no
                           # idempotency contract (free-form events).
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id":         self.id,
            "source":     self.source,
            "content":    self.content,
            "ts":         self.ts,
            "dedupe_key": self.dedupe_key,
            "metadata":   dict(self.metadata),
        }


@dataclass
class SemanticFact:
    """One consolidated semantic fact with confidence."""

    id: int
    concept: str          # canonical lowercase token, e.g. "rag"
    definition: str       # "Retrieval-augmented generation"
    confidence: float     # 0.05 .. 1.0 (floored at 0.05; pruning < that)
    first_learned_ts: float
    last_recalled_ts: float
    status: str           # "shallow" | "consolidated" | "archived"
    mention_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id":               self.id,
            "concept":          self.concept,
            "definition":       self.definition,
            "confidence":       round(self.confidence, 4),
            "first_learned_ts": self.first_learned_ts,
            "last_recalled_ts": self.last_recalled_ts,
            "status":           self.status,
            "mention_count":    self.mention_count,
        }


@dataclass
class Skill:
    """One procedural-memory ability with Beta-binomial proficiency."""

    id: int
    ability_name: str     # canonical token, e.g. "answer_torrents_questions"
    proficiency: float    # alpha / (alpha + beta); 0.05 .. 1.0
    alpha: int            # Beta success pseudo-counts
    beta: int             # Beta failure pseudo-counts
    last_use_ts: float
    use_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id":            self.id,
            "ability_name":  self.ability_name,
            "proficiency":   round(self.proficiency, 4),
            "alpha":         self.alpha,
            "beta":          self.beta,
            "last_use_ts":   self.last_use_ts,
            "use_count":     self.use_count,
        }


@dataclass
class FactEdge:
    """One knowledge-graph edge between two semantic facts."""

    id: int
    fact_id_a: int
    fact_id_b: int
    relationship: str     # "uses" | "is_a" | "part_of" | "depends_on"
    strength: float       # 0.0 .. 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id":            self.id,
            "fact_id_a":     self.fact_id_a,
            "fact_id_b":     self.fact_id_b,
            "relationship":  self.relationship,
            "strength":      round(self.strength, 4),
        }


@dataclass
class ConsolidationRecord:
    """One row in the consolidation_log audit table."""

    id: int
    run_ts: float
    facts_promoted: int
    facts_decayed: int
    facts_archived: int
    skills_updated: int
    edges_created: int
    dry_run: bool
    note: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id":              self.id,
            "run_ts":          self.run_ts,
            "facts_promoted":  self.facts_promoted,
            "facts_decayed":   self.facts_decayed,
            "facts_archived":  self.facts_archived,
            "skills_updated":  self.skills_updated,
            "edges_created":   self.edges_created,
            "dry_run":         self.dry_run,
            "note":            self.note,
        }


# ---------------------------------------------------------------------------
# Schema (DDL per-statement so each CREATE auto-commits; mirroring feedback_store)
# ---------------------------------------------------------------------------
SCHEMA = f"""
CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    content TEXT NOT NULL,
    ts REAL NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{{}}',
    dedupe_key TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_episodes_ts ON episodes (ts);
CREATE INDEX IF NOT EXISTS idx_episodes_source ON episodes (source);
CREATE UNIQUE INDEX IF NOT EXISTS idx_episodes_dedupe ON episodes (dedupe_key)
    WHERE dedupe_key <> '';

CREATE TABLE IF NOT EXISTS semantic_facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    concept TEXT NOT NULL UNIQUE,
    definition TEXT NOT NULL DEFAULT '',
    confidence REAL NOT NULL DEFAULT 0.05,
    first_learned_ts REAL NOT NULL,
    last_recalled_ts REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'shallow',
    mention_count INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_facts_conf ON semantic_facts (confidence);
CREATE INDEX IF NOT EXISTS idx_facts_status ON semantic_facts (status);
CREATE INDEX IF NOT EXISTS idx_facts_last_recalled ON semantic_facts (last_recalled_ts);

CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ability_name TEXT NOT NULL UNIQUE,
    proficiency REAL NOT NULL DEFAULT 0.05,
    alpha INTEGER NOT NULL DEFAULT 1,
    beta INTEGER NOT NULL DEFAULT 1,
    last_use_ts REAL NOT NULL DEFAULT 0.0,
    use_count INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_skills_prof ON skills (proficiency);
CREATE INDEX IF NOT EXISTS idx_skills_last_use ON skills (last_use_ts);

CREATE TABLE IF NOT EXISTS knowledge_graph (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fact_id_a INTEGER NOT NULL,
    fact_id_b INTEGER NOT NULL,
    relationship TEXT NOT NULL DEFAULT 'related',
    strength REAL NOT NULL DEFAULT 0.5,
    UNIQUE (fact_id_a, fact_id_b, relationship)
);
CREATE INDEX IF NOT EXISTS idx_kg_a ON knowledge_graph (fact_id_a);
CREATE INDEX IF NOT EXISTS idx_kg_b ON knowledge_graph (fact_id_b);

CREATE TABLE IF NOT EXISTS consolidation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_ts REAL NOT NULL,
    facts_promoted INTEGER NOT NULL DEFAULT 0,
    facts_decayed INTEGER NOT NULL DEFAULT 0,
    facts_archived INTEGER NOT NULL DEFAULT 0,
    skills_updated INTEGER NOT NULL DEFAULT 0,
    edges_created INTEGER NOT NULL DEFAULT 0,
    dry_run INTEGER NOT NULL DEFAULT 0,
    note TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def _split_statements(sql: str) -> List[str]:
    """Naïve ``;``-split that drops SQL line comments and empty fragments.

    Acceptable here because the schema holds only DDL (CREATE TABLE /
    CREATE INDEX). Mirrors :mod:`tank_learn.feedback_store` exactly.
    """
    fragments: List[str] = []
    for raw in sql.split(";"):
        kept: List[str] = []
        for line in raw.splitlines():
            if line.lstrip().startswith("--"):
                continue
            kept.append(line)
        cleaned = "\n".join(kept).strip()
        if cleaned:
            fragments.append(cleaned)
    return fragments


_SCHEMA_STATEMENTS: List[str] = _split_statements(SCHEMA)


# ---------------------------------------------------------------------------
# Module-level aliases — canonical owner is the MemoryStore class, but the
# class attributes are exposed here too so callers and tests can write
# ``from .memory_store import CONFIDENCE_FLOOR`` without first importing
# the class. Mirrors the symmetry in :mod:`tank_learn.feedback_store`
# where helpers are at module level.
# ---------------------------------------------------------------------------
CONFIDENCE_FLOOR = 0.05
SKILL_MIN_PROFICIENCY = 0.05
EPISODIC_PROMOTE_MIN_MENTIONS = 3
EPISODIC_PROMOTE_MIN_SOURCES = 2
EPISODIC_PROMOTE_WINDOW_DAYS = 7
PROMOTION_CONFIDENCE = 0.5
FORGET_DECAY_TAU_DAYS = 14.0
SKILL_ALPHA_PRIOR = 1
SKILL_BETA_PRIOR = 1


# ---------------------------------------------------------------------------
# MemoryStore
# ---------------------------------------------------------------------------
class MemoryStore:
    """Hermetic SQLite-WAL long-term memory store.

    Public entry points (Phase 3 v1):

    * :meth:`record_episode`       — append an episodic event (dedup-safe)
    * :meth:`recent_episodes`      — paginated read of episodes
    * :meth:`upsert_fact`          — insert-or-update a semantic fact
    * :meth:`bump_fact_recall`     — mark a fact was just used (no decay tick)
    * :meth:`apply_fact_decay`     — multiply confidence by exp(-dt/tau)
    * :meth:`archive_stale_facts`  — soft-delete noise
    * :meth:`facts`                — paginated read of facts
    * :meth:`update_skill`         — Bayesian Beta-binomial bump on use
    * :meth:`skills`               — paginated read of skills
    * :meth:`add_edge`             — upsert a knowledge-graph edge
    * :meth:`edges`                — paginated read of edges
    * :meth:`record_consolidation` — append a consolidation audit row
    * :meth:`latest_consolidation` — read the most recent audit row
    """

    # ----- promotion thresholds (also used by consolidation.py) -----------
    EPISODIC_PROMOTE_MIN_MENTIONS = 3     # ≥ N episodes in window
    EPISODIC_PROMOTE_MIN_SOURCES = 2      # ≥ N distinct sources or distinct days
    EPISODIC_PROMOTE_WINDOW_DAYS = 7
    PROMOTION_CONFIDENCE = 0.5            # initial confidence for promoted facts

    # ----- Ebbinghaus decay ------------------------------------------------
    FORGET_DECAY_TAU_DAYS = 14.0         # half-life = tau * ln(2)
    CONFIDENCE_FLOOR = 0.05

    # ----- Bayesian skill priors (Beta-binomial) ---------------------------
    SKILL_ALPHA_PRIOR = 1
    SKILL_BETA_PRIOR = 1
    SKILL_MIN_PROFICIENCY = 0.05

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._db_path = str(db_path or DEFAULT_DB_PATH)
        parent = Path(self._db_path).parent
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass  # ":memory:" or read-only mounts.
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(
            self._db_path,
            timeout=10.0,
            check_same_thread=False,
            isolation_level=None,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        with self._lock:
            self._init_schema()

    # ── internal helpers ──────────────────────────────────────────────────
    def _init_schema(self) -> None:
        for stmt in _SCHEMA_STATEMENTS:
            self._conn.execute(stmt)
        self._conn.execute(
            "INSERT OR REPLACE INTO schema_meta (key, value) VALUES (?, ?)",
            ("schema_version", str(SCHEMA_VERSION)),
        )

    def close(self) -> None:
        """Idempotent close — detach before calling so ProgrammingError is silent."""
        with self._lock:
            conn, self._conn = self._conn, None
        if conn is not None:
            try:
                conn.close()
            except sqlite3.ProgrammingError:
                pass

    def __enter__(self) -> "MemoryStore":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    @property
    def db_path(self) -> str:
        return self._db_path

    @property
    def schema_version(self) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT value FROM schema_meta WHERE key = 'schema_version'"
            ).fetchone()
        return int(row["value"]) if row else 0

    # ── episodes ───────────────────────────────────────────────────────────
    def record_episode(
        self,
        source: str,
        content: str,
        *,
        ts: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        dedupe_key: str = "",
    ) -> int:
        """Append one episodic event. ``dedupe_key`` makes the insert idempotent
        when set (e.g., ``"hf.summary:mistral-7b-rag"``), so re-running the
        ingest bridge from an already-processed ``DiscoverySummary`` adds zero
        new rows.

        Returns the new row id; returns ``0`` if a row with the same
        ``dedupe_key`` already exists (silent no-op so callers don't have
        to catch :class:`sqlite3.IntegrityError` on hot ingestion loops).
        """
        ts = float(ts if ts is not None else time.time())
        meta_json = json.dumps(metadata or {}, sort_keys=True)
        try:
            with self._lock:
                cur = self._conn.execute(
                    "INSERT INTO episodes (source, content, ts, metadata_json, dedupe_key)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (
                        (source or "")[:32],
                        (content or "")[:2000],
                        ts,
                        meta_json,
                        dedupe_key[:200],
                    ),
                )
                return int(cur.lastrowid or 0)
        except sqlite3.IntegrityError:
            # Partial UNIQUE index on dedupe_key triggered — duplicate.
            return 0

    def recent_episodes(
        self,
        *,
        since_ts: Optional[float] = None,
        source: Optional[str] = None,
        limit: int = 100,
    ) -> List[Episode]:
        limit = max(1, min(int(limit), 2000))
        sql = "SELECT id, source, content, ts, metadata_json, dedupe_key FROM episodes"
        args: List[Any] = []
        clauses: List[str] = []
        if since_ts is not None:
            clauses.append("ts >= ?")
            args.append(float(since_ts))
        if source:
            clauses.append("source = ?")
            args.append(source)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY ts DESC LIMIT ?"
        args.append(limit)
        with self._lock:
            rows = self._conn.execute(sql, args).fetchall()
        out: List[Episode] = []
        for r in rows:
            try:
                meta = json.loads(r["metadata_json"])
            except (TypeError, ValueError):
                meta = {}
            out.append(Episode(
                id=int(r["id"]),
                source=str(r["source"]),
                content=str(r["content"]),
                ts=float(r["ts"]),
                dedupe_key=str(r["dedupe_key"] or ""),
                metadata=meta if isinstance(meta, dict) else {},
            ))
        return out

    # ── semantic facts ─────────────────────────────────────────────────────
    def upsert_fact(
        self,
        concept: str,
        definition: str,
        *,
        confidence: Optional[float] = None,
        ts: Optional[float] = None,
    ) -> int:
        """Insert-or-touch a semantic fact. Returns its row id.

        On conflict (``UNIQUE(concept)``), ``mention_count`` is bumped,
        ``last_recalled_ts`` is refreshed, and (if ``confidence`` is provided)
        the value is updated to ``max(current, new)`` so ingestion can only
        LIFT confidence, never silently lower it.
        """
        concept_norm = (concept or "").strip().lower()[:200]
        if not concept_norm:
            raise ValueError("concept is required")
        if confidence is not None and not (
            self.CONFIDENCE_FLOOR <= float(confidence) <= 1.0
        ):
            raise ValueError(
                f"confidence must be in [{self.CONFIDENCE_FLOOR}, 1.0]"
            )
        now = float(ts if ts is not None else time.time())
        new_conf = float(confidence) if confidence is not None else self.PROMOTION_CONFIDENCE
        with self._lock:
            row = self._conn.execute(
                "SELECT id FROM semantic_facts WHERE concept = ?",
                (concept_norm,),
            ).fetchone()
            if row is None:
                cur = self._conn.execute(
                    "INSERT INTO semantic_facts"
                    " (concept, definition, confidence, first_learned_ts,"
                    "  last_recalled_ts, status, mention_count)"
                    " VALUES (?, ?, ?, ?, ?, ?, 1)",
                    (
                        concept_norm,
                        (definition or "")[:1000],
                        new_conf,
                        now,
                        now,
                        "shallow",
                    ),
                )
                return int(cur.lastrowid or 0)
            fid = int(row["id"])
            # Bump mention_count + last_recalled_ts; lift confidence (no lower).
            self._conn.execute(
                """
                UPDATE semantic_facts
                SET mention_count = mention_count + 1,
                    last_recalled_ts = ?,
                    confidence = MAX(confidence, ?),
                    status = CASE
                        WHEN status = 'archived' THEN 'consolidated'
                        ELSE status
                    END,
                    definition = CASE
                        WHEN length(definition) < length(?)
                            THEN ?
                        ELSE definition
                    END
                WHERE id = ?
                """,
                (now, new_conf, definition or "", definition or "", fid),
            )
            return fid

    def bump_fact_recall(self, concept: str,
                         *, ts: Optional[float] = None) -> bool:
        """Touch a fact's ``last_recalled_ts`` + bump ``mention_count``."""
        concept_norm = (concept or "").strip().lower()[:200]
        now = float(ts if ts is not None else time.time())
        with self._lock:
            cur = self._conn.execute(
                "UPDATE semantic_facts SET last_recalled_ts = ?,"
                " mention_count = mention_count + 1"
                " WHERE concept = ? AND status <> 'archived'",
                (now, concept_norm),
            )
            return cur.rowcount > 0

    def apply_fact_decay(self, *, now_ts: Optional[float] = None,
                         tau_days: Optional[float] = None) -> int:
        """Multiply every non-archived fact's confidence by ``exp(-dt/tau)``
        where ``dt`` is days since ``last_recalled_ts``. Returns count of
        rows touched.

        Implemented in Python (not SQL) because core SQLite (before 3.35 +
        the math extension) does not ship :func:`math.exp`. The Python loop
        is bounded by the active fact count (<=5000 per dashboard tile)
        so the round-trip cost is negligible on Pi 5.
        """
        import math as _math
        tau = float(tau_days if tau_days is not None else self.FORGET_DECAY_TAU_DAYS)
        now = float(now_ts if now_ts is not None else time.time())
        if tau <= 0.0:
            raise ValueError("tau_days must be > 0")
        seconds_per_day = 86400.0
        # Pull all non-archived facts with the columns we need for the math.
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, confidence, last_recalled_ts"
                " FROM semantic_facts WHERE status <> 'archived'"
            ).fetchall()
            if not rows:
                return 0
            # Per-row decay + targeted UPDATE inside the lock so writers
            # see a consistent snapshot. The 1e-9 epsilon below avoids
            # writing rows whose decayed confidence already sits at floor.
            touched = 0
            for r in rows:
                dt = max(0.0, (now - float(r["last_recalled_ts"])) / seconds_per_day)
                new_conf = max(
                    self.CONFIDENCE_FLOOR,
                    float(r["confidence"]) * _math.exp(-dt / tau),
                )
                # Skip row if the floor already caps it AND the math didn't
                # move the value by more than 1e-9 (avoids pointless writes).
                if abs(new_conf - float(r["confidence"])) < 1e-9:
                    continue
                self._conn.execute(
                    "UPDATE semantic_facts SET confidence = ? WHERE id = ?",
                    (new_conf, int(r["id"])),
                )
                touched += 1
        return touched

    def archive_stale_facts(self, *, now_ts: Optional[float] = None,
                            stale_days: float = 90.0) -> int:
        now = float(now_ts if now_ts is not None else time.time())
        threshold = now - stale_days * 86400.0
        with self._lock:
            cur = self._conn.execute(
                "UPDATE semantic_facts SET status = 'archived'"
                " WHERE status <> 'archived'"
                "   AND confidence <= ?"
                "   AND last_recalled_ts < ?",
                (self.CONFIDENCE_FLOOR, threshold),
            )
            return int(cur.rowcount or 0)

    def facts(self, *, min_confidence: float = CONFIDENCE_FLOOR,
              status: Optional[str] = None,
              limit: int = 500) -> List[SemanticFact]:
        sql = "SELECT * FROM semantic_facts WHERE confidence >= ?"
        args: List[Any] = [float(min_confidence)]
        if status:
            sql += " AND status = ?"
            args.append(status)
        sql += " ORDER BY confidence DESC, mention_count DESC LIMIT ?"
        args.append(max(1, min(int(limit), 5000)))
        with self._lock:
            rows = self._conn.execute(sql, args).fetchall()
        return [self._row_to_fact(r) for r in rows]

    @staticmethod
    def _row_to_fact(r: sqlite3.Row) -> SemanticFact:
        return SemanticFact(
            id=int(r["id"]),
            concept=str(r["concept"]),
            definition=str(r["definition"] or ""),
            confidence=float(r["confidence"]),
            first_learned_ts=float(r["first_learned_ts"]),
            last_recalled_ts=float(r["last_recalled_ts"]),
            status=str(r["status"]),
            mention_count=int(r["mention_count"]),
        )

    # ── skills ─────────────────────────────────────────────────────────────
    def update_skill(self, ability_name: str, *, success: bool,
                     ts: Optional[float] = None) -> int:
        """Bayesian Beta-binomial bump on one skill use.

        success=True  → +1 to alpha (proficiency rises toward 1.0)
        success=False → +1 to beta  (proficiency drops toward 0.0)

        Idempotent for repeated invocations: the row exists, only counts change.
        Returns the row id.
        """
        ability_norm = (ability_name or "").strip().lower()[:200]
        if not ability_norm:
            raise ValueError("ability_name is required")
        now = float(ts if ts is not None else time.time())
        da = 1 if success else 0
        db = 0 if success else 1
        with self._lock:
            row = self._conn.execute(
                "SELECT id FROM skills WHERE ability_name = ?",
                (ability_norm,),
            ).fetchone()
            if row is None:
                cur = self._conn.execute(
                    "INSERT INTO skills (ability_name, proficiency, alpha,"
                    " beta, last_use_ts, use_count)"
                    " VALUES (?, ?, ?, ?, ?, 1)",
                    (
                        ability_norm,
                        self.SKILL_ALPHA_PRIOR / (
                            self.SKILL_ALPHA_PRIOR + self.SKILL_BETA_PRIOR),
                        self.SKILL_ALPHA_PRIOR + da,
                        self.SKILL_BETA_PRIOR + db,
                        now,
                    ),
                )
                return int(cur.lastrowid or 0)
            sid = int(row["id"])
            self._conn.execute(
                """
                UPDATE skills
                SET alpha = alpha + ?,
                    beta = beta + ?,
                    last_use_ts = ?,
                    use_count = use_count + 1,
                    proficiency = MAX(?, CAST(alpha + ? AS REAL)
                                       / (alpha + ? + beta + ?))
                WHERE id = ?
                """,
                (
                    da, db, now, self.SKILL_MIN_PROFICIENCY,
                    da, da, db, sid,
                ),
            )
            return sid

    def skills(self, *, min_proficiency: float = SKILL_MIN_PROFICIENCY,
               limit: int = 200) -> List[Skill]:
        sql = ("SELECT id, ability_name, proficiency, alpha, beta,"
               " last_use_ts, use_count FROM skills"
               " WHERE proficiency >= ?"
               " ORDER BY proficiency DESC, use_count DESC LIMIT ?")
        args = [float(min_proficiency), max(1, min(int(limit), 5000))]
        with self._lock:
            rows = self._conn.execute(sql, args).fetchall()
        return [
            Skill(
                id=int(r["id"]),
                ability_name=str(r["ability_name"]),
                proficiency=float(r["proficiency"]),
                alpha=int(r["alpha"]),
                beta=int(r["beta"]),
                last_use_ts=float(r["last_use_ts"]),
                use_count=int(r["use_count"]),
            )
            for r in rows
        ]

    # ── knowledge-graph edges ──────────────────────────────────────────────
    def add_edge(self, fact_id_a: int, fact_id_b: int,
                 relationship: str = "related",
                 strength: float = 0.5) -> int:
        """Upsert (a, b, relationship) → strength is lifted to MAX."""
        if fact_id_a == fact_id_b:
            return 0  # self-loops are noise; refuse.
        s = max(0.0, min(1.0, float(strength)))
        with self._lock:
            row = self._conn.execute(
                "SELECT id FROM knowledge_graph"
                " WHERE fact_id_a = ? AND fact_id_b = ? AND relationship = ?",
                (int(fact_id_a), int(fact_id_b), relationship),
            ).fetchone()
            if row is not None:
                self._conn.execute(
                    "UPDATE knowledge_graph SET strength = MAX(strength, ?)"
                    " WHERE id = ?",
                    (s, int(row["id"])),
                )
                return int(row["id"])
            cur = self._conn.execute(
                "INSERT INTO knowledge_graph"
                " (fact_id_a, fact_id_b, relationship, strength)"
                " VALUES (?, ?, ?, ?)",
                (int(fact_id_a), int(fact_id_b), relationship, s),
            )
            return int(cur.lastrowid or 0)

    def edges(self, *, min_strength: float = 0.0,
              limit: int = 500) -> List[FactEdge]:
        sql = ("SELECT id, fact_id_a, fact_id_b, relationship, strength"
               " FROM knowledge_graph WHERE strength >= ?"
               " ORDER BY strength DESC LIMIT ?")
        args = [float(min_strength), max(1, min(int(limit), 5000))]
        with self._lock:
            rows = self._conn.execute(sql, args).fetchall()
        return [
            FactEdge(
                id=int(r["id"]),
                fact_id_a=int(r["fact_id_a"]),
                fact_id_b=int(r["fact_id_b"]),
                relationship=str(r["relationship"]),
                strength=float(r["strength"]),
            )
            for r in rows
        ]

    # ── consolidation log ──────────────────────────────────────────────────
    def record_consolidation(self, *, now_ts: Optional[float] = None,
                             facts_promoted: int = 0,
                             facts_decayed: int = 0,
                             facts_archived: int = 0,
                             skills_updated: int = 0,
                             edges_created: int = 0,
                             dry_run: bool = False,
                             note: str = "") -> int:
        now = float(now_ts if now_ts is not None else time.time())
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO consolidation_log"
                " (run_ts, facts_promoted, facts_decayed, facts_archived,"
                "  skills_updated, edges_created, dry_run, note)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    now, int(facts_promoted), int(facts_decayed),
                    int(facts_archived), int(skills_updated),
                    int(edges_created), 1 if dry_run else 0,
                    (note or "")[:500],
                ),
            )
            return int(cur.lastrowid or 0)

    def latest_consolidation(self) -> Optional[ConsolidationRecord]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM consolidation_log ORDER BY run_ts DESC LIMIT 1"
            ).fetchone()
        if row is None:
            return None
        return ConsolidationRecord(
            id=int(row["id"]),
            run_ts=float(row["run_ts"]),
            facts_promoted=int(row["facts_promoted"]),
            facts_decayed=int(row["facts_decayed"]),
            facts_archived=int(row["facts_archived"]),
            skills_updated=int(row["skills_updated"]),
            edges_created=int(row["edges_created"]),
            dry_run=bool(row["dry_run"]),
            note=str(row["note"]),
        )

    # ── bulk export for recall ranker ──────────────────────────────────────
    def recall_candidates(self, *, include_archived: bool = False
                          ) -> Tuple[List[SemanticFact], List[Skill]]:
        """Pull the active fact+skill corpus for the recaller in one shot.

        Returning both lists lets the ranker score ``tier=all`` queries in a
        single pass and apply tier filters cheaply (a Python-side filter is
        ~µs on 10⁴ rows).
        """
        f_status = "" if include_archived else " AND status <> 'archived'"
        with self._lock:
            fact_rows = self._conn.execute(
                "SELECT * FROM semantic_facts WHERE 1=1" + f_status
                + " ORDER BY confidence DESC LIMIT 5000"
            ).fetchall()
            skill_rows = self._conn.execute(
                "SELECT id, ability_name, proficiency, alpha, beta,"
                " last_use_ts, use_count FROM skills"
                " WHERE proficiency >= ?"
                " ORDER BY proficiency DESC LIMIT 1000",
                (self.SKILL_MIN_PROFICIENCY,),
            ).fetchall()
        return (
            [self._row_to_fact(r) for r in fact_rows],
            [
                Skill(
                    id=int(r["id"]),
                    ability_name=str(r["ability_name"]),
                    proficiency=float(r["proficiency"]),
                    alpha=int(r["alpha"]),
                    beta=int(r["beta"]),
                    last_use_ts=float(r["last_use_ts"]),
                    use_count=int(r["use_count"]),
                )
                for r in skill_rows
            ],
        )


__all__ = [
    "DEFAULT_DB_PATH",
    "SCHEMA_VERSION",
    "Episode", "SemanticFact", "Skill", "FactEdge", "ConsolidationRecord",
    "MemoryStore",
]
