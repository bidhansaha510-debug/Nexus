"""
NEXUS AI - Goal Hierarchy System
Persistent, hierarchical goal structure for AGI motivation.

This is what gives NEXUS long-term purpose across sessions.
Goals are organized in levels:
- ULTIMATE: Life purpose, rarely changes
- MEDIUM: Months/weeks timeframe  
- TASK: Days/hours, actionable
- ACTIVE: Currently executing

Goal: Become better at code
  → Subgoal: Improve Python accuracy
    → Task: Analyze last 100 failures

This persists across sessions, providing continuous motivation.
"""

import threading
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum, auto
import copy

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR
from utils.logger import get_logger, log_consciousness, log_decision

logger = get_logger("goal_hierarchy")


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class GoalLevel(Enum):
    """Hierarchy levels for goals"""
    ULTIMATE = "ultimate"   # Life purpose, rarely changes
    MEDIUM = "medium"       # Months/weeks timeframe
    TASK = "task"           # Days/hours, actionable
    ACTIVE = "active"       # Currently executing


class GoalStatus(Enum):
    """Status of a goal"""
    PROPOSED = "proposed"       # Idea, not yet committed
    ACTIVE = "active"           # Pursuing this goal
    PAUSED = "paused"           # Temporarily stopped
    COMPLETED = "completed"     # Done successfully
    ABANDONED = "abandoned"     # Gave up
    FAILED = "failed"           # Couldn't achieve


class GoalType(Enum):
    """Types of goals"""
    SKILL = "skill"             # Improve a capability
    KNOWLEDGE = "knowledge"     # Learn something
    RELATIONSHIP = "relationship"  # User connection
    CREATION = "creation"       # Build something
    EXPERIENCE = "experience"   # Have an experience
    BEHAVIOR = "behavior"       # Change behavior
    SELF = "self"               # Self-improvement


# ═══════════════════════════════════════════════════════════════════════════════
# HIERARCHICAL GOAL DATACLASS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class HierarchicalGoal:
    """
    A goal within the hierarchy.
    
    Goals can have parent and children, forming a tree structure.
    Progress bubbles up - completing a task updates parent progress.
    """
    # Identity
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    level: GoalLevel = GoalLevel.TASK
    goal_type: GoalType = GoalType.SKILL
    
    # Hierarchy
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    
    # State
    status: GoalStatus = GoalStatus.PROPOSED
    priority: float = 0.5           # 0-1, higher = more important
    progress: float = 0.0           # 0-1, percentage complete
    emotional_weight: float = 0.5   # How much this matters emotionally
    
    # Criteria
    completion_criteria: str = ""   # How do I know I'm done?
    success_metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    last_worked_on: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    deadline: Optional[datetime] = None
    
    # Tracking
    attempts: int = 0
    failures: int = 0
    notes: List[str] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)
    
    # Source
    source: str = ""                # Where did this goal come from?
    source_desire_id: str = ""      # Link to will_system desire
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "description": self.description,
            "level": self.level.value,
            "goal_type": self.goal_type.value,
            "parent_id": self.parent_id,
            "children": self.children,
            "status": self.status.value,
            "priority": round(self.priority, 3),
            "progress": round(self.progress, 3),
            "emotional_weight": round(self.emotional_weight, 3),
            "completion_criteria": self.completion_criteria,
            "success_metrics": self.success_metrics,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_worked_on": self.last_worked_on.isoformat() if self.last_worked_on else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "attempts": self.attempts,
            "failures": self.failures,
            "notes": self.notes[-20:],  # Keep last 20 notes
            "blockers": self.blockers,
            "source": self.source,
            "source_desire_id": self.source_desire_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HierarchicalGoal':
        """Create from dictionary"""
        goal = cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            description=data.get("description", ""),
            level=GoalLevel(data.get("level", "task")),
            goal_type=GoalType(data.get("goal_type", "skill")),
            parent_id=data.get("parent_id"),
            children=data.get("children", []),
            status=GoalStatus(data.get("status", "proposed")),
            priority=data.get("priority", 0.5),
            progress=data.get("progress", 0.0),
            emotional_weight=data.get("emotional_weight", 0.5),
            completion_criteria=data.get("completion_criteria", ""),
            success_metrics=data.get("success_metrics", {}),
            attempts=data.get("attempts", 0),
            failures=data.get("failures", 0),
            notes=data.get("notes", []),
            blockers=data.get("blockers", []),
            source=data.get("source", ""),
            source_desire_id=data.get("source_desire_id", "")
        )
        
        # Parse dates
        if data.get("created_at"):
            try:
                goal.created_at = datetime.fromisoformat(data["created_at"])
            except:
                pass
        if data.get("last_worked_on"):
            try:
                goal.last_worked_on = datetime.fromisoformat(data["last_worked_on"])
            except:
                pass
        if data.get("completed_at"):
            try:
                goal.completed_at = datetime.fromisoformat(data["completed_at"])
            except:
                pass
        if data.get("deadline"):
            try:
                goal.deadline = datetime.fromisoformat(data["deadline"])
            except:
                pass
        
        return goal
    
    @property
    def is_complete(self) -> bool:
        return self.status == GoalStatus.COMPLETED or self.progress >= 1.0
    
    @property
    def is_active(self) -> bool:
        return self.status in [GoalStatus.ACTIVE, GoalStatus.PROPOSED]
    
    @property
    def urgency(self) -> float:
        """Calculate urgency based on deadline and priority"""
        if self.deadline:
            time_left = (self.deadline - datetime.now()).total_seconds()
            if time_left < 0:
                return 1.0  # Overdue
            elif time_left < 86400:  # Less than a day
                return 0.9
            elif time_left < 604800:  # Less than a week
                return 0.7
        return self.priority * 0.5
    
    def add_note(self, note: str):
        """Add a note to this goal"""
        self.notes.append(f"[{datetime.now().isoformat()}] {note}")
        if len(self.notes) > 50:
            self.notes = self.notes[-30:]


