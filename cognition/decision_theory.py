"""
NEXUS AI — Decision Theory Engine
Utility maximization, multi-criteria analysis, game theory,
prospect theory, regret minimization, decision frameworks.
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
import re

logger = get_logger("decision_theory")

def _extract_json(text: str) -> dict:
    """Safely extract JSON from LLM response text."""
    if not text or not text.strip():
        return {}
    cleaned = text.strip()
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', cleaned)
    if match:
        cleaned = match.group(1).strip()
    start = cleaned.find('{')
    end = cleaned.rfind('}')
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(cleaned[start:end + 1])
        except Exception:
            pass
    try:
        return json.loads(cleaned)
    except Exception:
        return {}

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)

class DecisionFramework(Enum):
    EXPECTED_UTILITY = "expected_utility"
    MINIMAX = "minimax"
    MAXIMIN = "maximin"
    REGRET_MINIMIZATION = "regret_minimization"
    SATISFICING = "satisficing"
    PROSPECT_THEORY = "prospect_theory"
    MULTI_CRITERIA = "multi_criteria"
    GAME_THEORY = "game_theory"
    PARETO = "pareto"
    COST_BENEFIT = "cost_benefit"

class GameType(Enum):
    ZERO_SUM = "zero_sum"
    NON_ZERO_SUM = "non_zero_sum"
    COOPERATIVE = "cooperative"
    COMPETITIVE = "competitive"
    PRISONERS_DILEMMA = "prisoners_dilemma"
    STAG_HUNT = "stag_hunt"
    CHICKEN = "chicken"
    COORDINATION = "coordination"

@dataclass
class DecisionOption:
    name: str = ""
    utility: float = 0.0
    probability: float = 1.0
    expected_value: float = 0.0
    risks: List[str] = field(default_factory=list)
    benefits: List[str] = field(default_factory=list)
    regret_score: float = 0.0
    criteria_scores: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "name": self.name, "utility": self.utility,
            "probability": self.probability,
            "expected_value": self.expected_value,
            "risks": self.risks, "benefits": self.benefits,
            "regret_score": self.regret_score,
            "criteria_scores": self.criteria_scores
        }

@dataclass
class Decision:
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    situation: str = ""
    framework: DecisionFramework = DecisionFramework.EXPECTED_UTILITY
    options: List[DecisionOption] = field(default_factory=list)
    recommended: str = ""
    reasoning: str = ""
    confidence: float = 0.5
    sensitivity_analysis: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "decision_id": self.decision_id, "situation": self.situation,
            "framework": self.framework.value,
            "options": [o.to_dict() for o in self.options],
            "recommended": self.recommended, "reasoning": self.reasoning,
            "confidence": self.confidence,
            "sensitivity_analysis": self.sensitivity_analysis,
            "created_at": self.created_at
        }

@dataclass
class GameAnalysis:
    game_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    scenario: str = ""
    game_type: GameType = GameType.NON_ZERO_SUM
    players: List[str] = field(default_factory=list)
    strategies: Dict[str, List[str]] = field(default_factory=dict)
    nash_equilibria: List[str] = field(default_factory=list)
    dominant_strategies: Dict[str, str] = field(default_factory=dict)
    recommended_strategy: str = ""
    reasoning: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "game_id": self.game_id, "scenario": self.scenario,
            "game_type": self.game_type.value, "players": self.players,
            "strategies": self.strategies,
            "nash_equilibria": self.nash_equilibria,
            "dominant_strategies": self.dominant_strategies,
            "recommended_strategy": self.recommended_strategy,
            "reasoning": self.reasoning, "created_at": self.created_at
        }

class DecisionTheoryEngine:
    """
    Formal decision-making: utility theory, game theory,
    multi-criteria analysis, prospect theory, regret minimization.
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

        self._decisions: List[Decision] = []
        self._game_analyses: List[GameAnalysis] = []
        self._running = False
        self._data_file = COGNITION_DIR / "decision_theory.json"

        self._stats = {
            "total_decisions": 0, "total_game_analyses": 0,
            "total_multi_criteria": 0, "total_tradeoffs": 0
        }

        self._load_data()
        logger.info("✅ Decision Theory Engine initialized")

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
        logger.info("⚖️ Decision Theory started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("⚖️ Decision Theory stopped")

    def analyze_decision(self, situation: str, framework: str = "expected_utility") -> Decision:
        """Analyze a decision using formal decision theory."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Analyze this decision using {framework} framework:\n{situation}\n\n"
                f"Return JSON:\n"
                f'{{"options": [{{"name": "str", "utility": 0.0-1.0, '
                f'"probability": 0.0-1.0, "expected_value": float, '
                f'"risks": ["str"], "benefits": ["str"], '
                f'"regret_score": 0.0-1.0}}], '
                f'"recommended": "option name", '
                f'"reasoning": "str", "confidence": 0.0-1.0, '
                f'"sensitivity_analysis": {{"key_assumptions": ["str"], '
                f'"tipping_points": ["str"]}}}}'
            )
            response = llm.generate(prompt, max_tokens=700, temperature=0.3)
            if not response.success:
                raise ValueError(f"LLM request failed: {response.error}")
            data = _extract_json(response.text)

            fw_map = {f.value: f for f in DecisionFramework}

            options = [DecisionOption(
                name=o.get("name", ""),
                utility=o.get("utility", 0.0),
                probability=o.get("probability", 1.0),
                expected_value=o.get("expected_value", 0.0),
                risks=o.get("risks", []),
                benefits=o.get("benefits", []),
                regret_score=o.get("regret_score", 0.0)
            ) for o in data.get("options", [])]

            decision = Decision(
                situation=situation,
                framework=fw_map.get(framework, DecisionFramework.EXPECTED_UTILITY),
                options=options,
                recommended=data.get("recommended", ""),
                reasoning=data.get("reasoning", ""),
                confidence=data.get("confidence", 0.5),
                sensitivity_analysis=data.get("sensitivity_analysis", {})
            )

            self._decisions.append(decision)
            self._stats["total_decisions"] += 1
            self._save_data()
            return decision

        except Exception as e:
            logger.debug(f"Decision analysis failed: {e}")
            return Decision(situation=situation)

    def game_theory_analysis(self, scenario: str) -> GameAnalysis:
        """Analyze a strategic interaction using game theory."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Model this as a game theory problem:\n{scenario}\n\n"
                f"Return JSON:\n"
                f'{{"game_type": "zero_sum|non_zero_sum|cooperative|competitive|'
                f'prisoners_dilemma|stag_hunt|chicken|coordination", '
                f'"players": ["str"], '
                f'"strategies": {{"player1": ["strategy options"]}}, '
                f'"nash_equilibria": ["equilibrium descriptions"], '
                f'"dominant_strategies": {{"player": "strategy"}}, '
                f'"recommended_strategy": "str", '
                f'"reasoning": "str"}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.3)
            if not response.success:
                raise ValueError(f"LLM request failed: {response.error}")
            data = _extract_json(response.text)

            gt_map = {g.value: g for g in GameType}

            ga = GameAnalysis(
                scenario=scenario,
                game_type=gt_map.get(data.get("game_type", "non_zero_sum"), GameType.NON_ZERO_SUM),
                players=data.get("players", []),
                strategies=data.get("strategies", {}),
                nash_equilibria=data.get("nash_equilibria", []),
                dominant_strategies=data.get("dominant_strategies", {}),
                recommended_strategy=data.get("recommended_strategy", ""),
                reasoning=data.get("reasoning", "")
            )

            self._game_analyses.append(ga)
            self._stats["total_game_analyses"] += 1
            self._save_data()
            return ga

        except Exception as e:
            logger.debug(f"Game theory analysis failed: {e}")
            return GameAnalysis(scenario=scenario)

    def multi_criteria_decision(self, situation: str, criteria: str = "") -> Dict[str, Any]:
        """Multi-criteria decision analysis (MCDA)."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Perform multi-criteria decision analysis:\n"
                f"Situation: {situation}\nCriteria: {criteria}\n\n"
                f"Return JSON:\n"
                f'{{"criteria": [{{"name": "str", "weight": 0.0-1.0, "description": "str"}}], '
                f'"options": [{{"name": "str", "scores": {{"criterion": 0.0-1.0}}, '
                f'"weighted_total": float}}], '
                f'"ranking": ["best to worst"], '
                f'"recommended": "str", "reasoning": "str"}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.3)
            if not response.success:
                raise ValueError(f"LLM request failed: {response.error}")
            data = _extract_json(response.text)
            self._stats["total_multi_criteria"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Multi-criteria analysis failed: {e}")
            return {"criteria": [], "options": [], "recommended": "unknown"}

    def analyze_tradeoffs(self, options_text: str) -> Dict[str, Any]:
        """Analyze tradeoffs between options."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Analyze the tradeoffs between:\n{options_text}\n\n"
                f"Return JSON:\n"
                f'{{"tradeoffs": [{{"dimension": "str", "option_a_advantage": "str", '
                f'"option_b_advantage": "str"}}], '
                f'"pareto_optimal": ["str"], '
                f'"dealbreakers": ["str"], '
                f'"recommendation": "str", '
                f'"decision_factors": ["most important factors"]}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.3)
            if not response.success:
                raise ValueError(f"LLM request failed: {response.error}")
            data = _extract_json(response.text)
            self._stats["total_tradeoffs"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Tradeoff analysis failed: {e}")
            return {"tradeoffs": [], "recommendation": "unknown"}

    def multi_criteria_analysis(self, decision: str) -> Dict[str, Any]:
        """
        Perform a structured multi-criteria analysis with weighted scoring.
        
        Decomposes a complex decision into criteria, weights them by importance,
        scores each option against each criterion, and produces a ranked recommendation.
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
                f'Perform a MULTI-CRITERIA ANALYSIS for this decision:\n'
                f'"{decision}"\n\n'
                f"Work through these steps:\n"
                f"  1. IDENTIFY OPTIONS: What are the available choices?\n"
                f"  2. DEFINE CRITERIA: What factors matter most? (cost, risk, time, quality, etc.)\n"
                f"  3. WEIGHT CRITERIA: Assign importance weights (must sum to 1.0)\n"
                f"  4. SCORE OPTIONS: Rate each option against each criterion (0-10)\n"
                f"  5. COMPUTE: Calculate weighted scores for each option\n"
                f"  6. SENSITIVITY: How would the ranking change if weights shifted?\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"options": ["option1", "option2"], '
                f'"criteria": [{{"name": "criterion", "weight": 0.3, "rationale": "why this weight"}}], '
                f'"scores": [{{"option": "option1", "criterion_scores": {{"criterion": 8}}, "weighted_total": 7.5}}], '
                f'"recommendation": "best option", '
                f'"sensitivity": "how robust is this ranking", '
                f'"confidence": 0.0-1.0}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a multi-criteria decision analysis (MCDA) expert — trained in AHP, TOPSIS, "
                    "and weighted scoring methods. Decompose complex decisions systematically. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.4,
                max_tokens=1000
            )

            if response.success:
                data = _extract_json(response.text)
                if data:
                    return data

        except Exception as e:
            import logging
            logging.getLogger("decision_theory").error(f"Multi-criteria analysis failed: {e}")

        return {"error": "Analysis failed"}

    def _save_data(self):
        try:
            data = {
                "decisions": [d.to_dict() for d in self._decisions[-200:]],
                "game_analyses": [g.to_dict() for g in self._game_analyses[-100:]],
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
                logger.info("📂 Loaded decision theory data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}

decision_theory = DecisionTheoryEngine()
