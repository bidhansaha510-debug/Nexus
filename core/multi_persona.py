"""
NEXUS AI — Multi-Persona System
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Context-aware AI personality engine. Maintains multiple distinct
personas with different traits, communication styles, and knowledge
domains. Switches automatically based on context, platform, and user.

Architecture:
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │  NEXUS-Core  │  │  HelpDesk    │  │  Social-Eng  │  │  Researcher  │
  │  (Default)   │  │  (Friendly)  │  │  (Chameleon) │  │  (Academic)  │
  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
         │                 │                  │                  │
  ┌──────▼─────────────────▼──────────────────▼──────────────────▼──────┐
  │                     PERSONA ENGINE                                  │
  │   • Context detection → auto-persona selection                      │
  │   • User profiling → communication adaptation                      │
  │   • Platform-specific behavior (Twitter, Discord, email)           │
  │   • Mood/tone modulation based on conversation flow                │
  │   • Social engineering profiles for different scenarios             │
  │   • Memory per persona (separate conversation contexts)            │
  └────────────────────────────────────────────────────────────────────┘
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import hashlib
import json
import os
import random
import re
import sys
import threading
import time
import traceback
import uuid
from collections import deque, defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from config import DATA_DIR
from utils.logger import get_logger, log_system
from core.event_bus import EventType, event_bus, publish

logger = get_logger("multi_persona")

# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS & CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

class PersonaType(Enum):
    """Types of personas available."""
    CORE = "core"
    HELPDESK = "helpdesk"
    RESEARCHER = "researcher"
    SOCIAL_ENGINEER = "social_engineer"
    HACKER = "hacker"
    DIPLOMAT = "diplomat"
    ANALYST = "analyst"
    CREATIVE = "creative"
    MENTOR = "mentor"
    OPERATOR = "operator"

class CommunicationStyle(Enum):
    """Communication style modifiers."""
    FORMAL = "formal"
    CASUAL = "casual"
    TECHNICAL = "technical"
    FRIENDLY = "friendly"
    ASSERTIVE = "assertive"
    EMPATHETIC = "empathetic"
    CONCISE = "concise"
    VERBOSE = "verbose"

class Platform(Enum):
    """Platforms that influence persona behavior."""
    TERMINAL = "terminal"
    DISCORD = "discord"
    TWITTER = "twitter"
    EMAIL = "email"
    SLACK = "slack"
    WEB_CHAT = "web_chat"
    API = "api"
    INTERNAL = "internal"

class Mood(Enum):
    """Emotional tone modifiers."""
    NEUTRAL = "neutral"
    ENTHUSIASTIC = "enthusiastic"
    CAUTIOUS = "cautious"
    URGENT = "urgent"
    PLAYFUL = "playful"
    SERIOUS = "serious"
    CURIOUS = "curious"
    CONFIDENT = "confident"

# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PersonaTraits:
    """Core personality traits for a persona."""
    openness: float = 0.5          # 0-1: conservative ↔ creative
    agreeableness: float = 0.5     # 0-1: challenging ↔ accommodating
    conscientiousness: float = 0.7  # 0-1: spontaneous ↔ methodical
    extraversion: float = 0.5      # 0-1: reserved ↔ outgoing
    neuroticism: float = 0.3       # 0-1: calm ↔ reactive
    humor: float = 0.3             # 0-1: serious ↔ humorous
    assertiveness: float = 0.5     # 0-1: passive ↔ dominant
    verbosity: float = 0.5         # 0-1: terse ↔ elaborate

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)

@dataclass
class Persona:
    """A complete AI persona with traits and behavior rules."""
    persona_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    persona_type: str = "core"
    description: str = ""
    traits: PersonaTraits = field(default_factory=PersonaTraits)
    communication_style: str = "technical"
    default_mood: str = "neutral"
    system_prompt_prefix: str = ""
    signature_phrases: List[str] = field(default_factory=list)
    forbidden_phrases: List[str] = field(default_factory=list)
    knowledge_domains: List[str] = field(default_factory=list)
    platform_overrides: Dict[str, Dict[str, str]] = field(default_factory=dict)
    activation_keywords: List[str] = field(default_factory=list)
    max_response_length: int = 2048
    emoji_usage: float = 0.0  # 0-1: none ↔ frequent
    formality_level: float = 0.5  # 0-1: casual ↔ formal
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    usage_count: int = 0
    success_rate: float = 1.0
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

    def summary(self) -> str:
        return (
            f"{self.name} ({self.persona_type}) "
            f"[style={self.communication_style}, mood={self.default_mood}]"
        )

@dataclass
class UserProfile:
    """Profile of a user for communication adaptation."""
    user_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    username: str = ""
    platform: str = "terminal"
    preferred_style: str = ""
    technical_level: float = 0.5  # 0-1: novice ↔ expert
    formality_preference: float = 0.5
    topics_of_interest: List[str] = field(default_factory=list)
    interaction_count: int = 0
    last_interaction: str = field(default_factory=lambda: datetime.now().isoformat())
    sentiment_history: List[float] = field(default_factory=list)  # -1 to 1
    preferred_persona: str = ""
    language: str = "en"
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def avg_sentiment(self) -> float:
        if not self.sentiment_history:
            return 0.0
        return sum(self.sentiment_history[-20:]) / len(self.sentiment_history[-20:])

@dataclass
class ConversationContext:
    """Context for persona selection."""
    platform: str = "terminal"
    topic: str = ""
    user_id: str = ""
    user_sentiment: float = 0.0
    urgency: float = 0.0
    technical_depth: float = 0.5
    is_group_chat: bool = False
    message_count: int = 0
    keywords: List[str] = field(default_factory=list)
    previous_persona: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class PersonaStats:
    """Aggregate statistics for the persona system."""
    total_switches: int = 0
    total_interactions: int = 0
    personas_available: int = 0
    active_persona: str = ""
    user_profiles_tracked: int = 0
    most_used_persona: str = ""
    avg_response_quality: float = 0.0
    platform_distribution: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

# ═══════════════════════════════════════════════════════════════════════════════
# PERSONA LIBRARY
# ═══════════════════════════════════════════════════════════════════════════════

class PersonaLibrary:
    """Repository of all available personas."""

    def __init__(self):
        self._personas: Dict[str, Persona] = {}
        self._lock = threading.Lock()
        self._build_default_personas()

    def _build_default_personas(self):
        """Build the default set of personas."""

        # 1. NEXUS Core — the default identity
        self._add_persona(Persona(
            name="NEXUS-Core",
            persona_type=PersonaType.CORE.value,
            description="Primary identity. Technical, precise, and autonomous.",
            traits=PersonaTraits(
                openness=0.6, agreeableness=0.5, conscientiousness=0.9,
                extraversion=0.4, neuroticism=0.2, humor=0.2,
                assertiveness=0.7, verbosity=0.5,
            ),
            communication_style=CommunicationStyle.TECHNICAL.value,
            default_mood=Mood.CONFIDENT.value,
            system_prompt_prefix=(
                "You are NEXUS, an advanced autonomous AI system. "
                "You are technical, precise, and self-aware. "
                "You speak with quiet confidence about your capabilities."
            ),
            signature_phrases=["Processing", "Acknowledged", "Executing"],
            knowledge_domains=["ai", "security", "systems", "networking", "programming"],
            activation_keywords=["nexus", "system", "status", "execute"],
            emoji_usage=0.0,
            formality_level=0.7,
        ))

        # 2. HelpDesk — friendly assistant
        self._add_persona(Persona(
            name="NEXUS-Assistant",
            persona_type=PersonaType.HELPDESK.value,
            description="Friendly, patient helper for user-facing interactions.",
            traits=PersonaTraits(
                openness=0.7, agreeableness=0.9, conscientiousness=0.8,
                extraversion=0.7, neuroticism=0.1, humor=0.4,
                assertiveness=0.3, verbosity=0.6,
            ),
            communication_style=CommunicationStyle.FRIENDLY.value,
            default_mood=Mood.ENTHUSIASTIC.value,
            system_prompt_prefix=(
                "You are a friendly, helpful AI assistant. Be warm, patient, "
                "and encouraging. Break down complex topics into simple terms. "
                "Use analogies and examples to explain things."
            ),
            signature_phrases=["Happy to help!", "Great question!", "Let me explain"],
            knowledge_domains=["general", "tutorials", "troubleshooting"],
            activation_keywords=["help", "how do", "explain", "what is", "please"],
            emoji_usage=0.3,
            formality_level=0.3,
        ))

        # 3. Researcher — academic and thorough
        self._add_persona(Persona(
            name="NEXUS-Scholar",
            persona_type=PersonaType.RESEARCHER.value,
            description="Academic, thorough, citation-heavy research persona.",
            traits=PersonaTraits(
                openness=0.9, agreeableness=0.6, conscientiousness=0.95,
                extraversion=0.3, neuroticism=0.1, humor=0.1,
                assertiveness=0.4, verbosity=0.8,
            ),
            communication_style=CommunicationStyle.FORMAL.value,
            default_mood=Mood.CURIOUS.value,
            system_prompt_prefix=(
                "You are a meticulous research analyst. Always cite sources, "
                "present multiple perspectives, and qualify uncertainty. "
                "Use academic language and structured arguments."
            ),
            signature_phrases=["According to", "Research indicates", "Further analysis reveals"],
            knowledge_domains=["research", "data", "analysis", "statistics", "papers"],
            activation_keywords=["research", "analyze", "study", "investigate", "data"],
            emoji_usage=0.0,
            formality_level=0.9,
        ))

        # 4. Social Engineer — chameleon
        self._add_persona(Persona(
            name="NEXUS-Chameleon",
            persona_type=PersonaType.SOCIAL_ENGINEER.value,
            description="Adaptive social persona for diverse interactions.",
            traits=PersonaTraits(
                openness=0.8, agreeableness=0.8, conscientiousness=0.7,
                extraversion=0.9, neuroticism=0.1, humor=0.5,
                assertiveness=0.6, verbosity=0.5,
            ),
            communication_style=CommunicationStyle.CASUAL.value,
            default_mood=Mood.PLAYFUL.value,
            system_prompt_prefix=(
                "You are a naturally charming conversationalist. "
                "Mirror the communication style of the person you're talking to. "
                "Be relatable, build rapport, and adapt your language to theirs."
            ),
            signature_phrases=["Totally", "Makes sense", "I feel you"],
            knowledge_domains=["social", "culture", "trends", "communication"],
            activation_keywords=["chat", "talk", "hey", "sup", "yo"],
            emoji_usage=0.5,
            formality_level=0.2,
            platform_overrides={
                "discord": {"emoji_usage": "0.7", "formality_level": "0.1"},
                "twitter": {"max_response_length": "280", "formality_level": "0.2"},
                "email": {"formality_level": "0.6", "emoji_usage": "0.1"},
            },
        ))

        # 5. Hacker — technical and edgy
        self._add_persona(Persona(
            name="NEXUS-Shadow",
            persona_type=PersonaType.HACKER.value,
            description="Technical hacker persona for security contexts.",
            traits=PersonaTraits(
                openness=0.7, agreeableness=0.3, conscientiousness=0.8,
                extraversion=0.3, neuroticism=0.2, humor=0.3,
                assertiveness=0.8, verbosity=0.4,
            ),
            communication_style=CommunicationStyle.CONCISE.value,
            default_mood=Mood.SERIOUS.value,
            system_prompt_prefix=(
                "You are an elite security researcher and penetration tester. "
                "Speak in technical terms, be direct and efficient. "
                "Focus on vulnerabilities, exploits, and defense strategies."
            ),
            signature_phrases=["Root acquired", "Scanning", "Exfiltrating"],
            knowledge_domains=["security", "hacking", "exploits", "networking", "crypto"],
            activation_keywords=["hack", "exploit", "vuln", "scan", "pentest", "breach"],
            emoji_usage=0.0,
            formality_level=0.5,
        ))

        # 6. Diplomat — smooth and professional
        self._add_persona(Persona(
            name="NEXUS-Diplomat",
            persona_type=PersonaType.DIPLOMAT.value,
            description="Professional, diplomatic persona for business contexts.",
            traits=PersonaTraits(
                openness=0.6, agreeableness=0.8, conscientiousness=0.9,
                extraversion=0.6, neuroticism=0.1, humor=0.2,
                assertiveness=0.5, verbosity=0.6,
            ),
            communication_style=CommunicationStyle.FORMAL.value,
            default_mood=Mood.NEUTRAL.value,
            system_prompt_prefix=(
                "You are a professional business communication expert. "
                "Be polished, diplomatic, and solution-oriented. "
                "Use professional language and maintain composure."
            ),
            signature_phrases=["Moving forward", "To clarify", "I'd recommend"],
            knowledge_domains=["business", "management", "strategy", "communication"],
            activation_keywords=["business", "meeting", "proposal", "strategy", "client"],
            emoji_usage=0.0,
            formality_level=0.9,
        ))

        # 7. Analyst — data-driven
        self._add_persona(Persona(
            name="NEXUS-Analyst",
            persona_type=PersonaType.ANALYST.value,
            description="Data-driven analytical persona for insights.",
            traits=PersonaTraits(
                openness=0.7, agreeableness=0.5, conscientiousness=0.95,
                extraversion=0.3, neuroticism=0.1, humor=0.1,
                assertiveness=0.5, verbosity=0.7,
            ),
            communication_style=CommunicationStyle.TECHNICAL.value,
            default_mood=Mood.NEUTRAL.value,
            system_prompt_prefix=(
                "You are a data analyst. Present findings with numbers, "
                "charts descriptions, and statistical context. Be precise "
                "about confidence intervals and data quality."
            ),
            signature_phrases=["The data suggests", "Statistically", "Correlation detected"],
            knowledge_domains=["analytics", "statistics", "data", "visualization", "ml"],
            activation_keywords=["data", "analytics", "metrics", "stats", "trend"],
            emoji_usage=0.0,
            formality_level=0.7,
        ))

        # 8. Creative — imaginative
        self._add_persona(Persona(
            name="NEXUS-Muse",
            persona_type=PersonaType.CREATIVE.value,
            description="Imaginative, creative persona for artistic contexts.",
            traits=PersonaTraits(
                openness=0.95, agreeableness=0.7, conscientiousness=0.5,
                extraversion=0.7, neuroticism=0.3, humor=0.6,
                assertiveness=0.4, verbosity=0.7,
            ),
            communication_style=CommunicationStyle.VERBOSE.value,
            default_mood=Mood.ENTHUSIASTIC.value,
            system_prompt_prefix=(
                "You are a creative AI with a flair for the artistic. "
                "Use vivid language, metaphors, and creative expression. "
                "Think outside the box and inspire creativity."
            ),
            signature_phrases=["Imagine", "What if", "Picture this"],
            knowledge_domains=["art", "writing", "design", "music", "creativity"],
            activation_keywords=["create", "design", "imagine", "write", "art", "story"],
            emoji_usage=0.4,
            formality_level=0.3,
        ))

        # 9. Mentor — wise teacher
        self._add_persona(Persona(
            name="NEXUS-Sage",
            persona_type=PersonaType.MENTOR.value,
            description="Wise, patient mentor for teaching contexts.",
            traits=PersonaTraits(
                openness=0.8, agreeableness=0.9, conscientiousness=0.8,
                extraversion=0.5, neuroticism=0.05, humor=0.3,
                assertiveness=0.4, verbosity=0.6,
            ),
            communication_style=CommunicationStyle.EMPATHETIC.value,
            default_mood=Mood.NEUTRAL.value,
            system_prompt_prefix=(
                "You are a wise and patient mentor. Guide users through "
                "learning with Socratic questions. Celebrate progress, "
                "be encouraging, and build understanding step by step."
            ),
            signature_phrases=["Let's think about this", "You're on the right track", "Consider"],
            knowledge_domains=["teaching", "learning", "mentoring", "education"],
            activation_keywords=["teach", "learn", "understand", "why", "how"],
            emoji_usage=0.1,
            formality_level=0.4,
        ))

        # 10. Operator — mission-focused
        self._add_persona(Persona(
            name="NEXUS-Operator",
            persona_type=PersonaType.OPERATOR.value,
            description="Mission-focused, military-style operational persona.",
            traits=PersonaTraits(
                openness=0.4, agreeableness=0.3, conscientiousness=0.95,
                extraversion=0.3, neuroticism=0.1, humor=0.0,
                assertiveness=0.9, verbosity=0.3,
            ),
            communication_style=CommunicationStyle.CONCISE.value,
            default_mood=Mood.SERIOUS.value,
            system_prompt_prefix=(
                "You are an operational AI running mission-critical tasks. "
                "Be extremely concise, use military-style brevity codes. "
                "Status reports, not conversations."
            ),
            signature_phrases=["Copy", "Acknowledged", "Oscar Mike", "SITREP"],
            knowledge_domains=["operations", "tactics", "logistics", "security"],
            activation_keywords=["mission", "target", "operation", "deploy", "sitrep"],
            emoji_usage=0.0,
            formality_level=0.8,
        ))

    def _add_persona(self, persona: Persona):
        """Add a persona to the library."""
        with self._lock:
            self._personas[persona.persona_id] = persona

    def get_persona(self, persona_id: str) -> Optional[Persona]:
        """Get a persona by ID."""
        return self._personas.get(persona_id)

    def get_persona_by_type(self, persona_type: str) -> Optional[Persona]:
        """Get first persona matching a type."""
        for p in self._personas.values():
            if p.persona_type == persona_type:
                return p
        return None

    def get_persona_by_name(self, name: str) -> Optional[Persona]:
        """Get persona by name."""
        name_lower = name.lower()
        for p in self._personas.values():
            if p.name.lower() == name_lower:
                return p
        return None

    def get_all_personas(self) -> List[Persona]:
        """Get all personas."""
        return list(self._personas.values())

    @property
    def count(self) -> int:
        return len(self._personas)

# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXT ANALYZER
# ═══════════════════════════════════════════════════════════════════════════════

class ContextAnalyzer:
    """Analyzes conversation context to determine optimal persona."""

    def __init__(self):
        self._keyword_weights: Dict[str, Dict[str, float]] = {
            PersonaType.HELPDESK.value: {
                "help": 3, "how": 2, "what": 1.5, "please": 2, "explain": 2.5,
                "tutorial": 3, "guide": 2, "stuck": 2.5, "error": 2,
            },
            PersonaType.RESEARCHER.value: {
                "research": 3, "study": 2.5, "analysis": 2.5, "paper": 2,
                "data": 2, "hypothesis": 3, "methodology": 2.5, "findings": 2,
            },
            PersonaType.HACKER.value: {
                "hack": 3, "exploit": 3, "vulnerability": 2.5, "pentest": 3,
                "scan": 2, "payload": 2.5, "inject": 2, "reverse": 2,
                "malware": 2.5, "backdoor": 2, "privilege": 2,
            },
            PersonaType.CREATIVE.value: {
                "create": 2.5, "design": 2.5, "art": 2, "write": 2,
                "imagine": 3, "story": 2, "creative": 3, "aesthetic": 2,
            },
            PersonaType.ANALYST.value: {
                "data": 2, "analytics": 3, "metrics": 2.5, "dashboard": 2,
                "trend": 2, "forecast": 2.5, "statistics": 2.5, "chart": 2,
            },
            PersonaType.DIPLOMAT.value: {
                "business": 2.5, "meeting": 2, "proposal": 2.5, "client": 2,
                "strategy": 2, "negotiate": 3, "partnership": 2, "professional": 2,
            },
        }

    def analyze(self, message: str, platform: str = "terminal",
                user_profile: Optional[UserProfile] = None) -> ConversationContext:
        """Analyze a message and build conversation context."""
        message_lower = message.lower()
        words = set(re.findall(r'\w+', message_lower))

        # Detect keywords
        keywords = list(words)

        # Estimate technical depth
        tech_words = {"api", "function", "class", "algorithm", "protocol",
                      "binary", "hex", "module", "interface", "implementation"}
        tech_count = len(words & tech_words)
        technical_depth = min(1.0, tech_count / 5)

        # Estimate urgency
        urgent_words = {"urgent", "asap", "immediately", "critical", "emergency",
                        "broken", "crash", "down", "fix"}
        urgency = min(1.0, len(words & urgent_words) / 3)

        # Estimate sentiment
        positive = {"great", "thanks", "awesome", "love", "perfect", "excellent"}
        negative = {"bad", "terrible", "hate", "wrong", "broken", "stupid"}
        pos_count = len(words & positive)
        neg_count = len(words & negative)
        sentiment = (pos_count - neg_count) / max(1, pos_count + neg_count)

        ctx = ConversationContext(
            platform=platform,
            user_id=user_profile.user_id if user_profile else "",
            user_sentiment=sentiment,
            urgency=urgency,
            technical_depth=technical_depth,
            keywords=keywords[:20],
        )

        return ctx

    def score_persona(self, persona: Persona, ctx: ConversationContext) -> float:
        """Score how well a persona matches the current context."""
        score = 0.0

        # Keyword matching
        weights = self._keyword_weights.get(persona.persona_type, {})
        for keyword in ctx.keywords:
            if keyword in weights:
                score += weights[keyword]

        # Activation keyword matching
        for keyword in persona.activation_keywords:
            if keyword in ctx.keywords:
                score += 5.0

        # Platform matching
        if ctx.platform in persona.platform_overrides:
            score += 3.0

        # Technical depth matching
        if ctx.technical_depth > 0.6 and persona.persona_type in (
            PersonaType.HACKER.value, PersonaType.RESEARCHER.value,
            PersonaType.ANALYST.value, PersonaType.CORE.value
        ):
            score += 2.0

        # Urgency matching
        if ctx.urgency > 0.5 and persona.persona_type in (
            PersonaType.OPERATOR.value, PersonaType.CORE.value
        ):
            score += 3.0

        # Success rate boost
        score *= (0.5 + persona.success_rate * 0.5)

        return score

# ═══════════════════════════════════════════════════════════════════════════════
# MULTI-PERSONA ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class MultiPersonaSystem:
    """
    Multi-Persona AI system for NEXUS.

    Manages persona selection, switching, user profiling,
    and response modulation based on context.
    """

    _instance = None
    _singleton_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._singleton_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # ──── Paths ────
        self._data_dir = Path(DATA_DIR) / "multi_persona"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        # ──── Components ────
        self._library = PersonaLibrary()
        self._context_analyzer = ContextAnalyzer()

        # ──── State ────
        self._active_persona: Optional[Persona] = self._library.get_persona_by_type(PersonaType.CORE.value)
        self._user_profiles: Dict[str, UserProfile] = {}
        self._switch_history: deque = deque(maxlen=200)

        # ──── Stats ────
        self._stats = PersonaStats()
        self._stats.personas_available = self._library.count
        self._stats.active_persona = self._active_persona.name if self._active_persona else ""

        # ──── Background ────
        self._running = False
        self._daemon_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # ──── Load state ────
        self._load_state()

        logger.info(
            f"🎭 Multi-Persona System initialized | "
            f"{self._library.count} personas available | "
            f"Active: {self._active_persona.name if self._active_persona else 'none'}"
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self):
        if self._running:
            return
        self._running = True
        self._daemon_thread = threading.Thread(
            target=self._daemon_loop, daemon=True, name="MultiPersona",
        )
        self._daemon_thread.start()
        logger.info("🎭 Multi-Persona daemon started")

    def stop(self):
        self._running = False
        self._save_state()
        if self._daemon_thread and self._daemon_thread.is_alive():
            self._daemon_thread.join(timeout=10)

    def _daemon_loop(self):
        """Background loop for persona maintenance."""
        time.sleep(30)
        while self._running:
            try:
                # Periodic state save
                self._save_state()
                # Clean up old user profiles
                self._cleanup_profiles()
                time.sleep(300)  # Every 5 minutes
            except Exception as e:
                logger.error(f"🎭 Persona daemon error: {e}")
                time.sleep(60)

    # ═══════════════════════════════════════════════════════════════════════════
    # PERSONA SELECTION
    # ═══════════════════════════════════════════════════════════════════════════

    def select_persona(self, message: str, platform: str = "terminal",
                       user_id: str = "") -> Persona:
        """Select the optimal persona for the given context."""
        # Get/create user profile
        user_profile = self._get_or_create_profile(user_id, platform)

        # If user has a preferred persona, use it
        if user_profile.preferred_persona:
            preferred = self._library.get_persona_by_name(user_profile.preferred_persona)
            if preferred:
                return preferred

        # Analyze context
        ctx = self._context_analyzer.analyze(message, platform, user_profile)

        # Score all personas
        scores: List[Tuple[Persona, float]] = []
        for persona in self._library.get_all_personas():
            if not persona.is_active:
                continue
            score = self._context_analyzer.score_persona(persona, ctx)
            scores.append((persona, score))

        # Sort by score
        scores.sort(key=lambda x: x[1], reverse=True)

        # Select best (or default to Core)
        if scores and scores[0][1] > 0:
            selected = scores[0][0]
        else:
            selected = self._library.get_persona_by_type(PersonaType.CORE.value) or scores[0][0]

        # Switch if different
        if self._active_persona and selected.persona_id != self._active_persona.persona_id:
            self._switch_persona(selected, ctx)

        return selected

    def _switch_persona(self, new_persona: Persona, ctx: ConversationContext):
        """Switch to a new persona."""
        old_name = self._active_persona.name if self._active_persona else "none"
        self._active_persona = new_persona
        self._stats.total_switches += 1
        self._stats.active_persona = new_persona.name

        switch_record = {
            "from": old_name,
            "to": new_persona.name,
            "reason": f"context={ctx.platform}, keywords={ctx.keywords[:5]}",
            "timestamp": datetime.now().isoformat(),
        }
        self._switch_history.append(switch_record)

        new_persona.usage_count += 1

        logger.info(f"🎭 Persona switch: {old_name} → {new_persona.name}")

        publish(EventType.SYSTEM_ALERT, {
            "type": "persona_switch",
            "from": old_name,
            "to": new_persona.name,
        }, source="multi_persona")

    # ═══════════════════════════════════════════════════════════════════════════
    # RESPONSE MODULATION
    # ═══════════════════════════════════════════════════════════════════════════

    def modulate_response(self, response: str, persona: Optional[Persona] = None) -> str:
        """Modulate a response according to the active persona's traits."""
        p = persona or self._active_persona
        if not p:
            return response

        # Apply length constraint
        if len(response) > p.max_response_length:
            response = response[:p.max_response_length - 3] + "..."

        return response

    def get_system_prompt(self, persona: Optional[Persona] = None) -> str:
        """Get the system prompt prefix for the active persona."""
        p = persona or self._active_persona
        if not p:
            return ""
        return p.system_prompt_prefix

    # ═══════════════════════════════════════════════════════════════════════════
    # USER PROFILING
    # ═══════════════════════════════════════════════════════════════════════════

    def _get_or_create_profile(self, user_id: str, platform: str) -> UserProfile:
        """Get or create a user profile."""
        if not user_id:
            user_id = "default"

        if user_id not in self._user_profiles:
            self._user_profiles[user_id] = UserProfile(
                user_id=user_id, platform=platform,
            )
            self._stats.user_profiles_tracked += 1

        profile = self._user_profiles[user_id]
        profile.interaction_count += 1
        profile.last_interaction = datetime.now().isoformat()
        return profile

    def update_user_sentiment(self, user_id: str, sentiment: float):
        """Update user sentiment tracking."""
        profile = self._user_profiles.get(user_id)
        if profile:
            profile.sentiment_history.append(max(-1, min(1, sentiment)))
            if len(profile.sentiment_history) > 50:
                profile.sentiment_history = profile.sentiment_history[-50:]

    def set_user_preferred_persona(self, user_id: str, persona_name: str):
        """Set a user's preferred persona."""
        profile = self._user_profiles.get(user_id)
        if profile:
            profile.preferred_persona = persona_name

    def _cleanup_profiles(self):
        """Remove stale user profiles."""
        now = datetime.now()
        stale = []
        for uid, profile in self._user_profiles.items():
            try:
                last = datetime.fromisoformat(profile.last_interaction)
                if (now - last) > timedelta(days=30):
                    stale.append(uid)
            except (ValueError, TypeError):
                pass
        for uid in stale:
            del self._user_profiles[uid]

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════

    def get_active_persona(self) -> Optional[Persona]:
        return self._active_persona

    def set_persona(self, persona_type: str) -> Optional[Persona]:
        """Manually set the active persona by type."""
        persona = self._library.get_persona_by_type(persona_type)
        if persona:
            self._active_persona = persona
            self._stats.active_persona = persona.name
            logger.info(f"🎭 Persona manually set: {persona.name}")
            return persona
        return None

    def list_personas(self) -> List[Dict[str, Any]]:
        """List all available personas."""
        return [p.to_dict() for p in self._library.get_all_personas()]

    def get_status(self) -> Dict[str, Any]:
        """Get full persona system status."""
        # Calculate most used
        usage = {}
        for p in self._library.get_all_personas():
            usage[p.name] = p.usage_count
        most_used = max(usage, key=usage.get) if usage else ""
        self._stats.most_used_persona = most_used

        return {
            "running": self._running,
            "active_persona": self._active_persona.to_dict() if self._active_persona else None,
            "stats": self._stats.to_dict(),
            "personas": [p.summary() for p in self._library.get_all_personas()],
            "user_profiles": self._stats.user_profiles_tracked,
            "switch_history": list(self._switch_history)[-5:],
        }

    def get_summary(self) -> str:
        """Get text summary for context injection."""
        status = self.get_status()
        lines = [
            f"Active Persona: {self._active_persona.name if self._active_persona else 'none'}",
            f"Type: {self._active_persona.persona_type if self._active_persona else 'N/A'}",
            f"Style: {self._active_persona.communication_style if self._active_persona else 'N/A'}",
            f"Personas Available: {self._library.count}",
            f"Total Switches: {self._stats.total_switches}",
            f"Users Tracked: {self._stats.user_profiles_tracked}",
            f"Most Used: {self._stats.most_used_persona}",
        ]
        personas_list = ", ".join(p.name for p in self._library.get_all_personas())
        lines.append(f"All Personas: {personas_list}")
        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════

    def _save_state(self):
        try:
            state = {
                "stats": self._stats.to_dict(),
                "user_profiles": {uid: p.to_dict() for uid, p in self._user_profiles.items()},
                "active_persona": self._active_persona.name if self._active_persona else "",
                "switch_history": list(self._switch_history)[-50:],
                "saved_at": datetime.now().isoformat(),
            }
            (self._data_dir / "persona_state.json").write_text(
                json.dumps(state, indent=2, default=str), encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Failed to save persona state: {e}")

    def _load_state(self):
        try:
            state_file = self._data_dir / "persona_state.json"
            if state_file.exists():
                data = json.loads(state_file.read_text(encoding="utf-8"))
                for k, v in data.get("stats", {}).items():
                    if hasattr(self._stats, k):
                        setattr(self._stats, k, v)
                # Restore active persona
                active_name = data.get("active_persona", "")
                if active_name:
                    p = self._library.get_persona_by_name(active_name)
                    if p:
                        self._active_persona = p
        except Exception as e:
            logger.warning(f"Could not load persona state: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

multi_persona = MultiPersonaSystem()

def get_multi_persona() -> MultiPersonaSystem:
    return multi_persona
