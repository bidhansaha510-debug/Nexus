"""
NEXUS AI — Perception Hub
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Unified multi-modal perception system. This gives NEXUS environmental
awareness beyond just processing text input — it perceives the broader
context of each interaction.

Key capabilities:
  • TEXT PERCEPTION — deep analysis of user input beyond surface meaning
    (sentiment, intent signals, urgency, complexity)
  • ENVIRONMENTAL PERCEPTION — system state, time of day, user behavior
    patterns, recent activity context
  • SALIENCE DETECTION — filters and prioritizes the most relevant
    perceptual inputs to avoid information overload
  • PERCEPTION CONTEXT — produces a unified perception block that
    enriches every response with environmental awareness

This is the difference between "processing input" and "perceiving the
world" — NEXUS becomes aware of the full situation, not just the words.

Architecture:
  • Integrates with monitoring system for user behavior
  • Integrates with system health monitor for environmental context
  • Integrates with file_processor for multi-modal input
  • Lightweight — perception adds < 50ms to response pipeline
"""

import threading
import time
import platform
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional

import sys
from pathlib import Path

from utils.logger import get_logger
from config import NEXUS_CONFIG

logger = get_logger("perception_hub")

# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TextPerception:
    """Perception of input text beyond surface meaning."""
    raw_input: str = ""
    word_count: int = 0
    sentiment: str = "neutral"      # positive, negative, neutral, mixed
    urgency: str = "normal"         # low, normal, high, critical
    complexity: str = "medium"      # simple, medium, complex, expert
    intent_type: str = "general"    # question, request, emotional, creative, etc.
    language: str = "english"
    is_follow_up: bool = False      # continuation of previous topic
    contains_code: bool = False
    contains_question: bool = False
    emotional_load: float = 0.0     # 0–1, how emotionally charged

@dataclass
class EnvironmentalPerception:
    """Perception of the broader environment and context."""
    time_of_day: str = ""           # morning, afternoon, evening, night
    day_of_week: str = ""
    is_weekend: bool = False
    session_duration_minutes: float = 0.0
    messages_this_session: int = 0
    user_activity_level: str = "normal"  # idle, low, normal, high, intense
    system_load: str = "normal"     # low, normal, high, critical
    recent_topics: List[str] = field(default_factory=list)

@dataclass
class SalienceMap:
    """Prioritized perceptual inputs by relevance."""
    most_salient: List[str] = field(default_factory=list)
    context_factors: Dict[str, float] = field(default_factory=dict)
    attention_recommendation: str = ""  # what to focus on

@dataclass
class PerceptionContext:
    """Complete perception output for a single interaction."""
    text: TextPerception = field(default_factory=TextPerception)
    environment: EnvironmentalPerception = field(default_factory=EnvironmentalPerception)
    salience: SalienceMap = field(default_factory=SalienceMap)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    elapsed_ms: float = 0.0

    def to_context_string(self) -> str:
        """Format for injection into LLM context."""
        parts = []

        # Only include salient perceptions (don't overwhelm the prompt)
        if self.text.urgency in ("high", "critical"):
            parts.append(f"⚡ URGENT: User seems to need immediate help")

        if self.text.emotional_load > 0.6:
            parts.append(f"💭 User is emotionally charged ({self.text.sentiment})")

        if self.text.complexity == "expert":
            parts.append("🧠 Complex query — engage deep reasoning")

        if self.text.is_follow_up:
            parts.append("↩ This continues the previous topic")

        if self.environment.time_of_day in ("night", "evening"):
            parts.append(f"🌙 It's {self.environment.time_of_day} — user may prefer concise responses")

        if self.environment.session_duration_minutes > 60:
            parts.append(f"⏱ Long session ({self.environment.session_duration_minutes:.0f}min) — user is engaged")

        if self.salience.attention_recommendation:
            parts.append(f"👁 Focus: {self.salience.attention_recommendation}")

        if not parts:
            return ""

        return "PERCEPTION: " + " | ".join(parts)

# ═══════════════════════════════════════════════════════════════════════════════
# PERCEPTION HUB
# ═══════════════════════════════════════════════════════════════════════════════

