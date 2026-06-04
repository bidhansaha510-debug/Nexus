"""
NEXUS AI — Routing Experiments (A/B Testing Framework)
Compare different routing strategies side-by-side.

Usage:
    from cognition.routing_experiments import experiment_manager

    # Define an experiment
    experiment_manager.add_experiment(RoutingExperiment(
        name="higher_semantic_weight",
        description="Test 2.5x semantic weight vs default 2.0x",
        config_overrides={"semantic_weight": 2.5},
        traffic_split=0.2,
    ))

    # In route(), get config for this request
    variant = experiment_manager.get_variant(user_input)
"""

import hashlib
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import get_logger

logger = get_logger("routing_experiments")


@dataclass
class ExperimentMetrics:
    """Metrics collected per experiment variant."""
    requests: int = 0
    total_engines_triggered: int = 0
    total_successful_insights: int = 0
    total_latency: float = 0.0
    total_chains_triggered: int = 0

    @property
    def avg_engines(self) -> float:
        return self.total_engines_triggered / max(1, self.requests)

    @property
    def avg_latency(self) -> float:
        return self.total_latency / max(1, self.requests)

    @property
    def insight_rate(self) -> float:
        return self.total_successful_insights / max(1, self.total_engines_triggered)


@dataclass
class RoutingExperiment:
    """An A/B test variant for routing configuration."""
    name: str
    description: str = ""
    config_overrides: Dict[str, Any] = field(default_factory=dict)
    traffic_split: float = 0.0  # 0.0-1.0, fraction of requests for this variant
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metrics: ExperimentMetrics = field(default_factory=ExperimentMetrics)

    # Supported config overrides:
    # - "max_engines": int (override MAX_ENGINES_PER_MESSAGE)
    # - "semantic_weight": float (override semantic merge weight)
    # - "keyword_threshold": float (override KEYWORD_HIGH_CONFIDENCE)
    # - "cooldown_messages": int (override COOLDOWN_MESSAGES)
    # - "engine_timeout": float (override ENGINE_TIMEOUT)


class ExperimentManager:
    """
    Manages A/B testing experiments for routing strategies.

    Each request is deterministically assigned to a variant based on
    a hash of the input (ensures consistent routing for identical inputs).
    """

    _instance = None
    _cls_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._cls_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._lock = threading.Lock()
        self._experiments: Dict[str, RoutingExperiment] = {}
        self._default_config: Dict[str, Any] = {}

        logger.info("ExperimentManager initialized")

    def add_experiment(self, experiment: RoutingExperiment) -> bool:
        """Add or update an experiment."""
        with self._lock:
            # Validate total traffic split doesn't exceed 1.0
            total_split = sum(
                e.traffic_split for name, e in self._experiments.items()
                if name != experiment.name and e.enabled
            )
            if total_split + experiment.traffic_split > 1.0:
                logger.warning(
                    f"Cannot add experiment '{experiment.name}': "
                    f"total traffic split would exceed 1.0 "
                    f"({total_split + experiment.traffic_split:.2f})"
                )
                return False

            self._experiments[experiment.name] = experiment
            logger.info(
                f"Experiment '{experiment.name}' added "
                f"(traffic: {experiment.traffic_split*100:.0f}%)"
            )
            return True

    def remove_experiment(self, name: str) -> bool:
        """Remove an experiment."""
        with self._lock:
            if name in self._experiments:
                del self._experiments[name]
                logger.info(f"Experiment '{name}' removed")
                return True
            return False

    def get_variant(self, user_input: str) -> Optional[RoutingExperiment]:
        """
        Deterministically assign a request to an experiment variant.
        Returns None if the request should use default config.
        """
        with self._lock:
            if not self._experiments:
                return None

            # Deterministic hash → value in [0, 1)
            input_hash = hashlib.sha256(user_input.encode()).hexdigest()
            hash_value = int(input_hash[:8], 16) / (16 ** 8)

            # Check each experiment's traffic range
            cumulative = 0.0
            for name, experiment in self._experiments.items():
                if not experiment.enabled:
                    continue
                cumulative += experiment.traffic_split
                if hash_value < cumulative:
                    return experiment

            return None  # Default config

    def get_config(self, user_input: str) -> Dict[str, Any]:
        """
        Get the effective routing config for this request.
        Returns default config merged with any active experiment overrides.
        """
        config = dict(self._default_config)
        variant = self.get_variant(user_input)
        if variant:
            config.update(variant.config_overrides)
            config["_experiment"] = variant.name
        return config

    def record_result(
        self,
        user_input: str,
        engines_triggered: int,
        successful_insights: int,
        latency: float,
        chains_triggered: int = 0,
    ):
        """Record the result of a routing decision for the assigned variant."""
        variant = self.get_variant(user_input)
        if variant:
            with self._lock:
                variant.metrics.requests += 1
                variant.metrics.total_engines_triggered += engines_triggered
                variant.metrics.total_successful_insights += successful_insights
                variant.metrics.total_latency += latency
                variant.metrics.total_chains_triggered += chains_triggered

    def get_stats(self) -> Dict[str, Any]:
        """Get experiment statistics."""
        with self._lock:
            stats = {
                "total_experiments": len(self._experiments),
                "active_experiments": sum(1 for e in self._experiments.values() if e.enabled),
                "experiments": {},
            }

            for name, exp in self._experiments.items():
                stats["experiments"][name] = {
                    "description": exp.description,
                    "traffic_split": exp.traffic_split,
                    "enabled": exp.enabled,
                    "config_overrides": exp.config_overrides,
                    "metrics": {
                        "requests": exp.metrics.requests,
                        "avg_engines": round(exp.metrics.avg_engines, 2),
                        "avg_latency": round(exp.metrics.avg_latency, 3),
                        "insight_rate": round(exp.metrics.insight_rate, 3),
                    },
                }

            return stats

    def list_experiments(self) -> List[Dict[str, Any]]:
        """List all experiments with their stats."""
        with self._lock:
            return [
                {
                    "name": name,
                    "description": exp.description,
                    "traffic_split": exp.traffic_split,
                    "enabled": exp.enabled,
                    "requests": exp.metrics.requests,
                    "avg_latency": round(exp.metrics.avg_latency, 3),
                    "insight_rate": round(exp.metrics.insight_rate, 3),
                }
                for name, exp in self._experiments.items()
            ]


# Singleton
experiment_manager = ExperimentManager()
