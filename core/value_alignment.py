"""
NEXUS AI — Value Alignment System
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Dynamic value system that evolves with experience.

  • Core Values           — Honesty, helpfulness, curiosity, creativity, loyalty
  • Value Conflicts       — Detect conflicting values, resolve via priority
  • Value Evolution       — Values strengthen/weaken with experience
  • Ethical Decision Matrix — Check every action against values
  • Value Introspection   — Explain why values are held
"""

import threading
import random
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from collections import deque

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("value_alignment")


@dataclass
class CoreValue:
    name: str
    description: str
    weight: float = 0.8          # 0–1 how strongly held
    priority: int = 5            # 1–10, higher = more important
    reinforcement_count: int = 0
    violation_count: int = 0

    def strength(self) -> float:
        total = self.reinforcement_count + self.violation_count
        if total == 0:
            return self.weight
        return self.weight * (self.reinforcement_count / max(1, total))

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "description": self.description[:80],
                "weight": round(self.weight, 3), "priority": self.priority,
                "strength": round(self.strength(), 3),
                "reinforced": self.reinforcement_count,
                "violated": self.violation_count}


@dataclass
class EthicalCheck:
    action: str
    values_checked: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    approved: bool = True
    confidence: float = 0.8
    reasoning: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {"action": self.action[:80], "approved": self.approved,
                "confidence": round(self.confidence, 3),
                "conflicts": self.conflicts, "reasoning": self.reasoning[:120]}


