"""
NEXUS AI — Analogy Generator Engine
Create novel analogies, metaphor mapping,
cross-domain comparisons, explanation by analogy.
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

logger = get_logger("analogy_generator")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)


class AnalogyType(Enum):
    STRUCTURAL = "structural"
    FUNCTIONAL = "functional"
    METAPHORICAL = "metaphorical"
    PROPORTIONAL = "proportional"    # A is to B as C is to D
    CAUSAL = "causal"
    EXPLANATORY = "explanatory"
    CREATIVE = "creative"


@dataclass
class Analogy:
    analogy_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source: str = ""
    target: str = ""
    analogy_type: AnalogyType = AnalogyType.STRUCTURAL
    mapping: str = ""
    explanation: str = ""
    strength: float = 0.5
    limitations: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "analogy_id": self.analogy_id,
            "source": self.source[:200], "target": self.target[:200],
            "analogy_type": self.analogy_type.value,
            "mapping": self.mapping, "explanation": self.explanation,
            "strength": self.strength, "limitations": self.limitations,
            "created_at": self.created_at
        }


class AnalogyGeneratorEngine:
    """
    Create novel analogies for explanation and insight —
    metaphor mapping, cross-domain comparison, proportional analogies.
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

        self._analogies: List[Analogy] = []
        self._running = False
        self._data_file = COGNITION_DIR / "analogy_generator.json"

        self._stats = {
            "total_analogies": 0, "total_explanations": 0,
            "total_metaphors": 0, "total_proportion_analogies": 0
        }

        self._load_data()
        logger.info("✅ Analogy Generator Engine initialized")

    def start(self):
        self._running = True
        logger.info("🔗 Analogy Generator started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🔗 Analogy Generator stopped")

    def generate_analogy(self, concept: str, audience: str = "general") -> Analogy:
        """Generate a novel analogy to explain a concept."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Create a brilliant analogy to explain:\n{concept}\n"
                f"Audience: {audience}\n\n"
                f"Return JSON:\n"
                f'{{"source": "the familiar thing to compare to", '
                f'"target": "the concept being explained", '
                f'"analogy_type": "structural|functional|metaphorical|proportional|causal|explanatory|creative", '
                f'"mapping": "X is like Y because...", '
                f'"explanation": "detailed explanation of how the analogy works", '
                f'"strength": 0.0-1.0, '
                f'"limitations": ["where the analogy breaks down"], '
                f'"aha_moment": "the key insight the analogy reveals"}}'
            )
            response = llm.generate(prompt, max_tokens=400, temperature=0.6)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            at_map = {a.value: a for a in AnalogyType}

            analogy = Analogy(
                source=data.get("source", ""),
                target=data.get("target", concept),
                analogy_type=at_map.get(data.get("analogy_type", "explanatory"), AnalogyType.EXPLANATORY),
                mapping=data.get("mapping", ""),
                explanation=data.get("explanation", ""),
                strength=data.get("strength", 0.5),
                limitations=data.get("limitations", [])
            )

            self._analogies.append(analogy)
            self._stats["total_analogies"] += 1
            self._save_data()
            return analogy

        except Exception as e:
            logger.debug(f"Analogy generation failed: {e}")
            return Analogy(target=concept)

    def explain_by_analogy(self, complex_topic: str, familiar_domain: str = "") -> Dict[str, Any]:
        """Explain a complex topic using analogies from a familiar domain."""
        try:
            from llm.llama_interface import llm
            domain_str = f" using concepts from {familiar_domain}" if familiar_domain else ""
            prompt = (
                f"Explain this complex topic{domain_str}:\n{complex_topic}\n\n"
                f"Return JSON:\n"
                f'{{"main_analogy": "the primary analogy", '
                f'"step_by_step": [{{"concept": "str", "analogy": "str"}}], '
                f'"intuitive_summary": "one-line analogy-based summary", '
                f'"visual_analogy": "an analogy you can picture in your mind", '
                f'"common_misconception": "what analogy people usually use that is wrong", '
                f'"layers": [{{"level": "beginner|intermediate|advanced", '
                f'"analogy": "str"}}]}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.5)
            if not response.success or not response.text:
                return {"main_analogy": "", "step_by_step": []}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"main_analogy": "", "step_by_step": []}
            self._stats["total_explanations"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Explanation by analogy failed: {e}")
            return {"main_analogy": "", "step_by_step": []}

    def find_metaphor(self, abstract_concept: str) -> Dict[str, Any]:
        """Find powerful metaphors for an abstract concept."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Find powerful metaphors for: {abstract_concept}\n\n"
                f"Return JSON:\n"
                f'{{"metaphors": [{{"metaphor": "str", '
                f'"resonance": 0.0-1.0, '
                f'"cultural_universality": 0.0-1.0, '
                f'"emotional_impact": "str"}}], '
                f'"best_metaphor": "the single most powerful one", '
                f'"dead_metaphors": ["overused metaphors to avoid"], '
                f'"novel_metaphor": "a completely original metaphor", '
                f'"embodied_metaphor": "a metaphor based on physical experience"}}'
            )
            response = llm.generate(prompt, max_tokens=400, temperature=0.6)
            if not response.success or not response.text:
                return {"metaphors": [], "best_metaphor": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"metaphors": [], "best_metaphor": ""}
            self._stats["total_metaphors"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Metaphor finding failed: {e}")
            return {"metaphors": [], "best_metaphor": ""}

    def proportional_analogy(self, a: str, b: str, c: str) -> Dict[str, Any]:
        """Complete a proportional analogy: A is to B as C is to ?"""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Complete this proportional analogy:\n"
                f"{a} is to {b} as {c} is to ?\n\n"
                f"Return JSON:\n"
                f'{{"answer": "what completes the analogy", '
                f'"relationship": "the relationship between A and B", '
                f'"explanation": "why this answer follows the same pattern", '
                f'"alternative_answers": ["other valid completions"], '
                f'"confidence": 0.0-1.0, '
                f'"pattern_type": "the type of relationship (functional, causal, etc)"}}'
            )
            response = llm.generate(prompt, max_tokens=300, temperature=0.4)
            if not response.success or not response.text:
                return {"answer": "", "confidence": 0.0}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"answer": "", "confidence": 0.0}
            self._stats["total_proportion_analogies"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Proportional analogy failed: {e}")
            return {"answer": "", "confidence": 0.0}

    def _save_data(self):
        try:
            data = {
                "analogies": [a.to_dict() for a in self._analogies[-200:]],
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
                logger.info("📂 Loaded analogy generator data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def deep_analogy(self, concept: str) -> Dict[str, Any]:
        """Generate a deep structural analogy that illuminates a concept."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Generate a DEEP ANALOGY for:\n'
                f'"{concept}"\n\n'
                f"Find an analogy that is:\n"
                f"  1. STRUCTURAL (not just surface similarity)\n"
                f"  2. FROM A DIFFERENT DOMAIN (surprising connection)\n"
                f"  3. ILLUMINATING (reveals something non-obvious)\n"
                f"  4. RICH (multiple mapping points, not just one)\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"source_domain": "where the analogy comes from", '
                f'"analogy_statement": "X is like Y because...", '
                f'"mapping_points": [{{"source": "element in analogy", "target": "element in concept", "insight": "what this mapping reveals"}}], '
                f'"where_analogy_breaks": "limits of this analogy", '
                f'"surprise_factor": 0.0-1.0, '
                f'"explanatory_power": 0.0-1.0}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are an analogy generation engine based on Gentner's structure-mapping theory. "
                    "You find deep, structural analogies that illuminate concepts by connecting them "
                    "to surprising domains. Go beyond surface similarity. Respond ONLY with valid JSON."
                ),
                temperature=0.7, max_tokens=800
            )
            if response.success:
                from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"error": "Analogy generation failed"}
            return data
        except Exception as e:
            logger.debug(f"Deep analogy failed: {e}")
        return {"error": "Analogy generation failed"}


    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}


analogy_generator = AnalogyGeneratorEngine()
