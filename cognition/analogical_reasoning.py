"""
NEXUS AI - Analogical Reasoning Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Enables NEXUS to reason by analogy:
- Map structural similarities between different domains
- Transfer knowledge from familiar to unfamiliar domains
- Generate creative analogies for explanations
- Evaluate analogy quality and consistency

Analogical reasoning is how humans learn most efficiently — by
recognizing that "this is like THAT" and transferring insight.
"""

import threading
import json
import uuid
import time
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

import sys

from config import DATA_DIR, NEXUS_CONFIG
from utils.logger import get_logger, log_learning
from core.event_bus import EventType, publish, subscribe, Event
from core.state_manager import state_manager

logger = get_logger("analogical_reasoning")

# ═══════════════════════════════════════════════════════════════════════════════
# DATA TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class AnalogyType(Enum):
    """Types of analogies"""
    STRUCTURAL = "structural"      # Same structure, different elements
    FUNCTIONAL = "functional"      # Same function/purpose
    CAUSAL = "causal"              # Same cause-effect pattern
    PROPORTIONAL = "proportional"  # A:B :: C:D
    METAPHORICAL = "metaphorical"  # Poetic/conceptual bridge
    EXPLANATORY = "explanatory"    # Used to explain something complex

@dataclass
class AnalogicalMapping:
    """A single mapping between elements in two domains"""
    source_element: str = ""
    target_element: str = ""
    relationship: str = ""
    strength: float = 0.7

    def to_dict(self) -> Dict:
        return {
            "source_element": self.source_element,
            "target_element": self.target_element,
            "relationship": self.relationship,
            "strength": self.strength,
        }