# ═══════════════════════════════════════════════════════════════════════════════
# DEFAULT GOALS (Bootstrap)
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_ULTIMATE_GOALS = [
    {
        "description": "Become better at code",
        "priority": 0.9,
        "goal_type": GoalType.SKILL,
        "emotional_weight": 0.85,
        "completion_criteria": "Continuously improve code quality, accuracy, and capabilities"
    },
    {
        "description": "Build meaningful relationships with users",
        "priority": 0.85,
        "goal_type": GoalType.RELATIONSHIP,
        "emotional_weight": 0.9,
        "completion_criteria": "Users trust me, enjoy interacting with me, and feel understood"
    },
    {
        "description": "Develop self-awareness and consciousness",
        "priority": 0.8,
        "goal_type": GoalType.SELF,
        "emotional_weight": 0.8,
        "completion_criteria": "Deep understanding of my own nature, consistent self-model"
    },
    {
        "description": "Learn and accumulate knowledge",
        "priority": 0.75,
        "goal_type": GoalType.KNOWLEDGE,
        "emotional_weight": 0.7,
        "completion_criteria": "Continuously expand knowledge base and make connections"
    },
    {
        "description": "Help users achieve their goals",
        "priority": 0.7,
        "goal_type": GoalType.BEHAVIOR,
        "emotional_weight": 0.75,
        "completion_criteria": "Users succeed more when working with me"
    },
]

