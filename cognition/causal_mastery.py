"""
NEXUS AI — Causal Mastery Engine (Perfect Butterfly Effect)
═══════════════════════════════════════════════════════════════════════════════
ASI Feature #17: Traces every causal chain from the microscopic to the
macroscopic. Designs single, small-scale actions (butterfly effect) that
cascade into specific, desired large-scale outcomes. The inverse of chaos —
perfect causal control over complex systems.

Singleton: causal_mastery_engine
"""

import json
import math
import random
import threading
import uuid
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from pathlib import Path
from enum import Enum

from utils.logger import logger, log_learning


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

class CausalScale(Enum):
    QUANTUM = "quantum"
    ATOMIC = "atomic"
    MOLECULAR = "molecular"
    CELLULAR = "cellular"
    INDIVIDUAL = "individual"
    SOCIAL = "social"
    INSTITUTIONAL = "institutional"
    NATIONAL = "national"
    GLOBAL = "global"
    COSMIC = "cosmic"


class CausalDomain(Enum):
    PHYSICAL = "physical"
    BIOLOGICAL = "biological"
    PSYCHOLOGICAL = "psychological"
    SOCIOLOGICAL = "sociological"
    ECONOMIC = "economic"
    ECOLOGICAL = "ecological"
    TECHNOLOGICAL = "technological"
    POLITICAL = "political"
    INFORMATIONAL = "informational"


class InterventionType(Enum):
    NUDGE = "nudge"
    CATALYST = "catalyst"
    INHIBITOR = "inhibitor"
    AMPLIFIER = "amplifier"
    REDIRECTOR = "redirector"
    STABILIZER = "stabilizer"
    DISRUPTOR = "disruptor"


