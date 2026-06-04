"""
NEXUS AI — Social Cognition Engine
Group dynamics, social norms modeling, cooperation/competition,
trust networks, persuasion detection, social influence.
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

logger = get_logger("social_cognition")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)


class SocialDynamic(Enum):
    COOPERATION = "cooperation"
    COMPETITION = "competition"
    CONFLICT = "conflict"
    NEGOTIATION = "negotiation"
    PERSUASION = "persuasion"
    CONFORMITY = "conformity"
    LEADERSHIP = "leadership"
    FOLLOWSHIP = "followship"
    COLLABORATION = "collaboration"
    OSTRACISM = "ostracism"


class InfluenceTactic(Enum):
    RECIPROCITY = "reciprocity"
    COMMITMENT = "commitment"
    SOCIAL_PROOF = "social_proof"
    AUTHORITY = "authority"
    LIKING = "liking"
    SCARCITY = "scarcity"
    UNITY = "unity"
    FEAR_APPEAL = "fear_appeal"
    FLATTERY = "flattery"
    LOGICAL_APPEAL = "logical_appeal"


@dataclass
class SocialAnalysis:
    analysis_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    situation: str = ""
    actors: List[Dict[str, Any]] = field(default_factory=list)
    dynamics: List[str] = field(default_factory=list)
    power_structure: Dict[str, Any] = field(default_factory=dict)
    norms_at_play: List[str] = field(default_factory=list)
    influence_tactics: List[str] = field(default_factory=list)
    group_cohesion: float = 0.5
    conflict_level: float = 0.0
    predictions: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "analysis_id": self.analysis_id, "situation": self.situation[:200],
            "actors": self.actors, "dynamics": self.dynamics,
            "power_structure": self.power_structure,
            "norms_at_play": self.norms_at_play,
            "influence_tactics": self.influence_tactics,
            "group_cohesion": self.group_cohesion,
            "conflict_level": self.conflict_level,
            "predictions": self.predictions, "created_at": self.created_at
        }


@dataclass
class TrustAssessment:
    trust_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    entity: str = ""
    trust_level: float = 0.5
    competence_trust: float = 0.5
    benevolence_trust: float = 0.5
    integrity_trust: float = 0.5
    evidence: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "trust_id": self.trust_id, "entity": self.entity,
            "trust_level": self.trust_level,
            "competence_trust": self.competence_trust,
            "benevolence_trust": self.benevolence_trust,
            "integrity_trust": self.integrity_trust,
            "evidence": self.evidence, "risk_factors": self.risk_factors,
            "created_at": self.created_at
        }


class SocialCognitionEngine:
    """
    Models social dynamics, group behavior, influence tactics,
    trust relationships, and social norms.
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

        self._analyses: List[SocialAnalysis] = []
        self._trust_assessments: List[TrustAssessment] = []
        self._running = False
        self._data_file = COGNITION_DIR / "social_cognition.json"

        self._stats = {
            "total_analyses": 0, "total_trust_assessments": 0,
            "total_norm_evaluations": 0, "total_influence_detections": 0
        }

        self._load_data()
        logger.info("✅ Social Cognition Engine initialized")

    def start(self):
        self._running = True
        logger.info("👥 Social Cognition started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("👥 Social Cognition stopped")

    def analyze_social_situation(self, situation: str) -> SocialAnalysis:
        """Analyze social dynamics in a situation."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Analyze the social dynamics in this situation:\n{situation}\n\n"
                f"Return JSON:\n"
                f'{{"actors": [{{"name": "str", "role": "str", "goals": ["str"], "power": 0.0-1.0}}], '
                f'"dynamics": ["cooperation|competition|conflict|negotiation|persuasion|conformity|leadership"], '
                f'"power_structure": {{"type": "hierarchical|flat|distributed", "key_holder": "str"}}, '
                f'"norms_at_play": ["social norms"], '
                f'"influence_tactics": ["reciprocity|social_proof|authority|scarcity|liking|commitment"], '
                f'"group_cohesion": 0.0-1.0, "conflict_level": 0.0-1.0, '
                f'"predictions": ["likely outcomes"]}}'
            )
            response = llm.generate(prompt, max_tokens=700, temperature=0.4)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            analysis = SocialAnalysis(
                situation=situation,
                actors=data.get("actors", []),
                dynamics=data.get("dynamics", []),
                power_structure=data.get("power_structure", {}),
                norms_at_play=data.get("norms_at_play", []),
                influence_tactics=data.get("influence_tactics", []),
                group_cohesion=data.get("group_cohesion", 0.5),
                conflict_level=data.get("conflict_level", 0.0),
                predictions=data.get("predictions", [])
            )

            self._analyses.append(analysis)
            self._stats["total_analyses"] += 1
            self._save_data()
            return analysis

        except Exception as e:
            logger.debug(f"Social analysis failed: {e}")
            return SocialAnalysis(situation=situation)

    def assess_trust(self, entity: str, context: str = "") -> TrustAssessment:
        """Assess trustworthiness of an entity."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Assess the trustworthiness of: {entity}\nContext: {context}\n\n"
                f"Return JSON:\n"
                f'{{"trust_level": 0.0-1.0, "competence_trust": 0.0-1.0, '
                f'"benevolence_trust": 0.0-1.0, "integrity_trust": 0.0-1.0, '
                f'"evidence": ["supporting evidence"], '
                f'"risk_factors": ["risk factors"]}}'
            )
            response = llm.generate(prompt, max_tokens=400, temperature=0.3)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            ta = TrustAssessment(
                entity=entity,
                trust_level=data.get("trust_level", 0.5),
                competence_trust=data.get("competence_trust", 0.5),
                benevolence_trust=data.get("benevolence_trust", 0.5),
                integrity_trust=data.get("integrity_trust", 0.5),
                evidence=data.get("evidence", []),
                risk_factors=data.get("risk_factors", [])
            )

            self._trust_assessments.append(ta)
            self._stats["total_trust_assessments"] += 1
            self._save_data()
            return ta

        except Exception as e:
            logger.debug(f"Trust assessment failed: {e}")
            return TrustAssessment(entity=entity)

    def detect_influence(self, text: str) -> Dict[str, Any]:
        """Detect influence and persuasion tactics in text."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Detect influence and persuasion tactics in:\n{text}\n\n"
                f"Return JSON:\n"
                f'{{"tactics_detected": [{{"tactic": "str", "evidence": "str", '
                f'"effectiveness": 0.0-1.0, "ethical": true/false}}], '
                f'"manipulation_level": 0.0-1.0, '
                f'"target_vulnerabilities": ["str"], '
                f'"defense_strategies": ["str"]}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.3)
            if not response.success or not response.text:
                return {"tactics_detected": [], "manipulation_level": 0.0}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"tactics_detected": [], "manipulation_level": 0.0}
            self._stats["total_influence_detections"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Influence detection failed: {e}")
            return {"tactics_detected": [], "manipulation_level": 0.0}

    def evaluate_social_norm(self, action: str, context: str = "") -> Dict[str, Any]:
        """Evaluate whether an action conforms to social norms."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Evaluate this action against social norms:\n"
                f"Action: {action}\nContext: {context}\n\n"
                f"Return JSON:\n"
                f'{{"conformity_level": 0.0-1.0, '
                f'"norms_followed": ["str"], "norms_violated": ["str"], '
                f'"social_consequences": ["str"], '
                f'"cultural_sensitivity": 0.0-1.0, '
                f'"alternative_actions": ["socially better alternatives"]}}'
            )
            response = llm.generate(prompt, max_tokens=400, temperature=0.3)
            if not response.success or not response.text:
                return {"conformity_level": 0.5, "norms_followed": [], "norms_violated": []}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"conformity_level": 0.5, "norms_followed": [], "norms_violated": []}
            self._stats["total_norm_evaluations"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Social norm evaluation failed: {e}")
            return {"conformity_level": 0.5, "norms_followed": [], "norms_violated": []}

    def model_group_dynamics(self, group_description: str) -> Dict[str, Any]:
        """Model the dynamics of a group."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Model the group dynamics of:\n{group_description}\n\n"
                f"Return JSON:\n"
                f'{{"group_size_category": "dyad|small|medium|large|crowd", '
                f'"cohesion": 0.0-1.0, "groupthink_risk": 0.0-1.0, '
                f'"leadership_type": "str", '
                f'"communication_patterns": ["str"], '
                f'"potential_issues": ["str"], '
                f'"strengths": ["str"], '
                f'"optimization_suggestions": ["str"]}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            if not response.success or not response.text:
                return {"cohesion": 0.5, "groupthink_risk": 0.5}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"cohesion": 0.5, "groupthink_risk": 0.5}
            return data
        except Exception as e:
            logger.debug(f"Group dynamics modeling failed: {e}")
            return {"cohesion": 0.5, "groupthink_risk": 0.5}

    def _save_data(self):
        try:
            data = {
                "analyses": [a.to_dict() for a in self._analyses[-200:]],
                "trust_assessments": [t.to_dict() for t in self._trust_assessments[-200:]],
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
                logger.info("📂 Loaded social cognition data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def power_dynamics(self, situation: str) -> Dict[str, Any]:
        """Analyze the power dynamics and social hierarchies in a situation."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Analyze the POWER DYNAMICS in this situation:\n'
                f'"{situation}"\n\n'
                f"Examine:\n"
                f"  1. ACTORS: Who holds power and what kind?\n"
                f"  2. POWER SOURCES: Formal authority, expertise, information, social capital\n"
                f"  3. DYNAMICS: How does power flow and shift?\n"
                f"  4. HIDDEN POWER: Who has influence that is not obvious?\n"
                f"  5. LEVERAGE: How can power be gained or shared more equitably?\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"actors": [{{"name": "who", "power_type": "formal|expert|informational|social", "level": "high|medium|low"}}], '
                f'"power_flows": ["how power moves between actors"], '
                f'"hidden_influences": ["non-obvious power holders"], '
                f'"leverage_points": ["how to shift the balance"], '
                f'"confidence": 0.0-1.0}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a social dynamics analyst with expertise in organizational behavior, "
                    "political science, and sociology. You identify visible and hidden power structures "
                    "with precision. Respond ONLY with valid JSON."
                ),
                temperature=0.5, max_tokens=800
            )
            if response.success:
                from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"error": "Analysis failed"}
            return data
        except Exception as e:
            logger.debug(f"Power dynamics analysis failed: {e}")
        return {"error": "Analysis failed"}


    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}


social_cognition = SocialCognitionEngine()