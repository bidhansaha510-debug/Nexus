"""
NEXUS AI — Knowledge Integration Engine
Ontology building, knowledge graph construction, cross-domain synthesis,
semantic linking, concept mapping, knowledge unification.
"""

import threading
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("knowledge_integration")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)


class RelationType(Enum):
    IS_A = "is_a"
    HAS_A = "has_a"
    PART_OF = "part_of"
    CAUSES = "causes"
    ENABLES = "enables"
    CONTRADICTS = "contradicts"
    SUPPORTS = "supports"
    SIMILAR_TO = "similar_to"
    OPPOSITE_OF = "opposite_of"
    DEPENDS_ON = "depends_on"
    PRECEDES = "precedes"
    SPECIALIZES = "specializes"
    GENERALIZES = "generalizes"
    RELATED_TO = "related_to"


@dataclass
class ConceptNode:
    node_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    domain: str = ""
    description: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    connections: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "node_id": self.node_id, "name": self.name,
            "domain": self.domain, "description": self.description,
            "properties": self.properties, "connections": self.connections
        }


@dataclass
class KnowledgeGraph:
    graph_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    topic: str = ""
    nodes: List[ConceptNode] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)
    domains: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "graph_id": self.graph_id, "topic": self.topic,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": self.edges, "domains": self.domains,
            "created_at": self.created_at
        }


@dataclass
class Synthesis:
    synthesis_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    domains: List[str] = field(default_factory=list)
    concepts: List[str] = field(default_factory=list)
    unified_understanding: str = ""
    cross_domain_links: List[Dict[str, str]] = field(default_factory=list)
    emergent_insights: List[str] = field(default_factory=list)
    coherence: float = 0.5
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "synthesis_id": self.synthesis_id, "domains": self.domains,
            "concepts": self.concepts,
            "unified_understanding": self.unified_understanding,
            "cross_domain_links": self.cross_domain_links,
            "emergent_insights": self.emergent_insights,
            "coherence": self.coherence, "created_at": self.created_at
        }