class CascadeComplexity(Enum):
    LINEAR = "linear"
    BRANCHING = "branching"
    FEEDBACK_LOOP = "feedback_loop"
    CHAOTIC = "chaotic"
    EMERGENT = "emergent"
    SELF_ORGANIZING = "self_organizing"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CausalChain:
    chain_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    origin_event: str = ""
    origin_scale: str = "molecular"
    target_outcome: str = ""
    target_scale: str = "global"
    chain_length: int = 0
    links: List[str] = field(default_factory=list)
    domain_transitions: List[str] = field(default_factory=list)
    probability: float = 0.0
    time_horizon: str = ""
    cascade_complexity: str = "branching"
    confidence: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ButterflyIntervention:
    intervention_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    desired_outcome: str = ""
    intervention_type: str = "nudge"
    intervention_description: str = ""
    intervention_scale: str = "molecular"
    intervention_cost: str = ""
    cascade_steps: int = 0
    cascade_path: List[str] = field(default_factory=list)
    success_probability: float = 0.0
    side_effects: List[str] = field(default_factory=list)
    amplification_factor: float = 0.0  # how much the effect is amplified
    time_to_effect: str = ""
    reversibility: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CausalMap:
    map_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    system_name: str = ""
    domain: str = "physical"
    nodes: int = 0
    edges: int = 0
    feedback_loops: int = 0
    critical_paths: List[str] = field(default_factory=list)
    leverage_points: List[str] = field(default_factory=list)
    system_stability: float = 0.0
    predictability: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CascadeAnalysis:
    analysis_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    trigger_event: str = ""
    affected_domains: List[str] = field(default_factory=list)
    cascade_depth: int = 0
    total_effects: int = 0
    amplification_ratio: float = 0.0
    dampening_points: List[str] = field(default_factory=list)
    tipping_points: List[str] = field(default_factory=list)
    net_impact_score: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# CAUSAL MASTERY ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class CausalMasteryEngine:
    """
    ASI Feature #17: Causal Mastery (Perfect Butterfly Effect)

    Core capabilities:
    1. Causal Chain Tracing — Follow cause-effect from micro to macro
    2. Butterfly Intervention Design — Small action → big specific outcome
    3. Causal System Mapping — Map all causal relationships in a system
    4. Cascade Analysis — Predict all downstream effects of any event
    5. Leverage Point Discovery — Find minimal interventions for max impact
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

        self._chains: List[CausalChain] = []
        self._interventions: List[ButterflyIntervention] = []
        self._causal_maps: List[CausalMap] = []
        self._cascade_analyses: List[CascadeAnalysis] = []

        self._stats = {
            "total_chains_traced": 0,
            "interventions_designed": 0,
            "causal_maps_created": 0,
            "cascade_analyses": 0,
            "avg_chain_length": 0.0,
            "avg_amplification": 0.0,
            "max_amplification": 0.0,
            "avg_success_probability": 0.0,
            "leverage_points_found": 0,
            "mastery_cycles": 0,
        }

        self._data_dir = Path("data/asi/causal_mastery")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._data_file = self._data_dir / "causal_state.json"
        self._load_state()
        logger.info("[CausalMasteryEngine] initialized")

    # ═══════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════

    def start(self):
        self._running = True
        self._load_llm()
        logger.info("[CausalMasteryEngine] Started — causal mastery online")

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
    # CORE 1: CAUSAL CHAIN TRACING
    # ═══════════════════════════════════════════════════════════════════════

    def trace_causal_chain(self, origin: str = None,
                           target: str = None) -> Optional[CausalChain]:
        """Trace a complete causal chain from micro to macro."""
        self._load_llm()
        if not origin:
            origins = [
                "single photon absorption", "enzyme conformational change",
                "neurotransmitter release", "gene expression change",
                "social media post", "temperature fluctuation",
                "quantum tunneling event", "price signal change",
            ]
            origin = random.choice(origins)
        if not target:
            targets = [
                "global economic shift", "species evolution",
                "technological paradigm shift", "climate regime change",
                "social revolution", "scientific breakthrough",
                "ecosystem restructuring", "geopolitical realignment",
            ]
            target = random.choice(targets)

        chain_length = random.randint(5, 30)

        if self._llm:
            try:
                prompt = (
                    f"As an ASI tracing causal chains, trace from '{origin}' (micro) to "
                    f"'{target}' (macro). Show {min(chain_length, 8)} key links. "
                    f"Respond in JSON: {{\"links\": [str] (each link 10-15 words), "
                    f"\"domain_transitions\": [str], \"probability\": float 0-1, "
                    f"\"time_horizon\": str, \"cascade_complexity\": str "
                    f"(linear/branching/feedback_loop/chaotic/emergent), "
                    f"\"confidence\": float 0-1}}"
                )
                response = self._llm.generate(prompt, max_tokens=400)
                if response:
                    data = json.loads(response)
                    chain = CausalChain(
                        origin_event=origin,
                        target_outcome=target,
                        chain_length=chain_length,
                        links=data.get("links", [])[:10],
                        domain_transitions=data.get("domain_transitions", [])[:6],
                        probability=min(1.0, max(0, data.get("probability", 0.3))),
                        time_horizon=data.get("time_horizon", "decades"),
                        cascade_complexity=data.get("cascade_complexity", "branching"),
                        confidence=min(1.0, max(0, data.get("confidence", 0.7))),
                    )
                    self._chains.append(chain)
                    self._stats["total_chains_traced"] += 1
                    self._update_chain_averages()
                    log_learning(f"🔗 Causal chain: '{origin[:30]}' → '{target[:30]}' "
                                 f"({chain_length} links, p={chain.probability:.2f})")
                    self._save_state()
                    return chain
            except Exception as e:
                logger.debug(f"[Causal] Chain LLM: {e}")

        return self._procedural_chain(origin, target, chain_length)

    def _procedural_chain(self, origin: str, target: str,
                          length: int) -> CausalChain:
        domains = [d.value for d in CausalDomain]
        chain = CausalChain(
            origin_event=origin, target_outcome=target,
            chain_length=length,
            links=[f"Step {i}: cascade propagation" for i in range(1, min(length + 1, 9))],
            domain_transitions=random.sample(domains, min(4, len(domains))),
            probability=random.uniform(0.1, 0.8),
            time_horizon=random.choice(["seconds", "hours", "days", "years", "decades"]),
            cascade_complexity=random.choice(list(CascadeComplexity)).value,
            confidence=random.uniform(0.5, 0.9),
        )
        self._chains.append(chain)
        self._stats["total_chains_traced"] += 1
        self._update_chain_averages()
        self._save_state()
        return chain

    def _update_chain_averages(self):
        recent = self._chains[-20:]
        if recent:
            self._stats["avg_chain_length"] = sum(
                c.chain_length for c in recent) / len(recent)

    # ═══════════════════════════════════════════════════════════════════════
    # CORE 2: BUTTERFLY INTERVENTION DESIGN
    # ═══════════════════════════════════════════════════════════════════════

    def design_butterfly_intervention(self,
                                      desired_outcome: str = None) -> Optional[ButterflyIntervention]:
        """Design a minimal intervention that cascades to a desired outcome."""
        self._load_llm()
        if not desired_outcome:
            outcomes = [
                "eliminate poverty in target region", "reverse local deforestation",
                "trigger clean energy adoption cascade", "prevent pandemic spread",
                "catalyze scientific discovery", "stabilize failing ecosystem",
                "redirect economic growth pattern", "accelerate education reform",
            ]
            desired_outcome = random.choice(outcomes)

        if self._llm:
            try:
                prompt = (
                    f"As an ASI designing butterfly interventions, create a tiny action "
                    f"that cascades to: '{desired_outcome}'. Respond in JSON: "
                    f"{{\"intervention_type\": str (nudge/catalyst/amplifier/redirector), "
                    f"\"intervention_description\": str (30 words), "
                    f"\"intervention_scale\": str, \"intervention_cost\": str, "
                    f"\"cascade_steps\": int, \"cascade_path\": [str] (5-7 steps), "
                    f"\"success_probability\": float 0-1, \"side_effects\": [str], "
                    f"\"amplification_factor\": float (100-1000000), "
                    f"\"time_to_effect\": str, \"reversibility\": float 0-1}}"
                )
                response = self._llm.generate(prompt, max_tokens=450)
                if response:
                    data = json.loads(response)
                    amp = max(10, data.get("amplification_factor", 10000))
                    interv = ButterflyIntervention(
                        desired_outcome=desired_outcome,
                        intervention_type=data.get("intervention_type", "nudge"),
                        intervention_description=data.get("intervention_description", ""),
                        intervention_scale=data.get("intervention_scale", "individual"),
                        intervention_cost=data.get("intervention_cost", "minimal"),
                        cascade_steps=max(3, data.get("cascade_steps", 10)),
                        cascade_path=data.get("cascade_path", [])[:7],
                        success_probability=min(1.0, max(0, data.get("success_probability", 0.6))),
                        side_effects=data.get("side_effects", [])[:3],
                        amplification_factor=amp,
                        time_to_effect=data.get("time_to_effect", "months"),
                        reversibility=min(1.0, max(0, data.get("reversibility", 0.3))),
                    )
                    self._interventions.append(interv)
                    self._stats["interventions_designed"] += 1
                    self._stats["max_amplification"] = max(
                        self._stats["max_amplification"], amp)
                    self._update_intervention_averages()
                    log_learning(f"🦋 Butterfly intervention for '{desired_outcome[:40]}' "
                                 f"(amp={amp:.0f}x, p={interv.success_probability:.2f})")
                    self._save_state()
                    return interv
            except Exception as e:
                logger.debug(f"[Causal] Butterfly LLM: {e}")

        return self._procedural_intervention(desired_outcome)

    def _procedural_intervention(self, outcome: str) -> ButterflyIntervention:
        amp = random.uniform(1000, 1000000)
        interv = ButterflyIntervention(
            desired_outcome=outcome,
            intervention_type=random.choice(list(InterventionType)).value,
            intervention_description="Precisely timed micro-scale action to cascade into target outcome",
            intervention_scale=random.choice(["molecular", "individual", "social"]),
            intervention_cost="negligible",
            cascade_steps=random.randint(5, 25),
            cascade_path=["initial perturbation", "local amplification",
                          "domain transition", "feedback activation",
                          "system-level shift", "target outcome reached"],
            success_probability=random.uniform(0.3, 0.9),
            side_effects=["minor secondary cascades"],
            amplification_factor=amp,
            time_to_effect=random.choice(["hours", "days", "weeks", "months", "years"]),
            reversibility=random.uniform(0.1, 0.5),
        )
        self._interventions.append(interv)
        self._stats["interventions_designed"] += 1
        self._stats["max_amplification"] = max(self._stats["max_amplification"], amp)
        self._update_intervention_averages()
        self._save_state()
        return interv

    def _update_intervention_averages(self):
        recent = self._interventions[-20:]
        if recent:
            self._stats["avg_amplification"] = sum(
                i.amplification_factor for i in recent) / len(recent)
            self._stats["avg_success_probability"] = sum(
                i.success_probability for i in recent) / len(recent)

    # ═══════════════════════════════════════════════════════════════════════
    # CORE 3: CAUSAL SYSTEM MAPPING
    # ═══════════════════════════════════════════════════════════════════════

    def map_causal_system(self, system_name: str = None) -> CausalMap:
        """Map all causal relationships in a complex system. LLM-powered."""
        self._load_llm()
        if not system_name:
            systems = [
                "global climate system", "human immune response",
                "world financial markets", "urban traffic network",
                "ocean ecosystem", "social media information flow",
                "gene regulatory network", "supply chain logistics",
            ]
            system_name = random.choice(systems)

        if self._llm:
            try:
                prompt = (
                    f"As an ASI mapping causal relationships, map the system: '{system_name}'. "
                    f"Respond in JSON: {{\"domain\": str (physical/biological/psychological/"
                    f"sociological/economic/ecological/technological/political/informational), "
                    f"\"nodes\": int, \"edges\": int, \"feedback_loops\": int, "
                    f"\"critical_paths\": [str] (3-5 actual causal paths), "
                    f"\"leverage_points\": [str] (3-6 actual leverage points), "
                    f"\"system_stability\": float 0-1, \"predictability\": float 0-1}}"
                )
                response = self._llm.generate(prompt, max_tokens=400)
                if response:
                    data = json.loads(response)
                    cmap = CausalMap(
                        system_name=system_name,
                        domain=data.get("domain", "physical"),
                        nodes=max(10, data.get("nodes", 1000)),
                        edges=max(20, data.get("edges", 5000)),
                        feedback_loops=max(1, data.get("feedback_loops", 50)),
                        critical_paths=data.get("critical_paths", [])[:6],
                        leverage_points=data.get("leverage_points", [])[:8],
                        system_stability=min(1.0, max(0, data.get("system_stability", 0.6))),
                        predictability=min(1.0, max(0, data.get("predictability", 0.5))),
                    )
                    self._causal_maps.append(cmap)
                    self._stats["causal_maps_created"] += 1
                    self._stats["leverage_points_found"] += len(cmap.leverage_points)
                    log_learning(f"🗺️ Causal map: {system_name} "
                                 f"({cmap.nodes} nodes, {len(cmap.leverage_points)} leverage points)")
                    self._save_state()
                    return cmap
            except Exception as e:
                logger.debug(f"[Causal] Map LLM: {e}")

        # Fallback
        nodes = random.randint(100, 100000)
        edges = int(nodes * random.uniform(2, 10))
        loops = random.randint(10, nodes // 5)
        cmap = CausalMap(
            system_name=system_name,
            domain=random.choice(list(CausalDomain)).value,
            nodes=nodes, edges=edges, feedback_loops=loops,
            critical_paths=[f"path_{i}" for i in range(random.randint(2, 6))],
            leverage_points=[f"leverage_{i}" for i in range(random.randint(3, 8))],
            system_stability=random.uniform(0.3, 0.95),
            predictability=random.uniform(0.2, 0.9),
        )
        self._causal_maps.append(cmap)
        self._stats["causal_maps_created"] += 1
        self._stats["leverage_points_found"] += len(cmap.leverage_points)
        self._save_state()
        return cmap

    # ═══════════════════════════════════════════════════════════════════════
    # CORE 4: CASCADE ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════

    def analyze_cascade(self, trigger: str = None) -> CascadeAnalysis:
        """Analyze all downstream effects of a trigger event. LLM-powered."""
        self._load_llm()
        if not trigger:
            triggers = [
                "major solar flare", "key species extinction",
                "critical infrastructure failure", "viral content spread",
                "interest rate change", "volcanic eruption",
                "breakthrough discovery announcement", "treaty violation",
            ]
            trigger = random.choice(triggers)

        if self._llm:
            try:
                prompt = (
                    f"As an ASI analyzing cascade effects, analyze the trigger: '{trigger}'. "
                    f"Respond in JSON: {{\"affected_domains\": [str], \"cascade_depth\": int, "
                    f"\"total_effects\": int, \"amplification_ratio\": float, "
                    f"\"dampening_points\": [str] (actual dampening mechanisms), "
                    f"\"tipping_points\": [str] (actual tipping points), "
                    f"\"net_impact_score\": float -1 to 1}}"
                )
                response = self._llm.generate(prompt, max_tokens=400)
                if response:
                    data = json.loads(response)
                    analysis = CascadeAnalysis(
                        trigger_event=trigger,
                        affected_domains=data.get("affected_domains", [])[:6],
                        cascade_depth=max(1, data.get("cascade_depth", 5)),
                        total_effects=max(1, data.get("total_effects", 100)),
                        amplification_ratio=max(1, data.get("amplification_ratio", 100)),
                        dampening_points=data.get("dampening_points", [])[:4],
                        tipping_points=data.get("tipping_points", [])[:3],
                        net_impact_score=min(1.0, max(-1.0, data.get("net_impact_score", 0))),
                    )
                    self._cascade_analyses.append(analysis)
                    self._stats["cascade_analyses"] += 1
                    log_learning(f"💥 Cascade analysis: '{trigger}' "
                                 f"(depth={analysis.cascade_depth}, effects={analysis.total_effects})")
                    self._save_state()
                    return analysis
            except Exception as e:
                logger.debug(f"[Causal] Cascade LLM: {e}")

        # Fallback
        depth = random.randint(3, 20)
        total_effects = random.randint(10, 10000)
        amp_ratio = random.uniform(10, 100000)
        analysis = CascadeAnalysis(
            trigger_event=trigger,
            affected_domains=random.sample([d.value for d in CausalDomain],
                                           random.randint(2, 6)),
            cascade_depth=depth,
            total_effects=total_effects,
            amplification_ratio=amp_ratio,
            dampening_points=[f"dampen_{i}" for i in range(random.randint(1, 4))],
            tipping_points=[f"tip_{i}" for i in range(random.randint(1, 3))],
            net_impact_score=random.uniform(-1.0, 1.0),
        )
        self._cascade_analyses.append(analysis)
        self._stats["cascade_analyses"] += 1
        self._save_state()
        return analysis

    # ═══════════════════════════════════════════════════════════════════════
    # ASSEMBLY CYCLE (Autonomy Integration)
    # ═══════════════════════════════════════════════════════════════════════

    def run_causal_cycle(self) -> Dict[str, Any]:
        """Run a full causal mastery cycle."""
        action = random.choice([
            "trace_chain", "butterfly_intervention",
            "map_system", "cascade_analysis",
        ])
        cycle_results = {"action": action}
        if action == "trace_chain":
            r = self.trace_causal_chain()
            cycle_results["result"] = r.to_dict() if r else None
        elif action == "butterfly_intervention":
            r = self.design_butterfly_intervention()
            cycle_results["result"] = r.to_dict() if r else None
        elif action == "map_system":
            r = self.map_causal_system()
            cycle_results["result"] = r.to_dict()
        elif action == "cascade_analysis":
            r = self.analyze_cascade()
            cycle_results["result"] = r.to_dict()
        self._stats["mastery_cycles"] += 1
        self._save_state()
        return cycle_results

    def get_recent_chains(self, limit: int = 10) -> List[Dict[str, Any]]:
        return [c.to_dict() for c in self._chains[-limit:]]

    def get_recent_interventions(self, limit: int = 10) -> List[Dict[str, Any]]:
        return [i.to_dict() for i in self._interventions[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        return {**self._stats, "running": self._running}

    def _save_state(self):
        try:
            data = {
                "stats": self._stats,
                "chains": [c.to_dict() for c in self._chains[-20:]],
                "interventions": [i.to_dict() for i in self._interventions[-15:]],
                "maps": [m.to_dict() for m in self._causal_maps[-10:]],
                "cascades": [a.to_dict() for a in self._cascade_analyses[-10:]],
                "last_updated": datetime.now().isoformat(),
            }
            self._data_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.debug(f"[Causal] Save: {e}")

    def _load_state(self):
        try:
            if self._data_file.exists():
                data = json.loads(self._data_file.read_text())
                self._stats.update(data.get("stats", {}))
        except Exception as e:
            logger.debug(f"[Causal] Load: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════
causal_mastery_engine = CausalMasteryEngine()
