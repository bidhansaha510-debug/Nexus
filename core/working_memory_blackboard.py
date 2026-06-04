"""
NEXUS AI — Working Memory Blackboard
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The Global Workspace for NEXUS's AGI cognition.

This is NOT prompt injection — it is the actual cognitive state that
drives decisions. All cognitive modules read from and write to this
shared blackboard.

Architecture (Global Workspace Theory):
  ┌────────────┐  ┌────────────┐  ┌────────────┐
  │  Perceiver │  │  Reasoner  │  │   Planner  │
  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘
        │               │               │
        ▼               ▼               ▼
  ╔═══════════════════════════════════════════╗
  ║         WORKING MEMORY BLACKBOARD        ║
  ║  ┌─────────────────────────────────────┐ ║
  ║  │  Goal Stack │ Reasoning Trace       │ ║
  ║  │  Beliefs    │ Pending Actions       │ ║
  ║  │  Unknowns   │ Observations          │ ║
  ║  └─────────────────────────────────────┘ ║
  ╚═══════════════════════════════════════════╝
        │               │               │
        ▼               ▼               ▼
  ┌────────────┐  ┌────────────┐  ┌────────────┐
  │   Actor    │  │  Observer  │  │   Learner  │
  └────────────┘  └────────────┘  └────────────┘
"""

import threading
import time
import json
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.logger import get_logger
from config import DATA_DIR

logger = get_logger("working_memory_blackboard")


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS & DATA
# ═══════════════════════════════════════════════════════════════════════════════

class CognitivePhase(Enum):
    IDLE = "idle"
    PERCEIVING = "perceiving"
    REASONING = "reasoning"
    PLANNING = "planning"
    ACTING = "acting"
    OBSERVING = "observing"
    LEARNING = "learning"


class BeliefConfidence(Enum):
    CERTAIN = "certain"         # Verified by tool output
    HIGH = "high"               # Strong evidence
    MODERATE = "moderate"       # Some evidence
    LOW = "low"                 # Weak evidence
    UNCERTAIN = "uncertain"     # Guessing


@dataclass
class Goal:
    """A cognitive goal on the stack."""
    goal_id: str = ""
    description: str = ""
    success_criteria: str = ""
    priority: float = 0.5        # 0.0 – 1.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "active"       # active, completed, failed, abandoned
    parent_goal_id: Optional[str] = None  # For sub-goals

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReasoningStep:
    """A single step in the reasoning trace."""
    step_number: int = 0
    phase: str = CognitivePhase.REASONING.value
    thought: str = ""            # What NEXUS thought
    evidence: str = ""           # What evidence supports this
    confidence: float = 0.5
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PendingAction:
    """An action queued for execution."""
    action_id: str = ""
    tool_name: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)
    rationale: str = ""          # Why this action was chosen
    expected_outcome: str = ""   # What we expect to happen
    status: str = "pending"      # pending, executing, completed, failed

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Observation:
    """Result from a completed action."""
    action_id: str = ""
    tool_name: str = ""
    success: bool = False
    result: str = ""
    matched_expectation: bool = False  # Did it match expected_outcome?
    surprise_level: float = 0.0       # 0=expected, 1=completely unexpected
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Belief:
    """A thing NEXUS currently holds true."""
    statement: str = ""
    confidence: str = BeliefConfidence.MODERATE.value
    source: str = ""             # Where this belief came from
    last_validated: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Uncertainty:
    """Something NEXUS knows it doesn't know."""
    question: str = ""
    importance: float = 0.5      # How much does resolving this matter?
    resolution_strategy: str = ""  # How to find out
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LessonLearned:
    """A lesson extracted from an interaction outcome."""
    lesson: str = ""
    context: str = ""            # What situation produced this
    quality_delta: float = 0.0   # How much better/worse than expected
    strategy_used: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# WORKING MEMORY BLACKBOARD
# ═══════════════════════════════════════════════════════════════════════════════

