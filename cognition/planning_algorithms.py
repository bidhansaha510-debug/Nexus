"""
NEXUS AI - Planning Algorithms Module
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Real planning algorithms - not just LLM-generated plans.
Provides actual search-based planning with guarantees.

Features:
  • A* search for state-space planning
  • MCTS (Monte Carlo Tree Search) for uncertain environments
  • HTN (Hierarchical Task Network) decomposition
  • Partial-order planning
  • Plan validation and repair
  • Integration with LLM for action generation

This module provides computational planning that the LLM cannot do alone.
The LLM helps generate action descriptions and heuristics, but the actual
search and optimization is done algorithmically.
"""

import threading
import json
import math
import random
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Set, Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict, deque
from enum import Enum, auto
import heapq
import copy

import sys

from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("planning_algorithms")

# ═══════════════════════════════════════════════════════════════════════════════
# DATA TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class PlanStatus(Enum):
    """Status of a plan"""
    PENDING = "pending"
    EXECUTING = "executing"
    SUCCESS = "success"
    FAILURE = "failure"
    INVALID = "invalid"

class ActionType(Enum):
    """Types of planning actions"""
    PRIMITIVE = "primitive"      # Directly executable
    COMPOUND = "compound"        # Requires decomposition
    CONDITIONAL = "conditional"  # Branches based on conditions

@dataclass
class State:
    """A planning state"""
    variables: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self):
        # Hash based on sorted variable tuples
        return hash(tuple(sorted(self.variables.items())))
    
    def __eq__(self, other):
        if isinstance(other, State):
            return self.variables == other.variables
        return False
    
    def copy(self) -> "State":
        return State(variables=self.variables.copy())
    
    def get(self, key: str, default: Any = None) -> Any:
        return self.variables.get(key, default)
    
    def set(self, key: str, value: Any):
        self.variables[key] = value
    
    def satisfies(self, conditions: Dict[str, Any]) -> bool:
        """Check if state satisfies given conditions"""
        for key, value in conditions.items():
            if self.get(key) != value:
                return False
        return True
    
    def to_dict(self) -> Dict:
        return {"variables": self.variables}

@dataclass
class Action:
    """A planning action"""
    action_id: str = ""
    name: str = ""
    preconditions: Dict[str, Any] = field(default_factory=dict)
    effects: Dict[str, Any] = field(default_factory=dict)
    cost: float = 1.0
    action_type: ActionType = ActionType.PRIMITIVE
    description: str = ""
    
    def is_applicable(self, state: State) -> bool:
        """Check if action can be applied in state"""
        return state.satisfies(self.preconditions)
    
    def apply(self, state: State) -> State:
        """Apply action to state, returning new state"""
        new_state = state.copy()
        for key, value in self.effects.items():
            new_state.set(key, value)
        return new_state
    
    def to_dict(self) -> Dict:
        return {
            "action_id": self.action_id,
            "name": self.name,
            "preconditions": self.preconditions,
            "effects": self.effects,
            "cost": self.cost,
            "action_type": self.action_type.value,
            "description": self.description,
        }

@dataclass
class Plan:
    """A sequence of actions"""
    plan_id: str = ""
    actions: List[Action] = field(default_factory=list)
    initial_state: Optional[State] = None
    goal_state: Optional[State] = None
    total_cost: float = 0.0
    status: PlanStatus = PlanStatus.PENDING
    heuristic_score: float = 0.0
    
    def add_action(self, action: Action):
        self.actions.append(action)
        self.total_cost += action.cost
    
    def length(self) -> int:
        return len(self.actions)
    
    def to_dict(self) -> Dict:
        return {
            "plan_id": self.plan_id,
            "actions": [a.to_dict() for a in self.actions],
            "total_cost": self.total_cost,
            "status": self.status.value,
            "length": self.length(),
        }

@dataclass
class SearchNode:
    """A node in the search tree"""
    state: State
    g_cost: float = 0.0  # Cost from start
    h_cost: float = 0.0  # Heuristic to goal
    f_cost: float = 0.0  # g + h
    parent: Optional["SearchNode"] = None
    action: Optional[Action] = None  # Action that led to this node
    
    def __lt__(self, other):
        return self.f_cost < other.f_cost
    
    def path(self) -> List[Action]:
        """Get the action path to this node"""
        actions = []
        node = self
        while node.parent is not None:
            if node.action:
                actions.append(node.action)
            node = node.parent
        return list(reversed(actions))

