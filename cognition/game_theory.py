"""
NEXUS AI — Game Theory Engine
Strategic interaction analysis, Nash equilibrium,
payoff matrices, dominant strategies, mechanism design.
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

logger = get_logger("game_theory")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)


class GameType(Enum):
    ZERO_SUM = "zero_sum"
    NON_ZERO_SUM = "non_zero_sum"
    COOPERATIVE = "cooperative"
    SEQUENTIAL = "sequential"
    SIMULTANEOUS = "simultaneous"
    REPEATED = "repeated"
    EVOLUTIONARY = "evolutionary"


@dataclass
class GameAnalysis:
    analysis_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    situation: str = ""
    game_type: GameType = GameType.NON_ZERO_SUM
    players: List[str] = field(default_factory=list)
    strategies: Dict[str, List[str]] = field(default_factory=dict)
    nash_equilibrium: str = ""
    dominant_strategy: str = ""
    recommended_move: str = ""
    payoff_summary: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "analysis_id": self.analysis_id,
            "situation": self.situation[:200],
            "game_type": self.game_type.value,
            "players": self.players,
            "strategies": self.strategies,
            "nash_equilibrium": self.nash_equilibrium,
            "dominant_strategy": self.dominant_strategy,
            "recommended_move": self.recommended_move,
            "payoff_summary": self.payoff_summary,
            "created_at": self.created_at
        }


class GameTheoryEngine:
    """
    Strategic interaction analysis — Nash equilibrium,
    payoff analysis, dominant strategies, mechanism design.
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

        self._analyses: List[GameAnalysis] = []
        self._running = False
        self._data_file = COGNITION_DIR / "game_theory.json"

        self._stats = {
            "total_analyses": 0, "total_dilemmas": 0,
            "total_mechanism_designs": 0, "total_predictions": 0
        }

        self._load_data()
        logger.info("✅ Game Theory Engine initialized")

    def start(self):
        self._running = True
        logger.info("♟️ Game Theory started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("♟️ Game Theory stopped")

    def analyze_game(self, situation: str) -> GameAnalysis:
        """Analyze a strategic interaction using game theory."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Analyze this situation using game theory:\n{situation}\n\n"
                f"Return JSON:\n"
                f'{{"game_type": "zero_sum|non_zero_sum|cooperative|sequential|simultaneous|repeated|evolutionary", '
                f'"players": ["who are the players"], '
                f'"strategies": {{"player": ["their available strategies"]}}, '
                f'"nash_equilibrium": "the equilibrium outcome (if any)", '
                f'"dominant_strategy": "strategy that always works best (if any)", '
                f'"recommended_move": "what to do given this analysis", '
                f'"payoff_summary": "who gains/loses what", '
                f'"key_insight": "the most important strategic insight", '
                f'"classic_game_parallel": "which classic game this resembles (prisoners dilemma, chicken, etc)"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.3)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            gt_map = {g.value: g for g in GameType}

            analysis = GameAnalysis(
                situation=situation,
                game_type=gt_map.get(data.get("game_type", "non_zero_sum"), GameType.NON_ZERO_SUM),
                players=data.get("players", []),
                strategies=data.get("strategies", {}),
                nash_equilibrium=data.get("nash_equilibrium", ""),
                dominant_strategy=data.get("dominant_strategy", ""),
                recommended_move=data.get("recommended_move", ""),
                payoff_summary=data.get("payoff_summary", "")
            )

            self._analyses.append(analysis)
            self._stats["total_analyses"] += 1
            self._save_data()
            return analysis

        except Exception as e:
            logger.debug(f"Game analysis failed: {e}")
            return GameAnalysis(situation=situation)

    def prisoners_dilemma(self, scenario: str) -> Dict[str, Any]:
        """Analyze a scenario as a prisoner's dilemma variant."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Analyze this as a prisoner's dilemma:\n{scenario}\n\n"
                f"Return JSON:\n"
                f'{{"cooperate_cooperate": "outcome if both cooperate", '
                f'"defect_defect": "outcome if both defect", '
                f'"cooperate_defect": "outcome if you cooperate and they defect", '
                f'"defect_cooperate": "outcome if you defect and they cooperate", '
                f'"is_true_pd": true/false, '
                f'"recommended_strategy": "cooperate|defect|tit_for_tat|generous_tit_for_tat", '
                f'"iterated": true/false, '
                f'"trust_factor": 0.0-1.0, '
                f'"reasoning": "why this strategy is recommended"}}'
            )
            response = llm.generate(prompt, max_tokens=400, temperature=0.3)
            if not response.success or not response.text:
                return {"recommended_strategy": "", "is_true_pd": False}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"recommended_strategy": "", "is_true_pd": False}
            self._stats["total_dilemmas"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.warning(f"Prisoner's dilemma analysis failed: {e}")
            return {"recommended_strategy": "", "is_true_pd": False}

    def predict_behavior(self, actors: str, incentives: str) -> Dict[str, Any]:
        """Predict rational behavior given incentives."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Predict behavior using game theory:\n"
                f"Actors: {actors}\nIncentives: {incentives}\n\n"
                f"Return JSON:\n"
                f'{{"predicted_actions": [{{"actor": "str", "likely_action": "str", '
                f'"probability": 0.0-1.0, "reasoning": "str"}}], '
                f'"equilibrium_outcome": "most likely stable outcome", '
                f'"wildcard_scenarios": ["unlikely but possible outcomes"], '
                f'"assumptions": ["assumptions in this prediction"], '
                f'"confidence": 0.0-1.0}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.3)
            if not response.success or not response.text:
                return {"predicted_actions": [], "confidence": 0.0}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"predicted_actions": [], "confidence": 0.0}
            self._stats["total_predictions"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Behavior prediction failed: {e}")
            return {"predicted_actions": [], "confidence": 0.0}

    def design_mechanism(self, goal: str, constraints: str = "") -> Dict[str, Any]:
        """Design incentive mechanisms to achieve desired outcomes."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Design an incentive mechanism:\nGoal: {goal}\n"
                + (f"Constraints: {constraints}\n" if constraints else "") +
                f"\nReturn JSON:\n"
                f'{{"mechanism": "description of the incentive system", '
                f'"incentive_structure": [{{"action": "str", "reward": "str", "penalty": "str"}}], '
                f'"alignment_score": 0.0-1.0, '
                f'"gaming_risks": ["ways this could be exploited"], '
                f'"unintended_consequences": ["possible side effects"], '
                f'"robustness": 0.0-1.0, '
                f'"real_world_examples": ["similar mechanisms that exist"]}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            if not response.success or not response.text:
                return {"mechanism": "", "alignment_score": 0.0}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"mechanism": "", "alignment_score": 0.0}
            self._stats["total_mechanism_designs"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Mechanism design failed: {e}")
            return {"mechanism": "", "alignment_score": 0.0}

    def _save_data(self):
        try:
            data = {
                "analyses": [a.to_dict() for a in self._analyses[-200:]],
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
                logger.info("📂 Loaded game theory data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}


game_theory = GameTheoryEngine()