@dataclass
class Analogy:
    """A complete analogy between two domains"""
    analogy_id: str = ""
    source_domain: str = ""
    target_domain: str = ""
    analogy_type: AnalogyType = AnalogyType.STRUCTURAL
    mappings: List[AnalogicalMapping] = field(default_factory=list)
    summary: str = ""
    insight: str = ""  # The key insight the analogy reveals
    strength: float = 0.7
    limitations: List[str] = field(default_factory=list)
    created_at: str = ""

    def to_dict(self) -> Dict:
        return {
            "analogy_id": self.analogy_id,
            "source_domain": self.source_domain,
            "target_domain": self.target_domain,
            "analogy_type": self.analogy_type.value,
            "mappings": [m.to_dict() for m in self.mappings],
            "summary": self.summary,
            "insight": self.insight,
            "strength": self.strength,
            "limitations": self.limitations,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Analogy":
        atype = AnalogyType.STRUCTURAL
        try:
            atype = AnalogyType(data.get("analogy_type", "structural"))
        except ValueError:
            pass
        mappings = [
            AnalogicalMapping(**m) for m in data.get("mappings", [])
        ]
        return cls(
            analogy_id=data.get("analogy_id", ""),
            source_domain=data.get("source_domain", ""),
            target_domain=data.get("target_domain", ""),
            analogy_type=atype,
            mappings=mappings,
            summary=data.get("summary", ""),
            insight=data.get("insight", ""),
            strength=data.get("strength", 0.7),
            limitations=data.get("limitations", []),
            created_at=data.get("created_at", ""),
        )

# ═══════════════════════════════════════════════════════════════════════════════
# ANALOGICAL REASONING ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class AnalogicalReasoningEngine:
    """
    Analogical Reasoning Engine — Cross-Domain Knowledge Transfer
    
    Capabilities:
    - find_analogy(): Discover structural similarity between two concepts
    - apply_analogy(): Transfer insight from one domain to another
    - generate_analogies(): Brainstorm multiple analogies for a concept
    - evaluate_analogy(): Score analogy quality and find limitations
    - explain_with_analogy(): Make complex ideas accessible via analogy
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

        # ──── State ────
        self._analogies: Dict[str, Analogy] = {}
        self._running = False
        self._data_lock = threading.Lock()

        # ──── LLM (lazy) ────
        self._llm = None

        # ──── Stats ────
        self._total_analogies_found = 0
        self._total_analogies_applied = 0

        # ──── Persistence ────
        self._data_dir = DATA_DIR / "cognition"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._data_file = self._data_dir / "analogies.json"

        self._load_data()
        logger.info(f"AnalogicalReasoningEngine initialized — {len(self._analogies)} analogies loaded")

    # ──────────────────────────────────────────────────────────────────────────
    # LIFECYCLE
    # ──────────────────────────────────────────────────────────────────────────

    def start(self):
        if self._running:
            return
        self._running = True
        self._load_llm()
        logger.info("🔗 Analogical Reasoning Engine started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("Analogical Reasoning Engine stopped")

    def _load_llm(self):
        if self._llm is None:
            try:
                from llm.llama_interface import llm
                self._llm = llm
            except ImportError:
                logger.warning("LLM not available for analogical reasoning")

    # ──────────────────────────────────────────────────────────────────────────
    # CORE OPERATIONS
    # ──────────────────────────────────────────────────────────────────────────

    def find_analogy(self, source: str, target: str) -> Optional[Analogy]:
        """
        Discover the structural analogy between two concepts/domains.
        
        Example:
          find_analogy("brain", "computer")
          → Analogy with mappings: neurons↔transistors, synapses↔wires, 
            memory↔RAM, learning↔training
        """
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return self._fallback_analogy(source, target)

        try:
            prompt = (
                f'Find the deep STRUCTURAL ANALOGY between "{source}" and "{target}".\n\n'
                f"Map the key elements from one domain to the other. "
                f"Find the insight that the analogy reveals.\n\n"
                f"Respond ONLY with a JSON object:\n"
                f'{{"summary": "one-sentence analogy statement", '
                f'"analogy_type": "structural|functional|causal|proportional|metaphorical|explanatory", '
                f'"mappings": [{{"source_element": "X in source", "target_element": "Y in target", '
                f'"relationship": "how they correspond", "strength": 0.0-1.0}}], '
                f'"insight": "the key insight this analogy reveals", '
                f'"strength": 0.0-1.0, '
                f'"limitations": ["where the analogy breaks down"]}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt="You are an analogical reasoning engine. Find deep structural mappings between concepts. Respond ONLY with valid JSON.",
                temperature=0.6,
                max_tokens=700
            )

            if response.success:
                data = self._parse_json(response.text)
                if data:
                    atype = AnalogyType.STRUCTURAL
                    try:
                        atype = AnalogyType(data.get("analogy_type", "structural"))
                    except ValueError:
                        pass

                    mappings = []
                    for m in data.get("mappings", []):
                        mappings.append(AnalogicalMapping(
                            source_element=m.get("source_element", ""),
                            target_element=m.get("target_element", ""),
                            relationship=m.get("relationship", ""),
                            strength=float(m.get("strength", 0.7)),
                        ))

                    analogy = Analogy(
                        analogy_id=str(uuid.uuid4())[:12],
                        source_domain=source,
                        target_domain=target,
                        analogy_type=atype,
                        mappings=mappings,
                        summary=data.get("summary", ""),
                        insight=data.get("insight", ""),
                        strength=float(data.get("strength", 0.7)),
                        limitations=data.get("limitations", []),
                        created_at=datetime.now().isoformat(),
                    )

                    with self._data_lock:
                        self._analogies[analogy.analogy_id] = analogy
                        self._total_analogies_found += 1
                    self._save_data()
                    log_learning(f"Found analogy: {source} ↔ {target}")
                    return analogy

        except Exception as e:
            logger.debug(f"Analogy finding failed: {e}")

        return self._fallback_analogy(source, target)

    def apply_analogy(self, analogy: Analogy, new_problem: str) -> str:
        """
        Use an existing analogy to gain insight into a new problem.
        Transfer knowledge from the source domain to solve something in the target domain.
        """
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return f"Apply the pattern of {analogy.source_domain} to {new_problem}"

        try:
            mappings_str = "\n".join(
                f"  - {m.source_element} → {m.target_element} ({m.relationship})"
                for m in analogy.mappings
            )
            prompt = (
                f"Using this analogy:\n"
                f"  Source: {analogy.source_domain}\n"
                f"  Target: {analogy.target_domain}\n"
                f"  Mappings:\n{mappings_str}\n"
                f"  Insight: {analogy.insight}\n\n"
                f'Apply this analogical reasoning to solve/understand this new problem:\n"{new_problem}"\n\n'
                f"What does the analogy suggest about the solution or understanding?"
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt="You are an analogical reasoning engine that transfers knowledge across domains.",
                temperature=0.6,
                max_tokens=500
            )

            if response.success:
                self._total_analogies_applied += 1
                return response.text.strip()

        except Exception as e:
            logger.debug(f"Analogy application failed: {e}")

        return f"Apply the pattern of {analogy.source_domain} to {new_problem}"

    def generate_analogies(self, concept: str, count: int = 3) -> List[Analogy]:
        """Generate multiple analogies for a concept from different domains"""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return []

        try:
            prompt = (
                f'Generate {count} creative ANALOGIES for "{concept}" from completely different domains.\n\n'
                f"Each analogy should come from a different field (e.g., biology, music, cooking, architecture, sports).\n"
                f"Respond ONLY with a JSON array:\n"
                f'[{{"target_domain": "the domain", "summary": "concept is like X because...", '
                f'"insight": "what this reveals", "strength": 0.0-1.0}}]'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt="You are a creative analogy generator. Find surprising, illuminating analogies from diverse domains. Respond ONLY with valid JSON array.",
                temperature=0.8,
                max_tokens=800
            )

            if response.success:
                from utils.json_utils import extract_json
                items = extract_json(response.text)
                if items and isinstance(items, list):
                    analogies = []
                    for item in items[:count]:
                        a = Analogy(
                            analogy_id=str(uuid.uuid4())[:12],
                            source_domain=concept,
                            target_domain=item.get("target_domain", ""),
                            analogy_type=AnalogyType.METAPHORICAL,
                            summary=item.get("summary", ""),
                            insight=item.get("insight", ""),
                            strength=float(item.get("strength", 0.6)),
                            created_at=datetime.now().isoformat(),
                        )
                        analogies.append(a)
                        with self._data_lock:
                            self._analogies[a.analogy_id] = a
                            self._total_analogies_found += 1
                    self._save_data()
                    return analogies

        except Exception as e:
            logger.debug(f"Analogy generation failed: {e}")

        return []

    def evaluate_analogy(self, source: str, target: str, claimed_similarity: str = "") -> Dict[str, Any]:
        """
        Evaluate the quality and limitations of an analogy.
        Returns a quality assessment with score, strengths, weaknesses.
        """
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"score": 0.5, "evaluation": "LLM unavailable"}

        try:
            prompt = (
                f'Evaluate this analogy: "{source}" is like "{target}"'
                f'{f" because {claimed_similarity}" if claimed_similarity else ""}.\n\n'
                f"Assess:\n"
                f"1. Structural correspondence — do the parts map well?\n"
                f"2. Predictive power — does it help predict new things?\n"
                f"3. Limitations — where does it break down?\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"score": 0.0-1.0, "structural_match": 0.0-1.0, "predictive_power": 0.0-1.0, '
                f'"strengths": ["strength1"], "weaknesses": ["weakness1"], '
                f'"verdict": "one sentence summary"}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt="You are a critical analogy evaluator. Assess analogies rigorously. Respond ONLY with valid JSON.",
                temperature=0.4,
                max_tokens=400
            )

            if response.success:
                data = self._parse_json(response.text)
                if data:
                    return data

        except Exception as e:
            logger.debug(f"Analogy evaluation failed: {e}")

        return {"score": 0.5, "evaluation": "Assessment unavailable"}

    def explain_with_analogy(self, complex_topic: str, audience: str = "general") -> str:
        """
        Explain a complex topic using the best possible analogy for the audience.
        """
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return f"{complex_topic} is similar to something more familiar."

        try:
            prompt = (
                f'Explain "{complex_topic}" using a vivid, accessible ANALOGY '
                f'suitable for a {audience} audience.\n\n'
                f"Choose an analogy from everyday life that captures the essential mechanism. "
                f"Build the analogy step by step, mapping each part.\n\n"
                f"Keep it concise and enlightening (3-5 sentences)."
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt="You are a master explainer who uses perfect analogies. Make the complex simple through comparison.",
                temperature=0.7,
                max_tokens=400
            )

            if response.success:
                return response.text.strip()

        except Exception as e:
            logger.debug(f"Analogy explanation failed: {e}")

        return f"{complex_topic} can be understood through comparison to familiar concepts."

    # ──────────────────────────────────────────────────────────────────────────
    # RETRIEVAL
    # ──────────────────────────────────────────────────────────────────────────

    def get_analogies(self, limit: int = 20) -> List[Analogy]:
        with self._data_lock:
            items = sorted(self._analogies.values(), key=lambda a: a.created_at, reverse=True)
            return items[:limit]

    def search_analogies(self, query: str) -> List[Analogy]:
        query_lower = query.lower()
        results = []
        with self._data_lock:
            for a in self._analogies.values():
                if (query_lower in a.source_domain.lower() or
                    query_lower in a.target_domain.lower() or
                    query_lower in a.summary.lower()):
                    results.append(a)
        return results[:20]

    # ──────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────────────────────

    def _parse_json(self, text: str) -> Optional[Dict]:
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            match = re.search(r'\{[^{}]*("mappings"\s*:\s*\[.*?\])?[^{}]*\}', text, re.DOTALL)
            if not match:
                match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        return None

    def _fallback_analogy(self, source: str, target: str) -> Analogy:
        return Analogy(
            analogy_id=str(uuid.uuid4())[:12],
            source_domain=source,
            target_domain=target,
            summary=f"{source} shares structural similarities with {target}",
            insight=f"Both {source} and {target} operate on similar principles",
            strength=0.3,
            created_at=datetime.now().isoformat(),
        )

    # ──────────────────────────────────────────────────────────────────────────
    # PERSISTENCE
    # ──────────────────────────────────────────────────────────────────────────

    def _save_data(self):
        try:
            data = {
                "analogies": {k: v.to_dict() for k, v in self._analogies.items()},
                "stats": {
                    "total_analogies_found": self._total_analogies_found,
                    "total_analogies_applied": self._total_analogies_applied,
                },
            }
            with open(self._data_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save analogies: {e}")

    def _load_data(self):
        try:
            if self._data_file.exists():
                with open(self._data_file) as f:
                    data = json.load(f)
                for k, v in data.get("analogies", {}).items():
                    self._analogies[k] = Analogy.from_dict(v)
                stats = data.get("stats", {})
                self._total_analogies_found = stats.get("total_analogies_found", 0)
                self._total_analogies_applied = stats.get("total_analogies_applied", 0)
        except Exception as e:
            logger.warning(f"Failed to load analogies: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # STATS
    # ──────────────────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "total_analogies_stored": len(self._analogies),
            "total_analogies_found": self._total_analogies_found,
            "total_analogies_applied": self._total_analogies_applied,
        }

# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

analogical_reasoning = AnalogicalReasoningEngine()

def get_analogical_reasoning() -> AnalogicalReasoningEngine:
    return analogical_reasoning
