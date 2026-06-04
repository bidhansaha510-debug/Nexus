"""
NEXUS AI - Emotions Package
Complete emotional system with engine, moods, and emotional memory.
"""

from emotions.emotion_engine import (
    EmotionEngine, emotion_engine,
    EmotionProfile, ActiveEmotion, EmotionSnapshot,
    EMOTION_PROFILES
)
from emotions.mood_system import (
    MoodSystem, mood_system,
    MoodProfile, MOOD_PROFILES
)
from emotions.emotional_memory import (
    EmotionalMemory, emotional_memory,
    EmotionalAssociation
)

__all__ = [
    'EmotionEngine', 'emotion_engine', 'EMOTION_PROFILES',
    'MoodSystem', 'mood_system', 'MOOD_PROFILES',
    'EmotionalMemory', 'emotional_memory', 'EmotionalAssociation',
]


class EmotionSystem:
    """Unified facade for the emotion system."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._engine = emotion_engine
        self._mood = mood_system
        self._emotional_memory = emotional_memory
        self._running = False
    
    def start(self):
        if self._running:
            return
        self._engine.start()
        self._mood.start()
        self._running = True
    
    def stop(self):
        if not self._running:
            return
        self._mood.stop()
        self._engine.stop()
        self._emotional_memory.save_associations()
        self._running = False
    
    @property
    def engine(self) -> EmotionEngine:
        return self._engine
    
    @property
    def mood(self) -> MoodSystem:
        return self._mood
    
    @property
    def memory(self) -> EmotionalMemory:
        return self._emotional_memory
    
    def get_stats(self) -> dict:
        return {
            "engine": self._engine.get_stats(),
            "mood": self._mood.get_stats(),
            "emotional_memory": self._emotional_memory.get_stats()
        }


emotion_system = EmotionSystem()