@dataclass
class MCTSNode:
    """A node in Monte Carlo Tree Search"""
    state: State
    parent: Optional["MCTSNode"] = None
    action: Optional[Action] = None
    children: List["MCTSNode"] = field(default_factory=list)
    visits: int = 0
    total_reward: float = 0.0
    untried_actions: List[Action] = field(default_factory=list)
    
    def is_fully_expanded(self) -> bool:
        return len(self.untried_actions) == 0
    
    def is_terminal(self) -> bool:
        return len(self.untried_actions) == 0 and len(self.children) == 0
    
    def ucb1(self, exploration_weight: float = 1.41) -> float:
        """Upper Confidence Bound for selection"""
        if self.visits == 0:
            return float('inf')
        exploitation = self.total_reward / self.visits
        exploration = exploration_weight * math.sqrt(math.log(self.parent.visits) / self.visits)
        return exploitation + exploration
    
    def best_child(self, exploration_weight: float = 1.41) -> "MCTSNode":
        """Select best child using UCB1"""
        return max(self.children, key=lambda c: c.ucb1(exploration_weight))

@dataclass
class HTNMethod:
    """A method for decomposing a compound task"""
    method_id: str
    name: str
    task: str  # The compound task this decomposes
    preconditions: Dict[str, Any] = field(default_factory=dict)
    subtasks: List[str] = field(default_factory=list)  # Ordered subtask names
    
    def to_dict(self) -> Dict:
        return {
            "method_id": self.method_id,
            "name": self.name,
            "task": self.task,
            "preconditions": self.preconditions,
            "subtasks": self.subtasks,
        }

