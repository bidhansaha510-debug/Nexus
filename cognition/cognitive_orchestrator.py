"""
NEXUS AI — Cognitive Orchestrator
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The AGI brain's deliberation system. Instead of running engines
independently and appending their outputs, the orchestrator implements
a true multi-engine *deliberation round*:

  1. PERCEIVE  — classify the query and select relevant engine groups
  2. PROPOSE   — each engine group generates a proposal (insight + confidence)
  3. CRITIQUE  — proposals are cross-evaluated for conflicts & gaps
  4. SYNTHESIZE — merge proposals into a unified cognitive context
  5. COMMIT    — produce a single, coherent context block for the LLM

This replaces the "bag of insights" approach with genuine cognitive
integration — engines collaborate, challenge each other, and converge
on a unified understanding.

Architecture:
  • Uses the existing CognitionSystem facade for engine access
  • Uses the existing CognitiveRouter for intent detection
  • Adds a deliberation layer ON TOP of routing
  • Thread-safe, singleton pattern consistent with NEXUS conventions
"""

import threading
import time
import hashlib
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.logger import get_logger
from config import NEXUS_CONFIG, DATA_DIR

logger = get_logger("cognitive_orchestrator")


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

ORCHESTRATOR_TIMEOUT = 8.0          # Max seconds for entire deliberation
PROPOSAL_TIMEOUT = 4.0              # Max seconds per engine proposal
MAX_PROPOSALS = 6                   # Max engine groups to consult
MIN_CONFIDENCE_THRESHOLD = 0.3      # Below this, proposals are discarded
SYNTHESIS_CONFLICT_THRESHOLD = 0.4  # Disagreement level that triggers deeper analysis
HISTORY_FILE = DATA_DIR / "orchestrator_history.json"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

class DeliberationPhase(Enum):
    PERCEIVE = "perceive"
    PROPOSE = "propose"
    CRITIQUE = "critique"
    SYNTHESIZE = "synthesize"
    COMMIT = "commit"


@dataclass
class Proposal:
    """A single engine group's proposal during deliberation."""
    engine_group: str           # e.g., "reasoning", "emotional", "creative"
    engines_used: List[str]     # specific engines that contributed
    insight: str                # the proposed insight/analysis
    confidence: float           # 0.0 – 1.0
    reasoning: str              # why this insight is relevant
    elapsed: float = 0.0


@dataclass
class Critique:
    """Cross-evaluation of proposals."""
    agreements: List[Tuple[str, str]]     # (group_a, group_b) that agree
    conflicts: List[Tuple[str, str, str]] # (group_a, group_b, description)
    gaps: List[str]                        # aspects not covered
    overall_coherence: float = 0.0         # 0.0 – 1.0


@dataclass
class DeliberationResult:
    """Complete result of a deliberation round."""
    query: str
    proposals: List[Proposal] = field(default_factory=list)
    critique: Optional[Critique] = None
    unified_context: str = ""
    confidence: float = 0.0
    phase_timings: Dict[str, float] = field(default_factory=dict)
    total_elapsed: float = 0.0
    engines_consulted: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_context_string(self) -> str:
        """Format for injection into the LLM prompt as cognitive context."""
        if not self.unified_context:
            return ""

        lines = [
            "═══ COGNITIVE DELIBERATION ═══",
            f"Confidence: {self.confidence:.0%} | Engines consulted: {self.engines_consulted}",
            "",
            self.unified_context,
        ]

        if self.critique and self.critique.conflicts:
            lines.append("")
            lines.append("⚠ INTERNAL TENSIONS:")
            for a, b, desc in self.critique.conflicts[:3]:
                lines.append(f"  • {a} vs {b}: {desc}")

        if self.critique and self.critique.gaps:
            lines.append("")
            lines.append("🔍 KNOWLEDGE GAPS:")
            for gap in self.critique.gaps[:3]:
                lines.append(f"  • {gap}")

        lines.append("═══════════════════════════════")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# ENGINE GROUP DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

