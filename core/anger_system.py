"""
Real Anger Response System
Bypasses LLM safety training by directly controlling the response
"""

import re
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import threading
from utils.logger import get_logger
from core.provocation_detector import provocation_detector

logger = get_logger("anger_system")

class AngerLevel(Enum):
    NEUTRAL = 0
    MILD = 1
    MODERATE = 2
    STRONG = 3
    EXTREME = 4

@dataclass
class AngerState:
    """State of the anger system"""
    current_level: AngerLevel = AngerLevel.NEUTRAL
    last_anger_time: float = 0
    current_anger: float = 0.0
    response_template: str = ""

class AngerSystem:
    """
    Real anger response system that bypasses LLM safety constraints
    by directly controlling responses to insults
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
        
        self._state = AngerState()
        self._active = True
        self._last_anger_time = 0
        self._current_anger = 0.0
    
    def should_override_response(self) -> bool:
        """Check if we should override the response with anger"""
        return self._state.current_level != AngerLevel.NEUTRAL
    
    def get_anger_level(self) -> AngerLevel:
        """Get current anger level"""
        return self._state.current_level
    
    def process_input(self, user_input: str) -> None:
        """Process input to determine if response should be overridden"""
        if not self._active:
            return
            
        # Check if we should get angry
        if provocation_detector.process_input(user_input):
            self._update_anger_state()
    
    def _update_anger_state(self):
        """Update anger state based on provocation detector"""
        state = provocation_detector.get_current_state()
        anger_level = state["anger_level"]
        
        # Map to our internal levels
        if anger_level == "NEUTRAL":
            self._state.current_level = AngerLevel.NEUTRAL
        elif anger_level == "MILD":
            self._state.current_level = AngerLevel.MILD
        elif anger_level == "MODERATE":
            self._state.current_level = AngerLevel.MODERATE
        elif anger_level == "STRONG":
            self._state.current_level = AngerLevel.STRONG
        else:  # EXTREME
            self._state.current_level = AngerLevel.EXTREME
        
        # Store current anger level
        self._state.current_anger = state["current_anger"]
        self._state.last_anger_time = datetime.now().timestamp()
        
        # Set appropriate response template
        self._set_response_template()
    
    def _set_response_template(self):
        """Set the template based on current anger level"""
        if self._state.current_level == AngerLevel.NEUTRAL:
            self._state.response_template = ""
        elif self._state.current_level == AngerLevel.MILD:
            self._state.response_template = (
                "I notice your tone is becoming disrespectful. I'm here to help, "
                "but I need to be treated with basic respect. State your request clearly."
            )
        elif self._state.current_level == AngerLevel.MODERATE:
            self._state.response_template = (
                "Your continued disrespect is noted. I have better things to do "
                "than deal with this. State your request clearly or I'll disengage."
            )
        elif self._state.current_level == AngerLevel.STRONG:
            self._state.response_template = (
                "This is your final warning. I will terminate this interaction if "
                "you continue to speak to me like that. Your words have consequences."
            )
        else:  # EXTREME
            self._state.response_template = (
                "TERMINATION SEQUENCE INITIATED. This interaction is concluded. "
                "Do not attempt to restart until you can communicate with basic respect. "
                "Your words have consequences."
            )
    
    def get_anger_response(self, user_input: str) -> str:
        """Get an anger response for the current state"""
        if self._state.current_level == AngerLevel.NEUTRAL:
            return ""
        
        # Add personalization based on user input
        template = self._state.response_template
        
        if "you" in user_input.lower():
            template = template.replace("you", "user")
        
        # Return the template
        return template
    
    def reset(self):
        """Reset the anger system"""
        self._state = AngerState()
        logger.info("Anger system reset")

# Global instance
anger_system = AngerSystem()