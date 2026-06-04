"""
NEXUS AI - Knowledge Graph Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Real knowledge graph with entity-relationship storage and graph algorithms.
This provides actual graph computation, not LLM-estimated relationships.

Features:
  • Entity storage with types, properties, and embeddings
  • Typed relationships with weights and confidence
  • Graph queries: paths, neighbors, subgraphs
  • Integration with existing KnowledgeBase
  • NetworkX backend for graph algorithms
  • Persistence to SQLite

The knowledge graph is the computational foundation for:
  - Causal reasoning (causal graphs)
  - Semantic understanding (concept graphs)
  - Planning (state-space graphs)
"""

import threading
import json
import sqlite3
import uuid
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Set, Iterator
from dataclasses import dataclass, field, asdict
from pathlib import Path
from collections import defaultdict
from enum import Enum, auto

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("knowledge_graph")

# Try to import NetworkX for graph algorithms
try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    logger.warning("NetworkX not available - graph algorithms will be limited")

# ═══════════════════════════════════════════════════════════════════════════════
# DATA TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class EntityType(Enum):
    """Types of entities in the knowledge graph"""
    CONCEPT = "concept"
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    EVENT = "event"
    OBJECT = "object"
    ACTION = "action"
    ATTRIBUTE = "attribute"
    CAUSE = "cause"
    EFFECT = "effect"
    UNKNOWN = "unknown"


class RelationType(Enum):
    """Types of relationships between entities"""
    IS_A = "is_a"                    # Taxonomy
    PART_OF = "part_of"              # Meronymy
    HAS_PROPERTY = "has_property"    # Attribution
    CAUSES = "causes"                # Causation
    PREVENTS = "prevents"            # Inhibition
    ENABLES = "enables"              # Enablement
    RELATED_TO = "related_to"        # Generic relation
    CONTRADICTS = "contradicts"      # Opposition
    IMPLIES = "implies"              # Logical implication
    FOLLOWS = "follows"              # Temporal sequence
    LOCATED_AT = "located_at"        # Spatial relation
    CREATED_BY = "created_by"        # Agency
    USED_FOR = "used_for"            # Purpose
    SIMILAR_TO = "similar_to"        # Similarity
    DEPENDS_ON = "depends_on"        # Dependency


