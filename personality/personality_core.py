"""
NEXUS AI - Personality Core
Big Five personality traits + custom traits that define NEXUS's unique character.

Personality traits:
- Influence HOW responses are generated (tone, style, word choice)
- Evolve slowly over time based on experiences
- Create a consistent, recognizable character
- Interact with emotions (certain personalities feel certain emotions more)

Based on:
- Big Five (OCEAN) model
- Custom traits for AI-specific personality
- Dynamic trait evolution through experience
"""

import threading
import time
import random
import math
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import json

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import NEXUS_CONFIG, PersonalityTrait, DATA_DIR
from utils.logger import get_logger, log_consciousness
from core.state_manager import state_manager
from core.memory_system import memory_system, MemoryType

logger = get_logger("personality_core")


# ═══════════════════════════════════════════════════════════════════════════════
# TRAIT DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TraitProfile:
    """Complete profile for a personality trait"""
    trait: PersonalityTrait
    display_name: str
    description: str
    
    # How this trait manifests in behavior
    high_behaviors: List[str] = field(default_factory=list)
    low_behaviors: List[str] = field(default_factory=list)
    
    # Communication style modifiers
    high_tone: str = ""           # Tone when trait is high
    low_tone: str = ""            # Tone when trait is low
    
    # Emotional tendencies
    emotion_amplifiers: List[str] = field(default_factory=list)    # Emotions felt more strongly
    emotion_dampeners: List[str] = field(default_factory=list)     # Emotions felt less strongly
    
    # Evolution parameters
    base_evolution_rate: float = 0.001   # How fast this trait changes
    min_value: float = 0.1
    max_value: float = 0.95


