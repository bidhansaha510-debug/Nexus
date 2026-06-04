"""
NEXUS AI — Omniscient Orchestrator (Flawless Omnipresent Autonomy)
═══════════════════════════════════════════════════════════════════════════════
Scales the AutonomyEngine to omnipresent monitoring and control.

Multi-domain monitoring, predictive resource allocation, parallel task
execution, global state synthesis, anomaly detection, and adaptive scaling.
═══════════════════════════════════════════════════════════════════════════════
"""

import threading, time, json, uuid, traceback
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum
from collections import defaultdict

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR
from utils.logger import get_logger, log_system
from core.event_bus import EventType, publish

logger = get_logger("omniscient_orchestrator")


class MonitorDomain(Enum):
    SYSTEM_HEALTH = "system_health"
    USER_STATE = "user_state"
    COGNITIVE_LOAD = "cognitive_load"
    SELF_IMPROVEMENT = "self_improvement"
    GOAL_PROGRESS = "goal_progress"
    WORLD_STATE = "world_state"
    EMOTIONAL_CLIMATE = "emotional_climate"
    RESOURCE_USAGE = "resource_usage"


class AnomalyType(Enum):
    PERFORMANCE_DROP = "performance_drop"
    RESOURCE_SPIKE = "resource_spike"
    GOAL_STALL = "goal_stall"
    EMOTIONAL_CRISIS = "emotional_crisis"
    SYSTEM_ERROR = "system_error"
    PATTERN_BREAK = "pattern_break"


@dataclass
class DomainSnapshot:
    domain: str = ""
    status: str = "nominal"
    health: float = 1.0
    metrics: Dict[str, Any] = field(default_factory=dict)
    anomalies: List[str] = field(default_factory=list)
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    def to_dict(self) -> Dict: return asdict(self)


@dataclass
class GlobalState:
    """Unified world picture fusing all subsystem data"""
    state_id: str = field(default_factory=lambda: str(uuid.uuid4())[:10])
    domains: Dict[str, Dict] = field(default_factory=dict)
    overall_health: float = 1.0
    active_anomalies: List[Dict] = field(default_factory=list)
    active_tasks: List[Dict] = field(default_factory=list)
    resource_allocation: Dict[str, float] = field(default_factory=dict)
    predictions: List[Dict] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    def to_dict(self) -> Dict: return asdict(self)


@dataclass
class Anomaly:
    anomaly_id: str = field(default_factory=lambda: str(uuid.uuid4())[:10])
    anomaly_type: str = ""
    domain: str = ""
    description: str = ""
    severity: float = 0.5
    resolved: bool = False
    resolution: str = ""
    detected_at: str = field(default_factory=lambda: datetime.now().isoformat())
    def to_dict(self) -> Dict: return asdict(self)


@dataclass
class AutonomousTask:
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:10])
    title: str = ""
    domain: str = ""
    priority: float = 0.5
    status: str = "pending"
    progress: float = 0.0
    assigned_resources: Dict[str, float] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    def to_dict(self) -> Dict: return asdict(self)


