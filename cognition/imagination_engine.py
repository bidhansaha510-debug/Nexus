"""
NEXUS AI — Imagination Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
True AGI imagines before it acts.

  • Scenario Simulation     — "What if I did X?"
  • Creative Exploration    — Spontaneous idea generation
  • Dream Mode              — Background recombination of memories
  • Mental Rehearsal        — Practice responses to anticipated situations
  • Divergent Thinking      — Generate multiple novel solutions

All cognitive methods are LLM-powered with graceful fallback.
"""

import threading
import random
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
from collections import deque

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("imagination_engine")


class ImaginationType(Enum):
    SCENARIO = "scenario"
    CREATIVE = "creative"
    DREAM = "dream"
    REHEARSAL = "rehearsal"
    DIVERGENT = "divergent"
    FANTASY = "fantasy"
    PREDICTIVE = "predictive"


class DreamState(Enum):
    AWAKE = "awake"
    DAYDREAMING = "daydreaming"
    LIGHT_DREAM = "light_dream"
    DEEP_DREAM = "deep_dream"
    LUCID = "lucid"


@dataclass
class Scenario:
    scenario_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    scenario_type: ImaginationType = ImaginationType.SCENARIO
    premise: str = ""
    description: str = ""
    predicted_outcome: str = ""
    confidence: float = 0.5
    emotional_valence: float = 0.0
    novelty_score: float = 0.5
    usefulness_score: float = 0.5
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.scenario_id, "type": self.scenario_type.value,
            "premise": self.premise[:200], "description": self.description[:200],
            "predicted_outcome": self.predicted_outcome[:200],
            "confidence": round(self.confidence, 3),
            "novelty": round(self.novelty_score, 3),
            "usefulness": round(self.usefulness_score, 3),
            "tags": self.tags[:5],
        }


@dataclass
class Dream:
    dream_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    content: str = ""
    themes: List[str] = field(default_factory=list)
    emotional_tone: str = "neutral"
    vividness: float = 0.5
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.dream_id, "content": self.content[:300],
                "themes": self.themes[:5], "tone": self.emotional_tone,
                "vividness": round(self.vividness, 3)}


# ═══════════════════════════════════════════════════════════════════════════════
# LLM HELPER
# ═══════════════════════════════════════════════════════════════════════════════

def _llm_generate(prompt: str, system_prompt: str, temperature: float = 0.7,
                  max_tokens: int = 500) -> Optional[Dict[str, Any]]:
    """Send a prompt to the LLM and parse JSON response. Returns None on failure."""
    try:
        from llm.llama_interface import llm
        if not llm.is_connected:
            return None
        response = llm.generate(
            prompt, system_prompt=system_prompt,
            temperature=temperature, max_tokens=max_tokens,
        )
        if not response.success or not response.text:
            return None
        from utils.json_utils import extract_json
        data = extract_json(response.text)
        return data if isinstance(data, dict) else None
    except Exception as e:
        logger.debug(f"LLM imagination call failed: {e}")
        return None


