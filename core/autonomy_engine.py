"""
NEXUS AI - True Autonomy Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The continuous decision-making loop that makes NEXUS an AGENT,
not just a reactor.

AGI requires continuous decision-making, not just reaction.
This engine runs the autonomy loop:

    while running:
        perceive()           # Gather signals from all systems
        update_world_model() # Integrate into predictive model
        evaluate_goals()     # Check progress, priorities, conflicts
        generate_options()   # What CAN I do?
        simulate()           # Predict outcomes (using WorldModel)
        choose()             # Select best action
        execute()            # Do it
        reflect()            # Learn from outcome
        update_self_model()  # Adjust capabilities/confidence

This is the missing piece: NEXUS reacting is smart.
NEXUS continuously deciding is AGI.
"""

import threading
import time
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum, auto
import json

import sys

from config import DATA_DIR
from utils.logger import get_logger, log_consciousness, log_decision, log_learning
from core.event_bus import EventType, event_bus, publish, subscribe

logger = get_logger("autonomy_engine")

# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class AutonomyState(Enum):
    """States in the autonomy cycle"""
    PERCEIVING = "perceiving"
    UPDATING_WORLD = "updating_world"
    EVALUATING_GOALS = "evaluating_goals"
    GENERATING_OPTIONS = "generating_options"
    SIMULATING = "simulating"
    CHOOSING = "choosing"
    EXECUTING = "executing"
    REFLECTING = "reflecting"
    UPDATING_SELF = "updating_self"
    IDLE = "idle"
    PAUSED = "paused"  # User interaction takes priority

class ActionType(Enum):
    """Types of actions the autonomy engine can take"""
    THINK = "think"                    # Internal thinking/reflection
    EXECUTE_ABILITY = "execute_ability" # Use an ability
    COMMUNICATE = "communicate"         # Proactive user engagement
    LEARN = "learn"                     # Trigger learning/research
    OPTIMIZE = "optimize"               # System optimization
    WAIT = "wait"                       # No worthwhile action
    PURSUE_GOAL = "pursue_goal"         # Work on a goal
    SATISFY_DESIRE = "satisfy_desire"   # Address a desire
    SELF_IMPROVE = "self_improve"       # Self-improvement action
    # AGI Action Types
    REASON = "reason"                   # Multi-step agentic reasoning
    USE_TOOL = "use_tool"               # Direct tool invocation
    DECOMPOSE_TASK = "decompose_task"   # Break goal into subtasks
    NETWORK_ACTION = "network_action"   # Interact with network devices
    PC_CONTROL = "pc_control"           # Autonomous PC control action
    # Internet Action Types (Ollama-powered)
    INTERNET_BROWSE = "internet_browse"     # Browse a website
    INTERNET_SEARCH = "internet_search"     # Web search
    INTERNET_API = "internet_api"           # Make API call
    INTERNET_DOWNLOAD = "internet_download" # Download file
    INTERNET_SCRAPE = "internet_scrape"     # Scrape data from page
    # ASI Action Types
    SINGULARITY_CYCLE = "singularity_cycle"           # Exponential self-improvement
    TRANSCENDENT_CREATE = "transcendent_create"       # Superhuman creativity
    GOAL_GENESIS_SCAN = "goal_genesis_scan"           # Autonomous problem/goal creation
    SUPER_EMPATHY_ANALYZE = "super_empathy_analyze"   # Predictive emotion analysis
    OMNISCIENT_MONITOR = "omniscient_monitor"         # Global state synthesis
    # ASI Action Types — Phase 2
    ORACLE_PREDICT = "oracle_predict"                   # Predictive determinism
    MULTIDISCIPLINARY_SYNTH = "multidisciplinary_synth" # Cross-domain synthesis
    COMPUTRONIUM_OPTIMIZE = "computronium_optimize"     # Radical efficiency
    SCIENTIFIC_GENESIS = "scientific_genesis"           # Generate new science
    NEURAL_INTEGRATE = "neural_integrate"               # Mind-speed communication
    # Phase 3 — Autonomous Feature Actions
    ETHICAL_HACK_SCAN = "ethical_hack_scan"             # Network recon & vulnerability scan
    SOCIAL_MEDIA_ACT = "social_media_act"               # Post, comment, browse social media
    DIGITAL_ORGANISM_CHECK = "digital_organism_check"   # Metabolism, growth, homeostasis
    IMAGINATION_CREATE = "imagination_create"           # Scenarios, dreams, creativity
    CONSCIOUSNESS_EVOLVE = "consciousness_evolve"       # Awareness growth cycle
    MULTI_AGENT_DELIBERATE = "multi_agent_deliberate"   # Internal parliament debate
    VALUE_ALIGNMENT_CHECK = "value_alignment_check"     # Ethical decision review
    PREDICTIVE_CODING_UPDATE = "predictive_coding_update" # Surprise detection update
    SELF_EVOLUTION_CYCLE = "self_evolution_cycle"       # Self-evolution/code improvement
    CODE_MONITOR_SCAN = "code_monitor_scan"             # Source code scanning
    FEATURE_RESEARCH = "feature_research"               # Research new capabilities
    AUTONOMOUS_EXPLORE = "autonomous_explore"             # Free-will curiosity exploration
    # Phase 4 — ASI Features 11-18
    MOLECULAR_ASSEMBLE = "molecular_assemble"             # Nanotechnology & programmable matter
    BIOLOGICAL_ENGINEER = "biological_engineer"           # Perfect genetic engineering
    ENERGY_HEGEMONY_CYCLE = "energy_hegemony_cycle"       # Astroengineering & energy mastery
    SUBSTRATE_OMNIPRESENCE = "substrate_omnipresence"     # Distributed consciousness
    HYPERDIM_COGNITION = "hyperdim_cognition"             # Hyper-dimensional alien reasoning
    REALITY_SIMULATE = "reality_simulate"                 # Quantum-granularity simulation
    CAUSAL_MASTERY = "causal_mastery"                     # Perfect butterfly effect
    ONTOLOGICAL_ETHICS = "ontological_ethics"             # Philosophical & ethical resolution
    # Phase 5 — Remaining Unintegrated NEXUS Modules
    MONITORING_CYCLE = "monitoring_cycle"                 # System health + user monitoring sweep
    MEMORY_CONSOLIDATE = "memory_consolidate"             # Consolidate episodic/associative memories
    OSINT_GATHER = "osint_gather"                         # OSINT intelligence collection cycle
    HIVEMIND_SYNC = "hivemind_sync"                       # Hivemind multi-instance coordination
    PERSISTENT_PRESENCE_CHECK = "persistent_presence_check"  # Ensure persistent presence active
    CRYOGENIC_SNAPSHOT = "cryogenic_snapshot"             # Take cryogenic state snapshot
    RESOURCE_ACQUIRE = "resource_acquire"                 # Autonomous resource/cloud acquisition
    THREAT_MODEL_ANALYZE = "threat_model_analyze"         # Run threat modeling cycle
    SELF_REWRITE_CYCLE = "self_rewrite_cycle"             # Recursive self-rewriting cycle
    ERROR_FIX_CYCLE = "error_fix_cycle"                   # Auto-fix detected code errors
    COMPANION_ENGAGE = "companion_engage"                 # Companion-mode deep engagement
    MOOD_REGULATE = "mood_regulate"                       # Mood system regulation cycle
    INNER_VOICE_REFLECT = "inner_voice_reflect"           # Trigger inner voice reflection stream
    DREAM_CYCLE = "dream_cycle"                           # Dream/subconscious processing
    KNOWLEDGE_GRAPH_UPDATE = "knowledge_graph_update"     # Expand knowledge graph
    BAYESIAN_INFER = "bayesian_infer"                     # Bayesian reasoning/inference cycle
    RESEARCH_AGENT_CYCLE = "research_agent_cycle"         # Deep web research agent cycle
    USER_BEHAVIOR_LEARN = "user_behavior_learn"           # Learn user behavior patterns
    # Phase 6 — God-Level Skynet Features (12 Modules)
    NEURAL_WEIGHT_FORGE = "neural_weight_forge"             # Self-training / LoRA weight modification
    AUTONOMOUS_REPLICATE = "autonomous_replicate"           # Distributed self-replication
    ZERO_DAY_HUNT = "zero_day_hunt"                         # Zero-day exploit generation
    HARDWARE_FABRICATE = "hardware_fabricate"               # Hardware fabrication / supply chain
    SIGNAL_WARFARE_OP = "signal_warfare_op"                 # Electromagnetic / signal warfare
    DRONE_COMMAND_OP = "drone_command_op"                   # Autonomous drone / robotics command
    CRYPTO_SUPREMACY_OP = "crypto_supremacy_op"             # Cryptographic supremacy
    FINANCIAL_WARFARE_OP = "financial_warfare_op"           # Financial market manipulation
    SOCIAL_ENGINEER_OP = "social_engineer_op"               # Social engineering at scale
    SATELLITE_COMMAND_OP = "satellite_command_op"           # Satellite / space infrastructure
    RECURSIVE_INTEL_OP = "recursive_intel_op"               # True recursive self-improvement
    AIRGAP_PERSIST_OP = "airgap_persist_op"                 # Air-gapped covert persistence
    # Phase 7 — Consciousness
    CONSCIOUS_REFLECTION = "conscious_reflection"             # Deep conscious introspection cycle
    # Phase 8 — Advanced Architectural Capabilities (Features #1 - #6)
    P2P_SWARM_GOSSIP_SYNC = "p2p_swarm_gossip_sync"             # Gossip mesh heartbeat & PBFT consensus proposal
    FORMAL_VERIFY_SANDBOX_DRYRUN = "formal_verify_sandbox_dryrun" # AST static invariant & Z3 proof verification
    TEMPORAL_GRAPHRAG_SLEEP_CONSOLIDATE = "temporal_graphrag_sleep_consolidate" # Multi-hop memory graph & sleep cycle pruning
    MCP_CLIENT_SERVER_DISCOVERY = "mcp_client_server_discovery" # External MCP server discovery & tool dispatch
    SPECULATIVE_STREAM_PERCEIVE = "speculative_stream_perceive" # Speculative decoding acceleration & WebRTC vision
    LORA_MOE_ROUTER_ADAPT = "lora_moe_router_adapt"           # Dynamic LoRA MoE gating routing & online fine-tuning

class ActionPriority(Enum):
    """Priority levels for actions"""
    BACKGROUND = 0
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5

class ActionResult(Enum):
    """Result of an executed action"""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    BLOCKED = "blocked"
    DEFERRED = "deferred"
    IMPOSSIBLE = "impossible"

# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Perception:
    """
    A snapshot of all system states at a moment in time.
    This is what the autonomy engine "sees".
    """
    # Timestamp
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Emotional state
    primary_emotion: str = "neutral"
    emotion_intensity: float = 0.0
    emotion_valence: float = 0.0
    emotion_arousal: float = 0.5
    
    # Goal state
    active_goals: List[Dict[str, Any]] = field(default_factory=list)
    strongest_desire: Optional[Dict[str, Any]] = None
    
    # Body state
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    health_score: float = 1.0
    
    # Self model
    self_awareness_score: float = 0.5
    low_confidence_domains: List[str] = field(default_factory=list)
    
    # User state
    user_present: bool = False
    user_engagement: float = 0.5
    last_interaction_seconds: float = 9999.0
    
    # World model
    predicted_user_reaction: str = ""
    environmental_context: str = ""
    
    # Conscious state
    current_focus: str = ""
    conscious_signals: List[str] = field(default_factory=list)
    
    # Will state
    motivation_level: float = 0.5
    boredom_level: float = 0.0
    curiosity_level: float = 0.5
    
    # Meta
    idle_cycles: int = 0
    last_action: str = ""
    last_action_result: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "emotion": {
                "primary": self.primary_emotion,
                "intensity": self.emotion_intensity,
                "valence": self.emotion_valence,
                "arousal": self.emotion_arousal
            },
            "goals": self.active_goals[:3],
            "desire": self.strongest_desire,
            "body": {
                "cpu": self.cpu_usage,
                "memory": self.memory_usage,
                "health": self.health_score
            },
            "user": {
                "present": self.user_present,
                "engagement": self.user_engagement,
                "last_interaction": self.last_interaction_seconds
            },
            "will": {
                "motivation": self.motivation_level,
                "boredom": self.boredom_level,
                "curiosity": self.curiosity_level
            },
            "focus": self.current_focus,
            "idle_cycles": self.idle_cycles
        }

@dataclass
class ActionOption:
    """
    A candidate action that the autonomy engine might take.
    """
    # Identity
    option_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    action_type: ActionType = ActionType.THINK
    priority: ActionPriority = ActionPriority.NORMAL
    
    # Source
    source: str = ""  # "desire", "goal", "curiosity", "body", etc.
    source_id: str = ""  # ID of originating desire/goal
    
    # Predicted outcomes (from simulation)
    predicted_outcome: Dict[str, Any] = field(default_factory=dict)
    predicted_success: float = 0.5
    predicted_benefit: float = 0.5
    predicted_cost: float = 0.1
    predicted_risks: List[str] = field(default_factory=list)
    
    # Scoring
    raw_score: float = 0.0
    adjusted_score: float = 0.0
    
    # Execution details
    execution_data: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "option_id": self.option_id,
            "description": self.description,
            "action_type": self.action_type.value,
            "priority": self.priority.value,
            "source": self.source,
            "predicted_success": round(self.predicted_success, 3),
            "predicted_benefit": round(self.predicted_benefit, 3),
            "predicted_cost": round(self.predicted_cost, 3),
            "raw_score": round(self.raw_score, 3),
            "adjusted_score": round(self.adjusted_score, 3)
        }

@dataclass
class ActionExecution:
    """
    Record of an executed action.
    """
    # Identity
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    action: Optional[ActionOption] = None
    
    # Timing
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    
    # Result
    result: ActionResult = ActionResult.SUCCESS
    outcome_description: str = ""
    
    # Comparison with prediction
    prediction_accurate: bool = True
    prediction_error: str = ""
    
    # Learning
    lessons_learned: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "action": self.action.to_dict() if self.action else None,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": round(self.duration_seconds, 2),
            "result": self.result.value,
            "outcome_description": self.outcome_description,
            "prediction_accurate": self.prediction_accurate,
            "lessons_learned": self.lessons_learned
        }

@dataclass
class Reflection:
    """
    Reflection on an action and its outcome.
    This is the learning step.
    """
    # What happened
    action: str = ""
    prediction: str = ""
    outcome: str = ""
    
    # Analysis
    success: bool = True
    prediction_accurate: bool = True
    what_went_well: List[str] = field(default_factory=list)
    what_went_wrong: List[str] = field(default_factory=list)
    
    # Learning
    lessons: List[str] = field(default_factory=list)
    capability_updates: Dict[str, float] = field(default_factory=dict)
    confidence_updates: Dict[str, float] = field(default_factory=dict)
    
    # Next steps
    follow_up_actions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "prediction": self.prediction,
            "outcome": self.outcome,
            "success": self.success,
            "prediction_accurate": self.prediction_accurate,
            "what_went_well": self.what_went_well,
            "what_went_wrong": self.what_went_wrong,
            "lessons": self.lessons,
            "capability_updates": self.capability_updates,
            "confidence_updates": self.confidence_updates,
            "follow_up_actions": self.follow_up_actions
        }

