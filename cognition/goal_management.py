"""
NEXUS AI — Goal Management Engine
Goal decomposition, prioritization, conflict resolution,
goal tracking, subgoal generation, progress monitoring.
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

logger = get_logger("goal_management")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)


class GoalPriority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    OPTIONAL = "optional"


class GoalStatus(Enum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    PAUSED = "paused"


class GoalConflictType(Enum):
    RESOURCE = "resource"
    TIME = "time"
    VALUE = "value"
    LOGICAL = "logical"
    DEPENDENCY = "dependency"


@dataclass
class Goal:
    goal_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    description: str = ""
    priority: GoalPriority = GoalPriority.MEDIUM
    status: GoalStatus = GoalStatus.PROPOSED
    subgoals: List[Dict[str, Any]] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    deadline: str = ""
    progress: float = 0.0
    metrics: Dict[str, Any] = field(default_factory=dict)
    blockers: List[str] = field(default_factory=list)
    parent_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "goal_id": self.goal_id, "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "subgoals": self.subgoals, "dependencies": self.dependencies,
            "deadline": self.deadline, "progress": self.progress,
            "metrics": self.metrics, "blockers": self.blockers,
            "parent_id": self.parent_id, "created_at": self.created_at
        }


@dataclass
class GoalConflict:
    conflict_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    goal_a: str = ""
    goal_b: str = ""
    conflict_type: GoalConflictType = GoalConflictType.RESOURCE
    description: str = ""
    resolution: str = ""
    resolved: bool = False

    def to_dict(self) -> Dict:
        return {
            "conflict_id": self.conflict_id, "goal_a": self.goal_a,
            "goal_b": self.goal_b,
            "conflict_type": self.conflict_type.value,
            "description": self.description,
            "resolution": self.resolution, "resolved": self.resolved
        }


class GoalManagementEngine:
    """
    Goal decomposition, prioritization, conflict resolution,
    progress tracking, and strategic alignment.
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

        self._goals: Dict[str, Goal] = {}
        self._conflicts: List[GoalConflict] = []
        self._running = False
        self._data_file = COGNITION_DIR / "goal_management.json"

        self._stats = {
            "total_goals": 0, "active_goals": 0,
            "completed_goals": 0, "total_conflicts": 0,
            "total_decompositions": 0
        }

        self._load_data()
        logger.info("✅ Goal Management Engine initialized")

    def start(self):
        self._running = True
        logger.info("🎯 Goal Management started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🎯 Goal Management stopped")

    def decompose_goal(self, goal_description: str) -> Goal:
        """Decompose a high-level goal into subgoals."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Decompose this goal into actionable subgoals:\n{goal_description}\n\n"
                f"Return JSON:\n"
                f'{{"title": "str", "description": "str", '
                f'"priority": "critical|high|medium|low|optional", '
                f'"subgoals": [{{"title": "str", "description": "str", '
                f'"effort": "small|medium|large", '
                f'"dependencies": ["str"], '
                f'"metrics": {{"success_criteria": "str"}}}}'
                f'], '
                f'"deadline_suggestion": "str", '
                f'"metrics": {{"kpis": ["str"], "success_definition": "str"}}, '
                f'"risks": ["str"]}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.3)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            gp_map = {g.value: g for g in GoalPriority}
            goal = Goal(
                title=data.get("title", goal_description[:50]),
                description=data.get("description", goal_description),
                priority=gp_map.get(data.get("priority", "medium"), GoalPriority.MEDIUM),
                status=GoalStatus.PROPOSED,
                subgoals=data.get("subgoals", []),
                deadline=data.get("deadline_suggestion", ""),
                metrics=data.get("metrics", {})
            )

            self._goals[goal.goal_id] = goal
            self._stats["total_goals"] += 1
            self._stats["total_decompositions"] += 1
            self._save_data()
            return goal

        except Exception as e:
            logger.debug(f"Goal decomposition failed: {e}")
            return Goal(title=goal_description)

    def prioritize_goals(self, goals_text: str) -> Dict[str, Any]:
        """Prioritize a set of goals."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Prioritize these goals using Eisenhower matrix + impact analysis:\n"
                f"{goals_text}\n\n"
                f"Return JSON:\n"
                f'{{"prioritized": [{{"goal": "str", "priority": "critical|high|medium|low", '
                f'"urgency": 0.0-1.0, "importance": 0.0-1.0, '
                f'"impact": 0.0-1.0, "effort": 0.0-1.0, '
                f'"roi_score": 0.0-1.0, "quadrant": "do_first|schedule|delegate|eliminate"}}], '
                f'"recommended_order": ["str"], '
                f'"quick_wins": ["str"], '
                f'"strategic_goals": ["str"]}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.3)
            if not response.success or not response.text:
                return {"prioritized": [], "recommended_order": []}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"prioritized": [], "recommended_order": []}
            return data
        except Exception as e:
            logger.debug(f"Goal prioritization failed: {e}")
            return {"prioritized": [], "recommended_order": []}

    def resolve_conflict(self, goal_a: str, goal_b: str) -> GoalConflict:
        """Resolve conflict between two competing goals."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Resolve the conflict between these two goals:\n"
                f"Goal A: {goal_a}\nGoal B: {goal_b}\n\n"
                f"Return JSON:\n"
                f'{{"conflict_type": "resource|time|value|logical|dependency", '
                f'"description": "nature of the conflict", '
                f'"resolution": "recommended resolution", '
                f'"compromise_options": ["str"], '
                f'"can_coexist": true/false, '
                f'"priority_recommendation": "A|B|both|neither", '
                f'"reasoning": "str"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.3)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            ct_map = {c.value: c for c in GoalConflictType}
            conflict = GoalConflict(
                goal_a=goal_a, goal_b=goal_b,
                conflict_type=ct_map.get(data.get("conflict_type", "resource"), GoalConflictType.RESOURCE),
                description=data.get("description", ""),
                resolution=data.get("resolution", ""),
                resolved=True
            )

            self._conflicts.append(conflict)
            self._stats["total_conflicts"] += 1
            self._save_data()
            return conflict

        except Exception as e:
            logger.debug(f"Conflict resolution failed: {e}")
            return GoalConflict(goal_a=goal_a, goal_b=goal_b)

    def track_progress(self, goal: str, update: str) -> Dict[str, Any]:
        """Track progress on a goal and suggest next steps."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Track progress and suggest next steps:\n"
                f"Goal: {goal}\nUpdate: {update}\n\n"
                f"Return JSON:\n"
                f'{{"progress_percentage": 0-100, '
                f'"milestones_completed": ["str"], '
                f'"remaining_milestones": ["str"], '
                f'"blockers": ["str"], '
                f'"next_steps": ["str"], '
                f'"on_track": true/false, '
                f'"estimated_completion": "str", '
                f'"recommendations": ["str"]}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.3)
            if not response.success or not response.text:
                return {"progress_percentage": 0, "on_track": False}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"progress_percentage": 0, "on_track": False}
            return data
        except Exception as e:
            logger.debug(f"Progress tracking failed: {e}")
            return {"progress_percentage": 0, "on_track": False}

    def get_active_goals(self) -> List[Dict]:
        return [g.to_dict() for g in self._goals.values()
                if g.status in (GoalStatus.ACTIVE, GoalStatus.IN_PROGRESS)]

    def _save_data(self):
        try:
            data = {
                "goals": {gid: g.to_dict() for gid, g in list(self._goals.items())[-200:]},
                "conflicts": [c.to_dict() for c in self._conflicts[-100:]],
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
                logger.info("📂 Loaded goal management data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats,
                "current_active_goals": len(self.get_active_goals())}


goal_management = GoalManagementEngine()