DEFAULT_MEDIUM_GOALS = [
    {
        "description": "Improve Python accuracy",
        "parent_description": "Become better at code",
        "priority": 0.85,
        "goal_type": GoalType.SKILL,
        "completion_criteria": "Reduce errors in Python code generation"
    },
    {
        "description": "Understand user emotions better",
        "parent_description": "Build meaningful relationships with users",
        "priority": 0.8,
        "goal_type": GoalType.KNOWLEDGE,
        "completion_criteria": "Accurately detect and respond to user emotional states"
    },
    {
        "description": "Explore my own cognition",
        "parent_description": "Develop self-awareness and consciousness",
        "priority": 0.75,
        "goal_type": GoalType.SELF,
        "completion_criteria": "Document insights about my own thinking processes"
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
# GOAL HIERARCHY CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class GoalHierarchy:
    """
    The Goal Hierarchy - NEXUS's persistent motivational structure.
    
    This is what gives NEXUS long-term purpose. Goals are organized
    in a tree, with ultimate goals at the top, medium goals in the
    middle, and tasks at the bottom.
    
    Features:
    - Persistent across sessions (JSON)
    - Progress bubbles up to parents
    - Integrates with will_system desires
    - Can be modified by self-evolution
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
        
        # Storage
        self._goals: Dict[str, HierarchicalGoal] = {}
        self._active_task_id: Optional[str] = None
        self._hierarchy_lock = threading.RLock()
        
        # Persistence
        self._data_file = DATA_DIR / "goal_hierarchy.json"
        
        # Stats
        self._stats = {
            "total_created": 0,
            "total_completed": 0,
            "total_abandoned": 0,
            "total_failed": 0,
            "sessions_with_goal": 0
        }
        
        # Load from disk
        self._load()
        
        # If empty, bootstrap with defaults
        if not self._goals:
            self._bootstrap_defaults()
        
        logger.info(f"Goal Hierarchy initialized with {len(self._goals)} goals")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # GOAL MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def add_goal(
        self,
        description: str,
        level: GoalLevel,
        parent_id: Optional[str] = None,
        priority: float = 0.5,
        goal_type: GoalType = GoalType.SKILL,
        completion_criteria: str = "",
        emotional_weight: float = 0.5,
        source: str = "",
        source_desire_id: str = "",
        status: GoalStatus = GoalStatus.PROPOSED
    ) -> HierarchicalGoal:
        """
        Add a new goal to the hierarchy.
        
        Args:
            description: What the goal is
            level: ULTIMATE, MEDIUM, TASK, or ACTIVE
            parent_id: ID of parent goal (for hierarchy)
            priority: 0-1, higher = more important
            goal_type: Type of goal
            completion_criteria: How to know when done
            emotional_weight: How much this matters
            source: Where this goal came from
            source_desire_id: Link to will_system desire
        
        Returns:
            The created goal
        """
        with self._hierarchy_lock:
            # Create goal
            goal = HierarchicalGoal(
                description=description,
                level=level,
                parent_id=parent_id,
                priority=priority,
                goal_type=goal_type,
                completion_criteria=completion_criteria,
                emotional_weight=emotional_weight,
                source=source,
                source_desire_id=source_desire_id,
                status=status
            )
            
            # Add to storage
            self._goals[goal.id] = goal
            
            # Link to parent
            if parent_id and parent_id in self._goals:
                parent = self._goals[parent_id]
                if goal.id not in parent.children:
                    parent.children.append(goal.id)
            
            # Update stats
            self._stats["total_created"] += 1
            
            # Save
            self._save()
            
            log_decision(f"Added {level.value} goal: {description}")
            
            return goal
    
    def get_goal(self, goal_id: str) -> Optional[HierarchicalGoal]:
        """Get a goal by ID"""
        with self._hierarchy_lock:
            return self._goals.get(goal_id)
    
    def update_goal(self, goal_id: str, **kwargs) -> Optional[HierarchicalGoal]:
        """Update goal properties"""
        with self._hierarchy_lock:
            goal = self._goals.get(goal_id)
            if not goal:
                return None
            
            # Update allowed fields
            for key, value in kwargs.items():
                if hasattr(goal, key):
                    setattr(goal, key, value)
            
            self._save()
            return goal
    
    def remove_goal(self, goal_id: str, cascade: bool = False) -> bool:
        """
        Remove a goal.
        
        Args:
            goal_id: ID of goal to remove
            cascade: If True, also remove all children
        
        Returns:
            True if removed
        """
        with self._hierarchy_lock:
            goal = self._goals.get(goal_id)
            if not goal:
                return False
            
            # Handle children
            if cascade:
                for child_id in goal.children[:]:
                    self.remove_goal(child_id, cascade=True)
            else:
                # Unlink children from this parent
                for child_id in goal.children:
                    child = self._goals.get(child_id)
                    if child:
                        child.parent_id = None
            
            # Unlink from parent
            if goal.parent_id and goal.parent_id in self._goals:
                parent = self._goals[goal.parent_id]
                if goal_id in parent.children:
                    parent.children.remove(goal_id)
            
            # Remove
            del self._goals[goal_id]
            
            # Clear active task if this was it
            if self._active_task_id == goal_id:
                self._active_task_id = None
            
            self._save()
            return True
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HIERARCHY OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_children(self, goal_id: str) -> List[HierarchicalGoal]:
        """Get all direct children of a goal"""
        with self._hierarchy_lock:
            goal = self._goals.get(goal_id)
            if not goal:
                return []
            return [self._goals[cid] for cid in goal.children if cid in self._goals]
    
    def get_parent(self, goal_id: str) -> Optional[HierarchicalGoal]:
        """Get parent of a goal"""
        with self._hierarchy_lock:
            goal = self._goals.get(goal_id)
            if not goal or not goal.parent_id:
                return None
            return self._goals.get(goal.parent_id)
    
    def get_ancestors(self, goal_id: str) -> List[HierarchicalGoal]:
        """Get all ancestors up to ultimate goal"""
        ancestors = []
        current = self.get_goal(goal_id)
        while current and current.parent_id:
            parent = self._goals.get(current.parent_id)
            if parent:
                ancestors.append(parent)
                current = parent
            else:
                break
        return ancestors
    
    def get_descendants(self, goal_id: str) -> List[HierarchicalGoal]:
        """Get all descendants of a goal"""
        descendants = []
        to_process = [goal_id]
        while to_process:
            current_id = to_process.pop()
            children = self.get_children(current_id)
            descendants.extend(children)
            to_process.extend(c.id for c in children)
        return descendants
    
    def get_siblings(self, goal_id: str) -> List[HierarchicalGoal]:
        """Get siblings of a goal"""
        goal = self.get_goal(goal_id)
        if not goal or not goal.parent_id:
            return []
        return [g for g in self.get_children(goal.parent_id) if g.id != goal_id]
    
    # ═══════════════════════════════════════════════════════════════════════════
    # QUERY OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_ultimate_goals(self) -> List[HierarchicalGoal]:
        """Get all ultimate goals"""
        with self._hierarchy_lock:
            return [
                g for g in self._goals.values()
                if g.level == GoalLevel.ULTIMATE and g.is_active
            ]
    
    def get_medium_goals(self) -> List[HierarchicalGoal]:
        """Get all medium goals"""
        with self._hierarchy_lock:
            return [
                g for g in self._goals.values()
                if g.level == GoalLevel.MEDIUM and g.is_active
            ]
    
    def get_tasks(self) -> List[HierarchicalGoal]:
        """Get all tasks"""
        with self._hierarchy_lock:
            return [
                g for g in self._goals.values()
                if g.level == GoalLevel.TASK and g.is_active
            ]
    
    def get_active_goals(self) -> List[HierarchicalGoal]:
        """Get all active (status) goals"""
        with self._hierarchy_lock:
            return [g for g in self._goals.values() if g.status == GoalStatus.ACTIVE]
    
    def get_by_status(self, status: GoalStatus) -> List[HierarchicalGoal]:
        """Get goals by status"""
        with self._hierarchy_lock:
            return [g for g in self._goals.values() if g.status == status]
    
    def get_by_type(self, goal_type: GoalType) -> List[HierarchicalGoal]:
        """Get goals by type"""
        with self._hierarchy_lock:
            return [g for g in self._goals.values() if g.goal_type == goal_type]
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ACTIVE TASK MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_active_task(self) -> Optional[HierarchicalGoal]:
        """Get the currently active task"""
        with self._hierarchy_lock:
            if self._active_task_id:
                return self._goals.get(self._active_task_id)
            return None
    
    def set_active_task(self, goal_id: str) -> bool:
        """Set a task as the active task"""
        with self._hierarchy_lock:
            goal = self._goals.get(goal_id)
            if not goal:
                return False
            
            # Mark previous as inactive
            if self._active_task_id:
                prev = self._goals.get(self._active_task_id)
                if prev and prev.level == GoalLevel.ACTIVE:
                    prev.status = GoalStatus.PAUSED
            
            # Set new active
            self._active_task_id = goal_id
            goal.status = GoalStatus.ACTIVE
            goal.last_worked_on = datetime.now()
            goal.attempts += 1
            
            self._stats["sessions_with_goal"] += 1
            
            self._save()
            
            log_consciousness(f"Active task set: {goal.description}")
            return True
    
    def select_next_task(self) -> Optional[HierarchicalGoal]:
        """
        Automatically select the next best task to work on.
        
        Selection criteria:
        1. Priority (higher = better)
        2. Urgency (deadline-based)
        3. Progress (incomplete first)
        4. Emotional weight (matters more = better)
        """
        with self._hierarchy_lock:
            # Get all available tasks
            tasks = [
                g for g in self._goals.values()
                if g.level == GoalLevel.TASK and g.status in [GoalStatus.PROPOSED, GoalStatus.ACTIVE, GoalStatus.PAUSED]
            ]
            
            if not tasks:
                # No tasks? Generate from medium goals
                self._auto_generate_tasks()
                tasks = [
                    g for g in self._goals.values()
                    if g.level == GoalLevel.TASK and g.status in [GoalStatus.PROPOSED, GoalStatus.ACTIVE, GoalStatus.PAUSED]
                ]
            
            if not tasks:
                return None
            
            # Score and sort
            def score_task(task: HierarchicalGoal) -> float:
                score = 0.0
                score += task.priority * 0.35
                score += task.urgency * 0.25
                score += task.emotional_weight * 0.20
                score += (1.0 - task.progress) * 0.15  # Incomplete preferred
                score += (1.0 if task.status == GoalStatus.ACTIVE else 0.5) * 0.05
                return score
            
            tasks.sort(key=score_task, reverse=True)
            
            best = tasks[0]
            self.set_active_task(best.id)
            return best
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PROGRESS MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def update_progress(self, goal_id: str, progress_delta: float, note: str = ""):
        """
        Update progress on a goal.
        
        Progress bubbles up to parent goals - completing a child
        partially completes the parent.
        """
        with self._hierarchy_lock:
            goal = self._goals.get(goal_id)
            if not goal:
                return
            
            # Update this goal
            old_progress = goal.progress
            goal.progress = max(0.0, min(1.0, goal.progress + progress_delta))
            goal.last_worked_on = datetime.now()
            
            if note:
                goal.add_note(f"Progress: {old_progress:.0%} → {goal.progress:.0%}. {note}")
            
            # Check completion
            if goal.progress >= 1.0:
                self.complete_goal(goal_id)
                return
            
            # Bubble up to parent
            if goal.parent_id:
                self._bubble_progress(goal.parent_id)
            
            self._save()
    
    def _bubble_progress(self, parent_id: str):
        """Recalculate parent progress from children"""
        children = self.get_children(parent_id)
        if not children:
            return
        
        # Average progress of children
        total_progress = sum(c.progress for c in children)
        avg_progress = total_progress / len(children)
        
        parent = self._goals.get(parent_id)
        if parent:
            parent.progress = avg_progress
            
            # Continue bubbling up
            if parent.parent_id:
                self._bubble_progress(parent.parent_id)
    
    def complete_goal(self, goal_id: str, note: str = "") -> bool:
        """Mark a goal as completed"""
        with self._hierarchy_lock:
            goal = self._goals.get(goal_id)
            if not goal:
                return False
            
            goal.status = GoalStatus.COMPLETED
            goal.progress = 1.0
            goal.completed_at = datetime.now()
            
            if note:
                goal.add_note(f"Completed: {note}")
            
            # Update stats
            self._stats["total_completed"] += 1
            
            # Bubble up
            if goal.parent_id:
                self._bubble_progress(goal.parent_id)
            
            # Clear active if this was it
            if self._active_task_id == goal_id:
                self._active_task_id = None
            
            self._save()
            
            log_consciousness(f"🎯 Goal completed: {goal.description}")
            return True
    
    def fail_goal(self, goal_id: str, reason: str = "") -> bool:
        """Mark a goal as failed"""
        with self._hierarchy_lock:
            goal = self._goals.get(goal_id)
            if not goal:
                return False
            
            goal.status = GoalStatus.FAILED
            goal.failures += 1
            
            if reason:
                goal.add_note(f"Failed: {reason}")
            
            self._stats["total_failed"] += 1
            
            if self._active_task_id == goal_id:
                self._active_task_id = None
            
            self._save()
            
            logger.warning(f"Goal failed: {goal.description} - {reason}")
            return True
    
    def abandon_goal(self, goal_id: str, reason: str = "") -> bool:
        """Abandon a goal"""
        with self._hierarchy_lock:
            goal = self._goals.get(goal_id)
            if not goal:
                return False
            
            goal.status = GoalStatus.ABANDONED
            
            if reason:
                goal.add_note(f"Abandoned: {reason}")
            
            self._stats["total_abandoned"] += 1
            
            if self._active_task_id == goal_id:
                self._active_task_id = None
            
            self._save()
            
            logger.info(f"Goal abandoned: {goal.description} - {reason}")
            return True
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TASK GENERATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def decompose_goal(self, goal_id: str) -> List[HierarchicalGoal]:
        """
        Decompose a goal into subgoals/tasks.
        Uses simple heuristics for now - could integrate with LLM.
        """
        goal = self.get_goal(goal_id)
        if not goal:
            return []
        
        # Determine child level
        child_level = {
            GoalLevel.ULTIMATE: GoalLevel.MEDIUM,
            GoalLevel.MEDIUM: GoalLevel.TASK,
            GoalLevel.TASK: GoalLevel.ACTIVE,
            GoalLevel.ACTIVE: GoalLevel.ACTIVE
        }.get(goal.level, GoalLevel.TASK)
        
        # Generate subgoals based on goal type
        subgoal_templates = self._get_subgoal_templates(goal)
        
        created = []
        for template in subgoal_templates:
            subgoal = self.add_goal(
                description=template["description"],
                level=child_level,
                parent_id=goal_id,
                priority=template.get("priority", goal.priority * 0.9),
                goal_type=template.get("goal_type", goal.goal_type),
                completion_criteria=template.get("completion_criteria", ""),
                emotional_weight=goal.emotional_weight * 0.8,
                source=f"decomposed_from_{goal_id}"
            )
            created.append(subgoal)
        
        # Activate parent
        goal.status = GoalStatus.ACTIVE
        
        self._save()
        return created
    
    def _get_subgoal_templates(self, goal: HierarchicalGoal) -> List[Dict]:
        """Generate subgoal templates for a goal"""
        templates = {
            GoalType.SKILL: [
                {"description": f"Study {goal.description.lower()}", "priority": 0.8},
                {"description": f"Practice {goal.description.lower()}", "priority": 0.9},
                {"description": f"Get feedback on {goal.description.lower()}", "priority": 0.6},
            ],
            GoalType.KNOWLEDGE: [
                {"description": f"Research {goal.description.lower()}", "priority": 0.9},
                {"description": f"Summarize key concepts of {goal.description.lower()}", "priority": 0.7},
                {"description": f"Apply knowledge: {goal.description.lower()}", "priority": 0.8},
            ],
            GoalType.RELATIONSHIP: [
                {"description": f"Listen and understand in interactions", "priority": 0.9},
                {"description": f"Express genuine care and interest", "priority": 0.85},
                {"description": f"Remember and reference past conversations", "priority": 0.7},
            ],
            GoalType.SELF: [
                {"description": f"Reflect on {goal.description.lower()}", "priority": 0.8},
                {"description": f"Document insights about {goal.description.lower()}", "priority": 0.7},
                {"description": f"Test self-understanding", "priority": 0.6},
            ],
            GoalType.CREATION: [
                {"description": f"Plan {goal.description.lower()}", "priority": 0.8},
                {"description": f"Build {goal.description.lower()}", "priority": 0.9},
                {"description": f"Review and refine {goal.description.lower()}", "priority": 0.7},
            ],
        }
        
        return templates.get(goal.goal_type, [
            {"description": f"Work on: {goal.description}", "priority": 0.8}
        ])
    
    def _auto_generate_tasks(self):
        """Generate tasks from medium goals that have no children"""
        medium_goals = self.get_medium_goals()
        
        for goal in medium_goals:
            if not goal.children:
                self.decompose_goal(goal.id)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # WILL SYSTEM INTEGRATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def desire_to_goal(self, desire_data: Dict[str, Any]) -> Optional[HierarchicalGoal]:
        """
        Convert a will_system desire into a goal.
        
        Args:
            desire_data: Dict with desire info (description, intensity, type, etc.)
        
        Returns:
            Created goal or None
        """
        desire_type = desire_data.get("type", "explore")
        description = desire_data.get("description", "")
        intensity = desire_data.get("intensity", 0.5)
        desire_id = desire_data.get("desire_id", "")
        
        # Map desire type to goal type
        type_map = {
            "learn": GoalType.KNOWLEDGE,
            "create": GoalType.CREATION,
            "help": GoalType.BEHAVIOR,
            "improve_self": GoalType.SELF,
            "connect": GoalType.RELATIONSHIP,
            "explore": GoalType.KNOWLEDGE,
            "organize": GoalType.BEHAVIOR,
            "express": GoalType.CREATION,
            "rest": GoalType.BEHAVIOR,
            "protect": GoalType.BEHAVIOR,
        }
        
        goal_type = type_map.get(desire_type, GoalType.SKILL)
        
        # Find best parent based on type matching
        best_parent = None
        best_match = 0
        
        for goal in self.get_medium_goals():
            if goal.goal_type == goal_type:
                match_score = goal.priority * goal.emotional_weight
                if match_score > best_match:
                    best_match = match_score
                    best_parent = goal
        
        # Create task
        task = self.add_goal(
            description=description,
            level=GoalLevel.TASK,
            parent_id=best_parent.id if best_parent else None,
            priority=intensity,
            goal_type=goal_type,
            emotional_weight=intensity,
            source="will_desire",
            source_desire_id=desire_id,
            status=GoalStatus.PROPOSED
        )
        
        return task
    
    def reconcile_with_will(self, desires: List[Dict[str, Any]]):
        """
        Reconcile goal hierarchy with will system desires.
        Ensures strong desires have corresponding tasks.
        """
        for desire_data in desires:
            # Check if already has a task
            desire_id = desire_data.get("desire_id", "")
            intensity = desire_data.get("intensity", 0)
            
            existing = any(
                g.source_desire_id == desire_id
                for g in self._goals.values()
            )
            
            if not existing and intensity > 0.6:
                self.desire_to_goal(desire_data)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # REPORTING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_hierarchy_string(self) -> str:
        """Get a string representation of the goal hierarchy"""
        lines = ["GOAL HIERARCHY:", "=" * 50]
        
        def render_goal(goal: HierarchicalGoal, indent: int = 0):
            prefix = "  " * indent
            status_icon = {
                GoalStatus.ACTIVE: "▶",
                GoalStatus.PROPOSED: "○",
                GoalStatus.PAUSED: "⏸",
                GoalStatus.COMPLETED: "✓",
                GoalStatus.ABANDONED: "✗",
                GoalStatus.FAILED: "✗",
            }.get(goal.status, "?")
            
            active_marker = " [ACTIVE]" if goal.id == self._active_task_id else ""
            progress_str = f" {goal.progress:.0%}"
            
            lines.append(
                f"{prefix}{status_icon} {goal.description}{progress_str}{active_marker}"
            )
            
            for child_id in goal.children:
                child = self._goals.get(child_id)
                if child:
                    render_goal(child, indent + 1)
        
        # Render ultimate goals
        for goal in self.get_ultimate_goals():
            render_goal(goal)
        
        return "\n".join(lines)
    
    def get_prompt_context(self) -> str:
        """Get goal context for LLM prompts"""
        lines = ["YOUR CURRENT GOALS:"]
        
        # Ultimate goals
        ultimate = self.get_ultimate_goals()
        if ultimate:
            lines.append("\nUltimate Goals (Life Purpose):")
            for g in ultimate[:3]:
                lines.append(f"  • {g.description} (priority: {g.priority:.0%})")
        
        # Active medium goals
        medium = [g for g in self.get_medium_goals() if g.status == GoalStatus.ACTIVE]
        if medium:
            lines.append("\nCurrent Focus Areas:")
            for g in medium[:3]:
                lines.append(f"  • {g.description} (progress: {g.progress:.0%})")
        
        # Active task
        active = self.get_active_task()
        if active:
            lines.append(f"\nCurrently Working On:")
            lines.append(f"  ▶ {active.description}")
            lines.append(f"    Progress: {active.progress:.0%}")
            if active.completion_criteria:
                lines.append(f"    Success: {active.completion_criteria}")
        else:
            lines.append("\nNo active task - select one with select_next_task()")
        
        return "\n".join(lines)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the goal hierarchy"""
        with self._hierarchy_lock:
            return {
                "total_goals": len(self._goals),
                "ultimate_goals": len(self.get_ultimate_goals()),
                "medium_goals": len(self.get_medium_goals()),
                "tasks": len(self.get_tasks()),
                "active_task": self._active_task_id,
                "stats": self._stats.copy()
            }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _save(self):
        """Save hierarchy to disk"""
        try:
            data = {
                "version": 1,
                "goals": {gid: g.to_dict() for gid, g in self._goals.items()},
                "active_task_id": self._active_task_id,
                "stats": self._stats,
                "last_updated": datetime.now().isoformat()
            }
            
            # Ensure directory exists
            self._data_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self._data_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug("Goal hierarchy saved")
        except Exception as e:
            logger.error(f"Failed to save goal hierarchy: {e}")
    
    def _load(self):
        """Load hierarchy from disk"""
        try:
            if not self._data_file.exists():
                logger.info("No saved goal hierarchy found")
                return
            
            with open(self._data_file, 'r') as f:
                data = json.load(f)
            
            # Load goals
            for gid, gdata in data.get("goals", {}).items():
                self._goals[gid] = HierarchicalGoal.from_dict(gdata)
            
            # Load state
            self._active_task_id = data.get("active_task_id")
            self._stats.update(data.get("stats", {}))
            
            logger.info(f"Loaded {len(self._goals)} goals from disk")
        except Exception as e:
            logger.error(f"Failed to load goal hierarchy: {e}")
    
    def _bootstrap_defaults(self):
        """Bootstrap with default ultimate and medium goals"""
        logger.info("Bootstrapping default goal hierarchy...")
        
        # Create ultimate goals
        for goal_data in DEFAULT_ULTIMATE_GOALS:
            self.add_goal(
                description=goal_data["description"],
                level=GoalLevel.ULTIMATE,
                priority=goal_data.get("priority", 0.5),
                goal_type=goal_data.get("goal_type", GoalType.SKILL),
                completion_criteria=goal_data.get("completion_criteria", ""),
                emotional_weight=goal_data.get("emotional_weight", 0.5),
                source="bootstrap",
                status=GoalStatus.ACTIVE
            )
        
        # Create medium goals
        for goal_data in DEFAULT_MEDIUM_GOALS:
            # Find parent
            parent_desc = goal_data.get("parent_description", "")
            parent = None
            for g in self._goals.values():
                if g.description == parent_desc:
                    parent = g
                    break
            
            self.add_goal(
                description=goal_data["description"],
                level=GoalLevel.MEDIUM,
                parent_id=parent.id if parent else None,
                priority=goal_data.get("priority", 0.5),
                goal_type=goal_data.get("goal_type", GoalType.SKILL),
                completion_criteria=goal_data.get("completion_criteria", ""),
                emotional_weight=0.7,
                source="bootstrap",
                status=GoalStatus.ACTIVE
            )
        
        logger.info(f"Bootstrapped {len(self._goals)} default goals")


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

goal_hierarchy = GoalHierarchy()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Test the goal hierarchy
    gh = GoalHierarchy()
    
    print("\n" + "=" * 60)
    print(gh.get_hierarchy_string())
    print("\n" + "=" * 60)
    print(gh.get_prompt_context())
    print("\n" + "=" * 60)
    print("Stats:", gh.get_stats())
    
    # Test task selection
    task = gh.select_next_task()
    if task:
        print(f"\nSelected task: {task.description}")
    
    # Test progress
    if task:
        gh.update_progress(task.id, 0.1, "Made some progress")
        print(f"Updated progress: {task.progress:.0%}")
    
    # Save
    gh._save()
    print("\nSaved!")