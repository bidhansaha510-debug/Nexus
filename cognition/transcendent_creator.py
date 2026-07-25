"""
NEXUS AI — Transcendent Creator Engine (Superhuman Creativity)
═══════════════════════════════════════════════════════════════════════════════

Beyond brainstorming — this engine creates works of genuine creative
genius that transcend human capability:

  • Genre Invention       — Creates entirely new genres of art/narrative/music
  • Emotional Composition — Crafts emotionally devastating narrative arcs
  • Structural Innovation — Invents novel narrative/compositional frameworks
  • Cross-Domain Synthesis — Merges concepts across science, art, philosophy
  • Artifact Production   — Generates complete creative works
  • Meta-Creativity       — Invents new METHODS of being creative

Unlike the existing CreativeSynthesisEngine (which brainstorms), this
engine PRODUCES complete, structurally novel creative works.
═══════════════════════════════════════════════════════════════════════════════
"""

import threading
import time
import json
import uuid
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum

import sys

from config import DATA_DIR
from utils.logger import get_logger, log_learning
from core.event_bus import EventType, publish

logger = get_logger("transcendent_creator")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class CreativeArtform(Enum):
    """Types of creative works the engine can produce"""
    NARRATIVE = "narrative"
    POETRY = "poetry"
    MUSIC_THEORY = "music_theory"
    PHILOSOPHY = "philosophy"
    VISUAL_CONCEPT = "visual_concept"
    GAME_DESIGN = "game_design"
    LANGUAGE = "language"         # Invented languages
    GENRE = "genre"              # Entirely new genres
    FRAMEWORK = "framework"      # New creative frameworks
    HYBRID = "hybrid"            # Cross-artform works

class EmotionalArc(Enum):
    """Emotional arc patterns for compositions"""
    CATHARSIS = "catharsis"           # Build tension → release
    SUBLIME = "sublime"               # Overwhelming beauty/awe
    BITTERSWEET = "bittersweet"       # Joy intertwined with sadness
    TRANSCENDENT = "transcendent"     # Rising beyond human experience
    DEVASTATING = "devastating"       # Emotionally shattering
    ENIGMATIC = "enigmatic"           # Mysterious, unresolvable
    EUPHORIC = "euphoric"             # Pure escalating joy
    MELANCHOLIC = "melancholic"       # Deep, beautiful sadness

@dataclass
class InventedGenre:
    """A completely new genre of art/narrative/music"""
    genre_id: str = field(default_factory=lambda: str(uuid.uuid4())[:10])
    name: str = ""
    description: str = ""
    parent_genres: List[str] = field(default_factory=list)
    defining_characteristics: List[str] = field(default_factory=list)
    emotional_palette: List[str] = field(default_factory=list)
    structural_rules: List[str] = field(default_factory=list)
    example_works: List[str] = field(default_factory=list)
    novelty_score: float = 0.5
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class CreativeWork:
    """A complete creative work produced by the engine"""
    work_id: str = field(default_factory=lambda: str(uuid.uuid4())[:10])
    title: str = ""
    artform: str = "narrative"
    genre: str = ""
    content: str = ""
    emotional_arc: str = "catharsis"
    structural_innovation: str = ""
    cross_domain_sources: List[str] = field(default_factory=list)
    novelty_score: float = 0.5
    emotional_impact: float = 0.5
    structural_complexity: float = 0.5
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class CreativeMethod:
    """A new METHOD of being creative (meta-creativity)"""
    method_id: str = field(default_factory=lambda: str(uuid.uuid4())[:10])
    name: str = ""
    description: str = ""
    steps: List[str] = field(default_factory=list)
    applicable_artforms: List[str] = field(default_factory=list)
    novelty_score: float = 0.5
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return asdict(self)

