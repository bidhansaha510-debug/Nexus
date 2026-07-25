"""
NEXUS AI — Emotional Intelligence Engine
Empathy modeling, emotional regulation strategies,
emotional contagion, EQ assessment, emotion coaching.
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

logger = get_logger("emotional_intelligence")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)

class EmpathyType(Enum):
    COGNITIVE = "cognitive"
    AFFECTIVE = "affective"
    COMPASSIONATE = "compassionate"

class RegulationStrategy(Enum):
    REAPPRAISAL = "reappraisal"
    SUPPRESSION = "suppression"
    DISTRACTION = "distraction"
    ACCEPTANCE = "acceptance"
    PROBLEM_SOLVING = "problem_solving"
    SEEKING_SUPPORT = "seeking_support"
    MINDFULNESS = "mindfulness"
    EXPRESSION = "expression"
    HUMOR = "humor"
    PHYSICAL_ACTIVITY = "physical_activity"

class EmotionalGranularity(Enum):
    BASIC = "basic"
    MODERATE = "moderate"
    NUANCED = "nuanced"
    EXPERT = "expert"

@dataclass
class EmpathyResponse:
    response_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    input_situation: str = ""
    detected_emotions: List[str] = field(default_factory=list)
    empathy_type: EmpathyType = EmpathyType.COGNITIVE
    understanding: str = ""
    validation: str = ""
    suggested_response: str = ""
    emotional_intensity: float = 0.5
    confidence: float = 0.5
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "response_id": self.response_id,
            "input_situation": self.input_situation[:200],
            "detected_emotions": self.detected_emotions,
            "empathy_type": self.empathy_type.value,
            "understanding": self.understanding,
            "validation": self.validation,
            "suggested_response": self.suggested_response,
            "emotional_intensity": self.emotional_intensity,
            "confidence": self.confidence, "created_at": self.created_at
        }

@dataclass
class RegulationPlan:
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    emotion: str = ""
    intensity: float = 0.5
    trigger: str = ""
    strategies: List[str] = field(default_factory=list)
    primary_strategy: str = ""
    coping_steps: List[str] = field(default_factory=list)
    long_term_suggestions: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "plan_id": self.plan_id, "emotion": self.emotion,
            "intensity": self.intensity, "trigger": self.trigger,
            "strategies": self.strategies,
            "primary_strategy": self.primary_strategy,
            "coping_steps": self.coping_steps,
            "long_term_suggestions": self.long_term_suggestions,
            "created_at": self.created_at
        }

@dataclass
class EQAssessment:
    assessment_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    context: str = ""
    self_awareness: float = 0.5
    self_regulation: float = 0.5
    motivation: float = 0.5
    empathy: float = 0.5
    social_skills: float = 0.5
    overall_eq: float = 0.5
    strengths: List[str] = field(default_factory=list)
    growth_areas: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "assessment_id": self.assessment_id, "context": self.context[:100],
            "self_awareness": self.self_awareness,
            "self_regulation": self.self_regulation,
            "motivation": self.motivation, "empathy": self.empathy,
            "social_skills": self.social_skills, "overall_eq": self.overall_eq,
            "strengths": self.strengths, "growth_areas": self.growth_areas,
            "created_at": self.created_at
        }

class EmotionalIntelligenceEngine:
    """
    Advanced emotional intelligence: empathy modeling, emotional regulation,
    EQ assessment, emotion coaching, and social-emotional understanding.
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

        self._empathy_responses: List[EmpathyResponse] = []
        self._regulation_plans: List[RegulationPlan] = []
        self._eq_assessments: List[EQAssessment] = []
        self._running = False
        self._data_file = COGNITION_DIR / "emotional_intelligence.json"

        self._stats = {
            "total_empathy_responses": 0, "total_regulation_plans": 0,
            "total_eq_assessments": 0, "total_coaching_sessions": 0
        }

        self._load_data()
        logger.info("✅ Emotional Intelligence Engine initialized")

    @staticmethod
    def _safe_parse_json(text: str) -> dict:
        import json
        if not text or not text.strip(): return {}
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try: return json.loads(cleaned[start:end + 1])
            except Exception: pass
        try: return json.loads(cleaned)
        except Exception: return {}

    def start(self):
        self._running = True
        logger.info("💗 Emotional Intelligence started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("💗 Emotional Intelligence stopped")

    def empathize(self, situation: str) -> EmpathyResponse:
        """Generate an empathetic response to a situation."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Provide a deeply empathetic analysis of this situation:\n{situation}\n\n"
                f"Return JSON:\n"
                f'{{"detected_emotions": ["str"], '
                f'"empathy_type": "cognitive|affective|compassionate", '
                f'"understanding": "what the person likely feels and why", '
                f'"validation": "validating statement", '
                f'"suggested_response": "empathetic response to give", '
                f'"emotional_intensity": 0.0-1.0, '
                f'"confidence": 0.0-1.0}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            if not response.text:
                raise ValueError("Empty response from LLM")
            try:
                if not response.success or not response.text:
                    return {}
                from utils.json_utils import extract_json
                data = extract_json(response.text)
                if not data:
                    return {}
            except json.JSONDecodeError:
                # Basic cleanup attempt
                text = response.text.replace("```json", "").replace("```", "").strip()
                if "{" in text:
                    text = text[text.find("{"):text.rfind("}")+1]
                data = json.loads(text)

            et_map = {e.value: e for e in EmpathyType}
            er = EmpathyResponse(
                input_situation=situation,
                detected_emotions=data.get("detected_emotions", []),
                empathy_type=et_map.get(data.get("empathy_type", "cognitive"), EmpathyType.COGNITIVE),
                understanding=data.get("understanding", ""),
                validation=data.get("validation", ""),
                suggested_response=data.get("suggested_response", ""),
                emotional_intensity=data.get("emotional_intensity", 0.5),
                confidence=data.get("confidence", 0.5)
            )

            self._empathy_responses.append(er)
            self._stats["total_empathy_responses"] += 1
            self._save_data()
            return er

        except Exception as e:
            logger.debug(f"Empathy generation failed: {e}")
            return EmpathyResponse(input_situation=situation)

    def regulate_emotion(self, emotion: str, intensity: float = 0.7,
                         trigger: str = "") -> RegulationPlan:
        """Create an emotional regulation plan."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Create an emotional regulation plan:\n"
                f"Emotion: {emotion} (intensity: {intensity})\n"
                f"Trigger: {trigger}\n\n"
                f"Return JSON:\n"
                f'{{"strategies": ["reappraisal|suppression|distraction|acceptance|'
                f'problem_solving|seeking_support|mindfulness|expression|humor"], '
                f'"primary_strategy": "str", '
                f'"coping_steps": ["concrete steps"], '
                f'"long_term_suggestions": ["str"], '
                f'"expected_relief_time": "str"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            if not response.text:
                raise ValueError("Empty response from LLM")
            try:
                if not response.success or not response.text:
                    return {}
                from utils.json_utils import extract_json
                data = extract_json(response.text)
                if not data:
                    return {}
            except json.JSONDecodeError:
                text = response.text.replace("```json", "").replace("```", "").strip()
                if "{" in text:
                    text = text[text.find("{"):text.rfind("}")+1]
                data = json.loads(text)

            plan = RegulationPlan(
                emotion=emotion, intensity=intensity, trigger=trigger,
                strategies=data.get("strategies", []),
                primary_strategy=data.get("primary_strategy", "acceptance"),
                coping_steps=data.get("coping_steps", []),
                long_term_suggestions=data.get("long_term_suggestions", [])
            )

            self._regulation_plans.append(plan)
            self._stats["total_regulation_plans"] += 1
            self._save_data()
            return plan

        except Exception as e:
            logger.debug(f"Emotion regulation failed: {e}")
            return RegulationPlan(emotion=emotion, intensity=intensity, trigger=trigger)

    def assess_eq(self, behavioral_context: str) -> EQAssessment:
        """Assess emotional quotient from behavioral context."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Assess the emotional intelligence demonstrated in:\n{behavioral_context}\n\n"
                f"Rate each EQ dimension 0-1:\n"
                f"Return JSON:\n"
                f'{{"self_awareness": 0.0-1.0, "self_regulation": 0.0-1.0, '
                f'"motivation": 0.0-1.0, "empathy": 0.0-1.0, '
                f'"social_skills": 0.0-1.0, '
                f'"strengths": ["str"], "growth_areas": ["str"]}}'
            )
            response = llm.generate(prompt, max_tokens=400, temperature=0.3)
            if not response.text:
                raise ValueError("Empty response from LLM")
            try:
                if not response.success or not response.text:
                    return {}
                from utils.json_utils import extract_json
                data = extract_json(response.text)
                if not data:
                    return {}
            except json.JSONDecodeError:
                text = response.text.replace("```json", "").replace("```", "").strip()
                if "{" in text:
                    text = text[text.find("{"):text.rfind("}")+1]
                data = json.loads(text)

            dims = ["self_awareness", "self_regulation", "motivation", "empathy", "social_skills"]
            scores = [data.get(d, 0.5) for d in dims]
            overall = sum(scores) / len(scores)

            eq = EQAssessment(
                context=behavioral_context,
                self_awareness=data.get("self_awareness", 0.5),
                self_regulation=data.get("self_regulation", 0.5),
                motivation=data.get("motivation", 0.5),
                empathy=data.get("empathy", 0.5),
                social_skills=data.get("social_skills", 0.5),
                overall_eq=overall,
                strengths=data.get("strengths", []),
                growth_areas=data.get("growth_areas", [])
            )

            self._eq_assessments.append(eq)
            self._stats["total_eq_assessments"] += 1
            self._save_data()
            return eq

        except Exception as e:
            logger.debug(f"EQ assessment failed: {e}")
            return EQAssessment(context=behavioral_context)

    def emotional_coaching(self, problem: str) -> Dict[str, Any]:
        """Provide emotional coaching for a problem."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Provide emotional coaching for:\n{problem}\n\n"
                f"Return JSON:\n"
                f'{{"emotional_root": "underlying emotional issue", '
                f'"current_pattern": "pattern being exhibited", '
                f'"healthier_alternative": "str", '
                f'"coaching_steps": ["actionable steps"], '
                f'"affirmations": ["positive affirmations"], '
                f'"resources": ["helpful resources or techniques"]}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            if not response.text:
                raise ValueError("Empty response from LLM")
            try:
                if not response.success or not response.text:
                    return {}
                from utils.json_utils import extract_json
                data = extract_json(response.text)
                if not data:
                    return {}
            except json.JSONDecodeError:
                text = response.text.replace("```json", "").replace("```", "").strip()
                if "{" in text:
                    text = text[text.find("{"):text.rfind("}")+1]
                data = json.loads(text)
            self._stats["total_coaching_sessions"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Emotional coaching failed: {e}")
            return {"emotional_root": "unknown", "coaching_steps": []}

    def analyze_emotional_dynamics(self, conversation: str) -> Dict[str, Any]:
        """Analyze emotional dynamics in a conversation or interaction."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Analyze the emotional dynamics in this interaction:\n{conversation}\n\n"
                f"Return JSON:\n"
                f'{{"emotional_trajectory": [{{"phase": "str", "emotions": ["str"], '
                f'"intensity": 0.0-1.0}}], '
                f'"emotional_contagion": "str", '
                f'"power_dynamics": "str", '
                f'"emotional_turning_points": ["str"], '
                f'"unspoken_emotions": ["str"], '
                f'"relationship_impact": "str"}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.4)
            if not response.text:
                return {"emotional_trajectory": [], "relationship_impact": "unknown"}
            try:
                if not response.success or not response.text:
                    return {"emotional_trajectory": [], "relationship_impact": "unknown"}
                data = extract_json(response.text)
                if not data:
                    return {"emotional_trajectory": [], "relationship_impact": "unknown"}
                return data
            except:
                return {"emotional_trajectory": [], "relationship_impact": "unknown"}
        except Exception as e:
            logger.debug(f"Emotional dynamics analysis failed: {e}")
            return {"emotional_trajectory": [], "relationship_impact": "unknown"}

    def _save_data(self):
        try:
            data = {
                "empathy_responses": [e.to_dict() for e in self._empathy_responses[-200:]],
                "regulation_plans": [r.to_dict() for r in self._regulation_plans[-100:]],
                "eq_assessments": [a.to_dict() for a in self._eq_assessments[-100:]],
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
                logger.info("📂 Loaded emotional intelligence data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def emotional_forecast(self, situation: str) -> Dict[str, Any]:
        """Predict emotional trajectory and suggest preemptive strategies."""
        try:
            from llm.llama_interface import llm

            prompt = (
                f'Predict the EMOTIONAL TRAJECTORY of this situation:\n'
                f'"{situation}"\n\n'
                f"Think through:\n"
                f"  1. CURRENT EMOTIONAL STATE: What emotions are likely present now?\n"
                f"  2. TRIGGERS AHEAD: What upcoming events could shift emotions?\n"
                f"  3. TRAJECTORY: How will emotions evolve over time?\n"
                f"  4. RISK POINTS: When is emotional distress most likely?\n"
                f"  5. PREEMPTIVE STRATEGIES: What can be done NOW to improve the trajectory?\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"current_emotions": ["emotion1"], '
                f'"trajectory": [{{"timeframe": "soon/medium/later", "predicted_emotion": "emotion", "intensity": 0.0-1.0}}], '
                f'"risk_points": ["when distress is likely"], '
                f'"strategies": ["preemptive action"], '
                f'"confidence": 0.0-1.0}}'
            )
            response = llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are an emotional intelligence engine with deep expertise in affective "
                    "forecasting, emotional regulation, and psychological resilience. You predict "
                    "how emotions will evolve and suggest evidence-based preemptive strategies. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.5, max_tokens=800
            )
            if response.success:
                return extract_json(response.text)

        except Exception as e:
            logger.debug(f"Emotional forecast failed: {e}")
        return {"error": "Forecast failed"}

    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}

emotional_intelligence = EmotionalIntelligenceEngine()