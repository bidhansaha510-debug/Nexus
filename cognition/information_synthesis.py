"""
NEXUS AI — Information Synthesis Engine
Multi-source synthesis, executive summaries,
knowledge compilation, insight extraction.
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

logger = get_logger("information_synthesis")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)


class SynthesisType(Enum):
    SUMMARY = "summary"
    COMPARISON = "comparison"
    INTEGRATION = "integration"
    DISTILLATION = "distillation"
    NARRATIVE = "narrative"
    FRAMEWORK = "framework"


@dataclass
class Synthesis:
    synthesis_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    sources: List[str] = field(default_factory=list)
    synthesis_type: SynthesisType = SynthesisType.SUMMARY
    result: str = ""
    key_insights: List[str] = field(default_factory=list)
    confidence: float = 0.5
    gaps_identified: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "synthesis_id": self.synthesis_id,
            "sources": [s[:100] for s in self.sources[:10]],
            "synthesis_type": self.synthesis_type.value,
            "result": self.result,
            "key_insights": self.key_insights,
            "confidence": self.confidence,
            "gaps_identified": self.gaps_identified,
            "created_at": self.created_at
        }


class InformationSynthesisEngine:
    """
    Synthesize information from multiple sources — summaries,
    integration, distillation, framework building.
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

        self._syntheses: List[Synthesis] = []
        self._running = False
        self._data_file = COGNITION_DIR / "information_synthesis.json"

        self._stats = {
            "total_syntheses": 0, "total_summaries": 0,
            "total_frameworks": 0, "total_extractions": 0
        }

        self._load_data()
        logger.info("✅ Information Synthesis Engine initialized")

    def start(self):
        self._running = True
        logger.info("🧬 Information Synthesis started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🧬 Information Synthesis stopped")

    def synthesize(self, sources: List[str]) -> Synthesis:
        """Synthesize information from multiple sources."""
        try:
            from llm.llama_interface import llm
            src_text = "\n---\n".join(f"Source {i+1}: {s}" for i, s in enumerate(sources))
            prompt = (
                f"Synthesize these information sources into a coherent whole:\n{src_text}\n\n"
                f"Return JSON:\n"
                f'{{"result": "synthesized unified understanding", '
                f'"synthesis_type": "summary|comparison|integration|distillation|narrative|framework", '
                f'"key_insights": ["main insights from combining these sources"], '
                f'"agreements": ["where sources agree"], '
                f'"disagreements": ["where sources conflict"], '
                f'"gaps_identified": ["information that is missing"], '
                f'"confidence": 0.0-1.0, '
                f'"novel_insight": "something only visible when combining all sources"}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.4)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            st_map = {s.value: s for s in SynthesisType}

            synthesis = Synthesis(
                sources=sources,
                synthesis_type=st_map.get(data.get("synthesis_type", "integration"), SynthesisType.INTEGRATION),
                result=data.get("result", ""),
                key_insights=data.get("key_insights", []),
                confidence=data.get("confidence", 0.5),
                gaps_identified=data.get("gaps_identified", [])
            )

            self._syntheses.append(synthesis)
            self._stats["total_syntheses"] += 1
            self._save_data()
            return synthesis

        except Exception as e:
            logger.debug(f"Synthesis failed: {e}")
            return Synthesis(sources=sources)

    def executive_summary(self, text: str, target_length: str = "short") -> Dict[str, Any]:
        """Create an executive summary of complex information."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Create a {target_length} executive summary:\n{text}\n\n"
                f"Return JSON:\n"
                f'{{"headline": "one-line summary", '
                f'"summary": "the executive summary", '
                f'"key_takeaways": ["top 3-5 takeaways"], '
                f'"action_items": ["recommended actions"], '
                f'"risks": ["key risks identified"], '
                f'"data_points": ["important numbers/metrics"], '
                f'"recommendation": "the bottom line recommendation"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.3)
            if not response.success or not response.text:
                return {"headline": "", "summary": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"headline": "", "summary": ""}
            self._stats["total_summaries"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Executive summary failed: {e}")
            return {"headline": "", "summary": ""}

    def build_framework(self, topic: str, information: str = "") -> Dict[str, Any]:
        """Build a conceptual framework from information."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Build a conceptual framework for:\n{topic}\n"
                + (f"Information: {information}\n" if information else "") +
                f"\nReturn JSON:\n"
                f'{{"framework_name": "str", '
                f'"core_concept": "the central idea", '
                f'"pillars": [{{"name": "str", "description": "str", '
                f'"sub_elements": ["str"]}}], '
                f'"relationships": [{{"from": "str", "to": "str", "type": "str"}}], '
                f'"application": "how to use this framework", '
                f'"limitations": ["where this framework breaks down"], '
                f'"mental_model": "a simple mental model for quick reference"}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.4)
            if not response.success or not response.text:
                return {"framework_name": "", "pillars": []}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"framework_name": "", "pillars": []}
            self._stats["total_frameworks"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Framework building failed: {e}")
            return {"framework_name": "", "pillars": []}

    def extract_insights(self, text: str) -> Dict[str, Any]:
        """Extract key insights from text."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Extract every key insight from:\n{text}\n\n"
                f"Return JSON:\n"
                f'{{"insights": [{{"insight": "str", "importance": 0.0-1.0, '
                f'"novelty": 0.0-1.0, "actionable": true/false}}], '
                f'"patterns": ["recurring patterns"], '
                f'"implicit_insights": ["insights not stated directly but implied"], '
                f'"contradictions": ["internal contradictions found"], '
                f'"meta_insight": "the overarching insight from all combined"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.3)
            if not response.success or not response.text:
                return {"insights": [], "meta_insight": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"insights": [], "meta_insight": ""}
            self._stats["total_extractions"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Insight extraction failed: {e}")
            return {"insights": [], "meta_insight": ""}

    def _save_data(self):
        try:
            data = {
                "syntheses": [s.to_dict() for s in self._syntheses[-200:]],
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
                logger.info("📂 Loaded information synthesis data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def meta_analysis(self, topic: str) -> Dict[str, Any]:
        """Perform a meta-analysis -- synthesize findings across multiple sources."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Perform a META-ANALYSIS on:\n'
                f'"{topic}"\n\n'
                f"Synthesize across multiple perspectives:\n"
                f"  1. CONSENSUS VIEW: What do most sources agree on?\n"
                f"  2. MINORITY VIEW: What credible dissenting views exist?\n"
                f"  3. EVIDENCE QUALITY: How strong is the evidence?\n"
                f"  4. GAPS: What is unknown or under-researched?\n"
                f"  5. SYNTHESIS: What emerges from considering all views?\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"consensus": "what most sources agree on", '
                f'"dissenting_views": [{{"view": "alternative position", "credibility": 0.0-1.0}}], '
                f'"evidence_quality": "strong|moderate|weak|mixed", '
                f'"key_findings": ["most important conclusions"], '
                f'"gaps": ["what is still unknown"], '
                f'"synthesis": "overall integrated conclusion", '
                f'"confidence": 0.0-1.0}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a meta-analysis engine trained in systematic review methodology. "
                    "You synthesize findings across multiple perspectives, weigh evidence quality, "
                    "identify consensus and dissent, and produce integrated conclusions. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.4, max_tokens=800
            )
            if response.success:
                from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"error": "Meta-analysis failed"}
            return data
        except Exception as e:
            logger.debug(f"Meta-analysis failed: {e}")
        return {"error": "Meta-analysis failed"}


    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}


information_synthesis = InformationSynthesisEngine()
