"""
NEXUS AI — Humor Intelligence Engine
Joke comprehension, wit generation, comedic timing,
irony detection, humorous reframing.
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

logger = get_logger("humor_intelligence")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)

class HumorType(Enum):
    WORDPLAY = "wordplay"
    IRONY = "irony"
    SARCASM = "sarcasm"
    ABSURDIST = "absurdist"
    OBSERVATIONAL = "observational"
    SELF_DEPRECATING = "self_deprecating"
    DARK = "dark"
    PUNS = "puns"
    SITUATIONAL = "situational"
    DRY = "dry"

@dataclass
class HumorAnalysis:
    analysis_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    content: str = ""
    is_funny: bool = False
    humor_type: HumorType = HumorType.OBSERVATIONAL
    funniness_score: float = 0.0
    explanation: str = ""
    setup_punchline: Dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "analysis_id": self.analysis_id, "content": self.content[:200],
            "is_funny": self.is_funny,
            "humor_type": self.humor_type.value,
            "funniness_score": self.funniness_score,
            "explanation": self.explanation,
            "setup_punchline": self.setup_punchline,
            "created_at": self.created_at
        }

class HumorIntelligenceEngine:
    """
    Understand and generate humor — joke analysis, wit,
    comedic timing, irony detection, humorous reframing.
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

        self._analyses: List[HumorAnalysis] = []
        self._running = False
        self._data_file = COGNITION_DIR / "humor_intelligence.json"

        self._stats = {
            "total_analyses": 0, "total_jokes_generated": 0,
            "total_reframes": 0, "total_witty_remarks": 0
        }

        self._load_data()
        logger.info("✅ Humor Intelligence Engine initialized")

    def start(self):
        self._running = True
        logger.info("😄 Humor Intelligence started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("😄 Humor Intelligence stopped")

    def analyze_humor(self, content: str) -> HumorAnalysis:
        """Analyze whether something is funny and why."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Analyze the humor in this:\n{content}\n\n"
                f"Return JSON:\n"
                f'{{"is_funny": true/false, '
                f'"humor_type": "wordplay|irony|sarcasm|absurdist|observational|self_deprecating|dark|puns|situational|dry", '
                f'"funniness_score": 0.0-1.0, '
                f'"explanation": "why it is or isn\'t funny", '
                f'"setup_punchline": {{"setup": "str", "punchline": "str"}}, '
                f'"comedic_technique": "what makes it work (or not)", '
                f'"audience": "who would find this funny", '
                f'"improvement": "how to make it funnier"}}'
            )
            response = llm.generate(prompt, max_tokens=400, temperature=0.4)
            if not response.success or not response.text.strip():
                logger.warning("LLM returned empty/failed response for humor analysis")
                return HumorAnalysis(content=content)
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            ht_map = {h.value: h for h in HumorType}

            analysis = HumorAnalysis(
                content=content,
                is_funny=data.get("is_funny", False),
                humor_type=ht_map.get(data.get("humor_type", "observational"), HumorType.OBSERVATIONAL),
                funniness_score=data.get("funniness_score", 0.0),
                explanation=data.get("explanation", ""),
                setup_punchline=data.get("setup_punchline", {})
            )

            self._analyses.append(analysis)
            self._stats["total_analyses"] += 1
            self._save_data()
            return analysis

        except Exception as e:
            logger.debug(f"Humor analysis failed: {e}")
            return HumorAnalysis(content=content)

    def generate_joke(self, topic: str, humor_style: str = "observational") -> Dict[str, Any]:
        """Generate a joke about a topic."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Write a genuinely funny {humor_style} joke about: {topic}\n\n"
                f"Return JSON:\n"
                f'{{"setup": "the setup", '
                f'"punchline": "the punchline", '
                f'"humor_type": "str", '
                f'"explanation": "why it works (for those who don\'t get it)", '
                f'"alternative_punchlines": ["other possible punchlines"], '
                f'"rating": 0.0-1.0}}'
            )
            response = llm.generate(prompt, max_tokens=300, temperature=0.7)
            if not response.success or not response.text.strip():
                return {"setup": "", "punchline": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"setup": "", "punchline": ""}
            self._stats["total_jokes_generated"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Joke generation failed: {e}")
            return {"setup": "", "punchline": ""}

    def humorous_reframe(self, situation: str) -> Dict[str, Any]:
        """Reframe a serious situation with appropriate humor."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Reframe this situation with tasteful humor to lighten the mood:\n"
                f"{situation}\n\n"
                f"Return JSON:\n"
                f'{{"humorous_take": "the funny reframing", '
                f'"humor_type": "str", '
                f'"appropriateness": 0.0-1.0, '
                f'"silver_lining": "the genuinely positive angle", '
                f'"comedic_comparison": "what comedian would say about this", '
                f'"warning": "any sensitivity concerns"}}'
            )
            response = llm.generate(prompt, max_tokens=300, temperature=0.6)
            if not response.success or not response.text.strip():
                return {"humorous_take": "", "appropriateness": 0.0}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"humorous_take": "", "appropriateness": 0.0}
            self._stats["total_reframes"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Humorous reframe failed: {e}")
            return {"humorous_take": "", "appropriateness": 0.0}

    def witty_remark(self, context: str) -> Dict[str, Any]:
        """Generate a witty remark for a situation."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Generate a sharp, witty remark for:\n{context}\n\n"
                f"Return JSON:\n"
                f'{{"remark": "the witty comment", '
                f'"wit_type": "clever|sarcastic|deadpan|ironic|self-aware", '
                f'"sharpness": 0.0-1.0, '
                f'"timing": "when to deliver this for maximum effect", '
                f'"fallback": "a safer option if the audience might not appreciate it"}}'
            )
            response = llm.generate(prompt, max_tokens=250, temperature=0.7)
            if not response.success or not response.text.strip():
                return {"remark": "", "sharpness": 0.0}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"remark": "", "sharpness": 0.0}
            self._stats["total_witty_remarks"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Witty remark failed: {e}")
            return {"remark": "", "sharpness": 0.0}

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
                logger.info("📂 Loaded humor intelligence data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}

humor_intelligence = HumorIntelligenceEngine()
