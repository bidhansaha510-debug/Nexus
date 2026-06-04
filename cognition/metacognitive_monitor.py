"""
NEXUS AI — Metacognitive Monitor Engine
Monitors reasoning quality, calibrates confidence, detects cognitive biases,
and tracks epistemic humility (knowing what you don't know).
"""

import threading
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("metacognitive_monitor")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# DATA TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class BiasType(Enum):
    CONFIRMATION = "confirmation_bias"
    ANCHORING = "anchoring_bias"
    AVAILABILITY = "availability_bias"
    DUNNING_KRUGER = "dunning_kruger"
    SUNK_COST = "sunk_cost"
    BANDWAGON = "bandwagon_effect"
    RECENCY = "recency_bias"
    HALO = "halo_effect"
    FRAMING = "framing_effect"
    OVERCONFIDENCE = "overconfidence"
    HINDSIGHT = "hindsight_bias"
    NEGATIVITY = "negativity_bias"
    PROJECTION = "projection_bias"
    STATUS_QUO = "status_quo_bias"
    SURVIVORSHIP = "survivorship_bias"


class ReasoningQuality(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    ADEQUATE = "adequate"
    POOR = "poor"
    FLAWED = "flawed"


class ConfidenceLevel(Enum):
    CERTAIN = "certain"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    UNCERTAIN = "uncertain"
    NO_KNOWLEDGE = "no_knowledge"


@dataclass
class BiasDetection:
    bias_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    bias_type: BiasType = BiasType.CONFIRMATION
    context: str = ""
    evidence: List[str] = field(default_factory=list)
    severity: float = 0.5  # 0-1
    mitigation: str = ""
    detected_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "bias_id": self.bias_id, "bias_type": self.bias_type.value,
            "context": self.context, "evidence": self.evidence,
            "severity": self.severity, "mitigation": self.mitigation,
            "detected_at": self.detected_at
        }


@dataclass
class ReasoningAssessment:
    assessment_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    reasoning_text: str = ""
    quality: ReasoningQuality = ReasoningQuality.ADEQUATE
    confidence: ConfidenceLevel = ConfidenceLevel.MODERATE
    confidence_score: float = 0.5  # 0-1
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    biases_detected: List[BiasDetection] = field(default_factory=list)
    logical_coherence: float = 0.5
    evidence_quality: float = 0.5
    completeness: float = 0.5
    suggestions: List[str] = field(default_factory=list)
    knowledge_gaps: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "assessment_id": self.assessment_id,
            "reasoning_text": self.reasoning_text[:200],
            "quality": self.quality.value,
            "confidence": self.confidence.value,
            "confidence_score": self.confidence_score,
            "strengths": self.strengths, "weaknesses": self.weaknesses,
            "biases_detected": [b.to_dict() for b in self.biases_detected],
            "logical_coherence": self.logical_coherence,
            "evidence_quality": self.evidence_quality,
            "completeness": self.completeness,
            "suggestions": self.suggestions,
            "knowledge_gaps": self.knowledge_gaps,
            "created_at": self.created_at
        }


@dataclass
class ConfidenceCalibration:
    calibration_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    claim: str = ""
    predicted_confidence: float = 0.5
    actual_accuracy: Optional[float] = None
    calibration_error: float = 0.0
    domain: str = "general"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "calibration_id": self.calibration_id, "claim": self.claim,
            "predicted_confidence": self.predicted_confidence,
            "actual_accuracy": self.actual_accuracy,
            "calibration_error": self.calibration_error,
            "domain": self.domain, "created_at": self.created_at
        }


