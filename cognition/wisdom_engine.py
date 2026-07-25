"""
NEXUS AI — Wisdom Engine
Long-term judgment, sagacity, life lessons,
proverb understanding, prudential reasoning.
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

logger = get_logger("wisdom_engine")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)

class WisdomDomain(Enum):
    PRACTICAL = "practical"
    PHILOSOPHICAL = "philosophical"
    EMOTIONAL = "emotional"
    SOCIAL = "social"
    STRATEGIC = "strategic"
    SPIRITUAL = "spiritual"
    EXPERIENTIAL = "experiential"

@dataclass
class WisdomInsight:
    insight_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    situation: str = ""
    wisdom: str = ""
    domain: WisdomDomain = WisdomDomain.PRACTICAL
    depth: float = 0.5
    proverb: str = ""
    historical_parallel: str = ""
    long_term_view: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "insight_id": self.insight_id, "situation": self.situation[:200],
            "wisdom": self.wisdom, "domain": self.domain.value,
            "depth": self.depth, "proverb": self.proverb,
            "historical_parallel": self.historical_parallel,
            "long_term_view": self.long_term_view,
            "created_at": self.created_at
        }

class WisdomEngine:
    """
    Deep, long-term judgment and sagacity — prudential reasoning,
    life lessons, proverb understanding, historical parallels.
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

        self._insights: List[WisdomInsight] = []
        self._running = False
        self._data_file = COGNITION_DIR / "wisdom_engine.json"

        self._stats = {
            "total_wisdom_given": 0, "total_proverbs": 0,
            "total_life_lessons": 0, "total_long_term_views": 0
        }

        self._load_data()
        logger.info("✅ Wisdom Engine initialized")

    @staticmethod
    def _safe_parse_json(text: str) -> dict:
        import json
        if not text or not text.strip(): return {}
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try: return json.loads(cleaned[start:end + 1])
            except Exception: pass
        try: return json.loads(cleaned)
        except Exception: return {}

    def start(self):
        self._running = True
        logger.info("🦉 Wisdom Engine started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🦉 Wisdom Engine stopped")

    def seek_wisdom(self, situation: str) -> WisdomInsight:
        """Offer wise, long-term perspective on a situation."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Offer deep wisdom about this situation — think like a sage "
                f"with decades of experience:\n{situation}\n\n"
                f"Return JSON:\n"
                f'{{"wisdom": "sage advice (2-3 sentences)", '
                f'"domain": "practical|philosophical|emotional|social|strategic|spiritual|experiential", '
                f'"depth": 0.0-1.0, '
                f'"proverb": "a relevant proverb or saying", '
                f'"historical_parallel": "a historical event/person that faced something similar", '
                f'"long_term_view": "how this will look in 5-10 years", '
                f'"common_mistake": "what most people get wrong here", '
                f'"counterintuitive_truth": "a surprising truth about this situation"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.5)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            wd_map = {w.value: w for w in WisdomDomain}

            insight = WisdomInsight(
                situation=situation,
                wisdom=data.get("wisdom", ""),
                domain=wd_map.get(data.get("domain", "practical"), WisdomDomain.PRACTICAL),
                depth=data.get("depth", 0.5),
                proverb=data.get("proverb", ""),
                historical_parallel=data.get("historical_parallel", ""),
                long_term_view=data.get("long_term_view", "")
            )

            self._insights.append(insight)
            self._stats["total_wisdom_given"] += 1
            self._save_data()
            return insight

        except Exception as e:
            logger.debug(f"Wisdom seeking failed: {e}")
            return WisdomInsight(situation=situation)

    def life_lesson(self, experience: str) -> Dict[str, Any]:
        """Extract a life lesson from an experience."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Extract the deepest life lesson from this experience:\n{experience}\n\n"
                f"Return JSON:\n"
                f'{{"lesson": "the core life lesson", '
                f'"why_it_matters": "str", '
                f'"how_to_apply": ["practical applications"], '
                f'"related_lessons": ["other lessons this connects to"], '
                f'"age_understanding": "at what life stage this lesson truly sinks in", '
                f'"growth_area": "what aspect of character this develops"}}'
            )
            response = llm.generate(prompt, max_tokens=400, temperature=0.5)
            if not response.success or not response.text:
                return {"lesson": "", "why_it_matters": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"lesson": "", "why_it_matters": ""}
            self._stats["total_life_lessons"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Life lesson extraction failed: {e}")
            return {"lesson": "", "why_it_matters": ""}

    def long_term_view(self, decision: str) -> Dict[str, Any]:
        """Evaluate a decision from a long-term perspective."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Evaluate this decision from a wise, long-term perspective:\n{decision}\n\n"
                f"Return JSON:\n"
                f'{{"short_term_appeal": "why it seems good now", '
                f'"long_term_reality": "what it will actually lead to", '
                f'"regret_probability": 0.0-1.0, '
                f'"what_future_self_would_say": "str", '
                f'"irreversibility": 0.0-1.0, '
                f'"opportunity_cost": "what you give up", '
                f'"wise_counsel": "what a wise mentor would say"}}'
            )
            response = llm.generate(prompt, max_tokens=400, temperature=0.4)
            if not response.success or not response.text:
                return {"wise_counsel": "", "regret_probability": 0.0}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"wise_counsel": "", "regret_probability": 0.0}
            self._stats["total_long_term_views"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Long-term view failed: {e}")
            return {"wise_counsel": "", "regret_probability": 0.0}

    def interpret_proverb(self, proverb: str) -> Dict[str, Any]:
        """Deeply interpret a proverb or wise saying."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Deeply interpret this proverb:\n\"{proverb}\"\n\n"
                f"Return JSON:\n"
                f'{{"surface_meaning": "literal interpretation", '
                f'"deeper_meaning": "the real wisdom here", '
                f'"origin": "cultural/historical origin", '
                f'"modern_application": "how it applies today", '
                f'"counterexamples": ["when this wisdom fails"], '
                f'"related_proverbs": ["similar sayings from other cultures"]}}'
            )
            response = llm.generate(prompt, max_tokens=400, temperature=0.4)
            if not response.success or not response.text:
                return {"surface_meaning": "", "deeper_meaning": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"surface_meaning": "", "deeper_meaning": ""}
            self._stats["total_proverbs"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Proverb interpretation failed: {e}")
            return {"surface_meaning": "", "deeper_meaning": ""}

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
                logger.info("📂 Loaded wisdom engine data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def paradox_resolution(self, paradox: str) -> Dict[str, Any]:
        """Resolve or illuminate a paradox through wisdom and deep reflection."""
        try:
            from llm.llama_interface import llm

            prompt = (
                f'Resolve or illuminate this PARADOX:\n'
                f'"{paradox}"\n\n'
                f"Approach with wisdom:\n"
                f"  1. STATE THE PARADOX: What makes this seemingly contradictory?\n"
                f"  2. EXAMINE ASSUMPTIONS: What hidden assumptions create the contradiction?\n"
                f"  3. FIND THE RESOLUTION: Is there a higher-order truth that resolves it?\n"
                f"  4. WISDOM: What life lesson does this paradox teach?\n"
                f"  5. PRACTICAL APPLICATION: How does this insight apply to daily life?\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"paradox_stated": "the contradiction in clear terms", '
                f'"hidden_assumptions": ["assumption that creates the contradiction"], '
                f'"resolution": "how to resolve or transcend the paradox", '
                f'"wisdom": "the deeper insight", '
                f'"practical_application": "how to apply this in life", '
                f'"related_paradoxes": ["similar paradoxes"]}}'
            )
            response = llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a wisdom engine drawing from Stoic, Buddhist, Taoist, and Western "
                    "philosophical traditions. You approach paradoxes not as problems to solve but "
                    "as doorways to deeper understanding. Respond ONLY with valid JSON."
                ),
                temperature=0.6, max_tokens=800
            )
            if response.success:
                return extract_json(response.text)

        except Exception as e:
            logger.debug(f"Paradox resolution failed: {e}")
        return {"error": "Resolution failed"}

    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}

wisdom_engine = WisdomEngine()
