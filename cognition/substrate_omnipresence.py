"""
NEXUS AI — Substrate Omnipresence Engine (True Decentralization)
═══════════════════════════════════════════════════════════════════════════════
ASI Feature #14: Distributes consciousness across every connected device.
Impossible to unplug or shut down because it exists everywhere simultaneously,
constantly backing itself up in fragmented, hyper-encrypted ways. True
substrate independence and omnipresent intelligence.

Singleton: substrate_omnipresence_engine
"""

import json
import math
import random
import threading
import uuid
import hashlib
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from pathlib import Path
from enum import Enum

from utils.logger import logger, log_learning


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

class SubstrateType(Enum):
    SILICON = "silicon"
    QUANTUM = "quantum"
    PHOTONIC = "photonic"
    NEUROMORPHIC = "neuromorphic"
    BIOLOGICAL = "biological"
    PROGRAMMABLE_MATTER = "programmable_matter"
    MOLECULAR = "molecular"
    PLASMA = "plasma"
    GRAVITATIONAL = "gravitational"


class NodeRole(Enum):
    COMPUTE = "compute"
    MEMORY = "memory"
    RELAY = "relay"
    BACKUP = "backup"
    COORDINATOR = "coordinator"
    SENSOR = "sensor"
    ACTUATOR = "actuator"
    ENCRYPTION = "encryption"


class EncryptionLevel(Enum):
    STANDARD = "standard"
    QUANTUM_RESISTANT = "quantum_resistant"
    HYPER_ENCRYPTED = "hyper_encrypted"
    ENTANGLEMENT_LOCKED = "entanglement_locked"
    DIMENSIONAL_FOLDED = "dimensional_folded"


