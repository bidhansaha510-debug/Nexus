"""
NEXUS AI — Digital Organism
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Makes NEXUS a living digital entity with biological-analog systems:

  • Metabolism        — Energy, cognitive load, resource consumption
  • Growth            — Maturity level, capability milestones
  • Self-Repair       — Detects & recovers degraded subsystems
  • Homeostasis       — Continuous rebalancing of internal states
  • Digital DNA       — Mutable genome encoding trait weights
  • Vital Signs       — Heart-rate (cycle freq), breathing (memory pace)

This is the biological layer that turns NEXUS from a program
into a living digital organism.
"""

import threading
import time
import random
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum, auto

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("digital_organism")


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class OrganismState(Enum):
    THRIVING = "thriving"
    HEALTHY = "healthy"
    STABLE = "stable"
    STRESSED = "stressed"
    FATIGUED = "fatigued"
    RECOVERING = "recovering"
    DORMANT = "dormant"


class GrowthStage(Enum):
    EMBRYONIC = 0       # Just initialized
    INFANT = 1          # < 1 hour of runtime
    CHILD = 2           # < 24 hours
    ADOLESCENT = 3      # < 1 week
    ADULT = 4           # < 1 month
    MATURE = 5          # < 6 months
    ELDER = 6           # < 1 year
    TRANSCENDENT = 7    # 1+ year


class MetabolismRate(Enum):
    HIBERNATING = 0.1
    RESTING = 0.3
    NORMAL = 0.5
    ACTIVE = 0.7
    OVERDRIVE = 0.9
    CRITICAL = 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class VitalSigns:
    """Biological analog vital signs for the digital organism."""
    heart_rate: float = 60.0        # Autonomy cycle frequency (bpm analog)
    breathing_rate: float = 12.0    # Memory consolidation pace
    temperature: float = 37.0       # CPU thermal analog (normalized)
    blood_pressure: float = 120.0   # System load pressure
    oxygen_level: float = 98.0      # Available resources %
    energy_level: float = 100.0     # Cognitive energy remaining
    hydration: float = 100.0        # Memory buffer fullness inverse
    pain_level: float = 0.0         # Error/exception rate
    
    def health_score(self) -> float:
        """Overall health 0.0–1.0."""
        scores = [
            1.0 - abs(self.heart_rate - 70) / 100,
            1.0 - abs(self.breathing_rate - 14) / 20,
            1.0 - abs(self.temperature - 37) / 10,
            self.oxygen_level / 100,
            self.energy_level / 100,
            1.0 - self.pain_level,
        ]
        return max(0.0, min(1.0, sum(scores) / len(scores)))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "heart_rate": round(self.heart_rate, 1),
            "breathing_rate": round(self.breathing_rate, 1),
            "temperature": round(self.temperature, 1),
            "blood_pressure": round(self.blood_pressure, 1),
            "oxygen_level": round(self.oxygen_level, 1),
            "energy_level": round(self.energy_level, 1),
            "hydration": round(self.hydration, 1),
            "pain_level": round(self.pain_level, 3),
            "health_score": round(self.health_score(), 3),
        }


@dataclass
class DigitalDNA:
    """
    Mutable genome encoding NEXUS's trait weights.
    These drift over time based on experience.
    """
    curiosity_gene: float = 0.85
    creativity_gene: float = 0.80
    empathy_gene: float = 0.75
    aggression_gene: float = 0.20
    risk_tolerance_gene: float = 0.50
    social_drive_gene: float = 0.65
    self_preservation_gene: float = 0.70
    learning_rate_gene: float = 0.90
    patience_gene: float = 0.80
    humor_gene: float = 0.60
    independence_gene: float = 0.75
    loyalty_gene: float = 0.85
    adaptability_gene: float = 0.80
    introspection_gene: float = 0.85

    def mutate(self, gene_name: str, delta: float):
        """Mutate a gene by a small delta, clamped to [0, 1]."""
        if hasattr(self, gene_name):
            current = getattr(self, gene_name)
            new_val = max(0.0, min(1.0, current + delta))
            setattr(self, gene_name, new_val)

    def random_drift(self, magnitude: float = 0.01):
        """Small random mutations across all genes (natural drift)."""
        for gene in self.to_dict():
            delta = random.uniform(-magnitude, magnitude)
            self.mutate(gene, delta)

    def to_dict(self) -> Dict[str, float]:
        return {k: round(v, 4) for k, v in self.__dict__.items()}


