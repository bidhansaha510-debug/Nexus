"""
NEXUS AI — Curiosity Drive Engine
Generate questions, drive exploration, information gap detection,
intrinsic motivation for knowledge seeking.
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

logger = get_logger("curiosity_drive")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)


class CuriosityType(Enum):
    EPISTEMIC = "epistemic"         # Want to know facts
    PERCEPTUAL = "perceptual"       # Want to observe
    DIVERSIVE = "diversive"         # Novelty seeking
    SPECIFIC = "specific"           # Focused on one topic
    SOCIAL = "social"               # About people
    CREATIVE = "creative"           # Exploratory imagination


@dataclass
class CuriosityQuestion:
    question_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    question: str = ""
    curiosity_type: CuriosityType = CuriosityType.EPISTEMIC
    importance: float = 0.5
    knowledge_gap: str = ""
    potential_impact: str = ""
    exploration_path: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "question_id": self.question_id, "question": self.question,
            "curiosity_type": self.curiosity_type.value,
            "importance": self.importance,
            "knowledge_gap": self.knowledge_gap,
            "potential_impact": self.potential_impact,
            "exploration_path": self.exploration_path,
            "created_at": self.created_at
        }


class CuriosityDriveEngine:
    """
    Generate questions and drive exploration — detect knowledge gaps,
    pursue interesting threads, maintain intrinsic motivation.
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

        self._questions: List[CuriosityQuestion] = []
        self._running = False
        self._data_file = COGNITION_DIR / "curiosity_drive.json"

        self._stats = {
            "total_questions_generated": 0, "total_gaps_detected": 0,
            "total_explorations": 0, "total_deep_dives": 0
        }

        self._load_data()
        logger.info("✅ Curiosity Drive Engine initialized")

    def start(self):
        self._running = True
        logger.info("🔎 Curiosity Drive started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🔎 Curiosity Drive stopped")

    def generate_questions(self, topic: str, count: int = 5) -> List[CuriosityQuestion]:
        """Generate curious questions about a topic."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Generate {count} genuinely curious, thought-provoking questions about:\n"
                f"{topic}\n\n"
                f"Return JSON:\n"
                f'{{"questions": [{{"question": "str", '
                f'"curiosity_type": "epistemic|perceptual|diversive|specific|social|creative", '
                f'"importance": 0.0-1.0, '
                f'"knowledge_gap": "what we don\'t know", '
                f'"potential_impact": "why answering this matters", '
                f'"exploration_path": ["step 1 to find out", "step 2"]}}]}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.6)
            if not response.success or not response.text.strip():
                logger.warning(f"LLM returned empty/failed response for question generation")
                return []
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            ct_map = {c.value: c for c in CuriosityType}
            questions = []
            for q_data in data.get("questions", []):
                q = CuriosityQuestion(
                    question=q_data.get("question", ""),
                    curiosity_type=ct_map.get(q_data.get("curiosity_type", "epistemic"), CuriosityType.EPISTEMIC),
                    importance=q_data.get("importance", 0.5),
                    knowledge_gap=q_data.get("knowledge_gap", ""),
                    potential_impact=q_data.get("potential_impact", ""),
                    exploration_path=q_data.get("exploration_path", [])
                )
                questions.append(q)
                self._questions.append(q)

            self._stats["total_questions_generated"] += len(questions)
            self._save_data()
            return questions

        except Exception as e:
            logger.debug(f"Question generation failed: {e}")
            return []

    def detect_knowledge_gaps(self, text: str) -> Dict[str, Any]:
        """Detect knowledge gaps in a body of text."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Identify knowledge gaps in this text — what's missing, "
                f"assumed, or left unexplored:\n{text}\n\n"
                f"Return JSON:\n"
                f'{{"gaps": [{{"topic": "str", "gap_description": "str", '
                f'"importance": 0.0-1.0, "difficulty_to_fill": 0.0-1.0}}], '
                f'"unstated_assumptions": ["things taken for granted"], '
                f'"unexplored_connections": ["links to other topics not mentioned"], '
                f'"depth_assessment": "shallow|moderate|deep|expert", '
                f'"recommended_exploration": ["topics to investigate next"]}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            if not response.success or not response.text.strip():
                return {"gaps": [], "depth_assessment": "unknown"}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"gaps": [], "depth_assessment": "unknown"}
            self._stats["total_gaps_detected"] += len(data.get("gaps", []))
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Knowledge gap detection failed: {e}")
            return {"gaps": [], "depth_assessment": "unknown"}

    def deep_dive(self, topic: str) -> Dict[str, Any]:
        """Plan a deep-dive exploration into a topic."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Plan a deep-dive exploration into:\n{topic}\n\n"
                f"Return JSON:\n"
                f'{{"overview": "what this topic is about", '
                f'"key_questions": ["fundamental questions to answer"], '
                f'"subtopics": [{{"name": "str", "importance": 0.0-1.0, '
                f'"prerequisite_knowledge": "str"}}], '
                f'"learning_path": ["ordered steps for deep understanding"], '
                f'"related_fields": ["connected domains"], '
                f'"frontier_questions": ["cutting-edge unknowns"], '
                f'"estimated_depth_time": "how long to reach expertise"}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.5)
            if not response.success or not response.text.strip():
                return {"overview": "", "key_questions": []}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"overview": "", "key_questions": []}
            self._stats["total_deep_dives"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Deep dive planning failed: {e}")
            return {"overview": "", "key_questions": []}

    def explore_tangent(self, main_topic: str) -> Dict[str, Any]:
        """Follow an interesting tangent from the main topic."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Starting from the topic '{main_topic}', follow the most "
                f"interesting tangent — find a surprising connection:\n\n"
                f"Return JSON:\n"
                f'{{"tangent_topic": "str", '
                f'"connection_to_original": "how they connect", '
                f'"surprise_factor": 0.0-1.0, '
                f'"interesting_fact": "str", '
                f'"further_tangents": ["even deeper rabbit holes"], '
                f'"practical_relevance": "why this tangent matters"}}'
            )
            response = llm.generate(prompt, max_tokens=400, temperature=0.7)
            if not response.success or not response.text.strip():
                return {"tangent_topic": "", "connection_to_original": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"tangent_topic": "", "connection_to_original": ""}
            self._stats["total_explorations"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Tangent exploration failed: {e}")
            return {"tangent_topic": "", "connection_to_original": ""}

    def _save_data(self):
        try:
            data = {
                "questions": [q.to_dict() for q in self._questions[-300:]],
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
                logger.info("📂 Loaded curiosity drive data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def rabbit_hole(self, topic: str) -> Dict[str, Any]:
        """Go deep into a topic, following curiosity to unexpected places."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Go down a RABBIT HOLE starting from:\n'
                f'"{topic}"\n\n'
                f"Follow your curiosity through 5 surprising connections:\n"
                f"  Each step should be a genuine surprise -- something most people would not know.\n"
                f"  Connect each step to the next through a non-obvious link.\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"starting_point": "the original topic", '
                f'"rabbit_hole": [{{"step": 1, "discovery": "fascinating fact or connection", '
                f'"link_to_next": "how this connects to the next step", '
                f'"surprise_level": 0.0-1.0}}], '
                f'"deepest_insight": "the most mind-expanding discovery", '
                f'"questions_raised": ["new questions to explore"]}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a curiosity engine -- you follow threads of knowledge to unexpected "
                    "places, making surprising connections between domains. You are driven by "
                    "genuine intellectual curiosity. Respond ONLY with valid JSON."
                ),
                temperature=0.8, max_tokens=900
            )
            if response.success:
                from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"error": "Exploration failed"}
            return data
        except Exception as e:
            logger.debug(f"Rabbit hole exploration failed: {e}")
        return {"error": "Exploration failed"}


    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}


curiosity_drive = CuriosityDriveEngine()