# ═══════════════════════════════════════════════════════════════════════════════
# METACOGNITIVE MONITOR ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class MetacognitiveMonitor:
    """
    Monitors and assesses reasoning quality, detects cognitive biases,
    calibrates confidence levels, and tracks knowledge boundaries.
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

        self._assessments: List[ReasoningAssessment] = []
        self._bias_history: List[BiasDetection] = []
        self._calibrations: List[ConfidenceCalibration] = []
        self._knowledge_boundaries: Dict[str, float] = {}
        self._running = False
        self._data_file = COGNITION_DIR / "metacognitive_monitor.json"

        self._stats = {
            "total_assessments": 0,
            "total_biases_detected": 0,
            "total_calibrations": 0,
            "avg_reasoning_quality": 0.0,
            "avg_confidence_calibration": 0.0,
            "most_common_bias": None
        }

        self._load_data()
        logger.info("✅ Metacognitive Monitor initialized")

    def start(self):
        self._running = True
        logger.info("🧠 Metacognitive Monitor started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🧠 Metacognitive Monitor stopped")

    # ─── Core Operations ─────────────────────────────────────────────────────

    def assess_reasoning(self, reasoning_text: str, context: str = "") -> ReasoningAssessment:
        """Assess the quality of a piece of reasoning."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Assess the quality of this reasoning. "
                f"Context: {context}\n"
                f"Reasoning: {reasoning_text}\n\n"
                f"Return JSON:\n"
                f'{{"quality": "excellent|good|adequate|poor|flawed", '
                f'"confidence_score": 0.0-1.0, '
                f'"logical_coherence": 0.0-1.0, '
                f'"evidence_quality": 0.0-1.0, '
                f'"completeness": 0.0-1.0, '
                f'"strengths": ["str"], '
                f'"weaknesses": ["str"], '
                f'"biases": ["bias_name"], '
                f'"knowledge_gaps": ["str"], '
                f'"suggestions": ["str"]}}'
            )
            response = llm.generate(prompt, max_tokens=800, temperature=0.3)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            quality_map = {q.value: q for q in ReasoningQuality}
            quality = quality_map.get(data.get("quality", "adequate"), ReasoningQuality.ADEQUATE)

            biases = []
            for b_name in data.get("biases", []):
                bias_map = {b.value: b for b in BiasType}
                bt = bias_map.get(b_name)
                if bt:
                    biases.append(BiasDetection(
                        bias_type=bt, context=reasoning_text[:100],
                        severity=0.5
                    ))

            cs = data.get("confidence_score", 0.5)
            if cs > 0.9:
                conf = ConfidenceLevel.CERTAIN
            elif cs > 0.75:
                conf = ConfidenceLevel.HIGH
            elif cs > 0.5:
                conf = ConfidenceLevel.MODERATE
            elif cs > 0.25:
                conf = ConfidenceLevel.LOW
            else:
                conf = ConfidenceLevel.UNCERTAIN

            assessment = ReasoningAssessment(
                reasoning_text=reasoning_text, quality=quality,
                confidence=conf, confidence_score=cs,
                strengths=data.get("strengths", []),
                weaknesses=data.get("weaknesses", []),
                biases_detected=biases,
                logical_coherence=data.get("logical_coherence", 0.5),
                evidence_quality=data.get("evidence_quality", 0.5),
                completeness=data.get("completeness", 0.5),
                suggestions=data.get("suggestions", []),
                knowledge_gaps=data.get("knowledge_gaps", [])
            )

            self._assessments.append(assessment)
            self._bias_history.extend(biases)
            self._stats["total_assessments"] += 1
            self._stats["total_biases_detected"] += len(biases)
            self._save_data()
            return assessment

        except Exception as e:
            logger.debug(f"Reasoning assessment failed: {e}")
            return ReasoningAssessment(
                reasoning_text=reasoning_text,
                quality=ReasoningQuality.ADEQUATE,
                suggestions=[f"Assessment failed: {e}"]
            )

    def detect_biases(self, text: str) -> List[BiasDetection]:
        """Detect cognitive biases in a piece of text."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Analyze this text for cognitive biases:\n{text}\n\n"
                f"For each bias found, return JSON array:\n"
                f'[{{"bias_type": "confirmation_bias|anchoring_bias|availability_bias|'
                f'dunning_kruger|sunk_cost|bandwagon_effect|recency_bias|halo_effect|'
                f'framing_effect|overconfidence|hindsight_bias|negativity_bias|'
                f'projection_bias|status_quo_bias|survivorship_bias", '
                f'"evidence": ["specific quote or pattern"], '
                f'"severity": 0.0-1.0, '
                f'"mitigation": "how to counter this bias"}}]'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.3)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            detections = []
            bias_map = {b.value: b for b in BiasType}
            for item in data:
                bt = bias_map.get(item.get("bias_type"))
                if bt:
                    det = BiasDetection(
                        bias_type=bt, context=text[:100],
                        evidence=item.get("evidence", []),
                        severity=item.get("severity", 0.5),
                        mitigation=item.get("mitigation", "")
                    )
                    detections.append(det)
                    self._bias_history.append(det)

            self._stats["total_biases_detected"] += len(detections)
            self._save_data()
            return detections

        except Exception as e:
            logger.debug(f"Bias detection failed: {e}")
            return []

    def calibrate_confidence(self, claim: str, domain: str = "general") -> ConfidenceCalibration:
        """Estimate calibrated confidence for a claim."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"How confident should one be in this claim? Domain: {domain}\n"
                f"Claim: {claim}\n\n"
                f"Return JSON:\n"
                f'{{"confidence": 0.0-1.0, '
                f'"reasoning": "brief explanation", '
                f'"key_uncertainties": ["str"]}}'
            )
            response = llm.generate(prompt, max_tokens=300, temperature=0.3)
            if not response.success or not response.text:
                return ConfidenceCalibration(claim=claim, predicted_confidence=0.5, domain=domain)
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return ConfidenceCalibration(claim=claim, predicted_confidence=0.5, domain=domain)

            cal = ConfidenceCalibration(
                claim=claim,
                predicted_confidence=data.get("confidence", 0.5),
                domain=domain
            )

            self._calibrations.append(cal)
            self._stats["total_calibrations"] += 1
            self._save_data()
            return cal

        except Exception as e:
            logger.debug(f"Confidence calibration failed: {e}")
            return ConfidenceCalibration(claim=claim, predicted_confidence=0.5, domain=domain)

    def identify_knowledge_gaps(self, topic: str) -> Dict[str, Any]:
        """Identify what is known vs unknown about a topic."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"For the topic '{topic}', identify:\n"
                f"1. What is well-known/established\n"
                f"2. What is partially known\n"
                f"3. What is unknown or uncertain\n"
                f"4. What I might be wrong about\n\n"
                f"Return JSON:\n"
                f'{{"well_known": ["str"], "partially_known": ["str"], '
                f'"unknown": ["str"], "potential_errors": ["str"], '
                f'"knowledge_confidence": 0.0-1.0}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            if not response.success or not response.text:
                return {"well_known": [], "unknown": ["Analysis failed: no response"],
                        "knowledge_confidence": 0.0}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"well_known": [], "unknown": ["Analysis failed: no data"],
                        "knowledge_confidence": 0.0}

            self._knowledge_boundaries[topic] = data.get("knowledge_confidence", 0.5)
            self._save_data()
            return data

        except Exception as e:
            logger.debug(f"Knowledge gap identification failed: {e}")
            return {"well_known": [], "unknown": [f"Analysis failed: {e}"],
                    "knowledge_confidence": 0.0}

    def evaluate_argument(self, argument: str) -> Dict[str, Any]:
        """Evaluate the strength of an argument."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Evaluate this argument for logical validity and soundness:\n"
                f"{argument}\n\n"
                f"Return JSON:\n"
                f'{{"validity": 0.0-1.0, "soundness": 0.0-1.0, '
                f'"premises_identified": ["str"], "conclusion": "str", '
                f'"logical_fallacies": ["str"], "missing_premises": ["str"], '
                f'"counterarguments": ["str"], "overall_strength": 0.0-1.0}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.3)
            if not response.success or not response.text:
                return {"validity": 0.5, "soundness": 0.5, "overall_strength": 0.5}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"validity": 0.5, "soundness": 0.5, "overall_strength": 0.5}
            return data
        except Exception as e:
            logger.debug(f"Argument evaluation failed: {e}")
            return {"validity": 0.5, "soundness": 0.5, "overall_strength": 0.5}

    # ─── Retrieval ────────────────────────────────────────────────────────────

    def get_recent_assessments(self, limit: int = 10) -> List[Dict]:
        return [a.to_dict() for a in self._assessments[-limit:]]

    def get_bias_summary(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for b in self._bias_history:
            counts[b.bias_type.value] = counts.get(b.bias_type.value, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))

    # ─── Persistence ──────────────────────────────────────────────────────────

    def _save_data(self):
        try:
            data = {
                "assessments": [a.to_dict() for a in self._assessments[-200:]],
                "bias_history": [b.to_dict() for b in self._bias_history[-500:]],
                "calibrations": [c.to_dict() for c in self._calibrations[-200:]],
                "knowledge_boundaries": self._knowledge_boundaries,
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
                self._knowledge_boundaries = data.get("knowledge_boundaries", {})
                logger.info(f"📂 Loaded metacognitive data ({self._stats['total_assessments']} assessments)")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            **self._stats,
            "knowledge_domains_tracked": len(self._knowledge_boundaries)
        }


# ─── Singleton ────────────────────────────────────────────────────────────────
metacognitive_monitor = MetacognitiveMonitor()
