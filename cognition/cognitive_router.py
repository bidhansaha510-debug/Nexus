"""
NEXUS AI — Cognitive Router
Automatic intent detection, multi-method AGI engine routing, and engine chaining.

Architecture:
  • engine_registry.py  – declarative multi-method adapter table
  • intent_classifier.py – hybrid semantic + keyword + LLM intent detection
  • INTENT_PATTERNS     – word-boundary regex patterns (reduces false positives)
  • Engine Chaining     – pipelines where outputs feed into next engine
  • Per-engine metrics  – success/fail rate, avg latency
  • Thread-safe         – Lock protects mutable shared state
  • LRU result cache    – avoids re-running identical inputs

Intent Detection (3-layer hybrid):
  • Layer 1: Fast keyword scan (< 1ms) — catches explicit intent
  • Layer 2: Semantic similarity (< 50ms) — catches implicit intent
  • Layer 3: LLM classification — only when layers 1+2 are ambiguous
"""

import json
import re
import time
import hashlib
import threading
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional, Tuple, Set, Union, Literal
from dataclasses import dataclass, field
from datetime import datetime
from enum import auto, Enum

import sys
from pathlib import Path

from utils.logger import get_logger

# Import multi-method registry + chains
from cognition.engine_registry import (
    ENGINE_REGISTRY, ALL_ENGINE_KEYS, ENGINE_CHAINS,
    EngineAdapter, EngineMethod,
)

# Import hybrid intent classifier — DEFERRED to after INTENT_PATTERNS to avoid circular import
# (intent_classifier → KeywordDetector → needs INTENT_PATTERNS from this module)

logger = get_logger("cognitive_router")

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

MAX_ENGINES_PER_MESSAGE = 5
ENGINE_TIMEOUT = 6.0
MIN_MESSAGE_LENGTH = 5
COOLDOWN_MESSAGES = 3
LLM_FALLBACK_THRESHOLD = 2
MAX_INPUT_LENGTH = 2000
CACHE_MAX_SIZE = 64

# ═══════════════════════════════════════════════════════════════════════════════
# REASONING DEPTH
# ═══════════════════════════════════════════════════════════════════════════════

class ReasoningDepth(Enum):
    """Controls how many engines run and how thorough the analysis is."""
    SHALLOW = "shallow"   # 1-2 engines, fastest, keyword-only
    MEDIUM = "medium"     # 3-5 engines, default, hybrid detection
    DEEP = "deep"         # 5-8 engines, full semantic + LLM + auto-chain

