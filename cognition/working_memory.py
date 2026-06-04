"""
NEXUS AI — Working Memory Engine
Short-term context management, attention buffering,
cognitive load tracking, information chunking.
"""

import threading
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from collections import deque

import re
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("working_memory")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)

MAX_BUFFER_SIZE = 20
MAX_CHUNKS = 7  # Miller's number


class MemoryPriority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


@dataclass
class MemoryItem:
    item_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    content: str = ""
    category: str = ""
    priority: MemoryPriority = MemoryPriority.NORMAL
    relevance_score: float = 0.5
    access_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_accessed: str = field(default_factory=lambda: datetime.now().isoformat())
    decay_rate: float = 0.1

    def to_dict(self) -> Dict:
        return {
            "item_id": self.item_id, "content": self.content[:300],
            "category": self.category, "priority": self.priority.value,
            "relevance_score": self.relevance_score,
            "access_count": self.access_count,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "decay_rate": self.decay_rate
        }


@dataclass
class CognitiveChunk:
    chunk_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    label: str = ""
    items: List[str] = field(default_factory=list)
    summary: str = ""
    importance: float = 0.5

    def to_dict(self) -> Dict:
        return {
            "chunk_id": self.chunk_id, "label": self.label,
            "items": self.items, "summary": self.summary,
            "importance": self.importance
        }


