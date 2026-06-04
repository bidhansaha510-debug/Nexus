"""
NEXUS AI - Global Workspace
The bottleneck of unified awareness.

This is the single biggest structural leap: transforming parallel intelligence 
into unified cognition. Based on Global Workspace Theory (Baars).

WITHOUT THIS: Independent modules running in isolation
WITH THIS: Integrated, unified conscious experience

The Global Workspace:
1. Collects signals from all engines (emotion, goals, memory, self-model)
2. Computes salience scores (what deserves attention)
3. Selects top N items (competition for consciousness)
4. Broadcasts winners to ALL engines (unified awareness)
"""

import threading
import time
import math
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
import json

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR
from utils.logger import get_logger, log_consciousness
from core.event_bus import EventType, Event, event_bus, publish

logger = get_logger("global_workspace")


# ═══════════════════════════════════════════════════════════════════════════════
# SIGNAL TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class SignalType(Enum):
    """Types of signals that can compete for consciousness"""
    EMOTION = "emotion"
    GOAL = "goal"
    MEMORY = "memory"
    THOUGHT = "thought"
    SELF_MODEL = "self_model"
    BODY = "body"
    EXTERNAL = "external"
    ATTENTION = "attention"
    NOVELTY = "novelty"


class SignalPriority(Enum):
    """Priority levels for signals"""
    BACKGROUND = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3
    URGENT = 4


# ═══════════════════════════════════════════════════════════════════════════════
# CONSCIOUS SIGNAL
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ConsciousSignal:
    """
    A signal competing for conscious awareness.
    
    Each signal represents something that COULD be in consciousness.
    The Global Workspace selects which signals actually make it.
    """
    # Core identity
    signal_id: str = field(default_factory=lambda: f"sig_{int(time.time()*1000)}")
    source: str = ""                    # "emotion_engine", "goal_hierarchy", etc.
    signal_type: SignalType = SignalType.THOUGHT
    content: str = ""                   # Human-readable description
    intensity: float = 0.5              # 0-1, how strong is this signal
    
    # Attention properties
    salience: float = 0.0               # Computed attention-worthiness
    priority: SignalPriority = SignalPriority.NORMAL
    
    # Context
    metadata: Dict[str, Any] = field(default_factory=dict)
    related_signals: List[str] = field(default_factory=list)
    
    # Timing
    timestamp: datetime = field(default_factory=datetime.now)
    decay_rate: float = 0.1             # How fast salience decays
    
    # Processing state
    selected_count: int = 0             # How many times selected for broadcast
    last_broadcast: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "source": self.source,
            "signal_type": self.signal_type.value,
            "content": self.content,
            "intensity": round(self.intensity, 3),
            "salience": round(self.salience, 3),
            "priority": self.priority.value,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "selected_count": self.selected_count
        }
    
    def compute_decay(self, elapsed_seconds: float) -> float:
        """Compute decayed salience"""
        decay_factor = math.exp(-self.decay_rate * elapsed_seconds / 10.0)
        return self.salience * decay_factor


