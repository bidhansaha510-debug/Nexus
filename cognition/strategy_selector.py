"""
NEXUS AI — Multi-Strategy Reasoner
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Dynamically selects between 6 reasoning strategies based on query
classification and historical performance from the MetaLearner.

Instead of a single reasoning approach for all queries, this system
picks the optimal strategy per query, leveraging NEXUS's 50+ existing
cognition engines.

Strategies:
  1. Chain-of-Thought  → Step-by-step logical deduction
  2. Decomposition     → Break into sub-problems (TaskEngine)
  3. Analogy           → Find similar solved problems
  4. First Principles  → Reason from axioms upward
  5. Debate            → Generate pro/con arguments
  6. Metacognitive     → Monitor reasoning quality in real-time
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.logger import get_logger

logger = get_logger("strategy_selector")


# ═══════════════════════════════════════════════════════════════════════════════
# STRATEGY DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ReasoningStrategy:
    """A reasoning strategy with its execution logic."""
    name: str = ""
    description: str = ""
    system_prompt_fragment: str = ""
    best_for: List[str] = field(default_factory=list)
    cognitive_engines: List[str] = field(default_factory=list)
    requires_tools: bool = False
    avg_latency_seconds: float = 2.0


STRATEGIES: Dict[str, ReasoningStrategy] = {
    "chain_of_thought": ReasoningStrategy(
        name="chain_of_thought",
        description="Step-by-step logical deduction",
        system_prompt_fragment=(
            "Approach this problem using chain-of-thought reasoning.\n"
            "1. Identify the core question\n"
            "2. List what you know and what you need to figure out\n"
            "3. Work through each step of your reasoning explicitly\n"
            "4. Check each step for logical consistency\n"
            "5. State your conclusion with confidence level"
        ),
        best_for=["math", "debugging", "technical"],
        cognitive_engines=["logical_reasoning", "causal_reasoning"],
    ),
    "decomposition": ReasoningStrategy(
        name="decomposition",
        description="Break into sub-problems and solve each",
        system_prompt_fragment=(
            "Decompose this into smaller sub-problems.\n"
            "1. Identify the top-level goal\n"
            "2. Break it into 2-5 independent sub-tasks\n"
            "3. Solve each sub-task in order of dependency\n"
            "4. Synthesize the sub-solutions into a complete answer\n"
            "5. Verify the combined solution addresses the original question"
        ),
        best_for=["planning", "coding", "analysis"],
        cognitive_engines=["planning_engine", "constraint_solver"],
        requires_tools=True,
    ),
    "analogy": ReasoningStrategy(
        name="analogy",
        description="Find analogies to similar known problems",
        system_prompt_fragment=(
            "Use analogical reasoning to approach this.\n"
            "1. Identify the structural pattern of this problem\n"
            "2. Search your knowledge for similar problems you've solved before\n"
            "3. Map the solution from the analogous problem to this one\n"
            "4. Adjust for differences between the two situations\n"
            "5. Validate the transferred solution"
        ),
        best_for=["creative", "philosophical", "technical"],
        cognitive_engines=["analogical_reasoning", "conceptual_blending"],
    ),
    "first_principles": ReasoningStrategy(
        name="first_principles",
        description="Reason from fundamental axioms upward",
        system_prompt_fragment=(
            "Apply first-principles thinking.\n"
            "1. Strip away all assumptions and conventions\n"
            "2. Identify the fundamental truths or axioms that apply\n"
            "3. Build up your reasoning from these foundations\n"
            "4. Question any step that relies on convention rather than logic\n"
            "5. Arrive at a conclusion grounded in first principles"
        ),
        best_for=["analysis", "technical", "philosophical"],
        cognitive_engines=["hypothesis_engine", "causal_reasoning"],
    ),
    "debate": ReasoningStrategy(
        name="debate",
        description="Generate arguments for and against, then judge",
        system_prompt_fragment=(
            "Use dialectical reasoning — debate yourself.\n"
            "1. State the strongest argument FOR the most obvious answer\n"
            "2. State the strongest argument AGAINST it\n"
            "3. Consider alternative answers and their arguments\n"
            "4. Weigh the evidence and reasoning quality of each side\n"
            "5. Reach a conclusion with explicit reasoning for why this side wins"
        ),
        best_for=["philosophical", "analysis", "creative"],
        cognitive_engines=["debate_engine", "dialectical_reasoning", "adversarial_thinking"],
    ),
    "metacognitive": ReasoningStrategy(
        name="metacognitive",
        description="Monitor reasoning quality in real-time",
        system_prompt_fragment=(
            "Apply metacognitive monitoring while reasoning.\n"
            "1. Before answering, assess: what do I know vs. not know about this?\n"
            "2. Flag any assumptions you're making\n"
            "3. Rate your confidence in each claim (high/medium/low)\n"
            "4. Identify potential cognitive biases affecting your reasoning\n"
            "5. Explicitly state what could make your answer wrong"
        ),
        best_for=["factual", "technical", "analysis"],
        cognitive_engines=["metacognitive_monitor", "error_detection"],
    ),
    "direct": ReasoningStrategy(
        name="direct",
        description="Simple direct response without complex reasoning",
        system_prompt_fragment="",
        best_for=["conversation", "factual"],
        cognitive_engines=[],
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# STRATEGY SELECTOR
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class StrategyDecision:
    """The result of a strategy selection."""
    strategy_name: str = "direct"
    strategy: Optional[ReasoningStrategy] = None
    query_type: str = "unknown"
    confidence: float = 0.0
    reason: str = ""
    prompt_fragment: str = ""
    cognitive_engines: List[str] = field(default_factory=list)


class StrategySelector:
    """
    Selects the optimal reasoning strategy for a given query.

    Uses the MetaLearner's historical performance data to pick strategies
    that have historically worked well for similar query types.
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

        self._meta_learner = None  # Lazy loaded
        self._cognitive_router = None  # Lazy loaded

        logger.info("[STRATEGY-SELECTOR] Initialized with %d strategies", len(STRATEGIES))

    def _load_meta_learner(self):
        """Lazy load meta learner."""
        if self._meta_learner is None:
            try:
                from cognition.meta_learner import meta_learner
                self._meta_learner = meta_learner
            except Exception as e:
                logger.warning(f"Could not load MetaLearner: {e}")

    def _load_cognitive_router(self):
        """Lazy load cognitive router."""
        if self._cognitive_router is None:
            try:
                from cognition.cognitive_router import CognitiveRouter
                self._cognitive_router = CognitiveRouter()
            except Exception as e:
                logger.warning(f"Could not load CognitiveRouter: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # SELECTION
    # ─────────────────────────────────────────────────────────────────────────

    def select(self, query: str, query_type: str = None) -> StrategyDecision:
        """
        Select the best reasoning strategy for a query.

        Args:
            query: The user's query text
            query_type: Optional pre-classified query type

        Returns:
            StrategyDecision with the chosen strategy and context
        """
        self._load_meta_learner()

        # Classify query if not provided
        if query_type is None:
            if self._meta_learner:
                query_type = self._meta_learner.classify_query(query)
            else:
                query_type = "unknown"

        # Ask meta-learner for best historical strategy
        if self._meta_learner:
            best_name = self._meta_learner.get_best_strategy(query_type)
            confidence = self._meta_learner.get_strategy_confidence(query_type, best_name)
        else:
            # Fall back to hardcoded defaults
            best_name = self._get_default_strategy(query_type)
            confidence = 0.3

        strategy = STRATEGIES.get(best_name, STRATEGIES["direct"])

        # Build the decision
        decision = StrategyDecision(
            strategy_name=best_name,
            strategy=strategy,
            query_type=query_type,
            confidence=confidence,
            reason=f"MetaLearner selected '{best_name}' for {query_type} "
                   f"(confidence: {confidence:.2f})",
            prompt_fragment=strategy.system_prompt_fragment,
            cognitive_engines=list(strategy.cognitive_engines),
        )

        logger.debug(f"[STRATEGY-SELECTOR] {decision.reason}")
        return decision

    def _get_default_strategy(self, query_type: str) -> str:
        """Get default strategy when no meta-learning data is available."""
        for name, strategy in STRATEGIES.items():
            if query_type in strategy.best_for:
                return name
        return "chain_of_thought"

    # ─────────────────────────────────────────────────────────────────────────
    # COGNITIVE ENGINE INVOCATION
    # ─────────────────────────────────────────────────────────────────────────

    def invoke_cognitive_engines(
        self, query: str, decision: StrategyDecision
    ) -> str:
        """
        Invoke the cognitive engines recommended by the chosen strategy.

        Returns aggregated insights from the engines as context.
        """
        if not decision.cognitive_engines:
            return ""

        self._load_cognitive_router()
        if self._cognitive_router is None:
            return ""

        try:
            # Use the cognitive router to invoke the recommended engines
            insights = self._cognitive_router.route(
                query,
                engine_filter=decision.cognitive_engines,
            )

            if insights and hasattr(insights, 'to_context_string'):
                context = insights.to_context_string()
                if context:
                    return f"\n\n[Cognitive Engine Insights]\n{context}"
        except Exception as e:
            logger.debug(f"[STRATEGY-SELECTOR] Engine invocation failed: {e}")

        return ""

    # ─────────────────────────────────────────────────────────────────────────
    # STRATEGY INFO
    # ─────────────────────────────────────────────────────────────────────────

    def get_all_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Get info about all available strategies."""
        return {
            name: {
                "description": s.description,
                "best_for": s.best_for,
                "engines": s.cognitive_engines,
                "requires_tools": s.requires_tools,
            }
            for name, s in STRATEGIES.items()
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get strategy selector statistics."""
        self._load_meta_learner()
        return {
            "total_strategies": len(STRATEGIES),
            "meta_learner_available": self._meta_learner is not None,
            "cognitive_router_available": self._cognitive_router is not None,
            "meta_learning_stats": self._meta_learner.get_stats() if self._meta_learner else {},
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

strategy_selector = StrategySelector()
