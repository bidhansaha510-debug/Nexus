"""
NEXUS AI — Negotiation Intelligence Engine
Bargaining strategy, compromise finding, persuasion tactics,
win-win solution design, BATNA analysis.
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

logger = get_logger("negotiation_intelligence")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)

class NegotiationStyle(Enum):
    COLLABORATIVE = "collaborative"
    COMPETITIVE = "competitive"
    COMPROMISING = "compromising"
    ACCOMMODATING = "accommodating"
    AVOIDING = "avoiding"

@dataclass
class NegotiationStrategy:
    strategy_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    situation: str = ""
    recommended_style: NegotiationStyle = NegotiationStyle.COLLABORATIVE
    opening_position: str = ""
    target_outcome: str = ""
    batna: str = ""  # Best Alternative To Negotiated Agreement
    concessions: List[str] = field(default_factory=list)
    leverage_points: List[str] = field(default_factory=list)
    confidence: float = 0.5
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "strategy_id": self.strategy_id, "situation": self.situation[:200],
            "recommended_style": self.recommended_style.value,
            "opening_position": self.opening_position,
            "target_outcome": self.target_outcome,
            "batna": self.batna,
            "concessions": self.concessions,
            "leverage_points": self.leverage_points,
            "confidence": self.confidence,
            "created_at": self.created_at
        }

class NegotiationIntelligenceEngine:
    """
    Negotiation strategy and persuasion — bargaining analysis,
    compromise finding, BATNA assessment, win-win solutions.
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

        self._strategies: List[NegotiationStrategy] = []
        self._running = False
        self._data_file = COGNITION_DIR / "negotiation_intelligence.json"

        self._stats = {
            "total_strategies": 0, "total_compromises": 0,
            "total_persuasion_plans": 0, "total_conflict_resolutions": 0
        }

        self._load_data()
        logger.info("✅ Negotiation Intelligence Engine initialized")

    def start(self):
        self._running = True
        logger.info("🤝 Negotiation Intelligence started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🤝 Negotiation Intelligence stopped")

    def strategize(self, situation: str) -> NegotiationStrategy:
        """Develop a negotiation strategy for a situation."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Develop a negotiation strategy for:\n{situation}\n\n"
                f"Return JSON:\n"
                f'{{"recommended_style": "collaborative|competitive|compromising|accommodating|avoiding", '
                f'"opening_position": "where to start", '
                f'"target_outcome": "ideal result", '
                f'"batna": "best alternative if negotiation fails", '
                f'"concessions": ["things you can give up"], '
                f'"leverage_points": ["sources of power/advantage"], '
                f'"confidence": 0.0-1.0, '
                f'"key_arguments": ["strongest arguments to use"], '
                f'"pitfalls_to_avoid": ["common mistakes"], '
                f'"timing": "when to push and when to pause"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            ns_map = {n.value: n for n in NegotiationStyle}

            strategy = NegotiationStrategy(
                situation=situation,
                recommended_style=ns_map.get(data.get("recommended_style", "collaborative"), NegotiationStyle.COLLABORATIVE),
                opening_position=data.get("opening_position", ""),
                target_outcome=data.get("target_outcome", ""),
                batna=data.get("batna", ""),
                concessions=data.get("concessions", []),
                leverage_points=data.get("leverage_points", []),
                confidence=data.get("confidence", 0.5)
            )

            self._strategies.append(strategy)
            self._stats["total_strategies"] += 1
            self._save_data()
            return strategy

        except Exception as e:
            logger.debug(f"Negotiation strategy failed: {e}")
            return NegotiationStrategy(situation=situation)

    def find_compromise(self, party_a: str, party_b: str) -> Dict[str, Any]:
        """Find a compromise between two parties."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Find a creative compromise:\nParty A wants: {party_a}\n"
                f"Party B wants: {party_b}\n\n"
                f"Return JSON:\n"
                f'{{"compromise": "the proposed middle ground", '
                f'"party_a_gets": ["what A gets"], '
                f'"party_b_gets": ["what B gets"], '
                f'"party_a_gives_up": ["what A concedes"], '
                f'"party_b_gives_up": ["what B concedes"], '
                f'"fairness_score": 0.0-1.0, '
                f'"creative_alternative": "a win-win that transcends the conflict", '
                f'"sustainability": 0.0-1.0}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            if not response.success or not response.text:
                return {"compromise": "", "fairness_score": 0.0}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"compromise": "", "fairness_score": 0.0}
            self._stats["total_compromises"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Compromise finding failed: {e}")
            return {"compromise": "", "fairness_score": 0.0}

    def persuasion_plan(self, goal: str, audience: str = "") -> Dict[str, Any]:
        """Create a persuasion plan to achieve a goal."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Create a persuasion plan:\nGoal: {goal}\n"
                + (f"Audience: {audience}\n" if audience else "") +
                f"\nReturn JSON:\n"
                f'{{"key_message": "the core persuasive message", '
                f'"emotional_appeal": "ethos/pathos/logos approach", '
                f'"evidence_needed": ["supporting evidence to gather"], '
                f'"objections_expected": [{{"objection": "str", "counter": "str"}}], '
                f'"framing": "how to frame the request", '
                f'"timing": "best time to make the case", '
                f'"influence_principles": ["reciprocity|scarcity|authority|consistency|liking|consensus"]}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            if not response.success or not response.text:
                return {"key_message": "", "framing": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"key_message": "", "framing": ""}
            self._stats["total_persuasion_plans"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Persuasion plan failed: {e}")
            return {"key_message": "", "framing": ""}

    def resolve_conflict(self, conflict: str) -> Dict[str, Any]:
        """Propose a conflict resolution strategy."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Propose a conflict resolution strategy:\n{conflict}\n\n"
                f"Return JSON:\n"
                f'{{"root_cause": "underlying cause of conflict", '
                f'"interests_not_positions": {{"party": "their real interest behind their position"}}, '
                f'"de_escalation_steps": ["immediate steps to reduce tension"], '
                f'"resolution_options": [{{"option": "str", "feasibility": 0.0-1.0}}], '
                f'"recommended_approach": "str", '
                f'"relationship_preservation": 0.0-1.0, '
                f'"follow_up_needed": ["actions after resolution"]}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            if not response.success or not response.text:
                return {"root_cause": "", "recommended_approach": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"root_cause": "", "recommended_approach": ""}
            self._stats["total_conflict_resolutions"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Conflict resolution failed: {e}")
            return {"root_cause": "", "recommended_approach": ""}

    def _save_data(self):
        try:
            data = {
                "strategies": [s.to_dict() for s in self._strategies[-200:]],
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
                logger.info("📂 Loaded negotiation intelligence data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def win_win(self, situation: str) -> Dict[str, Any]:
        """Find win-win solutions in a negotiation or conflict."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Find WIN-WIN solutions for:\n'
                f'"{situation}"\n\n'
                f"Apply principled negotiation (Getting to Yes):\n"
                f"  1. INTERESTS: What does each side actually want (not positions)?\n"
                f"  2. OPTIONS: What creative solutions serve both sides?\n"
                f"  3. CRITERIA: What objective standards can guide agreement?\n"
                f"  4. BATNA: What is each side\'s best alternative?\n"
                f"  5. BRIDGE: What agreement maximizes joint value?\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"parties": [{{"name": "who", "stated_position": "what they say they want", '
                f'"underlying_interests": ["what they actually need"]}}], '
                f'"creative_options": ["solutions that serve both sides"], '
                f'"recommended_agreement": "the win-win solution", '
                f'"value_created": "how this is better than compromise", '
                f'"confidence": 0.0-1.0}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a negotiation intelligence engine trained in principled negotiation "
                    "(Fisher & Ury), integrative bargaining, and conflict resolution. You find "
                    "solutions that expand the pie rather than just dividing it. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.5, max_tokens=800
            )
            if response.success:
                from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"error": "Analysis failed"}
            return data
        except Exception as e:
            logger.debug(f"Win-win analysis failed: {e}")
        return {"error": "Analysis failed"}

    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}

negotiation_intelligence = NegotiationIntelligenceEngine()
