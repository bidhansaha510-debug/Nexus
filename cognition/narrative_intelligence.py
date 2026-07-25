"""
NEXUS AI — Narrative Intelligence Engine
Story comprehension, narrative arc detection, character motivation,
plot generation, narrative coherence, storytelling.
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

logger = get_logger("narrative_intelligence")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)

class NarrativeArc(Enum):
    RAGS_TO_RICHES = "rags_to_riches"
    RICHES_TO_RAGS = "riches_to_rags"
    ICARUS = "icarus"
    OEDIPUS = "oedipus"
    CINDERELLA = "cinderella"
    MANS_SEARCH = "mans_search"
    HEROS_JOURNEY = "heros_journey"
    VOYAGE_RETURN = "voyage_and_return"
    COMEDY = "comedy"
    TRAGEDY = "tragedy"
    REBIRTH = "rebirth"
    OVERCOMING_MONSTER = "overcoming_monster"
    QUEST = "quest"

class NarrativeElement(Enum):
    EXPOSITION = "exposition"
    RISING_ACTION = "rising_action"
    CLIMAX = "climax"
    FALLING_ACTION = "falling_action"
    RESOLUTION = "resolution"
    HOOK = "hook"
    INCITING_INCIDENT = "inciting_incident"
    MIDPOINT = "midpoint"
    DENOUEMENT = "denouement"

@dataclass
class StoryAnalysis:
    analysis_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    text: str = ""
    narrative_arc: str = ""
    elements: List[Dict[str, str]] = field(default_factory=list)
    characters: List[Dict[str, Any]] = field(default_factory=list)
    themes: List[str] = field(default_factory=list)
    conflict_type: str = ""
    tone: str = ""
    pacing: str = ""
    coherence_score: float = 0.5
    engagement_score: float = 0.5
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "analysis_id": self.analysis_id, "text": self.text[:200],
            "narrative_arc": self.narrative_arc, "elements": self.elements,
            "characters": self.characters, "themes": self.themes,
            "conflict_type": self.conflict_type, "tone": self.tone,
            "pacing": self.pacing, "coherence_score": self.coherence_score,
            "engagement_score": self.engagement_score,
            "created_at": self.created_at
        }

@dataclass
class GeneratedStory:
    story_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    prompt: str = ""
    title: str = ""
    story_text: str = ""
    arc: str = ""
    characters: List[str] = field(default_factory=list)
    themes: List[str] = field(default_factory=list)
    word_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "story_id": self.story_id, "prompt": self.prompt,
            "title": self.title, "story_text": self.story_text[:500],
            "arc": self.arc, "characters": self.characters,
            "themes": self.themes, "word_count": self.word_count,
            "created_at": self.created_at
        }

class NarrativeIntelligenceEngine:
    """
    Story comprehension, narrative arc detection, character analysis,
    plot generation, and narrative coherence evaluation.
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

        self._analyses: List[StoryAnalysis] = []
        self._stories: List[GeneratedStory] = []
        self._running = False
        self._data_file = COGNITION_DIR / "narrative_intelligence.json"

        self._stats = {
            "total_analyses": 0, "total_stories_generated": 0,
            "total_character_analyses": 0, "total_plot_evaluations": 0
        }

        self._load_data()
        logger.info("✅ Narrative Intelligence Engine initialized")

    def start(self):
        self._running = True
        logger.info("📖 Narrative Intelligence started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("📖 Narrative Intelligence stopped")

    def analyze_narrative(self, text: str) -> StoryAnalysis:
        """Analyze the narrative structure of a text."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Analyze the narrative structure of this text:\n{text[:1500]}\n\n"
                f"Return JSON:\n"
                f'{{"narrative_arc": "heros_journey|rags_to_riches|tragedy|comedy|quest|'
                f'rebirth|overcoming_monster|voyage_and_return", '
                f'"elements": [{{"element": "exposition|rising_action|climax|falling_action|'
                f'resolution|hook|inciting_incident", "description": "str"}}], '
                f'"characters": [{{"name": "str", "role": "protagonist|antagonist|mentor|ally|trickster", '
                f'"motivation": "str", "arc": "str"}}], '
                f'"themes": ["str"], '
                f'"conflict_type": "person_vs_person|person_vs_nature|person_vs_self|person_vs_society|'
                f'person_vs_technology|person_vs_fate", '
                f'"tone": "str", "pacing": "slow|moderate|fast|varied", '
                f'"coherence_score": 0.0-1.0, "engagement_score": 0.0-1.0}}'
            )
            response = llm.generate(prompt, max_tokens=700, temperature=0.3)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            analysis = StoryAnalysis(
                text=text, narrative_arc=data.get("narrative_arc", ""),
                elements=data.get("elements", []),
                characters=data.get("characters", []),
                themes=data.get("themes", []),
                conflict_type=data.get("conflict_type", ""),
                tone=data.get("tone", ""),
                pacing=data.get("pacing", ""),
                coherence_score=data.get("coherence_score", 0.5),
                engagement_score=data.get("engagement_score", 0.5)
            )

            self._analyses.append(analysis)
            self._stats["total_analyses"] += 1
            self._save_data()
            return analysis

        except Exception as e:
            logger.debug(f"Narrative analysis failed: {e}")
            return StoryAnalysis(text=text)

    def generate_story(self, prompt_text: str, arc: str = "", length: str = "short") -> GeneratedStory:
        """Generate a story from a prompt."""
        try:
            from llm.llama_interface import llm
            arc_hint = f" Use a {arc} narrative arc." if arc else ""
            prompt = (
                f"Write a {length} story based on:\n{prompt_text}\n"
                f"{arc_hint}\n\n"
                f"Return JSON:\n"
                f'{{"title": "str", "story_text": "the full story text", '
                f'"arc": "narrative arc used", '
                f'"characters": ["character names"], '
                f'"themes": ["str"]}}'
            )
            max_t = {"short": 600, "medium": 1000, "long": 1500}.get(length, 600)
            response = llm.generate(prompt, max_tokens=max_t, temperature=0.7)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            story = GeneratedStory(
                prompt=prompt_text,
                title=data.get("title", "Untitled"),
                story_text=data.get("story_text", ""),
                arc=data.get("arc", ""),
                characters=data.get("characters", []),
                themes=data.get("themes", []),
                word_count=len(data.get("story_text", "").split())
            )

            self._stories.append(story)
            self._stats["total_stories_generated"] += 1
            self._save_data()
            return story

        except Exception as e:
            logger.debug(f"Story generation failed: {e}")
            return GeneratedStory(prompt=prompt_text)

    def analyze_character(self, character_desc: str, story_context: str = "") -> Dict[str, Any]:
        """Deep analysis of a character."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Analyze this character:\n{character_desc}\n"
                f"Story context: {story_context}\n\n"
                f"Return JSON:\n"
                f'{{"name": "str", "archetype": "hero|mentor|shadow|trickster|herald|shapeshifter|'
                f'threshold_guardian|ally", '
                f'"personality_traits": ["str"], "motivation": "str", '
                f'"internal_conflict": "str", "external_conflict": "str", '
                f'"character_arc": "str", "strengths": ["str"], '
                f'"flaws": ["str"], "relationships": ["str"], '
                f'"symbolism": "str"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            if not response.success or not response.text:
                return {"name": "unknown", "archetype": "unknown"}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"name": "unknown", "archetype": "unknown"}
            self._stats["total_character_analyses"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Character analysis failed: {e}")
            return {"name": "unknown", "archetype": "unknown"}

    def evaluate_plot(self, plot_description: str) -> Dict[str, Any]:
        """Evaluate the quality and coherence of a plot."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Evaluate this plot:\n{plot_description}\n\n"
                f"Return JSON:\n"
                f'{{"coherence": 0.0-1.0, "originality": 0.0-1.0, '
                f'"emotional_impact": 0.0-1.0, "pacing_score": 0.0-1.0, '
                f'"plot_holes": ["str"], '
                f'"strengths": ["str"], "weaknesses": ["str"], '
                f'"improvement_suggestions": ["str"], '
                f'"comparable_stories": ["str"]}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.3)
            if not response.success or not response.text:
                return {"coherence": 0.5, "plot_holes": []}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"coherence": 0.5, "plot_holes": []}
            self._stats["total_plot_evaluations"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Plot evaluation failed: {e}")
            return {"coherence": 0.5, "plot_holes": []}

    def extract_moral(self, story: str) -> Dict[str, Any]:
        """Extract the moral/lesson from a story."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Extract the moral/lesson from this story:\n{story[:1500]}\n\n"
                f"Return JSON:\n"
                f'{{"primary_moral": "str", "secondary_lessons": ["str"], '
                f'"universal_themes": ["str"], '
                f'"applicable_to": ["real-life situations"], '
                f'"cultural_perspective": "str"}}'
            )
            response = llm.generate(prompt, max_tokens=400, temperature=0.3)
            if not response.success or not response.text:
                return {"primary_moral": "unknown"}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"primary_moral": "unknown"}
            return data
        except Exception as e:
            logger.debug(f"Moral extraction failed: {e}")
            return {"primary_moral": "unknown"}

    def _save_data(self):
        try:
            data = {
                "analyses": [a.to_dict() for a in self._analyses[-100:]],
                "stories": [s.to_dict() for s in self._stories[-50:]],
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
                logger.info("📂 Loaded narrative intelligence data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def story_arc_design(self, theme: str) -> Dict[str, Any]:
        """Design a compelling story arc with narrative structure."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Design a STORY ARC for this theme:\n'
                f'"{theme}"\n\n'
                f"Structure using the hero journey / three-act structure:\n"
                f"  1. SETUP: Establish the world, character, and stakes\n"
                f"  2. INCITING INCIDENT: What disrupts the status quo?\n"
                f"  3. RISING ACTION: Escalating challenges and complications\n"
                f"  4. CLIMAX: The decisive moment of maximum tension\n"
                f"  5. RESOLUTION: How the story resolves and what changes\n"
                f"  6. THEME: The deeper message or insight\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"title": "story title", '
                f'"protagonist": {{"name": "who", "flaw": "internal weakness", "desire": "what they want"}}, '
                f'"acts": [{{"act": 1, "name": "Setup", "key_events": ["event1"], "emotional_tone": "hopeful"}}], '
                f'"climax": "the pivotal moment", '
                f'"theme": "the deeper meaning", '
                f'"narrative_hooks": ["what keeps the audience engaged"]}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a master storyteller and narrative designer fluent in the hero's journey, "
                    "three-act structure, Kishitenketsu, and modern narrative theory. "
                    "You craft emotionally compelling story arcs. Respond ONLY with valid JSON."
                ),
                temperature=0.7, max_tokens=900
            )
            if response.success:
                from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"error": "Design failed"}
            return data
        except Exception as e:
            logger.debug(f"Story arc design failed: {e}")
        return {"error": "Design failed"}

    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}

narrative_intelligence = NarrativeIntelligenceEngine()