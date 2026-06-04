"""
NEXUS AI — Error Detection Engine
Identify inconsistencies, logical fallacies, bugs,
contradictions, and factual errors in reasoning.
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

logger = get_logger("error_detection")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)


class ErrorType(Enum):
    LOGICAL = "logical"
    FACTUAL = "factual"
    CONSISTENCY = "consistency"
    REASONING = "reasoning"
    MATHEMATICAL = "mathematical"
    GRAMMATICAL = "grammatical"
    SEMANTIC = "semantic"
    CAUSAL = "causal"


class Severity(Enum):
    TRIVIAL = "trivial"
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CRITICAL = "critical"


@dataclass
class DetectedError:
    error_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    content: str = ""
    error_type: ErrorType = ErrorType.LOGICAL
    severity: Severity = Severity.MINOR
    description: str = ""
    location: str = ""
    suggestion: str = ""
    confidence: float = 0.5
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "error_id": self.error_id, "content": self.content[:200],
            "error_type": self.error_type.value,
            "severity": self.severity.value,
            "description": self.description,
            "location": self.location,
            "suggestion": self.suggestion,
            "confidence": self.confidence,
            "created_at": self.created_at
        }


class ErrorDetectionEngine:
    """
    Find logical errors, inconsistencies, contradictions,
    and factual mistakes in text and reasoning.
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

        self._errors: List[DetectedError] = []
        self._running = False
        self._data_file = COGNITION_DIR / "error_detection.json"

        self._stats = {
            "total_checks": 0, "total_errors_found": 0,
            "total_fact_checks": 0, "total_consistency_checks": 0
        }

        self._load_data()
        logger.info("✅ Error Detection Engine initialized")

    def start(self):
        self._running = True
        logger.info("🔍 Error Detection started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🔍 Error Detection stopped")

    def detect_errors(self, text: str) -> Dict[str, Any]:
        """Scan text for all types of errors."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Thoroughly scan this text for any errors:\n{text}\n\n"
                f"Return JSON:\n"
                f'{{"errors": [{{"error_type": "logical|factual|consistency|reasoning|mathematical|grammatical|semantic|causal", '
                f'"severity": "trivial|minor|moderate|major|critical", '
                f'"description": "what the error is", '
                f'"location": "where in the text", '
                f'"suggestion": "how to fix it", '
                f'"confidence": 0.0-1.0}}], '
                f'"overall_quality": 0.0-1.0, '
                f'"error_count": 0, '
                f'"most_critical": "the most important error to fix"}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.2)
            if not response.success or not response.text.strip():
                logger.warning("LLM returned empty/failed response for error detection")
                return {"errors": [], "overall_quality": 0.0}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            for err_data in data.get("errors", []):
                et_map = {e.value: e for e in ErrorType}
                sv_map = {s.value: s for s in Severity}
                error = DetectedError(
                    content=text[:200],
                    error_type=et_map.get(err_data.get("error_type", "logical"), ErrorType.LOGICAL),
                    severity=sv_map.get(err_data.get("severity", "minor"), Severity.MINOR),
                    description=err_data.get("description", ""),
                    location=err_data.get("location", ""),
                    suggestion=err_data.get("suggestion", ""),
                    confidence=err_data.get("confidence", 0.5)
                )
                self._errors.append(error)

            self._stats["total_checks"] += 1
            self._stats["total_errors_found"] += len(data.get("errors", []))
            self._save_data()
            return data

        except Exception as e:
            logger.debug(f"Error detection failed: {e}")
            return {"errors": [], "overall_quality": 0.0}

    def fact_check(self, claim: str) -> Dict[str, Any]:
        """Fact-check a specific claim."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Fact-check this claim:\n{claim}\n\n"
                f"Return JSON:\n"
                f'{{"verdict": "true|mostly_true|mixed|mostly_false|false|unverifiable", '
                f'"confidence": 0.0-1.0, '
                f'"evidence_for": ["supporting evidence"], '
                f'"evidence_against": ["contradicting evidence"], '
                f'"nuances": ["important context or caveats"], '
                f'"corrected_statement": "more accurate version if needed", '
                f'"source_quality": "how verifiable this is"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.2)
            if not response.success or not response.text.strip():
                return {"verdict": "unverifiable", "confidence": 0.0}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"verdict": "unverifiable", "confidence": 0.0}
            self._stats["total_fact_checks"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Fact check failed: {e}")
            return {"verdict": "unverifiable", "confidence": 0.0}

    def check_consistency(self, statements: List[str]) -> Dict[str, Any]:
        """Check a set of statements for internal consistency."""
        try:
            from llm.llama_interface import llm
            stmt_text = "\n".join(f"- {s}" for s in statements)
            prompt = (
                f"Check these statements for internal consistency:\n{stmt_text}\n\n"
                f"Return JSON:\n"
                f'{{"is_consistent": true/false, '
                f'"contradictions": [{{"statement_a": "str", "statement_b": "str", '
                f'"nature_of_conflict": "str"}}], '
                f'"ambiguities": ["statements that could be interpreted multiple ways"], '
                f'"implicit_assumptions": ["unstated assumptions required for consistency"], '
                f'"consistency_score": 0.0-1.0}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.2)
            if not response.success or not response.text.strip():
                return {"is_consistent": True, "contradictions": []}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"is_consistent": True, "contradictions": []}
            self._stats["total_consistency_checks"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Consistency check failed: {e}")
            return {"is_consistent": True, "contradictions": []}

    def find_logical_fallacies(self, argument: str) -> Dict[str, Any]:
        """Identify logical fallacies in an argument."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Identify all logical fallacies in this argument:\n{argument}\n\n"
                f"Return JSON:\n"
                f'{{"fallacies": [{{"name": "str", "type": "formal|informal", '
                f'"description": "how it appears here", '
                f'"example_from_text": "the specific part", '
                f'"severity": 0.0-1.0}}], '
                f'"argument_strength": 0.0-1.0, '
                f'"steelman_version": "the strongest possible version of this argument", '
                f'"missing_evidence": ["what would make this argument stronger"]}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.2)
            if not response.success or not response.text.strip():
                return {"fallacies": [], "argument_strength": 0.0}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"fallacies": [], "argument_strength": 0.0}
            return data
        except Exception as e:
            logger.debug(f"Fallacy detection failed: {e}")
            return {"fallacies": [], "argument_strength": 0.0}

    def _save_data(self):
        try:
            data = {
                "errors": [e.to_dict() for e in self._errors[-300:]],
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
                logger.info("📂 Loaded error detection data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def premortem(self, plan: str) -> Dict[str, Any]:
        """Perform a premortem analysis -- imagine the plan has failed and work backwards."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Perform a PREMORTEM on this plan:\n'
                f'"{plan}"\n\n'
                f"Imagine it is 6 months from now and this plan has FAILED spectacularly.\n"
                f"  1. FAILURE MODES: What are the most likely reasons it failed?\n"
                f"  2. BLIND SPOTS: What did the planners not see?\n"
                f"  3. ASSUMPTION FAILURES: Which assumptions turned out to be wrong?\n"
                f"  4. EXTERNAL SHOCKS: What unexpected events derailed things?\n"
                f"  5. PREVENTIVE ACTIONS: What could have been done to prevent each failure?\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"failure_modes": [{{"failure": "what went wrong", "probability": 0.0-1.0, '
                f'"severity": "catastrophic|major|moderate|minor", '
                f'"preventive_action": "what to do now"}}], '
                f'"blind_spots": ["what is being overlooked"], '
                f'"assumption_risks": ["assumptions that could be wrong"], '
                f'"overall_risk_level": "high|medium|low"}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a premortem analysis engine -- you imagine failure and work backwards "
                    "to identify risks before they happen. You are trained in prospective hindsight, "
                    "which research shows dramatically improves risk identification. "
                    "Be thorough and honest about risks. Respond ONLY with valid JSON."
                ),
                temperature=0.5, max_tokens=900
            )
            if response.success:
                from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"error": "Premortem failed"}
            return data
        except Exception as e:
            logger.debug(f"Premortem failed: {e}")
        return {"error": "Premortem failed"}


    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}


error_detection = ErrorDetectionEngine()