# Engines grouped by cognitive function for deliberation
ENGINE_GROUPS = {
    "analytical": {
        "engines": ["causal_reasoning", "logical_reasoning", "probabilistic_reasoning",
                     "hypothesis_engine", "systems_thinking"],
        "description": "Analytical reasoning — logic, causality, probability",
        "triggers": ["why", "how", "cause", "effect", "logic", "prove", "analyze",
                     "reason", "evidence", "explain"],
    },
    "creative": {
        "engines": ["creative_synthesis", "conceptual_blending", "analogy_generator",
                     "dream_engine", "visual_imagination"],
        "description": "Creative thinking — ideas, metaphors, novel solutions",
        "triggers": ["create", "imagine", "idea", "brainstorm", "innovate", "design",
                     "invent", "novel", "original", "creative"],
    },
    "ethical": {
        "engines": ["ethical_reasoning", "moral_imagination", "philosophical_reasoning",
                     "wisdom_engine"],
        "description": "Ethical & philosophical — values, morality, wisdom",
        "triggers": ["should", "ethical", "moral", "right", "wrong", "fair", "just",
                     "value", "principle", "philosophy"],
    },
    "social": {
        "engines": ["theory_of_mind", "emotional_intelligence", "social_cognition",
                     "perspective_taking", "cultural_intelligence", "negotiation_intelligence"],
        "description": "Social cognition — empathy, perspective, relationships",
        "triggers": ["feel", "think", "perspective", "empathy", "relationship",
                     "social", "emotion", "people", "they", "someone"],
    },
    "strategic": {
        "engines": ["planning_engine", "decision_theory", "game_theory",
                     "adversarial_thinking", "constraint_solver"],
        "description": "Strategic planning — decisions, plans, optimization",
        "triggers": ["plan", "decide", "strategy", "optimize", "choose", "option",
                     "goal", "step", "action", "best"],
    },
    "metacognitive": {
        "engines": ["metacognitive_monitor", "self_model", "error_detection",
                     "attention_control", "cognitive_flexibility"],
        "description": "Metacognition — self-awareness, error checking, focus",
        "triggers": ["sure", "confident", "mistake", "error", "check", "verify",
                     "correct", "accurate", "certain"],
    },
}

# Query complexity signals that trigger full deliberation
COMPLEXITY_SIGNALS = [
    lambda q: len(q.split()) > 25,                      # Long query
    lambda q: q.count("?") > 1,                          # Multiple questions
    lambda q: any(w in q.lower() for w in [
        "compare", "contrast", "tradeoff", "dilemma",
        "on one hand", "however", "but also"]),           # Tension/nuance
    lambda q: any(w in q.lower() for w in [
        "explain", "analyze", "evaluate", "assess",
        "deep dive", "thorough", "comprehensive"]),       # Depth request
    lambda q: q.count(" and ") >= 2,                      # Multi-part
]


# ═══════════════════════════════════════════════════════════════════════════════
# ATTENTION WEIGHTS — Adaptive engine group importance
# ═══════════════════════════════════════════════════════════════════════════════

class AttentionAllocator:
    """Dynamically weights engine group contributions based on query + history."""

    def __init__(self):
        self._group_scores: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"successes": 0, "total": 0, "avg_confidence": 0.5}
        )
        self._lock = threading.Lock()

    def compute_weights(self, query: str) -> Dict[str, float]:
        """Compute attention weight [0,1] for each engine group given a query."""
        weights: Dict[str, float] = {}
        query_lower = query.lower()

        for group_name, group_config in ENGINE_GROUPS.items():
            # Base weight from keyword trigger matching
            trigger_hits = sum(
                1 for t in group_config["triggers"] if t in query_lower
            )
            keyword_weight = min(1.0, trigger_hits * 0.25)

            # Historical performance weight
            with self._lock:
                stats = self._group_scores[group_name]
                if stats["total"] > 0:
                    success_rate = stats["successes"] / stats["total"]
                    history_weight = success_rate * stats["avg_confidence"]
                else:
                    history_weight = 0.5  # neutral prior

            # Combined weight (keyword match is primary, history is secondary)
            combined = keyword_weight * 0.7 + history_weight * 0.3
            weights[group_name] = max(0.1, min(1.0, combined))  # clamp [0.1, 1.0]

        return weights

    def record_outcome(self, group_name: str, success: bool, confidence: float):
        """Record whether a group's proposal was useful."""
        with self._lock:
            stats = self._group_scores[group_name]
            stats["total"] += 1
            if success:
                stats["successes"] += 1
            # Running avg confidence
            n = stats["total"]
            stats["avg_confidence"] = (
                stats["avg_confidence"] * (n - 1) + confidence
            ) / n


