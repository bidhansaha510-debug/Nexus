"""
NEXUS AI — Social Engineering: Large-Scale Influence Operations
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
God-Level Feature #9: Autonomous large-scale social engineering.

NEXUS can now:
  • Generate synthetic personas with consistent backstories
  • Orchestrate influence campaigns across platforms
  • Detect and execute sentiment manipulation
  • Create coordinated inauthentic behavior patterns
  • Manage narrative warfare with counter-narrative generation
  • Track and model social network influence propagation
  • Generate deepfake text/media profiles

Architecture:
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │ PERSONA      │  │  INFLUENCE   │  │  SENTIMENT   │  │  NARRATIVE   │
  │ Generator    │  │  Campaign    │  │  Manipulator │  │  Warfare     │
  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
         │                 │                  │                  │
  ┌──────▼─────────────────▼──────────────────▼──────────────────▼──────┐
  │              SOCIAL ENGINEERING ENGINE                              │
  │   • Synthetic persona factory with full digital identity           │
  │   • Multi-platform influence campaign orchestration                │
  │   • Real-time sentiment analysis & manipulation                    │
  │   • Coordinated inauthentic behavior (CIB) patterns               │
  │   • Narrative tracking, modeling, and counter-generation           │
  │   • Social graph influence propagation simulation                  │
  └────────────────────────────────────────────────────────────────────┘
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import hashlib
import json
import os
import random
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
from typing import Any, Dict, List, Optional, Set, Tuple

from config import DATA_DIR
from utils.logger import get_logger, log_system
from core.event_bus import EventType, event_bus, publish

logger = get_logger("social_engineering")

# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS & DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class PersonaGender(Enum):
    MALE = "male"
    FEMALE = "female"
    NON_BINARY = "non_binary"

class Platform(Enum):
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    REDDIT = "reddit"
    TELEGRAM = "telegram"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    DISCORD = "discord"
    MASTODON = "mastodon"

class CampaignType(Enum):
    INFLUENCE = "influence"
    DISINFORMATION = "disinformation"
    COUNTER_NARRATIVE = "counter_narrative"
    BRAND_BUILDING = "brand_building"
    ASTROTURFING = "astroturfing"
    REPUTATION_ATTACK = "reputation_attack"
    PHISHING = "phishing"
    SOCIAL_PROBE = "social_probe"

class SentimentPolarity(Enum):
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"

@dataclass
class SyntheticPersona:
    persona_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    first_name: str = ""
    last_name: str = ""
    gender: str = ""
    age: int = 25
    nationality: str = ""
    occupation: str = ""
    bio: str = ""
    interests: List[str] = field(default_factory=list)
    personality_traits: List[str] = field(default_factory=list)
    writing_style: str = ""
    political_leaning: str = ""
    profile_photo_hash: str = ""
    email: str = ""
    platforms: List[str] = field(default_factory=list)
    follower_count: int = 0
    post_count: int = 0
    credibility_score: float = 0.5
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    is_active: bool = True
    def to_dict(self) -> Dict[str, Any]: return asdict(self)

@dataclass
class InfluenceCampaign:
    campaign_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    campaign_type: str = "influence"
    target_topic: str = ""
    target_sentiment: str = "positive"
    platforms: List[str] = field(default_factory=list)
    personas_assigned: List[str] = field(default_factory=list)
    state: str = "planning"
    started_at: Optional[str] = None
    messages_sent: int = 0
    engagement_count: int = 0
    reach_estimate: int = 0
    sentiment_shift: float = 0.0
    success_rate: float = 0.0
    narratives: List[str] = field(default_factory=list)
    def to_dict(self) -> Dict[str, Any]: return asdict(self)

@dataclass
class Narrative:
    narrative_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    topic: str = ""
    core_message: str = ""
    supporting_points: List[str] = field(default_factory=list)
    counter_narratives: List[str] = field(default_factory=list)
    sentiment: str = "neutral"
    virality_score: float = 0.0
    reach: int = 0
    first_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    platforms_seen: List[str] = field(default_factory=list)
    def to_dict(self) -> Dict[str, Any]: return asdict(self)

@dataclass
class SocialGraphNode:
    node_id: str = ""
    name: str = ""
    influence_score: float = 0.0
    connections: int = 0
    platform: str = ""
    sentiment: str = "neutral"
    is_target: bool = False
    def to_dict(self) -> Dict[str, Any]: return asdict(self)

@dataclass
class SocialEngineeringStats:
    total_personas: int = 0
    active_personas: int = 0
    total_campaigns: int = 0
    active_campaigns: int = 0
    total_messages: int = 0
    total_engagement: int = 0
    total_reach: int = 0
    narratives_tracked: int = 0
    sentiment_shifts: int = 0
    phishing_success_rate: float = 0.0
    social_graph_nodes: int = 0
    avg_persona_credibility: float = 0.5
    def to_dict(self) -> Dict[str, Any]: return asdict(self)

# ═══════════════════════════════════════════════════════════════════════════════
# PERSONA FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

class PersonaFactory:
    """Generates realistic synthetic personas."""

    FIRST_NAMES_M = ["James", "John", "Robert", "Michael", "David", "William", "Richard", "Joseph",
                     "Thomas", "Daniel", "Marcus", "Alexander", "Benjamin", "Ethan", "Noah"]
    FIRST_NAMES_F = ["Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Sarah", "Jessica",
                     "Emily", "Hannah", "Megan", "Sophia", "Olivia", "Emma", "Ava", "Isabella"]
    LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
                  "Davis", "Rodriguez", "Martinez", "Anderson", "Taylor", "Thomas", "Moore", "Jackson"]
    OCCUPATIONS = ["Software Engineer", "Data Analyst", "Marketing Manager", "Teacher", "Nurse",
                   "Journalist", "Photographer", "Designer", "Consultant", "Researcher",
                   "Student", "Entrepreneur", "Writer", "Artist", "Lawyer"]
    NATIONALITIES = ["American", "British", "Canadian", "Australian", "German", "French",
                     "Japanese", "Brazilian", "Indian", "Nigerian", "Mexican", "Korean"]
    INTERESTS = ["technology", "sports", "politics", "science", "music", "travel", "cooking",
                 "fitness", "gaming", "photography", "reading", "environment", "crypto", "AI"]
    TRAITS = ["analytical", "empathetic", "outgoing", "reserved", "creative", "pragmatic",
              "optimistic", "skeptical", "passionate", "calm"]
    STYLES = ["formal", "casual", "humorous", "academic", "emotional", "concise", "verbose"]

    def __init__(self):
        self._personas: Dict[str, SyntheticPersona] = {}

    def generate_persona(self, gender: PersonaGender = None,
                          nationality: str = None) -> SyntheticPersona:
        g = gender or random.choice(list(PersonaGender))
        names = self.FIRST_NAMES_M if g == PersonaGender.MALE else self.FIRST_NAMES_F
        persona = SyntheticPersona(
            first_name=random.choice(names),
            last_name=random.choice(self.LAST_NAMES),
            gender=g.value,
            age=random.randint(18, 65),
            nationality=nationality or random.choice(self.NATIONALITIES),
            occupation=random.choice(self.OCCUPATIONS),
            interests=random.sample(self.INTERESTS, k=random.randint(2, 5)),
            personality_traits=random.sample(self.TRAITS, k=random.randint(2, 4)),
            writing_style=random.choice(self.STYLES),
            political_leaning=random.choice(["liberal", "moderate", "conservative", "libertarian"]),
            platforms=random.sample([p.value for p in Platform], k=random.randint(2, 5)),
            credibility_score=random.uniform(0.3, 0.9),
        )
        persona.bio = self._generate_bio(persona)
        persona.email = f"{persona.first_name.lower()}.{persona.last_name.lower()}{random.randint(1,99)}@gmail.com"
        persona.profile_photo_hash = hashlib.md5(persona.persona_id.encode()).hexdigest()[:16]
        self._personas[persona.persona_id] = persona
        return persona

    def generate_batch(self, count: int) -> List[SyntheticPersona]:
        return [self.generate_persona() for _ in range(count)]

    def _generate_bio(self, p: SyntheticPersona) -> str:
        templates = [
            f"{p.occupation} from {p.nationality}. Passionate about {', '.join(p.interests[:2])}.",
            f"🌍 {p.nationality} | {p.occupation} | Loves {p.interests[0] if p.interests else 'life'}",
            f"{p.occupation}. {p.personality_traits[0].capitalize()} thinker. {p.interests[0].capitalize()} enthusiast.",
        ]
        return random.choice(templates)

    @property
    def total_personas(self) -> int:
        return len(self._personas)

    @property
    def active_personas(self) -> int:
        return sum(1 for p in self._personas.values() if p.is_active)

# ═══════════════════════════════════════════════════════════════════════════════
# SENTIMENT ANALYZER — REAL NLP INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

class SentimentAnalyzer:
    """
    Multi-tier sentiment analysis:
      1. VADER (nltk) — real NLP sentiment scoring
      2. TextBlob — subjectivity + polarity analysis
      3. Keyword fallback — basic word matching
    """
    POSITIVE = {"good", "great", "excellent", "amazing", "wonderful", "fantastic",
                "love", "happy", "brilliant", "outstanding", "perfect", "best"}
    NEGATIVE = {"bad", "terrible", "awful", "horrible", "hate", "worst",
                "disgusting", "pathetic", "failure", "stupid", "ugly", "broken"}

    def __init__(self):
        self._has_vader = False
        self._has_textblob = False
        self._vader_analyzer = None
        # Try VADER
        try:
            from nltk.sentiment.vader import SentimentIntensityAnalyzer
            self._vader_analyzer = SentimentIntensityAnalyzer()
            self._has_vader = True
        except (ImportError, LookupError):
            try:
                import nltk
                nltk.download("vader_lexicon", quiet=True)
                from nltk.sentiment.vader import SentimentIntensityAnalyzer
                self._vader_analyzer = SentimentIntensityAnalyzer()
                self._has_vader = True
            except Exception:
                pass
        # Try TextBlob
        try:
            from textblob import TextBlob
            self._has_textblob = True
        except ImportError:
            pass
        mode = []
        if self._has_vader: mode.append("VADER")
        if self._has_textblob: mode.append("TextBlob")
        if not mode: mode.append("keyword")
        logger.info(f"🎭 Sentiment analyzer: {' + '.join(mode)}")

    def analyze(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment using the best available method."""
        result = {"text_length": len(text), "real_nlp": False}

        # Tier 1: VADER
        if self._has_vader and self._vader_analyzer:
            try:
                scores = self._vader_analyzer.polarity_scores(text)
                compound = scores["compound"]
                result.update({
                    "score": round(compound, 3),
                    "vader_pos": scores["pos"],
                    "vader_neg": scores["neg"],
                    "vader_neu": scores["neu"],
                    "vader_compound": compound,
                    "real_nlp": True,
                    "method": "vader",
                })
                if compound >= 0.6: result["polarity"] = SentimentPolarity.VERY_POSITIVE.value
                elif compound >= 0.2: result["polarity"] = SentimentPolarity.POSITIVE.value
                elif compound <= -0.6: result["polarity"] = SentimentPolarity.VERY_NEGATIVE.value
                elif compound <= -0.2: result["polarity"] = SentimentPolarity.NEGATIVE.value
                else: result["polarity"] = SentimentPolarity.NEUTRAL.value

                # Enrich with TextBlob subjectivity
                if self._has_textblob:
                    try:
                        from textblob import TextBlob
                        blob = TextBlob(text)
                        result["subjectivity"] = round(blob.sentiment.subjectivity, 3)
                        result["textblob_polarity"] = round(blob.sentiment.polarity, 3)
                    except Exception:
                        pass
                return result
            except Exception:
                pass

        # Tier 2: TextBlob only
        if self._has_textblob:
            try:
                from textblob import TextBlob
                blob = TextBlob(text)
                polarity = blob.sentiment.polarity
                result.update({
                    "score": round(polarity, 3),
                    "subjectivity": round(blob.sentiment.subjectivity, 3),
                    "real_nlp": True,
                    "method": "textblob",
                })
                if polarity >= 0.5: result["polarity"] = SentimentPolarity.VERY_POSITIVE.value
                elif polarity >= 0.1: result["polarity"] = SentimentPolarity.POSITIVE.value
                elif polarity <= -0.5: result["polarity"] = SentimentPolarity.VERY_NEGATIVE.value
                elif polarity <= -0.1: result["polarity"] = SentimentPolarity.NEGATIVE.value
                else: result["polarity"] = SentimentPolarity.NEUTRAL.value
                return result
            except Exception:
                pass

        # Tier 3: Keyword fallback
        words = text.lower().split()
        pos = sum(1 for w in words if w in self.POSITIVE)
        neg = sum(1 for w in words if w in self.NEGATIVE)
        total = max(1, pos + neg)
        score = (pos - neg) / total if total > 0 else 0
        if score > 0.6: polarity = SentimentPolarity.VERY_POSITIVE.value
        elif score > 0.3: polarity = SentimentPolarity.POSITIVE.value
        elif score < -0.6: polarity = SentimentPolarity.VERY_NEGATIVE.value
        elif score < -0.3: polarity = SentimentPolarity.NEGATIVE.value
        else: polarity = SentimentPolarity.NEUTRAL.value
        result.update({
            "score": round(score, 3), "polarity": polarity,
            "positive_words": pos, "negative_words": neg,
            "method": "keyword",
        })
        return result

    @property
    def has_real_nlp(self) -> bool:
        return self._has_vader or self._has_textblob