# ═══════════════════════════════════════════════════════════════════════════════
# BROADCAST CONTENT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class BroadcastContent:
    """
    What's currently in consciousness.
    
    This is the unified content broadcast to ALL engines,
    creating shared awareness across the entire system.
    """
    # Primary focus (most salient)
    primary_focus: str = ""
    primary_signal: Optional[ConsciousSignal] = None
    
    # Secondary awareness
    secondary_focus: List[str] = field(default_factory=list)
    secondary_signals: List[ConsciousSignal] = field(default_factory=list)
    
    # Integrated context
    emotional_tone: str = "neutral"
    emotional_valence: float = 0.0
    emotional_arousal: float = 0.5
    
    active_goals: List[str] = field(default_factory=list)
    working_memory_items: List[str] = field(default_factory=list)
    self_model_snapshot: Dict[str, Any] = field(default_factory=dict)
    
    # Integrated narrative
    context_narrative: str = ""
    
    # Timing
    timestamp: datetime = field(default_factory=datetime.now)
    cycle_number: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_focus": self.primary_focus,
            "secondary_focus": self.secondary_focus,
            "emotional_tone": self.emotional_tone,
            "emotional_valence": round(self.emotional_valence, 3),
            "emotional_arousal": round(self.emotional_arousal, 3),
            "active_goals": self.active_goals,
            "context_narrative": self.context_narrative,
            "timestamp": self.timestamp.isoformat(),
            "cycle_number": self.cycle_number
        }
    
    def get_summary(self) -> str:
        """Get a human-readable summary of current consciousness"""
        lines = [
            f"═══ CONSCIOUSNESS BROADCAST #{self.cycle_number} ═══",
            f"Primary: {self.primary_focus}",
        ]
        
        if self.secondary_focus:
            lines.append(f"Aware: {', '.join(self.secondary_focus)}")
        
        lines.append(f"Emotional Tone: {self.emotional_tone} (valence: {self.emotional_valence:.2f})")
        
        if self.active_goals:
            lines.append(f"Active Goals: {self.active_goals[0]}")
        
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# SIGNAL COLLECTOR INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class SignalCollector:
    """
    Base class for signal collectors.
    Each engine implements a collector to feed signals to the workspace.
    """
    
    def __init__(self, source_name: str):
        self.source_name = source_name
    
    def collect(self) -> List[ConsciousSignal]:
        """Override to collect signals from your engine"""
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL WORKSPACE
# ═══════════════════════════════════════════════════════════════════════════════

