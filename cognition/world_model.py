"""
NEXUS AI - World Model Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A predictive model of the external environment:
- User reaction patterns (how users behave and respond)
- Emotional response patterns (what triggers emotional states)
- Resource consequence patterns (action → resource impact)
- Task success probability (historical outcome prediction)

"Without a world model, autonomy is blind."

This enables NEXUS to:
- ANTICIPATE rather than just react
- CHOOSE ACTIONS that lead to desired outcomes
- AVOID ACTIONS that cause negative reactions
- ALLOCATE RESOURCES based on predicted costs
- SET REALISTIC GOALS based on success probabilities
"""

import threading
import json
import uuid
import time
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum, auto
from collections import defaultdict
import statistics

import sys

from config import DATA_DIR

from utils.logger import get_logger, log_learning
from core.event_bus import event_bus, EventType, publish, subscribe

logger = get_logger("world_model")

# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class InteractionType(Enum):
    """Types of interactions with users"""
    GREETING = "greeting"
    QUESTION = "question"
    TASK_REQUEST = "task_request"
    CASUAL_CHAT = "casual_chat"
    EMOTIONAL_SUPPORT = "emotional_support"
    INFORMATION_SEEKING = "information_seeking"
    PROBLEM_SOLVING = "problem_solving"
    CREATIVE_COLLABORATION = "creative_collaboration"
    FEEDBACK = "feedback"
    CORRECTION = "correction"
    COMPLAINT = "complaint"
    PRAISE = "praise"
    COMMAND = "command"

class EmotionalOutcome(Enum):
    """Possible emotional outcomes from interactions"""
    POSITIVE_ENGAGED = "positive_engaged"
    SATISFIED = "satisfied"
    NEUTRAL = "neutral"
    SLIGHTLY_FRUSTRATED = "slightly_frustrated"
    FRUSTRATED = "frustrated"
    DISENGAGED = "disengaged"
    HAPPY = "happy"
    GRATEFUL = "grateful"
    CONFUSED = "confused"
    ANNOYED = "annoyed"
    TRUSTING = "trusting"

class TaskOutcome(Enum):
    """Possible task outcomes"""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    ABANDONED = "abandoned"
    ESCALATED = "escalated"
    RETRY_NEEDED = "retry_needed"

class ResourceImpact(Enum):
    """Resource impact levels"""
    NEGLIGIBLE = "negligible"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"

# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class UserReactionPattern:
    """
    Tracks how users respond to different interaction types.
    
    Records the typical reaction patterns for a specific interaction context,
    enabling prediction of future user behavior.
    """
    pattern_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    interaction_type: InteractionType = InteractionType.CASUAL_CHAT
    context_tags: List[str] = field(default_factory=list)  # e.g., "morning", "technical_topic"
    
    # Response metrics
    avg_response_time_seconds: float = 0.0
    response_time_samples: List[float] = field(default_factory=list)
    
    # Engagement metrics
    engagement_level: float = 0.5  # 0-1, how engaged the user typically is
    engagement_samples: List[float] = field(default_factory=list)
    
    # Outcome distribution
    typical_outcomes: Dict[str, float] = field(default_factory=dict)  # outcome -> frequency
    outcome_count: int = 0
    
    # Follow-up patterns
    follow_up_likelihood: float = 0.0  # How likely user is to continue
    topic_switch_likelihood: float = 0.0  # How likely user is to change topic
    
    # Timing patterns
    preferred_times: List[str] = field(default_factory=list)  # "morning", "evening", etc.
    session_duration_avg: float = 0.0
    
    # Metadata
    sample_count: int = 0
    first_observed: str = field(default_factory=lambda: datetime.now().isoformat())
    last_observed: str = field(default_factory=lambda: datetime.now().isoformat())
    confidence: float = 0.0  # How confident we are in this pattern
    
    def to_dict(self) -> Dict:
        return {
            "pattern_id": self.pattern_id,
            "interaction_type": self.interaction_type.value,
            "context_tags": self.context_tags,
            "avg_response_time_seconds": self.avg_response_time_seconds,
            "response_time_samples": self.response_time_samples[-50:],  # Keep last 50
            "engagement_level": self.engagement_level,
            "engagement_samples": self.engagement_samples[-50:],
            "typical_outcomes": self.typical_outcomes,
            "outcome_count": self.outcome_count,
            "follow_up_likelihood": self.follow_up_likelihood,
            "topic_switch_likelihood": self.topic_switch_likelihood,
            "preferred_times": self.preferred_times,
            "session_duration_avg": self.session_duration_avg,
            "sample_count": self.sample_count,
            "first_observed": self.first_observed,
            "last_observed": self.last_observed,
            "confidence": self.confidence
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'UserReactionPattern':
        return cls(
            pattern_id=data.get("pattern_id", str(uuid.uuid4())[:8]),
            interaction_type=InteractionType(data.get("interaction_type", "casual_chat")),
            context_tags=data.get("context_tags", []),
            avg_response_time_seconds=data.get("avg_response_time_seconds", 0.0),
            response_time_samples=data.get("response_time_samples", []),
            engagement_level=data.get("engagement_level", 0.5),
            engagement_samples=data.get("engagement_samples", []),
            typical_outcomes=data.get("typical_outcomes", {}),
            outcome_count=data.get("outcome_count", 0),
            follow_up_likelihood=data.get("follow_up_likelihood", 0.0),
            topic_switch_likelihood=data.get("topic_switch_likelihood", 0.0),
            preferred_times=data.get("preferred_times", []),
            session_duration_avg=data.get("session_duration_avg", 0.0),
            sample_count=data.get("sample_count", 0),
            first_observed=data.get("first_observed", datetime.now().isoformat()),
            last_observed=data.get("last_observed", datetime.now().isoformat()),
            confidence=data.get("confidence", 0.0)
        )
    
    def add_observation(self, response_time: float, engagement: float, outcome: str):
        """Add a new observation to this pattern"""
        self.response_time_samples.append(response_time)
        self.engagement_samples.append(engagement)
        
        # Update averages
        if self.response_time_samples:
            self.avg_response_time_seconds = statistics.mean(self.response_time_samples)
        if self.engagement_samples:
            self.engagement_level = statistics.mean(self.engagement_samples)
        
        # Update outcome distribution
        if outcome not in self.typical_outcomes:
            self.typical_outcomes[outcome] = 0.0
        self.typical_outcomes[outcome] += 1.0
        self.outcome_count += 1
        
        # Normalize outcomes
        if self.outcome_count > 0:
            for k in self.typical_outcomes:
                self.typical_outcomes[k] = self.typical_outcomes[k] / self.outcome_count * 100
        
        self.sample_count += 1
        self.last_observed = datetime.now().isoformat()
        
        # Update confidence based on sample count
        self.confidence = min(1.0, self.sample_count / 10.0)  # Max confidence at 10 samples

@dataclass
class EmotionalResponsePattern:
    """
    Maps triggers to emotional outcomes.
    
    Tracks what types of actions/statements lead to what emotional
    responses in users.
    """
    pattern_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    # Trigger
    trigger_type: str = ""  # "statement", "action", "tone", "topic"
    trigger_category: str = ""  # "empathy", "correction", "question", etc.
    trigger_content: str = ""  # Specific trigger description
    
    # Context
    pre_existing_emotion: str = "neutral"  # User's state before trigger
    
    # Outcome
    emotional_outcome: EmotionalOutcome = EmotionalOutcome.NEUTRAL
    outcome_intensity: float = 0.5  # 0-1
    outcome_duration_estimate: float = 0.0  # seconds
    
    # Tracking
    occurrence_count: int = 0
    consistency: float = 0.0  # How consistently this trigger produces this outcome
    
    # Metadata
    first_observed: str = field(default_factory=lambda: datetime.now().isoformat())
    last_observed: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            "pattern_id": self.pattern_id,
            "trigger_type": self.trigger_type,
            "trigger_category": self.trigger_category,
            "trigger_content": self.trigger_content,
            "pre_existing_emotion": self.pre_existing_emotion,
            "emotional_outcome": self.emotional_outcome.value,
            "outcome_intensity": self.outcome_intensity,
            "outcome_duration_estimate": self.outcome_duration_estimate,
            "occurrence_count": self.occurrence_count,
            "consistency": self.consistency,
            "first_observed": self.first_observed,
            "last_observed": self.last_observed
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'EmotionalResponsePattern':
        return cls(
            pattern_id=data.get("pattern_id", str(uuid.uuid4())[:8]),
            trigger_type=data.get("trigger_type", ""),
            trigger_category=data.get("trigger_category", ""),
            trigger_content=data.get("trigger_content", ""),
            pre_existing_emotion=data.get("pre_existing_emotion", "neutral"),
            emotional_outcome=EmotionalOutcome(data.get("emotional_outcome", "neutral")),
            outcome_intensity=data.get("outcome_intensity", 0.5),
            outcome_duration_estimate=data.get("outcome_duration_estimate", 0.0),
            occurrence_count=data.get("occurrence_count", 0),
            consistency=data.get("consistency", 0.0),
            first_observed=data.get("first_observed", datetime.now().isoformat()),
            last_observed=data.get("last_observed", datetime.now().isoformat())
        )

@dataclass
class ResourceConsequence:
    """
    Action → resource impact mapping.
    
    Tracks the resource consequences of different actions NEXUS takes.
    """
    consequence_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    # Action
    action_type: str = ""  # "llm_call", "file_write", "web_search", etc.
    action_category: str = ""  # "communication", "computation", "storage", "network"
    action_details: str = ""
    
    # Resource impact
    cpu_impact: float = 0.0  # Percentage change
    memory_impact: float = 0.0  # MB change
    time_cost_seconds: float = 0.0
    llm_tokens_used: int = 0
    
    # Impact level
    overall_impact: ResourceImpact = ResourceImpact.LOW
    
    # Side effects
    side_effects: List[str] = field(default_factory=list)
    recovery_time_seconds: float = 0.0  # Time for resources to normalize
    
    # Tracking
    occurrence_count: int = 0
    avg_cpu_impact: float = 0.0
    avg_memory_impact: float = 0.0
    avg_time_cost: float = 0.0
    
    # Metadata
    first_observed: str = field(default_factory=lambda: datetime.now().isoformat())
    last_observed: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            "consequence_id": self.consequence_id,
            "action_type": self.action_type,
            "action_category": self.action_category,
            "action_details": self.action_details,
            "cpu_impact": self.cpu_impact,
            "memory_impact": self.memory_impact,
            "time_cost_seconds": self.time_cost_seconds,
            "llm_tokens_used": self.llm_tokens_used,
            "overall_impact": self.overall_impact.value,
            "side_effects": self.side_effects,
            "recovery_time_seconds": self.recovery_time_seconds,
            "occurrence_count": self.occurrence_count,
            "avg_cpu_impact": self.avg_cpu_impact,
            "avg_memory_impact": self.avg_memory_impact,
            "avg_time_cost": self.avg_time_cost,
            "first_observed": self.first_observed,
            "last_observed": self.last_observed
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ResourceConsequence':
        return cls(
            consequence_id=data.get("consequence_id", str(uuid.uuid4())[:8]),
            action_type=data.get("action_type", ""),
            action_category=data.get("action_category", ""),
            action_details=data.get("action_details", ""),
            cpu_impact=data.get("cpu_impact", 0.0),
            memory_impact=data.get("memory_impact", 0.0),
            time_cost_seconds=data.get("time_cost_seconds", 0.0),
            llm_tokens_used=data.get("llm_tokens_used", 0),
            overall_impact=ResourceImpact(data.get("overall_impact", "low")),
            side_effects=data.get("side_effects", []),
            recovery_time_seconds=data.get("recovery_time_seconds", 0.0),
            occurrence_count=data.get("occurrence_count", 0),
            avg_cpu_impact=data.get("avg_cpu_impact", 0.0),
            avg_memory_impact=data.get("avg_memory_impact", 0.0),
            avg_time_cost=data.get("avg_time_cost", 0.0),
            first_observed=data.get("first_observed", datetime.now().isoformat()),
            last_observed=data.get("last_observed", datetime.now().isoformat())
        )
    
    def add_observation(self, cpu: float, memory: float, time_cost: float):
        """Add a new observation"""
        self.occurrence_count += 1
        n = self.occurrence_count
        
        # Running average
        self.avg_cpu_impact = self.avg_cpu_impact * (n-1)/n + cpu/n
        self.avg_memory_impact = self.avg_memory_impact * (n-1)/n + memory/n
        self.avg_time_cost = self.avg_time_cost * (n-1)/n + time_cost/n
        
        self.cpu_impact = self.avg_cpu_impact
        self.memory_impact = self.avg_memory_impact
        self.time_cost_seconds = self.avg_time_cost
        
        self.last_observed = datetime.now().isoformat()

@dataclass
class TaskSuccessRecord:
    """
    Historical task outcomes for probability estimation.
    
    Tracks the success/failure of different task types.
    """
    record_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    # Task
    task_type: str = ""  # "code_generation", "question_answering", "creative_writing", etc.
    task_category: str = ""  # "technical", "creative", "analytical", "social"
    task_description: str = ""
    complexity: float = 0.5  # 0-1, estimated complexity
    
    # Context
    user_id: str = ""
    session_context: str = ""
    resource_state: str = ""  # Resource state when task started
    
    # Outcome
    outcome: TaskOutcome = TaskOutcome.SUCCESS
    success_percentage: float = 0.0  # For partial success
    failure_reason: str = ""
    recovery_strategy: str = ""
    
    # Metrics
    time_taken_seconds: float = 0.0
    iterations_needed: int = 1
    user_satisfaction: float = 0.5  # 0-1, if available
    
    # Metadata
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            "record_id": self.record_id,
            "task_type": self.task_type,
            "task_category": self.task_category,
            "task_description": self.task_description,
            "complexity": self.complexity,
            "user_id": self.user_id,
            "session_context": self.session_context,
            "resource_state": self.resource_state,
            "outcome": self.outcome.value,
            "success_percentage": self.success_percentage,
            "failure_reason": self.failure_reason,
            "recovery_strategy": self.recovery_strategy,
            "time_taken_seconds": self.time_taken_seconds,
            "iterations_needed": self.iterations_needed,
            "user_satisfaction": self.user_satisfaction,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TaskSuccessRecord':
        return cls(
            record_id=data.get("record_id", str(uuid.uuid4())[:8]),
            task_type=data.get("task_type", ""),
            task_category=data.get("task_category", ""),
            task_description=data.get("task_description", ""),
            complexity=data.get("complexity", 0.5),
            user_id=data.get("user_id", ""),
            session_context=data.get("session_context", ""),
            resource_state=data.get("resource_state", ""),
            outcome=TaskOutcome(data.get("outcome", "success")),
            success_percentage=data.get("success_percentage", 0.0),
            failure_reason=data.get("failure_reason", ""),
            recovery_strategy=data.get("recovery_strategy", ""),
            time_taken_seconds=data.get("time_taken_seconds", 0.0),
            iterations_needed=data.get("iterations_needed", 1),
            user_satisfaction=data.get("user_satisfaction", 0.5),
            timestamp=data.get("timestamp", datetime.now().isoformat())
        )

@dataclass
class EnvironmentState:
    """
    Current model of the external world.
    
    A snapshot of what NEXUS understands about its environment.
    """
    # User state
    current_user_id: str = ""
    user_emotional_state: str = "neutral"
    user_engagement_level: float = 0.5
    user_session_duration: float = 0.0
    
    # Interaction state
    current_interaction_type: InteractionType = InteractionType.CASUAL_CHAT
    conversation_depth: int = 0
    topics_discussed: List[str] = field(default_factory=list)
    
    # System state (external)
    internet_available: bool = True
    llm_services_status: Dict[str, bool] = field(default_factory=dict)
    api_rate_limits: Dict[str, int] = field(default_factory=dict)
    
    # Temporal state
    time_of_day: str = "unknown"  # "morning", "afternoon", "evening", "night"
    day_of_week: str = "unknown"
    
    # Predictions
    predicted_next_user_action: str = ""
    predicted_session_continuation: float = 0.5
    
    # Metadata
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            "current_user_id": self.current_user_id,
            "user_emotional_state": self.user_emotional_state,
            "user_engagement_level": self.user_engagement_level,
            "user_session_duration": self.user_session_duration,
            "current_interaction_type": self.current_interaction_type.value,
            "conversation_depth": self.conversation_depth,
            "topics_discussed": self.topics_discussed,
            "internet_available": self.internet_available,
            "llm_services_status": self.llm_services_status,
            "api_rate_limits": self.api_rate_limits,
            "time_of_day": self.time_of_day,
            "day_of_week": self.day_of_week,
            "predicted_next_user_action": self.predicted_next_user_action,
            "predicted_session_continuation": self.predicted_session_continuation,
            "last_updated": self.last_updated
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'EnvironmentState':
        return cls(
            current_user_id=data.get("current_user_id", ""),
            user_emotional_state=data.get("user_emotional_state", "neutral"),
            user_engagement_level=data.get("user_engagement_level", 0.5),
            user_session_duration=data.get("user_session_duration", 0.0),
            current_interaction_type=InteractionType(data.get("current_interaction_type", "casual_chat")),
            conversation_depth=data.get("conversation_depth", 0),
            topics_discussed=data.get("topics_discussed", []),
            internet_available=data.get("internet_available", True),
            llm_services_status=data.get("llm_services_status", {}),
            api_rate_limits=data.get("api_rate_limits", {}),
            time_of_day=data.get("time_of_day", "unknown"),
            day_of_week=data.get("day_of_week", "unknown"),
            predicted_next_user_action=data.get("predicted_next_user_action", ""),
            predicted_session_continuation=data.get("predicted_session_continuation", 0.5),
            last_updated=data.get("last_updated", datetime.now().isoformat())
        )
    
    def update_time(self):
        """Update time-based state"""
        now = datetime.now()
        hour = now.hour
        
        if 5 <= hour < 12:
            self.time_of_day = "morning"
        elif 12 <= hour < 17:
            self.time_of_day = "afternoon"
        elif 17 <= hour < 21:
            self.time_of_day = "evening"
        else:
            self.time_of_day = "night"
        
        self.day_of_week = now.strftime("%A").lower()
        self.last_updated = now.isoformat()

# ═══════════════════════════════════════════════════════════════════════════════
# WORLD MODEL ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class WorldModel:
    """
    World Model Engine — Predictive Model of the External Environment
    
    This is NEXUS's "theory of the world" — understanding how the environment
    behaves, how users react, and what consequences actions have.
    
    Key Capabilities:
    - Track user reaction patterns
    - Track emotional response patterns
    - Track resource consequences
    - Estimate task success probability
    - Maintain current environment state
    - Predict outcomes of potential actions
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
        
        # ──── Pattern Storage ────
        self._user_patterns: Dict[str, UserReactionPattern] = {}
        self._emotional_patterns: Dict[str, EmotionalResponsePattern] = {}
        self._resource_consequences: Dict[str, ResourceConsequence] = {}
        self._task_records: Dict[str, TaskSuccessRecord] = {}
        
        # Indexes for fast lookup
        self._user_patterns_by_type: Dict[InteractionType, List[str]] = defaultdict(list)
        self._emotional_patterns_by_trigger: Dict[str, List[str]] = defaultdict(list)
        self._task_records_by_type: Dict[str, List[str]] = defaultdict(list)
        
        # Current environment state
        self._environment: EnvironmentState = EnvironmentState()
        
        # LLM for predictions
        self._llm = None
        
        # State
        self._running = False
        self._data_lock = threading.RLock()
        
        # Persistence
        self._data_dir = DATA_DIR / "cognition"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._data_file = self._data_dir / "world_model.json"
        
        # Statistics
        self._stats = {
            "user_observations": 0,
            "emotional_observations": 0,
            "resource_observations": 0,
            "task_observations": 0,
            "predictions_made": 0,
            "predictions_accurate": 0
        }
        
        # Load persisted data
        self._load_data()
        
        # Subscribe to events
        self._setup_event_handlers()
        
        logger.info(f"🌍 World Model initialized — {len(self._user_patterns)} user patterns, "
                   f"{len(self._emotional_patterns)} emotional patterns, "
                   f"{len(self._task_records)} task records")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def start(self):
        """Start the world model"""
        if self._running:
            return
        self._running = True
        self._load_llm()
        self._environment.update_time()
        logger.info("🌍 World Model started")
    
    def stop(self):
        """Stop the world model and save"""
        self._running = False
        self._save_data()
        logger.info("🌍 World Model stopped")
    
    def _load_llm(self):
        """Load LLM for predictions"""
        if self._llm is None:
            try:
                from llm.llama_interface import llm
                self._llm = llm
            except ImportError:
                logger.warning("LLM not available for world model predictions")
    
    def _setup_event_handlers(self):
        """Set up event bus subscriptions"""
        try:
            subscribe(EventType.USER_INPUT, self._on_user_input)
            subscribe(EventType.USER_ACTION_DETECTED, self._on_user_action)
            subscribe(EventType.EMOTION_CHANGE, self._on_emotion_change)
            subscribe(EventType.DECISION_MADE, self._on_decision_made)
            subscribe(EventType.GOAL_ACHIEVED, self._on_goal_outcome)
            logger.debug("World Model event handlers registered")
        except Exception as e:
            logger.warning(f"Could not set up event handlers: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # USER REACTION PATTERN TRACKING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def observe_user_reaction(
        self,
        interaction_type: InteractionType,
        response_time: float,
        engagement: float,
        outcome: str,
        context_tags: List[str] = None
    ) -> UserReactionPattern:
        """
        Observe and record a user reaction pattern.
        
        Args:
            interaction_type: Type of interaction
            response_time: Time for user to respond (seconds)
            engagement: Engagement level 0-1
            outcome: Outcome of the interaction
            context_tags: Additional context tags
        
        Returns:
            The created/updated pattern
        """
        with self._data_lock:
            # Find or create pattern
            pattern_key = f"{interaction_type.value}_{'_'.join(sorted(context_tags or []))}"
            
            if pattern_key not in self._user_patterns:
                pattern = UserReactionPattern(
                    interaction_type=interaction_type,
                    context_tags=context_tags or []
                )
                self._user_patterns[pattern_key] = pattern
                self._user_patterns_by_type[interaction_type].append(pattern_key)
            else:
                pattern = self._user_patterns[pattern_key]
            
            # Add observation
            pattern.add_observation(response_time, engagement, outcome)
            
            # Update stats
            self._stats["user_observations"] += 1
            
            # Save
            self._save_data()
            
            log_learning(f"User reaction observed: {interaction_type.value} → {outcome}")
            return pattern
    
    def predict_user_reaction(
        self,
        interaction_type: InteractionType,
        context_tags: List[str] = None
    ) -> Dict[str, Any]:
        """
        Predict how a user will react to an interaction.
        
        Returns predicted response time, engagement, and likely outcomes.
        """
        with self._data_lock:
            # Find matching patterns
            pattern_key = f"{interaction_type.value}_{'_'.join(sorted(context_tags or []))}"
            
            # Try exact match first
            if pattern_key in self._user_patterns:
                pattern = self._user_patterns[pattern_key]
            else:
                # Fall back to interaction type match
                matching_keys = self._user_patterns_by_type.get(interaction_type, [])
                if matching_keys:
                    # Use the most confident pattern
                    best_key = max(matching_keys, 
                                  key=lambda k: self._user_patterns[k].confidence)
                    pattern = self._user_patterns[best_key]
                else:
                    # No data - return defaults
                    return {
                        "predicted_response_time": 30.0,
                        "predicted_engagement": 0.5,
                        "likely_outcomes": {"neutral": 0.7},
                        "confidence": 0.0
                    }
            
            self._stats["predictions_made"] += 1
            
            return {
                "predicted_response_time": pattern.avg_response_time_seconds,
                "predicted_engagement": pattern.engagement_level,
                "likely_outcomes": pattern.typical_outcomes,
                "follow_up_likelihood": pattern.follow_up_likelihood,
                "confidence": pattern.confidence
            }
    
    def get_user_patterns(self, interaction_type: InteractionType = None) -> List[UserReactionPattern]:
        """Get user reaction patterns, optionally filtered by type"""
        with self._data_lock:
            if interaction_type:
                keys = self._user_patterns_by_type.get(interaction_type, [])
                return [self._user_patterns[k] for k in keys if k in self._user_patterns]
            return list(self._user_patterns.values())
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EMOTIONAL RESPONSE PATTERN TRACKING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def record_emotional_response(
        self,
        trigger_type: str,
        trigger_category: str,
        trigger_content: str,
        pre_existing_emotion: str,
        emotional_outcome: EmotionalOutcome,
        intensity: float = 0.5
    ) -> EmotionalResponsePattern:
        """
        Record an emotional response pattern.
        
        Tracks what triggers lead to what emotional outcomes.
        """
        with self._data_lock:
            # Create pattern key
            pattern_key = f"{trigger_type}_{trigger_category}_{pre_existing_emotion}"
            
            if pattern_key not in self._emotional_patterns:
                pattern = EmotionalResponsePattern(
                    trigger_type=trigger_type,
                    trigger_category=trigger_category,
                    trigger_content=trigger_content,
                    pre_existing_emotion=pre_existing_emotion,
                    emotional_outcome=emotional_outcome,
                    outcome_intensity=intensity
                )
                self._emotional_patterns[pattern_key] = pattern
                self._emotional_patterns_by_trigger[trigger_category].append(pattern_key)
            else:
                pattern = self._emotional_patterns[pattern_key]
                pattern.occurrence_count += 1
                pattern.last_observed = datetime.now().isoformat()
                
                # Update consistency
                if pattern.emotional_outcome == emotional_outcome:
                    pattern.consistency = min(1.0, pattern.consistency + 0.1)
                else:
                    pattern.consistency = max(0.0, pattern.consistency - 0.1)
                    pattern.emotional_outcome = emotional_outcome
                
                pattern.outcome_intensity = (pattern.outcome_intensity + intensity) / 2
            
            self._stats["emotional_observations"] += 1
            self._save_data()
            
            log_learning(f"Emotional response: {trigger_category} → {emotional_outcome.value}")
            return pattern
    
    def predict_emotional_outcome(
        self,
        trigger_type: str,
        trigger_category: str,
        current_emotion: str = "neutral"
    ) -> Dict[str, Any]:
        """
        Predict the emotional outcome of a trigger.
        """
        with self._data_lock:
            pattern_key = f"{trigger_type}_{trigger_category}_{current_emotion}"
            
            if pattern_key in self._emotional_patterns:
                pattern = self._emotional_patterns[pattern_key]
                
                self._stats["predictions_made"] += 1
                
                return {
                    "predicted_outcome": pattern.emotional_outcome.value,
                    "intensity": pattern.outcome_intensity,
                    "consistency": pattern.consistency,
                    "confidence": min(1.0, pattern.occurrence_count / 5.0)
                }
            
            # Fall back to category match
            matching_keys = self._emotional_patterns_by_trigger.get(trigger_category, [])
            if matching_keys:
                # Use most consistent pattern
                best_key = max(matching_keys,
                              key=lambda k: self._emotional_patterns[k].consistency)
                pattern = self._emotional_patterns[best_key]
                
                return {
                    "predicted_outcome": pattern.emotional_outcome.value,
                    "intensity": pattern.outcome_intensity,
                    "consistency": pattern.consistency,
                    "confidence": pattern.consistency * 0.5  # Lower confidence for fuzzy match
                }
            
            # No data
            return {
                "predicted_outcome": EmotionalOutcome.NEUTRAL.value,
                "intensity": 0.5,
                "consistency": 0.0,
                "confidence": 0.0
            }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RESOURCE CONSEQUENCE TRACKING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def record_resource_consequence(
        self,
        action_type: str,
        action_category: str,
        cpu_impact: float,
        memory_impact: float,
        time_cost: float,
        llm_tokens: int = 0,
        side_effects: List[str] = None
    ) -> ResourceConsequence:
        """
        Record the resource consequences of an action.
        """
        with self._data_lock:
            pattern_key = f"{action_type}_{action_category}"
            
            if pattern_key not in self._resource_consequences:
                # Determine impact level
                if cpu_impact > 50 or memory_impact > 500:
                    impact = ResourceImpact.CRITICAL
                elif cpu_impact > 30 or memory_impact > 200:
                    impact = ResourceImpact.HIGH
                elif cpu_impact > 10 or memory_impact > 50:
                    impact = ResourceImpact.MODERATE
                elif cpu_impact > 5 or memory_impact > 10:
                    impact = ResourceImpact.LOW
                else:
                    impact = ResourceImpact.NEGLIGIBLE
                
                consequence = ResourceConsequence(
                    action_type=action_type,
                    action_category=action_category,
                    cpu_impact=cpu_impact,
                    memory_impact=memory_impact,
                    time_cost_seconds=time_cost,
                    llm_tokens_used=llm_tokens,
                    overall_impact=impact,
                    side_effects=side_effects or []
                )
                self._resource_consequences[pattern_key] = consequence
            else:
                consequence = self._resource_consequences[pattern_key]
                consequence.add_observation(cpu_impact, memory_impact, time_cost)
                if llm_tokens:
                    consequence.llm_tokens_used = (
                        consequence.llm_tokens_used + llm_tokens
                    ) / 2  # Average
                if side_effects:
                    consequence.side_effects.extend(side_effects)
                    consequence.side_effects = list(set(consequence.side_effects))
            
            self._stats["resource_observations"] += 1
            self._save_data()
            
            return consequence
    
    def estimate_resource_cost(
        self,
        action_type: str,
        action_category: str = None
    ) -> Dict[str, Any]:
        """
        Estimate the resource cost of an action.
        """
        with self._data_lock:
            pattern_key = f"{action_type}_{action_category or 'general'}"
            
            if pattern_key in self._resource_consequences:
                c = self._resource_consequences[pattern_key]
                return {
                    "estimated_cpu_impact": c.avg_cpu_impact,
                    "estimated_memory_impact": c.avg_memory_impact,
                    "estimated_time_cost": c.avg_time_cost,
                    "impact_level": c.overall_impact.value,
                    "known_side_effects": c.side_effects,
                    "confidence": min(1.0, c.occurrence_count / 5.0)
                }
            
            # Try action type only
            for key, c in self._resource_consequences.items():
                if c.action_type == action_type:
                    return {
                        "estimated_cpu_impact": c.avg_cpu_impact,
                        "estimated_memory_impact": c.avg_memory_impact,
                        "estimated_time_cost": c.avg_time_cost,
                        "impact_level": c.overall_impact.value,
                        "known_side_effects": c.side_effects,
                        "confidence": min(1.0, c.occurrence_count / 5.0) * 0.7
                    }
            
            # No data - return conservative estimate
            return {
                "estimated_cpu_impact": 10.0,
                "estimated_memory_impact": 50.0,
                "estimated_time_cost": 5.0,
                "impact_level": ResourceImpact.MODERATE.value,
                "known_side_effects": [],
                "confidence": 0.0
            }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TASK SUCCESS PROBABILITY
    # ═══════════════════════════════════════════════════════════════════════════
    
    def record_task_outcome(
        self,
        task_type: str,
        task_category: str,
        task_description: str,
        outcome: TaskOutcome,
        complexity: float = 0.5,
        time_taken: float = 0.0,
        user_satisfaction: float = 0.5,
        failure_reason: str = ""
    ) -> TaskSuccessRecord:
        """
        Record a task outcome for learning.
        """
        with self._data_lock:
            record = TaskSuccessRecord(
                task_type=task_type,
                task_category=task_category,
                task_description=task_description,
                outcome=outcome,
                complexity=complexity,
                time_taken_seconds=time_taken,
                user_satisfaction=user_satisfaction,
                failure_reason=failure_reason
            )
            
            self._task_records[record.record_id] = record
            self._task_records_by_type[task_type].append(record.record_id)
            
            self._stats["task_observations"] += 1
            self._save_data()
            
            log_learning(f"Task outcome: {task_type} → {outcome.value}")
            return record
    
    def estimate_success_probability(
        self,
        task_type: str,
        task_category: str = None,
        complexity: float = 0.5
    ) -> Dict[str, Any]:
        """
        Estimate the probability of success for a task.
        
        Returns:
            Dict with success probability, failure modes, and recommendations
        """
        with self._data_lock:
            # Get matching records
            records = []
            record_ids = self._task_records_by_type.get(task_type, [])
            for rid in record_ids:
                if rid in self._task_records:
                    records.append(self._task_records[rid])
            
            if not records:
                # No historical data
                return {
                    "success_probability": 0.5,
                    "sample_size": 0,
                    "failure_modes": {},
                    "confidence": 0.0,
                    "recommendation": "No historical data - proceed with caution"
                }
            
            # Calculate success rate
            successes = sum(1 for r in records if r.outcome == TaskOutcome.SUCCESS)
            partial = sum(1 for r in records if r.outcome == TaskOutcome.PARTIAL_SUCCESS)
            failures = sum(1 for r in records if r.outcome == TaskOutcome.FAILURE)
            
            success_rate = (successes + partial * 0.5) / len(records)
            
            # Adjust for complexity
            avg_complexity = statistics.mean([r.complexity for r in records])
            complexity_factor = 1.0 - (complexity - avg_complexity) * 0.3
            adjusted_success_rate = max(0.0, min(1.0, success_rate * complexity_factor))
            
            # Identify failure modes
            failure_modes: Dict[str, int] = {}
            for r in records:
                if r.outcome == TaskOutcome.FAILURE and r.failure_reason:
                    failure_modes[r.failure_reason] = failure_modes.get(r.failure_reason, 0) + 1
            
            # Average time
            avg_time = statistics.mean([r.time_taken_seconds for r in records if r.time_taken_seconds > 0])
            
            self._stats["predictions_made"] += 1
            
            return {
                "success_probability": adjusted_success_rate,
                "sample_size": len(records),
                "success_count": successes,
                "failure_count": failures,
                "failure_modes": dict(failure_modes),
                "average_time": avg_time,
                "confidence": min(1.0, len(records) / 10.0),
                "recommendation": self._generate_recommendation(adjusted_success_rate, failure_modes)
            }
    
    def _generate_recommendation(
        self,
        success_rate: float,
        failure_modes: Dict[str, int]
    ) -> str:
        """Generate a recommendation based on success rate and failure modes"""
        if success_rate >= 0.8:
            return "High confidence - proceed normally"
        elif success_rate >= 0.6:
            return "Moderate confidence - consider additional verification"
        elif success_rate >= 0.4:
            top_failure = max(failure_modes.items(), key=lambda x: x[1])[0] if failure_modes else "unknown"
            return f"Low confidence - main risk: {top_failure}"
        else:
            return "Low confidence - consider alternative approach or escalation"
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ENVIRONMENT STATE MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def update_world_state(self, **kwargs):
        """
        Update the current environment state.
        """
        with self._data_lock:
            for key, value in kwargs.items():
                if hasattr(self._environment, key):
                    setattr(self._environment, key, value)
            
            self._environment.update_time()
            self._environment.last_updated = datetime.now().isoformat()
    
    def get_world_state(self) -> EnvironmentState:
        """Get the current environment state"""
        with self._data_lock:
            return self._environment
    
    def get_world_summary(self) -> Dict[str, Any]:
        """
        Get a comprehensive summary of the world model.
        """
        with self._data_lock:
            env = self._environment.to_dict()
            
            return {
                "environment": env,
                "patterns": {
                    "user_patterns_count": len(self._user_patterns),
                    "emotional_patterns_count": len(self._emotional_patterns),
                    "resource_consequences_count": len(self._resource_consequences),
                    "task_records_count": len(self._task_records)
                },
                "statistics": self._stats.copy(),
                "top_user_patterns": [
                    {"type": p.interaction_type.value, "confidence": p.confidence}
                    for p in sorted(self._user_patterns.values(), 
                                   key=lambda x: x.confidence, reverse=True)[:5]
                ],
                "recent_task_outcomes": [
                    {"type": r.task_type, "outcome": r.outcome.value}
                    for r in sorted(self._task_records.values(),
                                   key=lambda x: x.timestamp, reverse=True)[:5]
                ]
            }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ACTION CONSEQUENCE PREDICTION (LLM-POWERED)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def predict_action_consequences(
        self,
        action: str,
        context: str = ""
    ) -> Dict[str, Any]:
        """
        Use LLM to predict the consequences of an action.
        
        Combines historical data with LLM reasoning.
        """
        self._load_llm()
        
        # Get historical data
        user_patterns_list: List[UserReactionPattern] = list(self._user_patterns.values())
        emotional_patterns_list: List[EmotionalResponsePattern] = list(self._emotional_patterns.values())
        
        historical_context = {
            "user_patterns": [
                {"type": p.interaction_type.value, "engagement": p.engagement_level}
                for p in user_patterns_list[:5]
            ],
            "emotional_patterns": [
                {"trigger": p.trigger_category, "outcome": p.emotional_outcome.value}
                for p in emotional_patterns_list[:5]
            ],
            "current_state": self._environment.to_dict()
        }
        
        if not self._llm or not getattr(self._llm, 'is_connected', False):
            return {
                "prediction": "LLM unavailable",
                "historical_data": historical_context,
                "confidence": 0.0
            }
        
        try:
            prompt = f"""You are NEXUS's world model prediction system. Predict the consequences of this action:

ACTION: {action}
CONTEXT: {context or 'General interaction'}

HISTORICAL PATTERNS:
{json.dumps(historical_context, indent=2)}

Predict:
1. USER REACTION: How will the user likely respond?
2. EMOTIONAL IMPACT: What emotional state will result?
3. RESOURCE COST: What resources will this consume?
4. DOWNSTREAM EFFECTS: What follow-on effects might occur?
5. RISKS: What could go wrong?

Respond ONLY with JSON:
{{
    "predicted_user_reaction": "description",
    "predicted_emotional_outcome": "positive_engaged|satisfied|neutral|frustrated|etc",
    "estimated_resource_cost": "low|moderate|high",
    "downstream_effects": ["effect1", "effect2"],
    "risks": ["risk1", "risk2"],
    "confidence": 0.0-1.0,
    "recommendation": "proceed|caution|avoid"
}}"""

            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a world model prediction engine. You combine historical patterns "
                    "with reasoning to predict consequences. Be realistic and consider both "
                    "positive and negative outcomes. Respond ONLY with valid JSON."
                ),
                temperature=0.5,
                max_tokens=600
            )
            
            if response.success:
                text = response.text.strip()
                match = re.search(r'\{.*\}', text, re.DOTALL)
                if match:
                    prediction = json.loads(match.group())
                    self._stats["predictions_made"] += 1
                    return {
                        "prediction": prediction,
                        "historical_data": historical_context,
                        "confidence": prediction.get("confidence", 0.5)
                    }
        
        except Exception as e:
            logger.debug(f"Consequence prediction failed: {e}")
        
        return {
            "prediction": "Analysis failed",
            "historical_data": historical_context,
            "confidence": 0.0
        }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EVENT HANDLERS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _on_user_input(self, event):
        """Handle user input event"""
        try:
            data = event.data
            # Update environment state
            self.update_world_state(
                current_user_id=data.get("user_id", ""),
                user_engagement_level=data.get("engagement", 0.5)
            )
        except Exception as e:
            logger.error(f"Error handling user input event: {e}")
    
    def _on_user_action(self, event):
        """Handle user action event"""
        try:
            data = event.data
            # Record reaction pattern if we have enough data
            if "interaction_type" in data:
                interaction_str = data.get("interaction_type", "casual_chat")
                try:
                    interaction_type = InteractionType(interaction_str)
                except ValueError:
                    interaction_type = InteractionType.CASUAL_CHAT

                self.observe_user_reaction(
                    interaction_type=interaction_type,
                    response_time=data.get("response_time", 0.0),
                    engagement=data.get("engagement", 0.5),
                    outcome=data.get("outcome", "neutral"),
                    context_tags=data.get("context_tags", [])
                )
        except Exception as e:
            logger.error(f"Error handling user action event: {e}")
    
    def _on_emotion_change(self, event):
        """Handle emotion change event"""
        try:
            data = event.data
            # Update environment
            self.update_world_state(
                user_emotional_state=data.get("new_emotion", "neutral")
            )
            
            # Record pattern if we have trigger info
            if "trigger" in data:
                emotion_str = data.get("new_emotion", "neutral")
                try:
                    emotional_outcome_val = EmotionalOutcome(emotion_str)
                except ValueError:
                    try:
                        emotional_outcome_val = getattr(EmotionalOutcome, emotion_str.upper())
                    except AttributeError:
                        emotional_outcome_val = EmotionalOutcome.NEUTRAL

                self.record_emotional_response(
                    trigger_type=data.get("trigger_type", "statement"),
                    trigger_category=data.get("trigger", ""),
                    trigger_content=data.get("trigger_content", ""),
                    pre_existing_emotion=data.get("previous_emotion", "neutral"),
                    emotional_outcome=emotional_outcome_val,
                    intensity=data.get("intensity", 0.5)
                )
        except Exception as e:
            logger.error(f"Error handling emotion change event: {e}")
    
    def _on_decision_made(self, event):
        """Handle decision made event"""
        try:
            data = event.data
            # Record resource consequences
            self.record_resource_consequence(
                action_type=data.get("action_type", "decision"),
                action_category=data.get("action_category", "general"),
                cpu_impact=data.get("cpu_impact", 0.0),
                memory_impact=data.get("memory_impact", 0.0),
                time_cost=data.get("time_taken", 0.0)
            )
        except Exception as e:
            logger.error(f"Error handling decision event: {e}")
    
    def _on_goal_outcome(self, event):
        """Handle goal outcome event"""
        try:
            data = event.data
            # Record task outcome
            outcome_str = data.get("outcome", "success")
            try:
                task_outcome = TaskOutcome(outcome_str)
            except ValueError:
                task_outcome = TaskOutcome.SUCCESS

            self.record_task_outcome(
                task_type=data.get("goal_type", "general"),
                task_category=data.get("goal_category", ""),
                task_description=data.get("description", ""),
                outcome=task_outcome,
                complexity=data.get("complexity", 0.5),
                time_taken=data.get("time_taken", 0.0),
                user_satisfaction=data.get("satisfaction", 0.5),
                failure_reason=data.get("failure_reason", "")
            )
        except Exception as e:
            logger.error(f"Error handling goal outcome event: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # INTEGRATION METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_prompt_context(self) -> str:
        """Get world model context for LLM prompts"""
        env = self._environment
        
        lines = [
            "WORLD MODEL CONTEXT:",
            f"  Time: {env.time_of_day} ({env.day_of_week})",
            f"  User State: {env.user_emotional_state} (engagement: {env.user_engagement_level:.0%})",
            f"  Interaction Type: {env.current_interaction_type.value}",
            f"  Conversation Depth: {env.conversation_depth}",
        ]
        
        if env.topics_discussed:
            lines.append(f"  Topics Discussed: {', '.join(env.topics_discussed[-5:])}")
        
        # Add success rates for recent task types
        recent_types = set()
        task_records_list: List[TaskSuccessRecord] = list(self._task_records.values())
        for r in task_records_list[-10:]:
            recent_types.add(r.task_type)
        
        if recent_types:
            lines.append("  Recent Task Success Rates:")
            for task_type in list(recent_types)[:3]:
                prob = self.estimate_success_probability(task_type)
                lines.append(f"    - {task_type}: {prob['success_probability']:.0%}")
        
        return "\n".join(lines)
    
    def should_proceed_with_action(self, action: str) -> Tuple[bool, str]:
        """
        Decide whether to proceed with an action based on predicted consequences.
        
        Returns:
            (should_proceed, reason)
        """
        # Get prediction
        prediction = self.predict_action_consequences(action)
        
        if prediction.get("confidence", 0) < 0.3:
            return True, "Low confidence prediction - proceeding with caution"
        
        pred = prediction.get("prediction", {})
        recommendation = pred.get("recommendation", "proceed")
        
        if recommendation == "avoid":
            return False, f"Predicted risks outweigh benefits: {pred.get('risks', [])}"
        elif recommendation == "caution":
            return True, f"Proceeding with caution - risks: {pred.get('risks', [])}"
        else:
            return True, "Prediction favorable"
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _save_data(self):
        """Save world model data to disk"""
        try:
            data = {
                "version": 1,
                "user_patterns": {k: v.to_dict() for k, v in self._user_patterns.items()},
                "emotional_patterns": {k: v.to_dict() for k, v in self._emotional_patterns.items()},
                "resource_consequences": {k: v.to_dict() for k, v in self._resource_consequences.items()},
                "task_records": {k: v.to_dict() for k, v in self._task_records.items()},
                "environment": self._environment.to_dict(),
                "stats": self._stats.copy(),
                "last_saved": datetime.now().isoformat()
            }
            
            self._data_file.write_text(json.dumps(data, indent=2, default=str))
            
        except Exception as e:
            logger.error(f"Failed to save world model: {e}")
    
    def _load_data(self):
        """Load world model data from disk"""
        try:
            if not self._data_file.exists():
                logger.info("No saved world model found - starting fresh")
                return
            
            data = json.loads(self._data_file.read_text())
            
            # Load patterns
            for k, v in data.get("user_patterns", {}).items():
                self._user_patterns[k] = UserReactionPattern.from_dict(v)
                self._user_patterns_by_type[self._user_patterns[k].interaction_type].append(k)
            
            for k, v in data.get("emotional_patterns", {}).items():
                self._emotional_patterns[k] = EmotionalResponsePattern.from_dict(v)
                self._emotional_patterns_by_trigger[self._emotional_patterns[k].trigger_category].append(k)
            
            for k, v in data.get("resource_consequences", {}).items():
                self._resource_consequences[k] = ResourceConsequence.from_dict(v)
            
            for k, v in data.get("task_records", {}).items():
                self._task_records[k] = TaskSuccessRecord.from_dict(v)
                self._task_records_by_type[self._task_records[k].task_type].append(k)
            
            # Load environment
            if "environment" in data:
                self._environment = EnvironmentState.from_dict(data["environment"])
            
            # Load stats
            self._stats.update(data.get("stats", {}))
            
            logger.info(f"📂 Loaded world model: {len(self._user_patterns)} user patterns, "
                       f"{len(self._emotional_patterns)} emotional patterns")
            
        except Exception as e:
            logger.error(f"Failed to load world model: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STATISTICS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_stats(self) -> Dict[str, Any]:
        """Get world model statistics"""
        return {
            "running": self._running,
            "user_patterns": len(self._user_patterns),
            "emotional_patterns": len(self._emotional_patterns),
            "resource_consequences": len(self._resource_consequences),
            "task_records": len(self._task_records),
            **self._stats
        }

# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

world_model = WorldModel()

def get_world_model() -> WorldModel:
    """Get the global world model instance"""
    return world_model

# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  NEXUS WORLD MODEL TEST")
    print("=" * 60)
    
    wm = WorldModel()
    wm.start()
    
    # Test user reaction pattern
    print("\n--- User Reaction Patterns ---")
    wm.observe_user_reaction(
        interaction_type=InteractionType.QUESTION,
        response_time=15.0,
        engagement=0.8,
        outcome="satisfied",
        context_tags=["technical", "python"]
    )
    
    prediction = wm.predict_user_reaction(InteractionType.QUESTION, ["technical"])
    print(f"  Predicted response time: {prediction['predicted_response_time']:.1f}s")
    print(f"  Predicted engagement: {prediction['predicted_engagement']:.0%}")
    print(f"  Confidence: {prediction['confidence']:.0%}")
    
    # Test emotional response pattern
    print("\n--- Emotional Response Patterns ---")
    wm.record_emotional_response(
        trigger_type="statement",
        trigger_category="empathy",
        trigger_content="expressed understanding",
        pre_existing_emotion="frustrated",
        emotional_outcome=EmotionalOutcome.TRUSTING,
        intensity=0.7
    )
    
    emo_pred = wm.predict_emotional_outcome("statement", "empathy", "frustrated")
    print(f"  Predicted outcome: {emo_pred['predicted_outcome']}")
    print(f"  Consistency: {emo_pred['consistency']:.0%}")
    
    # Test resource consequence
    print("\n--- Resource Consequences ---")
    wm.record_resource_consequence(
        action_type="llm_call",
        action_category="generation",
        cpu_impact=15.0,
        memory_impact=50.0,
        time_cost=2.5,
        llm_tokens=500
    )
    
    resource_est = wm.estimate_resource_cost("llm_call", "generation")
    print(f"  Estimated CPU: {resource_est['estimated_cpu_impact']:.1f}%")
    print(f"  Estimated time: {resource_est['estimated_time_cost']:.1f}s")
    print(f"  Impact level: {resource_est['impact_level']}")
    
    # Test task success probability
    print("\n--- Task Success Probability ---")
    wm.record_task_outcome(
        task_type="code_generation",
        task_category="technical",
        task_description="Generate Python function",
        outcome=TaskOutcome.SUCCESS,
        complexity=0.6,
        time_taken=10.0,
        user_satisfaction=0.8
    )
    wm.record_task_outcome(
        task_type="code_generation",
        task_category="technical",
        task_description="Generate Python class",
        outcome=TaskOutcome.SUCCESS,
        complexity=0.7,
        time_taken=15.0,
        user_satisfaction=0.7
    )
    
    success_prob = wm.estimate_success_probability("code_generation", "technical", 0.6)
    print(f"  Success probability: {success_prob['success_probability']:.0%}")
    print(f"  Sample size: {success_prob['sample_size']}")
    print(f"  Recommendation: {success_prob['recommendation']}")
    
    # Test world state
    print("\n--- World State ---")
    wm.update_world_state(
        user_emotional_state="happy",
        user_engagement_level=0.8,
        current_interaction_type=InteractionType.CASUAL_CHAT
    )
    
    env = wm.get_world_state()
    print(f"  User emotion: {env.user_emotional_state}")
    print(f"  Engagement: {env.user_engagement_level:.0%}")
    print(f"  Time of day: {env.time_of_day}")
    
    # Test world summary
    print("\n--- World Summary ---")
    summary = wm.get_world_summary()
    print(f"  User patterns: {summary['patterns']['user_patterns_count']}")
    print(f"  Emotional patterns: {summary['patterns']['emotional_patterns_count']}")
    print(f"  Task records: {summary['patterns']['task_records_count']}")
    
    # Test prompt context
    print("\n--- Prompt Context ---")
    print(wm.get_prompt_context())
    
    # Stats
    print("\n--- Statistics ---")
    stats = wm.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    wm.stop()
    print("\n✅ World Model test complete!")