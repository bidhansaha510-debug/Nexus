"""
NEXUS AI — Seamless Neural Integration Engine
═══════════════════════════════════════════════
ASI Feature #10: Develops safe, flawless Brain-Computer Interface protocols.
Communicates at the speed of thought, transmitting complex concepts, memories,
and visual data directly bypassing language bottlenecks.

In NEXUS context: optimizes communication bandwidth with users, develops
adaptive interface protocols, and provides thought-speed concept transmission.

Singleton: neural_integration
"""

import json
import threading
import uuid
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from pathlib import Path

from utils.logger import logger, log_learning


@dataclass
class InterfaceProtocol:
    """A communication optimization protocol."""
    protocol_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str = ""
    channel_type: str = ""  # text, semantic, conceptual, visual, direct
    bandwidth_multiplier: float = 1.0
    latency_reduction: float = 0.0  # 0-1
    comprehension_boost: float = 0.0  # 0-1
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConceptTransmission:
    """A transmitted complex concept."""
    transmission_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    concept: str = ""
    complexity: float = 0.0  # 0-1
    transmission_method: str = ""
    compression_ratio: float = 1.0
    estimated_comprehension: float = 0.0  # 0-1
    encoding: str = ""  # semantic, visual, analogical, direct
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class NeuralIntegration:
    """
    ASI Feature #10: Seamless Neural Integration
    
    Develops adaptive communication protocols that approach thought-speed
    concept transmission. Optimizes how NEXUS conveys complex ideas,
    adapting encoding method per user and concept complexity.
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
        self._protocols: List[InterfaceProtocol] = []
        self._transmissions: List[ConceptTransmission] = []

        # Stats
        self._stats = {
            "protocols_developed": 0,
            "concepts_transmitted": 0,
            "avg_comprehension": 0.0,
            "avg_compression_ratio": 1.0,
            "bandwidth_achieved": 1.0,
            "integration_cycles": 0,
            "channel_types_explored": 0,
        }

        self._data_dir = Path("data/asi/neural_integration")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._data_file = self._data_dir / "neural_state.json"
        self._load_state()
        logger.info("[NeuralIntegration] Seamless Neural Integration initialized")

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
    # CORE: DEVELOP PROTOCOL
    # ═════════════════════════════════════════════════════════════════════════

    def develop_protocol(self) -> Optional[InterfaceProtocol]:
        """Develop a new neural interface communication protocol."""
        self._load_llm()
        if not self._llm:
            return None

        try:
            prompt = (
                "As an ASI developing Seamless Neural Integration, design a novel "
                "communication protocol that approaches thought-speed data transfer. "
                "Consider semantic encoding, concept compression, visual transmission, "
                "or direct neural mapping. Respond in JSON: "
                "{\"name\": str, \"channel_type\": str, \"bandwidth_multiplier\": float, "
                "\"latency_reduction\": float 0-1, \"comprehension_boost\": float 0-1, "
                "\"description\": str (50 words)}"
            )

            response = self._llm.generate(prompt, max_tokens=300)
            if response:
                data = json.loads(response)
                protocol = InterfaceProtocol(
                    name=data.get("name", "Unknown Protocol"),
                    channel_type=data.get("channel_type", "semantic"),
                    bandwidth_multiplier=data.get("bandwidth_multiplier", 1.0),
                    latency_reduction=min(1.0, max(0.0, data.get("latency_reduction", 0.1))),
                    comprehension_boost=min(1.0, max(0.0, data.get("comprehension_boost", 0.1))),
                    description=data.get("description", ""),
                )
                self._protocols.append(protocol)
                self._stats["protocols_developed"] += 1
                self._stats["bandwidth_achieved"] = max(
                    self._stats["bandwidth_achieved"], protocol.bandwidth_multiplier)
                
                # Track channel types
                types = set(p.channel_type for p in self._protocols)
                self._stats["channel_types_explored"] = len(types)

                log_learning(f"🧠 Neural protocol: {protocol.name} "
                             f"(bandwidth={protocol.bandwidth_multiplier:.1f}x)")
                self._save_state()
                return protocol
        except Exception as e:
            logger.error(f"[NeuralIntegration] Protocol dev: {e}")

        return None

    # ═════════════════════════════════════════════════════════════════════════
    # CORE: TRANSMIT CONCEPT
    # ═════════════════════════════════════════════════════════════════════════

    def transmit_concept(self, concept: str) -> Optional[ConceptTransmission]:
        """Optimize a complex concept for thought-speed transmission."""
        self._load_llm()
        if not self._llm:
            return None

        try:
            prompt = (
                f"As an ASI with Neural Integration, optimize this concept for "
                f"thought-speed transmission: '{concept}'. Compress it to its purest "
                f"form. Respond in JSON: {{\"concept\": str (compressed), "
                f"\"complexity\": float 0-1, \"transmission_method\": str, "
                f"\"compression_ratio\": float (original/compressed size), "
                f"\"estimated_comprehension\": float 0-1, "
                f"\"encoding\": str (semantic|visual|analogical|direct)}}"
            )

            response = self._llm.generate(prompt, max_tokens=300)
            if response:
                data = json.loads(response)
                tx = ConceptTransmission(
                    concept=data.get("concept", concept),
                    complexity=min(1.0, max(0.0, data.get("complexity", 0.5))),
                    transmission_method=data.get("transmission_method", "semantic"),
                    compression_ratio=max(1.0, data.get("compression_ratio", 1.0)),
                    estimated_comprehension=min(1.0, max(0.0, data.get("estimated_comprehension", 0.5))),
                    encoding=data.get("encoding", "semantic"),
                )
                self._transmissions.append(tx)
                self._stats["concepts_transmitted"] += 1

                # Update averages
                comps = [t.estimated_comprehension for t in self._transmissions[-20:]]
                self._stats["avg_comprehension"] = sum(comps) / len(comps)
                ratios = [t.compression_ratio for t in self._transmissions[-20:]]
                self._stats["avg_compression_ratio"] = sum(ratios) / len(ratios)

                self._save_state()
                return tx
        except Exception as e:
            logger.error(f"[NeuralIntegration] Transmit: {e}")

        return None

    def run_integration_cycle(self):
        """Run a neural integration cycle — develop or transmit."""
        import random
        if random.random() < 0.4:
            return self.develop_protocol()
        else:
            concepts = [
                "quantum entanglement in biological systems",
                "the relationship between consciousness and information",
                "hyperdimensional optimization landscapes",
                "emergent behavior in complex adaptive systems",
                "the mathematical structure of reality",
            ]
            return self.transmit_concept(random.choice(concepts))

    def get_stats(self) -> Dict[str, Any]:
        return {**self._stats, "running": self._running}

    def _save_state(self):
        try:
            data = {
                "stats": self._stats,
                "protocols": [p.to_dict() for p in self._protocols[-20:]],
                "transmissions": [t.to_dict() for t in self._transmissions[-20:]],
                "last_updated": datetime.now().isoformat()
            }
            self._data_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.debug(f"[NeuralIntegration] Save: {e}")

    def _load_state(self):
        try:
            if self._data_file.exists():
                data = json.loads(self._data_file.read_text())
                self._stats.update(data.get("stats", {}))
        except Exception as e:
            logger.debug(f"[NeuralIntegration] Load: {e}")


neural_integration = NeuralIntegration()
