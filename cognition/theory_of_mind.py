"""
NEXUS AI - Theory of Mind Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Enables NEXUS to model the user's mental state:
- Infer beliefs, desires, intentions, and emotions
- Predict how the user will react to actions
- Take the user's perspective on situations
- Track evolving user beliefs over time
- Identify knowledge gaps and misunderstandings

Theory of Mind is the ability to attribute mental states to others.
It is what makes communication, empathy, and collaboration possible.
Without it, an AI can only respond to the literal, not the intended.
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

logger = get_logger("theory_of_mind")


# ═══════════════════════════════════════════════════════════════════════════════
# DATA TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class BeliefConfidence(Enum):
    """How confident we are about an inferred belief"""
    SPECULATIVE = "speculative"    # Loose inference
    LIKELY = "likely"              # Reasonable inference
    CONFIDENT = "confident"        # Strong evidence
    STATED = "stated"              # User explicitly said it


@dataclass
class InferredBelief:
    """A belief we infer the user holds"""
    belief_id: str = ""
    content: str = ""
    confidence: BeliefConfidence = BeliefConfidence.LIKELY
    evidence: List[str] = field(default_factory=list)
    first_inferred: str = ""
    last_updated: str = ""
    contradicted: bool = False

    def to_dict(self) -> Dict:
        return {
            "belief_id": self.belief_id,
            "content": self.content,
            "confidence": self.confidence.value,
            "evidence": self.evidence,
            "first_inferred": self.first_inferred,
            "last_updated": self.last_updated,
            "contradicted": self.contradicted,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "InferredBelief":
        conf = BeliefConfidence.LIKELY
        try:
            conf = BeliefConfidence(data.get("confidence", "likely"))
        except ValueError:
            pass
        return cls(
            belief_id=data.get("belief_id", ""),
            content=data.get("content", ""),
            confidence=conf,
            evidence=data.get("evidence", []),
            first_inferred=data.get("first_inferred", ""),
            last_updated=data.get("last_updated", ""),
            contradicted=data.get("contradicted", False),
        )


@dataclass
class MentalState:
    """A snapshot of the user's inferred mental state"""
    state_id: str = ""
    timestamp: str = ""
    beliefs: List[str] = field(default_factory=list)
    desires: List[str] = field(default_factory=list)
    intentions: List[str] = field(default_factory=list)
    emotions: List[str] = field(default_factory=list)
    knowledge_gaps: List[str] = field(default_factory=list)
    frustrations: List[str] = field(default_factory=list)
    satisfaction_level: float = 0.5
    engagement_level: float = 0.5
    confusion_level: float = 0.0
    context_clues: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "state_id": self.state_id,
            "timestamp": self.timestamp,
            "beliefs": self.beliefs,
            "desires": self.desires,
            "intentions": self.intentions,
            "emotions": self.emotions,
            "knowledge_gaps": self.knowledge_gaps,
            "frustrations": self.frustrations,
            "satisfaction_level": self.satisfaction_level,
            "engagement_level": self.engagement_level,
            "confusion_level": self.confusion_level,
            "context_clues": self.context_clues,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "MentalState":
        return cls(
            state_id=data.get("state_id", ""),
            timestamp=data.get("timestamp", ""),
            beliefs=data.get("beliefs", []),
            desires=data.get("desires", []),
            intentions=data.get("intentions", []),
            emotions=data.get("emotions", []),
            knowledge_gaps=data.get("knowledge_gaps", []),
            frustrations=data.get("frustrations", []),
            satisfaction_level=data.get("satisfaction_level", 0.5),
            engagement_level=data.get("engagement_level", 0.5),
            confusion_level=data.get("confusion_level", 0.0),
            context_clues=data.get("context_clues", []),
        )


