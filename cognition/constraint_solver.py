"""
NEXUS AI — Constraint Solver Engine
Constraint satisfaction, optimization, resource allocation,
scheduling, satisfiability, feasibility analysis.
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

logger = get_logger("constraint_solver")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)


class ConstraintType(Enum):
    HARD = "hard"
    SOFT = "soft"
    PREFERENCE = "preference"
    BOUNDARY = "boundary"
    EQUALITY = "equality"
    INEQUALITY = "inequality"
    TEMPORAL = "temporal"
    RESOURCE = "resource"
    LOGICAL = "logical"


class OptimizationGoal(Enum):
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"
    SATISFY = "satisfy"
    BALANCE = "balance"
    PARETO = "pareto"


class FeasibilityResult(Enum):
    FEASIBLE = "feasible"
    INFEASIBLE = "infeasible"
    PARTIALLY_FEASIBLE = "partially_feasible"
    UNKNOWN = "unknown"
    NEEDS_RELAXATION = "needs_relaxation"


@dataclass
class Constraint:
    name: str = ""
    type: ConstraintType = ConstraintType.HARD
    description: str = ""
    priority: int = 5
    relaxable: bool = False

    def to_dict(self) -> Dict:
        return {
            "name": self.name, "type": self.type.value,
            "description": self.description, "priority": self.priority,
            "relaxable": self.relaxable
        }


@dataclass
class Solution:
    solution_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    problem: str = ""
    feasibility: FeasibilityResult = FeasibilityResult.UNKNOWN
    assignments: Dict[str, Any] = field(default_factory=dict)
    satisfied_constraints: List[str] = field(default_factory=list)
    violated_constraints: List[str] = field(default_factory=list)
    objective_value: Optional[float] = None
    optimality_gap: float = 0.0
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    reasoning: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "solution_id": self.solution_id, "problem": self.problem[:200],
            "feasibility": self.feasibility.value,
            "assignments": self.assignments,
            "satisfied_constraints": self.satisfied_constraints,
            "violated_constraints": self.violated_constraints,
            "objective_value": self.objective_value,
            "optimality_gap": self.optimality_gap,
            "alternatives": self.alternatives,
            "reasoning": self.reasoning, "created_at": self.created_at
        }


@dataclass
class Schedule:
    schedule_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    tasks: List[Dict[str, Any]] = field(default_factory=list)
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    resource_usage: Dict[str, Any] = field(default_factory=dict)
    total_duration: str = ""
    utilization: float = 0.0
    bottlenecks: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "schedule_id": self.schedule_id, "tasks": self.tasks,
            "timeline": self.timeline,
            "resource_usage": self.resource_usage,
            "total_duration": self.total_duration,
            "utilization": self.utilization,
            "bottlenecks": self.bottlenecks,
            "created_at": self.created_at
        }


class ConstraintSolverEngine:
    """
    Constraint satisfaction and optimization: resource allocation,
    scheduling, feasibility analysis, and tradeoff optimization.
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

        self._solutions: List[Solution] = []
        self._schedules: List[Schedule] = []
        self._running = False
        self._data_file = COGNITION_DIR / "constraint_solver.json"

        self._stats = {
            "total_problems_solved": 0, "total_schedules": 0,
            "total_feasibility_checks": 0, "total_optimizations": 0,
            "total_allocations": 0
        }

        self._load_data()
        logger.info("✅ Constraint Solver Engine initialized")

    def start(self):
        self._running = True
        logger.info("🧩 Constraint Solver started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🧩 Constraint Solver stopped")

    def solve_constraints(self, problem: str) -> Solution:
        """Solve a constraint satisfaction problem."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Solve this constraint satisfaction problem:\n{problem}\n\n"
                f"Return JSON:\n"
                f'{{"feasibility": "feasible|infeasible|partially_feasible|needs_relaxation", '
                f'"assignments": {{"variable": "value"}}, '
                f'"satisfied_constraints": ["str"], '
                f'"violated_constraints": ["str"], '
                f'"objective_value": null or float, '
                f'"optimality_gap": 0.0-1.0, '
                f'"alternatives": [{{"assignments": {{}}, "tradeoff": "str"}}], '
                f'"reasoning": "str"}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.3)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            fr_map = {f.value: f for f in FeasibilityResult}
            solution = Solution(
                problem=problem,
                feasibility=fr_map.get(data.get("feasibility", "unknown"), FeasibilityResult.UNKNOWN),
                assignments=data.get("assignments", {}),
                satisfied_constraints=data.get("satisfied_constraints", []),
                violated_constraints=data.get("violated_constraints", []),
                objective_value=data.get("objective_value"),
                optimality_gap=data.get("optimality_gap", 0.0),
                alternatives=data.get("alternatives", []),
                reasoning=data.get("reasoning", "")
            )

            self._solutions.append(solution)
            self._stats["total_problems_solved"] += 1
            self._save_data()
            return solution

        except Exception as e:
            logger.debug(f"Constraint solving failed: {e}")
            return Solution(problem=problem)

    def schedule_tasks(self, tasks_desc: str, constraints: str = "") -> Schedule:
        """Create an optimal schedule respecting constraints."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Create an optimal schedule for these tasks:\n{tasks_desc}\n"
                f"Constraints: {constraints}\n\n"
                f"Return JSON:\n"
                f'{{"tasks": [{{"name": "str", "duration": "str", '
                f'"dependencies": ["str"], "assigned_to": "str"}}], '
                f'"timeline": [{{"task": "str", "start": "str", "end": "str", '
                f'"resource": "str"}}], '
                f'"resource_usage": {{"resource": "utilization %"}}, '
                f'"total_duration": "str", '
                f'"utilization": 0.0-1.0, '
                f'"bottlenecks": ["str"], '
                f'"critical_path": ["str"]}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.3)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            schedule = Schedule(
                tasks=data.get("tasks", []),
                timeline=data.get("timeline", []),
                resource_usage=data.get("resource_usage", {}),
                total_duration=data.get("total_duration", ""),
                utilization=data.get("utilization", 0.0),
                bottlenecks=data.get("bottlenecks", [])
            )

            self._schedules.append(schedule)
            self._stats["total_schedules"] += 1
            self._save_data()
            return schedule

        except Exception as e:
            logger.debug(f"Task scheduling failed: {e}")
            return Schedule()

    def check_feasibility(self, requirements: str) -> Dict[str, Any]:
        """Check whether a set of requirements is feasible."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Check the feasibility of these requirements:\n{requirements}\n\n"
                f"Return JSON:\n"
                f'{{"feasibility": "feasible|infeasible|partially_feasible|needs_relaxation", '
                f'"confidence": 0.0-1.0, '
                f'"feasible_requirements": ["str"], '
                f'"infeasible_requirements": ["str"], '
                f'"conflicts": [{{"req_a": "str", "req_b": "str", "reason": "str"}}], '
                f'"relaxation_suggestions": ["str"], '
                f'"missing_resources": ["str"], '
                f'"overall_assessment": "str"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.3)
            if not response.success or not response.text:
                return {"feasibility": "unknown", "confidence": 0.0}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"feasibility": "unknown", "confidence": 0.0}
            self._stats["total_feasibility_checks"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Feasibility check failed: {e}")
            return {"feasibility": "unknown", "confidence": 0.0}

    def allocate_resources(self, resources: str, demands: str) -> Dict[str, Any]:
        """Optimally allocate resources to competing demands."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Optimally allocate these resources to competing demands:\n"
                f"Resources: {resources}\nDemands: {demands}\n\n"
                f"Return JSON:\n"
                f'{{"allocations": [{{"resource": "str", "allocated_to": "str", '
                f'"amount": "str", "priority": int}}], '
                f'"unmet_demands": ["str"], '
                f'"surplus_resources": ["str"], '
                f'"efficiency_score": 0.0-1.0, '
                f'"fairness_score": 0.0-1.0, '
                f'"optimization_rationale": "str", '
                f'"alternative_allocations": [{{"description": "str", '
                f'"tradeoff": "str"}}]}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.3)
            if not response.success or not response.text:
                return {"allocations": [], "efficiency_score": 0.0}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"allocations": [], "efficiency_score": 0.0}
            self._stats["total_allocations"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Resource allocation failed: {e}")
            return {"allocations": [], "efficiency_score": 0.0}

    def optimize(self, objective: str, constraints_text: str = "") -> Dict[str, Any]:
        """Optimize an objective subject to constraints."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Optimize this objective:\nObjective: {objective}\n"
                f"Constraints: {constraints_text}\n\n"
                f"Return JSON:\n"
                f'{{"optimal_solution": "str", '
                f'"variables": {{"var": "value"}}, '
                f'"objective_value": "str", '
                f'"sensitivity": [{{"parameter": "str", "impact": "str"}}], '
                f'"binding_constraints": ["str"], '
                f'"slack_constraints": ["str"], '
                f'"improvement_directions": ["str"]}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.3)
            if not response.success or not response.text:
                return {"optimal_solution": "unknown"}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"optimal_solution": "unknown"}
            self._stats["total_optimizations"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Optimization failed: {e}")
            return {"optimal_solution": "unknown"}

    def _save_data(self):
        try:
            data = {
                "solutions": [s.to_dict() for s in self._solutions[-200:]],
                "schedules": [s.to_dict() for s in self._schedules[-100:]],
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
                logger.info("📂 Loaded constraint solver data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}


constraint_solver = ConstraintSolverEngine()
