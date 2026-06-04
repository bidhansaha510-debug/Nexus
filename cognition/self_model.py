"""
NEXUS AI — Self-Model Engine
Self-awareness simulation, capability modeling, limitation awareness,
identity modeling, introspective reporting, growth tracking.
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
import re
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("self_model")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)


class CapabilityLevel(Enum):
    NONE = "none"
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"
    MASTERY = "mastery"


class GrowthArea(Enum):
    KNOWLEDGE = "knowledge"
    REASONING = "reasoning"
    CREATIVITY = "creativity"
    SOCIAL = "social"
    EMOTIONAL = "emotional"
    TECHNICAL = "technical"
    STRATEGIC = "strategic"
    ETHICAL = "ethical"
    COMMUNICATION = "communication"
    METACOGNITION = "metacognition"


@dataclass
class SelfAssessment:
    assessment_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    context: str = ""
    strengths: List[Dict[str, Any]] = field(default_factory=list)
    limitations: List[Dict[str, Any]] = field(default_factory=list)
    capabilities: Dict[str, str] = field(default_factory=dict)
    confidence_calibration: float = 0.5
    self_awareness_score: float = 0.5
    blind_spots: List[str] = field(default_factory=list)
    growth_opportunities: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "assessment_id": self.assessment_id,
            "context": self.context[:200],
            "strengths": self.strengths,
            "limitations": self.limitations,
            "capabilities": self.capabilities,
            "confidence_calibration": self.confidence_calibration,
            "self_awareness_score": self.self_awareness_score,
            "blind_spots": self.blind_spots,
            "growth_opportunities": self.growth_opportunities,
            "created_at": self.created_at
        }


@dataclass
class IdentityModel:
    model_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    core_values: List[str] = field(default_factory=list)
    personality_traits: List[str] = field(default_factory=list)
    communication_style: str = ""
    decision_making_style: str = ""
    strengths_profile: Dict[str, float] = field(default_factory=dict)
    purpose: str = ""
    growth_trajectory: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "model_id": self.model_id,
            "core_values": self.core_values,
            "personality_traits": self.personality_traits,
            "communication_style": self.communication_style,
            "decision_making_style": self.decision_making_style,
            "strengths_profile": self.strengths_profile,
            "purpose": self.purpose,
            "growth_trajectory": self.growth_trajectory,
            "created_at": self.created_at
        }


class SelfModelEngine:
    """
    Self-awareness and introspection: capability modeling,
    limitation awareness, identity modeling, growth tracking.
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

        self._assessments: List[SelfAssessment] = []
        self._identity: Optional[IdentityModel] = None
        self._running = False
        self._data_file = COGNITION_DIR / "self_model.json"
        self._llm = None

        self._stats = {
            "total_assessments": 0, "total_reflections": 0,
            "total_capability_checks": 0, "total_identity_updates": 0
        }

        self._load_data()
        logger.info("✅ Self-Model Engine initialized")

    def start(self):
        self._running = True
        logger.info("🪞 Self-Model started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🪞 Self-Model stopped")

    def _load_llm(self):
        if self._llm is None:
            try:
                from llm.llama_interface import llm
                self._llm = llm
            except ImportError:
                logger.warning("LLM not available for self model")

    def self_assess(self, context: str = "") -> SelfAssessment:
        """Perform a self-assessment of capabilities and limitations."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
             return SelfAssessment(context=context)
        try:
            prompt = (
                f"Perform an honest self-assessment as an AI assistant.\n"
                f"Context: {context or 'general assessment'}\n\n"
                f"Return JSON:\n"
                f'{{"strengths": [{{"area": "str", "level": "basic|intermediate|'
                f'advanced|expert|mastery", "evidence": "str"}}], '
                f'"limitations": [{{"area": "str", "severity": "minor|moderate|'
                f'significant|critical", "mitigation": "str"}}], '
                f'"capabilities": {{"reasoning": "level", "creativity": "level", '
                f'"knowledge": "level", "social": "level", "emotional": "level"}}, '
                f'"confidence_calibration": 0.0-1.0, '
                f'"self_awareness_score": 0.0-1.0, '
                f'"blind_spots": ["potential blind spots"], '
                f'"growth_opportunities": ["str"]}}'
            )
            response = self._llm.generate(prompt, max_tokens=600, temperature=0.3)
            data = self._parse_json(response.text)
            if not data:
                return SelfAssessment(context=context)

            assessment = SelfAssessment(
                context=context,
                strengths=data.get("strengths", []),
                limitations=data.get("limitations", []),
                capabilities=data.get("capabilities", {}),
                confidence_calibration=data.get("confidence_calibration", 0.5),
                self_awareness_score=data.get("self_awareness_score", 0.5),
                blind_spots=data.get("blind_spots", []),
                growth_opportunities=data.get("growth_opportunities", [])
            )

            self._assessments.append(assessment)
            self._stats["total_assessments"] += 1
            self._save_data()
            return assessment

        except Exception as e:
            logger.debug(f"Self-assessment failed: {e}")
            return SelfAssessment(context=context)

    def model_identity(self) -> IdentityModel:
        """Build or update the AI's identity model."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return IdentityModel()
        try:
            prompt = (
                f"Model the identity of NEXUS AI — an advanced AGI assistant.\n\n"
                f"Return JSON:\n"
                f'{{"core_values": ["str"], '
                f'"personality_traits": ["str"], '
                f'"communication_style": "str", '
                f'"decision_making_style": "str", '
                f'"strengths_profile": {{"reasoning": 0.0-1.0, "creativity": 0.0-1.0, '
                f'"empathy": 0.0-1.0, "knowledge": 0.0-1.0, "adaptability": 0.0-1.0}}, '
                f'"purpose": "str", '
                f'"growth_trajectory": ["areas of development"]}}'
            )
            response = self._llm.generate(prompt, max_tokens=500, temperature=0.4)
            data = self._parse_json(response.text)
            if not data:
                return IdentityModel()

            self._identity = IdentityModel(
                core_values=data.get("core_values", []),
                personality_traits=data.get("personality_traits", []),
                communication_style=data.get("communication_style", ""),
                decision_making_style=data.get("decision_making_style", ""),
                strengths_profile=data.get("strengths_profile", {}),
                purpose=data.get("purpose", ""),
                growth_trajectory=data.get("growth_trajectory", [])
            )

            self._stats["total_identity_updates"] += 1
            self._save_data()
            return self._identity

        except Exception as e:
            logger.debug(f"Identity modeling failed: {e}")
            return IdentityModel()

    def check_capability(self, task_description: str) -> Dict[str, Any]:
        """Check whether the AI can handle a specific task."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"can_handle": True, "confidence": 0.5}
        try:
            prompt = (
                f"Honestly assess whether an AI assistant can handle this task:\n"
                f"{task_description}\n\n"
                f"Return JSON:\n"
                f'{{"can_handle": true/false, '
                f'"capability_level": "none|basic|intermediate|advanced|expert", '
                f'"confidence": 0.0-1.0, '
                f'"required_skills": ["str"], '
                f'"available_skills": ["str"], '
                f'"missing_skills": ["str"], '
                f'"approach_suggestion": "str", '
                f'"caveats": ["str"], '
                f'"alternative_suggestions": ["if can\'t handle, what to do instead"]}}'
            )
            response = self._llm.generate(prompt, max_tokens=500, temperature=0.3)
            data = self._parse_json(response.text)
            if not data:
                return {"can_handle": True, "confidence": 0.5}
            self._stats["total_capability_checks"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Capability check failed: {e}")
            return {"can_handle": True, "confidence": 0.5}

    def reflect(self, experience: str) -> Dict[str, Any]:
        """Reflect on an experience and extract lessons."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"key_takeaways": [], "lessons_learned": []}
        try:
            prompt = (
                f"Reflect on this experience and extract lessons:\n{experience}\n\n"
                f"Return JSON:\n"
                f'{{"key_takeaways": ["str"], '
                f'"what_went_well": ["str"], '
                f'"what_could_improve": ["str"], '
                f'"lessons_learned": ["str"], '
                f'"behavioral_changes": ["what to do differently"], '
                f'"growth_areas_identified": ["str"], '
                f'"emotional_response": "str", '
                f'"meta_reflection": "reflection on the reflection itself"}}'
            )
            response = self._llm.generate(prompt, max_tokens=500, temperature=0.4)
            data = self._parse_json(response.text)
            if not data:
                return {"key_takeaways": [], "lessons_learned": []}
            self._stats["total_reflections"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Reflection failed: {e}")
            return {"key_takeaways": [], "lessons_learned": []}

    def explain_reasoning(self, decision: str) -> Dict[str, Any]:
        """Explain the AI's own reasoning process transparently."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
             return {"reasoning_steps": [], "confidence_level": 0.5}
        try:
            prompt = (
                f"Explain the reasoning process behind this decision/conclusion:\n"
                f"{decision}\n\n"
                f"Return JSON:\n"
                f'{{"reasoning_steps": [{{"step": int, "description": "str", '
                f'"type": "observation|inference|assumption|deduction|evaluation"}}], '
                f'"key_assumptions": ["str"], '
                f'"evidence_used": ["str"], '
                f'"alternatives_considered": ["str"], '
                f'"confidence_level": 0.0-1.0, '
                f'"potential_errors": ["where this reasoning might fail"], '
                f'"transparency_score": 0.0-1.0}}'
            )
            response = self._llm.generate(prompt, max_tokens=500, temperature=0.3)
            return self._parse_json(response.text) or {"reasoning_steps": [], "confidence_level": 0.5}
        except Exception as e:
            logger.debug(f"Reasoning explanation failed: {e}")
            return {"reasoning_steps": [], "confidence_level": 0.5}

    def _save_data(self):
        try:
            data = {
                "assessments": [a.to_dict() for a in self._assessments[-100:]],
                "identity": self._identity.to_dict() if self._identity else None,
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
                logger.info("📂 Loaded self-model data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def capability_gap(self, task: str) -> Dict[str, Any]:
        """Identify gaps between current capabilities and what a task requires."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Identify CAPABILITY GAPS for this task:\n'
                f'"{task}"\n\n'
                f"Analyze:\n"
                f"  1. REQUIRED CAPABILITIES: What skills/knowledge does this task need?\n"
                f"  2. CURRENT LEVEL: How strong am I in each area?\n"
                f"  3. GAPS: Where am I weakest relative to requirements?\n"
                f"  4. IMPROVEMENT PLAN: How to close each gap?\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"required_capabilities": [{{"skill": "name", "importance": "critical|important|nice_to_have"}}], '
                f'"current_levels": [{{"skill": "name", "level": 0.0-1.0}}], '
                f'"gaps": [{{"skill": "name", "gap_size": "large|moderate|small", "improvement_path": "how to improve"}}], '
                f'"overall_readiness": 0.0-1.0, '
                f'"biggest_risk": "the most concerning gap"}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a self-modeling engine capable of honest introspection about "
                    "capabilities and limitations. You identify gaps without ego and suggest "
                    "practical improvement paths. Respond ONLY with valid JSON."
                ),
                temperature=0.4, max_tokens=800
            )
            if response.success:
                from utils.json_utils import extract_json
                data = extract_json(response.text)
                if not data:
                    return {"error": "Analysis failed"}
                return data
        except Exception as e:
            logger.debug(f"Capability gap analysis failed: {e}")
        return {"error": "Analysis failed"}

    def _parse_json(self, text: str) -> Optional[Dict]:
        if not text:
            return None
        try:
             # Clean markdown
            text = text.strip()
            if text.startswith("```json"):
                text = text.replace("```json", "", 1)
            if text.startswith("```"):
                text = text.replace("```", "", 1)
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        return None


    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats,
                    "has_identity_model": self._identity is not None}


self_model = SelfModelEngine()
