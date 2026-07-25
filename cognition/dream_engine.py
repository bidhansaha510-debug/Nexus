"""
NEXUS AI — Dream Engine
Free association, subconscious-style ideation, surreal blending,
dream-logic reasoning, creative incubation.
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

logger = get_logger("dream_engine")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)

class DreamType(Enum):
    FREE_ASSOCIATION = "free_association"
    LUCID = "lucid"
    NIGHTMARISH = "nightmarish"
    PROPHETIC = "prophetic"
    SURREAL = "surreal"
    PROBLEM_SOLVING = "problem_solving"
    MEMORY_REPLAY = "memory_replay"

@dataclass
class Dream:
    dream_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    seed: str = ""
    dream_type: DreamType = DreamType.FREE_ASSOCIATION
    narrative: str = ""
    symbols: List[Dict[str, str]] = field(default_factory=list)
    emotions_evoked: List[str] = field(default_factory=list)
    hidden_meaning: str = ""
    surrealism_level: float = 0.5
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "dream_id": self.dream_id, "seed": self.seed[:200],
            "dream_type": self.dream_type.value,
            "narrative": self.narrative,
            "symbols": self.symbols,
            "emotions_evoked": self.emotions_evoked,
            "hidden_meaning": self.hidden_meaning,
            "surrealism_level": self.surrealism_level,
            "created_at": self.created_at
        }

class DreamEngine:
    """
    Subconscious-style ideation — free association, surreal
    blending, dream-logic reasoning, creative incubation.
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

        self._dreams: List[Dream] = []
        self._running = False
        self._data_file = COGNITION_DIR / "dream_engine.json"

        self._stats = {
            "total_dreams": 0, "total_associations": 0,
            "total_incubations": 0, "total_interpretations": 0
        }

        self._load_data()
        logger.info("✅ Dream Engine initialized")

    def start(self):
        self._running = True
        logger.info("💭 Dream Engine started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("💭 Dream Engine stopped")

    def dream(self, seed: str) -> Dream:
        """Generate a surreal dream-like sequence from a seed concept."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Generate a surreal, dream-like narrative starting from:\n{seed}\n\n"
                f"Use dream logic: unexpected transitions, symbolic imagery, "
                f"emotional undertones. Let the subconscious roam free.\n\n"
                f"Return JSON:\n"
                f'{{"dream_type": "free_association|lucid|surreal|problem_solving|memory_replay", '
                f'"narrative": "the dream narrative (3-5 sentences)", '
                f'"symbols": [{{"symbol": "str", "meaning": "str"}}], '
                f'"emotions_evoked": ["str"], '
                f'"hidden_meaning": "what the dream might be about deep down", '
                f'"surrealism_level": 0.0-1.0, '
                f'"recurring_motif": "a pattern that keeps appearing"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.8)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            dt_map = {d.value: d for d in DreamType}

            dream = Dream(
                seed=seed,
                dream_type=dt_map.get(data.get("dream_type", "free_association"), DreamType.FREE_ASSOCIATION),
                narrative=data.get("narrative", ""),
                symbols=data.get("symbols", []),
                emotions_evoked=data.get("emotions_evoked", []),
                hidden_meaning=data.get("hidden_meaning", ""),
                surrealism_level=data.get("surrealism_level", 0.5)
            )

            self._dreams.append(dream)
            self._stats["total_dreams"] += 1
            self._save_data()
            return dream

        except Exception as e:
            logger.debug(f"Dream generation failed: {e}")
            return Dream(seed=seed)

    def run_sleep_consolidation(self) -> Dict[str, Any]:
        """Trigger background sleep consolidation & memory pruning via Temporal GraphRAG."""
        try:
            from memory.temporal_graphrag import get_temporal_graphrag
            graphrag = get_temporal_graphrag()
            return graphrag.run_sleep_consolidation()
        except Exception as e:
            logger.warning(f"Sleep consolidation in DreamEngine exception: {e}")
            return {"status": "failed", "error": str(e)}

    def free_associate(self, start_word: str, depth: int = 10) -> Dict[str, Any]:
        """Free-associate from a starting concept."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Free-associate from the word '{start_word}'. "
                f"Let each thought lead naturally to the next, "
                f"following subconscious connections ({depth} steps).\n\n"
                f"Return JSON:\n"
                f'{{"chain": [{{"word": "str", "connection": "why this follows"}}], '
                f'"emotional_drift": "how the emotional tone shifted", '
                f'"themes_emerged": ["themes that appeared"], '
                f'"surprise_connection": "the most unexpected link in the chain", '
                f'"insight": "what this chain reveals about the starting concept"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.8)
            if not response.success or not response.text:
                return {"chain": [], "insight": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"chain": [], "insight": ""}
            self._stats["total_associations"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Free association failed: {e}")
            return {"chain": [], "insight": ""}

    def incubate(self, problem: str) -> Dict[str, Any]:
        """Incubate a problem using dream-like subconscious processing."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Use creative incubation (subconscious problem-solving) for:\n{problem}\n\n"
                f"Instead of logical analysis, let the mind wander freely "
                f"around the problem and see what solutions emerge.\n\n"
                f"Return JSON:\n"
                f'{{"incubated_insights": ["surprising solutions that emerged"], '
                f'"metaphorical_solution": "the problem seen as a metaphor", '
                f'"unexpected_connection": "a connection from a totally unrelated domain", '
                f'"eureka_moment": "the aha! insight", '
                f'"emotional_resolution": "how it feels when solved this way", '
                f'"dream_logic_steps": ["the non-linear path to the solution"]}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.7)
            if not response.success or not response.text:
                return {"incubated_insights": [], "eureka_moment": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"incubated_insights": [], "eureka_moment": ""}
            self._stats["total_incubations"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Incubation failed: {e}")
            return {"incubated_insights": [], "eureka_moment": ""}

    def interpret_dream(self, dream_narrative: str) -> Dict[str, Any]:
        """Interpret the meaning of a dream narrative."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Interpret this dream:\n{dream_narrative}\n\n"
                f"Return JSON:\n"
                f'{{"primary_theme": "str", '
                f'"symbol_analysis": [{{"symbol": "str", "interpretation": "str"}}], '
                f'"emotional_undercurrent": "str", '
                f'"unresolved_conflict": "what inner conflict this represents", '
                f'"wish_fulfillment": "what desire is being expressed", '
                f'"shadow_content": "what the dreamer might be avoiding", '
                f'"actionable_insight": "what to do with this information"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.5)
            if not response.success or not response.text:
                return {"primary_theme": "", "symbol_analysis": []}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"primary_theme": "", "symbol_analysis": []}
            self._stats["total_interpretations"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Dream interpretation failed: {e}")
            return {"primary_theme": "", "symbol_analysis": []}

    def _save_data(self):
        try:
            data = {
                "dreams": [d.to_dict() for d in self._dreams[-200:]],
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
                logger.info("📂 Loaded dream engine data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def lucid_dream(self, seed: str) -> Dict[str, Any]:
        """Generate a vivid, surreal dream-like narrative from a seed concept."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Generate a LUCID DREAM sequence from this seed:\n'
                f'"{seed}"\n\n'
                f"Create a surreal, vivid narrative that:\n"
                f"  1. Begins with a familiar setting that subtly shifts\n"
                f"  2. Introduces dream logic (impossible physics, time shifts)\n"
                f"  3. Contains symbolic imagery with psychological meaning\n"
                f"  4. Builds to a moment of lucidity (awareness of dreaming)\n"
                f"  5. Resolves with an insight or transformation\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"dream_narrative": "the full dream sequence", '
                f'"symbols": [{{"symbol": "what appears", "meaning": "psychological interpretation"}}], '
                f'"emotional_arc": ["curiosity", "wonder", "realization"], '
                f'"insight": "what the dream reveals", '
                f'"lucidity_moment": "when awareness of dreaming occurs"}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a dream engine -- inspired by Jungian psychology, surrealist art, "
                    "and the neuroscience of dreaming. You create vivid, symbolically rich dream "
                    "narratives that feel genuinely dreamlike. Respond ONLY with valid JSON."
                ),
                temperature=0.9, max_tokens=1000
            )
            if response.success:
                from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"error": "Dream generation failed"}
            return data
        except Exception as e:
            logger.debug(f"Lucid dream generation failed: {e}")
        return {"error": "Dream generation failed"}

    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}

dream_engine = DreamEngine()