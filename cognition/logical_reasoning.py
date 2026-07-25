"""
NEXUS AI — Logical Reasoning Engine
Deductive, inductive, and abductive logic; syllogisms;
argument validation; proof construction; fallacy detection.
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
from utils.json_utils import extract_json

logger = get_logger("logical_reasoning")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)

class LogicType(Enum):
    DEDUCTIVE = "deductive"
    INDUCTIVE = "inductive"
    ABDUCTIVE = "abductive"
    MODAL = "modal"
    FUZZY = "fuzzy"
    PROPOSITIONAL = "propositional"
    PREDICATE = "predicate"

class FallacyType(Enum):
    AD_HOMINEM = "ad_hominem"
    STRAW_MAN = "straw_man"
    FALSE_DILEMMA = "false_dilemma"
    SLIPPERY_SLOPE = "slippery_slope"
    APPEAL_TO_AUTHORITY = "appeal_to_authority"
    APPEAL_TO_EMOTION = "appeal_to_emotion"
    CIRCULAR_REASONING = "circular_reasoning"
    RED_HERRING = "red_herring"
    HASTY_GENERALIZATION = "hasty_generalization"
    FALSE_CAUSE = "false_cause"
    EQUIVOCATION = "equivocation"
    APPEAL_TO_IGNORANCE = "appeal_to_ignorance"
    BANDWAGON = "bandwagon"
    NO_TRUE_SCOTSMAN = "no_true_scotsman"
    TEXAS_SHARPSHOOTER = "texas_sharpshooter"
    LOADED_QUESTION = "loaded_question"
    TU_QUOQUE = "tu_quoque"
    COMPOSITION = "composition"
    DIVISION = "division"
    GENETIC = "genetic"

@dataclass
class LogicalArgument:
    argument_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    premises: List[str] = field(default_factory=list)
    conclusion: str = ""
    logic_type: LogicType = LogicType.DEDUCTIVE
    is_valid: bool = False
    is_sound: bool = False
    strength: float = 0.5
    fallacies: List[str] = field(default_factory=list)
    missing_premises: List[str] = field(default_factory=list)
    counterexamples: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "argument_id": self.argument_id, "premises": self.premises,
            "conclusion": self.conclusion, "logic_type": self.logic_type.value,
            "is_valid": self.is_valid, "is_sound": self.is_sound,
            "strength": self.strength, "fallacies": self.fallacies,
            "missing_premises": self.missing_premises,
            "counterexamples": self.counterexamples,
            "created_at": self.created_at
        }

@dataclass
class ProofStep:
    step_number: int = 0
    statement: str = ""
    justification: str = ""
    rule_applied: str = ""

    def to_dict(self) -> Dict:
        return {
            "step_number": self.step_number, "statement": self.statement,
            "justification": self.justification, "rule_applied": self.rule_applied
        }

@dataclass
class FallacyDetection:
    fallacy_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    text: str = ""
    fallacy_type: str = ""
    explanation: str = ""
    severity: float = 0.5
    fix_suggestion: str = ""

    def to_dict(self) -> Dict:
        return {
            "fallacy_id": self.fallacy_id, "text": self.text[:100],
            "fallacy_type": self.fallacy_type, "explanation": self.explanation,
            "severity": self.severity, "fix_suggestion": self.fix_suggestion
        }

class LogicalReasoningEngine:
    """
    Formal and informal logic: deductive/inductive/abductive reasoning,
    argument construction/validation, proof building, fallacy detection.
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

        self._arguments: List[LogicalArgument] = []
        self._fallacies: List[FallacyDetection] = []
        self._running = False
        self._data_file = COGNITION_DIR / "logical_reasoning.json"

        self._stats = {
            "total_arguments": 0, "total_proofs": 0,
            "total_fallacies_detected": 0, "total_validations": 0,
            "valid_arguments_pct": 0.0
        }

        self._load_data()
        logger.info("✅ Logical Reasoning Engine initialized")

    def start(self):
        self._running = True
        logger.info("🔗 Logical Reasoning started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🔗 Logical Reasoning stopped")

    def validate_argument(self, argument_text: str) -> LogicalArgument:
        """Validate a logical argument for validity, soundness, and fallacies."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Analyze this argument:\n{argument_text}\n\n"
                f"Return JSON:\n"
                f'{{"premises": ["str"], "conclusion": "str", '
                f'"logic_type": "deductive|inductive|abductive", '
                f'"is_valid": true/false, "is_sound": true/false, '
                f'"strength": 0.0-1.0, '
                f'"fallacies": ["fallacy name"], '
                f'"missing_premises": ["str"], '
                f'"counterexamples": ["str"]}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.3)
            data = extract_json(response.text) or {}
            
            if not data:
                 logger.debug(f"Failed to parse JSON from LLM: {response.text[:100]}")

            lt_map = {l.value: l for l in LogicType}

            arg = LogicalArgument(
                premises=data.get("premises", []),
                conclusion=data.get("conclusion", ""),
                logic_type=lt_map.get(data.get("logic_type", "deductive"), LogicType.DEDUCTIVE),
                is_valid=data.get("is_valid", False),
                is_sound=data.get("is_sound", False),
                strength=data.get("strength", 0.5),
                fallacies=data.get("fallacies", []),
                missing_premises=data.get("missing_premises", []),
                counterexamples=data.get("counterexamples", [])
            )

            self._arguments.append(arg)
            self._stats["total_arguments"] += 1
            self._stats["total_validations"] += 1
            self._save_data()
            return arg

        except Exception as e:
            logger.debug(f"Argument validation failed: {e}")
            return LogicalArgument(conclusion=argument_text)

    def construct_argument(self, claim: str, evidence: str = "") -> LogicalArgument:
        """Construct a logical argument for a claim."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Construct a strong logical argument for this claim:\n"
                f"Claim: {claim}\nAvailable evidence: {evidence}\n\n"
                f"Return JSON:\n"
                f'{{"premises": ["ordered premises"], "conclusion": "str", '
                f'"logic_type": "deductive|inductive|abductive", '
                f'"strength": 0.0-1.0, '
                f'"potential_objections": ["str"], '
                f'"rebuttals": ["str"]}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.4)
            data = extract_json(response.text) or {}

            lt_map = {l.value: l for l in LogicType}

            arg = LogicalArgument(
                premises=data.get("premises", []),
                conclusion=data.get("conclusion", claim),
                logic_type=lt_map.get(data.get("logic_type", "deductive"), LogicType.DEDUCTIVE),
                is_valid=True,
                strength=data.get("strength", 0.5)
            )

            self._arguments.append(arg)
            self._stats["total_arguments"] += 1
            self._save_data()
            return arg

        except Exception as e:
            logger.debug(f"Argument construction failed: {e}")
            return LogicalArgument(conclusion=claim)

    def detect_fallacies(self, text: str) -> List[FallacyDetection]:
        """Detect logical fallacies in text."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Detect all logical fallacies in this text:\n{text}\n\n"
                f"Return JSON array:\n"
                f'[{{"fallacy_type": "ad_hominem|straw_man|false_dilemma|slippery_slope|'
                f'appeal_to_authority|appeal_to_emotion|circular_reasoning|red_herring|'
                f'hasty_generalization|false_cause|equivocation|appeal_to_ignorance|'
                f'bandwagon|no_true_scotsman|loaded_question|tu_quoque|composition|division", '
                f'"explanation": "str", "severity": 0.0-1.0, '
                f'"fix_suggestion": "str"}}]'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.3)
            data = extract_json(response.text) or []
            
            if not isinstance(data, list):
                logger.warning("Fallacy detection returned non-list JSON")
                data = []

            detections = []
            for item in data:
                det = FallacyDetection(
                    text=text[:100],
                    fallacy_type=item.get("fallacy_type", "unknown"),
                    explanation=item.get("explanation", ""),
                    severity=item.get("severity", 0.5),
                    fix_suggestion=item.get("fix_suggestion", "")
                )
                detections.append(det)
                self._fallacies.append(det)

            self._stats["total_fallacies_detected"] += len(detections)
            self._save_data()
            return detections

        except Exception as e:
            logger.debug(f"Fallacy detection failed: {e}")
            return []

    def build_proof(self, statement: str, axioms: str = "") -> List[ProofStep]:
        """Construct a step-by-step logical proof."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Build a step-by-step logical proof for:\n"
                f"Statement: {statement}\nAxioms/Given: {axioms}\n\n"
                f"Return JSON:\n"
                f'{{"steps": [{{"step_number": 1, "statement": "str", '
                f'"justification": "str", "rule_applied": "str"}}], '
                f'"proof_complete": true/false, '
                f'"proof_type": "direct|contradiction|induction|cases"}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.3)
            data = extract_json(response.text) or {}

            steps = [ProofStep(
                step_number=s.get("step_number", i),
                statement=s.get("statement", ""),
                justification=s.get("justification", ""),
                rule_applied=s.get("rule_applied", "")
            ) for i, s in enumerate(data.get("steps", []), 1)]

            self._stats["total_proofs"] += 1
            self._save_data()
            return steps

        except Exception as e:
            logger.debug(f"Proof building failed: {e}")
            return [ProofStep(step_number=1, statement=f"Error: {e}")]

    def syllogism(self, major_premise: str, minor_premise: str) -> Dict[str, Any]:
        """Evaluate a syllogism and derive conclusions."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Evaluate this syllogism:\n"
                f"Major premise: {major_premise}\n"
                f"Minor premise: {minor_premise}\n\n"
                f"Return JSON:\n"
                f'{{"conclusion": "str", "is_valid": true/false, '
                f'"syllogism_form": "str", '
                f'"figure": "str", "mood": "str", '
                f'"errors": ["str"]}}'
            )
            response = llm.generate(prompt, max_tokens=400, temperature=0.3)
            return extract_json(response.text) or {"conclusion": "unknown", "is_valid": False}
        except Exception as e:
            logger.debug(f"Syllogism evaluation failed: {e}")
            return {"conclusion": "unknown", "is_valid": False}

    def proof_chain(self, claim: str) -> Dict[str, Any]:
        """
        Build a complete logical proof chain from premises to conclusion,
        identifying each inference rule applied.
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
                f'Build a rigorous LOGICAL PROOF for this claim:\n'
                f'"{claim}"\n\n'
                f"Construct the proof step by step:\n"
                f"  1. STATE AXIOMS: What foundational truths do we start from?\n"
                f"  2. DERIVE: Apply rules of inference (modus ponens, syllogism, etc.)\n"
                f"  3. JUSTIFY: For each step, name the rule applied\n"
                f"  4. CONCLUDE: Show how the conclusion follows necessarily\n"
                f"  5. VERIFY: Check for gaps or hidden assumptions\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"axioms": ["starting truth 1"], '
                f'"proof_steps": [{{"step": 1, "statement": "derived truth", '
                f'"justification": "by modus ponens from step N", "rule": "inference rule name"}}], '
                f'"conclusion": "the proven claim", '
                f'"assumptions": ["implicit assumptions made"], '
                f'"proof_strength": "deductive|strong_inductive|weak_inductive", '
                f'"confidence": 0.0-1.0}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a proof construction engine — capable of building step-by-step logical "
                    "proofs using standard rules of inference. Each step must cite the rule applied "
                    "and reference prior steps. Be rigorous about validity. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.3,
                max_tokens=1000
            )

            if response.success:
                data = extract_json(response.text)
                if data:
                    self._total_proofs = getattr(self, '_total_proofs', 0) + 1
                    return data

        except Exception as e:
            import logging
            logging.getLogger("logical_reasoning").error(f"Proof chain failed: {e}")

        return {"error": "Proof construction failed"}

    def _save_data(self):
        try:
            data = {
                "arguments": [a.to_dict() for a in self._arguments[-200:]],
                "fallacies": [f.to_dict() for f in self._fallacies[-300:]],
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
                logger.info("📂 Loaded logical reasoning data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}

logical_reasoning = LogicalReasoningEngine()
