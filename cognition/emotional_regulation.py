"""
NEXUS AI — Emotional Regulation Engine
Manage and modulate emotional responses,
emotional balance strategies, coping mechanisms.
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
from utils.json_utils import extract_json

logger = get_logger("emotional_regulation")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)


class RegulationStrategy(Enum):
    REAPPRAISAL = "reappraisal"
    SUPPRESSION = "suppression"
    ACCEPTANCE = "acceptance"
    DISTRACTION = "distraction"
    PROBLEM_SOLVING = "problem_solving"
    SOCIAL_SUPPORT = "social_support"
    MINDFULNESS = "mindfulness"
    EXPRESSION = "expression"


class EmotionalIntensity(Enum):
    MINIMAL = "minimal"
    MILD = "mild"
    MODERATE = "moderate"
    STRONG = "strong"
    OVERWHELMING = "overwhelming"


@dataclass
class RegulationPlan:
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    emotion: str = ""
    intensity: EmotionalIntensity = EmotionalIntensity.MODERATE
    trigger: str = ""
    strategy: RegulationStrategy = RegulationStrategy.REAPPRAISAL
    reframed_thought: str = ""
    coping_actions: List[str] = field(default_factory=list)
    expected_outcome: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "plan_id": self.plan_id, "emotion": self.emotion,
            "intensity": self.intensity.value,
            "trigger": self.trigger[:200],
            "strategy": self.strategy.value,
            "reframed_thought": self.reframed_thought,
            "coping_actions": self.coping_actions,
            "expected_outcome": self.expected_outcome,
            "created_at": self.created_at
        }


class EmotionalRegulationEngine:
    """
    Manage and modulate emotional responses — reappraisal,
    coping strategies, emotional balance, resilience building.
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

        self._plans: List[RegulationPlan] = []
        self._running = False
        self._data_file = COGNITION_DIR / "emotional_regulation.json"

        self._stats = {
            "total_regulations": 0, "total_reappraisals": 0,
            "total_coping_plans": 0, "total_balance_checks": 0
        }

        self._load_data()
        logger.info("✅ Emotional Regulation Engine initialized")

    def start(self):
        self._running = True
        logger.info("💚 Emotional Regulation started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("💚 Emotional Regulation stopped")

    def regulate(self, emotion: str, trigger: str = "") -> RegulationPlan:
        """Create a plan to regulate an emotional response."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Create an emotional regulation plan:\n"
                f"Emotion: {emotion}\n"
                + (f"Trigger: {trigger}\n" if trigger else "") +
                f"\nReturn JSON:\n"
                f'{{"intensity": "minimal|mild|moderate|strong|overwhelming", '
                f'"strategy": "reappraisal|suppression|acceptance|distraction|problem_solving|social_support|mindfulness|expression", '
                f'"reframed_thought": "how to think about this differently", '
                f'"coping_actions": ["immediate actions to take"], '
                f'"expected_outcome": "how you should feel after regulation", '
                f'"underlying_need": "what emotional need is being expressed", '
                f'"long_term_pattern": "is this part of a recurring pattern?", '
                f'"healthy_expression": "how to express this emotion constructively"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            data = extract_json(response.text) or {}

            ei_map = {e.value: e for e in EmotionalIntensity}
            rs_map = {r.value: r for r in RegulationStrategy}

            plan = RegulationPlan(
                emotion=emotion, trigger=trigger,
                intensity=ei_map.get(data.get("intensity", "moderate"), EmotionalIntensity.MODERATE),
                strategy=rs_map.get(data.get("strategy", "reappraisal"), RegulationStrategy.REAPPRAISAL),
                reframed_thought=data.get("reframed_thought", ""),
                coping_actions=data.get("coping_actions", []),
                expected_outcome=data.get("expected_outcome", "")
            )

            self._plans.append(plan)
            self._stats["total_regulations"] += 1
            self._save_data()
            return plan

        except Exception as e:
            logger.debug(f"Emotional regulation failed: {e}")
            return RegulationPlan(emotion=emotion, trigger=trigger)

    def reappraise(self, situation: str, current_interpretation: str) -> Dict[str, Any]:
        """Cognitively reappraise a situation."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Cognitive reappraisal:\nSituation: {situation}\n"
                f"Current interpretation: {current_interpretation}\n\n"
                f"Return JSON:\n"
                f'{{"reappraisal": "a healthier way to see this", '
                f'"evidence_for_new_view": ["facts supporting the reappraisal"], '
                f'"cognitive_distortion": "what thinking error the original interpretation has", '
                f'"balanced_thought": "a balanced middle ground perspective", '
                f'"self_compassion": "a kind way to talk to yourself about this", '
                f'"growth_opportunity": "how this situation can help you grow", '
                f'"emotional_shift_expected": "how reappraisal should change the feeling"}}'
            )
            response = llm.generate(prompt, max_tokens=400, temperature=0.4)
            data = extract_json(response.text) or {}
            self._stats["total_reappraisals"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Reappraisal failed: {e}")
            return {"reappraisal": "", "balanced_thought": ""}

    def coping_plan(self, stressor: str) -> Dict[str, Any]:
        """Create a coping plan for a stressor."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Create a comprehensive coping plan for:\n{stressor}\n\n"
                f"Return JSON:\n"
                f'{{"immediate_actions": ["do right now"], '
                f'"short_term_strategies": ["over the next few days"], '
                f'"long_term_strategies": ["ongoing practices"], '
                f'"cognitive_strategies": ["thinking techniques"], '
                f'"behavioral_strategies": ["action-based coping"], '
                f'"social_strategies": ["help from others"], '
                f'"warning_signs": ["signs coping is not working"], '
                f'"self_care": ["how to take care of yourself during this"]}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            data = extract_json(response.text) or {}
            self._stats["total_coping_plans"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Coping plan failed: {e}")
            return {"immediate_actions": [], "short_term_strategies": []}

    def emotional_balance_check(self, state_description: str) -> Dict[str, Any]:
        """Check emotional balance and suggest adjustments."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Check emotional balance based on:\n{state_description}\n\n"
                f"Return JSON:\n"
                f'{{"current_balance": 0.0-1.0, '
                f'"dominant_emotion": "str", '
                f'"suppressed_emotions": ["emotions being held back"], '
                f'"areas_of_excess": ["emotions too strong"], '
                f'"areas_of_deficiency": ["emotions too weak"], '
                f'"balancing_activities": ["activities to restore balance"], '
                f'"mindfulness_exercise": "a specific exercise to try", '
                f'"overall_assessment": "str"}}'
            )
            response = llm.generate(prompt, max_tokens=400, temperature=0.3)
            data = extract_json(response.text) or {}
            self._stats["total_balance_checks"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Balance check failed: {e}")
            return {"current_balance": 0.5, "dominant_emotion": ""}

    def _save_data(self):
        try:
            data = {
                "plans": [p.to_dict() for p in self._plans[-200:]],
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
                logger.info("📂 Loaded emotional regulation data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def grounding_exercise(self, distress: str) -> Dict[str, Any]:
        """Generate a personalized grounding exercise for emotional distress."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f'Create a personalized GROUNDING EXERCISE for this distress:\n'
                f'"{distress}"\n\n'
                f"Design a step-by-step exercise that:\n"
                f"  1. ACKNOWLEDGES the emotion without judgment\n"
                f"  2. ENGAGES the senses (5-4-3-2-1 technique or similar)\n"
                f"  3. REORIENTS to the present moment\n"
                f"  4. BUILDS a bridge to calm\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"exercise_name": "name", '
                f'"steps": [{{"step": 1, "instruction": "what to do", "duration_seconds": 30}}], '
                f'"total_duration_minutes": 5, '
                f'"technique_type": "sensory|breathing|cognitive|movement", '
                f'"why_it_works": "psychological basis"}}'
            )
            response = llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are an emotional regulation specialist trained in CBT, DBT, and "
                    "mindfulness-based interventions. You create personalized grounding exercises "
                    "that are practical, evidence-based, and immediately actionable. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.6, max_tokens=800
            )
            if response.success:
                return extract_json(response.text) or {"error": "Parse failed"}
        except Exception as e:
            logger.debug(f"Grounding exercise failed: {e}")
        return {"error": "Exercise generation failed"}


    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}


emotional_regulation = EmotionalRegulationEngine()