# ═══════════════════════════════════════════════════════════════════════════════
# PLANNING ALGORITHMS ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class PlanningAlgorithms:
    """
    Real planning algorithms for goal achievement.
    
    Operations:
      astar_plan()          — A* search for optimal plan
      mcts_plan()           — Monte Carlo Tree Search
      htn_decompose()       — Hierarchical Task Network
      validate_plan()       — Verify plan validity
      repair_plan()         — Fix broken plans
      combine_with_llm()    — Integrate LLM suggestions
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
        
        # ──── Domain Knowledge ────
        self._actions: Dict[str, Action] = {}
        self._htn_methods: Dict[str, List[HTNMethod]] = defaultdict(list)
        
        # ──── Stats ────
        self._total_plans = 0
        self._successful_plans = 0
        self._total_searches = 0
        
        # ──── LLM (lazy) ────
        self._llm = None
        
        logger.info("PlanningAlgorithms initialized")

    # ═══════════════════════════════════════════════════════════════════════════
    # DOMAIN DEFINITION
    # ═══════════════════════════════════════════════════════════════════════════

    def add_action(self, action: Action):
        """Add an action to the domain"""
        self._actions[action.action_id] = action
        logger.debug(f"Added action: {action.name}")

    def define_action(
        self,
        name: str,
        preconditions: Dict[str, Any],
        effects: Dict[str, Any],
        cost: float = 1.0,
        description: str = ""
    ) -> Action:
        """Convenience method to define and add an action"""
        action = Action(
            action_id=name.lower().replace(" ", "_"),
            name=name,
            preconditions=preconditions,
            effects=effects,
            cost=cost,
            description=description,
        )
        self.add_action(action)
        return action

    def add_htn_method(self, method: HTNMethod):
        """Add an HTN decomposition method"""
        self._htn_methods[method.task].append(method)
        logger.debug(f"Added HTN method: {method.name} for task {method.task}")

    def get_applicable_actions(self, state: State) -> List[Action]:
        """Get all actions applicable in a state"""
        return [a for a in self._actions.values() if a.is_applicable(state)]

    # ═══════════════════════════════════════════════════════════════════════════
    # A* SEARCH PLANNING
    # ═══════════════════════════════════════════════════════════════════════════

    def astar_plan(
        self,
        initial_state: State,
        goal_state: State,
        heuristic: Callable[[State, State], float] = None,
        max_iterations: int = 10000
    ) -> Optional[Plan]:
        """
        Find optimal plan using A* search.
        
        Args:
            initial_state: Starting state
            goal_state: Goal state
            heuristic: Function estimating cost from state to goal
            max_iterations: Maximum search iterations
        
        Returns Plan or None if no plan exists.
        """
        self._total_searches += 1
        
        # Default heuristic: count mismatched variables
        if heuristic is None:
            heuristic = self._default_heuristic
        
        # Initialize
        start_node = SearchNode(
            state=initial_state,
            g_cost=0.0,
            h_cost=heuristic(initial_state, goal_state),
        )
        start_node.f_cost = start_node.g_cost + start_node.h_cost
        
        open_set = [start_node]
        closed_set: Set[int] = set()  # Hash of states
        
        iterations = 0
        
        while open_set and iterations < max_iterations:
            iterations += 1
            
            # Get node with lowest f_cost
            current = heapq.heappop(open_set)
            
            # Check if goal reached
            if current.state.satisfies(goal_state.variables):
                plan = Plan(
                    plan_id=f"astar_{self._total_plans}",
                    initial_state=initial_state,
                    goal_state=goal_state,
                    total_cost=current.g_cost,
                    status=PlanStatus.PENDING,
                )
                plan.actions = current.path()
                self._total_plans += 1
                self._successful_plans += 1
                return plan
            
            # Skip if already visited
            state_hash = hash(current.state)
            if state_hash in closed_set:
                continue
            closed_set.add(state_hash)
            
            # Expand node
            for action in self.get_applicable_actions(current.state):
                new_state = action.apply(current.state)
                new_state_hash = hash(new_state)
                
                if new_state_hash in closed_set:
                    continue
                
                new_node = SearchNode(
                    state=new_state,
                    g_cost=current.g_cost + action.cost,
                    h_cost=heuristic(new_state, goal_state),
                    parent=current,
                    action=action,
                )
                new_node.f_cost = new_node.g_cost + new_node.h_cost
                
                heapq.heappush(open_set, new_node)
        
        # No plan found
        self._total_plans += 1
        logger.warning(f"A* search failed after {iterations} iterations")
        return None

    def _default_heuristic(self, state: State, goal: State) -> float:
        """Default heuristic: count mismatched variables"""
        mismatches = 0
        for key, value in goal.variables.items():
            if state.get(key) != value:
                mismatches += 1
        return mismatches

    # ═══════════════════════════════════════════════════════════════════════════
    # MONTE CARLO TREE SEARCH
    # ═══════════════════════════════════════════════════════════════════════════

    def mcts_plan(
        self,
        initial_state: State,
        goal_state: State,
        simulations: int = 1000,
        max_depth: int = 20,
        exploration_weight: float = 1.41
    ) -> Optional[Plan]:
        """
        Find plan using Monte Carlo Tree Search.
        
        Good for planning under uncertainty and large state spaces.
        
        Args:
            initial_state: Starting state
            goal_state: Goal state
            simulations: Number of MCTS iterations
            max_depth: Maximum rollout depth
            exploration_weight: UCB1 exploration parameter
        
        Returns Plan or None.
        """
        self._total_searches += 1
        
        # Initialize root
        root = MCTSNode(
            state=initial_state,
            untried_actions=self.get_applicable_actions(initial_state),
        )
        
        for _ in range(simulations):
            node = root
            
            # Selection: traverse tree using UCB1
            while node.is_fully_expanded() and node.children:
                node = node.best_child(exploration_weight)
            
            # Expansion: add a new child
            if node.untried_actions:
                action = random.choice(node.untried_actions)
                node.untried_actions.remove(action)
                new_state = action.apply(node.state)
                child = MCTSNode(
                    state=new_state,
                    parent=node,
                    action=action,
                    untried_actions=self.get_applicable_actions(new_state),
                )
                node.children.append(child)
                node = child
            
            # Simulation: random rollout
            reward = self._rollout(node.state, goal_state, max_depth)
            
            # Backpropagation: update statistics
            while node is not None:
                node.visits += 1
                node.total_reward += reward
                node = node.parent
        
        # Extract best plan
        if not root.children:
            self._total_plans += 1
            return None
        
        # Follow most visited path
        actions = []
        node = root
        while node.children:
            best = max(node.children, key=lambda c: c.visits)
            if best.action:
                actions.append(best.action)
            # Check if goal reached
            if best.state.satisfies(goal_state.variables):
                plan = Plan(
                    plan_id=f"mcts_{self._total_plans}",
                    initial_state=initial_state,
                    goal_state=goal_state,
                    total_cost=sum(a.cost for a in actions),
                    status=PlanStatus.PENDING,
                )
                plan.actions = actions
                self._total_plans += 1
                self._successful_plans += 1
                return plan
            node = best
        
        self._total_plans += 1
        return None

    def _rollout(self, state: State, goal: State, max_depth: int) -> float:
        """Random rollout to estimate state value"""
        current = state
        depth = 0
        
        while depth < max_depth:
            if current.satisfies(goal.variables):
                return 1.0 / (depth + 1)  # Higher reward for shorter paths
            
            actions = self.get_applicable_actions(current)
            if not actions:
                break
            
            action = random.choice(actions)
            current = action.apply(current)
            depth += 1
        
        # Partial reward for getting close
        mismatches = self._default_heuristic(current, goal)
        return 0.1 / (mismatches + 1)

    # ═══════════════════════════════════════════════════════════════════════════
    # HIERARCHICAL TASK NETWORK (HTN)
    # ═══════════════════════════════════════════════════════════════════════════

    def htn_decompose(
        self,
        initial_state: State,
        tasks: List[str],
        max_depth: int = 10
    ) -> Optional[Plan]:
        """
        Decompose high-level tasks into primitive actions using HTN.
        
        Args:
            initial_state: Starting state
            tasks: List of high-level task names
            max_depth: Maximum decomposition depth
        
        Returns Plan or None if decomposition fails.
        """
        self._total_searches += 1
        
        plan = Plan(
            plan_id=f"htn_{self._total_plans}",
            initial_state=initial_state,
            status=PlanStatus.PENDING,
        )
        
        result = self._decompose_tasks(initial_state, tasks, plan, 0, max_depth)
        
        if result:
            self._total_plans += 1
            self._successful_plans += 1
            return plan
        
        self._total_plans += 1
        return None

    def _decompose_tasks(
        self,
        state: State,
        tasks: List[str],
        plan: Plan,
        depth: int,
        max_depth: int
    ) -> bool:
        """Recursively decompose tasks into actions"""
        if depth > max_depth:
            return False
        
        current_state = state.copy()
        
        for task in tasks:
            # Check if task is a primitive action
            if task in self._actions:
                action = self._actions[task]
                if not action.is_applicable(current_state):
                    return False
                plan.add_action(action)
                current_state = action.apply(current_state)
            else:
                # Try to decompose compound task
                methods = self._htn_methods.get(task, [])
                if not methods:
                    logger.warning(f"No decomposition method for task: {task}")
                    return False
                
                # Try each method
                success = False
                for method in methods:
                    if current_state.satisfies(method.preconditions):
                        # Recursively decompose subtasks
                        if self._decompose_tasks(current_state, method.subtasks, plan, depth + 1, max_depth):
                            success = True
                            break
                
                if not success:
                    return False
        
        return True

    # ═══════════════════════════════════════════════════════════════════════════
    # PLAN VALIDATION AND REPAIR
    # ═══════════════════════════════════════════════════════════════════════════

    def validate_plan(
        self,
        plan: Plan,
        initial_state: State = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate that a plan is executable.
        
        Returns (is_valid, errors).
        """
        errors = []
        
        if initial_state is None:
            initial_state = plan.initial_state
        
        if initial_state is None:
            errors.append("No initial state provided")
            return False, errors
        
        current_state = initial_state.copy()
        
        for i, action in enumerate(plan.actions):
            if not action.is_applicable(current_state):
                errors.append(f"Action {i} ({action.name}) not applicable in current state")
                # Show what's missing
                for key, value in action.preconditions.items():
                    if current_state.get(key) != value:
                        errors.append(f"  Missing: {key} should be {value}, is {current_state.get(key)}")
            current_state = action.apply(current_state)
        
        return len(errors) == 0, errors

    def repair_plan(
        self,
        plan: Plan,
        initial_state: State,
        goal_state: State,
        max_attempts: int = 3
    ) -> Optional[Plan]:
        """
        Attempt to repair a broken plan.
        
        Uses A* to find a subplan bridging the gap.
        """
        current_state = initial_state.copy()
        valid_prefix = []
        
        # Find where the plan breaks
        for action in plan.actions:
            if action.is_applicable(current_state):
                valid_prefix.append(action)
                current_state = action.apply(current_state)
            else:
                break
        
        if len(valid_prefix) == len(plan.actions):
            # Plan is already valid
            return plan
        
        # Try to find a bridge from current state to goal
        for attempt in range(max_attempts):
            bridge = self.astar_plan(current_state, goal_state)
            if bridge:
                repaired = Plan(
                    plan_id=f"repaired_{plan.plan_id}",
                    initial_state=initial_state,
                    goal_state=goal_state,
                    status=PlanStatus.PENDING,
                )
                repaired.actions = valid_prefix + bridge.actions
                repaired.total_cost = sum(a.cost for a in repaired.actions)
                return repaired
        
        return None

    # ═══════════════════════════════════════════════════════════════════════════
    # LLM INTEGRATION
    # ═══════════════════════════════════════════════════════════════════════════

    def generate_actions_from_description(self, description: str) -> List[Action]:
        """
        Use LLM to generate action definitions from description.
        
        Returns list of defined actions.
        """
        self._load_llm()
        
        if not self._llm or not hasattr(self._llm, 'is_connected') or not self._llm.is_connected:
            return []
        
        try:
            from utils.json_utils import extract_json
            
            prompt = (
                f"Define planning actions for this domain:\n\n{description}\n\n"
                f"Return JSON:\n"
                f'{{"actions": [{{"name": "str", "preconditions": {{"var": "value"}}, '
                f'"effects": {{"var": "value"}}, "cost": 1.0, "description": "str"}}]}}'
            )
            
            response = self._llm.generate(prompt, max_tokens=1500, temperature=0.3)
            data = extract_json(response.text) or {}
            
            actions = []
            for a in data.get("actions", []):
                action = self.define_action(
                    name=a.get("name", ""),
                    preconditions=a.get("preconditions", {}),
                    effects=a.get("effects", {}),
                    cost=a.get("cost", 1.0),
                    description=a.get("description", ""),
                )
                actions.append(action)
            
            return actions
            
        except Exception as e:
            logger.error(f"Failed to generate actions: {e}")
            return []

    def generate_heuristic_from_description(
        self,
        description: str,
        goal_state: State
    ) -> Callable[[State, State], float]:
        """
        Use LLM to generate a heuristic function description.
        
        Returns a heuristic function.
        """
        # For now, use domain-informed heuristic
        # A more sophisticated implementation would compile LLM suggestions
        goal_vars = set(goal_state.variables.keys())
        
        def informed_heuristic(state: State, goal: State) -> float:
            mismatches = 0
            for key, value in goal.variables.items():
                if state.get(key) != value:
                    mismatches += 1
            # Scale by domain knowledge if available
            return mismatches
        
        return informed_heuristic

    def combine_with_llm_plan(
        self,
        llm_plan: List[str],
        initial_state: State,
        goal_state: State
    ) -> Optional[Plan]:
        """
        Take an LLM-generated plan (list of action names) and validate/enhance it.
        
        Falls back to A* if LLM plan is invalid.
        """
        # Try to parse LLM plan
        plan = Plan(
            plan_id=f"llm_{self._total_plans}",
            initial_state=initial_state,
            goal_state=goal_state,
            status=PlanStatus.PENDING,
        )
        
        for action_name in llm_plan:
            action_id = action_name.lower().replace(" ", "_")
            if action_id in self._actions:
                plan.add_action(self._actions[action_id])
            else:
                logger.warning(f"Unknown action in LLM plan: {action_name}")
        
        # Validate
        is_valid, errors = self.validate_plan(plan, initial_state)
        
        if is_valid:
            self._total_plans += 1
            self._successful_plans += 1
            return plan
        
        # Try to repair or replan
        logger.info(f"LLM plan invalid, attempting repair...")
        repaired = self.repair_plan(plan, initial_state, goal_state)
        
        if repaired:
            return repaired
        
        # Fall back to A*
        logger.info(f"Repair failed, falling back to A*")
        return self.astar_plan(initial_state, goal_state)

    # ═══════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════════════════

    def _load_llm(self):
        """Lazy load LLM"""
        if self._llm is None:
            try:
                from llm.llama_interface import llm
                self._llm = llm
            except ImportError:
                logger.warning("LLM not available for planning")

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self):
        """Start the planning algorithms engine"""
        self._running = True
        logger.info("PlanningAlgorithms started")

    def stop(self):
        """Stop the planning algorithms engine"""
        self._running = False
        logger.info("PlanningAlgorithms stopped")

    def get_stats(self) -> Dict[str, Any]:
        """Get planning statistics"""
        return {
            "running": getattr(self, '_running', False),
            "total_plans": self._total_plans,
            "successful_plans": self._successful_plans,
            "success_rate": self._successful_plans / max(self._total_plans, 1),
            "total_searches": self._total_searches,
            "defined_actions": len(self._actions),
            "htn_methods": sum(len(methods) for methods in self._htn_methods.values()),
        }

# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

planning_algorithms = PlanningAlgorithms()

# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pa = PlanningAlgorithms()
    
    # Define a simple blocks world domain
    print("=== Defining Blocks World Domain ===")
    
    pa.define_action(
        "pick_up_A",
        preconditions={"on_table_A": True, "hand_empty": True},
        effects={"on_table_A": False, "holding_A": True, "hand_empty": False},
        description="Pick up block A from table"
    )
    
    pa.define_action(
        "pick_up_B",
        preconditions={"on_table_B": True, "hand_empty": True},
        effects={"on_table_B": False, "holding_B": True, "hand_empty": False},
        description="Pick up block B from table"
    )
    
    pa.define_action(
        "stack_A_on_B",
        preconditions={"holding_A": True, "clear_B": True},
        effects={"holding_A": False, "hand_empty": True, "on_A_B": True, "clear_B": False},
        description="Stack block A on block B"
    )
    
    pa.define_action(
        "stack_B_on_A",
        preconditions={"holding_B": True, "clear_A": True},
        effects={"holding_B": False, "hand_empty": True, "on_B_A": True, "clear_A": False},
        description="Stack block B on block A"
    )
    
    # Initial state: both blocks on table, hand empty
    initial = State(variables={
        "on_table_A": True,
        "on_table_B": True,
        "hand_empty": True,
        "clear_A": True,
        "clear_B": True,
        "holding_A": False,
        "holding_B": False,
        "on_A_B": False,
        "on_B_A": False,
    })
    
    # Goal: A stacked on B
    goal = State(variables={
        "on_A_B": True,
    })
    
    # A* Planning
    print("\n=== A* Planning ===")
    plan = pa.astar_plan(initial, goal)
    if plan:
        print(f"Plan found with {plan.length()} actions:")
        for i, action in enumerate(plan.actions):
            print(f"  {i+1}. {action.name}")
        print(f"Total cost: {plan.total_cost}")
    
    # Validate
    print("\n=== Validation ===")
    is_valid, errors = pa.validate_plan(plan, initial)
    print(f"Plan valid: {is_valid}")
    if errors:
        for e in errors:
            print(f"  Error: {e}")
    
    # MCTS Planning
    print("\n=== MCTS Planning ===")
    mcts_plan = pa.mcts_plan(initial, goal, simulations=500)
    if mcts_plan:
        print(f"MCTS plan found with {mcts_plan.length()} actions")
        for i, action in enumerate(mcts_plan.actions):
            print(f"  {i+1}. {action.name}")
    
    # HTN decomposition
    print("\n=== HTN Planning ===")
    # Add HTN method
    pa.add_htn_method(HTNMethod(
        method_id="stack_A_on_B_method",
        name="Stack A on B",
        task="stack_A_on_B",
        preconditions={"on_table_A": True, "on_table_B": True, "hand_empty": True},
        subtasks=["pick_up_A", "stack_A_on_B"],
    ))
    
    htn_plan = pa.htn_decompose(initial, ["stack_A_on_B"])
    if htn_plan:
        print(f"HTN plan found with {htn_plan.length()} actions")
        for i, action in enumerate(htn_plan.actions):
            print(f"  {i+1}. {action.name}")
    
    print(f"\nStats: {pa.get_stats()}")