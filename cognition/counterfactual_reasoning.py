"""
NEXUS AI — Counterfactual Reasoning Engine
"What would have happened if..." alternate-history thinking,
hypothetical scenario evaluation, regret analysis, policy evaluation.
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
import re
import sys

from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("counterfactual_reasoning")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)

class CounterfactualType(Enum):
    UPWARD = "upward"          # Better outcome possible
    DOWNWARD = "downward"      # Worse outcome possible
    LATERAL = "lateral"        # Different but neutral outcome
    PREVENTIVE = "preventive"  # What could have prevented X
    ADDITIVE = "additive"      # What if X was added
    SUBTRACTIVE = "subtractive"  # What if X was removed

class PlausibilityLevel(Enum):
    IMPOSSIBLE = "impossible"
    IMPLAUSIBLE = "implausible"
    POSSIBLE = "possible"
    PLAUSIBLE = "plausible"
    LIKELY = "likely"
    NEAR_CERTAIN = "near_certain"

@dataclass
class Counterfactual:
    cf_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    original_scenario: str = ""
    altered_condition: str = ""
    predicted_outcome: str = ""
    cf_type: CounterfactualType = CounterfactualType.LATERAL
    plausibility: PlausibilityLevel = PlausibilityLevel.POSSIBLE
    confidence: float = 0.5
    causal_chain: List[str] = field(default_factory=list)
    key_differences: List[str] = field(default_factory=list)
    lessons_learned: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "cf_id": self.cf_id, "original_scenario": self.original_scenario[:200],
            "altered_condition": self.altered_condition,
            "predicted_outcome": self.predicted_outcome,
            "cf_type": self.cf_type.value,
            "plausibility": self.plausibility.value,
            "confidence": self.confidence,
            "causal_chain": self.causal_chain,
            "key_differences": self.key_differences,
            "lessons_learned": self.lessons_learned,
            "created_at": self.created_at
        }

class CounterfactualReasoningEngine:
    """
    'What if' analysis — explore alternate histories, evaluate
    decisions retroactively, and identify causal pivots.
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

        self._counterfactuals: List[Counterfactual] = []
        self._running = False
        self._data_file = COGNITION_DIR / "counterfactual_reasoning.json"
        self._llm = None

        self._stats = {
            "total_counterfactuals": 0, "total_regret_analyses": 0,
            "total_policy_evals": 0, "total_pivots_found": 0
        }

        self._load_data()
        logger.info("✅ Counterfactual Reasoning Engine initialized")

    def start(self):
        self._running = True
        logger.info("🔄 Counterfactual Reasoning started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🔄 Counterfactual Reasoning stopped")

    def _load_llm(self):
        if self._llm is None:
            try:
                from llm.llama_interface import llm
                self._llm = llm
            except ImportError:
                logger.warning("LLM not available for counterfactual reasoning")

    def what_if(self, scenario: str, change: str = "") -> Counterfactual:
        """Analyze what would have happened if something were different."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Counterfactual reasoning — explore what would happen differently:\n"
                f"Scenario: {scenario}\n"
                + (f"Change: {change}\n" if change else "") +
                f"\nReturn JSON:\n"
                f'{{"altered_condition": "what is changed", '
                f'"predicted_outcome": "what would likely happen instead", '
                f'"cf_type": "upward|downward|lateral|preventive|additive|subtractive", '
                f'"plausibility": "impossible|implausible|possible|plausible|likely|near_certain", '
                f'"confidence": 0.0-1.0, '
                f'"causal_chain": ["step 1 → step 2 → ..."], '
                f'"key_differences": ["how this differs from reality"], '
                f'"lessons_learned": ["insights from this counterfactual"]}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            data = self._parse_json(response.text)
            if not data:
                 return Counterfactual(original_scenario=scenario)

            ct_map = {c.value: c for c in CounterfactualType}
            pl_map = {p.value: p for p in PlausibilityLevel}

            cf = Counterfactual(
                original_scenario=scenario,
                altered_condition=data.get("altered_condition", change),
                predicted_outcome=data.get("predicted_outcome", ""),
                cf_type=ct_map.get(data.get("cf_type", "lateral"), CounterfactualType.LATERAL),
                plausibility=pl_map.get(data.get("plausibility", "possible"), PlausibilityLevel.POSSIBLE),
                confidence=data.get("confidence", 0.5),
                causal_chain=data.get("causal_chain", []),
                key_differences=data.get("key_differences", []),
                lessons_learned=data.get("lessons_learned", [])
            )

            self._counterfactuals.append(cf)
            self._stats["total_counterfactuals"] += 1
            self._save_data()
            return cf

        except Exception as e:
            logger.debug(f"Counterfactual analysis failed: {e}")
            return Counterfactual(original_scenario=scenario)

    def regret_analysis(self, decision: str, outcome: str) -> Dict[str, Any]:
        """Analyze whether a past decision was optimal."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Regret analysis — was this decision optimal?\n"
                f"Decision: {decision}\nOutcome: {outcome}\n\n"
                f"Return JSON:\n"
                f'{{"regret_level": 0.0-1.0, '
                f'"better_alternatives": ["what could have been done instead"], '
                f'"what_went_wrong": ["factors that led to suboptimal outcome"], '
                f'"what_went_right": ["factors that were correct"], '
                f'"was_foreseeable": true/false, '
                f'"key_lesson": "primary takeaway", '
                f'"prevention_strategy": "how to avoid this in future"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.3)
            data = self._parse_json(response.text) or {"regret_level": 0.0, "better_alternatives": []}
            self._stats["total_regret_analyses"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Regret analysis failed: {e}")
            return {"regret_level": 0.0, "better_alternatives": []}

    def find_pivot_points(self, narrative: str) -> Dict[str, Any]:
        """Identify key decision points where outcomes could have diverged."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Identify the critical pivot points in this narrative where "
                f"a different choice would have changed everything:\n{narrative}\n\n"
                f"Return JSON:\n"
                f'{{"pivot_points": [{{"moment": "str", "actual_choice": "str", '
                f'"alternative_choice": "str", "impact_if_different": "str", '
                f'"reversibility": 0.0-1.0}}], '
                f'"most_critical_pivot": "str", '
                f'"overall_determinism": 0.0-1.0}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.4)
            data = self._parse_json(response.text) or {"pivot_points": [], "most_critical_pivot": ""}
            self._stats["total_pivots_found"] += len(data.get("pivot_points", []))
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Pivot point analysis failed: {e}")
            return {"pivot_points": [], "most_critical_pivot": ""}

    def policy_evaluation(self, policy: str, context: str = "") -> Dict[str, Any]:
        """Evaluate a policy by examining counterfactual scenarios."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Evaluate this policy using counterfactual reasoning:\n"
                f"Policy: {policy}\n"
                + (f"Context: {context}\n" if context else "") +
                f"\nReturn JSON:\n"
                f'{{"effectiveness_score": 0.0-1.0, '
                f'"without_policy": "what would happen without it", '
                f'"with_stronger_policy": "what if it were stricter", '
                f'"with_weaker_policy": "what if it were more lenient", '
                f'"unintended_consequences": ["str"], '
                f'"optimal_adjustment": "recommendation"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.3)
            data = self._parse_json(response.text) or {"effectiveness_score": 0.0}
            self._stats["total_policy_evals"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Policy evaluation failed: {e}")
            return {"effectiveness_score": 0.0}

    def timeline_divergence(self, event: str, change: str) -> Dict[str, Any]:
        """
        Model how a single change creates cascading divergences across time,
        mapping the butterfly effect.
        """
        if not hasattr(self, '_llm') or self._llm is None:
            try:
                from llm.llama_interface import llm
                self._llm = llm
            except ImportError:
                return {"error": "LLM not available"}

        if not self._llm.is_connected:
            return {"error": "LLM not connected"}

        try:
            prompt = (
                f'Model a TIMELINE DIVERGENCE:\n'
                f'ORIGINAL EVENT: "{event}"\n'
                f'HYPOTHETICAL CHANGE: "{change}"\n\n'
                f"Map how history unfolds differently:\n"
                f"  1. DIVERGENCE POINT: The exact moment timelines split\n"
                f"  2. IMMEDIATE (hours-days): First differences in the new timeline\n"
                f"  3. SHORT-TERM (weeks-months): How early changes compound\n"
                f"  4. MEDIUM-TERM (months-years): Structural shifts in the alternate timeline\n"
                f"  5. LONG-TERM (years-decades): Ultimate outcome of the divergence\n"
                f"  6. CONVERGENCE POINTS: Where timelines might reconverge despite the change\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"divergence_point": "the exact moment", '
                f'"immediate_effects": ["effect 1"], '
                f'"short_term_effects": ["effect 1"], '
                f'"medium_term_effects": ["effect 1"], '
                f'"long_term_effects": ["effect 1"], '
                f'"convergence_points": ["where timelines reconverge"], '
                f'"butterfly_magnitude": "minimal|moderate|significant|transformative", '
                f'"confidence": 0.0-1.0}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a timeline divergence analyst — you model how a single change creates "
                    "cascading differences across time. Your expertise spans history, systems dynamics, "
                    "and chaos theory. You carefully distinguish high-confidence near-term predictions "
                    "from speculative long-term ones. Respond ONLY with valid JSON."
                ),
                temperature=0.6,
                max_tokens=900
            )

            data = self._parse_json(response.text)
            if data:
                return data

        except Exception as e:
            logger.debug(f"Timeline divergence failed: {e}")

        return {"error": "Timeline divergence analysis failed"}

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
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        return None

    def _save_data(self):
        try:
            data = {
                "counterfactuals": [c.to_dict() for c in self._counterfactuals[-200:]],
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
                logger.info("📂 Loaded counterfactual reasoning data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}

counterfactual_reasoning = CounterfactualReasoningEngine()