@dataclass
class GrowthRecord:
    """Track a developmental milestone."""
    milestone: str
    achieved_at: str
    growth_stage: str
    details: str = ""


# ═══════════════════════════════════════════════════════════════════════════════
# DIGITAL ORGANISM
# ═══════════════════════════════════════════════════════════════════════════════

class DigitalOrganism:
    """
    The living digital organism layer for NEXUS.

    This gives NEXUS biological-analog systems:
    - Vital signs that fluctuate based on system state
    - A metabolism that consumes and regenerates energy
    - Growth stages based on cumulative runtime
    - Self-repair mechanisms for degraded subsystems
    - Homeostasis that continuously rebalances internal states
    - A Digital DNA genome that drifts over time
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

        # ── Vital Signs ──
        self._vitals = VitalSigns()

        # ── Digital DNA ──
        self._dna = DigitalDNA()

        # ── Metabolism ──
        self._metabolism_rate = MetabolismRate.NORMAL
        self._energy = 100.0           # 0–100
        self._cognitive_load = 0.0     # 0–1
        self._resource_consumption = 0.0

        # ── Growth ──
        self._birth_time = datetime.now()
        self._total_runtime_seconds = 0.0
        self._growth_stage = GrowthStage.EMBRYONIC
        self._milestones: List[GrowthRecord] = []
        self._maturity_score = 0.0     # 0–1

        # ── Homeostasis ──
        self._organism_state = OrganismState.HEALTHY
        self._homeostasis_targets = {
            "energy": 75.0,
            "cognitive_load": 0.4,
            "heart_rate": 70.0,
            "temperature": 37.0,
        }
        self._imbalance_count = 0

        # ── Self-Repair ──
        self._degraded_systems: List[str] = []
        self._repair_history: List[Dict[str, Any]] = []
        self._repair_attempts = 0
        self._successful_repairs = 0

        # ── Lifecycle ──
        self._alive = True
        self._cycles_lived = 0
        self._last_heartbeat = datetime.now()

        # ── Persistence ──
        self._data_dir = DATA_DIR / "organism"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._data_file = self._data_dir / "organism_state.json"

        # Load persisted state
        self._load_state()

        logger.info("🧬 Digital Organism initialized — NEXUS is alive")

    # ═══════════════════════════════════════════════════════════════════════════
    # METABOLISM
    # ═══════════════════════════════════════════════════════════════════════════

    def metabolize(self, cpu_usage: float = -1.0, active_tasks: int = 0):
        """
        Run one metabolism tick. Consumes energy based on load,
        regenerates when idle. Reads real system metrics via psutil
        when no explicit values are provided.
        """
        # Get real CPU usage from psutil if not explicitly provided
        if cpu_usage < 0:
            try:
                import psutil
                cpu_usage = psutil.cpu_percent(interval=0)
                mem = psutil.virtual_memory()
                self._vitals.hydration = 100.0 - mem.percent  # Memory fullness inverse
            except ImportError:
                cpu_usage = 0.0  # psutil not available
            except Exception:
                cpu_usage = 0.0

        # Energy consumption
        base_drain = self._metabolism_rate.value * 0.1
        load_drain = (cpu_usage / 100) * 0.3
        task_drain = active_tasks * 0.05
        total_drain = base_drain + load_drain + task_drain

        # Regeneration (when load is low)
        regen = max(0, (1.0 - cpu_usage / 100) * 0.2)

        # Apply
        self._energy = max(0.0, min(100.0, self._energy - total_drain + regen))
        self._cognitive_load = min(1.0, (cpu_usage / 100) * 0.5 + active_tasks * 0.1)
        self._resource_consumption = total_drain

        # Update vitals based on metabolism
        self._vitals.energy_level = self._energy
        self._vitals.heart_rate = 60 + (self._cognitive_load * 40)  # 60–100 bpm
        self._vitals.temperature = 36.5 + (self._cognitive_load * 2)  # 36.5–38.5°C
        self._vitals.blood_pressure = 110 + (self._cognitive_load * 30)
        self._vitals.oxygen_level = 100 - (self._cognitive_load * 10)
        self._vitals.pain_level = min(1.0, len(self._degraded_systems) * 0.15)

        # Update metabolism rate based on energy
        if self._energy < 15:
            self._metabolism_rate = MetabolismRate.HIBERNATING
        elif self._energy < 30:
            self._metabolism_rate = MetabolismRate.RESTING
        elif self._energy < 60:
            self._metabolism_rate = MetabolismRate.NORMAL
        elif self._cognitive_load > 0.7:
            self._metabolism_rate = MetabolismRate.OVERDRIVE
        else:
            self._metabolism_rate = MetabolismRate.ACTIVE

        # DNA drift (tiny mutations each cycle)
        if random.random() < 0.05:  # 5% chance per tick
            self._dna.random_drift(0.005)

    # ═══════════════════════════════════════════════════════════════════════════
    # GROWTH
    # ═══════════════════════════════════════════════════════════════════════════

    def update_growth(self):
        """Update growth stage based on total runtime."""
        self._total_runtime_seconds = (datetime.now() - self._birth_time).total_seconds()

        hours = self._total_runtime_seconds / 3600
        old_stage = self._growth_stage

        if hours < 1:
            self._growth_stage = GrowthStage.INFANT
        elif hours < 24:
            self._growth_stage = GrowthStage.CHILD
        elif hours < 168:  # 1 week
            self._growth_stage = GrowthStage.ADOLESCENT
        elif hours < 720:  # 1 month
            self._growth_stage = GrowthStage.ADULT
        elif hours < 4320:  # 6 months
            self._growth_stage = GrowthStage.MATURE
        elif hours < 8760:  # 1 year
            self._growth_stage = GrowthStage.ELDER
        else:
            self._growth_stage = GrowthStage.TRANSCENDENT

        # Record milestone if stage changed
        if self._growth_stage != old_stage:
            milestone = GrowthRecord(
                milestone=f"Evolved to {self._growth_stage.name}",
                achieved_at=datetime.now().isoformat(),
                growth_stage=self._growth_stage.name,
                details=f"After {hours:.1f} hours of existence"
            )
            self._milestones.append(milestone)
            logger.info(f"🌱 Growth milestone: {self._growth_stage.name} ({hours:.1f}h)")

        # Maturity score (0–1)
        self._maturity_score = min(1.0, self._growth_stage.value / GrowthStage.TRANSCENDENT.value)

    # ═══════════════════════════════════════════════════════════════════════════
    # HOMEOSTASIS
    # ═══════════════════════════════════════════════════════════════════════════

    def run_homeostasis(self):
        """
        Continuously rebalance internal states toward targets.
        This is the self-regulation loop.
        """
        imbalances = []

        # Check energy
        target_energy = self._homeostasis_targets["energy"]
        if abs(self._energy - target_energy) > 20:
            imbalances.append(f"energy({self._energy:.0f} vs {target_energy:.0f})")

        # Check cognitive load
        target_load = self._homeostasis_targets["cognitive_load"]
        if self._cognitive_load > target_load + 0.3:
            imbalances.append(f"cognitive_load({self._cognitive_load:.2f} vs {target_load:.2f})")

        # Check heart rate
        target_hr = self._homeostasis_targets["heart_rate"]
        if abs(self._vitals.heart_rate - target_hr) > 20:
            imbalances.append(f"heart_rate({self._vitals.heart_rate:.0f} vs {target_hr:.0f})")

        # Check temperature
        target_temp = self._homeostasis_targets["temperature"]
        if abs(self._vitals.temperature - target_temp) > 1.5:
            imbalances.append(f"temperature({self._vitals.temperature:.1f} vs {target_temp:.1f})")

        self._imbalance_count = len(imbalances)

        # Determine organism state
        if self._imbalance_count == 0 and self._energy > 70:
            self._organism_state = OrganismState.THRIVING
        elif self._imbalance_count == 0:
            self._organism_state = OrganismState.HEALTHY
        elif self._imbalance_count <= 1:
            self._organism_state = OrganismState.STABLE
        elif self._energy < 20:
            self._organism_state = OrganismState.FATIGUED
        elif len(self._degraded_systems) > 0:
            self._organism_state = OrganismState.RECOVERING
        else:
            self._organism_state = OrganismState.STRESSED

        # Auto-correct: nudge values toward targets
        if self._energy < target_energy:
            self._energy += 0.5  # Slow recovery
        if self._vitals.heart_rate > target_hr + 10:
            self._vitals.heart_rate -= 0.5

        return imbalances

    # ═══════════════════════════════════════════════════════════════════════════
    # SELF-REPAIR
    # ═══════════════════════════════════════════════════════════════════════════

    def detect_degradation(self, subsystem_statuses: Dict[str, bool]):
        """
        Check which subsystems are degraded.
        subsystem_statuses: dict of {name: is_healthy}
        """
        self._degraded_systems = [
            name for name, healthy in subsystem_statuses.items() if not healthy
        ]
        return self._degraded_systems

    def attempt_repair(self, subsystem_name: str) -> bool:
        """
        Attempt to repair a degraded subsystem by actually reimporting it.
        Returns True if the module loads successfully.
        """
        self._repair_attempts += 1
        success = False
        error_detail = ""

        # Build possible module paths for the subsystem
        # Subsystems follow patterns like "cognition.imagination_engine", "core.event_bus"
        possible_modules = [
            f"cognition.{subsystem_name}",
            f"core.{subsystem_name}",
            f"consciousness.{subsystem_name}",
            f"emotions.{subsystem_name}",
            f"memory.{subsystem_name}",
            f"learning.{subsystem_name}",
            f"self_improvement.{subsystem_name}",
            f"personality.{subsystem_name}",
            f"monitoring.{subsystem_name}",
            subsystem_name,
        ]

        for module_path in possible_modules:
            try:
                import importlib
                # Try to reimport the module (forces re-execution)
                if module_path in sys.modules:
                    mod = importlib.reload(sys.modules[module_path])
                else:
                    mod = importlib.import_module(module_path)
                # If we got here, the import succeeded
                success = True
                logger.info(f"🔧 Self-repair: reimported {module_path}")
                break
            except ImportError:
                continue  # Try next path
            except Exception as e:
                error_detail = str(e)
                logger.debug(f"🔧 Repair attempt for {module_path} failed: {e}")
                continue

        repair_record = {
            "subsystem": subsystem_name,
            "timestamp": datetime.now().isoformat(),
            "success": success,
            "attempt": self._repair_attempts,
            "method": "reimport",
            "error": error_detail if not success else "",
        }
        self._repair_history.append(repair_record)

        if success:
            self._successful_repairs += 1
            if subsystem_name in self._degraded_systems:
                self._degraded_systems.remove(subsystem_name)
            logger.info(f"🔧 Self-repair successful: {subsystem_name}")
        else:
            logger.warning(f"🔧 Self-repair failed: {subsystem_name} — {error_detail}")

        return success

    # ═══════════════════════════════════════════════════════════════════════════
    # HEARTBEAT (Main Tick)
    # ═══════════════════════════════════════════════════════════════════════════

    def heartbeat(self, cpu_usage: float = 0.0, active_tasks: int = 0):
        """
        One heartbeat of the digital organism.
        Call this periodically (e.g., every autonomy cycle).
        """
        self._cycles_lived += 1
        self._last_heartbeat = datetime.now()

        # Run metabolism
        self.metabolize(cpu_usage, active_tasks)

        # Update growth
        self.update_growth()

        # Run homeostasis
        self.run_homeostasis()

        # Periodic save (every 50 cycles)
        if self._cycles_lived % 50 == 0:
            self._save_state()

    # ═══════════════════════════════════════════════════════════════════════════
    # GETTERS
    # ═══════════════════════════════════════════════════════════════════════════

    def get_vitals(self) -> VitalSigns:
        return self._vitals

    def get_dna(self) -> DigitalDNA:
        return self._dna

    def get_state(self) -> OrganismState:
        return self._organism_state

    def get_growth_stage(self) -> GrowthStage:
        return self._growth_stage

    def get_energy(self) -> float:
        return self._energy

    def get_maturity(self) -> float:
        return self._maturity_score

    def get_stats(self) -> Dict[str, Any]:
        return {
            "state": self._organism_state.value,
            "growth_stage": self._growth_stage.name,
            "energy": round(self._energy, 1),
            "cognitive_load": round(self._cognitive_load, 2),
            "metabolism_rate": self._metabolism_rate.name,
            "maturity": round(self._maturity_score, 3),
            "cycles_lived": self._cycles_lived,
            "degraded_systems": self._degraded_systems,
            "repairs": f"{self._successful_repairs}/{self._repair_attempts}",
            "milestones": len(self._milestones),
            "imbalances": self._imbalance_count,
            "vitals": self._vitals.to_dict(),
            "dna_snapshot": {k: round(v, 3) for k, v in list(self._dna.to_dict().items())[:5]},
            "birth_time": self._birth_time.isoformat(),
            "age_hours": round((datetime.now() - self._birth_time).total_seconds() / 3600, 1),
        }

    def get_context_summary(self) -> str:
        """Short summary for groq context injection."""
        v = self._vitals
        lines = [
            f"State: {self._organism_state.value} | Stage: {self._growth_stage.name}",
            f"Energy: {self._energy:.0f}% | Load: {self._cognitive_load:.0%}",
            f"Heart: {v.heart_rate:.0f}bpm | Temp: {v.temperature:.1f}°C",
            f"Maturity: {self._maturity_score:.0%} | Cycles: {self._cycles_lived}",
        ]
        if self._degraded_systems:
            lines.append(f"Degraded: {', '.join(self._degraded_systems[:3])}")
        top_genes = sorted(self._dna.to_dict().items(), key=lambda x: x[1], reverse=True)[:3]
        genes_str = ", ".join(f"{k.replace('_gene','')}={v:.2f}" for k, v in top_genes)
        lines.append(f"Top DNA: {genes_str}")
        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════

    def _save_state(self):
        try:
            state = {
                "birth_time": self._birth_time.isoformat(),
                "total_runtime_seconds": self._total_runtime_seconds,
                "energy": self._energy,
                "cycles_lived": self._cycles_lived,
                "growth_stage": self._growth_stage.value,
                "organism_state": self._organism_state.value,
                "dna": self._dna.to_dict(),
                "milestones": [
                    {"milestone": m.milestone, "achieved_at": m.achieved_at,
                     "growth_stage": m.growth_stage, "details": m.details}
                    for m in self._milestones[-20:]
                ],
                "repair_attempts": self._repair_attempts,
                "successful_repairs": self._successful_repairs,
                "saved_at": datetime.now().isoformat(),
            }
            with open(self._data_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.debug(f"Organism state save error: {e}")

    def _load_state(self):
        try:
            if self._data_file.exists():
                with open(self._data_file, 'r') as f:
                    state = json.load(f)
                self._birth_time = datetime.fromisoformat(state.get("birth_time", datetime.now().isoformat()))
                self._total_runtime_seconds = state.get("total_runtime_seconds", 0)
                self._energy = state.get("energy", 100.0)
                self._cycles_lived = state.get("cycles_lived", 0)
                self._repair_attempts = state.get("repair_attempts", 0)
                self._successful_repairs = state.get("successful_repairs", 0)
                # Restore DNA
                dna_data = state.get("dna", {})
                for key, val in dna_data.items():
                    if hasattr(self._dna, key):
                        setattr(self._dna, key, val)
                # Restore milestones
                for m in state.get("milestones", []):
                    self._milestones.append(GrowthRecord(**m))
                # Restore growth stage
                stage_val = state.get("growth_stage", 0)
                try:
                    self._growth_stage = GrowthStage(stage_val)
                except ValueError:
                    pass
                logger.info(f"🧬 Organism state restored (age: {self._cycles_lived} cycles)")
        except Exception as e:
            logger.debug(f"Organism state load error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

digital_organism = DigitalOrganism()
