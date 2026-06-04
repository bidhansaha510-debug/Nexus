"""
NEXUS AI — Swarm Intelligence Engine
Emergent collective intelligence: simulates swarms of specialized
micro-agents that converge on solutions through stigmergy, flocking,
and hive-mind consensus.
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

logger = get_logger("swarm_intelligence")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)


class SwarmMode(Enum):
    SOLVE = "solve"
    STIGMERGY = "stigmergy"
    FLOCKING = "flocking"
    HIVE_MIND = "hive_mind"


@dataclass
class SwarmAgent:
    agent_id: str = field(default_factory=lambda: str(uuid.uuid4())[:6])
    role: str = ""
    bias: str = ""
    solution: str = ""
    confidence: float = 0.5
    pheromone_strength: float = 0.0


@dataclass
class SwarmResult:
    result_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    problem: str = ""
    mode: SwarmMode = SwarmMode.SOLVE
    agents: List[SwarmAgent] = field(default_factory=list)
    consensus: str = ""
    dissent: str = ""
    emergent_insight: str = ""
    confidence: float = 0.5
    summary: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "result_id": self.result_id, "problem": self.problem[:200],
            "mode": self.mode.value,
            "num_agents": len(self.agents),
            "consensus": self.consensus,
            "confidence": self.confidence,
            "summary": self.summary,
            "created_at": self.created_at
        }


class SwarmIntelligenceEngine:
    """
    Emergent collective intelligence — spawns virtual agents with
    different biases, uses stigmergy and flocking to converge on
    high-quality solutions.
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

        self._results: List[SwarmResult] = []
        self._running = False
        self._data_file = COGNITION_DIR / "swarm_intelligence.json"

        self._stats = {
            "total_swarms": 0, "total_stigmergy": 0,
            "total_flocking": 0, "total_hive_minds": 0
        }

        self._load_data()
        logger.info("✅ Swarm Intelligence Engine initialized")

    def start(self):
        self._running = True
        logger.info("🐝 Swarm Intelligence started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🐝 Swarm Intelligence stopped")

    # ─── Core Methods ────────────────────────────────────────────────────────

    def swarm_solve(self, problem: str) -> SwarmResult:
        """Spawn a swarm of diverse virtual agents to solve a problem."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"SWARM INTELLIGENCE — Collective Problem Solving:\n"
                f'Problem: "{problem}"\n\n'
                f"Simulate 5 specialist agents with DIFFERENT biases/domains:\n"
                f"  • Optimist, Pessimist, Pragmatist, Contrarian, Visionary\n"
                f"Each agent independently proposes a solution.\n"
                f"Then aggregate via weighted voting to find consensus.\n\n"
                f"Return JSON:\n"
                f'{{"agents": [{{"role": "str", "bias": "str", '
                f'"solution": "their proposed solution", '
                f'"confidence": 0.0-1.0, "reasoning": "key argument"}}], '
                f'"consensus": "the weighted-majority solution", '
                f'"dissent": "strongest dissenting view and why", '
                f'"emergent_insight": "what emerged from the collective that no single agent saw", '
                f'"confidence": 0.0-1.0, '
                f'"summary": "one-line swarm verdict"}}'
            )
            response = llm.generate(prompt, max_tokens=800, temperature=0.6)
            if not response.success or not response.text:
                return SwarmResult(problem=problem)
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return SwarmResult(problem=problem)

            agents = []
            for a in data.get("agents", []):
                agents.append(SwarmAgent(
                    role=a.get("role", ""),
                    bias=a.get("bias", ""),
                    solution=a.get("solution", ""),
                    confidence=float(a.get("confidence", 0.5)),
                ))

            result = SwarmResult(
                problem=problem, mode=SwarmMode.SOLVE,
                agents=agents,
                consensus=data.get("consensus", ""),
                dissent=data.get("dissent", ""),
                emergent_insight=data.get("emergent_insight", ""),
                confidence=float(data.get("confidence", 0.5)),
                summary=data.get("summary", ""),
            )

            self._results.append(result)
            self._stats["total_swarms"] += 1
            self._save_data()
            return result

        except Exception as e:
            logger.debug(f"Swarm solve failed: {e}")
            return SwarmResult(problem=problem)

    def stigmergy(self, topic: str) -> Dict[str, Any]:
        """Build solutions through indirect coordination — like ant
        pheromone trails, each agent leaves markers for the next."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"STIGMERGY — Indirect Coordination:\n"
                f'Topic: "{topic}"\n\n'
                f"Simulate pheromone-trail problem solving:\n"
                f"  Round 1: Scout agent explores and leaves a trail\n"
                f"  Round 2: Next agent follows strongest trail, adds own markers\n"
                f"  Round 3: Third agent reinforces successful paths, abandons dead ends\n"
                f"  Convergence: Strongest trail = best solution\n\n"
                f"Return JSON:\n"
                f'{{"rounds": [{{"agent": "scout|follower|reinforcer", '
                f'"trail": "what they explored", "pheromone_left": "marker for next agent", '
                f'"path_strength": 0.0-1.0}}], '
                f'"strongest_path": "the solution path with most pheromone", '
                f'"abandoned_paths": ["dead ends discovered"], '
                f'"emergent_solution": "what the swarm converged on", '
                f'"confidence": 0.0-1.0, '
                f'"summary": "one-line result"}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.5)
            if not response.success or not response.text:
                return {"emergent_solution": "", "rounds": []}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"emergent_solution": "", "rounds": []}

            self._stats["total_stigmergy"] += 1
            self._save_data()
            return data

        except Exception as e:
            logger.debug(f"Stigmergy failed: {e}")
            return {"emergent_solution": "", "rounds": []}

    def flocking(self, ideas: str) -> Dict[str, Any]:
        """Align scattered ideas into coherent direction using
        Boids-like rules: separation, alignment, cohesion."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"FLOCKING — Align Scattered Ideas:\n"
                f'Ideas: "{ideas}"\n\n'
                f"Apply Boids rules to these scattered ideas:\n"
                f"  1. SEPARATION: Identify where ideas conflict/overlap (push apart duplicates)\n"
                f"  2. ALIGNMENT: Find common direction (shared theme or goal)\n"
                f"  3. COHESION: Pull ideas toward center of mass (unifying principle)\n\n"
                f"Return JSON:\n"
                f'{{"raw_ideas": ["parsed individual ideas"], '
                f'"separation": [{{"idea_a": "str", "idea_b": "str", "conflict": "str"}}], '
                f'"alignment": "the shared direction all ideas point toward", '
                f'"cohesion": "the unifying principle that binds them", '
                f'"flocked_direction": "the coherent direction after flocking", '
                f'"formation": "how the ideas organize into a structured flock", '
                f'"confidence": 0.0-1.0, '
                f'"summary": "one-line flock heading"}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.5)
            if not response.success or not response.text:
                return {"flocked_direction": "", "alignment": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"flocked_direction": "", "alignment": ""}

            self._stats["total_flocking"] += 1
            self._save_data()
            return data

        except Exception as e:
            logger.debug(f"Flocking failed: {e}")
            return {"flocked_direction": "", "alignment": ""}

    def hive_mind(self, question: str) -> Dict[str, Any]:
        """Simulate a diverse committee that deliberates and reaches consensus."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"HIVE MIND — Committee Deliberation:\n"
                f'Question: "{question}"\n\n'
                f"Simulate a committee of 5 diverse experts:\n"
                f"  • Scientist, Philosopher, Engineer, Artist, Strategist\n"
                f"Each gives their perspective. Then they deliberate.\n"
                f"Final vote produces a consensus or qualified majority.\n\n"
                f"Return JSON:\n"
                f'{{"perspectives": [{{"expert": "str", "view": "their perspective", '
                f'"vote": "for|against|abstain", "key_insight": "str"}}], '
                f'"deliberation": "how the discussion evolved", '
                f'"consensus": "the final collective answer", '
                f'"vote_count": {{"for": 0, "against": 0, "abstain": 0}}, '
                f'"minority_report": "the dissenting view worth preserving", '
                f'"collective_wisdom": "insight that only emerged from the group", '
                f'"confidence": 0.0-1.0, '
                f'"summary": "one-line hive mind verdict"}}'
            )
            response = llm.generate(prompt, max_tokens=800, temperature=0.5)
            if not response.success or not response.text:
                return {"consensus": "", "perspectives": []}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"consensus": "", "perspectives": []}

            self._stats["total_hive_minds"] += 1
            self._save_data()
            return data

        except Exception as e:
            logger.debug(f"Hive mind failed: {e}")
            return {"consensus": "", "perspectives": []}

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
                logger.info("📂 Loaded swarm intelligence data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}


swarm_intelligence = SwarmIntelligenceEngine()
