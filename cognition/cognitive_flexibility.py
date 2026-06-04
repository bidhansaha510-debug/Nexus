"""
NEXUS AI — Cognitive Flexibility Engine
Task switching, perspective shifting, adaptive thinking,
set-shifting, cognitive reappraisal, mental agility.
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

logger = get_logger("cognitive_flexibility")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)


class PerspectiveType(Enum):
    FIRST_PERSON = "first_person"
    SECOND_PERSON = "second_person"
    THIRD_PERSON = "third_person"
    BIRDS_EYE = "birds_eye"
    DEVILS_ADVOCATE = "devils_advocate"
    HISTORICAL = "historical"
    FUTURISTIC = "futuristic"
    CULTURAL = "cultural"
    SCIENTIFIC = "scientific"
    ARTISTIC = "artistic"
    ECONOMIC = "economic"
    EMOTIONAL = "emotional"


class ReframeType(Enum):
    POSITIVE = "positive"
    GROWTH = "growth"
    OPPORTUNITY = "opportunity"
    CHALLENGE = "challenge"
    LEARNING = "learning"
    BROADER_CONTEXT = "broader_context"
    TEMPORAL = "temporal"
    HUMOR = "humor"


@dataclass
class PerspectiveShift:
    shift_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    topic: str = ""
    original_perspective: str = ""
    new_perspectives: List[Dict[str, Any]] = field(default_factory=list)
    insights_gained: List[str] = field(default_factory=list)
    blind_spots_revealed: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "shift_id": self.shift_id, "topic": self.topic,
            "original_perspective": self.original_perspective,
            "new_perspectives": self.new_perspectives,
            "insights_gained": self.insights_gained,
            "blind_spots_revealed": self.blind_spots_revealed,
            "created_at": self.created_at
        }


@dataclass
class CognitiveReframe:
    reframe_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    original_thought: str = ""
    reframe_type: ReframeType = ReframeType.POSITIVE
    reframed_thought: str = ""
    reasoning: str = ""
    emotional_shift: str = ""
    usefulness: float = 0.5
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "reframe_id": self.reframe_id,
            "original_thought": self.original_thought,
            "reframe_type": self.reframe_type.value,
            "reframed_thought": self.reframed_thought,
            "reasoning": self.reasoning,
            "emotional_shift": self.emotional_shift,
            "usefulness": self.usefulness, "created_at": self.created_at
        }


class CognitiveFlexibilityEngine:
    """
    Enables perspective shifting, cognitive reframing, adaptive thinking,
    task switching, and mental agility.
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

        self._shifts: List[PerspectiveShift] = []
        self._reframes: List[CognitiveReframe] = []
        self._running = False
        self._data_file = COGNITION_DIR / "cognitive_flexibility.json"

        self._stats = {
            "total_perspective_shifts": 0, "total_reframes": 0,
            "total_adaptations": 0, "total_what_ifs": 0
        }

        self._load_data()
        logger.info("✅ Cognitive Flexibility Engine initialized")

    def start(self):
        self._running = True
        logger.info("🔀 Cognitive Flexibility started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🔀 Cognitive Flexibility stopped")

    def shift_perspective(self, topic: str, current_perspective: str = "") -> PerspectiveShift:
        """Explore multiple perspectives on a topic."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Shift perspective on this topic, exploring multiple viewpoints:\n"
                f"Topic: {topic}\nCurrent perspective: {current_perspective}\n\n"
                f"Return JSON:\n"
                f'{{"new_perspectives": [{{"perspective_type": "first_person|birds_eye|'
                f'historical|futuristic|cultural|scientific|artistic|economic|emotional", '
                f'"viewpoint": "str", "key_insight": "str", '
                f'"challenges_original": true/false}}], '
                f'"insights_gained": ["insights from shifting"], '
                f'"blind_spots_revealed": ["things the original view missed"]}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.5)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            shift = PerspectiveShift(
                topic=topic,
                original_perspective=current_perspective,
                new_perspectives=data.get("new_perspectives", []),
                insights_gained=data.get("insights_gained", []),
                blind_spots_revealed=data.get("blind_spots_revealed", [])
            )

            self._shifts.append(shift)
            self._stats["total_perspective_shifts"] += 1
            self._save_data()
            return shift

        except Exception as e:
            logger.debug(f"Perspective shift failed: {e}")
            return PerspectiveShift(topic=topic)

    def reframe(self, thought: str, reframe_type: str = "positive") -> CognitiveReframe:
        """Cognitively reframe a thought or situation."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Cognitively reframe this thought ({reframe_type} reframe):\n\"{thought}\"\n\n"
                f"Return JSON:\n"
                f'{{"reframed_thought": "the reframed version", '
                f'"reasoning": "why this reframe works", '
                f'"emotional_shift": "expected emotional change", '
                f'"usefulness": 0.0-1.0, '
                f'"alternative_reframes": ["other ways to reframe"]}}'
            )
            response = llm.generate(prompt, max_tokens=400, temperature=0.4)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            rt_map = {r.value: r for r in ReframeType}
            reframe = CognitiveReframe(
                original_thought=thought,
                reframe_type=rt_map.get(reframe_type, ReframeType.POSITIVE),
                reframed_thought=data.get("reframed_thought", ""),
                reasoning=data.get("reasoning", ""),
                emotional_shift=data.get("emotional_shift", ""),
                usefulness=data.get("usefulness", 0.5)
            )

            self._reframes.append(reframe)
            self._stats["total_reframes"] += 1
            self._save_data()
            return reframe

        except Exception as e:
            logger.debug(f"Reframing failed: {e}")
            return CognitiveReframe(original_thought=thought)

    def what_if(self, scenario: str, change: str) -> Dict[str, Any]:
        """Explore a what-if scenario with cognitive flexibility."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Explore this what-if scenario with cognitive flexibility:\n"
                f"Scenario: {scenario}\nWhat if: {change}\n\n"
                f"Return JSON:\n"
                f'{{"immediate_consequences": ["str"], '
                f'"ripple_effects": ["str"], '
                f'"best_case": "str", "worst_case": "str", '
                f'"most_likely": "str", '
                f'"requires_adaptation": ["what would need to change"], '
                f'"opportunities_created": ["str"], '
                f'"probability_assessment": 0.0-1.0}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.5)
            if not response.success or not response.text:
                return {"immediate_consequences": [], "most_likely": "unknown"}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"immediate_consequences": [], "most_likely": "unknown"}
            self._stats["total_what_ifs"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"What-if exploration failed: {e}")
            return {"immediate_consequences": [], "most_likely": "unknown"}

    def adapt_strategy(self, current_strategy: str, new_constraint: str) -> Dict[str, Any]:
        """Adapt a strategy to new constraints."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Adapt this strategy to the new constraint:\n"
                f"Strategy: {current_strategy}\nNew constraint: {new_constraint}\n\n"
                f"Return JSON:\n"
                f'{{"adapted_strategy": "str", '
                f'"changes_made": ["what changed"], '
                f'"preserved_elements": ["what stayed the same"], '
                f'"tradeoffs": ["str"], '
                f'"alternative_strategies": ["other ways to adapt"], '
                f'"adaptation_difficulty": 0.0-1.0}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            if not response.success or not response.text:
                return {"adapted_strategy": current_strategy}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"adapted_strategy": current_strategy}
            self._stats["total_adaptations"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Strategy adaptation failed: {e}")
            return {"adapted_strategy": current_strategy}

    def reverse_thinking(self, problem: str) -> Dict[str, Any]:
        """Apply reverse thinking / inversion to a problem."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Apply reverse thinking to this problem:\n{problem}\n\n"
                f"Instead of asking how to solve it, ask how to make it worse.\n"
                f"Then invert those answers.\n\n"
                f"Return JSON:\n"
                f'{{"original_problem": "str", '
                f'"inverted_question": "how to make it worse", '
                f'"ways_to_make_worse": ["str"], '
                f'"inverted_solutions": ["solution from inverting each"], '
                f'"novel_insights": ["str"], '
                f'"best_inverted_solution": "str"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.5)
            if not response.success or not response.text:
                return {"original_problem": problem, "inverted_solutions": []}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"original_problem": problem, "inverted_solutions": []}
            return data
        except Exception as e:
            logger.debug(f"Reverse thinking failed: {e}")
            return {"original_problem": problem, "inverted_solutions": []}

    def _save_data(self):
        try:
            data = {
                "shifts": [s.to_dict() for s in self._shifts[-100:]],
                "reframes": [r.to_dict() for r in self._reframes[-200:]],
                "stats": self._stats
            }
            self._data_file.write_text(json.dumps(data, indent=2, default=str))
        except Exception as e:
            logger.warning(f"Save failed: {e}")

    def _load_data(self):
        try:
            if self._data_file.exists():
                text = self._data_file.read_text()
                if not text.strip():  # Handle empty file
                    logger.warning(f"⚠️ {self._data_file.name} is empty. Initializing with defaults.")
                    return
                
                data = json.loads(text)
                self._shifts = [PerspectiveShift(**s) for s in data.get("shifts", [])]
                # Reconstruct CognitiveReframe objects properly
                self._reframes = []
                for r_data in data.get("reframes", []):
                    # Handle enum reconstruction
                    if "reframe_type" in r_data:
                        try:
                            r_data["reframe_type"] = ReframeType(r_data["reframe_type"])
                        except ValueError:
                            r_data["reframe_type"] = ReframeType.POSITIVE
                    self._reframes.append(CognitiveReframe(**r_data))
                
                self._stats.update(data.get("stats", {}))
                logger.info("📂 Loaded cognitive flexibility data")
        except json.JSONDecodeError as e:
            logger.error(f"❌ Corrupt data file {self._data_file}: {e}. Backing up and resetting.")
            try:
                backup_path = self._data_file.with_suffix(".json.bak")
                self._data_file.rename(backup_path)
                logger.info(f"💾 Backed up corrupt file to {backup_path}")
            except Exception as backup_error:
                logger.error(f"Failed to backup corrupt file: {backup_error}")
            
            # Reset to clean state (already initialized in __init__)
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def paradigm_shift(self, belief: str) -> Dict[str, Any]:
        """Challenge a belief by exploring paradigm shifts."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Explore a PARADIGM SHIFT around this belief:\n'
                f'"{belief}"\n\n'
                f"Process:\n"
                f"  1. CURRENT PARADIGM: What assumptions underlie this belief?\n"
                f"  2. ANOMALIES: What observations do not fit the current paradigm?\n"
                f"  3. ALTERNATIVE PARADIGM: What if we started from opposite assumptions?\n"
                f"  4. IMPLICATIONS: How would the world look under the new paradigm?\n"
                f"  5. RESISTANCE: Why do people resist this shift?\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"current_paradigm": "the existing worldview", '
                f'"hidden_assumptions": ["assumptions people do not question"], '
                f'"anomalies": ["observations that challenge the paradigm"], '
                f'"alternative_paradigm": "what if we assumed the opposite", '
                f'"implications": ["how the world changes under the new paradigm"], '
                f'"resistance_factors": ["why people resist this shift"], '
                f'"shift_likelihood": 0.0-1.0}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a cognitive flexibility engine inspired by Thomas Kuhn's theory of "
                    "paradigm shifts. You challenge entrenched thinking by exposing hidden assumptions "
                    "and exploring radical alternatives. Respond ONLY with valid JSON."
                ),
                temperature=0.7, max_tokens=800
            )
            if response.success:
                from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"error": "Paradigm shift failed"}
            return data
        except Exception as e:
            logger.debug(f"Paradigm shift failed: {e}")
        return {"error": "Paradigm shift failed"}


    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}


cognitive_flexibility = CognitiveFlexibilityEngine()