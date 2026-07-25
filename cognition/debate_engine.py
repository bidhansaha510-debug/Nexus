"""
NEXUS AI — Debate Engine
Structured argumentation, rebuttal generation,
argument evaluation, rhetoric analysis.
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

logger = get_logger("debate_engine")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)

class DebateFormat(Enum):
    OXFORD = "oxford"
    LINCOLN_DOUGLAS = "lincoln_douglas"
    PARLIAMENTARY = "parliamentary"
    SOCRATIC = "socratic"
    INFORMAL = "informal"

class ArgumentStrength(Enum):
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    COMPELLING = "compelling"
    IRREFUTABLE = "irrefutable"

@dataclass
class Argument:
    argument_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    position: str = ""
    claim: str = ""
    evidence: List[str] = field(default_factory=list)
    reasoning: str = ""
    strength: ArgumentStrength = ArgumentStrength.MODERATE
    rebuttals: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "argument_id": self.argument_id, "position": self.position[:200],
            "claim": self.claim, "evidence": self.evidence,
            "reasoning": self.reasoning, "strength": self.strength.value,
            "rebuttals": self.rebuttals, "created_at": self.created_at
        }

class DebateEngine:
    """
    Structured argumentation — build arguments, generate rebuttals,
    evaluate rhetoric, conduct structured debates.
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

        self._arguments: List[Argument] = []
        self._running = False
        self._data_file = COGNITION_DIR / "debate_engine.json"

        self._stats = {
            "total_arguments": 0, "total_rebuttals": 0,
            "total_evaluations": 0, "total_debates": 0
        }

        self._load_data()
        logger.info("✅ Debate Engine initialized")

    def start(self):
        self._running = True
        logger.info("🎙️ Debate Engine started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🎙️ Debate Engine stopped")

    def build_argument(self, position: str) -> Argument:
        """Build a strong argument for a position."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Build the strongest possible argument for:\n{position}\n\n"
                f"Return JSON:\n"
                f'{{"claim": "the central claim", '
                f'"evidence": ["supporting evidence/facts"], '
                f'"reasoning": "logical chain from evidence to conclusion", '
                f'"strength": "weak|moderate|strong|compelling|irrefutable", '
                f'"emotional_appeal": "how to make it resonate emotionally", '
                f'"preemptive_rebuttals": ["address likely counter-arguments"], '
                f'"rhetorical_technique": "the main persuasion technique used", '
                f'"conclusion": "the closing statement"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            as_map = {a.value: a for a in ArgumentStrength}

            argument = Argument(
                position=position,
                claim=data.get("claim", ""),
                evidence=data.get("evidence", []),
                reasoning=data.get("reasoning", ""),
                strength=as_map.get(data.get("strength", "moderate"), ArgumentStrength.MODERATE),
                rebuttals=data.get("preemptive_rebuttals", [])
            )

            self._arguments.append(argument)
            self._stats["total_arguments"] += 1
            self._save_data()
            return argument

        except Exception as e:
            logger.debug(f"Argument building failed: {e}")
            return Argument(position=position)

    def generate_rebuttal(self, argument: str) -> Dict[str, Any]:
        """Generate a rebuttal to an argument."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Generate a devastating rebuttal to:\n{argument}\n\n"
                f"Return JSON:\n"
                f'{{"rebuttal": "the core counter-argument", '
                f'"attack_points": [{{"weakness": "str", "attack": "str"}}], '
                f'"evidence_against": ["counter-evidence"], '
                f'"logical_flaws": ["logical errors in the original"], '
                f'"alternative_explanation": "a better explanation of the same facts", '
                f'"rhetorical_counter": "rhetorically effective response", '
                f'"concession": "what you can concede without losing the debate"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            if not response.success or not response.text:
                return {"rebuttal": "", "attack_points": []}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"rebuttal": "", "attack_points": []}
            self._stats["total_rebuttals"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Rebuttal generation failed: {e}")
            return {"rebuttal": "", "attack_points": []}

    def evaluate_argument(self, argument: str) -> Dict[str, Any]:
        """Evaluate the strength and quality of an argument."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Evaluate this argument's quality:\n{argument}\n\n"
                f"Return JSON:\n"
                f'{{"overall_strength": "weak|moderate|strong|compelling|irrefutable", '
                f'"logic_score": 0.0-1.0, '
                f'"evidence_score": 0.0-1.0, '
                f'"rhetoric_score": 0.0-1.0, '
                f'"clarity_score": 0.0-1.0, '
                f'"weaknesses": ["specific weaknesses"], '
                f'"strengths": ["specific strengths"], '
                f'"improvement_suggestions": ["how to strengthen this"], '
                f'"persuasiveness": 0.0-1.0}}'
            )
            response = llm.generate(prompt, max_tokens=400, temperature=0.3)
            if not response.success or not response.text:
                return {"overall_strength": "moderate", "logic_score": 0.0}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"overall_strength": "moderate", "logic_score": 0.0}
            self._stats["total_evaluations"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Argument evaluation failed: {e}")
            return {"overall_strength": "moderate", "logic_score": 0.0}

    def structured_debate(self, topic: str, pro: str = "", con: str = "") -> Dict[str, Any]:
        """Conduct a structured debate on a topic."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Conduct a structured debate on: {topic}\n"
                + (f"Pro position: {pro}\n" if pro else "")
                + (f"Con position: {con}\n" if con else "")
                + f"\nReturn JSON:\n"
                f'{{"opening_pro": "opening argument for the motion", '
                f'"opening_con": "opening argument against", '
                f'"rebuttal_pro": "pro rebuttal", '
                f'"rebuttal_con": "con rebuttal", '
                f'"closing_pro": "pro closing", '
                f'"closing_con": "con closing", '
                f'"judge_verdict": "which side argued better and why", '
                f'"key_clash_points": ["the main points of disagreement"], '
                f'"winner": "pro|con|draw"}}'
            )
            response = llm.generate(prompt, max_tokens=700, temperature=0.5)
            if not response.success or not response.text:
                return {"judge_verdict": "", "winner": "draw"}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"judge_verdict": "", "winner": "draw"}
            self._stats["total_debates"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Structured debate failed: {e}")
            return {"judge_verdict": "", "winner": "draw"}

    def _save_data(self):
        try:
            data = {
                "arguments": [a.to_dict() for a in self._arguments[-200:]],
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
                logger.info("📂 Loaded debate engine data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}

debate_engine = DebateEngine()
