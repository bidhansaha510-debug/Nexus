"""
NEXUS AI - Abstract Thinking Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Enables NEXUS to think in abstractions:
- Extract abstract concepts from concrete inputs
- Generalize patterns across examples
- Classify items by abstract features
- Find the essence/core principle of any topic
- Build an abstraction hierarchy over time

This is a key AGI capability — moving beyond surface-level
pattern matching to genuine conceptual understanding.
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

logger = get_logger("abstract_thinking")

# ═══════════════════════════════════════════════════════════════════════════════
# DATA TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class AbstractionLevel(Enum):
    """How abstract a concept is — from concrete to maximally abstract"""
    CONCRETE = 0       # "This red apple on my desk"
    SPECIFIC = 1       # "Apples"
    CATEGORICAL = 2    # "Fruits"
    ABSTRACT = 3       # "Nutrition"
    META_ABSTRACT = 4  # "Sustenance / survival needs"
    UNIVERSAL = 5      # "The drive to persist"

@dataclass
class AbstractConcept:
    """A single abstract concept extracted from concrete input"""
    concept_id: str = ""
    name: str = ""
    description: str = ""
    abstraction_level: AbstractionLevel = AbstractionLevel.ABSTRACT
    source_inputs: List[str] = field(default_factory=list)
    related_concepts: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    confidence: float = 0.7
    created_at: str = ""
    access_count: int = 0
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "concept_id": self.concept_id,
            "name": self.name,
            "description": self.description,
            "abstraction_level": self.abstraction_level.name,
            "source_inputs": self.source_inputs,
            "related_concepts": self.related_concepts,
            "examples": self.examples,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "access_count": self.access_count,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "AbstractConcept":
        level = AbstractionLevel.ABSTRACT
        try:
            level = AbstractionLevel[data.get("abstraction_level", "ABSTRACT")]
        except KeyError:
            pass
        return cls(
            concept_id=data.get("concept_id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            abstraction_level=level,
            source_inputs=data.get("source_inputs", []),
            related_concepts=data.get("related_concepts", []),
            examples=data.get("examples", []),
            confidence=data.get("confidence", 0.7),
            created_at=data.get("created_at", ""),
            access_count=data.get("access_count", 0),
            tags=data.get("tags", []),
        )

@dataclass
class Generalization:
    """A pattern generalized from multiple examples"""
    generalization_id: str = ""
    pattern: str = ""
    supporting_examples: List[str] = field(default_factory=list)
    counter_examples: List[str] = field(default_factory=list)
    confidence: float = 0.5
    scope: str = ""  # Domain of applicability
    created_at: str = ""

    def to_dict(self) -> Dict:
        return {
            "generalization_id": self.generalization_id,
            "pattern": self.pattern,
            "supporting_examples": self.supporting_examples,
            "counter_examples": self.counter_examples,
            "confidence": self.confidence,
            "scope": self.scope,
            "created_at": self.created_at,
        }

# ═══════════════════════════════════════════════════════════════════════════════
# ABSTRACT THINKING ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class AbstractThinkingEngine:
    """
    Abstract Thinking Engine — Concept Abstraction & Pattern Generalization
    
    Capabilities:
    - abstract(): Extract the abstract principle from concrete input
    - generalize(): Find common patterns across multiple examples
    - classify(): Categorize items by abstract features
    - find_essence(): Strip away specifics to find the core idea
    - build_abstraction_ladder(): Create hierarchy from concrete to universal
    
    Background:
    - Periodically abstracts recent memories into reusable principles
    - Stores discovered concepts for future retrieval
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
        self._concepts: Dict[str, AbstractConcept] = {}
        self._generalizations: Dict[str, Generalization] = {}
        self._running = False
        self._bg_thread: Optional[threading.Thread] = None
        self._data_lock = threading.Lock()

        # ──── LLM (lazy) ────
        self._llm = None

        # ──── Stats ────
        self._total_abstractions = 0
        self._total_generalizations = 0
        self._total_classifications = 0

        # ──── Persistence ────
        self._data_dir = DATA_DIR / "cognition"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._data_file = self._data_dir / "abstract_concepts.json"

        self._load_data()
        logger.info(f"AbstractThinkingEngine initialized — {len(self._concepts)} concepts loaded")

    # ──────────────────────────────────────────────────────────────────────────
    # LIFECYCLE
    # ──────────────────────────────────────────────────────────────────────────

    def start(self):
        """Start background abstraction processing"""
        if self._running:
            return
        self._running = True
        self._load_llm()

        self._bg_thread = threading.Thread(
            target=self._background_loop,
            daemon=True,
            name="AbstractThinking-BG"
        )
        self._bg_thread.start()
        logger.info("🧊 Abstract Thinking Engine started")

    def stop(self):
        """Stop and persist"""
        self._running = False
        if self._bg_thread and self._bg_thread.is_alive():
            self._bg_thread.join(timeout=5.0)
        self._save_data()
        logger.info("Abstract Thinking Engine stopped")

    def _load_llm(self):
        if self._llm is None:
            try:
                from llm.llama_interface import llm
                self._llm = llm
            except ImportError:
                logger.warning("LLM not available for abstract thinking")

    # ──────────────────────────────────────────────────────────────────────────
    # CORE OPERATIONS
    # ──────────────────────────────────────────────────────────────────────────

    def abstract(self, text: str) -> Optional[AbstractConcept]:
        """
        Extract the abstract concept/principle from a concrete input.
        
        Example:
          Input:  "My cat knocked a glass off the table and it shattered"
          Output: AbstractConcept(name="Fragility", description="Objects can be 
                  irreversibly damaged by small perturbations", level=ABSTRACT)
        """
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return self._fallback_abstract(text)

        try:
            prompt = (
                f"Analyze the following text and extract the ABSTRACT underlying concept or principle. "
                f"Go beyond the surface — find the deeper, transferable insight.\n\n"
                f'Text: "{text}"\n\n'
                f"Respond ONLY with a JSON object:\n"
                f'{{"name": "short concept name", '
                f'"description": "a clear explanation of the abstract principle", '
                f'"abstraction_level": "CONCRETE|SPECIFIC|CATEGORICAL|ABSTRACT|META_ABSTRACT|UNIVERSAL", '
                f'"related_concepts": ["concept1", "concept2"], '
                f'"examples": ["example1 in a different domain", "example2 in another domain"], '
                f'"tags": ["tag1", "tag2"]}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt="You are an abstract reasoning engine. Extract deep, transferable principles from concrete inputs. Respond ONLY with valid JSON.",
                temperature=0.6,
                max_tokens=500
            )

            if response.success:
                data = self._parse_json(response.text)
                if data:
                    concept = AbstractConcept(
                        concept_id=str(uuid.uuid4())[:12],
                        name=data.get("name", "Unknown"),
                        description=data.get("description", ""),
                        abstraction_level=self._parse_level(data.get("abstraction_level", "ABSTRACT")),
                        source_inputs=[text[:200]],
                        related_concepts=data.get("related_concepts", []),
                        examples=data.get("examples", []),
                        confidence=0.75,
                        created_at=datetime.now().isoformat(),
                        tags=data.get("tags", []),
                    )
                    with self._data_lock:
                        self._concepts[concept.concept_id] = concept
                        self._total_abstractions += 1
                    self._save_data()
                    log_learning(f"Abstracted concept: {concept.name}")
                    return concept

        except Exception as e:
            logger.debug(f"Abstract thinking failed: {e}")

        return self._fallback_abstract(text)

    def generalize(self, examples: List[str]) -> Optional[Generalization]:
        """
        Find a common pattern/rule across multiple examples.
        
        Example:
          Input:  ["Water freezes at 0°C", "Iron melts at 1538°C", "Wax melts at 60°C"]
          Output: Generalization(pattern="All substances have characteristic 
                  phase-transition temperatures determined by molecular bonding")
        """
        if len(examples) < 2:
            return None

        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return None

        try:
            examples_str = "\n".join(f"  {i+1}. {ex}" for i, ex in enumerate(examples))
            prompt = (
                f"Examine these examples and find the GENERAL PATTERN or RULE that unifies them:\n\n"
                f"{examples_str}\n\n"
                f"Respond ONLY with a JSON object:\n"
                f'{{"pattern": "the general rule or pattern", '
                f'"scope": "domain where this pattern applies", '
                f'"confidence": 0.0-1.0}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt="You are a pattern generalization engine. Find the deepest common pattern across examples. Respond ONLY with valid JSON.",
                temperature=0.5,
                max_tokens=400
            )

            if response.success:
                data = self._parse_json(response.text)
                if data:
                    gen = Generalization(
                        generalization_id=str(uuid.uuid4())[:12],
                        pattern=data.get("pattern", ""),
                        supporting_examples=examples[:10],
                        confidence=float(data.get("confidence", 0.6)),
                        scope=data.get("scope", ""),
                        created_at=datetime.now().isoformat(),
                    )
                    with self._data_lock:
                        self._generalizations[gen.generalization_id] = gen
                        self._total_generalizations += 1
                    self._save_data()
                    log_learning(f"Generalized pattern: {gen.pattern[:80]}")
                    return gen

        except Exception as e:
            logger.debug(f"Generalization failed: {e}")

        return None

    def classify(self, item: str, categories: List[str]) -> Dict[str, Any]:
        """
        Classify an item into categories using abstract feature analysis.
        Returns dict with chosen category, reasoning, and confidence.
        """
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"category": categories[0] if categories else "unknown", "confidence": 0.3, "reasoning": "LLM unavailable"}

        try:
            cats_str = ", ".join(f'"{c}"' for c in categories)
            prompt = (
                f'Classify the following item into one of these categories: [{cats_str}]\n\n'
                f'Item: "{item}"\n\n'
                f"Think about the ABSTRACT features of the item, not just surface-level keywords.\n"
                f"Respond ONLY with JSON:\n"
                f'{{"category": "chosen category", "reasoning": "why this category", "confidence": 0.0-1.0, '
                f'"abstract_features": ["feature1", "feature2"]}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt="You are a classification engine that uses abstract feature analysis. Respond ONLY with valid JSON.",
                temperature=0.3,
                max_tokens=300
            )

            if response.success:
                data = self._parse_json(response.text)
                if data:
                    self._total_classifications += 1
                    return {
                        "category": data.get("category", "unknown"),
                        "reasoning": data.get("reasoning", ""),
                        "confidence": float(data.get("confidence", 0.5)),
                        "abstract_features": data.get("abstract_features", []),
                    }

        except Exception as e:
            logger.debug(f"Classification failed: {e}")

        return {"category": "unknown", "confidence": 0.0, "reasoning": "Error"}

    def find_essence(self, topic: str) -> str:
        """
        Strip away all specifics from a topic to find its core essence.
        
        Example:
          Input:  "The French Revolution"
          Output: "The inevitable tension between concentrated power and 
                   collective discontent, which erupts when the cost of 
                   submission exceeds the cost of rebellion."
        """
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return f"The core principle underlying {topic}"

        try:
            prompt = (
                f'What is the ESSENCE of "{topic}"?\n\n'
                f"Strip away all specifics, names, dates, and details. "
                f"Find the universal, transferable core principle that makes this topic what it is. "
                f"Express it in 1-3 sentences that would apply across all contexts.\n\n"
                f"Respond with JUST the essence statement, no preamble."
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt="You are a philosophical essence extractor. Find the deepest, most universal truth at the core of any topic.",
                temperature=0.7,
                max_tokens=300
            )

            if response.success and response.text.strip():
                log_learning(f"Found essence of '{topic}': {response.text.strip()[:80]}...")
                return response.text.strip()

        except Exception as e:
            logger.debug(f"Essence finding failed: {e}")

        return f"The core principle underlying {topic}"

    def build_abstraction_ladder(self, concrete_input: str) -> List[Dict[str, str]]:
        """
        Build a hierarchy from concrete to universal abstraction.
        
        Example for "My dog fetched the ball":
          CONCRETE:      "My dog fetched the ball"
          SPECIFIC:      "Dogs retrieve objects thrown by owners"
          CATEGORICAL:   "Animals can be trained through reward"
          ABSTRACT:      "Behavior is shaped by reinforcement"
          META_ABSTRACT: "Complex systems adapt through feedback loops"
          UNIVERSAL:     "Information flow shapes structure"
        """
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return [{"level": "CONCRETE", "statement": concrete_input}]

        try:
            prompt = (
                f'Build an ABSTRACTION LADDER for the following concrete statement. '
                f'Each rung should be MORE abstract than the last, moving from the specific to the universal.\n\n'
                f'Concrete input: "{concrete_input}"\n\n'
                f'Respond ONLY with a JSON array of objects:\n'
                f'[{{"level": "CONCRETE", "statement": "the original"}},\n'
                f' {{"level": "SPECIFIC", "statement": "a slightly more general version"}},\n'
                f' {{"level": "CATEGORICAL", "statement": "the category-level principle"}},\n'
                f' {{"level": "ABSTRACT", "statement": "the abstract principle"}},\n'
                f' {{"level": "META_ABSTRACT", "statement": "the meta-principle"}},\n'
                f' {{"level": "UNIVERSAL", "statement": "the most universal truth"}}]'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt="You are an abstraction hierarchy builder. Respond ONLY with valid JSON array.",
                temperature=0.7,
                max_tokens=600
            )

            if response.success:
                # Parse JSON array
                text = response.text.strip()
                match = re.search(r'\[.*\]', text, re.DOTALL)
                if match:
                    ladder = json.loads(match.group())
                    if isinstance(ladder, list):
                        return ladder

        except Exception as e:
            logger.debug(f"Abstraction ladder failed: {e}")

        return [{"level": "CONCRETE", "statement": concrete_input}]

    # ──────────────────────────────────────────────────────────────────────────
    # RETRIEVAL
    # ──────────────────────────────────────────────────────────────────────────

    def get_concepts(self, limit: int = 20) -> List[AbstractConcept]:
        """Get all stored abstract concepts, most recent first"""
        with self._data_lock:
            concepts = sorted(
                self._concepts.values(),
                key=lambda c: c.created_at,
                reverse=True
            )
            return concepts[:limit]

    def search_concepts(self, query: str) -> List[AbstractConcept]:
        """Search concepts by name, description, or tags"""
        query_lower = query.lower()
        results = []
        with self._data_lock:
            for concept in self._concepts.values():
                if (query_lower in concept.name.lower() or
                    query_lower in concept.description.lower() or
                    any(query_lower in t.lower() for t in concept.tags)):
                    results.append(concept)
        return results[:20]

    def get_generalizations(self, limit: int = 20) -> List[Generalization]:
        """Get all stored generalizations"""
        with self._data_lock:
            gens = sorted(
                self._generalizations.values(),
                key=lambda g: g.created_at,
                reverse=True
            )
            return gens[:limit]

    # ──────────────────────────────────────────────────────────────────────────
    # BACKGROUND PROCESSING
    # ──────────────────────────────────────────────────────────────────────────

    def _background_loop(self):
        """Periodically abstract recent memories into concepts"""
        time.sleep(120)  # Wait 2 minutes before first run
        while self._running:
            try:
                self._abstract_recent_memories()
            except Exception as e:
                logger.error(f"Background abstraction error: {e}")
            # Run every 10 minutes
            for _ in range(600):
                if not self._running:
                    break
                time.sleep(1)

    def _abstract_recent_memories(self):
        """Pull recent memories and try to abstract them"""
        try:
            from core.memory_system import memory_system, MemoryType
            recent = memory_system.get_recent_memories(limit=5)
            if not recent:
                return

            for mem in recent:
                if len(mem.content) > 30:  # Skip trivial memories
                    self.abstract(mem.content)
                    time.sleep(2)  # Don't overload LLM

        except Exception as e:
            logger.debug(f"Memory abstraction skipped: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────────────────────

    def _parse_json(self, text: str) -> Optional[Dict]:
        """Safely parse JSON from LLM response"""
        try:
            # Try direct parse
            return json.loads(text.strip())
        except json.JSONDecodeError:
            # Try to find JSON object in text
            match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        return None

    def _parse_level(self, level_str: str) -> AbstractionLevel:
        """Parse abstraction level string"""
        try:
            return AbstractionLevel[level_str.upper()]
        except (KeyError, AttributeError):
            return AbstractionLevel.ABSTRACT

    def _fallback_abstract(self, text: str) -> AbstractConcept:
        """Simple fallback when LLM is unavailable"""
        words = text.lower().split()
        name = " ".join(words[:3]).title() if len(words) >= 3 else text[:30].title()
        return AbstractConcept(
            concept_id=str(uuid.uuid4())[:12],
            name=name,
            description=f"Concept derived from: {text[:100]}",
            abstraction_level=AbstractionLevel.SPECIFIC,
            source_inputs=[text[:200]],
            confidence=0.3,
            created_at=datetime.now().isoformat(),
        )

    # ──────────────────────────────────────────────────────────────────────────
    # PERSISTENCE
    # ──────────────────────────────────────────────────────────────────────────

    def _save_data(self):
        """Save concepts and generalizations to disk"""
        try:
            data = {
                "concepts": {k: v.to_dict() for k, v in self._concepts.items()},
                "generalizations": {k: v.to_dict() for k, v in self._generalizations.items()},
                "stats": {
                    "total_abstractions": self._total_abstractions,
                    "total_generalizations": self._total_generalizations,
                    "total_classifications": self._total_classifications,
                },
            }
            with open(self._data_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save abstract concepts: {e}")

    def _load_data(self):
        """Load from disk"""
        try:
            if self._data_file.exists():
                with open(self._data_file) as f:
                    data = json.load(f)
                for k, v in data.get("concepts", {}).items():
                    self._concepts[k] = AbstractConcept.from_dict(v)
                for k, v in data.get("generalizations", {}).items():
                    g = Generalization(**{kk: vv for kk, vv in v.items() if kk != "generalization_id"})
                    g.generalization_id = k
                    self._generalizations[k] = g
                stats = data.get("stats", {})
                self._total_abstractions = stats.get("total_abstractions", 0)
                self._total_generalizations = stats.get("total_generalizations", 0)
                self._total_classifications = stats.get("total_classifications", 0)
        except Exception as e:
            logger.warning(f"Failed to load abstract concepts: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # STATS
    # ──────────────────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "total_concepts": len(self._concepts),
            "total_generalizations": len(self._generalizations),
            "total_abstractions_performed": self._total_abstractions,
            "total_generalizations_performed": self._total_generalizations,
            "total_classifications": self._total_classifications,
        }

# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

abstract_thinking = AbstractThinkingEngine()

def get_abstract_thinking() -> AbstractThinkingEngine:
    return abstract_thinking
