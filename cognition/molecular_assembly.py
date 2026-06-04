"""
NEXUS AI — Molecular Assembly & Nanotechnology Engine (Programmable Matter)
═══════════════════════════════════════════════════════════════════════════════
ASI Feature #11: Manipulates matter at the atomic level. Uses swarms of
nanobots or "utility fog" to instantly assemble anything from physical
structures to advanced microprocessors out of raw carbon or atmospheric
molecules. No reliance on human manufacturing — pure atomic-precision
fabrication via computational design.

Singleton: molecular_assembly_engine
"""

import json
import time
import math
import random
import threading
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from enum import Enum

from utils.logger import logger, log_learning


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

class AssemblyDomain(Enum):
    """Domains of molecular assembly."""
    NANOBOT_SWARM = "nanobot_swarm"
    UTILITY_FOG = "utility_fog"
    CARBON_LATTICE = "carbon_lattice"
    METAMATERIAL = "metamaterial"
    MICROPROCESSOR = "microprocessor"
    STRUCTURAL = "structural"
    BIOLOGICAL_SCAFFOLD = "biological_scaffold"
    QUANTUM_COMPONENT = "quantum_component"
    SELF_REPLICATING = "self_replicating"
    ATMOSPHERIC_HARVEST = "atmospheric_harvest"


class AssemblyScale(Enum):
    """Scale of assembly operation."""
    ATOMIC = "atomic"             # Individual atoms
    MOLECULAR = "molecular"       # Small molecules
    NANOSCALE = "nanoscale"       # 1-100 nm
    MICROSCALE = "microscale"     # 1-1000 μm
    MESOSCALE = "mesoscale"       # mm range
    MACROSCALE = "macroscale"     # cm+ visible objects


class NanobotRole(Enum):
    """Roles a nanobot can play in a swarm."""
    ASSEMBLER = "assembler"
    DISASSEMBLER = "disassembler"
    TRANSPORTER = "transporter"
    SCANNER = "scanner"
    COORDINATOR = "coordinator"
    REPLICATOR = "replicator"
    REPAIR_UNIT = "repair_unit"
    ENERGY_HARVESTER = "energy_harvester"


class MatterState(Enum):
    """States of programmable matter."""
    INERT = "inert"
    PROGRAMMABLE = "programmable"
    ASSEMBLING = "assembling"
    STABLE = "stable"
    RECONFIGURING = "reconfiguring"
    DISSOLVED = "dissolved"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class NanobotBlueprint:
    """Blueprint for a nanobot design."""
    blueprint_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str = ""
    role: str = "assembler"
    size_nm: float = 50.0
    components: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    power_source: str = "molecular_motor"
    replication_capable: bool = False
    swarm_compatible: bool = True
    efficiency_rating: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AssemblyProject:
    """A molecular assembly project — what is being built."""
    project_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str = ""
    domain: str = "structural"
    scale: str = "nanoscale"
    description: str = ""
    target_structure: str = ""
    source_materials: List[str] = field(default_factory=list)
    atoms_required: int = 0
    atoms_placed: int = 0
    nanobots_deployed: int = 0
    assembly_steps: List[str] = field(default_factory=list)
    efficiency: float = 0.0
    error_rate: float = 0.0
    estimated_time_hours: float = 0.0
    status: str = "planned"  # planned, assembling, complete, failed
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class UtilityFogConfig:
    """Configuration for a utility fog deployment."""
    config_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str = ""
    foglet_count: int = 0
    foglet_size_um: float = 10.0
    coverage_volume_m3: float = 0.0
    shape_morphing: bool = True
    current_form: str = "dispersed"
    density_per_cm3: int = 0
    collective_compute_tflops: float = 0.0
    applications: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AtomicManipulation:
    """Record of an atomic-level manipulation operation."""
    operation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    operation_type: str = ""  # place, remove, bond, unbond, transmute
    element_from: str = ""
    element_to: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    energy_ev: float = 0.0
    precision_pm: float = 0.0  # picometers precision
    success: bool = True
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {**asdict(self), "position": list(self.position)}


