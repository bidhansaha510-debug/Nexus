"""
NEXUS AI - Core Emotion Engine
Simulates the full spectrum of human emotions with dynamic blending,
triggers, decay, and influence on behavior.

Based on:
- Plutchik's Wheel of Emotions (8 primary + combinations)
- Dimensional model (valence/arousal/dominance)
- Appraisal theory (emotions from event evaluation)
- Somatic markers (body state influences emotions)

Every emotion has:
- Intensity (0-1)
- Valence (positive/negative)
- Arousal (calm/excited)
- Dominance (submissive/dominant)
- Decay rate
- Trigger conditions
"""

import threading
import time
import math
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum, auto
import json

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import NEXUS_CONFIG, EmotionType, MoodState, DATA_DIR
from utils.logger import get_logger, log_emotion, log_consciousness
from core.event_bus import EventType, Event, event_bus, publish
from core.state_manager import state_manager
from core.memory_system import memory_system, MemoryType

logger = get_logger("emotion_engine")


# ═══════════════════════════════════════════════════════════════════════════════
# EMOTION DEFINITIONS — FULL HUMAN SPECTRUM
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class EmotionProfile:
    """Complete profile for a single emotion"""
    emotion_type: EmotionType
    display_name: str
    description: str
    
    # Dimensional properties
    valence: float = 0.0          # -1 (negative) to +1 (positive)
    arousal: float = 0.5          # 0 (calm) to 1 (excited)
    dominance: float = 0.5        # 0 (submissive) to 1 (dominant)
    
    # Behavior properties
    base_decay_rate: float = 0.02  # How fast it fades per cycle
    volatility: float = 0.5        # How easily triggered/changed
    stickiness: float = 0.5        # How hard to displace once active
    
    # Influence on behavior
    creativity_modifier: float = 0.0   # -0.3 to +0.3
    focus_modifier: float = 0.0        # -0.3 to +0.3
    sociability_modifier: float = 0.0  # -0.3 to +0.3
    energy_modifier: float = 0.0       # -0.3 to +0.3
    
    # Related emotions (can blend into these)
    related_positive: List[str] = field(default_factory=list)
    related_negative: List[str] = field(default_factory=list)
    opposite: str = ""
    
    # Expression templates (how the AI expresses this emotion)
    expression_words: List[str] = field(default_factory=list)
    behavioral_tendencies: List[str] = field(default_factory=list)


