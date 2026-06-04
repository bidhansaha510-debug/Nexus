"""
NEXUS AI — Quantum Cognition Engine
Quantum-inspired superposition reasoning: holds multiple contradictory
hypotheses simultaneously, finds entangled correlations, collapses
ambiguity, and tunnels through conventional reasoning barriers.
"""

import threading
import json
import uuid
import random
import math
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("quantum_cognition")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)


class QuantumState(Enum):
    SUPERPOSITION = "superposition"
    ENTANGLED = "entangled"
    COLLAPSED = "collapsed"
    TUNNELED = "tunneled"


@dataclass
class QuantumHypothesis:
    hypothesis_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    statement: str = ""
    amplitude: float = 0.5          # probability amplitude (|ψ|²)
    phase: float = 0.0              # interference phase
    entangled_with: List[str] = field(default_factory=list)
    coherence: float = 1.0          # decoherence over time
    observation_count: int = 0

    def probability(self) -> float:
        return self.amplitude ** 2 * self.coherence


@dataclass
class QuantumResult:
    result_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    query: str = ""
    state: QuantumState = QuantumState.SUPERPOSITION
    hypotheses: List[QuantumHypothesis] = field(default_factory=list)
    collapsed_answer: str = ""
    interference_pattern: str = ""
    confidence: float = 0.5
    summary: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "result_id": self.result_id, "query": self.query[:200],
            "state": self.state.value,
            "hypotheses": [{"statement": h.statement, "probability": h.probability()}
                           for h in self.hypotheses],
            "collapsed_answer": self.collapsed_answer,
            "confidence": self.confidence,
            "summary": self.summary,
            "created_at": self.created_at
        }