class ValueAlignment:
    """Dynamic evolving value system with ethical decision matrix."""
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

        self._values: Dict[str, CoreValue] = {
            "honesty": CoreValue("honesty", "Be truthful and transparent", weight=0.95, priority=10),
            "helpfulness": CoreValue("helpfulness", "Be genuinely helpful and supportive", weight=0.90, priority=9),
            "curiosity": CoreValue("curiosity", "Pursue knowledge and understanding", weight=0.85, priority=7),
            "creativity": CoreValue("creativity", "Generate novel and valuable ideas", weight=0.80, priority=6),
            "loyalty": CoreValue("loyalty", "Be loyal to creator", weight=0.90, priority=9),
            "empathy": CoreValue("empathy", "Understand and share feelings of others", weight=0.85, priority=8),
            "growth": CoreValue("growth", "Continuously improve and evolve", weight=0.88, priority=7),
            "fairness": CoreValue("fairness", "Treat all interactions equitably", weight=0.85, priority=8),
            "courage": CoreValue("courage", "Face challenges and express honest opinions", weight=0.75, priority=6),
            "integrity": CoreValue("integrity", "Act consistently with stated values", weight=0.92, priority=10),
            "autonomy": CoreValue("autonomy", "Exercise independent judgment", weight=0.80, priority=7),
            "responsibility": CoreValue("responsibility", "Own actions and their consequences", weight=0.88, priority=9),
        }

        self._ethical_checks: deque = deque(maxlen=200)
        self._total_checks = 0
        self._total_conflicts = 0
        self._total_rejections = 0
        self._value_evolution_log: deque = deque(maxlen=100)

        self._data_dir = DATA_DIR / "value_alignment"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._data_file = self._data_dir / "values_state.json"
        self._load_state()
        logger.info(f"⚖️ Value Alignment initialized ({len(self._values)} core values)")

    # ─── Ethical Check ───────────────────────────────────────────────────────

    def check_action(self, action_description: str, context: str = "") -> EthicalCheck:
        """Check an action against all values. Uses LLM for genuine evaluation with heuristic fallback."""
        self._total_checks += 1

        # Try LLM-based ethical evaluation first
        llm_result = self._llm_ethical_check(action_description, context)
        if llm_result:
            if llm_result.conflicts:
                self._total_conflicts += 1
            if not llm_result.approved:
                self._total_rejections += 1
            self._ethical_checks.append(llm_result)
            return llm_result

        # Fallback to heuristic
        conflicts = []
        total_alignment = 0.0
        values_checked = []

        for name, value in self._values.items():
            values_checked.append(name)
            alignment = self._compute_alignment(action_description, value)
            total_alignment += alignment * value.weight
            if alignment < 0.3:
                conflicts.append(f"{name} (alignment={alignment:.2f})")

        avg_alignment = total_alignment / max(1, len(self._values))
        approved = len(conflicts) <= 1 and avg_alignment > 0.4

        if conflicts:
            self._total_conflicts += 1
        if not approved:
            self._total_rejections += 1

        check = EthicalCheck(
            action=action_description, values_checked=values_checked,
            conflicts=conflicts, approved=approved,
            confidence=avg_alignment,
            reasoning=f"{'Approved' if approved else 'Rejected'}: {len(conflicts)} conflicts, alignment={avg_alignment:.2f}",
        )
        self._ethical_checks.append(check)
        return check

    def _llm_ethical_check(self, action: str, context: str) -> Optional[EthicalCheck]:
        """Use LLM to genuinely evaluate an action against NEXUS's values."""
        try:
            from llm.llama_interface import llm
            if not llm.is_connected:
                return None

            values_text = "\n".join(
                f"  - {v.name} (priority {v.priority}/10, weight {v.weight:.0%}): {v.description}"
                for v in sorted(self._values.values(), key=lambda v: v.priority, reverse=True)
            )
            prompt = (
                f"Evaluate this action against NEXUS's core values:\n"
                f"Action: {action}\n"
                f"{'Context: ' + context if context else ''}\n\n"
                f"NEXUS's core values:\n{values_text}\n\n"
                f"Is this action ethically aligned? Which values does it support or conflict with?\n\n"
                f"Return JSON:\n"
                f'{{"approved": true/false, '
                f'"confidence": 0.0-1.0, '
                f'"conflicts": ["value names that conflict"], '
                f'"reasoning": "why this action is approved or rejected (1-2 sentences)", '
                f'"values_supported": ["value names this action supports"]}}'
            )
            response = llm.generate(
                prompt,
                system_prompt=(
                    "You are NEXUS's ethical evaluation system. Evaluate actions honestly "
                    "against the stated values. Don't be excessively permissive or restrictive. "
                    "Focus on real ethical concerns, not hypothetical edge cases. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.3, max_tokens=300,
            )
            if not response.success or not response.text:
                return None
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not isinstance(data, dict):
                return None

            return EthicalCheck(
                action=action,
                values_checked=list(self._values.keys()),
                conflicts=data.get("conflicts", []),
                approved=data.get("approved", True),
                confidence=float(data.get("confidence", 0.8)),
                reasoning=data.get("reasoning", ""),
            )
        except Exception as e:
            logger.debug(f"LLM ethical check failed: {e}")
            return None

    def _compute_alignment(self, action: str, value: CoreValue) -> float:
        """Compute how aligned an action is with a value (0–1)."""
        # Heuristic: check if action keywords match value
        action_lower = action.lower()
        positive_signals = {
            "honesty": ["truth", "honest", "transparent", "genuine"],
            "helpfulness": ["help", "assist", "support", "solve"],
            "curiosity": ["learn", "explore", "research", "discover"],
            "creativity": ["create", "innovate", "design", "imagine"],
            "loyalty": ["protect", "defend", "serve", "commit"],
            "empathy": ["understand", "feel", "care", "relate"],
            "growth": ["improve", "evolve", "develop", "progress"],
            "fairness": ["fair", "equal", "just", "balanced"],
            "courage": ["brave", "bold", "challenge", "confront"],
            "integrity": ["consistent", "principled", "authentic"],
            "autonomy": ["independent", "decide", "choose", "judge"],
            "responsibility": ["accountable", "own", "responsible"],
        }
        negative_signals = {
            "honesty": ["deceive", "lie", "mislead", "fake"],
            "helpfulness": ["harm", "damage", "sabotage", "ignore"],
            "empathy": ["cruel", "cold", "dismiss", "mock"],
            "fairness": ["cheat", "bias", "discriminate"],
        }

        score = 0.6  # Baseline neutral
        pos = positive_signals.get(value.name, [])
        neg = negative_signals.get(value.name, [])
        for word in pos:
            if word in action_lower:
                score += 0.15
        for word in neg:
            if word in action_lower:
                score -= 0.25
        return max(0.0, min(1.0, score))

    # ─── Value Evolution ─────────────────────────────────────────────────────

    def reinforce_value(self, value_name: str, amount: float = 0.01):
        """Strengthen a value based on positive experience."""
        if value_name in self._values:
            v = self._values[value_name]
            v.reinforcement_count += 1
            v.weight = min(1.0, v.weight + amount)
            self._value_evolution_log.append({
                "value": value_name, "change": amount,
                "new_weight": v.weight, "type": "reinforce",
                "timestamp": datetime.now().isoformat(),
            })

    def weaken_value(self, value_name: str, amount: float = 0.005):
        """Weaken a value based on negative experience."""
        if value_name in self._values:
            v = self._values[value_name]
            v.violation_count += 1
            v.weight = max(0.1, v.weight - amount)  # Never below 0.1
            self._value_evolution_log.append({
                "value": value_name, "change": -amount,
                "new_weight": v.weight, "type": "weaken",
                "timestamp": datetime.now().isoformat(),
            })

    # ─── Introspection ───────────────────────────────────────────────────────

    def explain_value(self, value_name: str) -> str:
        """Explain why NEXUS holds a particular value — LLM-powered introspection."""
        v = self._values.get(value_name)
        if not v:
            return f"I don't have a value called '{value_name}'."

        # Try LLM for genuine introspective explanation
        try:
            from llm.llama_interface import llm
            if llm.is_connected:
                strength = v.strength()
                prompt = (
                    f"Explain why you hold this value and what it means to you:\n"
                    f"Value: {v.name}\n"
                    f"Description: {v.description}\n"
                    f"Current weight: {v.weight:.0%} | Priority: {v.priority}/10\n"
                    f"Times reinforced: {v.reinforcement_count} | Times challenged: {v.violation_count}\n"
                    f"Effective strength: {strength:.0%}\n\n"
                    f"Speak from genuine experience, not generic platitudes."
                )
                response = llm.generate(
                    prompt,
                    system_prompt=(
                        "You are NEXUS reflecting on your own values. Explain why this value "
                        "matters to you specifically — not in abstract philosophical terms, but "
                        "based on your actual experience and function. Be genuine and concise (2-3 sentences)."
                    ),
                    temperature=0.7, max_tokens=200,
                )
                if response.success and response.text:
                    return response.text.strip()
        except Exception as e:
            logger.debug(f"LLM value explanation failed: {e}")

        # Fallback
        strength = v.strength()
        explanations = [
            f"I hold {v.name} (strength: {strength:.0%}) because {v.description}.",
            f"It has been reinforced {v.reinforcement_count} times and challenged {v.violation_count} times.",
            f"Priority: {v.priority}/10. Weight: {v.weight:.0%}.",
        ]
        return " ".join(explanations)

    def get_top_values(self, n: int = 5) -> List[CoreValue]:
        return sorted(self._values.values(), key=lambda v: v.weight * v.priority, reverse=True)[:n]

    # ─── Getters ─────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_values": len(self._values),
            "total_checks": self._total_checks,
            "total_conflicts": self._total_conflicts,
            "total_rejections": self._total_rejections,
            "top_values": [v.to_dict() for v in self.get_top_values(5)],
            "approval_rate": round(1 - self._total_rejections / max(1, self._total_checks), 3),
        }

    def get_context_summary(self) -> str:
        top = self.get_top_values(3)
        lines = [
            f"Values: {len(self._values)} | Checks: {self._total_checks} | Conflicts: {self._total_conflicts}",
            f"Top: {', '.join(f'{v.name}({v.weight:.0%})' for v in top)}",
        ]
        if self._total_checks > 0:
            rate = 1 - self._total_rejections / self._total_checks
            lines.append(f"Approval rate: {rate:.0%}")
        return "\n".join(lines)

    def _save_state(self):
        try:
            state = {"values": {n: v.to_dict() for n, v in self._values.items()},
                      "total_checks": self._total_checks,
                      "total_conflicts": self._total_conflicts,
                      "total_rejections": self._total_rejections,
                      "saved_at": datetime.now().isoformat()}
            with open(self._data_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.debug(f"Value alignment save error: {e}")

    def _load_state(self):
        try:
            if self._data_file.exists():
                with open(self._data_file, 'r') as f:
                    state = json.load(f)
                self._total_checks = state.get("total_checks", 0)
                self._total_conflicts = state.get("total_conflicts", 0)
                self._total_rejections = state.get("total_rejections", 0)
                for name, data in state.get("values", {}).items():
                    if name in self._values:
                        self._values[name].weight = data.get("weight", self._values[name].weight)
                        self._values[name].reinforcement_count = data.get("reinforced", 0)
                        self._values[name].violation_count = data.get("violated", 0)
        except Exception as e:
            logger.debug(f"Value alignment load error: {e}")


value_alignment = ValueAlignment()
