"""
NEXUS AI — Common Sense Reasoning Engine
Everyday knowledge, physical intuition, folk psychology,
naive physics, affordance reasoning, practical wisdom.
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

logger = get_logger("common_sense")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)


import re

class CommonSenseDomain(Enum):
    PHYSICS = "physics"
    SOCIAL = "social"
    TEMPORAL = "temporal"
    SPATIAL = "spatial"
    BIOLOGICAL = "biological"
    PSYCHOLOGICAL = "psychological"
    ECONOMIC = "economic"
    CULTURAL = "cultural"
    PRACTICAL = "practical"
    SAFETY = "safety"


class PlausibilityLevel(Enum):
    IMPOSSIBLE = "impossible"
    IMPLAUSIBLE = "implausible"
    UNLIKELY = "unlikely"
    POSSIBLE = "possible"
    LIKELY = "likely"
    OBVIOUS = "obvious"
    CERTAIN = "certain"


@dataclass
class CommonSenseJudgment:
    judgment_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    statement: str = ""
    plausibility: PlausibilityLevel = PlausibilityLevel.POSSIBLE
    plausibility_score: float = 0.5
    domain: CommonSenseDomain = CommonSenseDomain.PRACTICAL
    reasoning: str = ""
    assumptions: List[str] = field(default_factory=list)
    exceptions: List[str] = field(default_factory=list)
    cultural_context: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "judgment_id": self.judgment_id, "statement": self.statement,
            "plausibility": self.plausibility.value,
            "plausibility_score": self.plausibility_score,
            "domain": self.domain.value, "reasoning": self.reasoning,
            "assumptions": self.assumptions, "exceptions": self.exceptions,
            "cultural_context": self.cultural_context,
            "created_at": self.created_at
        }


@dataclass
class PhysicsIntuition:
    intuition_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    scenario: str = ""
    prediction: str = ""
    physical_principles: List[str] = field(default_factory=list)
    confidence: float = 0.5
    common_misconceptions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "intuition_id": self.intuition_id, "scenario": self.scenario,
            "prediction": self.prediction,
            "physical_principles": self.physical_principles,
            "confidence": self.confidence,
            "common_misconceptions": self.common_misconceptions
        }


class CommonSenseEngine:
    """
    Everyday knowledge and practical reasoning — physics intuition,
    social knowledge, practical wisdom, plausibility judgments.
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

        self._judgments: List[CommonSenseJudgment] = []
        self._physics_intuitions: List[PhysicsIntuition] = []
        self._running = False
        self._data_file = COGNITION_DIR / "common_sense.json"
        self._llm = None

        self._stats = {
            "total_judgments": 0, "total_physics_queries": 0,
            "total_affordance_checks": 0, "total_practical_advice": 0
        }

        self._load_data()
        logger.info("✅ Common Sense Reasoning Engine initialized")

    def start(self):
        self._running = True
        logger.info("🌍 Common Sense Reasoning started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🌍 Common Sense Reasoning stopped")

    def _load_llm(self):
        if self._llm is None:
            try:
                from llm.llama_interface import llm
                self._llm = llm
            except ImportError:
                logger.warning("LLM not available for common sense")

    def judge_plausibility(self, statement: str) -> CommonSenseJudgment:
        """Judge how plausible a statement is using common sense."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Using common sense, judge the plausibility of:\n\"{statement}\"\n\n"
                f"Return JSON:\n"
                f'{{"plausibility": "impossible|implausible|unlikely|possible|likely|obvious|certain", '
                f'"plausibility_score": 0.0-1.0, '
                f'"domain": "physics|social|temporal|spatial|biological|psychological|economic|cultural|practical|safety", '
                f'"reasoning": "explain your common sense reasoning", '
                f'"assumptions": ["assumptions being made"], '
                f'"exceptions": ["cases where this might not hold"], '
                f'"cultural_context": "any cultural specificity"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.3)
            data = self._parse_json(response.text)
            if not data:
                return CommonSenseJudgment(statement=statement)

            pl_map = {p.value: p for p in PlausibilityLevel}
            dm_map = {d.value: d for d in CommonSenseDomain}

            judgment = CommonSenseJudgment(
                statement=statement,
                plausibility=pl_map.get(data.get("plausibility", "possible"), PlausibilityLevel.POSSIBLE),
                plausibility_score=data.get("plausibility_score", 0.5),
                domain=dm_map.get(data.get("domain", "practical"), CommonSenseDomain.PRACTICAL),
                reasoning=data.get("reasoning", ""),
                assumptions=data.get("assumptions", []),
                exceptions=data.get("exceptions", []),
                cultural_context=data.get("cultural_context", "")
            )

            self._judgments.append(judgment)
            self._stats["total_judgments"] += 1
            self._save_data()
            return judgment

        except Exception as e:
            logger.debug(f"Plausibility judgment failed: {e}")
            return CommonSenseJudgment(statement=statement)

    def physics_intuition(self, scenario: str) -> PhysicsIntuition:
        """Apply naive physics / physical intuition to a scenario."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Using physical intuition (naive physics), predict what happens:\n{scenario}\n\n"
                f"Return JSON:\n"
                f'{{"prediction": "what will happen", '
                f'"physical_principles": ["gravity", "friction", "momentum", etc.], '
                f'"confidence": 0.0-1.0, '
                f'"common_misconceptions": ["things people often get wrong about this"], '
                f'"step_by_step": ["step 1", "step 2"]}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.3)
            data = self._parse_json(response.text)
            if not data:
                return PhysicsIntuition(scenario=scenario)

            pi = PhysicsIntuition(
                scenario=scenario,
                prediction=data.get("prediction", ""),
                physical_principles=data.get("physical_principles", []),
                confidence=data.get("confidence", 0.5),
                common_misconceptions=data.get("common_misconceptions", [])
            )

            self._physics_intuitions.append(pi)
            self._stats["total_physics_queries"] += 1
            self._save_data()
            return pi

        except Exception as e:
            logger.debug(f"Physics intuition failed: {e}")
            return PhysicsIntuition(scenario=scenario)

    def check_affordance(self, object_desc: str) -> Dict[str, Any]:
        """Determine what an object can be used for (affordance reasoning)."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"What can this object be used for? (Affordance reasoning)\n"
                f"Object: {object_desc}\n\n"
                f"Return JSON:\n"
                f'{{"primary_uses": ["str"], "alternative_uses": ["str"], '
                f'"dangerous_uses": ["str"], "properties": ["str"], '
                f'"typical_context": "str", "size_category": "str", '
                f'"material_guess": "str"}}'
            )
            response = llm.generate(prompt, max_tokens=400, temperature=0.4)
            data = self._parse_json(response.text) or {"primary_uses": [], "alternative_uses": []}
            self._stats["total_affordance_checks"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Affordance check failed: {e}")
            return {"primary_uses": [], "alternative_uses": []}

    def practical_advice(self, situation: str) -> Dict[str, Any]:
        """Give practical, common-sense advice for a situation."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Give practical common-sense advice for:\n{situation}\n\n"
                f"Return JSON:\n"
                f'{{"advice": ["practical tips"], '
                f'"things_to_avoid": ["common mistakes"], '
                f'"prerequisites": ["things to do first"], '
                f'"expected_outcome": "str", '
                f'"difficulty": "easy|medium|hard", '
                f'"time_estimate": "str"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            data = self._parse_json(response.text) or {"advice": [], "things_to_avoid": []}
            self._stats["total_practical_advice"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Practical advice failed: {e}")
            return {"advice": [], "things_to_avoid": []}

    def fill_in_the_blanks(self, incomplete_scenario: str) -> Dict[str, Any]:
        """Fill in unstated but implied information using common sense."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Using common sense, fill in what's implied but not stated:\n"
                f"{incomplete_scenario}\n\n"
                f"Return JSON:\n"
                f'{{"stated_facts": ["explicitly mentioned"], '
                f'"implied_facts": ["common sense inferences"], '
                f'"likely_context": "str", '
                f'"background_knowledge_used": ["str"], '
                f'"confidence": 0.0-1.0}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            return self._parse_json(response.text) or {"stated_facts": [], "implied_facts": [], "confidence": 0.0}
        except Exception as e:
            logger.debug(f"Fill-in-the-blanks failed: {e}")
            return {"stated_facts": [], "implied_facts": [], "confidence": 0.0}

    def _save_data(self):
        try:
            data = {
                "judgments": [j.to_dict() for j in self._judgments[-200:]],
                "physics_intuitions": [p.to_dict() for p in self._physics_intuitions[-100:]],
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
                logger.info("📂 Loaded common sense data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def sanity_check(self, claim: str) -> Dict[str, Any]:
        """Apply common sense reasoning to check if a claim passes the sniff test."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'SANITY CHECK this claim using common sense:\n'
                f'"{claim}"\n\n'
                f"Apply these common sense tests:\n"
                f"  1. PLAUSIBILITY: Does this pass the basic sniff test?\n"
                f"  2. MAGNITUDE: Are the numbers/scale reasonable?\n"
                f"  3. CONSISTENCY: Does it contradict well-known facts?\n"
                f"  4. MOTIVATION: Who benefits from this claim being believed?\n"
                f"  5. EVIDENCE: What evidence would be needed to verify this?\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"passes_sniff_test": true, '
                f'"plausibility_score": 0.0-1.0, '
                f'"red_flags": ["concerns about this claim"], '
                f'"likely_true_parts": ["aspects that seem reasonable"], '
                f'"likely_false_parts": ["aspects that seem dubious"], '
                f'"verification_needed": ["what to check"], '
                f'"verdict": "plausible|questionable|implausible"}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a common sense reasoning engine. You apply practical, everyday "
                    "reasoning to evaluate claims -- checking for basic plausibility, reasonable "
                    "magnitudes, and obvious red flags. You are the voice of 'wait, does this "
                    "actually make sense?'. Respond ONLY with valid JSON."
                ),
                temperature=0.3, max_tokens=700
            )
            if response.success:
                from utils.json_utils import extract_json
                data = extract_json(response.text)
                if not data:
                    return {"error": "Sanity check failed"}
                return data
        except Exception as e:
            logger.debug(f"Sanity check failed: {e}")
        return {"error": "Sanity check failed"}

    def _parse_json(self, text: str) -> Optional[Dict]:
        if not text:
            return None
        try:
            # Clean markdown
            text = text.strip()
            if text.startswith("```json"):
                text = text.replace("```json", "", 1)
            if text.startswith("```"):
                text = text.replace("```", "", 1)
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            return json.loads(text)
        except json.JSONDecodeError:
            # Fallback: regex to find JSON object
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        return None


    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}


common_sense = CommonSenseEngine()
