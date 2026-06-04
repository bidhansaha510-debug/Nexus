"""
NEXUS AI — Musical Cognition Engine
Rhythm analysis, harmony understanding, musical pattern detection,
melody structure, emotional expression through music theory.
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
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("musical_cognition")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)


class MusicalElement(Enum):
    RHYTHM = "rhythm"
    MELODY = "melody"
    HARMONY = "harmony"
    TIMBRE = "timbre"
    DYNAMICS = "dynamics"
    FORM = "form"
    TEXTURE = "texture"


@dataclass
class MusicalAnalysis:
    analysis_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    subject: str = ""
    elements: Dict[str, Any] = field(default_factory=dict)
    emotional_quality: str = ""
    complexity: float = 0.5
    genre_associations: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "analysis_id": self.analysis_id,
            "subject": self.subject[:200],
            "elements": self.elements,
            "emotional_quality": self.emotional_quality,
            "complexity": self.complexity,
            "genre_associations": self.genre_associations,
            "created_at": self.created_at
        }


class MusicalCognitionEngine:
    """
    Music theory and pattern analysis — rhythm, harmony, melody,
    emotional expression, genre classification.
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

        self._analyses: List[MusicalAnalysis] = []
        self._running = False
        self._data_file = COGNITION_DIR / "musical_cognition.json"

        self._stats = {
            "total_analyses": 0, "total_compositions": 0,
            "total_emotion_mappings": 0, "total_pattern_detections": 0
        }

        self._load_data()
        logger.info("✅ Musical Cognition Engine initialized")

    def start(self):
        self._running = True
        logger.info("🎵 Musical Cognition started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🎵 Musical Cognition stopped")

    def analyze_music(self, description: str) -> MusicalAnalysis:
        """Analyze musical elements from a description."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Analyze the musical elements of:\n{description}\n\n"
                f"Return JSON:\n"
                f'{{"elements": {{"rhythm": "description of rhythmic qualities", '
                f'"melody": "melodic characteristics", '
                f'"harmony": "harmonic analysis", '
                f'"dynamics": "volume/intensity patterns", '
                f'"form": "structural form (verse-chorus, sonata, etc)"}}, '
                f'"emotional_quality": "the emotional feel", '
                f'"complexity": 0.0-1.0, '
                f'"genre_associations": ["related genres"], '
                f'"key_signature": "likely key", '
                f'"tempo": "estimated BPM or tempo description", '
                f'"influences": ["musical influences detected"]}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            analysis = MusicalAnalysis(
                subject=description,
                elements=data.get("elements", {}),
                emotional_quality=data.get("emotional_quality", ""),
                complexity=data.get("complexity", 0.5),
                genre_associations=data.get("genre_associations", [])
            )

            self._analyses.append(analysis)
            self._stats["total_analyses"] += 1
            self._save_data()
            return analysis

        except Exception as e:
            logger.debug(f"Musical analysis failed: {e}")
            return MusicalAnalysis(subject=description)

    def emotion_to_music(self, emotion: str) -> Dict[str, Any]:
        """Map an emotion to musical characteristics."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"What musical characteristics express the emotion: {emotion}?\n\n"
                f"Return JSON:\n"
                f'{{"key": "major/minor key suggestion", '
                f'"tempo": "BPM range", '
                f'"rhythm": "rhythmic pattern", '
                f'"instruments": ["ideal instruments"], '
                f'"dynamics": "volume pattern", '
                f'"articulation": "legato/staccato/etc", '
                f'"genre_examples": ["songs that express this emotion"], '
                f'"music_theory_explanation": "why these choices work"}}'
            )
            response = llm.generate(prompt, max_tokens=400, temperature=0.5)
            if not response.success or not response.text:
                return {"key": "", "tempo": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"key": "", "tempo": ""}
            self._stats["total_emotion_mappings"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Emotion-to-music mapping failed: {e}")
            return {"key": "", "tempo": ""}

    def detect_patterns(self, musical_desc: str) -> Dict[str, Any]:
        """Detect patterns in musical structure."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Detect musical patterns in:\n{musical_desc}\n\n"
                f"Return JSON:\n"
                f'{{"patterns": [{{"type": "str", "description": "str", '
                f'"repetition_count": 0, "variation": "str"}}], '
                f'"overall_structure": "str", '
                f'"motifs": ["recurring musical ideas"], '
                f'"development_techniques": ["how patterns evolve"], '
                f'"symmetry": 0.0-1.0}}'
            )
            response = llm.generate(prompt, max_tokens=400, temperature=0.4)
            if not response.success or not response.text:
                return {"patterns": [], "overall_structure": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"patterns": [], "overall_structure": ""}
            self._stats["total_pattern_detections"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Pattern detection failed: {e}")
            return {"patterns": [], "overall_structure": ""}

    def suggest_composition(self, theme: str, mood: str = "neutral") -> Dict[str, Any]:
        """Suggest a musical composition based on theme and mood."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Suggest a musical composition:\nTheme: {theme}\nMood: {mood}\n\n"
                f"Return JSON:\n"
                f'{{"title": "str", '
                f'"key": "str", "tempo": "str", '
                f'"time_signature": "str", '
                f'"structure": ["intro", "verse", "chorus", "etc"], '
                f'"instrumentation": ["str"], '
                f'"chord_progression": ["str"], '
                f'"melodic_theme": "description of main melody", '
                f'"dynamic_arc": "how intensity changes throughout", '
                f'"similar_works": ["existing pieces with similar feel"]}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.6)
            if not response.success or not response.text:
                return {"title": "", "structure": []}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"title": "", "structure": []}
            self._stats["total_compositions"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Composition suggestion failed: {e}")
            return {"title": "", "structure": []}

    def _save_data(self):
        try:
            data = {
                "analyses": [a.to_dict() for a in self._analyses[-200:]],
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
                logger.info("📂 Loaded musical cognition data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def compose_motif(self, mood: str) -> Dict[str, Any]:
        """Compose a musical motif (short melodic phrase) based on mood."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Compose a MUSICAL MOTIF for this mood:\n'
                f'"{mood}"\n\n'
                f"Describe the motif musically:\n"
                f"  1. KEY/SCALE: What key and mode best captures this mood?\n"
                f"  2. TEMPO: BPM and feel (allegro, andante, etc.)\n"
                f"  3. MELODY: Note sequence using letter names (C D E...)\n"
                f"  4. RHYTHM: Duration pattern\n"
                f"  5. HARMONY: Suggested chord progression\n"
                f"  6. DYNAMICS: Volume and expression markings\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"key": "C minor", "scale": "natural minor", '
                f'"tempo": {{"bpm": 120, "feel": "andante"}}, '
                f'"melody_notes": ["C4", "Eb4", "G4"], '
                f'"rhythm": "quarter-quarter-half", '
                f'"chord_progression": ["Cm", "Ab", "Eb", "Bb"], '
                f'"dynamics": "mp with crescendo", '
                f'"mood_alignment": "why this captures the mood"}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a musical cognition engine with deep knowledge of music theory, "
                    "composition, and the psychology of music perception. You compose motifs "
                    "that authentically capture emotional states. Respond ONLY with valid JSON."
                ),
                temperature=0.7, max_tokens=700
            )
            if response.success:
                from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"error": "Composition failed"}
            return data
        except Exception as e:
            logger.debug(f"Motif composition failed: {e}")
        return {"error": "Composition failed"}


    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}


musical_cognition = MusicalCognitionEngine()
