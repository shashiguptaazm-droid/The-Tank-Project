#!/usr/bin/env python3
"""tank_learn.scripts.teach — operator manual-feed CLI.

Examples
========
Teach an episode (raw event with provenance)::
    python3 -m tank_learn.scripts.teach \\
        --kind episode \\
        --source user_teach \\
        --content "Mistral-7B-RAG was published on HuggingFace today."

Teach a semantic fact (will be UPSERTed; bumped confidence on repeat)::
    python3 -m tank_learn.scripts.teach \\
        --kind fact \\
        --concept rag \\
        --definition "Retrieval-augmented generation: inject retrieved docs into LLM context." \\
        --confidence 0.70

Teach an ability (skill) with explicit priors::
    python3 -m tank_learn.scripts.teach \\
        --kind skill \\
        --ability answer_torrents_questions \\
        --alpha 4 --beta 1

Mark a SUCCESSFUL use of an existing skill (Bayesian bump)::
    python3 -m tank_learn.scripts.teach --kind use \\
        --ability answer_torrents_questions --success

Batch import from a JSON file (one record per line, JSONL)::
    python3 -m tank_learn.scripts.teach --jsonl teach.jsonl

Each JSONL row is one of::

    {"kind": "episode", "source": "...", "content": "...", "ts": 1234567890.0, "metadata": {...}}
    {"kind": "fact", "concept": "rag", "definition": "...", "confidence": 0.7, "ts": ...}
    {"kind": "skill", "ability": "...", "alpha": 2, "beta": 1, "ts": ...}
    {"kind": "use", "ability": "...", "success": true, "ts": ...}
    {"kind": "module", "source": "huggingface",
     "name": "mistral-7b-rag", "url": "...", "summary": "...",
     "capabilities": ["text-generation", "retrieval"]}
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from ..discovery_store import ModuleRecord
from ..ingest import ingest_module
from ..memory_store import (
    DEFAULT_DB_PATH,
    CONFIDENCE_FLOOR,
    MemoryStore,
    SKILL_ALPHA_PRIOR,
    SKILL_BETA_PRIOR,
    Skill,
)


def _open_store(args: argparse.Namespace) -> MemoryStore:
    return MemoryStore(db_path=args.db)


def _cmd_episode(store: MemoryStore, args: argparse.Namespace) -> int:
    if not args.content:
        print("ERROR: --content is required for --kind episode",
              file=sys.stderr)
        return 2
    eid = store.record_episode(
        source=(args.source or "user_teach")[:32],
        content=args.content[:2000],
        ts=args.ts or time.time(),
        metadata=_parse_kv(args.metadata),
        dedupe_key=(args.dedupe_key or "")[:200],
    )
    print(json.dumps({"_ok": True, "episode_id": eid,
                      "kind": "episode"}))
    return 0


def _cmd_fact(store: MemoryStore, args: argparse.Namespace) -> int:
    if not args.concept:
        print("ERROR: --concept is required for --kind fact", file=sys.stderr)
        return 2
    fid = store.upsert_fact(
        args.concept.strip().lower(),
        args.definition or "",
        confidence=(args.confidence if args.confidence is not None
                     else None),
        ts=args.ts or time.time(),
    )
    print(json.dumps({
        "_ok": True, "fact_id": fid, "kind": "fact",
        "concept": args.concept.strip().lower(),
    }))
    return 0


def _cmd_skill(store: MemoryStore, args: argparse.Namespace) -> int:
    if not args.ability:
        print("ERROR: --ability is required for --kind skill",
              file=sys.stderr)
        return 2
    a = args.alpha if args.alpha is not None else SKILL_ALPHA_PRIOR
    b = args.beta if args.beta is not None else SKILL_BETA_PRIOR
    now = args.ts or time.time()
    ability_norm = (args.ability or "").strip().lower()
    # Insert-or-touch: bump last_use_ts to mark "operator declared this".
    existing = [s for s in store.skills(min_proficiency=0.0,
                                        limit=10_000)
                if s.ability_name == ability_norm]
    if existing:
        store.update_skill(ability_norm, success=True, ts=now)
        print(json.dumps({
            "_ok": True, "skill_id": existing[0].id, "kind": "skill",
            "ability": ability_norm,
            "status": "refreshed",
        }))
        return 0
    # Fresh.
    import sqlite3
    with store._lock:  # type: ignore[attr-defined]
        cur = store._conn.execute(  # type: ignore[attr-defined]
            "INSERT INTO skills (ability_name, proficiency, alpha, beta,"
            " last_use_ts, use_count) VALUES (?, ?, ?, ?, ?, 0)",
            (ability_norm, a / (a + b), a, b, now),
        )
        sid = int(cur.lastrowid or 0)
    print(json.dumps({
        "_ok": True, "skill_id": sid, "kind": "skill",
        "ability": ability_norm,
        "alpha": a, "beta": b,
        "starting_proficiency": round(a / (a + b), 4),
    }))
    return 0


def _cmd_use(store: MemoryStore, args: argparse.Namespace) -> int:
    if not args.ability:
        print("ERROR: --ability is required for --kind use", file=sys.stderr)
        return 2
    sid = store.update_skill(
        args.ability.strip().lower(), success=bool(args.success),
        ts=args.ts or time.time(),
    )
    skill_rows = [s for s in store.skills(min_proficiency=0.0, limit=10_000)
                  if s.ability_name == args.ability.strip().lower()]
    prof = skill_rows[0].proficiency if skill_rows else None
    print(json.dumps({
        "_ok": True, "skill_id": sid, "kind": "use",
        "ability": args.ability.strip().lower(),
        "success": bool(args.success),
        "proficiency_after": prof,
    }))
    return 0


def _cmd_module(store: MemoryStore, args: argparse.Namespace) -> int:
    if not args.module_name:
        print("ERROR: --module-name is required for --kind module",
              file=sys.stderr)
        return 2
    caps: List[str] = []
    if args.capabilities:
        caps = [c.strip().lower() for c in args.capabilities.split(",")
                if c.strip()]
    rec = ModuleRecord(
        source=(args.module_source or "user_teach"),
        name=args.module_name,
        url=args.module_url or "",
        summary=args.module_summary or "",
        capabilities=caps,
    )
    res = ingest_module(store, rec,
                        now_ts=args.ts or time.time(),
                        source_label="user_teach")
    print(json.dumps({"_ok": True, "kind": "module", **res.to_dict()}))
    return 0


def _cmd_jsonl(store: MemoryStore, args: argparse.Namespace) -> int:
    path = Path(args.jsonl)
    if not path.is_file():
        print(f"ERROR: jsonl file not found: {path}", file=sys.stderr)
        return 2
    n = 0
    ok = 0
    with path.open("r", encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw or raw.startswith("#"):
                continue
            try:
                row = json.loads(raw)
            except ValueError:
                print(f"ERROR: invalid JSON on line {n + 1}",
                      file=sys.stderr)
                return 3
            kind = str(row.get("kind", "")).lower().strip()
            n += 1
            if kind == "episode":
                eid = store.record_episode(
                    source=(row.get("source") or "user_teach")[:32],
                    content=(row.get("content") or "")[:2000],
                    ts=row.get("ts") or time.time(),
                    metadata=row.get("metadata") or {},
                    dedupe_key=(row.get("dedupe_key") or "")[:200],
                )
                if eid: ok += 1
            elif kind == "fact":
                fid = store.upsert_fact(
                    (row.get("concept") or "").strip().lower(),
                    row.get("definition") or "",
                    confidence=row.get("confidence"),
                    ts=row.get("ts") or time.time(),
                )
                if fid: ok += 1
            elif kind == "skill":
                a = row.get("alpha") or SKILL_ALPHA_PRIOR
                b = row.get("beta") or SKILL_BETA_PRIOR
                nm = (row.get("ability") or "").strip().lower()
                ts = row.get("ts") or time.time()
                if not nm: continue
                with store._lock:  # type: ignore[attr-defined]
                    cur = store._conn.execute(  # type: ignore[attr-defined]
                        "INSERT OR IGNORE INTO skills"
                        " (ability_name, proficiency, alpha, beta,"
                        " last_use_ts, use_count)"
                        " VALUES (?, ?, ?, ?, ?, 0)",
                        (nm, a/(a+b), a, b, ts),
                    )
                    if cur.lastrowid: ok += 1
            elif kind == "use":
                ab = (row.get("ability") or "").strip().lower()
                if not ab: continue
                try:
                    if store.update_skill(
                        ab, success=bool(row.get("success", True)),
                        ts=row.get("ts") or time.time(),
                    ):
                        ok += 1
                except ValueError:
                    continue
            elif kind == "module":
                rec = ModuleRecord(
                    source=row.get("source") or "user_teach",
                    name=row.get("name") or "",
                    url=row.get("url") or "",
                    summary=row.get("summary") or "",
                    capabilities=row.get("capabilities") or [],
                )
                if not rec.name: continue
                res = ingest_module(store, rec,
                                    now_ts=row.get("ts") or time.time(),
                                    source_label="user_teach")
                if res.episodes_added: ok += 1
            else:
                print(f"WARN: unknown kind on line {n}: {kind!r}",
                      file=sys.stderr)
    print(json.dumps({"_ok": True, "kind": "jsonl", "rows": n,
                      "applied": ok}))
    return 0


def _parse_kv(arg: str) -> Dict[str, Any]:
    """Parse ``key=value,key2=value2`` into a dict. Naïve but hermetic."""
    if not arg:
        return {}
    out: Dict[str, Any] = {}
    for pair in arg.split(","):
        if "=" not in pair:
            continue
        k, v = pair.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Manually teach episodes / facts / skills to The Tank.",
    )
    parser.add_argument("--db", default=DEFAULT_DB_PATH,
                        help="Path to the memory SQLite DB.")
    parser.add_argument("--kind", required=False,
                        choices=["episode", "fact", "skill", "use",
                                 "module", "jsonl"],
                        help="What to teach.")
    # Common
    parser.add_argument("--source", default="user_teach",
                        help="Episode source label.")
    parser.add_argument("--content", default="",
                        help="Episode content.")
    parser.add_argument("--ts", type=float, default=None,
                        help="Override timestamp (epoch seconds).")
    parser.add_argument("--metadata", default="",
                        help="Episode metadata as 'k=v,k=v'.")
    parser.add_argument("--dedupe-key", default="",
                        help="Episode dedupe key for idempotency.")
    # Fact
    parser.add_argument("--concept", default="")
    parser.add_argument("--definition", default="")
    parser.add_argument("--confidence", type=float, default=None,
                        help=f"Confidence in [{CONFIDENCE_FLOOR}, 1.0].")
    # Skill
    parser.add_argument("--ability", default="")
    parser.add_argument("--alpha", type=int, default=None)
    parser.add_argument("--beta", type=int, default=None)
    # Use (skill invocation record)
    parser.add_argument("--success", action="store_true",
                        help="Mark a successful skill use.")
    # Module
    parser.add_argument("--module-name", default="")
    parser.add_argument("--module-source", default="")
    parser.add_argument("--module-url", default="")
    parser.add_argument("--module-summary", default="")
    parser.add_argument("--capabilities", default="",
                        help="Comma-separated capability tokens.")
    # JSONL batch
    parser.add_argument("--jsonl", default="",
                        help="Path to a JSONL batch file.")
    args = parser.parse_args(argv)
    if not args.kind:
        parser.print_help(sys.stderr)
        return 1
    store = _open_store(args)
    try:
        if args.kind == "episode":   return _cmd_episode(store, args)
        if args.kind == "fact":      return _cmd_fact(store, args)
        if args.kind == "skill":     return _cmd_skill(store, args)
        if args.kind == "use":       return _cmd_use(store, args)
        if args.kind == "module":    return _cmd_module(store, args)
        if args.kind == "jsonl":     return _cmd_jsonl(store, args)
        return 1
    finally:
        store.close()


if __name__ == "__main__":
    sys.exit(main())
