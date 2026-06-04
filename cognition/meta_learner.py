"""
NEXUS AI — Meta-Learning Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Tracks what strategies work for what kinds of problems, learns from
every interaction, and adapts future behavior automatically.

This is NOT retrieval-augmented generation (RAG). RAG retrieves *facts*.
This learns *behavior patterns* — it changes HOW NEXUS responds.

Architecture:
  ┌─────────────┐     ┌──────────────┐     ┌──────────────────┐
  │ Interaction  │────▶│ MetaLearner  │────▶│ Adaptive Prompt  │
  │  Outcomes    │     │  (UCB1 +     │     │   Additions      │
  │              │     │  Bayesian)   │     │                  │
  └─────────────┘     └──────────────┘     └──────────────────┘
"""

import json
import math
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("meta_learner")


# ═══════════════════════════════════════════════════════════════════════════════
# QUERY TYPES
# ═══════════════════════════════════════════════════════════════════════════════

QUERY_TYPES = [
    "math",
    "creative",
    "analysis",
    "factual",
    "planning",
    "debugging",
    "coding",
    "conversation",
    "philosophical",
    "technical",
    "unknown",
]

STRATEGY_TYPES = [
    "chain_of_thought",
    "decomposition",
    "analogy",
    "first_principles",
    "debate",
    "metacognitive",
    "direct",           # Simple direct response
]


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class InteractionOutcome:
    """Records the outcome of a single interaction."""
    outcome_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    query_type: str = "unknown"
    strategy_used: str = "direct"
    quality_score: float = 0.5       # From self-critique (0-1)
    latency_seconds: float = 0.0
    tools_used: List[str] = field(default_factory=list)
    was_agentic: bool = False
    user_satisfied: bool = True      # Inferred from follow-ups
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StrategyPerformance:
    """Running statistics for a strategy on a particular query type."""
    strategy: str = "direct"
    query_type: str = "unknown"
    total_uses: int = 0
    total_score: float = 0.0
    total_latency: float = 0.0
    successes: int = 0               # score > 0.6
    failures: int = 0                # score < 0.4
    last_used: str = ""

    @property
    def avg_score(self) -> float:
        return self.total_score / max(1, self.total_uses)

    @property
    def avg_latency(self) -> float:
        return self.total_latency / max(1, self.total_uses)

    @property
    def success_rate(self) -> float:
        total = self.successes + self.failures
        return self.successes / max(1, total)

    def ucb1_score(self, total_interactions: int) -> float:
        """Upper Confidence Bound for exploration-exploitation balance."""
        if self.total_uses == 0:
            return float('inf')  # Unexplored → always try first
        exploitation = self.avg_score
        exploration = math.sqrt(2 * math.log(max(1, total_interactions)) / self.total_uses)
        return exploitation + exploration

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy,
            "query_type": self.query_type,
            "total_uses": self.total_uses,
            "total_score": round(self.total_score, 3),
            "total_latency": round(self.total_latency, 2),
            "successes": self.successes,
            "failures": self.failures,
            "last_used": self.last_used,
            "avg_score": round(self.avg_score, 3),
            "success_rate": round(self.success_rate, 3),
        }


@dataclass
class LearnedBehavior:
    """A behavior pattern NEXUS has learned from experience."""
    behavior_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    query_type: str = "unknown"
    prompt_addition: str = ""        # Injected into system prompt
    confidence: float = 0.5
    evidence_count: int = 0          # How many interactions support this
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_validated: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# META-LEARNER
# ═══════════════════════════════════════════════════════════════════════════════

