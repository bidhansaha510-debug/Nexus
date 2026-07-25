"""
NEXUS AI — Conceptual Blending Engine
Merge disparate concepts into novel hybrid ideas,
cross-domain fusion, emergent property discovery.
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

from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("conceptual_blending")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)

class BlendType(Enum):
    FUSION = "fusion"
    COMPOSITION = "composition"
    COMPLETION = "completion"
    ELABORATION = "elaboration"
    COMPRESSION = "compression"
    METAPHORICAL = "metaphorical"

@dataclass
class ConceptBlend:
    blend_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    input_concepts: List[str] = field(default_factory=list)
    blended_concept: str = ""
    blend_type: BlendType = BlendType.FUSION
    emergent_properties: List[str] = field(default_factory=list)
    shared_structure: str = ""
    novelty_score: float = 0.5
    usefulness_score: float = 0.5
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "blend_id": self.blend_id,
            "input_concepts": self.input_concepts,
            "blended_concept": self.blended_concept,
            "blend_type": self.blend_type.value,
            "emergent_properties": self.emergent_properties,
            "shared_structure": self.shared_structure,
            "novelty_score": self.novelty_score,
            "usefulness_score": self.usefulness_score,
            "description": self.description,
            "created_at": self.created_at
        }

class ConceptualBlendingEngine:
    """
    Merge disparate concepts into novel hybrids — creative fusion,
    emergent property discovery, cross-domain innovation.
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

        self._blends: List[ConceptBlend] = []
        self._running = False
        self._data_file = COGNITION_DIR / "conceptual_blending.json"

        self._stats = {
            "total_blends": 0, "total_fusions": 0,
            "total_inventions": 0, "avg_novelty": 0.0
        }

        self._load_data()
        logger.info("✅ Conceptual Blending Engine initialized")

    def start(self):
        self._running = True
        logger.info("🔀 Conceptual Blending started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🔀 Conceptual Blending stopped")

    def blend(self, concept_a: str, concept_b: str) -> ConceptBlend:
        """Blend two concepts into a novel hybrid."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Blend these two concepts into a novel hybrid idea:\n"
                f"Concept A: {concept_a}\nConcept B: {concept_b}\n\n"
                f"Return JSON:\n"
                f'{{"blended_concept": "name of the new hybrid concept", '
                f'"blend_type": "fusion|composition|completion|elaboration|compression|metaphorical", '
                f'"emergent_properties": ["new properties that neither concept had alone"], '
                f'"shared_structure": "what the two concepts have in common", '
                f'"novelty_score": 0.0-1.0, '
                f'"usefulness_score": 0.0-1.0, '
                f'"description": "explain the blended concept", '
                f'"real_world_application": "how this could be used"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.6)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            bt_map = {b.value: b for b in BlendType}

            blend = ConceptBlend(
                input_concepts=[concept_a, concept_b],
                blended_concept=data.get("blended_concept", ""),
                blend_type=bt_map.get(data.get("blend_type", "fusion"), BlendType.FUSION),
                emergent_properties=data.get("emergent_properties", []),
                shared_structure=data.get("shared_structure", ""),
                novelty_score=data.get("novelty_score", 0.5),
                usefulness_score=data.get("usefulness_score", 0.5),
                description=data.get("description", "")
            )

            self._blends.append(blend)
            self._stats["total_blends"] += 1
            self._stats["total_fusions"] += 1
            self._update_avg_novelty(blend.novelty_score)
            self._save_data()
            return blend

        except Exception as e:
            logger.debug(f"Conceptual blending failed: {e}")
            return ConceptBlend(input_concepts=[concept_a, concept_b])

    def multi_blend(self, concepts: List[str]) -> Dict[str, Any]:
        """Blend multiple concepts together."""
        try:
            from llm.llama_interface import llm
            concept_list = ", ".join(concepts)
            prompt = (
                f"Blend all of these concepts into a single novel idea:\n"
                f"Concepts: {concept_list}\n\n"
                f"Return JSON:\n"
                f'{{"hybrid_name": "str", '
                f'"description": "what this new concept is", '
                f'"emergent_properties": ["new properties"], '
                f'"contributing_elements": {{"concept": "what it contributes"}}, '
                f'"novelty_score": 0.0-1.0, '
                f'"applications": ["potential uses"], '
                f'"analogous_to": "what existing thing this most resembles"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.6)
            if not response.success or not response.text:
                return {"hybrid_name": "", "description": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"hybrid_name": "", "description": ""}
            self._stats["total_blends"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Multi-blend failed: {e}")
            return {"hybrid_name": "", "description": ""}

    def invent(self, problem: str) -> Dict[str, Any]:
        """Invent a novel solution by blending concepts from different domains."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Invent a novel solution by blending concepts from different fields:\n"
                f"Problem: {problem}\n\n"
                f"Return JSON:\n"
                f'{{"invention_name": "str", '
                f'"domains_blended": ["field 1", "field 2"], '
                f'"concept_from_each": {{"field": "borrowed concept"}}, '
                f'"how_it_works": "str", '
                f'"emergent_advantage": "what makes this better than existing solutions", '
                f'"feasibility": 0.0-1.0, '
                f'"novelty": 0.0-1.0, '
                f'"similar_inventions": ["existing things that used similar blending"]}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.7)
            if not response.success or not response.text:
                return {"invention_name": "", "how_it_works": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"invention_name": "", "how_it_works": ""}
            self._stats["total_inventions"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Invention failed: {e}")
            return {"invention_name": "", "how_it_works": ""}

    def find_shared_structure(self, concept_a: str, concept_b: str) -> Dict[str, Any]:
        """Identify shared structural patterns between two concepts."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Find the deep shared structure between:\n"
                f"A: {concept_a}\nB: {concept_b}\n\n"
                f"Return JSON:\n"
                f'{{"shared_patterns": ["structural similarities"], '
                f'"unique_to_a": ["str"], '
                f'"unique_to_b": ["str"], '
                f'"structural_mapping": {{"element_in_a": "corresponding_element_in_b"}}, '
                f'"abstraction": "the general pattern they both embody", '
                f'"transfer_potential": 0.0-1.0}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            if not response.success or not response.text:
                return {"shared_patterns": [], "abstraction": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"shared_patterns": [], "abstraction": ""}
            return data
        except Exception as e:
            logger.debug(f"Shared structure analysis failed: {e}")
            return {"shared_patterns": [], "abstraction": ""}

    def _update_avg_novelty(self, new_score: float):
        n = self._stats["total_blends"]
        old = self._stats["avg_novelty"]
        self._stats["avg_novelty"] = old + (new_score - old) / max(n, 1)

    def _save_data(self):
        try:
            data = {
                "blends": [b.to_dict() for b in self._blends[-200:]],
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
                logger.info("📂 Loaded conceptual blending data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def triple_blend(self, concept_a: str, concept_b: str, concept_c: str) -> Dict[str, Any]:
        """Blend three concepts to create an emergent innovation."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'TRIPLE BLEND these three concepts into something new:\n'
                f'A: "{concept_a}"\nB: "{concept_b}"\nC: "{concept_c}"\n\n'
                f"Process:\n"
                f"  1. Find shared structural features across all three\n"
                f"  2. Identify unique properties each contributes\n"
                f"  3. Create a novel concept that emerges from their intersection\n"
                f"  4. Describe what this new concept looks/feels/works like\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"shared_structure": "what all three have in common", '
                f'"unique_contributions": {{"A": "what A adds", "B": "what B adds", "C": "what C adds"}}, '
                f'"blended_concept": "the emergent idea", '
                f'"description": "vivid description of the new concept", '
                f'"applications": ["practical uses"], '
                f'"novelty_score": 0.0-1.0}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a conceptual blending engine based on Fauconnier and Turner's theory. "
                    "You find deep structural similarities between seemingly unrelated concepts "
                    "and create genuinely novel emergent ideas. Respond ONLY with valid JSON."
                ),
                temperature=0.8, max_tokens=800
            )
            if response.success:
                from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"error": "Blend failed"}
            return data
        except Exception as e:
            logger.debug(f"Triple blend failed: {e}")
        return {"error": "Blend failed"}

    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}

conceptual_blending = ConceptualBlendingEngine()