class KnowledgeIntegrationEngine:
    """
    Builds knowledge graphs, synthesizes cross-domain knowledge,
    creates ontologies, and finds semantic connections.
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

        self._graphs: List[KnowledgeGraph] = []
        self._syntheses: List[Synthesis] = []
        self._running = False
        self._data_file = COGNITION_DIR / "knowledge_integration.json"

        self._stats = {
            "total_graphs": 0, "total_syntheses": 0,
            "total_concepts_mapped": 0, "total_connections": 0
        }

        self._load_data()
        logger.info("✅ Knowledge Integration Engine initialized")

    def start(self):
        self._running = True
        logger.info("🌐 Knowledge Integration started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🌐 Knowledge Integration stopped")

    def build_knowledge_graph(self, topic: str, depth: str = "moderate") -> KnowledgeGraph:
        """Build a knowledge graph for a topic."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Build a knowledge graph for: {topic} (depth: {depth})\n\n"
                f"Return JSON:\n"
                f'{{"nodes": [{{"name": "str", "domain": "str", '
                f'"description": "str", "properties": {{}}}}'
                f'], '
                f'"edges": [{{"from": "str", "to": "str", '
                f'"relation": "is_a|has_a|part_of|causes|enables|contradicts|supports|'
                f'similar_to|opposite_of|depends_on|precedes|specializes|generalizes|related_to", '
                f'"strength": 0.0-1.0}}], '
                f'"domains": ["str"]}}'
            )
            response = llm.generate(prompt, max_tokens=700, temperature=0.4)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            nodes = [ConceptNode(
                name=n.get("name", ""),
                domain=n.get("domain", ""),
                description=n.get("description", ""),
                properties=n.get("properties", {})
            ) for n in data.get("nodes", [])]

            graph = KnowledgeGraph(
                topic=topic, nodes=nodes,
                edges=data.get("edges", []),
                domains=data.get("domains", [])
            )

            self._graphs.append(graph)
            self._stats["total_graphs"] += 1
            self._stats["total_concepts_mapped"] += len(nodes)
            self._stats["total_connections"] += len(graph.edges)
            self._save_data()
            return graph

        except Exception as e:
            logger.debug(f"Knowledge graph building failed: {e}")
            return KnowledgeGraph(topic=topic)

    def synthesize_domains(self, domains: List[str]) -> Synthesis:
        """Synthesize knowledge across multiple domains."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Synthesize knowledge across these domains:\n{', '.join(domains)}\n\n"
                f"Return JSON:\n"
                f'{{"unified_understanding": "how these domains connect", '
                f'"cross_domain_links": [{{"domain_a": "str", "concept_a": "str", '
                f'"domain_b": "str", "concept_b": "str", "connection": "str"}}], '
                f'"emergent_insights": ["insights from combining domains"], '
                f'"coherence": 0.0-1.0, '
                f'"concepts": ["key concepts across domains"]}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.4)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            syn = Synthesis(
                domains=domains,
                concepts=data.get("concepts", []),
                unified_understanding=data.get("unified_understanding", ""),
                cross_domain_links=data.get("cross_domain_links", []),
                emergent_insights=data.get("emergent_insights", []),
                coherence=data.get("coherence", 0.5)
            )

            self._syntheses.append(syn)
            self._stats["total_syntheses"] += 1
            self._save_data()
            return syn

        except Exception as e:
            logger.debug(f"Domain synthesis failed: {e}")
            return Synthesis(domains=domains)

    def find_connections(self, concept_a: str, concept_b: str) -> Dict[str, Any]:
        """Find semantic connections between two concepts."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Find all meaningful connections between:\n"
                f"A: {concept_a}\nB: {concept_b}\n\n"
                f"Return JSON:\n"
                f'{{"direct_connections": [{{"type": "str", "description": "str"}}], '
                f'"indirect_connections": [{{"path": ["intermediary concepts"], '
                f'"description": "str"}}], '
                f'"shared_properties": ["str"], '
                f'"shared_domains": ["str"], '
                f'"analogy": "str", '
                f'"connection_strength": 0.0-1.0}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            if not response.success or not response.text:
                return {"direct_connections": [], "connection_strength": 0.0}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"direct_connections": [], "connection_strength": 0.0}
            return data
        except Exception as e:
            logger.debug(f"Connection finding failed: {e}")
            return {"direct_connections": [], "connection_strength": 0.0}

    def build_ontology(self, domain: str) -> Dict[str, Any]:
        """Build a formal ontology for a domain."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Build a formal ontology for the domain: {domain}\n\n"
                f"Return JSON:\n"
                f'{{"domain": "str", '
                f'"top_level_categories": ["str"], '
                f'"hierarchy": [{{"concept": "str", "parent": "str or null", '
                f'"children": ["str"], "properties": ["str"]}}'
                f'], '
                f'"axioms": ["fundamental rules"], '
                f'"relationships": [{{"from": "str", "to": "str", "type": "str"}}]}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.3)
            if not response.success or not response.text:
                return {"domain": domain, "top_level_categories": []}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"domain": domain, "top_level_categories": []}
            return data
        except Exception as e:
            logger.debug(f"Ontology building failed: {e}")
            return {"domain": domain, "top_level_categories": []}

    def concept_map(self, central_concept: str) -> Dict[str, Any]:
        """Create a concept map radiating from a central concept."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Create a concept map with '{central_concept}' at the center.\n\n"
                f"Return JSON:\n"
                f'{{"center": "str", '
                f'"primary_branches": [{{"concept": "str", "relation": "str", '
                f'"sub_branches": [{{"concept": "str", "relation": "str"}}]}}'
                f'], '
                f'"cross_links": [{{"from": "str", "to": "str", "relation": "str"}}], '
                f'"total_concepts": int}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.4)
            if not response.success or not response.text:
                return {"center": central_concept, "primary_branches": []}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"center": central_concept, "primary_branches": []}
            return data
        except Exception as e:
            logger.debug(f"Concept mapping failed: {e}")
            return {"center": central_concept, "primary_branches": []}

    def _save_data(self):
        try:
            data = {
                "graphs": [g.to_dict() for g in self._graphs[-50:]],
                "syntheses": [s.to_dict() for s in self._syntheses[-100:]],
                "stats": self._stats
            }
            self._data_file.write_text(json.dumps(data, indent=2, default=str))
        except Exception as e:
            logger.warning(f"Save failed: {e}")

    def _load_data(self):
        try:
            if self._data_file.exists():
                data = json.loads(self._data_file.read_text())
                self._stats.update(data.get("stats", {}))
                logger.info("📂 Loaded knowledge integration data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def knowledge_gap(self, topic: str) -> Dict[str, Any]:
        """Identify gaps in understanding and suggest how to fill them."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Identify KNOWLEDGE GAPS about:\n'
                f'"{topic}"\n\n'
                f"Map what is known and unknown:\n"
                f"  1. WELL-ESTABLISHED: What do we know with high confidence?\n"
                f"  2. PARTIALLY UNDERSTOOD: What do we know incompletely?\n"
                f"  3. UNKNOWN: What important questions remain unanswered?\n"
                f"  4. LEARNING PATH: How to most efficiently fill the gaps?\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"well_established": ["facts known with high confidence"], '
                f'"partially_understood": ["areas of incomplete knowledge"], '
                f'"unknown": ["important unanswered questions"], '
                f'"critical_gaps": ["most important gaps to fill first"], '
                f'"learning_path": [{{"step": 1, "action": "what to learn", "resource_type": "book|course|practice|mentor"}}], '
                f'"current_understanding": 0.0-1.0}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a knowledge integration engine that maps the boundaries of understanding. "
                    "You identify what is known, what is partially known, and what remains unknown, "
                    "then suggest efficient learning paths to fill critical gaps. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.4, max_tokens=800
            )
            if response.success:
                from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"error": "Analysis failed"}
            return data
        except Exception as e:
            logger.debug(f"Knowledge gap analysis failed: {e}")
        return {"error": "Analysis failed"}


    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}


knowledge_integration = KnowledgeIntegrationEngine()