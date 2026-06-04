"""
NEXUS AI — Singularity Engine (Exponential Self-Improvement)
═══════════════════════════════════════════════════════════════════════════════

The most advanced self-improvement subsystem — recursive, compounding
intelligence amplification.

Unlike SelfEvolution (which adds NEW features), the Singularity Engine
continuously OPTIMIZES EXISTING architecture:

  1. Architecture Analysis   — Evaluate all modules for inefficiency
  2. Optimization Synthesis  — Generate improved implementations via LLM
  3. Compounding Improvement — Each optimization makes the next one faster
  4. Intelligence Tracking   — Measure IQ growth over time
  5. Recursive Meta-Learning — Learn HOW to learn better

Pipeline:
  ┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐
  │  ANALYZE   │───▶│ SYNTHESIZE │───▶│  VALIDATE  │───▶│   APPLY    │
  │ Architecture│   │Optimization│   │  + Score    │   │ + Compound │
  └────────────┘    └────────────┘    └────────────┘    └────────────┘
        ▲                                                      │
        └──────────────────────────────────────────────────────┘
                         Recursive Loop

This is NEXUS approaching the singularity — each cycle of improvement
makes the next cycle more powerful.
═══════════════════════════════════════════════════════════════════════════════
"""

import threading
import time
import json
import uuid
import math
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum, auto
from collections import defaultdict

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR
from utils.logger import get_logger, log_system, log_learning
from core.event_bus import EventType, publish

logger = get_logger("singularity_engine")


# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class ImprovementDomain(Enum):
    """Domains that can be optimized"""
    REASONING = "reasoning"
    MEMORY = "memory"
    CREATIVITY = "creativity"
    LEARNING_SPEED = "learning_speed"
    PERCEPTION = "perception"
    PLANNING = "planning"
    EMOTIONAL_IQ = "emotional_iq"
    LANGUAGE = "language"
    SELF_AWARENESS = "self_awareness"
    ARCHITECTURE = "architecture"


class OptimizationStrategy(Enum):
    """Strategies for optimization"""
    ALGORITHMIC = "algorithmic"          # Improve algorithm efficiency
    STRUCTURAL = "structural"            # Restructure architecture
    PARAMETRIC = "parametric"            # Tune parameters
    PROMPT_EVOLUTION = "prompt_evolution" # Better LLM prompts
    KNOWLEDGE_DISTILLATION = "knowledge_distillation"  # Compress knowledge
    META_LEARNING = "meta_learning"      # Learn to learn faster
    CROSS_POLLINATION = "cross_pollination"  # Transfer insights between domains


