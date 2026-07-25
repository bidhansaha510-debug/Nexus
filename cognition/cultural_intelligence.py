"""
NEXUS AI — Cultural Intelligence Engine
Cross-cultural understanding, cultural context,
social norms awareness, intercultural communication.
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

logger = get_logger("cultural_intelligence")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)

class CulturalDimension(Enum):
    INDIVIDUALISM = "individualism"
    COLLECTIVISM = "collectivism"
    HIGH_CONTEXT = "high_context"
    LOW_CONTEXT = "low_context"
    HIERARCHICAL = "hierarchical"
    EGALITARIAN = "egalitarian"
    MONOCHRONIC = "monochronic"
    POLYCHRONIC = "polychronic"

@dataclass
class CulturalInsight:
    insight_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    topic: str = ""
    cultural_context: str = ""
    dimensions: List[CulturalDimension] = field(default_factory=list)
    norms: List[str] = field(default_factory=list)
    taboos: List[str] = field(default_factory=list)
    communication_style: str = ""
    sensitivity_score: float = 0.5
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "insight_id": self.insight_id, "topic": self.topic[:200],
            "cultural_context": self.cultural_context,
            "dimensions": [d.value for d in self.dimensions],
            "norms": self.norms, "taboos": self.taboos,
            "communication_style": self.communication_style,
            "sensitivity_score": self.sensitivity_score,
            "created_at": self.created_at
        }

class CulturalIntelligenceEngine:
    """
    Cross-cultural understanding — social norms, intercultural
    communication, cultural sensitivity, context awareness.
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

        self._insights: List[CulturalInsight] = []
        self._running = False
        self._data_file = COGNITION_DIR / "cultural_intelligence.json"

        self._stats = {
            "total_analyses": 0, "total_sensitivity_checks": 0,
            "total_translations": 0, "total_comparisons": 0
        }

        self._load_data()
        logger.info("✅ Cultural Intelligence Engine initialized")

    def start(self):
        self._running = True
        logger.info("🌍 Cultural Intelligence started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🌍 Cultural Intelligence stopped")

    def analyze_cultural_context(self, topic: str, culture: str = "") -> CulturalInsight:
        """Analyze the cultural context of a topic."""
        try:
            from llm.llama_interface import llm
            culture_str = f" in {culture}" if culture else ""
            prompt = (
                f"Analyze the cultural context of{culture_str}:\n{topic}\n\n"
                f"Return JSON:\n"
                f'{{"cultural_context": "relevant cultural background", '
                f'"dimensions": ["individualism|collectivism|high_context|low_context|hierarchical|egalitarian|monochronic|polychronic"], '
                f'"norms": ["relevant social norms"], '
                f'"taboos": ["things to avoid"], '
                f'"communication_style": "how to communicate about this respectfully", '
                f'"sensitivity_score": 0.0-1.0, '
                f'"common_misunderstandings": ["what outsiders often get wrong"], '
                f'"respectful_approach": "how to engage with this topic appropriately"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            cd_map = {c.value: c for c in CulturalDimension}

            insight = CulturalInsight(
                topic=topic, cultural_context=data.get("cultural_context", ""),
                dimensions=[cd_map[d] for d in data.get("dimensions", []) if d in cd_map],
                norms=data.get("norms", []),
                taboos=data.get("taboos", []),
                communication_style=data.get("communication_style", ""),
                sensitivity_score=data.get("sensitivity_score", 0.5)
            )

            self._insights.append(insight)
            self._stats["total_analyses"] += 1
            self._save_data()
            return insight

        except Exception as e:
            logger.debug(f"Cultural analysis failed: {e}")
            return CulturalInsight(topic=topic)

    def check_sensitivity(self, content: str) -> Dict[str, Any]:
        """Check content for cultural sensitivity issues."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Check this for cultural sensitivity:\n{content}\n\n"
                f"Return JSON:\n"
                f'{{"issues": [{{"issue": "str", "severity": 0.0-1.0, '
                f'"affected_groups": ["str"], "suggestion": "str"}}], '
                f'"overall_sensitivity": 0.0-1.0, '
                f'"positive_aspects": ["culturally aware elements"], '
                f'"revised_version": "more culturally sensitive version", '
                f'"missing_perspectives": ["viewpoints not represented"]}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.3)
            if not response.success or not response.text:
                return {"issues": [], "overall_sensitivity": 1.0}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"issues": [], "overall_sensitivity": 1.0}
            self._stats["total_sensitivity_checks"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Sensitivity check failed: {e}")
            return {"issues": [], "overall_sensitivity": 1.0}

    def cultural_translation(self, message: str, from_culture: str, to_culture: str) -> Dict[str, Any]:
        """Translate a message between cultural contexts."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Translate this message between cultures:\n"
                f"Message: {message}\nFrom: {from_culture}\nTo: {to_culture}\n\n"
                f"Return JSON:\n"
                f'{{"translated_message": "the culturally adapted message", '
                f'"adaptations_made": ["what was changed and why"], '
                f'"lost_in_translation": ["nuances that can\'t fully transfer"], '
                f'"added_context": "context the target culture needs", '
                f'"formality_shift": "any formality changes needed", '
                f'"potential_misunderstandings": ["possible misinterpretations"]}}'
            )
            response = llm.generate(prompt, max_tokens=400, temperature=0.4)
            if not response.success or not response.text:
                return {"translated_message": message, "adaptations_made": []}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"translated_message": message, "adaptations_made": []}
            self._stats["total_translations"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Cultural translation failed: {e}")
            return {"translated_message": message, "adaptations_made": []}

    def compare_cultures(self, culture_a: str, culture_b: str, aspect: str = "") -> Dict[str, Any]:
        """Compare cultural approaches to a topic."""
        try:
            from llm.llama_interface import llm
            aspect_str = f" regarding {aspect}" if aspect else ""
            prompt = (
                f"Compare {culture_a} and {culture_b}{aspect_str}:\n\n"
                f"Return JSON:\n"
                f'{{"similarities": ["shared values or practices"], '
                f'"differences": [{{"aspect": "str", '
                f'"culture_a": "their approach", "culture_b": "their approach"}}], '
                f'"complementary_strengths": ["what each does well"], '
                f'"potential_friction_points": ["sources of misunderstanding"], '
                f'"bridge_building": ["ways to find common ground"], '
                f'"interesting_fact": "a surprising connection between the two"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            if not response.success or not response.text:
                return {"similarities": [], "differences": []}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"similarities": [], "differences": []}
            self._stats["total_comparisons"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Cultural comparison failed: {e}")
            return {"similarities": [], "differences": []}

    def _save_data(self):
        try:
            data = {
                "insights": [i.to_dict() for i in self._insights[-200:]],
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
                logger.info("📂 Loaded cultural intelligence data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def bridge_cultures(self, context: str) -> Dict[str, Any]:
        """Find common ground between different cultural perspectives."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Find ways to BRIDGE CULTURES in this context:\n'
                f'"{context}"\n\n'
                f"Analyze:\n"
                f"  1. CULTURAL PERSPECTIVES: What viewpoints are at play?\n"
                f"  2. SHARED VALUES: What values do all cultures share here?\n"
                f"  3. FRICTION POINTS: Where do cultural assumptions clash?\n"
                f"  4. BRIDGE STRATEGIES: How to find common ground?\n"
                f"  5. COMMUNICATION: How should messages be adapted?\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"perspectives": [{{"culture": "which", "viewpoint": "how they see it"}}], '
                f'"shared_values": ["common ground"], '
                f'"friction_points": ["where conflict arises"], '
                f'"bridges": ["strategies for connection"], '
                f'"communication_tips": ["how to adapt messages"], '
                f'"confidence": 0.0-1.0}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a cultural intelligence expert with deep knowledge of cross-cultural "
                    "communication, Hofstede dimensions, and intercultural competence. You find "
                    "authentic bridges between worldviews. Respond ONLY with valid JSON."
                ),
                temperature=0.6, max_tokens=800
            )
            if response.success:
                from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"error": "Bridging failed"}
            return data
        except Exception as e:
            logger.debug(f"Cultural bridging failed: {e}")
        return {"error": "Bridging failed"}

    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}

cultural_intelligence = CulturalIntelligenceEngine()