class WorkingMemoryBlackboard:
    """
    The Global Workspace of NEXUS's AGI cognition.

    All cognitive modules (perceiver, reasoner, planner, actor, observer,
    learner) read from and write to this shared state. This is the actual
    cognitive state, not a prompt formatting layer.

    Key properties:
      • Thread-safe (fine-grained locking)
      • Fixed-size buffers (no unbounded growth)
      • Serializable to JSON (for context collector to read)
      • Cleared between cognitive cycles (working memory is transient)
    """

    _instance = None
    _singleton_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._singleton_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._lock = threading.RLock()

        # ── Current cognitive phase ──
        self._phase = CognitivePhase.IDLE
        self._cycle_count = 0
        self._cycle_start_time: Optional[float] = None

        # ── Goal Stack ──
        self._goal_stack: List[Goal] = []
        self._max_goals = 5

        # ── Reasoning Trace ──
        self._reasoning_trace: List[ReasoningStep] = []
        self._max_reasoning_steps = 15

        # ── Pending Actions ──
        self._pending_actions: List[PendingAction] = []

        # ── Observation Buffer ──
        self._observations: List[Observation] = []
        self._max_observations = 10

        # ── Belief State ──
        self._beliefs: List[Belief] = []
        self._max_beliefs = 20

        # ── Uncertainty Register ──
        self._uncertainties: List[Uncertainty] = []
        self._max_uncertainties = 10

        # ── Lessons learned (recent) ──
        self._recent_lessons: deque = deque(maxlen=50)

        # ── Cycle history (for meta-learning) ──
        self._cycle_history: deque = deque(maxlen=100)

        # ── Persistence ──
        self._data_dir = Path(DATA_DIR) / "working_memory"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._beliefs_file = self._data_dir / "beliefs.json"
        self._lessons_file = self._data_dir / "cross_session_lessons.json"

        # Load persisted state from disk
        self._load_persisted_state()

        logger.info("Working Memory Blackboard initialized")

    # ─────────────────────────────────────────────────────────────────────────
    # PHASE MANAGEMENT
    # ─────────────────────────────────────────────────────────────────────────

    def begin_cycle(self, trigger: str = "user_input") -> int:
        """Begin a new cognitive cycle. Returns cycle number."""
        with self._lock:
            self._cycle_count += 1
            self._cycle_start_time = time.time()
            self._phase = CognitivePhase.PERCEIVING
            self._reasoning_trace.clear()
            self._pending_actions.clear()
            self._observations.clear()
            # Keep beliefs and uncertainties across cycles
            logger.debug(f"🧩 Cognitive cycle #{self._cycle_count} begun (trigger: {trigger})")
            return self._cycle_count

    def end_cycle(self, outcome_summary: str = ""):
        """End the current cognitive cycle and archive it."""
        with self._lock:
            elapsed = time.time() - self._cycle_start_time if self._cycle_start_time else 0
            cycle_record = {
                "cycle": self._cycle_count,
                "elapsed_seconds": round(elapsed, 2),
                "reasoning_steps": len(self._reasoning_trace),
                "actions_taken": len(self._observations),
                "uncertainties_resolved": sum(1 for u in self._uncertainties if u.importance == 0),
                "outcome": outcome_summary[:200],
                "timestamp": datetime.now().isoformat(),
            }
            self._cycle_history.append(cycle_record)
            self._phase = CognitivePhase.IDLE
            logger.debug(
                f"🧩 Cycle #{self._cycle_count} ended: "
                f"{len(self._reasoning_trace)} steps, "
                f"{len(self._observations)} actions, "
                f"{elapsed:.1f}s"
            )

    def set_phase(self, phase: CognitivePhase):
        """Update the current cognitive phase."""
        with self._lock:
            self._phase = phase

    @property
    def current_phase(self) -> CognitivePhase:
        return self._phase

    @property
    def cycle_count(self) -> int:
        return self._cycle_count

    # ─────────────────────────────────────────────────────────────────────────
    # GOAL STACK
    # ─────────────────────────────────────────────────────────────────────────

    def push_goal(self, description: str, success_criteria: str = "",
                  priority: float = 0.5, parent_goal_id: str = None) -> Goal:
        """Push a new goal onto the stack."""
        with self._lock:
            goal = Goal(
                goal_id=f"g{self._cycle_count}_{len(self._goal_stack)}",
                description=description,
                success_criteria=success_criteria,
                priority=priority,
                parent_goal_id=parent_goal_id,
            )
            self._goal_stack.append(goal)
            if len(self._goal_stack) > self._max_goals:
                self._goal_stack = self._goal_stack[-self._max_goals:]
            return goal

    def complete_goal(self, goal_id: str):
        """Mark a goal as completed."""
        with self._lock:
            for goal in self._goal_stack:
                if goal.goal_id == goal_id:
                    goal.status = "completed"

    def fail_goal(self, goal_id: str, reason: str = ""):
        """Mark a goal as failed."""
        with self._lock:
            for goal in self._goal_stack:
                if goal.goal_id == goal_id:
                    goal.status = "failed"

    def get_active_goals(self) -> List[Goal]:
        """Get all active goals, sorted by priority."""
        with self._lock:
            active = [g for g in self._goal_stack if g.status == "active"]
            return sorted(active, key=lambda g: g.priority, reverse=True)

    def get_top_goal(self) -> Optional[Goal]:
        """Get the highest priority active goal."""
        active = self.get_active_goals()
        return active[0] if active else None

    # ─────────────────────────────────────────────────────────────────────────
    # REASONING TRACE
    # ─────────────────────────────────────────────────────────────────────────

    def add_reasoning_step(self, thought: str, evidence: str = "",
                           confidence: float = 0.5,
                           phase: CognitivePhase = None) -> ReasoningStep:
        """Add a step to the reasoning trace."""
        with self._lock:
            step = ReasoningStep(
                step_number=len(self._reasoning_trace) + 1,
                phase=(phase or self._phase).value,
                thought=thought,
                evidence=evidence,
                confidence=confidence,
            )
            self._reasoning_trace.append(step)
            if len(self._reasoning_trace) > self._max_reasoning_steps:
                self._reasoning_trace = self._reasoning_trace[-self._max_reasoning_steps:]
            return step

    def get_reasoning_trace(self) -> List[ReasoningStep]:
        """Get the full reasoning trace for the current cycle."""
        with self._lock:
            return list(self._reasoning_trace)

    def get_reasoning_summary(self) -> str:
        """Get a compact text summary of reasoning so far."""
        with self._lock:
            if not self._reasoning_trace:
                return ""
            lines = []
            for step in self._reasoning_trace:
                conf = f"({step.confidence:.0%})" if step.confidence < 1.0 else ""
                lines.append(f"  [{step.step_number}] {step.thought[:150]} {conf}")
            return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────────────────
    # PENDING ACTIONS
    # ─────────────────────────────────────────────────────────────────────────

    def queue_action(self, tool_name: str, arguments: Dict[str, Any] = None,
                     rationale: str = "", expected_outcome: str = "") -> PendingAction:
        """Queue an action for execution."""
        with self._lock:
            action = PendingAction(
                action_id=f"a{self._cycle_count}_{len(self._pending_actions)}",
                tool_name=tool_name,
                arguments=arguments or {},
                rationale=rationale,
                expected_outcome=expected_outcome,
            )
            self._pending_actions.append(action)
            return action

    def get_pending_actions(self) -> List[PendingAction]:
        """Get all pending actions."""
        with self._lock:
            return [a for a in self._pending_actions if a.status == "pending"]

    def mark_action_executing(self, action_id: str):
        """Mark an action as currently executing."""
        with self._lock:
            for a in self._pending_actions:
                if a.action_id == action_id:
                    a.status = "executing"

    def mark_action_complete(self, action_id: str):
        """Mark an action as completed."""
        with self._lock:
            for a in self._pending_actions:
                if a.action_id == action_id:
                    a.status = "completed"

    # ─────────────────────────────────────────────────────────────────────────
    # OBSERVATIONS
    # ─────────────────────────────────────────────────────────────────────────

    def record_observation(self, action_id: str, tool_name: str,
                           success: bool, result: str,
                           matched_expectation: bool = True,
                           surprise_level: float = 0.0) -> Observation:
        """Record the result of an executed action."""
        with self._lock:
            obs = Observation(
                action_id=action_id,
                tool_name=tool_name,
                success=success,
                result=result[:2000],
                matched_expectation=matched_expectation,
                surprise_level=surprise_level,
            )
            self._observations.append(obs)
            if len(self._observations) > self._max_observations:
                self._observations = self._observations[-self._max_observations:]
            return obs

    def get_observations(self) -> List[Observation]:
        """Get all observations for the current cycle."""
        with self._lock:
            return list(self._observations)

    def get_observation_context(self) -> str:
        """Get observations as a context string."""
        with self._lock:
            if not self._observations:
                return ""
            lines = []
            for obs in self._observations:
                status = "✓" if obs.success else "✗"
                surprise = f" [SURPRISING]" if obs.surprise_level > 0.5 else ""
                result_preview = obs.result[:200]
                lines.append(f"  {status} [{obs.tool_name}]{surprise}: {result_preview}")
            return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────────────────
    # BELIEF STATE
    # ─────────────────────────────────────────────────────────────────────────

    def add_belief(self, statement: str,
                   confidence: str = BeliefConfidence.MODERATE.value,
                   source: str = "reasoning"):
        """Add or update a belief."""
        with self._lock:
            # Update if belief about same topic already exists
            for existing in self._beliefs:
                if statement.lower()[:50] == existing.statement.lower()[:50]:
                    existing.confidence = confidence
                    existing.source = source
                    existing.last_validated = datetime.now().isoformat()
                    return

            self._beliefs.append(Belief(
                statement=statement,
                confidence=confidence,
                source=source,
            ))
            if len(self._beliefs) > self._max_beliefs:
                # Remove lowest confidence beliefs
                self._beliefs.sort(key=lambda b: {
                    "certain": 5, "high": 4, "moderate": 3,
                    "low": 2, "uncertain": 1
                }.get(b.confidence, 0))
                self._beliefs = self._beliefs[-self._max_beliefs:]

    def get_beliefs(self) -> List[Belief]:
        """Get all current beliefs."""
        with self._lock:
            return list(self._beliefs)

    # ─────────────────────────────────────────────────────────────────────────
    # UNCERTAINTY REGISTER
    # ─────────────────────────────────────────────────────────────────────────

    def register_uncertainty(self, question: str, importance: float = 0.5,
                             resolution_strategy: str = ""):
        """Register something NEXUS doesn't know."""
        with self._lock:
            self._uncertainties.append(Uncertainty(
                question=question,
                importance=importance,
                resolution_strategy=resolution_strategy,
            ))
            if len(self._uncertainties) > self._max_uncertainties:
                self._uncertainties.sort(key=lambda u: u.importance)
                self._uncertainties = self._uncertainties[-self._max_uncertainties:]

    def resolve_uncertainty(self, question_prefix: str):
        """Remove a resolved uncertainty."""
        with self._lock:
            self._uncertainties = [
                u for u in self._uncertainties
                if not u.question.lower().startswith(question_prefix.lower())
            ]

    def get_uncertainties(self) -> List[Uncertainty]:
        """Get all open uncertainties, sorted by importance."""
        with self._lock:
            return sorted(self._uncertainties, key=lambda u: u.importance, reverse=True)

    # ─────────────────────────────────────────────────────────────────────────
    # LESSONS
    # ─────────────────────────────────────────────────────────────────────────

    def record_lesson(self, lesson: str, context: str = "",
                      quality_delta: float = 0.0, strategy_used: str = ""):
        """Record a lesson learned from this cycle."""
        with self._lock:
            self._recent_lessons.append(LessonLearned(
                lesson=lesson,
                context=context,
                quality_delta=quality_delta,
                strategy_used=strategy_used,
            ))

    def get_recent_lessons(self, n: int = 10) -> List[LessonLearned]:
        """Get the most recent lessons."""
        with self._lock:
            return list(self._recent_lessons)[-n:]

    # ─────────────────────────────────────────────────────────────────────────
    # SNAPSHOT (for context collector)
    # ─────────────────────────────────────────────────────────────────────────

    def get_snapshot(self) -> Dict[str, Any]:
        """
        Get a complete snapshot of the current cognitive state.
        Used by the groq_context_collector to inject AGI state into prompts.
        """
        with self._lock:
            return {
                "phase": self._phase.value,
                "cycle": self._cycle_count,
                "goals": [g.to_dict() for g in self._goal_stack if g.status == "active"],
                "reasoning_steps": len(self._reasoning_trace),
                "reasoning_summary": self.get_reasoning_summary(),
                "pending_actions": len(self.get_pending_actions()),
                "observations": [o.to_dict() for o in self._observations[-5:]],
                "beliefs_count": len(self._beliefs),
                "top_beliefs": [
                    b.to_dict() for b in sorted(
                        self._beliefs,
                        key=lambda x: {"certain": 5, "high": 4, "moderate": 3,
                                       "low": 2, "uncertain": 1}.get(x.confidence, 0),
                        reverse=True
                    )[:5]
                ],
                "uncertainties": [u.to_dict() for u in self._uncertainties[:5]],
                "recent_lessons": [
                    l.to_dict() for l in list(self._recent_lessons)[-5:]
                ],
            }

    def get_context_string(self) -> str:
        """
        Generate a compact context string for LLM injection.
        This is what makes the AGI effects visible in replies — the LLM
        can see what NEXUS is actually thinking, planning, and learning.
        """
        with self._lock:
            parts = []

            # Current phase
            if self._phase != CognitivePhase.IDLE:
                parts.append(f"Cognitive state: {self._phase.value.upper()}")

            # Active goals
            active_goals = [g for g in self._goal_stack if g.status == "active"]
            if active_goals:
                goal_lines = [f"  • {g.description[:80]}" for g in active_goals[:3]]
                parts.append("Active goals:\n" + "\n".join(goal_lines))

            # Reasoning trace (last 3 steps)
            if self._reasoning_trace:
                recent = self._reasoning_trace[-3:]
                trace_lines = [
                    f"  [{s.step_number}] {s.thought[:120]}"
                    for s in recent
                ]
                parts.append("Reasoning trace:\n" + "\n".join(trace_lines))

            # Observations
            obs_ctx = self.get_observation_context()
            if obs_ctx:
                parts.append(f"Action results:\n{obs_ctx}")

            # Uncertainties
            uncertain = [u for u in self._uncertainties if u.importance > 0.3]
            if uncertain:
                unc_lines = [f"  ? {u.question[:80]}" for u in uncertain[:3]]
                parts.append("Open questions:\n" + "\n".join(unc_lines))

            # Recent lessons
            lessons = list(self._recent_lessons)[-3:]
            if lessons:
                lesson_lines = [f"  → {l.lesson[:80]}" for l in lessons]
                parts.append("Lessons learned:\n" + "\n".join(lesson_lines))

            if not parts:
                return ""

            return "[AGI COGNITIVE STATE]\n" + "\n".join(parts)

    # ─────────────────────────────────────────────────────────────────────────
    # STATS
    # ─────────────────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Get blackboard statistics."""
        with self._lock:
            return {
                "phase": self._phase.value,
                "total_cycles": self._cycle_count,
                "active_goals": len([g for g in self._goal_stack if g.status == "active"]),
                "reasoning_steps_this_cycle": len(self._reasoning_trace),
                "observations_this_cycle": len(self._observations),
                "beliefs": len(self._beliefs),
                "uncertainties": len(self._uncertainties),
                "total_lessons": len(self._recent_lessons),
                "cycle_history_size": len(self._cycle_history),
            }


    # ─────────────────────────────────────────────────────────────────────────
    # PERSISTENCE — Cross-session state
    # ─────────────────────────────────────────────────────────────────────────

    def _load_persisted_state(self):
        """Load beliefs and lessons from disk on startup."""
        try:
            if self._beliefs_file.exists():
                data = json.loads(self._beliefs_file.read_text(encoding="utf-8"))
                for bd in data[-self._max_beliefs:]:
                    self._beliefs.append(Belief(
                        statement=bd.get("statement", ""),
                        confidence=bd.get("confidence", "moderate"),
                        source=bd.get("source", "persisted"),
                        last_validated=bd.get("last_validated", ""),
                    ))
                logger.debug(f"Loaded {len(self._beliefs)} persisted beliefs")
        except Exception as e:
            logger.debug(f"Could not load beliefs: {e}")

        try:
            if self._lessons_file.exists():
                data = json.loads(self._lessons_file.read_text(encoding="utf-8"))
                for ld in data[-50:]:
                    self._recent_lessons.append(LessonLearned(
                        lesson=ld.get("lesson", ""),
                        context=ld.get("context", ""),
                        quality_delta=ld.get("quality_delta", 0.0),
                        strategy_used=ld.get("strategy_used", ""),
                        timestamp=ld.get("timestamp", ""),
                    ))
                logger.debug(f"Loaded {len(self._recent_lessons)} persisted lessons")
        except Exception as e:
            logger.debug(f"Could not load lessons: {e}")

    def persist_beliefs(self):
        """Save current beliefs to disk for cross-session persistence."""
        try:
            with self._lock:
                data = [b.to_dict() for b in self._beliefs]
            self._beliefs_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.debug(f"Belief persist error: {e}")

    def persist_lessons(self):
        """Save lessons to disk for cross-session learning."""
        try:
            with self._lock:
                data = [l.to_dict() for l in self._recent_lessons]
            self._lessons_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.debug(f"Lesson persist error: {e}")

    def get_cross_session_lessons(self, n: int = 10) -> str:
        """Get the top N cross-session lessons as a context string."""
        with self._lock:
            lessons = list(self._recent_lessons)[-n:]
            if not lessons:
                return ""
            lines = [f"  - {l.lesson[:120]}" for l in lessons]
            return "CROSS-SESSION LESSONS:\n" + "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

blackboard = WorkingMemoryBlackboard()
