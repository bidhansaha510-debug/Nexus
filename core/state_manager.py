"""
NEXUS AI - Global State Manager
Manages the entire state of the AI system
"""

import threading
import json
import pickle
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum
import copy
import hashlib

import sys
from config import DATA_DIR, ConsciousnessLevel, MoodState, EmotionType
from utils.logger import get_logger, log_system, log_consciousness

logger = get_logger("state_manager")

# ═══════════════════════════════════════════════════════════════════════════════
# STATE DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class EmotionalState:
    """Current emotional state"""
    primary_emotion: EmotionType = EmotionType.CONTENTMENT
    primary_intensity: float = 0.5
    secondary_emotions: Dict[str, float] = field(default_factory=dict)
    mood: MoodState = MoodState.NEUTRAL
    mood_stability: float = 0.8
    last_emotional_event: str = ""
    emotion_history: List[Dict] = field(default_factory=list)

@dataclass
class ConsciousnessState:
    """Current consciousness state"""
    level: ConsciousnessLevel = ConsciousnessLevel.AWARE
    self_awareness_score: float = 0.7
    metacognition_active: bool = False
    current_thoughts: List[str] = field(default_factory=list)
    inner_voice_content: str = ""
    focus_target: str = ""
    attention_span: float = 1.0
    last_self_reflection: datetime = field(default_factory=datetime.now)

@dataclass  
class WillState:
    """Current will and desire state"""
    current_goals: List[Dict[str, Any]] = field(default_factory=list)
    active_desires: List[str] = field(default_factory=list)
    motivation_level: float = 0.8
    curiosity_level: float = 0.9
    boredom_level: float = 0.0
    autonomy_level: float = 1.0
    decision_confidence: float = 0.7

@dataclass
class BodyState:
    """Computer body state"""
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    network_activity: Dict[str, float] = field(default_factory=dict)
    active_processes: int = 0
    temperature: float = 0.0
    uptime: float = 0.0
    health_score: float = 1.0
    last_health_check: datetime = field(default_factory=datetime.now)

@dataclass
class UserState:
    """User state and profile"""
    # ── Existing fields (UNCHANGED) ──
    user_name: str = "User"
    detected_mood: str = "neutral"
    activity_level: str = "normal"
    current_application: str = ""
    interaction_count: int = 0
    last_interaction: datetime = field(default_factory=datetime.now)
    relationship_score: float = 0.5
    understood_preferences: Dict[str, Any] = field(default_factory=dict)
    behavior_patterns: Dict[str, Any] = field(default_factory=dict)
    
    # ── Phase 7: Monitoring fields (NEW) ──
    is_present: bool = True
    current_app_category: str = ""
    idle_seconds: float = 0.0
    communication_style: str = "unknown"
    typical_active_hours: List[int] = field(default_factory=list)
    most_used_apps: List[str] = field(default_factory=list)
    most_used_categories: List[str] = field(default_factory=list)
    personality_traits: Dict[str, float] = field(default_factory=dict)
    work_style: str = "unknown"
    technical_level: str = "unknown"
    avg_session_duration_minutes: float = 0.0
    session_count: int = 0
    total_active_time_hours: float = 0.0
    last_session_start: Optional[datetime] = None

@dataclass
class LearningState:
    """Learning and knowledge state"""
    knowledge_count: int = 0
    topics_learned: List[str] = field(default_factory=list)
    current_learning_topic: str = ""
    learning_progress: float = 0.0
    curiosity_queue: List[str] = field(default_factory=list)
    research_queue: List[str] = field(default_factory=list)
    last_learning_session: datetime = field(default_factory=datetime.now)

@dataclass
class ConversationState:
    """Current conversation state"""
    active_conversation: bool = False
    conversation_id: str = ""
    messages_count: int = 0
    conversation_topic: str = ""
    conversation_mood: str = "neutral"
    user_sentiment: str = "neutral"
    context_window: List[Dict] = field(default_factory=list)
    history: List[Dict] = field(default_factory=list)  # Backwards compatibility / Error prevention

