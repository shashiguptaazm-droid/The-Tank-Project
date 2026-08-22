"""TankOS Knowledge Graph — entity relationship graph for intelligent context.

Connects people, places, objects, tasks, memories, and concepts into a
rich relationship graph that enables contextual reasoning. The graph is
automatically populated from experiences, conversations, and sensor data.

Features:
- Entity types: person, place, object, concept, task, device, memory, event
- Relationship types: located_in, used_for, related_to, part_of, followed_by,
  contains, owned_by, created_by, similar_to, opposite_of
- Automatic entity extraction from text and sensor data
- Graph queries: neighbors, paths, subgraphs, communities
- Importance-based decay (forgetting) of weak connections
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from tank_os.core.event_bus import Event, EventBus, Priority

logger = logging.getLogger("tank_os.ai.knowledge_graph")

# ── Constants ───────────────────────────────────────────────────────────

DEFAULT_STORE_PATH = Path.home() / ".config" / "tank_os" / "knowledge_graph.json"
MAX_ENTITIES = 5000
MAX_RELATIONSHIPS = 20000
ENTITY_DECAY_DAYS = 90  # Entities unseen for 90 days lose strength
RELATIONSHIP_DECAY_DAYS = 60


# ── Data Models ─────────────────────────────────────────────────────────

@dataclass
class Entity:
    """A node in the knowledge graph."""

    id: str
    name: str
    entity_type: str  # "person", "place", "object", "concept", "task", "device", "memory", "event"
    aliases: List[str] = field(default_factory=list)
    description: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    strength: float = 1.0       # 0.0-1.0, decays over time
    first_seen: float = 0.0
    last_seen: float = 0.0
    times_encountered: int = 1
    source: str = ""            # How this entity was discovered


@dataclass
class Relationship:
    """An edge connecting two entities in the knowledge graph."""

    id: str
    source_id: str
    target_id: str
    relationship_type: str  # "located_in", "used_for", "related_to", "part_of",
                           # "followed_by", "contains", "owned_by", "created_by",
                           # "similar_to", "opposite_of", "interacted_with"
    strength: float = 1.0   # 0.0-1.0
    confidence: float = 1.0  # 0.0-1.0
    first_observed: float = 0.0
    last_observed: float = 0.0
    times_observed: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def reverse_type(self) -> str:
        """Get the reverse relationship type."""
        reverse_map = {
            "located_in": "contains",
            "contains": "located_in",
            "part_of": "has_part",
            "has_part": "part_of",
            "owned_by": "owns",
            "owns": "owned_by",
            "created_by": "created",
            "created": "created_by",
            "followed_by": "follows",
            "follows": "followed_by",
            "similar_to": "similar_to",
            "opposite_of": "opposite_of",
            "related_to": "related_to",
            "used_for": "used_by",
            "used_by": "used_for",
            "interacted_with": "interacted_with",
        }
        return reverse_map.get(self.relationship_type, "related_to")


@dataclass
class GraphQuery:
    """Result of a graph query."""

    entities: List[Entity] = field(default_factory=list)
    relationships: List[Relationship] = field(default_factory=list)
    paths: List[List[Dict[str, Any]]] = field(default_factory=list)
    confidence: float = 0.0


# ── Knowledge Graph Engine ──────────────────────────────────────────────

class KnowledgeGraph:
    """Entity relationship knowledge graph for contextual AI reasoning.

    Builds and maintains a graph of entities (people, places, objects, etc.)
    and their relationships. Used by the AI to understand context, make
    connections, and reason about the world.

    Usage:
        kg = KnowledgeGraph()
        kg.initialize()

        # Add entities
        kg.add_entity("person", "Alice", {"role": "owner"})
        kg.add_entity("place", "Living Room")
        kg.add_entity("object", "Charging Dock")

        # Add relationships
        kg.add_relationship("Alice", "Living Room", "located_in")
        kg.add_relationship("Charging Dock", "Living Room", "located_in")

        # Query
        result = kg.query("Alice")
        nearby = kg.get_neighbors("Living Room")
    """

    _instance: Optional["KnowledgeGraph"] = None
    _lock = threading.Lock()

    # ── Entity type recognition patterns ────────────────────────────
    TYPE_PATTERNS: Dict[str, List[str]] = {
        "person": [r"\\b(Mr|Mrs|Ms|Dr)\\.\\s+\\w+"],
        "place": [r"\\b(living|kitchen|bedroom|bathroom|garage|office"
                  r"|hallway|dining|basement|patio|deck|garden)",
                  r"\\b(room|area|zone|section)\\b"],
        "device": [r"\\b(camera|sensor|motor|servo|LIDAR|display|speaker"
                   r"|microphone|dock|charger|OLED|ESP32)\\b"],
        "object": [r"\\b(door|window|table|chair|sofa|shelf|box"
                    r"|cabinet|drawer|rug|lamp|plant|phone|book)\\b"],
        "concept": [r"\\b(safety|patrol|charge|dock|map|memory|learn"
                     r"|explore|follow|guard|record)\\b"],
    }

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._bus = EventBus()
                cls._instance._entities: Dict[str, Entity] = {}
                cls._instance._relationships: Dict[str, Relationship] = {}
                cls._instance._store_path: Path = DEFAULT_STORE_PATH
                cls._instance._name_to_id: Dict[str, str] = {}  # Fast lookup
                cls._instance._entity_by_type: Dict[str, List[str]] = {}
            return cls._instance

    def initialize(self, store_path: Optional[str] = None) -> None:
        """Load graph from disk and register EventBus listeners."""
        if store_path:
            self._store_path = Path(store_path)
        self._load()
        self._register_listeners()
        logger.info(
            "KnowledgeGraph initialized (%d entities, %d relationships)",
            len(self._entities), len(self._relationships),
        )

    def _load(self) -> None:
        """Load graph data from disk."""
        if not self._store_path.exists():
            return
        try:
            data = json.loads(self._store_path.read_text())
            for e_data in data.get("entities", []):
                entity = Entity(**e_data)
                self._entities[entity.id] = entity
                self._name_to_id[entity.name.lower()] = entity.id
                self._entity_by_type.setdefault(entity.entity_type, []).append(entity.id)
            for r_data in data.get("relationships", []):
                rel = Relationship(**r_data)
                self._relationships[rel.id] = rel
            logger.debug("Loaded %d entities, %d relationships",
                         len(self._entities), len(self._relationships))
        except Exception as e:
            logger.warning("Failed to load knowledge graph: %s", e)

    def _save(self) -> None:
        """Persist graph to disk."""
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = {
                "entities": [vars(e) for e in self._entities.values()],
                "relationships": [vars(r) for r in self._relationships.values()],
                "last_save": time.time(),
            }
            self._store_path.write_text(json.dumps(data, indent=2, default=str))
        except Exception as e:
            logger.warning("Failed to save knowledge graph: %s", e)

    def _register_listeners(self) -> None:
        """Register EventBus listeners for automatic graph building."""
        self._bus.on("experience_recorded", self._on_experience_recorded)
        self._bus.on("memory_stored", self._on_memory_stored)
        self._bus.on("camera_detection", self._on_camera_detection)
        self._bus.on("knowledge_graph_query", self._on_query_request)

    # ── Entity Management ──────────────────────────────────────────

    def add_entity(self, entity_type: str, name: str,
                   description: str = "",
                   properties: Optional[Dict[str, Any]] = None,
                   aliases: Optional[List[str]] = None,
                   source: str = "") -> Entity:
        """Add or update an entity in the knowledge graph.

        Args:
            entity_type: Type (person, place, object, concept, task, device, memory, event)
            name: Primary name of the entity
            description: Optional description
            properties: Optional metadata properties
            aliases: Alternative names for lookup
            source: How this entity was discovered

        Returns:
            The Entity (new or updated)
        """
        name_lower = name.lower().strip()

        # Check if entity already exists
        existing_id = self._name_to_id.get(name_lower)
        if existing_id and existing_id in self._entities:
            entity = self._entities[existing_id]
            entity.times_encountered += 1
            entity.last_seen = time.time()
            entity.strength = min(1.0, entity.strength + 0.1)
            if description and not entity.description:
                entity.description = description
            if properties:
                entity.properties.update(properties)
            if aliases:
                for alias in aliases:
                    if alias.lower() not in self._name_to_id:
                        self._name_to_id[alias.lower()] = entity.id
                    entity.aliases.append(alias)
            return entity

        # Create new entity
        now = time.time()
        entity = Entity(
            id=str(uuid.uuid4())[:12],
            name=name,
            entity_type=entity_type,
            description=description[:200] if description else "",
            properties=properties or {},
            aliases=aliases or [],
            strength=1.0,
            first_seen=now,
            last_seen=now,
            source=source,
        )
        self._entities[entity.id] = entity
        self._name_to_id[name_lower] = entity.id
        self._entity_by_type.setdefault(entity_type, []).append(entity.id)

        # Prune if over limit
        if len(self._entities) > MAX_ENTITIES * 1.1:
            self._prune_entities()

        self._bus.emit(Event("knowledge_entity_added", {
            "id": entity.id,
            "name": name,
            "type": entity_type,
        }, source="knowledge_graph", priority=Priority.LOW))

        return entity

    def add_entities_batch(self, entities: List[Dict[str, Any]]) -> List[Entity]:
        """Add multiple entities at once."""
        results = []
        for e_data in entities:
            entity = self.add_entity(
                entity_type=e_data.get("type", "concept"),
                name=e_data.get("name", "unknown"),
                description=e_data.get("description", ""),
                properties=e_data.get("properties"),
                aliases=e_data.get("aliases"),
                source=e_data.get("source", ""),
            )
            results.append(entity)
        self._save()
        return results

    def get_entity(self, identifier: str) -> Optional[Entity]:
        """Look up an entity by ID or name.

        Args:
            identifier: Entity ID or name

        Returns:
            The matching Entity, or None
        """
        # Try ID first
        if identifier in self._entities:
            return self._entities[identifier]
        # Try name
        name_lower = identifier.lower().strip()
        if name_lower in self._name_to_id:
            eid = self._name_to_id[name_lower]
            return self._entities.get(eid)
        # Try alias
        for eid, entity in self._entities.items():
            if any(alias.lower() == name_lower for alias in entity.aliases):
                return entity
        return None

    def search_entities(self, query: str, entity_type: Optional[str] = None,
                        limit: int = 20) -> List[Entity]:
        """Search entities by name or description.

        Args:
            query: Search text
            entity_type: Optional type filter
            limit: Maximum results

        Returns:
            List of matching entities, sorted by relevance
        """
        q = query.lower().strip()
        scored: List[Tuple[float, Entity]] = []

        for entity in self._entities.values():
            if entity_type and entity.entity_type != entity_type:
                continue

            score = 0.0
            if q == entity.name.lower():
                score = 10.0
            elif q in entity.name.lower():
                score = 5.0
            if q in entity.description.lower():
                score += 2.0
            if any(q in alias.lower() for alias in entity.aliases):
                score += 3.0
            for val in entity.properties.values():
                if isinstance(val, str) and q in val.lower():
                    score += 1.0

            if score > 0:
                scored.append((score * entity.strength, entity))

        scored.sort(key=lambda x: -x[0])
        return [e for _, e in scored[:limit]]

    def get_entities_by_type(self, entity_type: str) -> List[Entity]:
        """Get all entities of a given type."""
        ids = self._entity_by_type.get(entity_type, [])
        return [self._entities[eid] for eid in ids if eid in self._entities]

    def _prune_entities(self) -> None:
        """Remove low-strength, old entities (forgetting mechanism)."""
        now = time.time()

        # Remove entities below strength threshold and very old
        ids_to_remove: List[str] = []
        for eid, entity in self._entities.items():
            age_days = (now - entity.last_seen) / 86400
            if entity.strength < 0.1 and age_days > ENTITY_DECAY_DAYS:
                ids_to_remove.append(eid)
            elif entity.strength < 0.2 and age_days > ENTITY_DECAY_DAYS * 2:
                ids_to_remove.append(eid)

        # Also remove weakest if still over limit
        if len(self._entities) - len(ids_to_remove) > MAX_ENTITIES:
            sorted_entities = sorted(
                [e for e in self._entities.values() if e.id not in ids_to_remove],
                key=lambda e: e.strength,
            )
            excess = len(sorted_entities) - MAX_ENTITIES
            ids_to_remove.extend(e.id for e in sorted_entities[:excess])

        # Remove entities and their relationships
        for eid in ids_to_remove:
            entity = self._entities.get(eid)
            if entity:
                del self._name_to_id[entity.name.lower()]
                for alias in entity.aliases:
                    self._name_to_id.pop(alias.lower(), None)
                del self._entities[eid]

        # Remove orphaned relationships
        self._relationships = {
            rid: rel for rid, rel in self._relationships.items()
            if rel.source_id in self._entities and rel.target_id in self._entities
        }

        if ids_to_remove:
            logger.debug("Pruned %d entities from knowledge graph", len(ids_to_remove))

    # ── Relationship Management ────────────────────────────────────

    def add_relationship(self, source: str, target: str,
                         relationship_type: str = "related_to",
                         confidence: float = 1.0,
                         metadata: Optional[Dict[str, Any]] = None) -> Optional[Relationship]:
        """Add or strengthen a relationship between two entities.

        Args:
            source: Source entity ID or name
            target: Target entity ID or name
            relationship_type: Type of relationship
            confidence: Confidence in this relationship (0.0-1.0)
            metadata: Optional metadata

        Returns:
            The Relationship, or None if either entity is not found
        """
        source_entity = self.get_entity(source)
        target_entity = self.get_entity(target)

        if not source_entity or not target_entity:
            logger.debug("Cannot add relationship: entity not found (%s -> %s)",
                         source, target)
            return None

        # Check for existing relationship
        existing = self._find_relationship(source_entity.id, target_entity.id,
                                            relationship_type)
        if existing:
            existing.times_observed += 1
            existing.last_observed = time.time()
            existing.strength = min(1.0, existing.strength + 0.1)
            existing.confidence = max(existing.confidence, confidence)
            if metadata:
                existing.metadata.update(metadata)
            return existing

        # Create new relationship
        rel = Relationship(
            id=str(uuid.uuid4())[:12],
            source_id=source_entity.id,
            target_id=target_entity.id,
            relationship_type=relationship_type,
            strength=1.0,
            confidence=confidence,
            first_observed=time.time(),
            last_observed=time.time(),
            metadata=metadata or {},
        )
        self._relationships[rel.id] = rel

        # Prune if over limit
        if len(self._relationships) > MAX_RELATIONSHIPS * 1.1:
            self._prune_relationships()

        self._bus.emit(Event("knowledge_relationship_added", {
            "source": source_entity.name,
            "target": target_entity.name,
            "type": relationship_type,
        }, source="knowledge_graph", priority=Priority.LOW))

        return rel

    def _find_relationship(self, source_id: str, target_id: str,
                           rel_type: str) -> Optional[Relationship]:
        """Find an existing relationship matching the given parameters."""
        for rel in self._relationships.values():
            if (rel.source_id == source_id and rel.target_id == target_id
                    and rel.relationship_type == rel_type):
                return rel
            # Also check reverse
            if (rel.source_id == target_id and rel.target_id == source_id
                    and rel.relationship_type == rel_type):
                return rel
        return None

    def get_relationships(self, entity_id: str,
                          relationship_type: Optional[str] = None) -> List[Relationship]:
        """Get all relationships involving an entity.

        Args:
            entity_id: Entity ID
            relationship_type: Optional type filter

        Returns:
            List of relationships
        """
        results = []
        for rel in self._relationships.values():
            if rel.source_id == entity_id or rel.target_id == entity_id:
                if relationship_type and rel.relationship_type != relationship_type:
                    continue
                results.append(rel)
        results.sort(key=lambda r: -r.strength)
        return results

    def _prune_relationships(self) -> None:
        """Remove weak, old relationships."""
        now = time.time()
        self._relationships = {
            rid: rel for rid, rel in self._relationships.items()
            if rel.strength > 0.1
            and (now - rel.last_observed) / 86400 < RELATIONSHIP_DECAY_DAYS
        }

    # ── Graph Queries ──────────────────────────────────────────────

    def query(self, identifier: str, depth: int = 1,
              max_results: int = 20) -> GraphQuery:
        """Query the graph for an entity and its context.

        Args:
            identifier: Entity ID or name
            depth: How many relationship hops to traverse (1-3)
            max_results: Maximum entities to return

        Returns:
            GraphQuery with entities, relationships, and paths
        """
        entity = self.get_entity(identifier)
        if not entity:
            return GraphQuery()

        visited: Set[str] = {entity.id}
        entities: Dict[str, Entity] = {entity.id: entity}
        relationships: Dict[str, Relationship] = {}
        paths: List[List[Dict[str, Any]]] = []

        # BFS traversal
        current_level = {entity.id}
        for level in range(depth):
            next_level: Set[str] = set()
            for eid in current_level:
                for rel in self.get_relationships(eid):
                    if rel.id not in relationships:
                        relationships[rel.id] = rel
                    other_id = rel.target_id if rel.source_id == eid else rel.source_id
                    if other_id not in visited and other_id in self._entities:
                        next_level.add(other_id)
                        visited.add(other_id)
                        entities[other_id] = self._entities[other_id]
                        # Build path
                        paths.append([
                            {"entity": entity.name, "type": entity.entity_type},
                            {"relationship": rel.relationship_type},
                            {"entity": self._entities[other_id].name,
                             "type": self._entities[other_id].entity_type},
                        ])
            current_level = next_level
            if len(entities) >= max_results:
                break

        return GraphQuery(
            entities=list(entities.values()),
            relationships=list(relationships.values()),
            paths=paths,
            confidence=entity.strength,
        )

    def get_neighbors(self, identifier: str,
                      relationship_type: Optional[str] = None,
                      max_distance: int = 1) -> List[Tuple[Entity, str, float]]:
        """Get entities near a given entity, with relationship context.

        Returns list of (entity, relationship_type, strength).
        """
        entity = self.get_entity(identifier)
        if not entity:
            return []

        neighbors: Dict[str, Tuple[Entity, str, float]] = {}
        for rel in self.get_relationships(entity.id, relationship_type):
            other_id = rel.target_id if rel.source_id == entity.id else rel.source_id
            if other_id in self._entities:
                other = self._entities[other_id]
                if other.id not in neighbors:
                    neighbors[other.id] = (other, rel.relationship_type,
                                            rel.strength * other.strength)

        return sorted(neighbors.values(), key=lambda x: -x[2])

    def find_path(self, source: str, target: str,
                  max_hops: int = 4) -> List[List[Dict[str, Any]]]:
        """Find paths between two entities.

        Args:
            source: Source entity ID or name
            target: Target entity ID or name
            max_hops: Maximum path length

        Returns:
            List of paths, where each path is a list of hops
        """
        source_entity = self.get_entity(source)
        target_entity = self.get_entity(target)

        if not source_entity or not target_entity:
            return []

        if source_entity.id == target_entity.id:
            return [[{"entity": source_entity.name, "type": source_entity.entity_type}]]

        # BFS shortest path
        paths: List[List[str]] = [[source_entity.id]]
        visited: Set[str] = {source_entity.id}

        for _ in range(max_hops):
            new_paths: List[List[str]] = []
            for path in paths:
                current = path[-1]
                for rel in self.get_relationships(current):
                    other = rel.target_id if rel.source_id == current else rel.source_id
                    if other == target_entity.id:
                        # Found!
                        full_path = path + [other]
                        result = self._path_to_readable(full_path)
                        return [result]
                    if other not in visited:
                        visited.add(other)
                        new_paths.append(path + [other])
            paths = new_paths
            if not paths:
                break

        # Convert best paths
        readable_paths = []
        for path in paths[:5]:
            readable_paths.append(self._path_to_readable(path))
        return readable_paths

    def _path_to_readable(self, path_ids: List[str]) -> List[Dict[str, Any]]:
        """Convert a path of IDs to readable hops."""
        readable = []
        for i, eid in enumerate(path_ids):
            entity = self._entities.get(eid)
            if not entity:
                continue
            readable.append({"entity": entity.name, "type": entity.entity_type})
            if i < len(path_ids) - 1:
                next_eid = path_ids[i + 1]
                for rel in self.get_relationships(eid):
                    other = rel.target_id if rel.source_id == eid else rel.source_id
                    if other == next_eid:
                        readable.append({"relationship": rel.relationship_type})
                        break
        return readable

    def get_communities(self, min_size: int = 2) -> List[List[Entity]]:
        """Find clusters of densely connected entities (communities)."""
        # Simple community detection using connected components
        visited: Set[str] = set()
        communities: List[List[Entity]] = []

        for eid in self._entities:
            if eid in visited:
                continue

            # BFS to find component
            component: List[Entity] = []
            queue = [eid]
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                component.append(self._entities[current])
                for rel in self.get_relationships(current):
                    other = rel.target_id if rel.source_id == current else rel.source_id
                    if other not in visited and other in self._entities:
                        queue.append(other)

            if len(component) >= min_size:
                communities.append(component)

        return sorted(communities, key=len, reverse=True)

    # ── Auto-population from Events ────────────────────────────────

    def _on_experience_recorded(self, event: Event) -> None:
        """Auto-extract entities from recorded experiences."""
        data = event.data
        summary = data.get("summary", "")
        exp_type = data.get("type", "")

        # Extract potential entities from summary text
        entities_found = self._extract_entities_from_text(summary)

        # Create concept entities for experience types
        self.add_entity("concept", exp_type.replace("_", " ").title(),
                         source="experience_auto")

        for name, etype in entities_found:
            self.add_entity(etype, name, source="experience_auto")

    def _on_memory_stored(self, event: Event) -> None:
        """Add memory entities to the graph."""
        data = event.data
        mem_type = data.get("type", "episodic")
        mem_id = data.get("id", "")

        self.add_entity(
            "memory", f"Memory ({mem_type})",
            properties={"memory_id": mem_id, "memory_type": mem_type},
            source="memory_auto",
        )

    def _on_camera_detection(self, event: Event) -> None:
        """Add detected objects as entities."""
        data = event.data
        objects = data.get("objects", [])
        if isinstance(objects, list):
            for obj in objects:
                name = obj.get("name", "unknown_object") if isinstance(obj, dict) else str(obj)
                self.add_entity("object", name.replace("_", " ").title(),
                                 source="vision_auto")

    def _extract_entities_from_text(self, text: str) -> List[Tuple[str, str]]:
        """Extract potential entities from natural language text.

        Returns list of (entity_name, entity_type) tuples.
        Only returns words that match known entity type patterns
        to avoid polluting the graph with common English words.
        """
        found: List[Tuple[str, str]] = []
        seen: Set[str] = set()

        stop_words = {
            "the", "a", "an", "is", "was", "are", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did",
            "will", "would", "could", "should", "may", "might",
            "shall", "can", "must", "need", "to", "of", "in",
            "for", "on", "with", "at", "by", "from", "as", "into",
            "through", "during", "before", "after", "above", "below",
            "between", "out", "off", "over", "under", "again",
            "further", "then", "once", "here", "there", "when",
            "where", "why", "how", "all", "each", "every", "both",
            "few", "more", "most", "other", "some", "such", "no",
            "nor", "not", "only", "own", "same", "so", "than",
            "too", "very", "just", "because", "also", "if", "or",
            "and", "but", "up", "down", "it", "its", "this", "that",
        }

        for etype, patterns in self.TYPE_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    word = match.group(0).strip().lower()
                    # Filter out stop words, single chars, pure numbers
                    if (len(word) > 2
                            and word not in stop_words
                            and not word.isdigit()
                            and word not in seen):
                        seen.add(word)
                        found.append((match.group(0).strip().title(), etype))

        return found[:5]  # Limit per event

    def _on_query_request(self, event: Event) -> None:
        """Handle graph query requests via EventBus."""
        identifier = event.data.get("entity", "")
        depth = event.data.get("depth", 1)
        result = self.query(identifier, depth=depth)

        self._bus.emit(Event("knowledge_graph_result", {
            "entity_count": len(result.entities),
            "relationship_count": len(result.relationships),
            "entities": [{"name": e.name, "type": e.entity_type}
                         for e in result.entities],
            "paths": result.paths,
        }, source="knowledge_graph"))

    # ── Graph Stats & Export ───────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        type_counts: Dict[str, int] = {}
        rel_type_counts: Dict[str, int] = {}
        for entity in self._entities.values():
            type_counts[entity.entity_type] = type_counts.get(entity.entity_type, 0) + 1
        for rel in self._relationships.values():
            rel_type_counts[rel.relationship_type] = rel_type_counts.get(
                rel.relationship_type, 0) + 1

        avg_strength = (
            sum(e.strength for e in self._entities.values()) / max(1, len(self._entities))
        )

        return {
            "total_entities": len(self._entities),
            "total_relationships": len(self._relationships),
            "by_type": type_counts,
            "by_relationship": rel_type_counts,
            "average_strength": round(avg_strength, 3),
            "communities": len(self.get_communities(min_size=3)),
            "most_connected": self._get_most_connected(5),
        }

    def _get_most_connected(self, n: int = 5) -> List[Dict[str, Any]]:
        """Get the most connected entities."""
        connection_counts: Dict[str, int] = {}
        for rel in self._relationships.values():
            connection_counts[rel.source_id] = connection_counts.get(rel.source_id, 0) + 1
            connection_counts[rel.target_id] = connection_counts.get(rel.target_id, 0) + 1

        sorted_entities = sorted(
            connection_counts.items(),
            key=lambda x: -x[1],
        )[:n]

        result = []
        for eid, count in sorted_entities:
            entity = self._entities.get(eid)
            if entity:
                result.append({"name": entity.name, "type": entity.entity_type,
                                "connections": count})
        return result

    def export_graph(self, filepath: str) -> bool:
        """Export the graph as JSON for visualization."""
        try:
            export_path = Path(filepath)
            export_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "entities": [
                    {"id": e.id, "name": e.name, "type": e.entity_type,
                     "strength": e.strength, "description": e.description}
                    for e in self._entities.values()
                ],
                "relationships": [
                    {"source": self._entities[r.source_id].name if r.source_id in self._entities else r.source_id,
                     "target": self._entities[r.target_id].name if r.target_id in self._entities else r.target_id,
                     "type": r.relationship_type, "strength": r.strength}
                    for r in self._relationships.values()
                    if r.source_id in self._entities and r.target_id in self._entities
                ],
            }
            export_path.write_text(json.dumps(data, indent=2))
            logger.info("Exported graph to %s (%d entities, %d edges)",
                         filepath, len(data["entities"]), len(data["relationships"]))
            return True
        except Exception as e:
            logger.warning("Export failed: %s", e)
            return False

    def get_summary(self) -> Dict[str, Any]:
        """Quick status summary."""
        return {
            "total_entities": len(self._entities),
            "total_relationships": len(self._relationships),
            "entity_types": list(self._entity_by_type.keys()),
            "top_entities": self._get_most_connected(3),
        }
