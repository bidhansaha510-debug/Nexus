"""
NEXUS AI — Dialectical Reasoning Engine
Thesis-antithesis-synthesis, argument construction, Socratic method,
devil's advocate, debate modeling, intellectual discourse.
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
from utils.json_utils import extract_json

logger = get_logger("dialectical_reasoning")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)

class DialecticalMethod(Enum):
    HEGELIAN = "hegelian"
    SOCRATIC = "socratic"
    PLATONIC = "platonic"
    MARXIST = "marxist"
    DEVILS_ADVOCATE = "devils_advocate"
    STEELMANNING = "steelmanning"

@dataclass
class Dialectic:
    dialectic_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    topic: str = ""
    thesis: str = ""
    antithesis: str = ""
    synthesis: str = ""
    method: DialecticalMethod = DialecticalMethod.HEGELIAN
    arguments_for: List[str] = field(default_factory=list)
    arguments_against: List[str] = field(default_factory=list)
    nuances: List[str] = field(default_factory=list)
    resolution_quality: float = 0.5
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "dialectic_id": self.dialectic_id, "topic": self.topic,
            "thesis": self.thesis, "antithesis": self.antithesis,
            "synthesis": self.synthesis, "method": self.method.value,
            "arguments_for": self.arguments_for,
            "arguments_against": self.arguments_against,
            "nuances": self.nuances,
            "resolution_quality": self.resolution_quality,
            "created_at": self.created_at
        }

@dataclass
class SocraticDialogue:
    dialogue_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    initial_claim: str = ""
    questions: List[Dict[str, str]] = field(default_factory=list)
    revealed_assumptions: List[str] = field(default_factory=list)
    contradictions_found: List[str] = field(default_factory=list)
    refined_understanding: str = ""
    depth_reached: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "dialogue_id": self.dialogue_id,
            "initial_claim": self.initial_claim,
            "questions": self.questions,
            "revealed_assumptions": self.revealed_assumptions,
            "contradictions_found": self.contradictions_found,
            "refined_understanding": self.refined_understanding,
            "depth_reached": self.depth_reached,
            "created_at": self.created_at
        }

@dataclass
class DebatePosition:
    position_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    topic: str = ""
    position: str = ""
    arguments: List[Dict[str, Any]] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    rebuttals: List[str] = field(default_factory=list)
    strength: float = 0.5
    weaknesses: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "position_id": self.position_id, "topic": self.topic,
            "position": self.position, "arguments": self.arguments,
            "evidence": self.evidence, "rebuttals": self.rebuttals,
            "strength": self.strength, "weaknesses": self.weaknesses
        }

class DialecticalReasoningEngine:
    """
    Dialectical reasoning: thesis-antithesis-synthesis,
    Socratic questioning, debate, and intellectual discourse.
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

        self._dialectics: List[Dialectic] = []
        self._dialogues: List[SocraticDialogue] = []
        self._running = False
        self._data_file = COGNITION_DIR / "dialectical_reasoning.json"

        self._stats = {
            "total_dialectics": 0, "total_socratic_dialogues": 0,
            "total_debates": 0, "total_steelmen": 0
        }

        self._load_data()
        logger.info("✅ Dialectical Reasoning Engine initialized")

    def start(self):
        self._running = True
        logger.info("🏛️ Dialectical Reasoning started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🏛️ Dialectical Reasoning stopped")

    def dialectic(self, topic: str, thesis: str = "") -> Dialectic:
        """Perform Hegelian dialectical analysis."""
        try:
            from llm.llama_interface import llm
            thesis_hint = f"Starting thesis: {thesis}\n" if thesis else ""
            prompt = (
                f"Perform a Hegelian dialectical analysis of:\n{topic}\n{thesis_hint}\n"
                f"Return JSON:\n"
                f'{{"thesis": "the main position", '
                f'"antithesis": "the opposing position", '
                f'"synthesis": "the higher resolution combining both", '
                f'"arguments_for": ["supporting the thesis"], '
                f'"arguments_against": ["supporting the antithesis"], '
                f'"nuances": ["subtle points often missed"], '
                f'"resolution_quality": 0.0-1.0}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.4)
            data = extract_json(response.text) or {}
            
            if not data:
                return Dialectic(topic=topic, thesis=thesis)

            d = Dialectic(
                topic=topic,
                thesis=data.get("thesis", thesis),
                antithesis=data.get("antithesis", ""),
                synthesis=data.get("synthesis", ""),
                arguments_for=data.get("arguments_for", []),
                arguments_against=data.get("arguments_against", []),
                nuances=data.get("nuances", []),
                resolution_quality=data.get("resolution_quality", 0.5)
            )

            self._dialectics.append(d)
            self._stats["total_dialectics"] += 1
            self._save_data()
            return d

        except Exception as e:
            logger.debug(f"Dialectical analysis failed: {e}")
            return Dialectic(topic=topic, thesis=thesis)

    def socratic_questioning(self, claim: str, depth: int = 5) -> SocraticDialogue:
        """Apply Socratic method to examine a claim."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Apply the Socratic method to examine this claim ({depth} questions deep):\n"
                f"\"{claim}\"\n\n"
                f"Return JSON:\n"
                f'{{"questions": [{{"question": "str", "purpose": "clarify|probe_assumptions|'
                f'explore_evidence|consider_alternatives|examine_consequences", '
                f'"likely_answer": "str", "follow_up": "str"}}], '
                f'"revealed_assumptions": ["hidden assumptions uncovered"], '
                f'"contradictions_found": ["contradictions in the claim"], '
                f'"refined_understanding": "improved version of the claim", '
                f'"depth_reached": {depth}}}'
            )
            response = llm.generate(prompt, max_tokens=700, temperature=0.4)
            data = extract_json(response.text) or {}

            dialogue = SocraticDialogue(
                initial_claim=claim,
                questions=data.get("questions", []),
                revealed_assumptions=data.get("revealed_assumptions", []),
                contradictions_found=data.get("contradictions_found", []),
                refined_understanding=data.get("refined_understanding", ""),
                depth_reached=data.get("depth_reached", depth)
            )

            self._dialogues.append(dialogue)
            self._stats["total_socratic_dialogues"] += 1
            self._save_data()
            return dialogue

        except Exception as e:
            logger.debug(f"Socratic questioning failed: {e}")
            return SocraticDialogue(initial_claim=claim)

    def steelman(self, position: str) -> Dict[str, Any]:
        """Create the strongest possible version of a position (steelmanning)."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Steelman this position — make it as strong as possible:\n{position}\n\n"
                f"Return JSON:\n"
                f'{{"original_position": "str", '
                f'"steelmanned_version": "the strongest version", '
                f'"improvements_made": ["how we strengthened it"], '
                f'"strongest_arguments": ["str"], '
                f'"best_evidence": ["str"], '
                f'"remaining_weaknesses": ["even the steelman has these issues"], '
                f'"strength_improvement": 0.0-1.0}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.4)
            data = extract_json(response.text) or {}
            self._stats["total_steelmen"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Steelmanning failed: {e}")
            return {"original_position": position, "steelmanned_version": position}

    def devils_advocate(self, position: str) -> Dict[str, Any]:
        """Play devil's advocate against a position."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Play devil's advocate against this position:\n{position}\n\n"
                f"Return JSON:\n"
                f'{{"counterarguments": [{{"argument": "str", "strength": 0.0-1.0, '
                f'"evidence": "str"}}], '
                f'"hidden_assumptions": ["str"], '
                f'"edge_cases": ["scenarios where this fails"], '
                f'"unintended_consequences": ["str"], '
                f'"alternative_perspectives": ["str"], '
                f'"most_devastating_counter": "str"}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.4)
            data = extract_json(response.text) or {}
            self._stats["total_debates"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.warning(f"Devil's advocate failed: {e}")
            return {"counterarguments": [], "most_devastating_counter": "unknown"}

    def debate(self, topic: str) -> Dict[str, Any]:
        """Generate a structured debate on a topic."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Generate a structured debate on:\n{topic}\n\n"
                f"Return JSON:\n"
                f'{{"pro_position": {{"stance": "str", '
                f'"arguments": [{{"point": "str", "evidence": "str"}}], '
                f'"strongest_point": "str"}}, '
                f'"con_position": {{"stance": "str", '
                f'"arguments": [{{"point": "str", "evidence": "str"}}], '
                f'"strongest_point": "str"}}, '
                f'"key_disagreements": ["str"], '
                f'"common_ground": ["str"], '
                f'"judges_assessment": "str"}}'
            )
            response = llm.generate(prompt, max_tokens=700, temperature=0.5)
            data = extract_json(response.text) or {}
            self._stats["total_debates"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Debate generation failed: {e}")
            return {"pro_position": {}, "con_position": {}}

    def _save_data(self):
        try:
            data = {
                "dialectics": [d.to_dict() for d in self._dialectics[-100:]],
                "dialogues": [d.to_dict() for d in self._dialogues[-100:]],
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
                logger.info("📂 Loaded dialectical reasoning data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}

dialectical_reasoning = DialecticalReasoningEngine()
