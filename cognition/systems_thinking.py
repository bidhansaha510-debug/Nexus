"""
NEXUS AI — Systems Thinking Engine
Complex systems modeling, feedback loops, emergence,
leverage points, system archetypes, and dynamics.
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

logger = get_logger("systems_thinking")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)

class FeedbackType(Enum):
    REINFORCING = "reinforcing"
    BALANCING = "balancing"
    DELAY = "delay"

class SystemArchetype(Enum):
    LIMITS_TO_GROWTH = "limits_to_growth"
    SHIFTING_BURDEN = "shifting_burden"
    ERODING_GOALS = "eroding_goals"
    ESCALATION = "escalation"
    SUCCESS_TO_SUCCESSFUL = "success_to_successful"
    TRAGEDY_OF_COMMONS = "tragedy_of_commons"
    FIXES_THAT_FAIL = "fixes_that_fail"
    GROWTH_UNDERINVESTMENT = "growth_underinvestment"
    ACCIDENTAL_ADVERSARIES = "accidental_adversaries"
    ATTRACTIVENESS_PRINCIPLE = "attractiveness_principle"

@dataclass
class SystemModel:
    model_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    components: List[Dict[str, Any]] = field(default_factory=list)
    connections: List[Dict[str, Any]] = field(default_factory=list)
    feedback_loops: List[Dict[str, Any]] = field(default_factory=list)
    archetypes: List[str] = field(default_factory=list)
    leverage_points: List[Dict[str, Any]] = field(default_factory=list)
    emergent_properties: List[str] = field(default_factory=list)
    boundaries: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "model_id": self.model_id, "name": self.name,
            "description": self.description, "components": self.components,
            "connections": self.connections,
            "feedback_loops": self.feedback_loops,
            "archetypes": self.archetypes,
            "leverage_points": self.leverage_points,
            "emergent_properties": self.emergent_properties,
            "boundaries": self.boundaries, "created_at": self.created_at
        }

class SystemsThinkingEngine:
    """
    Models complex systems: feedback loops, emergence,
    leverage points, system archetypes, and dynamic behavior.
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

        self._models: List[SystemModel] = []
        self._running = False
        self._data_file = COGNITION_DIR / "systems_thinking.json"

        self._stats = {
            "total_models": 0, "total_analyses": 0,
            "total_leverage_points": 0, "total_simulations": 0
        }

        self._load_data()
        logger.info("✅ Systems Thinking Engine initialized")

    def start(self):
        self._running = True
        logger.info("🔄 Systems Thinking started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🔄 Systems Thinking stopped")

    def model_system(self, system_description: str) -> SystemModel:
        """Model a complex system with components, feedback loops, and leverage points."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Model this system using systems thinking:\n{system_description}\n\n"
                f"Return JSON:\n"
                f'{{"name": "system name", "description": "str", '
                f'"components": [{{"name": "str", "type": "stock|flow|variable|process", '
                f'"state": "str"}}], '
                f'"connections": [{{"from": "str", "to": "str", "type": "positive|negative", '
                f'"strength": 0.0-1.0}}], '
                f'"feedback_loops": [{{"name": "str", "type": "reinforcing|balancing", '
                f'"components": ["str"], "effect": "str"}}], '
                f'"archetypes": ["limits_to_growth|shifting_burden|escalation|tragedy_of_commons|fixes_that_fail"], '
                f'"leverage_points": [{{"point": "str", "impact": 0.0-1.0, "difficulty": 0.0-1.0}}], '
                f'"emergent_properties": ["str"], '
                f'"boundaries": {{"internal": ["str"], "external": ["str"]}}}}'
            )
            response = llm.generate(prompt, max_tokens=800, temperature=0.4)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            model = SystemModel(
                name=data.get("name", ""),
                description=data.get("description", system_description),
                components=data.get("components", []),
                connections=data.get("connections", []),
                feedback_loops=data.get("feedback_loops", []),
                archetypes=data.get("archetypes", []),
                leverage_points=data.get("leverage_points", []),
                emergent_properties=data.get("emergent_properties", []),
                boundaries=data.get("boundaries", {})
            )

            self._models.append(model)
            self._stats["total_models"] += 1
            self._stats["total_leverage_points"] += len(model.leverage_points)
            self._save_data()
            return model

        except Exception as e:
            logger.debug(f"System modeling failed: {e}")
            return SystemModel(description=system_description)

    def find_leverage_points(self, system_description: str) -> List[Dict[str, Any]]:
        """Find high-impact leverage points in a system (Meadows' 12 places)."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Find leverage points (Donella Meadows style) in this system:\n"
                f"{system_description}\n\n"
                f"Return JSON array (sorted by impact, highest first):\n"
                f'[{{"rank": 1, "leverage_point": "str", '
                f'"meadows_category": "paradigm|goals|rules|structure|feedback|information|parameters", '
                f'"impact": 0.0-1.0, "difficulty": 0.0-1.0, '
                f'"intervention": "what to do", '
                f'"expected_effect": "str"}}]'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.4)
            if not response.success or not response.text:
                return []
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return []
            self._stats["total_leverage_points"] += len(data)
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Leverage point finding failed: {e}")
            return []

    def analyze_feedback_loops(self, system_description: str) -> Dict[str, Any]:
        """Identify and analyze feedback loops in a system."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Identify all feedback loops in this system:\n{system_description}\n\n"
                f"Return JSON:\n"
                f'{{"reinforcing_loops": [{{"name": "str", "components": ["str"], '
                f'"growth_rate": "str", "limit": "str"}}], '
                f'"balancing_loops": [{{"name": "str", "components": ["str"], '
                f'"target": "str", "delay": "str"}}], '
                f'"dominant_loop": "str", '
                f'"tipping_points": ["str"], '
                f'"system_behavior": "exponential_growth|oscillation|equilibrium|collapse|s_curve"}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.3)
            if not response.success or not response.text:
                return {"reinforcing_loops": [], "balancing_loops": []}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"reinforcing_loops": [], "balancing_loops": []}
            self._stats["total_analyses"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Feedback loop analysis failed: {e}")
            return {"reinforcing_loops": [], "balancing_loops": []}

    def simulate_intervention(self, system: str, intervention: str) -> Dict[str, Any]:
        """Simulate what happens when you intervene in a system."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Simulate this intervention in a system:\n"
                f"System: {system}\nIntervention: {intervention}\n\n"
                f"Return JSON:\n"
                f'{{"immediate_effects": ["str"], '
                f'"short_term": [{{"effect": "str", "timeframe": "str"}}], '
                f'"long_term": [{{"effect": "str", "timeframe": "str"}}], '
                f'"unintended_consequences": ["str"], '
                f'"cascading_effects": ["str"], '
                f'"resistance_factors": ["str"], '
                f'"probability_of_success": 0.0-1.0}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.4)
            if not response.success or not response.text:
                return {"immediate_effects": [], "probability_of_success": 0.5}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"immediate_effects": [], "probability_of_success": 0.5}
            self._stats["total_simulations"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Intervention simulation failed: {e}")
            return {"immediate_effects": [], "probability_of_success": 0.5}

    def detect_archetypes(self, situation: str) -> Dict[str, Any]:
        """Detect which system archetypes apply to a situation."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Which system archetypes apply to this situation?\n{situation}\n\n"
                f"Return JSON:\n"
                f'{{"archetypes_detected": [{{"name": "str", "confidence": 0.0-1.0, '
                f'"evidence": "str", "typical_solution": "str"}}], '
                f'"primary_archetype": "str", '
                f'"structural_explanation": "str"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.3)
            if not response.success or not response.text:
                return {"archetypes_detected": []}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"archetypes_detected": []}
            return data
        except Exception as e:
            logger.debug(f"Archetype detection failed: {e}")
            return {"archetypes_detected": []}

    def _save_data(self):
        try:
            data = {
                "models": [m.to_dict() for m in self._models[-100:]],
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
                logger.info("📂 Loaded systems thinking data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def leverage_points(self, system: str) -> Dict[str, Any]:
        """Identify leverage points in a system where small changes produce big effects."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Identify LEVERAGE POINTS in this system:\n'
                f'"{system}"\n\n'
                f"Using Donella Meadows hierarchy of leverage points:\n"
                f"  1. PARAMETERS: Numbers (least powerful)\n"
                f"  2. BUFFERS: Sizes of stabilizing stocks\n"
                f"  3. STRUCTURE: Material stocks and flows\n"
                f"  4. DELAYS: Lengths of delays relative to system changes\n"
                f"  5. FEEDBACK LOOPS: Strength of negative/positive feedback\n"
                f"  6. INFORMATION FLOWS: Who has access to information\n"
                f"  7. RULES: Incentives, punishments, constraints\n"
                f"  8. SELF-ORGANIZATION: Power to change system structure\n"
                f"  9. GOALS: The purpose of the system\n"
                f"  10. PARADIGMS: The mindset out of which the system arises (most powerful)\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"leverage_points": [{{"level": "paradigm|goal|rules|information|feedback|delay|structure|buffer|parameter", '
                f'"description": "the specific leverage point", '
                f'"intervention": "what to do", "expected_impact": "high|medium|low"}}], '
                f'"highest_leverage": "the single most impactful intervention", '
                f'"caution": "risks of intervening at this point"}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a systems thinking engine inspired by Donella Meadows. You identify "
                    "where small changes in complex systems produce large effects. You think in "
                    "terms of stocks, flows, feedback loops, and emergent behavior. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.5, max_tokens=900
            )
            if response.success:
                from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"error": "Analysis failed"}
            return data
        except Exception as e:
            logger.debug(f"Leverage points analysis failed: {e}")
        return {"error": "Analysis failed"}

    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}

systems_thinking = SystemsThinkingEngine()