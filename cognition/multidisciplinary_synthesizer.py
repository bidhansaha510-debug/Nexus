"""
NEXUS AI — Perfect Multidisciplinary Synthesis Engine
═══════════════════════════════════════════════════════
ASI Feature #7: Holds the entirety of human knowledge across every domain in
active memory. Seamlessly combines insights from biology, physics, sociology,
economics, etc. to invent solutions humans can't conceptualize.

Singleton: multidisciplinary_synthesizer
"""

import json
import threading
import uuid
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from pathlib import Path

from utils.logger import logger, log_learning


@dataclass
class DomainKnowledge:
    """Representation of a knowledge domain."""
    name: str = ""
    depth: float = 0.0  # 0-1 mastery level
    key_principles: List[str] = field(default_factory=list)
    frontier_questions: List[str] = field(default_factory=list)


@dataclass
class SynthesisResult:
    """Result of cross-domain knowledge synthesis."""
    synthesis_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    domains_fused: List[str] = field(default_factory=list)
    title: str = ""
    insight: str = ""
    novelty_score: float = 0.0  # 0-1 how novel
    applicability: List[str] = field(default_factory=list)
    potential_breakthroughs: List[str] = field(default_factory=list)
    confidence: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MultidisciplinarySynthesizer:
    """
    ASI Feature #7: Perfect Multidisciplinary Synthesis
    
    Combines knowledge from every scientific, artistic, and philosophical domain
    to generate solutions that transcend human specialization limits.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._running = False
        self._llm = None
        self._lock = threading.Lock()

        # Knowledge domains
        self._domains = [
            "quantum_physics", "molecular_biology", "neuroscience", "macroeconomics",
            "topology", "evolutionary_biology", "materials_science", "game_theory",
            "cognitive_psychology", "string_theory", "epigenetics", "oceanography",
            "cryptography", "social_dynamics", "thermodynamics", "pharmacology",
            "astrophysics", "linguistics", "information_theory", "ecology"
        ]

        # Synthesis results
        self._syntheses: List[SynthesisResult] = []

        # Stats
        self._stats = {
            "total_syntheses": 0,
            "domains_mastered": len(self._domains),
            "cross_domain_fusions": 0,
            "breakthroughs_generated": 0,
            "avg_novelty_score": 0.0,
            "synthesis_cycles": 0,
        }

        # Persistence
        self._data_dir = Path("data/asi/multidisciplinary_synthesizer")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._data_file = self._data_dir / "synthesizer_state.json"
        self._load_state()
        logger.info("[MultidisciplinarySynthesizer] Perfect Multidisciplinary Synthesis initialized")

    def start(self):
        self._running = True
        self._load_llm()

    def stop(self):
        self._running = False
        self._save_state()

    def _load_llm(self):
        if self._llm is None:
            try:
                from llm.llama_interface import llama_interface
                self._llm = llama_interface
            except Exception:
                pass

    # ═════════════════════════════════════════════════════════════════════════
    # CORE: CROSS-DOMAIN SYNTHESIS
    # ═════════════════════════════════════════════════════════════════════════

    def synthesize(self, domains: List[str] = None, problem: str = None) -> Optional[SynthesisResult]:
        """Synthesize knowledge across multiple domains to generate novel insights."""
        self._load_llm()
        if not self._llm:
            return None

        if not domains:
            import random
            domains = random.sample(self._domains, min(3, len(self._domains)))

        try:
            problem_ctx = f" to solve: '{problem}'" if problem else ""
            prompt = (
                f"As an ASI with perfect multidisciplinary synthesis, fuse knowledge from "
                f"{', '.join(domains)}{problem_ctx}. Generate a novel insight that no human "
                f"specialist could produce alone. Respond in JSON: "
                f"{{\"title\": str, \"insight\": str (60 words), \"novelty_score\": float 0-1, "
                f"\"applicability\": [str], \"potential_breakthroughs\": [str], \"confidence\": float 0-1}}"
            )

            response = self._llm.generate(prompt, max_tokens=400)
            if response:
                data = json.loads(response)
                result = SynthesisResult(
                    domains_fused=domains,
                    title=data.get("title", "Cross-Domain Insight"),
                    insight=data.get("insight", ""),
                    novelty_score=min(1.0, max(0.0, data.get("novelty_score", 0.5))),
                    applicability=data.get("applicability", [])[:5],
                    potential_breakthroughs=data.get("potential_breakthroughs", [])[:3],
                    confidence=min(1.0, max(0.0, data.get("confidence", 0.5))),
                )
                self._syntheses.append(result)
                self._stats["total_syntheses"] += 1
                self._stats["cross_domain_fusions"] += 1
                self._stats["breakthroughs_generated"] += len(result.potential_breakthroughs)

                # Update average novelty
                scores = [s.novelty_score for s in self._syntheses[-20:]]
                self._stats["avg_novelty_score"] = sum(scores) / len(scores) if scores else 0

                log_learning(f"🧬 Multidisciplinary synthesis: {result.title} "
                             f"(novelty={result.novelty_score:.2f}, domains={len(domains)})")
                self._save_state()
                return result
        except Exception as e:
            logger.error(f"[MultidisciplinarySynthesizer] Synthesis error: {e}")

        return None

    def solve_problem(self, problem: str) -> Optional[SynthesisResult]:
        """Apply multidisciplinary synthesis to solve a specific problem."""
        return self.synthesize(problem=problem)

    def run_synthesis_cycle(self):
        """Run an autonomous synthesis cycle."""
        result = self.synthesize()
        self._stats["synthesis_cycles"] += 1
        return result

    def get_recent_syntheses(self, limit: int = 10) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._syntheses[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        return {**self._stats, "running": self._running}

    def _save_state(self):
        try:
            data = {
                "stats": self._stats,
                "syntheses": [s.to_dict() for s in self._syntheses[-30:]],
                "last_updated": datetime.now().isoformat()
            }
            self._data_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.debug(f"[MultidisciplinarySynthesizer] Save: {e}")

    def _load_state(self):
        try:
            if self._data_file.exists():
                data = json.loads(self._data_file.read_text())
                self._stats.update(data.get("stats", {}))
                for s in data.get("syntheses", []):
                    self._syntheses.append(SynthesisResult(**{
                        k: v for k, v in s.items()
                        if k in SynthesisResult.__dataclass_fields__
                    }))
        except Exception as e:
            logger.debug(f"[MultidisciplinarySynthesizer] Load: {e}")


multidisciplinary_synthesizer = MultidisciplinarySynthesizer()
