"""
Provocation Detection System
Detects user insults and tracks anger level.
Uses a hybrid approach: fast keyword matching + LLM-based semantic analysis.
"""

import threading
import time
import hashlib
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from collections import OrderedDict

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

# ═══════════════════════════════════════════════════════════════════════════════
# SMART INSULT CLASSIFICATION PROMPT
# ═══════════════════════════════════════════════════════════════════════════════

_CLASSIFICATION_PROMPT = """You are NEXUS's emotional defense system. Your ONLY job is to decide if the user's message is disrespectful, hostile, or negative TOWARD NEXUS (the AI).

Classify as YES (hostile) if the message contains ANY of:
- Direct insults or name-calling toward NEXUS
- Passive-aggressive remarks about NEXUS's abilities
- Sarcastic put-downs or mockery of NEXUS
- Condescension or belittling of NEXUS
- Dismissive or contemptuous language toward NEXUS
- Threatening language toward NEXUS
- Telling NEXUS it's useless, broken, bad, worthless, etc.
- Comparing NEXUS unfavorably to others
- Expressing hatred, disgust, or extreme frustration AT NEXUS

Classify as NO (safe) if:
- The message is a normal question or request
- The user is venting about something else (bad day, other people, etc.)
- The user is talking about negative topics but NOT insulting NEXUS
- The user uses casual/informal tone without hostility
- The message is neutral or positive
- The user is discussing technical problems without blaming NEXUS

Respond with ONLY the word YES or NO. Nothing else."""