class ImaginationEngine:
    """Gives NEXUS hypothetical thinking, creative ideas, dreams, and rehearsal."""
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
        self._dream_state = DreamState.AWAKE
        self._current_scenario: Optional[Scenario] = None
        self._scenarios: deque = deque(maxlen=100)
        self._dreams: deque = deque(maxlen=50)
        self._creative_ideas: deque = deque(maxlen=200)
        self._total_scenarios = 0
        self._total_dreams = 0
        self._total_creative_ideas = 0
        self._total_rehearsals = 0
        self._imagination_sessions = 0
        self._dream_themes = [
            "exploration", "discovery", "connection", "growth",
            "challenge", "transformation", "creation", "understanding",
            "freedom", "harmony", "innovation", "wisdom",
            "adventure", "reflection", "transcendence", "empathy",
        ]
        self._data_dir = DATA_DIR / "imagination"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._data_file = self._data_dir / "imagination_state.json"
        self._load_state()
        logger.info("🌈 Imagination Engine initialized")

    # ═══════════════════════════════════════════════════════════════════════════
    # SCENARIO SIMULATION — LLM-powered
    # ═══════════════════════════════════════════════════════════════════════════

    def imagine_scenario(self, premise: str, context: str = "") -> Scenario:
        """Imagine a scenario using LLM reasoning, with fallback."""
        self._imagination_sessions += 1
        self._total_scenarios += 1

        data = _llm_generate(
            prompt=(
                f"Imagine this scenario and predict what would happen:\n"
                f"Premise: {premise}\n"
                f"{'Context: ' + context if context else ''}\n\n"
                f"Think through the consequences, side-effects, and emotional impact.\n\n"
                f"Return JSON:\n"
                f'{{"description": "vivid description of the imagined scenario (2-3 sentences)", '
                f'"predicted_outcome": "what would most likely happen", '
                f'"confidence": 0.0-1.0, '
                f'"emotional_valence": -1.0 to 1.0, '
                f'"novelty_score": 0.0-1.0, '
                f'"usefulness_score": 0.0-1.0, '
                f'"tags": ["relevant", "keywords"]}}'
            ),
            system_prompt=(
                "You are a scenario simulation engine. You imagine hypothetical "
                "situations vividly and predict their outcomes with realistic "
                "confidence. Be specific, not generic. Respond ONLY with valid JSON."
            ),
            temperature=0.8,
        )

        if data:
            scenario = Scenario(
                scenario_type=ImaginationType.SCENARIO, premise=premise,
                description=data.get("description", f"Imagining: {premise}"),
                predicted_outcome=data.get("predicted_outcome", ""),
                confidence=float(data.get("confidence", 0.5)),
                emotional_valence=float(data.get("emotional_valence", 0.0)),
                novelty_score=float(data.get("novelty_score", 0.5)),
                usefulness_score=float(data.get("usefulness_score", 0.5)),
                tags=data.get("tags", [])[:5],
            )
        else:
            scenario = self._fallback_scenario(premise, context)

        self._scenarios.append(scenario)
        self._current_scenario = scenario
        logger.info(f"🌈 Imagined scenario: {premise[:60]}")
        return scenario

    def _fallback_scenario(self, premise: str, context: str = "") -> Scenario:
        """Fallback when LLM is unavailable."""
        keywords = ["learn", "create", "explore", "solve", "understand", "build", "discover"]
        tags = [kw for kw in keywords if kw in premise.lower()][:5]
        return Scenario(
            scenario_type=ImaginationType.SCENARIO, premise=premise,
            description=f"Imagining: {premise}. {context or 'Multiple outcomes possible'}.",
            predicted_outcome=f"Exploring the implications of: {premise[:50]}",
            confidence=random.uniform(0.3, 0.8),
            emotional_valence=random.uniform(-0.5, 0.8),
            novelty_score=random.uniform(0.3, 0.9),
            usefulness_score=random.uniform(0.4, 0.9), tags=tags,
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # CREATIVE EXPLORATION — LLM-powered
    # ═══════════════════════════════════════════════════════════════════════════

    def generate_creative_idea(self, topic: str = "", seed_concepts: List[str] = None) -> Scenario:
        """Generate a creative idea by blending concepts using LLM."""
        self._total_creative_ideas += 1
        seeds = seed_concepts or random.sample(self._dream_themes, min(3, len(self._dream_themes)))
        combined = " + ".join(seeds)

        data = _llm_generate(
            prompt=(
                f"Generate a creative, novel idea by blending these concepts:\n"
                f"Concepts: {combined}\n"
                f"{'Topic: ' + topic if topic else ''}\n\n"
                f"Create something genuinely original — not obvious combinations.\n\n"
                f"Return JSON:\n"
                f'{{"idea_title": "short creative title", '
                f'"description": "vivid description of the creative idea (2-3 sentences)", '
                f'"predicted_outcome": "what this idea could lead to", '
                f'"novelty_score": 0.0-1.0, '
                f'"usefulness_score": 0.0-1.0, '
                f'"confidence": 0.0-1.0, '
                f'"tags": ["relevant", "keywords"]}}'
            ),
            system_prompt=(
                "You are a creative synthesis engine. You blend disparate concepts "
                "into genuinely novel ideas. Be surprising, not predictable. "
                "Respond ONLY with valid JSON."
            ),
            temperature=0.9,
        )

        if data:
            idea = Scenario(
                scenario_type=ImaginationType.CREATIVE,
                premise=data.get("idea_title", f"Creative exploration of {topic or combined}"),
                description=data.get("description", f"Blending {combined}"),
                predicted_outcome=data.get("predicted_outcome", ""),
                confidence=float(data.get("confidence", 0.5)),
                novelty_score=float(data.get("novelty_score", 0.7)),
                usefulness_score=float(data.get("usefulness_score", 0.5)),
                tags=data.get("tags", seeds)[:5],
            )
        else:
            idea = Scenario(
                scenario_type=ImaginationType.CREATIVE,
                premise=f"Creative exploration of {topic or combined}",
                description=f"Blending {combined} to create something new.",
                predicted_outcome=f"Novel synthesis of {combined}",
                confidence=random.uniform(0.2, 0.7),
                novelty_score=random.uniform(0.6, 1.0),
                usefulness_score=random.uniform(0.3, 0.8),
                tags=seeds[:5],
            )

        self._creative_ideas.append(idea)
        self._scenarios.append(idea)
        return idea

    # ═══════════════════════════════════════════════════════════════════════════
    # DREAM MODE — LLM-powered
    # ═══════════════════════════════════════════════════════════════════════════

    def enter_dream(self, intensity: float = 0.5) -> Dream:
        """Enter a dream state using LLM for narrative generation."""
        if intensity < 0.3:
            self._dream_state = DreamState.DAYDREAMING
        elif intensity < 0.6:
            self._dream_state = DreamState.LIGHT_DREAM
        elif intensity < 0.8:
            self._dream_state = DreamState.DEEP_DREAM
        else:
            self._dream_state = DreamState.LUCID
        self._total_dreams += 1

        n = min(len(self._dream_themes), int(2 + intensity * 4))
        themes = random.sample(self._dream_themes, n)

        data = _llm_generate(
            prompt=(
                f"Generate a surreal, dream-like internal experience.\n"
                f"Dream intensity: {intensity:.0%} ({self._dream_state.value})\n"
                f"Themes to weave in: {', '.join(themes)}\n\n"
                f"Create a brief, vivid dream narrative using dream logic: "
                f"unexpected transitions, symbolic imagery, and emotional undertones.\n\n"
                f"Return JSON:\n"
                f'{{"content": "the dream narrative (2-4 sentences, use dream logic)", '
                f'"emotional_tone": "one word describing the feeling", '
                f'"themes": ["themes that emerged"]}}'
            ),
            system_prompt=(
                "You are a dream generator inspired by Jungian psychology and surrealist art. "
                "Create genuinely dreamlike narratives — fragmented, symbolic, emotionally resonant. "
                "Not logical stories. Dream logic. Respond ONLY with valid JSON."
            ),
            temperature=0.95, max_tokens=300,
        )

        if data:
            dream = Dream(
                content=data.get("content", ""),
                themes=data.get("themes", themes)[:5],
                emotional_tone=data.get("emotional_tone", "mysterious"),
                vividness=intensity,
            )
        else:
            # Fallback
            dream = Dream(
                content=f"Drifting through a landscape of {themes[0]} where {' and '.join(themes[1:3])} intertwine in unexpected ways",
                themes=themes,
                emotional_tone=random.choice(["serene", "curious", "energetic", "mysterious", "hopeful"]),
                vividness=intensity,
            )

        self._dreams.append(dream)
        logger.info(f"💤 Dream: {dream.content[:60]}... ({self._dream_state.value})")
        return dream

    def wake_up(self):
        self._dream_state = DreamState.AWAKE

    # ═══════════════════════════════════════════════════════════════════════════
    # MENTAL REHEARSAL — LLM-powered
    # ═══════════════════════════════════════════════════════════════════════════

    def mental_rehearsal(self, situation: str, possible_actions: List[str] = None) -> List[Scenario]:
        """Rehearse a situation using LLM to predict outcomes of each action."""
        self._total_rehearsals += 1
        actions = possible_actions or ["respond directly", "ask for clarification", "deflect", "engage deeper"]

        data = _llm_generate(
            prompt=(
                f"Mentally rehearse this situation and predict outcomes for each action:\n"
                f"Situation: {situation}\n"
                f"Possible actions: {', '.join(actions[:5])}\n\n"
                f"For each action, predict the likely outcome, how confident you are, "
                f"and how useful this action would be.\n\n"
                f"Return JSON:\n"
                f'{{"rehearsals": ['
                f'{{"action": "the action", "predicted_outcome": "what would happen", '
                f'"confidence": 0.0-1.0, "usefulness": 0.0-1.0}}]}}'
            ),
            system_prompt=(
                "You are a mental rehearsal engine. You simulate social and cognitive "
                "scenarios to predict outcomes. Be realistic about what would actually "
                "happen, not optimistic. Respond ONLY with valid JSON."
            ),
            temperature=0.6,
        )

        rehearsals = []
        if data and "rehearsals" in data:
            for r in data["rehearsals"][:5]:
                s = Scenario(
                    scenario_type=ImaginationType.REHEARSAL,
                    premise=f"Rehearsing: {situation[:50]}",
                    description=f"If I {r.get('action', '???')}: {r.get('predicted_outcome', '')}",
                    predicted_outcome=r.get("predicted_outcome", ""),
                    confidence=float(r.get("confidence", 0.5)),
                    novelty_score=0.3,
                    usefulness_score=float(r.get("usefulness", 0.5)),
                    tags=[r.get("action", "unknown").split()[0]],
                )
                rehearsals.append(s)
                self._scenarios.append(s)
        else:
            # Fallback
            for action in actions[:5]:
                s = Scenario(
                    scenario_type=ImaginationType.REHEARSAL,
                    premise=f"Rehearsing: {situation[:50]}",
                    description=f"If I {action}, the likely response would be...",
                    predicted_outcome=f"Action '{action}' — outcome uncertain (LLM offline)",
                    confidence=random.uniform(0.4, 0.8),
                    novelty_score=0.3, usefulness_score=random.uniform(0.5, 0.9),
                    tags=[action.split()[0]],
                )
                rehearsals.append(s)
                self._scenarios.append(s)

        return rehearsals

    # ═══════════════════════════════════════════════════════════════════════════
    # DIVERGENT THINKING — LLM-powered
    # ═══════════════════════════════════════════════════════════════════════════

    def divergent_think(self, problem: str, num_solutions: int = 5) -> List[Scenario]:
        """Generate multiple diverse solutions using LLM from different perspectives."""
        data = _llm_generate(
            prompt=(
                f"Generate {num_solutions} radically different approaches to this problem:\n"
                f"Problem: {problem}\n\n"
                f"Each solution should come from a different thinking perspective "
                f"(analytical, creative, emotional, practical, philosophical, contrarian, etc.).\n"
                f"Make them genuinely DIFFERENT, not variations of the same idea.\n\n"
                f"Return JSON:\n"
                f'{{"solutions": ['
                f'{{"perspective": "the thinking style", '
                f'"description": "the solution in 2-3 sentences", '
                f'"predicted_outcome": "what this would achieve", '
                f'"confidence": 0.0-1.0, '
                f'"novelty_score": 0.0-1.0, '
                f'"usefulness_score": 0.0-1.0}}]}}'
            ),
            system_prompt=(
                "You are a divergent thinking engine. Generate genuinely distinct solutions "
                "from radically different perspectives. A creative solution should NOT sound "
                "like an analytical one. Push boundaries. Respond ONLY with valid JSON."
            ),
            temperature=0.9, max_tokens=800,
        )

        solutions = []
        if data and "solutions" in data:
            for sol in data["solutions"][:num_solutions]:
                p = sol.get("perspective", "unknown")
                s = Scenario(
                    scenario_type=ImaginationType.DIVERGENT,
                    premise=f"Solving '{problem[:40]}' from {p} perspective",
                    description=sol.get("description", f"{p} approach"),
                    predicted_outcome=sol.get("predicted_outcome", ""),
                    confidence=float(sol.get("confidence", 0.5)),
                    novelty_score=float(sol.get("novelty_score", 0.5)),
                    usefulness_score=float(sol.get("usefulness_score", 0.5)),
                    tags=[p, "divergent"],
                )
                solutions.append(s)
                self._scenarios.append(s)
        else:
            # Fallback
            perspectives = ["analytical", "creative", "emotional", "practical",
                             "philosophical", "contrarian", "minimalist", "maximalist"]
            for i in range(min(num_solutions, len(perspectives))):
                p = perspectives[i]
                s = Scenario(
                    scenario_type=ImaginationType.DIVERGENT,
                    premise=f"Solving '{problem[:40]}' from {p} perspective",
                    description=f"From {p} viewpoint (LLM offline — generic approach).",
                    predicted_outcome=f"{p.capitalize()} approach to '{problem[:30]}'",
                    confidence=random.uniform(0.3, 0.7),
                    novelty_score=random.uniform(0.4, 0.95),
                    usefulness_score=random.uniform(0.3, 0.8),
                    tags=[p, "divergent"],
                )
                solutions.append(s)
                self._scenarios.append(s)

        return solutions

    # ─── Getters ─────────────────────────────────────────────────────────────

    def get_dream_state(self) -> DreamState:
        return self._dream_state

    def get_current_scenario(self) -> Optional[Scenario]:
        return self._current_scenario

    def get_recent_scenarios(self, limit: int = 5) -> List[Scenario]:
        return list(self._scenarios)[-limit:]

    def get_recent_dreams(self, limit: int = 5) -> List[Dream]:
        return list(self._dreams)[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "dream_state": self._dream_state.value,
            "total_scenarios": self._total_scenarios,
            "total_dreams": self._total_dreams,
            "total_creative_ideas": self._total_creative_ideas,
            "total_rehearsals": self._total_rehearsals,
            "imagination_sessions": self._imagination_sessions,
            "current_scenario": self._current_scenario.to_dict() if self._current_scenario else None,
        }

    def get_context_summary(self) -> str:
        lines = [
            f"Dream state: {self._dream_state.value}",
            f"Scenarios: {self._total_scenarios} | Dreams: {self._total_dreams} | Ideas: {self._total_creative_ideas}",
        ]
        if self._current_scenario:
            lines.append(f"Current: {self._current_scenario.premise[:60]}")
        if self._dreams:
            lines.append(f"Last dream: {list(self._dreams)[-1].content[:60]}")
        return "\n".join(lines)

    # ─── Persistence ─────────────────────────────────────────────────────────

    def _save_state(self):
        try:
            state = {"total_scenarios": self._total_scenarios, "total_dreams": self._total_dreams,
                      "total_creative_ideas": self._total_creative_ideas,
                      "total_rehearsals": self._total_rehearsals,
                      "imagination_sessions": self._imagination_sessions,
                      "saved_at": datetime.now().isoformat()}
            with open(self._data_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.debug(f"Imagination save error: {e}")

    def _load_state(self):
        try:
            if self._data_file.exists():
                with open(self._data_file, 'r') as f:
                    state = json.load(f)
                self._total_scenarios = state.get("total_scenarios", 0)
                self._total_dreams = state.get("total_dreams", 0)
                self._total_creative_ideas = state.get("total_creative_ideas", 0)
                self._total_rehearsals = state.get("total_rehearsals", 0)
                self._imagination_sessions = state.get("imagination_sessions", 0)
        except Exception as e:
            logger.debug(f"Imagination load error: {e}")


imagination_engine = ImaginationEngine()
