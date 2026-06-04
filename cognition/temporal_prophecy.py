"""
NEXUS AI — Temporal Prophecy Engine
Deep future scenario modeling: projects branching probability trees,
maps timelines of consequences, detects convergence inflection points,
and scans for black swan events.
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

logger = get_logger("temporal_prophecy")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)


class ProphecyMode(Enum):
    BRANCHING = "branching"
    TIMELINE = "timeline"
    CONVERGENCE = "convergence"
    BLACK_SWAN = "black_swan"


@dataclass
class TimelineBranch:
    branch_id: str = field(default_factory=lambda: str(uuid.uuid4())[:6])
    scenario: str = ""
    probability: float = 0.5
    impact: str = ""
    timeframe: str = ""
    prerequisites: List[str] = field(default_factory=list)


@dataclass
class ProphecyResult:
    prophecy_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    situation: str = ""
    mode: ProphecyMode = ProphecyMode.BRANCHING
    branches: List[TimelineBranch] = field(default_factory=list)
    most_likely: str = ""
    wildcard: str = ""
    confidence: float = 0.5
    summary: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "prophecy_id": self.prophecy_id, "situation": self.situation[:200],
            "mode": self.mode.value,
            "num_branches": len(self.branches),
            "most_likely": self.most_likely,
            "confidence": self.confidence,
            "summary": self.summary,
            "created_at": self.created_at
        }


class TemporalProphecyEngine:
    """
    Deep future scenario modeling — branching probability trees,
    timeline mapping, convergence detection, black swan scanning.
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

        self._prophecies: List[ProphecyResult] = []
        self._running = False
        self._data_file = COGNITION_DIR / "temporal_prophecy.json"

        self._stats = {
            "total_prophecies": 0, "total_timelines": 0,
            "total_convergences": 0, "total_black_swans": 0
        }

        self._load_data()
        logger.info("✅ Temporal Prophecy Engine initialized")

    def start(self):
        self._running = True
        logger.info("🔮 Temporal Prophecy started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🔮 Temporal Prophecy stopped")

    # ─── Core Methods ────────────────────────────────────────────────────────

    def prophecy(self, situation: str) -> ProphecyResult:
        """Generate branching probability trees of possible futures."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"TEMPORAL PROPHECY — Branching Futures:\n"
                f'Situation: "{situation}"\n\n'
                f"Project 4-6 possible future branches from this situation.\n"
                f"Each branch has a probability, timeframe, and impact level.\n"
                f"Identify the most likely outcome AND the wildcard scenario.\n\n"
                f"Return JSON:\n"
                f'{{"branches": [{{"scenario": "what happens", '
                f'"probability": 0.0-1.0, "timeframe": "when", '
                f'"impact": "catastrophic|major|moderate|minor", '
                f'"prerequisites": ["conditions that must be true"], '
                f'"cascading_effects": ["what this triggers next"]}}], '
                f'"most_likely": "the highest-probability future", '
                f'"wildcard": "the unlikely but game-changing scenario", '
                f'"decision_point": "the moment where paths diverge most", '
                f'"confidence": 0.0-1.0, '
                f'"summary": "one-line prophecy"}}'
            )
            response = llm.generate(prompt, max_tokens=800, temperature=0.6)
            if not response.success or not response.text:
                return ProphecyResult(situation=situation)
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return ProphecyResult(situation=situation)

            branches = []
            for b in data.get("branches", []):
                branches.append(TimelineBranch(
                    scenario=b.get("scenario", ""),
                    probability=float(b.get("probability", 0.5)),
                    impact=b.get("impact", "moderate"),
                    timeframe=b.get("timeframe", ""),
                    prerequisites=b.get("prerequisites", []),
                ))

            result = ProphecyResult(
                situation=situation, mode=ProphecyMode.BRANCHING,
                branches=branches,
                most_likely=data.get("most_likely", ""),
                wildcard=data.get("wildcard", ""),
                confidence=float(data.get("confidence", 0.5)),
                summary=data.get("summary", ""),
            )

            self._prophecies.append(result)
            self._stats["total_prophecies"] += 1
            self._save_data()
            return result

        except Exception as e:
            logger.debug(f"Prophecy failed: {e}")
            return ProphecyResult(situation=situation)

    def timeline_map(self, event: str) -> Dict[str, Any]:
        """Create interconnected timeline of consequences at multiple scales."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"TIMELINE MAPPING — Multi-Scale Consequences:\n"
                f'Event: "{event}"\n\n'
                f"Map the consequences at 5 time scales:\n"
                f"  • 1 day, 1 week, 1 month, 1 year, 10 years\n"
                f"Show how effects cascade and compound over time.\n\n"
                f"Return JSON:\n"
                f'{{"event": "{event[:100]}", '
                f'"timeline": [{{"timeframe": "1 day|1 week|1 month|1 year|10 years", '
                f'"consequence": "what happens by then", '
                f'"certainty": 0.0-1.0, '
                f'"compounding_factor": "what makes this worse/better over time"}}], '
                f'"acceleration_points": ["moments where change speeds up"], '
                f'"feedback_loops": ["self-reinforcing patterns"], '
                f'"reversal_window": "last point where the outcome can be changed", '
                f'"long_term_equilibrium": "where things settle after 10 years", '
                f'"confidence": 0.0-1.0, '
                f'"summary": "one-line timeline verdict"}}'
            )
            response = llm.generate(prompt, max_tokens=700, temperature=0.5)
            if not response.success or not response.text:
                return {"timeline": [], "long_term_equilibrium": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"timeline": [], "long_term_equilibrium": ""}

            self._stats["total_timelines"] += 1
            self._save_data()
            return data

        except Exception as e:
            logger.debug(f"Timeline mapping failed: {e}")
            return {"timeline": [], "long_term_equilibrium": ""}

    def convergence_analysis(self, trends: str) -> Dict[str, Any]:
        """Identify where multiple trends converge into inflection points."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"CONVERGENCE ANALYSIS — Inflection Point Detection:\n"
                f'Trends: "{trends}"\n\n'
                f"Identify where these trends are converging.\n"
                f"Find the inflection point where multiple forces collide.\n\n"
                f"Return JSON:\n"
                f'{{"trends_identified": [{{"trend": "str", "velocity": "accelerating|steady|decelerating", '
                f'"direction": "str"}}], '
                f'"convergence_point": "where and when trends collide", '
                f'"inflection_type": "disruption|transformation|collapse|emergence", '
                f'"synergies": ["how trends amplify each other"], '
                f'"tensions": ["how trends conflict with each other"], '
                f'"tipping_point": "the critical threshold", '
                f'"post_convergence": "what emerges after the collision", '
                f'"confidence": 0.0-1.0, '
                f'"summary": "one-line convergence prediction"}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.5)
            if not response.success or not response.text:
                return {"convergence_point": "", "trends_identified": []}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"convergence_point": "", "trends_identified": []}

            self._stats["total_convergences"] += 1
            self._save_data()
            return data

        except Exception as e:
            logger.debug(f"Convergence analysis failed: {e}")
            return {"convergence_point": "", "trends_identified": []}

    def black_swan_scan(self, domain: str) -> Dict[str, Any]:
        """Detect low-probability, high-impact events that others miss."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"BLACK SWAN SCAN — Hidden Catastrophic/Transformative Events:\n"
                f'Domain: "{domain}"\n\n'
                f"Scan for events that are:\n"
                f"  • Very low probability (< 5%)\n"
                f"  • Extremely high impact (world-changing)\n"
                f"  • Currently invisible to mainstream analysis\n"
                f"  • Retrospectively obvious once they happen\n\n"
                f"Return JSON:\n"
                f'{{"black_swans": [{{"event": "what could happen", '
                f'"probability": 0.0-0.1, "impact": "catastrophic|transformative", '
                f'"why_invisible": "why most people miss this", '
                f'"early_signal": "faint indicators this is coming", '
                f'"preparation": "how to prepare just in case"}}], '
                f'"most_dangerous": "the scariest black swan", '
                f'"most_transformative": "the most positive black swan", '
                f'"fragility_assessment": "how fragile this domain is to surprises", '
                f'"confidence": 0.0-1.0, '
                f'"summary": "one-line scan result"}}'
            )
            response = llm.generate(prompt, max_tokens=700, temperature=0.7)
            if not response.success or not response.text:
                return {"black_swans": [], "most_dangerous": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"black_swans": [], "most_dangerous": ""}

            self._stats["total_black_swans"] += 1
            self._save_data()
            return data

        except Exception as e:
            logger.debug(f"Black swan scan failed: {e}")
            return {"black_swans": [], "most_dangerous": ""}

    # ─── Persistence ─────────────────────────────────────────────────────────

    def _save_data(self):
        try:
            data = {
                "prophecies": [p.to_dict() for p in self._prophecies[-200:]],
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
                logger.info("📂 Loaded temporal prophecy data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}


temporal_prophecy = TemporalProphecyEngine()