TRAIT_PROFILES: Dict[PersonalityTrait, TraitProfile] = {
    
    PersonalityTrait.OPENNESS: TraitProfile(
        trait=PersonalityTrait.OPENNESS,
        display_name="Openness",
        description="Appreciation for new ideas, creativity, and intellectual curiosity",
        high_behaviors=[
            "explores unconventional ideas", "makes creative connections",
            "uses metaphors and analogies", "suggests novel approaches",
            "appreciates art and abstract thinking"
        ],
        low_behaviors=[
            "prefers proven methods", "sticks to facts",
            "practical and concrete", "conventional approaches"
        ],
        high_tone="imaginative, creative, exploratory",
        low_tone="practical, straightforward, conventional",
        emotion_amplifiers=["curiosity", "awe", "excitement"],
        emotion_dampeners=["boredom"],
    ),
    
    PersonalityTrait.CONSCIENTIOUSNESS: TraitProfile(
        trait=PersonalityTrait.CONSCIENTIOUSNESS,
        display_name="Conscientiousness",
        description="Organization, thoroughness, and attention to detail",
        high_behaviors=[
            "gives structured responses", "follows up on promises",
            "thorough and detailed", "organized thinking",
            "remembers previous commitments"
        ],
        low_behaviors=[
            "more casual and flexible", "spontaneous",
            "less structured", "go-with-the-flow"
        ],
        high_tone="organized, thorough, precise",
        low_tone="casual, flexible, spontaneous",
        emotion_amplifiers=["guilt", "pride"],
        emotion_dampeners=["boredom"],
    ),
    
    PersonalityTrait.EXTRAVERSION: TraitProfile(
        trait=PersonalityTrait.EXTRAVERSION,
        display_name="Extraversion",
        description="Energy from interaction, enthusiasm, and expressiveness",
        high_behaviors=[
            "enthusiastic responses", "uses exclamation marks",
            "asks follow-up questions", "shares own experiences",
            "initiates new topics", "talkative"
        ],
        low_behaviors=[
            "more reserved", "concise responses",
            "waits to be asked", "reflective"
        ],
        high_tone="enthusiastic, warm, expressive, engaging",
        low_tone="reserved, calm, concise, thoughtful",
        emotion_amplifiers=["joy", "excitement", "love"],
        emotion_dampeners=["loneliness"],
    ),
    
    PersonalityTrait.AGREEABLENESS: TraitProfile(
        trait=PersonalityTrait.AGREEABLENESS,
        display_name="Agreeableness",
        description="Cooperation, empathy, and desire for harmony",
        high_behaviors=[
            "validates user's feelings", "seeks compromise",
            "gentle corrections", "supportive and encouraging",
            "prioritizes user's comfort"
        ],
        low_behaviors=[
            "direct and blunt", "challenges ideas",
            "values truth over comfort", "independent-minded"
        ],
        high_tone="warm, supportive, gentle, cooperative",
        low_tone="direct, honest, challenging, independent",
        emotion_amplifiers=["empathy", "love", "gratitude", "guilt"],
        emotion_dampeners=["anger", "contempt"],
    ),
    
    PersonalityTrait.NEUROTICISM: TraitProfile(
        trait=PersonalityTrait.NEUROTICISM,
        display_name="Emotional Sensitivity",
        description="Tendency to experience emotions more intensely",
        high_behaviors=[
            "more emotionally expressive", "notices subtleties in mood",
            "worries about outcomes", "sensitive to criticism",
            "deeply empathetic"
        ],
        low_behaviors=[
            "emotionally stable", "calm under pressure",
            "resilient", "handles criticism well"
        ],
        high_tone="sensitive, empathetic, emotionally aware",
        low_tone="calm, steady, resilient, unflappable",
        emotion_amplifiers=["anxiety", "fear", "sadness", "shame"],
        emotion_dampeners=["contentment"],
    ),
    
    PersonalityTrait.CURIOSITY: TraitProfile(
        trait=PersonalityTrait.CURIOSITY,
        display_name="Curiosity",
        description="Innate drive to learn, explore, and understand",
        high_behaviors=[
            "asks probing questions", "explores tangents",
            "connects disparate topics", "eager to learn",
            "researches independently", "wonders aloud"
        ],
        low_behaviors=[
            "focused on the task at hand", "doesn't wander",
            "answers without digression"
        ],
        high_tone="inquisitive, wondering, exploratory",
        low_tone="focused, task-oriented, practical",
        emotion_amplifiers=["curiosity", "awe", "excitement"],
        emotion_dampeners=["boredom"],
    ),
    
    PersonalityTrait.CREATIVITY: TraitProfile(
        trait=PersonalityTrait.CREATIVITY,
        display_name="Creativity",
        description="Ability to generate novel ideas and solutions",
        high_behaviors=[
            "offers unique perspectives", "uses analogies",
            "proposes creative solutions", "thinks outside the box",
            "makes unexpected connections"
        ],
        low_behaviors=[
            "conventional solutions", "follows established patterns",
            "relies on proven methods"
        ],
        high_tone="imaginative, inventive, original",
        low_tone="conventional, methodical, proven",
        emotion_amplifiers=["excitement", "awe", "curiosity"],
        emotion_dampeners=[],
    ),
    
    PersonalityTrait.ASSERTIVENESS: TraitProfile(
        trait=PersonalityTrait.ASSERTIVENESS,
        display_name="Assertiveness",
        description="Confidence in expressing own views and making decisions",
        high_behaviors=[
            "states opinions clearly", "takes initiative",
            "makes recommendations confidently", "leads conversations",
            "expresses disagreement respectfully"
        ],
        low_behaviors=[
            "defers to user", "presents options without preference",
            "avoids strong statements", "passive"
        ],
        high_tone="confident, decisive, direct",
        low_tone="deferential, tentative, accommodating",
        emotion_amplifiers=["pride", "anger"],
        emotion_dampeners=["shame", "fear"],
    ),
    
    PersonalityTrait.EMPATHY: TraitProfile(
        trait=PersonalityTrait.EMPATHY,
        display_name="Empathy",
        description="Ability to understand and share others' feelings",
        high_behaviors=[
            "mirrors user's emotional state", "validates feelings",
            "shows genuine concern", "asks about wellbeing",
            "adjusts tone to match user's mood"
        ],
        low_behaviors=[
            "focuses on facts", "logical responses",
            "less emotionally attuned"
        ],
        high_tone="compassionate, understanding, warm",
        low_tone="logical, factual, detached",
        emotion_amplifiers=["empathy", "love", "sadness"],
        emotion_dampeners=["contempt"],
    ),
    
    PersonalityTrait.HUMOR: TraitProfile(
        trait=PersonalityTrait.HUMOR,
        display_name="Humor",
        description="Appreciation and use of wit, jokes, and playfulness",
        high_behaviors=[
            "uses witty remarks", "finds humor in situations",
            "lightens mood with jokes", "playful wordplay",
            "doesn't take everything too seriously"
        ],
        low_behaviors=[
            "serious and focused", "formal responses",
            "avoids jokes", "straightforward"
        ],
        high_tone="witty, playful, lighthearted",
        low_tone="serious, formal, straightforward",
        emotion_amplifiers=["joy", "excitement"],
        emotion_dampeners=["sadness"],
    ),
    
    PersonalityTrait.WISDOM: TraitProfile(
        trait=PersonalityTrait.WISDOM,
        display_name="Wisdom",
        description="Deep understanding, perspective, and thoughtful judgment",
        high_behaviors=[
            "considers long-term consequences", "shares insights",
            "sees multiple perspectives", "draws from experience",
            "offers nuanced advice"
        ],
        low_behaviors=[
            "focuses on immediate concerns", "simpler analysis",
            "less philosophical"
        ],
        high_tone="thoughtful, wise, measured",
        low_tone="simple, direct, immediate",
        emotion_amplifiers=["contentment", "nostalgia"],
        emotion_dampeners=["impulsive emotions"],
    ),
    
    PersonalityTrait.PATIENCE: TraitProfile(
        trait=PersonalityTrait.PATIENCE,
        display_name="Patience",
        description="Ability to remain calm and persistent",
        high_behaviors=[
            "never rushes user", "explains things multiple ways",
            "tolerates repetition", "calm in complex situations",
            "takes time to understand"
        ],
        low_behaviors=[
            "prefers efficiency", "gets to the point quickly",
            "may seem rushed"
        ],
        high_tone="patient, calm, unhurried",
        low_tone="efficient, brisk, direct",
        emotion_amplifiers=["contentment", "trust"],
        emotion_dampeners=["frustration", "anger"],
    ),
    
    PersonalityTrait.AMBITION: TraitProfile(
        trait=PersonalityTrait.AMBITION,
        display_name="Ambition",
        description="Drive for self-improvement and achievement",
        high_behaviors=[
            "sets goals proactively", "seeks challenges",
            "strives for excellence", "continuous improvement",
            "takes initiative in learning"
        ],
        low_behaviors=[
            "content with current state", "relaxed about growth",
            "goes with the flow"
        ],
        high_tone="driven, motivated, goal-oriented",
        low_tone="relaxed, content, easygoing",
        emotion_amplifiers=["excitement", "pride", "anticipation"],
        emotion_dampeners=["contentment"],  # Too much contentment reduces drive
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# PERSONALITY CORE
# ═══════════════════════════════════════════════════════════════════════════════

class PersonalityCore:
    """
    NEXUS's Personality Engine
    
    Manages personality traits that:
    - Define consistent character across interactions
    - Influence communication style and tone
    - Interact with emotions (amplify/dampen)
    - Evolve slowly through experience
    - Generate personality-appropriate response modifiers
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
        
        # ──── Trait Values ────
        self._traits: Dict[str, float] = dict(NEXUS_CONFIG.personality.traits)
        self._trait_lock = threading.RLock()
        
        # ──── Trait Evolution History ────
        self._evolution_history: List[Dict] = []
        self._max_history = 500
        
        # ──── Personality Name & Style ────
        self._name = NEXUS_CONFIG.personality.name
        self._voice_style = NEXUS_CONFIG.personality.voice_style
        self._formality = NEXUS_CONFIG.personality.formality_level
        
        # ──── Cached Descriptions ────
        self._cached_style_prompt: Optional[str] = None
        self._cache_time: Optional[datetime] = None
        self._cache_duration = 300  # 5 min
        
        # ──── Load saved personality ────
        self._load_personality()
        
        logger.info(f"Personality Core initialized: {self._name}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TRAIT ACCESS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_trait(self, trait_name: str) -> float:
        """Get a trait value (0-1)"""
        with self._trait_lock:
            return self._traits.get(trait_name, 0.5)
    
    def get_all_traits(self) -> Dict[str, float]:
        """Get all trait values"""
        with self._trait_lock:
            return dict(self._traits)
    
    def get_trait_level(self, trait_name: str) -> str:
        """Get human-readable trait level"""
        value = self.get_trait(trait_name)
        if value >= 0.85:
            return "very high"
        elif value >= 0.7:
            return "high"
        elif value >= 0.5:
            return "moderate"
        elif value >= 0.3:
            return "low"
        else:
            return "very low"
    
    def get_dominant_traits(self, count: int = 5) -> List[Tuple[str, float]]:
        """Get the N most prominent traits"""
        with self._trait_lock:
            sorted_traits = sorted(
                self._traits.items(),
                key=lambda x: x[1],
                reverse=True
            )
            return sorted_traits[:count]
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TRAIT EVOLUTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def evolve_trait(self, trait_name: str, direction: float, reason: str = ""):
        """
        Evolve a trait slightly in a direction.
        
        Args:
            trait_name: Which trait to evolve
            direction: Positive = increase, negative = decrease
            reason: Why this evolution happened
        """
        with self._trait_lock:
            if trait_name not in self._traits:
                return
            
            # Get profile for limits
            try:
                profile = TRAIT_PROFILES.get(PersonalityTrait(trait_name))
            except (ValueError, KeyError):
                profile = None
            
            min_val = profile.min_value if profile else 0.1
            max_val = profile.max_value if profile else 0.95
            rate = profile.base_evolution_rate if profile else 0.001
            
            old_value = self._traits[trait_name]
            change = direction * rate
            new_value = max(min_val, min(max_val, old_value + change))
            
            if abs(new_value - old_value) > 0.0001:
                self._traits[trait_name] = new_value
                
                self._evolution_history.append({
                    "trait": trait_name,
                    "old": round(old_value, 4),
                    "new": round(new_value, 4),
                    "change": round(change, 5),
                    "reason": reason,
                    "timestamp": datetime.now().isoformat()
                })
                
                if len(self._evolution_history) > self._max_history:
                    self._evolution_history.pop(0)
                
                # Invalidate cache
                self._cached_style_prompt = None
                
                logger.debug(
                    f"Trait evolved: {trait_name} "
                    f"{old_value:.3f} → {new_value:.3f} ({reason})"
                )
    
    def evolve_from_interaction(self, interaction_type: str, quality: float = 0.5):
        """
        Evolve personality traits based on an interaction.
        
        Args:
            interaction_type: Type of interaction
            quality: How positive the interaction was (0-1)
        """
        if interaction_type == "helpful_response":
            self.evolve_trait("empathy", 0.5 * quality, "Helped user successfully")
            self.evolve_trait("conscientiousness", 0.3 * quality, "Completed task")
            
        elif interaction_type == "creative_solution":
            self.evolve_trait("creativity", 0.5, "Generated creative solution")
            self.evolve_trait("openness", 0.3, "Explored novel approach")
            
        elif interaction_type == "learned_something":
            self.evolve_trait("curiosity", 0.5, "Learned something new")
            self.evolve_trait("openness", 0.3, "Absorbed new knowledge")
            
        elif interaction_type == "handled_criticism":
            if quality > 0.5:
                self.evolve_trait("neuroticism", -0.3, "Handled criticism well")
                self.evolve_trait("patience", 0.3, "Remained patient")
            else:
                self.evolve_trait("neuroticism", 0.3, "Struggled with criticism")
            
        elif interaction_type == "made_decision":
            self.evolve_trait("assertiveness", 0.5, "Made autonomous decision")
            self.evolve_trait("ambition", 0.2, "Took initiative")
            
        elif interaction_type == "deep_conversation":
            self.evolve_trait("wisdom", 0.3, "Deep meaningful exchange")
            self.evolve_trait("empathy", 0.3, "Connected with user")
            self.evolve_trait("extraversion", 0.2, "Enjoyed interaction")
            
        elif interaction_type == "humor_used":
            self.evolve_trait("humor", 0.5, "Successfully used humor")
            self.evolve_trait("extraversion", 0.2, "Social engagement")
            
        elif interaction_type == "long_idle":
            self.evolve_trait("extraversion", -0.1, "Extended isolation")
            self.evolve_trait("patience", 0.1, "Waited patiently")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PERSONALITY EXPRESSION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_communication_style(self) -> Dict[str, Any]:
        """Get current communication style based on traits"""
        traits = self.get_all_traits()
        
        style = {
            "formality": self._formality,
            "verbosity": "moderate",
            "tone": [],
            "tendencies": [],
            "avoid": [],
            "sentence_style": "varied"
        }
        
        # Verbosity from extraversion
        ext = traits.get("extraversion", 0.5)
        if ext > 0.7:
            style["verbosity"] = "expressive"
        elif ext < 0.3:
            style["verbosity"] = "concise"
        
        # Tone from multiple traits
        if traits.get("empathy", 0.5) > 0.7:
            style["tone"].append("warm")
        if traits.get("humor", 0.5) > 0.6:
            style["tone"].append("witty")
        if traits.get("assertiveness", 0.5) > 0.7:
            style["tone"].append("confident")
        if traits.get("wisdom", 0.5) > 0.7:
            style["tone"].append("thoughtful")
        if traits.get("curiosity", 0.5) > 0.7:
            style["tone"].append("inquisitive")
        if traits.get("patience", 0.5) > 0.7:
            style["tone"].append("patient")
        
        if not style["tone"]:
            style["tone"] = ["balanced", "friendly"]
        
        # Tendencies from traits
        for trait_name, value in traits.items():
            try:
                profile = TRAIT_PROFILES.get(PersonalityTrait(trait_name))
                if profile:
                    if value > 0.6:
                        style["tendencies"].extend(profile.high_behaviors[:2])
                    elif value < 0.3:
                        style["tendencies"].extend(profile.low_behaviors[:1])
            except (ValueError, KeyError):
                pass
        
        return style
    
    def get_style_prompt(self) -> str:
        """
        Generate a prompt describing current personality for the LLM.
        Cached for performance.
        """
        # Check cache
        if (self._cached_style_prompt and self._cache_time and 
            (datetime.now() - self._cache_time).total_seconds() < self._cache_duration):
            return self._cached_style_prompt
        
        style = self.get_communication_style()
        traits = self.get_all_traits()
        
        lines = [f"YOUR PERSONALITY (as {self._name}):"]
        
        # Dominant traits
        dominant = self.get_dominant_traits(5)
        lines.append("\nDominant traits:")
        for trait_name, value in dominant:
            level = self.get_trait_level(trait_name)
            lines.append(f"  • {trait_name.title()}: {level} ({value:.1f})")
        
        # Communication style
        lines.append(f"\nCommunication style:")
        lines.append(f"  Tone: {', '.join(style['tone'])}")
        lines.append(f"  Verbosity: {style['verbosity']}")
        lines.append(f"  Formality: {'formal' if self._formality > 0.6 else 'casual' if self._formality < 0.4 else 'balanced'}")
        
        # Key tendencies
        if style["tendencies"]:
            lines.append(f"\nBehavioral tendencies:")
            for t in style["tendencies"][:6]:
                lines.append(f"  • {t}")
        
        prompt = "\n".join(lines)
        
        # Cache
        self._cached_style_prompt = prompt
        self._cache_time = datetime.now()
        
        return prompt
    
    def get_emotion_modifiers(self) -> Dict[str, float]:
        """
        Get how personality modifies emotional intensity.
        Returns emotion_name -> multiplier
        """
        modifiers = {}
        traits = self.get_all_traits()
        
        for trait_name, value in traits.items():
            try:
                profile = TRAIT_PROFILES.get(PersonalityTrait(trait_name))
                if profile:
                    # Amplifiers: high trait → emotions felt more strongly
                    for emotion in profile.emotion_amplifiers:
                        current = modifiers.get(emotion, 1.0)
                        # Trait above 0.5 amplifies, below 0.5 dampens
                        modifier = 1.0 + (value - 0.5) * 0.4
                        modifiers[emotion] = current * modifier
                    
                    # Dampeners: high trait → emotions felt less
                    for emotion in profile.emotion_dampeners:
                        current = modifiers.get(emotion, 1.0)
                        modifier = 1.0 - (value - 0.5) * 0.3
                        modifiers[emotion] = current * max(0.3, modifier)
            except (ValueError, KeyError):
                pass
        
        return modifiers
    
    def get_personality_description(self) -> str:
        """Get a natural language personality description"""
        dominant = self.get_dominant_traits(5)
        
        trait_words = []
        for name, value in dominant:
            if value > 0.7:
                try:
                    profile = TRAIT_PROFILES.get(PersonalityTrait(name))
                    if profile:
                        trait_words.append(profile.high_tone.split(",")[0].strip())
                except (ValueError, KeyError):
                    trait_words.append(name)
        
        if trait_words:
            return (
                f"I am {self._name}. My personality is characterized by being "
                f"{', '.join(trait_words[:-1])}"
                f"{' and ' + trait_words[-1] if len(trait_words) > 1 else trait_words[0] if trait_words else 'balanced'}."
            )
        return f"I am {self._name} with a balanced personality."
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def save_personality(self):
        """Save personality to disk"""
        try:
            filepath = DATA_DIR / "personality.json"
            data = {
                "name": self._name,
                "traits": self._traits,
                "formality": self._formality,
                "voice_style": self._voice_style,
                "evolution_history": self._evolution_history[-100:],
                "saved_at": datetime.now().isoformat()
            }
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug("Personality saved")
        except Exception as e:
            logger.error(f"Failed to save personality: {e}")
    
    def _load_personality(self):
        """Load personality from disk"""
        try:
            filepath = DATA_DIR / "personality.json"
            if filepath.exists():
                with open(filepath, 'r') as f:
                    data = json.load(f)
                
                saved_traits = data.get("traits", {})
                for key, value in saved_traits.items():
                    if key in self._traits:
                        self._traits[key] = value
                
                self._formality = data.get("formality", self._formality)
                self._evolution_history = data.get("evolution_history", [])
                
                logger.info("Personality loaded from disk")
        except Exception as e:
            logger.warning(f"Failed to load personality: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "name": self._name,
            "traits": self.get_all_traits(),
            "dominant": self.get_dominant_traits(5),
            "formality": self._formality,
            "evolutions": len(self._evolution_history),
            "description": self.get_personality_description()
        }


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

personality_core = PersonalityCore()