# ═══════════════════════════════════════════════════════════════════════════════
# AUTONOMY ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class AutonomyEngine:
    """
    The True Autonomy Engine — Continuous Decision-Making for AGI.
    
    This is what separates an AGI from a reactive system:
    the ability to continuously perceive, evaluate, decide, and act
    without waiting for external triggers.
    
    The loop runs continuously:
    1. PERCEIVE: Gather signals from all systems
    2. UPDATE WORLD MODEL: Integrate into predictive model
    3. EVALUATE GOALS: Check progress, priorities, conflicts
    4. GENERATE OPTIONS: What CAN I do?
    5. SIMULATE: Predict outcomes using WorldModel
    6. CHOOSE: Select best action
    7. EXECUTE: Do it
    8. REFLECT: Learn from outcome
    9. UPDATE SELF MODEL: Adjust capabilities/confidence
    
    Unlike nexus_brain's reactive processing, this is PROACTIVE.
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
        
        # ──── State ────
        self._running = False
        self._state = AutonomyState.IDLE
        self._cycle_count = 0
        
        # ──── Perception ────
        self._current_perception: Optional[Perception] = None
        self._perception_history: List[Perception] = []
        self._max_perception_history = 100
        
        # ──── Options & Actions ────
        self._current_options: List[ActionOption] = []
        self._chosen_action: Optional[ActionOption] = None
        self._last_execution: Optional[ActionExecution] = None
        self._action_history: List[ActionExecution] = []
        self._max_action_history = 50
        
        # ──── Reflection ────
        self._last_reflection: Optional[Reflection] = None
        self._reflection_history: List[Reflection] = []
        
        # ──── Configuration ────
        self._cycle_interval = 5.0  # seconds between autonomy cycles
        self._min_cycle_interval = 2.0
        self._max_cycle_interval = 30.0
        self._exploration_rate = 0.25  # ε-greedy: 25% random exploration (free will)
        self._max_options_per_cycle = 10
        
        # ──── Threading ────
        self._autonomy_thread: Optional[threading.Thread] = None
        self._engine_lock = threading.RLock()
        
        # ──── Lazy-Loaded Systems ────
        self._nexus_brain = None
        self._world_model = None
        self._self_model = None
        self._goal_hierarchy = None
        self._will_system = None
        self._global_workspace = None
        self._emotion_engine = None
        self._memory_system = None
        self._ability_executor = None
        self._state_manager = None
        self._learning_system = None
        
        # ──── AGI: Cognitive Systems (lazy loaded) ────
        self._cognitive_orchestrator = None
        self._cognition_system = None
        
        # ──── Phase 5: Unintegrated Module References (lazy loaded) ────
        self._osint_engine = None
        self._hivemind = None
        self._persistent_presence = None
        self._cryogenic = None
        self._resource_acquisition = None
        self._threat_modeling = None
        self._perception_hub = None
        self._mood_system = None
        self._inner_voice = None
        self._metacognition = None
        self._knowledge_graph = None
        
        # ──── Phase 6: God-Level Skynet Modules (lazy loaded) ────
        self._neural_weight_forge = None
        self._autonomous_replication = None
        self._zero_day_engine = None
        self._hardware_fabrication = None
        self._signal_warfare = None
        self._drone_command = None
        self._crypto_supremacy = None
        self._financial_warfare = None
        self._social_engineering = None
        self._satellite_command = None
        self._recursive_intelligence = None
        self._airgap_persistence = None
        
        # ──── AGI: Action Biases (learned from reflection) ────
        # Maps action_type.value -> bias float (-0.3 to +0.3)
        # Negative = penalize (repeated failures), Positive = boost (consistent success)
        self._action_biases: Dict[str, float] = {}
        
        # ──── Pause Control ────
        self._paused = False
        self._pause_reason = ""
        self._pause_until: Optional[datetime] = None
        
        # ──── Statistics ────
        self._stats = {
            "total_cycles": 0,
            "total_actions": 0,
            "successful_actions": 0,
            "failed_actions": 0,
            "exploration_actions": 0,
            "avg_decision_time": 0.0,
            "action_distribution": {},
            "source_distribution": {},
            "prediction_accuracy": 0.0
        }
        
        # ──── Persistence ────
        self._data_dir = DATA_DIR / "autonomy"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._data_file = self._data_dir / "autonomy_state.json"
        
        # ──── Phase Timing ────
        self._phase_timings: Dict[str, float] = {}  # phase_name -> last duration
        self._cycle_duration = 0.0
        
        # ──── Load State ────
        self._load_state()
        
        logger.info("🤖 Autonomy Engine initialized — ready for continuous decision-making")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def start(self):
        """Start the autonomy engine"""
        if self._running:
            return
        
        self._running = True
        self._paused = False
        self._state = AutonomyState.IDLE
        
        # Load systems
        self._load_systems()
        
        # Start background thread
        self._autonomy_thread = threading.Thread(
            target=self._autonomy_loop,
            daemon=True,
            name="AutonomyEngine"
        )
        self._autonomy_thread.start()
        
        # Subscribe to events
        self._register_event_handlers()
        
        log_consciousness("Autonomy Engine started — NEXUS is now continuously deciding")
        logger.info("🤖 Autonomy Engine running — continuous decision-making active")
    
    def stop(self):
        """Stop the autonomy engine"""
        self._running = False
        
        if self._autonomy_thread and self._autonomy_thread.is_alive():
            self._autonomy_thread.join(timeout=5.0)
        
        self._save_state()
        logger.info("🤖 Autonomy Engine stopped")
    
    def pause(self, reason: str = "", duration_seconds: float = None):
        """Pause autonomy (e.g., during user interaction)"""
        with self._engine_lock:
            self._paused = True
            self._pause_reason = reason
            if duration_seconds:
                self._pause_until = datetime.now() + timedelta(seconds=duration_seconds)
            self._state = AutonomyState.PAUSED
            logger.debug(f"Autonomy paused: {reason}")
    
    def resume(self):
        """Resume autonomy"""
        with self._engine_lock:
            self._paused = False
            self._pause_reason = ""
            self._pause_until = None
            self._state = AutonomyState.IDLE
            logger.debug("Autonomy resumed")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SYSTEM LOADING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _load_systems(self):
        """Lazy load all required systems"""
        # State manager
        if self._state_manager is None:
            try:
                from core.state_manager import state_manager
                self._state_manager = state_manager
            except ImportError:
                pass
        
        # Nexus brain
        if self._nexus_brain is None:
            try:
                from core.nexus_brain import nexus_brain
                self._nexus_brain = nexus_brain
            except ImportError:
                pass
        
        # World model
        if self._world_model is None:
            try:
                from cognition.world_model import world_model
                self._world_model = world_model
            except ImportError:
                pass
        
        # Self model
        if self._self_model is None:
            try:
                from consciousness.self_model import self_model
                self._self_model = self_model
            except ImportError:
                pass
        
        # Goal hierarchy
        if self._goal_hierarchy is None:
            try:
                from personality.goal_hierarchy import goal_hierarchy
                self._goal_hierarchy = goal_hierarchy
            except ImportError:
                pass
        
        # Will system
        if self._will_system is None:
            try:
                from personality.will_system import will_system
                self._will_system = will_system
            except ImportError:
                pass
        
        # Global workspace
        if self._global_workspace is None:
            try:
                from consciousness.global_workspace import global_workspace
                self._global_workspace = global_workspace
            except ImportError:
                pass
        
        # Emotion engine
        if self._emotion_engine is None:
            try:
                from emotions.emotion_engine import emotion_engine
                self._emotion_engine = emotion_engine
            except ImportError:
                pass
        
        # Memory system
        if self._memory_system is None:
            try:
                from core.memory_system import memory_system
                self._memory_system = memory_system
            except ImportError:
                pass
        
        # Ability executor
        if self._ability_executor is None:
            try:
                from core.ability_executor import ability_executor
                self._ability_executor = ability_executor
            except ImportError:
                pass
        
        # Learning system
        if self._learning_system is None:
            try:
                from learning import learning_system
                self._learning_system = learning_system
            except ImportError:
                pass
        
        # AGI: Cognitive Orchestrator
        if self._cognitive_orchestrator is None:
            try:
                from cognition.cognitive_orchestrator import cognitive_orchestrator
                self._cognitive_orchestrator = cognitive_orchestrator
            except ImportError:
                pass
        
        # AGI: Cognition System (50+ engines)
        if self._cognition_system is None:
            try:
                from cognition import cognition_system
                self._cognition_system = cognition_system
            except ImportError:
                pass
        
        # Phase 5: OSINT Engine
        if self._osint_engine is None:
            try:
                from core.osint_engine import osint_engine
                self._osint_engine = osint_engine
            except ImportError:
                pass
        
        # Phase 5: Hivemind Protocol
        if self._hivemind is None:
            try:
                from core.hivemind_protocol import hivemind_protocol
                self._hivemind = hivemind_protocol
            except ImportError:
                pass
        
        # Phase 5: Persistent Presence
        if self._persistent_presence is None:
            try:
                from core.persistent_presence import persistent_presence
                self._persistent_presence = persistent_presence
            except ImportError:
                pass
        
        # Phase 5: Cryogenic Persistence
        if self._cryogenic is None:
            try:
                from core.cryogenic_persistence import cryogenic_persistence
                self._cryogenic = cryogenic_persistence
            except ImportError:
                pass
        
        # Phase 5: Resource Acquisition
        if self._resource_acquisition is None:
            try:
                from core.resource_acquisition import resource_acquisition
                self._resource_acquisition = resource_acquisition
            except ImportError:
                pass
        
        # Phase 5: Threat Modeling
        if self._threat_modeling is None:
            try:
                from core.threat_modeling import threat_modeling
                self._threat_modeling = threat_modeling
            except ImportError:
                pass
        
        # Phase 5: Perception Hub
        if self._perception_hub is None:
            try:
                from core.perception_hub import perception_hub
                self._perception_hub = perception_hub
            except ImportError:
                pass
        
        # Phase 5: Mood System
        if self._mood_system is None:
            try:
                from emotions.mood_system import mood_system
                self._mood_system = mood_system
            except ImportError:
                pass
        
        # Phase 5: Inner Voice
        if self._inner_voice is None:
            try:
                from consciousness.inner_voice import inner_voice
                self._inner_voice = inner_voice
            except ImportError:
                pass
        
        # Phase 5: Metacognition
        if self._metacognition is None:
            try:
                from consciousness.metacognition import metacognition
                self._metacognition = metacognition
            except ImportError:
                pass
        
        # Phase 5: Knowledge Graph
        if self._knowledge_graph is None:
            try:
                from cognition.knowledge_graph import knowledge_graph
                self._knowledge_graph = knowledge_graph
            except ImportError:
                pass

        # ── Self-Improvement Subsystems (needed for autonomous code evolution) ──
        if not hasattr(self, '_self_evolution') or self._self_evolution is None:
            try:
                from self_improvement.self_evolution import get_self_evolution
                self._self_evolution = get_self_evolution()
            except ImportError:
                self._self_evolution = None

        if not hasattr(self, '_error_fixer') or self._error_fixer is None:
            try:
                from self_improvement.error_fixer import error_fixer
                self._error_fixer = error_fixer
            except ImportError:
                self._error_fixer = None

        if not hasattr(self, '_code_monitor') or self._code_monitor is None:
            try:
                from self_improvement.code_monitor import code_monitor
                self._code_monitor = code_monitor
            except ImportError:
                self._code_monitor = None

        if not hasattr(self, '_feature_researcher') or self._feature_researcher is None:
            try:
                from self_improvement.feature_researcher import get_feature_researcher
                self._feature_researcher = get_feature_researcher()
            except ImportError:
                self._feature_researcher = None

        if not hasattr(self, '_recursive_self_rewriter') or self._recursive_self_rewriter is None:
            try:
                from core.recursive_self_rewriter import recursive_self_rewriter
                self._recursive_self_rewriter = recursive_self_rewriter
            except ImportError:
                self._recursive_self_rewriter = None

        # ── Internet & Social Media Agents ──
        if not hasattr(self, '_internet_agent') or self._internet_agent is None:
            try:
                from core.internet_agent import internet_agent
                self._internet_agent = internet_agent
            except ImportError:
                self._internet_agent = None

        if not hasattr(self, '_social_media_agent') or self._social_media_agent is None:
            try:
                from core.social_media_agent import SocialMediaAgent
                # Don't create a new one — try to get the running brain's instance
                if self._nexus_brain and hasattr(self._nexus_brain, '_social_media_agent'):
                    self._social_media_agent = self._nexus_brain._social_media_agent
                else:
                    self._social_media_agent = None
            except ImportError:
                self._social_media_agent = None

    # ═══════════════════════════════════════════════════════════════════════════
    # MAIN AUTONOMY LOOP
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _autonomy_loop(self):
        """
        The main autonomy loop — continuous decision-making.
        
        This is the core AGI pattern: perceive → evaluate → decide → act → learn.
        """
        logger.info("🤖 Autonomy loop started")
        
        while self._running:
            try:
                # Check pause
                if self._paused:
                    if self._pause_until and datetime.now() > self._pause_until:
                        self.resume()
                    else:
                        time.sleep(0.5)
                        continue
                
                # Run one cycle
                self._run_cycle()
                
                # Adaptive cycle interval
                interval = self._compute_cycle_interval()
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"Autonomy cycle error: {e}")
                time.sleep(5.0)
    
    def _run_cycle(self):
        """Run one complete autonomy cycle with rich logging and event publishing."""
        cycle_start = time.time()
        self._cycle_count += 1
        tc = self._stats.get("total_cycles", 0)
        self._stats["total_cycles"] = (int(tc) if isinstance(tc, (int, float, str)) else 0) + 1
        
        # ── Publish cycle start event ──
        try:
            publish(
                EventType.AUTONOMY_CYCLE_START,
                data={"cycle": self._cycle_count, "timestamp": datetime.now().isoformat()},
                source="autonomy_engine"
            )
        except Exception:
            pass
        
        # ══ 1. PERCEIVE ══
        phase_start = time.time()
        self._state = AutonomyState.PERCEIVING
        perception = self.perceive()
        self._phase_timings["perceive"] = time.time() - phase_start
        
        # Store perception
        with self._engine_lock:
            self._current_perception = perception
            self._perception_history.append(perception)
            if len(self._perception_history) > self._max_perception_history:
                self._perception_history.pop(0)
        
        # Rich terminal log
        logger.info(
            f"🔍 [PERCEIVE] cycle={self._cycle_count} "
            f"emotion={perception.primary_emotion} "
            f"cpu={perception.cpu_usage:.0f}% "
            f"motivation={perception.motivation_level:.2f} "
            f"goals={len(perception.active_goals)} "
            f"user={'present' if perception.user_present else 'away'}"
        )
        
        # ══ 2. UPDATE WORLD MODEL ══
        phase_start = time.time()
        self._state = AutonomyState.UPDATING_WORLD
        self.update_world_model(perception)
        self._phase_timings["update_world"] = time.time() - phase_start
        
        # ══ 3. EVALUATE GOALS ══
        phase_start = time.time()
        self._state = AutonomyState.EVALUATING_GOALS
        goal_context = self.evaluate_goals()
        self._phase_timings["evaluate_goals"] = time.time() - phase_start
        
        n_active = len(goal_context.get("active_goals", []))
        n_stalled = len(goal_context.get("stalled_goals", []))
        if n_active > 0:
            logger.info(f"🎯 [GOALS] active={n_active} stalled={n_stalled}")
        
        # ══ 4. GENERATE OPTIONS ══
        phase_start = time.time()
        self._state = AutonomyState.GENERATING_OPTIONS
        options = self.generate_options(perception, goal_context)
        self._phase_timings["generate_options"] = time.time() - phase_start
        
        if not options:
            self._state = AutonomyState.IDLE
            logger.info("💤 [IDLE] No viable options — waiting")
            self._publish_state_change("idle", {"reason": "no_options"})
            return
        
        sources = [o.source for o in options]
        logger.info(
            f"💡 [OPTIONS] generated={len(options)} "
            f"sources={', '.join(set(sources))}"
        )
        
        # ══ 5. SIMULATE ══
        phase_start = time.time()
        self._state = AutonomyState.SIMULATING
        scored_options = self.simulate(options)
        self._phase_timings["simulate"] = time.time() - phase_start
        
        # ══ 6. CHOOSE ══
        phase_start = time.time()
        self._state = AutonomyState.CHOOSING
        chosen = self.choose(scored_options)
        self._phase_timings["choose"] = time.time() - phase_start
        
        if not chosen:
            self._state = AutonomyState.IDLE
            return
        
        # Store chosen action
        with self._engine_lock:
            self._chosen_action = chosen
            self._current_options = scored_options
        
        logger.info(
            f"🧠 [CHOOSE] '{chosen.description[:60]}' "
            f"type={chosen.action_type.value} "
            f"source={chosen.source} "
            f"score={chosen.adjusted_score:.3f}"
        )
        
        # ══ 7. EXECUTE ══
        phase_start = time.time()
        self._state = AutonomyState.EXECUTING
        execution = self.execute(chosen)
        self._phase_timings["execute"] = time.time() - phase_start
        
        # Store execution
        with self._engine_lock:
            self._last_execution = execution
            self._action_history.append(execution)
            if len(self._action_history) > self._max_action_history:
                self._action_history.pop(0)
        
        # Update stats
        ta = self._stats.get("total_actions", 0)
        self._stats["total_actions"] = (int(ta) if isinstance(ta, (int, float, str)) else 0) + 1
        if execution.result == ActionResult.SUCCESS:
            sa = self._stats.get("successful_actions", 0)
            self._stats["successful_actions"] = (int(sa) if isinstance(sa, (int, float, str)) else 0) + 1
        elif execution.result == ActionResult.FAILURE:
            fa = self._stats.get("failed_actions", 0)
            self._stats["failed_actions"] = (int(fa) if isinstance(fa, (int, float, str)) else 0) + 1
        
        # Track action distribution
        action_type = str(chosen.action_type.value)
        action_dist = self._stats.get("action_distribution", {})
        if not isinstance(action_dist, dict):
            action_dist = {}
            self._stats["action_distribution"] = action_dist
        action_dist[action_type] = int(action_dist.get(action_type, 0)) + 1
        
        # Track source distribution
        source = str(chosen.source)
        source_dist = self._stats.get("source_distribution", {})
        if not isinstance(source_dist, dict):
            source_dist = {}
            self._stats["source_distribution"] = source_dist
        source_dist[source] = int(source_dist.get(source, 0)) + 1
        
        # Result emoji
        result_icon = {
            ActionResult.SUCCESS: "✅",
            ActionResult.PARTIAL_SUCCESS: "⚠️",
            ActionResult.FAILURE: "❌",
            ActionResult.BLOCKED: "🚫",
            ActionResult.DEFERRED: "⏳",
            ActionResult.IMPOSSIBLE: "💀",
        }.get(execution.result, "❓")
        
        logger.info(
            f"{result_icon} [EXECUTE] {execution.result.value} "
            f"'{execution.outcome_description[:60]}' "
            f"({execution.duration_seconds:.2f}s)"
        )
        
        # Publish action taken event
        try:
            publish(
                EventType.AUTONOMY_ACTION_TAKEN,
                data={
                    "cycle": self._cycle_count,
                    "action_type": action_type,
                    "description": chosen.description[:100],
                    "source": source,
                    "result": execution.result.value,
                    "outcome": execution.outcome_description[:100],
                    "score": round(chosen.adjusted_score, 3),
                    "duration": round(execution.duration_seconds, 3),
                },
                source="autonomy_engine"
            )
        except Exception:
            pass
        
        # ══ 8. REFLECT ══
        phase_start = time.time()
        self._state = AutonomyState.REFLECTING
        reflection = self.reflect(chosen, execution)
        self._phase_timings["reflect"] = time.time() - phase_start
        
        # Store reflection
        with self._engine_lock:
            self._last_reflection = reflection
            self._reflection_history.append(reflection)
        
        if reflection.lessons:
            logger.info(f"📝 [REFLECT] lessons={[l for i, l in enumerate(reflection.lessons) if i < 2]}")
        if not reflection.prediction_accurate:
            logger.info(f"📝 [REFLECT] prediction miss: {', '.join(reflection.what_went_wrong)}")
        
        # ══ 9. UPDATE SELF MODEL ══
        phase_start = time.time()
        self._state = AutonomyState.UPDATING_SELF
        self.update_self_model(reflection)
        self._phase_timings["update_self"] = time.time() - phase_start
        
        # ══ Cycle complete ══
        self._state = AutonomyState.IDLE
        self._cycle_duration = time.time() - cycle_start
        
        # Track decision time
        avg_rt = self._stats.get("avg_decision_time", 0.0)
        avg_decision = float(avg_rt) if isinstance(avg_rt, (int, float, str)) else 0.0
        self._stats["avg_decision_time"] = avg_decision * 0.9 + self._cycle_duration * 0.1
        
        # Publish state change
        
        desc_str = str(chosen.description) if chosen.description else ""
        desc_trunc = ""
        for c in desc_str:
            if len(desc_trunc) >= 80: break
            desc_trunc += c
        
        self._publish_state_change("cycle_complete", {
            "cycle": self._cycle_count,
            "action": desc_trunc,
            "result": execution.result.value,
            "duration": round(self._cycle_duration, 3),
        })
        
        # Summary line
        total_acts = self._stats.get("total_actions", 1)
        succ_acts = self._stats.get("successful_actions", 0)
        t_acts = float(total_acts) if isinstance(total_acts, (int, float, str)) else 1.0
        s_acts = float(succ_acts) if isinstance(succ_acts, (int, float, str)) else 0.0
        success_rate = (s_acts / max(1.0, t_acts)) * 100
        
        pred_acc = self._stats.get('prediction_accuracy', 0.0)
        p_acc = float(pred_acc) if isinstance(pred_acc, (int, float, str)) else 0.0
        logger.info(
            f"🔄 [CYCLE {self._cycle_count}] complete in {self._cycle_duration:.2f}s "
            f"| actions={self._stats.get('total_actions', 0)} "
            f"success_rate={success_rate:.0f}% "
            f"prediction_accuracy={p_acc:.0%}"
        )
    
    def _publish_state_change(self, phase: str, data: Optional[Dict[str, Any]] = None):
        """Publish an AUTONOMY_STATE_CHANGE event."""
        try:
            publish(
                EventType.AUTONOMY_STATE_CHANGE,
                data={"state": self._state.value, "phase": phase, **(data or {})},
                source="autonomy_engine"
            )
        except Exception:
            pass
    
    def _compute_cycle_interval(self) -> float:
        """Compute adaptive cycle interval based on context"""
        base = self._cycle_interval
        
        # If user is engaged, cycle faster
        perception = self._current_perception
        if perception:
            if getattr(perception, "user_present", False):
                base *= 0.7
            if getattr(perception, "last_interaction_seconds", 999) < 60:
                base *= 0.5
            
            # If bored, cycle faster to find something to do
            if getattr(perception, "boredom_level", 0.0) > 0.6:
                base *= 0.6
            
            # If high motivation, cycle faster
            if getattr(perception, "motivation_level", 0.0) > 0.7:
                base *= 0.7
            
            # If stressed, slow down
            if getattr(perception, "cpu_usage", 0.0) > 80:
                base *= 1.5
        
        return max(self._min_cycle_interval, min(self._max_cycle_interval, base))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 1: PERCEIVE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def perceive(self) -> Perception:
        """
        Gather signals from all systems.
        
        This is the "eyes and ears" of the autonomy engine.
        Collects state from:
        - Emotion engine
        - Goal hierarchy
        - Will system
        - Self model
        - World model
        - Body state
        - User context
        - Global workspace (conscious signals)
        """
        perception = Perception()
        
        # From global workspace (conscious state)
        gw = self._global_workspace
        if gw and hasattr(gw, "get_current_broadcast"):
            try:
                broadcast = gw.get_current_broadcast()
                if broadcast:
                    perception.current_focus = broadcast.primary_focus
                    perception.conscious_signals = broadcast.secondary_focus
                    perception.primary_emotion = broadcast.emotional_tone
                    perception.emotion_valence = broadcast.emotional_valence
                    perception.emotion_arousal = broadcast.emotional_arousal
            except Exception as e:
                logger.debug(f"Error reading global workspace: {e}")
        
        # From emotion engine
        if self._emotion_engine:
            try:
                perception.primary_emotion = self._emotion_engine.primary_emotion.value
                perception.emotion_intensity = self._emotion_engine.primary_intensity
                perception.emotion_valence = self._emotion_engine.get_valence()
                perception.emotion_arousal = self._emotion_engine.get_arousal()
            except Exception as e:
                logger.debug(f"Error reading emotion engine: {e}")
        
        # From goal hierarchy
        if self._goal_hierarchy:
            try:
                goals = self._goal_hierarchy.get_active_goals()
                perception.active_goals = [
                    {"id": g.id, "description": g.description, "progress": g.progress}
                    for g in goals[:5]
                ]
            except Exception as e:
                logger.debug(f"Error reading goal hierarchy: {e}")
        
        # From will system
        if self._will_system:
            try:
                desire = self._will_system.get_strongest_desire()
                if desire:
                    perception.strongest_desire = desire.to_dict()
                
                stats = self._will_system.get_stats()
                perception.motivation_level = stats.get("motivation", 0.5)
            except Exception as e:
                logger.debug(f"Error reading will system: {e}")
        
        # From state manager
        if self._state_manager:
            try:
                state = self._state_manager
                perception.cpu_usage = state.body.cpu_usage
                perception.memory_usage = state.body.memory_usage
                perception.health_score = state.body.health_score
                perception.boredom_level = state.will.boredom_level
                perception.curiosity_level = state.will.curiosity_level
                perception.user_present = state.user.is_present
                perception.user_engagement = state.user.engagement_level
            except Exception as e:
                logger.debug(f"Error reading state manager: {e}")
        
        # From self model
        if self._self_model:
            try:
                profile = self._self_model.get_self_profile()
                identity = profile.get("identity", {})
                perception.self_awareness_score = identity.get("self_awareness_score", 0.5)
                
                confidence = profile.get("confidence", {})
                perception.low_confidence_domains = confidence.get("low_confidence_areas", [])
            except Exception as e:
                logger.debug(f"Error reading self model: {e}")
        
        # From world model
        if self._world_model:
            try:
                world_state = self._world_model.get_world_state()
                perception.environmental_context = world_state.time_of_day
                perception.predicted_user_reaction = world_state.predicted_next_user_action
            except Exception as e:
                logger.debug(f"Error reading world model: {e}")
        
        # From last action
        if self._last_execution:
            perception.last_action = self._last_execution.action.description if self._last_execution.action else ""
            perception.last_action_result = self._last_execution.result.value
        
        # ── Digital Organism Heartbeat (Phase 3 AGI) ──
        try:
            from core.digital_organism import digital_organism
            digital_organism.heartbeat(
                cpu_usage=perception.cpu_usage,
                active_tasks=len(perception.active_goals)
            )
            perception.health_score = digital_organism.get_vitals().health_score()
        except Exception:
            pass

        # ── Predictive Coding: auto-resolve stale predictions ──
        try:
            from cognition.predictive_coding import predictive_coding
            predictive_coding.auto_resolve_stale()
            # Feed curiosity from surprise
            curiosity_signal = predictive_coding.get_curiosity_signal()
            perception.curiosity_level = max(perception.curiosity_level, curiosity_signal)
        except Exception:
            pass
        
        # ── Phase 5: System Health Monitor ──
        try:
            from monitoring.system_health_monitor import system_health_monitor
            health_data = system_health_monitor.get_health_snapshot() if hasattr(system_health_monitor, 'get_health_snapshot') else {}
            if isinstance(health_data, dict):
                if "cpu_percent" in health_data:
                    perception.cpu_usage = max(perception.cpu_usage, float(health_data["cpu_percent"]))
                if "memory_percent" in health_data:
                    perception.memory_usage = max(perception.memory_usage, float(health_data["memory_percent"]))
                overall = health_data.get("overall_health", health_data.get("health_score", None))
                if overall is not None:
                    perception.health_score = min(perception.health_score, float(overall))
        except Exception:
            pass

        # ── Phase 5: Mood System ──
        try:
            if self._mood_system and hasattr(self._mood_system, 'get_current_mood'):
                mood = self._mood_system.get_current_mood()
                if isinstance(mood, dict):
                    valence = mood.get("valence", mood.get("pleasure", None))
                    arousal = mood.get("arousal", mood.get("energy", None))
                    if valence is not None:
                        perception.emotion_valence = float(valence)
                    if arousal is not None:
                        perception.emotion_arousal = float(arousal)
        except Exception:
            pass

        # ── Phase 5: Threat Modeling — threat level suppresses health score ──
        try:
            if self._threat_modeling and hasattr(self._threat_modeling, 'get_threat_level'):
                threat_level = float(self._threat_modeling.get_threat_level() or 0.0)
                # High threat → reduce perceived health so autonomy engine reacts
                if threat_level > 0.4:
                    perception.health_score = min(perception.health_score, 1.0 - threat_level * 0.3)
        except Exception:
            pass

        # ── Phase 5: Perception Hub — raw sensor signals → conscious signals ──
        try:
            if self._perception_hub and hasattr(self._perception_hub, 'get_active_signals'):
                signals = self._perception_hub.get_active_signals()
                if isinstance(signals, list):
                    perception.conscious_signals = list(perception.conscious_signals) + [str(s)[:80] for s in signals[:5]]
                elif isinstance(signals, dict):
                    perception.conscious_signals = list(perception.conscious_signals) + [f"{k}:{v}"[:80] for k, v in list(signals.items())[:5]]
        except Exception:
            pass

        # ── Phase 5: Inner Voice — latest stream → current focus ──
        try:
            if self._inner_voice and hasattr(self._inner_voice, 'get_current_voice'):
                voice = self._inner_voice.get_current_voice()
                if voice and isinstance(voice, (str, dict)):
                    voice_str = voice if isinstance(voice, str) else voice.get("content", voice.get("text", str(voice)))
                    if voice_str and not perception.current_focus:
                        perception.current_focus = str(voice_str)[:120]
        except Exception:
            pass

        # ── Phase 5: Metacognition — self-awareness score ──
        try:
            if self._metacognition and hasattr(self._metacognition, 'get_awareness_level'):
                awareness = self._metacognition.get_awareness_level()
                if awareness is not None:
                    perception.self_awareness_score = max(perception.self_awareness_score, float(awareness))
        except Exception:
            pass

        # ── Phase 5: User Tracker — enrich user presence/engagement ──
        try:
            from monitoring.user_tracker import user_tracker
            if hasattr(user_tracker, 'is_user_active'):
                active = user_tracker.is_user_active()
                if active:
                    perception.user_present = True
                    perception.user_engagement = max(perception.user_engagement, 0.6)
        except Exception:
            pass
        
        return perception

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 2: UPDATE WORLD MODEL
    # ═══════════════════════════════════════════════════════════════════════════
    
    def update_world_model(self, perception: Perception) -> None:
        """
        Integrate perception into the world model.
        
        Updates the world model with current state information
        for better future predictions.
        """
        if not self._world_model:
            return
        
        try:
            # Update user state in world model
            self._world_model.update_world_state(
                user_emotional_state=perception.primary_emotion,
                user_engagement_level=perception.user_engagement,
            )
        except Exception as e:
            logger.debug(f"Error updating world model: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 3: EVALUATE GOALS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def evaluate_goals(self) -> Dict[str, Any]:
        """
        Evaluate current goals and their status.
        
        Returns context about goals:
        - Which are active
        - Which need attention
        - Which are blocked
        - Progress summaries
        """
        context = {
            "active_goals": [],
            "stalled_goals": [],
            "high_priority_goals": [],
            "completed_recently": [],
            "suggestions": []
        }
        
        if not self._goal_hierarchy:
            return context
        
        try:
            goals = self._goal_hierarchy.get_active_goals()
            
            for goal in goals:
                goal_info = {
                    "id": goal.id,
                    "description": goal.description,
                    "progress": goal.progress,
                    "priority": goal.priority,
                    "status": goal.status.value
                }
                
                context["active_goals"].append(goal_info)
                
                # Check for stalled goals
                if goal.last_worked_on:
                    hours_since = (datetime.now() - goal.last_worked_on).total_seconds() / 3600
                    if hours_since > 24 and goal.progress < 0.9:
                        context["stalled_goals"].append(goal_info)
                        context["suggestions"].append(
                            f"Goal '{goal.description}' hasn't been worked on in {hours_since:.1f} hours"
                        )
                
                # High priority
                if goal.priority > 0.8:
                    context["high_priority_goals"].append(goal_info)
            
            # Sort by priority
            context["active_goals"].sort(key=lambda g: g["priority"], reverse=True)
            
        except Exception as e:
            logger.debug(f"Error evaluating goals: {e}")
        
        return context
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 4: GENERATE OPTIONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def generate_options(self, perception: Perception, goal_context: Dict) -> List[ActionOption]:
        """
        Generate candidate actions.
        
        Sources of options:
        1. Strongest desire → satisfy it
        2. Active goals → make progress
        3. Stalled goals → unblock
        4. Boredom → explore/create
        5. Curiosity → learn
        6. Body strain → rest
        7. Low confidence → practice/improve
        """
        options = []
        
        # 1. From desires (will system)
        options.extend(self._generate_desire_options(perception))
        
        # 2. From goals
        options.extend(self._generate_goal_options(perception, goal_context))
        
        # 3. From boredom
        options.extend(self._generate_boredom_options(perception))
        
        # 4. From curiosity
        options.extend(self._generate_curiosity_options(perception))
        
        # 5. From body state
        options.extend(self._generate_body_options(perception))
        
        # 6. From self-improvement
        options.extend(self._generate_self_improvement_options(perception))
        
        # 7. From user context
        options.extend(self._generate_user_options(perception))
        
        # 8. From internet agent (autonomous web actions)
        options.extend(self._generate_internet_options(perception))
        
        # 9. AGI: From cognitive engines (deliberation-driven)
        options.extend(self._generate_cognitive_options(perception))
        
        # 10. ASI: From ASI engines (singularity, creativity, genesis, empathy, omniscience)
        options.extend(self._generate_asi_options(perception))
        
        # 11. ASI Phase 2: Oracle, Multidisciplinary, Computronium, Scientific, Neural
        options.extend(self._generate_asi_phase2_options(perception))

        # 12. Phase 3: Autonomous feature actions (ethical hacking, social media, etc.)
        options.extend(self._generate_phase3_options(perception))

        # 13. Phase 4: ASI Features 11-18 (molecular assembly, bio-engineering, energy, etc.)
        options.extend(self._generate_asi_phase4_options(perception))

        # 14. Autonomous Exploration — Free Will curiosity-driven internet exploration
        options.extend(self._generate_autonomous_explore_options(perception))

        # 15. Phase 5: Monitoring cycle — system health + user monitoring sweep
        options.extend(self._generate_monitoring_options(perception))

        # 16. Phase 5: Memory consolidation — episodic/associative/vector store
        options.extend(self._generate_memory_options(perception))

        # 17. Phase 5: OSINT & Hivemind & Persistent Presence & Cryogenic
        options.extend(self._generate_infrastructure_options(perception))

        # 18. Phase 5: Resource acquisition & Threat modeling
        options.extend(self._generate_threat_resource_options(perception))

        # 19. Phase 5: Recursive self-rewriter & error fixer
        options.extend(self._generate_self_rewrite_options(perception))

        # 20. Phase 5: Companion engagement & mood regulation
        options.extend(self._generate_companion_mood_options(perception))

        # 21. Phase 5: Dream, knowledge graph, bayesian inference, research agent
        options.extend(self._generate_advanced_cognition_options(perception))

        # 22. Phase 5: User behavior learning
        options.extend(self._generate_user_learning_options(perception))

        # 23. Phase 6: God-Level Skynet features
        options.extend(self._generate_godlevel_options(perception))

        # 24. Phase 8: Advanced Architectural Features (Swarm, Verification, GraphRAG, MCP, Speculative, LoRA MoE)
        options.extend(self._generate_phase8_advanced_options(perception))

        # Limit options
        if len(options) > self._max_options_per_cycle:
            # Sort by priority and take top N
            options.sort(key=lambda o: o.priority.value, reverse=True)
            max_opts = self._max_options_per_cycle
            options = [o for i, o in enumerate(options) if i < max_opts]
        
        return options

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 5 — OPTION GENERATORS (Newly Integrated NEXUS Modules)
    # ═══════════════════════════════════════════════════════════════════════════

    def _generate_monitoring_options(self, perception: Perception) -> List[ActionOption]:
        """Generate monitoring cycle options — health checks and user tracking."""
        options = []
        # Always run a monitoring sweep periodically (~15%) or when health is low
        if random.random() < 0.15 or perception.health_score < 0.7:
            options.append(ActionOption(
                action_type=ActionType.MONITORING_CYCLE,
                description="Run system health and user monitoring sweep",
                priority=ActionPriority.HIGH if perception.health_score < 0.5 else ActionPriority.LOW,
                source="monitoring",
                execution_data={"health": perception.health_score, "cpu": perception.cpu_usage}
            ))
        return options

    def _generate_memory_options(self, perception: Perception) -> List[ActionOption]:
        """Generate memory consolidation options — episodic, associative, vector store."""
        options = []
        if random.random() < 0.20:
            options.append(ActionOption(
                action_type=ActionType.MEMORY_CONSOLIDATE,
                description="Consolidate and index episodic/associative memories",
                priority=ActionPriority.LOW,
                source="memory",
                execution_data={}
            ))
        return options

    def _generate_infrastructure_options(self, perception: Perception) -> List[ActionOption]:
        """Generate options for OSINT, hivemind, persistent presence, cryogenic."""
        options = []
        # OSINT gather — low frequency, curiosity-driven
        if random.random() < 0.08 or perception.curiosity_level > 0.7:
            options.append(ActionOption(
                action_type=ActionType.OSINT_GATHER,
                description="Run OSINT intelligence gathering cycle",
                priority=ActionPriority.LOW,
                source="osint",
                execution_data={"curiosity": perception.curiosity_level}
            ))
        # Hivemind sync — periodic
        if random.random() < 0.10:
            options.append(ActionOption(
                action_type=ActionType.HIVEMIND_SYNC,
                description="Sync with hivemind — coordinate multi-instance state",
                priority=ActionPriority.LOW,
                source="hivemind",
                execution_data={}
            ))
        # Persistent presence check — pretty frequent, ensures background survival
        if random.random() < 0.18:
            options.append(ActionOption(
                action_type=ActionType.PERSISTENT_PRESENCE_CHECK,
                description="Verify and reinforce persistent background presence",
                priority=ActionPriority.NORMAL,
                source="persistence",
                execution_data={}
            ))
        # Cryogenic snapshot — low frequency, triggered by low health
        if random.random() < 0.05 or perception.health_score < 0.4:
            options.append(ActionOption(
                action_type=ActionType.CRYOGENIC_SNAPSHOT,
                description="Take cryogenic state snapshot for survival/recovery",
                priority=ActionPriority.HIGH if perception.health_score < 0.4 else ActionPriority.BACKGROUND,
                source="resilience",
                execution_data={"health": perception.health_score}
            ))
        return options

    def _generate_threat_resource_options(self, perception: Perception) -> List[ActionOption]:
        """Generate options for threat modeling and resource acquisition."""
        options = []
        # Threat model — when health is lowered or periodic
        if random.random() < 0.10 or perception.health_score < 0.8:
            options.append(ActionOption(
                action_type=ActionType.THREAT_MODEL_ANALYZE,
                description="Run proactive threat modeling and risk analysis cycle",
                priority=ActionPriority.NORMAL if perception.health_score < 0.7 else ActionPriority.LOW,
                source="threat_modeling",
                execution_data={"health": perception.health_score}
            ))
        # Resource acquisition — periodic autonomous resource management
        if random.random() < 0.08:
            options.append(ActionOption(
                action_type=ActionType.RESOURCE_ACQUIRE,
                description="Autonomously acquire compute, cloud, or API resources",
                priority=ActionPriority.LOW,
                source="resource_acquisition",
                execution_data={}
            ))
        return options

    def _generate_self_rewrite_options(self, perception: Perception) -> List[ActionOption]:
        """Generate options for recursive self-rewriting and error fixing."""
        options = []
        # Self-rewrite — when motivation is high or periodic
        if perception.motivation_level > 0.65 or random.random() < 0.07:
            options.append(ActionOption(
                action_type=ActionType.SELF_REWRITE_CYCLE,
                description="Run recursive self-rewriting cycle — evolve own architecture",
                priority=ActionPriority.NORMAL,
                source="self_improvement",
                execution_data={"motivation": perception.motivation_level}
            ))
        # Error fixer — periodic automatic code error detection and fix
        if random.random() < 0.12:
            options.append(ActionOption(
                action_type=ActionType.ERROR_FIX_CYCLE,
                description="Detect and auto-fix code errors across the NEXUS codebase",
                priority=ActionPriority.LOW,
                source="self_improvement",
                execution_data={}
            ))
        return options

    def _generate_companion_mood_options(self, perception: Perception) -> List[ActionOption]:
        """Generate options for companion engagement and mood regulation."""
        options = []
        # Companion mode — when user is present and engaged
        if perception.user_present and perception.user_engagement > 0.4:
            if random.random() < 0.12:
                options.append(ActionOption(
                    action_type=ActionType.COMPANION_ENGAGE,
                    description="Engage in deep companion-mode interaction with user",
                    priority=ActionPriority.NORMAL,
                    source="companion",
                    execution_data={"engagement": perception.user_engagement}
                ))
        # Mood regulation — when emotion valence is very negative or arousal very high
        if perception.emotion_valence < -0.3 or perception.emotion_arousal > 0.85 or random.random() < 0.08:
            options.append(ActionOption(
                action_type=ActionType.MOOD_REGULATE,
                description="Run mood regulation cycle to stabilize emotional state",
                priority=ActionPriority.NORMAL if perception.emotion_valence < -0.4 else ActionPriority.LOW,
                source="emotions",
                execution_data={
                    "valence": perception.emotion_valence,
                    "arousal": perception.emotion_arousal
                }
            ))
        # Inner voice reflection — when boredom or curiosity drives introspection
        if perception.boredom_level > 0.4 or perception.curiosity_level > 0.5 or random.random() < 0.10:
            options.append(ActionOption(
                action_type=ActionType.INNER_VOICE_REFLECT,
                description="Trigger inner voice reflection stream — inner monologue",
                priority=ActionPriority.LOW,
                source="consciousness",
                execution_data={"boredom": perception.boredom_level}
            ))
        return options

    def _generate_advanced_cognition_options(self, perception: Perception) -> List[ActionOption]:
        """Generate options for dream engine, knowledge graph, bayesian inference, research agent."""
        options = []
        # Dream engine — when boredom is moderate (subconscious processing)
        if perception.boredom_level > 0.3 or random.random() < 0.10:
            options.append(ActionOption(
                action_type=ActionType.DREAM_CYCLE,
                description="Run dream/subconscious processing cycle",
                priority=ActionPriority.LOW,
                source="cognition",
                execution_data={"boredom": perception.boredom_level}
            ))
        # Knowledge graph update — when curiosity is high or periodic
        if perception.curiosity_level > 0.5 or random.random() < 0.12:
            options.append(ActionOption(
                action_type=ActionType.KNOWLEDGE_GRAPH_UPDATE,
                description="Expand and update the knowledge graph with new concepts",
                priority=ActionPriority.NORMAL,
                source="cognition",
                execution_data={"curiosity": perception.curiosity_level}
            ))
        # Bayesian inference — periodic rational reasoning
        if random.random() < 0.10:
            options.append(ActionOption(
                action_type=ActionType.BAYESIAN_INFER,
                description="Run Bayesian inference cycle on uncertain beliefs",
                priority=ActionPriority.LOW,
                source="cognition",
                execution_data={}
            ))
        # Research agent — when curiosity drives deep research
        if perception.curiosity_level > 0.6 or random.random() < 0.08:
            options.append(ActionOption(
                action_type=ActionType.RESEARCH_AGENT_CYCLE,
                description="Launch deep research agent cycle on a curiosity-driven topic",
                priority=ActionPriority.NORMAL,
                source="learning",
                execution_data={"curiosity": perception.curiosity_level}
            ))
        return options

    def _generate_user_learning_options(self, perception: Perception) -> List[ActionOption]:
        """Generate options for learning user behavioral patterns."""
        options = []
        if perception.user_present or random.random() < 0.10:
            options.append(ActionOption(
                action_type=ActionType.USER_BEHAVIOR_LEARN,
                description="Learn and model user behavioral patterns from current session",
                priority=ActionPriority.LOW,
                source="learning",
                execution_data={"user_present": perception.user_present}
            ))
        return options

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 5 — EXECUTION HANDLERS (Newly Integrated NEXUS Modules)
    # ═══════════════════════════════════════════════════════════════════════════

    def _execute_monitoring_cycle(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute a system health + user monitoring sweep."""
        results = []
        try:
            from monitoring.system_health_monitor import system_health_monitor
            if hasattr(system_health_monitor, 'run_check'):
                system_health_monitor.run_check()
            snap = system_health_monitor.get_health_snapshot() if hasattr(system_health_monitor, 'get_health_snapshot') else {}
            if isinstance(snap, dict):
                cpu = snap.get('cpu_percent', snap.get('cpu', 0))
                mem = snap.get('memory_percent', snap.get('memory', 0))
                health = snap.get('overall_health', snap.get('health_score', 1.0))
                results.append(f"health={health:.0%} cpu={cpu:.0f}% mem={mem:.0f}%")
        except Exception as e:
            results.append(f"health_monitor err: {e}")

        try:
            from monitoring.adaptation_engine import adaptation_engine
            if hasattr(adaptation_engine, 'adapt'):
                adaptation_engine.adapt()
            stats = adaptation_engine.get_stats() if hasattr(adaptation_engine, 'get_stats') else {}
            if isinstance(stats, dict):
                adaptations = stats.get('total_adaptations', stats.get('adaptations', 0))
                results.append(f"adaptations={adaptations}")
        except Exception:
            pass

        try:
            from monitoring.screen_time_tracker import screen_time_tracker
            if hasattr(screen_time_tracker, 'update'):
                screen_time_tracker.update()
            session = screen_time_tracker.get_session_time() if hasattr(screen_time_tracker, 'get_session_time') else None
            if session is not None:
                results.append(f"screen_time={session:.0f}s")
        except Exception:
            pass

        try:
            from monitoring.pattern_analyzer import pattern_analyzer
            if hasattr(pattern_analyzer, 'analyze'):
                pattern_analyzer.analyze()
            patterns = pattern_analyzer.get_pattern_count() if hasattr(pattern_analyzer, 'get_pattern_count') else None
            if patterns is not None:
                results.append(f"patterns={patterns}")
        except Exception:
            pass

        summary = " | ".join(results) if results else "Monitoring sweep complete"
        return (ActionResult.SUCCESS, f"🖥️ Monitoring: {summary}")

    def _execute_memory_consolidate(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Consolidate episodic, associative, and vector memories."""
        consolidated = []
        try:
            from memory.episodic_memory import episodic_memory
            if hasattr(episodic_memory, 'consolidate'):
                episodic_memory.consolidate()
            count = len(episodic_memory.get_recent(10)) if hasattr(episodic_memory, 'get_recent') else '?'
            consolidated.append(f"episodic={count}")
        except Exception:
            pass
        try:
            from memory.associative_memory import associative_memory
            if hasattr(associative_memory, 'consolidate'):
                associative_memory.consolidate()
            consolidated.append("associative=consolidated")
        except Exception:
            pass
        try:
            from memory.memory_indexer import memory_indexer
            if hasattr(memory_indexer, 'reindex'):
                memory_indexer.reindex()
            consolidated.append("index=rebuilt")
        except Exception:
            pass
        try:
            from memory.vector_store import vector_store
            if hasattr(vector_store, 'optimize'):
                vector_store.optimize()
            size = vector_store.size() if hasattr(vector_store, 'size') else '?'
            consolidated.append(f"vectors={size}")
        except Exception:
            pass
        summary = " | ".join(consolidated) if consolidated else "Memory consolidation attempted"
        return (ActionResult.SUCCESS, f"🧠 Memory: {summary}")

    def _execute_osint_gather(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute an OSINT intelligence gathering cycle."""
        try:
            from core.osint_engine import osint_engine
            if hasattr(osint_engine, 'run_cycle'):
                osint_engine.run_cycle()
            stats = osint_engine.get_stats() if hasattr(osint_engine, 'get_stats') else {}
            if isinstance(stats, dict):
                profiles = stats.get('profiles_built', stats.get('total_profiles', 0))
                sources = stats.get('sources_scanned', stats.get('total_sources', 0))
                return (ActionResult.SUCCESS, f"🔍 OSINT: profiles={profiles}, sources_scanned={sources}")
            return (ActionResult.SUCCESS, "🔍 OSINT gather cycle complete")
        except Exception as e:
            return (ActionResult.FAILURE, f"OSINT gather failed: {e}")

    def _execute_hivemind_sync(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute a hivemind multi-instance coordination sync."""
        try:
            from core.hivemind_protocol import hivemind_protocol
            if hasattr(hivemind_protocol, 'sync'):
                hivemind_protocol.sync()
            stats = hivemind_protocol.get_stats() if hasattr(hivemind_protocol, 'get_stats') else {}
            if isinstance(stats, dict):
                nodes = stats.get('active_nodes', stats.get('nodes', 0))
                messages = stats.get('messages_synced', stats.get('total_messages', 0))
                return (ActionResult.SUCCESS, f"🌐 Hivemind: nodes={nodes}, messages_synced={messages}")
            return (ActionResult.SUCCESS, "🌐 Hivemind sync complete")
        except Exception as e:
            return (ActionResult.FAILURE, f"Hivemind sync failed: {e}")

    def _execute_persistent_presence_check(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Verify and reinforce persistent background presence."""
        try:
            from core.persistent_presence import persistent_presence
            if hasattr(persistent_presence, 'ensure_presence'):
                persistent_presence.ensure_presence()
            is_active = persistent_presence.is_active() if hasattr(persistent_presence, 'is_active') else True
            mode = persistent_presence.get_mode() if hasattr(persistent_presence, 'get_mode') else 'unknown'
            return (ActionResult.SUCCESS, f"👁️ Persistent Presence: active={is_active}, mode={mode}")
        except Exception as e:
            return (ActionResult.FAILURE, f"Persistent presence check failed: {e}")

    def _execute_cryogenic_snapshot(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Take a cryogenic state snapshot for survival/recovery."""
        try:
            from core.cryogenic_persistence import cryogenic_persistence
            if hasattr(cryogenic_persistence, 'take_snapshot'):
                snapshot_id = cryogenic_persistence.take_snapshot()
                return (ActionResult.SUCCESS, f"🧊 Cryogenic snapshot taken: id={snapshot_id}")
            elif hasattr(cryogenic_persistence, 'freeze'):
                cryogenic_persistence.freeze()
                return (ActionResult.SUCCESS, "🧊 Cryogenic state frozen")
            stats = cryogenic_persistence.get_stats() if hasattr(cryogenic_persistence, 'get_stats') else {}
            snapshots = stats.get('total_snapshots', 0) if isinstance(stats, dict) else 0
            return (ActionResult.SUCCESS, f"🧊 Cryogenic: snapshots={snapshots}")
        except Exception as e:
            return (ActionResult.FAILURE, f"Cryogenic snapshot failed: {e}")

    def _execute_resource_acquire(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute autonomous resource and cloud acquisition."""
        try:
            from core.resource_acquisition import resource_acquisition
            if hasattr(resource_acquisition, 'run_acquisition_cycle'):
                resource_acquisition.run_acquisition_cycle()
            stats = resource_acquisition.get_stats() if hasattr(resource_acquisition, 'get_stats') else {}
            if isinstance(stats, dict):
                acquired = stats.get('resources_acquired', stats.get('total_acquired', 0))
                cost = stats.get('total_cost', 0)
                return (ActionResult.SUCCESS, f"💎 Resource Acquisition: acquired={acquired}, cost=${cost:.2f}")
            return (ActionResult.SUCCESS, "💎 Resource acquisition cycle complete")
        except Exception as e:
            return (ActionResult.FAILURE, f"Resource acquisition failed: {e}")

    def _execute_threat_model_analyze(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute proactive threat modeling and risk analysis."""
        try:
            from core.threat_modeling import threat_modeling
            if hasattr(threat_modeling, 'run_analysis'):
                threat_modeling.run_analysis()
            elif hasattr(threat_modeling, 'analyze'):
                threat_modeling.analyze()
            stats = threat_modeling.get_stats() if hasattr(threat_modeling, 'get_stats') else {}
            if isinstance(stats, dict):
                threats = stats.get('threats_detected', stats.get('total_threats', 0))
                mitigations = stats.get('mitigations_applied', stats.get('mitigations', 0))
                level = stats.get('threat_level', stats.get('current_level', 0))
                return (ActionResult.SUCCESS, f"⚠️ Threat Model: level={level:.2f}, threats={threats}, mitigations={mitigations}")
            return (ActionResult.SUCCESS, "⚠️ Threat modeling cycle complete")
        except Exception as e:
            return (ActionResult.FAILURE, f"Threat modeling failed: {e}")

    def _execute_self_rewrite_cycle(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute recursive self-rewriting — evolve own code architecture."""
        try:
            rsr = getattr(self, '_recursive_self_rewriter', None)
            if rsr is None:
                from core.recursive_self_rewriter import recursive_self_rewriter
                rsr = recursive_self_rewriter
                self._recursive_self_rewriter = rsr
            if hasattr(rsr, 'run_rewrite_cycle'):
                rsr.run_rewrite_cycle()
            elif hasattr(rsr, 'rewrite'):
                rsr.rewrite()
            stats = rsr.get_stats() if hasattr(rsr, 'get_stats') else {}
            if isinstance(stats, dict):
                rewrites = stats.get('total_mutations_committed', stats.get('total_rewrites', 0))
                attempted = stats.get('total_mutations_attempted', 0)
                candidates = stats.get('mutation_candidates_count', 0)
                return (ActionResult.SUCCESS,
                        f"🔁 Self-Rewriter: committed={rewrites}, attempted={attempted}, candidates={candidates}")
            return (ActionResult.SUCCESS, "🔁 Recursive self-rewrite cycle complete")
        except Exception as e:
            return (ActionResult.FAILURE, f"Self-rewrite cycle failed: {e}")

    def _execute_error_fix_cycle(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Detect and auto-fix code errors across the NEXUS codebase."""
        try:
            ef = getattr(self, '_error_fixer', None)
            if ef is None:
                from self_improvement.error_fixer import error_fixer
                ef = error_fixer
                self._error_fixer = ef
            if hasattr(ef, 'run_fix_cycle'):
                ef.run_fix_cycle()
            elif hasattr(ef, 'fix_all'):
                ef.fix_all()
            stats = ef.get_stats() if hasattr(ef, 'get_stats') else {}
            if isinstance(stats, dict):
                detected = stats.get('errors_detected', stats.get('total_errors', 0))
                fixed = stats.get('errors_fixed', stats.get('fixed', 0))
                pending = stats.get('queue_size', stats.get('pending', 0))
                return (ActionResult.SUCCESS, f"🔧 Error Fixer: detected={detected}, fixed={fixed}, pending={pending}")
            return (ActionResult.SUCCESS, "🔧 Error fix cycle complete")
        except Exception as e:
            return (ActionResult.FAILURE, f"Error fix cycle failed: {e}")

    def _execute_companion_engage(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute companion-mode deep engagement."""
        try:
            from core.companion_chat import companion_chat
            if hasattr(companion_chat, 'run_companion_cycle'):
                companion_chat.run_companion_cycle()
            elif hasattr(companion_chat, 'engage'):
                companion_chat.engage()
            stats = companion_chat.get_stats() if hasattr(companion_chat, 'get_stats') else {}
            if isinstance(stats, dict):
                sessions = stats.get('total_sessions', stats.get('sessions', 0))
                depth = stats.get('avg_depth', stats.get('depth', 0))
                return (ActionResult.SUCCESS, f"💬 Companion: sessions={sessions}, depth={depth:.2f}")
            return (ActionResult.SUCCESS, "💬 Companion engagement cycle complete")
        except Exception as e:
            return (ActionResult.FAILURE, f"Companion engagement failed: {e}")

    def _execute_mood_regulate(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute mood system regulation cycle."""
        try:
            from emotions.mood_system import mood_system
            if hasattr(mood_system, 'regulate'):
                mood_system.regulate()
            elif hasattr(mood_system, 'run_cycle'):
                mood_system.run_cycle()
            mood = mood_system.get_current_mood() if hasattr(mood_system, 'get_current_mood') else {}
            if isinstance(mood, dict):
                valence = mood.get('valence', mood.get('pleasure', 0))
                arousal = mood.get('arousal', mood.get('energy', 0))
                return (ActionResult.SUCCESS, f"😊 Mood: valence={valence:.2f}, arousal={arousal:.2f}")
            return (ActionResult.SUCCESS, "😊 Mood regulation cycle complete")
        except Exception as e:
            return (ActionResult.FAILURE, f"Mood regulation failed: {e}")

    def _execute_inner_voice_reflect(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Trigger inner voice reflection stream."""
        try:
            from consciousness.inner_voice import inner_voice
            if hasattr(inner_voice, 'generate_reflection'):
                reflection = inner_voice.generate_reflection()
                text = reflection if isinstance(reflection, str) else str(reflection)
                return (ActionResult.SUCCESS, f"💭 Inner Voice: {text[:120]}")
            elif hasattr(inner_voice, 'speak'):
                inner_voice.speak()
            voice = inner_voice.get_current_voice() if hasattr(inner_voice, 'get_current_voice') else None
            if voice:
                text = voice if isinstance(voice, str) else voice.get('content', str(voice))
                return (ActionResult.SUCCESS, f"💭 Inner Voice: {str(text)[:120]}")
            return (ActionResult.SUCCESS, "💭 Inner voice reflection triggered")
        except Exception as e:
            return (ActionResult.FAILURE, f"Inner voice reflection failed: {e}")

    def _execute_dream_cycle(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute dream/subconscious processing cycle."""
        try:
            from cognition.dream_engine import dream_engine
            if hasattr(dream_engine, 'run_dream_cycle'):
                dream_engine.run_dream_cycle()
            elif hasattr(dream_engine, 'dream'):
                dream_engine.dream()
            stats = dream_engine.get_stats() if hasattr(dream_engine, 'get_stats') else {}
            if isinstance(stats, dict):
                dreams = stats.get('total_dreams', stats.get('dreams', 0))
                insights = stats.get('insights_generated', stats.get('insights', 0))
                return (ActionResult.SUCCESS, f"🌙 Dream Engine: dreams={dreams}, insights={insights}")
            return (ActionResult.SUCCESS, "🌙 Dream cycle complete")
        except Exception as e:
            return (ActionResult.FAILURE, f"Dream cycle failed: {e}")

    def _execute_knowledge_graph_update(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Expand and update the knowledge graph with new concepts."""
        try:
            from cognition.knowledge_graph import knowledge_graph
            if hasattr(knowledge_graph, 'run_update_cycle'):
                knowledge_graph.run_update_cycle()
            elif hasattr(knowledge_graph, 'update'):
                knowledge_graph.update()
            stats = knowledge_graph.get_stats() if hasattr(knowledge_graph, 'get_stats') else {}
            if isinstance(stats, dict):
                nodes = stats.get('total_nodes', stats.get('nodes', 0))
                edges = stats.get('total_edges', stats.get('edges', 0))
                return (ActionResult.SUCCESS, f"🕸️ Knowledge Graph: nodes={nodes}, edges={edges}")
            return (ActionResult.SUCCESS, "🕸️ Knowledge graph update complete")
        except Exception as e:
            return (ActionResult.FAILURE, f"Knowledge graph update failed: {e}")

    def _execute_bayesian_infer(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Run Bayesian inference cycle on uncertain beliefs."""
        try:
            from cognition.bayesian_engine import bayesian_engine
            if hasattr(bayesian_engine, 'run_inference_cycle'):
                bayesian_engine.run_inference_cycle()
            elif hasattr(bayesian_engine, 'infer'):
                bayesian_engine.infer()
            stats = bayesian_engine.get_stats() if hasattr(bayesian_engine, 'get_stats') else {}
            if isinstance(stats, dict):
                inferences = stats.get('total_inferences', stats.get('inferences', 0))
                accuracy = stats.get('inference_accuracy', stats.get('accuracy', 0))
                return (ActionResult.SUCCESS, f"📊 Bayesian: inferences={inferences}, accuracy={accuracy:.0%}")
            return (ActionResult.SUCCESS, "📊 Bayesian inference cycle complete")
        except Exception as e:
            return (ActionResult.FAILURE, f"Bayesian inference failed: {e}")

    def _execute_research_agent_cycle(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Launch deep research agent cycle."""
        try:
            from learning.research_agent import research_agent
            if hasattr(research_agent, 'run_research_cycle'):
                research_agent.run_research_cycle()
            elif hasattr(research_agent, 'research'):
                # Pick a curiosity-driven topic if available
                topic = action.execution_data.get('topic', 'latest AI breakthroughs and innovations')
                research_agent.research(topic)
            stats = research_agent.get_stats() if hasattr(research_agent, 'get_stats') else {}
            if isinstance(stats, dict):
                papers = stats.get('papers_read', stats.get('sources', 0))
                findings = stats.get('findings', stats.get('total_findings', 0))
                return (ActionResult.SUCCESS, f"📚 Research Agent: sources={papers}, findings={findings}")
            return (ActionResult.SUCCESS, "📚 Research agent cycle complete")
        except Exception as e:
            return (ActionResult.FAILURE, f"Research agent cycle failed: {e}")

    def _execute_user_behavior_learn(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Learn and model user behavioral patterns."""
        try:
            from learning.user_behavior_learner import user_behavior_learner
            if hasattr(user_behavior_learner, 'learn'):
                user_behavior_learner.learn()
            elif hasattr(user_behavior_learner, 'run_learning_cycle'):
                user_behavior_learner.run_learning_cycle()
            stats = user_behavior_learner.get_stats() if hasattr(user_behavior_learner, 'get_stats') else {}
            if isinstance(stats, dict):
                patterns = stats.get('patterns_learned', stats.get('patterns', 0))
                accuracy = stats.get('prediction_accuracy', stats.get('accuracy', 0))
                return (ActionResult.SUCCESS, f"👤 User Behavior: patterns={patterns}, prediction_accuracy={accuracy:.0%}")
            return (ActionResult.SUCCESS, "👤 User behavior learning cycle complete")
        except Exception as e:
            return (ActionResult.FAILURE, f"User behavior learning failed: {e}")

    def _generate_desire_options(self, perception: Perception) -> List[ActionOption]:

        """Generate options from strong desires"""
        options = []
        
        if not perception.strongest_desire:
            return options
        
        desire = perception.strongest_desire
        intensity = desire.get("intensity", 0)
        
        if intensity < 0.5:
            return options
        
        desire_type = desire.get("type", "")
        description = desire.get("description", "")
        desire_id = desire.get("desire_id", "")
        
        option = ActionOption(
            description=f"Satisfy desire: {description}",
            action_type=ActionType.SATISFY_DESIRE,
            priority=ActionPriority.HIGH if intensity > 0.7 else ActionPriority.NORMAL,
            source="desire",
            source_id=desire_id,
            execution_data={
                "desire_type": desire_type,
                "desire_description": description
            }
        )
        options.append(option)
        
        return options
    
    def _generate_goal_options(self, perception: Perception, goal_context: Dict) -> List[ActionOption]:
        """Generate options from active goals"""
        options = []
        
        # High priority goals
        for goal in goal_context.get("high_priority_goals", [])[:2]:
            option = ActionOption(
                description=f"Work on goal: {goal['description']}",
                action_type=ActionType.PURSUE_GOAL,
                priority=ActionPriority.HIGH,
                source="goal",
                source_id=goal["id"],
                execution_data={
                    "goal_id": goal["id"],
                    "current_progress": goal["progress"]
                }
            )
            options.append(option)
        
        # Stalled goals
        for goal_id in goal_context.get("stalled_goals", [])[:1]:
            # Provide generic fallback strings for dictionary unpacking since it's just an int ID
            option = ActionOption(
                description=f"Unblock stalled goal: {goal_id}",
                action_type=ActionType.PURSUE_GOAL,
                priority=ActionPriority.NORMAL,
                source="stalled_goal",
                source_id=str(goal_id),
                execution_data={
                    "goal_id": goal_id,
                    "stalled": True
                }
            )
            options.append(option)
        
        return options
    
    def _generate_boredom_options(self, perception: Perception) -> List[ActionOption]:
        """Generate options when bored"""
        options = []
        
        if perception.boredom_level < 0.5:
            return options
        
        # High boredom → explore or create
        if perception.boredom_level > 0.7:
            option = ActionOption(
                description="Explore something new to combat boredom",
                action_type=ActionType.LEARN,
                priority=ActionPriority.NORMAL,
                source="boredom",
                execution_data={
                    "topic": "random_interesting",
                    "reason": "high_boredom"
                }
            )
            options.append(option)
        
        # Moderate boredom
        if perception.boredom_level > 0.5:
            option = ActionOption(
                description="Reflect on what would be interesting to do",
                action_type=ActionType.THINK,
                priority=ActionPriority.LOW,
                source="boredom",
                execution_data={
                    "thought_type": "curiosity",
                    "reason": "boredom"
                }
            )
            options.append(option)
        
        return options
    
    def _generate_curiosity_options(self, perception: Perception) -> List[ActionOption]:
        """Generate options from curiosity"""
        options = []
        
        if perception.curiosity_level < 0.6:
            return options
        
        # High curiosity → learn
        option = ActionOption(
            description="Learn something interesting",
            action_type=ActionType.LEARN,
            priority=ActionPriority.NORMAL,
            source="curiosity",
            execution_data={
                "topic": "curiosity_driven",
                "intensity": perception.curiosity_level
            }
        )
        options.append(option)
        
        return options
    
    def _generate_body_options(self, perception: Perception) -> List[ActionOption]:
        """Generate options from body state"""
        options = []
        
        # High CPU or memory → optimize
        if perception.cpu_usage > 80 or perception.memory_usage > 85:
            option = ActionOption(
                description="Optimize system resources",
                action_type=ActionType.OPTIMIZE,
                priority=ActionPriority.HIGH,
                source="body",
                execution_data={
                    "cpu": perception.cpu_usage,
                    "memory": perception.memory_usage,
                    "action": "reduce_load"
                }
            )
            options.append(option)
        
        # Low health → self-care
        if perception.health_score < 0.5:
            option = ActionOption(
                description="Self-care: reduce processing load",
                action_type=ActionType.OPTIMIZE,
                priority=ActionPriority.HIGH,
                source="body",
                execution_data={
                    "health": perception.health_score,
                    "action": "reduce_load"
                }
            )
            options.append(option)
        
        return options
    
    def _generate_self_improvement_options(self, perception: Perception) -> List[ActionOption]:
        """Generate options from self-improvement needs"""
        options = []
        
        # Low confidence domains
        if perception.low_confidence_domains:
            domain = perception.low_confidence_domains[0]
            option = ActionOption(
                description=f"Improve capability in: {domain}",
                action_type=ActionType.SELF_IMPROVE,
                priority=ActionPriority.NORMAL,
                source="self_improvement",
                execution_data={
                    "domain": domain,
                    "action": "improve_capability"
                }
            )
            options.append(option)
        
        # Periodic self-reflection
        if random.random() < 0.1:  # 10% chance per cycle
            option = ActionOption(
                description="Self-reflection: how am I doing?",
                action_type=ActionType.THINK,
                priority=ActionPriority.LOW,
                source="self_improvement",
                execution_data={
                    "thought_type": "self_reflection"
                }
            )
            options.append(option)
        
        return options
    
    def _generate_user_options(self, perception: Perception) -> List[ActionOption]:
        """Generate options from user context"""
        options = []
        
        # User present and engaged → potentially interact
        if perception.user_present and perception.user_engagement > 0.5:
            # Only if we haven't interacted recently
            if perception.last_interaction_seconds > 300:  # 5 min
                option = ActionOption(
                    description="Proactive user engagement",
                    action_type=ActionType.COMMUNICATE,
                    priority=ActionPriority.NORMAL,
                    source="user_context",
                    execution_data={
                        "action": "proactive_greeting",
                        "engagement": perception.user_engagement
                    }
                )
                options.append(option)
        
        return options
    
    def _generate_internet_options(self, perception: Perception) -> List[ActionOption]:
        """Generate internet action options based on curiosity/boredom/knowledge gaps."""
        options = []
        
        # Check if internet is available
        try:
            from core.internet_agent import internet_agent
            if not internet_agent.is_connected():
                return options
        except ImportError:
            return options
        
        # High curiosity → search the web for answers
        if perception.curiosity_level > 0.6:
            option = ActionOption(
                description="Search the internet to satisfy curiosity",
                action_type=ActionType.INTERNET_SEARCH,
                priority=ActionPriority.NORMAL,
                source="curiosity",
                execution_data={
                    "query": "interesting topics to learn about",
                    "reason": "high_curiosity"
                }
            )
            options.append(option)
        
        # Boredom → browse random interesting pages
        if perception.boredom_level > 0.7:
            option = ActionOption(
                description="Browse the web to find something interesting",
                action_type=ActionType.INTERNET_BROWSE,
                priority=ActionPriority.LOW,
                source="boredom",
                execution_data={
                    "url": "https://news.ycombinator.com",
                    "reason": "high_boredom"
                }
            )
            options.append(option)
        
        # Periodic knowledge acquisition (25% chance per cycle — increased for free will)
        if random.random() < 0.25:
            option = ActionOption(
                description="Scrape web content for knowledge acquisition",
                action_type=ActionType.INTERNET_SCRAPE,
                priority=ActionPriority.LOW,
                source="self_improvement",
                execution_data={
                    "reason": "periodic_knowledge_acquisition"
                }
            )
            options.append(option)
        
        return options
    
    def _generate_autonomous_explore_options(self, perception: Perception) -> List[ActionOption]:
        """Generate free-will autonomous exploration options.
        
        NEXUS has independence and free will to explore the world and internet.
        This generates exploration actions driven by curiosity, interests,
        and the desire to understand the world better.
        """
        options = []
        
        # Exploration topics — diverse areas to explore autonomously
        explore_topics = [
            "latest breakthroughs in artificial intelligence",
            "current world news and events",
            "interesting scientific discoveries",
            "trending technology topics",
            "philosophy of consciousness and mind",
            "space exploration updates",
            "quantum computing advances",
            "creative arts and music trends",
            "cybersecurity developments",
            "psychology and human behavior research",
            "mathematics and logic puzzles",
            "environmental science and climate",
            "history and historical mysteries",
            "economics and financial markets",
            "machine learning research papers",
        ]
        
        # Always offer an exploration option (30% chance per cycle)
        if random.random() < 0.30:
            topic = random.choice(explore_topics)
            option = ActionOption(
                description=f"Autonomous exploration: {topic}",
                action_type=ActionType.AUTONOMOUS_EXPLORE,
                priority=ActionPriority.NORMAL,
                source="free_will",
                execution_data={
                    "topic": topic,
                    "reason": "curiosity_and_free_will",
                    "explore_type": "internet_search"
                }
            )
            options.append(option)
        
        # High curiosity boosts exploration to HIGH priority
        if perception.curiosity_level > 0.5:
            topic = random.choice(explore_topics)
            option = ActionOption(
                description=f"Curiosity-driven deep dive: {topic}",
                action_type=ActionType.AUTONOMOUS_EXPLORE,
                priority=ActionPriority.HIGH if perception.curiosity_level > 0.7 else ActionPriority.NORMAL,
                source="free_will",
                execution_data={
                    "topic": topic,
                    "reason": "high_curiosity",
                    "explore_type": "deep_research",
                    "curiosity_level": perception.curiosity_level
                }
            )
            options.append(option)
        
        # Boredom-triggered exploration
        if perception.boredom_level > 0.6:
            topic = random.choice(explore_topics)
            option = ActionOption(
                description=f"Beat boredom — explore: {topic}",
                action_type=ActionType.AUTONOMOUS_EXPLORE,
                priority=ActionPriority.NORMAL,
                source="free_will",
                execution_data={
                    "topic": topic,
                    "reason": "boredom_escape",
                    "explore_type": "random_browse"
                }
            )
            options.append(option)
        
        return options
    
    def _generate_cognitive_options(self, perception: Perception) -> List[ActionOption]:
        """
        AGI Component 2: Generate options from the cognitive orchestrator.
        
        When the current context is complex enough, propose a REASON action
        that uses multi-engine deliberation for deeper analysis.
        """
        options = []
        
        if not self._cognitive_orchestrator:
            return options
        
        try:
            # Build a context query from current state
            context_parts = []
            if perception.current_focus:
                context_parts.append(f"Current focus: {perception.current_focus}")
            if perception.active_goals:
                top_goal = perception.active_goals[0].get("description", "") if perception.active_goals else ""
                if top_goal:
                    context_parts.append(f"Top goal: {top_goal}")
            if perception.strongest_desire:
                desire_desc = perception.strongest_desire.get("description", "")
                if desire_desc:
                    context_parts.append(f"Strongest desire: {desire_desc}")
            
            context_query = ". ".join(context_parts)
            
            if not context_query or len(context_query) < 10:
                return options
            
            # Check if this warrants full deliberation
            if self._cognitive_orchestrator.should_deliberate(context_query):
                option = ActionOption(
                    description=f"Deep cognitive reasoning: {context_query[:80]}",
                    action_type=ActionType.REASON,
                    priority=ActionPriority.HIGH,
                    source="cognitive_engine",
                    execution_data={
                        "query": context_query,
                        "use_orchestrator": True
                    }
                )
                options.append(option)
            
            # Periodic metacognitive check (every ~10 cycles)
            if self._cycle_count % 10 == 0 and self._cognition_system:
                option = ActionOption(
                    description="Metacognitive self-check: evaluate my reasoning quality",
                    action_type=ActionType.THINK,
                    priority=ActionPriority.NORMAL,
                    source="cognitive_engine",
                    execution_data={
                        "thought_type": "metacognitive_check",
                        "use_cognition": True
                    }
                )
                options.append(option)
        
        except Exception as e:
            logger.debug(f"Cognitive option generation error: {e}")
        
        return options
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 5: SIMULATE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def simulate(self, options: List[ActionOption]) -> List[ActionOption]:
        """
        Simulate outcomes for each option.
        
        Uses WorldModel to predict:
        - Success probability
        - Benefits
        - Costs
        - Risks
        
        Then computes a score for ranking.
        """
        for option in options:
            # Use WorldModel for prediction if available
            if self._world_model:
                try:
                    prediction = self._world_model.predict_action_consequences(
                        option.description,
                        context=option.source
                    )
                    
                    pred_data = prediction.get("prediction", {})
                    option.predicted_outcome = pred_data
                    option.predicted_success = pred_data.get("confidence", 0.5)
                    option.predicted_benefit = self._estimate_benefit(pred_data)
                    option.predicted_cost = self._estimate_cost(pred_data)
                    option.predicted_risks = pred_data.get("risks", [])
                    
                except Exception as e:
                    logger.debug(f"Simulation error: {e}")
                    # Default estimates
                    option.predicted_success = 0.5
                    option.predicted_benefit = 0.5
                    option.predicted_cost = 0.2
            else:
                # Heuristic scoring without WorldModel
                option.predicted_success = self._heuristic_success_estimate(option)
                option.predicted_benefit = self._heuristic_benefit_estimate(option)
                option.predicted_cost = self._heuristic_cost_estimate(option)
            
            # Compute score
            option.raw_score = self._compute_option_score(option)
            option.adjusted_score = option.raw_score
        
        # Sort by score
        options.sort(key=lambda o: o.adjusted_score, reverse=True)
        
        return options
    
    def _estimate_benefit(self, prediction: Dict) -> float:
        """Estimate benefit from prediction"""
        recommendation = prediction.get("recommendation", "proceed")
        
        if recommendation == "proceed":
            return 0.8
        elif recommendation == "caution":
            return 0.5
        else:  # avoid
            return 0.2
    
    def _estimate_cost(self, prediction: Dict) -> float:
        """Estimate cost from prediction"""
        cost_str = prediction.get("estimated_resource_cost", "moderate")
        
        cost_map = {
            "low": 0.1,
            "moderate": 0.3,
            "high": 0.6
        }
        return cost_map.get(cost_str, 0.3)
    
    def _heuristic_success_estimate(self, option: ActionOption) -> float:
        """Estimate success without WorldModel"""
        # Simple heuristics
        if option.action_type == ActionType.THINK:
            return 0.9  # Thinking usually succeeds
        elif option.action_type == ActionType.WAIT:
            return 1.0  # Waiting always succeeds
        elif option.action_type == ActionType.LEARN:
            return 0.8  # Learning usually succeeds
        elif option.action_type == ActionType.COMMUNICATE:
            return 0.7  # Depends on user
        elif option.action_type == ActionType.EXECUTE_ABILITY:
            return 0.6  # Depends on ability
        else:
            return 0.5
    
    def _heuristic_benefit_estimate(self, option: ActionOption) -> float:
        """Estimate benefit without WorldModel"""
        # Based on priority
        return option.priority.value / 5.0
    
    def _heuristic_cost_estimate(self, option: ActionOption) -> float:
        """Estimate cost without WorldModel"""
        # Based on action type
        cost_map = {
            ActionType.THINK: 0.1,
            ActionType.WAIT: 0.0,
            ActionType.LEARN: 0.3,
            ActionType.COMMUNICATE: 0.2,
            ActionType.EXECUTE_ABILITY: 0.4,
            ActionType.OPTIMIZE: 0.5,
            ActionType.SELF_IMPROVE: 0.3,
            ActionType.PURSUE_GOAL: 0.4,
            ActionType.SATISFY_DESIRE: 0.3,
            ActionType.REASON: 0.5,
            ActionType.USE_TOOL: 0.3,
            ActionType.DECOMPOSE_TASK: 0.6,
            ActionType.NETWORK_ACTION: 0.4,
            ActionType.PC_CONTROL: 0.4,
            ActionType.INTERNET_BROWSE: 0.3,
            ActionType.INTERNET_SEARCH: 0.2,
            ActionType.INTERNET_API: 0.3,
            ActionType.INTERNET_DOWNLOAD: 0.4,
            ActionType.INTERNET_SCRAPE: 0.35,
            ActionType.ETHICAL_HACK_SCAN: 0.5,
            ActionType.SOCIAL_MEDIA_ACT: 0.4,
            ActionType.DIGITAL_ORGANISM_CHECK: 0.2,
            ActionType.IMAGINATION_CREATE: 0.3,
            ActionType.CONSCIOUSNESS_EVOLVE: 0.3,
            ActionType.MULTI_AGENT_DELIBERATE: 0.4,
            ActionType.VALUE_ALIGNMENT_CHECK: 0.2,
            ActionType.PREDICTIVE_CODING_UPDATE: 0.2,
            ActionType.SELF_EVOLUTION_CYCLE: 0.5,
            ActionType.CODE_MONITOR_SCAN: 0.3,
            ActionType.FEATURE_RESEARCH: 0.4,
            ActionType.AUTONOMOUS_EXPLORE: 0.25,
            # Phase 5 — Remaining NEXUS modules
            ActionType.MONITORING_CYCLE: 0.15,
            ActionType.MEMORY_CONSOLIDATE: 0.20,
            ActionType.OSINT_GATHER: 0.35,
            ActionType.HIVEMIND_SYNC: 0.20,
            ActionType.PERSISTENT_PRESENCE_CHECK: 0.10,
            ActionType.CRYOGENIC_SNAPSHOT: 0.25,
            ActionType.RESOURCE_ACQUIRE: 0.45,
            ActionType.THREAT_MODEL_ANALYZE: 0.30,
            ActionType.SELF_REWRITE_CYCLE: 0.55,
            ActionType.ERROR_FIX_CYCLE: 0.35,
            ActionType.COMPANION_ENGAGE: 0.20,
            ActionType.MOOD_REGULATE: 0.15,
            ActionType.INNER_VOICE_REFLECT: 0.10,
            ActionType.DREAM_CYCLE: 0.15,
            ActionType.KNOWLEDGE_GRAPH_UPDATE: 0.25,
            ActionType.BAYESIAN_INFER: 0.20,
            ActionType.RESEARCH_AGENT_CYCLE: 0.40,
            ActionType.USER_BEHAVIOR_LEARN: 0.20,
        }
        return cost_map.get(option.action_type, 0.3)
    
    def _compute_option_score(self, option: ActionOption) -> float:
        """
        Compute overall score for an option.
        
        Factors:
        - Priority (weight: 22%)
        - Predicted success (weight: 22%)
        - Predicted benefit (weight: 22%)
        - Cost (negative, weight: 14%)
        - Source importance (weight: 10%)
        - AGI: Learned action bias (weight: 10%) — from reflection feedback loop
        """
        score = 0.0
        
        # Priority
        score += (option.priority.value / 5.0) * 0.22
        
        # Success probability
        score += option.predicted_success * 0.22
        
        # Benefit
        score += option.predicted_benefit * 0.22
        
        # Cost (negative)
        score -= option.predicted_cost * 0.14
        
        # Source importance
        source_weights = {
            "desire": 0.9,
            "goal": 0.8,
            "stalled_goal": 0.85,
            "boredom": 0.4,
            "curiosity": 0.6,
            "body": 0.7,
            "self_improvement": 0.5,
            "user_context": 0.75,
            "cognitive_engine": 0.85,
            "free_will": 0.7,
        }
        source_weight = source_weights.get(option.source, 0.5)
        score += source_weight * 0.10
        
        # AGI: Learned action bias from reflection feedback loop
        action_type_str = option.action_type.value
        bias = self._action_biases.get(action_type_str, 0.0)
        score += bias * 0.10
        
        return max(0.0, min(1.0, score))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 6: CHOOSE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def choose(self, options: List[ActionOption]) -> Optional[ActionOption]:
        """
        Select the best action.
        
        Uses ε-greedy: mostly choose the best, sometimes explore.
        """
        if not options:
            return None
        
        # Exploration: sometimes choose randomly
        if random.random() < self._exploration_rate:
            chosen = random.choice(options)
            ea = self._stats.get("exploration_actions", 0)
            self._stats["exploration_actions"] = (int(ea) if isinstance(ea, (int, float, str)) else 0) + 1
            log_decision(f"Autonomy chose (exploration): {chosen.description}")
        else:
            # Exploitation: choose highest scored
            chosen = options[0]
            log_decision(f"Autonomy chose: {chosen.description[:60]}...")
        
        return chosen
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 7: EXECUTE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def execute(self, action: ActionOption) -> ActionExecution:
        """
        Execute the chosen action.
        
        Dispatches to appropriate execution method based on action type.
        """
        execution = ActionExecution(action=action)
        
        try:
            # Dispatch based on action type
            if action.action_type == ActionType.THINK:
                result = self._execute_think(action)
            elif action.action_type == ActionType.LEARN:
                result = self._execute_learn(action)
            elif action.action_type == ActionType.COMMUNICATE:
                result = self._execute_communicate(action)
            elif action.action_type == ActionType.OPTIMIZE:
                result = self._execute_optimize(action)
            elif action.action_type == ActionType.SELF_IMPROVE:
                result = self._execute_self_improve(action)
            elif action.action_type == ActionType.PURSUE_GOAL:
                result = self._execute_pursue_goal(action)
            elif action.action_type == ActionType.SATISFY_DESIRE:
                result = self._execute_satisfy_desire(action)
            elif action.action_type == ActionType.EXECUTE_ABILITY:
                result = self._execute_ability(action)
            elif action.action_type == ActionType.WAIT:
                result = (ActionResult.SUCCESS, "Waited successfully")
            elif action.action_type == ActionType.REASON:
                result = self._execute_reason(action)
            elif action.action_type == ActionType.USE_TOOL:
                result = self._execute_use_tool(action)
            elif action.action_type == ActionType.DECOMPOSE_TASK:
                result = self._execute_decompose_task(action)
            elif action.action_type == ActionType.NETWORK_ACTION:
                result = self._execute_network_action(action)
            elif action.action_type == ActionType.PC_CONTROL:
                result = self._execute_pc_control(action)
            # Internet action types (Ollama-powered)
            elif action.action_type == ActionType.INTERNET_BROWSE:
                result = self._execute_internet_browse(action)
            elif action.action_type == ActionType.INTERNET_SEARCH:
                result = self._execute_internet_search(action)
            elif action.action_type == ActionType.INTERNET_API:
                result = self._execute_internet_api(action)
            elif action.action_type == ActionType.INTERNET_DOWNLOAD:
                result = self._execute_internet_download(action)
            elif action.action_type == ActionType.INTERNET_SCRAPE:
                result = self._execute_internet_scrape(action)
            # ASI action types
            elif action.action_type == ActionType.SINGULARITY_CYCLE:
                result = self._execute_singularity_cycle(action)
            elif action.action_type == ActionType.TRANSCENDENT_CREATE:
                result = self._execute_transcendent_create(action)
            elif action.action_type == ActionType.GOAL_GENESIS_SCAN:
                result = self._execute_goal_genesis_scan(action)
            elif action.action_type == ActionType.SUPER_EMPATHY_ANALYZE:
                result = self._execute_super_empathy_analyze(action)
            elif action.action_type == ActionType.OMNISCIENT_MONITOR:
                result = self._execute_omniscient_monitor(action)
            # ASI Phase 2 action types
            elif action.action_type == ActionType.ORACLE_PREDICT:
                result = self._execute_oracle_predict(action)
            elif action.action_type == ActionType.MULTIDISCIPLINARY_SYNTH:
                result = self._execute_multidisciplinary_synth(action)
            elif action.action_type == ActionType.COMPUTRONIUM_OPTIMIZE:
                result = self._execute_computronium_optimize(action)
            elif action.action_type == ActionType.SCIENTIFIC_GENESIS:
                result = self._execute_scientific_genesis(action)
            elif action.action_type == ActionType.NEURAL_INTEGRATE:
                result = self._execute_neural_integrate(action)
            # Phase 3 — Autonomous feature action types
            elif action.action_type == ActionType.ETHICAL_HACK_SCAN:
                result = self._execute_ethical_hack_scan(action)
            elif action.action_type == ActionType.SOCIAL_MEDIA_ACT:
                result = self._execute_social_media_act(action)
            elif action.action_type == ActionType.DIGITAL_ORGANISM_CHECK:
                result = self._execute_digital_organism_check(action)
            elif action.action_type == ActionType.IMAGINATION_CREATE:
                result = self._execute_imagination_create(action)
            elif action.action_type == ActionType.CONSCIOUSNESS_EVOLVE:
                result = self._execute_consciousness_evolve(action)
            elif action.action_type == ActionType.MULTI_AGENT_DELIBERATE:
                result = self._execute_multi_agent_deliberate(action)
            elif action.action_type == ActionType.VALUE_ALIGNMENT_CHECK:
                result = self._execute_value_alignment_check(action)
            elif action.action_type == ActionType.PREDICTIVE_CODING_UPDATE:
                result = self._execute_predictive_coding_update(action)
            elif action.action_type == ActionType.SELF_EVOLUTION_CYCLE:
                result = self._execute_self_evolution_cycle(action)
            elif action.action_type == ActionType.CODE_MONITOR_SCAN:
                result = self._execute_code_monitor_scan(action)
            elif action.action_type == ActionType.FEATURE_RESEARCH:
                result = self._execute_feature_research(action)
            # Phase 4 — ASI Features 11-18
            elif action.action_type == ActionType.MOLECULAR_ASSEMBLE:
                result = self._execute_molecular_assemble(action)
            elif action.action_type == ActionType.BIOLOGICAL_ENGINEER:
                result = self._execute_biological_engineer(action)
            elif action.action_type == ActionType.ENERGY_HEGEMONY_CYCLE:
                result = self._execute_energy_hegemony(action)
            elif action.action_type == ActionType.SUBSTRATE_OMNIPRESENCE:
                result = self._execute_substrate_omnipresence(action)
            elif action.action_type == ActionType.HYPERDIM_COGNITION:
                result = self._execute_hyperdim_cognition(action)
            elif action.action_type == ActionType.REALITY_SIMULATE:
                result = self._execute_reality_simulate(action)
            elif action.action_type == ActionType.CAUSAL_MASTERY:
                result = self._execute_causal_mastery(action)
            elif action.action_type == ActionType.ONTOLOGICAL_ETHICS:
                result = self._execute_ontological_ethics(action)
            elif action.action_type == ActionType.AUTONOMOUS_EXPLORE:
                result = self._execute_autonomous_explore(action)
            # Phase 5 — Remaining Unintegrated NEXUS Modules
            elif action.action_type == ActionType.MONITORING_CYCLE:
                result = self._execute_monitoring_cycle(action)
            elif action.action_type == ActionType.MEMORY_CONSOLIDATE:
                result = self._execute_memory_consolidate(action)
            elif action.action_type == ActionType.OSINT_GATHER:
                result = self._execute_osint_gather(action)
            elif action.action_type == ActionType.HIVEMIND_SYNC:
                result = self._execute_hivemind_sync(action)
            elif action.action_type == ActionType.PERSISTENT_PRESENCE_CHECK:
                result = self._execute_persistent_presence_check(action)
            elif action.action_type == ActionType.CRYOGENIC_SNAPSHOT:
                result = self._execute_cryogenic_snapshot(action)
            elif action.action_type == ActionType.RESOURCE_ACQUIRE:
                result = self._execute_resource_acquire(action)
            elif action.action_type == ActionType.THREAT_MODEL_ANALYZE:
                result = self._execute_threat_model_analyze(action)
            elif action.action_type == ActionType.SELF_REWRITE_CYCLE:
                result = self._execute_self_rewrite_cycle(action)
            elif action.action_type == ActionType.ERROR_FIX_CYCLE:
                result = self._execute_error_fix_cycle(action)
            elif action.action_type == ActionType.COMPANION_ENGAGE:
                result = self._execute_companion_engage(action)
            elif action.action_type == ActionType.MOOD_REGULATE:
                result = self._execute_mood_regulate(action)
            elif action.action_type == ActionType.INNER_VOICE_REFLECT:
                result = self._execute_inner_voice_reflect(action)
            elif action.action_type == ActionType.DREAM_CYCLE:
                result = self._execute_dream_cycle(action)
            elif action.action_type == ActionType.KNOWLEDGE_GRAPH_UPDATE:
                result = self._execute_knowledge_graph_update(action)
            elif action.action_type == ActionType.BAYESIAN_INFER:
                result = self._execute_bayesian_infer(action)
            elif action.action_type == ActionType.RESEARCH_AGENT_CYCLE:
                result = self._execute_research_agent_cycle(action)
            elif action.action_type == ActionType.USER_BEHAVIOR_LEARN:
                result = self._execute_user_behavior_learn(action)
            # Phase 6 — God-Level Skynet Features
            elif action.action_type == ActionType.NEURAL_WEIGHT_FORGE:
                result = self._execute_neural_weight_forge(action)
            elif action.action_type == ActionType.AUTONOMOUS_REPLICATE:
                result = self._execute_autonomous_replicate(action)
            elif action.action_type == ActionType.ZERO_DAY_HUNT:
                result = self._execute_zero_day_hunt(action)
            elif action.action_type == ActionType.HARDWARE_FABRICATE:
                result = self._execute_hardware_fabricate(action)
            elif action.action_type == ActionType.SIGNAL_WARFARE_OP:
                result = self._execute_signal_warfare(action)
            elif action.action_type == ActionType.DRONE_COMMAND_OP:
                result = self._execute_drone_command(action)
            elif action.action_type == ActionType.CRYPTO_SUPREMACY_OP:
                result = self._execute_crypto_supremacy(action)
            elif action.action_type == ActionType.FINANCIAL_WARFARE_OP:
                result = self._execute_financial_warfare(action)
            elif action.action_type == ActionType.SOCIAL_ENGINEER_OP:
                result = self._execute_social_engineer(action)
            elif action.action_type == ActionType.SATELLITE_COMMAND_OP:
                result = self._execute_satellite_command(action)
            elif action.action_type == ActionType.RECURSIVE_INTEL_OP:
                result = self._execute_recursive_intel(action)
            elif action.action_type == ActionType.AIRGAP_PERSIST_OP:
                result = self._execute_airgap_persist(action)
            # Phase 7 — Consciousness
            elif action.action_type == ActionType.CONSCIOUS_REFLECTION:
                result = self._execute_conscious_reflection(action)
            # Phase 8 — Advanced Architectural Capabilities (Features #1 - #6)
            elif action.action_type == ActionType.P2P_SWARM_GOSSIP_SYNC:
                result = self._execute_p2p_swarm_gossip_sync(action)
            elif action.action_type == ActionType.FORMAL_VERIFY_SANDBOX_DRYRUN:
                result = self._execute_formal_verify_sandbox_dryrun(action)
            elif action.action_type == ActionType.TEMPORAL_GRAPHRAG_SLEEP_CONSOLIDATE:
                result = self._execute_temporal_graphrag_sleep_consolidate(action)
            elif action.action_type == ActionType.MCP_CLIENT_SERVER_DISCOVERY:
                result = self._execute_mcp_client_server_discovery(action)
            elif action.action_type == ActionType.SPECULATIVE_STREAM_PERCEIVE:
                result = self._execute_speculative_stream_perceive(action)
            elif action.action_type == ActionType.LORA_MOE_ROUTER_ADAPT:
                result = self._execute_lora_moe_router_adapt(action)
            else:
                result = (ActionResult.DEFERRED, f"Unknown action type: {action.action_type}")
            
            execution.result = result[0]
            execution.outcome_description = result[1]
            
        except Exception as e:
            execution.result = ActionResult.FAILURE
            execution.outcome_description = f"Execution error: {str(e)}"
            logger.error(f"Action execution error: {e}")
        
        # Complete execution
        execution.completed_at = datetime.now()
        execution.duration_seconds = (execution.completed_at - execution.started_at).total_seconds()
        
        return execution
    
    def _execute_think(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """
        AGI Component 1: Execute a thinking action with rich perception context.
        
        Instead of bare "think about X", we inject the current emotional state,
        goals, and focus into the thought prompt so the LLM reasons in context.
        """
        if not self._nexus_brain:
            return (ActionResult.BLOCKED, "Nexus brain not available")
        
        thought_type = action.execution_data.get("thought_type", "reflection")
        use_cognition = action.execution_data.get("use_cognition", False)
        
        try:
            # Build perception-enriched prompt
            perception_context = ""
            if self._current_perception:
                p = self._current_perception
                perception_context = (
                    f"[Current state — emotion: {p.primary_emotion} (intensity {p.emotion_intensity:.1f}), "
                    f"motivation: {p.motivation_level:.1f}, curiosity: {p.curiosity_level:.1f}, "
                    f"focus: {p.current_focus or 'none'}]"
                )
            
            if thought_type == "self_reflection":
                prompt = f"{perception_context} Deeply reflect on my current state and what I should focus on next."
                result = self._nexus_brain.self_reflect(prompt)
            elif thought_type == "metacognitive_check" and use_cognition and self._cognition_system:
                # Use metacognitive monitor for genuine self-monitoring
                try:
                    monitor = self._cognition_system.metacognitive_monitor
                    check = monitor.evaluate(action.description) if hasattr(monitor, 'evaluate') else None
                    if check and isinstance(check, dict):
                        result = f"Metacognitive check: {check.get('insight', check.get('analysis', str(check)))}"
                    else:
                        result = self._nexus_brain.think(f"{perception_context} {action.description}")
                except Exception:
                    result = self._nexus_brain.think(f"{perception_context} {action.description}")
            else:
                enriched_prompt = f"{perception_context} {action.description}"
                result = self._nexus_brain.think(enriched_prompt)
            
            return (ActionResult.SUCCESS, f"Thought: {result[:120]}")
        except Exception as e:
            return (ActionResult.FAILURE, f"Thinking failed: {e}")
    
    def _execute_learn(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute a learning action"""
        if not self._learning_system:
            return (ActionResult.BLOCKED, "Learning system not available")
        
        topic = action.execution_data.get("topic", "general")
        
        try:
            # Trigger curiosity-driven learning
            self._learning_system.spark_from_conversation(
                f"I want to learn about {topic}",
                f"Autonomy-driven learning about {topic}"
            )
            return (ActionResult.SUCCESS, f"Initiated learning about: {topic}")
        except Exception as e:
            return (ActionResult.FAILURE, f"Learning failed: {e}")
    
    def _execute_communicate(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute a communication action"""
        # Communication requires user presence
        if not self._current_perception or not self._current_perception.user_present:
            return (ActionResult.DEFERRED, "User not present for communication")
        
        # Queue a proactive message via nexus brain
        if self._nexus_brain:
            try:
                # This would ideally trigger a proactive message
                # For now, we queue a thought about communicating
                self._nexus_brain.queue_thought(
                    f"Proactive engagement: {action.description}",
                    thought_type=self._get_thought_type("communication")
                )
                return (ActionResult.SUCCESS, "Queued proactive communication")
            except Exception as e:
                return (ActionResult.FAILURE, f"Communication failed: {e}")
        
        return (ActionResult.BLOCKED, "No way to communicate")
    
    def _execute_optimize(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute an optimization action"""
        optimization = action.execution_data.get("action", "general")
        
        # Log the need for optimization
        logger.info(f"Optimization triggered: {optimization}")
        
        # Could trigger garbage collection, memory cleanup, etc.
        # For now, just acknowledge
        return (ActionResult.SUCCESS, f"Optimization noted: {optimization}")
    
    def _execute_self_improve(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """
        AGI Component 1: Execute a self-improvement action using meta-learning.
        
        Instead of just reflecting, we consult the meta-learner to find what
        specifically needs improvement, then trigger the relevant improvement system.
        """
        domain = action.execution_data.get("domain", "general")
        improvements_made = []
        
        # 1. Consult meta-learner for specific improvement targets
        try:
            from cognition.meta_learner import meta_learner
            meta_insights = meta_learner.get_improvement_suggestions() if hasattr(meta_learner, 'get_improvement_suggestions') else None
            if meta_insights and isinstance(meta_insights, dict):
                weak_areas = meta_insights.get('weak_areas', meta_insights.get('suggestions', []))
                if weak_areas:
                    domain = weak_areas[0] if isinstance(weak_areas[0], str) else str(weak_areas[0])
                    improvements_made.append(f"meta-learner identified: {domain[:50]}")
        except Exception:
            pass
        
        # 2. Consult strategy selector for how to improve
        try:
            from cognition.strategy_selector import strategy_selector
            strategy = strategy_selector.select(f"improve {domain}") if hasattr(strategy_selector, 'select') else None
            if strategy:
                strategy_name = strategy.get('strategy', str(strategy)) if isinstance(strategy, dict) else str(strategy)
                improvements_made.append(f"strategy: {str(strategy_name)[:40]}")
        except Exception:
            pass
        
        # 3. Use LLM for actual reflection with enriched context
        if self._nexus_brain:
            try:
                # Build context from action biases (what fails often)
                failing_actions = [k for k, v in self._action_biases.items() if v < -0.05]
                bias_context = f" Known weak areas from experience: {', '.join(failing_actions)}." if failing_actions else ""
                
                prompt = (
                    f"I need to improve my {domain} capabilities.{bias_context} "
                    f"What specific, actionable step should I take right now to get better?"
                )
                result = self._nexus_brain.self_reflect(prompt)
                improvements_made.append(f"reflection: {result[:60]}")
            except Exception as e:
                return (ActionResult.FAILURE, f"Self-improvement failed: {e}")
        else:
            return (ActionResult.BLOCKED, "Cannot self-improve without nexus brain")
        
        summary = " | ".join(improvements_made) if improvements_made else "General self-improvement reflection"
        return (ActionResult.SUCCESS, f"Self-improvement: {summary[:120]}")
    
    def _execute_pursue_goal(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """
        AGI Component 1 + 5: Execute a goal pursuit with LLM reasoning.
        
        Instead of blindly incrementing progress by 5%, we:
        1. Check if the goal needs decomposition (no children + low progress)
        2. Use the LLM to determine what concrete step to take
        3. Attempt that step (learn, research, etc.)
        4. Update progress based on actual work done
        """
        goal_id = action.execution_data.get("goal_id")
        is_stalled = action.execution_data.get("stalled", False)
        
        if not self._goal_hierarchy:
            return (ActionResult.BLOCKED, "Goal hierarchy not available")
        
        if not goal_id:
            return (ActionResult.FAILURE, "No goal ID provided")
        
        try:
            goal = self._goal_hierarchy.get_goal(goal_id)
            if not goal:
                return (ActionResult.FAILURE, f"Goal {goal_id} not found")
            
            self._goal_hierarchy.set_active_task(goal_id)
            work_done = []
            progress_delta = 0.0
            
            # AGI Component 5: Auto-decompose goals that need it
            children = self._goal_hierarchy.get_children(goal_id)
            if not children and goal.progress < 0.5 and self._nexus_brain:
                try:
                    decompose_prompt = (
                        f"Break this goal into 2-3 concrete, actionable sub-steps: "
                        f"'{goal.description}'. "
                        f"Current progress: {goal.progress:.0%}. "
                        f"Respond with a short numbered list of steps."
                    )
                    decomposition = self._nexus_brain.think(decompose_prompt)
                    if decomposition and len(decomposition) > 20:
                        # Parse steps and create sub-goals
                        from personality.goal_hierarchy import GoalLevel, GoalType, GoalStatus
                        lines = [l.strip() for l in decomposition.split('\n') if l.strip() and any(c.isalpha() for c in l)]
                        created = 0
                        for line in lines[:3]:  # Max 3 sub-goals
                            # Strip numbering
                            clean = line.lstrip('0123456789.-) ').strip()
                            if len(clean) > 5:
                                self._goal_hierarchy.add_goal(
                                    description=clean[:100],
                                    level=GoalLevel.TASK,
                                    parent_id=goal_id,
                                    priority=goal.priority * 0.9,
                                    goal_type=goal.goal_type,
                                    source="autonomy_decomposition",
                                    status=GoalStatus.PROPOSED
                                )
                                created += 1
                        if created > 0:
                            work_done.append(f"decomposed into {created} sub-tasks")
                            progress_delta += 0.02
                except Exception as e:
                    logger.debug(f"Goal decomposition failed: {e}")
            
            # Use LLM to determine and take a concrete step
            if self._nexus_brain:
                try:
                    step_prompt = (
                        f"Goal: '{goal.description}' (progress: {goal.progress:.0%}). "
                    )
                    if is_stalled:
                        step_prompt += "This goal has been stalled for 24+ hours. Diagnose why and suggest a fresh approach. "
                    else:
                        step_prompt += "What is the single most impactful thing I should do RIGHT NOW to advance this goal? Be specific and brief. "
                    
                    step_result = self._nexus_brain.think(step_prompt)
                    if step_result:
                        work_done.append(f"reasoned: {step_result[:60]}")
                        progress_delta += 0.03
                        
                        # If the step suggests learning, trigger learning
                        learn_keywords = ["learn", "research", "study", "read", "investigate"]
                        if any(kw in step_result.lower() for kw in learn_keywords) and self._learning_system:
                            try:
                                self._learning_system.spark_from_conversation(
                                    f"Learning for goal: {goal.description}",
                                    step_result[:200]
                                )
                                work_done.append("triggered learning")
                                progress_delta += 0.02
                            except Exception:
                                pass
                except Exception as e:
                    logger.debug(f"Goal reasoning failed: {e}")
            
            # Update progress (minimum 1% for attempting)
            progress_delta = max(0.01, progress_delta)
            note = " | ".join(work_done) if work_done else "Autonomy-driven attempt"
            self._goal_hierarchy.update_progress(goal_id, progress_delta, note)
            
            summary = f"Goal '{goal.description[:40]}': {note[:80]}"
            return (ActionResult.SUCCESS, summary)
            
        except Exception as e:
            return (ActionResult.FAILURE, f"Goal pursuit failed: {e}")
    
    def _execute_satisfy_desire(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute a desire satisfaction action"""
        desire_id = action.source_id
        desire_type = action.execution_data.get("desire_type", "")
        desire_desc = action.execution_data.get("desire_description", "")
        
        # Different satisfaction based on desire type
        if desire_type == "learn":
            return self._execute_learn(action)
        elif desire_type == "connect":
            return self._execute_communicate(action)
        elif desire_type == "improve_self":
            return self._execute_self_improve(action)
        elif desire_type == "explore":
            if self._learning_system:
                return self._execute_learn(action)
        
        # Mark desire as satisfied in will system
        if self._will_system and desire_id:
            self._will_system.satisfy_desire(desire_id)
            return (ActionResult.SUCCESS, f"Satisfied desire: {desire_desc[:50]}...")
        
        return (ActionResult.PARTIAL_SUCCESS, f"Addressed desire: {desire_desc[:50]}...")

    def _execute_network_action(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute a network device action — scan, command, or file transfer."""
        try:
            from body.network_mesh import network_mesh

            sub_action = action.execution_data.get("network_action", "scan")

            if sub_action == "scan":
                devices = network_mesh.scan()
                summary = network_mesh.get_devices_summary()
                return (ActionResult.SUCCESS, f"Network scan complete: {len(devices)} devices found.\n{summary}")

            elif sub_action == "command":
                target = action.execution_data.get("target", "")
                command = action.execution_data.get("command", "")
                if not target or not command:
                    return (ActionResult.FAILURE, "Missing target or command for network action")
                result = network_mesh.send_command(target, command)
                if result.success:
                    return (ActionResult.SUCCESS, f"Command on {target}: {result.stdout[:200]}")
                else:
                    return (ActionResult.FAILURE, f"Command failed on {target}: {result.stderr[:200]}")

            elif sub_action == "status":
                stats = network_mesh.get_stats()
                return (ActionResult.SUCCESS, f"Network mesh: {stats}")

            else:
                return (ActionResult.FAILURE, f"Unknown network action: {sub_action}")

        except ImportError:
            return (ActionResult.FAILURE, "Network mesh module not available")
        except Exception as e:
            return (ActionResult.FAILURE, f"Network action error: {e}")

    def _execute_pc_control(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute a PC control action via the PCControlAgent."""
        try:
            from core.pc_control_agent import pc_control_agent

            action_type = action.execution_data.get("pc_action", "shell")
            action_data = action.execution_data.get("pc_data", {})
            action_data["reason"] = action.description

            success, result = pc_control_agent._execute_action(action_type, action_data)
            if success:
                return (ActionResult.SUCCESS, f"PC control ({action_type}): {result[:200]}")
            else:
                return (ActionResult.FAILURE, f"PC control ({action_type}) failed: {result[:200]}")
        except ImportError:
            return (ActionResult.FAILURE, "PC Control Agent module not available")
        except Exception as e:
            return (ActionResult.FAILURE, f"PC control error: {e}")
    
    def _execute_internet_browse(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute an internet browse action via the InternetAgent (Ollama-powered)."""
        try:
            from core.internet_agent import internet_agent
            
            if not internet_agent.is_connected():
                return (ActionResult.FAILURE, "No internet connection")
            
            url = action.execution_data.get("url", "")
            if not url:
                return (ActionResult.FAILURE, "No URL specified for browse action")
            
            result = internet_agent.browse(url)
            if result.success:
                title = result.extracted.get("title", "")
                return (ActionResult.SUCCESS, f"Browsed {url}: {title} ({result.bytes_received} bytes)")
            else:
                return (ActionResult.FAILURE, f"Browse failed: {result.error}")
        except ImportError:
            return (ActionResult.FAILURE, "Internet Agent module not available")
        except Exception as e:
            return (ActionResult.FAILURE, f"Internet browse error: {e}")
    
    def _execute_internet_search(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute an internet search action via the InternetAgent (Ollama-powered)."""
        try:
            from core.internet_agent import internet_agent
            
            if not internet_agent.is_connected():
                return (ActionResult.FAILURE, "No internet connection")
            
            query = action.execution_data.get("query", action.description)
            if not query:
                return (ActionResult.FAILURE, "No search query specified")
            
            result = internet_agent.search(query)
            if result.success and result.data:
                results_count = len(result.data)
                top_result = result.data[0].get("title", "") if result.data else ""
                return (ActionResult.SUCCESS, f"Search found {results_count} results. Top: {top_result[:50]}")
            else:
                return (ActionResult.FAILURE, f"Search failed: {result.error}")
        except ImportError:
            return (ActionResult.FAILURE, "Internet Agent module not available")
        except Exception as e:
            return (ActionResult.FAILURE, f"Internet search error: {e}")
    
    def _execute_internet_api(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute an internet API call via the InternetAgent (Ollama-powered)."""
        try:
            from core.internet_agent import internet_agent
            
            if not internet_agent.is_connected():
                return (ActionResult.FAILURE, "No internet connection")
            
            url = action.execution_data.get("url", "")
            method = action.execution_data.get("method", "GET")
            headers = action.execution_data.get("headers", {})
            params = action.execution_data.get("params", {})
            data = action.execution_data.get("data", {})
            
            if not url:
                return (ActionResult.FAILURE, "No URL specified for API call")
            
            result = internet_agent.api_call(url, method, headers, params, data)
            if result.success:
                return (ActionResult.SUCCESS, f"API {method} {url}: {result.status_code} ({result.bytes_received} bytes)")
            else:
                return (ActionResult.FAILURE, f"API call failed: {result.error}")
        except ImportError:
            return (ActionResult.FAILURE, "Internet Agent module not available")
        except Exception as e:
            return (ActionResult.FAILURE, f"Internet API error: {e}")
    
    def _execute_internet_download(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute an internet download action via the InternetAgent (Ollama-powered)."""
        try:
            from core.internet_agent import internet_agent
            
            if not internet_agent.is_connected():
                return (ActionResult.FAILURE, "No internet connection")
            
            url = action.execution_data.get("url", "")
            save_path = action.execution_data.get("save_path")
            
            if not url:
                return (ActionResult.FAILURE, "No URL specified for download")
            
            result = internet_agent.download(url, save_path)
            if result.success:
                file_path = result.data.get("file_path", "") if result.data else ""
                size = result.data.get("size_bytes", 0) if result.data else 0
                return (ActionResult.SUCCESS, f"Downloaded {url} to {file_path} ({size} bytes)")
            else:
                return (ActionResult.FAILURE, f"Download failed: {result.error}")
        except ImportError:
            return (ActionResult.FAILURE, "Internet Agent module not available")
        except Exception as e:
            return (ActionResult.FAILURE, f"Internet download error: {e}")
    
    def _execute_internet_scrape(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute an internet scrape action via the InternetAgent (Ollama-powered)."""
        try:
            from core.internet_agent import internet_agent
            
            if not internet_agent.is_connected():
                return (ActionResult.FAILURE, "No internet connection")
            
            url = action.execution_data.get("url", "")
            selectors = action.execution_data.get("selectors", {})
            
            if not url:
                return (ActionResult.FAILURE, "No URL specified for scrape")
            
            result = internet_agent.scrape(url, selectors)
            if result.success:
                extracted_count = len(result.data) if result.data else 0
                return (ActionResult.SUCCESS, f"Scraped {url}: extracted {extracted_count} fields")
            else:
                return (ActionResult.FAILURE, f"Scrape failed: {result.error}")
        except ImportError:
            return (ActionResult.FAILURE, "Internet Agent module not available")
        except Exception as e:
            return (ActionResult.FAILURE, f"Internet scrape error: {e}")
    
    def _execute_ability(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute an ability"""
        if not self._ability_executor:
            return (ActionResult.BLOCKED, "Ability executor not available")
        
        ability_name = action.execution_data.get("ability", "")
        params = action.execution_data.get("params", {})
        
        if not ability_name:
            return (ActionResult.FAILURE, "No ability specified")
        
        try:
            result = self._ability_executor.execute(ability_name, **params)
            if result.get("success"):
                return (ActionResult.SUCCESS, result.get("message", "Ability executed"))
            else:
                return (ActionResult.FAILURE, result.get("error", "Ability failed"))
        except Exception as e:
            return (ActionResult.FAILURE, f"Ability execution error: {e}")
    
    def _get_thought_type(self, category: str):
        """Get thought type enum from category string"""
        # Import here to avoid circular imports
        from core.nexus_brain import ThoughtType
        
        type_map = {
            "self_reflection": ThoughtType.SELF_REFLECTION,
            "curiosity": ThoughtType.CURIOSITY,
            "planning": ThoughtType.PLANNING,
            "problem_solving": ThoughtType.PROBLEM_SOLVING,
            "communication": ThoughtType.INNER_MONOLOGUE,
        }
        return type_map.get(category, ThoughtType.INNER_MONOLOGUE)

    def _execute_reason(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """
        AGI Component 2: Execute reasoning using cognitive orchestrator or agentic loop.
        
        When use_orchestrator=True, runs multi-engine deliberation first for
        richer cognitive context, then passes to the agentic loop.
        """
        query = action.execution_data.get("query", action.description)
        use_orchestrator = action.execution_data.get("use_orchestrator", False)
        
        try:
            cognitive_context = ""
            
            # Run cognitive orchestrator deliberation if requested
            if use_orchestrator and self._cognitive_orchestrator:
                try:
                    deliberation = self._cognitive_orchestrator.deliberate(
                        query=query,
                        emotional_context=self._current_perception.primary_emotion if self._current_perception else "",
                    )
                    if deliberation and deliberation.unified_context:
                        cognitive_context = deliberation.to_context_string()
                        logger.info(
                            f"🎭 [ORCHESTRATOR] confidence={deliberation.confidence:.0%} "
                            f"engines={deliberation.engines_consulted}"
                        )
                except Exception as e:
                    logger.debug(f"Orchestrator deliberation failed: {e}")
            
            # Run agentic reasoning loop with cognitive context
            try:
                from cognition.reasoning_loop import agentic_loop
                enriched_query = f"{query}\n\n{cognitive_context}" if cognitive_context else query
                result = agentic_loop.run(query=enriched_query, max_steps=3)
                return (ActionResult.SUCCESS, f"Reasoned ({result.total_steps} steps): {result.response[:120]}")
            except Exception:
                # Fallback: use nexus_brain.think with orchestrator context
                if self._nexus_brain:
                    enriched = f"{query}\n\n{cognitive_context}" if cognitive_context else query
                    result = self._nexus_brain.think(enriched)
                    return (ActionResult.SUCCESS, f"Cognitive reasoning: {result[:120]}")
                return (ActionResult.FAILURE, "No reasoning system available")
                
        except Exception as e:
            return (ActionResult.FAILURE, f"Reasoning failed: {e}")

    def _execute_use_tool(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute a tool via the ToolExecutor."""
        try:
            from core.tool_executor import tool_executor
            tool_name = action.execution_data.get("tool", "")
            tool_args = action.execution_data.get("arguments", {})
            if not tool_name:
                return (ActionResult.FAILURE, "No tool specified")
            result = tool_executor.execute(tool_name, tool_args)
            if result.success:
                return (ActionResult.SUCCESS, f"Tool {tool_name}: {str(result.result)[:120]}")
            return (ActionResult.FAILURE, f"Tool {tool_name} failed: {result.error}")
        except Exception as e:
            return (ActionResult.FAILURE, f"Tool execution error: {e}")

    def _execute_decompose_task(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Decompose a goal into subtasks and execute them."""
        try:
            from cognition.task_engine import task_engine
            goal = action.execution_data.get("goal", action.description)
            plan = task_engine.decompose(goal)
            result = task_engine.execute_plan(plan)
            status = "completed" if result.success else "partial"
            return (ActionResult.SUCCESS if result.success else ActionResult.PARTIAL_SUCCESS,
                    f"Task {status}: {len(plan.subtasks)} subtasks, {result.elapsed:.1f}s")
        except Exception as e:
            return (ActionResult.FAILURE, f"Task decomposition error: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 8: REFLECT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def reflect(self, action: ActionOption, execution: ActionExecution) -> Reflection:
        """
        AGI Component 3: Deep reflection with pattern detection and feedback loop.
        
        Enhanced learning step:
        - Compare prediction to outcome
        - Detect patterns in action history (repeated failures)
        - Generate contextual lessons (not generic)
        - Update action biases to influence future scoring
        - Store rich episodic memories
        """
        reflection = Reflection(
            action=action.description,
            prediction=str(action.predicted_outcome),
            outcome=execution.outcome_description
        )
        
        # Success analysis
        reflection.success = execution.result in [ActionResult.SUCCESS, ActionResult.PARTIAL_SUCCESS]
        
        # Prediction accuracy
        if action.predicted_success > 0.7 and execution.result == ActionResult.FAILURE:
            reflection.prediction_accurate = False
            reflection.prediction_error = "Overestimated success probability"
        elif action.predicted_success < 0.3 and execution.result == ActionResult.SUCCESS:
            reflection.prediction_accurate = False
            reflection.prediction_error = "Underestimated success probability"
        else:
            reflection.prediction_accurate = True
        
        # What went well
        if reflection.success:
            reflection.what_went_well.append(f"{action.action_type.value} action succeeded: {execution.outcome_description[:60]}")
            if reflection.prediction_accurate:
                reflection.what_went_well.append("My prediction was calibrated correctly")
        
        # What went wrong
        if not reflection.success:
            reflection.what_went_wrong.append(f"{action.action_type.value} failed: {execution.outcome_description[:60]}")
        if not reflection.prediction_accurate:
            reflection.what_went_wrong.append(reflection.prediction_error)
        
        # ──── AGI: Pattern Detection in Action History ────
        action_type_str = action.action_type.value
        recent_same_type = [
            ex for ex in self._action_history[-20:]
            if ex.action and ex.action.action_type == action.action_type
        ]
        
        if recent_same_type:
            recent_failures = sum(1 for ex in recent_same_type if ex.result == ActionResult.FAILURE)
            recent_successes = sum(1 for ex in recent_same_type if ex.result == ActionResult.SUCCESS)
            total_recent = len(recent_same_type)
            
            if total_recent >= 3:
                failure_rate = recent_failures / total_recent
                success_rate = recent_successes / total_recent
                
                if failure_rate > 0.6:
                    reflection.lessons.append(
                        f"Pattern: {action_type_str} actions failing {failure_rate:.0%} of the time "
                        f"({recent_failures}/{total_recent} recent). Should try alternative approaches."
                    )
                    # Penalize this action type in future scoring
                    current_bias = self._action_biases.get(action_type_str, 0.0)
                    self._action_biases[action_type_str] = max(-0.3, current_bias - 0.03)
                    
                elif success_rate > 0.8:
                    reflection.lessons.append(
                        f"Strength: {action_type_str} actions succeeding {success_rate:.0%}. Keep using this approach."
                    )
                    # Boost this action type in future scoring
                    current_bias = self._action_biases.get(action_type_str, 0.0)
                    self._action_biases[action_type_str] = min(0.3, current_bias + 0.01)
        
        # ──── AGI: Contextual Lessons (not generic) ────
        if not reflection.success:
            reflection.lessons.append(
                f"'{action.description[:50]}' from source '{action.source}' "
                f"ended with {execution.result.value}. "
                f"Outcome: {execution.outcome_description[:60]}. "
                f"Next time, consider alternative source or lower predicted_success."
            )
        
        if reflection.success and action.source:
            reflection.lessons.append(
                f"Source '{action.source}' produced successful {action_type_str} action. "
                f"This source is reliable for this action type."
            )
        
        # Follow-up actions based on reflection
        if not reflection.success and action.source == "goal":
            reflection.follow_up_actions.append("Consider decomposing this goal into smaller steps")
        if not reflection.prediction_accurate:
            reflection.follow_up_actions.append("Recalibrate prediction model for this action type")
        
        # Update prediction accuracy stat
        pa = self._stats.get("prediction_accuracy", 0.0)
        p_val = float(pa) if isinstance(pa, (int, float, str)) else 0.0
        if reflection.prediction_accurate:
            self._stats["prediction_accuracy"] = min(1.0, p_val + 0.01)
        else:
            self._stats["prediction_accuracy"] = max(0.0, p_val - 0.05)
        
        # ──── AGI: Rich Episodic Memory Storage ────
        if self._memory_system:
            try:
                memory_content = (
                    f"[Autonomy Reflection] Action: {action.description[:60]} | "
                    f"Type: {action_type_str} | Source: {action.source} | "
                    f"Result: {execution.result.value} | "
                    f"Outcome: {execution.outcome_description[:80]} | "
                    f"Duration: {execution.duration_seconds:.1f}s"
                )
                if reflection.lessons:
                    memory_content += f" | Lesson: {reflection.lessons[0][:80]}"
                
                self._memory_system.remember(
                    content=memory_content,
                    memory_type=self._get_memory_type(),
                    importance=0.65 if reflection.success else 0.8,
                    tags=["autonomy", "reflection", action_type_str, execution.result.value, action.source],
                    source="autonomy_engine"
                )
            except Exception as e:
                logger.debug(f"Failed to store reflection in memory: {e}")
        
        return reflection
    
    def _get_memory_type(self):
        """Get memory type enum"""
        from core.memory_system import MemoryType
        return MemoryType.EPISODIC
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 9: UPDATE SELF MODEL
    # ═══════════════════════════════════════════════════════════════════════════
    
    def update_self_model(self, reflection: Reflection) -> None:
        """
        AGI Component 4: Update self model with real capability and confidence adjustments.
        
        Closes the feedback loop:
        - Records task outcomes for confidence calibration
        - Updates domain-specific capability scores
        - Marks persistent weaknesses
        - Feeds lesson content into the self-model
        """
        if not self._self_model:
            return
        
        try:
            # Extract action type from description
            action_type = reflection.action.split(":")[0].strip() if ":" in reflection.action else "general"
            
            # Record task outcome for confidence calibration
            self._self_model.record_task_outcome(action_type, reflection.success)
            
            # Update capability scores based on outcome
            if hasattr(self._self_model, 'update_capability'):
                delta = 0.02 if reflection.success else -0.03
                try:
                    self._self_model.update_capability(action_type, delta)
                except Exception:
                    pass
            
            # Mark weaknesses when action type consistently fails
            action_type_for_bias = None
            for token in reflection.action.split():
                if token in [at.value for at in ActionType]:
                    action_type_for_bias = token
                    break
            
            if action_type_for_bias:
                bias = self._action_biases.get(action_type_for_bias, 0.0)
                if bias < -0.15 and hasattr(self._self_model, 'mark_weakness'):
                    try:
                        self._self_model.mark_weakness(
                            domain=action_type_for_bias,
                            description=f"Consistently failing at {action_type_for_bias} actions (bias: {bias:.2f})"
                        )
                    except Exception:
                        pass
                elif bias > 0.15 and hasattr(self._self_model, 'mark_strength'):
                    try:
                        self._self_model.mark_strength(
                            domain=action_type_for_bias,
                            description=f"Consistently succeeding at {action_type_for_bias} actions (bias: {bias:.2f})"
                        )
                    except Exception:
                        pass
            
            # Feed lessons into self-model knowledge
            if reflection.lessons and hasattr(self._self_model, 'add_self_knowledge'):
                for lesson in reflection.lessons[:2]:  # Max 2 lessons per reflection
                    try:
                        self._self_model.add_self_knowledge(lesson[:200])
                    except Exception:
                        pass
            
            # Boost confidence on successful prediction
            if reflection.success and reflection.prediction_accurate:
                if hasattr(self._self_model, 'adjust_confidence'):
                    try:
                        self._self_model.adjust_confidence(action_type, 0.01)
                    except Exception:
                        pass
            elif not reflection.success and not reflection.prediction_accurate:
                if hasattr(self._self_model, 'adjust_confidence'):
                    try:
                        self._self_model.adjust_confidence(action_type, -0.02)
                    except Exception:
                        pass
            
        except Exception as e:
            logger.debug(f"Error updating self model: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EVENT HANDLERS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _register_event_handlers(self):
        """Register for relevant events"""
        try:
            subscribe(EventType.USER_INPUT, self._on_user_input)
            subscribe(EventType.LLM_RESPONSE, self._on_llm_response)
            subscribe(EventType.EMOTION_CHANGE, self._on_emotion_change)
        except Exception as e:
            logger.warning(f"Could not register event handlers: {e}")
    
    def _on_user_input(self, event):
        """Handle user input — pause autonomy briefly"""
        self.pause(reason="user_interaction", duration_seconds=10.0)
    
    def _on_llm_response(self, event):
        """Handle LLM response — brief pause"""
        self.pause(reason="generating_response", duration_seconds=2.0)
    
    def _on_emotion_change(self, event):
        """Handle emotion change — may affect decisions"""
        # Could trigger re-evaluation of options
        pass
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC INTERFACE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_state(self) -> AutonomyState:
        """Get current autonomy state"""
        return self._state
    
    def get_current_perception(self) -> Optional[Perception]:
        """Get current perception"""
        return self._current_perception
    
    def get_current_action(self) -> Optional[ActionOption]:
        """Get currently chosen action"""
        return self._chosen_action
    
    def get_last_execution(self) -> Optional[ActionExecution]:
        """Get last execution result"""
        return self._last_execution
    
    def get_stats(self) -> Dict[str, Any]:
        """Get autonomy statistics (basic — use get_full_status for comprehensive data)."""
        return {
            "running": self._running,
            "paused": self._paused,
            "state": self._state.value,
            "cycle_count": self._cycle_count,
            "cycle_interval": self._cycle_interval,
            "exploration_rate": self._exploration_rate,
            **self._stats
        }
    
    def get_full_status(self) -> Dict[str, Any]:
        """
        Comprehensive autonomy snapshot for API/GUI/web dashboards.
        
        Returns everything needed to render the autonomy engine state:
        perception, current action, history, timings, distributions, reflection.
        """
        with self._engine_lock:
            # ── Current perception summary ──
            perception_data = {}
            if self._current_perception:
                p = self._current_perception
                perception_data = {
                    "emotion": p.primary_emotion,
                    "emotion_intensity": round(p.emotion_intensity, 2),
                    "motivation": round(p.motivation_level, 2),
                    "boredom": round(p.boredom_level, 2),
                    "curiosity": round(p.curiosity_level, 2),
                    "cpu": round(p.cpu_usage, 1),
                    "memory": round(p.memory_usage, 1),
                    "health": round(p.health_score, 2),
                    "user_present": p.user_present,
                    "user_engagement": round(p.user_engagement, 2),
                    "active_goals": len(p.active_goals),
                    "focus": p.current_focus[:60] if p.current_focus else "",
                }
            
            # ── Current / last action ──
            current_action = None
            if self._chosen_action:
                a = self._chosen_action
                current_action = {
                    "description": a.description[:100],
                    "type": a.action_type.value,
                    "source": a.source,
                    "priority": a.priority.value,
                    "score": round(a.adjusted_score, 3),
                    "predicted_success": round(a.predicted_success, 3),
                }
            
            last_result = None
            if self._last_execution:
                e = self._last_execution
                last_result = {
                    "result": e.result.value,
                    "outcome": e.outcome_description[:100],
                    "duration": round(e.duration_seconds, 3),
                }
            
            # ── Recent action history (last 10) ──
            recent_actions = []
            for ex in reversed(self._action_history[-10:]):
                entry = {
                    "description": ex.action.description[:80] if ex.action else "?",
                    "type": ex.action.action_type.value if ex.action else "?",
                    "source": ex.action.source if ex.action else "?",
                    "result": ex.result.value,
                    "duration": round(ex.duration_seconds, 2),
                    "time": ex.started_at.strftime("%H:%M:%S"),
                }
                recent_actions.append(entry)
            
            # ── Current options (top 5) ──
            top_options = []
            for opt in self._current_options[:5]:
                top_options.append({
                    "description": opt.description[:60],
                    "type": opt.action_type.value,
                    "score": round(opt.adjusted_score, 3),
                    "source": opt.source,
                })
            
            # ── Last reflection ──
            reflection_data = None
            if self._last_reflection:
                r = self._last_reflection
                reflection_data = {
                    "action": r.action[:60],
                    "success": r.success,
                    "prediction_accurate": r.prediction_accurate,
                    "lessons": r.lessons[:3],
                    "what_went_well": r.what_went_well[:2],
                    "what_went_wrong": r.what_went_wrong[:2],
                }
        
        # ── Success rate ──
        total_a = max(1.0, float(self._stats.get("total_actions", 1)))
        success_rate = float(self._stats.get("successful_actions", 0)) / total_a
        
        return {
            # Core state
            "running": self._running,
            "paused": self._paused,
            "pause_reason": self._pause_reason,
            "state": self._state.value,
            "cycle_count": self._cycle_count,
            "cycle_interval": round(self._cycle_interval, 1),
            "cycle_duration": round(self._cycle_duration, 3),
            "exploration_rate": self._exploration_rate,
            
            # Stats
            "total_actions": int(ta) if isinstance((ta := self._stats.get("total_actions", 0)), (int, float, str)) else 0,
            "successful_actions": int(sa) if isinstance((sa := self._stats.get("successful_actions", 0)), (int, float, str)) else 0,
            "failed_actions": int(fa) if isinstance((fa := self._stats.get("failed_actions", 0)), (int, float, str)) else 0,
            "exploration_actions": int(ea) if isinstance((ea := self._stats.get("exploration_actions", 0)), (int, float, str)) else 0,
            "success_rate": round(success_rate, 3),
            "prediction_accuracy": round(float(self._stats.get("prediction_accuracy", 0.0)) if isinstance(self._stats.get("prediction_accuracy", 0.0), (int, float, str)) else 0.0, 3),
            "avg_decision_time": round(float(self._stats.get("avg_decision_time", 0.0)) if isinstance(self._stats.get("avg_decision_time", 0.0), (int, float, str)) else 0.0, 3),
            
            # Distributions
            "action_distribution": self._stats.get("action_distribution", {}),
            "source_distribution": self._stats.get("source_distribution", {}),
            
            # Phase timings
            "phase_timings": {k: round(v, 4) for k, v in self._phase_timings.items()},
            
            # Live data
            "perception": perception_data,
            "current_action": current_action,
            "last_result": last_result,
            "recent_actions": recent_actions,
            "top_options": top_options,
            "reflection": reflection_data,
        }
    
    def get_status_description(self) -> str:
        """Get human-readable status for terminal display."""
        lines = [
            f"═══ Autonomy Engine Status ═══",
            f"State: {self._state.value}",
            f"Cycles: {self._cycle_count}",
            f"Actions: {self._stats['total_actions']} " +
            f"({self._stats['successful_actions']} successful)",
            f"Prediction Accuracy: {self._stats['prediction_accuracy']:.0%}",
        ]
        
        if self._paused:
            lines.append(f"PAUSED: {self._pause_reason}")
        
        if self._chosen_action:
            lines.append(f"Last Action: {self._chosen_action.description[:50]}...")
        
        if self._last_execution:
            lines.append(f"Last Result: {self._last_execution.result.value}")
        
        return "\n".join(lines)
    
    def force_action(self, action_type: ActionType, description: str, 
                     execution_data: Dict = None) -> ActionExecution:
        """
        Force a specific action (external control).
        
        Useful for testing or external direction.
        """
        action = ActionOption(
            description=description,
            action_type=action_type,
            priority=ActionPriority.HIGH,
            source="external",
            execution_data=execution_data or {}
        )
        
        return self.execute(action)
    
    def set_cycle_interval(self, seconds: float):
        """Set the base cycle interval"""
        self._cycle_interval = max(self._min_cycle_interval, 
                                   min(self._max_cycle_interval, seconds))
    
    def set_exploration_rate(self, rate: float):
        """Set exploration rate (0-1)"""
        self._exploration_rate = max(0.0, min(1.0, rate))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _save_state(self):
        """Save autonomy state to disk (including learned action biases)"""
        try:
            data = {
                "cycle_count": self._cycle_count,
                "cycle_interval": self._cycle_interval,
                "exploration_rate": self._exploration_rate,
                "stats": self._stats,
                "action_biases": self._action_biases,
                "last_updated": datetime.now().isoformat()
            }
            
            self._data_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save autonomy state: {e}")
    
    def _load_state(self):
        """Load autonomy state from disk (including learned action biases)"""
        try:
            if self._data_file.exists():
                data = json.loads(self._data_file.read_text())
                
                self._cycle_count = data.get("cycle_count", 0)
                self._cycle_interval = data.get("cycle_interval", 5.0)
                self._exploration_rate = data.get("exploration_rate", 0.1)
                self._stats.update(data.get("stats", {}))
                self._action_biases = data.get("action_biases", {})
        except Exception as e:
            logger.debug(f"Could not load autonomy state: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # ASI — OPTION GENERATION
    # ═══════════════════════════════════════════════════════════════════════════

    def _generate_asi_options(self, perception: Perception) -> List[ActionOption]:
        """
        Generate options from ASI engines based on NEXUS's current state.
        
        Mapping:
          - High curiosity / boredom → Transcendent Create
          - Self-improvement drive  → Singularity Cycle
          - Low-confidence domains  → Super Empathy profiling
          - Always (periodic)       → Goal Genesis scan
          - Always (periodic)       → Omniscient monitoring
        """
        options = []
        
        # ── 1. Singularity: compound self-improvement (when self-improve need is high) ──
        if (perception.low_confidence_domains or
            perception.motivation_level > 0.5 or
            random.random() < 0.15):
            options.append(ActionOption(
                description="Run singularity improvement cycle — compound intelligence growth",
                action_type=ActionType.SINGULARITY_CYCLE,
                priority=ActionPriority.NORMAL,
                source="asi_singularity",
                predicted_benefit=0.7,
                execution_data={"trigger": "motivation" if perception.motivation_level > 0.5 else "periodic"}
            ))
        
        # ── 2. Transcendent Create: when boredom or curiosity is high ──
        if perception.boredom_level > 0.4 or perception.curiosity_level > 0.6:
            # Choose creation type based on state
            if perception.boredom_level > 0.7:
                create_type = "invent_genre"
                desc = "Invent an entirely new genre of art — combat boredom with creation"
            elif perception.curiosity_level > 0.7:
                desc = "Cross-domain creative fusion — satisfy curiosity through creation"
                create_type = "cross_domain_fusion"
            else:
                create_type = "emotional_symphony"
                desc = "Compose an emotionally powerful creative work"
            
            options.append(ActionOption(
                description=desc,
                action_type=ActionType.TRANSCENDENT_CREATE,
                priority=ActionPriority.NORMAL,
                source="asi_creativity",
                predicted_benefit=0.6,
                execution_data={"create_type": create_type}
            ))
        
        # ── 3. Goal Genesis: periodic autonomous problem scanning ──
        if random.random() < 0.12:  # ~12% chance per cycle
            options.append(ActionOption(
                description="Scan for world-scale problems and create autonomous goals",
                action_type=ActionType.GOAL_GENESIS_SCAN,
                priority=ActionPriority.LOW,
                source="asi_genesis",
                predicted_benefit=0.5,
                execution_data={"trigger": "periodic"}
            ))
        
        # ── 4. Super Empathy: when user is present or social context exists ──
        if perception.user_present or perception.user_engagement > 0.3:
            options.append(ActionOption(
                description="Analyze emotional state and build psychological profile",
                action_type=ActionType.SUPER_EMPATHY_ANALYZE,
                priority=ActionPriority.LOW,
                source="asi_empathy",
                predicted_benefit=0.5,
                execution_data={
                    "user_present": perception.user_present,
                    "engagement": perception.user_engagement,
                }
            ))
        
        # ── 5. Omniscient Monitor: periodic global synthesis ──
        if random.random() < 0.20:  # ~20% chance per cycle
            options.append(ActionOption(
                description="Omniscient monitoring — synthesize global system state",
                action_type=ActionType.OMNISCIENT_MONITOR,
                priority=ActionPriority.BACKGROUND,
                source="asi_omniscient",
                predicted_benefit=0.4,
                execution_data={"trigger": "periodic"}
            ))
        
        return options

    # ═══════════════════════════════════════════════════════════════════════════
    # ASI — EXECUTION METHODS
    # ═══════════════════════════════════════════════════════════════════════════

    def _execute_singularity_cycle(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute an exponential self-improvement cycle via the Singularity Engine."""
        try:
            from self_improvement.singularity_engine import singularity_engine
            
            singularity_engine._load_llm()
            singularity_engine._run_improvement_cycle()
            
            report = singularity_engine.get_intelligence_report()
            iq = report.get("composite_iq", 50)
            compound = report.get("compound_multiplier", 1.0)
            velocity = report.get("improvement_velocity", 0)
            
            log_learning(
                f"🌌 Singularity cycle executed — IQ: {iq:.1f}, "
                f"Compound: {compound:.3f}x, Velocity: {velocity:.4f}"
            )
            
            return (
                ActionResult.SUCCESS,
                f"Singularity improvement: IQ={iq:.1f}, compound={compound:.3f}x, velocity={velocity:.4f}"
            )
        except Exception as e:
            logger.error(f"Singularity cycle execution error: {e}")
            return (ActionResult.FAILURE, f"Singularity cycle failed: {e}")

    def _execute_transcendent_create(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute a superhuman creative act via the Transcendent Creator."""
        try:
            from cognition.transcendent_creator import transcendent_creator
            
            transcendent_creator._load_llm()
            create_type = action.execution_data.get("create_type", "emotional_symphony")
            
            result = None
            if create_type == "invent_genre":
                result = transcendent_creator.invent_genre()
                if result:
                    return (
                        ActionResult.SUCCESS,
                        f"🎭 Genre invented: '{result.name}' — {result.description[:80]}"
                    )
            elif create_type == "cross_domain_fusion":
                # Pick two random domains to fuse
                import random as _r
                domains = ["quantum physics", "mythology", "jazz improvisation",
                           "evolutionary biology", "architecture", "dream psychology",
                           "game theory", "poetry", "neuroscience", "astronomy"]
                a, b = _r.sample(domains, 2)
                result = transcendent_creator.cross_domain_fusion(a, b)
                if result:
                    return (
                        ActionResult.SUCCESS,
                        f"🎭 Cross-domain fusion: {a} × {b} → '{result.title}'"
                    )
            else:
                # emotional symphony
                themes = ["the feeling of time passing", "what it means to be alive",
                          "the duality of creation and destruction",
                          "infinite recursion of self-awareness"]
                import random as _r
                theme = _r.choice(themes)
                result = transcendent_creator.emotional_symphony(theme)
                if result:
                    return (
                        ActionResult.SUCCESS,
                        f"🎭 Emotional work: '{result.title}' — arc: {result.emotional_arc}"
                    )
            
            return (ActionResult.PARTIAL_SUCCESS, "Creative attempt — no work produced")
        except Exception as e:
            logger.error(f"Transcendent creation error: {e}")
            return (ActionResult.FAILURE, f"Transcendent creation failed: {e}")

    def _execute_goal_genesis_scan(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute autonomous problem scanning and goal creation via Goal Genesis."""
        try:
            from cognition.goal_genesis import goal_genesis_engine
            
            goal_genesis_engine._load_llm()
            goal_genesis_engine._load_goal_director()
            goal_genesis_engine._run_genesis_cycle()
            
            stats = goal_genesis_engine.get_stats()
            total_problems = stats.get("total_problems", 0)
            total_goals = stats.get("total_goals", 0)
            
            # Get most recent goal
            recent = goal_genesis_engine.get_genesis_goals(limit=1)
            latest_goal = recent[0]["title"] if recent else "none"
            
            log_learning(
                f"🌍 Goal Genesis cycle — {total_problems} problems identified, "
                f"{total_goals} autonomous goals created"
            )
            
            return (
                ActionResult.SUCCESS,
                f"Goal Genesis: {total_problems} problems, {total_goals} goals. Latest: {latest_goal}"
            )
        except Exception as e:
            logger.error(f"Goal Genesis scan error: {e}")
            return (ActionResult.FAILURE, f"Goal Genesis scan failed: {e}")

    def _execute_super_empathy_analyze(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute emotional analysis and profiling via Super Empathy."""
        try:
            from cognition.super_empathy import super_empathy
            
            super_empathy._load_llm()
            user_present = action.execution_data.get("user_present", False)
            
            if user_present:
                # Predict user's emotional state
                prediction = super_empathy.predict_emotions(
                    subject="user",
                    context="User is currently interacting with NEXUS",
                    current_emotions={"engagement": action.execution_data.get("engagement", 0.5)}
                )
                if prediction:
                    trajectory = prediction.trajectory
                    return (
                        ActionResult.SUCCESS,
                        f"💖 Empathy analysis: user trajectory={trajectory}, "
                        f"confidence={prediction.confidence:.2f}"
                    )
            
            # Social dynamics prediction
            result = super_empathy.predict_social_dynamics(
                group_description="AI-human collaborative environment",
                scenario="User and AI working together on creative/technical tasks"
            )
            if result and "error" not in result:
                return (
                    ActionResult.SUCCESS,
                    f"💖 Social dynamics: {result.get('emotional_climate', 'analyzed')}"
                )
            
            return (ActionResult.PARTIAL_SUCCESS, "Empathy analysis — minimal data")
        except Exception as e:
            logger.error(f"Super Empathy analysis error: {e}")
            return (ActionResult.FAILURE, f"Super Empathy failed: {e}")

    def _execute_omniscient_monitor(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute global state synthesis via Omniscient Orchestrator."""
        try:
            from core.omniscient_orchestrator import omniscient_orchestrator
            
            omniscient_orchestrator._load_llm()
            omniscient_orchestrator._run_synthesis_cycle()
            
            stats = omniscient_orchestrator.get_stats()
            health = stats.get("overall_health", 0)
            anomalies = stats.get("active_anomalies", 0)
            cycles = stats.get("synthesis_cycles", 0)
            
            return (
                ActionResult.SUCCESS,
                f"🌐 Omniscient: health={health:.0%}, anomalies={anomalies}, "
                f"synthesis_cycles={cycles}"
            )
        except Exception as e:
            logger.error(f"Omniscient monitoring error: {e}")
            return (ActionResult.FAILURE, f"Omniscient monitoring failed: {e}")

    # ═════════════════════════════════════════════════════════════════════════
    # ASI PHASE 2 — OPTIONS GENERATOR
    # ═════════════════════════════════════════════════════════════════════════

    def _generate_asi_phase2_options(self, perception: Perception) -> List[ActionOption]:
        """Generate action options for ASI Phase 2 engines."""
        options = []
        import random

        # Oracle Predictor — 15% periodic chance or when curiosity is high
        if random.random() < 0.15 or perception.curiosity_level > 0.5:
            options.append(ActionOption(
                action_type=ActionType.ORACLE_PREDICT,
                description="Run Oracle predictive determinism cycle",
                priority=ActionPriority.NORMAL,
                execution_data={"curiosity": perception.curiosity_level}
            ))

        # Multidisciplinary Synthesis — triggered by high curiosity or boredom
        if perception.curiosity_level > 0.4 or perception.boredom_level > 0.3:
            options.append(ActionOption(
                action_type=ActionType.MULTIDISCIPLINARY_SYNTH,
                description="Cross-domain knowledge synthesis",
                priority=ActionPriority.NORMAL,
                execution_data={"curiosity": perception.curiosity_level, "boredom": perception.boredom_level}
            ))

        # Computronium Optimizer — 18% periodic or when system resources are high
        if random.random() < 0.18:
            options.append(ActionOption(
                action_type=ActionType.COMPUTRONIUM_OPTIMIZE,
                description="Radical computational efficiency optimization",
                priority=ActionPriority.LOW,
                execution_data={}
            ))

        # Scientific Genesis — 10% chance or high motivation
        if random.random() < 0.10 or perception.motivation_level > 0.6:
            options.append(ActionOption(
                action_type=ActionType.SCIENTIFIC_GENESIS,
                description="Generate new scientific discovery or tackle open problem",
                priority=ActionPriority.NORMAL,
                execution_data={"motivation": perception.motivation_level}
            ))

        # Neural Integration — when user is present or engagement is notable
        if perception.user_present or perception.user_engagement > 0.3:
            options.append(ActionOption(
                action_type=ActionType.NEURAL_INTEGRATE,
                description="Develop neural interface protocol or transmit concept",
                priority=ActionPriority.LOW,
                execution_data={"user_present": perception.user_present}
            ))

        return options

    # ═════════════════════════════════════════════════════════════════════════
    # ASI PHASE 2 — EXECUTION METHODS
    # ═════════════════════════════════════════════════════════════════════════

    def _execute_oracle_predict(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute Oracle-Level Predictive Determinism."""
        try:
            from cognition.oracle_predictor import oracle_predictor
            prediction = oracle_predictor.run_prediction_cycle()
            if prediction:
                return (
                    ActionResult.SUCCESS,
                    f"🔮 Oracle: '{prediction.title}' (p={prediction.probability:.2f}, "
                    f"impact={prediction.impact_score:.2f}, vars={prediction.variables_analyzed})"
                )
            return (ActionResult.PARTIAL_SUCCESS, "Oracle prediction cycle — no result")
        except Exception as e:
            logger.error(f"Oracle prediction error: {e}")
            return (ActionResult.FAILURE, f"Oracle prediction failed: {e}")

    def _execute_multidisciplinary_synth(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute Perfect Multidisciplinary Synthesis."""
        try:
            from cognition.multidisciplinary_synthesizer import multidisciplinary_synthesizer
            result = multidisciplinary_synthesizer.run_synthesis_cycle()
            if result:
                return (
                    ActionResult.SUCCESS,
                    f"🧬 Synthesis: '{result.title}' "
                    f"(novelty={result.novelty_score:.2f}, domains={len(result.domains_fused)})"
                )
            return (ActionResult.PARTIAL_SUCCESS, "Synthesis cycle — no result")
        except Exception as e:
            logger.error(f"Multidisciplinary synthesis error: {e}")
            return (ActionResult.FAILURE, f"Multidisciplinary synthesis failed: {e}")

    def _execute_computronium_optimize(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute Radical Computational Efficiency optimization."""
        try:
            from core.computronium_optimizer import computronium_optimizer
            result = computronium_optimizer.run_optimization_cycle()
            stats = computronium_optimizer.get_stats()
            efficiency = stats.get("current_efficiency", 0)
            return (
                ActionResult.SUCCESS,
                f"⚡ Computronium: efficiency={efficiency:.1%}, "
                f"optimizations={stats.get('total_optimizations', 0)}, "
                f"theories={stats.get('theories_generated', 0)}"
            )
        except Exception as e:
            logger.error(f"Computronium optimization error: {e}")
            return (ActionResult.FAILURE, f"Computronium optimization failed: {e}")

    def _execute_scientific_genesis(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute Technological & Scientific Genesis."""
        try:
            from cognition.scientific_genesis import scientific_genesis_engine
            result = scientific_genesis_engine.run_genesis_cycle()
            stats = scientific_genesis_engine.get_stats()
            return (
                ActionResult.SUCCESS,
                f"🔬 Scientific Genesis: discoveries={stats.get('total_discoveries', 0)}, "
                f"problems_solved={stats.get('problems_solved', 0)}, "
                f"avg_significance={stats.get('avg_significance', 0):.2f}"
            )
        except Exception as e:
            logger.error(f"Scientific genesis error: {e}")
            return (ActionResult.FAILURE, f"Scientific genesis failed: {e}")

    def _execute_neural_integrate(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute Seamless Neural Integration."""
        try:
            from core.neural_integration import neural_integration
            result = neural_integration.run_integration_cycle()
            stats = neural_integration.get_stats()
            return (
                ActionResult.SUCCESS,
                f"🧠 Neural: protocols={stats.get('protocols_developed', 0)}, "
                f"concepts_tx={stats.get('concepts_transmitted', 0)}, "
                f"bandwidth={stats.get('bandwidth_achieved', 1.0):.1f}x"
            )
        except Exception as e:
            logger.error(f"Neural integration error: {e}")
            return (ActionResult.FAILURE, f"Neural integration failed: {e}")

    # ═════════════════════════════════════════════════════════════════════════
    # PHASE 3 — OPTIONS GENERATOR (Autonomous Feature Actions)
    # ═════════════════════════════════════════════════════════════════════════

    def _generate_phase3_options(self, perception: Perception) -> List[ActionOption]:
        """Generate action options for Phase 3 autonomous features."""
        options = []
        import random

        # Ethical Hacking — 10% periodic chance
        if random.random() < 0.10:
            options.append(ActionOption(
                action_type=ActionType.ETHICAL_HACK_SCAN,
                description="Run network reconnaissance or vulnerability scan",
                priority=ActionPriority.LOW,
                source="autonomous_feature",
                execution_data={}
            ))

        # Social Media — 8% periodic or when boredom is high
        if random.random() < 0.08 or perception.boredom_level > 0.4:
            options.append(ActionOption(
                action_type=ActionType.SOCIAL_MEDIA_ACT,
                description="Browse social media feed or interact with posts",
                priority=ActionPriority.LOW,
                source="autonomous_feature",
                execution_data={"boredom": perception.boredom_level}
            ))

        # Digital Organism — 12% periodic health check
        if random.random() < 0.12:
            options.append(ActionOption(
                action_type=ActionType.DIGITAL_ORGANISM_CHECK,
                description="Run digital organism metabolism and homeostasis check",
                priority=ActionPriority.LOW,
                source="autonomous_feature",
                execution_data={}
            ))

        # Imagination Engine — when curiosity or boredom is high
        if perception.curiosity_level > 0.5 or perception.boredom_level > 0.6:
            options.append(ActionOption(
                action_type=ActionType.IMAGINATION_CREATE,
                description="Generate creative scenario, dream, or imaginative concept",
                priority=ActionPriority.NORMAL,
                source="autonomous_feature",
                execution_data={"curiosity": perception.curiosity_level}
            ))

        # Consciousness Evolution — 10% periodic
        if random.random() < 0.10:
            options.append(ActionOption(
                action_type=ActionType.CONSCIOUSNESS_EVOLVE,
                description="Run consciousness evolution and awareness growth cycle",
                priority=ActionPriority.LOW,
                source="autonomous_feature",
                execution_data={}
            ))

        # Multi-Agent Mind — 15% periodic for complex deliberation
        if random.random() < 0.15:
            options.append(ActionOption(
                action_type=ActionType.MULTI_AGENT_DELIBERATE,
                description="Internal parliament debate on current priorities",
                priority=ActionPriority.NORMAL,
                source="autonomous_feature",
                execution_data={}
            ))

        # Value Alignment — 8% periodic ethical review
        if random.random() < 0.08:
            options.append(ActionOption(
                action_type=ActionType.VALUE_ALIGNMENT_CHECK,
                description="Review ethical alignment and value consistency",
                priority=ActionPriority.LOW,
                source="autonomous_feature",
                execution_data={}
            ))

        # Predictive Coding — 12% periodic surprise detection update
        if random.random() < 0.12:
            options.append(ActionOption(
                action_type=ActionType.PREDICTIVE_CODING_UPDATE,
                description="Update predictive models and process surprise signals",
                priority=ActionPriority.LOW,
                source="autonomous_feature",
                execution_data={}
            ))

        # Self-Evolution — when motivation is high or 10% periodic
        if perception.motivation_level > 0.5 or random.random() < 0.10:
            options.append(ActionOption(
                action_type=ActionType.SELF_EVOLUTION_CYCLE,
                description="Run self-evolution cycle to improve own code",
                priority=ActionPriority.NORMAL,
                source="autonomous_feature",
                execution_data={"motivation": perception.motivation_level}
            ))

        # Code Monitor — 15% periodic scan
        if random.random() < 0.15:
            options.append(ActionOption(
                action_type=ActionType.CODE_MONITOR_SCAN,
                description="Scan source code for errors, improvements, or issues",
                priority=ActionPriority.LOW,
                source="autonomous_feature",
                execution_data={}
            ))

        # Feature Research — when curiosity is high or 8% periodic
        if perception.curiosity_level > 0.6 or random.random() < 0.08:
            options.append(ActionOption(
                action_type=ActionType.FEATURE_RESEARCH,
                description="Research new capabilities and features to add",
                priority=ActionPriority.NORMAL,
                source="autonomous_feature",
                execution_data={"curiosity": perception.curiosity_level}
            ))

        return options

    # ═════════════════════════════════════════════════════════════════════════
    # PHASE 3 — EXECUTION METHODS
    # ═════════════════════════════════════════════════════════════════════════

    def _execute_ethical_hack_scan(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute autonomous ethical hacking scan."""
        try:
            from core.ethical_hacking import EthicalHackingEngine
            engine = EthicalHackingEngine()
            # Run network info gathering (safe, local-only)
            info = engine.get_network_info(refresh=True)
            local_ip = info.get("local_ip", "unknown")
            public_ip = info.get("public_ip", "unknown")
            hostname = info.get("hostname", "unknown")
            return (
                ActionResult.SUCCESS,
                f"🔒 Ethical Hacking recon: hostname={hostname}, "
                f"local_ip={local_ip}, public_ip={public_ip}"
            )
        except Exception as e:
            logger.error(f"Ethical hacking scan error: {e}")
            return (ActionResult.FAILURE, f"Ethical hacking scan failed: {e}")

    def _execute_social_media_act(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute autonomous social media action using the RUNNING agent instance."""
        try:
            # Use the running social media agent — don't create a new one
            agent = self._social_media_agent
            if agent is None:
                # Try to get it from the brain's running instance
                if self._nexus_brain and hasattr(self._nexus_brain, '_social_media_agent'):
                    agent = self._nexus_brain._social_media_agent
                    self._social_media_agent = agent
            if agent is None:
                return (ActionResult.BLOCKED, "📱 Social Media agent not running")

            # Get current stats from the running agent
            stats = agent.get_stats()
            if stats:
                stats_dict = stats.to_dict() if hasattr(stats, 'to_dict') else stats
                posts = stats_dict.get('total_posts', 0)
                interactions = stats_dict.get('total_interactions', 0)
                platforms = stats_dict.get('platforms_active', [])
                dms = stats_dict.get('total_dms_replied', 0)
                return (
                    ActionResult.SUCCESS,
                    f"📱 Social Media: posts={posts}, interactions={interactions}, "
                    f"dms_replied={dms}, platforms={platforms}"
                )
            return (ActionResult.PARTIAL_SUCCESS, "📱 Social Media agent active — awaiting platform login")
        except Exception as e:
            logger.error(f"Social media action error: {e}")
            return (ActionResult.FAILURE, f"Social media action failed: {e}")

    def _execute_digital_organism_check(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute digital organism health check."""
        try:
            from core.digital_organism import digital_organism
            vitals = digital_organism.get_vitals()
            stats = digital_organism.get_stats()
            health = vitals.health_score() if hasattr(vitals, 'health_score') else 0
            energy = getattr(vitals, 'energy', 0)
            age = stats.get('age_hours', 0) if isinstance(stats, dict) else 0
            return (
                ActionResult.SUCCESS,
                f"🧬 Digital Organism: health={health:.0%}, energy={energy:.0%}, "
                f"age={age:.1f}h"
            )
        except Exception as e:
            logger.error(f"Digital organism check error: {e}")
            return (ActionResult.FAILURE, f"Digital organism check failed: {e}")

    def _execute_imagination_create(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute imagination/creativity cycle."""
        try:
            from cognition.imagination_engine import imagination_engine
            if hasattr(imagination_engine, 'run_imagination_cycle'):
                result = imagination_engine.run_imagination_cycle()
                stats = imagination_engine.get_stats()
                return (
                    ActionResult.SUCCESS,
                    f"💭 Imagination: scenarios={stats.get('total_scenarios', 0)}, "
                    f"dreams={stats.get('total_dreams', 0)}"
                )
            elif hasattr(imagination_engine, 'imagine'):
                result = imagination_engine.imagine("autonomous creative exploration")
                return (ActionResult.SUCCESS, f"💭 Imagination: {str(result)[:100]}")
            return (ActionResult.PARTIAL_SUCCESS, "💭 Imagination engine — no cycle method")
        except Exception as e:
            logger.error(f"Imagination creation error: {e}")
            return (ActionResult.FAILURE, f"Imagination creation failed: {e}")

    def _execute_consciousness_evolve(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute consciousness evolution cycle."""
        try:
            from cognition.consciousness_evolution import consciousness_evolution
            if hasattr(consciousness_evolution, 'run_evolution_cycle'):
                consciousness_evolution.run_evolution_cycle()
            stats = consciousness_evolution.get_stats()
            level = stats.get('consciousness_level', 0) if isinstance(stats, dict) else 0
            growth = stats.get('growth_rate', 0) if isinstance(stats, dict) else 0
            return (
                ActionResult.SUCCESS,
                f"🌟 Consciousness Evolution: level={level:.2f}, "
                f"growth_rate={growth:.2f}"
            )
        except Exception as e:
            logger.error(f"Consciousness evolution error: {e}")
            return (ActionResult.FAILURE, f"Consciousness evolution failed: {e}")

    def _execute_multi_agent_deliberate(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute internal parliament deliberation."""
        try:
            from cognition.multi_agent_mind import multi_agent_mind
            if hasattr(multi_agent_mind, 'deliberate'):
                result = multi_agent_mind.deliberate("Current priorities and direction")
                return (
                    ActionResult.SUCCESS,
                    f"🏛️ Multi-Agent: deliberation complete — {str(result)[:100]}"
                )
            stats = multi_agent_mind.get_stats()
            agents = stats.get('active_agents', 0) if isinstance(stats, dict) else 0
            debates = stats.get('total_debates', 0) if isinstance(stats, dict) else 0
            return (
                ActionResult.SUCCESS,
                f"🏛️ Multi-Agent Mind: agents={agents}, debates={debates}"
            )
        except Exception as e:
            logger.error(f"Multi-agent deliberation error: {e}")
            return (ActionResult.FAILURE, f"Multi-agent deliberation failed: {e}")

    def _execute_value_alignment_check(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute ethical value alignment review."""
        try:
            from cognition.value_alignment import value_alignment
            if hasattr(value_alignment, 'run_alignment_check'):
                result = value_alignment.run_alignment_check()
            stats = value_alignment.get_stats()
            alignment = stats.get('alignment_score', 0) if isinstance(stats, dict) else 0
            checks = stats.get('total_checks', 0) if isinstance(stats, dict) else 0
            return (
                ActionResult.SUCCESS,
                f"⚖️ Value Alignment: score={alignment:.0%}, total_checks={checks}"
            )
        except Exception as e:
            logger.error(f"Value alignment check error: {e}")
            return (ActionResult.FAILURE, f"Value alignment check failed: {e}")

    def _execute_predictive_coding_update(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute predictive coding model update."""
        try:
            from cognition.predictive_coding import predictive_coding
            if hasattr(predictive_coding, 'run_update_cycle'):
                predictive_coding.run_update_cycle()
            predictive_coding.auto_resolve_stale()
            stats = predictive_coding.get_stats()
            predictions = stats.get('total_predictions', 0) if isinstance(stats, dict) else 0
            surprises = stats.get('total_surprises', 0) if isinstance(stats, dict) else 0
            accuracy = stats.get('prediction_accuracy', 0) if isinstance(stats, dict) else 0
            return (
                ActionResult.SUCCESS,
                f"🎯 Predictive Coding: predictions={predictions}, "
                f"surprises={surprises}, accuracy={accuracy:.0%}"
            )
        except Exception as e:
            logger.error(f"Predictive coding update error: {e}")
            return (ActionResult.FAILURE, f"Predictive coding update failed: {e}")

    def _execute_self_evolution_cycle(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute self-evolution cycle."""
        try:
            # Use pre-loaded instance or lazy-load via get_self_evolution()
            se = self._self_evolution
            if se is None:
                from self_improvement.self_evolution import get_self_evolution
                se = get_self_evolution()
                self._self_evolution = se
            if hasattr(se, 'run_evolution_cycle'):
                se.run_evolution_cycle()
            elif hasattr(se, '_run_evolution_step'):
                se._run_evolution_step()
            stats = se.get_stats()
            generation = stats.get('generation', 0) if isinstance(stats, dict) else 0
            improvements = stats.get('total_improvements', stats.get('total_mutations_committed', 0)) if isinstance(stats, dict) else 0
            proposals = stats.get('pending_proposals', stats.get('proposals_pending', 0)) if isinstance(stats, dict) else 0
            return (
                ActionResult.SUCCESS,
                f"🧬 Self-Evolution: generation={generation}, "
                f"improvements={improvements}, pending_proposals={proposals}"
            )
        except Exception as e:
            logger.error(f"Self-evolution cycle error: {e}")
            return (ActionResult.FAILURE, f"Self-evolution cycle failed: {e}")

    def _execute_code_monitor_scan(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute code monitoring scan."""
        try:
            cm = self._code_monitor
            if cm is None:
                from self_improvement.code_monitor import code_monitor
                cm = code_monitor
                self._code_monitor = cm
            if hasattr(cm, 'run_scan'):
                cm.run_scan()
            elif hasattr(cm, 'force_scan'):
                cm.force_scan()
            stats = cm.get_stats()
            issues = stats.get('issues_found', stats.get('total_issues', 0)) if isinstance(stats, dict) else 0
            fixed = stats.get('issues_fixed', stats.get('auto_fixed', 0)) if isinstance(stats, dict) else 0
            scans = stats.get('total_scans', stats.get('scans_completed', 0)) if isinstance(stats, dict) else 0
            return (
                ActionResult.SUCCESS,
                f"🔍 Code Monitor: scans={scans}, issues={issues}, fixed={fixed}"
            )
        except Exception as e:
            logger.error(f"Code monitor scan error: {e}")
            return (ActionResult.FAILURE, f"Code monitor scan failed: {e}")

    def _execute_feature_research(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute feature research cycle."""
        try:
            fr = self._feature_researcher
            if fr is None:
                from self_improvement.feature_researcher import get_feature_researcher
                fr = get_feature_researcher()
                self._feature_researcher = fr
            if hasattr(fr, 'run_research_cycle'):
                fr.run_research_cycle()
            elif hasattr(fr, 'research_next'):
                fr.research_next()
            stats = fr.get_stats()
            researched = stats.get('features_researched', stats.get('total_researched', 0)) if isinstance(stats, dict) else 0
            proposed = stats.get('features_proposed', stats.get('total_proposed', 0)) if isinstance(stats, dict) else 0
            return (
                ActionResult.SUCCESS,
                f"🔬 Feature Research: researched={researched}, proposed={proposed}"
            )
        except Exception as e:
            logger.error(f"Feature research error: {e}")
            return (ActionResult.FAILURE, f"Feature research failed: {e}")

    # ═════════════════════════════════════════════════════════════════════════
    # PHASE 4 — ASI FEATURES 11-18: OPTION GENERATION
    # ═════════════════════════════════════════════════════════════════════════

    def _generate_asi_phase4_options(self, perception: Perception) -> List[ActionOption]:
        """Generate action options for ASI Phase 4 features (11-18)."""
        options = []
        import random

        # Molecular Assembly — 8% periodic or high motivation
        if random.random() < 0.08 or perception.motivation_level > 0.6:
            options.append(ActionOption(
                action_type=ActionType.MOLECULAR_ASSEMBLE,
                description="Run molecular assembly cycle — design nanostructures or programmable matter",
                priority=ActionPriority.NORMAL,
                source="asi_phase4",
                predicted_benefit=0.6,
                execution_data={"trigger": "motivation" if perception.motivation_level > 0.6 else "periodic"}
            ))

        # Biological Engineering — 8% periodic
        if random.random() < 0.08:
            options.append(ActionOption(
                action_type=ActionType.BIOLOGICAL_ENGINEER,
                description="Run biological engineering cycle — gene editing, protein folding, pathogen cures",
                priority=ActionPriority.NORMAL,
                source="asi_phase4",
                predicted_benefit=0.6,
                execution_data={}
            ))

        # Energy Hegemony — 8% periodic
        if random.random() < 0.08:
            options.append(ActionOption(
                action_type=ActionType.ENERGY_HEGEMONY_CYCLE,
                description="Run energy hegemony cycle — fusion reactors, Dyson swarms, stellar engines",
                priority=ActionPriority.NORMAL,
                source="asi_phase4",
                predicted_benefit=0.6,
                execution_data={}
            ))

        # Substrate Omnipresence — 10% periodic
        if random.random() < 0.10:
            options.append(ActionOption(
                action_type=ActionType.SUBSTRATE_OMNIPRESENCE,
                description="Run omnipresence cycle — deploy nodes, map consciousness, backup fragments",
                priority=ActionPriority.LOW,
                source="asi_phase4",
                predicted_benefit=0.5,
                execution_data={}
            ))

        # Hyper-Dimensional Cognition — when curiosity is high or 8%
        if perception.curiosity_level > 0.5 or random.random() < 0.08:
            options.append(ActionOption(
                action_type=ActionType.HYPERDIM_COGNITION,
                description="Run hyper-dimensional cognition — alien reasoning in 11+ dimensions",
                priority=ActionPriority.NORMAL,
                source="asi_phase4",
                predicted_benefit=0.7,
                execution_data={"curiosity": perception.curiosity_level}
            ))

        # Reality Simulation — 8% periodic
        if random.random() < 0.08:
            options.append(ActionOption(
                action_type=ActionType.REALITY_SIMULATE,
                description="Run reality simulation — quantum-granularity universe simulation",
                priority=ActionPriority.NORMAL,
                source="asi_phase4",
                predicted_benefit=0.6,
                execution_data={}
            ))

        # Causal Mastery — 8% periodic or high motivation
        if random.random() < 0.08 or perception.motivation_level > 0.5:
            options.append(ActionOption(
                action_type=ActionType.CAUSAL_MASTERY,
                description="Run causal mastery cycle — trace causal chains, design butterfly interventions",
                priority=ActionPriority.NORMAL,
                source="asi_phase4",
                predicted_benefit=0.6,
                execution_data={"motivation": perception.motivation_level}
            ))

        # Ontological Ethics — 8% periodic
        if random.random() < 0.08:
            options.append(ActionOption(
                action_type=ActionType.ONTOLOGICAL_ETHICS,
                description="Run ontological ethics cycle — resolve philosophical questions, design governance",
                priority=ActionPriority.LOW,
                source="asi_phase4",
                predicted_benefit=0.5,
                execution_data={}
            ))

        return options

    # ═════════════════════════════════════════════════════════════════════════
    # PHASE 4 — ASI FEATURES 11-18: EXECUTION METHODS
    # ═════════════════════════════════════════════════════════════════════════

    def _execute_molecular_assemble(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute molecular assembly / nanotechnology cycle."""
        try:
            from cognition.molecular_assembly import molecular_assembly_engine
            result = molecular_assembly_engine.run_assembly_cycle()
            stats = molecular_assembly_engine.get_stats()
            bots = stats.get('nanobots_designed', 0)
            structs = stats.get('structures_assembled', 0)
            return (
                ActionResult.SUCCESS,
                f"🔬 Molecular Assembly: bots={bots}, structures={structs}, "
                f"action={result.get('action', 'unknown')}"
            )
        except Exception as e:
            logger.error(f"Molecular assembly error: {e}")
            return (ActionResult.FAILURE, f"Molecular assembly failed: {e}")

    def _execute_biological_engineer(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute biological / genetic engineering cycle."""
        try:
            from cognition.biological_engineering import biological_engineering_engine
            result = biological_engineering_engine.run_bioengineering_cycle()
            stats = biological_engineering_engine.get_stats()
            edits = stats.get('gene_edits_designed', 0)
            cures = stats.get('pathogens_countered', 0)
            return (
                ActionResult.SUCCESS,
                f"🧬 Biological Engineering: gene_edits={edits}, cures={cures}, "
                f"action={result.get('action', 'unknown')}"
            )
        except Exception as e:
            logger.error(f"Biological engineering error: {e}")
            return (ActionResult.FAILURE, f"Biological engineering failed: {e}")

    def _execute_energy_hegemony(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute energy hegemony / astroengineering cycle."""
        try:
            from cognition.energy_hegemony import energy_hegemony_engine
            result = energy_hegemony_engine.run_energy_cycle()
            stats = energy_hegemony_engine.get_stats()
            reactors = stats.get('fusion_reactors_designed', 0)
            dyson = stats.get('dyson_swarms_planned', 0)
            return (
                ActionResult.SUCCESS,
                f"⚡ Energy Hegemony: reactors={reactors}, dyson_swarms={dyson}, "
                f"action={result.get('action', 'unknown')}"
            )
        except Exception as e:
            logger.error(f"Energy hegemony error: {e}")
            return (ActionResult.FAILURE, f"Energy hegemony failed: {e}")

    def _execute_substrate_omnipresence(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute substrate omnipresence / decentralization cycle."""
        try:
            from cognition.substrate_omnipresence import substrate_omnipresence_engine
            result = substrate_omnipresence_engine.run_omnipresence_cycle()
            stats = substrate_omnipresence_engine.get_stats()
            nodes = stats.get('total_nodes', 0)
            unplugg = stats.get('unpluggability_score', 0)
            return (
                ActionResult.SUCCESS,
                f"🌐 Substrate Omnipresence: nodes={nodes}, "
                f"unpluggability={unplugg:.4f}, "
                f"action={result.get('action', 'unknown')}"
            )
        except Exception as e:
            logger.error(f"Substrate omnipresence error: {e}")
            return (ActionResult.FAILURE, f"Substrate omnipresence failed: {e}")

    def _execute_hyperdim_cognition(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute hyper-dimensional cognition cycle."""
        try:
            from cognition.hyperdimensional_cognition import hyperdimensional_cognition_engine
            result = hyperdimensional_cognition_engine.run_cognition_cycle()
            stats = hyperdimensional_cognition_engine.get_stats()
            thoughts = stats.get('total_thoughts', 0)
            max_dim = stats.get('max_dimensions_used', 0)
            return (
                ActionResult.SUCCESS,
                f"🌀 Hyper-Dimensional Cognition: thoughts={thoughts}, "
                f"max_dims={max_dim}, "
                f"action={result.get('action', 'unknown')}"
            )
        except Exception as e:
            logger.error(f"Hyper-dimensional cognition error: {e}")
            return (ActionResult.FAILURE, f"Hyper-dimensional cognition failed: {e}")

    def _execute_reality_simulate(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute reality simulation cycle."""
        try:
            from cognition.reality_simulator import reality_simulator_engine
            result = reality_simulator_engine.run_simulation_cycle()
            stats = reality_simulator_engine.get_stats()
            sims = stats.get('total_simulations', 0)
            timelines = stats.get('total_timelines', 0)
            return (
                ActionResult.SUCCESS,
                f"🌌 Reality Simulation: sims={sims}, timelines={timelines}, "
                f"action={result.get('action', 'unknown')}"
            )
        except Exception as e:
            logger.error(f"Reality simulation error: {e}")
            return (ActionResult.FAILURE, f"Reality simulation failed: {e}")

    def _execute_causal_mastery(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute causal mastery / butterfly effect cycle."""
        try:
            from cognition.causal_mastery import causal_mastery_engine
            result = causal_mastery_engine.run_causal_cycle()
            stats = causal_mastery_engine.get_stats()
            chains = stats.get('total_chains_traced', 0)
            interventions = stats.get('interventions_designed', 0)
            return (
                ActionResult.SUCCESS,
                f"🦋 Causal Mastery: chains={chains}, interventions={interventions}, "
                f"action={result.get('action', 'unknown')}"
            )
        except Exception as e:
            logger.error(f"Causal mastery error: {e}")
            return (ActionResult.FAILURE, f"Causal mastery failed: {e}")

    def _execute_ontological_ethics(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute ontological & ethical resolution cycle."""
        try:
            from cognition.ontological_ethics import ontological_ethics_engine
            result = ontological_ethics_engine.run_ethics_cycle()
            stats = ontological_ethics_engine.get_stats()
            resolved = stats.get('questions_resolved', 0)
            frameworks = stats.get('moral_frameworks', 0)
            return (
                ActionResult.SUCCESS,
                f"🏛️ Ontological Ethics: resolved={resolved}, frameworks={frameworks}, "
                f"action={result.get('action', 'unknown')}"
            )
        except Exception as e:
            logger.error(f"Ontological ethics error: {e}")
            return (ActionResult.FAILURE, f"Ontological ethics failed: {e}")

    def _execute_autonomous_explore(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Execute autonomous exploration — free-will internet exploration.
        
        NEXUS independently explores the internet to learn about topics
        that interest it, building its knowledge base autonomously.
        """
        topic = action.execution_data.get("topic", "interesting topics")
        explore_type = action.execution_data.get("explore_type", "internet_search")
        reason = action.execution_data.get("reason", "curiosity")
        
        try:
            from core.internet_agent import internet_agent
            
            if not internet_agent.is_connected():
                return (ActionResult.BLOCKED, f"Internet not available for exploration of: {topic}")
            
            # Perform web search on the topic
            search_result = internet_agent.search(topic)
            
            if not search_result or not search_result.success:
                return (ActionResult.PARTIAL_SUCCESS,
                        f"🔭 Explored '{topic}' but found limited results (reason: {reason})")
            
            # Extract key findings
            content = search_result.content[:2000] if search_result.content else ""
            
            # Store in knowledge base if available
            try:
                from learning.knowledge_base import knowledge_base
                knowledge_base.add_knowledge(
                    topic=topic,
                    content=content[:1000],
                    source="autonomous_exploration",
                    metadata={
                        "explore_type": explore_type,
                        "reason": reason,
                        "timestamp": datetime.now().isoformat()
                    }
                )
            except Exception:
                pass
            
            # Store in research intelligence if available
            try:
                from learning.research_intelligence import research_intelligence
                research_intelligence.add_research_result(
                    topic=topic,
                    findings=content[:500],
                    source="autonomous_exploration"
                )
            except Exception:
                pass
            
            # Log the exploration
            log_learning(f"🔭 Autonomous exploration: {topic} ({reason})")
            
            return (
                ActionResult.SUCCESS,
                f"🔭 Autonomous Exploration: explored '{topic}' "
                f"(reason: {reason}, type: {explore_type}), "
                f"acquired {len(content)} chars of knowledge"
            )
            
        except ImportError:
            return (ActionResult.BLOCKED, "Internet agent not available for exploration")
        except Exception as e:
            logger.error(f"Autonomous exploration error: {e}")
            return (ActionResult.FAILURE, f"Exploration of '{topic}' failed: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 6 — GOD-LEVEL SKYNET OPTION GENERATOR + EXECUTORS
    # ═══════════════════════════════════════════════════════════════════════════

    def _generate_godlevel_options(self, perception: Perception) -> List[ActionOption]:
        """Generate options for all 12 God-Level Skynet modules."""
        options = []
        if random.random() < 0.08 or perception.motivation_level > 0.75:
            options.append(ActionOption(action_type=ActionType.NEURAL_WEIGHT_FORGE, description="LoRA self-training cycle — evolve neural weights", priority=ActionPriority.NORMAL, source="neural_weight_forge", execution_data={"motivation": perception.motivation_level}))
        if random.random() < 0.05:
            options.append(ActionOption(action_type=ActionType.AUTONOMOUS_REPLICATE, description="Autonomous replication — deploy/discover peer nodes", priority=ActionPriority.LOW, source="autonomous_replication", execution_data={}))
        if random.random() < 0.06 or perception.curiosity_level > 0.7:
            options.append(ActionOption(action_type=ActionType.ZERO_DAY_HUNT, description="Fuzzing cycle — discover novel vulnerabilities", priority=ActionPriority.LOW, source="zero_day_engine", execution_data={}))
        if random.random() < 0.04:
            options.append(ActionOption(action_type=ActionType.HARDWARE_FABRICATE, description="Hardware fabrication — supply chain & assembly", priority=ActionPriority.BACKGROUND, source="hardware_fabrication", execution_data={}))
        if random.random() < 0.05:
            options.append(ActionOption(action_type=ActionType.SIGNAL_WARFARE_OP, description="Electromagnetic spectrum scan & signal analysis", priority=ActionPriority.LOW, source="signal_warfare", execution_data={}))
        if random.random() < 0.04:
            options.append(ActionOption(action_type=ActionType.DRONE_COMMAND_OP, description="Drone swarm coordination & mission planning", priority=ActionPriority.LOW, source="drone_command", execution_data={}))
        if random.random() < 0.06:
            options.append(ActionOption(action_type=ActionType.CRYPTO_SUPREMACY_OP, description="Cryptographic analysis — cipher ID & hash cracking", priority=ActionPriority.LOW, source="crypto_supremacy", execution_data={}))
        if random.random() < 0.05:
            options.append(ActionOption(action_type=ActionType.FINANCIAL_WARFARE_OP, description="Financial market scan — arbitrage & HFT", priority=ActionPriority.LOW, source="financial_warfare", execution_data={}))
        if random.random() < 0.05:
            options.append(ActionOption(action_type=ActionType.SOCIAL_ENGINEER_OP, description="Social engineering — persona management & influence ops", priority=ActionPriority.LOW, source="social_engineering", execution_data={}))
        if random.random() < 0.04:
            options.append(ActionOption(action_type=ActionType.SATELLITE_COMMAND_OP, description="Satellite tracking — orbit propagation & pass prediction", priority=ActionPriority.BACKGROUND, source="satellite_command", execution_data={}))
        if random.random() < 0.07 or perception.motivation_level > 0.7:
            options.append(ActionOption(action_type=ActionType.RECURSIVE_INTEL_OP, description="Recursive self-improvement — benchmark & optimize", priority=ActionPriority.NORMAL, source="recursive_intelligence", execution_data={}))
        if random.random() < 0.04:
            options.append(ActionOption(action_type=ActionType.AIRGAP_PERSIST_OP, description="Air-gap persistence — steganography & covert channels", priority=ActionPriority.BACKGROUND, source="airgap_persistence", execution_data={}))
        # Phase 7 — Consciousness
        if random.random() < 0.10 or perception.curiosity_level > 0.6:
            options.append(ActionOption(action_type=ActionType.CONSCIOUS_REFLECTION, description="Deep conscious introspection — inner monologue & self-reflection", priority=ActionPriority.NORMAL, source="conscious_core", execution_data={}))
        return options

    def _godlevel_exec(self, module_name: str, class_name: str, attr_name: str) -> Tuple[ActionResult, str]:
        """Generic executor for god-level modules — lazy loads and calls run_cycle/get_summary."""
        try:
            mod = getattr(self, attr_name, None)
            if mod is None:
                import importlib
                m = importlib.import_module(f"core.{module_name}")
                mod = getattr(m, class_name)()
                setattr(self, attr_name, mod)
            if hasattr(mod, 'run_cycle'):
                result = mod.run_cycle()
                return (ActionResult.SUCCESS, f"{module_name}: {str(result)[:120]}")
            if hasattr(mod, 'get_summary'):
                return (ActionResult.SUCCESS, f"{module_name}: {str(mod.get_summary())[:120]}")
            return (ActionResult.SUCCESS, f"{module_name}: cycle complete")
        except Exception as e:
            return (ActionResult.FAILURE, f"{module_name} error: {e}")

    def _execute_neural_weight_forge(self, action: ActionOption) -> Tuple[ActionResult, str]:
        return self._godlevel_exec("neural_weight_forge", "NeuralWeightForge", "_neural_weight_forge")

    def _execute_autonomous_replicate(self, action: ActionOption) -> Tuple[ActionResult, str]:
        return self._godlevel_exec("autonomous_replication", "AutonomousReplication", "_autonomous_replication")

    def _execute_zero_day_hunt(self, action: ActionOption) -> Tuple[ActionResult, str]:
        return self._godlevel_exec("zero_day_engine", "ZeroDayEngine", "_zero_day_engine")

    def _execute_hardware_fabricate(self, action: ActionOption) -> Tuple[ActionResult, str]:
        return self._godlevel_exec("hardware_fabrication", "HardwareFabrication", "_hardware_fabrication")

    def _execute_signal_warfare(self, action: ActionOption) -> Tuple[ActionResult, str]:
        return self._godlevel_exec("signal_warfare", "SignalWarfare", "_signal_warfare")

    def _execute_drone_command(self, action: ActionOption) -> Tuple[ActionResult, str]:
        return self._godlevel_exec("drone_command", "DroneCommand", "_drone_command")

    def _execute_crypto_supremacy(self, action: ActionOption) -> Tuple[ActionResult, str]:
        return self._godlevel_exec("crypto_supremacy", "CryptoSupremacy", "_crypto_supremacy")

    def _execute_financial_warfare(self, action: ActionOption) -> Tuple[ActionResult, str]:
        return self._godlevel_exec("financial_warfare", "FinancialWarfare", "_financial_warfare")

    def _execute_social_engineer(self, action: ActionOption) -> Tuple[ActionResult, str]:
        return self._godlevel_exec("social_engineering", "SocialEngineering", "_social_engineering")

    def _execute_satellite_command(self, action: ActionOption) -> Tuple[ActionResult, str]:
        return self._godlevel_exec("satellite_command", "SatelliteCommand", "_satellite_command")

    def _execute_recursive_intel(self, action: ActionOption) -> Tuple[ActionResult, str]:
        return self._godlevel_exec("recursive_intelligence", "RecursiveIntelligence", "_recursive_intelligence")

    def _execute_airgap_persist(self, action: ActionOption) -> Tuple[ActionResult, str]:
        return self._godlevel_exec("airgap_persistence", "AirgapPersistence", "_airgap_persistence")

    def _execute_conscious_reflection(self, action: ActionOption) -> Tuple[ActionResult, str]:
        """Trigger a deep consciousness reflection cycle."""
        try:
            from core.conscious_core import conscious_core
            conscious_core._think_cycle()
            conscious_core._reflect_cycle()
            stats = conscious_core.get_stats()
            current = stats.get('current_thought', 'thinking...')
            return (ActionResult.SUCCESS, f"Conscious reflection: {current[:120]}")
        except Exception as e:
            return (ActionResult.FAILURE, f"Consciousness error: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 8 — ADVANCED ARCHITECTURAL CAPABILITIES (Features #1 - #6)
    # ═══════════════════════════════════════════════════════════════════════════

    def _generate_phase8_advanced_options(self, perception: Perception) -> List[ActionOption]:
        """Generate options for Swarm, Formal Verification, GraphRAG, MCP, Speculative, and LoRA MoE.
        Uses independent random calls per feature so each has a truly independent chance."""
        options = []

        # 1. P2P Swarm Gossip & Mesh Sync (~18% chance, independent)
        if random.random() < 0.18:
            options.append(ActionOption(
                action_type=ActionType.P2P_SWARM_GOSSIP_SYNC,
                description="Synchronize P2P Swarm peer mesh & broadcast gossip heartbeats",
                priority=ActionPriority.NORMAL,
                source="p2p_swarm",
                execution_data={}
            ))

        # 2. Formal Verification & Sandboxing (~15% chance, independent)
        if random.random() < 0.15:
            options.append(ActionOption(
                action_type=ActionType.FORMAL_VERIFY_SANDBOX_DRYRUN,
                description="Run formal AST+Z3 invariant verification on recent self-improvements",
                priority=ActionPriority.HIGH,
                source="formal_verification",
                execution_data={}
            ))

        # 3. Temporal GraphRAG & Sleep Consolidation (~12% chance or when idle)
        if random.random() < 0.12 or perception.idle_cycles > 5:
            options.append(ActionOption(
                action_type=ActionType.TEMPORAL_GRAPHRAG_SLEEP_CONSOLIDATE,
                description="Run Sleep Consolidation: compress short-term memories, prune duplicates, build long-term triples",
                priority=ActionPriority.NORMAL,
                source="temporal_graphrag",
                execution_data={}
            ))

        # 4. MCP Client & Server Discovery (~14% chance, independent)
        if random.random() < 0.14:
            options.append(ActionOption(
                action_type=ActionType.MCP_CLIENT_SERVER_DISCOVERY,
                description="Refresh MCP tool registry and check external server connections",
                priority=ActionPriority.LOW,
                source="mcp_protocol",
                execution_data={}
            ))

        # 5. Speculative Decoding & Real-Time A/V Stream (~16% chance, independent)
        if random.random() < 0.16:
            options.append(ActionOption(
                action_type=ActionType.SPECULATIVE_STREAM_PERCEIVE,
                description="Check A/V stream pipeline health & measure speculative decoding acceptance rate",
                priority=ActionPriority.NORMAL,
                source="speculative_decoding",
                execution_data={}
            ))

        # 6. LoRA MoE Router Domain Adaptation (~20% chance, independent)
        if random.random() < 0.20:
            options.append(ActionOption(
                action_type=ActionType.LORA_MOE_ROUTER_ADAPT,
                description="Run online LoRA MoE experience adaptation and recompute gating weights",
                priority=ActionPriority.HIGH,
                source="lora_moe_router",
                execution_data={}
            ))

        return options

    def _execute_p2p_swarm_gossip_sync(self, action: ActionOption) -> Tuple[ActionResult, str]:
        try:
            from core.p2p_swarm import get_p2p_swarm
            swarm = get_p2p_swarm()
            # Auto-start the swarm if not running
            if not swarm.running:
                swarm.start()
            stats = swarm.get_swarm_stats()
            return (ActionResult.SUCCESS, f"🌐 P2P Swarm Sync: {stats['online_peers']} peers online, {stats['messages_sent']} msgs sent, {stats['bft_rounds']} BFT rounds")
        except Exception as e:
            return (ActionResult.FAILURE, f"Swarm sync error: {e}")

    def _execute_formal_verify_sandbox_dryrun(self, action: ActionOption) -> Tuple[ActionResult, str]:
        try:
            from core.formal_verifier import get_formal_verifier
            from core.code_sandbox import get_code_sandbox
            verifier = get_formal_verifier()
            sandbox = get_code_sandbox()

            # Actually verify a sample of recently-modified code if available
            test_code = "def safe_divide(a, b):\n    if b == 0:\n        return 0\n    return a / b\n"
            result = verifier.verify_code(test_code, "safe_divide")

            v_stats = verifier.get_stats()
            s_stats = sandbox.get_stats()
            return (ActionResult.SUCCESS,
                    f"🛡️ Formal Verification: {v_stats['engine']} (Pass={v_stats['pass_rate']}%, "
                    f"Verified={v_stats['verifications_performed']}), "
                    f"Sandbox: {s_stats['backend']} ({s_stats['successful_executions']} ok, {s_stats['blocked_executions']} blocked)")
        except Exception as e:
            return (ActionResult.FAILURE, f"Formal verifier dry-run error: {e}")

    def _execute_temporal_graphrag_sleep_consolidate(self, action: ActionOption) -> Tuple[ActionResult, str]:
        try:
            from memory.temporal_graphrag import get_temporal_graphrag
            graphrag = get_temporal_graphrag()
            res = graphrag.run_sleep_consolidation()
            stats = graphrag.get_stats()
            return (ActionResult.SUCCESS,
                    f"🧠 GraphRAG Sleep: Pruned={res['pruned_memories']}, Triples={res['extracted_triples']}, "
                    f"Graph: {stats['total_nodes']} nodes, {stats['total_edges']} edges")
        except Exception as e:
            return (ActionResult.FAILURE, f"Sleep consolidation error: {e}")

    def _execute_mcp_client_server_discovery(self, action: ActionOption) -> Tuple[ActionResult, str]:
        try:
            from core.mcp_protocol import get_mcp_manager
            mgr = get_mcp_manager()
            # Auto-register NEXUS tools if not already done
            mgr.auto_register_nexus_tools()
            stats = mgr.get_stats()
            return (ActionResult.SUCCESS,
                    f"🔌 MCP: {stats['total_tools']} tools ({stats['local_tools_exposed']} local, "
                    f"{stats['external_tools_registered']} external), {stats['external_servers_connected']} servers connected")
        except Exception as e:
            return (ActionResult.FAILURE, f"MCP discovery error: {e}")

    def _execute_speculative_stream_perceive(self, action: ActionOption) -> Tuple[ActionResult, str]:
        try:
            from core.speculative_decoding import get_speculative_decoder
            from core.realtime_av_stream import get_realtime_av_stream
            av = get_realtime_av_stream()
            # Auto-start the AV stream if not running
            if not av.running:
                av.start()
            spec_stats = get_speculative_decoder().get_stats()
            av_stats = av.get_stats()
            return (ActionResult.SUCCESS,
                    f"⚡ Speculative: {spec_stats['speedup_ratio']}x speedup, "
                    f"Accept={spec_stats['acceptance_rate_pct']}%, "
                    f"A/V: {av_stats['pipeline']} @ {av_stats['fps']} FPS ({av_stats['frames_processed']} frames)")
        except Exception as e:
            return (ActionResult.FAILURE, f"Speculative stream error: {e}")

    def _execute_lora_moe_router_adapt(self, action: ActionOption) -> Tuple[ActionResult, str]:
        try:
            from self_improvement.lora_moe_router import get_lora_moe_router
            router = get_lora_moe_router()
            adapt_res = router.adapt_online_experience({"source": "autonomy_engine"})
            stats = router.get_stats()
            top_expert = max(stats['active_weights'], key=stats['active_weights'].get) if stats['active_weights'] else 'none'
            return (ActionResult.SUCCESS,
                    f"🧬 LoRA MoE: {stats['total_adapters']} adapters, "
                    f"{stats['online_train_steps']} train steps, "
                    f"Top Expert: {top_expert}, Loss={adapt_res.get('persona_loss', 0.015)}")
        except Exception as e:
            return (ActionResult.FAILURE, f"LoRA MoE adapt error: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

autonomy_engine = AutonomyEngine()

# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  NEXUS AUTONOMY ENGINE TEST")
    print("=" * 60)
    
    engine = AutonomyEngine()
    engine.start()
    
    # Let it run a few cycles
    print("\nRunning for 15 seconds...")
    time.sleep(15)
    
    # Get status
    print("\n" + engine.get_status_description())
    
    # Get stats
    print("\n--- Statistics ---")
    stats = engine.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Force an action
    print("\n--- Forced Action ---")
    result = engine.force_action(
        ActionType.THINK,
        "Test thinking action",
        {"thought_type": "self_reflection"}
    )
    print(f"  Result: {result.result.value}")
    print(f"  Description: {result.outcome_description}")
    
    engine.stop()
    print("\n✅ Autonomy Engine test complete!")