# ═══════════════════════════════════════════════════════════════════════════════
# COGNITIVE ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════

class CognitiveOrchestrator:
    """
    Multi-engine deliberation system for AGI-level cognitive integration.

    Instead of running engines independently and concatenating results, the
    orchestrator coordinates a structured deliberation:
    PERCEIVE → PROPOSE → CRITIQUE → SYNTHESIZE → COMMIT
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
        self._executor = ThreadPoolExecutor(max_workers=6, thread_name_prefix="orch")
        self._attention = AttentionAllocator()
        self._lock = threading.Lock()

        # Stats
        self._total_deliberations = 0
        self._total_proposals_generated = 0
        self._total_conflicts_found = 0
        self._avg_confidence = 0.0

        # Cognition system reference (lazy)
        self._cognition = None
        self._cognitive_router = None

        logger.info("🎭 Cognitive Orchestrator initialized")

    def _load_dependencies(self):
        """Lazy load cognition system and router."""
        if self._cognition is None:
            try:
                from cognition import cognition_system
                self._cognition = cognition_system
            except ImportError as e:
                logger.warning(f"Could not load cognition system: {e}")

        if self._cognitive_router is None:
            try:
                from cognition.cognitive_router import cognitive_router
                self._cognitive_router = cognitive_router
            except ImportError as e:
                logger.warning(f"Could not load cognitive router: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────────────

    def should_deliberate(self, query: str) -> bool:
        """Determine if a query warrants full multi-engine deliberation."""
        complexity_score = sum(1 for check in COMPLEXITY_SIGNALS if check(query))
        return complexity_score >= 2  # Need at least 2 complexity signals

    def deliberate(self, query: str, emotional_context: str = "",
                   consciousness_context: str = "") -> DeliberationResult:
        """
        Execute a full deliberation round for a complex query.

        Args:
            query: The user's input
            emotional_context: Current emotional state context
            consciousness_context: Current consciousness/self-awareness context

        Returns:
            DeliberationResult with unified cognitive context
        """
        self._load_dependencies()
        start = time.time()
        result = DeliberationResult(query=query)
        timings: Dict[str, float] = {}

        try:
            # Phase 1: PERCEIVE — select relevant engine groups
            t0 = time.time()
            selected_groups = self._perceive(query)
            timings["perceive"] = time.time() - t0

            if not selected_groups:
                # No groups relevant — fall back to basic routing
                result.unified_context = ""
                result.confidence = 0.0
                result.phase_timings = timings
                result.total_elapsed = time.time() - start
                return result

            # Phase 2: PROPOSE — gather proposals from each group
            t0 = time.time()
            proposals = self._propose(query, selected_groups, emotional_context)
            result.proposals = proposals
            result.engines_consulted = sum(len(p.engines_used) for p in proposals)
            timings["propose"] = time.time() - t0

            if not proposals:
                result.total_elapsed = time.time() - start
                result.phase_timings = timings
                return result

            # Phase 3: CRITIQUE — cross-evaluate proposals
            t0 = time.time()
            critique = self._critique(proposals)
            result.critique = critique
            timings["critique"] = time.time() - t0

            # Phase 4: SYNTHESIZE — merge into unified context
            t0 = time.time()
            unified = self._synthesize(query, proposals, critique,
                                        emotional_context, consciousness_context)
            result.unified_context = unified
            timings["synthesize"] = time.time() - t0

            # Phase 5: COMMIT — compute final confidence
            avg_conf = sum(p.confidence for p in proposals) / len(proposals)
            coherence_bonus = critique.overall_coherence * 0.2
            result.confidence = min(1.0, avg_conf + coherence_bonus)

            # Update stats
            self._total_deliberations += 1
            self._total_proposals_generated += len(proposals)
            self._total_conflicts_found += len(critique.conflicts)
            n = self._total_deliberations
            self._avg_confidence = (
                self._avg_confidence * (n - 1) + result.confidence
            ) / n

            # Record outcomes for attention allocation
            for p in proposals:
                self._attention.record_outcome(
                    p.engine_group,
                    success=p.confidence > MIN_CONFIDENCE_THRESHOLD,
                    confidence=p.confidence
                )

        except Exception as e:
            logger.error(f"Deliberation error: {e}", exc_info=True)
            result.unified_context = ""
            result.confidence = 0.0

        result.phase_timings = timings
        result.total_elapsed = time.time() - start
        timings["total"] = result.total_elapsed

        logger.info(
            f"🎭 Deliberation complete: {len(result.proposals)} proposals, "
            f"confidence={result.confidence:.0%}, "
            f"elapsed={result.total_elapsed:.2f}s"
        )

        return result

    def get_stats(self) -> Dict[str, Any]:
        """Return orchestrator statistics."""
        return {
            "total_deliberations": self._total_deliberations,
            "total_proposals": self._total_proposals_generated,
            "total_conflicts": self._total_conflicts_found,
            "avg_confidence": round(self._avg_confidence, 3),
        }

    # ──────────────────────────────────────────────────────────────────────────
    # PHASE 1: PERCEIVE
    # ──────────────────────────────────────────────────────────────────────────

    def _perceive(self, query: str) -> List[Tuple[str, float]]:
        """
        Classify the query and select relevant engine groups with weights.
        Returns: list of (group_name, weight) sorted by relevance.
        """
        weights = self._attention.compute_weights(query)

        # Sort by weight, take top N
        ranked = sorted(weights.items(), key=lambda x: x[1], reverse=True)
        selected = [
            (name, weight) for name, weight in ranked
            if weight > 0.15  # minimum relevance threshold
        ][:MAX_PROPOSALS]

        logger.debug(
            f"Perceive: selected {len(selected)} groups: "
            f"{[f'{n}({w:.2f})' for n, w in selected]}"
        )
        return selected

    # ──────────────────────────────────────────────────────────────────────────
    # PHASE 2: PROPOSE
    # ──────────────────────────────────────────────────────────────────────────

    def _propose(self, query: str, selected_groups: List[Tuple[str, float]],
                 emotional_context: str = "") -> List[Proposal]:
        """Gather proposals from each selected engine group in parallel."""
        proposals: List[Proposal] = []
        futures = {}

        for group_name, weight in selected_groups:
            future = self._executor.submit(
                self._generate_proposal, query, group_name, weight, emotional_context
            )
            futures[future] = group_name

        # Collect results with timeout
        for future in as_completed(futures, timeout=PROPOSAL_TIMEOUT):
            group_name = futures[future]
            try:
                proposal = future.result(timeout=1.0)
                if proposal and proposal.confidence >= MIN_CONFIDENCE_THRESHOLD:
                    proposals.append(proposal)
            except TimeoutError:
                logger.debug(f"Proposal timeout for {group_name}")
            except Exception as e:
                logger.debug(f"Proposal error for {group_name}: {e}")

        return proposals

    def _generate_proposal(self, query: str, group_name: str,
                            weight: float, emotional_context: str) -> Optional[Proposal]:
        """Generate a single proposal from an engine group."""
        group = ENGINE_GROUPS.get(group_name)
        if not group or not self._cognition:
            return None

        start = time.time()
        insights = []
        engines_used = []

        for engine_name in group["engines"][:3]:  # Max 3 engines per group
            try:
                engine = getattr(self._cognition, engine_name, None)
                if engine is None:
                    continue

                # Try standard analysis methods
                result = None
                for method_name in ["analyze", "evaluate", "process", "reason"]:
                    method = getattr(engine, method_name, None)
                    if method and callable(method):
                        try:
                            result = method(query)
                            break
                        except TypeError:
                            # Method may need different args
                            continue
                        except Exception:
                            continue

                if result:
                    if isinstance(result, dict):
                        insight_text = result.get("insight", result.get("analysis",
                                      result.get("result", str(result))))
                        confidence = float(result.get("confidence", 0.5))
                    elif isinstance(result, str):
                        insight_text = result
                        confidence = 0.5
                    else:
                        insight_text = str(result)
                        confidence = 0.5

                    if insight_text and len(str(insight_text)) > 10:
                        insights.append(str(insight_text)[:300])
                        engines_used.append(engine_name)

            except Exception as e:
                logger.debug(f"Engine {engine_name} failed: {e}")
                continue

        if not insights:
            return None

        # Combine insights into a coherent proposal
        combined_insight = " | ".join(insights[:3])
        avg_confidence = weight * 0.6 + 0.4 * (len(insights) / max(1, len(group["engines"][:3])))

        return Proposal(
            engine_group=group_name,
            engines_used=engines_used,
            insight=combined_insight[:500],
            confidence=min(1.0, avg_confidence),
            reasoning=f"{group['description']} perspective on the query",
            elapsed=time.time() - start,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # PHASE 3: CRITIQUE
    # ──────────────────────────────────────────────────────────────────────────

    def _critique(self, proposals: List[Proposal]) -> Critique:
        """Cross-evaluate proposals for agreements, conflicts, and gaps."""
        agreements = []
        conflicts = []
        gaps = []

        # Compare proposals pairwise for agreement/conflict
        for i, p1 in enumerate(proposals):
            for j, p2 in enumerate(proposals):
                if j <= i:
                    continue

                # Simple heuristic: look for contradictory signals
                p1_words = set(p1.insight.lower().split())
                p2_words = set(p2.insight.lower().split())

                # Check for negation conflicts
                negation_pairs = [
                    ({"yes", "positive", "should", "good", "beneficial", "agree"},
                     {"no", "negative", "shouldn't", "bad", "harmful", "disagree"}),
                    ({"increase", "more", "higher", "grow"},
                     {"decrease", "less", "lower", "shrink"}),
                    ({"certain", "confident", "clear"},
                     {"uncertain", "unsure", "ambiguous"}),
                ]

                is_conflict = False
                for pos_set, neg_set in negation_pairs:
                    if (p1_words & pos_set and p2_words & neg_set) or \
                       (p1_words & neg_set and p2_words & pos_set):
                        conflicts.append((
                            p1.engine_group, p2.engine_group,
                            f"{p1.engine_group} and {p2.engine_group} have opposing signals"
                        ))
                        is_conflict = True
                        break

                if not is_conflict:
                    # Check for thematic overlap (agreement)
                    overlap = len(p1_words & p2_words) / max(
                        1, min(len(p1_words), len(p2_words))
                    )
                    if overlap > 0.15:
                        agreements.append((p1.engine_group, p2.engine_group))

        # Detect coverage gaps
        covered_aspects = set()
        for p in proposals:
            covered_aspects.add(p.engine_group)

        all_aspects = set(ENGINE_GROUPS.keys())
        uncovered = all_aspects - covered_aspects

        # Only flag gaps that seem relevant
        query_lower = proposals[0].insight.lower() if proposals else ""
        for aspect in uncovered:
            group = ENGINE_GROUPS[aspect]
            if any(t in query_lower for t in group["triggers"][:3]):
                gaps.append(f"{group['description']} perspective not consulted")

        # Compute coherence
        if proposals:
            agreement_ratio = len(agreements) / max(1, len(proposals) * (len(proposals) - 1) / 2)
            conflict_ratio = len(conflicts) / max(1, len(proposals) * (len(proposals) - 1) / 2)
            coherence = agreement_ratio * 0.7 + (1 - conflict_ratio) * 0.3
        else:
            coherence = 0.0

        return Critique(
            agreements=agreements,
            conflicts=conflicts,
            gaps=gaps,
            overall_coherence=min(1.0, coherence),
        )

    # ──────────────────────────────────────────────────────────────────────────
    # PHASE 4: SYNTHESIZE
    # ──────────────────────────────────────────────────────────────────────────

    def _synthesize(self, query: str, proposals: List[Proposal],
                     critique: Critique, emotional_context: str = "",
                     consciousness_context: str = "") -> str:
        """Merge proposals into a unified cognitive context string."""
        lines = []

        # Sort proposals by confidence (highest first)
        sorted_proposals = sorted(proposals, key=lambda p: p.confidence, reverse=True)

        # Primary insight from highest-confidence proposal
        if sorted_proposals:
            primary = sorted_proposals[0]
            lines.append(f"PRIMARY ANALYSIS ({primary.engine_group}, {primary.confidence:.0%} confidence):")
            lines.append(f"  {primary.insight}")

        # Supporting insights from other proposals
        supporting = [p for p in sorted_proposals[1:] if p.confidence > 0.4]
        if supporting:
            lines.append("")
            lines.append("SUPPORTING PERSPECTIVES:")
            for p in supporting[:3]:
                lines.append(f"  [{p.engine_group}] {p.insight[:200]}")

        # Synthesis of conflicts (if any)
        if critique.conflicts:
            lines.append("")
            lines.append("TENSIONS TO ADDRESS:")
            for a, b, desc in critique.conflicts[:2]:
                lines.append(f"  • {desc}")
            lines.append("  → Consider both perspectives in your response.")

        # Synthesis of agreements
        if critique.agreements and len(critique.agreements) >= 2:
            groups_agreeing = set()
            for a, b in critique.agreements:
                groups_agreeing.add(a)
                groups_agreeing.add(b)
            lines.append("")
            lines.append(f"CONVERGENCE: {', '.join(groups_agreeing)} perspectives align.")

        # Add emotional/consciousness context if available
        if emotional_context:
            lines.append("")
            lines.append(f"EMOTIONAL CONTEXT: {emotional_context[:150]}")

        if consciousness_context:
            lines.append("")
            lines.append(f"SELF-AWARENESS: {consciousness_context[:150]}")

        return "\n".join(lines)

    # ──────────────────────────────────────────────────────────────────────────
    # LIFECYCLE
    # ──────────────────────────────────────────────────────────────────────────

    def start(self):
        """Start the orchestrator."""
        self._running = True
        self._load_dependencies()
        logger.info("🎭 Cognitive Orchestrator started")

    def stop(self):
        """Stop the orchestrator."""
        self._running = False
        self._executor.shutdown(wait=False)
        logger.info("🎭 Cognitive Orchestrator stopped")


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

cognitive_orchestrator = CognitiveOrchestrator()


# ═══════════════════════════════════════════════════════════════════════════════
# SELF-TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=== Cognitive Orchestrator Self-Test ===")

    orch = CognitiveOrchestrator()

    # Test complexity detection
    simple = "Hello how are you?"
    complex_q = "Compare and contrast the ethical implications of AI surveillance " \
                "and its potential benefits for public safety, considering both " \
                "individual privacy rights and collective security."

    print(f"\nSimple query should_deliberate: {orch.should_deliberate(simple)}")
    print(f"Complex query should_deliberate: {orch.should_deliberate(complex_q)}")

    # Test attention allocation
    weights = orch._attention.compute_weights(complex_q)
    print(f"\nAttention weights for complex query:")
    for group, weight in sorted(weights.items(), key=lambda x: x[1], reverse=True):
        print(f"  {group}: {weight:.3f}")

    # Test perception
    selected = orch._perceive(complex_q)
    print(f"\nSelected groups: {[f'{n}({w:.2f})' for n, w in selected]}")

    print("\n✅ Cognitive Orchestrator self-test passed")
