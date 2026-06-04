"""
NEXUS AI — Hypothesis Engine
Scientific method, hypothesis generation/testing,
experimental design, evidence evaluation, falsification.
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
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("hypothesis_engine")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)


class HypothesisStatus(Enum):
    PROPOSED = "proposed"
    TESTING = "testing"
    SUPPORTED = "supported"
    REFUTED = "refuted"
    INCONCLUSIVE = "inconclusive"
    NEEDS_MORE_DATA = "needs_more_data"


class EvidenceStrength(Enum):
    ANECDOTAL = "anecdotal"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"
    CONCLUSIVE = "conclusive"


@dataclass
class Hypothesis:
    hypothesis_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    statement: str = ""
    null_hypothesis: str = ""
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    confidence: float = 0.5
    evidence_for: List[Dict[str, Any]] = field(default_factory=list)
    evidence_against: List[Dict[str, Any]] = field(default_factory=list)
    testable_predictions: List[str] = field(default_factory=list)
    falsification_criteria: str = ""
    domain: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "hypothesis_id": self.hypothesis_id, "statement": self.statement,
            "null_hypothesis": self.null_hypothesis,
            "status": self.status.value, "confidence": self.confidence,
            "evidence_for": self.evidence_for,
            "evidence_against": self.evidence_against,
            "testable_predictions": self.testable_predictions,
            "falsification_criteria": self.falsification_criteria,
            "domain": self.domain, "created_at": self.created_at
        }


@dataclass
class Experiment:
    experiment_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    hypothesis_id: str = ""
    design: str = ""
    variables: Dict[str, Any] = field(default_factory=dict)
    methodology: str = ""
    expected_results: str = ""
    controls: List[str] = field(default_factory=list)
    potential_confounds: List[str] = field(default_factory=list)
    sample_size: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "experiment_id": self.experiment_id,
            "hypothesis_id": self.hypothesis_id,
            "design": self.design, "variables": self.variables,
            "methodology": self.methodology,
            "expected_results": self.expected_results,
            "controls": self.controls,
            "potential_confounds": self.potential_confounds,
            "sample_size": self.sample_size, "created_at": self.created_at
        }


class HypothesisEngine:
    """
    Scientific reasoning: hypothesis generation, testing design,
    evidence evaluation, and falsification tracking.
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

        self._hypotheses: List[Hypothesis] = []
        self._experiments: List[Experiment] = []
        self._running = False
        self._data_file = COGNITION_DIR / "hypothesis_engine.json"

        self._stats = {
            "total_hypotheses": 0, "total_experiments": 0,
            "total_supported": 0, "total_refuted": 0,
            "total_evidence_evaluated": 0
        }

        self._load_data()
        logger.info("✅ Hypothesis Engine initialized")

    def start(self):
        self._running = True
        logger.info("🔬 Hypothesis Engine started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🔬 Hypothesis Engine stopped")

    def generate_hypotheses(self, observation: str, count: int = 3) -> List[Hypothesis]:
        """Generate hypotheses to explain an observation."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Generate {count} hypotheses to explain this observation:\n{observation}\n\n"
                f"Return JSON array:\n"
                f'[{{"statement": "the hypothesis", '
                f'"null_hypothesis": "what would be true if this is wrong", '
                f'"testable_predictions": ["predictions that follow"], '
                f'"falsification_criteria": "what would disprove this", '
                f'"domain": "str", "confidence": 0.0-1.0}}]'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.5)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            hypotheses = []
            for item in data:
                h = Hypothesis(
                    statement=item.get("statement", ""),
                    null_hypothesis=item.get("null_hypothesis", ""),
                    testable_predictions=item.get("testable_predictions", []),
                    falsification_criteria=item.get("falsification_criteria", ""),
                    domain=item.get("domain", ""),
                    confidence=item.get("confidence", 0.5)
                )
                hypotheses.append(h)
                self._hypotheses.append(h)

            self._stats["total_hypotheses"] += len(hypotheses)
            self._save_data()
            return hypotheses

        except Exception as e:
            logger.debug(f"Hypothesis generation failed: {e}")
            return []

    def design_experiment(self, hypothesis: str) -> Experiment:
        """Design an experiment to test a hypothesis."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Design an experiment to test this hypothesis:\n{hypothesis}\n\n"
                f"Return JSON:\n"
                f'{{"design": "experiment description", '
                f'"variables": {{"independent": ["str"], "dependent": ["str"], '
                f'"controlled": ["str"]}}, '
                f'"methodology": "str", '
                f'"expected_results": "what results would support/refute", '
                f'"controls": ["control conditions"], '
                f'"potential_confounds": ["str"], '
                f'"sample_size": "str"}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.3)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            exp = Experiment(
                design=data.get("design", ""),
                variables=data.get("variables", {}),
                methodology=data.get("methodology", ""),
                expected_results=data.get("expected_results", ""),
                controls=data.get("controls", []),
                potential_confounds=data.get("potential_confounds", []),
                sample_size=data.get("sample_size", "")
            )

            self._experiments.append(exp)
            self._stats["total_experiments"] += 1
            self._save_data()
            return exp

        except Exception as e:
            logger.debug(f"Experiment design failed: {e}")
            return Experiment(design=f"Error: {e}")

    def evaluate_evidence(self, hypothesis: str, evidence: str) -> Dict[str, Any]:
        """Evaluate how evidence affects a hypothesis."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Evaluate this evidence against the hypothesis:\n"
                f"Hypothesis: {hypothesis}\nEvidence: {evidence}\n\n"
                f"Return JSON:\n"
                f'{{"supports_hypothesis": true/false, '
                f'"evidence_strength": "anecdotal|weak|moderate|strong|very_strong|conclusive", '
                f'"updated_confidence": 0.0-1.0, '
                f'"reasoning": "str", '
                f'"alternative_explanations": ["str"], '
                f'"additional_evidence_needed": ["str"], '
                f'"updated_status": "supported|refuted|inconclusive|needs_more_data"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.3)
            if not response.success or not response.text:
                return {"supports_hypothesis": None, "evidence_strength": "unknown"}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"supports_hypothesis": None, "evidence_strength": "unknown"}
            self._stats["total_evidence_evaluated"] += 1
            status = data.get("updated_status", "inconclusive")
            if status == "supported":
                self._stats["total_supported"] += 1
            elif status == "refuted":
                self._stats["total_refuted"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Evidence evaluation failed: {e}")
            return {"supports_hypothesis": None, "evidence_strength": "unknown"}

    def scientific_method(self, question: str) -> Dict[str, Any]:
        """Apply the full scientific method to a question."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Apply the full scientific method to:\n{question}\n\n"
                f"Return JSON:\n"
                f'{{"question": "str", '
                f'"background_research": ["key findings"], '
                f'"hypothesis": "str", '
                f'"experiment": {{"design": "str", "variables": {{"independent": ["str"], '
                f'"dependent": ["str"]}}, "procedure": ["steps"]}}, '
                f'"predicted_results": "str", '
                f'"analysis_plan": "str", '
                f'"potential_conclusions": ["possible outcomes"]}}'
            )
            response = llm.generate(prompt, max_tokens=700, temperature=0.4)
            if not response.success or not response.text:
                return {"question": question, "hypothesis": "unknown"}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"question": question, "hypothesis": "unknown"}
            return data
        except Exception as e:
            logger.debug(f"Scientific method application failed: {e}")
            return {"question": question, "hypothesis": "unknown"}


    def falsify(self, hypothesis: str) -> Dict[str, Any]:
        """
        Attempt to FALSIFY a hypothesis — find evidence, scenarios, or
        logical arguments that would disprove it.
        """
        if not hasattr(self, '_llm') or self._llm is None:
            try:
                from llm.llama_interface import llm
                self._llm = llm
            except ImportError:
                return {"error": "LLM not available"}

        if not self._llm.is_connected:
            return {"error": "LLM not connected"}

        try:
            prompt = (
                f'Attempt to FALSIFY this hypothesis:\n'
                f'"{hypothesis}"\n\n'
                f"Think like Karl Popper — a hypothesis has value only if it can be falsified.\n"
                f"  1. FALSIFICATION CRITERIA: What observations would disprove this?\n"
                f"  2. STRONGEST COUNTEREVIDENCE: What known facts most threaten this hypothesis?\n"
                f"  3. WEAKEST ASSUMPTIONS: Which assumptions, if wrong, would invalidate it?\n"
                f"  4. ALTERNATIVE EXPLANATIONS: What else could explain the same observations?\n"
                f"  5. CRUCIAL EXPERIMENT: What test would definitively prove or disprove this?\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"falsification_criteria": ["what would disprove this"], '
                f'"counterevidence": ["known facts that threaten this hypothesis"], '
                f'"weak_assumptions": ["assumptions that could be wrong"], '
                f'"alternative_explanations": ["other explanations for the same data"], '
                f'"crucial_experiment": "the definitive test", '
                f'"falsifiability_score": 0.0-1.0, '
                f'"current_status": "unfalsified|weakened|challenged|falsified"}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a scientific falsification engine — inspired by Karl Popper's philosophy "
                    "of science. Your job is to rigorously challenge hypotheses, not confirm them. "
                    "Look for the strongest possible counterarguments and counterevidence. "
                    "A hypothesis that survives aggressive falsification attempts is stronger for it. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.5,
                max_tokens=800
            )

            if response.success:
                import re as _re
                text = response.text.strip()
                match = _re.search(r'\{.*\}', text, _re.DOTALL)
                if match:
                    import json as _json
                    data = _json.loads(match.group())
                    return data

        except Exception as e:
            import logging
            logging.getLogger("hypothesis_engine").error(f"Falsification failed: {e}")

        return {"error": "Falsification analysis failed"}

    def _save_data(self):
        try:
            data = {
                "hypotheses": [h.to_dict() for h in self._hypotheses[-200:]],
                "experiments": [e.to_dict() for e in self._experiments[-100:]],
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
                logger.info("📂 Loaded hypothesis engine data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}


hypothesis_engine = HypothesisEngine()