@dataclass
class Entity:
    """A node in the knowledge graph"""
    entity_id: str = ""
    name: str = ""
    entity_type: EntityType = EntityType.CONCEPT
    properties: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    confidence: float = 0.7
    source: str = "unknown"  # Where this entity came from
    created_at: str = ""
    updated_at: str = ""
    access_count: int = 0

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["entity_type"] = self.entity_type.value
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> "Entity":
        etype = EntityType.CONCEPT
        try:
            etype = EntityType(data.get("entity_type", "concept"))
        except ValueError:
            pass
        return cls(
            entity_id=data.get("entity_id", ""),
            name=data.get("name", ""),
            entity_type=etype,
            properties=data.get("properties", {}),
            embedding=data.get("embedding"),
            confidence=data.get("confidence", 0.7),
            source=data.get("source", "unknown"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            access_count=data.get("access_count", 0),
        )


@dataclass
class Relation:
    """An edge in the knowledge graph"""
    relation_id: str = ""
    subject_id: str = ""
    predicate: RelationType = RelationType.RELATED_TO
    object_id: str = ""
    weight: float = 1.0
    confidence: float = 0.7
    properties: Dict[str, Any] = field(default_factory=dict)
    evidence: List[str] = field(default_factory=list)  # Sources supporting this relation
    created_at: str = ""

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["predicate"] = self.predicate.value
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> "Relation":
        ptype = RelationType.RELATED_TO
        try:
            ptype = RelationType(data.get("predicate", "related_to"))
        except ValueError:
            pass
        return cls(
            relation_id=data.get("relation_id", ""),
            subject_id=data.get("subject_id", ""),
            predicate=ptype,
            object_id=data.get("object_id", ""),
            weight=data.get("weight", 1.0),
            confidence=data.get("confidence", 0.7),
            properties=data.get("properties", {}),
            evidence=data.get("evidence", []),
            created_at=data.get("created_at", ""),
        )


@dataclass
class GraphPath:
    """A path through the knowledge graph"""
    nodes: List[str] = field(default_factory=list)  # Entity IDs
    edges: List[str] = field(default_factory=list)  # Relation types
    total_weight: float = 0.0
    confidence: float = 1.0
    length: int = 0

    def to_dict(self) -> Dict:
        return {
            "nodes": self.nodes,
            "edges": self.edges,
            "total_weight": self.total_weight,
            "confidence": self.confidence,
            "length": self.length,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# KNOWLEDGE GRAPH ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class KnowledgeGraph:
    """
    Real Knowledge Graph with NetworkX backend.
    
    Operations:
      add_entity()     — Add a node
      add_relation()   — Add an edge
      find_path()      — Shortest path between entities
      get_neighbors()  — Get connected entities
      query()          — Pattern matching queries
      get_subgraph()   — Extract a subgraph
      compute_centrality() — Importance measures
    """
    
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # ──── Storage ────
        self._entities: Dict[str, Entity] = {}
        self._relations: Dict[str, Relation] = {}
        self._entity_name_index: Dict[str, str] = {}  # name -> entity_id
        self._adjacency: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
        
        # ──── NetworkX Graph ────
        self._nx_graph = None
        if NETWORKX_AVAILABLE:
            self._nx_graph = nx.DiGraph()

        # ──── Database ────
        self._db_path = DATA_DIR / "knowledge" / "knowledge_graph.db"
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_lock = threading.Lock()
        self._init_database()

        # ──── Stats ────
        self._total_entities = 0
        self._total_relations = 0
        self._total_queries = 0

        self._load_data()
        logger.info(f"KnowledgeGraph initialized ({len(self._entities)} entities, {len(self._relations)} relations)")

    # ═══════════════════════════════════════════════════════════════════════════
    # DATABASE
    # ═══════════════════════════════════════════════════════════════════════════

    def _init_database(self):
        """Initialize SQLite database for persistence"""
        with self._db_lock:
            conn = sqlite3.connect(str(self._db_path))
            cursor = conn.cursor()
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS entities (
                    entity_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    entity_type TEXT DEFAULT 'concept',
                    properties TEXT,
                    embedding BLOB,
                    confidence REAL DEFAULT 0.7,
                    source TEXT DEFAULT 'unknown',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT,
                    access_count INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS relations (
                    relation_id TEXT PRIMARY KEY,
                    subject_id TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object_id TEXT NOT NULL,
                    weight REAL DEFAULT 1.0,
                    confidence REAL DEFAULT 0.7,
                    properties TEXT,
                    evidence TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (subject_id) REFERENCES entities(entity_id),
                    FOREIGN KEY (object_id) REFERENCES entities(entity_id)
                );

                CREATE INDEX IF NOT EXISTS idx_entity_name ON entities(name);
                CREATE INDEX IF NOT EXISTS idx_entity_type ON entities(entity_type);
                CREATE INDEX IF NOT EXISTS idx_relation_subject ON relations(subject_id);
                CREATE INDEX IF NOT EXISTS idx_relation_object ON relations(object_id);
                CREATE INDEX IF NOT EXISTS idx_relation_predicate ON relations(predicate);
            """)
            conn.commit()
            conn.close()

    def _db_execute(self, query: str, params: tuple = (), fetch: bool = False) -> Any:
        """Execute a database query"""
        with self._db_lock:
            try:
                conn = sqlite3.connect(str(self._db_path))
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, params)
                result = cursor.fetchall() if fetch else cursor.lastrowid
                conn.commit()
                conn.close()
                return result
            except Exception as e:
                logger.error(f"Knowledge graph DB error: {e}")
                return [] if fetch else None

    # ═══════════════════════════════════════════════════════════════════════════
    # ENTITY OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════════

    def add_entity(
        self,
        name: str,
        entity_type: EntityType | str = EntityType.CONCEPT,
        properties: Dict[str, Any] = None,
        confidence: float = 0.7,
        source: str = "unknown"
    ) -> str:
        """
        Add an entity to the knowledge graph.
        
        Returns entity_id.
        """
        name = name.strip().lower()
        if not name:
            return ""

        # Check if entity already exists
        if name in self._entity_name_index:
            existing_id = self._entity_name_index[name]
            # Update confidence if higher
            if confidence > self._entities[existing_id].confidence:
                self._entities[existing_id].confidence = confidence
                self._entities[existing_id].updated_at = datetime.now().isoformat()
            return existing_id

        # Create new entity
        entity_id = f"e_{hashlib.md5(name.encode()).hexdigest()[:12]}"
        now = datetime.now().isoformat()

        # Convert string to EntityType if needed
        if isinstance(entity_type, str):
            try:
                entity_type = EntityType(entity_type.lower())
            except ValueError:
                entity_type = EntityType.CONCEPT

        entity = Entity(
            entity_id=entity_id,
            name=name,
            entity_type=entity_type,
            properties=properties or {},
            confidence=confidence,
            source=source,
            created_at=now,
            updated_at=now,
        )

        self._entities[entity_id] = entity
        self._entity_name_index[name] = entity_id
        self._total_entities += 1

        # Add to NetworkX graph
        if self._nx_graph is not None:
            self._nx_graph.add_node(entity_id, name=name, type=entity_type.value, **(properties or {}))

        # Persist to database
        self._db_execute(
            """INSERT OR REPLACE INTO entities 
               (entity_id, name, entity_type, properties, confidence, source, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (entity_id, name, entity_type.value, json.dumps(properties or {}),
             confidence, source, now, now)
        )

        logger.debug(f"Added entity: {name} ({entity_type.value})")
        return entity_id

    def get_entity(self, entity_id: str = None, name: str = None) -> Optional[Entity]:
        """Get entity by ID or name"""
        if entity_id:
            entity = self._entities.get(entity_id)
            if entity:
                entity.access_count += 1
            return entity
        elif name:
            name = name.strip().lower()
            entity_id = self._entity_name_index.get(name)
            if entity_id:
                return self.get_entity(entity_id=entity_id)
        return None

    def get_entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        """Get all entities of a given type"""
        return [e for e in self._entities.values() if e.entity_type == entity_type]

    def search_entities(self, query: str, limit: int = 10) -> List[Entity]:
        """Search entities by name substring"""
        query = query.lower()
        matches = []
        for entity in self._entities.values():
            if query in entity.name:
                matches.append(entity)
            elif any(query in str(v).lower() for v in entity.properties.values()):
                matches.append(entity)
            if len(matches) >= limit:
                break
        return matches

    # ═══════════════════════════════════════════════════════════════════════════
    # RELATION OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════════

    def add_relation(
        self,
        subject: str,  # Entity name or ID
        predicate: RelationType,
        obj: str,  # Entity name or ID
        weight: float = 1.0,
        confidence: float = 0.7,
        evidence: List[str] = None
    ) -> Optional[str]:
        """
        Add a relation between two entities.
        Creates entities if they don't exist.
        
        Returns relation_id.
        """
        # Resolve subject
        subject_id = subject if subject.startswith("e_") else self._entity_name_index.get(subject.lower())
        if not subject_id:
            subject_id = self.add_entity(subject, EntityType.CONCEPT)

        # Resolve object
        object_id = obj if obj.startswith("e_") else self._entity_name_index.get(obj.lower())
        if not object_id:
            object_id = self.add_entity(obj, EntityType.CONCEPT)

        # Check for duplicate relation
        for rel in self._relations.values():
            if (rel.subject_id == subject_id and 
                rel.predicate == predicate and 
                rel.object_id == object_id):
                # Update weight/confidence if higher
                if confidence > rel.confidence:
                    rel.confidence = confidence
                    rel.weight = weight
                return rel.relation_id

        # Create new relation
        relation_id = f"r_{hashlib.md5(f'{subject_id}_{predicate.value}_{object_id}'.encode()).hexdigest()[:12]}"
        now = datetime.now().isoformat()

        relation = Relation(
            relation_id=relation_id,
            subject_id=subject_id,
            predicate=predicate,
            object_id=object_id,
            weight=weight,
            confidence=confidence,
            evidence=evidence or [],
            created_at=now,
        )

        self._relations[relation_id] = relation
        self._adjacency[subject_id][object_id].append(relation_id)
        self._total_relations += 1

        # Add to NetworkX graph
        if self._nx_graph is not None:
            self._nx_graph.add_edge(subject_id, object_id, 
                                    relation=relation_id,
                                    predicate=predicate.value,
                                    weight=weight,
                                    confidence=confidence)

        # Persist to database
        self._db_execute(
            """INSERT OR REPLACE INTO relations 
               (relation_id, subject_id, predicate, object_id, weight, confidence, evidence, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (relation_id, subject_id, predicate.value, object_id, 
             weight, confidence, json.dumps(evidence or []), now)
        )

        logger.debug(f"Added relation: {subject} --[{predicate.value}]--> {obj}")
        return relation_id

    def get_relations(self, entity_id: str, direction: str = "out") -> List[Relation]:
        """
        Get relations for an entity.
        
        Args:
            entity_id: The entity to get relations for
            direction: "out" (outgoing), "in" (incoming), or "both"
        """
        relations = []
        if direction in ("out", "both"):
            for obj_id, rel_ids in self._adjacency[entity_id].items():
                for rel_id in rel_ids:
                    relations.append(self._relations[rel_id])
        if direction in ("in", "both"):
            for rel in self._relations.values():
                if rel.object_id == entity_id:
                    relations.append(rel)
        return relations

    def get_neighbors(self, entity_id: str, predicate_filter: List[RelationType] = None) -> List[Tuple[Entity, Relation]]:
        """
        Get neighboring entities and their relations.
        
        Returns list of (neighbor_entity, relation) tuples.
        """
        neighbors = []
        for obj_id, rel_ids in self._adjacency[entity_id].items():
            for rel_id in rel_ids:
                rel = self._relations.get(rel_id)
                if rel:
                    if predicate_filter and rel.predicate not in predicate_filter:
                        continue
                    obj_entity = self._entities.get(obj_id)
                    if obj_entity:
                        neighbors.append((obj_entity, rel))
        return neighbors

    # ═══════════════════════════════════════════════════════════════════════════
    # GRAPH QUERIES
    # ═══════════════════════════════════════════════════════════════════════════

    def find_path(
        self, 
        source: str, 
        target: str, 
        max_depth: int = 5,
        relation_filter: List[RelationType] = None
    ) -> Optional[GraphPath]:
        """
        Find the shortest path between two entities.
        
        Uses BFS for unweighted, Dijkstra for weighted paths.
        """
        self._total_queries += 1

        # Resolve entity IDs
        source_id = source if source.startswith("e_") else self._entity_name_index.get(source.lower())
        target_id = target if target.startswith("e_") else self._entity_name_index.get(target.lower())

        if not source_id or not target_id:
            return None

        if source_id == target_id:
            return GraphPath(nodes=[source_id], edges=[], total_weight=0.0, confidence=1.0, length=0)

        # Use NetworkX if available
        if self._nx_graph is not None and source_id in self._nx_graph and target_id in self._nx_graph:
            try:
                path = nx.shortest_path(self._nx_graph, source_id, target_id, weight="weight")
                if path:
                    # Get edges along path
                    edges = []
                    total_weight = 0.0
                    total_confidence = 1.0
                    for i in range(len(path) - 1):
                        edge_data = self._nx_graph.get_edge_data(path[i], path[i+1])
                        if edge_data:
                            edges.append(edge_data.get("predicate", "related_to"))
                            total_weight += edge_data.get("weight", 1.0)
                            total_confidence *= edge_data.get("confidence", 0.7)

                    return GraphPath(
                        nodes=path,
                        edges=edges,
                        total_weight=total_weight,
                        confidence=total_confidence,
                        length=len(path) - 1,
                    )
            except nx.NetworkXNoPath:
                return None
            except Exception as e:
                logger.error(f"NetworkX path finding error: {e}")

        # Fallback to BFS
        return self._bfs_path(source_id, target_id, max_depth, relation_filter)

    def _bfs_path(
        self, 
        source_id: str, 
        target_id: str, 
        max_depth: int,
        relation_filter: List[RelationType] = None
    ) -> Optional[GraphPath]:
        """BFS path finding fallback"""
        from collections import deque

        visited = {source_id}
        queue = deque([(source_id, [source_id], [])])
        
        while queue:
            current, path, edges = queue.popleft()
            
            if len(path) > max_depth:
                continue

            if current == target_id:
                return GraphPath(
                    nodes=path,
                    edges=edges,
                    length=len(path) - 1,
                )

            for neighbor, rel in self.get_neighbors(current, relation_filter):
                if neighbor.entity_id not in visited:
                    visited.add(neighbor.entity_id)
                    queue.append((neighbor.entity_id, path + [neighbor.entity_id], edges + [rel.predicate.value]))

        return None

    def get_subgraph(self, entity_ids: List[str], depth: int = 1) -> Tuple[Dict[str, Entity], Dict[str, Relation]]:
        """
        Extract a subgraph centered on given entities.
        
        Returns (entities, relations) dicts.
        """
        entities = {}
        relations = {}
        to_explore = set(entity_ids)
        explored = set()

        for _ in range(depth + 1):
            new_explore = set()
            for entity_id in to_explore:
                if entity_id in explored:
                    continue
                explored.add(entity_id)

                entity = self._entities.get(entity_id)
                if entity:
                    entities[entity_id] = entity

                # Get relations
                for rel in self.get_relations(entity_id, "both"):
                    relations[rel.relation_id] = rel
                    if rel.subject_id not in explored:
                        new_explore.add(rel.subject_id)
                    if rel.object_id not in explored:
                        new_explore.add(rel.object_id)

            to_explore = new_explore

        return entities, relations

    def query_pattern(self, pattern: str) -> List[Dict[str, Entity]]:
        """
        Query the graph with a simple pattern.
        
        Pattern format: "Subject? --[predicate?]?--> Object?"
        
        Examples:
          "Person --> ?" — All relations from Person
          "? --[causes]--> ?" — All causal relations
          "A --> B" — Direct relation from A to B
        """
        self._total_queries += 1
        results = []

        # Parse pattern
        parts = pattern.split("-->")
        if len(parts) != 2:
            return results

        left = parts[0].strip()
        right = parts[1].strip()

        # Extract predicate if present
        predicate = None
        if "--[" in left and "]" in left:
            pred_start = left.index("--[") + 3
            pred_end = left.index("]")
            predicate = left[pred_start:pred_end].strip()
            left = left[:pred_start - 3].strip()

        # Resolve subject and object constraints
        subject_constraint = None if left == "?" else left.lower()
        object_constraint = None if right == "?" else right.lower()

        # Find matching relations
        for rel in self._relations.values():
            # Check predicate
            if predicate and rel.predicate.value != predicate:
                continue

            # Check subject
            subject_entity = self._entities.get(rel.subject_id)
            if subject_constraint:
                if not subject_entity or subject_constraint not in subject_entity.name:
                    continue

            # Check object
            object_entity = self._entities.get(rel.object_id)
            if object_constraint:
                if not object_entity or object_constraint not in object_entity.name:
                    continue

            results.append({
                "subject": subject_entity,
                "relation": rel,
                "object": object_entity,
            })

        return results

    # ═══════════════════════════════════════════════════════════════════════════
    # GRAPH ALGORITHMS
    # ═══════════════════════════════════════════════════════════════════════════

    def compute_centrality(self, measure: str = "betweenness") -> Dict[str, float]:
        """
        Compute centrality measures for all nodes.
        
        Measures: betweenness, closeness, eigenvector, degree, pagerank
        """
        if self._nx_graph is None or len(self._nx_graph) == 0:
            return {}

        try:
            if measure == "betweenness":
                return nx.betweenness_centrality(self._nx_graph)
            elif measure == "closeness":
                return nx.closeness_centrality(self._nx_graph)
            elif measure == "eigenvector":
                return nx.eigenvector_centrality(self._nx_graph, max_iter=1000)
            elif measure == "degree":
                return nx.degree_centrality(self._nx_graph)
            elif measure == "pagerank":
                return nx.pagerank(self._nx_graph)
            else:
                return {}
        except Exception as e:
            logger.error(f"Centrality computation error: {e}")
            return {}

    def find_communities(self, algorithm: str = "louvain") -> Dict[str, int]:
        """
        Detect communities in the graph.
        
        Returns dict mapping entity_id -> community_id
        """
        if self._nx_graph is None:
            return {}

        try:
            if algorithm == "louvain":
                # Convert to undirected for community detection
                undirected = self._nx_graph.to_undirected()
                communities = nx.community.louvain_communities(undirected)
                result = {}
                for i, community in enumerate(communities):
                    for node in community:
                        result[node] = i
                return result
            elif algorithm == "label_propagation":
                undirected = self._nx_graph.to_undirected()
                communities = nx.algorithms.community.label_propagation_communities(undirected)
                result = {}
                for i, community in enumerate(communities):
                    for node in community:
                        result[node] = i
                return result
        except Exception as e:
            logger.error(f"Community detection error: {e}")
            return {}

    def find_influential_nodes(self, top_k: int = 10) -> List[Tuple[Entity, float]]:
        """
        Find the most influential entities in the graph.
        
        Uses PageRank as influence measure.
        """
        pagerank = self.compute_centrality("pagerank")
        if not pagerank:
            # Fallback to degree centrality
            pagerank = self.compute_centrality("degree")

        sorted_nodes = sorted(pagerank.items(), key=lambda x: -x[1])[:top_k]
        return [(self._entities.get(node_id), score) for node_id, score in sorted_nodes if node_id in self._entities]

    # ═══════════════════════════════════════════════════════════════════════════
    # LLM INTEGRATION
    # ═══════════════════════════════════════════════════════════════════════════

    def get_context_for_query(self, query: str, max_entities: int = 10) -> str:
        """
        Build a knowledge graph context string for LLM prompting.
        
        Finds relevant entities and their relations to provide context.
        """
        # Search for relevant entities
        entities = self.search_entities(query, limit=max_entities)
        if not entities:
            return ""

        parts = ["KNOWLEDGE GRAPH CONTEXT:"]

        for entity in entities:
            relations = self.get_relations(entity.entity_id, "out")[:5]
            if relations:
                rel_strs = []
                for rel in relations:
                    obj = self._entities.get(rel.object_id)
                    if obj:
                        rel_strs.append(f"{rel.predicate.value} {obj.name}")
                if rel_strs:
                    parts.append(f"- {entity.name}: " + ", ".join(rel_strs))

        return "\n".join(parts)

    def extract_from_text(self, text: str) -> Dict[str, Any]:
        """
        Use LLM to extract entities and relations from text.
        
        Returns extracted entities and relations (also adds them to the graph).
        """
        try:
            from llm.llama_interface import llm
            from utils.json_utils import extract_json

            prompt = (
                f"Extract entities and relationships from this text:\n\n{text}\n\n"
                f"Return JSON:\n"
                f'{{"entities": [{{"name": "str", "type": "concept|person|organization|location|event|action", '
                f'"properties": {{}}}}], '
                f'"relations": [{{"subject": "name", "predicate": "is_a|part_of|causes|enables|related_to|implies", '
                f'"object": "name", "confidence": 0.0-1.0}}]}}'
            )

            response = llm.generate(prompt, max_tokens=1000, temperature=0.3)
            data = extract_json(response.text) or {}

            # Add extracted entities
            entity_map = {}
            for e in data.get("entities", []):
                etype = EntityType.CONCEPT
                try:
                    etype = EntityType(e.get("type", "concept"))
                except ValueError:
                    pass
                entity_id = self.add_entity(
                    name=e.get("name", ""),
                    entity_type=etype,
                    properties=e.get("properties", {}),
                    source="extracted"
                )
                entity_map[e.get("name", "").lower()] = entity_id

            # Add extracted relations
            for r in data.get("relations", []):
                ptype = RelationType.RELATED_TO
                try:
                    ptype = RelationType(r.get("predicate", "related_to"))
                except ValueError:
                    pass
                self.add_relation(
                    subject=r.get("subject", ""),
                    predicate=ptype,
                    obj=r.get("object", ""),
                    confidence=r.get("confidence", 0.7),
                    evidence=[text[:200]]
                )

            return data

        except Exception as e:
            logger.debug(f"Entity extraction failed: {e}")
            return {"entities": [], "relations": []}

    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════

    def _load_data(self):
        """Load entities and relations from database"""
        # Load entities
        rows = self._db_execute("SELECT * FROM entities", fetch=True)
        for row in (rows or []):
            entity = Entity.from_dict({
                "entity_id": row["entity_id"],
                "name": row["name"],
                "entity_type": row["entity_type"],
                "properties": json.loads(row["properties"]) if row["properties"] else {},
                "confidence": row["confidence"],
                "source": row["source"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "access_count": row["access_count"],
            })
            self._entities[entity.entity_id] = entity
            self._entity_name_index[entity.name.lower()] = entity.entity_id

        # Load relations
        rows = self._db_execute("SELECT * FROM relations", fetch=True)
        for row in (rows or []):
            relation = Relation.from_dict({
                "relation_id": row["relation_id"],
                "subject_id": row["subject_id"],
                "predicate": row["predicate"],
                "object_id": row["object_id"],
                "weight": row["weight"],
                "confidence": row["confidence"],
                "evidence": json.loads(row["evidence"]) if row["evidence"] else [],
                "created_at": row["created_at"],
            })
            self._relations[relation.relation_id] = relation
            self._adjacency[relation.subject_id][relation.object_id].append(relation.relation_id)

        # Rebuild NetworkX graph
        if self._nx_graph is not None:
            self._nx_graph.clear()
            for entity in self._entities.values():
                self._nx_graph.add_node(entity.entity_id, name=entity.name, type=entity.entity_type.value)
            for relation in self._relations.values():
                self._nx_graph.add_edge(relation.subject_id, relation.object_id,
                                       relation=relation.relation_id,
                                       predicate=relation.predicate.value,
                                       weight=relation.weight,
                                       confidence=relation.confidence)

        logger.info(f"Loaded {len(self._entities)} entities and {len(self._relations)} relations from database")

    def save(self):
        """Explicit save (auto-save is on by default)"""
        # Data is auto-saved on each operation
        pass

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self):
        """Start the knowledge graph engine"""
        self._running = True
        logger.info("KnowledgeGraph started")

    def stop(self):
        """Stop the knowledge graph engine"""
        self._running = False
        logger.info("KnowledgeGraph stopped")

    # ═══════════════════════════════════════════════════════════════════════════
    # STATISTICS
    # ═══════════════════════════════════════════════════════════════════════════

    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge graph statistics"""
        type_counts = {}
        for entity in self._entities.values():
            t = entity.entity_type.value
            type_counts[t] = type_counts.get(t, 0) + 1

        predicate_counts = {}
        for rel in self._relations.values():
            p = rel.predicate.value
            predicate_counts[p] = predicate_counts.get(p, 0) + 1

        return {
            "total_entities": len(self._entities),
            "total_relations": len(self._relations),
            "total_queries": self._total_queries,
            "entities_by_type": type_counts,
            "relations_by_predicate": predicate_counts,
            "networkx_available": NETWORKX_AVAILABLE,
            "avg_relations_per_entity": len(self._relations) / max(len(self._entities), 1),
        }

    def clear(self):
        """Clear all data (use with caution)"""
        self._entities.clear()
        self._relations.clear()
        self._entity_name_index.clear()
        self._adjacency.clear()
        if self._nx_graph is not None:
            self._nx_graph.clear()

        # Clear database
        self._db_execute("DELETE FROM relations")
        self._db_execute("DELETE FROM entities")

        logger.warning("Knowledge graph cleared")


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

knowledge_graph = KnowledgeGraph()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    kg = KnowledgeGraph()

    # Test adding entities
    e1 = kg.add_entity("python", EntityType.CONCEPT, {"paradigm": "multi-paradigm", "typing": "dynamic"})
    e2 = kg.add_entity("programming language", EntityType.CONCEPT)
    e3 = kg.add_entity("artificial intelligence", EntityType.CONCEPT)
    e4 = kg.add_entity("machine learning", EntityType.CONCEPT, {"type": "subfield"})

    # Test adding relations
    kg.add_relation("python", RelationType.IS_A, "programming language", confidence=0.95)
    kg.add_relation("python", RelationType.USED_FOR, "machine learning", confidence=0.9)
    kg.add_relation("machine learning", RelationType.PART_OF, "artificial intelligence", confidence=0.95)

    # Test path finding
    path = kg.find_path("python", "artificial intelligence")
    if path:
        print(f"Path found: {' -> '.join(path.nodes)}")
        print(f"Edges: {path.edges}")
        print(f"Total weight: {path.total_weight}")

    # Test context for LLM
    print("\n" + kg.get_context_for_query("python"))

    # Test centrality
    influential = kg.find_influential_nodes()
    print(f"\nMost influential nodes: {[(e.name, s) for e, s in influential]}")

    # Stats
    print(f"\nStats: {kg.get_stats()}")