class MetaLearner:
    """
    Learns from every interaction to adapt future behavior.

    Core capabilities:
    1. Strategy tracking — which reasoning strategies work best for which query types
    2. Behavioral adaptation — generates prompt additions based on learned patterns
    3. UCB1 exploration — balances exploiting known-good strategies vs exploring new ones
    4. Continuous improvement — performance data persists across sessions
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._data_dir = Path(DATA_DIR) / "meta_learning"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        # Strategy performance matrix: {query_type: {strategy: StrategyPerformance}}
        self._performance: Dict[str, Dict[str, StrategyPerformance]] = {}

        # Learned behavioral patterns
        self._behaviors: List[LearnedBehavior] = []

        # Recent outcomes for pattern detection
        self._recent_outcomes: List[InteractionOutcome] = []
        self._max_recent = 200

        # Global counters
        self._total_interactions = 0
        self._session_interactions = 0

        # Load persistent data
        self._load_data()

        logger.info(f"[META-LEARNER] Initialized with {self._total_interactions} "
                    f"historical interactions, {len(self._behaviors)} learned behaviors")

    # ─────────────────────────────────────────────────────────────────────────
    # QUERY CLASSIFICATION
    # ─────────────────────────────────────────────────────────────────────────

    def classify_query(self, query: str) -> str:
        """Classify a query into a type using keyword heuristics."""
        q = query.lower().strip()

        # Math / calculation
        if any(w in q for w in ["calculate", "solve", "equation", "math", "formula",
                                "integral", "derivative", "sum of", "what is"]) \
                and any(c.isdigit() for c in q):
            return "math"

        # Coding / debugging
        if any(w in q for w in ["code", "function", "class", "bug", "error",
                                "implement", "refactor", "python", "javascript",
                                "algorithm", "api", "debug", "fix"]):
            return "coding" if "debug" not in q and "fix" not in q and "error" not in q \
                else "debugging"

        # Planning
        if any(w in q for w in ["plan", "design", "architecture", "roadmap",
                                "strategy", "how should", "approach"]):
            return "planning"

        # Analysis
        if any(w in q for w in ["analyze", "compare", "evaluate", "assess",
                                "review", "examine", "pros and cons", "trade-off"]):
            return "analysis"

        # Creative
        if any(w in q for w in ["write", "story", "poem", "creative", "imagine",
                                "generate", "invent", "brainstorm"]):
            return "creative"

        # Philosophical
        if any(w in q for w in ["meaning", "purpose", "consciousness", "ethics",
                                "morality", "existence", "philosophy", "why do we"]):
            return "philosophical"

        # Technical
        if any(w in q for w in ["how does", "explain", "what is", "technical",
                                "mechanism", "process", "system"]):
            return "technical"

        # Factual
        if any(w in q for w in ["who", "when", "where", "what year", "how many",
                                "capital of", "population", "fact"]):
            return "factual"

        # Conversation
        if any(w in q for w in ["hello", "hi", "hey", "how are", "thanks",
                                "good morning", "what's up"]):
            return "conversation"

        return "unknown"

    # ─────────────────────────────────────────────────────────────────────────
    # STRATEGY SELECTION
    # ─────────────────────────────────────────────────────────────────────────

    def get_best_strategy(self, query_type: str) -> str:
        """
        Get the best strategy for a query type using UCB1 multi-armed bandit.

        Returns the strategy with the highest UCB1 score, which balances
        exploitation (use what works) with exploration (try new things).
        """
        type_perf = self._performance.get(query_type, {})

        if not type_perf:
            # No data for this query type — return sensible default
            defaults = {
                "math": "chain_of_thought",
                "coding": "decomposition",
                "debugging": "chain_of_thought",
                "planning": "decomposition",
                "analysis": "first_principles",
                "creative": "analogy",
                "philosophical": "debate",
                "factual": "direct",
                "conversation": "direct",
                "technical": "chain_of_thought",
            }
            return defaults.get(query_type, "chain_of_thought")

        # Calculate UCB1 scores for each strategy
        best_strategy = "direct"
        best_score = -1.0

        for strategy_name in STRATEGY_TYPES:
            perf = type_perf.get(strategy_name)
            if perf is None:
                # Unexplored strategy → always try it
                return strategy_name
            score = perf.ucb1_score(self._total_interactions)
            if score > best_score:
                best_score = score
                best_strategy = strategy_name

        return best_strategy

    def get_strategy_confidence(self, query_type: str, strategy: str) -> float:
        """How confident are we that this strategy is good for this query type?"""
        type_perf = self._performance.get(query_type, {})
        perf = type_perf.get(strategy)
        if perf is None or perf.total_uses < 3:
            return 0.0  # Not enough data
        # Confidence grows with evidence
        evidence_factor = min(1.0, perf.total_uses / 20.0)
        return perf.avg_score * evidence_factor

    # ─────────────────────────────────────────────────────────────────────────
    # OUTCOME RECORDING
    # ─────────────────────────────────────────────────────────────────────────

    def record_outcome(self, outcome: InteractionOutcome) -> None:
        """Record the outcome of an interaction and update strategy performance."""
        self._total_interactions += 1
        self._session_interactions += 1

        # Update strategy performance
        qt = outcome.query_type
        st = outcome.strategy_used

        if qt not in self._performance:
            self._performance[qt] = {}
        if st not in self._performance[qt]:
            self._performance[qt][st] = StrategyPerformance(
                strategy=st, query_type=qt
            )

        perf = self._performance[qt][st]
        perf.total_uses += 1
        perf.total_score += outcome.quality_score
        perf.total_latency += outcome.latency_seconds
        perf.last_used = outcome.timestamp

        if outcome.quality_score > 0.6:
            perf.successes += 1
        elif outcome.quality_score < 0.4:
            perf.failures += 1

        # Store recent outcome
        self._recent_outcomes.append(outcome)
        if len(self._recent_outcomes) > self._max_recent:
            self._recent_outcomes = self._recent_outcomes[-self._max_recent:]

        # Check for behavioral patterns periodically
        if self._session_interactions % 10 == 0:
            self._detect_patterns()

        # Persist every 5 interactions
        if self._session_interactions % 5 == 0:
            self._save_data()

        logger.debug(f"[META-LEARNER] Recorded: {qt}/{st} → score={outcome.quality_score:.2f}")

    # ─────────────────────────────────────────────────────────────────────────
    # ADAPTIVE PROMPT GENERATION
    # ─────────────────────────────────────────────────────────────────────────

    def get_adaptive_prompt_additions(self, query_type: str = None) -> str:
        """
        Generate personalized prompt additions based on learned patterns.

        These are injected into the system prompt to guide behavior based
        on what NEXUS has learned works well.
        """
        additions = []

        # Add relevant learned behaviors
        for behavior in self._behaviors:
            if behavior.confidence < 0.5:
                continue
            if query_type and behavior.query_type != "unknown" \
                    and behavior.query_type != query_type:
                continue
            additions.append(behavior.prompt_addition)

        # Add strategy-specific guidance
        if query_type:
            best = self.get_best_strategy(query_type)
            confidence = self.get_strategy_confidence(query_type, best)

            if confidence > 0.3:
                strategy_prompts = {
                    "chain_of_thought": "Think through this step-by-step, showing your reasoning.",
                    "decomposition": "Break this into smaller sub-problems and solve each one.",
                    "analogy": "Find analogies to similar known problems to guide your approach.",
                    "first_principles": "Reason from first principles — what are the fundamental truths here?",
                    "debate": "Consider arguments for and against before reaching a conclusion.",
                    "metacognitive": "Monitor your reasoning quality — flag any uncertainty.",
                }
                if best in strategy_prompts:
                    additions.append(strategy_prompts[best])

        if not additions:
            return ""

        return "\n\n[Learned behavior guidance]\n" + "\n".join(f"• {a}" for a in additions)

    # ─────────────────────────────────────────────────────────────────────────
    # PATTERN DETECTION
    # ─────────────────────────────────────────────────────────────────────────

    def _detect_patterns(self) -> None:
        """Analyze recent outcomes to detect behavioral patterns."""
        if len(self._recent_outcomes) < 10:
            return

        # Group by query type
        by_type: Dict[str, List[InteractionOutcome]] = defaultdict(list)
        for outcome in self._recent_outcomes[-50:]:
            by_type[outcome.query_type].append(outcome)

        for qt, outcomes in by_type.items():
            if len(outcomes) < 5:
                continue

            # Check if a strategy consistently outperforms others
            by_strategy: Dict[str, List[float]] = defaultdict(list)
            for o in outcomes:
                by_strategy[o.strategy_used].append(o.quality_score)

            for strategy, scores in by_strategy.items():
                avg = sum(scores) / len(scores)
                if avg > 0.7 and len(scores) >= 3:
                    # This strategy works well — check if we already know this
                    already_known = any(
                        b.query_type == qt and strategy in b.description
                        for b in self._behaviors
                    )
                    if not already_known:
                        behavior = LearnedBehavior(
                            description=f"Strategy '{strategy}' works well for {qt} queries (avg score: {avg:.2f})",
                            query_type=qt,
                            prompt_addition=f"For {qt} queries, prefer the {strategy} approach.",
                            confidence=min(0.9, avg),
                            evidence_count=len(scores),
                        )
                        self._behaviors.append(behavior)
                        logger.info(f"[META-LEARNER] New behavior learned: {behavior.description}")

            # Check for common failure patterns
            low_scores = [o for o in outcomes if o.quality_score < 0.4]
            if len(low_scores) >= 3:
                # Many failures for this type — add a caution behavior
                already_cautious = any(
                    b.query_type == qt and "extra care" in b.prompt_addition.lower()
                    for b in self._behaviors
                )
                if not already_cautious:
                    behavior = LearnedBehavior(
                        description=f"{qt} queries have high failure rate — needs extra care",
                        query_type=qt,
                        prompt_addition=f"Take extra care with {qt} queries — verify your answer thoroughly before responding.",
                        confidence=0.6,
                        evidence_count=len(low_scores),
                    )
                    self._behaviors.append(behavior)
                    logger.info(f"[META-LEARNER] Caution behavior learned: {behavior.description}")

    # ─────────────────────────────────────────────────────────────────────────
    # PERSISTENCE
    # ─────────────────────────────────────────────────────────────────────────

    def _save_data(self) -> None:
        """Persist meta-learning data to disk."""
        try:
            data = {
                "total_interactions": self._total_interactions,
                "performance": {},
                "behaviors": [b.to_dict() for b in self._behaviors],
                "recent_outcomes": [o.to_dict() for o in self._recent_outcomes[-100:]],
                "saved_at": datetime.now().isoformat(),
            }

            # Serialize performance matrix
            for qt, strategies in self._performance.items():
                data["performance"][qt] = {
                    st: perf.to_dict() for st, perf in strategies.items()
                }

            save_path = self._data_dir / "meta_learning.json"
            with open(save_path, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.warning(f"[META-LEARNER] Save failed: {e}")

    def _load_data(self) -> None:
        """Load meta-learning data from disk."""
        try:
            load_path = self._data_dir / "meta_learning.json"
            if not load_path.exists():
                return

            with open(load_path, "r") as f:
                data = json.load(f)

            self._total_interactions = data.get("total_interactions", 0)

            # Restore performance matrix
            for qt, strategies in data.get("performance", {}).items():
                self._performance[qt] = {}
                for st, perf_data in strategies.items():
                    perf = StrategyPerformance(
                        strategy=perf_data.get("strategy", st),
                        query_type=perf_data.get("query_type", qt),
                        total_uses=perf_data.get("total_uses", 0),
                        total_score=perf_data.get("total_score", 0.0),
                        total_latency=perf_data.get("total_latency", 0.0),
                        successes=perf_data.get("successes", 0),
                        failures=perf_data.get("failures", 0),
                        last_used=perf_data.get("last_used", ""),
                    )
                    self._performance[qt][st] = perf

            # Restore behaviors
            for b_data in data.get("behaviors", []):
                behavior = LearnedBehavior(
                    behavior_id=b_data.get("behavior_id", str(uuid.uuid4())[:8]),
                    description=b_data.get("description", ""),
                    query_type=b_data.get("query_type", "unknown"),
                    prompt_addition=b_data.get("prompt_addition", ""),
                    confidence=b_data.get("confidence", 0.5),
                    evidence_count=b_data.get("evidence_count", 0),
                    created_at=b_data.get("created_at", ""),
                    last_validated=b_data.get("last_validated", ""),
                )
                self._behaviors.append(behavior)

            # Restore recent outcomes
            for o_data in data.get("recent_outcomes", []):
                outcome = InteractionOutcome(
                    outcome_id=o_data.get("outcome_id", ""),
                    query_type=o_data.get("query_type", "unknown"),
                    strategy_used=o_data.get("strategy_used", "direct"),
                    quality_score=o_data.get("quality_score", 0.5),
                    latency_seconds=o_data.get("latency_seconds", 0.0),
                    tools_used=o_data.get("tools_used", []),
                    was_agentic=o_data.get("was_agentic", False),
                    timestamp=o_data.get("timestamp", ""),
                )
                self._recent_outcomes.append(outcome)

        except Exception as e:
            logger.warning(f"[META-LEARNER] Load failed (starting fresh): {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC STATS
    # ─────────────────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Get meta-learning statistics."""
        return {
            "total_interactions": self._total_interactions,
            "session_interactions": self._session_interactions,
            "learned_behaviors": len(self._behaviors),
            "tracked_query_types": len(self._performance),
            "recent_outcomes": len(self._recent_outcomes),
            "top_strategies": {
                qt: self.get_best_strategy(qt)
                for qt in self._performance.keys()
            },
        }

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get a summary of strategy performance across all query types."""
        summary = {}
        for qt, strategies in self._performance.items():
            summary[qt] = {
                st: {
                    "avg_score": round(perf.avg_score, 3),
                    "uses": perf.total_uses,
                    "success_rate": round(perf.success_rate, 3),
                }
                for st, perf in strategies.items()
                if perf.total_uses > 0
            }
        return summary

    def get_learning_velocity(self) -> Dict[str, Any]:
        """
        Track whether NEXUS is actually getting better over time.
        Compares recent performance to historical performance.
        This closes the learning feedback loop.
        """
        if len(self._recent_outcomes) < 20:
            return {"sufficient_data": False, "message": "Need more interactions to measure velocity"}

        recent = self._recent_outcomes[-20:]
        older = self._recent_outcomes[-40:-20] if len(self._recent_outcomes) >= 40 else []

        recent_avg = sum(o.quality_score for o in recent) / len(recent)

        if older:
            older_avg = sum(o.quality_score for o in older) / len(older)
            velocity = recent_avg - older_avg
            improving = velocity > 0.02
        else:
            velocity = 0.0
            improving = None

        return {
            "sufficient_data": True,
            "recent_avg_quality": round(recent_avg, 3),
            "learning_velocity": round(velocity, 4),
            "improving": improving,
            "total_interactions": self._total_interactions,
            "learned_behaviors": len(self._behaviors),
        }

    def record_agi_loop_outcome(self, user_input: str, tool_results: list,
                                 elapsed: float, success: bool):
        """
        Record an AGI loop outcome for meta-learning.
        Bridges the AGI cognitive loop into the adaptive learning system.
        """
        query_type = self.classify_query(user_input)
        quality = 0.7 if success else 0.3

        # Adjust quality based on tool effectiveness
        if tool_results:
            tool_success_rate = sum(
                1 for r in tool_results if r.get("success")
            ) / max(1, len(tool_results))
            quality = 0.3 + (tool_success_rate * 0.4) + (0.3 if success else 0)

        outcome = InteractionOutcome(
            query_type=query_type,
            strategy_used="agi_loop",
            quality_score=quality,
            latency_seconds=elapsed,
            tools_used=[r.get("tool_name", "") for r in tool_results],
            was_agentic=True,
            user_satisfied=success,
        )
        self.record_outcome(outcome)

        # Also record on the working memory blackboard
        try:
            from core.working_memory_blackboard import blackboard
            blackboard.record_lesson(
                lesson=f"AGI loop: {query_type} query, quality={quality:.2f}, "
                       f"{len(tool_results)} tools used",
                context=user_input[:100],
                quality_delta=quality - 0.5,
                strategy_used="agi_loop",
            )
        except Exception:
            pass

    def get_learning_summary(self) -> str:
        """
        Generate a text summary of meta-learning state.
        Used by the context collector.
        """
        velocity = self.get_learning_velocity()
        lines = [
            f"Interactions learned from: {self._total_interactions}",
            f"Learned behaviors: {len(self._behaviors)}",
        ]

        if velocity.get("sufficient_data"):
            lines.append(
                f"Recent quality: {velocity['recent_avg_quality']:.0%}"
            )
            if velocity.get("improving") is not None:
                direction = "↑ improving" if velocity["improving"] else "→ stable"
                lines.append(f"Learning velocity: {direction}")

        return " | ".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

meta_learner = MetaLearner()