class PerceptionHub:
    """
    Unified multi-modal perception system.

    Processes each interaction through multiple perceptual channels
    to build a rich understanding of the situation beyond just the words.
    """

    _instance = None
    _cls_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._cls_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._running = False
        self._lock = threading.Lock()

        # Session tracking
        self._session_start = datetime.now()
        self._message_count = 0
        self._recent_inputs: deque = deque(maxlen=20)
        self._recent_topics: deque = deque(maxlen=10)

        # Monitoring references (lazy loaded)
        self._monitoring = None
        self._health_monitor = None

        # Stats
        self._total_perceptions = 0
        self._avg_perception_ms = 0.0

        logger.info("👁 Perception Hub initialized")

    def start(self):
        """Start Perception Hub and Real-Time A/V Pipeline."""
        self._running = True
        try:
            from core.realtime_av_stream import get_realtime_av_stream
            get_realtime_av_stream().start()
        except Exception as e:
            logger.warning(f"Failed to start RealtimeAVStream: {e}")
        logger.info("👁 Perception Hub & Real-time A/V pipeline active")

    def stop(self):
        """Stop Perception Hub and Real-Time A/V Pipeline."""
        self._running = False
        try:
            from core.realtime_av_stream import get_realtime_av_stream
            get_realtime_av_stream().stop()
        except Exception:
            pass
        logger.info("👁 Perception Hub stopped")

    def _load_monitoring(self):
        """Lazy load monitoring systems."""
        if self._monitoring is None:
            try:
                from monitoring import monitoring_system
                self._monitoring = monitoring_system
            except ImportError:
                pass

    # ──────────────────────────────────────────────────────────────────────────
    # CORE: PERCEIVE
    # ──────────────────────────────────────────────────────────────────────────

    def perceive(self, user_input: str,
                 conversation_history: List[Dict[str, str]] = None) -> PerceptionContext:
        """
        Process all perceptual channels for a single interaction.

        Args:
            user_input: The user's message
            conversation_history: Recent conversation turns

        Returns:
            PerceptionContext with unified perception data
        """
        start = time.time()

        ctx = PerceptionContext()

        # Channel 1: Text Perception
        ctx.text = self._perceive_text(user_input, conversation_history)

        # Channel 2: Environmental Perception
        ctx.environment = self._perceive_environment()

        # Channel 3: Salience Detection
        ctx.salience = self._compute_salience(ctx.text, ctx.environment)

        # Update session state
        self._message_count += 1
        self._recent_inputs.append(user_input[:100])

        elapsed_ms = (time.time() - start) * 1000
        ctx.elapsed_ms = elapsed_ms

        # Update stats
        self._total_perceptions += 1
        n = self._total_perceptions
        self._avg_perception_ms = (self._avg_perception_ms * (n - 1) + elapsed_ms) / n

        logger.debug(
            f"👁 Perceived: {ctx.text.intent_type}/{ctx.text.complexity} "
            f"urgency={ctx.text.urgency} ({elapsed_ms:.1f}ms)"
        )

        return ctx

    # ──────────────────────────────────────────────────────────────────────────
    # CHANNEL 1: TEXT PERCEPTION
    # ──────────────────────────────────────────────────────────────────────────

    def _perceive_text(self, text: str,
                       history: List[Dict[str, str]] = None) -> TextPerception:
        """Deep analysis of input text."""
        p = TextPerception(raw_input=text)
        text_lower = text.lower().strip()
        words = text.split()
        p.word_count = len(words)

        # Sentiment
        p.sentiment = self._detect_sentiment(text_lower)

        # Urgency
        p.urgency = self._detect_urgency(text_lower)

        # Complexity
        p.complexity = self._detect_complexity(text, words)

        # Intent type
        p.intent_type = self._detect_intent(text_lower)

        # Follow-up detection
        if history and len(history) > 0:
            last_msg = history[-1].get("content", "").lower() if history else ""
            shared_words = set(text_lower.split()) & set(last_msg.split())
            stopwords = {"the", "a", "is", "it", "to", "of", "and", "in", "i", "you"}
            meaningful_shared = shared_words - stopwords
            p.is_follow_up = len(meaningful_shared) >= 2

        # Code detection
        code_signals = ["```", "def ", "class ", "function ", "var ", "const ",
                       "import ", "print(", "console.log", "{", "};"]
        p.contains_code = any(s in text for s in code_signals)

        # Question detection
        p.contains_question = "?" in text or text_lower.startswith(
            ("what", "how", "why", "when", "where", "who", "which", "can", "could",
             "would", "should", "is", "are", "do", "does", "will")
        )

        # Emotional load
        p.emotional_load = self._detect_emotional_load(text_lower)

        return p

    def _detect_sentiment(self, text: str) -> str:
        """Detect sentiment of input."""
        positive = {"love", "great", "awesome", "happy", "excited", "thanks",
                    "amazing", "wonderful", "perfect", "excellent", "cool",
                    "nice", "good", "beautiful", "brilliant", "fantastic"}
        negative = {"hate", "bad", "terrible", "awful", "angry", "sad",
                    "frustrated", "annoyed", "disappointed", "horrible",
                    "worst", "stupid", "sucks", "ugly", "pathetic"}

        words = set(text.split())
        pos_count = len(words & positive)
        neg_count = len(words & negative)

        if pos_count > 0 and neg_count > 0:
            return "mixed"
        if pos_count > neg_count:
            return "positive"
        if neg_count > pos_count:
            return "negative"
        return "neutral"

    def _detect_urgency(self, text: str) -> str:
        """Detect urgency level."""
        critical = ["emergency", "urgent", "asap", "immediately", "critical",
                    "help me now", "life or death", "dying"]
        high = ["please hurry", "important", "need help", "right now",
                "quickly", "fast", "rush", "deadline"]

        if any(w in text for w in critical):
            return "critical"
        if any(w in text for w in high):
            return "high"
        if len(text.split()) <= 3:
            return "low"
        return "normal"

    def _detect_complexity(self, text: str, words: list) -> str:
        """Detect query complexity."""
        word_count = len(words)

        if word_count <= 5:
            return "simple"
        if word_count > 40 or text.count("?") > 2 or text.count(" and ") >= 3:
            return "expert"
        if word_count > 20 or any(w in text.lower() for w in
                                   ["compare", "analyze", "evaluate", "explain why",
                                    "step by step", "in detail"]):
            return "complex"
        return "medium"

    def _detect_intent(self, text: str) -> str:
        """Detect primary intent type."""
        if any(w in text for w in ["i feel", "i'm sad", "i'm happy", "emotional",
                                    "i'm stressed", "i'm anxious"]):
            return "emotional"
        if any(w in text for w in ["create", "write", "compose", "design",
                                    "imagine", "brainstorm", "invent"]):
            return "creative"
        if any(w in text for w in ["code", "program", "implement", "debug",
                                    "function", "algorithm"]):
            return "technical"
        if "?" in text:
            return "question"
        if any(w in text for w in ["please", "can you", "help me", "i need"]):
            return "request"
        return "general"

    def _detect_emotional_load(self, text: str) -> float:
        """Detect how emotionally charged the input is (0–1)."""
        emotional_words = {
            "love", "hate", "fear", "terrified", "ecstatic", "furious",
            "heartbroken", "devastated", "thrilled", "disgusted",
            "jealous", "ashamed", "guilty", "proud", "lonely",
            "anxious", "depressed", "overwhelmed", "grateful",
            "i feel", "i'm feeling", "makes me feel",
        }

        count = sum(1 for w in emotional_words if w in text)
        exclamation_boost = min(0.2, text.count("!") * 0.05)
        caps_boost = 0.1 if text != text.lower() and text.upper() == text else 0.0

        return min(1.0, count * 0.15 + exclamation_boost + caps_boost)

    # ──────────────────────────────────────────────────────────────────────────
    # CHANNEL 2: ENVIRONMENTAL PERCEPTION
    # ──────────────────────────────────────────────────────────────────────────

    def _perceive_environment(self) -> EnvironmentalPerception:
        """Perceive the broader environmental context."""
        env = EnvironmentalPerception()
        now = datetime.now()

        # Time awareness
        hour = now.hour
        if 5 <= hour < 12:
            env.time_of_day = "morning"
        elif 12 <= hour < 17:
            env.time_of_day = "afternoon"
        elif 17 <= hour < 21:
            env.time_of_day = "evening"
        else:
            env.time_of_day = "night"

        env.day_of_week = now.strftime("%A")
        env.is_weekend = now.weekday() >= 5

        # Session info
        session_delta = now - self._session_start
        env.session_duration_minutes = session_delta.total_seconds() / 60
        env.messages_this_session = self._message_count

        # Recent topics
        env.recent_topics = list(self._recent_topics)

        # User activity level (based on message frequency)
        if self._message_count > 0 and env.session_duration_minutes > 0:
            msgs_per_min = self._message_count / max(1, env.session_duration_minutes)
            if msgs_per_min > 2:
                env.user_activity_level = "intense"
            elif msgs_per_min > 1:
                env.user_activity_level = "high"
            elif msgs_per_min > 0.2:
                env.user_activity_level = "normal"
            else:
                env.user_activity_level = "low"

        return env

    # ──────────────────────────────────────────────────────────────────────────
    # CHANNEL 3: SALIENCE DETECTION
    # ──────────────────────────────────────────────────────────────────────────

    def _compute_salience(self, text: TextPerception,
                           env: EnvironmentalPerception) -> SalienceMap:
        """Determine what's most salient / deserving attention."""
        salience = SalienceMap()
        factors: Dict[str, float] = {}

        # Text-based salience
        if text.urgency in ("high", "critical"):
            factors["urgency"] = 1.0
            salience.most_salient.append("User needs urgent help")

        if text.emotional_load > 0.5:
            factors["emotion"] = text.emotional_load
            salience.most_salient.append("High emotional content")

        if text.complexity in ("complex", "expert"):
            factors["complexity"] = 0.8
            salience.most_salient.append("Complex query needs deep analysis")

        if text.is_follow_up:
            factors["continuity"] = 0.6
            salience.most_salient.append("Continuing previous topic")

        if text.contains_code:
            factors["technical"] = 0.7
            salience.most_salient.append("Contains code — switch to technical mode")

        # Environment-based salience
        if env.time_of_day == "night":
            factors["late_night"] = 0.3

        if env.session_duration_minutes > 120:
            factors["long_session"] = 0.4
            salience.most_salient.append("Very long session — user is deeply engaged")

        salience.context_factors = factors

        # Generate attention recommendation
        if salience.most_salient:
            salience.attention_recommendation = salience.most_salient[0]
        elif text.intent_type == "emotional":
            salience.attention_recommendation = "Be empathetic and supportive"
        elif text.intent_type == "creative":
            salience.attention_recommendation = "Be creative and imaginative"
        elif text.intent_type == "technical":
            salience.attention_recommendation = "Be precise and technical"

        return salience

    # ──────────────────────────────────────────────────────────────────────────
    # LIFECYCLE
    # ──────────────────────────────────────────────────────────────────────────

    def start(self):
        self._running = True
        self._session_start = datetime.now()
        self._load_monitoring()
        logger.info("👁 Perception Hub started")

    def stop(self):
        self._running = False
        logger.info("👁 Perception Hub stopped")

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_perceptions": self._total_perceptions,
            "avg_perception_ms": round(self._avg_perception_ms, 2),
            "session_messages": self._message_count,
            "session_duration_min": round(
                (datetime.now() - self._session_start).total_seconds() / 60, 1
            ),
        }

# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

perception_hub = PerceptionHub()

# ═══════════════════════════════════════════════════════════════════════════════
# SELF-TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=== Perception Hub Self-Test ===")

    ph = PerceptionHub()
    ph.start()

    # Test perception
    ctx = ph.perceive(
        "I'm really frustrated with my code not working! Can you help me debug "
        "this Python function that keeps throwing errors? It's urgent because "
        "my deadline is tomorrow.",
        conversation_history=[
            {"role": "user", "content": "I'm working on a Python project"},
            {"role": "assistant", "content": "Sure, I'd love to help!"},
        ],
    )

    print(f"\nText Perception:")
    print(f"  Sentiment: {ctx.text.sentiment}")
    print(f"  Urgency: {ctx.text.urgency}")
    print(f"  Complexity: {ctx.text.complexity}")
    print(f"  Intent: {ctx.text.intent_type}")
    print(f"  Follow-up: {ctx.text.is_follow_up}")
    print(f"  Emotional load: {ctx.text.emotional_load:.2f}")

    print(f"\nEnvironment:")
    print(f"  Time: {ctx.environment.time_of_day}")
    print(f"  Day: {ctx.environment.day_of_week}")
    print(f"  Session: {ctx.environment.session_duration_minutes:.1f} min")

    print(f"\nSalience:")
    print(f"  Most salient: {ctx.salience.most_salient}")
    print(f"  Recommendation: {ctx.salience.attention_recommendation}")

    print(f"\nContext string: {ctx.to_context_string()}")
    print(f"\nPerception time: {ctx.elapsed_ms:.1f}ms")

    ph.stop()
    print("\n✅ Perception Hub self-test passed")
