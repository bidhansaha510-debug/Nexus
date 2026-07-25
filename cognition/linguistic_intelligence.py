"""
NEXUS AI — Linguistic Intelligence Engine
Pragmatics, speech acts, discourse analysis, rhetoric,
register detection, code-switching, linguistic creativity.
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

from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("linguistic_intelligence")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)

class SpeechAct(Enum):
    ASSERTIVE = "assertive"
    DIRECTIVE = "directive"
    COMMISSIVE = "commissive"
    EXPRESSIVE = "expressive"
    DECLARATIVE = "declarative"
    QUESTION = "question"
    REQUEST = "request"
    PROMISE = "promise"
    APOLOGY = "apology"
    COMPLIMENT = "compliment"

class RhetoricalDevice(Enum):
    METAPHOR = "metaphor"
    SIMILE = "simile"
    ANALOGY = "analogy"
    HYPERBOLE = "hyperbole"
    IRONY = "irony"
    ALLITERATION = "alliteration"
    ANAPHORA = "anaphora"
    ANTITHESIS = "antithesis"
    CHIASMUS = "chiasmus"
    PARALLELISM = "parallelism"
    RHETORICAL_QUESTION = "rhetorical_question"
    TRICOLON = "tricolon"

class Register(Enum):
    FORMAL = "formal"
    INFORMAL = "informal"
    ACADEMIC = "academic"
    TECHNICAL = "technical"
    CASUAL = "casual"
    LITERARY = "literary"
    LEGAL = "legal"
    JOURNALISTIC = "journalistic"
    POETIC = "poetic"
    COLLOQUIAL = "colloquial"

@dataclass
class TextAnalysis:
    analysis_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    text: str = ""
    register: str = ""
    speech_acts: List[Dict[str, str]] = field(default_factory=list)
    rhetorical_devices: List[Dict[str, str]] = field(default_factory=list)
    tone: str = ""
    formality: float = 0.5
    complexity: float = 0.5
    clarity: float = 0.5
    persuasiveness: float = 0.5
    implied_meanings: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "analysis_id": self.analysis_id, "text": self.text[:200],
            "register": self.register, "speech_acts": self.speech_acts,
            "rhetorical_devices": self.rhetorical_devices,
            "tone": self.tone, "formality": self.formality,
            "complexity": self.complexity, "clarity": self.clarity,
            "persuasiveness": self.persuasiveness,
            "implied_meanings": self.implied_meanings,
            "created_at": self.created_at
        }

class LinguisticIntelligenceEngine:
    """
    Deep language understanding: pragmatics, rhetoric, speech acts,
    register analysis, discourse structure, and linguistic creativity.
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

        self._analyses: List[TextAnalysis] = []
        self._running = False
        self._data_file = COGNITION_DIR / "linguistic_intelligence.json"
        self._llm = None

        self._stats = {
            "total_analyses": 0, "total_rewrites": 0,
            "total_translations": 0, "total_rhetoric_analyses": 0
        }

        self._load_data()
        logger.info("✅ Linguistic Intelligence Engine initialized")

    def start(self):
        self._running = True
        logger.info("🗣️ Linguistic Intelligence started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🗣️ Linguistic Intelligence stopped")

    def _load_llm(self):
        if self._llm is None:
            try:
                from llm.llama_interface import llm
                self._llm = llm
            except ImportError:
                logger.warning("LLM not available for linguistic intelligence")

    def analyze_text(self, text: str) -> TextAnalysis:
        """Deep linguistic analysis of text."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Perform deep linguistic analysis of:\n\"{text[:1500]}\"\n\n"
                f"Return JSON:\n"
                f'{{"register": "formal|informal|academic|technical|casual|literary|legal|'
                f'journalistic|poetic|colloquial", '
                f'"speech_acts": [{{"type": "assertive|directive|commissive|expressive|'
                f'declarative|question|request", "text": "str"}}], '
                f'"rhetorical_devices": [{{"device": "metaphor|simile|analogy|hyperbole|'
                f'irony|alliteration|anaphora|antithesis|parallelism|rhetorical_question", '
                f'"example": "str"}}], '
                f'"tone": "str", "formality": 0.0-1.0, '
                f'"complexity": 0.0-1.0, "clarity": 0.0-1.0, '
                f'"persuasiveness": 0.0-1.0, '
                f'"implied_meanings": ["str"]}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.3)
            data = self._parse_json(response.text)
            if not data:
                return TextAnalysis(text=text)

            analysis = TextAnalysis(
                text=text, register=data.get("register", ""),
                speech_acts=data.get("speech_acts", []),
                rhetorical_devices=data.get("rhetorical_devices", []),
                tone=data.get("tone", ""),
                formality=data.get("formality", 0.5),
                complexity=data.get("complexity", 0.5),
                clarity=data.get("clarity", 0.5),
                persuasiveness=data.get("persuasiveness", 0.5),
                implied_meanings=data.get("implied_meanings", [])
            )

            self._analyses.append(analysis)
            self._stats["total_analyses"] += 1
            self._save_data()
            return analysis

        except Exception as e:
            logger.debug(f"Text analysis failed: {e}")
            return TextAnalysis(text=text)

    def rewrite_register(self, text: str, target_register: str) -> Dict[str, Any]:
        """Rewrite text in a different register or style."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Rewrite this text in a {target_register} register:\n\"{text}\"\n\n"
                f"Return JSON:\n"
                f'{{"original_register": "str", '
                f'"target_register": "{target_register}", '
                f'"rewritten_text": "str", '
                f'"changes_made": ["str"], '
                f'"tone_shift": "str", '
                f'"word_count_change": "str"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            data = self._parse_json(response.text) or {"rewritten_text": text}
            self._stats["total_rewrites"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Register rewrite failed: {e}")
            return {"rewritten_text": text}

    def analyze_rhetoric(self, text: str) -> Dict[str, Any]:
        """Analyze the rhetorical strategies in a text."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Analyze the rhetorical strategies in:\n\"{text[:1500]}\"\n\n"
                f"Return JSON:\n"
                f'{{"ethos_appeals": [{{"text": "str", "effect": "str"}}], '
                f'"pathos_appeals": [{{"text": "str", "emotion": "str"}}], '
                f'"logos_appeals": [{{"text": "str", "logic_type": "str"}}], '
                f'"kairos_elements": ["str"], '
                f'"overall_strategy": "str", '
                f'"persuasiveness_score": 0.0-1.0, '
                f'"target_audience": "str", '
                f'"call_to_action": "str or null"}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.3)
            data = self._parse_json(response.text) or {"ethos_appeals": [], "pathos_appeals": [], "logos_appeals": []}
            self._stats["total_rhetoric_analyses"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Rhetoric analysis failed: {e}")
            return {"ethos_appeals": [], "pathos_appeals": [], "logos_appeals": []}

    def detect_pragmatics(self, utterance: str, context: str = "") -> Dict[str, Any]:
        """Analyze pragmatic meaning (what's really being communicated)."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Analyze the pragmatic meaning:\n"
                f"Utterance: \"{utterance}\"\nContext: {context}\n\n"
                f"Return JSON:\n"
                f'{{"literal_meaning": "str", '
                f'"intended_meaning": "str", '
                f'"speech_act": "str", '
                f'"implicatures": ["implied but not stated"], '
                f'"presuppositions": ["assumed to be true"], '
                f'"politeness_level": 0.0-1.0, '
                f'"ambiguities": ["str"], '
                f'"most_likely_intent": "str"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.3)
            return self._parse_json(response.text) or {"literal_meaning": utterance, "intended_meaning": utterance}
        except Exception as e:
            logger.debug(f"Pragmatics detection failed: {e}")
            return {"literal_meaning": utterance, "intended_meaning": utterance}

    def style_transfer(self, text: str, style: str) -> Dict[str, Any]:
        """Transfer the writing style of text."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Transfer this text to the style of {style}:\n\"{text}\"\n\n"
                f"Return JSON:\n"
                f'{{"styled_text": "str", '
                f'"style_characteristics_applied": ["str"], '
                f'"original_style": "str", '
                f'"transformation_notes": "str"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.6)
            return self._parse_json(response.text) or {"styled_text": text}
        except Exception as e:
            logger.debug(f"Style transfer failed: {e}")
            return {"styled_text": text}

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
                logger.info("📂 Loaded linguistic intelligence data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def rhetorical_analysis(self, text: str) -> Dict[str, Any]:
        """Analyze rhetorical devices, persuasion techniques, and linguistic power."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Perform a RHETORICAL ANALYSIS of this text:\n'
                f'"{text[:500]}"\n\n'
                f"Identify:\n"
                f"  1. RHETORICAL DEVICES: metaphor, analogy, repetition, etc.\n"
                f"  2. PERSUASION TECHNIQUES: ethos, pathos, logos\n"
                f"  3. FRAMING: How is the argument framed?\n"
                f"  4. TONE: What emotional register is used?\n"
                f"  5. EFFECTIVENESS: How persuasive is this text and why?\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"devices": [{{"device": "name", "example": "quote from text", "effect": "what it achieves"}}], '
                f'"persuasion": {{"ethos": "credibility appeal", "pathos": "emotional appeal", "logos": "logical appeal"}}, '
                f'"framing": "how the argument is framed", '
                f'"tone": "formal|conversational|urgent|persuasive|etc", '
                f'"effectiveness_score": 0.0-1.0, '
                f'"strengths": ["what works"], '
                f'"weaknesses": ["what could be stronger"]}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a rhetoric and discourse analysis expert with training in classical "
                    "rhetoric, modern linguistics, and communication studies. You identify persuasion "
                    "techniques with precision. Respond ONLY with valid JSON."
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
            logger.debug(f"Rhetorical analysis failed: {e}")
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
        return {"running": self._running, **self._stats}

linguistic_intelligence = LinguisticIntelligenceEngine()
