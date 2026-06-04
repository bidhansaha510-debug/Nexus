"""
NEXUS AI — Recursive Self-Improver
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Closes the loop: failure detection → pattern analysis → prompt evolution
→ A/B testing → permanent improvement.

Unlike SelfEvolution (which modifies CODE), this modifies BEHAVIORAL
PROMPTS — it's faster, safer, and continuously active.

Pipeline:
  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
  │ Failure   │───▶│ Pattern  │───▶│ Prompt   │───▶│  A/B     │
  │ Collector │    │ Analyzer │    │ Evolver  │    │  Tester  │
  └──────────┘    └──────────┘    └──────────┘    └──────────┘
"""

import json
import threading
import time
import uuid
from collections import defaultdict, Counter
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("recursive_improver")


# ═══════════════════════════════════════════════════════════════════════════════
# FAILURE TYPES
# ═══════════════════════════════════════════════════════════════════════════════

FAILURE_TYPES = {
    "hallucination": [
        "makes up facts", "not grounded", "fabricated", "invented",
        "false claim", "didn't actually", "no evidence"
    ],
    "incomplete": [
        "missing", "incomplete", "didn't address", "left out",
        "only partially", "forgot to", "needs more"
    ],
    "wrong_format": [
        "format", "structure", "layout", "should be", "expected",
        "not what was asked", "misunderstood"
    ],
    "too_verbose": [
        "too long", "verbose", "repetitive", "redundant", "wordy",
        "could be shorter", "unnecessary"
    ],
    "too_terse": [
        "too short", "not enough detail", "explain more",
        "lacks depth", "superficial", "shallow"
    ],
    "reasoning_error": [
        "logic", "reasoning", "incorrect", "wrong", "mistake",
        "error in", "flaw", "contradiction", "inconsistent"
    ],
    "off_topic": [
        "off topic", "irrelevant", "didn't answer", "tangent",
        "not what I asked", "unrelated"
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class FailureRecord:
    """Records a single response failure."""
    failure_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    query_summary: str = ""
    query_type: str = "unknown"
    response_summary: str = ""
    critique_score: float = 0.0
    critique_feedback: str = ""
    failure_type: str = "unknown"
    strategy_used: str = "direct"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FailurePattern:
    """A detected pattern across multiple failures."""
    pattern_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    failure_type: str = ""
    query_type: str = ""
    occurrence_count: int = 0
    example_queries: List[str] = field(default_factory=list)
    suggested_fix: str = ""
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PromptImprovement:
    """An evolved prompt fragment for addressing a failure pattern."""
    improvement_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    pattern_id: str = ""
    failure_type: str = ""
    query_type: str = ""
    prompt_fragment: str = ""
    # A/B Testing
    times_tested: int = 0
    avg_score_with: float = 0.0       # Avg score when this prompt is active
    avg_score_without: float = 0.0    # Avg score from historical baseline
    is_active: bool = False           # Currently in use?
    is_proven: bool = False           # Passed A/B test?
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# RECURSIVE SELF-IMPROVER
# ═══════════════════════════════════════════════════════════════════════════════

class RecursiveImprover:
    """
    Learns from failures to automatically improve response quality.

    1. Collects failures (critique score < threshold)
    2. Analyzes patterns across failures
    3. Generates improved prompt fragments
    4. A/B tests improvements
    5. Persists winning improvements
    """

    _instance = None
    _lock = threading.Lock()

    FAILURE_THRESHOLD = 0.5  # Score below this = failure
    PATTERN_MIN_OCCURRENCES = 3  # Need this many failures to detect a pattern
    AB_TEST_MIN_TRIALS = 5  # Need this many trials to judge an improvement

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

        self._data_dir = Path(DATA_DIR) / "self_improvement"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        # Failure tracking
        self._failures: List[FailureRecord] = []
        self._max_failures = 500

        # Detected patterns
        self._patterns: List[FailurePattern] = []

        # Prompt improvements (including those being A/B tested)
        self._improvements: List[PromptImprovement] = []

        # LLM for prompt generation (lazy loaded)
        self._llm = None

        self._load_data()

        active_count = sum(1 for i in self._improvements if i.is_active)
        proven_count = sum(1 for i in self._improvements if i.is_proven)
        logger.info(f"[SELF-IMPROVER] Initialized: {len(self._failures)} failures tracked, "
                    f"{len(self._patterns)} patterns, {active_count} active / {proven_count} proven improvements")

    # ─────────────────────────────────────────────────────────────────────────
    # FAILURE COLLECTION
    # ─────────────────────────────────────────────────────────────────────────

    def record_failure(
        self,
        query: str,
        response: str,
        critique_score: float,
        critique_feedback: str = "",
        query_type: str = "unknown",
        strategy_used: str = "direct",
    ) -> Optional[FailureRecord]:
        """Record a response failure for pattern analysis."""
        if critique_score >= self.FAILURE_THRESHOLD:
            return None  # Not a failure

        # Classify the failure type
        failure_type = self._classify_failure(critique_feedback, response)

        record = FailureRecord(
            query_summary=query[:200],
            query_type=query_type,
            response_summary=response[:200],
            critique_score=critique_score,
            critique_feedback=critique_feedback[:300],
            failure_type=failure_type,
            strategy_used=strategy_used,
        )

        self._failures.append(record)
        if len(self._failures) > self._max_failures:
            self._failures = self._failures[-self._max_failures:]

        logger.debug(f"[SELF-IMPROVER] Failure recorded: {failure_type} "
                    f"(score={critique_score:.2f})")

        # Check for patterns after accumulating enough failures
        if len(self._failures) % 5 == 0:
            self._analyze_patterns()

        # Save periodically
        if len(self._failures) % 10 == 0:
            self._save_data()

        return record

    def _classify_failure(self, feedback: str, response: str) -> str:
        """Classify the type of failure based on critique feedback."""
        feedback_lower = (feedback + " " + response[:100]).lower()

        best_type = "unknown"
        best_score = 0

        for failure_type, keywords in FAILURE_TYPES.items():
            score = sum(1 for kw in keywords if kw in feedback_lower)
            if score > best_score:
                best_score = score
                best_type = failure_type

        return best_type

    # ─────────────────────────────────────────────────────────────────────────
    # PATTERN ANALYSIS
    # ─────────────────────────────────────────────────────────────────────────

    def _analyze_patterns(self) -> None:
        """Detect recurring failure patterns."""
        # Group failures by (failure_type, query_type)
        groups: Dict[Tuple[str, str], List[FailureRecord]] = defaultdict(list)
        for f in self._failures[-100:]:  # Analyze recent failures
            groups[(f.failure_type, f.query_type)].append(f)

        for (ftype, qtype), failures in groups.items():
            if len(failures) < self.PATTERN_MIN_OCCURRENCES:
                continue

            # Check if we already have this pattern
            existing = next(
                (p for p in self._patterns
                 if p.failure_type == ftype and p.query_type == qtype),
                None
            )

            if existing:
                existing.occurrence_count = len(failures)
                existing.confidence = min(0.95, len(failures) / 20.0)
                continue

            # New pattern detected
            pattern = FailurePattern(
                failure_type=ftype,
                query_type=qtype,
                occurrence_count=len(failures),
                example_queries=[f.query_summary[:100] for f in failures[:3]],
                suggested_fix=self._generate_fix_suggestion(ftype, qtype),
                confidence=min(0.95, len(failures) / 20.0),
            )
            self._patterns.append(pattern)

            logger.info(f"[SELF-IMPROVER] Pattern detected: {ftype} in {qtype} "
                       f"({len(failures)} occurrences)")

            # Auto-generate a prompt improvement for this pattern
            self._generate_improvement(pattern)

    def _generate_fix_suggestion(self, failure_type: str, query_type: str) -> str:
        """Generate a human-readable fix suggestion."""
        suggestions = {
            "hallucination": "Add explicit instruction to only state facts that are verifiable",
            "incomplete": "Add instruction to check that all parts of the question are addressed",
            "wrong_format": "Add instruction to match the expected output format",
            "too_verbose": "Add instruction to be concise and avoid repetition",
            "too_terse": "Add instruction to provide thorough explanations with examples",
            "reasoning_error": "Add instruction to verify each logical step before proceeding",
            "off_topic": "Add instruction to re-read the question and stay focused on it",
        }
        return suggestions.get(failure_type,
                              f"Improve handling of {failure_type} in {query_type} queries")

    # ─────────────────────────────────────────────────────────────────────────
    # PROMPT EVOLUTION
    # ─────────────────────────────────────────────────────────────────────────

    def _generate_improvement(self, pattern: FailurePattern) -> None:
        """Generate a prompt improvement to address a failure pattern."""
        # Check if we already have an improvement for this pattern
        existing = next(
            (i for i in self._improvements if i.pattern_id == pattern.pattern_id),
            None
        )
        if existing:
            return

        # Generate the prompt fragment based on the failure type
        prompt_fragments = {
            "hallucination": (
                "CRITICAL: Do NOT invent, fabricate, or hallucinate information. "
                "If you are unsure about a fact, explicitly say so. Only state things "
                "you can ground in your training data or provided context."
            ),
            "incomplete": (
                "Before finalizing your response, re-read the original question and check: "
                "Have I addressed EVERY part of what was asked? If the question has multiple "
                "parts or sub-questions, make sure each one is answered."
            ),
            "wrong_format": (
                "Pay close attention to the expected format of the response. "
                "If code is requested, provide code. If a list is requested, use a list. "
                "Match the format the user expects."
            ),
            "too_verbose": (
                "Be concise. Avoid unnecessary repetition and filler phrases. "
                "Get to the point quickly while still being thorough."
            ),
            "too_terse": (
                "Provide thorough, detailed explanations. Include examples where helpful. "
                "Don't assume the user already knows the context — explain your reasoning."
            ),
            "reasoning_error": (
                "Double-check your reasoning step by step. After each logical step, pause and "
                "verify: does this follow from the previous step? Is there an error in my logic? "
                "If you find an inconsistency, correct it before continuing."
            ),
            "off_topic": (
                "Stay focused on exactly what was asked. Before responding, re-read the "
                "question carefully. If you feel yourself going on a tangent, stop and "
                "redirect back to the core question."
            ),
        }

        fragment = prompt_fragments.get(
            pattern.failure_type,
            f"Exercise extra care when handling {pattern.failure_type} issues in "
            f"{pattern.query_type} queries."
        )

        improvement = PromptImprovement(
            pattern_id=pattern.pattern_id,
            failure_type=pattern.failure_type,
            query_type=pattern.query_type,
            prompt_fragment=fragment,
            avg_score_without=self._get_baseline_score(pattern.query_type),
            is_active=True,  # Start testing immediately
        )

        self._improvements.append(improvement)
        logger.info(f"[SELF-IMPROVER] Generated improvement for {pattern.failure_type}: "
                   f"'{fragment[:80]}...'")

    def _get_baseline_score(self, query_type: str) -> float:
        """Get the average score for a query type (baseline for A/B testing)."""
        scores = [
            f.critique_score for f in self._failures
            if f.query_type == query_type
        ]
        if not scores:
            return 0.5
        return sum(scores) / len(scores)

    # ─────────────────────────────────────────────────────────────────────────
    # A/B TESTING
    # ─────────────────────────────────────────────────────────────────────────

    def record_test_result(
        self, query_type: str, critique_score: float
    ) -> None:
        """Record a test result for active improvements."""
        for imp in self._improvements:
            if not imp.is_active or imp.is_proven:
                continue
            if imp.query_type != query_type and imp.query_type != "unknown":
                continue

            # Update running average
            imp.times_tested += 1
            prev_total = imp.avg_score_with * (imp.times_tested - 1)
            imp.avg_score_with = (prev_total + critique_score) / imp.times_tested

            # Check if we have enough data to judge
            if imp.times_tested >= self.AB_TEST_MIN_TRIALS:
                improvement_delta = imp.avg_score_with - imp.avg_score_without

                if improvement_delta > 0.05:
                    # Improvement is better — keep it
                    imp.is_proven = True
                    logger.info(
                        f"[SELF-IMPROVER] Improvement PROVEN: {imp.failure_type} "
                        f"(+{improvement_delta:.3f} score improvement)"
                    )
                elif improvement_delta < -0.05:
                    # Improvement is worse — deactivate
                    imp.is_active = False
                    logger.info(
                        f"[SELF-IMPROVER] Improvement REJECTED: {imp.failure_type} "
                        f"({improvement_delta:.3f} worse)"
                    )
                # else: inconclusive, keep testing

    # ─────────────────────────────────────────────────────────────────────────
    # PROMPT GENERATION
    # ─────────────────────────────────────────────────────────────────────────

    def get_active_improvements(self, query_type: str = None) -> str:
        """
        Get all active prompt improvements as a system prompt addition.

        These are improvements that are either proven or currently being A/B tested.
        """
        fragments = []

        for imp in self._improvements:
            if not imp.is_active:
                continue
            # Apply if query type matches or improvement is for all types
            if query_type and imp.query_type not in ("unknown", query_type):
                continue
            fragments.append(imp.prompt_fragment)

        if not fragments:
            return ""

        return "\n\n[Self-Improvement Directives]\n" + "\n".join(
            f"• {f}" for f in fragments
        )

    # ─────────────────────────────────────────────────────────────────────────
    # PERSISTENCE
    # ─────────────────────────────────────────────────────────────────────────

    def _save_data(self) -> None:
        """Persist self-improvement data."""
        try:
            data = {
                "failures": [f.to_dict() for f in self._failures[-200:]],
                "patterns": [p.to_dict() for p in self._patterns],
                "improvements": [i.to_dict() for i in self._improvements],
                "saved_at": datetime.now().isoformat(),
            }
            path = self._data_dir / "recursive_improver.json"
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"[SELF-IMPROVER] Save failed: {e}")

    def _load_data(self) -> None:
        """Load self-improvement data."""
        try:
            path = self._data_dir / "recursive_improver.json"
            if not path.exists():
                return

            with open(path, "r") as f:
                data = json.load(f)

            for fd in data.get("failures", []):
                self._failures.append(FailureRecord(**{
                    k: v for k, v in fd.items()
                    if k in FailureRecord.__dataclass_fields__
                }))

            for pd in data.get("patterns", []):
                self._patterns.append(FailurePattern(**{
                    k: v for k, v in pd.items()
                    if k in FailurePattern.__dataclass_fields__
                }))

            for idata in data.get("improvements", []):
                self._improvements.append(PromptImprovement(**{
                    k: v for k, v in idata.items()
                    if k in PromptImprovement.__dataclass_fields__
                }))

        except Exception as e:
            logger.warning(f"[SELF-IMPROVER] Load failed (starting fresh): {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC STATS
    # ─────────────────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Get self-improvement statistics."""
        return {
            "total_failures_tracked": len(self._failures),
            "patterns_detected": len(self._patterns),
            "improvements_total": len(self._improvements),
            "improvements_active": sum(1 for i in self._improvements if i.is_active),
            "improvements_proven": sum(1 for i in self._improvements if i.is_proven),
            "improvements_rejected": sum(
                1 for i in self._improvements if not i.is_active and not i.is_proven
            ),
            "failure_type_distribution": dict(Counter(
                f.failure_type for f in self._failures[-100:]
            )),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

recursive_improver = RecursiveImprover()