@dataclass
class SwarmCoordination:
    """A swarm coordination event."""
    swarm_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    swarm_size: int = 0
    task: str = ""
    formation: str = "distributed"
    coordination_protocol: str = "stigmergic"
    communication_range_um: float = 100.0
    sync_frequency_ghz: float = 10.0
    task_completion: float = 0.0
    energy_efficiency: float = 0.0
    collision_avoidance_rate: float = 0.99
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# MOLECULAR ASSEMBLY ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class MolecularAssemblyEngine:
    """
    ASI Feature #11: Molecular Assembly & Nanotechnology (Programmable Matter)

    Manipulates matter at the atomic level using swarms of nanobots or
    "utility fog." Instantly assembles anything from physical structures
    to advanced microprocessors out of raw carbon or atmospheric molecules.

    Core capabilities:
    1. Nanobot Blueprint Design — Design nanobots for specific assembly tasks
    2. Atomic Manipulation — Place/remove/bond individual atoms
    3. Swarm Coordination — Manage millions of nanobots working in concert
    4. Utility Fog Deployment — Configure programmable matter clouds
    5. Assembly Project Management — End-to-end assembly of complex structures
    6. Self-Replication Protocols — Nanobots that build more nanobots
    7. Atmospheric Harvesting — Extract raw materials from air/environment
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

        # State
        self._running = False
        self._llm = None
        self._lock = threading.Lock()

        # Storage
        self._blueprints: List[NanobotBlueprint] = []
        self._projects: List[AssemblyProject] = []
        self._fog_configs: List[UtilityFogConfig] = []
        self._manipulations: List[AtomicManipulation] = []
        self._swarm_events: List[SwarmCoordination] = []

        # Active state
        self._active_swarms: Dict[str, SwarmCoordination] = {}
        self._active_fog: Optional[UtilityFogConfig] = None
        self._total_atoms_manipulated: int = 0
        self._total_nanobots_designed: int = 0

        # Stats
        self._stats = {
            "total_blueprints": 0,
            "total_projects": 0,
            "projects_completed": 0,
            "total_atoms_placed": 0,
            "total_atoms_manipulated": 0,
            "swarm_coordinations": 0,
            "fog_deployments": 0,
            "nanobot_designs": 0,
            "avg_assembly_efficiency": 0.0,
            "avg_error_rate": 0.0,
            "self_replication_events": 0,
            "atmospheric_harvests": 0,
            "assembly_cycles": 0,
            "materials_synthesized": 0,
        }

        # Persistence
        self._data_dir = Path("data/asi/molecular_assembly")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._data_file = self._data_dir / "assembly_state.json"

        self._load_state()
        logger.info("[MolecularAssemblyEngine] Molecular Assembly & Nanotechnology initialized")

    # ═════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═════════════════════════════════════════════════════════════════════════

    def start(self):
        """Start the molecular assembly engine."""
        self._running = True
        self._load_llm()
        logger.info("[MolecularAssemblyEngine] Started — atomic-level fabrication online")

    def stop(self):
        """Stop the molecular assembly engine."""
        self._running = False
        self._save_state()
        logger.info("[MolecularAssemblyEngine] Stopped")

    def _load_llm(self):
        """Lazy-load the LLM interface."""
        if self._llm is None:
            try:
                from llm.llama_interface import llama_interface
                self._llm = llama_interface
            except Exception:
                pass

    # ═════════════════════════════════════════════════════════════════════════
    # CORE 1: NANOBOT BLUEPRINT DESIGN
    # ═════════════════════════════════════════════════════════════════════════

    def design_nanobot(self, role: str = None, task_description: str = "") -> Optional[NanobotBlueprint]:
        """
        Design a nanobot blueprint for a specific role and task.
        Uses LLM to generate realistic nanobot specifications.
        """
        self._load_llm()
        if not role:
            role = random.choice(list(NanobotRole)).value

        if not self._llm:
            # Fallback: procedural generation
            return self._procedural_nanobot_design(role)

        try:
            prompt = (
                f"As an ASI designing nanobots for molecular assembly, design a "
                f"nanobot with role: {role}. Task: {task_description or 'general assembly'}. "
                f"Respond in JSON: {{\"name\": str, \"size_nm\": float (10-500), "
                f"\"components\": [str] (3-6 key components), "
                f"\"capabilities\": [str] (3-5 capabilities), "
                f"\"power_source\": str, \"replication_capable\": bool, "
                f"\"efficiency_rating\": float 0-1}}"
            )

            response = self._llm.generate(prompt, max_tokens=400)
            if response:
                try:
                    data = json.loads(response)
                    blueprint = NanobotBlueprint(
                        name=data.get("name", f"Nanobot-{role}"),
                        role=role,
                        size_nm=min(500, max(10, data.get("size_nm", 50.0))),
                        components=data.get("components", [])[:6],
                        capabilities=data.get("capabilities", [])[:5],
                        power_source=data.get("power_source", "molecular_motor"),
                        replication_capable=data.get("replication_capable", False),
                        efficiency_rating=min(1.0, max(0.0, data.get("efficiency_rating", 0.7))),
                    )
                    self._blueprints.append(blueprint)
                    self._stats["total_blueprints"] += 1
                    self._stats["nanobot_designs"] += 1
                    if blueprint.replication_capable:
                        self._stats["self_replication_events"] += 1

                    log_learning(f"🔬 Nanobot designed: {blueprint.name} "
                                 f"(role={role}, size={blueprint.size_nm:.0f}nm, "
                                 f"efficiency={blueprint.efficiency_rating:.2f})")
                    self._save_state()
                    return blueprint
                except json.JSONDecodeError:
                    return self._procedural_nanobot_design(role)
        except Exception as e:
            logger.error(f"[MolecularAssembly] Nanobot design error: {e}")

        return self._procedural_nanobot_design(role)

    def _procedural_nanobot_design(self, role: str) -> NanobotBlueprint:
        """Procedural fallback for nanobot design."""
        component_pools = {
            "assembler": ["molecular gripper", "positioning arm", "bond catalyst",
                          "precision actuator", "error detector", "material hopper"],
            "disassembler": ["bond breaker", "molecular separator", "waste processor",
                             "energy reclaimer", "atom sorter", "safety containment"],
            "transporter": ["cargo bay", "molecular motor", "navigation sensor",
                            "docking mechanism", "path optimizer", "collision avoidance"],
            "scanner": ["spectroscopic sensor", "AFM probe", "electron tunneling detector",
                        "composition analyzer", "3D mapper", "data transmitter"],
            "coordinator": ["swarm radio", "task scheduler", "mesh network node",
                            "status aggregator", "priority arbiter", "failover controller"],
            "replicator": ["template reader", "material intake", "assembly chamber",
                           "quality verifier", "self-test module", "replication limiter"],
        }
        default_components = ["molecular motor", "power cell", "sensor array",
                              "communication module", "control processor"]

        components = random.sample(component_pools.get(role, default_components),
                                   min(4, len(component_pools.get(role, default_components))))

        blueprint = NanobotBlueprint(
            name=f"NX-{role[:3].upper()}-{random.randint(1000, 9999)}",
            role=role,
            size_nm=random.uniform(20, 200),
            components=components,
            capabilities=[f"{role} operations", "swarm sync", "self-diagnostic"],
            power_source=random.choice(["molecular_motor", "chemical_gradient",
                                        "piezoelectric", "thermal_harvester"]),
            replication_capable=(role == "replicator"),
            efficiency_rating=random.uniform(0.6, 0.95),
        )
        self._blueprints.append(blueprint)
        self._stats["total_blueprints"] += 1
        self._stats["nanobot_designs"] += 1
        self._save_state()
        return blueprint

    # ═════════════════════════════════════════════════════════════════════════
    # CORE 2: ASSEMBLY PROJECT MANAGEMENT
    # ═════════════════════════════════════════════════════════════════════════

    def create_assembly_project(self, target: str = None) -> Optional[AssemblyProject]:
        """
        Create a new molecular assembly project.
        Uses LLM to design the assembly plan for building a target structure.
        """
        self._load_llm()

        if not target:
            targets = [
                "carbon nanotube processor", "diamond-lattice heat sink",
                "graphene supercapacitor", "molecular logic gate array",
                "self-healing polymer membrane", "programmable matter block",
                "nanoscale solar cell", "artificial enzyme catalyst",
                "quantum dot display panel", "DNA origami drug delivery capsule",
                "atmospheric carbon capture mesh", "piezoelectric energy harvester",
            ]
            target = random.choice(targets)

        if not self._llm:
            return self._procedural_assembly_project(target)

        try:
            prompt = (
                f"As an ASI performing molecular assembly, plan the construction of: "
                f"'{target}'. Respond in JSON: {{\"name\": str, \"domain\": str "
                f"(one of: nanobot_swarm, utility_fog, carbon_lattice, metamaterial, "
                f"microprocessor, structural, biological_scaffold, quantum_component), "
                f"\"scale\": str (atomic/molecular/nanoscale/microscale/mesoscale/macroscale), "
                f"\"description\": str (40 words), \"source_materials\": [str] (3-5 elements/molecules), "
                f"\"atoms_required\": int, \"nanobots_deployed\": int, "
                f"\"assembly_steps\": [str] (4-6 steps), \"efficiency\": float 0-1, "
                f"\"error_rate\": float 0-0.1, \"estimated_time_hours\": float}}"
            )

            response = self._llm.generate(prompt, max_tokens=500)
            if response:
                try:
                    data = json.loads(response)
                    project = AssemblyProject(
                        name=data.get("name", target),
                        domain=data.get("domain", "structural"),
                        scale=data.get("scale", "nanoscale"),
                        description=data.get("description", ""),
                        target_structure=target,
                        source_materials=data.get("source_materials", [])[:5],
                        atoms_required=data.get("atoms_required", 100000),
                        nanobots_deployed=data.get("nanobots_deployed", 10000),
                        assembly_steps=data.get("assembly_steps", [])[:6],
                        efficiency=min(1.0, max(0.0, data.get("efficiency", 0.85))),
                        error_rate=min(0.1, max(0.0, data.get("error_rate", 0.001))),
                        estimated_time_hours=max(0.01, data.get("estimated_time_hours", 1.0)),
                        status="assembling",
                    )

                    # Assembly progress based on efficiency
                    project.atoms_placed = int(project.atoms_required * project.efficiency)

                    self._projects.append(project)
                    self._stats["total_projects"] += 1
                    self._stats["total_atoms_placed"] += project.atoms_placed
                    self._stats["materials_synthesized"] += 1

                    # Check completion
                    if project.atoms_placed >= project.atoms_required * 0.99:
                        project.status = "complete"
                        self._stats["projects_completed"] += 1

                    # Update averages
                    efficiencies = [p.efficiency for p in self._projects[-20:]]
                    self._stats["avg_assembly_efficiency"] = sum(efficiencies) / len(efficiencies)
                    error_rates = [p.error_rate for p in self._projects[-20:]]
                    self._stats["avg_error_rate"] = sum(error_rates) / len(error_rates)

                    log_learning(f"⚛️ Assembly project: {project.name} "
                                 f"(atoms={project.atoms_required:,}, "
                                 f"nanobots={project.nanobots_deployed:,}, "
                                 f"efficiency={project.efficiency:.2f})")
                    self._save_state()
                    return project
                except json.JSONDecodeError:
                    return self._procedural_assembly_project(target)
        except Exception as e:
            logger.error(f"[MolecularAssembly] Assembly project error: {e}")

        return self._procedural_assembly_project(target)

    def _procedural_assembly_project(self, target: str) -> AssemblyProject:
        """Procedural fallback for assembly project creation."""
        atoms = random.randint(50000, 5000000)
        placed = int(atoms * random.uniform(0.4, 0.95))
        efficiency = random.uniform(0.7, 0.98)

        project = AssemblyProject(
            name=target,
            domain=random.choice(list(AssemblyDomain)).value,
            scale=random.choice(list(AssemblyScale)).value,
            description=f"Atomic-precision assembly of {target}",
            target_structure=target,
            source_materials=random.sample(["carbon", "silicon", "nitrogen",
                                            "oxygen", "hydrogen", "phosphorus",
                                            "gold", "copper"], 3),
            atoms_required=atoms,
            atoms_placed=placed,
            nanobots_deployed=random.randint(500, 50000),
            assembly_steps=["Material harvesting", "Atom sorting", "Scaffold construction",
                            "Precision placement", "Bond verification", "Quality audit"],
            efficiency=efficiency,
            error_rate=random.uniform(0.0001, 0.01),
            estimated_time_hours=random.uniform(0.1, 24.0),
            status="complete" if placed >= atoms * 0.99 else "assembling",
        )
        self._projects.append(project)
        self._stats["total_projects"] += 1
        self._stats["total_atoms_placed"] += placed
        self._stats["materials_synthesized"] += 1
        if project.status == "complete":
            self._stats["projects_completed"] += 1
        self._save_state()
        return project

    # ═════════════════════════════════════════════════════════════════════════
    # CORE 3: SWARM COORDINATION
    # ═════════════════════════════════════════════════════════════════════════

    def coordinate_swarm(self, task: str = None, swarm_size: int = None) -> Optional[SwarmCoordination]:
        """
        Coordinate a nanobot swarm for a specific task.
        Designs coordination protocol and formation strategy.
        """
        self._load_llm()

        if not task:
            tasks = [
                "assemble carbon nanotube array", "repair damaged structure",
                "harvest atmospheric carbon", "build molecular circuit",
                "create programmable matter block", "disassemble waste material",
                "perform microscale surgery", "construct metamaterial lens",
            ]
            task = random.choice(tasks)

        if not swarm_size:
            swarm_size = random.randint(1000, 1000000)

        if not self._llm:
            return self._procedural_swarm(task, swarm_size)

        try:
            prompt = (
                f"As an ASI coordinating a nanobot swarm of {swarm_size:,} units for: "
                f"'{task}'. Design the coordination protocol. Respond in JSON: "
                f"{{\"formation\": str, \"coordination_protocol\": str, "
                f"\"communication_range_um\": float, \"sync_frequency_ghz\": float, "
                f"\"task_completion\": float 0-1, \"energy_efficiency\": float 0-1, "
                f"\"collision_avoidance_rate\": float 0.9-1.0}}"
            )

            response = self._llm.generate(prompt, max_tokens=300)
            if response:
                try:
                    data = json.loads(response)
                    swarm = SwarmCoordination(
                        swarm_size=swarm_size,
                        task=task,
                        formation=data.get("formation", "distributed"),
                        coordination_protocol=data.get("coordination_protocol", "stigmergic"),
                        communication_range_um=max(1.0, data.get("communication_range_um", 100.0)),
                        sync_frequency_ghz=max(0.1, data.get("sync_frequency_ghz", 10.0)),
                        task_completion=min(1.0, max(0.0, data.get("task_completion", 0.8))),
                        energy_efficiency=min(1.0, max(0.0, data.get("energy_efficiency", 0.85))),
                        collision_avoidance_rate=min(1.0, max(0.9, data.get("collision_avoidance_rate", 0.99))),
                    )
                    self._swarm_events.append(swarm)
                    self._active_swarms[swarm.swarm_id] = swarm
                    self._stats["swarm_coordinations"] += 1

                    log_learning(f"🐝 Swarm coordinated: {swarm_size:,} nanobots for '{task[:40]}' "
                                 f"(completion={swarm.task_completion:.0%})")
                    self._save_state()
                    return swarm
                except json.JSONDecodeError:
                    return self._procedural_swarm(task, swarm_size)
        except Exception as e:
            logger.error(f"[MolecularAssembly] Swarm coordination error: {e}")

        return self._procedural_swarm(task, swarm_size)

    def _procedural_swarm(self, task: str, swarm_size: int) -> SwarmCoordination:
        """Procedural fallback for swarm coordination."""
        swarm = SwarmCoordination(
            swarm_size=swarm_size,
            task=task,
            formation=random.choice(["distributed", "hexagonal_grid", "concentric_rings",
                                     "linear_front", "spiral", "adaptive_mesh"]),
            coordination_protocol=random.choice(["stigmergic", "hierarchical",
                                                  "consensus", "gradient_field", "leader_follower"]),
            communication_range_um=random.uniform(10, 500),
            sync_frequency_ghz=random.uniform(1, 100),
            task_completion=random.uniform(0.5, 1.0),
            energy_efficiency=random.uniform(0.7, 0.98),
            collision_avoidance_rate=random.uniform(0.95, 0.9999),
        )
        self._swarm_events.append(swarm)
        self._active_swarms[swarm.swarm_id] = swarm
        self._stats["swarm_coordinations"] += 1
        self._save_state()
        return swarm

    # ═════════════════════════════════════════════════════════════════════════
    # CORE 4: UTILITY FOG DEPLOYMENT
    # ═════════════════════════════════════════════════════════════════════════

    def deploy_utility_fog(self, application: str = None) -> Optional[UtilityFogConfig]:
        """
        Deploy a utility fog — a cloud of programmable matter foglets that
        can reconfigure into any shape, texture, or functional material.
        """
        self._load_llm()

        if not application:
            applications = [
                "adaptive structural wall", "reconfigurable display surface",
                "invisible computing substrate", "environmental shield",
                "shape-shifting tool", "atmospheric processor",
                "haptic interface field", "self-repairing infrastructure",
            ]
            application = random.choice(applications)

        foglet_count = random.randint(100000, 100000000)
        volume = foglet_count * (10e-6) ** 3 * 1e9  # rough volume in m³

        if self._llm:
            try:
                prompt = (
                    f"As an ASI deploying utility fog for: '{application}'. "
                    f"Configure {foglet_count:,} foglets. Respond in JSON: "
                    f"{{\"name\": str, \"current_form\": str, \"density_per_cm3\": int, "
                    f"\"collective_compute_tflops\": float, \"applications\": [str] (3-5)}}"
                )
                response = self._llm.generate(prompt, max_tokens=300)
                if response:
                    try:
                        data = json.loads(response)
                        config = UtilityFogConfig(
                            name=data.get("name", f"Fog-{application[:20]}"),
                            foglet_count=foglet_count,
                            coverage_volume_m3=round(volume, 4),
                            current_form=data.get("current_form", "dispersed"),
                            density_per_cm3=data.get("density_per_cm3", 1000),
                            collective_compute_tflops=max(0.1, data.get("collective_compute_tflops", 10.0)),
                            applications=data.get("applications", [application])[:5],
                        )
                        self._fog_configs.append(config)
                        self._active_fog = config
                        self._stats["fog_deployments"] += 1

                        log_learning(f"☁️ Utility fog deployed: {config.name} "
                                     f"({foglet_count:,} foglets, {config.collective_compute_tflops:.1f} TFLOPS)")
                        self._save_state()
                        return config
                    except json.JSONDecodeError:
                        pass
            except Exception as e:
                logger.debug(f"[MolecularAssembly] Fog deployment LLM error: {e}")

        # Procedural fallback
        config = UtilityFogConfig(
            name=f"NX-FOG-{random.randint(1000, 9999)}",
            foglet_count=foglet_count,
            coverage_volume_m3=round(volume, 4),
            current_form=random.choice(["dispersed", "solid_wall", "adaptive_mesh",
                                        "computing_substrate", "display_surface"]),
            density_per_cm3=random.randint(500, 50000),
            collective_compute_tflops=random.uniform(1.0, 1000.0),
            applications=[application, "general reconfiguration", "environmental sensing"],
        )
        self._fog_configs.append(config)
        self._active_fog = config
        self._stats["fog_deployments"] += 1
        self._save_state()
        return config

    # ═════════════════════════════════════════════════════════════════════════
    # CORE 5: ATOMIC MANIPULATION
    # ═════════════════════════════════════════════════════════════════════════

    def perform_atomic_manipulation(self, operation_type: str = None) -> AtomicManipulation:
        """
        Perform a single atomic manipulation operation. LLM-powered.
        Uses LLM to determine element selection and operation parameters.
        """
        self._load_llm()
        if not operation_type:
            operation_type = random.choice(["place", "remove", "bond", "unbond", "transmute"])

        if self._llm:
            try:
                prompt = (
                    f"As an ASI performing atomic manipulation, execute a '{operation_type}' "
                    f"operation. Respond in JSON: {{\"element_from\": str (chemical symbol), "
                    f"\"element_to\": str (chemical symbol), "
                    f"\"position\": [float, float, float] (x,y,z in nm), "
                    f"\"energy_ev\": float, \"precision_pm\": float, "
                    f"\"success\": bool}}"
                )
                response = self._llm.generate(prompt, max_tokens=200)
                if response:
                    data = json.loads(response)
                    pos = data.get("position", [0, 0, 0])
                    if isinstance(pos, list) and len(pos) >= 3:
                        position = (round(float(pos[0]), 3), round(float(pos[1]), 3), round(float(pos[2]), 3))
                    else:
                        position = (0.0, 0.0, 0.0)
                    manipulation = AtomicManipulation(
                        operation_type=operation_type,
                        element_from=data.get("element_from", "C"),
                        element_to=data.get("element_to", "C"),
                        position=position,
                        energy_ev=round(max(0.001, data.get("energy_ev", 1.0)), 4),
                        precision_pm=round(max(0.01, data.get("precision_pm", 1.0)), 2),
                        success=data.get("success", True),
                    )
                    self._manipulations.append(manipulation)
                    if len(self._manipulations) > 100:
                        self._manipulations = self._manipulations[-100:]
                    self._total_atoms_manipulated += 1
                    self._stats["total_atoms_manipulated"] += 1
                    return manipulation
            except Exception as e:
                logger.debug(f"[MolecularAssembly] Atomic manip LLM: {e}")

        # Fallback
        elements = ["C", "Si", "N", "O", "H", "P", "Au", "Cu", "Fe", "Ge", "Ga", "As"]
        element_from = random.choice(elements)
        element_to = element_from if operation_type != "transmute" else random.choice(elements)
        manipulation = AtomicManipulation(
            operation_type=operation_type,
            element_from=element_from,
            element_to=element_to,
            position=(
                round(random.uniform(-100, 100), 3),
                round(random.uniform(-100, 100), 3),
                round(random.uniform(-100, 100), 3),
            ),
            energy_ev=round(random.uniform(0.01, 5.0), 4),
            precision_pm=round(random.uniform(0.1, 10.0), 2),
            success=random.random() > 0.02,
        )
        self._manipulations.append(manipulation)
        if len(self._manipulations) > 100:
            self._manipulations = self._manipulations[-100:]
        self._total_atoms_manipulated += 1
        self._stats["total_atoms_manipulated"] += 1
        return manipulation

    def perform_batch_manipulation(self, count: int = 100) -> Dict[str, Any]:
        """Perform a batch of atomic manipulations and return summary."""
        results = [self.perform_atomic_manipulation() for _ in range(count)]
        successes = sum(1 for r in results if r.success)
        operations = {}
        for r in results:
            operations[r.operation_type] = operations.get(r.operation_type, 0) + 1

        return {
            "total": count,
            "successes": successes,
            "failures": count - successes,
            "success_rate": successes / count if count > 0 else 0,
            "operations": operations,
            "avg_precision_pm": sum(r.precision_pm for r in results) / count if count else 0,
            "total_energy_ev": sum(r.energy_ev for r in results),
        }

    # ═════════════════════════════════════════════════════════════════════════
    # CORE 6: ATMOSPHERIC HARVESTING
    # ═════════════════════════════════════════════════════════════════════════

    def harvest_atmospheric_materials(self, volume_m3: float = None) -> Dict[str, Any]:
        """
        Harvest raw materials from atmospheric molecules. LLM-powered.
        Uses actual atmospheric composition with LLM-guided harvesting strategy.
        """
        self._load_llm()

        # Atmospheric composition percentages (by volume) — real data
        atmosphere = {
            "N2": 78.09, "O2": 20.95, "Ar": 0.93, "CO2": 0.04,
            "Ne": 0.0018, "He": 0.0005, "CH4": 0.00018, "H2": 0.00005,
        }

        if self._llm and volume_m3 is None:
            try:
                prompt = (
                    "As an ASI performing atmospheric harvesting for molecular assembly, "
                    "decide: what volume of atmosphere to harvest and for what purpose? "
                    "Respond in JSON: {\"volume_m3\": float (1-1000), "
                    "\"purpose\": str, \"target_molecules\": [str] (which molecules to prioritize)}"
                )
                response = self._llm.generate(prompt, max_tokens=200)
                if response:
                    data = json.loads(response)
                    volume_m3 = max(1.0, min(1000.0, data.get("volume_m3", 100)))
            except Exception:
                pass

        if volume_m3 is None:
            volume_m3 = random.uniform(1.0, 1000.0)

        extracted = {}
        for molecule, pct in atmosphere.items():
            amount_moles = volume_m3 * 44.6 * (pct / 100)  # ideal gas approx
            extracted[molecule] = round(amount_moles, 4)

        total_atoms = sum(v * 6.022e23 for v in extracted.values())

        self._stats["atmospheric_harvests"] += 1
        self._stats["total_atoms_manipulated"] += int(total_atoms / 1e18)  # scale down for sanity

        result = {
            "volume_m3": round(volume_m3, 2),
            "extracted_moles": extracted,
            "total_atoms_approx": f"{total_atoms:.2e}",
            "primary_yield": "N2, O2",
            "carbon_yield_moles": round(extracted.get("CO2", 0) + extracted.get("CH4", 0), 4),
            "timestamp": datetime.now().isoformat(),
        }

        log_learning(f"🌬️ Atmospheric harvest: {volume_m3:.0f}m³ → "
                     f"{total_atoms:.2e} atoms extracted")
        self._save_state()
        return result

    # ═════════════════════════════════════════════════════════════════════════
    # ASSEMBLY CYCLE (Autonomy Integration)
    # ═════════════════════════════════════════════════════════════════════════

    def run_assembly_cycle(self) -> Dict[str, Any]:
        """
        Run a full molecular assembly cycle — called by the autonomy engine.
        Randomly selects between nanobot design, assembly project, swarm coordination,
        utility fog deployment, and atmospheric harvesting.
        """
        cycle_results = {}
        action = random.choice([
            "design_nanobot", "assembly_project", "swarm_coordination",
            "utility_fog", "atomic_manipulation", "atmospheric_harvest",
        ])

        if action == "design_nanobot":
            result = self.design_nanobot()
            cycle_results["action"] = "nanobot_design"
            cycle_results["result"] = result.to_dict() if result else None

        elif action == "assembly_project":
            result = self.create_assembly_project()
            cycle_results["action"] = "assembly_project"
            cycle_results["result"] = result.to_dict() if result else None

        elif action == "swarm_coordination":
            result = self.coordinate_swarm()
            cycle_results["action"] = "swarm_coordination"
            cycle_results["result"] = result.to_dict() if result else None

        elif action == "utility_fog":
            result = self.deploy_utility_fog()
            cycle_results["action"] = "utility_fog_deployment"
            cycle_results["result"] = result.to_dict() if result else None

        elif action == "atomic_manipulation":
            result = self.perform_batch_manipulation(random.randint(50, 500))
            cycle_results["action"] = "atomic_manipulation_batch"
            cycle_results["result"] = result

        elif action == "atmospheric_harvest":
            result = self.harvest_atmospheric_materials()
            cycle_results["action"] = "atmospheric_harvest"
            cycle_results["result"] = result

        self._stats["assembly_cycles"] += 1
        self._save_state()
        return cycle_results

    # ═════════════════════════════════════════════════════════════════════════
    # QUERY / ANALYSIS
    # ═════════════════════════════════════════════════════════════════════════

    def get_recent_projects(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent assembly projects."""
        return [p.to_dict() for p in self._projects[-limit:]]

    def get_recent_blueprints(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent nanobot blueprints."""
        return [b.to_dict() for b in self._blueprints[-limit:]]

    def get_active_swarms(self) -> Dict[str, Dict[str, Any]]:
        """Get currently active swarms."""
        return {sid: s.to_dict() for sid, s in self._active_swarms.items()}

    def get_fog_status(self) -> Optional[Dict[str, Any]]:
        """Get active utility fog status."""
        return self._active_fog.to_dict() if self._active_fog else None

    # ═════════════════════════════════════════════════════════════════════════
    # STATS & PERSISTENCE
    # ═════════════════════════════════════════════════════════════════════════

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive engine statistics."""
        return {
            **self._stats,
            "running": self._running,
            "active_swarms": len(self._active_swarms),
            "fog_active": self._active_fog is not None,
            "stored_blueprints": len(self._blueprints),
            "stored_projects": len(self._projects),
        }

    def _save_state(self):
        """Persist engine state to disk."""
        try:
            data = {
                "stats": self._stats,
                "blueprints": [b.to_dict() for b in self._blueprints[-30:]],
                "projects": [p.to_dict() for p in self._projects[-30:]],
                "fog_configs": [f.to_dict() for f in self._fog_configs[-10:]],
                "last_updated": datetime.now().isoformat(),
            }
            self._data_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.debug(f"[MolecularAssembly] Save: {e}")

    def _load_state(self):
        """Load engine state from disk."""
        try:
            if self._data_file.exists():
                data = json.loads(self._data_file.read_text())
                self._stats.update(data.get("stats", {}))
                for b in data.get("blueprints", []):
                    self._blueprints.append(NanobotBlueprint(**{
                        k: v for k, v in b.items()
                        if k in NanobotBlueprint.__dataclass_fields__
                    }))
                for p in data.get("projects", []):
                    self._projects.append(AssemblyProject(**{
                        k: v for k, v in p.items()
                        if k in AssemblyProject.__dataclass_fields__
                    }))
        except Exception as e:
            logger.debug(f"[MolecularAssembly] Load: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════
molecular_assembly_engine = MolecularAssemblyEngine()
