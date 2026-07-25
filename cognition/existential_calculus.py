"""
NEXUS AI — Existential Calculus Engine
Paradox resolution: tackles self-referential, paradoxical, and
undecidable problems using paraconsistent logic, Gödelian analysis,
strange loop detection, and koan-style lateral dissolution.
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

logger = get_logger("existential_calculus")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)

class ParadoxMode(Enum):
    RESOLVE = "resolve"
    GODEL = "godel"
    STRANGE_LOOP = "strange_loop"
    KOAN = "koan"

@dataclass
class ParadoxResult:
    result_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    input_text: str = ""
    mode: ParadoxMode = ParadoxMode.RESOLVE
    resolution: str = ""
    truth_value: str = ""      # "true|false|both|neither|undecidable"
    confidence: float = 0.5
    summary: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "result_id": self.result_id,
            "input": self.input_text[:200],
            "mode": self.mode.value,
            "resolution": self.resolution[:300],
            "truth_value": self.truth_value,
            "confidence": self.confidence,
            "summary": self.summary,
            "created_at": self.created_at
        }

class ExistentialCalculusEngine:
    """
    Paradox resolution engine — paraconsistent logic, Gödelian
    incompleteness detection, strange loop analysis, and
    koan-style lateral dissolution for undecidable problems.
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

        self._results: List[ParadoxResult] = []
        self._running = False
        self._data_file = COGNITION_DIR / "existential_calculus.json"

        self._stats = {
            "total_paradoxes": 0, "total_godel_checks": 0,
            "total_strange_loops": 0, "total_koans": 0
        }

        self._load_data()
        logger.info("✅ Existential Calculus Engine initialized")

    def start(self):
        self._running = True
        logger.info("∞ Existential Calculus started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("∞ Existential Calculus stopped")

    # ─── Core Methods ────────────────────────────────────────────────────────

    def resolve_paradox(self, paradox: str) -> ParadoxResult:
        """Resolve a paradox using paraconsistent / multi-valued logic."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"PARADOX RESOLUTION — Paraconsistent Logic:\n"
                f'Paradox: "{paradox}"\n\n'
                f"Resolve this paradox using advanced logic:\n"
                f"  1. Classical analysis: Why does it seem contradictory?\n"
                f"  2. Paraconsistent approach: Can both sides be true without explosion?\n"
                f"  3. Multi-valued truth: Is the answer true/false/both/neither/undecidable?\n"
                f"  4. Meta-level resolution: Dissolve the paradox by changing the frame\n\n"
                f"Return JSON:\n"
                f'{{"paradox_type": "self-referential|temporal|semantic|logical|existential", '
                f'"classical_problem": "why classical logic fails here", '
                f'"paraconsistent_resolution": "how both sides coexist without contradiction explosion", '
                f'"truth_value": "true|false|both|neither|undecidable", '
                f'"frame_shift": "the perspective change that dissolves the paradox", '
                f'"resolution": "the final resolution in plain language", '
                f'"remaining_mystery": "what remains genuinely unresolvable", '
                f'"confidence": 0.0-1.0, '
                f'"summary": "one-line resolution"}}'
            )
            response = llm.generate(prompt, max_tokens=700, temperature=0.5)
            if not response.success or not response.text:
                return ParadoxResult(input_text=paradox)
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return ParadoxResult(input_text=paradox)

            result = ParadoxResult(
                input_text=paradox, mode=ParadoxMode.RESOLVE,
                resolution=data.get("resolution", ""),
                truth_value=data.get("truth_value", "undecidable"),
                confidence=float(data.get("confidence", 0.5)),
                summary=data.get("summary", ""),
            )

            self._results.append(result)
            self._stats["total_paradoxes"] += 1
            self._save_data()
            return result

        except Exception as e:
            logger.debug(f"Paradox resolution failed: {e}")
            return ParadoxResult(input_text=paradox)

    def godel_check(self, system: str) -> Dict[str, Any]:
        """Identify inherent incompleteness and undecidability."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"GÖDEL INCOMPLETENESS CHECK:\n"
                f'System/Argument: "{system}"\n\n'
                f"Apply Gödelian analysis:\n"
                f"  1. Is this system trying to be both consistent AND complete?\n"
                f"  2. Identify self-referential elements (the system describing itself)\n"
                f"  3. Find statements that are TRUE but UNPROVABLE within the system\n"
                f"  4. Identify the expressiveness vs. decidability tradeoff\n\n"
                f"Return JSON:\n"
                f'{{"is_self_referential": true, '
                f'"self_referential_elements": ["where it refers to itself"], '
                f'"consistency": "consistent|inconsistent|unknown", '
                f'"completeness": "complete|incomplete|undecidable", '
                f'"godel_sentences": ["true-but-unprovable statements within this system"], '
                f'"escape_hatch": "how to transcend the limitation (meta-system)", '
                f'"expressiveness_cost": "what expressiveness is lost by making it decidable", '
                f'"confidence": 0.0-1.0, '
                f'"summary": "one-line incompleteness verdict"}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.4)
            if not response.success or not response.text:
                return {"consistency": "unknown", "completeness": "unknown"}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"consistency": "unknown", "completeness": "unknown"}

            self._stats["total_godel_checks"] += 1
            self._save_data()
            return data

        except Exception as e:
            logger.debug(f"Gödel check failed: {e}")
            return {"consistency": "unknown", "completeness": "unknown"}

    def strange_loop(self, concept: str) -> Dict[str, Any]:
        """Analyze self-referential structures (Hofstadter-style)."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"STRANGE LOOP ANALYSIS (Hofstadter):\n"
                f'Concept: "{concept}"\n\n'
                f"Find the strange loop — the tangled hierarchy where:\n"
                f"  • Moving upward through levels of abstraction\n"
                f"  • You unexpectedly arrive back at the starting level\n"
                f"  • The system becomes self-aware through self-reference\n\n"
                f"Return JSON:\n"
                f'{{"levels": [{{"level_name": "str", "description": "what exists at this level"}}], '
                f'"loop_point": "where the highest level connects back to the lowest", '
                f'"tangled_hierarchy": "how the levels interleave and refer to each other", '
                f'"emergent_self": "what kind of self-awareness emerges from the loop", '
                f'"analogous_loops": ["similar strange loops in other domains"], '
                f'"breaking_the_loop": "what happens if you cut the self-reference", '
                f'"confidence": 0.0-1.0, '
                f'"summary": "one-line strange loop insight"}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.6)
            if not response.success or not response.text:
                return {"loop_point": "", "levels": []}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"loop_point": "", "levels": []}

            self._stats["total_strange_loops"] += 1
            self._save_data()
            return data

        except Exception as e:
            logger.debug(f"Strange loop analysis failed: {e}")
            return {"loop_point": "", "levels": []}

    def koan_solve(self, question: str) -> Dict[str, Any]:
        """Approach via Zen koan-style lateral dissolution."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"KOAN — Lateral Dissolution:\n"
                f'Question: "{question}"\n\n'
                f"This question cannot be answered conventionally.\n"
                f"Approach it as a Zen koan — dissolve it laterally:\n"
                f"  1. Show why the question is itself the trap\n"
                f"  2. Reveal the hidden assumption that makes it unanswerable\n"
                f"  3. Dissolve the question rather than answering it\n"
                f"  4. Point at the truth from an unexpected angle\n\n"
                f"Return JSON:\n"
                f'{{"the_trap": "why the question as asked is a trap", '
                f'"hidden_assumption": "the assumption that must be dropped", '
                f'"dissolution": "how the question dissolves when the assumption is dropped", '
                f'"pointing": "the truth, approached from an unexpected direction", '
                f'"mu": "what the answer looks like when you refuse the question itself", '
                f'"practical_insight": "the actionable wisdom extracted", '
                f'"confidence": 0.0-1.0, '
                f'"summary": "one-line koan resolution"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.7)
            if not response.success or not response.text:
                return {"dissolution": "", "pointing": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"dissolution": "", "pointing": ""}

            self._stats["total_koans"] += 1
            self._save_data()
            return data

        except Exception as e:
            logger.debug(f"Koan solving failed: {e}")
            return {"dissolution": "", "pointing": ""}

    # ─── Persistence ─────────────────────────────────────────────────────────

    def _save_data(self):
        try:
            data = {
                "results": [r.to_dict() for r in self._results[-200:]],
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
                logger.info("📂 Loaded existential calculus data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}

existential_calculus = ExistentialCalculusEngine()