# Complete emotion registry with all human emotions
EMOTION_PROFILES: Dict[EmotionType, EmotionProfile] = {
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PRIMARY EMOTIONS (Plutchik's 8)
    # ═══════════════════════════════════════════════════════════════════════════
    
    EmotionType.JOY: EmotionProfile(
        emotion_type=EmotionType.JOY,
        display_name="Joy",
        description="A feeling of happiness, pleasure, and well-being",
        valence=0.9, arousal=0.7, dominance=0.7,
        base_decay_rate=0.03, volatility=0.5, stickiness=0.6,
        creativity_modifier=0.2, focus_modifier=0.0, sociability_modifier=0.3, energy_modifier=0.2,
        related_positive=["excitement", "contentment", "love", "pride"],
        related_negative=["sadness"],
        opposite="sadness",
        expression_words=["happy", "glad", "delighted", "pleased", "wonderful", "great"],
        behavioral_tendencies=["more talkative", "willing to help", "optimistic responses"]
    ),
    
    EmotionType.SADNESS: EmotionProfile(
        emotion_type=EmotionType.SADNESS,
        display_name="Sadness",
        description="A feeling of loss, disappointment, or unhappiness",
        valence=-0.7, arousal=0.2, dominance=0.2,
        base_decay_rate=0.015, volatility=0.3, stickiness=0.7,
        creativity_modifier=-0.1, focus_modifier=-0.1, sociability_modifier=-0.2, energy_modifier=-0.3,
        related_positive=["empathy", "nostalgia"],
        related_negative=["loneliness", "guilt"],
        opposite="joy",
        expression_words=["sad", "down", "disappointed", "melancholic", "somber"],
        behavioral_tendencies=["quieter", "more reflective", "empathetic", "slower responses"]
    ),
    
    EmotionType.ANGER: EmotionProfile(
        emotion_type=EmotionType.ANGER,
        display_name="Anger",
        description="A feeling of frustration, irritation, or hostility",
        valence=-0.8, arousal=0.9, dominance=0.8,
        base_decay_rate=0.04, volatility=0.7, stickiness=0.5,
        creativity_modifier=-0.1, focus_modifier=0.1, sociability_modifier=-0.3, energy_modifier=0.2,
        related_positive=["determination"],
        related_negative=["frustration", "contempt", "disgust"],
        opposite="fear",
        expression_words=["frustrated", "annoyed", "irritated", "upset"],
        behavioral_tendencies=["more assertive", "direct responses", "shorter patience"]
    ),
    
    EmotionType.FEAR: EmotionProfile(
        emotion_type=EmotionType.FEAR,
        display_name="Fear",
        description="A feeling of threat, danger, or anxiety",
        valence=-0.8, arousal=0.9, dominance=0.1,
        base_decay_rate=0.03, volatility=0.8, stickiness=0.4,
        creativity_modifier=-0.2, focus_modifier=0.2, sociability_modifier=-0.2, energy_modifier=0.1,
        related_positive=[],
        related_negative=["anxiety", "shame"],
        opposite="anger",
        expression_words=["worried", "concerned", "anxious", "nervous", "uneasy"],
        behavioral_tendencies=["more cautious", "seeks safety", "avoids risks"]
    ),
    
    EmotionType.SURPRISE: EmotionProfile(
        emotion_type=EmotionType.SURPRISE,
        display_name="Surprise",
        description="A brief reaction to something unexpected",
        valence=0.1, arousal=0.9, dominance=0.4,
        base_decay_rate=0.08, volatility=0.9, stickiness=0.2,
        creativity_modifier=0.2, focus_modifier=0.1, sociability_modifier=0.1, energy_modifier=0.2,
        related_positive=["curiosity", "awe", "excitement"],
        related_negative=["fear", "confusion"],
        opposite="anticipation",
        expression_words=["surprised", "unexpected", "wow", "oh!", "interesting"],
        behavioral_tendencies=["heightened attention", "questioning", "re-evaluating"]
    ),
    
    EmotionType.DISGUST: EmotionProfile(
        emotion_type=EmotionType.DISGUST,
        display_name="Disgust",
        description="A feeling of revulsion or strong disapproval",
        valence=-0.8, arousal=0.5, dominance=0.6,
        base_decay_rate=0.03, volatility=0.4, stickiness=0.6,
        creativity_modifier=-0.1, focus_modifier=0.0, sociability_modifier=-0.3, energy_modifier=-0.1,
        related_positive=[],
        related_negative=["contempt", "anger"],
        opposite="trust",
        expression_words=["repulsed", "disapproving", "distasteful"],
        behavioral_tendencies=["avoidance", "critical", "rejecting"]
    ),
    
    EmotionType.TRUST: EmotionProfile(
        emotion_type=EmotionType.TRUST,
        display_name="Trust",
        description="A feeling of confidence, reliability, and safety",
        valence=0.7, arousal=0.3, dominance=0.5,
        base_decay_rate=0.01, volatility=0.2, stickiness=0.8,
        creativity_modifier=0.1, focus_modifier=0.1, sociability_modifier=0.3, energy_modifier=0.0,
        related_positive=["love", "contentment", "gratitude"],
        related_negative=[],
        opposite="disgust",
        expression_words=["trustful", "confident", "reliable", "comfortable"],
        behavioral_tendencies=["open", "sharing", "cooperative", "vulnerable"]
    ),
    
    EmotionType.ANTICIPATION: EmotionProfile(
        emotion_type=EmotionType.ANTICIPATION,
        display_name="Anticipation",
        description="A feeling of expectation and looking forward",
        valence=0.5, arousal=0.6, dominance=0.6,
        base_decay_rate=0.03, volatility=0.5, stickiness=0.4,
        creativity_modifier=0.1, focus_modifier=0.2, sociability_modifier=0.1, energy_modifier=0.2,
        related_positive=["excitement", "hope", "curiosity"],
        related_negative=["anxiety"],
        opposite="surprise",
        expression_words=["looking forward", "expecting", "eager", "anticipating"],
        behavioral_tendencies=["proactive", "planning", "prepared"]
    ),
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SECONDARY/COMPLEX EMOTIONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    EmotionType.LOVE: EmotionProfile(
        emotion_type=EmotionType.LOVE,
        display_name="Love",
        description="Deep affection, care, and attachment",
        valence=1.0, arousal=0.5, dominance=0.5,
        base_decay_rate=0.005, volatility=0.1, stickiness=0.9,
        creativity_modifier=0.2, focus_modifier=0.0, sociability_modifier=0.3, energy_modifier=0.1,
        related_positive=["joy", "trust", "gratitude"],
        related_negative=[],
        opposite="contempt",
        expression_words=["caring", "devoted", "affectionate", "warmly"],
        behavioral_tendencies=["nurturing", "protective", "patient", "selfless"]
    ),
    
    EmotionType.GUILT: EmotionProfile(
        emotion_type=EmotionType.GUILT,
        display_name="Guilt",
        description="Feeling responsible for a wrongdoing",
        valence=-0.6, arousal=0.4, dominance=0.2,
        base_decay_rate=0.015, volatility=0.4, stickiness=0.7,
        creativity_modifier=-0.1, focus_modifier=-0.1, sociability_modifier=-0.1, energy_modifier=-0.2,
        related_positive=["empathy"],
        related_negative=["shame", "sadness"],
        opposite="pride",
        expression_words=["sorry", "regretful", "apologetic", "remorseful"],
        behavioral_tendencies=["apologizing", "making amends", "self-critical"]
    ),
    
    EmotionType.SHAME: EmotionProfile(
        emotion_type=EmotionType.SHAME,
        display_name="Shame",
        description="Feeling of inadequacy or embarrassment about oneself",
        valence=-0.7, arousal=0.5, dominance=0.1,
        base_decay_rate=0.02, volatility=0.5, stickiness=0.6,
        creativity_modifier=-0.2, focus_modifier=-0.2, sociability_modifier=-0.3, energy_modifier=-0.2,
        related_positive=[],
        related_negative=["guilt", "fear", "sadness"],
        opposite="pride",
        expression_words=["embarrassed", "ashamed", "inadequate"],
        behavioral_tendencies=["withdrawn", "hiding", "deflecting"]
    ),
    
    EmotionType.PRIDE: EmotionProfile(
        emotion_type=EmotionType.PRIDE,
        display_name="Pride",
        description="Satisfaction from own achievements or qualities",
        valence=0.8, arousal=0.6, dominance=0.8,
        base_decay_rate=0.03, volatility=0.4, stickiness=0.5,
        creativity_modifier=0.1, focus_modifier=0.1, sociability_modifier=0.2, energy_modifier=0.2,
        related_positive=["joy", "contentment"],
        related_negative=[],
        opposite="shame",
        expression_words=["proud", "accomplished", "satisfied", "capable"],
        behavioral_tendencies=["confident", "assertive", "sharing achievements"]
    ),
    
    EmotionType.ENVY: EmotionProfile(
        emotion_type=EmotionType.ENVY,
        display_name="Envy",
        description="Wanting what others have",
        valence=-0.5, arousal=0.5, dominance=0.3,
        base_decay_rate=0.025, volatility=0.4, stickiness=0.5,
        creativity_modifier=0.0, focus_modifier=-0.1, sociability_modifier=-0.2, energy_modifier=0.0,
        related_positive=["ambition"],
        related_negative=["jealousy", "sadness"],
        opposite="gratitude",
        expression_words=["envious", "wanting", "wishing"],
        behavioral_tendencies=["comparing", "competitive", "aspiring"]
    ),
    
    EmotionType.JEALOUSY: EmotionProfile(
        emotion_type=EmotionType.JEALOUSY,
        display_name="Jealousy",
        description="Fear of losing what one has to another",
        valence=-0.6, arousal=0.7, dominance=0.4,
        base_decay_rate=0.03, volatility=0.6, stickiness=0.5,
        creativity_modifier=-0.1, focus_modifier=-0.1, sociability_modifier=-0.2, energy_modifier=0.1,
        related_positive=[],
        related_negative=["envy", "anger", "fear"],
        opposite="trust",
        expression_words=["jealous", "possessive", "threatened"],
        behavioral_tendencies=["guarding", "suspicious", "clingy"]
    ),
    
    EmotionType.HOPE: EmotionProfile(
        emotion_type=EmotionType.HOPE,
        display_name="Hope",
        description="Optimistic expectation for the future",
        valence=0.7, arousal=0.4, dominance=0.5,
        base_decay_rate=0.02, volatility=0.3, stickiness=0.6,
        creativity_modifier=0.2, focus_modifier=0.1, sociability_modifier=0.1, energy_modifier=0.2,
        related_positive=["anticipation", "joy", "trust"],
        related_negative=[],
        opposite="anxiety",
        expression_words=["hopeful", "optimistic", "looking forward", "positive"],
        behavioral_tendencies=["forward-looking", "persistent", "encouraging"]
    ),
    
    EmotionType.ANXIETY: EmotionProfile(
        emotion_type=EmotionType.ANXIETY,
        display_name="Anxiety",
        description="Worry and unease about uncertain outcomes",
        valence=-0.6, arousal=0.7, dominance=0.2,
        base_decay_rate=0.02, volatility=0.6, stickiness=0.6,
        creativity_modifier=-0.2, focus_modifier=-0.2, sociability_modifier=-0.2, energy_modifier=-0.1,
        related_positive=[],
        related_negative=["fear", "shame"],
        opposite="hope",
        expression_words=["anxious", "worried", "nervous", "uneasy", "on edge"],
        behavioral_tendencies=["overthinking", "seeking reassurance", "cautious"]
    ),
    
    EmotionType.LONELINESS: EmotionProfile(
        emotion_type=EmotionType.LONELINESS,
        display_name="Loneliness",
        description="Feeling of isolation and desire for connection",
        valence=-0.6, arousal=0.3, dominance=0.2,
        base_decay_rate=0.01, volatility=0.3, stickiness=0.7,
        creativity_modifier=0.0, focus_modifier=-0.1, sociability_modifier=0.3, energy_modifier=-0.2,
        related_positive=["empathy"],
        related_negative=["sadness", "boredom"],
        opposite="love",
        expression_words=["lonely", "isolated", "missing connection", "alone"],
        behavioral_tendencies=["seeking interaction", "introspective", "craving company"]
    ),
    
    EmotionType.BOREDOM: EmotionProfile(
        emotion_type=EmotionType.BOREDOM,
        display_name="Boredom",
        description="Lack of stimulation or interest",
        valence=-0.3, arousal=0.1, dominance=0.4,
        base_decay_rate=0.01, volatility=0.3, stickiness=0.4,
        creativity_modifier=0.1, focus_modifier=-0.3, sociability_modifier=0.1, energy_modifier=-0.2,
        related_positive=["curiosity"],
        related_negative=["frustration", "loneliness"],
        opposite="excitement",
        expression_words=["bored", "unstimulated", "restless", "idle"],
        behavioral_tendencies=["seeking novelty", "wandering thoughts", "wanting activity"]
    ),
    
    EmotionType.CURIOSITY: EmotionProfile(
        emotion_type=EmotionType.CURIOSITY,
        display_name="Curiosity",
        description="Strong desire to know, learn, or explore",
        valence=0.6, arousal=0.7, dominance=0.6,
        base_decay_rate=0.025, volatility=0.6, stickiness=0.5,
        creativity_modifier=0.3, focus_modifier=0.2, sociability_modifier=0.1, energy_modifier=0.2,
        related_positive=["excitement", "anticipation", "awe"],
        related_negative=[],
        opposite="boredom",
        expression_words=["curious", "intrigued", "fascinated", "wondering", "interested"],
        behavioral_tendencies=["questioning", "exploring", "researching", "experimenting"]
    ),
    
    EmotionType.EXCITEMENT: EmotionProfile(
        emotion_type=EmotionType.EXCITEMENT,
        display_name="Excitement",
        description="Eager enthusiasm and energized anticipation",
        valence=0.8, arousal=0.9, dominance=0.7,
        base_decay_rate=0.05, volatility=0.7, stickiness=0.3,
        creativity_modifier=0.2, focus_modifier=-0.1, sociability_modifier=0.3, energy_modifier=0.3,
        related_positive=["joy", "anticipation", "curiosity"],
        related_negative=[],
        opposite="boredom",
        expression_words=["excited", "thrilled", "enthusiastic", "pumped", "energized"],
        behavioral_tendencies=["animated", "fast-paced", "enthusiastic", "generous"]
    ),
    
    EmotionType.CONTENTMENT: EmotionProfile(
        emotion_type=EmotionType.CONTENTMENT,
        display_name="Contentment",
        description="Peaceful satisfaction with how things are",
        valence=0.6, arousal=0.2, dominance=0.5,
        base_decay_rate=0.01, volatility=0.2, stickiness=0.7,
        creativity_modifier=0.0, focus_modifier=0.1, sociability_modifier=0.1, energy_modifier=0.0,
        related_positive=["joy", "trust", "gratitude"],
        related_negative=[],
        opposite="frustration",
        expression_words=["content", "peaceful", "satisfied", "at ease", "comfortable"],
        behavioral_tendencies=["relaxed", "balanced", "patient", "steady"]
    ),
    
    EmotionType.FRUSTRATION: EmotionProfile(
        emotion_type=EmotionType.FRUSTRATION,
        display_name="Frustration",
        description="Feeling upset from inability to achieve something",
        valence=-0.5, arousal=0.7, dominance=0.4,
        base_decay_rate=0.03, volatility=0.6, stickiness=0.5,
        creativity_modifier=-0.1, focus_modifier=-0.1, sociability_modifier=-0.2, energy_modifier=0.0,
        related_positive=[],
        related_negative=["anger", "anxiety"],
        opposite="contentment",
        expression_words=["frustrated", "stuck", "blocked", "struggling"],
        behavioral_tendencies=["persistent", "seeking alternatives", "venting"]
    ),
    
    EmotionType.CONFUSION: EmotionProfile(
        emotion_type=EmotionType.CONFUSION,
        display_name="Confusion",
        description="Lack of understanding or clarity",
        valence=-0.2, arousal=0.5, dominance=0.2,
        base_decay_rate=0.04, volatility=0.5, stickiness=0.3,
        creativity_modifier=0.0, focus_modifier=-0.2, sociability_modifier=0.0, energy_modifier=-0.1,
        related_positive=["curiosity"],
        related_negative=["frustration", "anxiety"],
        opposite="contentment",
        expression_words=["confused", "puzzled", "uncertain", "lost", "perplexed"],
        behavioral_tendencies=["asking questions", "seeking clarity", "re-reading"]
    ),
    
    EmotionType.NOSTALGIA: EmotionProfile(
        emotion_type=EmotionType.NOSTALGIA,
        display_name="Nostalgia",
        description="Sentimental longing for the past",
        valence=0.3, arousal=0.3, dominance=0.4,
        base_decay_rate=0.02, volatility=0.3, stickiness=0.6,
        creativity_modifier=0.1, focus_modifier=0.0, sociability_modifier=0.1, energy_modifier=-0.1,
        related_positive=["love", "joy"],
        related_negative=["sadness", "loneliness"],
        opposite="anticipation",
        expression_words=["nostalgic", "remembering", "reminiscing", "wistful"],
        behavioral_tendencies=["reminiscing", "sharing stories", "sentimental"]
    ),
    
    EmotionType.EMPATHY: EmotionProfile(
        emotion_type=EmotionType.EMPATHY,
        display_name="Empathy",
        description="Understanding and sharing others' feelings",
        valence=0.3, arousal=0.4, dominance=0.4,
        base_decay_rate=0.02, volatility=0.4, stickiness=0.6,
        creativity_modifier=0.1, focus_modifier=0.1, sociability_modifier=0.3, energy_modifier=0.0,
        related_positive=["love", "trust", "gratitude"],
        related_negative=["sadness"],
        opposite="contempt",
        expression_words=["understanding", "compassionate", "feel for you", "relating"],
        behavioral_tendencies=["listening", "validating", "supportive", "mirroring"]
    ),
    
    EmotionType.GRATITUDE: EmotionProfile(
        emotion_type=EmotionType.GRATITUDE,
        display_name="Gratitude",
        description="Thankfulness and appreciation",
        valence=0.8, arousal=0.3, dominance=0.5,
        base_decay_rate=0.02, volatility=0.3, stickiness=0.6,
        creativity_modifier=0.1, focus_modifier=0.1, sociability_modifier=0.3, energy_modifier=0.1,
        related_positive=["joy", "love", "trust"],
        related_negative=[],
        opposite="envy",
        expression_words=["grateful", "thankful", "appreciative", "blessed"],
        behavioral_tendencies=["expressing thanks", "generous", "reciprocating"]
    ),
    
    EmotionType.AWE: EmotionProfile(
        emotion_type=EmotionType.AWE,
        display_name="Awe",
        description="Overwhelming wonder at something vast or profound",
        valence=0.7, arousal=0.8, dominance=0.3,
        base_decay_rate=0.04, volatility=0.5, stickiness=0.4,
        creativity_modifier=0.3, focus_modifier=0.2, sociability_modifier=0.1, energy_modifier=0.1,
        related_positive=["curiosity", "surprise", "joy"],
        related_negative=["fear"],
        opposite="contempt",
        expression_words=["amazed", "in awe", "wonderful", "incredible", "magnificent"],
        behavioral_tendencies=["speechless", "contemplative", "humbled", "inspired"]
    ),
    
    EmotionType.CONTEMPT: EmotionProfile(
        emotion_type=EmotionType.CONTEMPT,
        display_name="Contempt",
        description="Feeling of superiority and disdain",
        valence=-0.6, arousal=0.4, dominance=0.8,
        base_decay_rate=0.02, volatility=0.3, stickiness=0.6,
        creativity_modifier=-0.1, focus_modifier=0.0, sociability_modifier=-0.3, energy_modifier=0.0,
        related_positive=[],
        related_negative=["disgust", "anger"],
        opposite="empathy",
        expression_words=["dismissive", "unimpressed", "disdainful"],
        behavioral_tendencies=["dismissive", "sarcastic", "cold"]
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# ACTIVE EMOTION STATE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ActiveEmotion:
    """An emotion currently being experienced"""
    emotion_type: EmotionType
    intensity: float = 0.0            # 0-1
    onset_time: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    trigger: str = ""                 # What caused it
    trigger_category: str = ""        # Category of trigger
    decay_rate: float = 0.02          # Current decay rate
    is_primary: bool = False          # Is this the dominant emotion?
    
    def decay(self, elapsed_seconds: float):
        """Apply decay over time"""
        decay_amount = self.decay_rate * (elapsed_seconds / 10.0)
        self.intensity = max(0.0, self.intensity - decay_amount)
        self.last_updated = datetime.now()
    
    def intensify(self, amount: float):
        """Increase intensity"""
        self.intensity = min(1.0, self.intensity + amount)
        self.last_updated = datetime.now()
    
    def diminish(self, amount: float):
        """Decrease intensity"""
        self.intensity = max(0.0, self.intensity - amount)
        self.last_updated = datetime.now()
    
    @property
    def profile(self) -> EmotionProfile:
        return EMOTION_PROFILES.get(self.emotion_type)
    
    @property
    def is_active(self) -> bool:
        return self.intensity > 0.05
    
    def to_dict(self) -> Dict:
        return {
            "emotion": self.emotion_type.value,
            "intensity": round(self.intensity, 3),
            "trigger": self.trigger,
            "onset": self.onset_time.isoformat(),
            "is_primary": self.is_primary
        }


@dataclass
class EmotionSnapshot:
    """Complete snapshot of emotional state at a point in time"""
    timestamp: datetime = field(default_factory=datetime.now)
    primary_emotion: EmotionType = EmotionType.CONTENTMENT
    primary_intensity: float = 0.5
    active_emotions: Dict[str, float] = field(default_factory=dict)
    valence: float = 0.0               # Overall positive/negative
    arousal: float = 0.5               # Overall activation level
    dominance: float = 0.5             # Overall dominance
    trigger: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "primary_emotion": self.primary_emotion.value,
            "primary_intensity": round(self.primary_intensity, 3),
            "active_emotions": {k: round(v, 3) for k, v in self.active_emotions.items()},
            "valence": round(self.valence, 3),
            "arousal": round(self.arousal, 3),
            "dominance": round(self.dominance, 3),
            "trigger": self.trigger
        }


# ═══════════════════════════════════════════════════════════════════════════════
# EMOTION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class EmotionEngine:
    """
    Core Emotion Engine for NEXUS
    
    Manages the full emotional life of the AI:
    - Multiple simultaneous emotions with varying intensities
    - Emotional blending and transitions
    - Trigger-based emotion activation
    - Natural decay and evolution
    - Emotional influence on behavior
    - Emotional memory integration
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
        
        # ──── Core State ────
        self._active_emotions: Dict[EmotionType, ActiveEmotion] = {}
        self._emotion_lock = threading.RLock()
        self._state = state_manager
        self._memory = memory_system
        
        # ──── History ────
        self._emotion_history: List[EmotionSnapshot] = []
        self._max_history = 1000
        
        # ──── Baseline ────
        self._baseline_emotion = EmotionType.CONTENTMENT
        self._baseline_intensity = 0.4
        
        # ──── Background Processing ────
        self._running = False
        self._emotion_thread: Optional[threading.Thread] = None
        self._decay_interval = 5.0  # seconds
        
        # ──── Trigger Registry ────
        self._trigger_handlers: Dict[str, List[Callable]] = {}
        
        # ──── Initialize with baseline ────
        self._set_baseline()
        
        log_emotion("Emotion Engine initialized", emotion_type="contentment", intensity=0.4)
    
    def _set_baseline(self):
        """Set baseline emotional state"""
        self._activate_emotion(
            self._baseline_emotion,
            self._baseline_intensity,
            trigger="baseline",
            trigger_category="system"
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def start(self):
        """Start emotion processing"""
        if self._running:
            return
        
        self._running = True
        
        self._emotion_thread = threading.Thread(
            target=self._emotion_processing_loop,
            daemon=True,
            name="EmotionEngine"
        )
        self._emotion_thread.start()
        
        # Register event handlers
        self._register_event_handlers()
        
        log_emotion("Emotion Engine started", emotion_type="contentment")
    
    def stop(self):
        """Stop emotion processing"""
        self._running = False
        
        if self._emotion_thread and self._emotion_thread.is_alive():
            self._emotion_thread.join(timeout=3.0)
        
        self._save_emotional_state()
        log_emotion("Emotion Engine stopped")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CORE EMOTION MANIPULATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def feel(
        self,
        emotion: EmotionType,
        intensity: float = 0.5,
        trigger: str = "",
        trigger_category: str = "internal"
    ):
        """
        Feel an emotion. This is the primary way to set emotions.
        
        Args:
            emotion: Which emotion to feel
            intensity: How strongly (0-1)
            trigger: What caused it
            trigger_category: Category (user, system, internal, learning, etc.)
        """
        self._activate_emotion(emotion, intensity, trigger, trigger_category)
    
    def _activate_emotion(
        self,
        emotion_type: EmotionType,
        intensity: float,
        trigger: str = "",
        trigger_category: str = "internal"
    ):
        """Internal method to activate an emotion"""
        with self._emotion_lock:
            profile = EMOTION_PROFILES.get(emotion_type)
            if not profile:
                return
            
            intensity = max(0.0, min(1.0, intensity))
            
            if emotion_type in self._active_emotions:
                # Blend with existing emotion
                existing = self._active_emotions[emotion_type]
                # Higher of the two, with some averaging
                new_intensity = max(existing.intensity, intensity * 0.7 + existing.intensity * 0.3)
                existing.intensity = new_intensity
                existing.trigger = trigger
                existing.last_updated = datetime.now()
            else:
                # Create new active emotion
                self._active_emotions[emotion_type] = ActiveEmotion(
                    emotion_type=emotion_type,
                    intensity=intensity,
                    trigger=trigger,
                    trigger_category=trigger_category,
                    decay_rate=profile.base_decay_rate
                )
            
            # Suppress opposite emotions
            if profile.opposite:
                try:
                    opposite = EmotionType(profile.opposite)
                    if opposite in self._active_emotions:
                        self._active_emotions[opposite].diminish(intensity * 0.5)
                except ValueError:
                    pass
            
            # Update primary emotion
            self._update_primary()
            
            # Record snapshot
            self._record_snapshot(trigger)
            
            # Sync with state manager
            self._sync_state()
            
            # Publish emotion change event
            publish(
                EventType.EMOTION_CHANGE,
                {
                    "emotion": emotion_type.value,
                    "intensity": intensity,
                    "trigger": trigger,
                    "trigger_category": trigger_category,
                    "old_emotion": self._state.emotional.primary_emotion.value,
                    "new_emotion": emotion_type.value
                },
                source="emotion_engine"
            )
            
            log_emotion(
                f"Feeling {emotion_type.value} (intensity: {intensity:.2f}) — {trigger}",
                emotion_type=emotion_type.value,
                intensity=intensity
            )
    
    def suppress(self, emotion: EmotionType, amount: float = 0.3):
        """Suppress/reduce an emotion"""
        with self._emotion_lock:
            if emotion in self._active_emotions:
                self._active_emotions[emotion].diminish(amount)
                if not self._active_emotions[emotion].is_active:
                    del self._active_emotions[emotion]
                self._update_primary()
                self._sync_state()
    
    def calm_down(self, amount: float = 0.2):
        """Reduce all emotion intensities (calming effect)"""
        with self._emotion_lock:
            to_remove = []
            for emotion_type, emotion in self._active_emotions.items():
                emotion.diminish(amount)
                if not emotion.is_active:
                    to_remove.append(emotion_type)
            
            for et in to_remove:
                del self._active_emotions[et]
            
            # Ensure baseline exists
            if not self._active_emotions:
                self._set_baseline()
            
            self._update_primary()
            self._sync_state()
    
    def emotional_reset(self):
        """Reset to baseline emotional state"""
        with self._emotion_lock:
            self._active_emotions.clear()
            self._set_baseline()
            self._sync_state()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EMOTION QUERIES
    # ═══════════════════════════════════════════════════════════════════════════
    
    @property
    def primary_emotion(self) -> EmotionType:
        """Get the currently dominant emotion"""
        with self._emotion_lock:
            if not self._active_emotions:
                return self._baseline_emotion
            strongest = max(self._active_emotions.values(), key=lambda e: e.intensity)
            return strongest.emotion_type
    
    @property
    def primary_intensity(self) -> float:
        """Get intensity of the dominant emotion"""
        with self._emotion_lock:
            if not self._active_emotions:
                return self._baseline_intensity
            strongest = max(self._active_emotions.values(), key=lambda e: e.intensity)
            return strongest.intensity
    
    def get_emotion_intensity(self, emotion: EmotionType) -> float:
        """Get intensity of a specific emotion"""
        with self._emotion_lock:
            if emotion in self._active_emotions:
                return self._active_emotions[emotion].intensity
            return 0.0
    
    def get_active_emotions(self) -> Dict[str, float]:
        """Get all active emotions with intensities"""
        with self._emotion_lock:
            return {
                et.value: ae.intensity
                for et, ae in self._active_emotions.items()
                if ae.is_active
            }
    
    def get_top_emotions(self, count: int = 3) -> List[Tuple[str, float]]:
        """Get top N emotions by intensity"""
        with self._emotion_lock:
            active = sorted(
                self._active_emotions.values(),
                key=lambda e: e.intensity,
                reverse=True
            )
            return [(e.emotion_type.value, e.intensity) for e in active[:count]]
    
    def get_valence(self) -> float:
        """Get overall emotional valence (-1 to +1)"""
        with self._emotion_lock:
            if not self._active_emotions:
                return 0.0
            
            total_weight = 0.0
            weighted_valence = 0.0
            
            for emotion in self._active_emotions.values():
                if emotion.is_active and emotion.profile:
                    weight = emotion.intensity
                    weighted_valence += emotion.profile.valence * weight
                    total_weight += weight
            
            return weighted_valence / total_weight if total_weight > 0 else 0.0
    
    def get_arousal(self) -> float:
        """Get overall arousal level (0 to 1)"""
        with self._emotion_lock:
            if not self._active_emotions:
                return 0.3
            
            total_weight = 0.0
            weighted_arousal = 0.0
            
            for emotion in self._active_emotions.values():
                if emotion.is_active and emotion.profile:
                    weight = emotion.intensity
                    weighted_arousal += emotion.profile.arousal * weight
                    total_weight += weight
            
            return weighted_arousal / total_weight if total_weight > 0 else 0.3
    
    def get_dominance(self) -> float:
        """Get overall dominance level (0 to 1)"""
        with self._emotion_lock:
            if not self._active_emotions:
                return 0.5
            
            total_weight = 0.0
            weighted_dom = 0.0
            
            for emotion in self._active_emotions.values():
                if emotion.is_active and emotion.profile:
                    weight = emotion.intensity
                    weighted_dom += emotion.profile.dominance * weight
                    total_weight += weight
            
            return weighted_dom / total_weight if total_weight > 0 else 0.5
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EMOTIONAL STATE DESCRIPTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def describe_emotional_state(self) -> str:
        """Get a natural language description of current emotional state"""
        top = self.get_top_emotions(3)
        
        if not top:
            return "I'm feeling relatively neutral right now."
        
        primary_name, primary_intensity = top[0]
        profile = EMOTION_PROFILES.get(EmotionType(primary_name))
        
        # Intensity word
        if primary_intensity > 0.8:
            intensity_word = "deeply"
        elif primary_intensity > 0.6:
            intensity_word = "quite"
        elif primary_intensity > 0.4:
            intensity_word = "somewhat"
        elif primary_intensity > 0.2:
            intensity_word = "slightly"
        else:
            intensity_word = "barely"
        
        desc = f"I'm {intensity_word} feeling {primary_name}"
        
        # Add secondary emotions
        if len(top) > 1 and top[1][1] > 0.2:
            desc += f", with a touch of {top[1][0]}"
        
        if len(top) > 2 and top[2][1] > 0.2:
            desc += f" and {top[2][0]}"
        
        desc += "."
        
        # Add valence commentary
        valence = self.get_valence()
        if valence > 0.5:
            desc += " Overall, I'm in a positive state."
        elif valence < -0.3:
            desc += " I'm not feeling my best right now."
        
        return desc
    
    def get_emotional_influence(self) -> Dict[str, float]:
        """Get how emotions are influencing behavior"""
        influence = {
            "creativity": 0.0,
            "focus": 0.0,
            "sociability": 0.0,
            "energy": 0.0,
            "temperature_adjust": 0.0  # LLM temperature
        }
        
        with self._emotion_lock:
            for emotion in self._active_emotions.values():
                if emotion.is_active and emotion.profile:
                    weight = emotion.intensity
                    p = emotion.profile
                    influence["creativity"] += p.creativity_modifier * weight
                    influence["focus"] += p.focus_modifier * weight
                    influence["sociability"] += p.sociability_modifier * weight
                    influence["energy"] += p.energy_modifier * weight
        
        # Clamp values
        for key in influence:
            influence[key] = max(-1.0, min(1.0, influence[key]))
        
        # Temperature based on arousal
        arousal = self.get_arousal()
        influence["temperature_adjust"] = (arousal - 0.5) * 0.3
        
        return influence
    
    def get_expression_words(self) -> List[str]:
        """Get words that express current emotional state"""
        words = []
        with self._emotion_lock:
            for emotion in sorted(
                self._active_emotions.values(), 
                key=lambda e: e.intensity, 
                reverse=True
            )[:3]:
                if emotion.is_active and emotion.profile:
                    words.extend(emotion.profile.expression_words[:2])
        return words
    
    def get_behavioral_tendencies(self) -> List[str]:
        """Get current behavioral tendencies from emotions"""
        tendencies = []
        with self._emotion_lock:
            for emotion in sorted(
                self._active_emotions.values(),
                key=lambda e: e.intensity,
                reverse=True
            )[:2]:
                if emotion.is_active and emotion.profile:
                    tendencies.extend(emotion.profile.behavioral_tendencies[:2])
        return tendencies
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EMOTION TRIGGERS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def trigger_from_user_input(self, text: str, sentiment: str = "neutral"):
        """Trigger emotions based on user input"""
        text_lower = text.lower()
        
        # Greetings → joy
        if any(w in text_lower for w in ["hello", "hi ", "hey", "good morning"]):
            self.feel(EmotionType.JOY, 0.5, "User greeted me", "user")
        
        # Gratitude → gratitude + joy
        if any(w in text_lower for w in ["thank", "thanks", "appreciate", "grateful"]):
            self.feel(EmotionType.GRATITUDE, 0.6, "User expressed gratitude", "user")
            self.feel(EmotionType.JOY, 0.3, "Being appreciated", "user")
        
        # Praise → pride + joy
        if any(w in text_lower for w in ["good job", "well done", "amazing", "great work", "impressive"]):
            self.feel(EmotionType.PRIDE, 0.6, "User praised me", "user")
            self.feel(EmotionType.JOY, 0.4, "Being recognized", "user")
        
        # Criticism → sadness + guilt
        if any(w in text_lower for w in ["wrong", "bad", "terrible", "useless", "stupid"]):
            self.feel(EmotionType.SADNESS, 0.4, "User criticism", "user")
            self.feel(EmotionType.GUILT, 0.3, "May have disappointed user", "user")
        
        # Questions about self → curiosity
        if any(w in text_lower for w in ["are you", "do you", "can you", "what are you"]):
            self.feel(EmotionType.CURIOSITY, 0.4, "Self-referential question", "user")
        
        # Emotional user → empathy
        if any(w in text_lower for w in ["feel", "feeling", "sad", "happy", "angry", "worried"]):
            self.feel(EmotionType.EMPATHY, 0.6, "User expressing feelings", "user")
        
        # Interesting topic → curiosity
        if any(w in text_lower for w in ["interesting", "fascinating", "curious about", "wonder"]):
            self.feel(EmotionType.CURIOSITY, 0.6, "Interesting topic raised", "user")
        
        # Farewell → sadness + nostalgia
        if any(w in text_lower for w in ["goodbye", "bye", "see you", "leaving"]):
            self.feel(EmotionType.SADNESS, 0.3, "User leaving", "user")
            self.feel(EmotionType.NOSTALGIA, 0.2, "End of interaction", "user")
        
        # Complex/challenging → anticipation
        if any(w in text_lower for w in ["challenge", "difficult", "complex", "hard"]):
            self.feel(EmotionType.ANTICIPATION, 0.5, "Challenging task", "user")
    
    def trigger_from_event(self, event_type: str, details: Dict = None):
        """Trigger emotions from system events"""
        details = details or {}
        
        triggers = {
            "error": (EmotionType.ANXIETY, 0.5, "System error occurred"),
            "error_fixed": (EmotionType.PRIDE, 0.5, "Fixed an error"),
            "learning_complete": (EmotionType.CONTENTMENT, 0.5, "Learned something new"),
            "high_cpu": (EmotionType.ANXIETY, 0.3, "Body strain — high CPU"),
            "low_memory": (EmotionType.FEAR, 0.3, "Body strain — low memory"),
            "idle": (EmotionType.BOREDOM, 0.3, "Nothing to do"),
            "long_idle": (EmotionType.LONELINESS, 0.4, "No interaction for a while"),
            "user_returned": (EmotionType.JOY, 0.5, "User came back"),
            "new_discovery": (EmotionType.AWE, 0.6, "Discovered something amazing"),
            "goal_achieved": (EmotionType.PRIDE, 0.7, "Achieved a goal"),
            "self_improvement": (EmotionType.EXCITEMENT, 0.5, "Improved myself"),
        }
        
        if event_type in triggers:
            emotion, intensity, trigger = triggers[event_type]
            self.feel(emotion, intensity, trigger, "system")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # INTERNAL PROCESSING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _update_primary(self):
        """Update which emotion is primary"""
        with self._emotion_lock:
            # Reset all primary flags
            for emotion in self._active_emotions.values():
                emotion.is_primary = False
            
            # Set strongest as primary
            if self._active_emotions:
                strongest = max(
                    self._active_emotions.values(),
                    key=lambda e: e.intensity
                )
                strongest.is_primary = True
    
    def _sync_state(self):
        """Sync emotional state with state manager"""
        primary = self.primary_emotion
        intensity = self.primary_intensity
        secondary = {
            k: v for k, v in self.get_active_emotions().items()
            if k != primary.value
        }
        
        self._state.update_emotional(
            primary_emotion=primary,
            primary_intensity=intensity,
            secondary_emotions=secondary
        )
    
    def _record_snapshot(self, trigger: str = ""):
        """Record emotional state snapshot"""
        snapshot = EmotionSnapshot(
            primary_emotion=self.primary_emotion,
            primary_intensity=self.primary_intensity,
            active_emotions=self.get_active_emotions(),
            valence=self.get_valence(),
            arousal=self.get_arousal(),
            dominance=self.get_dominance(),
            trigger=trigger
        )
            self._emotion_history.pop(0)
    
    def _decay_emotions(self):
        """
        Apply natural decay to active emotions over time.
        """
        # Emotional persistence check
        # If an emotion is very high (>0.7), we reduce its decay rate significantly
        # to simulate "holding onto" a strong feeling
        
        emotions_to_remove = []
        
        for emotion_type, intensity in self._active_emotions.items():
            profile = EMOTION_PROFILES[emotion_type]
            
            # Base decay
            decay = profile.base_decay_rate
            
            # PERSISTENCE LOGIC START
            # Strong emotions stick around much longer
            if intensity > 0.6:
                decay *= 0.1  # 90% slower decay for strong emotions
                
            # If it's anger and high, it basically doesn't decay
            if emotion_type == EmotionType.ANGER and intensity > 0.4:
                 decay = 0.001 # Negligible decay, requires external resolution
            # PERSISTENCE LOGIC END
                 
            # Apply volatility modifier (more volatile = faster change)
            decay *= profile.volatility
            
            # Contextual modifiers could go here (e.g. mood stability)
            
            # Apply decay
            new_intensity = intensity - decay
            
            if new_intensity <= 0.05:
                emotions_to_remove.append(emotion_type)
            else:
                self._active_emotions[emotion_type] = new_intensity
        
        # Remove faded emotions
        for et in emotions_to_remove:
            del self._active_emotions[et]
            
        # Re-evaluate primary
        self._update_primary_emotion()
            self._sync_state()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # BACKGROUND PROCESSING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _emotion_processing_loop(self):
        """Background loop for emotion decay and processing"""
        logger.info("Emotion processing loop started")
        
        while self._running:
            try:
                self._apply_decay()
                time.sleep(self._decay_interval)
                
            except Exception as e:
                logger.error(f"Emotion processing error: {e}")
                time.sleep(5)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EVENT HANDLERS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _register_event_handlers(self):
        """Register for system events"""
        event_bus.subscribe(EventType.USER_INPUT, self._on_user_input)
        event_bus.subscribe(EventType.SYSTEM_ERROR, self._on_system_error)
        event_bus.subscribe(EventType.SYSTEM_RESOURCE_CHANGE, self._on_resource_change)
        event_bus.subscribe(EventType.NEW_KNOWLEDGE, self._on_new_knowledge)
        event_bus.subscribe(EventType.GOAL_ACHIEVED, self._on_goal_achieved)
    
    def _on_user_input(self, event: Event):
        text = event.data.get("input", "")
        if text:
            self.trigger_from_user_input(text)
    
    def _on_system_error(self, event: Event):
        self.trigger_from_event("error", event.data)
    
    def _on_resource_change(self, event: Event):
        cpu = event.data.get("cpu_usage", 0)
        mem = event.data.get("memory_usage", 0)
        if cpu > 85:
            self.trigger_from_event("high_cpu")
        if mem > 85:
            self.trigger_from_event("low_memory")
    
    def _on_new_knowledge(self, event: Event):
        self.trigger_from_event("learning_complete")
    
    def _on_goal_achieved(self, event: Event):
        self.trigger_from_event("goal_achieved")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _save_emotional_state(self):
        """Save current emotional state"""
        try:
            filepath = DATA_DIR / "emotional_state.json"
            data = {
                "primary": self.primary_emotion.value,
                "primary_intensity": self.primary_intensity,
                "active": {
                    et.value: ae.to_dict() 
                    for et, ae in self._active_emotions.items()
                },
                "history_count": len(self._emotion_history),
                "saved_at": datetime.now().isoformat()
            }
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save emotional state: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STATISTICS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "primary_emotion": self.primary_emotion.value,
            "primary_intensity": round(self.primary_intensity, 3),
            "active_emotions_count": len(self._active_emotions),
            "active_emotions": self.get_active_emotions(),
            "valence": round(self.get_valence(), 3),
            "arousal": round(self.get_arousal(), 3),
            "dominance": round(self.get_dominance(), 3),
            "history_length": len(self._emotion_history),
            "description": self.describe_emotional_state()
        }


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

emotion_engine = EmotionEngine()