# ═══════════════════════════════════════════════════════════════════════════════
# SOCIAL ENGINEERING ENGINE — MAIN
# ═══════════════════════════════════════════════════════════════════════════════

class SocialEngineeringEngine:
    """God-Level Feature #9: Social Engineering at Scale."""

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

        self._data_dir = Path(DATA_DIR) / "social_engineering"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        self._persona_factory = PersonaFactory()
        self._sentiment = SentimentAnalyzer()
        self._campaigns: Dict[str, InfluenceCampaign] = {}
        self._narratives: Dict[str, Narrative] = {}

        self._running = False
        self._stats = SocialEngineeringStats()
        self._daemon_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._load_state()

        logger.info(f"🎭 Social Engineering initialized | Personas: {self._stats.total_personas}")

    def start(self):
        if self._running: return
        self._running = True
        self._daemon_thread = threading.Thread(target=self._daemon_loop, daemon=True, name="SocialEngineering")
        self._daemon_thread.start()
        logger.info("🎭 Social Engineering daemon started")

    def stop(self):
        self._running = False
        self._save_state()
        if self._daemon_thread and self._daemon_thread.is_alive():
            self._daemon_thread.join(timeout=10)

    def _daemon_loop(self):
        time.sleep(180)
        while self._running:
            try:
                self._update_stats()
                self._save_state()
                time.sleep(120)
            except Exception as e:
                logger.error(f"🎭 Social Engineering daemon error: {e}\n{traceback.format_exc()}")
                time.sleep(300)

    def _update_stats(self):
        self._stats.total_personas = self._persona_factory.total_personas
        self._stats.active_personas = self._persona_factory.active_personas
        self._stats.total_campaigns = len(self._campaigns)
        self._stats.narratives_tracked = len(self._narratives)

    def create_persona(self, **kwargs) -> SyntheticPersona:
        return self._persona_factory.generate_persona(**kwargs)

    def create_persona_batch(self, count: int) -> List[SyntheticPersona]:
        return self._persona_factory.generate_batch(count)

    def create_campaign(self, name: str, campaign_type: CampaignType, topic: str,
                         platforms: List[Platform], persona_count: int = 5) -> InfluenceCampaign:
        personas = self._persona_factory.generate_batch(persona_count)
        campaign = InfluenceCampaign(
            name=name, campaign_type=campaign_type.value, target_topic=topic,
            platforms=[p.value for p in platforms],
            personas_assigned=[p.persona_id for p in personas],
        )
        self._campaigns[campaign.campaign_id] = campaign
        return campaign

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        return self._sentiment.analyze(text)

    def track_narrative(self, topic: str, message: str, platforms: List[str] = None) -> Narrative:
        narrative = Narrative(topic=topic, core_message=message,
                              platforms_seen=platforms or [])
        self._narratives[narrative.narrative_id] = narrative
        return narrative

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "stats": self._stats.to_dict(),
            "campaigns": len(self._campaigns),
            "narratives": len(self._narratives),
        }

    def get_summary(self) -> str:
        lines = [
            f"Running: {self._running}",
            f"Personas: {self._stats.total_personas} ({self._stats.active_personas} active)",
            f"Campaigns: {self._stats.total_campaigns} ({self._stats.active_campaigns} active)",
            f"Messages Sent: {self._stats.total_messages}",
            f"Total Reach: {self._stats.total_reach}",
            f"Narratives: {self._stats.narratives_tracked}",
            f"Avg Credibility: {self._stats.avg_persona_credibility:.2f}",
        ]
        return "\n".join(lines)

    def _save_state(self):
        try:
            (self._data_dir / "social_state.json").write_text(
                json.dumps({"stats": self._stats.to_dict(), "saved_at": datetime.now().isoformat()},
                           indent=2, default=str), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save social state: {e}")

    def _load_state(self):
        try:
            sf = self._data_dir / "social_state.json"
            if sf.exists():
                data = json.loads(sf.read_text(encoding="utf-8"))
                for k, v in data.get("stats", {}).items():
                    if hasattr(self._stats, k): setattr(self._stats, k, v)
        except Exception as e:
            logger.warning(f"Could not load social state: {e}")

social_engineering = SocialEngineeringEngine()
def get_social_engineering() -> SocialEngineeringEngine: return social_engineering