DEPTH_CONFIG = {
    ReasoningDepth.SHALLOW: {
        "max_engines": 2,
        "skip_semantic": True,
        "skip_llm": True,
        "auto_chain": False,
    },
    ReasoningDepth.MEDIUM: {
        "max_engines": 5,
        "skip_semantic": False,
        "skip_llm": False,
        "auto_chain": False,
    },
    ReasoningDepth.DEEP: {
        "max_engines": 8,
        "skip_semantic": False,
        "skip_llm": False,
        "auto_chain": True,
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RoutingResult:
    """Result from a single engine invocation."""
    engine_name: str = ""
    method_name: str = ""
    insight: str = ""
    elapsed: float = 0.0
    success: bool = False
    error: str = ""
    confidence: float = 0.5  # Method confidence score (Tier 3 #8)

@dataclass
class RoutingTrace:
    """Structured trace of a routing decision for debugging and analysis."""
    input_hash: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    depth: str = "medium"
    keyword_scores: Dict[str, float] = field(default_factory=dict)
    semantic_scores: Dict[str, float] = field(default_factory=dict)
    llm_scores: Dict[str, float] = field(default_factory=dict)
    selected_engines: List[str] = field(default_factory=list)
    cooldown_overrides: Dict[str, str] = field(default_factory=dict)
    adaptive_adjustments: Dict[str, float] = field(default_factory=dict)
    chain_decision: str = ""
    dynamic_chain_built: bool = False
    results_summary: Dict[str, bool] = field(default_factory=dict)
    total_elapsed: float = 0.0

@dataclass
class CognitiveInsights:
    """Aggregated insights from all routed engines."""
    results: List[RoutingResult] = field(default_factory=list)
    engines_triggered: List[str] = field(default_factory=list)
    chain_used: str = ""
    total_elapsed: float = 0.0
    user_input: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    depth: str = "medium"
    synthesized_insight: str = ""
    trace: Optional[RoutingTrace] = None

    def to_context_string(self) -> str:
        """Format insights for injection into LLM context."""
        if not self.results:
            return ""

        lines = ["COGNITIVE INSIGHTS (auto-analyzed):"]
        for r in self.results:
            if r.success and r.insight:
                label = f"{r.engine_name}.{r.method_name}" if r.method_name else r.engine_name
                lines.append(f"  [{label}]: {r.insight}")

        if len(lines) <= 1:
            return ""

        if self.chain_used:
            lines.append(f"  [chain: {self.chain_used}]")

        # Add synthesized insight if available
        if self.synthesized_insight:
            lines.append(f"  [SYNTHESIS]: {self.synthesized_insight}")

        if self.depth != "medium":
            lines.append(f"  [depth: {self.depth}]")

        return "\n".join(lines)

# ═══════════════════════════════════════════════════════════════════════════════
# INSIGHT SYNTHESIZER
# ═══════════════════════════════════════════════════════════════════════════════

# Engine category mapping for synthesis grouping
_ENGINE_CATEGORIES = {
    "reasoning": ["causal", "logic", "probability", "hypothesis", "counterfactual", "dialectic"],
    "emotional": ["emotional", "emotional_reg", "mind", "social"],
    "creative": ["creative", "dream", "music", "visual", "conceptual_blend", "analogy_gen", "analogy"],
    "strategic": ["planning", "negotiation", "game_theory", "adversarial", "debate", "constraint", "systems", "synthesis"],
    "cognitive": ["attention", "working_memory", "self_model", "error_detect", "curiosity", "transfer", "perspective", "flexibility", "common_sense"],
    "philosophical": ["philosophy", "ethics", "wisdom", "moral_imagination", "narrative"],
    "other": ["spatial", "temporal", "knowledge", "intuition", "humor", "cultural", "linguistic"],
}

# Reverse lookup
_ENGINE_TO_CATEGORY: Dict[str, str] = {}
for _cat, _engines in _ENGINE_CATEGORIES.items():
    for _e in _engines:
        _ENGINE_TO_CATEGORY[_e] = _cat

# Cross-engine synthesis patterns
_SYNTHESIS_PATTERNS = {
    frozenset(["causal", "decision"]): "Root cause analysis leads to an actionable recommendation.",
    frozenset(["causal", "counterfactual"]): "Causal analysis combined with alternative scenario exploration.",
    frozenset(["emotional", "emotional_reg"]): "Emotional understanding paired with regulation strategies.",
    frozenset(["emotional", "wisdom"]): "Emotional awareness grounded in deeper wisdom.",
    frozenset(["logic", "error_detect"]): "Logical validation with error checking for robust reasoning.",
    frozenset(["creative", "analogy_gen"]): "Creative ideas explained through accessible analogies.",
    frozenset(["planning", "adversarial"]): "Strategic plan stress-tested for vulnerabilities.",
    frozenset(["philosophy", "ethics"]): "Philosophical inquiry with ethical grounding.",
    frozenset(["systems", "planning"]): "Systems-level understanding driving actionable planning.",
    frozenset(["hypothesis", "error_detect"]): "Hypotheses generated and critically evaluated.",
    frozenset(["perspective", "mind"]): "Multi-perspective analysis with theory of mind.",
    frozenset(["dialectic", "wisdom"]): "Dialectical exploration distilled into wisdom.",
    frozenset(["game_theory", "negotiation"]): "Game-theoretic analysis driving negotiation strategy.",
}

class InsightSynthesizer:
    """Template-based synthesis of cross-engine insights (no LLM call for speed)."""

    @staticmethod
    def synthesize(results: List[RoutingResult]) -> str:
        """Produce a synthesized summary from multiple engine results."""
        successful = [r for r in results if r.success and r.insight]
        if len(successful) < 2:
            return ""

        # 1. Group by category
        categories: Dict[str, List[RoutingResult]] = {}
        for r in successful:
            cat = _ENGINE_TO_CATEGORY.get(r.engine_name, "other")
            categories.setdefault(cat, []).append(r)

        parts = []

        # 2. Check for known cross-engine patterns
        engine_set = set(r.engine_name for r in successful)
        for pattern_engines, pattern_desc in _SYNTHESIS_PATTERNS.items():
            if pattern_engines.issubset(engine_set):
                parts.append(pattern_desc)
                break  # Only use first matching pattern

        # 3. Category-level summaries
        if len(categories) > 1:
            cat_names = [c for c in categories.keys() if c != "other"]
            if cat_names:
                parts.append(f"Multi-dimensional analysis across {', '.join(cat_names)} perspectives.")

        # 4. Detect potential conflicts (engines in different categories with competing conclusions)
        if len(categories) >= 2 and any(len(v) >= 2 for v in categories.values()):
            parts.append("Multiple converging insights strengthen overall confidence.")

        return " ".join(parts) if parts else ""

@dataclass
class MethodMetrics:
    """Per-method observability counters (Tier 2 #4)."""
    calls: int = 0
    successes: int = 0
    failures: int = 0
    total_latency: float = 0.0

    @property
    def avg_latency(self) -> float:
        return self.total_latency / max(1, self.calls)

    @property
    def success_rate(self) -> float:
        return self.successes / max(1, self.calls)

@dataclass
class EngineMetrics:
    """Per-engine observability counters."""
    calls: int = 0
    successes: int = 0
    failures: int = 0
    total_latency: float = 0.0
    method_metrics: Dict[str, MethodMetrics] = field(default_factory=dict)  # Tier 2 #4

    @property
    def avg_latency(self) -> float:
        return self.total_latency / max(1, self.calls)

    @property
    def failure_rate(self) -> float:
        return self.failures / max(1, self.calls)

# ═══════════════════════════════════════════════════════════════════════════════
# INTENT PATTERNS
# ═══════════════════════════════════════════════════════════════════════════════

INTENT_PATTERNS: List[Tuple[List[str], str, float]] = [
    # Causal Reasoning
    (["why did", "why does", "why is", "why are", "why would",
      "because of", "caused by", "root cause", "what led to",
      "consequence of", "effect of", "result of", "due to",
      "reason for", "what causes"],
     "causal", 1.0),

    # Decision Theory
    (["should i", "should we", "decide between", "decision",
      "choose between", "choice", "tradeoff", "trade-off",
      "pros and cons", "worth it", "better to", "which option"],
     "decision", 1.2),

    # Ethical Reasoning
    (["is it ethical", "morally", "moral dilemma", "right or wrong",
      "ethical to", "unethical", "moral obligation", "fairness of",
      "justice in", "ethical implications"],
     "ethics", 1.0),

    # Logical Reasoning
    (["logically", "valid argument", "logical fallacy",
      "syllogism", "if then", "therefore",
      "it follows that", "deduction", "induction",
      "prove that", "logical proof"],
     "logic", 0.8),

    # Probabilistic Reasoning
    (["probability of", "how likely", "chances of", "odds of",
      "percent chance", "statistical", "expected value",
      "risk of", "uncertainty about", "bayesian"],
     "probability", 0.9),

    # Hypothesis Engine
    (["hypothesis about", "theory about", "my theory is",
      "could it be that", "possible explanation",
      "what explains", "hypothesize", "test the idea"],
     "hypothesis", 0.8),

    # Counterfactual Reasoning
    (["what if", "what would have happened", "had i done",
      "if only", "imagine if", "alternate reality",
      "counterfactual", "could have been", "different outcome"],
     "counterfactual", 0.9),

    # Dialectical Reasoning
    (["both sides of", "thesis and antithesis", "on one hand",
      "opposing view", "counterpoint to", "steelman",
      "dialectical", "socratic questioning"],
     "dialectic", 0.8),

    # Philosophical Reasoning
    (["philosophically", "philosophical question", "existence of",
      "meaning of life", "consciousness is", "free will",
      "determinism", "metaphysics", "epistemology",
      "ontology", "existential question"],
     "philosophy", 0.8),

    # ── Intelligence Engines ──

    # Emotional Intelligence
    (["i feel", "i feel so", "i'm feeling", "emotionally", "my emotions",
      "i'm anxious", "i'm depressed", "i'm overwhelmed",
      "how to deal with my feelings", "emotional support"],
     "emotional", 0.8),

    # Emotional Regulation
    (["calm me down", "manage my anger", "control my emotions",
      "how to cope with", "self-care for", "regulate my",
      "emotional balance", "stress management"],
     "emotional_reg", 0.8),

    # Theory of Mind
    (["they might think", "from their perspective",
      "what are they feeling", "their point of view",
      "how would they react", "their intention",
      "understand them better"],
     "mind", 0.9),

    # Social Cognition
    (["social dynamics", "group dynamics", "social influence",
      "peer pressure", "social norm", "power dynamic",
      "being manipulated", "trust issue"],
     "social", 0.7),

    # Cultural Intelligence
    (["cultural context", "cross-cultural", "cultural tradition",
      "cultural etiquette", "multicultural", "intercultural",
      "globalization of", "cultural sensitivity"],
     "cultural", 0.7),

    # Linguistic Intelligence
    (["rephrase this", "rewrite this", "change the tone",
      "more formal", "less formal", "writing style",
      "rhetoric of", "persuasive writing"],
     "linguistic", 0.7),

    # Narrative Intelligence
    (["story about", "narrative of", "plot of",
      "character analysis", "tell me a story",
      "moral of the story", "narrative structure"],
     "narrative", 0.7),

    # Humor Intelligence
    (["tell me a joke", "that's funny", "humor in",
      "make me laugh", "pun about", "witty response",
      "comedy about", "hilarious"],
     "humor", 0.7),

    # Wisdom Engine
    (["wisdom about", "wise advice", "sage advice", "life lesson",
      "life advice", "long-term perspective", "big picture advice",
      "timeless wisdom"],
     "wisdom", 0.8),

    # ── Creative Engines ──

    # Creative Synthesis
    (["creative solution", "brainstorm", "innovative idea",
      "think outside the box", "creative approach",
      "original idea", "novel approach"],
     "creative", 0.8),

    # Dream Engine
    (["dream about", "surreal", "subconscious", "free associate",
      "stream of consciousness", "wild idea about",
      "let your mind wander"],
     "dream", 0.6),

    # Musical Cognition
    (["music about", "song about", "melody of", "rhythm of",
      "chord progression", "harmony in", "tempo of",
      "compose a", "symphony"],
     "music", 0.8),

    # Visual Imagination
    (["visualize this", "picture this", "diagram of",
      "imagine the scene", "mental image of", "illustration of"],
     "visual", 0.7),

    # Conceptual Blending
    (["combine these", "merge ideas", "blend concepts",
      "fuse together", "hybrid of", "cross between",
      "combination of", "mashup of"],
     "conceptual_blend", 0.8),

    # Analogy Generator
    (["analogy for", "explain like i'm five", "eli5",
      "in simple terms", "metaphor for",
      "think of it like"],
     "analogy_gen", 0.8),

    # Analogical Reasoning
    (["similar to", "compared to", "analogous to",
      "just like when", "reminds me of", "parallel to"],
     "analogy", 0.7),

    # ── Cognitive Engines ──

    # Attention Control
    (["can't focus on", "help me focus", "need to focus",
      "too distracted", "attention span", "prioritize my",
      "overwhelmed by tasks", "multitasking"],
     "attention", 0.7),

    # Working Memory
    (["remember this", "keep in mind", "earlier we discussed",
      "as i said before", "we discussed earlier", "don't forget that",
      "hold that thought"],
     "working_memory", 0.7),

    # Self-Model
    (["can you do", "are you able to", "your capability",
      "your limitation", "what are you", "who are you"],
     "self_model", 0.6),

    # Error Detection
    (["find errors in", "mistake in", "what's wrong with",
      "bug in", "inconsistency in", "incorrect",
      "check this for errors", "verify this", "fact check this",
      "is this correct"],
     "error_detect", 1.0),

    # Curiosity Drive
    (["i'm curious about", "i wonder", "that's interesting",
      "explore this", "dig deeper into", "tell me more about",
      "what else about", "fascinating"],
     "curiosity", 0.6),

    # Transfer Learning
    (["apply this to", "transfer knowledge", "use in another context",
      "cross-domain", "from one field to another",
      "leverage what i know", "apply what i know"],
     "transfer", 0.7),

    # Perspective Taking
    (["from their perspective", "in their shoes", "how would they feel",
      "empathize with", "see it from their side", "other side of",
      "their viewpoint"],
     "perspective", 0.9),

    # Cognitive Flexibility
    (["alternatively", "different perspective", "another way to look",
      "flip it", "reverse thinking", "paradigm shift",
      "think differently"],
     "flexibility", 0.7),

    # Common Sense
    (["common sense", "obviously", "everyone knows", "is it plausible",
      "realistic to", "practical to"],
     "common_sense", 0.5),

    # ── Strategic Engines ──

    # Planning
    (["make a plan for", "steps to", "action plan",
      "roadmap for", "how do i start", "project plan",
      "strategy for", "break this down"],
     "planning", 0.9),

    # Negotiation Intelligence
    (["negotiate with", "negotiation strategy", "bargain for",
      "compromise on", "make a deal", "persuade them",
      "convince them", "mediate between", "settlement for"],
     "negotiation", 0.9),

    # Game Theory
    (["game theory", "strategic move", "nash equilibrium",
      "zero-sum game", "prisoner's dilemma", "payoff matrix",
      "dominant strategy", "minimax", "competitive advantage"],
     "game_theory", 0.9),

    # Adversarial Thinking
    (["red team this", "attack vector", "vulnerability in",
      "weakness of", "exploit in", "defense against",
      "adversarial", "threat model", "security of",
      "penetration test", "stress test this", "premortem"],
     "adversarial", 0.9),

    # Debate Engine
    (["debate this", "argue for", "make a case for",
      "build an argument", "counter-argument",
      "rebuttal to", "structured debate"],
     "debate", 0.8),

    # Constraint Solver
    (["constraint", "resource limit", "optimize for",
      "is it feasible", "schedule under", "allocate resources",
      "best allocation"],
     "constraint", 0.7),

    # Systems Thinking
    (["complex system", "interconnected", "ecosystem",
      "feedback loop", "emergence", "systemic",
      "ripple effect", "unintended consequence",
      "leverage point", "vicious cycle"],
     "systems", 0.8),

    # Information Synthesis
    (["summarize this", "synthesize these", "combine this information",
      "executive summary", "boil down to", "distill this",
      "key takeaways", "bottom line is"],
     "synthesis", 0.8),

    # ── Remaining ──

    # Spatial Reasoning
    (["where is", "layout of", "spatial", "navigate to",
      "distance between", "position of", "direction to"],
     "spatial", 0.7),

    # Temporal Reasoning
    (["how long will", "timeline of", "when did",
      "sequence of events", "schedule for", "duration of",
      "chronological"],
     "temporal", 0.7),

    # Knowledge Integration
    (["connection between", "how does x relate to y",
      "interdisciplinary", "knowledge graph",
      "synthesize domains", "connect the dots"],
     "knowledge", 0.7),

    # Intuition Engine
    (["gut feeling", "instinct says", "something feels off",
      "i have a hunch", "my intuition", "vibe of",
      "sixth sense"],
     "intuition", 0.6),

    # Moral Imagination
    (["envision a better", "ideal world", "moral imagination",
      "ethical future", "how things should be", "moral vision",
      "flourishing society"],
     "moral_imagination", 0.8),

    # ── Ultimate Advancement Engines ──

    # Quantum Cognition
    (["superposition", "quantum reasoning", "all possibilities",
      "multiple hypotheses", "entangle", "hidden correlation",
      "collapse the possibilities", "tunnel through"],
     "quantum_cognition", 0.9),

    # Swarm Intelligence
    (["collective intelligence", "swarm solve", "crowd wisdom",
      "hive mind", "panel of experts", "committee discussion",
      "stigmergy", "emergent solution"],
     "swarm", 0.8),

    # Temporal Prophecy
    (["predict the future", "future scenario", "what will happen next",
      "black swan", "branching futures", "tipping point",
      "inflection point", "convergence of trends"],
     "prophecy", 0.9),

    # Adversarial Evolution
    (["evolve this idea", "anti-fragile", "harden this",
      "mutation test", "survival of fittest", "tournament selection",
      "immune response", "stress evolve"],
     "evolution", 0.8),

    # Cross-Dimensional Reasoning
    (["multi-dimensional analysis", "hypercube", "fractal pattern",
      "self-similar", "dimensional bridge", "cross-domain structure",
      "N-dimensional", "simplify complexity"],
     "cross_dimensional", 0.8),

    # Existential Calculus
    (["resolve paradox", "self-referential", "godel",
      "incompleteness", "strange loop", "tangled hierarchy",
      "koan", "unanswerable question", "dissolve the question"],
     "existential", 0.9),
]

# Pre-compile word-boundary regexes for fast matching
_COMPILED_PATTERNS: List[Tuple[List['re.Pattern'], str, float]] = []
for _pats, _key, _weight in INTENT_PATTERNS:
    _compiled = [re.compile(r'\b' + re.escape(p) + r'\b', re.IGNORECASE) for p in _pats]
    _COMPILED_PATTERNS.append((_compiled, _key, _weight))

# Pre-compile sub-patterns from the registry for method selection
_COMPILED_SUB_PATTERNS: Dict[str, List[Tuple[List['re.Pattern'], int]]] = {}
for _ekey, _adapter in ENGINE_REGISTRY.items():
    _method_patterns = []
    for _midx, _method in enumerate(_adapter.methods):
        if _method.sub_patterns:
            _compiled_subs = [re.compile(r'\b' + re.escape(p) + r'\b', re.IGNORECASE) for p in _method.sub_patterns]
            _method_patterns.append((_compiled_subs, _midx))
    _COMPILED_SUB_PATTERNS[_ekey] = _method_patterns

# Pre-compile chain patterns
_COMPILED_CHAIN_PATTERNS: Dict[str, List['re.Pattern']] = {}
for _cname, _cdata in ENGINE_CHAINS.items():
    _COMPILED_CHAIN_PATTERNS[_cname] = [
        re.compile(r'\b' + re.escape(p) + r'\b', re.IGNORECASE) for p in _cdata["patterns"]
    ]

# NOW import intent_classifier (safe because INTENT_PATTERNS is defined above)
from cognition.intent_classifier import intent_classifier, ScoredIntent

# ═══════════════════════════════════════════════════════════════════════════════
# LRU CACHE
# ═══════════════════════════════════════════════════════════════════════════════

class _LRUCache:
    """Thread-safe bounded LRU cache for CognitiveInsights."""

    def __init__(self, maxsize: int = CACHE_MAX_SIZE):
        self._data: OrderedDict[str, CognitiveInsights] = OrderedDict()
        self._maxsize = maxsize
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[CognitiveInsights]:
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
                return self._data[key]
        return None

    def put(self, key: str, value: CognitiveInsights):
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
            else:
                if len(self._data) >= self._maxsize:
                    self._data.popitem(last=False)
            self._data[key] = value

    @staticmethod
    def make_key(text: str) -> str:
        normalized = text.strip().lower()[:500]
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

# ═══════════════════════════════════════════════════════════════════════════════
# ENGINE RUNNER  (multi-method aware)
# ═══════════════════════════════════════════════════════════════════════════════

# Thread-local storage for method metrics access in _select_method
_method_metrics_ref: Dict[str, EngineMetrics] = {}

def _select_method(engine_key: str, user_input: str) -> int:
    """Pick the best method index for this engine based on sub-pattern matching.

    Uses historical method success rates (Tier 3 #9) as a tie-breaker
    when multiple methods match equally well.
    """
    method_patterns = _COMPILED_SUB_PATTERNS.get(engine_key, [])
    adapter = ENGINE_REGISTRY[engine_key]
    best_idx = adapter.default
    best_score = 0.0
    best_reliability = 0.0

    for compiled_subs, method_idx in method_patterns:
        score = float(sum(1 for pat in compiled_subs if pat.search(user_input)))
        if score > 0:
            # Tier 3 #9: Apply historical success rate as tie-breaker
            reliability = 0.5  # neutral default
            em = _method_metrics_ref.get(engine_key)
            if em:
                method_name = adapter.methods[method_idx].name
                mm = em.method_metrics.get(method_name)
                if mm and mm.calls >= 5:
                    reliability = float(mm.success_rate) if isinstance(getattr(mm, 'success_rate', 0.5), (int, float)) else 0.5
                    # Deprioritize unreliable methods
                    if reliability < 0.4:
                        score -= 1.0
                    elif reliability > 0.7:
                        score += 0.5  # slight boost for reliable methods

            if score > best_score or (score == best_score and reliability > best_reliability):
                best_score = score
                best_idx = method_idx
                best_reliability = reliability

    return best_idx

def _check_engine_available(engine_key: str, cognition) -> bool:
    """Verify an engine is actually loaded on the cognition instance (Tier 2 #5)."""
    adapter = ENGINE_REGISTRY.get(engine_key)
    if not adapter or not adapter.methods:
        return False
    # Check if the engine attribute exists by trying the first method's invoke path
    # Engine methods follow the pattern c.engine_attr.method_name(i)
    try:
        method = adapter.methods[0]
        # Extract engine attribute name from the invoke lambda
        # All invokes follow: lambda c, i: c.<engine_attr>.<method>(...)
        # We test by calling invoke with None input to see if the attribute exists
        # Instead, just check if the engine attribute exists via registry mapping
        # Most engine keys map to cognition attributes with predictable names
        method.invoke(cognition, "__availability_check__")
        return True  # If it doesn't raise AttributeError, the engine is loaded
    except AttributeError:
        return False
    except Exception:
        return True  # Other errors mean the engine IS loaded but failed for other reasons

def _run_engine(engine_key: str, user_input: str, cognition, method_idx: int = -1) -> RoutingResult:
    """Run a single engine method via the registry and return a concise insight."""
    adapter = ENGINE_REGISTRY.get(engine_key)
    if not adapter:
        return RoutingResult(engine_name=engine_key, success=False, error="unknown engine")

    # Select method: explicit index or auto-detect
    if method_idx < 0:
        method_idx = _select_method(engine_key, user_input)

    method_idx = min(method_idx, len(adapter.methods) - 1)
    method = adapter.methods[method_idx]

    start = time.time()
    try:
        raw = method.invoke(cognition, user_input)
        insight = method.format_result(raw)
        elapsed = time.time() - start

        # Tier 3 #8: Extract confidence from result if available
        confidence = 0.5
        if isinstance(raw, dict):
            confidence = float(raw.get("confidence", 0.5))
        elif hasattr(raw, "confidence"):
            confidence = float(getattr(raw, "confidence", 0.5))

        return RoutingResult(
            engine_name=engine_key, method_name=method.name,
            insight=insight, elapsed=elapsed, success=bool(insight),
            confidence=confidence
        )
    except Exception as e:
        elapsed = time.time() - start
        logger.debug(f"Engine {engine_key}.{method.name} failed: {e}")
        return RoutingResult(
            engine_name=engine_key, method_name=method.name,
            elapsed=elapsed, success=False, error=str(e),
            confidence=0.0
        )

# ═══════════════════════════════════════════════════════════════════════════════
# COGNITIVE ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

class CognitiveRouter:
    """
    Automatic intent detection, multi-method AGI engine routing, and chaining.

    Analyzes user messages via keyword matching + LLM fallback,
    selects 1-5 most relevant engines (picking the best method per engine),
    runs them in parallel, and optionally chains engine pipelines
    where outputs feed into next engine.
    """

    _instance = None
    _cls_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._cls_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._running = False
        self._executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="agi-route")

        # Mutable state — all guarded by _state_lock
        self._state_lock = threading.Lock()
        self._recent_engines: List[str] = []
        self._recent_intents: List[set] = []  # Recent intent sets for topic continuity
        self._total_routes = 0
        self._total_insights = 0
        self._total_chains = 0
        self._total_dynamic_chains = 0
        self._metrics: Dict[str, EngineMetrics] = {k: EngineMetrics() for k in ENGINE_REGISTRY}

        # LRU result cache
        self._cache = _LRUCache(CACHE_MAX_SIZE)

        # Routing traces ring buffer
        self._traces: List[RoutingTrace] = []
        self._max_traces = 100

        self._llm = None  # Lazy loaded
        self._synthesizer = InsightSynthesizer()

        logger.info(f"✅ Cognitive Router initialized ({len(ENGINE_REGISTRY)} engines, "
                     f"{sum(len(a.methods) for a in ENGINE_REGISTRY.values())} methods, "
                     f"{len(ENGINE_CHAINS)} chains)")

    def start(self):
        self._running = True
        logger.info("🧭 Cognitive Router started — automatic AGI routing active")

    def stop(self):
        self._running = False
        self._executor.shutdown(wait=False)
        logger.info("🧭 Cognitive Router stopped")

    # ──────────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────────────

    def route(self, user_input: str, cognition, depth: str = "medium") -> CognitiveInsights:
        """Analyze user input and automatically route to relevant AGI engines.
        
        Args:
            user_input: The user's message text
            cognition: The cognition system instance
            depth: Reasoning depth - "shallow", "medium", or "deep"
        """
        if not self._running:
            return CognitiveInsights(user_input=user_input, depth=depth)

        # Parse depth
        try:
            reasoning_depth = ReasoningDepth(depth)
        except ValueError:
            reasoning_depth = ReasoningDepth.MEDIUM
        depth_cfg = DEPTH_CONFIG[reasoning_depth]

        user_input = self._sanitize_input(user_input)

        if len(user_input) < MIN_MESSAGE_LENGTH:
            return CognitiveInsights(user_input=user_input, depth=depth)

        # Check cache
        cache_key = _LRUCache.make_key(user_input + depth)
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.debug(f"🧭 Cache hit for input (key={cache_key[:8]}…)")
            return cached

        start_time = time.time()

        # Initialize trace
        trace = RoutingTrace(
            input_hash=cache_key[:12],
            depth=depth,
        )

        # 0. Check for engine chains first (skip in SHALLOW mode)
        if reasoning_depth != ReasoningDepth.SHALLOW:
            chain_name = self._detect_chain(user_input)
            if chain_name:
                trace.chain_decision = f"matched:{chain_name}"
                insights = self._run_chain(chain_name, user_input, cognition)
                if insights and insights.results:
                    insights.total_elapsed = time.time() - start_time
                    insights.depth = depth
                    insights.synthesized_insight = self._synthesizer.synthesize(insights.results)
                    insights.trace = trace
                    trace.total_elapsed = insights.total_elapsed
                    self._record_trace(trace)
                    self._cache.put(cache_key, insights)
                    with self._state_lock:
                        self._total_routes += 1
                        self._total_chains += 1
                    return insights

        # 1. Hybrid intent detection (depth-aware)
        scored_intents = intent_classifier.detect(user_input)

        # Record intent scores in trace
        for si in scored_intents[:10]:
            if "keyword" in si.method:
                trace.keyword_scores[si.engine_key] = round(si.score, 3)
            elif "semantic" in si.method:
                trace.semantic_scores[si.engine_key] = round(si.score, 3)
            elif "llm" in si.method:
                trace.llm_scores[si.engine_key] = round(si.score, 3)

        # Convert ScoredIntent to tuple format for compatibility
        scored_engines = [(intent.engine_key, intent.score) for intent in scored_intents]

        if not scored_engines:
            return CognitiveInsights(user_input=user_input, depth=depth)

        # 2. Apply adaptive scoring based on engine metrics (Tier 2 #5)
        scored_engines = self._adaptive_score_boost(scored_engines)

        # 3. Select top engines (with context-aware cooldown, depth-aware max)
        current_intents = set(ek for ek, _ in scored_engines[:10])
        selected = self._select_engines(scored_engines, depth_cfg["max_engines"], current_intents, trace)

        if not selected:
            return CognitiveInsights(user_input=user_input, depth=depth)

        with self._state_lock:
            self._total_routes += 1
        trace.selected_engines = selected
        logger.info(f"🧭 Routing to engines [{depth}]: {', '.join(selected)}")

        # 4. Check for dynamic chain opportunities (Tier 2 #6)
        from cognition.engine_registry import ENGINE_DEPENDENCIES
        chain_engines, parallel_engines = self._build_dynamic_chain(selected)

        results = []
        if chain_engines:
            trace.dynamic_chain_built = True
            logger.info(f"🔗 Dynamic chain: {' → '.join(chain_engines)}")
            # Run chain sequentially
            context = user_input
            for key in chain_engines:
                result = _run_engine(key, context, cognition)
                results.append(result)
                if result.success and result.insight:
                    context = f"{user_input}\n\n[Previous insight from {key}]: {result.insight}"
            with self._state_lock:
                self._total_dynamic_chains += 1

        # Run remaining engines in parallel
        if parallel_engines:
            parallel_results = self._run_parallel(parallel_engines, user_input, cognition)
            results.extend(parallel_results)

        # 5. Update cooldown tracker & metrics (thread-safe)
        successful = [r for r in results if r.success]
        with self._state_lock:
            self._recent_engines = (selected + self._recent_engines)[
                :COOLDOWN_MESSAGES * MAX_ENGINES_PER_MESSAGE
            ]
            self._recent_intents = ([current_intents] + self._recent_intents)[:COOLDOWN_MESSAGES]
            self._total_insights += len(successful)

            for r in results:
                m = self._metrics.get(r.engine_name)
                if m:
                    m.calls += 1
                    m.total_latency += r.elapsed
                    if r.success:
                        m.successes += 1
                    else:
                        m.failures += 1
                    # Tier 2 #4: Per-method metrics
                    if r.method_name:
                        if r.method_name not in m.method_metrics:
                            m.method_metrics[r.method_name] = MethodMetrics()
                        mm = m.method_metrics[r.method_name]
                        mm.calls += 1
                        mm.total_latency += r.elapsed
                        if r.success:
                            mm.successes += 1
                        else:
                            mm.failures += 1

        total_elapsed = time.time() - start_time

        # 6. Synthesize insights
        synthesized = self._synthesizer.synthesize(results)

        # 7. Build final result
        trace.results_summary = {r.engine_name: r.success for r in results}
        trace.total_elapsed = total_elapsed
        self._record_trace(trace)

        insights = CognitiveInsights(
            results=results,
            engines_triggered=selected,
            total_elapsed=total_elapsed,
            user_input=user_input,
            depth=depth,
            synthesized_insight=synthesized,
            trace=trace,
        )

        self._cache.put(cache_key, insights)
        return insights

    def _record_trace(self, trace: RoutingTrace):
        """Add a trace to the ring buffer."""
        with self._state_lock:
            self._traces.append(trace)
            if len(self._traces) > self._max_traces:
                keep = len(self._traces) - self._max_traces
                self._traces = [t for i, t in enumerate(self._traces) if i >= keep]

    def get_recent_traces(self, count: int = 10) -> List[RoutingTrace]:
        """Get the most recent routing traces."""
        with self._state_lock:
            keep = max(0, len(self._traces) - count)
            return [t for i, t in enumerate(self._traces) if i >= keep]

    # ──────────────────────────────────────────────────────────────────────────
    # INPUT SANITIZATION
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _sanitize_input(text: str) -> str:
        """Truncate oversized input and strip control characters."""
        text = text[:MAX_INPUT_LENGTH]
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        return text.strip()

    # ──────────────────────────────────────────────────────────────────────────
    # ENGINE CHAINING
    # ──────────────────────────────────────────────────────────────────────────

    def _detect_chain(self, user_input: str) -> Optional[str]:
        """Check if user input matches an engine chain pattern."""
        for chain_name, compiled_pats in _COMPILED_CHAIN_PATTERNS.items():
            if any(pat.search(user_input) for pat in compiled_pats):
                return chain_name
        return None

    def _run_chain(self, chain_name: str, user_input: str, cognition) -> CognitiveInsights:
        """Run an engine chain: each engine's output feeds as context to the next."""
        chain = ENGINE_CHAINS[chain_name]
        engine_keys = chain["engines"]
        results = []
        context = user_input

        logger.info(f"🔗 Running chain '{chain_name}': {' → '.join(engine_keys)}")

        for key in engine_keys:
            result = _run_engine(key, context, cognition)
            results.append(result)

            # Feed successful insight as additional context
            if result.success and result.insight:
                context = f"{user_input}\n\n[Previous insight from {key}]: {result.insight}"

        with self._state_lock:
            for r in results:
                m = self._metrics.get(r.engine_name)
                if m:
                    m.calls += 1
                    m.total_latency += r.elapsed
                    if r.success:
                        m.successes += 1
                    else:
                        m.failures += 1

        return CognitiveInsights(
            results=results,
            engines_triggered=engine_keys,
            chain_used=chain_name,
            user_input=user_input,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # INTENT DETECTION
    # ──────────────────────────────────────────────────────────────────────────

    def _detect_intent(self, user_input: str) -> List[Tuple[str, float]]:
        """Word-boundary regex intent detection."""
        scores: Dict[str, float] = {}

        for compiled_patterns, engine_key, weight in _COMPILED_PATTERNS:
            match_count = sum(1 for pat in compiled_patterns if pat.search(user_input))
            if match_count > 0:
                scores[engine_key] = match_count * weight

        return sorted(scores.items(), key=lambda x: x[1], reverse=True)

    def _select_engines(
        self,
        scored: List[Tuple[str, float]],
        max_engines: int = MAX_ENGINES_PER_MESSAGE,
        current_intents: Optional[Set[str]] = None,
        trace: Optional[RoutingTrace] = None,
    ) -> List[str]:
        """Select top N engines with context-aware cooldown and adaptive scoring."""
        selected = []
        with self._state_lock:
            recent_snapshot = list(self._recent_engines)
            recent_intents_snapshot = list(self._recent_intents)

        # Calculate topic continuity score
        continuity = self._topic_continuity_score(current_intents, recent_intents_snapshot)

        for engine_key, score in scored:
            if len(selected) >= max_engines:
                break

            recent_count = recent_snapshot.count(engine_key)

            # Context-aware cooldown (Tier 2 #4)
            if recent_count >= COOLDOWN_MESSAGES:
                # If topic is continuing and this engine is relevant, relax cooldown
                if continuity > 0.4 and isinstance(current_intents, set) and engine_key in current_intents:
                    # Allow the engine through with reduced threshold
                    effective_cooldown = COOLDOWN_MESSAGES + 2  # Relaxed by 2
                    if recent_count >= effective_cooldown:
                        if trace:
                            getattr(trace, "cooldown_overrides", {})[engine_key] = f"blocked (count={recent_count}, continuity={continuity:.2f})"
                        continue
                    else:
                        if trace:
                            getattr(trace, "cooldown_overrides", {})[engine_key] = f"relaxed (count={recent_count}, continuity={continuity:.2f})"
                else:
                    if trace:
                        getattr(trace, "cooldown_overrides", {})[engine_key] = f"blocked (count={recent_count})"
                    continue

            selected.append(engine_key)

        return selected

    def _topic_continuity_score(self, current_intents: Optional[Set[str]], recent_intents: List[Set[str]]) -> float:
        """Score 0-1 indicating how much the current topic continues from recent queries."""
        if not current_intents or not recent_intents:
            return 0.0

        # Compare against the most recent intent set
        most_recent = recent_intents[0] if recent_intents else set()
        if not most_recent:
            return 0.0

        # Type guard for current_intents to ensure it's a valid set against the expected typed intersection and unions below
        valid_intents = current_intents if isinstance(current_intents, set) else set()

        overlap = len(valid_intents & most_recent)
        total = len(valid_intents | most_recent)
        return overlap / max(1, total)  # Jaccard similarity

    def _adaptive_score_boost(self, scored: List[Tuple[str, float]]) -> List[Tuple[str, float]]:
        """Adjust engine scores based on historical metrics (Tier 2 #5)."""
        adjusted = []
        with self._state_lock:
            for engine_key, score in scored:
                m = self._metrics.get(engine_key)
                if m and m.calls >= 5:  # Only activate with enough data
                    boost = 1.0
                    # Penalize high-failure engines
                    if m.failure_rate > 0.5:
                        boost *= 0.7
                    # Penalize slow engines
                    if m.avg_latency > 4.0:
                        boost *= 0.8
                    # Reward reliable fast engines
                    if m.failure_rate < 0.2 and m.avg_latency < 1.0:
                        boost *= 1.1
                    adjusted.append((engine_key, score * boost))
                else:
                    adjusted.append((engine_key, score))

        # Re-sort by adjusted score
        adjusted.sort(key=lambda x: x[1], reverse=True)
        return adjusted

    def _build_dynamic_chain(self, selected: List[str]) -> Tuple[List[str], List[str]]:
        """Build ad-hoc chain from dependency graph; returns (chain_engines, parallel_engines).
        
        Uses centralized get_execution_order() from engine_registry for
        topologically-correct sequencing. Engines with active dependencies
        among the selected set run sequentially; the rest run in parallel.
        """
        if not selected or len(selected) < 2:
            return [], selected

        from cognition.engine_registry import ENGINE_DEPENDENCIES, get_execution_order

        # Identify engines that have dependency relationships within the selected set
        chained_set = set()
        for engine_key in selected:
            deps = getattr(ENGINE_DEPENDENCIES, "get", lambda x, y: [])(engine_key, [])
            if any(dep in selected for dep in deps):
                chained_set.add(engine_key)
                for dep in deps:
                    if dep in selected:
                        chained_set.add(dep)

        if not chained_set:
            return [], selected

        # Use centralized topological sort for correct ordering
        chain_order = get_execution_order(list(chained_set))
        parallel = [e for e in selected if e not in chained_set]
        return chain_order, parallel

    # ──────────────────────────────────────────────────────────────────────────
    # PARALLEL EXECUTION
    # ──────────────────────────────────────────────────────────────────────────

    def _run_parallel(self, engine_keys: List[str], user_input: str, cognition) -> List[RoutingResult]:
        """Run selected engines in parallel with timeout; cancel stragglers."""
        results = []
        futures = {}

        for key in engine_keys:
            future = self._executor.submit(_run_engine, key, user_input, cognition)
            futures[future] = key

        for future in as_completed(futures, timeout=ENGINE_TIMEOUT + 1):
            try:
                result = future.result(timeout=ENGINE_TIMEOUT)
                results.append(result)
            except Exception as e:
                key = futures[future]
                logger.debug(f"Engine {key} timed out or failed: {e}")
                results.append(RoutingResult(
                    engine_name=key, success=False, error=f"timeout/error: {e}"
                ))

        # Cancel any futures that have not completed
        for future in futures:
            if not future.done():
                future.cancel()

        return results

    # ──────────────────────────────────────────────────────────────────────────
    # LLM FALLBACK
    # ──────────────────────────────────────────────────────────────────────────

    def _llm_detect_intent(self, user_input: str) -> List[str]:
        """LLM-based intent detection fallback."""
        try:
            if self._llm is None:
                from llm.llama_interface import llm as _llm
                self._llm = _llm

            if not self._llm.is_connected:
                return []

            engine_list = ", ".join(ALL_ENGINE_KEYS)

            response = self._llm.generate(
                prompt=(
                    f"Given this user message, pick the 1-3 most relevant cognitive engine keys "
                    f"from the following list. Respond ONLY with a JSON array of strings, nothing else.\n\n"
                    f"ENGINE KEYS: {engine_list}\n\n"
                    f"USER MESSAGE: \"{user_input}\"\n\n"
                    f"Respond with ONLY a JSON array like [\"key1\", \"key2\"]. No explanation."
                ),
                system_prompt="You are an intent classifier. Respond ONLY with a JSON array of engine key strings.",
                temperature=0.1,
                max_tokens=80,
            )

            if response.success:
                text = response.text.strip()
                match = re.search(r'\[.*?\]', text, re.DOTALL)
                if match:
                    try:
                        keys = json.loads(match.group())
                    except json.JSONDecodeError:
                        keys = []
                    valid = [str(k) for k in keys if isinstance(k, str) and k in ENGINE_REGISTRY] if isinstance(keys, list) else []
                    if valid:
                        logger.info(f"🧠 LLM intent detection picked: {', '.join(valid)}")
                        return [v for i, v in enumerate(valid) if i < 3]

        except Exception as e:
            logger.debug(f"LLM intent detection failed: {e}")

        return []

    # ──────────────────────────────────────────────────────────────────────────
    # STATS / OBSERVABILITY
    # ──────────────────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        with self._state_lock:
            # Materializing sorted metrics as a fully-typed list instead of allowing generator returns across generic boundaries
            sorted_by_calls = sorted(
                self._metrics.items(),
                key=lambda kv: float(getattr(kv[1], "calls", 0)),
                reverse=True,
            )
            top_engines = [kv for i, kv in enumerate(sorted_by_calls) if i < 5]

            worst_engines_list = list((k, m) for k, m in self._metrics.items() if float(getattr(m, "calls", 0)) >= 3)
            worst_sorted = sorted(
                worst_engines_list,
                key=lambda kv: float(getattr(kv[1], "failure_rate", 0.0)),
                reverse=True,
            )
            worst_engines = [kv for i, kv in enumerate(worst_sorted) if i < 5]

            # Reliability scores
            reliable_engines_list = list((k, m) for k, m in self._metrics.items() if float(getattr(m, "calls", 0)) >= 5)
            reliable_sorted = sorted(
                reliable_engines_list,
                key=lambda kv: (1.0 - float(getattr(kv[1], "failure_rate", 0.0))) / max(0.1, float(getattr(kv[1], "avg_latency", 0.1))),
                reverse=True,
            )
            reliable_engines = [kv for i, kv in enumerate(reliable_sorted) if i < 5]

            total_methods = sum(len(a.methods) for a in ENGINE_REGISTRY.values())

            # Get intent classifier stats
            classifier_stats = intent_classifier.get_stats()

            return {
                "running": self._running,
                "total_routes": self._total_routes,
                "total_insights": self._total_insights,
                "total_chains": self._total_chains,
                "total_dynamic_chains": self._total_dynamic_chains,
                "recent_engines": self._recent_engines[:6],
                "registered_engines": len(ENGINE_REGISTRY),
                "registered_methods": total_methods,
                "registered_chains": len(ENGINE_CHAINS),
                "intent_classifier": classifier_stats,
                "top_engines": [
                    {"key": k, "calls": m.calls, "avg_latency": round(m.avg_latency, 3)}
                    for k, m in top_engines
                ],
                "worst_failure_rate": [
                    {"key": k, "failure_rate": round(m.failure_rate, 3), "calls": m.calls}
                    for k, m in worst_engines
                ],
                "most_reliable": [
                    {"key": k, "reliability": round(1 - m.failure_rate, 3), "avg_latency": round(m.avg_latency, 3)}
                    for k, m in reliable_engines
                ],
                "recent_traces": len(self._traces),
            }

# Singleton
cognitive_router = CognitiveRouter()
