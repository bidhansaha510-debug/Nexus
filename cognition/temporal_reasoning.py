"""
NEXUS AI — Temporal Reasoning Engine
Understanding time sequences, temporal logic, duration estimation,
scheduling, timeline construction, and temporal causality.
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

logger = get_logger("temporal_reasoning")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)

class TemporalRelation(Enum):
    BEFORE = "before"
    AFTER = "after"
    DURING = "during"
    SIMULTANEOUS = "simultaneous"
    OVERLAPS = "overlaps"
    STARTS = "starts"
    FINISHES = "finishes"
    CONTAINS = "contains"
    PRECEDES = "precedes"
    FOLLOWS = "follows"
    CAUSES_THEN = "causes_then"

class TimeScale(Enum):
    MILLISECONDS = "milliseconds"
    SECONDS = "seconds"
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"
    YEARS = "years"
    DECADES = "decades"
    CENTURIES = "centuries"

@dataclass
class TemporalEvent:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    start_time: str = ""
    end_time: str = ""
    duration: str = ""
    time_scale: str = "unknown"
    is_recurring: bool = False
    frequency: str = ""
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "event_id": self.event_id, "description": self.description,
            "start_time": self.start_time, "end_time": self.end_time,
            "duration": self.duration, "time_scale": self.time_scale,
            "is_recurring": self.is_recurring, "frequency": self.frequency,
            "dependencies": self.dependencies
        }

@dataclass
class Timeline:
    timeline_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    topic: str = ""
    events: List[TemporalEvent] = field(default_factory=list)
    relations: List[Dict[str, str]] = field(default_factory=list)
    time_span: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "timeline_id": self.timeline_id, "topic": self.topic,
            "events": [e.to_dict() for e in self.events],
            "relations": self.relations, "time_span": self.time_span,
            "created_at": self.created_at
        }

@dataclass
class DurationEstimate:
    estimate_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    task: str = ""
    min_duration: str = ""
    expected_duration: str = ""
    max_duration: str = ""
    confidence: float = 0.5
    factors: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "estimate_id": self.estimate_id, "task": self.task,
            "min_duration": self.min_duration,
            "expected_duration": self.expected_duration,
            "max_duration": self.max_duration,
            "confidence": self.confidence,
            "factors": self.factors, "assumptions": self.assumptions
        }

class TemporalReasoningEngine:
    """
    Reasons about time — sequences, durations, schedules,
    temporal logic, and timeline construction.
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

        self._timelines: List[Timeline] = []
        self._estimates: List[DurationEstimate] = []
        self._running = False
        self._data_file = COGNITION_DIR / "temporal_reasoning.json"

        self._stats = {
            "total_timelines": 0, "total_estimates": 0,
            "total_sequences": 0, "total_schedules": 0
        }

        self._load_data()
        logger.info("✅ Temporal Reasoning Engine initialized")

    def start(self):
        self._running = True
        logger.info("⏱️ Temporal Reasoning started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("⏱️ Temporal Reasoning stopped")

    def build_timeline(self, topic: str, context: str = "") -> Timeline:
        """Build a chronological timeline for a topic."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Build a chronological timeline for: {topic}\n"
                f"Context: {context}\n\n"
                f"Return JSON:\n"
                f'{{"events": [{{"description": "str", "start_time": "str", '
                f'"end_time": "str", "duration": "str"}}], '
                f'"relations": [{{"event_a": "str", "relation": "before|after|during|'
                f'simultaneous|overlaps|causes_then", "event_b": "str"}}], '
                f'"time_span": "total span"}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.3)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            events = [TemporalEvent(
                description=e.get("description", ""),
                start_time=e.get("start_time", ""),
                end_time=e.get("end_time", ""),
                duration=e.get("duration", "")
            ) for e in data.get("events", [])]

            tl = Timeline(
                topic=topic, events=events,
                relations=data.get("relations", []),
                time_span=data.get("time_span", "")
            )

            self._timelines.append(tl)
            self._stats["total_timelines"] += 1
            self._save_data()
            return tl

        except Exception as e:
            logger.debug(f"Timeline building failed: {e}")
            return Timeline(topic=topic)

    def estimate_duration(self, task: str, context: str = "") -> DurationEstimate:
        """Estimate how long something will take."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Estimate the duration for: {task}\nContext: {context}\n\n"
                f"Return JSON:\n"
                f'{{"min_duration": "str", "expected_duration": "str", '
                f'"max_duration": "str", "confidence": 0.0-1.0, '
                f'"factors": ["things that affect duration"], '
                f'"assumptions": ["assumptions made"]}}'
            )
            response = llm.generate(prompt, max_tokens=400, temperature=0.3)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            est = DurationEstimate(
                task=task,
                min_duration=data.get("min_duration", ""),
                expected_duration=data.get("expected_duration", ""),
                max_duration=data.get("max_duration", ""),
                confidence=data.get("confidence", 0.5),
                factors=data.get("factors", []),
                assumptions=data.get("assumptions", [])
            )

            self._estimates.append(est)
            self._stats["total_estimates"] += 1
            self._save_data()
            return est

        except Exception as e:
            logger.debug(f"Duration estimation failed: {e}")
            return DurationEstimate(task=task)

    def sequence_events(self, events_text: str) -> Dict[str, Any]:
        """Put a set of events into temporal order."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Order these events chronologically:\n{events_text}\n\n"
                f"Return JSON:\n"
                f'{{"ordered_events": ["event in order"], '
                f'"temporal_relations": [{{"a": "str", "relation": "str", "b": "str"}}], '
                f'"ambiguities": ["unclear orderings"], '
                f'"confidence": 0.0-1.0}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.3)
            if not response.success or not response.text:
                return {"ordered_events": [], "confidence": 0.0}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"ordered_events": [], "confidence": 0.0}
            self._stats["total_sequences"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Event sequencing failed: {e}")
            return {"ordered_events": [], "confidence": 0.0}

    def create_schedule(self, tasks: str, constraints: str = "") -> Dict[str, Any]:
        """Create a schedule from tasks and constraints."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Create an optimal schedule for these tasks:\n{tasks}\n"
                f"Constraints: {constraints}\n\n"
                f"Return JSON:\n"
                f'{{"schedule": [{{"task": "str", "start": "str", "end": "str", '
                f'"duration": "str", "dependencies": ["str"]}}], '
                f'"total_duration": "str", '
                f'"critical_path": ["str"], '
                f'"parallel_opportunities": ["str"], '
                f'"bottlenecks": ["str"]}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.3)
            if not response.success or not response.text:
                return {"schedule": [], "total_duration": "unknown"}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"schedule": [], "total_duration": "unknown"}
            self._stats["total_schedules"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Schedule creation failed: {e}")
            return {"schedule": [], "total_duration": "unknown"}

    def temporal_query(self, question: str, context: str = "") -> Dict[str, Any]:
        """Answer a temporal reasoning question."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Answer this temporal reasoning question:\n{question}\n"
                f"Context: {context}\n\n"
                f"Return JSON:\n"
                f'{{"answer": "str", "reasoning": "str", '
                f'"temporal_relations": ["str"], "confidence": 0.0-1.0}}'
            )
            response = llm.generate(prompt, max_tokens=400, temperature=0.3)
            if not response.success or not response.text:
                return {"answer": f"Error: {e}", "confidence": 0.0}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"answer": f"Error: {e}", "confidence": 0.0}
            return data
        except Exception as e:
            logger.debug(f"Temporal query failed: {e}")
            return {"answer": f"Error: {e}", "confidence": 0.0}

    def _save_data(self):
        try:
            data = {
                "timelines": [t.to_dict() for t in self._timelines[-100:]],
                "estimates": [e.to_dict() for e in self._estimates[-200:]],
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
                logger.info("📂 Loaded temporal reasoning data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def timeline_analysis(self, events: str) -> Dict[str, Any]:
        """Analyze the temporal structure of events and identify patterns."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Perform a TIMELINE ANALYSIS of these events:\n'
                f'{events}\n\n'
                f"Analyze:\n"
                f"  1. SEQUENCE: Put events in correct temporal order\n"
                f"  2. CAUSATION: Which events caused which?\n"
                f"  3. PATTERNS: Any cyclical or recurring patterns?\n"
                f"  4. TEMPO: Is change accelerating or decelerating?\n"
                f"  5. PREDICTION: What likely happens next?\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"ordered_events": [{{"event": "what", "time": "when", "significance": "why it matters"}}], '
                f'"causal_links": ["event A caused event B"], '
                f'"patterns": ["cyclical or recurring patterns found"], '
                f'"tempo": "accelerating|steady|decelerating", '
                f'"prediction": "what likely happens next", '
                f'"confidence": 0.0-1.0}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a temporal reasoning engine with expertise in chronological analysis, "
                    "historical patterns, and trend forecasting. You identify causal sequences "
                    "and temporal patterns in events. Respond ONLY with valid JSON."
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
            logger.debug(f"Timeline analysis failed: {e}")
        return {"error": "Analysis failed"}

    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}

temporal_reasoning = TemporalReasoningEngine()