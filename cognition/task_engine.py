"""
NEXUS AI — Task Decomposition Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Breaks complex goals into executable subtask DAGs, executes them
in dependency order, and handles failures with retry/replan.
"""
import sys, time, json, re, uuid, threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.logger import get_logger
from config import NEXUS_CONFIG, DATA_DIR

logger = get_logger("task_engine")


class SubTaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class SubTask:
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    dependencies: List[str] = field(default_factory=list)  # task_ids this depends on
    required_tools: List[str] = field(default_factory=list)
    estimated_effort: str = "low"  # low, medium, high
    status: SubTaskStatus = SubTaskStatus.PENDING
    result: str = ""
    error: str = ""
    elapsed: float = 0.0
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id, "description": self.description,
            "dependencies": self.dependencies, "tools": self.required_tools,
            "status": self.status.value, "result": self.result[:200],
            "error": self.error, "elapsed": round(self.elapsed, 3),
        }

@dataclass
class TaskPlan:
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    goal: str = ""
    subtasks: List[SubTask] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "pending"  # pending, running, completed, failed, replanned
    total_elapsed: float = 0.0
    replans: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id, "goal": self.goal,
            "status": self.status, "replans": self.replans,
            "subtasks": [s.to_dict() for s in self.subtasks],
            "total_elapsed": round(self.total_elapsed, 3),
        }

@dataclass
class TaskResult:
    plan: TaskPlan = None
    success: bool = False
    final_output: str = ""
    subtask_results: Dict[str, str] = field(default_factory=dict)
    elapsed: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success, "final_output": self.final_output[:500],
            "subtask_count": len(self.subtask_results),
            "elapsed": round(self.elapsed, 3),
            "plan": self.plan.to_dict() if self.plan else None,
        }


class TaskEngine:
    """
    Decomposes complex goals into executable subtask DAGs.
    Executes subtasks in dependency order using the AgenticLoop.
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
        self._llm = None
        self._agentic_loop = None
        self._max_subtasks = NEXUS_CONFIG.agentic.max_subtasks
        self._subtask_timeout = NEXUS_CONFIG.agentic.subtask_timeout
        self._active_plan: Optional[TaskPlan] = None
        self._completed_plans: List[TaskPlan] = []
        self._data_file = DATA_DIR / "task_engine_state.json"
        self._load_state()
        logger.info("TaskEngine initialized")

    def _load_llm(self):
        if self._llm is None:
            try:
                from llm.groq_interface import GroqInterface
                self._llm = GroqInterface()
            except Exception:
                from llm.llama_interface import LlamaInterface
                self._llm = LlamaInterface()

    def _load_agentic_loop(self):
        if self._agentic_loop is None:
            from cognition.reasoning_loop import agentic_loop
            self._agentic_loop = agentic_loop

    # ──────────────────────────────────────────────────────────────────────────
    # DECOMPOSITION
    # ──────────────────────────────────────────────────────────────────────────

    def decompose(self, goal: str) -> TaskPlan:
        """Decompose a complex goal into a subtask DAG using LLM."""
        self._load_llm()

        prompt = f"""Decompose this goal into a list of subtasks that can be executed in order.

GOAL: {goal}

Rules:
- Each subtask should be a single, concrete action
- Subtasks can depend on previous subtasks (by ID)
- Max {self._max_subtasks} subtasks
- Include which tools might be needed

