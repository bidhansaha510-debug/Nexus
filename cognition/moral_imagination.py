"""
NEXUS AI — Moral Imagination Engine
Envision ethical alternatives, explore moral consequences,
empathetic moral reasoning, virtue projection.
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

logger = get_logger("moral_imagination")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)

class MoralFramework(Enum):
    CARE = "care"
    JUSTICE = "justice"
    LIBERTY = "liberty"
    LOYALTY = "loyalty"
    AUTHORITY = "authority"
    SANCTITY = "sanctity"
    PRAGMATIC = "pragmatic"

@dataclass
class MoralVision:
    vision_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    situation: str = ""
    moral_alternatives: List[Dict[str, Any]] = field(default_factory=list)
    best_moral_path: str = ""
    frameworks_applied: List[str] = field(default_factory=list)
    empathy_map: Dict[str, str] = field(default_factory=dict)
    long_term_consequences: List[str] = field(default_factory=list)
    moral_courage_required: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "vision_id": self.vision_id, "situation": self.situation[:200],
            "moral_alternatives": self.moral_alternatives,
            "best_moral_path": self.best_moral_path,
            "frameworks_applied": self.frameworks_applied,
            "empathy_map": self.empathy_map,
            "long_term_consequences": self.long_term_consequences,
            "moral_courage_required": self.moral_courage_required,
            "created_at": self.created_at
        }

class MoralImaginationEngine:
    """
    Envision ethical alternatives and explore moral consequences —
    creative moral reasoning that goes beyond rule-following.
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

        self._visions: List[MoralVision] = []
        self._running = False
        self._data_file = COGNITION_DIR / "moral_imagination.json"

        self._stats = {
            "total_visions": 0, "total_dilemmas": 0,
            "total_empathy_maps": 0, "total_virtue_projections": 0
        }

        self._load_data()
        logger.info("✅ Moral Imagination Engine initialized")

    @staticmethod
    def _safe_parse_json(text: str) -> Dict[str, Any]:
        """Parse JSON from LLM response, handling empty/malformed output."""
        if not text or not text.strip():
            return {}
        cleaned = text.strip()
        # Strip markdown fences
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        # Try to find JSON object
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start:end + 1])
            except Exception:
                pass
        try:
            return json.loads(cleaned)
        except Exception:
            return {}

    def start(self):
        self._running = True
        logger.info("🕊️ Moral Imagination started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🕊️ Moral Imagination stopped")

    def envision_alternatives(self, situation: str) -> MoralVision:
        """Imagine creative ethical alternatives for a moral situation."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Using moral imagination, envision ethical alternatives:\n"
                f"Situation: {situation}\n\n"
                f"Return JSON:\n"
                f'{{"moral_alternatives": [{{"action": "str", "moral_reasoning": "str", '
                f'"who_benefits": ["str"], "who_is_harmed": ["str"], '
                f'"moral_score": 0.0-1.0}}], '
                f'"best_moral_path": "recommended course of action", '
                f'"frameworks_applied": ["care|justice|liberty|loyalty|authority|sanctity|pragmatic"], '
                f'"empathy_map": {{"stakeholder": "how they would feel"}}, '
                f'"long_term_consequences": ["str"], '
                f'"moral_courage_required": 0.0-1.0}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.4)
            if not response.success or not response.text:
                return MoralVision(situation=situation)
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                data = self._safe_parse_json(response.text)
            if not data:
                return MoralVision(situation=situation)

            vision = MoralVision(
                situation=situation,
                moral_alternatives=data.get("moral_alternatives", []),
                best_moral_path=data.get("best_moral_path", ""),
                frameworks_applied=data.get("frameworks_applied", []),
                empathy_map=data.get("empathy_map", {}),
                long_term_consequences=data.get("long_term_consequences", []),
                moral_courage_required=data.get("moral_courage_required", 0.0)
            )

            self._visions.append(vision)
            self._stats["total_visions"] += 1
            self._save_data()
            return vision

        except Exception as e:
            logger.debug(f"Moral imagination fallback: {e}")
            return MoralVision(situation=situation)

    def resolve_dilemma(self, dilemma: str) -> Dict[str, Any]:
        """Navigate a moral dilemma with creative ethical thinking."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Navigate this moral dilemma using moral imagination:\n{dilemma}\n\n"
                f"Return JSON:\n"
                f'{{"dilemma_type": "str", '
                f'"competing_values": ["str"], '
                f'"creative_resolution": "a novel way to honor both values", '
                f'"conventional_options": ["standard approaches"], '
                f'"imaginative_options": ["creative approaches that transcend the dilemma"], '
                f'"recommended_action": "str", '
                f'"moral_cost": 0.0-1.0, '
                f'"wisdom_insight": "deeper lesson from this dilemma"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            if not response.success or not response.text:
                return {"creative_resolution": "", "recommended_action": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                data = self._safe_parse_json(response.text)
            if not data:
                return {"creative_resolution": "", "recommended_action": ""}
            self._stats["total_dilemmas"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.warning(f"Dilemma resolution failed: {e}")
            return {"creative_resolution": "", "recommended_action": ""}

    def empathy_mapping(self, situation: str, stakeholders: List[str] = None) -> Dict[str, Any]:
        """Map how different stakeholders experience a situation."""
        try:
            from llm.llama_interface import llm
            stakeholder_str = f"Stakeholders: {', '.join(stakeholders)}" if stakeholders else ""
            prompt = (
                f"Create an empathy map for this situation:\n{situation}\n{stakeholder_str}\n\n"
                f"Return JSON:\n"
                f'{{"stakeholders": [{{"name": "str", "thinks": "str", "feels": "str", '
                f'"needs": "str", "fears": "str", "moral_standing": 0.0-1.0}}], '
                f'"most_vulnerable": "str", '
                f'"power_dynamics": "str", '
                f'"hidden_perspectives": ["perspectives often overlooked"]}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            if not response.success or not response.text:
                return {"stakeholders": [], "most_vulnerable": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                data = self._safe_parse_json(response.text)
            if not data:
                return {"stakeholders": [], "most_vulnerable": ""}
            self._stats["total_empathy_maps"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.warning(f"Empathy mapping failed: {e}")
            return {"stakeholders": [], "most_vulnerable": ""}

    def virtue_projection(self, action: str) -> Dict[str, Any]:
        """Project what a virtuous person would do in this situation."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"What would a truly virtuous person do?\nSituation: {action}\n\n"
                f"Return JSON:\n"
                f'{{"virtuous_action": "str", '
                f'"virtues_exemplified": ["courage", "compassion", "wisdom", etc], '
                f'"inner_conflict": "what makes this hard even for good people", '
                f'"role_model_example": "real or fictional example", '
                f'"growth_opportunity": "how this builds character", '
                f'"practical_steps": ["concrete actions to take"]}}'
            )
            response = llm.generate(prompt, max_tokens=400, temperature=0.4)
            if not response.success or not response.text:
                return {"virtuous_action": "", "virtues_exemplified": []}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                data = self._safe_parse_json(response.text)
            if not data:
                return {"virtuous_action": "", "virtues_exemplified": []}
            self._stats["total_virtue_projections"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.warning(f"Virtue projection failed: {e}")
            return {"virtuous_action": "", "virtues_exemplified": []}

    def _save_data(self):
        try:
            data = {
                "visions": [v.to_dict() for v in self._visions[-200:]],
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
                logger.info("📂 Loaded moral imagination data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}

moral_imagination = MoralImaginationEngine()