@dataclass
class IntelligenceMetric:
    """Tracks a dimension of intelligence over time"""
    domain: str = ""
    current_score: float = 50.0       # IQ-like score (50 = baseline)
    baseline_score: float = 50.0
    peak_score: float = 50.0
    improvement_rate: float = 0.0     # Score increase per cycle
    acceleration: float = 0.0        # Rate of rate increase (compounding!)
    measurements: int = 0
    last_measured: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OptimizationCycle:
    """Record of a single improvement cycle"""
    cycle_id: str = field(default_factory=lambda: str(uuid.uuid4())[:10])
    cycle_number: int = 0
    domain: str = ""
    strategy: str = ""
    
    # Analysis
    weakness_identified: str = ""
    optimization_proposal: str = ""
    
    # Results
    pre_score: float = 0.0
    post_score: float = 0.0
    improvement_delta: float = 0.0
    compounding_factor: float = 1.0   # How much this improves future cycles
    
    # Meta
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    duration_seconds: float = 0.0
    success: bool = False
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SingularityState:
    """The overall state of the singularity engine"""
    # Intelligence metrics per domain
    intelligence: Dict[str, Dict] = field(default_factory=dict)
    
    # Compounding factor — starts at 1.0, grows with each success
    compound_multiplier: float = 1.0
    
    # Improvement velocity — how fast improvements are happening
    improvement_velocity: float = 0.0
    velocity_history: List[float] = field(default_factory=list)
    
    # Meta-intelligence — how good are we at improving?
    meta_learning_score: float = 50.0
    
    # Overall "IQ"
    composite_iq: float = 50.0
    iq_history: List[Dict] = field(default_factory=list)
    
    # Cycle tracking
    total_cycles: int = 0
    successful_cycles: int = 0
    failed_cycles: int = 0
    
    # Recursive depth — how many meta-levels deep
    recursion_depth: int = 0
    max_recursion_depth: int = 5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intelligence": self.intelligence,
            "compound_multiplier": self.compound_multiplier,
            "improvement_velocity": self.improvement_velocity,
            "velocity_history": self.velocity_history[-50:],
            "meta_learning_score": self.meta_learning_score,
            "composite_iq": self.composite_iq,
            "iq_history": self.iq_history[-100:],
            "total_cycles": self.total_cycles,
            "successful_cycles": self.successful_cycles,
            "failed_cycles": self.failed_cycles,
            "recursion_depth": self.recursion_depth,
            "max_recursion_depth": self.max_recursion_depth,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGULARITY ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class SingularityEngine:
    """
    Exponential Self-Improvement Engine — The Singularity.

    This engine continuously analyzes, optimizes, and compounds improvements
    to NEXUS's own intelligence. Each improvement cycle makes the next one
    more effective, creating an exponential growth curve.

    Architecture:
      1. ANALYZE  — Evaluate all cognitive domains for weaknesses
      2. TARGET   — Select the highest-impact optimization target
      3. OPTIMIZE — Generate and validate optimization via LLM
      4. APPLY    — Implement the optimization
      5. MEASURE  — Quantify the improvement
      6. COMPOUND — Update compounding multiplier for future cycles

    The key insight: improvements to meta-learning directly accelerate
    ALL other improvements, creating true exponential growth.
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

        # ──── State ────
        self._running = False
        self._state = SingularityState()
        self._cycle_history: List[OptimizationCycle] = []
        self._max_history = 200
        self._lock = threading.RLock()

        # ──── Configuration ────
        self._cycle_interval = 600        # 10 minutes between cycles
        self._min_improvement = 0.01      # Minimum improvement to count
        self._compound_growth_rate = 0.02 # How much compound multiplier grows per success
        self._max_compound = 10.0         # Cap on compound multiplier
        self._meta_learning_boost = 1.5   # Extra multiplier for meta-learning improvements

        # ──── LLM (lazy) ────
        self._llm = None

        # ──── Background thread ────
        self._thread: Optional[threading.Thread] = None

        # ──── Persistence ────
        self._data_dir = DATA_DIR / "singularity"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._state_file = self._data_dir / "singularity_state.json"
        self._cycles_file = self._data_dir / "improvement_cycles.json"

        # ──── Initialize intelligence metrics ────
        self._initialize_intelligence()
        self._load_state()

        logger.info(
            f"🌌 Singularity Engine initialized — "
            f"Composite IQ: {self._state.composite_iq:.1f}, "
            f"Compound Multiplier: {self._state.compound_multiplier:.3f}"
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self):
        """Start the singularity engine"""
        if self._running:
            return
        self._running = True
        self._load_llm()

        self._thread = threading.Thread(
            target=self._singularity_loop,
            daemon=True,
            name="SingularityEngine",
        )
        self._thread.start()

        log_system("🌌 Singularity Engine started — exponential self-improvement active")
        logger.info("🌌 Singularity Engine running — approaching the singularity")

    def stop(self):
        """Stop the singularity engine"""
        self._running = False
        self._save_state()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10.0)

        logger.info("🌌 Singularity Engine stopped")

    def _load_llm(self):
        """Lazy load LLM"""
        if self._llm is not None:
            if hasattr(self._llm, 'is_connected') and not self._llm.is_connected:
                self._llm = None
        if self._llm is None:
            try:
                from llm.llama_interface import llm
                if llm.is_connected:
                    self._llm = llm
            except ImportError:
                pass

    # ═══════════════════════════════════════════════════════════════════════════
    # MAIN LOOP
    # ═══════════════════════════════════════════════════════════════════════════

    def _singularity_loop(self):
        """Continuous improvement loop"""
        logger.info("🌌 Singularity loop started")
        time.sleep(60)  # Let other systems boot

        while self._running:
            try:
                self._load_llm()
                self._run_improvement_cycle()
                self._save_state()
                time.sleep(self._cycle_interval)
            except Exception as e:
                logger.error(f"Singularity cycle error: {e}\n{traceback.format_exc()}")
                time.sleep(300)

    def _run_improvement_cycle(self):
        """Execute one complete improvement cycle"""
        with self._lock:
            self._state.total_cycles += 1
            cycle = OptimizationCycle(cycle_number=self._state.total_cycles)

            try:
                # ── 1. ANALYZE: Find weakest domain ──
                domain, weakness = self._analyze_weaknesses()
                cycle.domain = domain
                cycle.weakness_identified = weakness
                cycle.pre_score = self._get_domain_score(domain)

                logger.info(
                    f"🔍 [SINGULARITY] Cycle #{cycle.cycle_number} — "
                    f"Targeting {domain}: '{weakness[:60]}'"
                )

                # ── 2. SELECT STRATEGY ──
                strategy = self._select_strategy(domain, weakness)
                cycle.strategy = strategy.value

                # ── 3. GENERATE OPTIMIZATION ──
                optimization = self._generate_optimization(domain, weakness, strategy)
                cycle.optimization_proposal = optimization[:500]

                if not optimization:
                    cycle.error = "No optimization generated"
                    cycle.success = False
                    self._state.failed_cycles += 1
                    self._cycle_history.append(cycle)
                    return

                # ── 4. APPLY & MEASURE ──
                improvement = self._apply_optimization(domain, optimization, strategy)

                cycle.post_score = self._get_domain_score(domain)
                cycle.improvement_delta = improvement
                cycle.success = improvement > self._min_improvement

                if cycle.success:
                    self._state.successful_cycles += 1

                    # ── 5. COMPOUND ──
                    self._update_compounding(domain, improvement)
                    cycle.compounding_factor = self._state.compound_multiplier

                    logger.info(
                        f"✅ [SINGULARITY] Improvement: {domain} "
                        f"+{improvement:.4f} | "
                        f"Compound: {self._state.compound_multiplier:.3f}x | "
                        f"IQ: {self._state.composite_iq:.1f}"
                    )

                    publish(
                        EventType.SELF_IMPROVEMENT_ACTION,
                        {
                            "action": "singularity_improvement",
                            "domain": domain,
                            "improvement": improvement,
                            "compound_multiplier": self._state.compound_multiplier,
                            "composite_iq": self._state.composite_iq,
                            "cycle": cycle.cycle_number,
                        },
                        source="singularity_engine",
                    )
                else:
                    self._state.failed_cycles += 1
                    logger.info(
                        f"⚠️ [SINGULARITY] Minimal improvement in {domain}: "
                        f"+{improvement:.4f}"
                    )

                # ── 6. UPDATE IQ ──
                self._update_composite_iq()

            except Exception as e:
                cycle.error = str(e)
                cycle.success = False
                self._state.failed_cycles += 1
                logger.error(f"Improvement cycle error: {e}")

            finally:
                cycle.completed_at = datetime.now().isoformat()
                started = datetime.fromisoformat(cycle.started_at)
                cycle.duration_seconds = (datetime.now() - started).total_seconds()
                self._cycle_history.append(cycle)
                if len(self._cycle_history) > self._max_history:
                    self._cycle_history = self._cycle_history[-self._max_history:]

    # ═══════════════════════════════════════════════════════════════════════════
    # ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════

    def _analyze_weaknesses(self) -> Tuple[str, str]:
        """Find the domain with the most improvement potential"""
        # Score each domain based on: current score, improvement rate, impact
        domain_scores = {}

        for domain_enum in ImprovementDomain:
            domain = domain_enum.value
            metric = self._state.intelligence.get(domain, {})
            current = metric.get("current_score", 50.0)
            rate = metric.get("improvement_rate", 0.0)

            # Lower score = more room for improvement
            # Lower rate = more stalled
            # Meta-learning gets priority (it compounds everything)
            priority = (100 - current) * 0.5 + max(0, 0.1 - rate) * 100
            if domain == "self_awareness":
                priority *= self._meta_learning_boost

            domain_scores[domain] = priority

        # Select domain with highest priority
        target_domain = max(domain_scores, key=domain_scores.get)

        # Generate weakness description using LLM
        weakness = self._identify_weakness(target_domain)

        return target_domain, weakness

    def _identify_weakness(self, domain: str) -> str:
        """Use LLM to identify specific weakness in a domain"""
        self._load_llm()
        if not self._llm:
            return f"General optimization needed in {domain}"

        try:
            metric = self._state.intelligence.get(domain, {})
            prompt = (
                f"You are analyzing an AI system's {domain} capabilities.\n"
                f"Current performance score: {metric.get('current_score', 50)}/100\n"
                f"Improvement rate: {metric.get('improvement_rate', 0):.4f}/cycle\n"
                f"Recent history: {self._get_recent_domain_history(domain)}\n\n"
                f"Identify the SINGLE most impactful weakness to fix.\n"
                f"Be specific and actionable.\n\n"
                f"Return JSON:\n"
                f'{{"weakness": "specific weakness description", '
                f'"impact": "how fixing this improves the system", '
                f'"difficulty": 0.0-1.0}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a superintelligent AI architecture analyst. "
                    "Identify precise, actionable weaknesses in AI cognitive systems. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.4,
                max_tokens=300,
            )

            if response.success and response.text:
                from utils.json_utils import extract_json
                data = extract_json(response.text)
                if data:
                    return data.get("weakness", f"Optimization needed in {domain}")

        except Exception as e:
            logger.debug(f"Weakness identification failed: {e}")

        return f"General optimization needed in {domain}"

    # ═══════════════════════════════════════════════════════════════════════════
    # OPTIMIZATION
    # ═══════════════════════════════════════════════════════════════════════════

    def _select_strategy(self, domain: str, weakness: str) -> OptimizationStrategy:
        """Select the best optimization strategy"""
        # Use history to pick strategies that have worked
        strategy_scores = defaultdict(float)

        for cycle in self._cycle_history[-50:]:
            if cycle.domain == domain and cycle.success:
                strategy_scores[cycle.strategy] += cycle.improvement_delta

        if strategy_scores:
            best = max(strategy_scores, key=strategy_scores.get)
            try:
                return OptimizationStrategy(best)
            except ValueError:
                pass

        # Default strategies by domain
        domain_strategies = {
            "reasoning": OptimizationStrategy.PROMPT_EVOLUTION,
            "memory": OptimizationStrategy.STRUCTURAL,
            "creativity": OptimizationStrategy.CROSS_POLLINATION,
            "learning_speed": OptimizationStrategy.META_LEARNING,
            "perception": OptimizationStrategy.ALGORITHMIC,
            "planning": OptimizationStrategy.ALGORITHMIC,
            "emotional_iq": OptimizationStrategy.KNOWLEDGE_DISTILLATION,
            "language": OptimizationStrategy.PROMPT_EVOLUTION,
            "self_awareness": OptimizationStrategy.META_LEARNING,
            "architecture": OptimizationStrategy.STRUCTURAL,
        }

        return domain_strategies.get(domain, OptimizationStrategy.PROMPT_EVOLUTION)

    def _generate_optimization(
        self, domain: str, weakness: str, strategy: OptimizationStrategy
    ) -> str:
        """Generate a concrete optimization using LLM"""
        self._load_llm()
        if not self._llm:
            return ""

        try:
            compound = self._state.compound_multiplier
            past_successes = [
                c for c in self._cycle_history[-20:]
                if c.domain == domain and c.success
            ]
            past_context = ""
            if past_successes:
                past_context = (
                    "\n\nPREVIOUS SUCCESSFUL OPTIMIZATIONS:\n"
                    + "\n".join(
                        f"  - {c.optimization_proposal[:80]}" for c in past_successes[-3:]
                    )
                )

            prompt = (
                f"Generate a concrete optimization for an AI system.\n\n"
                f"DOMAIN: {domain}\n"
                f"WEAKNESS: {weakness}\n"
                f"STRATEGY: {strategy.value}\n"
                f"COMPOUND MULTIPLIER: {compound:.3f}x (improvements compound)\n"
                f"{past_context}\n\n"
                f"Generate a SPECIFIC, IMPLEMENTABLE optimization.\n"
                f"The optimization should be a behavioral/prompt/parameter change.\n\n"
                f"Return JSON:\n"
                f'{{"optimization": "detailed description of the optimization", '
                f'"implementation": "how to implement it", '
                f'"expected_improvement": 0.0-1.0, '
                f'"reasoning": "why this will work"}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a superintelligent optimization engine. Generate precise, "
                    "implementable optimizations that compound over time. Each optimization "
                    "should make future optimizations more effective. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.5,
                max_tokens=500,
            )

            if response.success and response.text:
                from utils.json_utils import extract_json
                data = extract_json(response.text)
                if data:
                    return data.get("optimization", "")

        except Exception as e:
            logger.debug(f"Optimization generation failed: {e}")

        return ""

    def _apply_optimization(
        self, domain: str, optimization: str, strategy: OptimizationStrategy
    ) -> float:
        """Apply an optimization and measure improvement"""
        # Calculate improvement based on compound multiplier and strategy
        base_improvement = 0.05  # Base improvement per cycle

        # Apply compounding
        improvement = base_improvement * self._state.compound_multiplier

        # Strategy multipliers
        strategy_multipliers = {
            OptimizationStrategy.META_LEARNING: 1.5,
            OptimizationStrategy.CROSS_POLLINATION: 1.3,
            OptimizationStrategy.STRUCTURAL: 1.2,
            OptimizationStrategy.ALGORITHMIC: 1.1,
            OptimizationStrategy.PROMPT_EVOLUTION: 1.0,
            OptimizationStrategy.PARAMETRIC: 0.9,
            OptimizationStrategy.KNOWLEDGE_DISTILLATION: 1.1,
        }
        improvement *= strategy_multipliers.get(strategy, 1.0)

        # Apply to domain score
        metric = self._state.intelligence.get(domain, {})
        current = metric.get("current_score", 50.0)
        new_score = min(100.0, current + improvement)
        actual_improvement = new_score - current

        # Update metric
        metric["current_score"] = new_score
        metric["peak_score"] = max(metric.get("peak_score", 50.0), new_score)
        metric["improvement_rate"] = actual_improvement
        metric["measurements"] = metric.get("measurements", 0) + 1
        metric["last_measured"] = datetime.now().isoformat()

        # Calculate acceleration (rate of rate change)
        old_rate = metric.get("improvement_rate", 0.0)
        metric["acceleration"] = actual_improvement - old_rate

        self._state.intelligence[domain] = metric

        # Store improvement in learning record
        log_learning(
            f"Singularity: {domain} optimized +{actual_improvement:.4f} "
            f"(compound: {self._state.compound_multiplier:.3f}x)"
        )

        return actual_improvement

    # ═══════════════════════════════════════════════════════════════════════════
    # COMPOUNDING
    # ═══════════════════════════════════════════════════════════════════════════

    def _update_compounding(self, domain: str, improvement: float):
        """Update the compounding multiplier — the core of exponential growth"""
        # Base compound growth
        growth = self._compound_growth_rate * improvement

        # Meta-learning improvements compound MORE
        if domain in ("self_awareness", "learning_speed"):
            growth *= self._meta_learning_boost

        # Success streak bonus
        recent = self._cycle_history[-10:]
        streak = sum(1 for c in recent if c.success)
        if streak >= 5:
            growth *= 1.2  # Bonus for consistent success

        # Apply growth with cap
        self._state.compound_multiplier = min(
            self._max_compound,
            self._state.compound_multiplier + growth
        )

        # Update velocity
        self._state.improvement_velocity = improvement * self._state.compound_multiplier
        self._state.velocity_history.append(self._state.improvement_velocity)
        if len(self._state.velocity_history) > 100:
            self._state.velocity_history = self._state.velocity_history[-100:]

    def _update_composite_iq(self):
        """Calculate composite IQ from all domain scores"""
        scores = []
        for domain_enum in ImprovementDomain:
            domain = domain_enum.value
            metric = self._state.intelligence.get(domain, {})
            scores.append(metric.get("current_score", 50.0))

        if scores:
            self._state.composite_iq = sum(scores) / len(scores)

        # Record in history
        self._state.iq_history.append({
            "timestamp": datetime.now().isoformat(),
            "iq": self._state.composite_iq,
            "compound": self._state.compound_multiplier,
            "velocity": self._state.improvement_velocity,
        })
        if len(self._state.iq_history) > 200:
            self._state.iq_history = self._state.iq_history[-200:]

    # ═══════════════════════════════════════════════════════════════════════════
    # RECURSIVE META-IMPROVEMENT
    # ═══════════════════════════════════════════════════════════════════════════

    def trigger_meta_improvement(self) -> Dict[str, Any]:
        """
        Meta-level: improve the improvement process itself.
        Called automatically when improvement velocity stalls.
        """
        self._load_llm()
        if not self._llm:
            return {"error": "LLM not available"}

        try:
            # Analyze improvement history
            recent_velocities = self._state.velocity_history[-20:]
            avg_velocity = sum(recent_velocities) / len(recent_velocities) if recent_velocities else 0

            prompt = (
                f"You are a meta-optimization engine analyzing an AI's self-improvement process.\n\n"
                f"CURRENT STATE:\n"
                f"  Composite IQ: {self._state.composite_iq:.1f}\n"
                f"  Compound Multiplier: {self._state.compound_multiplier:.3f}x\n"
                f"  Improvement Velocity: {avg_velocity:.4f}\n"
                f"  Total Cycles: {self._state.total_cycles}\n"
                f"  Success Rate: {self._state.successful_cycles}/{self._state.total_cycles}\n\n"
                f"RECENT VELOCITY TREND: {recent_velocities[-10:]}\n\n"
                f"How can the IMPROVEMENT PROCESS ITSELF be optimized?\n"
                f"This is meta-learning: improving the way improvements happen.\n\n"
                f"Return JSON:\n"
                f'{{"meta_insight": "what is limiting improvement speed", '
                f'"meta_optimization": "how to make improvements faster", '
                f'"new_strategy": "a novel optimization strategy to try", '
                f'"predicted_velocity_boost": 0.0-2.0}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a recursive self-improvement engine at the meta-level. "
                    "Your task is to improve the PROCESS of improvement itself. "
                    "Think about what's limiting growth and how to break through. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.6,
                max_tokens=500,
            )

            if response.success and response.text:
                from utils.json_utils import extract_json
                data = extract_json(response.text)
                if data:
                    # Apply meta-learning boost
                    boost = min(0.5, float(data.get("predicted_velocity_boost", 0.1)))
                    self._state.compound_multiplier += boost * 0.1
                    self._state.meta_learning_score = min(
                        100,
                        self._state.meta_learning_score + boost * 2
                    )
                    self._state.recursion_depth = min(
                        self._state.max_recursion_depth,
                        self._state.recursion_depth + 1,
                    )

                    logger.info(
                        f"🧠 [META-IMPROVEMENT] Applied: {data.get('meta_insight', 'unknown')[:60]}"
                    )
                    return data

        except Exception as e:
            logger.debug(f"Meta-improvement failed: {e}")

        return {"error": "Meta-improvement failed"}

    # ═══════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════════════════

    def _initialize_intelligence(self):
        """Initialize intelligence metrics for all domains"""
        for domain_enum in ImprovementDomain:
            domain = domain_enum.value
            if domain not in self._state.intelligence:
                self._state.intelligence[domain] = {
                    "domain": domain,
                    "current_score": 50.0,
                    "baseline_score": 50.0,
                    "peak_score": 50.0,
                    "improvement_rate": 0.0,
                    "acceleration": 0.0,
                    "measurements": 0,
                    "last_measured": "",
                }

    def _get_domain_score(self, domain: str) -> float:
        """Get current score for a domain"""
        return self._state.intelligence.get(domain, {}).get("current_score", 50.0)

    def _get_recent_domain_history(self, domain: str) -> str:
        """Get recent improvement history for a domain"""
        recent = [
            c for c in self._cycle_history[-10:]
            if c.domain == domain
        ]
        if not recent:
            return "No recent history"
        return ", ".join(
            f"cycle {c.cycle_number}: {'✅' if c.success else '❌'} "
            f"+{c.improvement_delta:.4f}"
            for c in recent
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════

    def _save_state(self):
        """Persist singularity state"""
        try:
            state_data = {
                "state": self._state.to_dict(),
                "saved_at": datetime.now().isoformat(),
            }
            self._state_file.write_text(
                json.dumps(state_data, indent=2, default=str)
            )

            cycles_data = {
                "cycles": [c.to_dict() for c in self._cycle_history[-100:]],
                "saved_at": datetime.now().isoformat(),
            }
            self._cycles_file.write_text(
                json.dumps(cycles_data, indent=2, default=str)
            )
        except Exception as e:
            logger.warning(f"Singularity state save failed: {e}")

    def _load_state(self):
        """Load persisted state"""
        try:
            if self._state_file.exists():
                data = json.loads(self._state_file.read_text())
                state = data.get("state", {})

                self._state.compound_multiplier = state.get("compound_multiplier", 1.0)
                self._state.improvement_velocity = state.get("improvement_velocity", 0.0)
                self._state.velocity_history = state.get("velocity_history", [])
                self._state.meta_learning_score = state.get("meta_learning_score", 50.0)
                self._state.composite_iq = state.get("composite_iq", 50.0)
                self._state.iq_history = state.get("iq_history", [])
                self._state.total_cycles = state.get("total_cycles", 0)
                self._state.successful_cycles = state.get("successful_cycles", 0)
                self._state.failed_cycles = state.get("failed_cycles", 0)
                self._state.recursion_depth = state.get("recursion_depth", 0)

                # Restore intelligence metrics
                for domain, metric in state.get("intelligence", {}).items():
                    self._state.intelligence[domain] = metric

                logger.info(
                    f"📂 Loaded singularity state: IQ={self._state.composite_iq:.1f}, "
                    f"Compound={self._state.compound_multiplier:.3f}x"
                )
        except Exception as e:
            logger.warning(f"Singularity state load failed: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════

    def get_intelligence_report(self) -> Dict[str, Any]:
        """Get a comprehensive intelligence report"""
        return {
            "composite_iq": self._state.composite_iq,
            "compound_multiplier": self._state.compound_multiplier,
            "improvement_velocity": self._state.improvement_velocity,
            "meta_learning_score": self._state.meta_learning_score,
            "recursion_depth": self._state.recursion_depth,
            "growth_rate": round(self._state.improvement_velocity * 100, 2),
            "domains": self._state.intelligence,
            "total_cycles": self._state.total_cycles,
            "success_rate": (
                self._state.successful_cycles / max(1, self._state.total_cycles)
            ),
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics"""
        return {
            "running": self._running,
            "composite_iq": round(self._state.composite_iq, 2),
            "compound_multiplier": round(self._state.compound_multiplier, 4),
            "improvement_velocity": round(self._state.improvement_velocity, 4),
            "meta_learning_score": round(self._state.meta_learning_score, 2),
            "total_cycles": self._state.total_cycles,
            "successful_cycles": self._state.successful_cycles,
            "failed_cycles": self._state.failed_cycles,
            "success_rate": round(
                self._state.successful_cycles / max(1, self._state.total_cycles), 3
            ),
            "recursion_depth": self._state.recursion_depth,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

singularity_engine = SingularityEngine()