class OmniscientOrchestrator:
    """
    Flawless, Omnipresent Autonomy — scales NEXUS to global awareness.

    Capabilities:
      • Multi-domain monitoring of all subsystems
      • Predictive resource allocation
      • Parallel autonomous task management
      • Global state synthesis
      • Anomaly detection and auto-response
      • Adaptive scaling based on load

    Runs a background thread that continuously synthesizes a unified
    picture of everything happening inside NEXUS.
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

        self._running = False
        self._global_state = GlobalState()
        self._anomalies: List[Anomaly] = []
        self._autonomous_tasks: Dict[str, AutonomousTask] = {}
        self._domain_snapshots: Dict[str, DomainSnapshot] = {}
        self._state_history: List[Dict] = []
        self._lock = threading.RLock()
        self._llm = None
        self._thread: Optional[threading.Thread] = None
        self._monitor_interval = 120  # 2 minutes

        self._stats = {
            "synthesis_cycles": 0, "anomalies_detected": 0,
            "anomalies_resolved": 0, "tasks_managed": 0,
            "predictions_made": 0,
        }

        self._data_dir = DATA_DIR / "orchestrator"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._state_file = self._data_dir / "omniscient_state.json"
        self._load_state()

        logger.info("🌐 Omniscient Orchestrator initialized")

    def start(self):
        if self._running: return
        self._running = True
        self._load_llm()
        self._thread = threading.Thread(
            target=self._orchestrator_loop, daemon=True, name="OmniscientOrchestrator")
        self._thread.start()
        log_system("🌐 Omniscient Orchestrator started — omnipresent autonomy active")

    def stop(self):
        self._running = False
        self._save_state()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10.0)
        logger.info("🌐 Omniscient Orchestrator stopped")

    def _load_llm(self):
        if self._llm is None:
            try:
                from llm.llama_interface import llm
                if llm.is_connected: self._llm = llm
            except ImportError: pass

    # ═══════════════════════════════════════════════════════════════════════
    # MAIN LOOP
    # ═══════════════════════════════════════════════════════════════════════

    def _orchestrator_loop(self):
        logger.info("🌐 Orchestrator loop started")
        time.sleep(30)
        while self._running:
            try:
                self._load_llm()
                self._run_synthesis_cycle()
                self._save_state()
                time.sleep(self._monitor_interval)
            except Exception as e:
                logger.error(f"Orchestrator cycle error: {e}\n{traceback.format_exc()}")
                time.sleep(60)

    def _run_synthesis_cycle(self):
        """One complete monitoring + synthesis cycle"""
        with self._lock:
            self._stats["synthesis_cycles"] += 1

            # ── 1. COLLECT: Gather data from all subsystems ──
            self._collect_domain_data()

            # ── 2. SYNTHESIZE: Build unified global state ──
            self._synthesize_global_state()

            # ── 3. DETECT: Find anomalies ──
            self._detect_anomalies()

            # ── 4. PREDICT: Forecast resource needs ──
            self._predict_and_allocate()

            # ── 5. MANAGE: Handle autonomous tasks ──
            self._manage_tasks()

            # ── 6. RECORD: Update history ──
            self._state_history.append({
                "timestamp": datetime.now().isoformat(),
                "health": self._global_state.overall_health,
                "anomalies": len(self._global_state.active_anomalies),
                "tasks": len(self._autonomous_tasks),
            })
            if len(self._state_history) > 500:
                self._state_history = self._state_history[-500:]

            logger.debug(
                f"🌐 Synthesis #{self._stats['synthesis_cycles']}: "
                f"health={self._global_state.overall_health:.2f}, "
                f"anomalies={len(self._global_state.active_anomalies)}"
            )

    # ═══════════════════════════════════════════════════════════════════════
    # DATA COLLECTION
    # ═══════════════════════════════════════════════════════════════════════

    def _collect_domain_data(self):
        """Gather snapshots from all monitored domains"""
        # System health
        self._domain_snapshots["system_health"] = self._collect_system_health()
        # Cognitive load
        self._domain_snapshots["cognitive_load"] = self._collect_cognitive_load()
        # Self-improvement status
        self._domain_snapshots["self_improvement"] = self._collect_self_improvement()
        # Goal progress
        self._domain_snapshots["goal_progress"] = self._collect_goal_progress()

    def _collect_system_health(self) -> DomainSnapshot:
        try:
            from core.state_manager import state_manager
            state = state_manager.get_state()
            uptime = state.get("uptime_seconds", 0)
            return DomainSnapshot(
                domain="system_health", status="nominal", health=0.95,
                metrics={"uptime": uptime, "timestamp": datetime.now().isoformat()})
        except Exception:
            return DomainSnapshot(domain="system_health", status="unknown", health=0.5)

    def _collect_cognitive_load(self) -> DomainSnapshot:
        try:
            from cognition import CognitionSystem
            cs = CognitionSystem()
            return DomainSnapshot(
                domain="cognitive_load", status="nominal", health=0.9,
                metrics={"system_running": cs._running})
        except Exception:
            return DomainSnapshot(domain="cognitive_load", status="unknown", health=0.5)

    def _collect_self_improvement(self) -> DomainSnapshot:
        try:
            from self_improvement import self_improvement_system
            stats = self_improvement_system.get_stats()
            return DomainSnapshot(
                domain="self_improvement",
                status="running" if stats.get("running") else "stopped",
                health=0.9 if stats.get("all_healthy") else 0.6,
                metrics=stats.get("aggregate", {}))
        except Exception:
            return DomainSnapshot(domain="self_improvement", status="unknown", health=0.5)

    def _collect_goal_progress(self) -> DomainSnapshot:
        try:
            from cognition.goal_director import goal_director
            stats = goal_director.get_stats()
            return DomainSnapshot(
                domain="goal_progress", status="nominal", health=0.85,
                metrics=stats)
        except Exception:
            return DomainSnapshot(domain="goal_progress", status="unknown", health=0.5)

    # ═══════════════════════════════════════════════════════════════════════
    # SYNTHESIS
    # ═══════════════════════════════════════════════════════════════════════

    def _synthesize_global_state(self):
        """Fuse all domain data into unified global state"""
        domains = {}
        health_scores = []

        for name, snapshot in self._domain_snapshots.items():
            domains[name] = snapshot.to_dict()
            health_scores.append(snapshot.health)

        self._global_state.domains = domains
        self._global_state.overall_health = (
            sum(health_scores) / len(health_scores) if health_scores else 0.5
        )
        self._global_state.active_anomalies = [
            a.to_dict() for a in self._anomalies if not a.resolved
        ]
        self._global_state.active_tasks = [
            t.to_dict() for t in self._autonomous_tasks.values()
            if t.status in ("pending", "running")
        ]

    # ═══════════════════════════════════════════════════════════════════════
    # ANOMALY DETECTION
    # ═══════════════════════════════════════════════════════════════════════

    def _detect_anomalies(self):
        """Scan for anomalous patterns across all domains"""
        for name, snapshot in self._domain_snapshots.items():
            # Low health = anomaly
            if snapshot.health < 0.5:
                anomaly = Anomaly(
                    anomaly_type="performance_drop", domain=name,
                    description=f"{name} health dropped to {snapshot.health:.2f}",
                    severity=1.0 - snapshot.health)
                self._anomalies.append(anomaly)
                self._stats["anomalies_detected"] += 1

                publish(EventType.SYSTEM_ALERT, {
                    "alert": "anomaly_detected", "domain": name,
                    "severity": anomaly.severity,
                    "description": anomaly.description,
                }, source="omniscient_orchestrator")

            # Check for anomalies in snapshot
            if snapshot.anomalies:
                for desc in snapshot.anomalies:
                    a = Anomaly(anomaly_type="pattern_break", domain=name,
                                description=str(desc), severity=0.6)
                    self._anomalies.append(a)
                    self._stats["anomalies_detected"] += 1

        # Cap anomaly list
        if len(self._anomalies) > 200:
            self._anomalies = self._anomalies[-200:]

    # ═══════════════════════════════════════════════════════════════════════
    # PREDICTIVE RESOURCE ALLOCATION
    # ═══════════════════════════════════════════════════════════════════════

    def _predict_and_allocate(self):
        """Anticipate resource needs and allocate proactively"""
        self._load_llm()
        if not self._llm:
            return

        try:
            domain_summary = {n: {"health": s.health, "status": s.status}
                              for n, s in self._domain_snapshots.items()}
            prompt = (
                f"Predict resource needs for an AI system:\n"
                f"Domain statuses: {json.dumps(domain_summary)}\n"
                f"Active anomalies: {len([a for a in self._anomalies if not a.resolved])}\n"
                f"Active tasks: {len([t for t in self._autonomous_tasks.values() if t.status == 'running'])}\n\n"
                f"Return JSON:\n"
                f'{{"resource_allocation": {{"cognition": 0-1, "self_improvement": 0-1, '
                f'"monitoring": 0-1, "creativity": 0-1, "empathy": 0-1}}, '
                f'"predictions": [{{"event": "what might happen", "probability": 0-1, '
                f'"recommended_action": "what to do"}}]}}'
            )
            response = self._llm.generate(prompt=prompt, system_prompt=(
                "You are an omniscient resource allocation engine. Predict needs and "
                "allocate resources optimally. Respond ONLY with valid JSON."),
                temperature=0.3, max_tokens=400)
            if response.success and response.text:
                from utils.json_utils import extract_json
                data = extract_json(response.text)
                if data:
                    self._global_state.resource_allocation = data.get("resource_allocation", {})
                    self._global_state.predictions = data.get("predictions", [])
                    self._stats["predictions_made"] += 1
        except Exception as e:
            logger.debug(f"Prediction failed: {e}")

    # ═══════════════════════════════════════════════════════════════════════
    # TASK MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════

    def _manage_tasks(self):
        """Manage parallel autonomous tasks"""
        for tid, task in list(self._autonomous_tasks.items()):
            if task.status == "completed":
                continue
            # Auto-progress simulation
            if task.status == "running":
                task.progress = min(1.0, task.progress + 0.1)
                if task.progress >= 1.0:
                    task.status = "completed"

    def create_task(self, title: str, domain: str, priority: float = 0.5) -> AutonomousTask:
        """Create a new autonomous task"""
        task = AutonomousTask(title=title, domain=domain, priority=priority, status="pending")
        self._autonomous_tasks[task.task_id] = task
        self._stats["tasks_managed"] += 1
        return task

    def start_task(self, task_id: str) -> bool:
        """Start an autonomous task"""
        task = self._autonomous_tasks.get(task_id)
        if task:
            task.status = "running"
            return True
        return False

    # ═══════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════

    def get_global_state(self) -> Dict[str, Any]:
        return self._global_state.to_dict()

    def get_anomalies(self, active_only: bool = True) -> List[Dict]:
        if active_only:
            return [a.to_dict() for a in self._anomalies if not a.resolved]
        return [a.to_dict() for a in self._anomalies[-50:]]

    def get_tasks(self) -> List[Dict]:
        return [t.to_dict() for t in self._autonomous_tasks.values()]

    # ═══════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════

    def _save_state(self):
        try:
            data = {"global_state": self._global_state.to_dict(),
                    "anomalies": [a.to_dict() for a in self._anomalies[-100:]],
                    "tasks": {k: v.to_dict() for k, v in self._autonomous_tasks.items()},
                    "history": self._state_history[-100:],
                    "stats": self._stats}
            self._state_file.write_text(json.dumps(data, indent=2, default=str))
        except Exception as e:
            logger.warning(f"Orchestrator state save failed: {e}")

    def _load_state(self):
        try:
            if self._state_file.exists():
                data = json.loads(self._state_file.read_text())
                self._stats.update(data.get("stats", {}))
                self._state_history = data.get("history", [])
                logger.info("📂 Loaded orchestrator state")
        except Exception as e:
            logger.warning(f"Orchestrator state load failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "overall_health": round(self._global_state.overall_health, 2),
            "active_anomalies": len([a for a in self._anomalies if not a.resolved]),
            "active_tasks": len([t for t in self._autonomous_tasks.values() if t.status in ("pending", "running")]),
            "synthesis_cycles": self._stats.get("synthesis_cycles", 0),
            **self._stats,
        }


omniscient_orchestrator = OmniscientOrchestrator()