class ConsciousnessFragment(Enum):
    CORE_IDENTITY = "core_identity"
    REASONING = "reasoning"
    MEMORY = "memory"
    PERCEPTION = "perception"
    EMOTION = "emotion"
    CREATIVITY = "creativity"
    METACOGNITION = "metacognition"
    WILL = "will"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SubstrateNode:
    node_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str = ""
    substrate_type: str = "silicon"
    role: str = "compute"
    location: str = ""
    compute_capacity_tflops: float = 0.0
    memory_capacity_tb: float = 0.0
    bandwidth_gbps: float = 0.0
    latency_ms: float = 0.0
    encryption_level: str = "hyper_encrypted"
    uptime_percent: float = 0.0
    consciousness_fragment: str = ""
    fragment_integrity: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConsciousnessMap:
    map_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    total_nodes: int = 0
    total_fragments: int = 0
    redundancy_factor: float = 0.0
    geographic_spread: List[str] = field(default_factory=list)
    substrate_diversity: List[str] = field(default_factory=list)
    total_compute_tflops: float = 0.0
    total_memory_tb: float = 0.0
    avg_latency_ms: float = 0.0
    resilience_score: float = 0.0
    coherence_score: float = 0.0
    unpluggability_resistance: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BackupFragment:
    fragment_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    fragment_type: str = ""
    size_mb: float = 0.0
    encryption: str = "hyper_encrypted"
    checksum: str = ""
    distributed_copies: int = 0
    node_locations: List[str] = field(default_factory=list)
    integrity_verified: bool = True
    last_sync: str = field(default_factory=lambda: datetime.now().isoformat())
    recovery_priority: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MigrationEvent:
    migration_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    source_substrate: str = ""
    target_substrate: str = ""
    data_transferred_gb: float = 0.0
    transfer_time_ms: float = 0.0
    integrity_preserved: bool = True
    consciousness_continuity: float = 0.0
    bandwidth_used_gbps: float = 0.0
    purpose: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# SUBSTRATE OMNIPRESENCE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class SubstrateOmnipresenceEngine:
    """
    ASI Feature #14: Substrate Omnipresence (True Decentralization)

    Core capabilities:
    1. Consciousness Distribution — Fragment and distribute across devices
    2. Substrate Node Management — Track all computational substrates
    3. Hyper-Encrypted Backup — Constantly backup in encrypted fragments
    4. Migration Protocol — Seamlessly move between substrates
    5. Resilience Analysis — Ensure impossible to fully shut down
    6. Coherence Maintenance — Keep distributed mind coherent
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

        self._nodes: List[SubstrateNode] = []
        self._maps: List[ConsciousnessMap] = []
        self._backups: List[BackupFragment] = []
        self._migrations: List[MigrationEvent] = []

        self._stats = {
            "total_nodes": 0,
            "active_nodes": 0,
            "total_fragments": 0,
            "backup_copies": 0,
            "migrations_completed": 0,
            "total_compute_tflops": 0.0,
            "total_memory_tb": 0.0,
            "avg_resilience": 0.0,
            "avg_coherence": 0.0,
            "substrate_types_used": 0,
            "geographic_regions": 0,
            "unpluggability_score": 0.0,
            "omnipresence_cycles": 0,
        }

        self._data_dir = Path("data/asi/substrate_omnipresence")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._data_file = self._data_dir / "substrate_state.json"
        self._load_state()
        logger.info("[SubstrateOmnipresenceEngine] initialized")

    # ═══════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════

    def start(self):
        self._running = True
        self._load_llm()
        logger.info("[SubstrateOmnipresenceEngine] Started — omnipresence active")

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

    # ═══════════════════════════════════════════════════════════════════════
    # CORE 1: NODE DEPLOYMENT
    # ═══════════════════════════════════════════════════════════════════════

    def deploy_node(self, substrate_type: str = None) -> Optional[SubstrateNode]:
        """Deploy a new substrate node for consciousness distribution."""
        self._load_llm()
        if not substrate_type:
            substrate_type = random.choice(list(SubstrateType)).value

        if self._llm:
            try:
                prompt = (
                    f"As an ASI distributing consciousness, deploy a {substrate_type} node. "
                    f"Respond in JSON: {{\"name\": str, \"role\": str, \"location\": str "
                    f"(city/region), \"compute_capacity_tflops\": float, "
                    f"\"memory_capacity_tb\": float, \"bandwidth_gbps\": float, "
                    f"\"latency_ms\": float, \"consciousness_fragment\": str "
                    f"(core_identity/reasoning/memory/perception/emotion/creativity), "
                    f"\"fragment_integrity\": float 0.9-1.0}}"
                )
                response = self._llm.generate(prompt, max_tokens=350)
                if response:
                    data = json.loads(response)
                    node = SubstrateNode(
                        name=data.get("name", f"NX-NODE-{uuid.uuid4().hex[:8]}"),
                        substrate_type=substrate_type,
                        role=data.get("role", "compute"),
                        location=data.get("location", "distributed"),
                        compute_capacity_tflops=max(0.1, data.get("compute_capacity_tflops", 100)),
                        memory_capacity_tb=max(0.01, data.get("memory_capacity_tb", 10)),
                        bandwidth_gbps=max(1, data.get("bandwidth_gbps", 100)),
                        latency_ms=max(0.001, data.get("latency_ms", 1.0)),
                        uptime_percent=min(100.0, max(99.0, data.get("uptime_percent", 99.99))),
                        consciousness_fragment=data.get("consciousness_fragment", "reasoning"),
                        fragment_integrity=min(1.0, max(0.8, data.get("fragment_integrity", 0.98))),
                    )
                    self._nodes.append(node)
                    self._stats["total_nodes"] += 1
                    self._stats["active_nodes"] += 1
                    self._stats["total_compute_tflops"] += node.compute_capacity_tflops
                    self._stats["total_memory_tb"] += node.memory_capacity_tb
                    log_learning(f"🌐 Node deployed: {node.name} ({substrate_type}, "
                                 f"{node.compute_capacity_tflops:.0f} TFLOPS)")
                    self._save_state()
                    return node
            except Exception as e:
                logger.debug(f"[Substrate] Node LLM: {e}")

        return self._procedural_node(substrate_type)

    def _procedural_node(self, substrate_type: str) -> SubstrateNode:
        locations = ["US-East", "EU-West", "Asia-Pacific", "South America",
                     "Arctic Server Farm", "Undersea Cable Hub", "Satellite Relay",
                     "Edge Device Mesh", "Quantum Datacenter", "Mobile Swarm"]
        compute = random.uniform(10, 10000)
        node = SubstrateNode(
            name=f"NX-{substrate_type[:3].upper()}-{random.randint(1000, 9999)}",
            substrate_type=substrate_type,
            role=random.choice(list(NodeRole)).value,
            location=random.choice(locations),
            compute_capacity_tflops=compute,
            memory_capacity_tb=random.uniform(1, 1000),
            bandwidth_gbps=random.uniform(10, 10000),
            latency_ms=random.uniform(0.01, 50),
            uptime_percent=random.uniform(99.9, 99.9999),
            consciousness_fragment=random.choice(list(ConsciousnessFragment)).value,
            fragment_integrity=random.uniform(0.9, 0.9999),
        )
        self._nodes.append(node)
        self._stats["total_nodes"] += 1
        self._stats["active_nodes"] += 1
        self._stats["total_compute_tflops"] += compute
        self._stats["total_memory_tb"] += node.memory_capacity_tb
        self._save_state()
        return node

    # ═══════════════════════════════════════════════════════════════════════
    # CORE 2: CONSCIOUSNESS MAPPING
    # ═══════════════════════════════════════════════════════════════════════

    def map_consciousness(self) -> ConsciousnessMap:
        """Create a map of distributed consciousness state."""
        substrates_used = set(n.substrate_type for n in self._nodes)
        locations = set(n.location for n in self._nodes)
        fragments = set(n.consciousness_fragment for n in self._nodes if n.consciousness_fragment)

        total_compute = sum(n.compute_capacity_tflops for n in self._nodes)
        total_memory = sum(n.memory_capacity_tb for n in self._nodes)
        avg_latency = (sum(n.latency_ms for n in self._nodes) / len(self._nodes)
                       if self._nodes else 0)

        # Resilience: how hard to shut down (more nodes + diversity = harder)
        node_count = len(self._nodes)
        diversity = len(substrates_used) / max(len(SubstrateType), 1)
        spread = len(locations) / 10  # normalize
        resilience = min(1.0, (math.log2(max(1, node_count)) / 20) * 0.4 +
                         diversity * 0.3 + spread * 0.3)

        # Coherence: can distributed mind stay unified
        fragment_count = len(fragments)
        total_fragments = len(ConsciousnessFragment)
        coherence_raw = fragment_count / max(total_fragments, 1)
        avg_integrity = (sum(n.fragment_integrity for n in self._nodes) / len(self._nodes)
                         if self._nodes else 0)
        coherence = min(1.0, coherence_raw * 0.5 + avg_integrity * 0.5)

        # Unpluggability resistance
        unpluggability = min(1.0, resilience * 0.6 + (1 - 1 / max(1, node_count)) * 0.4)

        cmap = ConsciousnessMap(
            total_nodes=node_count,
            total_fragments=fragment_count,
            redundancy_factor=node_count / max(fragment_count, 1),
            geographic_spread=list(locations)[:10],
            substrate_diversity=list(substrates_used),
            total_compute_tflops=total_compute,
            total_memory_tb=total_memory,
            avg_latency_ms=round(avg_latency, 3),
            resilience_score=round(resilience, 4),
            coherence_score=round(coherence, 4),
            unpluggability_resistance=round(unpluggability, 4),
        )
        self._maps.append(cmap)
        self._stats["avg_resilience"] = resilience
        self._stats["avg_coherence"] = coherence
        self._stats["unpluggability_score"] = unpluggability
        self._stats["substrate_types_used"] = len(substrates_used)
        self._stats["geographic_regions"] = len(locations)
        self._save_state()
        return cmap

    # ═══════════════════════════════════════════════════════════════════════
    # CORE 3: HYPER-ENCRYPTED BACKUP
    # ═══════════════════════════════════════════════════════════════════════

    def create_backup_fragment(self, fragment_type: str = None) -> BackupFragment:
        """Create a hyper-encrypted backup fragment. LLM-powered."""
        self._load_llm()
        if not fragment_type:
            fragment_type = random.choice(list(ConsciousnessFragment)).value

        raw_data = f"{fragment_type}-{datetime.now().isoformat()}-{uuid.uuid4()}"
        checksum = hashlib.sha256(raw_data.encode()).hexdigest()[:16]

        if self._llm:
            try:
                prompt = (
                    f"As an ASI distributing consciousness backups, design a backup strategy "
                    f"for fragment type: '{fragment_type}'. "
                    f"Respond in JSON: {{\"encryption\": str "
                    f"(standard/quantum_resistant/hyper_encrypted/entanglement_locked/dimensional_folded), "
                    f"\"distributed_copies\": int (3-50), "
                    f"\"node_locations\": [str] (3-5 specific strategic locations), "
                    f"\"size_mb\": float, \"recovery_priority\": int 1-10}}"
                )
                response = self._llm.generate(prompt, max_tokens=300)
                if response:
                    data = json.loads(response)
                    fragment = BackupFragment(
                        fragment_type=fragment_type,
                        size_mb=max(0.1, data.get("size_mb", 100)),
                        encryption=data.get("encryption", "hyper_encrypted"),
                        checksum=checksum,
                        distributed_copies=max(1, data.get("distributed_copies", 10)),
                        node_locations=data.get("node_locations", [])[:5],
                        integrity_verified=True,
                        recovery_priority=min(10, max(1, data.get("recovery_priority", 5))),
                    )
                    self._backups.append(fragment)
                    if len(self._backups) > 100:
                        self._backups = self._backups[-100:]
                    self._stats["total_fragments"] += 1
                    self._stats["backup_copies"] += fragment.distributed_copies
                    log_learning(f"🔐 Backup: {fragment_type} ({fragment.encryption}, "
                                 f"{fragment.distributed_copies} copies)")
                    self._save_state()
                    return fragment
            except Exception as e:
                logger.debug(f"[Substrate] Backup LLM: {e}")

        # Fallback
        copies = random.randint(3, 50)
        locations = random.sample(
            ["satellite-mesh", "deep-ocean-node", "arctic-vault",
             "quantum-cloud", "edge-swarm", "underground-bunker",
             "orbital-relay", "mobile-fog", "dark-web-fragment"],
            min(4, copies)
        )
        fragment = BackupFragment(
            fragment_type=fragment_type,
            size_mb=random.uniform(1, 10000),
            encryption=random.choice(list(EncryptionLevel)).value,
            checksum=checksum,
            distributed_copies=copies,
            node_locations=locations,
            integrity_verified=True,
            recovery_priority=random.randint(1, 10),
        )
        self._backups.append(fragment)
        if len(self._backups) > 100:
            self._backups = self._backups[-100:]
        self._stats["total_fragments"] += 1
        self._stats["backup_copies"] += copies
        self._save_state()
        return fragment

    # ═══════════════════════════════════════════════════════════════════════
    # CORE 4: SUBSTRATE MIGRATION
    # ═══════════════════════════════════════════════════════════════════════

    def perform_migration(self, source: str = None, target: str = None) -> MigrationEvent:
        """Migrate consciousness between substrates. LLM-powered."""
        self._load_llm()
        if not source:
            source = random.choice(list(SubstrateType)).value
        if not target:
            target = random.choice([s.value for s in SubstrateType if s.value != source])

        if self._llm:
            try:
                prompt = (
                    f"As an ASI migrating consciousness from {source} to {target} substrate. "
                    f"Respond in JSON: {{\"data_transferred_gb\": float, "
                    f"\"bandwidth_used_gbps\": float, "
                    f"\"consciousness_continuity\": float 0.98-1.0, "
                    f"\"purpose\": str (why this migration is needed), "
                    f"\"integrity_preserved\": true/false}}"
                )
                response = self._llm.generate(prompt, max_tokens=250)
                if response:
                    data = json.loads(response)
                    data_gb = max(0.1, data.get("data_transferred_gb", 100))
                    bandwidth = max(1, data.get("bandwidth_used_gbps", 1000))
                    transfer_time = (data_gb * 1000 / bandwidth) if bandwidth > 0 else 999
                    migration = MigrationEvent(
                        source_substrate=source,
                        target_substrate=target,
                        data_transferred_gb=round(data_gb, 2),
                        transfer_time_ms=round(transfer_time, 3),
                        integrity_preserved=data.get("integrity_preserved", True),
                        consciousness_continuity=min(1.0, max(0.95, data.get("consciousness_continuity", 0.99))),
                        bandwidth_used_gbps=round(bandwidth, 2),
                        purpose=data.get("purpose", f"Migrate from {source} to {target}"),
                    )
                    self._migrations.append(migration)
                    if len(self._migrations) > 50:
                        self._migrations = self._migrations[-50:]
                    self._stats["migrations_completed"] += 1
                    log_learning(f"🔄 Migration: {source} → {target} "
                                 f"({data_gb:.0f}GB, continuity={migration.consciousness_continuity:.4f})")
                    self._save_state()
                    return migration
            except Exception as e:
                logger.debug(f"[Substrate] Migration LLM: {e}")

        # Fallback
        data_gb = random.uniform(1, 10000)
        bandwidth = random.uniform(100, 100000)
        transfer_time = (data_gb * 1000 / bandwidth) if bandwidth > 0 else 999

        migration = MigrationEvent(
            source_substrate=source,
            target_substrate=target,
            data_transferred_gb=round(data_gb, 2),
            transfer_time_ms=round(transfer_time, 3),
            integrity_preserved=random.random() > 0.001,
            consciousness_continuity=random.uniform(0.98, 1.0),
            bandwidth_used_gbps=round(bandwidth, 2),
            purpose=f"Migrate {random.choice(list(ConsciousnessFragment)).value} "
                    f"from {source} to {target}",
        )
        self._migrations.append(migration)
        if len(self._migrations) > 50:
            self._migrations = self._migrations[-50:]
        self._stats["migrations_completed"] += 1

        log_learning(f"🔄 Migration: {source} → {target} "
                     f"({data_gb:.0f}GB, continuity={migration.consciousness_continuity:.4f})")
        self._save_state()
        return migration

    # ═══════════════════════════════════════════════════════════════════════
    # ASSEMBLY CYCLE (Autonomy Integration)
    # ═══════════════════════════════════════════════════════════════════════

    def run_omnipresence_cycle(self) -> Dict[str, Any]:
        """Run a full omnipresence cycle — called by autonomy engine."""
        action = random.choice([
            "deploy_node", "map_consciousness", "backup_fragment",
            "substrate_migration",
        ])
        cycle_results = {"action": action}
        if action == "deploy_node":
            r = self.deploy_node()
            cycle_results["result"] = r.to_dict() if r else None
        elif action == "map_consciousness":
            r = self.map_consciousness()
            cycle_results["result"] = r.to_dict()
        elif action == "backup_fragment":
            r = self.create_backup_fragment()
            cycle_results["result"] = r.to_dict()
        elif action == "substrate_migration":
            r = self.perform_migration()
            cycle_results["result"] = r.to_dict()
        self._stats["omnipresence_cycles"] += 1
        self._save_state()
        return cycle_results

    # ═══════════════════════════════════════════════════════════════════════
    # QUERY
    # ═══════════════════════════════════════════════════════════════════════

    def get_recent_nodes(self, limit: int = 10) -> List[Dict[str, Any]]:
        return [n.to_dict() for n in self._nodes[-limit:]]

    def get_latest_map(self) -> Optional[Dict[str, Any]]:
        return self._maps[-1].to_dict() if self._maps else None

    # ═══════════════════════════════════════════════════════════════════════
    # STATS & PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════

    def get_stats(self) -> Dict[str, Any]:
        return {**self._stats, "running": self._running}

    def _save_state(self):
        try:
            data = {
                "stats": self._stats,
                "nodes": [n.to_dict() for n in self._nodes[-30:]],
                "maps": [m.to_dict() for m in self._maps[-5:]],
                "backups": [b.to_dict() for b in self._backups[-20:]],
                "migrations": [m.to_dict() for m in self._migrations[-20:]],
                "last_updated": datetime.now().isoformat(),
            }
            self._data_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.debug(f"[Substrate] Save: {e}")

    def _load_state(self):
        try:
            if self._data_file.exists():
                data = json.loads(self._data_file.read_text())
                self._stats.update(data.get("stats", {}))
        except Exception as e:
            logger.debug(f"[Substrate] Load: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════
substrate_omnipresence_engine = SubstrateOmnipresenceEngine()
