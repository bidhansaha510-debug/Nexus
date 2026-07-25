"""
NEXUS AI — Cross-Dimensional Reasoning Engine
N-dimensional pattern mapping: reasons across multiple abstract
dimensions simultaneously — hypercube analysis, dimensional collapse,
fractal pattern recognition, and cross-domain bridging.
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

logger = get_logger("cross_dimensional_reasoning")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)

class DimensionMode(Enum):
    HYPERCUBE = "hypercube"
    COLLAPSE = "collapse"
    FRACTAL = "fractal"
    BRIDGE = "bridge"

@dataclass
class DimensionalResult:
    result_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    problem: str = ""
    mode: DimensionMode = DimensionMode.HYPERCUBE
    dimensions_analyzed: int = 0
    insight: str = ""
    confidence: float = 0.5
    summary: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "result_id": self.result_id, "problem": self.problem[:200],
            "mode": self.mode.value,
            "dimensions_analyzed": self.dimensions_analyzed,
            "insight": self.insight[:300],
            "confidence": self.confidence,
            "summary": self.summary,
            "created_at": self.created_at
        }

class CrossDimensionalReasoningEngine:
    """
    N-dimensional pattern mapping — analyzes problems across
    orthogonal dimensions, collapses complexity, finds fractal patterns,
    and builds bridges between domains.
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

        self._results: List[DimensionalResult] = []
        self._running = False
        self._data_file = COGNITION_DIR / "cross_dimensional.json"

        self._stats = {
            "total_hypercubes": 0, "total_collapses": 0,
            "total_fractals": 0, "total_bridges": 0
        }

        self._load_data()
        logger.info("✅ Cross-Dimensional Reasoning Engine initialized")

    def start(self):
        self._running = True
        logger.info("🌌 Cross-Dimensional Reasoning started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🌌 Cross-Dimensional Reasoning stopped")

    # ─── Core Methods ────────────────────────────────────────────────────────

    def hypercube_analyze(self, problem: str) -> DimensionalResult:
        """Map a problem across multiple orthogonal dimensions."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"HYPERCUBE ANALYSIS — Multi-Dimensional Mapping:\n"
                f'Problem: "{problem}"\n\n'
                f"Analyze this problem across 6 orthogonal dimensions:\n"
                f"  1. TIME: How it changes over time\n"
                f"  2. SCALE: How it looks at micro/meso/macro levels\n"
                f"  3. ABSTRACTION: Concrete → conceptual → meta\n"
                f"  4. DOMAIN: How it maps across fields (tech, biology, social)\n"
                f"  5. AGENCY: Individual → group → systemic forces\n"
                f"  6. ENTROPY: Order → complexity → chaos\n\n"
                f"Return JSON:\n"
                f'{{"dimensions": [{{"name": "str", "low_end": "the problem at the low extreme", '
                f'"high_end": "the problem at the high extreme", '
                f'"current_position": "where the problem currently sits", '
                f'"movement": "which direction it is trending"}}], '
                f'"cross_sections": ["interesting patterns visible when combining 2+ dimensions"], '
                f'"hidden_dimension": "a dimension not listed above that is secretly important", '
                f'"hypercube_insight": "what you can see from the N-dimensional view that is invisible from any single dimension", '
                f'"confidence": 0.0-1.0, '
                f'"summary": "one-line hypercube verdict"}}'
            )
            response = llm.generate(prompt, max_tokens=800, temperature=0.6)
            if not response.success or not response.text:
                return DimensionalResult(problem=problem)
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return DimensionalResult(problem=problem)

            result = DimensionalResult(
                problem=problem, mode=DimensionMode.HYPERCUBE,
                dimensions_analyzed=len(data.get("dimensions", [])),
                insight=data.get("hypercube_insight", ""),
                confidence=float(data.get("confidence", 0.5)),
                summary=data.get("summary", ""),
            )

            self._results.append(result)
            self._stats["total_hypercubes"] += 1
            self._save_data()
            return result

        except Exception as e:
            logger.debug(f"Hypercube analysis failed: {e}")
            return DimensionalResult(problem=problem)

    def dimensional_collapse(self, complex_data: str) -> Dict[str, Any]:
        """Reduce high-dimensional complexity to actionable insights."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"DIMENSIONAL COLLAPSE — Reduce Complexity:\n"
                f'Complex situation: "{complex_data}"\n\n'
                f"This situation has too many variables, angles, and dimensions.\n"
                f"Collapse it down to what ACTUALLY MATTERS:\n"
                f"  1. Identify all dimensions of complexity\n"
                f"  2. Rank them by true importance\n"
                f"  3. Collapse irrelevant dimensions\n"
                f"  4. Produce a simplified but accurate model\n\n"
                f"Return JSON:\n"
                f'{{"original_dimensions": ["all the axes of complexity"], '
                f'"importance_ranking": [{{"dimension": "str", "importance": 0.0-1.0, '
                f'"keep_or_collapse": "keep|collapse"}}], '
                f'"collapsed_model": "the simplified but accurate version", '
                f'"information_lost": "what nuance was sacrificed", '
                f'"compression_ratio": "how much simpler the new model is", '
                f'"actionable_insight": "the clear takeaway from the simplified model", '
                f'"confidence": 0.0-1.0, '
                f'"summary": "one-line collapsed insight"}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.4)
            if not response.success or not response.text:
                return {"collapsed_model": "", "actionable_insight": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"collapsed_model": "", "actionable_insight": ""}

            self._stats["total_collapses"] += 1
            self._save_data()
            return data

        except Exception as e:
            logger.debug(f"Dimensional collapse failed: {e}")
            return {"collapsed_model": "", "actionable_insight": ""}

    def fractal_pattern(self, phenomenon: str) -> Dict[str, Any]:
        """Identify self-similar patterns at different scales."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"FRACTAL PATTERN DETECTION — Self-Similarity Across Scales:\n"
                f'Phenomenon: "{phenomenon}"\n\n'
                f"Find the FRACTAL PATTERN — the same shape that repeats at:\n"
                f"  • Individual level\n"
                f"  • Group/organizational level\n"
                f"  • Societal/global level\n"
                f"  • Abstract/universal level\n\n"
                f"Return JSON:\n"
                f'{{"core_pattern": "the fundamental shape that repeats", '
                f'"scales": [{{"level": "individual|group|societal|universal", '
                f'"manifestation": "how the pattern appears at this scale", '
                f'"scale_specific_variation": "how it differs from other scales"}}], '
                f'"scaling_law": "the mathematical/logical rule governing repetition", '
                f'"predictive_power": "what this fractal lets you predict at other scales", '
                f'"boundary_conditions": "where the fractal breaks down", '
                f'"confidence": 0.0-1.0, '
                f'"summary": "one-line fractal insight"}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.5)
            if not response.success or not response.text:
                return {"core_pattern": "", "scales": []}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"core_pattern": "", "scales": []}

            self._stats["total_fractals"] += 1
            self._save_data()
            return data

        except Exception as e:
            logger.debug(f"Fractal pattern detection failed: {e}")
            return {"core_pattern": "", "scales": []}

    def dimensional_bridge(self, domain_a: str, domain_b: str = "") -> Dict[str, Any]:
        """Find hidden structural bridges between different domains."""
        if not domain_b:
            parts = domain_a.split(" and ", 1)
            if len(parts) == 2:
                domain_a, domain_b = parts
            else:
                domain_b = "a contrasting domain"
        try:
            from llm.llama_interface import llm
            prompt = (
                f"DIMENSIONAL BRIDGE — Cross-Domain Structure Mapping:\n"
                f'Domain A: "{domain_a}"\n'
                f'Domain B: "{domain_b}"\n\n'
                f"Find structural isomorphisms — places where the SHAPE of\n"
                f"one domain maps onto the other, even though the content differs.\n\n"
                f"Return JSON:\n"
                f'{{"structural_bridges": [{{"element_in_a": "str", '
                f'"element_in_b": "str", "shared_structure": "the isomorphism", '
                f'"bridge_strength": 0.0-1.0}}], '
                f'"deep_isomorphism": "the fundamental structural similarity", '
                f'"transfer_opportunities": ["what you can import from A to B and vice versa"], '
                f'"false_bridges": ["apparent similarities that are actually superficial"], '
                f'"novel_synthesis": "a new idea that only exists at the bridge between domains", '
                f'"confidence": 0.0-1.0, '
                f'"summary": "one-line bridge discovery"}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.5)
            if not response.success or not response.text:
                return {"structural_bridges": [], "deep_isomorphism": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"structural_bridges": [], "deep_isomorphism": ""}

            self._stats["total_bridges"] += 1
            self._save_data()
            return data

        except Exception as e:
            logger.debug(f"Dimensional bridge failed: {e}")
            return {"structural_bridges": [], "deep_isomorphism": ""}

    # ─── Persistence ─────────────────────────────────────────────────────────

    def _save_data(self):
        try:
            data = {
                "results": [r.to_dict() for r in self._results[-200:]],
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
                logger.info("📂 Loaded cross-dimensional data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}

cross_dimensional_reasoning = CrossDimensionalReasoningEngine()