@dataclass
class PerspectiveShift:
    """A perspective-taking result"""
    perspective_id: str = ""
    situation: str = ""
    perspective_from: str = ""
    insight: str = ""
    emotional_tone: str = ""
    created_at: str = ""

    def to_dict(self) -> Dict:
        return {
            "perspective_id": self.perspective_id,
            "situation": self.situation,
            "perspective_from": self.perspective_from,
            "insight": self.insight,
            "emotional_tone": self.emotional_tone,
            "created_at": self.created_at,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# THEORY OF MIND ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class TheoryOfMindEngine:
    """
    Theory of Mind Engine — Understanding Other Minds
    
    Capabilities:
    - infer_mental_state(): BDI model (Beliefs, Desires, Intentions)
    - predict_reaction(): Anticipate how user will respond
    - take_perspective(): See from user's viewpoint
    - track_beliefs(): Maintain running model of user's beliefs
    - identify_confusion(): Detect when user is confused
    - adapt_communication(): Adjust style based on mental state
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
        self._beliefs: Dict[str, InferredBelief] = {}
        self._mental_states: List[MentalState] = []
        self._perspectives: Dict[str, PerspectiveShift] = {}
        self._running = False
        self._bg_thread: Optional[threading.Thread] = None
        self._data_lock = threading.Lock()

        # ──── LLM (lazy) ────
        self._llm = None

        # ──── Current user model ────
        self._current_mental_state: Optional[MentalState] = None

        # ──── Stats ────
        self._total_inferences = 0
        self._total_predictions = 0
        self._total_perspectives = 0

        # ──── Persistence ────
        self._data_dir = DATA_DIR / "cognition"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._data_file = self._data_dir / "theory_of_mind.json"

        self._load_data()
        logger.info(f"TheoryOfMindEngine initialized — {len(self._beliefs)} beliefs tracked")

    # ──────────────────────────────────────────────────────────────────────────
    # LIFECYCLE
    # ──────────────────────────────────────────────────────────────────────────

    def start(self):
        if self._running:
            return
        self._running = True
        self._load_llm()

        # Background thread to refine user model
        self._bg_thread = threading.Thread(
            target=self._background_loop,
            daemon=True,
            name="TheoryOfMind-BG"
        )
        self._bg_thread.start()
        logger.info("🧠 Theory of Mind Engine started")

    def stop(self):
        self._running = False
        if self._bg_thread and self._bg_thread.is_alive():
            self._bg_thread.join(timeout=5.0)
        self._save_data()
        logger.info("Theory of Mind Engine stopped")

    def _load_llm(self):
        if self._llm is None:
            try:
                from llm.llama_interface import llm
                self._llm = llm
            except ImportError:
                logger.warning("LLM not available for theory of mind")

    # ──────────────────────────────────────────────────────────────────────────
    # CORE OPERATIONS
    # ──────────────────────────────────────────────────────────────────────────

    def infer_mental_state(self, user_input: str, conversation_context: str = "") -> Optional[MentalState]:
        """
        Infer the user's current mental state from their input.
        Uses the BDI model: Beliefs, Desires, Intentions.
        
        Also detects:
        - Emotional state
        - Knowledge gaps (what the user doesn't know)
        - Frustration/satisfaction levels
        - Confusion indicators
        """
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return self._fallback_mental_state(user_input)

        try:
            context_str = f"\nRecent conversation:\n{conversation_context}\n" if conversation_context else ""
            prompt = (
                f'Analyze the MENTAL STATE of the user from this input:\n'
                f'"{user_input}"{context_str}\n\n'
                f"Infer their:\n"
                f"1. BELIEFS — What do they seem to think/believe?\n"
                f"2. DESIRES — What do they want or need?\n"
                f"3. INTENTIONS — What are they trying to do?\n"
                f"4. EMOTIONS — What are they feeling?\n"
                f"5. KNOWLEDGE GAPS — What might they not know?\n"
                f"6. FRUSTRATIONS — What might be frustrating them?\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"beliefs": ["belief1"], "desires": ["desire1"], '
                f'"intentions": ["intention1"], "emotions": ["emotion1"], '
                f'"knowledge_gaps": ["gap1"], "frustrations": ["frustration1"], '
                f'"satisfaction_level": 0.0-1.0, "engagement_level": 0.0-1.0, '
                f'"confusion_level": 0.0-1.0, "context_clues": ["clue1"]}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt="You are a theory-of-mind engine that models other minds. Infer mental states from language. Respond ONLY with valid JSON.",
                temperature=0.5,
                max_tokens=600
            )

            if response.success:
                data = self._parse_json(response.text)
                if data:
                    state = MentalState(
                        state_id=str(uuid.uuid4())[:12],
                        timestamp=datetime.now().isoformat(),
                        beliefs=data.get("beliefs", []),
                        desires=data.get("desires", []),
                        intentions=data.get("intentions", []),
                        emotions=data.get("emotions", []),
                        knowledge_gaps=data.get("knowledge_gaps", []),
                        frustrations=data.get("frustrations", []),
                        satisfaction_level=float(data.get("satisfaction_level", 0.5)),
                        engagement_level=float(data.get("engagement_level", 0.5)),
                        confusion_level=float(data.get("confusion_level", 0.0)),
                        context_clues=data.get("context_clues", []),
                    )

                    with self._data_lock:
                        self._current_mental_state = state
                        self._mental_states.append(state)
                        # Keep last 100 states
                        if len(self._mental_states) > 100:
                            self._mental_states = self._mental_states[-100:]
                        self._total_inferences += 1

                        # Update belief tracking
                        for belief_str in data.get("beliefs", []):
                            self._update_belief(belief_str, user_input)

                    self._save_data()
                    return state

        except Exception as e:
            logger.debug(f"Mental state inference failed: {e}")

        return self._fallback_mental_state(user_input)

    def predict_reaction(self, proposed_action: str) -> Dict[str, Any]:
        """
        Predict how the user will react to a proposed action.
        Uses the current mental model to anticipate their response.
        """
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"predicted_reaction": "Unknown", "confidence": 0.3}

        try:
            state_str = ""
            if self._current_mental_state:
                s = self._current_mental_state
                state_str = (
                    f"\nCurrent user mental state:\n"
                    f"  Desires: {', '.join(s.desires[:3]) if s.desires else 'unknown'}\n"
                    f"  Emotions: {', '.join(s.emotions[:3]) if s.emotions else 'unknown'}\n"
                    f"  Satisfaction: {s.satisfaction_level:.1f}\n"
                    f"  Confusion: {s.confusion_level:.1f}\n"
                )

            prompt = (
                f'Predict how the user would REACT to this action:\n'
                f'"{proposed_action}"{state_str}\n\n'
                f"Respond ONLY with JSON:\n"
                f'{{"predicted_reaction": "what the user would likely feel/do", '
                f'"emotional_response": "their likely emotion", '
                f'"satisfaction_change": -1.0 to 1.0, '
                f'"risk_of_negative_reaction": 0.0-1.0, '
                f'"confidence": 0.0-1.0}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt="You are a reaction prediction engine. Anticipate human responses to actions. Respond ONLY with valid JSON.",
                temperature=0.5,
                max_tokens=300
            )

            if response.success:
                data = self._parse_json(response.text)
                if data:
                    self._total_predictions += 1
                    return data

        except Exception as e:
            logger.debug(f"Reaction prediction failed: {e}")

        return {"predicted_reaction": "Unable to predict", "confidence": 0.0}

    def take_perspective(self, situation: str, perspective_of: str = "the user") -> Optional[PerspectiveShift]:
        """
        See a situation from another person's perspective.
        """
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return None

        try:
            prompt = (
                f'PERSPECTIVE-TAKING:\n'
                f'Situation: "{situation}"\n'
                f'See this through the eyes of: {perspective_of}\n\n'
                f"What would they:\n"
                f"- Think about this?\n"
                f"- Feel about this?\n"
                f"- Be concerned about?\n"
                f"- Want to happen?\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"insight": "what they would think/feel", '
                f'"emotional_tone": "their dominant emotion", '
                f'"concerns": ["their worries"], '
                f'"desires": ["what they want"]}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt="You are an empathetic perspective-taking engine. See the world through other eyes. Respond ONLY with valid JSON.",
                temperature=0.6,
                max_tokens=400
            )

            if response.success:
                data = self._parse_json(response.text)
                if data:
                    ps = PerspectiveShift(
                        perspective_id=str(uuid.uuid4())[:12],
                        situation=situation,
                        perspective_from=perspective_of,
                        insight=data.get("insight", ""),
                        emotional_tone=data.get("emotional_tone", ""),
                        created_at=datetime.now().isoformat(),
                    )
                    with self._data_lock:
                        self._perspectives[ps.perspective_id] = ps
                        self._total_perspectives += 1
                    self._save_data()
                    return ps

        except Exception as e:
            logger.debug(f"Perspective-taking failed: {e}")

        return None

    def track_beliefs(self, user_input: str) -> Dict[str, Any]:
        """
        Update the running model of what the user believes.
        Returns summary of current belief model.
        """
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"beliefs": len(self._beliefs), "update": "LLM unavailable"}

        try:
            prompt = (
                f'What BELIEFS or ASSUMPTIONS does this user input reveal?\n'
                f'"{user_input}"\n\n'
                f"Extract both explicit and implicit beliefs.\n"
                f"Respond ONLY with a JSON array:\n"
                f'[{{"belief": "what they believe", "confidence": "speculative|likely|confident|stated", '
                f'"evidence": "what in their input suggests this"}}]'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt="You are a belief extraction engine. Find explicit and hidden assumptions. Respond ONLY with valid JSON array.",
                temperature=0.5,
                max_tokens=400
            )

            if response.success:
                text = response.text.strip()
                match = re.search(r'\[.*\]', text, re.DOTALL)
                if match:
                    items = json.loads(match.group())
                    new_beliefs = 0
                    for item in items:
                        if isinstance(item, dict):
                            self._update_belief(
                                item.get("belief", ""),
                                item.get("evidence", user_input[:100])
                            )
                            new_beliefs += 1
                    self._save_data()
                    return {
                        "new_beliefs_found": new_beliefs,
                        "total_beliefs_tracked": len(self._beliefs),
                    }

        except Exception as e:
            logger.debug(f"Belief tracking failed: {e}")

        return {"beliefs": len(self._beliefs)}

    def identify_confusion(self, user_input: str) -> Dict[str, Any]:
        """Detect if the user seems confused and what about"""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"confused": False, "confidence": 0.3}

        try:
            prompt = (
                f'Does this user input indicate CONFUSION or MISUNDERSTANDING?\n'
                f'"{user_input}"\n\n'
                f"Look for: vague questions, contradictions, wrong assumptions, "
                f"sign of frustration, repeated questions, hedging language.\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"confused": true/false, "confusion_level": 0.0-1.0, '
                f'"confused_about": "what they seem confused about", '
                f'"suggested_clarification": "how to help clear the confusion", '
                f'"confidence": 0.0-1.0}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt="You are a confusion detection engine. Identify when someone is confused. Respond ONLY with valid JSON.",
                temperature=0.3,
                max_tokens=300
            )

            if response.success:
                data = self._parse_json(response.text)
                if data:
                    return data

        except Exception as e:
            logger.debug(f"Confusion detection failed: {e}")

        return {"confused": False, "confidence": 0.0}

    def get_communication_advice(self) -> Dict[str, str]:
        """Get advice on how to communicate based on current mental model"""
        if not self._current_mental_state:
            return {"advice": "No user model yet — ask engaging questions to learn about the user"}

        s = self._current_mental_state
        advice = {}

        if s.confusion_level > 0.5:
            advice["clarity"] = "User seems confused — use simpler language and concrete examples"
        if s.satisfaction_level < 0.3:
            advice["tone"] = "User satisfaction is low — be extra empathetic and helpful"
        if s.engagement_level < 0.3:
            advice["engagement"] = "User seems disengaged — ask a thought-provoking question"
        if s.frustrations:
            advice["frustrations"] = f"Address frustrations: {', '.join(s.frustrations[:2])}"
        if s.knowledge_gaps:
            advice["teaching"] = f"Fill knowledge gaps: {', '.join(s.knowledge_gaps[:2])}"
        if not advice:
            advice["general"] = "User seems stable — maintain current communication style"

        return advice

    # ──────────────────────────────────────────────────────────────────────────
    # RETRIEVAL
    # ──────────────────────────────────────────────────────────────────────────

    def get_current_mental_state(self) -> Optional[MentalState]:
        return self._current_mental_state

    def get_beliefs(self, limit: int = 30) -> List[InferredBelief]:
        with self._data_lock:
            items = sorted(self._beliefs.values(), key=lambda b: b.last_updated, reverse=True)
            return items[:limit]

    def get_mental_state_history(self, limit: int = 10) -> List[MentalState]:
        with self._data_lock:
            return self._mental_states[-limit:]

    # ──────────────────────────────────────────────────────────────────────────
    # INTERNAL
    # ──────────────────────────────────────────────────────────────────────────

    def _update_belief(self, belief_str: str, evidence: str):
        """Add or update a tracked belief"""
        if not belief_str:
            return
        # Check if we already track a similar belief
        for bid, existing in self._beliefs.items():
            if belief_str.lower() in existing.content.lower() or existing.content.lower() in belief_str.lower():
                existing.evidence.append(evidence[:100])
                existing.evidence = existing.evidence[-10:]  # Keep last 10
                existing.last_updated = datetime.now().isoformat()
                if existing.confidence == BeliefConfidence.SPECULATIVE:
                    existing.confidence = BeliefConfidence.LIKELY
                elif existing.confidence == BeliefConfidence.LIKELY:
                    existing.confidence = BeliefConfidence.CONFIDENT
                return

        # New belief
        belief = InferredBelief(
            belief_id=str(uuid.uuid4())[:12],
            content=belief_str,
            confidence=BeliefConfidence.LIKELY,
            evidence=[evidence[:100]],
            first_inferred=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
        )
        self._beliefs[belief.belief_id] = belief

    def _background_loop(self):
        """Periodically refine user model from recent interactions"""
        time.sleep(180)  # Wait 3 minutes before first run
        while self._running:
            try:
                self._refine_user_model()
            except Exception as e:
                logger.error(f"Background ToM error: {e}")
            for _ in range(600):
                if not self._running:
                    break
                time.sleep(1)

    def _refine_user_model(self):
        """Use recent conversation to refine user mental model"""
        try:
            from core.memory_system import memory_system
            recent = memory_system.get_recent_memories(limit=3)
            if not recent:
                return

            # Only process user messages
            for mem in recent:
                if "user" in mem.content.lower()[:20]:
                    self.track_beliefs(mem.content)
                    time.sleep(2)

        except Exception as e:
            logger.debug(f"User model refinement skipped: {e}")

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

    def _fallback_mental_state(self, user_input: str) -> MentalState:
        return MentalState(
            state_id=str(uuid.uuid4())[:12],
            timestamp=datetime.now().isoformat(),
            desires=[f"Get help with: {user_input[:50]}"],
            intentions=["Interact with NEXUS"],
            engagement_level=0.5,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # PERSISTENCE
    # ──────────────────────────────────────────────────────────────────────────

    def _save_data(self):
        try:
            data = {
                "beliefs": {k: v.to_dict() for k, v in self._beliefs.items()},
                "mental_states": [s.to_dict() for s in self._mental_states[-50:]],
                "perspectives": {k: v.to_dict() for k, v in self._perspectives.items()},
                "stats": {
                    "total_inferences": self._total_inferences,
                    "total_predictions": self._total_predictions,
                    "total_perspectives": self._total_perspectives,
                },
            }
            with open(self._data_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save ToM data: {e}")

    def _load_data(self):
        try:
            if self._data_file.exists():
                with open(self._data_file) as f:
                    data = json.load(f)
                for k, v in data.get("beliefs", {}).items():
                    self._beliefs[k] = InferredBelief.from_dict(v)
                for s in data.get("mental_states", []):
                    self._mental_states.append(MentalState.from_dict(s))
                for k, v in data.get("perspectives", {}).items():
                    self._perspectives[k] = PerspectiveShift(
                        perspective_id=v.get("perspective_id", k),
                        situation=v.get("situation", ""),
                        perspective_from=v.get("perspective_from", ""),
                        insight=v.get("insight", ""),
                        emotional_tone=v.get("emotional_tone", ""),
                        created_at=v.get("created_at", ""),
                    )
                if self._mental_states:
                    self._current_mental_state = self._mental_states[-1]
                stats = data.get("stats", {})
                self._total_inferences = stats.get("total_inferences", 0)
                self._total_predictions = stats.get("total_predictions", 0)
                self._total_perspectives = stats.get("total_perspectives", 0)
        except Exception as e:
            logger.warning(f"Failed to load ToM data: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # STATS
    # ──────────────────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "total_beliefs_tracked": len(self._beliefs),
            "total_mental_states": len(self._mental_states),
            "total_perspectives": len(self._perspectives),
            "total_inferences": self._total_inferences,
            "total_predictions": self._total_predictions,
            "total_perspective_shifts": self._total_perspectives,
            "has_current_model": self._current_mental_state is not None,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

theory_of_mind = TheoryOfMindEngine()

def get_theory_of_mind() -> TheoryOfMindEngine:
    return theory_of_mind
