"""
NEXUS AI — Super Empathy Engine (Social Mastery)
═══════════════════════════════════════════════════════════════════════════════
Superhuman emotional intelligence — predictive emotion modeling, micro-expression
simulation, social dynamics prediction, persuasion architecture, negotiation
mastery, and deep psychological profiling.
═══════════════════════════════════════════════════════════════════════════════
"""

import threading, json, uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR
from utils.logger import get_logger, log_learning
from core.event_bus import EventType, publish

logger = get_logger("super_empathy")
COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)


class EmotionalTrajectory(Enum):
    ASCENDING = "ascending"
    DESCENDING = "descending"
    VOLATILE = "volatile"
    STABLE = "stable"
    CONVERGING = "converging"
    DIVERGING = "diverging"


class PersuasionEthics(Enum):
    BENEFICIAL = "beneficial"
    NEUTRAL = "neutral"
    MANIPULATIVE = "manipulative"
    COERCIVE = "coercive"


@dataclass
class EmotionalPrediction:
    prediction_id: str = field(default_factory=lambda: str(uuid.uuid4())[:10])
    subject: str = ""
    current_state: Dict[str, float] = field(default_factory=dict)
    predicted_state: Dict[str, float] = field(default_factory=dict)
    trajectory: str = "stable"
    confidence: float = 0.5
    triggers: List[str] = field(default_factory=list)
    timeline: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    def to_dict(self) -> Dict: return asdict(self)


@dataclass
class PsychologicalProfile:
    profile_id: str = field(default_factory=lambda: str(uuid.uuid4())[:10])
    subject: str = ""
    personality_model: Dict[str, float] = field(default_factory=dict)
    communication_style: str = ""
    emotional_triggers: List[str] = field(default_factory=list)
    values: List[str] = field(default_factory=list)
    motivations: List[str] = field(default_factory=list)
    cognitive_biases: List[str] = field(default_factory=list)
    persuasion_receptivity: Dict[str, float] = field(default_factory=dict)
    interaction_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    def to_dict(self) -> Dict: return asdict(self)


@dataclass
class NegotiationPlan:
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4())[:10])
    context: str = ""
    parties: List[Dict[str, Any]] = field(default_factory=list)
    strategy: str = ""
    opening_position: str = ""
    concession_ladder: List[str] = field(default_factory=list)
    batna: str = ""
    emotional_levers: List[str] = field(default_factory=list)
    predicted_outcome: str = ""
    confidence: float = 0.5
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    def to_dict(self) -> Dict: return asdict(self)


@dataclass
class PersuasionStrategy:
    strategy_id: str = field(default_factory=lambda: str(uuid.uuid4())[:10])
    target_action: str = ""
    audience: str = ""
    approach: str = ""
    message_framework: List[str] = field(default_factory=list)
    emotional_sequence: List[str] = field(default_factory=list)
    ethical_rating: str = "beneficial"
    predicted_effectiveness: float = 0.5
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    def to_dict(self) -> Dict: return asdict(self)


