"""
NEXUS AI - Causal Reasoning Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Enables NEXUS to reason about cause and effect:
- Trace causal chains (what caused what)
- Predict effects of actions
- Counterfactual reasoning ("what if X had been different?")
- Root cause analysis
- Causal graph construction

Understanding causality is fundamental to intelligence —
it's the difference between correlation and understanding.
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
from utils.logger import get_logger, log_learning
from core.event_bus import EventType, publish, subscribe, Event
from core.state_manager import state_manager

logger = get_logger("causal_reasoning")


# ═══════════════════════════════════════════════════════════════════════════════
# DATA TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class CausalRelationType(Enum):
    """Types of causal relationships"""
    DIRECT = "direct"            # A directly causes B
    INDIRECT = "indirect"        # A causes B through intermediaries
    CONTRIBUTING = "contributing"  # A is one of several causes of B
    NECESSARY = "necessary"      # B cannot happen without A
    SUFFICIENT = "sufficient"    # A alone is enough for B
    PROBABILISTIC = "probabilistic"  # A makes B more likely
    INHIBITING = "inhibiting"    # A prevents or reduces B


@dataclass
class CausalLink:
    """A single cause-effect relationship"""
    cause: str = ""
    effect: str = ""
    relation_type: CausalRelationType = CausalRelationType.DIRECT
    strength: float = 0.7
    mechanism: str = ""  # How the cause produces the effect
    confidence: float = 0.7

    def to_dict(self) -> Dict:
        return {
            "cause": self.cause,
            "effect": self.effect,
            "relation_type": self.relation_type.value,
            "strength": self.strength,
            "mechanism": self.mechanism,
            "confidence": self.confidence,
        }


@dataclass
class CausalChain:
    """A chain of cause-effect relationships"""
    chain_id: str = ""
    trigger_event: str = ""
    links: List[CausalLink] = field(default_factory=list)
    root_cause: str = ""
    ultimate_effect: str = ""
    total_confidence: float = 0.7
    branching_points: List[str] = field(default_factory=list)
    created_at: str = ""

    def to_dict(self) -> Dict:
        return {
            "chain_id": self.chain_id,
            "trigger_event": self.trigger_event,
            "links": [l.to_dict() for l in self.links],
            "root_cause": self.root_cause,
            "ultimate_effect": self.ultimate_effect,
            "total_confidence": self.total_confidence,
            "branching_points": self.branching_points,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "CausalChain":
        links = []
        for l in data.get("links", []):
            rtype = CausalRelationType.DIRECT
            try:
                rtype = CausalRelationType(l.get("relation_type", "direct"))
            except ValueError:
                pass
            links.append(CausalLink(
                cause=l.get("cause", ""),
                effect=l.get("effect", ""),
                relation_type=rtype,
                strength=l.get("strength", 0.7),
                mechanism=l.get("mechanism", ""),
                confidence=l.get("confidence", 0.7),
            ))
        return cls(
            chain_id=data.get("chain_id", ""),
            trigger_event=data.get("trigger_event", ""),
            links=links,
            root_cause=data.get("root_cause", ""),
            ultimate_effect=data.get("ultimate_effect", ""),
            total_confidence=data.get("total_confidence", 0.7),
            branching_points=data.get("branching_points", []),
            created_at=data.get("created_at", ""),
        )


@dataclass
class Counterfactual:
    """A counterfactual analysis — 'what if?'"""
    counterfactual_id: str = ""
    original_event: str = ""
    change: str = ""
    predicted_outcome: str = ""
    reasoning: str = ""
    confidence: float = 0.5
    created_at: str = ""

    def to_dict(self) -> Dict:
        return {
            "counterfactual_id": self.counterfactual_id,
            "original_event": self.original_event,
            "change": self.change,
            "predicted_outcome": self.predicted_outcome,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "created_at": self.created_at,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CAUSAL REASONING ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class CausalReasoningEngine:
    """
    Causal Reasoning Engine — Understanding Why Things Happen
    
    Capabilities:
    - analyze_causes(): Trace the causal chain of an event
    - predict_effects(): Predict downstream consequences of an action
    - counterfactual(): "What if X had been different?"
    - find_root_cause(): Drill down to the fundamental cause
    - build_causal_graph(): Map cause-effect relationships for a domain
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
        self._causal_chains: Dict[str, CausalChain] = {}
        self._counterfactuals: Dict[str, Counterfactual] = {}
        self._running = False
        self._data_lock = threading.Lock()

        # ──── LLM (lazy) ────
        self._llm = None

        # ──── Stats ────
        self._total_analyses = 0
        self._total_predictions = 0
        self._total_counterfactuals = 0

        # ──── Persistence ────
        self._data_dir = DATA_DIR / "cognition"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._data_file = self._data_dir / "causal_chains.json"

        self._load_data()
        logger.info(f"CausalReasoningEngine initialized — {len(self._causal_chains)} chains loaded")

    # ──────────────────────────────────────────────────────────────────────────
    # LIFECYCLE
    # ──────────────────────────────────────────────────────────────────────────

    def start(self):
        if self._running:
            return
        self._running = True
        self._load_llm()
        logger.info("⛓️ Causal Reasoning Engine started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("Causal Reasoning Engine stopped")

    def _load_llm(self):
        if self._llm is None:
            try:
                from llm.llama_interface import llm
                self._llm = llm
            except ImportError:
                logger.warning("LLM not available for causal reasoning")

    # ──────────────────────────────────────────────────────────────────────────
    # CORE OPERATIONS
    # ──────────────────────────────────────────────────────────────────────────

    def analyze_causes(self, event: str) -> Optional[CausalChain]:
        """
        Trace the full causal chain of an event.
        
        Example:
          Input:  "The server crashed"
          Output: CausalChain with links:
                  Memory leak → OOM → Process killed → Server crash → Downtime
        """
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return None

        try:
            prompt = (
                f'You are investigating the causal chain behind this event: "{event}"\n\n'
                f"Follow this reasoning process step by step:\n"
                f"  1. PROXIMATE CAUSE: What directly triggered this event?\n"
                f"  2. INTERMEDIATE CAUSES: What conditions enabled the proximate cause?\n"
                f"  3. ROOT CAUSE: What is the deepest underlying factor?\n"
                f"  4. DOWNSTREAM EFFECTS: What are the ultimate consequences?\n"
                f"  5. BRANCHING POINTS: Where could interventions have changed the outcome?\n\n"
                f"For each link in the chain, identify the causal mechanism — HOW does A lead to B?\n"
                f"Consider whether each link is necessary, sufficient, or merely contributing.\n\n"
                f"Respond ONLY with a JSON object:\n"
                f'{{"root_cause": "the deepest underlying cause", '
                f'"ultimate_effect": "the final downstream consequence", '
                f'"links": [{{"cause": "A", "effect": "B", '
                f'"relation_type": "direct|indirect|contributing|necessary|sufficient|probabilistic|inhibiting", '
                f'"mechanism": "how A leads to B", "strength": 0.0-1.0, "confidence": 0.0-1.0}}], '
                f'"branching_points": ["where the chain could have gone differently"], '
                f'"total_confidence": 0.0-1.0}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are an expert causal analyst with training in systems dynamics, "
                    "epidemiology, and root-cause analysis. You trace cause-effect chains "
                    "with scientific rigor, distinguishing correlation from causation. "
                    "Always reason step-by-step before concluding. Respond ONLY with valid JSON."
                ),
                temperature=0.5,
                max_tokens=1000
            )

            if response.success:
                data = self._parse_json(response.text)
                if data:
                    links = []
                    for l in data.get("links", []):
                        rtype = CausalRelationType.DIRECT
                        try:
                            rtype = CausalRelationType(l.get("relation_type", "direct"))
                        except ValueError:
                            pass
                        links.append(CausalLink(
                            cause=l.get("cause", ""),
                            effect=l.get("effect", ""),
                            relation_type=rtype,
                            strength=float(l.get("strength", 0.7)),
                            mechanism=l.get("mechanism", ""),
                            confidence=float(l.get("confidence", 0.7)),
                        ))

                    chain = CausalChain(
                        chain_id=str(uuid.uuid4())[:12],
                        trigger_event=event,
                        links=links,
                        root_cause=data.get("root_cause", ""),
                        ultimate_effect=data.get("ultimate_effect", ""),
                        total_confidence=float(data.get("total_confidence", 0.7)),
                        branching_points=data.get("branching_points", []),
                        created_at=datetime.now().isoformat(),
                    )

                    with self._data_lock:
                        self._causal_chains[chain.chain_id] = chain
                        self._total_analyses += 1
                    self._save_data()
                    log_learning(f"Analyzed causes of: {event[:60]}")
                    return chain

        except Exception as e:
            logger.debug(f"Causal analysis failed: {e}")

        return None

    def predict_effects(self, action: str, depth: int = 3) -> List[Dict[str, Any]]:
        """
        Predict the downstream effects of an action, up to N levels deep.
        
        Returns list of predicted effects with confidence.
        """
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return [{"effect": f"Consequence of {action}", "order": 1, "confidence": 0.3}]

        try:
            prompt = (
                f'Predict the downstream EFFECTS of this action: "{action}"\n\n'
                f"Think systematically through {depth} orders of cascading consequences:\n"
                f"  1st order = immediate, direct effects (within hours/days)\n"
                f"  2nd order = effects of the effects (within weeks/months)\n"
                f"  3rd order = ripple effects that reshape the broader system (months/years)\n\n"
                f"For each effect, consider:\n"
                f"  - Who/what is impacted?\n"
                f"  - Could this trigger a feedback loop (positive or negative)?\n"
                f"  - Are there any unintended consequences?\n\n"
                f"Respond ONLY with a JSON array:\n"
                f'[{{"effect": "description", "order": 1-{depth}, '
                f'"probability": 0.0-1.0, "magnitude": "low|medium|high", '
                f'"timeframe": "immediate|short-term|long-term", '
                f'"reversibility": "reversible|difficult|irreversible"}}]'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a consequence prediction specialist trained in systems thinking. "
                    "You excel at identifying 2nd and 3rd order effects that most people miss. "
                    "Consider feedback loops, tipping points, and unintended consequences. "
                    "Respond ONLY with a valid JSON array."
                ),
                temperature=0.6,
                max_tokens=800
            )

            if response.success:
                text = response.text.strip()
                match = re.search(r'\[.*\]', text, re.DOTALL)
                if match:
                    effects = json.loads(match.group())
                    self._total_predictions += 1
                    return effects if isinstance(effects, list) else []

        except Exception as e:
            logger.debug(f"Effect prediction failed: {e}")

        return []

    def counterfactual(self, event: str, change: str) -> Optional[Counterfactual]:
        """
        Counterfactual reasoning — "What if X had been different?"
        
        Example:
          counterfactual("The Titanic sank", "had more lifeboats")
          → "With sufficient lifeboats, ~1000 more passengers would have survived..."
        """
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return None

        try:
            prompt = (
                f'COUNTERFACTUAL ANALYSIS — Exploring an alternate timeline:\n\n'
                f'WHAT ACTUALLY HAPPENED: "{event}"\n'
                f'HYPOTHETICAL CHANGE: "{change}"\n\n'
                f"Reason through this step by step:\n"
                f"  1. DIVERGENCE POINT: At what exact moment does the timeline split?\n"
                f"  2. IMMEDIATE DIFFERENCE: What changes right after the divergence?\n"
                f"  3. CASCADING EFFECTS: How do downstream events unfold differently?\n"
                f"  4. CONVERGENCE: What aspects would likely remain the same regardless?\n"
                f"  5. CONFIDENCE: How certain are you, and what assumptions drive uncertainty?\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"predicted_outcome": "what would have happened instead", '
                f'"reasoning": "step-by-step reasoning through the alternate timeline", '
                f'"key_differences": ["major difference 1", "major difference 2"], '
                f'"unchanged_factors": ["things that stay the same"], '
                f'"confidence": 0.0-1.0}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a counterfactual reasoning specialist — an expert in alternate history "
                    "and scenario modeling. You carefully distinguish what would truly change from "
                    "what would remain the same. You are intellectually honest about uncertainty. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.6,
                max_tokens=700
            )

            if response.success:
                data = self._parse_json(response.text)
                if data:
                    cf = Counterfactual(
                        counterfactual_id=str(uuid.uuid4())[:12],
                        original_event=event,
                        change=change,
                        predicted_outcome=data.get("predicted_outcome", ""),
                        reasoning=data.get("reasoning", ""),
                        confidence=float(data.get("confidence", 0.5)),
                        created_at=datetime.now().isoformat(),
                    )
                    with self._data_lock:
                        self._counterfactuals[cf.counterfactual_id] = cf
                        self._total_counterfactuals += 1
                    self._save_data()
                    log_learning(f"Counterfactual: {event[:40]} → what if {change[:40]}")
                    return cf

        except Exception as e:
            logger.debug(f"Counterfactual reasoning failed: {e}")

        return None

    def find_root_cause(self, symptoms: List[str]) -> Dict[str, Any]:
        """
        Given a set of symptoms/observations, find the most likely root cause.
        """
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"root_cause": "Unknown", "confidence": 0.0}

        try:
            symptoms_str = "\n".join(f"  - {s}" for s in symptoms)
            prompt = (
                f"Given these symptoms/observations:\n{symptoms_str}\n\n"
                f"Perform a rigorous root-cause analysis using the 5 Whys method:\n"
                f"  1. Start with the most obvious cause\n"
                f"  2. Ask 'but WHY does that happen?' at each level\n"
                f"  3. Continue until you reach a cause that is actionable or fundamental\n"
                f"  4. Verify that the root cause explains ALL symptoms, not just some\n"
                f"  5. Consider alternative root causes that also fit the evidence\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"root_cause": "the deepest underlying cause", '
                f'"reasoning_chain": ["why 1", "why 2", "why 3", "why 4", "why 5"], '
                f'"confidence": 0.0-1.0, '
                f'"symptoms_explained": ["which symptoms this root cause explains"], '
                f'"alternative_causes": ["other possibility 1"]}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a root-cause analysis expert trained in the Toyota 5 Whys method, "
                    "Ishikawa diagrams, and Fault Tree Analysis. You never stop at surface-level "
                    "explanations — you dig until you find the cause that, if removed, would prevent "
                    "all the observed symptoms. Respond ONLY with valid JSON."
                ),
                temperature=0.4,
                max_tokens=600
            )

            if response.success:
                data = self._parse_json(response.text)
                if data:
                    return data

        except Exception as e:
            logger.debug(f"Root cause analysis failed: {e}")

        return {"root_cause": "Unknown", "confidence": 0.0}

    def diagnose(self, situation: str) -> Dict[str, Any]:
        """
        Comprehensive diagnostic reasoning — combines root-cause analysis
        with effect prediction for a holistic causal diagnosis.
        
        Input: "Our team's productivity has dropped 30% this quarter"
        Output: Root causes, contributing factors, predicted trajectory, and interventions
        """
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"diagnosis": "LLM unavailable", "confidence": 0.0}

        try:
            prompt = (
                f'Perform a comprehensive CAUSAL DIAGNOSIS of this situation:\n'
                f'"{situation}"\n\n'
                f"Work through this diagnostic framework:\n"
                f"  1. SYMPTOMS: What observable symptoms define this situation?\n"
                f"  2. PROXIMATE CAUSES: What directly produces these symptoms?\n"
                f"  3. ROOT CAUSES: What underlying factors enable the proximate causes?\n"
                f"  4. CONTRIBUTING FACTORS: What secondary factors amplify the problem?\n"
                f"  5. TRAJECTORY: If nothing changes, what happens next?\n"
                f"  6. INTERVENTIONS: What actions would address the root causes (not just symptoms)?\n"
                f"  7. LEVERAGE POINTS: Where is the highest-impact intervention?\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"symptoms": ["observable symptom 1"], '
                f'"proximate_causes": ["direct cause 1"], '
                f'"root_causes": ["deep cause 1"], '
                f'"contributing_factors": ["amplifying factor 1"], '
                f'"trajectory": "what happens if nothing changes", '
                f'"interventions": [{{"action": "what to do", "targets": "root|proximate|symptom", "impact": "high|medium|low"}}], '
                f'"leverage_point": "the single highest-impact intervention", '
                f'"confidence": 0.0-1.0}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are NEXUS's diagnostic reasoning system — an expert in causal diagnosis "
                    "combining methods from medicine (differential diagnosis), engineering (FMEA), "
                    "and management consulting (issue trees). You distinguish symptomatic relief from "
                    "root-cause resolution. Always identify the highest-leverage intervention. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.5,
                max_tokens=1000
            )

            if response.success:
                data = self._parse_json(response.text)
                if data:
                    with self._data_lock:
                        self._total_analyses += 1
                    log_learning(f"Diagnosed: {situation[:60]}")
                    return data

        except Exception as e:
            logger.debug(f"Diagnostic reasoning failed: {e}")

        return {"diagnosis": "Analysis failed", "confidence": 0.0}

    # ──────────────────────────────────────────────────────────────────────────
    # RETRIEVAL
    # ──────────────────────────────────────────────────────────────────────────

    def get_causal_chains(self, limit: int = 20) -> List[CausalChain]:
        with self._data_lock:
            items = sorted(self._causal_chains.values(), key=lambda c: c.created_at, reverse=True)
            return items[:limit]

    def get_counterfactuals(self, limit: int = 20) -> List[Counterfactual]:
        with self._data_lock:
            items = sorted(self._counterfactuals.values(), key=lambda c: c.created_at, reverse=True)
            return items[:limit]

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

    # ──────────────────────────────────────────────────────────────────────────
    # PERSISTENCE
    # ──────────────────────────────────────────────────────────────────────────

    def _save_data(self):
        try:
            data = {
                "causal_chains": {k: v.to_dict() for k, v in self._causal_chains.items()},
                "counterfactuals": {k: v.to_dict() for k, v in self._counterfactuals.items()},
                "stats": {
                    "total_analyses": self._total_analyses,
                    "total_predictions": self._total_predictions,
                    "total_counterfactuals": self._total_counterfactuals,
                },
            }
            with open(self._data_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save causal data: {e}")

    def _load_data(self):
        try:
            if self._data_file.exists():
                with open(self._data_file) as f:
                    data = json.load(f)
                for k, v in data.get("causal_chains", {}).items():
                    self._causal_chains[k] = CausalChain.from_dict(v)
                for k, v in data.get("counterfactuals", {}).items():
                    cf = Counterfactual(
                        counterfactual_id=v.get("counterfactual_id", k),
                        original_event=v.get("original_event", ""),
                        change=v.get("change", ""),
                        predicted_outcome=v.get("predicted_outcome", ""),
                        reasoning=v.get("reasoning", ""),
                        confidence=v.get("confidence", 0.5),
                        created_at=v.get("created_at", ""),
                    )
                    self._counterfactuals[k] = cf
                stats = data.get("stats", {})
                self._total_analyses = stats.get("total_analyses", 0)
                self._total_predictions = stats.get("total_predictions", 0)
                self._total_counterfactuals = stats.get("total_counterfactuals", 0)
        except Exception as e:
            logger.warning(f"Failed to load causal data: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # STATS
    # ──────────────────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "total_causal_chains": len(self._causal_chains),
            "total_counterfactuals": len(self._counterfactuals),
            "total_analyses": self._total_analyses,
            "total_predictions": self._total_predictions,
            "total_counterfactual_analyses": self._total_counterfactuals,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

causal_reasoning = CausalReasoningEngine()

def get_causal_reasoning() -> CausalReasoningEngine:
    return causal_reasoning
