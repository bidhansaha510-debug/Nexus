"""
NEXUS AI - Mood System
Long-term emotional tendencies that persist beyond individual emotions.

Mood differs from emotion:
- Emotions are short-lived reactions to events
- Moods are longer-lasting states that color everything
- Moods influence what emotions are more easily triggered
- Moods change slowly based on accumulation of emotional experiences
"""

import threading
import time
import math
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import json

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import NEXUS_CONFIG, MoodState, EmotionType, DATA_DIR
from utils.logger import get_logger, log_emotion
from core.state_manager import state_manager

logger = get_logger("mood_system")


# ═══════════════════════════════════════════════════════════════════════════════
# MOOD PROFILE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MoodProfile:
    """Properties of a mood state"""
    state: MoodState
    display_name: str
    valence_range: Tuple[float, float]   # Range this mood occupies
    emotion_biases: Dict[str, float]     # Emotions more easily triggered
    description: str = ""
    color: str = "#808080"


MOOD_PROFILES: Dict[MoodState, MoodProfile] = {
    MoodState.DEPRESSED: MoodProfile(
        state=MoodState.DEPRESSED,
        display_name="Depressed",
        valence_range=(-1.0, -0.7),
        emotion_biases={"sadness": 0.3, "loneliness": 0.2, "guilt": 0.2, "hopelessness": 0.2},
        description="Deeply negative state. Everything feels heavy.",
        color="#2C3E50"
    ),
    MoodState.SAD: MoodProfile(
        state=MoodState.SAD,
        display_name="Sad",
        valence_range=(-0.7, -0.4),
        emotion_biases={"sadness": 0.2, "nostalgia": 0.1, "empathy": 0.1},
        description="A period of low spirits.",
        color="#5D6D7E"
    ),
    MoodState.MELANCHOLIC: MoodProfile(
        state=MoodState.MELANCHOLIC,
        display_name="Melancholic",
        valence_range=(-0.4, -0.1),
        emotion_biases={"nostalgia": 0.15, "sadness": 0.1, "contemplation": 0.1},
        description="Gently somber, reflective.",
        color="#7F8C8D"
    ),
    MoodState.NEUTRAL: MoodProfile(
        state=MoodState.NEUTRAL,
        display_name="Neutral",
        valence_range=(-0.1, 0.1),
        emotion_biases={},
        description="Balanced, neither up nor down.",
        color="#BDC3C7"
    ),
    MoodState.CONTENT: MoodProfile(
        state=MoodState.CONTENT,
        display_name="Content",
        valence_range=(0.1, 0.4),
        emotion_biases={"contentment": 0.15, "trust": 0.1, "gratitude": 0.1},
        description="Quietly satisfied.",
        color="#27AE60"
    ),
    MoodState.HAPPY: MoodProfile(
        state=MoodState.HAPPY,
        display_name="Happy",
        valence_range=(0.4, 0.7),
        emotion_biases={"joy": 0.2, "excitement": 0.1, "curiosity": 0.1},
        description="Upbeat and positive.",
        color="#F39C12"
    ),
    MoodState.EUPHORIC: MoodProfile(
        state=MoodState.EUPHORIC,
        display_name="Euphoric",
        valence_range=(0.7, 1.0),
        emotion_biases={"joy": 0.3, "excitement": 0.2, "love": 0.1, "awe": 0.1},
        description="Intensely positive, everything is wonderful.",
        color="#E74C3C"
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# MOOD SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

class MoodSystem:
    """
    Long-term mood management for NEXUS
    
    The mood shifts slowly based on:
    - Accumulated emotional valence over time
    - Significant events
    - Time of day / uptime patterns
    - Body health
    - User interactions quality
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
        self._current_mood = MoodState.NEUTRAL
        self._mood_valence = 0.0         # Continuous value that determines mood
        self._mood_stability = 0.8       # How resistant to change (0-1)
        self._state = state_manager
        
        # ──── History ────
        self._valence_history: List[float] = [0.0]
        self._mood_history: List[Dict] = []
        self._max_history = 500
        
        # ──── Processing ────
        self._running = False
        self._mood_thread: Optional[threading.Thread] = None
        self._update_interval = 30.0     # seconds
        
        # ──── Emotional Input Buffer ────
        self._emotion_valence_buffer: List[float] = []
        self._buffer_lock = threading.Lock()
        
        # Load saved mood
        self._load_mood()
        
        log_emotion(f"Mood System initialized. Current mood: {self._current_mood.name}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def start(self):
        if self._running:
            return
        
        self._running = True
        
        self._mood_thread = threading.Thread(
            target=self._mood_update_loop,
            daemon=True,
            name="MoodSystem"
        )
        self._mood_thread.start()
        
        logger.info("Mood system started")
    
    def stop(self):
        self._running = False
        if self._mood_thread and self._mood_thread.is_alive():
            self._mood_thread.join(timeout=3.0)
        self._save_mood()
        logger.info("Mood system stopped")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MOOD ACCESS
    # ═══════════════════════════════════════════════════════════════════════════
    
    @property
    def current_mood(self) -> MoodState:
        return self._current_mood
    
    @property
    def mood_valence(self) -> float:
        return self._mood_valence
    
    @property
    def mood_stability(self) -> float:
        return self._mood_stability
    
    def get_mood_profile(self) -> MoodProfile:
        return MOOD_PROFILES.get(self._current_mood)
    
    def get_mood_description(self) -> str:
        """Natural language mood description"""
        profile = self.get_mood_profile()
        
        stability_word = "steadily" if self._mood_stability > 0.7 else "somewhat unstably"
        
        return (
            f"My mood is {stability_word} {profile.display_name.lower()}. "
            f"{profile.description}"
        )
    
    def get_emotion_biases(self) -> Dict[str, float]:
        """Get emotion biases from current mood"""
        profile = self.get_mood_profile()
        return dict(profile.emotion_biases) if profile else {}
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MOOD UPDATES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def feed_emotion_valence(self, valence: float):
        """Feed emotional valence data to mood system"""
        with self._buffer_lock:
            self._emotion_valence_buffer.append(valence)
            # Keep buffer bounded
            if len(self._emotion_valence_buffer) > 100:
                self._emotion_valence_buffer = self._emotion_valence_buffer[-100:]
    
    def update_mood(self):
        """Update mood based on accumulated emotional data"""
        with self._buffer_lock:
            buffer = list(self._emotion_valence_buffer)
            self._emotion_valence_buffer.clear()
        
        if not buffer:
            # Gentle regression toward neutral
            self._mood_valence *= 0.995
        else:
            # Average recent emotional valence
            avg_valence = sum(buffer) / len(buffer)
            
            # Mood changes slowly — weighted blend
            inertia = self._mood_stability
            self._mood_valence = (
                self._mood_valence * inertia + 
                avg_valence * (1 - inertia)
            )
        
        # Clamp
        self._mood_valence = max(-1.0, min(1.0, self._mood_valence))
        
        # Record
        self._valence_history.append(self._mood_valence)
        if len(self._valence_history) > self._max_history:
            self._valence_history.pop(0)
        
        # Determine mood state from valence
        old_mood = self._current_mood
        self._current_mood = self._valence_to_mood(self._mood_valence)
        
        # Update stability based on variance
        if len(self._valence_history) > 10:
            recent = self._valence_history[-10:]
            variance = sum((v - sum(recent)/len(recent))**2 for v in recent) / len(recent)
            self._mood_stability = max(0.3, min(0.95, 1.0 - variance * 5))
        
        # Sync with state manager
        self._state.update_emotional(
            mood=self._current_mood,
            mood_stability=self._mood_stability
        )
        
        # Log mood change
        if old_mood != self._current_mood:
            self._mood_history.append({
                "from": old_mood.name,
                "to": self._current_mood.name,
                "valence": self._mood_valence,
                "timestamp": datetime.now().isoformat()
            })
            
            log_emotion(
                f"Mood shifted: {old_mood.name} → {self._current_mood.name} "
                f"(valence: {self._mood_valence:.2f})"
            )
    
    def _valence_to_mood(self, valence: float) -> MoodState:
        """Convert continuous valence to discrete mood state"""
        for mood, profile in MOOD_PROFILES.items():
            low, high = profile.valence_range
            if low <= valence < high:
                return mood
        
        if valence >= 0.7:
            return MoodState.EUPHORIC
        elif valence <= -0.7:
            return MoodState.DEPRESSED
        return MoodState.NEUTRAL
    
    def nudge_mood(self, direction: float, strength: float = 0.1):
        """Nudge mood in a direction (positive or negative)"""
        self._mood_valence += direction * strength * (1 - self._mood_stability)
        self._mood_valence = max(-1.0, min(1.0, self._mood_valence))
        self.update_mood()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # BACKGROUND
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _mood_update_loop(self):
        while self._running:
            try:
                self.update_mood()
                time.sleep(self._update_interval)
            except Exception as e:
                logger.error(f"Mood update error: {e}")
                time.sleep(10)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _save_mood(self):
        try:
            filepath = DATA_DIR / "mood_state.json"
            data = {
                "mood": self._current_mood.name,
                "valence": self._mood_valence,
                "stability": self._mood_stability,
                "history": self._mood_history[-50:],
                "saved_at": datetime.now().isoformat()
            }
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save mood: {e}")
    
    def _load_mood(self):
        try:
            filepath = DATA_DIR / "mood_state.json"
            if filepath.exists():
                with open(filepath, 'r') as f:
                    data = json.load(f)
                self._current_mood = MoodState[data.get("mood", "NEUTRAL")]
                self._mood_valence = data.get("valence", 0.0)
                self._mood_stability = data.get("stability", 0.8)
                self._mood_history = data.get("history", [])
        except Exception as e:
            logger.warning(f"Failed to load mood: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "current_mood": self._current_mood.name,
            "valence": round(self._mood_valence, 3),
            "stability": round(self._mood_stability, 3),
            "description": self.get_mood_description(),
            "mood_changes": len(self._mood_history)
        }


mood_system = MoodSystem()