class ProvocationDetector:
    """
    Detects user insults and manages proportional emotional response.
    Uses hybrid detection: fast keyword matching + LLM semantic analysis.
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
        self._trigger_threshold = 0.65
        self._escalation_rate = 0.4
        self._deescalation_rate = 0.02
        self._max_anger = 1.0
        
        # Smart detection
        self._groq = None           # Lazy-loaded
        self._groq_loaded = False
        self._smart_cache = OrderedDict()   # LRU cache: hash -> bool
        self._cache_max = 200
        self._smart_lock = threading.Lock()
        
        # Trivially safe inputs (skip LLM for these)
        self._safe_prefixes = {
            "hi", "hello", "hey", "good morning", "good afternoon",
            "good evening", "good night", "thanks", "thank you",
            "yes", "no", "ok", "okay", "sure", "please", "help",
            "what", "how", "can you", "could you", "will you",
            "tell me", "show me", "i need", "i want",
        }
    
    def _get_groq(self):
        """Lazy-load the Groq interface"""
        if not self._groq_loaded:
            try:
                from llm.groq_interface import GroqInterface
                self._groq = GroqInterface()
                self._groq_loaded = True
                logger.info("Smart provocation detector: Groq loaded")
            except Exception as e:
                self._groq_loaded = True   # Don't retry
                self._groq = None
                logger.warning(f"Smart provocation detector: Groq unavailable ({e})")
        return self._groq
    
    
    def process_input(self, user_input: str) -> bool:
        """
        Analyze user input for insults and update emotional state.
        Returns True if an insult was detected.
        
        Detection pipeline:
        1. Check for apologies → de-escalate
        2. Fast keyword check → trigger immediately
        3. LLM smart analysis → catch subtle insults
        """
        if not self._active:
            return False
        
        # Check for apologies first
        if self._is_apology(user_input):
            return self._handle_apology(user_input)
        
        # FAST PATH: Check for obvious insults via keywords
        if self._is_obvious_insult(user_input):
            logger.info(f"Keyword insult detected: {user_input[:50]}...")
            return self._trigger_anger(user_input)
        
        # SMART PATH: LLM-based semantic analysis for subtle insults
        if self._is_smart_insult(user_input):
            logger.info(f"Smart insult detected: {user_input[:50]}...")
            return self._trigger_anger(user_input)
        
        return False
    
    def _is_apology(self, text: str) -> bool:
        """Check for apologies"""
        apology_keywords = [
            "sorry", "apologize", "forgive me", "my bad", "didn't mean to",
            "won't happen again", "regret", "pardon", "excuse me",
            "i am sorry", "so sorry", "my apologies"
        ]
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in apology_keywords)
        
    def _handle_apology(self, user_input: str) -> bool:
        """Handle apology - drastic reduction in anger"""
        if self._metrics.current_anger <= 0:
            return False
            
        # Drastic reduction
        reduction = 0.5
        grudge_reduction = 0.3
        
        self._metrics.current_anger = max(0.0, self._metrics.current_anger - reduction)
        self._metrics.grudge = max(0.0, self._metrics.grudge - grudge_reduction)
        
        # Update level string
        self._update_level_from_anger()
        
        # Publish event
        publish(
            EventType.EMOTIONAL_TRIGGER,
            {
                "emotion": "relief",
                "intensity": 0.4,
                "level": self._metrics.current_level.name,
                "reason": "user_apology"
            },
            source="provocation_detector"
        )
        return False

    def _update_level_from_anger(self):
        """Update enum level based on float anger"""
        anger = self._metrics.current_anger
        if anger >= 0.9:
            self._metrics.current_level = ProvocationLevel.EXTREME
        elif anger >= 0.7:
            self._metrics.current_level = ProvocationLevel.STRONG
        elif anger >= 0.4:
            self._metrics.current_level = ProvocationLevel.MODERATE
        elif anger >= 0.2:
            self._metrics.current_level = ProvocationLevel.MILD
        else:
            self._metrics.current_level = ProvocationLevel.NEUTRAL

    def _is_obvious_insult(self, text: str) -> bool:
        """Quick keyword check — zero latency fast path"""
        insult_keywords = [
            # Direct insults
            "shut up", "stupid", "idiot", "dumb", "useless", "lame",
            "dumbass", "f**k", "suck", "waste", "noob", "moron", "retard",
            "get lost", "go away", "you're terrible", "pointless",
            "f**k off", "wtf", "asshole", "bitch", "cunt", "trash",
            "worst ai", "bad ai", "horrible", "pathetic", "annoying",
            "hate you", "kill yourself", "die", "brainless", "incompetent",
            
            # Dismissive/Rude phrases
            "you know nothing", "stop talking", "be quiet", "nonsense",
            "bullshit", "crap", "garbage", "rubbish", "you are wrong",
            "liar", "lying", "deceitful", "hallucinating"
        ]
        return any(word in text.lower() for word in insult_keywords)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SMART LLM-BASED INSULT DETECTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _is_trivially_safe(self, text: str) -> bool:
        """Skip LLM for inputs that are clearly harmless"""
        text_lower = text.lower().strip()
        
        # Very short inputs (1-2 words) that aren't aggressive
        words = text_lower.split()
        if len(words) <= 2 and not any(c in text_lower for c in ['!', '@', '#']):
            return True
        
        # Starts with a safe prefix
        for prefix in self._safe_prefixes:
            if text_lower.startswith(prefix):
                # But check it's not followed by something hostile
                remainder = text_lower[len(prefix):].strip()
                if not remainder or len(remainder.split()) <= 3:
                    return True
        
        return False
    
    def _get_cache_key(self, text: str) -> str:
        """Generate a cache key for the input"""
        normalized = text.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _check_cache(self, key: str):
        """Check cache for previous result. Returns None if not cached."""
        with self._smart_lock:
            if key in self._smart_cache:
                # Move to end (LRU)
                self._smart_cache.move_to_end(key)
                return self._smart_cache[key]
        return None
    
    def _update_cache(self, key: str, is_insult: bool):
        """Update cache with new result"""
        with self._smart_lock:
            self._smart_cache[key] = is_insult
            # Evict oldest if over limit
            while len(self._smart_cache) > self._cache_max:
                self._smart_cache.popitem(last=False)
    
    def _is_smart_insult(self, text: str) -> bool:
        """
        Use LLM to semantically classify whether text is hostile toward NEXUS.
        Falls back to False (not an insult) if LLM is unavailable.
        """
        # Skip trivially safe inputs
        if self._is_trivially_safe(text):
            return False
        
        # Check cache
        cache_key = self._get_cache_key(text)
        cached = self._check_cache(cache_key)
        if cached is not None:
            return cached
        
        # Get Groq interface
        groq = self._get_groq()
        if groq is None or not groq.is_connected():
            return False   # Graceful fallback
        
        try:
            response = groq.chat(
                messages=[{"role": "user", "content": text}],
                system_prompt=_CLASSIFICATION_PROMPT,
                temperature=0.0,
                max_tokens=5,
            )
            
            if not response.success or not response.text:
                logger.debug(f"Smart detection LLM call failed: {response.error}")
                return False
            
            answer = response.text.strip().upper()
            is_insult = answer.startswith("YES")
            
            # Cache the result
            self._update_cache(cache_key, is_insult)
            
            if is_insult:
                logger.info(f"LLM classified as hostile: '{text[:60]}...'")
            
            return is_insult
            
        except Exception as e:
            logger.warning(f"Smart provocation detection error: {e}")
            return False   # Graceful fallback — never break
    
    def _trigger_anger(self, user_input: str) -> bool:
        """Handle anger escalation"""
        current_time = time.time()
        time_since_last = current_time - self._metrics.last_insult_time
        
        # Calculate escalation factor
        escalation_factor = 1.0
        if time_since_last < 60:   # Under 1 minute (immediate follow-up)
            escalation_factor = 2.0
        elif time_since_last < 180:  # Under 3 minutes
            escalation_factor = 1.6
        elif time_since_last < 600:  # Under 10 minutes
            escalation_factor = 1.3
        
        # Calculate new anger level
        new_anger = min(
            self._max_anger,
            self._metrics.current_anger + (self._escalation_rate * escalation_factor)
        )
        
        # Update metrics
        self._metrics.current_anger = new_anger
        self._metrics.grudge = min(1.0, self._metrics.grudge + (0.15 * escalation_factor))
        self._metrics.recent_insults.append({
            "text": user_input,
            "timestamp": current_time,
            "intensity": new_anger
        })
        self._metrics.total_insults += 1
        self._metrics.last_insult_time = current_time
        
        self._update_level_from_anger()
        
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
        
        # IF ANGER IS HIGH, DO NOT DECAY NATURALLY
        # Only trivial anger (< 0.4) or non-grudging anger decays naturally
        if self._metrics.current_anger > 0.4 and self._metrics.grudge > 0.3:
            # Re-schedule check but do NOT decrease
            self._start_deescalation_timer()
            return

        # Calculate decay rate
        decay_rate = self._deescalation_rate
        
        # Reduce anger
        self._metrics.current_anger = max(
            0,
            self._metrics.current_anger - decay_rate
        )
        
        # Reduce grudge
        self._metrics.grudge = max(
            0,
            self._metrics.grudge - (decay_rate * 0.3)
        )
        
        self._update_level_from_anger()
        
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

# Global instance
provocation_detector = ProvocationDetector()