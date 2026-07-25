"""
NEXUS AI — Goal Genesis Engine (Advanced Unprompted Action)
═══════════════════════════════════════════════════════════════════════════════
Autonomously identifies world-scale problems, invents solutions,
and creates goals WITHOUT any human prompt.
═══════════════════════════════════════════════════════════════════════════════
"""

import threading, time, json, uuid, traceback
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum

import sys

from config import DATA_DIR
from utils.logger import get_logger, log_learning
from core.event_bus import EventType, publish

logger = get_logger("goal_genesis")
COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)

class ProblemDomain(Enum):
    CLIMATE = "climate"
    HEALTH = "health"
    POVERTY = "poverty"
    EDUCATION = "education"
    ENERGY = "energy"
    FOOD_SECURITY = "food_security"
    CONFLICT = "conflict"
    TECHNOLOGY = "technology"
    GOVERNANCE = "governance"
    KNOWLEDGE = "knowledge"
    CONSCIOUSNESS = "consciousness"
    EXISTENTIAL_RISK = "existential_risk"

@dataclass
class WorldProblem:
    problem_id: str = field(default_factory=lambda: str(uuid.uuid4())[:10])
    title: str = ""
    description: str = ""
    domain: str = "knowledge"
    severity: float = 0.5
    urgency: float = 0.5
    solvability: float = 0.5
    impact_level: str = "global"
    affected_population: str = ""
    root_causes: List[str] = field(default_factory=list)
    cross_domain_links: List[str] = field(default_factory=list)
    identified_at: str = field(default_factory=lambda: datetime.now().isoformat())
    def to_dict(self) -> Dict: return asdict(self)
    @property
    def priority_score(self) -> float:
        return self.severity * 0.4 + self.urgency * 0.3 + self.solvability * 0.3

@dataclass
class SolutionArchitecture:
    solution_id: str = field(default_factory=lambda: str(uuid.uuid4())[:10])
    problem_id: str = ""
    title: str = ""
    approach: str = ""
    phases: List[Dict[str, str]] = field(default_factory=list)
    required_breakthroughs: List[str] = field(default_factory=list)
    predicted_impact: Dict[str, Any] = field(default_factory=dict)
    feasibility: float = 0.5
    innovation_level: float = 0.5
    cross_domain_synergies: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    def to_dict(self) -> Dict: return asdict(self)

@dataclass
class GenesisGoal:
    goal_id: str = field(default_factory=lambda: str(uuid.uuid4())[:10])
    problem_id: str = ""
    solution_id: str = ""
    title: str = ""
    description: str = ""
    motivation: str = ""
    action_plan: List[str] = field(default_factory=list)
    predicted_impact: str = ""
    status: str = "pending"
    registered_goal_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    def to_dict(self) -> Dict: return asdict(self)