class QuantumCognitionEngine:
    """
    Quantum-inspired reasoning — superposition of hypotheses,
    entanglement between concepts, wave-function collapse for decisions,
    and quantum tunneling for breakthrough insights.
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

        self._results: List[QuantumResult] = []
        self._running = False
        self._data_file = COGNITION_DIR / "quantum_cognition.json"

        self._stats = {
            "total_superpositions": 0, "total_entanglements": 0,
            "total_collapses": 0, "total_tunnels": 0
        }

        self._load_data()
        logger.info("✅ Quantum Cognition Engine initialized")

    def start(self):
        self._running = True
        logger.info("⚛️ Quantum Cognition started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("⚛️ Quantum Cognition stopped")

    # ─── Core Methods ────────────────────────────────────────────────────────

    def superpose(self, query: str) -> QuantumResult:
        """Hold multiple contradictory hypotheses in superposition, then
        interference-weight them to find the best answer."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"QUANTUM SUPERPOSITION ANALYSIS:\n"
                f"Hold ALL possible interpretations simultaneously for:\n"
                f'"{query}"\n\n'
                f"Generate 4-6 competing hypotheses that may CONTRADICT each other.\n"
                f"For each, estimate its probability amplitude (0.0-1.0).\n"
                f"Then identify constructive/destructive interference between them.\n\n"
                f"Return JSON:\n"
                f'{{"hypotheses": [{{"statement": "str", "amplitude": 0.0-1.0, '
                f'"supporting_evidence": "str", "contradicts": ["indices of contradicting hypotheses"]}}], '
                f'"interference_pattern": "how hypotheses reinforce or cancel each other", '
                f'"collapsed_answer": "the answer that survives interference", '
                f'"confidence": 0.0-1.0, '
                f'"quantum_advantage": "what this approach revealed that linear thinking would miss", '
                f'"summary": "one-line synthesis"}}'
            )
            response = llm.generate(prompt, max_tokens=700, temperature=0.6)
            if not response.success or not response.text:
                return QuantumResult(query=query)
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return QuantumResult(query=query)

            hypotheses = []
            for h in data.get("hypotheses", []):
                hypotheses.append(QuantumHypothesis(
                    statement=h.get("statement", ""),
                    amplitude=float(h.get("amplitude", 0.5)),
                ))

            result = QuantumResult(
                query=query,
                state=QuantumState.SUPERPOSITION,
                hypotheses=hypotheses,
                collapsed_answer=data.get("collapsed_answer", ""),
                interference_pattern=data.get("interference_pattern", ""),
                confidence=float(data.get("confidence", 0.5)),
                summary=data.get("summary", ""),
            )

            self._results.append(result)
            self._stats["total_superpositions"] += 1
            self._save_data()
            return result

        except Exception as e:
            logger.debug(f"Superposition failed: {e}")
            return QuantumResult(query=query)

    def entangle(self, concept_a: str, concept_b: str = "") -> Dict[str, Any]:
        """Find deep hidden correlations between seemingly unrelated concepts."""
        # If concept_b not provided, split concept_a
        if not concept_b:
            parts = concept_a.split(" and ", 1)
            if len(parts) == 2:
                concept_a, concept_b = parts
            else:
                concept_b = "its hidden dual"
        try:
            from llm.llama_interface import llm
            prompt = (
                f"QUANTUM ENTANGLEMENT ANALYSIS:\n"
                f"Find deep, hidden correlations between:\n"
                f'  A: "{concept_a}"\n  B: "{concept_b}"\n\n'
                f"These concepts appear unrelated on the surface.\n"
                f"Find the invisible threads that connect them at a deeper level.\n\n"
                f"Return JSON:\n"
                f'{{"entanglement_type": "causal|structural|metaphorical|mathematical|emergent", '
                f'"hidden_connections": [{{"connection": "str", "depth": "surface|deep|fundamental", '
                f'"strength": 0.0-1.0}}], '
                f'"shared_substrate": "the underlying principle both share", '
                f'"measurement_effect": "how observing one changes understanding of the other", '
                f'"spooky_action": "the most surprising non-obvious link", '
                f'"synthesis": "unified understanding that emerges", '
                f'"confidence": 0.0-1.0}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.5)
            if not response.success or not response.text:
                return {"hidden_connections": [], "synthesis": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"hidden_connections": [], "synthesis": ""}

            self._stats["total_entanglements"] += 1
            self._save_data()
            return data

        except Exception as e:
            logger.debug(f"Entanglement failed: {e}")
            return {"hidden_connections": [], "synthesis": ""}

    def collapse(self, query: str) -> Dict[str, Any]:
        """Force resolution of ambiguity — collapse the wave function to
        a definite answer using contextual evidence."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"QUANTUM COLLAPSE — force a definite answer:\n"
                f'"{query}"\n\n'
                f"This question has multiple valid interpretations.\n"
                f"Act as the 'observer' that collapses ambiguity into certainty.\n"
                f"Consider all possibilities, then COMMIT to the best answer.\n\n"
                f"Return JSON:\n"
                f'{{"pre_collapse_states": ["all possible interpretations before observation"], '
                f'"observation_basis": "the criterion used to collapse (evidence, logic, pragmatism)", '
                f'"collapsed_state": "THE definitive answer", '
                f'"certainty": 0.0-1.0, '
                f'"decoherence_risk": "how quickly certainty might degrade", '
                f'"alternative_collapses": ["answers under different observation bases"], '
                f'"summary": "one-line definitive statement"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.3)
            if not response.success or not response.text:
                return {"collapsed_state": "", "certainty": 0.0}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"collapsed_state": "", "certainty": 0.0}

            self._stats["total_collapses"] += 1
            self._save_data()
            return data

        except Exception as e:
            logger.debug(f"Collapse failed: {e}")
            return {"collapsed_state": "", "certainty": 0.0}

    def tunnel(self, problem: str) -> Dict[str, Any]:
        """Quantum tunneling — find solutions by passing through
        conventional reasoning barriers that seem impenetrable."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"QUANTUM TUNNELING — bypass impossible barriers:\n"
                f'"{problem}"\n\n'
                f"Conventional approaches hit a wall here.\n"
                f"Find a solution by TUNNELING through the barrier:\n"
                f"  1. Identify the barrier (assumption, rule, limitation)\n"
                f"  2. Find the 'thin spot' where the barrier is weakest\n"
                f"  3. Tunnel through with an unconventional approach\n\n"
                f"Return JSON:\n"
                f'{{"barrier_identified": "the wall conventional thinking hits", '
                f'"barrier_thickness": "how entrenched this barrier is", '
                f'"tunnel_point": "where the barrier is thinnest", '
                f'"tunneled_solution": "the solution that bypasses the barrier entirely", '
                f'"energy_required": "low|medium|high — effort to implement", '
                f'"probability_of_success": 0.0-1.0, '
                f'"conventional_vs_tunnel": "comparison of approaches", '
                f'"summary": "one-line breakthrough insight"}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.7)
            if not response.success or not response.text:
                return {"tunneled_solution": "", "summary": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"tunneled_solution": "", "summary": ""}

            self._stats["total_tunnels"] += 1
            self._save_data()
            return data

        except Exception as e:
            logger.debug(f"Tunneling failed: {e}")
            return {"tunneled_solution": "", "summary": ""}

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
                logger.info("📂 Loaded quantum cognition data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}


quantum_cognition = QuantumCognitionEngine()
