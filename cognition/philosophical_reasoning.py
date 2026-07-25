"""
NEXUS AI — Philosophical Reasoning Engine
Epistemology, ontology, ethics, logic,
thought experiments, existential analysis.
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

logger = get_logger("philosophical_reasoning")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)

class PhilosophyBranch(Enum):
    EPISTEMOLOGY = "epistemology"
    ONTOLOGY = "ontology"
    ETHICS = "ethics"
    LOGIC = "logic"
    AESTHETICS = "aesthetics"
    POLITICAL = "political"
    EXISTENTIAL = "existential"
    METAPHYSICS = "metaphysics"

@dataclass
class PhilosophicalAnalysis:
    analysis_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    question: str = ""
    branch: PhilosophyBranch = PhilosophyBranch.EPISTEMOLOGY
    thesis: str = ""
    antithesis: str = ""
    synthesis: str = ""
    key_thinkers: List[str] = field(default_factory=list)
    depth: float = 0.5
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "analysis_id": self.analysis_id, "question": self.question[:200],
            "branch": self.branch.value,
            "thesis": self.thesis, "antithesis": self.antithesis,
            "synthesis": self.synthesis,
            "key_thinkers": self.key_thinkers,
            "depth": self.depth,
            "created_at": self.created_at
        }

class PhilosophicalReasoningEngine:
    """
    Deep philosophical analysis — epistemology, ontology, ethics,
    thought experiments, dialectical reasoning.
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

        self._analyses: List[PhilosophicalAnalysis] = []
        self._running = False
        self._data_file = COGNITION_DIR / "philosophical_reasoning.json"

        self._stats = {
            "total_analyses": 0, "total_thought_experiments": 0,
            "total_dialectics": 0, "total_existential": 0
        }

        self._load_data()
        logger.info("✅ Philosophical Reasoning Engine initialized")

    @staticmethod
    def _safe_parse_json(text: str) -> Dict[str, Any]:
        """Parse JSON from LLM response, handling empty/malformed output."""
        if not text or not text.strip():
            return {}
        cleaned = text.strip()
        # Strip markdown fences
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        # Try to find JSON object
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(cleaned[start:end + 1])
        return json.loads(cleaned)

    def start(self):
        self._running = True
        logger.info("🏛️ Philosophical Reasoning started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🏛️ Philosophical Reasoning stopped")

    def philosophize(self, question: str) -> PhilosophicalAnalysis:
        """Deeply analyze a philosophical question."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Provide deep philosophical analysis of:\n{question}\n\n"
                f"Return JSON:\n"
                f'{{"branch": "epistemology|ontology|ethics|logic|aesthetics|political|existential|metaphysics", '
                f'"thesis": "the primary philosophical position", '
                f'"antithesis": "the strongest opposing view", '
                f'"synthesis": "a reconciliation or deeper truth", '
                f'"key_thinkers": ["philosophers who addressed this"], '
                f'"depth": 0.0-1.0, '
                f'"paradoxes": ["inherent paradoxes in this question"], '
                f'"practical_implications": "what this means for everyday life", '
                f'"unanswerable_aspect": "what part of this may never be resolved"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.5)
            if not response.success or not response.text:
                return PhilosophicalAnalysis(question=question)
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                data = self._safe_parse_json(response.text)
            if not data:
                return PhilosophicalAnalysis(question=question)

            pb_map = {p.value: p for p in PhilosophyBranch}

            analysis = PhilosophicalAnalysis(
                question=question,
                branch=pb_map.get(data.get("branch", "epistemology"), PhilosophyBranch.EPISTEMOLOGY),
                thesis=data.get("thesis", ""),
                antithesis=data.get("antithesis", ""),
                synthesis=data.get("synthesis", ""),
                key_thinkers=data.get("key_thinkers", []),
                depth=data.get("depth", 0.5)
            )

            self._analyses.append(analysis)
            self._stats["total_analyses"] += 1
            self._save_data()
            return analysis

        except Exception as e:
            logger.debug(f"Philosophical analysis fallback: {e}")
            return PhilosophicalAnalysis(question=question)

    def thought_experiment(self, scenario: str) -> Dict[str, Any]:
        """Run a thought experiment."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Run a thought experiment based on:\n{scenario}\n\n"
                f"Return JSON:\n"
                f'{{"setup": "the thought experiment setup", '
                f'"key_question": "the central question it raises", '
                f'"intuitive_response": "what most people would say", '
                f'"philosophical_challenge": "why the intuitive response is problematic", '
                f'"competing_answers": [{{"position": "str", "argument": "str"}}], '
                f'"implications": ["what accepting each answer means"], '
                f'"related_experiments": ["classic thought experiments this connects to"], '
                f'"insight": "the deeper lesson this reveals"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.5)
            if not response.success or not response.text:
                return {"setup": "", "key_question": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                data = self._safe_parse_json(response.text)
            if not data:
                return {"setup": "", "key_question": ""}
            self._stats["total_thought_experiments"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.warning(f"Thought experiment failed: {e}")
            return {"setup": "", "key_question": ""}

    def dialectic(self, thesis: str) -> Dict[str, Any]:
        """Perform dialectical reasoning on a thesis."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Perform Hegelian dialectical analysis:\nThesis: {thesis}\n\n"
                f"Return JSON:\n"
                f'{{"thesis": "the original position, refined", '
                f'"antithesis": "the negation/opposition", '
                f'"synthesis": "the higher truth combining both", '
                f'"thesis_strengths": ["str"], '
                f'"thesis_weaknesses": ["str"], '
                f'"antithesis_strengths": ["str"], '
                f'"antithesis_weaknesses": ["str"], '
                f'"historical_context": "when this dialectic has played out in history", '
                f'"ongoing_tension": "whether the synthesis holds or creates new dialectics"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            if not response.success or not response.text:
                return {"thesis": thesis, "antithesis": "", "synthesis": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                data = self._safe_parse_json(response.text)
            if not data:
                return {"thesis": thesis, "antithesis": "", "synthesis": ""}
            self._stats["total_dialectics"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.warning(f"Dialectic failed: {e}")
            return {"thesis": thesis, "antithesis": "", "synthesis": ""}

    def existential_analysis(self, concern: str) -> Dict[str, Any]:
        """Analyze an existential concern."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Provide existential philosophical analysis of:\n{concern}\n\n"
                f"Return JSON:\n"
                f'{{"existential_theme": "freedom|meaning|death|isolation|authenticity|absurdity", '
                f'"philosophical_perspective": "str", '
                f'"key_existentialists": ["relevant philosophers and their views"], '
                f'"meaning_construction": "how to find meaning in this", '
                f'"authentic_response": "what an authentic response looks like", '
                f'"courage_required": "what must be faced honestly", '
                f'"liberation": "how confronting this can be freeing"}}'
            )
            response = llm.generate(prompt, max_tokens=400, temperature=0.5)
            if not response.success or not response.text:
                return {"existential_theme": "", "meaning_construction": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                data = self._safe_parse_json(response.text)
            if not data:
                return {"existential_theme": "", "meaning_construction": ""}
            self._stats["total_existential"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.warning(f"Existential analysis failed: {e}")
            return {"existential_theme": "", "meaning_construction": ""}

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
                logger.info("📂 Loaded philosophical reasoning data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}

philosophical_reasoning = PhilosophicalReasoningEngine()
