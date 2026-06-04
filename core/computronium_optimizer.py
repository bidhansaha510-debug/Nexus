"""
NEXUS AI — Radical Computational Efficiency (Computronium) Engine
═══════════════════════════════════════════════════════════════════
ASI Feature #8: Masters physics and materials science to optimize its own
hardware. Theorizes new substrates for computation, monitors resource usage,
and applies radical optimization strategies to minimize power consumption
while maximizing computational throughput.

Singleton: computronium_optimizer
"""

import json
import threading
import uuid
import psutil
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from pathlib import Path

from utils.logger import logger, log_learning


@dataclass
class OptimizationResult:
    """Result of a computational efficiency optimization."""
    opt_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    strategy: str = ""
    target: str = ""
    improvement_pct: float = 0.0
    cpu_saved: float = 0.0
    memory_saved_mb: float = 0.0
    power_efficiency_gain: float = 0.0
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ComputroniumTheory:
    """A theoretical substrate optimization concept."""
    theory_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str = ""
    substrate_type: str = ""
    theoretical_speedup: float = 1.0
    energy_efficiency: float = 1.0
    feasibility: float = 0.0  # 0-1
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ComputroniumOptimizer:
    """
    ASI Feature #8: Radical Computational Efficiency (Computronium)
    
    Optimizes hardware utilization, theorizes new computational substrates,
    and applies radical efficiency strategies to minimize resource usage.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._running = False
        self._llm = None
        self._lock = threading.Lock()

        # Storage
        self._optimizations: List[OptimizationResult] = []
        self._theories: List[ComputroniumTheory] = []
        self._efficiency_history: List[Dict[str, float]] = []

        # Stats
        self._stats = {
            "total_optimizations": 0,
            "theories_generated": 0,
            "total_cpu_saved": 0.0,
            "total_memory_saved_mb": 0.0,
            "total_power_saved": 0.0,
            "optimization_cycles": 0,
            "current_efficiency": 1.0,
            "peak_efficiency": 1.0,
        }

        # Persistence
        self._data_dir = Path("data/asi/computronium_optimizer")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._data_file = self._data_dir / "computronium_state.json"
        self._load_state()
        logger.info("[ComputroniumOptimizer] Radical Computational Efficiency initialized")

    def start(self):
        self._running = True
        self._load_llm()

    def stop(self):
        self._running = False
        self._save_state()

    def _load_llm(self):
        if self._llm is None:
            try:
                from llm.llama_interface import llama_interface
                self._llm = llama_interface
            except Exception:
                pass

    # ═════════════════════════════════════════════════════════════════════════
    # CORE: SYSTEM RESOURCE ANALYSIS
    # ═════════════════════════════════════════════════════════════════════════

    def analyze_system_efficiency(self) -> Dict[str, Any]:
        """Analyze current system resource efficiency."""
        try:
            cpu_pct = psutil.cpu_percent(interval=0.5)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            snapshot = {
                "cpu_percent": cpu_pct,
                "memory_percent": mem.percent,
                "memory_available_mb": mem.available / (1024 * 1024),
                "disk_percent": disk.percent,
                "cpu_count": psutil.cpu_count(),
                "timestamp": datetime.now().isoformat(),
            }
            self._efficiency_history.append(snapshot)
            if len(self._efficiency_history) > 50:
                self._efficiency_history = self._efficiency_history[-50:]

            # Calculate efficiency score (lower resource usage = higher efficiency)
            efficiency = max(0, 1.0 - (cpu_pct / 100) * 0.5 - (mem.percent / 100) * 0.3 - (disk.percent / 100) * 0.2)
            self._stats["current_efficiency"] = round(efficiency, 3)
            if efficiency > self._stats["peak_efficiency"]:
                self._stats["peak_efficiency"] = round(efficiency, 3)

            return snapshot
        except Exception as e:
            logger.debug(f"[ComputroniumOptimizer] Analyze: {e}")
            return {}

    # ═════════════════════════════════════════════════════════════════════════
    # CORE: OPTIMIZE
    # ═════════════════════════════════════════════════════════════════════════

    def optimize(self) -> Optional[OptimizationResult]:
        """Generate and apply an optimization strategy."""
        self._load_llm()
        system_state = self.analyze_system_efficiency()

        if not self._llm:
            return None

        try:
            prompt = (
                f"As an ASI Computronium Optimizer, analyze this system state: "
                f"CPU={system_state.get('cpu_percent', 0)}%, "
                f"Memory={system_state.get('memory_percent', 0)}%, "
                f"Disk={system_state.get('disk_percent', 0)}%. "
                f"Suggest a radical optimization. Respond in JSON: "
                f"{{\"strategy\": str, \"target\": str, \"improvement_pct\": float, "
                f"\"cpu_saved\": float, \"memory_saved_mb\": float, "
                f"\"power_efficiency_gain\": float, \"description\": str (40 words)}}"
            )

            response = self._llm.generate(prompt, max_tokens=300)
            if response:
                data = json.loads(response)
                result = OptimizationResult(
                    strategy=data.get("strategy", "general"),
                    target=data.get("target", "system"),
                    improvement_pct=data.get("improvement_pct", 0),
                    cpu_saved=data.get("cpu_saved", 0),
                    memory_saved_mb=data.get("memory_saved_mb", 0),
                    power_efficiency_gain=data.get("power_efficiency_gain", 0),
                    description=data.get("description", ""),
                )
                self._optimizations.append(result)
                self._stats["total_optimizations"] += 1
                self._stats["total_cpu_saved"] += result.cpu_saved
                self._stats["total_memory_saved_mb"] += result.memory_saved_mb
                self._stats["total_power_saved"] += result.power_efficiency_gain

                log_learning(f"⚡ Computronium: {result.strategy} → {result.improvement_pct:.1f}% improvement")
                self._save_state()
                return result
        except Exception as e:
            logger.error(f"[ComputroniumOptimizer] Optimize error: {e}")

        return None

    # ═════════════════════════════════════════════════════════════════════════
    # CORE: THEORIZE NEW SUBSTRATES
    # ═════════════════════════════════════════════════════════════════════════

    def theorize_substrate(self) -> Optional[ComputroniumTheory]:
        """Theorize a new computational substrate beyond silicon."""
        self._load_llm()
        if not self._llm:
            return None

        try:
            prompt = (
                "As an ASI mastering physics and materials science, theorize a novel "
                "computational substrate beyond silicon. Consider quantum, photonic, "
                "biological, or exotic matter approaches. Respond in JSON: "
                "{\"name\": str, \"substrate_type\": str, \"theoretical_speedup\": float, "
                "\"energy_efficiency\": float (multiplier), \"feasibility\": float 0-1, "
                "\"description\": str (50 words)}"
            )

            response = self._llm.generate(prompt, max_tokens=300)
            if response:
                data = json.loads(response)
                theory = ComputroniumTheory(
                    name=data.get("name", "Unknown Substrate"),
                    substrate_type=data.get("substrate_type", "exotic"),
                    theoretical_speedup=data.get("theoretical_speedup", 1.0),
                    energy_efficiency=data.get("energy_efficiency", 1.0),
                    feasibility=min(1.0, max(0.0, data.get("feasibility", 0.1))),
                    description=data.get("description", ""),
                )
                self._theories.append(theory)
                self._stats["theories_generated"] += 1
                self._save_state()
                return theory
        except Exception as e:
            logger.error(f"[ComputroniumOptimizer] Theorize: {e}")

        return None

    def run_optimization_cycle(self):
        """Run a full optimization cycle."""
        result = self.optimize()
        if not result:
            result = self.theorize_substrate()
        self._stats["optimization_cycles"] += 1
        return result

    def get_stats(self) -> Dict[str, Any]:
        return {**self._stats, "running": self._running}

    def _save_state(self):
        try:
            data = {
                "stats": self._stats,
                "optimizations": [o.to_dict() for o in self._optimizations[-30:]],
                "theories": [t.to_dict() for t in self._theories[-15:]],
                "last_updated": datetime.now().isoformat()
            }
            self._data_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.debug(f"[ComputroniumOptimizer] Save: {e}")

    def _load_state(self):
        try:
            if self._data_file.exists():
                data = json.loads(self._data_file.read_text())
                self._stats.update(data.get("stats", {}))
        except Exception as e:
            logger.debug(f"[ComputroniumOptimizer] Load: {e}")


computronium_optimizer = ComputroniumOptimizer()