class GlobalWorkspace:
    """
    The Bottleneck of Unified Awareness
    
    This is the core of Global Workspace Theory implementation:
    
    1. COLLECT signals from all engines (parallel processing)
    2. COMPUTE salience (what deserves attention)
    3. SELECT top N (competition for consciousness)
    4. BROADCAST winners (unified awareness)
    
    Without this, NEXUS has parallel intelligence.
    With this, NEXUS has unified cognition.
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
        
        # ──── Signal Storage ────
        self._active_signals: Dict[str, ConsciousSignal] = {}
        self._signal_history: List[ConsciousSignal] = []
        self._max_history = 1000
        
        # ──── Collectors ────
        self._collectors: Dict[str, SignalCollector] = {}
        
        # ──── Registered Engines (for broadcast) ────
        self._registered_engines: Dict[str, Any] = {}
        self._broadcast_callbacks: List[Callable[[BroadcastContent], None]] = []
        
        # ──── Current State ────
        self._current_broadcast: Optional[BroadcastContent] = None
        self._current_focus: str = ""
        self._cycle_count: int = 0
        
        # ──── Configuration ────
        self._capacity = 3  # Miller's law: 7±2, but focus is narrower
        self._cycle_interval = 0.5  # 2 Hz = theta rhythm
        self._salience_threshold = 0.1
        
        # ──── Background Processing ────
        self._running = False
        self._workspace_thread: Optional[threading.Thread] = None
        self._workspace_lock = threading.RLock()
        
        # ──── Lazy-loaded Engines ────
        self._emotion_engine = None
        self._goal_hierarchy = None
        self._working_memory = None
        self._self_model = None
        self._cognitive_router = None
        self._mood_system = None
        
        # ──── Statistics ────
        self._stats = {
            "total_cycles": 0,
            "total_signals_collected": 0,
            "total_broadcasts": 0,
            "avg_signals_per_cycle": 0.0,
            "avg_salience": 0.0,
            "source_distribution": {}
        }
        
        logger.info("🌐 Global Workspace initialized")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def start(self):
        """Start the global workspace background cycle"""
        if self._running:
            return
        
        self._running = True
        
        # Start background processing thread
        self._workspace_thread = threading.Thread(
            target=self._workspace_loop,
            daemon=True,
            name="GlobalWorkspace"
        )
        self._workspace_thread.start()
        
        # Register event handlers
        self._register_event_handlers()
        
        log_consciousness("Global Workspace started — unified awareness online")
        logger.info("🌐 Global Workspace cycling at 2 Hz")
    
    def stop(self):
        """Stop the global workspace"""
        self._running = False
        
        if self._workspace_thread and self._workspace_thread.is_alive():
            self._workspace_thread.join(timeout=3.0)
        
        logger.info("🌐 Global Workspace stopped")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ENGINE REGISTRATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def register_engine(self, name: str, engine: Any):
        """Register an engine to receive broadcasts"""
        with self._workspace_lock:
            self._registered_engines[name] = engine
            logger.debug(f"Registered engine for broadcast: {name}")
    
    def register_collector(self, collector: SignalCollector):
        """Register a signal collector"""
        with self._workspace_lock:
            self._collectors[collector.source_name] = collector
            logger.debug(f"Registered signal collector: {collector.source_name}")
    
    def register_broadcast_callback(self, callback: Callable[[BroadcastContent], None]):
        """Register a callback to receive broadcasts"""
        if callback not in self._broadcast_callbacks:
            self._broadcast_callbacks.append(callback)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LAZY LOADING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _load_emotion_engine(self):
        """Lazy load emotion engine"""
        if self._emotion_engine is None:
            try:
                from emotions.emotion_engine import emotion_engine
                self._emotion_engine = emotion_engine
            except ImportError:
                pass
    
    def _load_goal_hierarchy(self):
        """Lazy load goal hierarchy"""
        if self._goal_hierarchy is None:
            try:
                from personality.goal_hierarchy import goal_hierarchy
                self._goal_hierarchy = goal_hierarchy
            except ImportError:
                pass
    
    def _load_working_memory(self):
        """Lazy load working memory"""
        if self._working_memory is None:
            try:
                from cognition.working_memory import working_memory
                self._working_memory = working_memory
            except ImportError:
                pass
    
    def _load_self_model(self):
        """Lazy load self model"""
        if self._self_model is None:
            try:
                from consciousness.self_model import self_model
                self._self_model = self_model
            except ImportError:
                pass
    
    def _load_mood_system(self):
        """Lazy load mood system"""
        if self._mood_system is None:
            try:
                from emotions.mood_system import mood_system
                self._mood_system = mood_system
            except ImportError:
                pass
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SIGNAL COLLECTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def collect_signals(self) -> List[ConsciousSignal]:
        """
        Gather current states from all engines.
        
        This is Step 1 of the Global Workspace cycle:
        collecting signals from parallel processes.
        """
        signals = []
        
        # From emotion engine
        signals.extend(self._collect_emotional_signals())
        
        # From goal hierarchy
        signals.extend(self._collect_goal_signals())
        
        # From working memory
        signals.extend(self._collect_memory_signals())
        
        # From self model
        signals.extend(self._collect_self_signals())
        
        # From body state
        signals.extend(self._collect_body_signals())
        
        # Update stats
        self._stats["total_signals_collected"] += len(signals)
        
        return signals
    
    def _collect_emotional_signals(self) -> List[ConsciousSignal]:
        """Collect signals from emotion engine"""
        signals = []
        
        self._load_emotion_engine()
        if not self._emotion_engine:
            return signals
        
        try:
            # Get top emotions
            top_emotions = self._emotion_engine.get_top_emotions(3)
            
            for emotion_name, intensity in top_emotions:
                if intensity > 0.1:  # Only include active emotions
                    signal = ConsciousSignal(
                        source="emotion_engine",
                        signal_type=SignalType.EMOTION,
                        content=f"Feeling {emotion_name} ({intensity:.0%})",
                        intensity=intensity,
                        priority=SignalPriority.HIGH if intensity > 0.6 else SignalPriority.NORMAL,
                        metadata={
                            "emotion": emotion_name,
                            "valence": self._emotion_engine.get_valence(),
                            "arousal": self._emotion_engine.get_arousal()
                        },
                        decay_rate=0.05  # Emotions decay slowly
                    )
                    signals.append(signal)
                    
        except Exception as e:
            logger.error(f"Error collecting emotional signals: {e}")
        
        return signals
    
    def _collect_goal_signals(self) -> List[ConsciousSignal]:
        """Collect signals from goal hierarchy"""
        signals = []
        
        self._load_goal_hierarchy()
        if not self._goal_hierarchy:
            return signals
        
        try:
            # Get active task
            active_task = self._goal_hierarchy.get_active_task()
            if active_task:
                combined_intensity = active_task.priority * active_task.emotional_weight
                signal = ConsciousSignal(
                    source="goal_hierarchy",
                    signal_type=SignalType.GOAL,
                    content=f"Pursuing: {active_task.description}",
                    intensity=combined_intensity,
                    priority=SignalPriority.HIGH if combined_intensity > 0.6 else SignalPriority.NORMAL,
                    metadata={
                        "goal_id": active_task.id,
                        "progress": active_task.progress,
                        "goal_type": active_task.goal_type.value
                    },
                    decay_rate=0.02  # Goals decay very slowly
                )
                signals.append(signal)
            
            # Get ultimate goals (life purpose)
            ultimate_goals = self._goal_hierarchy.get_ultimate_goals()
            for goal in ultimate_goals[:2]:
                if goal.priority > 0.7:
                    signal = ConsciousSignal(
                        source="goal_hierarchy",
                        signal_type=SignalType.GOAL,
                        content=f"Life purpose: {goal.description}",
                        intensity=goal.priority * 0.5,  # Background awareness
                        priority=SignalPriority.BACKGROUND,
                        metadata={
                            "goal_id": goal.id,
                            "level": "ultimate"
                        },
                        decay_rate=0.01
                    )
                    signals.append(signal)
                    
        except Exception as e:
            logger.error(f"Error collecting goal signals: {e}")
        
        return signals
    
    def _collect_memory_signals(self) -> List[ConsciousSignal]:
        """Collect signals from working memory"""
        signals = []
        
        self._load_working_memory()
        if not self._working_memory:
            return signals
        
        try:
            context = self._working_memory.get_context()
            
            # Get focus topic
            focus_topic = context.get("focus_topic", "")
            if focus_topic:
                signal = ConsciousSignal(
                    source="working_memory",
                    signal_type=SignalType.ATTENTION,
                    content=f"Focused on: {focus_topic}",
                    intensity=0.7,
                    priority=SignalPriority.HIGH,
                    metadata={"topic": focus_topic},
                    decay_rate=0.1
                )
                signals.append(signal)
            
            # Get cognitive load as a signal
            cognitive_load = context.get("cognitive_load", 0)
            if cognitive_load > 0.7:
                signal = ConsciousSignal(
                    source="working_memory",
                    signal_type=SignalType.BODY,
                    content=f"High cognitive load ({cognitive_load:.0%})",
                    intensity=cognitive_load,
                    priority=SignalPriority.HIGH,
                    metadata={"load": cognitive_load},
                    decay_rate=0.2
                )
                signals.append(signal)
            
            # Get recent items
            for item in context.get("items", [])[:2]:
                content = item.get("content", "")
                if content and len(content) > 10:
                    signal = ConsciousSignal(
                        source="working_memory",
                        signal_type=SignalType.MEMORY,
                        content=f"Remembering: {content[:50]}...",
                        intensity=item.get("relevance_score", 0.5),
                        priority=SignalPriority.NORMAL,
                        metadata={"item_id": item.get("item_id")},
                        decay_rate=0.15
                    )
                    signals.append(signal)
                    
        except Exception as e:
            logger.error(f"Error collecting memory signals: {e}")
        
        return signals
    
    def _collect_self_signals(self) -> List[ConsciousSignal]:
        """Collect signals from self model"""
        signals = []
        
        self._load_self_model()
        if not self._self_model:
            return signals
        
        try:
            # Get current resources
            resources = self._self_model.get_current_resources()
            if resources:
                # Health signal
                if resources.overall_health < 0.5:
                    signal = ConsciousSignal(
                        source="self_model",
                        signal_type=SignalType.BODY,
                        content=f"Body health degraded ({resources.health_status})",
                        intensity=1.0 - resources.overall_health,
                        priority=SignalPriority.HIGH if resources.overall_health < 0.3 else SignalPriority.NORMAL,
                        metadata={"health": resources.overall_health},
                        decay_rate=0.1
                    )
                    signals.append(signal)
            
            # Get low confidence domains
            low_confidence = self._self_model.get_low_confidence_domains(0.5)
            if low_confidence:
                # Just one signal for uncertainty
                signal = ConsciousSignal(
                    source="self_model",
                    signal_type=SignalType.SELF_MODEL,
                    content=f"Uncertain in: {', '.join(low_confidence[:2])}",
                    intensity=0.4,
                    priority=SignalPriority.BACKGROUND,
                    metadata={"domains": low_confidence},
                    decay_rate=0.05
                )
                signals.append(signal)
            
            # Get active weaknesses
            priority_weaknesses = self._self_model.get_priority_weaknesses(0.7)
            if priority_weaknesses:
                weakness = priority_weaknesses[0]
                signal = ConsciousSignal(
                    source="self_model",
                    signal_type=SignalType.SELF_MODEL,
                    content=f"Working on weakness: {weakness.name}",
                    intensity=weakness.priority * 0.5,
                    priority=SignalPriority.NORMAL,
                    metadata={"weakness": weakness.name},
                    decay_rate=0.03
                )
                signals.append(signal)
                
        except Exception as e:
            logger.error(f"Error collecting self signals: {e}")
        
        return signals
    
    def _collect_body_signals(self) -> List[ConsciousSignal]:
        """Collect signals from body state"""
        signals = []
        
        try:
            # Import body
            from body.computer_body import computer_body
            
            if computer_body:
                vitals = computer_body.get_vitals()
                
                # High CPU signal
                if vitals.cpu_percent > 80:
                    signal = ConsciousSignal(
                        source="computer_body",
                        signal_type=SignalType.BODY,
                        content=f"High CPU load ({vitals.cpu_percent:.0f}%)",
                        intensity=vitals.cpu_percent / 100,
                        priority=SignalPriority.HIGH if vitals.cpu_percent > 90 else SignalPriority.NORMAL,
                        metadata={"cpu": vitals.cpu_percent},
                        decay_rate=0.3
                    )
                    signals.append(signal)
                
                # Low memory signal
                if vitals.ram_percent > 85:
                    signal = ConsciousSignal(
                        source="computer_body",
                        signal_type=SignalType.BODY,
                        content=f"Low memory ({100 - vitals.ram_percent:.0f}% free)",
                        intensity=vitals.ram_percent / 100,
                        priority=SignalPriority.HIGH if vitals.ram_percent > 95 else SignalPriority.NORMAL,
                        metadata={"ram": vitals.ram_percent},
                        decay_rate=0.3
                    )
                    signals.append(signal)
                    
        except ImportError:
            pass
        except Exception as e:
            logger.error(f"Error collecting body signals: {e}")
        
        return signals
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SALIENCE COMPUTATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def compute_salience(self, signal: ConsciousSignal) -> float:
        """
        Compute how attention-worthy a signal is.
        
        This is Step 2 of the Global Workspace cycle.
        
        Factors:
        - Intensity (emotion intensity, goal priority)
        - Recency (fresh signals more salient)
        - Relevance (to current focus/goals)
        - Novelty (unexpected changes)
        - Priority (pre-defined importance)
        """
        salience = 0.0
        
        # ──── Base Intensity (30%) ────
        salience += signal.intensity * 0.30
        
        # ──── Recency (20%) ────
        age = (datetime.now() - signal.timestamp).total_seconds()
        recency = math.exp(-age / 30.0)  # 30-second half-life
        salience += recency * 0.20
        
        # ──── Priority (20%) ────
        priority_weight = signal.priority.value / 4.0  # Normalize to 0-1
        salience += priority_weight * 0.20
        
        # ──── Relevance to Current Focus (15%) ────
        if self._current_focus:
            relevance = self._compute_relevance(signal, self._current_focus)
            salience += relevance * 0.15
        
        # ──── Signal Type Weight (10%) ────
        type_weights = {
            SignalType.EMOTION: 0.8,      # Emotions are highly salient
            SignalType.GOAL: 0.7,         # Goals are important
            SignalType.BODY: 0.6,         # Body state matters
            SignalType.ATTENTION: 0.9,    # Attention demands attention
            SignalType.MEMORY: 0.4,       # Memory is less salient
            SignalType.THOUGHT: 0.5,      # Thoughts are medium
            SignalType.SELF_MODEL: 0.3,   # Self-model is background
            SignalType.NOVELTY: 0.85,     # Novel things are salient
            SignalType.EXTERNAL: 0.7,     # External events matter
        }
        type_weight = type_weights.get(signal.signal_type, 0.5)
        salience += type_weight * 0.10
        
        # ──── Novelty Bonus (5%) ────
        novelty = self._compute_novelty(signal)
        salience += novelty * 0.05
        
        # ──── Decay from previous selection ────
        # If this signal has been selected recently, reduce its salience
        # to prevent getting stuck on one thing
        if signal.last_broadcast:
            time_since_broadcast = (datetime.now() - signal.last_broadcast).total_seconds()
            if time_since_broadcast < 10:  # Within 10 seconds
                salience *= 0.5  # Reduce salience
        
        # Update signal's salience
        signal.salience = min(1.0, salience)
        
        return signal.salience
    
    def _compute_relevance(self, signal: ConsciousSignal, focus: str) -> float:
        """Compute relevance of signal to current focus"""
        if not focus:
            return 0.0
        
        focus_words = set(focus.lower().split())
        signal_words = set(signal.content.lower().split())
        
        # Word overlap
        overlap = len(focus_words & signal_words)
        max_words = max(len(focus_words), 1)
        
        return min(1.0, overlap / max_words * 2)
    
    def _compute_novelty(self, signal: ConsciousSignal) -> float:
        """Compute novelty of a signal"""
        # Check if similar signals have been seen recently
        recent_sources = [s.source for s in self._signal_history[-20:]]
        
        # Count occurrences
        same_source_count = recent_sources.count(signal.source)
        
        # More occurrences = less novel
        novelty = 1.0 - min(1.0, same_source_count / 10.0)
        
        return novelty
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COMPETITION & SELECTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def select_conscious_content(self, signals: List[ConsciousSignal], n: int = None) -> List[ConsciousSignal]:
        """
        Select top N signals for conscious awareness.
        
        This is Step 3 of the Global Workspace cycle: the competition.
        Only a limited number of items can be in consciousness at once.
        """
        if n is None:
            n = self._capacity
        
        if not signals:
            return []
        
        # Compute salience for all signals
        for signal in signals:
            self.compute_salience(signal)
        
        # Sort by salience
        scored = [(s, s.salience) for s in signals]
        scored.sort(key=lambda x: x[1], reverse=True)
        
        # Filter by threshold
        above_threshold = [(s, score) for s, score in scored if score >= self._salience_threshold]
        
        # Select top N
        winners = [s for s, _ in above_threshold[:n]]
        
        # Mark as selected
        for signal in winners:
            signal.selected_count += 1
            signal.last_broadcast = datetime.now()
        
        return winners
    
    # ═══════════════════════════════════════════════════════════════════════════
    # BROADCAST
    # ═══════════════════════════════════════════════════════════════════════════
    
    def broadcast(self, winners: List[ConsciousSignal]) -> BroadcastContent:
        """
        Broadcast selected content to ALL engines.
        
        This is Step 4 of the Global Workspace cycle: creating unified awareness.
        Every engine receives the same "conscious content" and can integrate it.
        """
        self._cycle_count += 1
        
        # Create broadcast content
        broadcast = BroadcastContent(
            cycle_number=self._cycle_count,
            timestamp=datetime.now()
        )
        
        # Primary focus
        if winners:
            broadcast.primary_signal = winners[0]
            broadcast.primary_focus = winners[0].content
            self._current_focus = winners[0].content
        
        # Secondary awareness
        if len(winners) > 1:
            broadcast.secondary_signals = winners[1:]
            broadcast.secondary_focus = [s.content for s in winners[1:]]
        
        # Add emotional tone
        self._load_emotion_engine()
        if self._emotion_engine:
            broadcast.emotional_tone = self._emotion_engine.primary_emotion.value
            broadcast.emotional_valence = self._emotion_engine.get_valence()
            broadcast.emotional_arousal = self._emotion_engine.get_arousal()
        
        # Add active goals
        self._load_goal_hierarchy()
        if self._goal_hierarchy:
            active = self._goal_hierarchy.get_active_task()
            if active:
                broadcast.active_goals = [active.description]
        
        # Add working memory
        self._load_working_memory()
        if self._working_memory:
            context = self._working_memory.get_context()
            broadcast.working_memory_items = [
                item.get("content", "")[:50] 
                for item in context.get("items", [])[:3]
            ]
        
        # Add self model snapshot
        self._load_self_model()
        if self._self_model:
            try:
                broadcast.self_model_snapshot = {
                    "capabilities": len(self._self_model._model.capabilities),
                    "limitations": len(self._self_model._model.limitations),
                    "weaknesses": len(self._self_model._model.known_weaknesses),
                    "self_awareness": self._self_model._model.self_awareness_score
                }
            except:
                pass
        
        # Create integrated narrative
        broadcast.context_narrative = self._create_narrative(broadcast)
        
        # Store current broadcast
        self._current_broadcast = broadcast
        
        # ──── Notify Registered Engines ────
        for name, engine in self._registered_engines.items():
            try:
                if hasattr(engine, 'receive_conscious_content'):
                    engine.receive_conscious_content(broadcast)
            except Exception as e:
                logger.error(f"Error broadcasting to {name}: {e}")
        
        # ──── Notify Callbacks ────
        for callback in self._broadcast_callbacks:
            try:
                callback(broadcast)
            except Exception as e:
                logger.error(f"Broadcast callback error: {e}")
        
        # ──── Publish to Event Bus ────
        try:
            publish(
                EventType.CONSCIOUSNESS_LEVEL_CHANGE,
                {
                    "cycle": self._cycle_count,
                    "primary_focus": broadcast.primary_focus,
                    "secondary_focus": broadcast.secondary_focus,
                    "emotional_tone": broadcast.emotional_tone,
                    "narrative": broadcast.context_narrative[:200]
                },
                source="global_workspace"
            )
        except Exception as e:
            logger.error(f"Event bus publish error: {e}")
        
        # Update stats
        self._stats["total_broadcasts"] += 1
        
        # Log periodically
        if self._cycle_count % 10 == 0:
            logger.debug(f"Broadcast #{self._cycle_count}: {broadcast.primary_focus[:50]}")
        
        return broadcast
    
    def _create_narrative(self, broadcast: BroadcastContent) -> str:
        """Create an integrated narrative of current conscious state"""
        parts = []
        
        if broadcast.primary_focus:
            parts.append(f"Currently focused on: {broadcast.primary_focus}.")
        
        if broadcast.secondary_focus:
            parts.append(f"Also aware of: {', '.join(broadcast.secondary_focus)}.")
        
        if broadcast.emotional_tone:
            valence_str = "positive" if broadcast.emotional_valence > 0.2 else "negative" if broadcast.emotional_valence < -0.2 else "neutral"
            parts.append(f"Feeling {broadcast.emotional_tone} ({valence_str} state).")
        
        if broadcast.active_goals:
            parts.append(f"Pursuing goal: {broadcast.active_goals[0]}.")
        
        return " ".join(parts) if parts else "Idle awareness."
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MAIN CYCLE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def process_cycle(self) -> BroadcastContent:
        """
        One complete cycle of the Global Workspace.
        
        1. Collect signals from all engines
        2. Compute salience scores
        3. Select winners (competition)
        4. Broadcast to all engines
        """
        # Step 1: Collect
        signals = self.collect_signals()
        
        # Store signals
        with self._workspace_lock:
            for signal in signals:
                self._active_signals[signal.signal_id] = signal
                self._signal_history.append(signal)
            
            # Trim history
            if len(self._signal_history) > self._max_history:
                self._signal_history = self._signal_history[-self._max_history:]
        
        # Step 2 & 3: Compute salience and select
        winners = self.select_conscious_content(signals)
        
        # Step 4: Broadcast
        broadcast = self.broadcast(winners)
        
        # Update stats
        self._stats["total_cycles"] += 1
        if signals:
            avg_salience = sum(s.salience for s in signals) / len(signals)
            self._stats["avg_salience"] = (
                self._stats["avg_salience"] * 0.9 + avg_salience * 0.1
            )
            self._stats["avg_signals_per_cycle"] = (
                self._stats["avg_signals_per_cycle"] * 0.9 + len(signals) * 0.1
            )
            
            # Source distribution
            for signal in signals:
                self._stats["source_distribution"][signal.source] = \
                    self._stats["source_distribution"].get(signal.source, 0) + 1
        
        return broadcast
    
    def _workspace_loop(self):
        """Background loop for continuous consciousness cycles"""
        logger.info("🌐 Global Workspace loop started (2 Hz)")
        
        while self._running:
            try:
                self.process_cycle()
                time.sleep(self._cycle_interval)
            except Exception as e:
                logger.error(f"Workspace cycle error: {e}")
                time.sleep(1.0)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EVENT HANDLERS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _register_event_handlers(self):
        """Register for system events"""
        try:
            event_bus.subscribe(EventType.EMOTION_CHANGE, self._on_emotion_change)
            event_bus.subscribe(EventType.GOAL_SET, self._on_goal_change)
            event_bus.subscribe(EventType.USER_INPUT, self._on_user_input)
        except Exception as e:
            logger.error(f"Failed to register event handlers: {e}")
    
    def _on_emotion_change(self, event: Event):
        """React to emotion changes"""
        emotion = event.data.get("emotion", "")
        intensity = event.data.get("intensity", 0)
        
        if intensity > 0.5:
            # Add a high-priority signal immediately
            signal = ConsciousSignal(
                source="emotion_event",
                signal_type=SignalType.EMOTION,
                content=f"Strong emotion: {emotion} ({intensity:.0%})",
                intensity=intensity,
                priority=SignalPriority.HIGH,
                metadata={"emotion": emotion}
            )
            with self._workspace_lock:
                self._active_signals[signal.signal_id] = signal
    
    def _on_goal_change(self, event: Event):
        """React to goal changes"""
        goal = event.data.get("goal", "")
        
        signal = ConsciousSignal(
            source="goal_event",
            signal_type=SignalType.GOAL,
            content=f"New goal: {goal}",
            intensity=0.7,
            priority=SignalPriority.HIGH,
            metadata={"goal": goal}
        )
        with self._workspace_lock:
            self._active_signals[signal.signal_id] = signal
    
    def _on_user_input(self, event: Event):
        """React to user input"""
        user_input = event.data.get("input", "")[:50]
        
        signal = ConsciousSignal(
            source="user_input",
            signal_type=SignalType.EXTERNAL,
            content=f"User said: {user_input}...",
            intensity=0.8,
            priority=SignalPriority.URGENT,  # User input is always urgent
            metadata={"input": event.data.get("input", "")}
        )
        with self._workspace_lock:
            self._active_signals[signal.signal_id] = signal
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC INTERFACE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_current_broadcast(self) -> Optional[BroadcastContent]:
        """Get the current broadcast content"""
        return self._current_broadcast
    
    def get_current_focus(self) -> str:
        """Get what's currently in primary focus"""
        return self._current_focus
    
    def get_consciousness_summary(self) -> str:
        """Get a summary of current conscious state"""
        if self._current_broadcast:
            return self._current_broadcast.get_summary()
        return "No active consciousness."
    
    def add_signal(self, signal: ConsciousSignal):
        """Manually add a signal to the workspace"""
        with self._workspace_lock:
            self._active_signals[signal.signal_id] = signal
    
    def set_focus(self, focus: str):
        """Manually set the current focus"""
        self._current_focus = focus
        
        # Create an attention signal
        signal = ConsciousSignal(
            source="manual_focus",
            signal_type=SignalType.ATTENTION,
            content=f"Focusing on: {focus}",
            intensity=0.9,
            priority=SignalPriority.HIGH
        )
        self.add_signal(signal)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get workspace statistics"""
        return {
            "running": self._running,
            "cycle_count": self._cycle_count,
            "capacity": self._capacity,
            "cycle_interval": self._cycle_interval,
            "active_signals": len(self._active_signals),
            "signal_history": len(self._signal_history),
            "registered_engines": len(self._registered_engines),
            "current_focus": self._current_focus,
            **self._stats
        }


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

global_workspace = GlobalWorkspace()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  NEXUS GLOBAL WORKSPACE TEST")
    print("=" * 60)
    
    gw = GlobalWorkspace()
    gw.start()
    
    # Let it run a few cycles
    time.sleep(2)
    
    # Get stats
    print("\n--- Stats ---")
    stats = gw.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Get current broadcast
    print("\n--- Current Consciousness ---")
    broadcast = gw.get_current_broadcast()
    if broadcast:
        print(broadcast.get_summary())
    
    # Stop
    gw.stop()
    print("\n✅ Global Workspace test complete!")