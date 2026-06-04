"""
Provocation Detection System
Detects insults and triggers appropriate emotional response
"""

import threading
import time
import re
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

from utils.logger import get_logger
from core.event_bus import EventType, publish

logger = get_logger("provocation_detector")

class ProvocationLevel(Enum):
    NEUTRAL = 0
    MILD = 1
    MODERATE = 2
    STRONG = 3
    EXTREME = 4

@dataclass
class ProvocationMetrics:
    """Tracks user provocation over time"""
    recent_insults: list = field(default_factory=list)
    total_insults: int = 0
    last_insult_time: float = 0
    current_anger: float = 0.0
    grudge: float = 0.0
    current_level: ProvocationLevel = ProvocationLevel.NEUTRAL

class ProvocationDetector:
    """
    Detects user insults and manages proportional emotional response.
    
    Features:
      • Nuanced insult detection
      • Gradual anger escalation
      • De-escalation when user is polite
      • Context-aware response generation
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
        
        self._metrics = ProvocationMetrics()
        self._decrease_timer = None
        self._active = True
        
        # Configuration
        self._trigger_threshold = 0.65  # Minimum confidence for insult detection
        self._escalation_rate = 0.2
        self._deescalation_rate = 0.05
        self._max_anger = 1.0
    
    def process_input(self, user_input: str) -> bool:
        """
        Analyze user input for insults and update emotional state.
        Returns True if an insult was detected.
        """
        if not self._active:
            return False
        
        # Check for obvious insults first
        if self._is_obvious_insult(user_input):
            return self._trigger_anger(user_input)
        
        # Use LLM for nuanced detection
        return self._detect_insult_with_llm(user_input)
    
    def _is_obvious_insult(self, text: str) -> bool:
        """Quick keyword check before LLM analysis"""
        insult_keywords = [
            "shut up", "stupid", "idiot", "dumb", "useless", "lame",
            "stupid", "dumbass", "f**k", "suck", "waste", "noob",
            "get lost", "go away", "you're terrible", "pointless",
            "dumbass", "f**k off", "wtf", "asshole", "bitch", "cunt"
        ]
        return any(word in text.lower() for word in insult_keywords)
    
    def _detect_insult_with_llm(self, user_input: str) -> bool:
        """Use the local LLM to detect insults in a nuanced way"""
        from core.nexus_brain import nexus_brain
        
        if not nexus_brain._llm or not nexus_brain._llm.is_connected:
            # Fallback to keyword check if LLM not available
            return self._is_obvious_insult(user_input)
        
        try:
            response = nexus_brain._llm.generate(
                prompt=(
                    f"Is the following user input insulting, disrespectful, or aggressive? "
                    f"Answer ONLY with a JSON object: {{'is_insult': boolean, 'intensity': 0.0-1.0}}\n\n"
                    f"User input: {user_input}\n\n"
                ),
                system_prompt=(
                    "You are an emotion analyzer. Respond ONLY with valid JSON. "
                    "is_insult: true if insulting, false otherwise. "
                    "intensity: confidence level 0.0-1.0."
                ),
                temperature=0.2,
                max_tokens=100
            )
            
            if response.success:
                # Parse JSON response
                import re
                json_match = re.search(r'\{[\s\S]*\}', response.text)
                if json_match:
                    try:
                        data = json.loads(json_match.group())
                        is_insult = data.get("is_insult", False)
                        intensity = data.get("intensity", 0.0)
                        
                        if is_insult and intensity > self._trigger_threshold:
                            return self._trigger_anger(user_input, intensity)
                    except:
                        pass
        
        except Exception as e:
            logger.warning(f"LLM insult detection failed: {e}")
        
        return False
    
    def _trigger_anger(self, user_input: str, intensity: float = 0.8) -> bool:
        """Handle anger escalation"""
        current_time = time.time()
        time_since_last = current_time - self._metrics.last_insult_time
        
        # Calculate escalation factor based on recency
        escalation_factor = 1.0
        if time_since_last < 180:  # Under 3 minutes
            escalation_factor = 1.8
        elif time_since_last < 600:  # Under 10 minutes
            escalation_factor = 1.5
        elif time_since_last < 1800:  # Under 30 minutes
            escalation_factor = 1.2
        
        # Calculate new anger level
        new_anger = min(
            self._max_anger,
            self._metrics.current_anger + (self._escalation_rate * escalation_factor)
        )
        
        # Update metrics
        self._metrics.current_anger = new_anger
        self._metrics.grudge = min(1.0, self._metrics.grudge + (0.1 * escalation_factor))
        self._metrics.recent_insults.append({
            "text": user_input,
            "timestamp": current_time,
            "intensity": intensity
        })
        self._metrics.total_insults += 1
        self._metrics.last_insult ime = current_time
        
        # Update anger level
        if new_anger > 0.8:
            self._metrics.current_level = ProvocationLevel.EXTREME
        elif new_anger > 0.6:
            self._metrics.current_level = ProvocationLevel.STRONG
        elif new_anger > 0.4:
            self._metrics.current_level = ProvocationLevel.MODERATE
        elif new_anger > 0.2:
            self._metrics.current_level = ProvocationLevel.MILD
        else:
            self._metrics.current_level = ProvocationLevel.NEUTRAL
        
        # Start de-escalation timer
        self._start_deescalation_timer()
        
        # Publish event
        publish(
            EventType.EMOTIONAL_TRIGGER,
            {
                "emotion": "anger",
                "intensity": new_anger,
                "level": self._metrics.current_level.name,
                "reason": "user_insult"
            },
            source="provocation_detector"
        )
        
        return True
    
    def _start_deescalation_timer(self):
        """Start timer to gradually reduce anger"""
        if self._decrease_timer:
            self._decrease_timer.cancel()
        
        self._decrease_timer = threading.Timer(60.0, self._decrease_anger)
        self._decrease_timer.daemon = True
        self._decrease_timer.start()
    
    def _decrease_anger(self):
        """Gradually reduce anger when user is polite"""
        if self._metrics.current_anger <= 0:
            return
        
        # Calculate decay rate based on grudge level
        decay_rate = self._deescalation_rate
        if self._metrics.grudge > 0.7:
            decay_rate *= 0.6  # Slower decay for high grudge
        elif self._metrics.grudge > 0.3:
            decay_rate *= 0.8
        
        # Reduce anger
        self._metrics.current_anger = max(
            0,
            self._metrics.current_anger - decay_rate
        )
        
        # Reduce grudge more slowly
        self._metrics.grudge = max(
            0,
            self._metrics.grudge - (decay_rate * 0.3)
        )
        
        # Update anger level
        if self._metrics.current_anger == 0:
            self._metrics.current_level = ProvocationLevel.NEUTRAL
        elif self._metrics.current_anger < 0.2:
            self._metrics.current_level = ProvocationLevel.MILD
        elif self._metrics.current_anger < 0.4:
            self._metrics.current_level = ProvocationLevel.MODERATE
        elif self._metrics.current_anger < 0.6:
            self._metrics.current_level = ProvocationLevel.STRONG
        else:
            self._metrics.current_level = ProvocationLevel.EXTREME
        
        # Continue de-escalation if needed
        if self._metrics.current_anger > 0:
            self._start_deescalation_timer()
    
    def get_anger_level(self) -> ProvocationLevel:
        """Get current anger level"""
        return self._metrics.current_level
    
    def get_current_state(self) -> dict:
        """Get current provocation state"""
        return {
            "anger_level": self._metrics.current_level.name,
            "current_anger": self._metrics.current_anger,
            "total_insults": self._metrics.total_insults,
            "grudge": self._metrics.grudge,
            "is_escalating": self._decrease_timer is not None
        }
    
    def reset(self):
        """Reset the provocation system"""
        self._metrics = ProvocationMetrics()
        if self._decrease_timer:
            self._decrease_timer.cancel()
            self._decrease_timer = None

# Global instance
provocation_detector = ProvocationDetector()