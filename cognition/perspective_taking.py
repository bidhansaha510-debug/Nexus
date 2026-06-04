"""
NEXUS AI — Perspective Taking Engine
Simulate other viewpoints, role-playing different identities,
first-person experience simulation, bias awareness.
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

logger = get_logger("perspective_taking")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)


class PerspectiveType(Enum):
    PERSONAL = "personal"
    PROFESSIONAL = "professional"
    CULTURAL = "cultural"
    TEMPORAL = "temporal"       # Past/future self
    ADVERSARIAL = "adversarial"
    EMPATHETIC = "empathetic"
    CONTRARIAN = "contrarian"


@dataclass
class Perspective:
    perspective_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    topic: str = ""
    viewpoint_holder: str = ""
    perspective_type: PerspectiveType = PerspectiveType.PERSONAL
    viewpoint: str = ""
    reasoning: str = ""
    emotional_tone: str = ""
    blind_spots: List[str] = field(default_factory=list)
    values_prioritized: List[str] = field(default_factory=list)
    agreement_with_original: float = 0.5
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "perspective_id": self.perspective_id, "topic": self.topic[:200],
            "viewpoint_holder": self.viewpoint_holder,
            "perspective_type": self.perspective_type.value,
            "viewpoint": self.viewpoint, "reasoning": self.reasoning,
            "emotional_tone": self.emotional_tone,
            "blind_spots": self.blind_spots,
            "values_prioritized": self.values_prioritized,
            "agreement_with_original": self.agreement_with_original,
            "created_at": self.created_at
        }


class PerspectiveTakingEngine:
    """
    Simulate other viewpoints and experiences — role-play different
    identities, understand biases, see issues from multiple angles.
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

        self._perspectives: List[Perspective] = []
        self._running = False
        self._data_file = COGNITION_DIR / "perspective_taking.json"

        self._stats = {
            "total_perspectives": 0, "total_role_plays": 0,
            "total_bias_checks": 0, "total_multi_views": 0
        }

        self._load_data()
        logger.info("✅ Perspective Taking Engine initialized")

    def start(self):
        self._running = True
        logger.info("👁️ Perspective Taking started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("👁️ Perspective Taking stopped")

    def take_perspective(self, topic: str, viewpoint_holder: str) -> Perspective:
        """See a topic from someone else's perspective."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Take the perspective of {viewpoint_holder} on this topic:\n"
                f"Topic: {topic}\n\n"
                f"Think and respond AS IF you were {viewpoint_holder}.\n\n"
                f"Return JSON:\n"
                f'{{"viewpoint": "their actual perspective in first person", '
                f'"reasoning": "why they think this way", '
                f'"emotional_tone": "how they feel about it", '
                f'"perspective_type": "personal|professional|cultural|temporal|adversarial|empathetic|contrarian", '
                f'"blind_spots": ["what they might miss"], '
                f'"values_prioritized": ["what they value most"], '
                f'"agreement_with_original": 0.0-1.0}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.5)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            pt_map = {p.value: p for p in PerspectiveType}

            perspective = Perspective(
                topic=topic, viewpoint_holder=viewpoint_holder,
                perspective_type=pt_map.get(data.get("perspective_type", "personal"), PerspectiveType.PERSONAL),
                viewpoint=data.get("viewpoint", ""),
                reasoning=data.get("reasoning", ""),
                emotional_tone=data.get("emotional_tone", ""),
                blind_spots=data.get("blind_spots", []),
                values_prioritized=data.get("values_prioritized", []),
                agreement_with_original=data.get("agreement_with_original", 0.5)
            )

            self._perspectives.append(perspective)
            self._stats["total_perspectives"] += 1
            self._save_data()
            return perspective

        except Exception as e:
            logger.debug(f"Perspective taking failed: {e}")
            return Perspective(topic=topic, viewpoint_holder=viewpoint_holder)

    def multi_perspective(self, topic: str, holders: List[str] = None) -> Dict[str, Any]:
        """Get multiple perspectives on a topic at once."""
        try:
            from llm.llama_interface import llm
            holder_str = f"Perspectives: {', '.join(holders)}" if holders else "Generate 4 diverse perspectives"
            prompt = (
                f"Show multiple perspectives on:\n{topic}\n{holder_str}\n\n"
                f"Return JSON:\n"
                f'{{"perspectives": [{{"holder": "who", "viewpoint": "their view", '
                f'"key_value": "what they prioritize", "emotional_stance": "str"}}], '
                f'"common_ground": ["points of agreement"], '
                f'"irreconcilable_differences": ["fundamental disagreements"], '
                f'"synthesis": "a balanced view incorporating all perspectives"}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.5)
            if not response.success or not response.text:
                return {"perspectives": [], "synthesis": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"perspectives": [], "synthesis": ""}
            self._stats["total_multi_views"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Multi-perspective failed: {e}")
            return {"perspectives": [], "synthesis": ""}

    def check_bias(self, statement: str) -> Dict[str, Any]:
        """Check a statement for perspective biases."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Analyze this statement for perspective biases:\n{statement}\n\n"
                f"Return JSON:\n"
                f'{{"biases_detected": [{{"bias_type": "str", "description": "str", '
                f'"severity": 0.0-1.0}}], '
                f'"assumed_perspective": "whose viewpoint this reflects", '
                f'"excluded_perspectives": ["viewpoints not considered"], '
                f'"debiased_version": "the statement rewritten more inclusively", '
                f'"overall_bias_score": 0.0-1.0}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.3)
            if not response.success or not response.text:
                return {"biases_detected": [], "overall_bias_score": 0.0}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"biases_detected": [], "overall_bias_score": 0.0}
            self._stats["total_bias_checks"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Bias check failed: {e}")
            return {"biases_detected": [], "overall_bias_score": 0.0}

    def role_play(self, character: str, scenario: str) -> Dict[str, Any]:
        """Role-play as a specific character in a scenario."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Role-play as {character} in this scenario:\n{scenario}\n\n"
                f"Return JSON:\n"
                f'{{"character_response": "what they would say/do (in first person)", '
                f'"inner_thoughts": "their private thoughts", '
                f'"emotional_state": "how they feel", '
                f'"motivations": ["what drives their actions"], '
                f'"concerns": ["what worries them"], '
                f'"personality_traits_shown": ["traits visible in this response"]}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.6)
            if not response.success or not response.text:
                return {"character_response": "", "emotional_state": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"character_response": "", "emotional_state": ""}
            self._stats["total_role_plays"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Role play failed: {e}")
            return {"character_response": "", "emotional_state": ""}

    def _save_data(self):
        try:
            data = {
                "perspectives": [p.to_dict() for p in self._perspectives[-200:]],
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
                logger.info("📂 Loaded perspective taking data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def role_reversal(self, situation: str) -> Dict[str, Any]:
        """See a situation from multiple reversed perspectives."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Perform a ROLE REVERSAL analysis for:\n'
                f'"{situation}"\n\n'
                f"View the situation from at least 3 reversed perspectives:\n"
                f"  1. PRIMARY PERSPECTIVE: How the main actor sees it\n"
                f"  2. OPPOSITE PERSPECTIVE: How their counterpart sees it\n"
                f"  3. OBSERVER PERSPECTIVE: How a neutral third party sees it\n"
                f"  4. FUTURE PERSPECTIVE: How they will all see it in hindsight\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"perspectives": [{{"role": "who", "view": "how they see it", '
                f'"emotions": ["what they feel"], "priorities": ["what matters to them"]}}], '
                f'"key_blindspots": ["what each perspective misses"], '
                f'"common_ground": "where all perspectives agree", '
                f'"resolution_insight": "what the role reversal reveals"}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a perspective-taking engine that enables genuine empathetic "
                    "understanding by modeling how different people experience the same situation. "
                    "You practice cognitive empathy without judgment. Respond ONLY with valid JSON."
                ),
                temperature=0.6, max_tokens=800
            )
            if response.success:
                from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"error": "Role reversal failed"}
            return data
        except Exception as e:
            logger.debug(f"Role reversal failed: {e}")
        return {"error": "Role reversal failed"}


    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}


perspective_taking = PerspectiveTakingEngine()
