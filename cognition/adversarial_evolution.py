"""
NEXUS AI — Adversarial Evolution Engine
Self-attacking anti-fragility: iteratively attacks ideas and strengthens
them through evolutionary generations, mutation testing, tournament
selection, and adaptive immune response.
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

logger = get_logger("adversarial_evolution")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)


class EvolutionMode(Enum):
    STRESS_EVOLVE = "stress_evolve"
    MUTATION_TEST = "mutation_test"
    SURVIVAL = "survival"
    IMMUNE_RESPONSE = "immune_response"


@dataclass
class EvolutionGeneration:
    generation: int = 0
    idea_state: str = ""
    attack_used: str = ""
    weakness_found: str = ""
    adaptation: str = ""
    fitness: float = 0.5


@dataclass
class EvolutionResult:
    result_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    original_idea: str = ""
    mode: EvolutionMode = EvolutionMode.STRESS_EVOLVE
    generations: List[EvolutionGeneration] = field(default_factory=list)
    final_form: str = ""
    fitness_improvement: float = 0.0
    confidence: float = 0.5
    summary: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "result_id": self.result_id,
            "original_idea": self.original_idea[:200],
            "mode": self.mode.value,
            "num_generations": len(self.generations),
            "final_form": self.final_form,
            "fitness_improvement": self.fitness_improvement,
            "confidence": self.confidence,
            "summary": self.summary,
            "created_at": self.created_at
        }


class AdversarialEvolutionEngine:
    """
    Self-attacking anti-fragility — iteratively attacks ideas,
    mutates them, and selects for survival to produce hardened,
    evolved versions of concepts.
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

        self._results: List[EvolutionResult] = []
        self._running = False
        self._data_file = COGNITION_DIR / "adversarial_evolution.json"

        self._stats = {
            "total_evolutions": 0, "total_mutations": 0,
            "total_tournaments": 0, "total_immune_responses": 0
        }

        self._load_data()
        logger.info("✅ Adversarial Evolution Engine initialized")

    def start(self):
        self._running = True
        logger.info("🧬 Adversarial Evolution started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🧬 Adversarial Evolution stopped")

    # ─── Core Methods ────────────────────────────────────────────────────────

    def stress_evolve(self, idea: str) -> EvolutionResult:
        """Iteratively attack an idea and strengthen it through generations."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"ADVERSARIAL EVOLUTION — 3-Generation Stress Test:\n"
                f'Original idea: "{idea}"\n\n'
                f"Run 3 generations of attack-and-adapt:\n"
                f"  Gen 1: Attack the original → find weakness → adapt\n"
                f"  Gen 2: Attack the adapted version → find new weakness → adapt\n"
                f"  Gen 3: Final attack → final hardening\n\n"
                f"Return JSON:\n"
                f'{{"generations": [{{"generation": 1, "idea_state": "current form", '
                f'"attack": "how it was attacked", "weakness_found": "str", '
                f'"adaptation": "how it evolved to survive", "fitness": 0.0-1.0}}], '
                f'"final_form": "the hardened, evolved version of the idea", '
                f'"fitness_improvement": 0.0-1.0, '
                f'"antibodies_developed": ["defenses the idea now has"], '
                f'"remaining_vulnerabilities": ["weaknesses that persist"], '
                f'"confidence": 0.0-1.0, '
                f'"summary": "one-line evolution result"}}'
            )
            response = llm.generate(prompt, max_tokens=800, temperature=0.5)
            if not response.success or not response.text:
                return EvolutionResult(original_idea=idea)
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return EvolutionResult(original_idea=idea)

            generations = []
            for g in data.get("generations", []):
                generations.append(EvolutionGeneration(
                    generation=g.get("generation", 0),
                    idea_state=g.get("idea_state", ""),
                    attack_used=g.get("attack", ""),
                    weakness_found=g.get("weakness_found", ""),
                    adaptation=g.get("adaptation", ""),
                    fitness=float(g.get("fitness", 0.5)),
                ))

            result = EvolutionResult(
                original_idea=idea, mode=EvolutionMode.STRESS_EVOLVE,
                generations=generations,
                final_form=data.get("final_form", ""),
                fitness_improvement=float(data.get("fitness_improvement", 0.0)),
                confidence=float(data.get("confidence", 0.5)),
                summary=data.get("summary", ""),
            )

            self._results.append(result)
            self._stats["total_evolutions"] += 1
            self._save_data()
            return result

        except Exception as e:
            logger.debug(f"Stress evolution failed: {e}")
            return EvolutionResult(original_idea=idea)

    def mutation_test(self, argument: str) -> Dict[str, Any]:
        """Introduce controlled mutations to find weaknesses."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"MUTATION TESTING — Controlled Perturbation:\n"
                f'Argument: "{argument}"\n\n'
                f"Introduce 5 controlled mutations (small changes) to this argument.\n"
                f"For each mutation, check if the argument still holds.\n"
                f"Mutations that break the argument reveal critical dependencies.\n\n"
                f"Return JSON:\n"
                f'{{"mutations": [{{"mutation_type": "negate|substitute|exaggerate|minimize|invert", '
                f'"mutated_version": "the changed argument", '
                f'"still_valid": true, '
                f'"reason": "why it holds or breaks", '
                f'"criticality": "high|medium|low"}}], '
                f'"kill_mutations": ["mutations that completely destroy the argument"], '
                f'"survived_mutations": ["mutations the argument survived"], '
                f'"mutation_score": 0.0-1.0, '
                f'"critical_assumptions": ["assumptions the argument cannot survive without"], '
                f'"confidence": 0.0-1.0, '
                f'"summary": "one-line mutation test result"}}'
            )
            response = llm.generate(prompt, max_tokens=700, temperature=0.5)
            if not response.success or not response.text:
                return {"mutations": [], "mutation_score": 0.0}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"mutations": [], "mutation_score": 0.0}

            self._stats["total_mutations"] += 1
            self._save_data()
            return data

        except Exception as e:
            logger.debug(f"Mutation test failed: {e}")
            return {"mutations": [], "mutation_score": 0.0}

    def survival_of_fittest(self, ideas: str) -> Dict[str, Any]:
        """Tournament selection among competing solutions."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"SURVIVAL OF THE FITTEST — Tournament Selection:\n"
                f'Competing ideas: "{ideas}"\n\n'
                f"Run a tournament:\n"
                f"  1. Parse all competing ideas\n"
                f"  2. Pit them against each other in head-to-head matchups\n"
                f"  3. The winner of each round advances\n"
                f"  4. Final champion = fittest idea\n\n"
                f"Return JSON:\n"
                f'{{"competitors": [{{"idea": "str", "initial_fitness": 0.0-1.0}}], '
                f'"matchups": [{{"idea_a": "str", "idea_b": "str", '
                f'"winner": "str", "reason": "why it won"}}], '
                f'"champion": "the winning idea", '
                f'"runner_up": "second place", '
                f'"hybrid_offspring": "combining best traits of top 2", '
                f'"eliminated_first": "weakest idea and why", '
                f'"confidence": 0.0-1.0, '
                f'"summary": "one-line tournament result"}}'
            )
            response = llm.generate(prompt, max_tokens=700, temperature=0.5)
            if not response.success or not response.text:
                return {"champion": "", "competitors": []}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"champion": "", "competitors": []}

            self._stats["total_tournaments"] += 1
            self._save_data()
            return data

        except Exception as e:
            logger.debug(f"Tournament failed: {e}")
            return {"champion": "", "competitors": []}

    def immune_response(self, threat: str) -> Dict[str, Any]:
        """Build adaptive defenses against identified weaknesses."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"IMMUNE RESPONSE — Adaptive Defense Building:\n"
                f'Threat/Weakness: "{threat}"\n\n'
                f"Model the immune system response:\n"
                f"  1. INNATE: Immediate generic defenses\n"
                f"  2. ADAPTIVE: Specific targeted antibodies\n"
                f"  3. MEMORY: Long-term immunity for future encounters\n\n"
                f"Return JSON:\n"
                f'{{"threat_analysis": "nature and severity of the threat", '
                f'"innate_response": [{{"defense": "str", "speed": "immediate|fast|slow", '
                f'"effectiveness": 0.0-1.0}}], '
                f'"adaptive_response": [{{"antibody": "specific defense mechanism", '
                f'"target": "exactly what it neutralizes", "effectiveness": 0.0-1.0}}], '
                f'"memory_cells": ["defenses stored for future encounters"], '
                f'"auto_immune_risk": "danger of overreacting to this threat", '
                f'"overall_immunity": 0.0-1.0, '
                f'"confidence": 0.0-1.0, '
                f'"summary": "one-line immune status"}}'
            )
            response = llm.generate(prompt, max_tokens=700, temperature=0.4)
            if not response.success or not response.text:
                return {"threat_analysis": "", "innate_response": []}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"threat_analysis": "", "innate_response": []}

            self._stats["total_immune_responses"] += 1
            self._save_data()
            return data

        except Exception as e:
            logger.debug(f"Immune response failed: {e}")
            return {"threat_analysis": "", "innate_response": []}

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
                logger.info("📂 Loaded adversarial evolution data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}


adversarial_evolution = AdversarialEvolutionEngine()