class WorkingMemoryEngine:
    """
    Short-term cognitive buffer — manages attention, tracks context,
    chunks information, and monitors cognitive load.
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

        self._buffer: deque = deque(maxlen=MAX_BUFFER_SIZE)
        self._chunks: List[CognitiveChunk] = []
        self._focus_topic: str = ""
        self._cognitive_load: float = 0.0
        self._running = False
        self._running = False
        self._data_file = COGNITION_DIR / "working_memory.json"
        self._llm = None

        self._stats = {
            "total_items_buffered": 0, "total_chunks_created": 0,
            "total_focus_shifts": 0, "total_load_assessments": 0,
            "peak_cognitive_load": 0.0
        }

        self._load_data()
        logger.info("✅ Working Memory Engine initialized")

    def _load_llm(self):
        if self._llm is None:
            try:
                from llm.llama_interface import llm
                self._llm = llm
            except ImportError:
                logger.warning("LLM not available for working memory")

    def start(self):
        self._running = True
        logger.info("🧠 Working Memory started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🧠 Working Memory stopped")

    def buffer_item(self, content: str, category: str = "general",
                    priority: str = "normal") -> MemoryItem:
        """Add an item to the working memory buffer."""
        pr_map = {p.value: p for p in MemoryPriority}
        item = MemoryItem(
            content=content, category=category,
            priority=pr_map.get(priority, MemoryPriority.NORMAL),
            relevance_score=0.7 if priority in ("critical", "high") else 0.5
        )
        self._buffer.append(item)
        self._stats["total_items_buffered"] += 1
        self._update_cognitive_load()
        self._save_data()
        return item

    def get_context(self, topic: str = "") -> Dict[str, Any]:
        """Retrieve current working memory context, optionally filtered by topic."""
        items = list(self._buffer)
        if topic:
            items = [i for i in items if topic.lower() in i.content.lower()
                     or topic.lower() in i.category.lower()]
        items.sort(key=lambda x: x.relevance_score, reverse=True)

        return {
            "items": [i.to_dict() for i in items[:MAX_CHUNKS]],
            "total_buffered": len(self._buffer),
            "focus_topic": self._focus_topic,
            "cognitive_load": self._cognitive_load,
            "chunks": [c.to_dict() for c in self._chunks[-5:]]
        }

    def chunk_information(self, text: str) -> Dict[str, Any]:
        """Break information into cognitive chunks for easier processing."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"chunks": [], "overall_complexity": 0.0}
        try:
            prompt = (
                f"Break this information into cognitive chunks "
                f"(groups of related ideas, max {MAX_CHUNKS} chunks):\n{text}\n\n"
                f"Return JSON:\n"
                f'{{"chunks": [{{"label": "short label", '
                f'"items": ["key point 1", "key point 2"], '
                f'"summary": "one-line summary", '
                f'"importance": 0.0-1.0}}], '
                f'"overall_complexity": 0.0-1.0, '
                f'"recommended_focus_order": ["chunk labels in priority order"]}}'
            )
            response = self._llm.generate(prompt, max_tokens=600, temperature=0.3)
            data = self._parse_json(response.text)
            if not data:
                return {"chunks": [], "overall_complexity": 0.0}

            for chunk_data in data.get("chunks", []):
                chunk = CognitiveChunk(
                    label=chunk_data.get("label", ""),
                    items=chunk_data.get("items", []),
                    summary=chunk_data.get("summary", ""),
                    importance=chunk_data.get("importance", 0.5)
                )
                self._chunks.append(chunk)

            self._stats["total_chunks_created"] += len(data.get("chunks", []))
            self._save_data()
            return data

        except Exception as e:
            logger.debug(f"Chunking failed: {e}")
            return {"chunks": [], "overall_complexity": 0.0}

    def assess_cognitive_load(self, task_description: str) -> Dict[str, Any]:
        """Assess the cognitive load of a task or conversation."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"total_load": 0.0, "overload_risk": "unknown"}
        try:
            prompt = (
                f"Assess the cognitive load of this task:\n{task_description}\n\n"
                f"Current buffer size: {len(self._buffer)} items\n\n"
                f"Return JSON:\n"
                f'{{"intrinsic_load": 0.0-1.0, '
                f'"extraneous_load": 0.0-1.0, '
                f'"germane_load": 0.0-1.0, '
                f'"total_load": 0.0-1.0, '
                f'"overload_risk": "none|low|moderate|high|critical", '
                f'"simplification_tips": ["ways to reduce load"], '
                f'"recommended_breaks": "when to take mental breaks"}}'
            )
            response = self._llm.generate(prompt, max_tokens=400, temperature=0.3)
            data = self._parse_json(response.text)
            if not data:
                return {"total_load": 0.0, "overload_risk": "unknown"}
            self._cognitive_load = data.get("total_load", 0.0)
            self._stats["total_load_assessments"] += 1
            if self._cognitive_load > self._stats["peak_cognitive_load"]:
                self._stats["peak_cognitive_load"] = self._cognitive_load
            self._save_data()
            return data

        except Exception as e:
            logger.warning(f"Cognitive load assessment failed: {e}")
            return {"total_load": 0.0, "overload_risk": "unknown"}

    def shift_focus(self, new_topic: str) -> Dict[str, Any]:
        """Shift attention focus to a new topic."""
        old_topic = self._focus_topic
        self._focus_topic = new_topic
        self._stats["total_focus_shifts"] += 1
        self._save_data()
        return {
            "old_focus": old_topic, "new_focus": new_topic,
            "context_items": len(self._buffer),
            "relevant_items": sum(
                1 for i in self._buffer
                if new_topic.lower() in i.content.lower()
            )
        }

    def clear_buffer(self) -> Dict[str, Any]:
        """Clear the working memory buffer."""
        count = len(self._buffer)
        self._buffer.clear()
        self._cognitive_load = 0.0
        self._save_data()
        return {"cleared_items": count, "cognitive_load": 0.0}

    def _update_cognitive_load(self):
        """Update cognitive load based on buffer occupancy."""
        self._cognitive_load = min(1.0, len(self._buffer) / MAX_BUFFER_SIZE)

    def _save_data(self):
        try:
            data = {
                "buffer": [i.to_dict() for i in self._buffer],
                "chunks": [c.to_dict() for c in self._chunks[-50:]],
                "focus_topic": self._focus_topic,
                "cognitive_load": self._cognitive_load,
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
                self._focus_topic = data.get("focus_topic", "")
                self._cognitive_load = data.get("cognitive_load", 0.0)
                logger.info("📂 Loaded working memory data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def synthesize_context(self, items: str) -> Dict[str, Any]:
        """Synthesize multiple context items into a coherent working model."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'SYNTHESIZE these items into a coherent model:\n'
                f'{items}\n\n'
                f"Process:\n"
                f"  1. IDENTIFY CONNECTIONS: What links these items together?\n"
                f"  2. FIND PATTERNS: What recurring themes emerge?\n"
                f"  3. RESOLVE CONFLICTS: How to reconcile contradictions?\n"
                f"  4. CREATE MODEL: Unified summary that captures all items\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"connections": ["how items relate"], '
                f'"patterns": ["recurring themes"], '
                f'"conflicts": ["contradictions found"], '
                f'"unified_model": "coherent synthesis of all items", '
                f'"key_insight": "most important takeaway", '
                f'"confidence": 0.0-1.0}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a working memory synthesis engine. You hold multiple pieces of "
                    "information simultaneously and find the connections between them, creating "
                    "a unified understanding. Respond ONLY with valid JSON."
                ),
                temperature=0.4, max_tokens=800
            )
            if response.success:
                from utils.json_utils import extract_json
                data = extract_json(response.text)
                if not data:
                    return {"error": "Synthesis failed"}
                return data
        except Exception as e:
            logger.debug(f"Context synthesis failed: {e}")
        return {"error": "Synthesis failed"}

    def _parse_json(self, text: str) -> Optional[Dict]:
        if not text:
            return None
        try:
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
            return {
                "running": self._running,
                "buffer_size": len(self._buffer),
                "focus_topic": self._focus_topic,
                "cognitive_load": self._cognitive_load,
                **self._stats
            }


working_memory = WorkingMemoryEngine()