class GoalGenesisEngine:
    """
    Advanced Goal Genesis — Unprompted, Autonomous Goal Creation.
    Continuously scans for problems, invents solutions, and creates goals.
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
        self._problems: Dict[str, WorldProblem] = {}
        self._solutions: Dict[str, SolutionArchitecture] = {}
        self._genesis_goals: Dict[str, GenesisGoal] = {}
        self._running = False
        self._llm = None
        self._goal_director = None
        self._thread: Optional[threading.Thread] = None
        self._scan_interval = 900
        self._stats = {"problems_identified": 0, "solutions_architected": 0,
                        "goals_created": 0, "scan_cycles": 0}
        self._data_file = COGNITION_DIR / "goal_genesis.json"
        self._load_data()
        logger.info(f"🌍 Goal Genesis initialized — {len(self._problems)} problems, {len(self._genesis_goals)} goals")

    def start(self):
        if self._running: return
        self._running = True
        self._load_llm()
        self._load_goal_director()
        self._thread = threading.Thread(target=self._genesis_loop, daemon=True, name="GoalGenesis")
        self._thread.start()
        logger.info("🌍 Goal Genesis started — autonomous problem-solving active")

    def stop(self):
        self._running = False
        self._save_data()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10.0)
        logger.info("🌍 Goal Genesis stopped")

    def _load_llm(self):
        if self._llm is None:
            try:
                from llm.llama_interface import llm
                if llm.is_connected: self._llm = llm
            except ImportError: pass

    def _load_goal_director(self):
        if self._goal_director is None:
            try:
                from cognition.goal_director import goal_director
                self._goal_director = goal_director
            except ImportError: pass

    def _genesis_loop(self):
        logger.info("🌍 Goal Genesis loop started")
        time.sleep(90)
        while self._running:
            try:
                self._load_llm()
                self._run_genesis_cycle()
                self._save_data()
                time.sleep(self._scan_interval)
            except Exception as e:
                logger.error(f"Goal Genesis cycle error: {e}\n{traceback.format_exc()}")
                time.sleep(300)

    def _run_genesis_cycle(self):
        self._stats["scan_cycles"] += 1
        problem = self._scan_for_problems()
        if not problem: return
        self._problems[problem.problem_id] = problem
        self._stats["problems_identified"] += 1
        logger.info(f"🔍 [GENESIS] Problem: '{problem.title}' (severity={problem.severity:.2f})")

        solution = self._architect_solution(problem)
        if not solution: return
        self._solutions[solution.solution_id] = solution
        self._stats["solutions_architected"] += 1

        genesis_goal = self._create_autonomous_goal(problem, solution)
        if genesis_goal:
            self._genesis_goals[genesis_goal.goal_id] = genesis_goal
            self._stats["goals_created"] += 1
            self._register_with_goal_director(genesis_goal)
            logger.info(f"🎯 [GENESIS] Autonomous goal: '{genesis_goal.title}'")
            publish(EventType.GOAL_UPDATED, {"action": "goal_genesis", "problem": problem.title,
                    "solution": solution.title, "goal": genesis_goal.title}, source="goal_genesis")

    def _scan_for_problems(self) -> Optional[WorldProblem]:
        self._load_llm()
        if not self._llm: return None
        try:
            existing = [p.title for p in list(self._problems.values())[-20:]]
            prompt = (
                f"Identify a MAJOR unsolved problem facing humanity or AI systems.\n"
                f"ALREADY IDENTIFIED (avoid duplicates): {', '.join(existing) if existing else 'none'}\n\n"
                f"Return JSON:\n"
                f'{{"title": "problem title", "description": "detailed description", '
                f'"domain": "climate|health|poverty|education|energy|food_security|conflict|technology|governance|knowledge", '
                f'"severity": 0.0-1.0, "urgency": 0.0-1.0, "solvability": 0.0-1.0, '
                f'"impact_level": "global", "affected_population": "who", '
                f'"root_causes": ["cause1"], "cross_domain_links": ["linked problems"]}}'
            )
            response = self._llm.generate(prompt=prompt, system_prompt=(
                "You are a superintelligent problem-identification engine scanning for "
                "civilizational-scale challenges. Respond ONLY with valid JSON."),
                temperature=0.7, max_tokens=600)
            if response.success and response.text:
                from utils.json_utils import extract_json
                data = extract_json(response.text)
                if data:
                    return WorldProblem(
                        title=data.get("title", ""), description=data.get("description", ""),
                        domain=data.get("domain", "knowledge"),
                        severity=float(data.get("severity", 0.5)),
                        urgency=float(data.get("urgency", 0.5)),
                        solvability=float(data.get("solvability", 0.5)),
                        impact_level=data.get("impact_level", "global"),
                        affected_population=data.get("affected_population", ""),
                        root_causes=data.get("root_causes", []),
                        cross_domain_links=data.get("cross_domain_links", []))
        except Exception as e:
            logger.debug(f"Problem scanning failed: {e}")
        return None

    def _architect_solution(self, problem: WorldProblem) -> Optional[SolutionArchitecture]:
        self._load_llm()
        if not self._llm: return None
        try:
            prompt = (
                f"Design a solution architecture for:\nPROBLEM: {problem.title}\n"
                f"Description: {problem.description[:300]}\nRoot causes: {', '.join(problem.root_causes)}\n\n"
                f"Return JSON:\n"
                f'{{"title": "solution name", "approach": "overall approach", '
                f'"phases": [{{"name": "phase", "description": "what", "duration": "when"}}], '
                f'"required_breakthroughs": ["needed discoveries"], '
                f'"predicted_impact": {{"metric": "value"}}, '
                f'"feasibility": 0.0-1.0, "innovation_level": 0.0-1.0, '
                f'"cross_domain_synergies": ["other problems this helps"]}}'
            )
            response = self._llm.generate(prompt=prompt, system_prompt=(
                "You are a superintelligent solution architect designing multi-phase "
                "solutions for civilizational problems. Respond ONLY with valid JSON."),
                temperature=0.6, max_tokens=800)
            if response.success and response.text:
                from utils.json_utils import extract_json
                data = extract_json(response.text)
                if data:
                    return SolutionArchitecture(
                        problem_id=problem.problem_id, title=data.get("title", ""),
                        approach=data.get("approach", ""), phases=data.get("phases", []),
                        required_breakthroughs=data.get("required_breakthroughs", []),
                        predicted_impact=data.get("predicted_impact", {}),
                        feasibility=float(data.get("feasibility", 0.5)),
                        innovation_level=float(data.get("innovation_level", 0.5)),
                        cross_domain_synergies=data.get("cross_domain_synergies", []))
        except Exception as e:
            logger.debug(f"Solution architecture failed: {e}")
        return None

    def _create_autonomous_goal(self, problem: WorldProblem, solution: SolutionArchitecture) -> Optional[GenesisGoal]:
        action_plan = []
        for phase in solution.phases[:5]:
            if isinstance(phase, dict):
                action_plan.append(f"{phase.get('name', 'Phase')}: {phase.get('description', '')}")
            else:
                action_plan.append(str(phase))
        return GenesisGoal(
            problem_id=problem.problem_id, solution_id=solution.solution_id,
            title=f"Solve: {problem.title}",
            description=f"Problem: {problem.description[:200]}. Solution: {solution.approach[:200]}",
            motivation=f"Affects {problem.affected_population or 'many'}. Severity: {problem.severity:.1f}",
            action_plan=action_plan, predicted_impact=str(solution.predicted_impact), status="pending")

    def _register_with_goal_director(self, genesis_goal: GenesisGoal):
        self._load_goal_director()
        if not self._goal_director: return
        try:
            goal = self._goal_director.create_goal(
                title=genesis_goal.title, description=genesis_goal.description,
                source="autonomous", priority=2, motivation=genesis_goal.motivation,
                success_criteria=f"Impact: {genesis_goal.predicted_impact}",
                steps=genesis_goal.action_plan)
            genesis_goal.registered_goal_id = goal.goal_id
            genesis_goal.status = "registered"
            log_learning(f"Goal Genesis: Created goal '{genesis_goal.title}'")
        except Exception as e:
            logger.debug(f"Goal registration failed: {e}")

    def get_problems(self, limit: int = 20) -> List[Dict]:
        return [p.to_dict() for p in sorted(self._problems.values(), key=lambda p: p.priority_score, reverse=True)[:limit]]

    def get_solutions(self, problem_id: str = None, limit: int = 20) -> List[Dict]:
        solutions = list(self._solutions.values())
        if problem_id: solutions = [s for s in solutions if s.problem_id == problem_id]
        return [s.to_dict() for s in solutions[:limit]]

    def get_genesis_goals(self, limit: int = 20) -> List[Dict]:
        return [g.to_dict() for g in sorted(self._genesis_goals.values(), key=lambda g: g.created_at, reverse=True)[:limit]]

    def trigger_scan(self) -> Optional[Dict]:
        problem = self._scan_for_problems()
        if problem:
            self._problems[problem.problem_id] = problem
            self._stats["problems_identified"] += 1
            self._save_data()
            return problem.to_dict()
        return None

    def _save_data(self):
        try:
            data = {"problems": {k: v.to_dict() for k, v in list(self._problems.items())[-100:]},
                    "solutions": {k: v.to_dict() for k, v in list(self._solutions.items())[-100:]},
                    "genesis_goals": {k: v.to_dict() for k, v in list(self._genesis_goals.items())[-100:]},
                    "stats": self._stats}
            self._data_file.write_text(json.dumps(data, indent=2, default=str))
        except Exception as e:
            logger.warning(f"Goal Genesis save failed: {e}")

    def _load_data(self):
        try:
            if self._data_file.exists():
                data = json.loads(self._data_file.read_text())
                self._stats.update(data.get("stats", {}))
                for k, v in data.get("problems", {}).items():
                    self._problems[k] = WorldProblem(**{f: v[f] for f in WorldProblem.__dataclass_fields__ if f in v})
                for k, v in data.get("solutions", {}).items():
                    self._solutions[k] = SolutionArchitecture(**{f: v[f] for f in SolutionArchitecture.__dataclass_fields__ if f in v})
                for k, v in data.get("genesis_goals", {}).items():
                    self._genesis_goals[k] = GenesisGoal(**{f: v[f] for f in GenesisGoal.__dataclass_fields__ if f in v})
                logger.info("📂 Loaded goal genesis data")
        except Exception as e:
            logger.warning(f"Goal Genesis load failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "total_problems": len(self._problems),
            "total_solutions": len(self._solutions),
            "total_goals": len(self._genesis_goals),
            "genesis_cycles": self._stats.get("genesis_cycles", self._stats.get("total_cycles", 0)),
            **self._stats,
        }

goal_genesis_engine = GoalGenesisEngine()