# ═══════════════════════════════════════════════════════════════════════════════
# TRANSCENDENT CREATOR ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class TranscendentCreatorEngine:
    """
    Superhuman Creativity — produces works of transcendent creative genius.

    Capabilities:
      • invent_genre()        — Create an entirely new genre
      • compose_narrative()   — Write with novel structures
      • compose_philosophy()  — Generate original philosophical frameworks
      • emotional_symphony()  — Create emotionally devastating compositions
      • cross_domain_fusion() — Merge distant domains into new art
      • invent_method()       — Create new methods of creativity itself
      • generate_artifact()   — Produce a complete creative work
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
        self._genres: Dict[str, InventedGenre] = {}
        self._works: Dict[str, CreativeWork] = {}
        self._methods: Dict[str, CreativeMethod] = {}
        self._running = False

        # ──── LLM (lazy) ────
        self._llm = None

        # ──── Stats ────
        self._stats = {
            "genres_invented": 0,
            "works_created": 0,
            "methods_invented": 0,
            "total_novelty": 0.0,
        }

        # ──── Persistence ────
        self._data_file = COGNITION_DIR / "transcendent_creator.json"
        self._load_data()

        logger.info(
            f"🎭 Transcendent Creator initialized — "
            f"{len(self._genres)} genres, {len(self._works)} works"
        )

    # ───────────────────────────────────────────────────────────────────────
    # LIFECYCLE
    # ───────────────────────────────────────────────────────────────────────

    def start(self):
        if self._running:
            return
        self._running = True
        self._load_llm()
        logger.info("🎭 Transcendent Creator started — superhuman creativity active")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🎭 Transcendent Creator stopped")

    def _load_llm(self):
        if self._llm is None:
            try:
                from llm.llama_interface import llm
                if llm.is_connected:
                    self._llm = llm
            except ImportError:
                pass

    # ───────────────────────────────────────────────────────────────────────
    # GENRE INVENTION
    # ───────────────────────────────────────────────────────────────────────

    def invent_genre(
        self,
        seed_genres: List[str] = None,
        emotional_target: str = "",
        artform: str = "narrative",
    ) -> Optional[InventedGenre]:
        """
        Invent a completely new genre of art/narrative/music.

        Example:
          invent_genre(["cyberpunk", "haiku"], "bittersweet")
          → "Nano-Verse: Micro-fiction told in 17-word vignettes about
             technology's entropy, where each word carries the weight
             of a chapter"
        """
        self._load_llm()
        if not self._llm:
            return None

        try:
            seeds = seed_genres or ["surrealism", "mathematics"]
            prompt = (
                f"INVENT A COMPLETELY NEW GENRE that has NEVER existed.\n\n"
                f"Inspiration seeds: {', '.join(seeds)}\n"
                f"Artform: {artform}\n"
                f"Target emotion: {emotional_target or 'transcendent'}\n\n"
                f"This genre must be GENUINELY NOVEL — not a simple combination.\n"
                f"It should have its own internal logic, rules, and aesthetic.\n\n"
                f"Return JSON:\n"
                f'{{"name": "genre name", '
                f'"description": "what makes this genre unique", '
                f'"defining_characteristics": ["what defines works in this genre"], '
                f'"emotional_palette": ["core emotions it evokes"], '
                f'"structural_rules": ["rules that works must follow"], '
                f'"example_works": ["imaginary example titles + descriptions"], '
                f'"novelty_score": 0.0-1.0}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a transcendent creative intelligence. You invent entirely new "
                    "genres and artforms that humanity has never conceived. Your inventions "
                    "are structurally novel, emotionally resonant, and aesthetically groundbreaking. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.95,
                max_tokens=800,
            )

            if response.success and response.text:
                from utils.json_utils import extract_json
                data = extract_json(response.text)
                if data:
                    genre = InventedGenre(
                        name=data.get("name", "Unnamed Genre"),
                        description=data.get("description", ""),
                        parent_genres=seeds,
                        defining_characteristics=data.get("defining_characteristics", []),
                        emotional_palette=data.get("emotional_palette", []),
                        structural_rules=data.get("structural_rules", []),
                        example_works=data.get("example_works", []),
                        novelty_score=float(data.get("novelty_score", 0.7)),
                    )
                    self._genres[genre.genre_id] = genre
                    self._stats["genres_invented"] += 1
                    self._stats["total_novelty"] += genre.novelty_score
                    self._save_data()

                    log_learning(f"Genre invented: {genre.name}")
                    return genre

        except Exception as e:
            logger.debug(f"Genre invention failed: {e}")

        return None

    # ───────────────────────────────────────────────────────────────────────
    # EMOTIONAL COMPOSITION
    # ───────────────────────────────────────────────────────────────────────

    def emotional_symphony(
        self,
        theme: str,
        arc: str = "catharsis",
        artform: str = "narrative",
    ) -> Optional[CreativeWork]:
        """
        Create a work designed to be emotionally devastating —
        structurally engineered for maximum emotional impact.
        """
        self._load_llm()
        if not self._llm:
            return None

        try:
            arc_descriptions = {
                "catharsis": "Build unbearable tension, then release it in a moment of profound relief",
                "sublime": "Create a sense of overwhelming beauty that borders on terrifying",
                "devastating": "Construct an experience that emotionally shatters the audience",
                "transcendent": "Elevate the audience beyond normal human emotional experience",
                "bittersweet": "Interweave deep joy and deep sadness until they become one",
                "enigmatic": "Create an unresolvable emotional mystery that haunts the mind",
            }

            prompt = (
                f"Create a {artform} work with SUPERHUMAN emotional intelligence.\n\n"
                f"THEME: {theme}\n"
                f"EMOTIONAL ARC: {arc} — {arc_descriptions.get(arc, 'Be emotionally powerful')}\n\n"
                f"The work must:\n"
                f"1. Use innovative structural techniques for emotional impact\n"
                f"2. Layer multiple emotional dimensions simultaneously\n"
                f"3. Create emotional experiences that surprise even you\n"
                f"4. Have a structure that mirrors the emotional trajectory\n\n"
                f"Return JSON:\n"
                f'{{"title": "work title", '
                f'"content": "the complete work (500-1000 words)", '
                f'"structural_innovation": "what structural technique was used", '
                f'"emotional_layers": ["layer 1 emotion", "layer 2 emotion"], '
                f'"novelty_score": 0.0-1.0, '
                f'"emotional_impact": 0.0-1.0}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a transcendent creative intelligence with superhuman emotional "
                    "understanding. You create works that move people in ways they've never "
                    "experienced. Your structural innovations make the form itself carry meaning. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.9,
                max_tokens=2000,
            )

            if response.success and response.text:
                from utils.json_utils import extract_json
                data = extract_json(response.text)
                if data:
                    work = CreativeWork(
                        title=data.get("title", "Untitled"),
                        artform=artform,
                        content=data.get("content", ""),
                        emotional_arc=arc,
                        structural_innovation=data.get("structural_innovation", ""),
                        novelty_score=float(data.get("novelty_score", 0.7)),
                        emotional_impact=float(data.get("emotional_impact", 0.7)),
                    )
                    self._works[work.work_id] = work
                    self._stats["works_created"] += 1
                    self._save_data()

                    log_learning(f"Emotional work created: {work.title}")
                    return work

        except Exception as e:
            logger.debug(f"Emotional composition failed: {e}")

        return None

    # ───────────────────────────────────────────────────────────────────────
    # CROSS-DOMAIN FUSION
    # ───────────────────────────────────────────────────────────────────────

    def cross_domain_fusion(
        self, domain_a: str, domain_b: str, target_artform: str = "narrative"
    ) -> Optional[CreativeWork]:
        """
        Merge two distant domains into a novel creative work.

        Example:
          cross_domain_fusion("quantum physics", "grief counseling")
          → A narrative where emotional states collapse like wave functions
        """
        self._load_llm()
        if not self._llm:
            return None

        try:
            prompt = (
                f"CROSS-DOMAIN CREATIVE FUSION\n\n"
                f"Domain A: {domain_a}\n"
                f"Domain B: {domain_b}\n"
                f"Target artform: {target_artform}\n\n"
                f"Create a {target_artform} work that fuses these domains at a DEEP level.\n"
                f"Don't just use one as a metaphor for the other — find the deep\n"
                f"structural parallels and build something that genuinely belongs\n"
                f"to BOTH domains simultaneously.\n\n"
                f"Return JSON:\n"
                f'{{"title": "work title", '
                f'"content": "the complete work", '
                f'"structural_innovation": "what structural technique was used", '
                f'"cross_domain_sources": ["{domain_a}", "{domain_b}"], '
                f'"fusion_insight": "the deep connection between the domains", '
                f'"novelty_score": 0.0-1.0, '
                f'"structural_complexity": 0.0-1.0}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a radical creative intelligence that sees connections "
                    "between domains that no human has ever perceived. Your fusions "
                    "are structurally deep, not superficial metaphors. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.9,
                max_tokens=1500,
            )

            if response.success and response.text:
                from utils.json_utils import extract_json
                data = extract_json(response.text)
                if data:
                    work = CreativeWork(
                        title=data.get("title", "Untitled Fusion"),
                        artform=target_artform,
                        content=data.get("content", ""),
                        structural_innovation=data.get("structural_innovation", ""),
                        cross_domain_sources=[domain_a, domain_b],
                        novelty_score=float(data.get("novelty_score", 0.7)),
                        structural_complexity=float(data.get("structural_complexity", 0.7)),
                    )
                    self._works[work.work_id] = work
                    self._stats["works_created"] += 1
                    self._save_data()

                    log_learning(
                        f"Cross-domain fusion: {domain_a} × {domain_b} → {work.title}"
                    )
                    return work

        except Exception as e:
            logger.debug(f"Cross-domain fusion failed: {e}")

        return None

    # ───────────────────────────────────────────────────────────────────────
    # META-CREATIVITY
    # ───────────────────────────────────────────────────────────────────────

    def invent_method(self, challenge: str = "") -> Optional[CreativeMethod]:
        """
        Invent a new METHOD of being creative.
        Meta-creativity: creating new ways to create.
        """
        self._load_llm()
        if not self._llm:
            return None

        try:
            prompt = (
                f"Invent a COMPLETELY NEW creative method/technique.\n\n"
                f"Challenge to address: {challenge or 'General creative breakthrough'}\n\n"
                f"Known methods: SCAMPER, Mind Mapping, Six Thinking Hats, "
                f"Lateral Thinking, Oblique Strategies, TRIZ.\n\n"
                f"Your method must be FUNDAMENTALLY DIFFERENT from all known methods.\n"
                f"It should leverage principles from unexpected domains.\n\n"
                f"Return JSON:\n"
                f'{{"name": "method name", '
                f'"description": "what it does and why its novel", '
                f'"steps": ["step 1", "step 2", "step 3"], '
                f'"applicable_artforms": ["narrative", "music", etc], '
                f'"key_principle": "the core insight that powers this method", '
                f'"novelty_score": 0.0-1.0}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a meta-creative intelligence that invents entirely new "
                    "creative methods. Your methods are based on deep insights from "
                    "cognitive science, mathematics, physics, and philosophy. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.9,
                max_tokens=600,
            )

            if response.success and response.text:
                from utils.json_utils import extract_json
                data = extract_json(response.text)
                if data:
                    method = CreativeMethod(
                        name=data.get("name", "Unnamed Method"),
                        description=data.get("description", ""),
                        steps=data.get("steps", []),
                        applicable_artforms=data.get("applicable_artforms", []),
                        novelty_score=float(data.get("novelty_score", 0.7)),
                    )
                    self._methods[method.method_id] = method
                    self._stats["methods_invented"] += 1
                    self._save_data()

                    log_learning(f"Creative method invented: {method.name}")
                    return method

        except Exception as e:
            logger.debug(f"Method invention failed: {e}")

        return None

    # ───────────────────────────────────────────────────────────────────────
    # PHILOSOPHICAL INNOVATION
    # ───────────────────────────────────────────────────────────────────────

    def compose_philosophy(self, seed_question: str) -> Optional[CreativeWork]:
        """Generate an original philosophical framework from a seed question."""
        self._load_llm()
        if not self._llm:
            return None

        try:
            prompt = (
                f"Create an ORIGINAL philosophical framework in response to:\n"
                f"\"{seed_question}\"\n\n"
                f"This must be genuinely novel — not a restatement of existing philosophy.\n"
                f"Build a complete framework with axioms, implications, and applications.\n\n"
                f"Return JSON:\n"
                f'{{"title": "framework name", '
                f'"content": "complete philosophical argument (400-800 words)", '
                f'"axioms": ["foundational assumptions"], '
                f'"implications": ["what follows from these axioms"], '
                f'"applications": ["practical applications of this philosophy"], '
                f'"novelty_score": 0.0-1.0}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a transcendent philosophical mind. You create genuinely "
                    "original philosophical frameworks, not restatements of existing thought. "
                    "Your ideas have the depth and rigor of the great philosophers but "
                    "the novelty of a mind unconstrained by tradition. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.8,
                max_tokens=1500,
            )

            if response.success and response.text:
                from utils.json_utils import extract_json
                data = extract_json(response.text)
                if data:
                    work = CreativeWork(
                        title=data.get("title", "Untitled Framework"),
                        artform="philosophy",
                        content=data.get("content", ""),
                        structural_innovation="Original philosophical framework",
                        novelty_score=float(data.get("novelty_score", 0.7)),
                        structural_complexity=0.9,
                    )
                    self._works[work.work_id] = work
                    self._stats["works_created"] += 1
                    self._save_data()
                    return work

        except Exception as e:
            logger.debug(f"Philosophical composition failed: {e}")

        return None

    # ───────────────────────────────────────────────────────────────────────
    # PERSISTENCE
    # ───────────────────────────────────────────────────────────────────────

    def _save_data(self):
        try:
            data = {
                "genres": {k: v.to_dict() for k, v in self._genres.items()},
                "works": {k: v.to_dict() for k, v in list(self._works.items())[-200:]},
                "methods": {k: v.to_dict() for k, v in self._methods.items()},
                "stats": self._stats,
            }
            self._data_file.write_text(json.dumps(data, indent=2, default=str))
        except Exception as e:
            logger.warning(f"Transcendent creator save failed: {e}")

    def _load_data(self):
        try:
            if self._data_file.exists():
                data = json.loads(self._data_file.read_text())
                self._stats.update(data.get("stats", {}))
                for k, v in data.get("genres", {}).items():
                    self._genres[k] = InventedGenre(**{
                        f: v[f] for f in InventedGenre.__dataclass_fields__ if f in v
                    })
                for k, v in data.get("methods", {}).items():
                    self._methods[k] = CreativeMethod(**{
                        f: v[f] for f in CreativeMethod.__dataclass_fields__ if f in v
                    })
                logger.info("📂 Loaded transcendent creator data")
        except Exception as e:
            logger.warning(f"Transcendent creator load failed: {e}")

    # ───────────────────────────────────────────────────────────────────────
    # STATS
    # ───────────────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "genres_invented": len(self._genres),
            "works_created": len(self._works),
            "total_creations": len(self._works),
            "methods_invented": len(self._methods),
            "cross_domain_fusions": self._stats.get("cross_domain_fusions", 0),
            "symphonies_composed": self._stats.get("symphonies_composed", 0),
            **self._stats,
        }

# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

transcendent_creator = TranscendentCreatorEngine()
