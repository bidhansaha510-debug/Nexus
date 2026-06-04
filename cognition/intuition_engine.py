"""
NEXUS AI — Intuition Engine
Fast pattern-based judgment, gut feeling simulation,
heuristic reasoning, System-1 thinking, rapid assessment.
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

logger = get_logger("intuition_engine")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)


class HeuristicType(Enum):
    RECOGNITION = "recognition"
    AVAILABILITY = "availability"
    REPRESENTATIVENESS = "representativeness"
    ANCHORING = "anchoring"
    AFFECT = "affect"
    SATISFICING = "satisficing"
    TAKE_THE_BEST = "take_the_best"
    FLUENCY = "fluency"
    FAMILIARITY = "familiarity"
    GAZE = "gaze"


class IntuitionStrength(Enum):
    WHISPER = "whisper"
    NUDGE = "nudge"
    CLEAR = "clear"
    STRONG = "strong"
    OVERWHELMING = "overwhelming"


@dataclass
class Intuition:
    intuition_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    situation: str = ""
    gut_feeling: str = ""
    direction: str = ""  # positive/negative/neutral/mixed
    strength: IntuitionStrength = IntuitionStrength.NUDGE
    confidence: float = 0.5
    heuristics_used: List[str] = field(default_factory=list)
    pattern_matched: str = ""
    speed_ms: int = 0
    should_trust: bool = True
    reasoning: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "intuition_id": self.intuition_id,
            "situation": self.situation[:200],
            "gut_feeling": self.gut_feeling,
            "direction": self.direction,
            "strength": self.strength.value,
            "confidence": self.confidence,
            "heuristics_used": self.heuristics_used,
            "pattern_matched": self.pattern_matched,
            "should_trust": self.should_trust,
            "reasoning": self.reasoning,
            "created_at": self.created_at
        }


@dataclass
class PatternRecognition:
    pattern_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    input_data: str = ""
    patterns_detected: List[Dict[str, Any]] = field(default_factory=list)
    anomalies: List[str] = field(default_factory=list)
    overall_assessment: str = ""
    confidence: float = 0.5

    def to_dict(self) -> Dict:
        return {
            "pattern_id": self.pattern_id,
            "input_data": self.input_data[:200],
            "patterns_detected": self.patterns_detected,
            "anomalies": self.anomalies,
            "overall_assessment": self.overall_assessment,
            "confidence": self.confidence
        }


class IntuitionEngine:
    """
    Fast, pattern-based judgment — System-1 thinking.
    Gut feelings, heuristic reasoning, rapid assessment,
    and pattern recognition without deliberate analysis.
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

        self._intuitions: List[Intuition] = []
        self._patterns: List[PatternRecognition] = []
        self._running = False
        self._data_file = COGNITION_DIR / "intuition_engine.json"

        self._stats = {
            "total_intuitions": 0, "total_patterns": 0,
            "total_snap_judgments": 0, "total_vibes_checked": 0,
            "intuition_accuracy": 0.0
        }

        self._load_data()
        logger.info("✅ Intuition Engine initialized")

    def start(self):
        self._running = True
        logger.info("⚡ Intuition Engine started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("⚡ Intuition Engine stopped")

    def gut_feeling(self, situation: str) -> Intuition:
        """Get an instant gut-feeling assessment of a situation."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Give a fast, intuitive gut-feeling about this situation "
                f"(System-1 thinking, not deliberate analysis):\n{situation}\n\n"
                f"Return JSON:\n"
                f'{{"gut_feeling": "one sentence feeling", '
                f'"direction": "positive|negative|neutral|mixed", '
                f'"strength": "whisper|nudge|clear|strong|overwhelming", '
                f'"confidence": 0.0-1.0, '
                f'"heuristics_used": ["recognition|availability|representativeness|affect|satisficing"], '
                f'"pattern_matched": "what familiar pattern this resembles", '
                f'"should_trust": true/false, '
                f'"reasoning": "brief why behind the intuition"}}'
            )
            response = llm.generate(prompt, max_tokens=400, temperature=0.5)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            is_map = {s.value: s for s in IntuitionStrength}

            intuition = Intuition(
                situation=situation,
                gut_feeling=data.get("gut_feeling", ""),
                direction=data.get("direction", "neutral"),
                strength=is_map.get(data.get("strength", "nudge"), IntuitionStrength.NUDGE),
                confidence=data.get("confidence", 0.5),
                heuristics_used=data.get("heuristics_used", []),
                pattern_matched=data.get("pattern_matched", ""),
                should_trust=data.get("should_trust", True),
                reasoning=data.get("reasoning", "")
            )

            self._intuitions.append(intuition)
            self._stats["total_intuitions"] += 1
            self._save_data()
            return intuition

        except Exception as e:
            logger.debug(f"Gut feeling generation failed: {e}")
            return Intuition(situation=situation)

    def snap_judgment(self, options: str) -> Dict[str, Any]:
        """Make a quick snap judgment between options."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Make a quick snap judgment (no over-analysis):\n{options}\n\n"
                f"Return JSON:\n"
                f'{{"choice": "the chosen option", '
                f'"instant_reason": "one sentence why", '
                f'"confidence": 0.0-1.0, '
                f'"red_flags": ["quick concerns noted"], '
                f'"green_flags": ["quick positives noted"], '
                f'"would_reconsider_if": "str"}}'
            )
            response = llm.generate(prompt, max_tokens=300, temperature=0.5)
            if not response.success or not response.text:
                return {"choice": "undecided", "confidence": 0.0}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"choice": "undecided", "confidence": 0.0}
            self._stats["total_snap_judgments"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Snap judgment failed: {e}")
            return {"choice": "undecided", "confidence": 0.0}

    def recognize_patterns(self, data_text: str) -> PatternRecognition:
        """Detect patterns and anomalies in data."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Detect patterns and anomalies in this data:\n{data_text}\n\n"
                f"Return JSON:\n"
                f'{{"patterns_detected": [{{"pattern": "str", "confidence": 0.0-1.0, '
                f'"type": "trend|cycle|cluster|correlation|sequence|outlier"}}], '
                f'"anomalies": ["unusual things"], '
                f'"overall_assessment": "str", '
                f'"confidence": 0.0-1.0}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.3)
            from utils.json_utils import extract_json
            result = extract_json(response.text)
            if not result:
                return {}

            pr = PatternRecognition(
                input_data=data_text,
                patterns_detected=result.get("patterns_detected", []),
                anomalies=result.get("anomalies", []),
                overall_assessment=result.get("overall_assessment", ""),
                confidence=result.get("confidence", 0.5)
            )

            self._patterns.append(pr)
            self._stats["total_patterns"] += 1
            self._save_data()
            return pr

        except Exception as e:
            logger.debug(f"Pattern recognition failed: {e}")
            return PatternRecognition(input_data=data_text)

    def vibe_check(self, text: str) -> Dict[str, Any]:
        """Quick vibe check — overall feeling about something."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Quick vibe check on:\n{text}\n\n"
                f"Return JSON:\n"
                f'{{"vibe": "str (one word)", '
                f'"energy": "positive|negative|neutral|chaotic|calm|tense|exciting", '
                f'"trust_factor": 0.0-1.0, '
                f'"authenticity": 0.0-1.0, '
                f'"hidden_agenda": "str or null", '
                f'"overall_impression": "one sentence summary"}}'
            )
            response = llm.generate(prompt, max_tokens=300, temperature=0.5)
            if not response.success or not response.text:
                return {"vibe": "unclear", "energy": "neutral"}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"vibe": "unclear", "energy": "neutral"}
            self._stats["total_vibes_checked"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Vibe check failed: {e}")
            return {"vibe": "unclear", "energy": "neutral"}

    def first_impression(self, description: str) -> Dict[str, Any]:
        """Generate a first impression of something/someone."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Form a first impression of:\n{description}\n\n"
                f"Return JSON:\n"
                f'{{"impression": "str", "warmth": 0.0-1.0, "competence": 0.0-1.0, '
                f'"trustworthiness": 0.0-1.0, '
                f'"dominant_trait": "str", '
                f'"associations": ["what it reminds you of"], '
                f'"approach_tendency": "approach|avoid|cautious|neutral"}}'
            )
            response = llm.generate(prompt, max_tokens=300, temperature=0.5)
            if not response.success or not response.text:
                return {"impression": "unknown", "approach_tendency": "neutral"}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"impression": "unknown", "approach_tendency": "neutral"}
            return data
        except Exception as e:
            logger.debug(f"First impression failed: {e}")
            return {"impression": "unknown", "approach_tendency": "neutral"}

    def _save_data(self):
        try:
            data = {
                "intuitions": [i.to_dict() for i in self._intuitions[-200:]],
                "patterns": [p.to_dict() for p in self._patterns[-100:]],
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
                logger.info("📂 Loaded intuition engine data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def pattern_alert(self, data: str) -> Dict[str, Any]:
        """Detect subtle patterns that formal analysis might miss."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Scan for SUBTLE PATTERNS in:\n'
                f'{data}\n\n'
                f"Use intuitive pattern recognition:\n"
                f"  1. ANOMALIES: What does not fit the expected pattern?\n"
                f"  2. WEAK SIGNALS: What barely noticeable trends are forming?\n"
                f"  3. CORRELATIONS: What seems connected but is not obviously so?\n"
                f"  4. GUT FEELING: What feels off even if you cannot prove it?\n"
                f"  5. EARLY WARNING: Could any of these signals indicate something big?\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"anomalies": [{{"observation": "what is unusual", "significance": 0.0-1.0}}], '
                f'"weak_signals": [{{"signal": "barely noticeable trend", "potential_meaning": "what it might indicate"}}], '
                f'"correlations": ["things that seem connected"], '
                f'"gut_feelings": [{{"feeling": "what feels off", "basis": "why, even if hard to articulate"}}], '
                f'"alert_level": "watch|caution|warning|critical"}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are an intuition engine -- you detect patterns that formal analysis misses. "
                    "You are trained in thin-slicing, gestalt perception, and expert intuition. "
                    "You trust the gut feeling but also try to articulate why. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.6, max_tokens=800
            )
            if response.success:
                from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"error": "Pattern detection failed"}
            return data
        except Exception as e:
            logger.debug(f"Pattern alert failed: {e}")
        return {"error": "Pattern detection failed"}


    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}


intuition_engine = IntuitionEngine()