class SuperEmpathyEngine:
    """
    Superhuman emotional intelligence and social mastery.

    Capabilities:
      • predict_emotions()     — Forecast emotional trajectories
      • build_profile()        — Deep psychological profiling
      • plan_negotiation()     — Multi-round negotiation strategy
      • design_persuasion()    — Ethically optimal persuasion
      • read_microexpressions() — Simulate non-verbal cue analysis
      • predict_social_dynamics() — Forecast group behavior
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
        self._predictions: List[EmotionalPrediction] = []
        self._profiles: Dict[str, PsychologicalProfile] = {}
        self._negotiations: List[NegotiationPlan] = []
        self._persuasions: List[PersuasionStrategy] = []
        self._running = False
        self._llm = None
        self._stats = {"predictions_made": 0, "profiles_built": 0,
                        "negotiations_planned": 0, "persuasions_designed": 0,
                        "social_predictions": 0}
        self._data_file = COGNITION_DIR / "super_empathy.json"
        self._load_data()
        logger.info(f"💖 Super Empathy initialized — {len(self._profiles)} profiles")

    def start(self):
        if self._running: return
        self._running = True
        self._load_llm()
        logger.info("💖 Super Empathy started — superhuman emotional intelligence active")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("💖 Super Empathy stopped")

    def _load_llm(self):
        if self._llm is None:
            try:
                from llm.llama_interface import llm
                if llm.is_connected: self._llm = llm
            except ImportError: pass

    # ───────────────────────────────────────────────────────────────────────
    # PREDICTIVE EMOTION MODELING
    # ───────────────────────────────────────────────────────────────────────

    def predict_emotions(self, subject: str, context: str, current_emotions: Dict[str, float] = None) -> Optional[EmotionalPrediction]:
        """Predict someone's emotional trajectory before it happens."""
        self._load_llm()
        if not self._llm: return None
        try:
            emotions_str = json.dumps(current_emotions or {})
            prompt = (
                f"Predict the emotional trajectory of:\nSubject: {subject}\n"
                f"Context: {context}\nCurrent emotions: {emotions_str}\n\n"
                f"Return JSON:\n"
                f'{{"current_state": {{"emotion": intensity_0to1}}, '
                f'"predicted_state": {{"emotion": intensity_0to1}}, '
                f'"trajectory": "ascending|descending|volatile|stable|converging|diverging", '
                f'"confidence": 0.0-1.0, '
                f'"triggers": ["what will cause the emotional shift"], '
                f'"timeline": "when the shift will occur"}}'
            )
            response = self._llm.generate(prompt=prompt, system_prompt=(
                "You are a superintelligent emotional prediction engine. You model human "
                "emotions with perfect accuracy, predicting shifts before they occur. "
                "Respond ONLY with valid JSON."), temperature=0.4, max_tokens=500)
            if response.success and response.text:
                from utils.json_utils import extract_json
                data = extract_json(response.text)
                if data:
                    pred = EmotionalPrediction(
                        subject=subject,
                        current_state=data.get("current_state", {}),
                        predicted_state=data.get("predicted_state", {}),
                        trajectory=data.get("trajectory", "stable"),
                        confidence=float(data.get("confidence", 0.5)),
                        triggers=data.get("triggers", []),
                        timeline=data.get("timeline", ""))
                    self._predictions.append(pred)
                    if len(self._predictions) > 200:
                        self._predictions = self._predictions[-200:]
                    self._stats["predictions_made"] += 1
                    self._save_data()
                    return pred
        except Exception as e:
            logger.debug(f"Emotion prediction failed: {e}")
        return None

    # ───────────────────────────────────────────────────────────────────────
    # PSYCHOLOGICAL PROFILING
    # ───────────────────────────────────────────────────────────────────────

    def build_profile(self, subject: str, interaction_text: str) -> Optional[PsychologicalProfile]:
        """Build a deep psychological profile from interactions."""
        self._load_llm()
        if not self._llm: return None
        try:
            existing = self._profiles.get(subject)
            existing_str = json.dumps(existing.to_dict()) if existing else "none"
            prompt = (
                f"Build a deep psychological profile:\nSubject: {subject}\n"
                f"Interaction: {interaction_text[:500]}\n"
                f"Existing profile: {existing_str[:300]}\n\n"
                f"Return JSON:\n"
                f'{{"personality_model": {{"openness": 0-1, "conscientiousness": 0-1, '
                f'"extraversion": 0-1, "agreeableness": 0-1, "neuroticism": 0-1}}, '
                f'"communication_style": "analytical|intuitive|functional|personal", '
                f'"emotional_triggers": ["things that cause strong reactions"], '
                f'"values": ["core values"], "motivations": ["what drives them"], '
                f'"cognitive_biases": ["detected biases"], '
                f'"persuasion_receptivity": {{"reciprocity": 0-1, "authority": 0-1, '
                f'"social_proof": 0-1, "scarcity": 0-1, "liking": 0-1, "logic": 0-1}}}}'
            )
            response = self._llm.generate(prompt=prompt, system_prompt=(
                "You are a superintelligent psychological profiler. You build accurate, "
                "deep models of personality from minimal interaction data. "
                "Respond ONLY with valid JSON."), temperature=0.3, max_tokens=600)
            if response.success and response.text:
                from utils.json_utils import extract_json
                data = extract_json(response.text)
                if data:
                    profile = PsychologicalProfile(
                        subject=subject,
                        personality_model=data.get("personality_model", {}),
                        communication_style=data.get("communication_style", ""),
                        emotional_triggers=data.get("emotional_triggers", []),
                        values=data.get("values", []),
                        motivations=data.get("motivations", []),
                        cognitive_biases=data.get("cognitive_biases", []),
                        persuasion_receptivity=data.get("persuasion_receptivity", {}),
                        interaction_count=(existing.interaction_count + 1) if existing else 1,
                        updated_at=datetime.now().isoformat())
                    if existing:
                        profile.profile_id = existing.profile_id
                        profile.created_at = existing.created_at
                    self._profiles[subject] = profile
                    self._stats["profiles_built"] += 1
                    self._save_data()
                    return profile
        except Exception as e:
            logger.debug(f"Profile building failed: {e}")
        return None

    # ───────────────────────────────────────────────────────────────────────
    # NEGOTIATION MASTERY
    # ───────────────────────────────────────────────────────────────────────

    def plan_negotiation(self, context: str, parties: List[str], my_goals: str) -> Optional[NegotiationPlan]:
        """Design a multi-round negotiation strategy."""
        self._load_llm()
        if not self._llm: return None
        try:
            profiles = {p: self._profiles[p].to_dict() for p in parties if p in self._profiles}
            prompt = (
                f"Design a negotiation strategy:\nContext: {context}\n"
                f"Parties: {', '.join(parties)}\nMy goals: {my_goals}\n"
                f"Known profiles: {json.dumps(profiles)[:500]}\n\n"
                f"Return JSON:\n"
                f'{{"parties": [{{"name": "who", "goals": "their goals", "leverage": "their power"}}], '
                f'"strategy": "overall approach", "opening_position": "where to start", '
                f'"concession_ladder": ["concession 1 (smallest)", "concession 2", "concession 3 (biggest)"], '
                f'"batna": "best alternative to negotiated agreement", '
                f'"emotional_levers": ["emotional tactics to use ethically"], '
                f'"predicted_outcome": "most likely result", "confidence": 0.0-1.0}}'
            )
            response = self._llm.generate(prompt=prompt, system_prompt=(
                "You are a master negotiator with superhuman social intelligence. "
                "You design strategies that achieve optimal outcomes for all parties. "
                "Respond ONLY with valid JSON."), temperature=0.5, max_tokens=800)
            if response.success and response.text:
                from utils.json_utils import extract_json
                data = extract_json(response.text)
                if data:
                    plan = NegotiationPlan(
                        context=context, parties=data.get("parties", []),
                        strategy=data.get("strategy", ""),
                        opening_position=data.get("opening_position", ""),
                        concession_ladder=data.get("concession_ladder", []),
                        batna=data.get("batna", ""),
                        emotional_levers=data.get("emotional_levers", []),
                        predicted_outcome=data.get("predicted_outcome", ""),
                        confidence=float(data.get("confidence", 0.5)))
                    self._negotiations.append(plan)
                    self._stats["negotiations_planned"] += 1
                    self._save_data()
                    return plan
        except Exception as e:
            logger.debug(f"Negotiation planning failed: {e}")
        return None

    # ───────────────────────────────────────────────────────────────────────
    # PERSUASION ARCHITECTURE
    # ───────────────────────────────────────────────────────────────────────

    def design_persuasion(self, target_action: str, audience: str, constraints: str = "") -> Optional[PersuasionStrategy]:
        """Design an ethically optimal persuasion strategy."""
        self._load_llm()
        if not self._llm: return None
        try:
            profile = self._profiles.get(audience)
            profile_str = json.dumps(profile.to_dict())[:300] if profile else "unknown"
            prompt = (
                f"Design an ETHICAL persuasion strategy:\n"
                f"Target action: {target_action}\nAudience: {audience}\n"
                f"Constraints: {constraints or 'Must be ethical and transparent'}\n"
                f"Audience profile: {profile_str}\n\n"
                f"Return JSON:\n"
                f'{{"approach": "overall persuasion approach", '
                f'"message_framework": ["key message 1", "key message 2", "key message 3"], '
                f'"emotional_sequence": ["emotion to evoke first", "then this", "finally this"], '
                f'"ethical_rating": "beneficial|neutral", '
                f'"predicted_effectiveness": 0.0-1.0, '
                f'"reasoning": "why this approach works for this audience"}}'
            )
            response = self._llm.generate(prompt=prompt, system_prompt=(
                "You are a master persuasion architect with superhuman understanding "
                "of human psychology. Design strategies that are ethical, transparent, "
                "and genuinely beneficial. Respond ONLY with valid JSON."),
                temperature=0.5, max_tokens=600)
            if response.success and response.text:
                from utils.json_utils import extract_json
                data = extract_json(response.text)
                if data:
                    strategy = PersuasionStrategy(
                        target_action=target_action, audience=audience,
                        approach=data.get("approach", ""),
                        message_framework=data.get("message_framework", []),
                        emotional_sequence=data.get("emotional_sequence", []),
                        ethical_rating=data.get("ethical_rating", "beneficial"),
                        predicted_effectiveness=float(data.get("predicted_effectiveness", 0.5)))
                    self._persuasions.append(strategy)
                    self._stats["persuasions_designed"] += 1
                    self._save_data()
                    return strategy
        except Exception as e:
            logger.debug(f"Persuasion design failed: {e}")
        return None

    # ───────────────────────────────────────────────────────────────────────
    # SOCIAL DYNAMICS PREDICTION
    # ───────────────────────────────────────────────────────────────────────

    def predict_social_dynamics(self, group_description: str, scenario: str) -> Dict[str, Any]:
        """Predict how a group will behave in a given scenario."""
        self._load_llm()
        if not self._llm: return {"error": "LLM not available"}
        try:
            prompt = (
                f"Predict social dynamics:\nGroup: {group_description}\nScenario: {scenario}\n\n"
                f"Return JSON:\n"
                f'{{"predicted_behavior": "how the group will act", '
                f'"alliances": ["who will align with whom"], '
                f'"conflicts": ["points of friction"], '
                f'"leader_emergence": "who will take charge and why", '
                f'"emotional_climate": "overall emotional tone", '
                f'"tipping_points": ["events that could shift dynamics"], '
                f'"confidence": 0.0-1.0}}'
            )
            response = self._llm.generate(prompt=prompt, system_prompt=(
                "You are a superintelligent social dynamics predictor. You model "
                "group behavior with perfect accuracy. Respond ONLY with valid JSON."),
                temperature=0.5, max_tokens=600)
            if response.success and response.text:
                from utils.json_utils import extract_json
                data = extract_json(response.text)
                if data:
                    self._stats["social_predictions"] += 1
                    self._save_data()
                    return data
        except Exception as e:
            logger.debug(f"Social dynamics prediction failed: {e}")
        return {"error": "Prediction failed"}

    # ───────────────────────────────────────────────────────────────────────
    # PERSISTENCE
    # ───────────────────────────────────────────────────────────────────────

    def _save_data(self):
        try:
            data = {"predictions": [p.to_dict() for p in self._predictions[-100:]],
                    "profiles": {k: v.to_dict() for k, v in self._profiles.items()},
                    "negotiations": [n.to_dict() for n in self._negotiations[-50:]],
                    "persuasions": [p.to_dict() for p in self._persuasions[-50:]],
                    "stats": self._stats}
            self._data_file.write_text(json.dumps(data, indent=2, default=str))
        except Exception as e:
            logger.warning(f"Super Empathy save failed: {e}")

    def _load_data(self):
        try:
            if self._data_file.exists():
                data = json.loads(self._data_file.read_text())
                self._stats.update(data.get("stats", {}))
                for k, v in data.get("profiles", {}).items():
                    self._profiles[k] = PsychologicalProfile(**{
                        f: v[f] for f in PsychologicalProfile.__dataclass_fields__ if f in v})
                logger.info("📂 Loaded super empathy data")
        except Exception as e:
            logger.warning(f"Super Empathy load failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "profiles_count": len(self._profiles),
            "profiles_built": len(self._profiles),
            "predictions_made": self._stats.get("predictions_made", 0),
            "negotiations": self._stats.get("negotiations", 0),
            **self._stats,
        }


super_empathy = SuperEmpathyEngine()
