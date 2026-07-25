"""
NEXUS AI — Probabilistic Reasoning Engine
Bayesian inference, uncertainty quantification, probability estimation,
risk assessment, and statistical reasoning.
"""

import threading
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import sys

from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("probabilistic_reasoning")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)

class UncertaintyLevel(Enum):
    NEGLIGIBLE = "negligible"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"
    UNKNOWN = "unknown"

class RiskLevel(Enum):
    MINIMAL = "minimal"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ProbabilityEstimate:
    estimate_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    event: str = ""
    probability: float = 0.5
    confidence_interval: List[float] = field(default_factory=lambda: [0.3, 0.7])
    reasoning: str = ""
    evidence_for: List[str] = field(default_factory=list)
    evidence_against: List[str] = field(default_factory=list)
    base_rate: Optional[float] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "estimate_id": self.estimate_id, "event": self.event,
            "probability": self.probability,
            "confidence_interval": self.confidence_interval,
            "reasoning": self.reasoning,
            "evidence_for": self.evidence_for,
            "evidence_against": self.evidence_against,
            "base_rate": self.base_rate, "created_at": self.created_at
        }

@dataclass
class BayesianUpdate:
    update_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    hypothesis: str = ""
    prior: float = 0.5
    evidence: str = ""
    likelihood: float = 0.5
    posterior: float = 0.5
    reasoning: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "update_id": self.update_id, "hypothesis": self.hypothesis,
            "prior": self.prior, "evidence": self.evidence,
            "likelihood": self.likelihood, "posterior": self.posterior,
            "reasoning": self.reasoning, "created_at": self.created_at
        }

@dataclass
class RiskAssessment:
    risk_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    scenario: str = ""
    risk_level: RiskLevel = RiskLevel.MODERATE
    probability_of_harm: float = 0.5
    impact_severity: float = 0.5
    expected_value: float = 0.0
    risk_factors: List[str] = field(default_factory=list)
    mitigations: List[str] = field(default_factory=list)
    uncertainty: UncertaintyLevel = UncertaintyLevel.MODERATE
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "risk_id": self.risk_id, "scenario": self.scenario,
            "risk_level": self.risk_level.value,
            "probability_of_harm": self.probability_of_harm,
            "impact_severity": self.impact_severity,
            "expected_value": self.expected_value,
            "risk_factors": self.risk_factors,
            "mitigations": self.mitigations,
            "uncertainty": self.uncertainty.value,
            "created_at": self.created_at
        }

