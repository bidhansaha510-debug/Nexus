"""
NEXUS AI — Spatial Reasoning Engine
Mental models for spatial relationships, geometric reasoning,
topology, path-finding, and spatial transformations.
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

logger = get_logger("spatial_reasoning")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)

class SpatialRelation(Enum):
    ABOVE = "above"
    BELOW = "below"
    LEFT_OF = "left_of"
    RIGHT_OF = "right_of"
    INSIDE = "inside"
    OUTSIDE = "outside"
    NEAR = "near"
    FAR = "far"
    ADJACENT = "adjacent"
    OVERLAPPING = "overlapping"
    BETWEEN = "between"
    SURROUNDING = "surrounding"
    CONTAINS = "contains"
    PARALLEL = "parallel"
    PERPENDICULAR = "perpendicular"

class TransformationType(Enum):
    ROTATION = "rotation"
    TRANSLATION = "translation"
    SCALING = "scaling"
    REFLECTION = "reflection"
    PROJECTION = "projection"

@dataclass
class SpatialModel:
    model_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    entities: List[Dict[str, Any]] = field(default_factory=list)
    relations: List[Dict[str, Any]] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    dimensions: int = 2
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "model_id": self.model_id, "description": self.description,
            "entities": self.entities, "relations": self.relations,
            "properties": self.properties, "dimensions": self.dimensions,
            "created_at": self.created_at
        }

@dataclass
class SpatialQuery:
    query_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    question: str = ""
    answer: str = ""
    spatial_model: Optional[SpatialModel] = None
    confidence: float = 0.5
    reasoning_steps: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "query_id": self.query_id, "question": self.question,
            "answer": self.answer, "confidence": self.confidence,
            "reasoning_steps": self.reasoning_steps,
            "created_at": self.created_at
        }

@dataclass
class PathResult:
    path_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    start: str = ""
    end: str = ""
    path: List[str] = field(default_factory=list)
    distance_estimate: str = ""
    obstacles: List[str] = field(default_factory=list)
    alternative_paths: List[List[str]] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "path_id": self.path_id, "start": self.start, "end": self.end,
            "path": self.path, "distance_estimate": self.distance_estimate,
            "obstacles": self.obstacles,
            "alternative_paths": self.alternative_paths
        }

class SpatialReasoningEngine:
    """
    Reasons about spatial relationships, constructs mental models,
    performs geometric reasoning, and solves spatial problems.
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

        self._models: List[SpatialModel] = []
        self._queries: List[SpatialQuery] = []
        self._running = False
        self._data_file = COGNITION_DIR / "spatial_reasoning.json"

        self._stats = {
            "total_models": 0, "total_queries": 0,
            "total_paths": 0, "total_transformations": 0
        }

        self._load_data()
        logger.info("✅ Spatial Reasoning Engine initialized")

    def start(self):
        self._running = True
        logger.info("📐 Spatial Reasoning started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("📐 Spatial Reasoning stopped")

    # ─── Core Operations ─────────────────────────────────────────────────────

    def build_spatial_model(self, scene_description: str) -> SpatialModel:
        """Build a mental spatial model from a description."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Build a spatial model from this description:\n{scene_description}\n\n"
                f"Return JSON:\n"
                f'{{"entities": [{{"name": "str", "position": "str", "size": "str", "shape": "str"}}], '
                f'"relations": [{{"entity_a": "str", "relation": "above|below|left_of|right_of|'
                f'inside|outside|near|far|adjacent|overlapping|between|contains", "entity_b": "str"}}], '
                f'"dimensions": 2 or 3, '
                f'"properties": {{"scale": "str", "coordinate_system": "str"}}}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.3)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            model = SpatialModel(
                description=scene_description,
                entities=data.get("entities", []),
                relations=data.get("relations", []),
                properties=data.get("properties", {}),
                dimensions=data.get("dimensions", 2)
            )

            self._models.append(model)
            self._stats["total_models"] += 1
            self._save_data()
            return model

        except Exception as e:
            logger.debug(f"Spatial model building failed: {e}")
            return SpatialModel(description=scene_description)

    def query_spatial(self, question: str, context: str = "") -> SpatialQuery:
        """Answer a spatial reasoning question."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Answer this spatial reasoning question step-by-step.\n"
                f"Context: {context}\nQuestion: {question}\n\n"
                f"Return JSON:\n"
                f'{{"answer": "str", "confidence": 0.0-1.0, '
                f'"reasoning_steps": ["step 1", "step 2", ...], '
                f'"spatial_relations_used": ["str"]}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.3)
            if not response.success or not response.text:
                return SpatialQuery(question=question, answer=f"Error: {e}")
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return SpatialQuery(question=question, answer=f"Error: {e}")

            query = SpatialQuery(
                question=question,
                answer=data.get("answer", "Unknown"),
                confidence=data.get("confidence", 0.5),
                reasoning_steps=data.get("reasoning_steps", [])
            )

            self._queries.append(query)
            self._stats["total_queries"] += 1
            self._save_data()
            return query

        except Exception as e:
            logger.debug(f"Spatial query failed: {e}")
            return SpatialQuery(question=question, answer=f"Error: {e}")

    def find_path(self, start: str, end: str, environment: str = "") -> PathResult:
        """Find a conceptual path between two locations."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Find a path from '{start}' to '{end}'.\n"
                f"Environment: {environment}\n\n"
                f"Return JSON:\n"
                f'{{"path": ["waypoint1", "waypoint2", ...], '
                f'"distance_estimate": "str", '
                f'"obstacles": ["str"], '
                f'"alternative_paths": [["alt_waypoint1", "alt_waypoint2"]]}}'
            )
            response = llm.generate(prompt, max_tokens=400, temperature=0.3)
            if not response.success or not response.text:
                return PathResult(start=start, end=end)
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return PathResult(start=start, end=end)

            result = PathResult(
                start=start, end=end,
                path=data.get("path", []),
                distance_estimate=data.get("distance_estimate", "unknown"),
                obstacles=data.get("obstacles", []),
                alternative_paths=data.get("alternative_paths", [])
            )

            self._stats["total_paths"] += 1
            self._save_data()
            return result

        except Exception as e:
            logger.debug(f"Path finding failed: {e}")
            return PathResult(start=start, end=end)

    def transform(self, object_desc: str, transformation: str) -> Dict[str, Any]:
        """Apply a spatial transformation and describe the result."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Apply spatial transformation to this object:\n"
                f"Object: {object_desc}\n"
                f"Transformation: {transformation}\n\n"
                f"Return JSON:\n"
                f'{{"original": "str", "transformed": "str", '
                f'"transformation_type": "rotation|translation|scaling|reflection|projection", '
                f'"description": "what changed", '
                f'"properties_preserved": ["str"], "properties_changed": ["str"]}}'
            )
            response = llm.generate(prompt, max_tokens=400, temperature=0.3)
            if not response.success or not response.text:
                return {"original": object_desc, "transformed": "unknown"}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"original": object_desc, "transformed": "unknown"}
            self._stats["total_transformations"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Transform failed: {e}")
            return {"original": object_desc, "transformed": "unknown"}

    def compare_layouts(self, layout_a: str, layout_b: str) -> Dict[str, Any]:
        """Compare two spatial arrangements."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Compare these two spatial layouts:\nA: {layout_a}\nB: {layout_b}\n\n"
                f"Return JSON:\n"
                f'{{"similarities": ["str"], "differences": ["str"], '
                f'"structural_alignment": 0.0-1.0, '
                f'"which_is_better": "A|B|equal", "reasoning": "str"}}'
            )
            response = llm.generate(prompt, max_tokens=400, temperature=0.3)
            if not response.success or not response.text:
                return {"similarities": [], "differences": [], "structural_alignment": 0.5}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"similarities": [], "differences": [], "structural_alignment": 0.5}
            return data
        except Exception as e:
            logger.debug(f"Layout comparison failed: {e}")
            return {"similarities": [], "differences": [], "structural_alignment": 0.5}

    # ─── Persistence ──────────────────────────────────────────────────────────

    def _save_data(self):
        try:
            data = {
                "models": [m.to_dict() for m in self._models[-100:]],
                "queries": [q.to_dict() for q in self._queries[-200:]],
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
                logger.info(f"📂 Loaded spatial reasoning data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}

spatial_reasoning = SpatialReasoningEngine()