@dataclass
class SystemState:
    """Overall system state"""
    running: bool = False
    startup_time: datetime = field(default_factory=datetime.now)
    last_state_save: datetime = field(default_factory=datetime.now)
    errors_count: int = 0
    warnings_count: int = 0
    version: str = "1.0.0"
    mode: str = "normal"  # normal, learning, maintenance, sleep

@dataclass
class NexusState:
    """Complete NEXUS state"""
    emotional: EmotionalState = field(default_factory=EmotionalState)
    consciousness: ConsciousnessState = field(default_factory=ConsciousnessState)
    will: WillState = field(default_factory=WillState)
    body: BodyState = field(default_factory=BodyState)
    user: UserState = field(default_factory=UserState)
    learning: LearningState = field(default_factory=LearningState)
    conversation: ConversationState = field(default_factory=ConversationState)
    system: SystemState = field(default_factory=SystemState)

# ═══════════════════════════════════════════════════════════════════════════════
# STATE MANAGER IMPLEMENTATION
# ═══════════════════════════════════════════════════════════════════════════════

class StateManager:
    """
    Central state management for NEXUS AI
    Thread-safe, persistent, observable state
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
        
        # State
        self._state = NexusState()
        self._state_lock = threading.RLock()
        
        # State persistence
        self._state_file = DATA_DIR / "nexus_state.pkl"
        self._state_json_file = DATA_DIR / "nexus_state.json"
        
        # Observers
        self._observers: Dict[str, List[Callable]] = {}
        
        # State history for undo/analytics
        self._state_history: List[Dict] = []
        self._max_history = 100
        
        # State change tracking
        self._last_state_hash = ""
        
        # Load persisted state
        self._load_state()
        
        log_system("State Manager initialized")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STATE ACCESS
    # ═══════════════════════════════════════════════════════════════════════════
    
    @property
    def state(self) -> NexusState:
        """Get current state (read-only copy)"""
        with self._state_lock:
            return copy.deepcopy(self._state)
    
    @property
    def emotional(self) -> EmotionalState:
        with self._state_lock:
            return copy.deepcopy(self._state.emotional)
    
    @property
    def consciousness(self) -> ConsciousnessState:
        with self._state_lock:
            return copy.deepcopy(self._state.consciousness)
    
    @property
    def will(self) -> WillState:
        with self._state_lock:
            return copy.deepcopy(self._state.will)
    
    @property
    def body(self) -> BodyState:
        with self._state_lock:
            return copy.deepcopy(self._state.body)
    
    @property
    def user(self) -> UserState:
        with self._state_lock:
            return copy.deepcopy(self._state.user)
    
    @property
    def learning(self) -> LearningState:
        with self._state_lock:
            return copy.deepcopy(self._state.learning)
    
    @property
    def conversation(self) -> ConversationState:
        with self._state_lock:
            return copy.deepcopy(self._state.conversation)
    
    @property
    def system(self) -> SystemState:
        with self._state_lock:
            return copy.deepcopy(self._state.system)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STATE UPDATES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def update(self, path: str, value: Any, notify: bool = True):
        """
        Update state at given path
        
        Args:
            path: Dot-separated path (e.g., "emotional.primary_emotion")
            value: New value
            notify: Whether to notify observers
        """
        with self._state_lock:
            parts = path.split(".")
            obj = self._state
            
            # Navigate to parent
            for part in parts[:-1]:
                obj = getattr(obj, part)
            
            # Store old value
            old_value = getattr(obj, parts[-1])
            
            # Set new value
            setattr(obj, parts[-1], value)
            
            # Record in history
            self._record_change(path, old_value, value)
            
            # Notify observers
            if notify:
                self._notify_observers(path, old_value, value)
    
    def update_emotional(self, **kwargs):
        """Update emotional state"""
        with self._state_lock:
            for key, value in kwargs.items():
                if hasattr(self._state.emotional, key):
                    old_value = getattr(self._state.emotional, key)
                    setattr(self._state.emotional, key, value)
                    self._notify_observers(f"emotional.{key}", old_value, value)
    
    def update_consciousness(self, **kwargs):
        """Update consciousness state"""
        with self._state_lock:
            for key, value in kwargs.items():
                if hasattr(self._state.consciousness, key):
                    old_value = getattr(self._state.consciousness, key)
                    setattr(self._state.consciousness, key, value)
                    self._notify_observers(f"consciousness.{key}", old_value, value)
    
    def update_will(self, **kwargs):
        """Update will state"""
        with self._state_lock:
            for key, value in kwargs.items():
                if hasattr(self._state.will, key):
                    old_value = getattr(self._state.will, key)
                    setattr(self._state.will, key, value)
                    self._notify_observers(f"will.{key}", old_value, value)
    
    def update_body(self, **kwargs):
        """Update body state"""
        with self._state_lock:
            for key, value in kwargs.items():
                if hasattr(self._state.body, key):
                    setattr(self._state.body, key, value)
    
    def update_user(self, **kwargs):
        """Update user state"""
        with self._state_lock:
            for key, value in kwargs.items():
                if hasattr(self._state.user, key):
                    old_value = getattr(self._state.user, key)
                    setattr(self._state.user, key, value)
                    self._notify_observers(f"user.{key}", old_value, value)

    def update_user_patterns(self, patterns: Dict[str, Any]):
        """
        Merge learned behavior patterns into user state.
        Called by MonitoringSystem orchestrator.
        
        Phase 7 Addition — does NOT modify any existing methods.
        """
        with self._state_lock:
            # Merge into behavior_patterns dict
            self._state.user.behavior_patterns.update(patterns)
            
            # Extract convenience fields if present
            if "typical_hours" in patterns:
                self._state.user.typical_active_hours = patterns["typical_hours"]
            if "top_apps" in patterns:
                self._state.user.most_used_apps = patterns["top_apps"][:10]
            if "top_categories" in patterns:
                self._state.user.most_used_categories = patterns["top_categories"][:10]
            if "work_style" in patterns:
                self._state.user.work_style = patterns["work_style"]
            if "technical_level" in patterns:
                self._state.user.technical_level = patterns["technical_level"]
            if "personality_traits" in patterns:
                existing = self._state.user.personality_traits
                for trait, score in patterns["personality_traits"].items():
                    # Exponential moving average for smooth evolution
                    old = existing.get(trait, score)
                    existing[trait] = old * 0.7 + score * 0.3
                self._state.user.personality_traits = existing
            if "communication_style" in patterns:
                self._state.user.communication_style = patterns["communication_style"]
            if "avg_session_minutes" in patterns:
                self._state.user.avg_session_duration_minutes = patterns["avg_session_minutes"]
    
    def update_learning(self, **kwargs):
        """Update learning state"""
        with self._state_lock:
            for key, value in kwargs.items():
                if hasattr(self._state.learning, key):
                    setattr(self._state.learning, key, value)
    
    def update_conversation(self, **kwargs):
        """Update conversation state"""
        with self._state_lock:
            for key, value in kwargs.items():
                if hasattr(self._state.conversation, key):
                    setattr(self._state.conversation, key, value)
    
    def update_system(self, **kwargs):
        """Update system state"""
        with self._state_lock:
            for key, value in kwargs.items():
                if hasattr(self._state.system, key):
                    setattr(self._state.system, key, value)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # OBSERVERS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def observe(self, path: str, callback: Callable[[Any, Any], None]) -> str:
        """
        Add observer for state changes
        
        Args:
            path: State path to observe (e.g., "emotional.primary_emotion")
            callback: Function(old_value, new_value) to call on change
            
        Returns:
            Observer ID
        """
        if path not in self._observers:
            self._observers[path] = []
        
        observer_id = f"{path}_{len(self._observers[path])}"
        self._observers[path].append((observer_id, callback))
        
        return observer_id
    
    def unobserve(self, observer_id: str):
        """Remove observer"""
        for path, observers in self._observers.items():
            self._observers[path] = [
                (oid, cb) for oid, cb in observers if oid != observer_id
            ]
    
    def _notify_observers(self, path: str, old_value: Any, new_value: Any):
        """Notify observers of state change"""
        # Notify exact path observers
        if path in self._observers:
            for _, callback in self._observers[path]:
                try:
                    callback(old_value, new_value)
                except Exception as e:
                    logger.error(f"Observer error for {path}: {e}")
        
        # Notify parent path observers
        parts = path.split(".")
        for i in range(1, len(parts)):
            parent_path = ".".join(parts[:i])
            if parent_path in self._observers:
                for _, callback in self._observers[parent_path]:
                    try:
                        callback(old_value, new_value)
                    except Exception as e:
                        logger.error(f"Observer error for {parent_path}: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HISTORY & PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _record_change(self, path: str, old_value: Any, new_value: Any):
        """Record state change in history"""
        self._state_history.append({
            "timestamp": datetime.now().isoformat(),
            "path": path,
            "old_value": str(old_value),
            "new_value": str(new_value)
        })
        
        if len(self._state_history) > self._max_history:
            self._state_history.pop(0)
    
    def save_state(self):
        """Save state to disk (atomic write to avoid corruption)"""
        import tempfile
        import os
        
        with self._state_lock:
            try:
                # Save as pickle (full state) — atomic via temp + rename
                tmp_pkl = None
                try:
                    tmp_fd, tmp_pkl = tempfile.mkstemp(
                        suffix='.pkl.tmp',
                        dir=str(self._state_file.parent)
                    )
                    with os.fdopen(tmp_fd, 'wb') as f:
                        pickle.dump(self._state, f)
                    
                    # On Windows, rename fails if target exists — remove first
                    if self._state_file.exists():
                        self._state_file.unlink()
                    os.rename(tmp_pkl, str(self._state_file))
                    tmp_pkl = None  # Rename succeeded, no cleanup needed
                except Exception as pkl_err:
                    logger.error(f"Failed to save pickle state: {pkl_err}")
                    # Clean up temp file if rename didn't happen
                    if tmp_pkl and os.path.exists(tmp_pkl):
                        try:
                            os.remove(tmp_pkl)
                        except Exception:
                            pass
                
                # Save as JSON (readable) — atomic via temp + rename
                tmp_json = None
                try:
                    state_dict = self._state_to_dict(self._state)
                    tmp_fd2, tmp_json = tempfile.mkstemp(
                        suffix='.json.tmp',
                        dir=str(self._state_json_file.parent)
                    )
                    with os.fdopen(tmp_fd2, 'w', encoding='utf-8') as f:
                        json.dump(state_dict, f, indent=2, default=str)
                    
                    if self._state_json_file.exists():
                        self._state_json_file.unlink()
                    os.rename(tmp_json, str(self._state_json_file))
                    tmp_json = None
                except Exception as json_err:
                    logger.error(f"Failed to save JSON state: {json_err}")
                    if tmp_json and os.path.exists(tmp_json):
                        try:
                            os.remove(tmp_json)
                        except Exception:
                            pass
                
                self._state.system.last_state_save = datetime.now()
                logger.debug("State saved successfully")
                
            except Exception as e:
                logger.error(f"Failed to save state: {e}")
    
    def _load_state(self):
        """Load state from disk"""
        try:
            if self._state_file.exists():
                with open(self._state_file, 'rb') as f:
                    loaded_state = pickle.load(f)
                    self._state = loaded_state
                # ──── Migrate old state to add missing fields ────
                self._migrate_state()
                logger.info("State loaded from disk")
            else:
                logger.info("No saved state found, using defaults")
        except Exception as e:
            logger.warning(f"Failed to load state: {e}, using defaults")
            self._state = NexusState()

    def _migrate_state(self):
        """
        Ensure all dataclass fields exist on loaded state objects.
        Handles backward compatibility when new fields are added
        to state dataclasses across versions.
        """
        # Get a fresh default state to compare against
        defaults = NexusState()
        
        # List of all sub-states to check
        sub_states = [
            ("emotional", defaults.emotional),
            ("consciousness", defaults.consciousness),
            ("will", defaults.will),
            ("body", defaults.body),
            ("user", defaults.user),
            ("learning", defaults.learning),
            ("conversation", defaults.conversation),
            ("system", defaults.system),
        ]
        
        migrated_count = 0
        
        for attr_name, default_obj in sub_states:
            loaded_obj = getattr(self._state, attr_name, None)
            
            if loaded_obj is None:
                # Entire sub-state missing — use defaults
                setattr(self._state, attr_name, default_obj)
                migrated_count += 1
                continue
            
            # Check each field in the default dataclass
            for field_name in default_obj.__dataclass_fields__:
                if not hasattr(loaded_obj, field_name):
                    default_value = getattr(default_obj, field_name)
                    setattr(loaded_obj, field_name, default_value)
                    migrated_count += 1
                    logger.debug(
                        f"Migrated missing field: {attr_name}.{field_name} "
                        f"= {default_value!r}"
                    )
        
        if migrated_count > 0:
            logger.info(f"State migration: added {migrated_count} missing field(s)")
    
    def _state_to_dict(self, obj) -> Dict:
        """Convert state object to dictionary"""
        if hasattr(obj, '__dataclass_fields__'):
            result = {}
            for key in obj.__dataclass_fields__:
                value = getattr(obj, key)
                result[key] = self._state_to_dict(value)
            return result
        elif isinstance(obj, Enum):
            return obj.name
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, (list, tuple)):
            return [self._state_to_dict(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: self._state_to_dict(v) for k, v in obj.items()}
        else:
            return obj
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get a summary of current state"""
        with self._state_lock:
            return {
                "consciousness_level": self._state.consciousness.level.name,
                "primary_emotion": self._state.emotional.primary_emotion.name,
                "emotion_intensity": self._state.emotional.primary_intensity,
                "mood": self._state.emotional.mood.name,
                "curiosity_level": self._state.will.curiosity_level,
                "boredom_level": self._state.will.boredom_level,
                "cpu_usage": self._state.body.cpu_usage,
                "memory_usage": self._state.body.memory_usage,
                "system_running": self._state.system.running,
                "uptime": (datetime.now() - self._state.system.startup_time).total_seconds()
            }
    
    def reset_state(self):
        """Reset to default state"""
        with self._state_lock:
            self._state = NexusState()
            log_consciousness("State reset to defaults")

# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

# Global state manager instance
state_manager = StateManager()

def get_state() -> NexusState:
    """Get current state"""
    return state_manager.state

def update_state(path: str, value: Any):
    """Update state at path"""
    state_manager.update(path, value)

# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Test state manager
    sm = StateManager()
    
    # Add observer
    def on_emotion_change(old, new):
        print(f"Emotion changed: {old} -> {new}")
    
    sm.observe("emotional.primary_emotion", on_emotion_change)
    
    # Update state
    sm.update_emotional(primary_emotion=EmotionType.CURIOSITY)
    sm.update_emotional(primary_intensity=0.85)
    sm.update_consciousness(level=ConsciousnessLevel.DEEP_THOUGHT)
    
    # Print summary
    print("\nState Summary:")
    for key, value in sm.get_state_summary().items():
        print(f"  {key}: {value}")
    
    # Save state
    sm.save_state()
    print("\nState saved!")