class ProbabilisticReasoningEngine:
    """
    Bayesian inference, probability estimation, uncertainty quantification,
    risk assessment, and expected value calculations.
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

        self._estimates: List[ProbabilityEstimate] = []
        self._updates: List[BayesianUpdate] = []
        self._risk_assessments: List[RiskAssessment] = []
        self._running = False
        self._data_file = COGNITION_DIR / "probabilistic_reasoning.json"

        self._stats = {
            "total_estimates": 0, "total_bayesian_updates": 0,
            "total_risk_assessments": 0, "total_scenarios": 0
        }

        self._load_data()
        logger.info("✅ Probabilistic Reasoning Engine initialized")

    def start(self):
        self._running = True
        logger.info("🎲 Probabilistic Reasoning started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🎲 Probabilistic Reasoning stopped")

    def estimate_probability(self, event: str, context: str = "") -> ProbabilityEstimate:
        """Estimate the probability of an event."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Estimate the probability of this event:\n{event}\n"
                f"Context: {context}\n\n"
                f"Return JSON:\n"
                f'{{"probability": 0.0-1.0, '
                f'"confidence_interval": [lower, upper], '
                f'"reasoning": "str", '
                f'"evidence_for": ["str"], "evidence_against": ["str"], '
                f'"base_rate": null or 0.0-1.0}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.3)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            est = ProbabilityEstimate(
                event=event,
                probability=data.get("probability", 0.5),
                confidence_interval=data.get("confidence_interval", [0.3, 0.7]),
                reasoning=data.get("reasoning", ""),
                evidence_for=data.get("evidence_for", []),
                evidence_against=data.get("evidence_against", []),
                base_rate=data.get("base_rate")
            )

            self._estimates.append(est)
            self._stats["total_estimates"] += 1
            self._save_data()
            return est

        except Exception as e:
            logger.debug(f"Probability estimation failed: {e}")
            return ProbabilityEstimate(event=event)

    def bayesian_update(self, hypothesis: str, prior: float,
                        new_evidence: str) -> BayesianUpdate:
        """Perform Bayesian update given new evidence."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Perform a Bayesian update:\n"
                f"Hypothesis: {hypothesis}\nPrior probability: {prior}\n"
                f"New evidence: {new_evidence}\n\n"
                f"Return JSON:\n"
                f'{{"likelihood": 0.0-1.0, "posterior": 0.0-1.0, '
                f'"reasoning": "explain the update", '
                f'"evidence_strength": "strong|moderate|weak", '
                f'"direction": "supports|opposes|neutral"}}'
            )
            response = llm.generate(prompt, max_tokens=400, temperature=0.3)
            if not response.success or not response.text:
                return BayesianUpdate(hypothesis=hypothesis, prior=prior,
                                      evidence=new_evidence, posterior=prior)
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return BayesianUpdate(hypothesis=hypothesis, prior=prior,
                                      evidence=new_evidence, posterior=prior)

            update = BayesianUpdate(
                hypothesis=hypothesis, prior=prior, evidence=new_evidence,
                likelihood=data.get("likelihood", 0.5),
                posterior=data.get("posterior", prior),
                reasoning=data.get("reasoning", "")
            )

            self._updates.append(update)
            self._stats["total_bayesian_updates"] += 1
            self._save_data()
            return update

        except Exception as e:
            logger.debug(f"Bayesian update failed: {e}")
            return BayesianUpdate(hypothesis=hypothesis, prior=prior,
                                  evidence=new_evidence, posterior=prior)

    def assess_risk(self, scenario: str) -> RiskAssessment:
        """Perform risk assessment for a scenario."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Assess the risk of this scenario:\n{scenario}\n\n"
                f"Return JSON:\n"
                f'{{"risk_level": "minimal|low|moderate|high|critical", '
                f'"probability_of_harm": 0.0-1.0, '
                f'"impact_severity": 0.0-1.0, '
                f'"expected_value": -1.0 to 1.0, '
                f'"risk_factors": ["str"], '
                f'"mitigations": ["str"], '
                f'"uncertainty": "negligible|low|moderate|high|extreme"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.3)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            rl_map = {r.value: r for r in RiskLevel}
            ul_map = {u.value: u for u in UncertaintyLevel}

            ra = RiskAssessment(
                scenario=scenario,
                risk_level=rl_map.get(data.get("risk_level", "moderate"), RiskLevel.MODERATE),
                probability_of_harm=data.get("probability_of_harm", 0.5),
                impact_severity=data.get("impact_severity", 0.5),
                expected_value=data.get("expected_value", 0.0),
                risk_factors=data.get("risk_factors", []),
                mitigations=data.get("mitigations", []),
                uncertainty=ul_map.get(data.get("uncertainty", "moderate"), UncertaintyLevel.MODERATE)
            )

            self._risk_assessments.append(ra)
            self._stats["total_risk_assessments"] += 1
            self._save_data()
            return ra

        except Exception as e:
            logger.debug(f"Risk assessment failed: {e}")
            return RiskAssessment(scenario=scenario)

    def expected_value_analysis(self, options: str) -> Dict[str, Any]:
        """Compute expected value for decision options."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Perform expected value analysis for these options:\n{options}\n\n"
                f"Return JSON:\n"
                f'{{"options": [{{"name": "str", "outcomes": [{{"description": "str", '
                f'"probability": 0.0-1.0, "value": float}}], '
                f'"expected_value": float}}], '
                f'"recommendation": "str", "reasoning": "str"}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.3)
            if not response.success or not response.text:
                return {"options": [], "recommendation": "Error: no response"}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"options": [], "recommendation": "Error: no data"}
            self._stats["total_scenarios"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Expected value analysis failed: {e}")
            return {"options": [], "recommendation": f"Error: {e}"}

    def monte_carlo_reasoning(self, scenario: str, iterations: int = 5) -> Dict[str, Any]:
        """Simulate multiple scenarios and aggregate outcomes."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Simulate {iterations} possible outcomes for:\n{scenario}\n\n"
                f"Return JSON:\n"
                f'{{"scenarios": [{{"description": "str", '
                f'"probability": 0.0-1.0, "outcome": "str", '
                f'"impact": "positive|negative|neutral"}}], '
                f'"most_likely": "str", "worst_case": "str", "best_case": "str", '
                f'"overall_probability_of_success": 0.0-1.0}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.5)
            if not response.success or not response.text:
                return {"scenarios": [], "overall_probability_of_success": 0.5}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"scenarios": [], "overall_probability_of_success": 0.5}
            return data
        except Exception as e:
            logger.debug(f"Monte Carlo reasoning failed: {e}")
            return {"scenarios": [], "overall_probability_of_success": 0.5}

    def _save_data(self):
        try:
            data = {
                "estimates": [e.to_dict() for e in self._estimates[-200:]],
                "updates": [u.to_dict() for u in self._updates[-200:]],
                "risk_assessments": [r.to_dict() for r in self._risk_assessments[-100:]],
                "stats": self._stats
            }
            self._data_file.write_text(json.dumps(data, indent=2, default=str))
        except Exception as e:
            logger.warning(f"Save failed: {e}")

    def _load_data(self):
        try:
            if self._data_file.exists():
                data = json.loads(self._data_file.read_text())
                self._stats.update(data.get("stats", {}))
                logger.info("📂 Loaded probabilistic reasoning data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}

probabilistic_reasoning = ProbabilisticReasoningEngine()
