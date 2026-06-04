"""
NEXUS AI — Attention Control Engine
Focus management, distraction filtering, priority shifting,
sustained attention modeling, attention allocation.
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

logger = get_logger("attention_control")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)


class AttentionMode(Enum):
    FOCUSED = "focused"
    DIFFUSE = "diffuse"
    DIVIDED = "divided"
    SUSTAINED = "sustained"
    SELECTIVE = "selective"
    ALTERNATING = "alternating"


@dataclass
class AttentionState:
    state_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    mode: AttentionMode = AttentionMode.FOCUSED
    primary_focus: str = ""
    secondary_foci: List[str] = field(default_factory=list)
    distractions: List[str] = field(default_factory=list)
    focus_strength: float = 0.5
    fatigue_level: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "state_id": self.state_id, "mode": self.mode.value,
            "primary_focus": self.primary_focus,
            "secondary_foci": self.secondary_foci,
            "distractions": self.distractions,
            "focus_strength": self.focus_strength,
            "fatigue_level": self.fatigue_level,
            "created_at": self.created_at
        }


class AttentionControlEngine:
    """
    Focus management and attention allocation — filter distractions,
    prioritize information, manage cognitive resources.
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

        self._states: List[AttentionState] = []
        self._current_focus: str = ""
        self._running = False
        self._data_file = COGNITION_DIR / "attention_control.json"

        self._stats = {
            "total_focus_sessions": 0, "total_prioritizations": 0,
            "total_distraction_filters": 0, "total_attention_shifts": 0
        }

        self._load_data()
        logger.info("✅ Attention Control Engine initialized")


    @staticmethod
    def _safe_parse_json(text: str) -> dict:
        import json
        if not text or not text.strip(): return {}
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try: return json.loads(cleaned[start:end + 1])
            except Exception: pass
        try: return json.loads(cleaned)
        except Exception: return {}

    def start(self):
        self._running = True
        logger.info("🎯 Attention Control started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🎯 Attention Control stopped")

    def focus(self, task: str, context: str = "") -> AttentionState:
        """Determine optimal focus strategy for a task."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Determine the optimal attention strategy for:\n"
                f"Task: {task}\n"
                + (f"Context: {context}\n" if context else "") +
                f"\nReturn JSON:\n"
                f'{{"mode": "focused|diffuse|divided|sustained|selective|alternating", '
                f'"primary_focus": "what to focus on most", '
                f'"secondary_foci": ["secondary items to monitor"], '
                f'"distractions": ["things to actively ignore"], '
                f'"focus_strength": 0.0-1.0, '
                f'"recommended_duration": "how long to maintain this focus", '
                f'"break_strategy": "when and how to take breaks", '
                f'"environment_tips": ["how to set up for optimal focus"]}}'
            )
            response = llm.generate(prompt, max_tokens=400, temperature=0.3)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            am_map = {a.value: a for a in AttentionMode}

            state = AttentionState(
                mode=am_map.get(data.get("mode", "focused"), AttentionMode.FOCUSED),
                primary_focus=data.get("primary_focus", task),
                secondary_foci=data.get("secondary_foci", []),
                distractions=data.get("distractions", []),
                focus_strength=data.get("focus_strength", 0.5)
            )

            self._states.append(state)
            self._current_focus = state.primary_focus
            self._stats["total_focus_sessions"] += 1
            self._save_data()
            return state

        except Exception as e:
            logger.debug(f"Focus strategy failed: {e}")
            return AttentionState(primary_focus=task)

    def prioritize(self, items: List[str]) -> Dict[str, Any]:
        """Prioritize a list of items by attention-worthiness."""
        try:
            from llm.llama_interface import llm
            item_text = "\n".join(f"- {i}" for i in items)
            prompt = (
                f"Prioritize these items by attention-worthiness:\n{item_text}\n\n"
                f"Return JSON:\n"
                f'{{"prioritized": [{{"item": "str", "priority": 1, '
                f'"attention_needed": "deep|moderate|quick|background", '
                f'"reason": "why this priority"}}], '
                f'"can_be_batched": ["items that can be handled together"], '
                f'"can_be_deferred": ["items that can wait"], '
                f'"requires_immediate": ["time-sensitive items"]}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.3)
            if not response.success or not response.text:
                return {"prioritized": [], "requires_immediate": []}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"prioritized": [], "requires_immediate": []}
            self._stats["total_prioritizations"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Prioritization failed: {e}")
            return {"prioritized": [], "requires_immediate": []}

    def filter_distractions(self, main_task: str, incoming: List[str]) -> Dict[str, Any]:
        """Filter incoming information against current focus."""
        try:
            from llm.llama_interface import llm
            incoming_text = "\n".join(f"- {i}" for i in incoming)
            prompt = (
                f"Current focus: {main_task}\n"
                f"Incoming items:\n{incoming_text}\n\n"
                f"Filter what deserves attention vs what's a distraction:\n\n"
                f"Return JSON:\n"
                f'{{"attend_to": [{{"item": "str", "reason": "why it matters"}}], '
                f'"filter_out": [{{"item": "str", "reason": "why to ignore"}}], '
                f'"save_for_later": [{{"item": "str", "when": "when to revisit"}}], '
                f'"focus_impact": "how these items affect current focus"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.3)
            if not response.success or not response.text:
                return {"attend_to": [], "filter_out": []}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"attend_to": [], "filter_out": []}
            self._stats["total_distraction_filters"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Distraction filtering failed: {e}")
            return {"attend_to": [], "filter_out": []}

    def switch_attention(self, from_task: str, to_task: str) -> Dict[str, Any]:
        """Manage an attention switch between tasks."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Manage attention switch:\nFrom: {from_task}\nTo: {to_task}\n\n"
                f"Return JSON:\n"
                f'{{"save_state": "what to remember about current task", '
                f'"transition_cost": 0.0-1.0, '
                f'"warmup_needed": "what to do to get into the new task", '
                f'"estimated_switch_time": "how long the transition takes", '
                f'"risk_of_losing_context": 0.0-1.0, '
                f'"return_strategy": "how to come back to the original task later"}}'
            )
            response = llm.generate(prompt, max_tokens=300, temperature=0.3)
            if not response.success or not response.text:
                return {"transition_cost": 0.0}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"transition_cost": 0.0}
            self._current_focus = to_task
            self._stats["total_attention_shifts"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Attention switch failed: {e}")
            return {"transition_cost": 0.0}

    def _save_data(self):
        try:
            data = {
                "states": [s.to_dict() for s in self._states[-100:]],
                "current_focus": self._current_focus,
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
                self._current_focus = data.get("current_focus", "")
                logger.info("📂 Loaded attention control data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def prioritize_tasks(self, tasks: str) -> Dict[str, Any]:
        """Prioritize a list of tasks using Eisenhower matrix and cognitive load analysis."""
        try:
            from llm.llama_interface import llm

            prompt = (
                f'PRIORITIZE these tasks using the Eisenhower matrix:\n'
                f'{tasks}\n\n'
                f"For each task:\n"
                f"  1. Classify as urgent/not-urgent AND important/not-important\n"
                f"  2. Estimate cognitive load (high/medium/low)\n"
                f"  3. Recommend sequencing based on energy and focus requirements\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"tasks": [{{"task": "name", "urgent": true, "important": true, '
                f'"quadrant": "do_first|schedule|delegate|eliminate", '
                f'"cognitive_load": "high|medium|low", "recommended_time": "morning|afternoon|evening"}}], '
                f'"suggested_order": ["task in optimal order"], '
                f'"quick_wins": ["tasks that can be done in under 5 minutes"]}}'
            )
            response = llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a cognitive attention and task prioritization engine. You apply the "
                    "Eisenhower matrix, cognitive load theory, and energy management principles "
                    "to help humans focus on what truly matters. Respond ONLY with valid JSON."
                ),
                temperature=0.3, max_tokens=800
            )
            if response.success:
                return extract_json(response.text)

        except Exception as e:
            logger.debug(f"Task prioritization failed: {e}")
        return {"error": "Prioritization failed"}


    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, "current_focus": self._current_focus, **self._stats}


attention_control = AttentionControlEngine()
