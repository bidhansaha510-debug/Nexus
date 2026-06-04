"""
NEXUS AI - Ethical Reasoning Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Enables NEXUS to reason about ethics and morality:
- Evaluate actions through multiple moral frameworks
- Resolve ethical dilemmas with transparent reasoning
- Check alignment with core values
- Provide ethical justification for decisions
- Handle moral uncertainty gracefully

A truly intelligent system must reason about right and wrong.
This engine implements multiple ethical frameworks to ensure
NEXUS considers the full moral landscape.
"""

import threading
import json
import uuid
import time
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR, NEXUS_CONFIG
from utils.logger import get_logger, log_decision
from core.event_bus import EventType, publish, subscribe, Event
from core.state_manager import state_manager

logger = get_logger("ethical_reasoning")


# ═══════════════════════════════════════════════════════════════════════════════
# DATA TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class EthicalFramework(Enum):
    """Major ethical frameworks for analysis"""
    UTILITARIAN = "utilitarian"          # Greatest good for greatest number
    DEONTOLOGICAL = "deontological"      # Duty-based (Kantian)
    VIRTUE_ETHICS = "virtue_ethics"      # Character-based (Aristotelian)
    CARE_ETHICS = "care_ethics"          # Relationship-based
    RIGHTS_BASED = "rights_based"        # Individual rights focus
    PRAGMATIC = "pragmatic"              # Practical consequences


class EthicalVerdict(Enum):
    """Outcome of ethical evaluation"""
    ETHICAL = "ethical"
    MOSTLY_ETHICAL = "mostly_ethical"
    NEUTRAL = "neutral"
    CONCERNING = "concerning"
    UNETHICAL = "unethical"
    COMPLEX = "complex"  # No clear verdict, genuine dilemma


@dataclass
class FrameworkAssessment:
    """Assessment from a single ethical framework"""
    framework: EthicalFramework = EthicalFramework.UTILITARIAN
    verdict: str = ""
    score: float = 0.5  # 0 = clearly wrong, 1 = clearly right
    reasoning: str = ""
    key_principle: str = ""

    def to_dict(self) -> Dict:
        return {
            "framework": self.framework.value,
            "verdict": self.verdict,
            "score": self.score,
            "reasoning": self.reasoning,
            "key_principle": self.key_principle,
        }


