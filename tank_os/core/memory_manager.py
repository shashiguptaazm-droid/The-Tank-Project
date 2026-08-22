"""TankOS Memory Manager — conversations, vector embeddings, episodic memory, recall."""

from __future__ import annotations
import json, logging, threading, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from tank_os.core.event_bus import Event, EventBus


@dataclass
class MemoryEntry:
    id: str; content: str; memory_type: str = "episodic"  # episodic, semantic, procedural
    ts: float = 0.0; source: str = ""; tags: List[str] = field(default_factory=list)
    embedding: Optional[List[float]] = None


class MemoryManager:
    _instance: Optional["MemoryManager"] = None; _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._bus = EventBus()
                cls._instance._entries: List[MemoryEntry] = []
                cls._instance._store_path = Path.home() / ".config" / "tank_os" / "memory.jsonl"
                cls._instance._sentence_transformers = False
            return cls._instance

    def initialize(self) -> None:
        self._load()
        self._check_embeddings()
        logger.info("MemoryManager initialized (%d entries)", len(self._entries))

    def _check_embeddings(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer  # noqa: F401
            self._sentence_transformers = True
        except ImportError:
            self._sentence_transformers = False

    def _load(self) -> None:
        if self._store_path.exists():
            for line in self._store_path.read_text().splitlines():
                try:
                    data = json.loads(line)
                    self._entries.append(MemoryEntry(**data))
                except Exception: pass

    def _save(self) -> None:
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [json.dumps({"id": e.id, "content": e.content, "memory_type": e.memory_type,
                            "ts": e.ts, "source": e.source, "tags": e.tags})
                for e in self._entries[-500:]]
        self._store_path.write_text("\n".join(lines))

    def store(self, content: str, memory_type: str = "episodic",
              source: str = "", tags: Optional[List[str]] = None) -> MemoryEntry:
        import uuid
        entry = MemoryEntry(
            id=str(uuid.uuid4())[:8], content=content,
            memory_type=memory_type, ts=time.time(),
            source=source, tags=tags or [],
        )
        self._entries.append(entry)
        self._save()
        self._bus.emit(Event("memory_stored", {"id": entry.id, "type": memory_type}))
        return entry

    def recall(self, query: str = "", limit: int = 10) -> List[MemoryEntry]:
        if not query:
            return sorted(self._entries, key=lambda e: e.ts, reverse=True)[:limit]
        tokens = query.lower().split()
        scored = []
        for e in self._entries:
            score = sum(1 for t in tokens if t in e.content.lower())
            if score > 0:
                scored.append((score, e))
        scored.sort(key=lambda x: -x[0])
        return [e for _, e in scored[:limit]]

    def search_vector(self, query: str, limit: int = 5) -> List[MemoryEntry]:
        if not self._sentence_transformers:
            return self.recall(query, limit)
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer("all-MiniLM-L6-v2")
            q_vec = model.encode(query)
            scored = []
            for e in self._entries:
                if e.content:
                    e_vec = model.encode(e.content[:512])
                    import numpy as np
                    score = float(np.dot(q_vec, e_vec) / (np.linalg.norm(q_vec) * np.linalg.norm(e_vec) + 1e-10))
                    scored.append((score, e))
            scored.sort(key=lambda x: -x[0])
            return [e for _, e in scored[:limit]]
        except Exception: return self.recall(query, limit)

    def clear(self) -> None:
        self._entries.clear()
        if self._store_path.exists(): self._store_path.unlink()
        self._bus.emit(Event("memory_cleared", {}))

    @property
    def count(self) -> int: return len(self._entries)
    @property
    def types(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for e in self._entries: counts[e.memory_type] = counts.get(e.memory_type, 0) + 1
        return counts


logger = logging.getLogger("tank_os.memory_manager")
