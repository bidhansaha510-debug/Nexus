"""
NEXUS AI — Associative Memory Engine
Neural-inspired associative recall: spreading activation network
for creative memory retrieval, priming, creative association chains,
and Hebbian learning-based consolidation.
"""

import threading
import json
import uuid
import math
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("associative_memory")

MEMORY_DIR = DATA_DIR / "memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class MemoryNode:
    """A node in the associative network."""
    node_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    concept: str = ""
    activation: float = 0.0          # current activation level (0.0-1.0)
    resting_level: float = 0.1       # baseline activation
    decay_rate: float = 0.05         # how fast activation decays
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    access_count: int = 0

    def to_dict(self) -> Dict:
        return {
            "node_id": self.node_id, "concept": self.concept,
            "activation": round(self.activation, 4),
            "resting_level": self.resting_level,
            "access_count": self.access_count,
        }


@dataclass
class MemoryLink:
    """A weighted link between two memory nodes."""
    source: str = ""           # node_id
    target: str = ""           # node_id
    weight: float = 0.5        # connection strength (0.0-1.0)
    link_type: str = "semantic" # semantic|causal|temporal|emotional
    co_activations: int = 0     # Hebbian counter


class AssociativeMemoryEngine:
    """
    Neural-inspired associative recall — spreading activation network
    for creative memory retrieval, context priming, long-chain
    association, and Hebbian learning.
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

        self._nodes: Dict[str, MemoryNode] = {}     # node_id → MemoryNode
        self._concept_index: Dict[str, str] = {}     # concept → node_id
        self._links: List[MemoryLink] = []
        self._adjacency: Dict[str, List[Tuple[str, float]]] = {}  # node_id → [(target_id, weight)]
        self._running = False
        self._data_file = MEMORY_DIR / "associative_memory.json"

        self._stats = {
            "total_nodes": 0, "total_links": 0,
            "total_activations": 0, "total_primes": 0,
            "total_recalls": 0, "total_consolidations": 0
        }

        self._load_data()
        logger.info("✅ Associative Memory Engine initialized")

    def start(self):
        self._running = True
        logger.info("🧠 Associative Memory started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🧠 Associative Memory stopped")

    # ─── Internal helpers ────────────────────────────────────────────────────

    def _get_or_create_node(self, concept: str) -> MemoryNode:
        """Get existing node or create a new one for this concept."""
        concept_key = concept.strip().lower()
        if concept_key in self._concept_index:
            return self._nodes[self._concept_index[concept_key]]

        node = MemoryNode(concept=concept_key)
        self._nodes[node.node_id] = node
        self._concept_index[concept_key] = node.node_id
        self._adjacency.setdefault(node.node_id, [])
        self._stats["total_nodes"] += 1
        return node

    def _add_link(self, source_id: str, target_id: str, weight: float = 0.5,
                  link_type: str = "semantic"):
        """Add or strengthen a link between two nodes."""
        # Check if link exists
        for link in self._links:
            if link.source == source_id and link.target == target_id:
                # Strengthen existing link (Hebbian)
                link.weight = min(1.0, link.weight + 0.1)
                link.co_activations += 1
                return link

        link = MemoryLink(source=source_id, target=target_id,
                          weight=weight, link_type=link_type)
        self._links.append(link)
        self._adjacency.setdefault(source_id, []).append((target_id, weight))
        self._adjacency.setdefault(target_id, []).append((source_id, weight))
        self._stats["total_links"] += 1
        return link

    def _spreading_activation(self, start_id: str, depth: int = 3,
                              threshold: float = 0.1) -> Dict[str, float]:
        """Core spreading activation from a source node."""
        activations: Dict[str, float] = {}
        start_node = self._nodes.get(start_id)
        if not start_node:
            return activations

        start_node.activation = 1.0
        activations[start_id] = 1.0

        current_layer = {start_id}
        for d in range(depth):
            decay = 0.6 ** (d + 1)  # activation decays with distance
            next_layer: Set[str] = set()
            for node_id in current_layer:
                for target_id, weight in self._adjacency.get(node_id, []):
                    spread = activations.get(node_id, 0) * weight * decay
                    if spread >= threshold:
                        current = activations.get(target_id, 0)
                        activations[target_id] = min(1.0, current + spread)
                        if target_id in self._nodes:
                            self._nodes[target_id].activation = activations[target_id]
                        next_layer.add(target_id)
            current_layer = next_layer

        return activations

    # ─── Core Methods ────────────────────────────────────────────────────────

    def associate(self, concept: str) -> Dict[str, Any]:
        """Retrieve related concepts via spreading activation."""
        try:
            # First, use LLM to generate associations and build/update the network
            from llm.llama_interface import llm
            prompt = (
                f"ASSOCIATIVE RECALL — Spreading Activation:\n"
                f'Seed concept: "{concept}"\n\n'
                f"Generate a rich association network from this concept.\n"
                f"Think of how a neural network activates related memories.\n\n"
                f"Return JSON:\n"
                f'{{"associations": [{{"concept": "str", '
                f'"strength": 0.0-1.0, '
                f'"link_type": "semantic|causal|temporal|emotional", '
                f'"why": "reason for the association"}}], '
                f'"strongest_association": "the most powerfully linked concept", '
                f'"weakest_but_interesting": "a faint but creative connection", '
                f'"association_chain": ["concept → A → B → C (chain of associations)"], '
                f'"emotional_resonance": "the emotional texture of this concept cluster", '
                f'"confidence": 0.0-1.0, '
                f'"summary": "one-line association map"}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.6)
            if not response.success or not response.text:
                return {"associations": [], "summary": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"associations": [], "summary": ""}

            # Build/update the network with the LLM's associations
            source_node = self._get_or_create_node(concept)
            source_node.access_count += 1
            source_node.activation = 1.0

            for assoc in data.get("associations", []):
                target_node = self._get_or_create_node(assoc.get("concept", ""))
                self._add_link(
                    source_node.node_id, target_node.node_id,
                    weight=float(assoc.get("strength", 0.5)),
                    link_type=assoc.get("link_type", "semantic"),
                )

            # Now do spreading activation through the built network
            activations = self._spreading_activation(source_node.node_id)

            # Enrich result with network info
            data["network_size"] = len(self._nodes)
            data["activated_nodes"] = len(activations)

            self._stats["total_activations"] += 1
            self._save_data()
            return data

        except Exception as e:
            logger.debug(f"Association failed: {e}")
            return {"associations": [], "summary": ""}

    def prime(self, context: str) -> Dict[str, Any]:
        """Pre-activate relevant memory nodes to bias future retrieval."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"MEMORY PRIMING — Context Pre-Activation:\n"
                f'Context: "{context}"\n\n'
                f"Identify the key concepts that should be pre-activated\n"
                f"in memory to prepare for processing related information.\n\n"
                f"Return JSON:\n"
                f'{{"primed_concepts": [{{"concept": "str", '
                f'"prime_strength": 0.0-1.0, '
                f'"expected_relevance": "why this should be pre-activated"}}], '
                f'"semantic_frame": "the overall frame being activated", '
                f'"ready_for": ["types of queries this priming prepares for"], '
                f'"inhibited_concepts": ["concepts suppressed by this context"], '
                f'"confidence": 0.0-1.0, '
                f'"summary": "one-line priming status"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            if not response.success or not response.text:
                return {"primed_concepts": [], "semantic_frame": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"primed_concepts": [], "semantic_frame": ""}

            # Actually prime the network
            for pc in data.get("primed_concepts", []):
                node = self._get_or_create_node(pc.get("concept", ""))
                node.activation = float(pc.get("prime_strength", 0.5))

            self._stats["total_primes"] += 1
            self._save_data()
            return data

        except Exception as e:
            logger.debug(f"Priming failed: {e}")
            return {"primed_concepts": [], "semantic_frame": ""}

    def creative_recall(self, seed: str) -> Dict[str, Any]:
        """Follow long chains of loose associations for creative inspiration."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"CREATIVE RECALL — Long-Chain Association:\n"
                f'Seed: "{seed}"\n\n'
                f"Follow a chain of 8-10 associations, letting each step get\n"
                f"FURTHER from the original. Allow creative leaps.\n"
                f"The endpoint should be surprisingly different from the start.\n\n"
                f"Return JSON:\n"
                f'{{"chain": [{{"step": 1, "concept": "str", '
                f'"connection": "why this follows from the previous"}}], '
                f'"creative_distance": "how far the endpoint is from the seed", '
                f'"serendipity_moment": "the most surprising leap in the chain", '
                f'"creative_spark": "a novel idea that emerges from connecting start and end", '
                f'"confidence": 0.0-1.0, '
                f'"summary": "one-line creative discovery"}}'
            )
            response = llm.generate(prompt, max_tokens=700, temperature=0.8)
            if not response.success or not response.text:
                return {"chain": [], "creative_spark": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"chain": [], "creative_spark": ""}

            # Build network from chain
            prev_node = self._get_or_create_node(seed)
            for step in data.get("chain", []):
                next_node = self._get_or_create_node(step.get("concept", ""))
                self._add_link(prev_node.node_id, next_node.node_id,
                               weight=0.3, link_type="semantic")
                prev_node = next_node

            self._stats["total_recalls"] += 1
            self._save_data()
            return data

        except Exception as e:
            logger.debug(f"Creative recall failed: {e}")
            return {"chain": [], "creative_spark": ""}

    def memory_consolidate(self) -> Dict[str, Any]:
        """Strengthen frequent pathways and prune weak ones (Hebbian)."""
        try:
            pruned = 0
            strengthened = 0

            # Strengthen links with high co-activation (Hebbian: fire together, wire together)
            for link in self._links:
                if link.co_activations >= 3:
                    link.weight = min(1.0, link.weight + 0.05)
                    strengthened += 1

            # Prune very weak links
            before = len(self._links)
            self._links = [l for l in self._links if l.weight >= 0.05]
            pruned = before - len(self._links)

            # Rebuild adjacency
            self._adjacency = {}
            for link in self._links:
                self._adjacency.setdefault(link.source, []).append((link.target, link.weight))
                self._adjacency.setdefault(link.target, []).append((link.source, link.weight))

            # Decay all activations toward resting level
            for node in self._nodes.values():
                node.activation = node.resting_level

            self._stats["total_consolidations"] += 1
            self._stats["total_links"] = len(self._links)
            self._save_data()

            return {
                "strengthened": strengthened,
                "pruned": pruned,
                "total_nodes": len(self._nodes),
                "total_links": len(self._links),
                "summary": f"Consolidated: {strengthened} strengthened, {pruned} pruned",
                "confidence": 0.9,
            }

        except Exception as e:
            logger.debug(f"Consolidation failed: {e}")
            return {"strengthened": 0, "pruned": 0, "summary": "Consolidation failed"}

    # ─── Persistence ─────────────────────────────────────────────────────────

    def _save_data(self):
        try:
            data = {
                "nodes": {nid: n.to_dict() for nid, n in list(self._nodes.items())[-500:]},
                "concept_index": dict(list(self._concept_index.items())[-500:]),
                "links": [{"s": l.source, "t": l.target, "w": round(l.weight, 3),
                           "lt": l.link_type, "co": l.co_activations}
                          for l in self._links[-2000:]],
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
                # Restore nodes
                for nid, nd in data.get("nodes", {}).items():
                    node = MemoryNode(
                        node_id=nid, concept=nd.get("concept", ""),
                        activation=nd.get("activation", 0.0),
                        resting_level=nd.get("resting_level", 0.1),
                        access_count=nd.get("access_count", 0),
                    )
                    self._nodes[nid] = node
                # Restore concept index
                self._concept_index = data.get("concept_index", {})
                # Restore links
                for ld in data.get("links", []):
                    link = MemoryLink(
                        source=ld.get("s", ""), target=ld.get("t", ""),
                        weight=ld.get("w", 0.5), link_type=ld.get("lt", "semantic"),
                        co_activations=ld.get("co", 0),
                    )
                    self._links.append(link)
                    self._adjacency.setdefault(link.source, []).append((link.target, link.weight))
                    self._adjacency.setdefault(link.target, []).append((link.source, link.weight))
                logger.info(f"📂 Loaded associative memory: {len(self._nodes)} nodes, {len(self._links)} links")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}


associative_memory = AssociativeMemoryEngine()