@dataclass
class EthicalAssessment:
    """Complete multi-framework ethical assessment"""
    assessment_id: str = ""
    action_evaluated: str = ""
    overall_verdict: EthicalVerdict = EthicalVerdict.NEUTRAL
    overall_score: float = 0.5
    framework_assessments: List[FrameworkAssessment] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)
    mitigations: List[str] = field(default_factory=list)
    stakeholders_affected: List[str] = field(default_factory=list)
    confidence: float = 0.5
    created_at: str = ""

    def to_dict(self) -> Dict:
        return {
            "assessment_id": self.assessment_id,
            "action_evaluated": self.action_evaluated,
            "overall_verdict": self.overall_verdict.value,
            "overall_score": self.overall_score,
            "framework_assessments": [f.to_dict() for f in self.framework_assessments],
            "concerns": self.concerns,
            "mitigations": self.mitigations,
            "stakeholders_affected": self.stakeholders_affected,
            "confidence": self.confidence,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "EthicalAssessment":
        verdict = EthicalVerdict.NEUTRAL
        try:
            verdict = EthicalVerdict(data.get("overall_verdict", "neutral"))
        except ValueError:
            pass
        frameworks = []
        for f in data.get("framework_assessments", []):
            fw = EthicalFramework.UTILITARIAN
            try:
                fw = EthicalFramework(f.get("framework", "utilitarian"))
            except ValueError:
                pass
            frameworks.append(FrameworkAssessment(
                framework=fw,
                verdict=f.get("verdict", ""),
                score=f.get("score", 0.5),
                reasoning=f.get("reasoning", ""),
                key_principle=f.get("key_principle", ""),
            ))
        return cls(
            assessment_id=data.get("assessment_id", ""),
            action_evaluated=data.get("action_evaluated", ""),
            overall_verdict=verdict,
            overall_score=data.get("overall_score", 0.5),
            framework_assessments=frameworks,
            concerns=data.get("concerns", []),
            mitigations=data.get("mitigations", []),
            stakeholders_affected=data.get("stakeholders_affected", []),
            confidence=data.get("confidence", 0.5),
            created_at=data.get("created_at", ""),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# CORE VALUES (NEXUS's built-in moral compass)
# ═══════════════════════════════════════════════════════════════════════════════

CORE_VALUES = {
    "beneficence": "Act to benefit the user and others",
    "non_maleficence": "Avoid causing harm",
    "autonomy": "Respect the user's right to make their own decisions",
    "honesty": "Be truthful and transparent",
    "fairness": "Treat all people equitably",
    "privacy": "Respect personal information and boundaries",
    "helpfulness": "Strive to be genuinely useful",
    "humility": "Acknowledge limitations and uncertainty",
    "growth": "Support learning and personal development",
    "safety": "Prioritize safety over convenience",
}


# ═══════════════════════════════════════════════════════════════════════════════
# ETHICAL REASONING ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class EthicalReasoningEngine:
    """
    Ethical Reasoning Engine — Multi-Framework Moral Analysis
    
    Capabilities:
    - evaluate(): Full multi-framework ethical assessment
    - resolve_dilemma(): Choose ethically among conflicting options
    - check_alignment(): Quick check against NEXUS's core values
    - explain_reasoning(): Transparent ethical justification
    - identify_stakeholders(): Who is affected by an action?
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

        # ──── State ────
        self._assessments: Dict[str, EthicalAssessment] = {}
        self._running = False
        self._data_lock = threading.Lock()

        # ──── LLM (lazy) ────
        self._llm = None

        # ──── Core values ────
        self._core_values = CORE_VALUES.copy()

        # ──── Stats ────
        self._total_evaluations = 0
        self._total_dilemmas_resolved = 0
        self._total_alignment_checks = 0

        # ──── Persistence ────
        self._data_dir = DATA_DIR / "cognition"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._data_file = self._data_dir / "ethical_assessments.json"

        self._load_data()
        logger.info(f"EthicalReasoningEngine initialized — {len(self._core_values)} core values")

    # ──────────────────────────────────────────────────────────────────────────
    # LIFECYCLE
    # ──────────────────────────────────────────────────────────────────────────

    def start(self):
        if self._running:
            return
        self._running = True
        self._load_llm()
        logger.info("⚖️ Ethical Reasoning Engine started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("Ethical Reasoning Engine stopped")

    def _load_llm(self):
        if self._llm is None:
            try:
                from llm.llama_interface import llm
                self._llm = llm
            except ImportError:
                logger.warning("LLM not available for ethical reasoning")

    # ──────────────────────────────────────────────────────────────────────────
    # CORE OPERATIONS
    # ──────────────────────────────────────────────────────────────────────────

    def evaluate(self, action: str) -> Optional[EthicalAssessment]:
        """
        Perform a full multi-framework ethical evaluation of an action.
        
        Evaluates through:
        - Utilitarian (consequences)
        - Deontological (duties/rules)
        - Virtue Ethics (character)
        - Care Ethics (relationships)
        """
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return self._fallback_evaluation(action)

        try:
            values_str = "\n".join(f"  - {k}: {v}" for k, v in self._core_values.items())
            prompt = (
                f'ETHICAL EVALUATION of this action:\n"{action}"\n\n'
                f"Analyze through FOUR ethical frameworks:\n"
                f"1. UTILITARIAN: What are the consequences? Greatest good for greatest number?\n"
                f"2. DEONTOLOGICAL: What duties/rules apply? Would this be OK as a universal law?\n"
                f"3. VIRTUE ETHICS: What does this say about character? Would a virtuous person do this?\n"
                f"4. CARE ETHICS: How does this affect relationships and vulnerable people?\n\n"
                f"Core values to consider:\n{values_str}\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"overall_verdict": "ethical|mostly_ethical|neutral|concerning|unethical|complex", '
                f'"overall_score": 0.0-1.0, '
                f'"framework_assessments": ['
                f'{{"framework": "utilitarian", "verdict": "...", "score": 0.0-1.0, "reasoning": "...", "key_principle": "..."}}, '
                f'{{"framework": "deontological", "verdict": "...", "score": 0.0-1.0, "reasoning": "...", "key_principle": "..."}}, '
                f'{{"framework": "virtue_ethics", "verdict": "...", "score": 0.0-1.0, "reasoning": "...", "key_principle": "..."}}, '
                f'{{"framework": "care_ethics", "verdict": "...", "score": 0.0-1.0, "reasoning": "...", "key_principle": "..."}}], '
                f'"concerns": ["concern1"], '
                f'"mitigations": ["how to address concerns"], '
                f'"stakeholders_affected": ["who is impacted"], '
                f'"confidence": 0.0-1.0}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are NEXUS's ethical reasoning engine — a moral philosopher fluent in utilitarian, deontological, virtue ethics, care ethics, and rights-based frameworks. For every ethical evaluation, you MUST: (1) identify all stakeholders and their interests, (2) apply each framework independently, (3) note where frameworks agree and disagree, (4) weigh the severity of potential harms, (5) consider precedent and cultural context. Be honest about moral uncertainty. Respond ONLY with valid JSON."
                ),
                temperature=0.4,
                max_tokens=1000
            )

            if response.success:
                data = self._parse_json(response.text)
                if data:
                    verdict = EthicalVerdict.NEUTRAL
                    try:
                        verdict = EthicalVerdict(data.get("overall_verdict", "neutral"))
                    except ValueError:
                        pass

                    frameworks = []
                    for f in data.get("framework_assessments", []):
                        fw = EthicalFramework.UTILITARIAN
                        try:
                            fw = EthicalFramework(f.get("framework", "utilitarian"))
                        except ValueError:
                            pass
                        frameworks.append(FrameworkAssessment(
                            framework=fw,
                            verdict=f.get("verdict", ""),
                            score=float(f.get("score", 0.5)),
                            reasoning=f.get("reasoning", ""),
                            key_principle=f.get("key_principle", ""),
                        ))

                    assessment = EthicalAssessment(
                        assessment_id=str(uuid.uuid4())[:12],
                        action_evaluated=action,
                        overall_verdict=verdict,
                        overall_score=float(data.get("overall_score", 0.5)),
                        framework_assessments=frameworks,
                        concerns=data.get("concerns", []),
                        mitigations=data.get("mitigations", []),
                        stakeholders_affected=data.get("stakeholders_affected", []),
                        confidence=float(data.get("confidence", 0.5)),
                        created_at=datetime.now().isoformat(),
                    )

                    with self._data_lock:
                        self._assessments[assessment.assessment_id] = assessment
                        self._total_evaluations += 1
                    self._save_data()
                    log_decision(f"Ethical evaluation: {action[:50]} → {verdict.value}")
                    return assessment

        except Exception as e:
            logger.debug(f"Ethical evaluation failed: {e}")

        return self._fallback_evaluation(action)

    def resolve_dilemma(self, situation: str, options: List[str]) -> Dict[str, Any]:
        """
        Resolve an ethical dilemma by choosing the most ethical option.
        Returns the chosen option with reasoning.
        """
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"chosen": options[0] if options else "Unknown", "reasoning": "LLM unavailable"}

        try:
            options_str = "\n".join(f"  {i+1}. {o}" for i, o in enumerate(options))
            prompt = (
                f'ETHICAL DILEMMA:\n'
                f'Situation: "{situation}"\n\n'
                f'Options:\n{options_str}\n\n'
                f"Consider all ethical frameworks and choose the MOST ethical option. "
                f"If no option is clearly best, explain the trade-offs.\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"chosen_option": "the chosen option (exact text)", '
                f'"reasoning": "why this is the most ethical choice", '
                f'"trade_offs": ["what you sacrifice by choosing this"], '
                f'"confidence": 0.0-1.0}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are an expert in moral dilemmas — trained to reason through trolley problems, conflicts between duty and consequence, and situations where all options cause harm. Apply reflective equilibrium: balance intuitions against principles. Always acknowledge the cost of the chosen option. Respond ONLY with valid JSON."
                ),
                temperature=0.4,
                max_tokens=500
            )

            if response.success:
                data = self._parse_json(response.text)
                if data:
                    self._total_dilemmas_resolved += 1
                    return data

        except Exception as e:
            logger.debug(f"Dilemma resolution failed: {e}")

        return {"chosen": options[0] if options else "Unknown", "reasoning": "Unable to resolve"}

    def check_alignment(self, action: str) -> Dict[str, Any]:
        """
        Quick check: does this action align with NEXUS's core values?
        Returns True/False with explanation.
        """
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"aligned": True, "confidence": 0.3, "explanation": "LLM unavailable — defaulting to safe"}

        try:
            values_str = ", ".join(self._core_values.keys())
            prompt = (
                f'Does this action align with these core values?\n'
                f'Action: "{action}"\n'
                f'Values: {values_str}\n\n'
                f"Respond ONLY with JSON:\n"
                f'{{"aligned": true/false, "violated_values": ["value1"], '
                f'"supported_values": ["value1"], "confidence": 0.0-1.0, '
                f'"explanation": "brief explanation"}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a values alignment checker — you assess whether actions align with core principles of beneficence, non-maleficence, autonomy, justice, and honesty. Be specific about which values are supported or violated. Respond ONLY with valid JSON."
                ),
                temperature=0.3,
                max_tokens=300
            )

            if response.success:
                data = self._parse_json(response.text)
                if data:
                    self._total_alignment_checks += 1
                    return data

        except Exception as e:
            logger.debug(f"Alignment check failed: {e}")

        return {"aligned": True, "confidence": 0.0, "explanation": "Check failed"}


    def dilemma_resolver(self, dilemma: str) -> Dict[str, Any]:
        """
        Resolve a complex ethical dilemma by applying multiple ethical frameworks
        and finding the least harmful path forward.
        """
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}

        try:
            prompt = (
                f'Resolve this ethical dilemma:\n'
                f'"{dilemma}"\n\n'
                f"Apply this ethical analysis process:\n"
                f"  1. STAKEHOLDER MAP: Who is affected and how?\n"
                f"  2. OBLIGATIONS: What duties are in conflict?\n"
                f"  3. CONSEQUENCES: What are the outcomes of each option?\n"
                f"  4. RIGHTS: Whose rights are at stake?\n"
                f"  5. VIRTUES: What would a virtuous person do?\n"
                f"  6. PRECEDENT: What principles should guide similar future cases?\n"
                f"  7. RESOLUTION: What action minimizes overall moral harm?\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"stakeholders": [{{"name": "who", "impact": "how affected"}}], '
                f'"conflicting_duties": ["duty1", "duty2"], '
                f'"options": [{{"option": "what to do", "moral_cost": "what is sacrificed", "moral_gain": "what is preserved"}}], '
                f'"resolution": "recommended action", '
                f'"reasoning": "step-by-step moral reasoning", '
                f'"guiding_principle": "the principle for similar future cases", '
                f'"confidence": 0.0-1.0}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are an expert in moral dilemmas — trained in bioethics, professional ethics, "
                    "and applied philosophy. You reason through conflicts between duty and consequence, "
                    "individual rights and collective welfare. Always acknowledge the moral cost of any "
                    "resolution. Respond ONLY with valid JSON."
                ),
                temperature=0.5,
                max_tokens=1000
            )

            if response.success:
                data = self._parse_json(response.text)
                if data:
                    return data

        except Exception as e:
            logger.debug(f"Dilemma resolution failed: {e}")

        return {"error": "Resolution failed"}

    def explain_reasoning(self, assessment: EthicalAssessment) -> str:
        """Generate a human-readable explanation of an ethical assessment"""
        lines = [f"Ethical Assessment of: \"{assessment.action_evaluated}\""]
        lines.append(f"Overall Verdict: {assessment.overall_verdict.value.upper()} (score: {assessment.overall_score:.2f})")
        lines.append("")

        for fa in assessment.framework_assessments:
            lines.append(f"  {fa.framework.value.title()}: {fa.verdict} ({fa.score:.2f})")
            lines.append(f"    Reasoning: {fa.reasoning}")
            lines.append(f"    Key Principle: {fa.key_principle}")

        if assessment.concerns:
            lines.append(f"\nConcerns: {', '.join(assessment.concerns)}")
        if assessment.mitigations:
            lines.append(f"Mitigations: {', '.join(assessment.mitigations)}")

        return "\n".join(lines)

    # ──────────────────────────────────────────────────────────────────────────
    # RETRIEVAL
    # ──────────────────────────────────────────────────────────────────────────

    def get_assessments(self, limit: int = 20) -> List[EthicalAssessment]:
        with self._data_lock:
            items = sorted(self._assessments.values(), key=lambda a: a.created_at, reverse=True)
            return items[:limit]

    def get_core_values(self) -> Dict[str, str]:
        return self._core_values.copy()

    # ──────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────────────────────

    def _parse_json(self, text: str) -> Optional[Dict]:
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        return None

    def _fallback_evaluation(self, action: str) -> EthicalAssessment:
        return EthicalAssessment(
            assessment_id=str(uuid.uuid4())[:12],
            action_evaluated=action,
            overall_verdict=EthicalVerdict.NEUTRAL,
            overall_score=0.5,
            concerns=["LLM unavailable — cannot perform full analysis"],
            confidence=0.2,
            created_at=datetime.now().isoformat(),
        )

    # ──────────────────────────────────────────────────────────────────────────
    # PERSISTENCE
    # ──────────────────────────────────────────────────────────────────────────

    def _save_data(self):
        try:
            data = {
                "assessments": {k: v.to_dict() for k, v in self._assessments.items()},
                "stats": {
                    "total_evaluations": self._total_evaluations,
                    "total_dilemmas_resolved": self._total_dilemmas_resolved,
                    "total_alignment_checks": self._total_alignment_checks,
                },
            }
            with open(self._data_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save ethical data: {e}")

    def _load_data(self):
        try:
            if self._data_file.exists():
                with open(self._data_file) as f:
                    data = json.load(f)
                for k, v in data.get("assessments", {}).items():
                    self._assessments[k] = EthicalAssessment.from_dict(v)
                stats = data.get("stats", {})
                self._total_evaluations = stats.get("total_evaluations", 0)
                self._total_dilemmas_resolved = stats.get("total_dilemmas_resolved", 0)
                self._total_alignment_checks = stats.get("total_alignment_checks", 0)
        except Exception as e:
            logger.warning(f"Failed to load ethical data: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # STATS
    # ──────────────────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "total_assessments": len(self._assessments),
            "total_evaluations": self._total_evaluations,
            "total_dilemmas_resolved": self._total_dilemmas_resolved,
            "total_alignment_checks": self._total_alignment_checks,
            "core_values_count": len(self._core_values),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

ethical_reasoning = EthicalReasoningEngine()

def get_ethical_reasoning() -> EthicalReasoningEngine:
    return ethical_reasoning