Respond with JSON ONLY:
{{
    "subtasks": [
        {{
            "id": "t1",
            "description": "First concrete step",
            "dependencies": [],
            "tools": ["tool_name"],
            "effort": "low"
        }},
        {{
            "id": "t2",
            "description": "Second step that depends on first",
            "dependencies": ["t1"],
            "tools": [],
            "effort": "medium"
        }}
    ]
}}"""

        try:
            messages = [{"role": "user", "content": prompt}]
            raw = self._llm.generate(messages, system_prompt="You decompose goals into subtasks. Respond ONLY with JSON.")
            subtasks = self._parse_decomposition(raw)
        except Exception as e:
            logger.debug(f"Decomposition failed: {e}")
            # Fallback: single subtask
            subtasks = [SubTask(task_id="t1", description=goal)]

        plan = TaskPlan(goal=goal, subtasks=subtasks[:self._max_subtasks])
        self._active_plan = plan
        self._save_state()

        logger.info(f"Decomposed '{goal[:50]}...' into {len(plan.subtasks)} subtasks")
        return plan

    def _parse_decomposition(self, raw: str) -> List[SubTask]:
        """Parse LLM decomposition into SubTask objects."""
        try:
            # Extract JSON
            json_match = re.search(r'\{.*\}', raw, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(raw)

            subtasks = []
            for item in data.get("subtasks", []):
                subtasks.append(SubTask(
                    task_id=str(item.get("id", str(uuid.uuid4())[:8])),
                    description=item.get("description", ""),
                    dependencies=item.get("dependencies", []),
                    required_tools=item.get("tools", []),
                    estimated_effort=item.get("effort", "low"),
                ))
            return subtasks
        except Exception as e:
            logger.warning(f"Parse error: {e}")
            return []

    # ──────────────────────────────────────────────────────────────────────────
    # EXECUTION
    # ──────────────────────────────────────────────────────────────────────────

    def execute_plan(self, plan: TaskPlan) -> TaskResult:
        """Execute all subtasks in dependency order."""
        self._load_agentic_loop()
        start = time.time()
        plan.status = "running"
        results: Dict[str, str] = {}

        # Topological sort by dependencies
        order = self._topological_sort(plan.subtasks)

        for subtask in order:
            # Check dependencies are met
            deps_met = all(
                any(s.task_id == dep and s.status == SubTaskStatus.COMPLETED
                    for s in plan.subtasks)
                for dep in subtask.dependencies
            )

            if not deps_met:
                subtask.status = SubTaskStatus.SKIPPED
                subtask.error = "Dependencies not met"
                continue

            # Execute the subtask
            subtask_result = self._execute_subtask(subtask, results)
            results[subtask.task_id] = subtask_result

            if subtask.status == SubTaskStatus.FAILED:
                logger.warning(f"Subtask {subtask.task_id} failed, attempting replan")
                if plan.replans < 2:
                    self._replan_from_failure(plan, subtask)
                    plan.replans += 1
                else:
                    logger.error("Max replans reached")
                    break

        # Determine overall success
        completed = [s for s in plan.subtasks if s.status == SubTaskStatus.COMPLETED]
        success = len(completed) == len(plan.subtasks)
        plan.status = "completed" if success else "failed"
        plan.total_elapsed = time.time() - start

        # Synthesize final output
        final_output = self._synthesize_output(plan, results)

        self._completed_plans.append(plan)
        self._active_plan = None
        self._save_state()

        return TaskResult(
            plan=plan, success=success, final_output=final_output,
            subtask_results=results, elapsed=plan.total_elapsed,
        )

    def _execute_subtask(self, subtask: SubTask, prior_results: Dict[str, str]) -> str:
        """Execute a single subtask using the AgenticLoop."""
        subtask.status = SubTaskStatus.RUNNING
        start = time.time()

        # Build context from prior results
        context_parts = []
        for dep_id in subtask.dependencies:
            if dep_id in prior_results:
                context_parts.append(f"[Result of {dep_id}]: {prior_results[dep_id][:300]}")
        context = "\n".join(context_parts)

        try:
            result = self._agentic_loop.run(
                query=subtask.description,
                context=context,
                max_steps=3,  # Subtasks get fewer steps
            )
            subtask.status = SubTaskStatus.COMPLETED
            subtask.result = result.response
            subtask.elapsed = time.time() - start
            logger.info(f"Subtask {subtask.task_id} completed ({subtask.elapsed:.1f}s)")
            return result.response

        except Exception as e:
            subtask.status = SubTaskStatus.FAILED
            subtask.error = str(e)
            subtask.elapsed = time.time() - start
            logger.warning(f"Subtask {subtask.task_id} failed: {e}")
            return ""

    def _replan_from_failure(self, plan: TaskPlan, failed: SubTask):
        """Replan after a subtask failure."""
        logger.info(f"Replanning after failure of {failed.task_id}: {failed.description[:50]}")
        # Simple replan: retry the failed subtask with lower effort
        failed.status = SubTaskStatus.PENDING
        failed.retry_count += 1
        failed.error = ""

    def _topological_sort(self, subtasks: List[SubTask]) -> List[SubTask]:
        """Sort subtasks by dependency order."""
        id_map = {s.task_id: s for s in subtasks}
        visited, order = set(), []

        def visit(s):
            if s.task_id in visited:
                return
            visited.add(s.task_id)
            for dep in s.dependencies:
                if dep in id_map:
                    visit(id_map[dep])
            order.append(s)

        for s in subtasks:
            visit(s)
        return order

    def _synthesize_output(self, plan: TaskPlan, results: Dict[str, str]) -> str:
        """Synthesize final output from all subtask results."""
        if not results:
            return "Task could not be completed."
        parts = [f"Goal: {plan.goal}", ""]
        for subtask in plan.subtasks:
            status_icon = "✓" if subtask.status == SubTaskStatus.COMPLETED else "✗"
            parts.append(f"{status_icon} {subtask.description}")
            if subtask.task_id in results and results[subtask.task_id]:
                parts.append(f"  → {results[subtask.task_id][:200]}")
        return "\n".join(parts)

    # ──────────────────────────────────────────────────────────────────────────
    # PERSISTENCE
    # ──────────────────────────────────────────────────────────────────────────

    def _save_state(self):
        try:
            state = {
                "active_plan": self._active_plan.to_dict() if self._active_plan else None,
                "completed_count": len(self._completed_plans),
                "saved_at": datetime.now().isoformat(),
            }
            self._data_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
        except Exception as e:
            logger.debug(f"State save error: {e}")

    def _load_state(self):
        try:
            if self._data_file.exists():
                data = json.loads(self._data_file.read_text(encoding="utf-8"))
                logger.debug(f"Loaded state: {data.get('completed_count', 0)} completed plans")
        except Exception as e:
            logger.debug(f"State load error: {e}")

    def get_stats(self) -> Dict[str, Any]:
        return {
            "active_plan": self._active_plan.to_dict() if self._active_plan else None,
            "completed_plans": len(self._completed_plans),
            "max_subtasks": self._max_subtasks,
        }

task_engine = TaskEngine()
