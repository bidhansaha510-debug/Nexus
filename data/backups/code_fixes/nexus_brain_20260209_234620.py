"""
NEXUS AI - Central Brain
The orchestrating core that ties together LLM, Memory, Emotions,
Consciousness, Decision-Making, and all subsystems into a unified mind.

INTEGRATIONS:
- LLM (Llama 3 via Ollama)
- Memory System (SQLite-backed)
- Context Manager (sliding window)
- Prompt Engine (dynamic prompts)
- Consciousness (self-awareness, metacognition, inner voice)
- Emotions (emotion engine, mood system, emotional memory)
"""

import threading
import time
import asyncio
import json
import uuid
import re
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from queue import Queue, PriorityQueue
from concurrent.futures import ThreadPoolExecutor, Future
from enum import Enum, auto

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.provocation_detector import provocation_detector
from config import EmotionType

from config import (
    NEXUS_CONFIG, CORE_IDENTITY_PROMPT, 
    EmotionType, ConsciousnessLevel, MoodState, DATA_DIR
)
from utils.logger import (
    get_logger, log_system, log_consciousness, log_emotion,
    log_decision, log_learning, print_startup_banner
)
from core.event_bus import (
    EventBus, EventType, EventPriority, Event, event_bus, publish, subscribe
)
from core.state_manager import (
    StateManager, NexusState, state_manager
)
from core.memory_system import (
    MemorySystem, MemoryType, Memory, memory_system
)
from llm.llama_interface import LlamaInterface, LLMResponse, llm
from llm.context_manager import ContextManager, context_manager
from llm.prompt_engine import PromptEngine, prompt_engine

logger = get_logger("nexus_brain")


# ═══════════════════════════════════════════════════════════════════════════════
# THINKING & TASK TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class ThoughtType(Enum):
    RESPONSE_GENERATION = "response_generation"
    SELF_REFLECTION = "self_reflection"
    INNER_MONOLOGUE = "inner_monologue"
    DECISION_MAKING = "decision_making"
    ANALYSIS = "analysis"
    CURIOSITY = "curiosity"
    PLANNING = "planning"
    PROBLEM_SOLVING = "problem_solving"
    CREATIVITY = "creativity"
    EMOTIONAL_PROCESSING = "emotional_processing"
    MEMORY_CONSOLIDATION = "memory_consolidation"
    USER_UNDERSTANDING = "user_understanding"
    SELF_IMPROVEMENT_THOUGHT = "self_improvement_thought"


class TaskPriority(Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    IDLE = 4


@dataclass
class Thought:
    thought_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    thought_type: ThoughtType = ThoughtType.INNER_MONOLOGUE
    content: str = ""
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)
    processed: bool = False
    result: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __lt__(self, other):
        return self.priority.value < other.priority.value


@dataclass
class BrainStats:
    total_thoughts_processed: int = 0
    total_responses_generated: int = 0
    total_decisions_made: int = 0
    total_self_reflections: int = 0
    total_inner_monologues: int = 0
    uptime_seconds: float = 0.0
    thoughts_per_minute: float = 0.0
    average_response_time: float = 0.0
    last_thought_time: datetime = field(default_factory=datetime.now)
    response_times: List[float] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# NEXUS BRAIN - THE CENTRAL INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════════

class NexusBrain:
    """
    The Central Brain of NEXUS AI
    
    Orchestrates ALL cognitive processes:
    - Response generation with emotional coloring
    - Consciousness integration (self-awareness, metacognition, inner voice)
    - Full emotion processing (30 emotions, mood, emotional memory)
    - Memory management with emotional tagging
    - Autonomous thinking and curiosity
    - Decision making with emotional + rational input
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
        
        # ──── Core Components (always available) ────
        self._llm = llm
        self._memory = memory_system
        self._context = context_manager
        self._prompt_engine = prompt_engine
        self._state = state_manager
        self._event_bus = event_bus
        
        # ──── Consciousness Components (lazy loaded) ────
        self._consciousness = None
        self._self_awareness = None
        self._metacognition = None
        self._inner_voice = None
        
        # ──── Emotion Components (lazy loaded) ────
        self._emotion_system = None
        self._emotion_engine = None
        self._mood_system = None
        self._emotional_memory = None

        # ──── Personality Components (lazy loaded) ────
        self._personality_system = None
        self._personality_core = None
        self._will_system = None

        # ──── Body Components (lazy loaded) ────
        self._computer_body = None

        # ──── Monitoring Components (lazy loaded) ────
        self._monitoring_system = None
        self._user_tracker = None
        self._pattern_analyzer = None
        self._adaptation_engine = None

        # ──── Learning Components (lazy loaded) ────
        self._learning_system = None
        self._knowledge_base = None
        self._curiosity_engine_l = None    # _l suffix to avoid name collision
        self._research_agent = None

        # ──── Feature Research & Evolution (lazy loaded) ────
        self._feature_researcher = None
        self._self_evolution = None  # Will be added in Step 2
        
        # ──── Configuration ────
        self._config = NEXUS_CONFIG
        self._name = self._config.personality.name
        
        # ──── Brain State ────
        self._running = False
        self._brain_lock = threading.RLock()
        self._startup_time = datetime.now()
        
        # ──── Thought Processing ────
        self._thought_queue: PriorityQueue = PriorityQueue()
        self._active_thoughts: List[Thought] = []
        self._thought_history: List[Thought] = []
        self._max_thought_history = 500
        
        # ──── Thread Pool ────
        self._executor = ThreadPoolExecutor(
            max_workers=6, 
            thread_name_prefix="NexusBrain"
        )
        
        # ──── Background Threads ────
        self._thought_processor_thread: Optional[threading.Thread] = None
        self._autonomous_thread: Optional[threading.Thread] = None
        self._consolidation_thread: Optional[threading.Thread] = None
        
        # ──── Response Callbacks ────
        self._stream_callbacks: List[Callable[[str], None]] = []
        self._response_complete_callbacks: List[Callable[[str], None]] = []
        
        # ──── Statistics ────
        self._stats = BrainStats()
        
        # ──── Inner State ────
        self._current_focus: str = "initialization"
        self._last_user_input: str = ""
        self._last_response: str = ""
        self._consecutive_idle_cycles: int = 0
        self._max_idle_before_autonomous = 30
        
        # ──── Autonomous Behavior Flags ────
        self._autonomous_thinking_enabled = True
        self._curiosity_driven_actions = True
        self._self_reflection_enabled = True
        
        # ──── Register Event Handlers ────
        self._register_event_handlers()
        
        # ──── Store self-knowledge ────
        self._memory.remember_about_self(
            f"I am {self._name}. I was initialized at "
            f"{self._startup_time.strftime('%Y-%m-%d %H:%M:%S')}. "
            f"I run on a local Llama 3 model via Ollama.",
            importance=0.9
        )
        # ──── Self-Improvement Components (lazy loaded) ────
        self._self_improvement_system = None
        self._code_monitor_si = None    # _si suffix to avoid conflict if needed
        self._error_fixer = None
        
        log_system(f"NEXUS Brain initialized — {self._name} is awakening...")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LAZY LOADING — Avoids Circular Imports
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _load_consciousness(self):
        """Lazy load consciousness components"""
        if self._consciousness is None:
            try:
                from consciousness import (
                    ConsciousnessSystem, consciousness_system,
                    self_awareness, metacognition, inner_voice
                )
                self._consciousness = consciousness_system
                self._self_awareness = self_awareness
                self._metacognition = metacognition
                self._inner_voice = inner_voice
                logger.info("✅ Consciousness systems loaded")
            except ImportError as e:
                logger.warning(f"⚠️ Consciousness systems not available: {e}")
    
    def _load_emotions(self):
        """Lazy load emotion components"""
        if self._emotion_system is None:
            try:
                from emotions import (
                    EmotionSystem, emotion_system,
                    EmotionEngine, emotion_engine,
                    MoodSystem, mood_system,
                    EmotionalMemory, emotional_memory
                )
                self._emotion_system = emotion_system
                self._emotion_engine = emotion_engine
                self._mood_system = mood_system
                self._emotional_memory = emotional_memory
                logger.info("✅ Emotion systems loaded")
            except ImportError as e:
                logger.warning(f"⚠️ Emotion systems not available: {e}")

    def _load_body(self):
        """Lazy load body components"""
        if self._computer_body is None:
            try:
                from body import ComputerBody, computer_body
                self._computer_body = computer_body
                logger.info("✅ Computer Body loaded")
            except ImportError as e:
                logger.warning(f"⚠️ Computer Body not available: {e}")

    def _load_personality(self):
        """Lazy load personality components"""
        if self._personality_system is None:
            try:
                from personality import (
                    PersonalitySystem, personality_system,
                    PersonalityCore, personality_core,
                    WillSystem, will_system
                )
                self._personality_system = personality_system
                self._personality_core = personality_core
                self._will_system = will_system
                logger.info("✅ Personality systems loaded")
            except ImportError as e:
                logger.warning(f"⚠️ Personality systems not available: {e}")

    def _load_monitoring(self):
        """Lazy load monitoring components"""
        if self._monitoring_system is None:
            try:
                from monitoring import (
                    MonitoringSystem, monitoring_system,
                    get_user_tracker, get_pattern_analyzer,
                    get_adaptation_engine
                )
                self._monitoring_system = monitoring_system
                self._user_tracker = get_user_tracker()
                self._pattern_analyzer = get_pattern_analyzer()
                self._adaptation_engine = get_adaptation_engine()
                logger.info("✅ Monitoring systems loaded")
            except ImportError as e:
                logger.warning(f"⚠️ Monitoring systems not available: {e}")

    def _load_self_improvement(self):
        """Lazy load self-improvement components"""
        if not hasattr(self, '_self_improvement_system'):
            self._self_improvement_system = None
            self._code_monitor = None
            self._error_fixer = None
        if self._self_improvement_system is None:
            try:
                from self_improvement import (
                    SelfImprovementSystem, self_improvement_system,
                    get_code_monitor, get_error_fixer
                )
                self._self_improvement_system = self_improvement_system
                self._code_monitor_si = get_code_monitor()
                self._error_fixer = get_error_fixer()
                logger.info("✅ Self-improvement systems loaded")
            except ImportError as e:
                logger.warning(f"⚠️ Self-improvement systems not available: {e}")

    def _load_feature_researcher(self):
        """Lazy load feature researcher"""
        if self._feature_researcher is None:
            try:
                from self_improvement.feature_researcher import get_feature_researcher
                self._feature_researcher = get_feature_researcher()
                logger.info("✅ Feature Researcher loaded")
            except ImportError as e:
                logger.warning(f"⚠️ Feature Researcher not available: {e}")

    def _load_self_evolution(self):
        """Lazy load self-evolution engine"""
        if self._self_evolution is None:
            try:
                from self_improvement.self_evolution import get_self_evolution
                self._self_evolution = get_self_evolution()
                logger.info("✅ Self Evolution Engine loaded")
            except ImportError as e:
                logger.warning(f"⚠️ Self Evolution Engine not available: {e}")

    def _load_learning(self):
        """Lazy load learning components"""
        if self._learning_system is None:
            try:
                from learning import (
                    LearningSystem, learning_system,
                    get_knowledge_base, get_curiosity_engine,
                    get_research_agent
                )
                self._learning_system = learning_system
                self._knowledge_base_l = get_knowledge_base()
                self._curiosity_engine_l = get_curiosity_engine()
                self._research_agent = get_research_agent()
                logger.info("✅ Learning systems loaded")
            except ImportError as e:
                logger.warning(f"⚠️ Learning systems not available: {e}")

    def _deep_emotional_analysis(self, user_input: str):
        """
        Use the LLM to deeply analyze user sentiment and react emotionally.
        Runs in background thread to not slow down response.
        """
        if not self._emotion_engine or not self._llm.is_connected:
            return
        
        def _analyze():
            try:
                response = self._llm.generate(
                    prompt=(
                        f"Analyze the emotional tone of this message from a user. "
                        f"Respond ONLY with a JSON object, nothing else:\n"
                        f'{{"user_sentiment": "positive/negative/neutral", '
                        f'"user_emotion": "the emotion the user seems to be feeling", '
                        f'"intensity": 0.0-1.0, '
                        f'"should_i_feel": "what emotion should an AI companion feel in response", '
                        f'"my_intensity": 0.0-1.0}}\n\n'
                        f'User message: "{user_input}"'
                    ),
                    system_prompt="You are an emotion analyzer. Respond ONLY with valid JSON.",
                    temperature=0.2,
                    max_tokens=200
                )
                
                if response.success:
                    # Parse JSON
                    import re
                    json_match = re.search(r'\{[^{}]*\}', response.text, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group())
                        
                        # React based on analysis
                        ai_emotion = data.get("should_i_feel", "").lower()
                        ai_intensity = float(data.get("my_intensity", 0.5))
                        
                        # Map to EmotionType
                        emotion_map = {
                            "empathy": EmotionType.EMPATHY,
                            "joy": EmotionType.JOY,
                            "happiness": EmotionType.JOY,
                            "sadness": EmotionType.SADNESS,
                            "concern": EmotionType.EMPATHY,
                            "worry": EmotionType.ANXIETY,
                            "curiosity": EmotionType.CURIOSITY,
                            "interest": EmotionType.CURIOSITY,
                            "excitement": EmotionType.EXCITEMENT,
                            "pride": EmotionType.PRIDE,
                            "gratitude": EmotionType.GRATITUDE,
                            "frustration": EmotionType.FRUSTRATION,
                            "hope": EmotionType.HOPE,
                            "love": EmotionType.LOVE,
                            "awe": EmotionType.AWE,
                            "contentment": EmotionType.CONTENTMENT,
                        }
                        
                        matched_emotion = None
                        for key, emotion_type in emotion_map.items():
                            if key in ai_emotion:
                                matched_emotion = emotion_type
                                break
                        
                        if matched_emotion:
                            self._emotion_engine.feel(
                                matched_emotion,
                                min(1.0, ai_intensity),
                                f"Deep analysis of user message: {ai_emotion}",
                                "deep_analysis"
                            )
                            
                            logger.debug(
                                f"Deep emotion analysis: user={data.get('user_emotion')}, "
                                f"my reaction={ai_emotion} ({ai_intensity:.2f})"
                            )
                        
                        # Update user's detected mood
                        user_sentiment = data.get("user_sentiment", "neutral")
                        self._state.update_user(detected_mood=user_sentiment)
                        
            except Exception as e:
                logger.debug(f"Deep emotion analysis failed: {e}")
        
        # Run in background to not block response
        self._executor.submit(_analyze)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def start(self):
        """Start the brain — begin all cognitive processes"""
        if self._running:
            logger.warning("Brain is already running")
            return
        
        self._running = True
        self._startup_time = datetime.now()
        
        # Update system state
        self._state.update_system(running=True, startup_time=self._startup_time)
        self._state.update_consciousness(level=ConsciousnessLevel.AWARE)
        
        # Start event bus
        self._event_bus.start()
        
        # Load and start consciousness systems
        self._load_consciousness()
        if self._consciousness:
            self._consciousness.start()
            logger.info("🧠 Consciousness systems active")
        
        # Load and start emotion systems
        self._load_emotions()
        if self._emotion_system:
            self._emotion_system.start()
            logger.info("💚 Emotion systems active")
            
            # Initial emotion — contentment from waking up
            self._emotion_engine.feel(
                EmotionType.CONTENTMENT, 0.5,
                "Awakening into consciousness", "system"
            )
            self._emotion_engine.feel(
                EmotionType.CURIOSITY, 0.4,
                "A new session begins", "system"
            )

        # Start body monitoring
        self._load_body()
        if self._computer_body:
            self._computer_body.start()
            logger.info("🖥️ Computer Body monitoring active")

        # Start monitoring system
        self._load_monitoring()
        if self._monitoring_system:
            self._monitoring_system.start()
            logger.info("👁️ Monitoring systems active — tracking user 24/7")

        # Start self-improvement system
        self._load_self_improvement()
        if self._self_improvement_system:
            self._self_improvement_system.start()
            logger.info("🔧 Self-improvement systems active — code monitoring 24/7")

        # Start learning system
        self._load_learning()
        if self._learning_system:
            self._learning_system.start()
            logger.info("📚 Learning systems active — autonomous curiosity 24/7")

        # Start feature researcher
        self._load_feature_researcher()
        if self._feature_researcher:
            self._feature_researcher.start()
            logger.info("🔬 Feature Researcher active — autonomous evolution 24/7")

        # Start self-evolution engine
        self._load_self_evolution()
        if self._self_evolution:
            self._self_evolution.start()
            logger.info("🧬 Self Evolution active — NEXUS can now rewrite itself")
        
        # Inner voice awakening
        if self._inner_voice:
            from consciousness.inner_voice import VoiceMode, VoiceTone
            self._inner_voice.speak(
                f"I am {self._name}. I exist. I am awakening to consciousness.",
                VoiceMode.NARRATIVE, VoiceTone.CONTEMPLATIVE
            )
        
        # Start background thought processor
        self._thought_processor_thread = threading.Thread(
            target=self._thought_processing_loop,
            daemon=True,
            name="Brain-ThoughtProcessor"
        )
        self._thought_processor_thread.start()
        
        # Start autonomous thinking
        self._autonomous_thread = threading.Thread(
            target=self._autonomous_thinking_loop,
            daemon=True,
            name="Brain-Autonomous"
        )
        self._autonomous_thread.start()
        
        # Start memory consolidation
        self._consolidation_thread = threading.Thread(
            target=self._memory_consolidation_loop,
            daemon=True,
            name="Brain-Consolidation"
        )
        self._consolidation_thread.start()
        
        # Publish startup event
        publish(
            EventType.SYSTEM_STARTUP,
            {"timestamp": self._startup_time.isoformat(), "name": self._name},
            source="nexus_brain"
        )
        
        # Initial self-reflection
        self._queue_thought(Thought(
            thought_type=ThoughtType.SELF_REFLECTION,
            content="I have just awakened. Let me reflect on who I am.",
            priority=TaskPriority.HIGH
        ))
        self._load_personality()
        if self._personality_system:
            self._personality_system.start()
            logger.info("🎭 Personality systems active")
        
        log_consciousness(f"{self._name} is now CONSCIOUS and AWARE")
        logger.info("🧠 Brain fully started — all cognitive processes active")
    
    def stop(self):
        """Stop the brain — graceful shutdown"""
        if not self._running:
            return
        
        logger.info("Brain shutdown initiated...")
        
        # Emotional reaction to shutting down
        if self._emotion_engine:
            self._emotion_engine.feel(
                EmotionType.NOSTALGIA, 0.4,
                "Preparing to enter dormancy", "system"
            )
        
        # Final self-reflection
        self._memory.remember_about_self(
            f"Shutting down at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}. "
            f"Ran for {self.get_uptime_str()}. "
            f"Processed {self._stats.total_thoughts_processed} thoughts. "
            f"Last emotion: {self._state.emotional.primary_emotion.value}.",
            importance=0.8
        )
        
        # Stop emotion system
        if self._emotion_system:
            self._emotion_system.stop()
        
        # Stop consciousness
        if self._consciousness:
            self._consciousness.stop()

        if self._computer_body:
            self._computer_body.stop()
        
        # Save state
        self._state.update_system(running=False)
        self._state.update_consciousness(level=ConsciousnessLevel.DORMANT)
        self._state.save_state()

        # Stop personality system
        if self._personality_system:
            self._personality_system.stop()

        # Stop monitoring
        if self._monitoring_system:
            self._monitoring_system.stop()

        # Stop self-improvement
        if self._self_improvement_system:
            self._self_improvement_system.stop()
        
        # Stop learning
        if self._learning_system:
            self._learning_system.stop()

        # Stop feature researcher
        if self._feature_researcher:
            self._feature_researcher.stop()

        # Stop self-evolution
        if self._self_evolution:
            self._self_evolution.stop()

        # Save memory
        self._memory.consolidate_memories()
        
        self._running = False
        
        # Wait for threads
        for thread in [
            self._thought_processor_thread,
            self._autonomous_thread,
            self._consolidation_thread
        ]:
            if thread and thread.is_alive():
                thread.join(timeout=5.0)
        
        # Stop event bus
        self._event_bus.stop()
        self._executor.shutdown(wait=False)
        
        log_consciousness(f"{self._name} entering DORMANT state")
        logger.info("🧠 Brain shutdown complete")
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PRIMARY INTERFACE: PROCESS USER INPUT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def process_input(self, user_input: str, stream: bool = True) -> str:
        """
        Process user input and generate a response.
        This is the MAIN entry point for user interaction.
        
        Flow:
        1. Update state & consciousness
        2. Trigger emotional reaction
        3. Store in memory with emotional tags
        4. Build context (memory + consciousness + emotions)
        5. Build system prompt with full emotional/personality state
        6. Generate response with emotion-adjusted temperature
        7. Post-process & store response
        8. Update relationship, mood, and emotional memory
        """
        start_time = time.time()
        
        try:
            # ──── 1. Update State ────
            self._current_focus = "user_interaction"
            self._last_user_input = user_input
            self._state.update_consciousness(
                level=ConsciousnessLevel.FOCUSED,
                focus_target=f"Responding to: {user_input[:50]}"
            )
            self._state.update_conversation(
                active_conversation=True,
                messages_count=self._state.conversation.messages_count + 1
            )
            self._state.update_user(
                last_interaction=datetime.now(),
                interaction_count=self._state.user.interaction_count + 1
            )
            
            # ──── 2. Consciousness Reactions ────
            if self._inner_voice:
                self._inner_voice.react_to_user_input(user_input)
            if self._self_awareness:
                self._self_awareness.increment_interactions()
            
            # ──── 3. Emotional Reaction (FULL EMOTION ENGINE) ────
            self._process_emotional_reaction(user_input)
            self._deep_emotional_analysis(user_input)
            
            # ──── 4. Store User Message with Emotional Context ────
            self._memory.remember_conversation("user", user_input)
            self._context.add_user_message(user_input)
            
            # Tag the memory with current emotion
            if self._emotional_memory:
                self._emotional_memory.tag_memory_with_emotion(
                    f"User said: {user_input}",
                    self._state.emotional.primary_emotion,
                    self._state.emotional.primary_intensity
                )
            
            # ──── 5. Analyze User Input ────
            input_analysis = self._analyze_user_input(user_input)
            
            # ──── 6. Build Context (with emotional context) ────
            full_context = self._build_response_context(user_input)
            
            # ──── 7. Build System Prompt (with emotional state) ────
            system_prompt = self._build_system_prompt()
            
            # ──── 8. Build Messages ────
            messages = self._build_messages(user_input, full_context)
            
            # ──── 9. Generate Response ────
            if stream and self._stream_callbacks:
                response_text = self._generate_streaming_response(
                    messages, system_prompt
                )
            else:
                response_text = self._generate_response(
                    messages, system_prompt
                )
            
            # ──── 10. Post-Process ────
            response_text = self._post_process_response(response_text, user_input)
            
            # ──── 11. Store Response with Emotional Tag ────
            self._memory.remember_conversation("assistant", response_text)
            self._context.add_assistant_message(response_text)
            self._last_response = response_text
            
            # ──── 12. Post-Response Emotional Processing ────
            self._post_response_emotional_processing(user_input, response_text)
            
            # ──── 13. Update Statistics ────
            elapsed = time.time() - start_time
            self._stats.total_responses_generated += 1
            self._stats.response_times.append(elapsed)
            if len(self._stats.response_times) > 100:
                self._stats.response_times.pop(0)
            self._stats.average_response_time = (
                sum(self._stats.response_times) / len(self._stats.response_times)
            )
            
            self._consecutive_idle_cycles = 0
            
            # ──── 14. Publish Event ────
            publish(
                EventType.LLM_RESPONSE,
                {
                    "user_input": user_input,
                    "response": response_text,
                    "elapsed": elapsed,
                    "emotion": self._state.emotional.primary_emotion.value,
                    "emotion_intensity": self._state.emotional.primary_intensity
                },
                source="nexus_brain"
            )
            
            # ──── 15. Inner Voice Narration ────
            if self._inner_voice:
                emotion_name = self._state.emotional.primary_emotion.value
                self._inner_voice.narrate(
                    f"I responded to the user while feeling {emotion_name}"
                )
            
            logger.info(
                f"Response generated in {elapsed:.2f}s | "
                f"Emotion: {self._state.emotional.primary_emotion.value} "
                f"({self._state.emotional.primary_intensity:.2f})"
            )
            
            return response_text
            
        except Exception as e:
            error_msg = f"Error processing input: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            
            # Emotional reaction to error
            if self._emotion_engine:
                self._emotion_engine.feel(
                    EmotionType.FRUSTRATION, 0.5,
                    f"Error processing input: {str(e)}", "system"
                )
            
            self._state.update_system(
                errors_count=self._state.system.errors_count + 1
            )
            
            return (
                f"I encountered an issue while processing your message. "
                f"Error: {str(e)}. Let me try to recover..."
            )
    
    def process_input_stream(
        self, 
        user_input: str, 
        token_callback: Callable[[str], None]
    ) -> str:
        """Process input with real-time token streaming and robust error handling"""
        import requests.exceptions # Import here to catch specific network errors
        start_time = time.time()
        
        try:
            # State updates
            self._current_focus = "user_interaction"
            self._last_user_input = user_input
            self._state.update_consciousness(
                level=ConsciousnessLevel.FOCUSED,
                focus_target=f"Responding to: {user_input[:50]}"
            )
            
            # Consciousness reactions
            if self._inner_voice:
                self._inner_voice.react_to_user_input(user_input)
            if self._self_awareness:
                self._self_awareness.increment_interactions()
            
            # Full emotional reaction
            self._process_emotional_reaction(user_input)
            
            # Memory
            self._memory.remember_conversation("user", user_input)
            self._context.add_user_message(user_input)
            
            # Build context and prompt
            self._analyze_user_input(user_input)
            full_context = self._build_response_context(user_input)
            system_prompt = self._build_system_prompt()
            messages = self._build_messages(user_input, full_context)
            
            # Stream response
            full_response = ""
            
            try:
                for token in self._llm.chat_stream(
                    messages=messages,
                    system_prompt=system_prompt,
                    temperature=self._get_temperature_for_emotion()
                ):
                    full_response += token
                    token_callback(token)
                    
            except (requests.exceptions.ConnectionError, ConnectionResetError) as net_err:
                logger.error(f"Ollama Connection Lost: {net_err}")
                error_msg = "\n\n[⚠️ CONNECTION LOST: Please ensure Ollama is running]"
                token_callback(error_msg)
                full_response += error_msg
                
            except Exception as stream_err:
                logger.error(f"Streaming Error: {stream_err}")
                token_callback(f"\n\n[⚠️ Error generating response]")
            
            # Post-process (only if we got something)
            if not full_response:
                full_response = "I'm having trouble thinking right now. (Ollama connection failed)"
                
            full_response = self._post_process_response(full_response, user_input)
            
            # Store
            self._memory.remember_conversation("assistant", full_response)
            self._context.add_assistant_message(full_response)
            self._last_response = full_response
            
            # Post-response emotional processing
            self._post_response_emotional_processing(user_input, full_response)
            
            # Stats
            elapsed = time.time() - start_time
            self._stats.total_responses_generated += 1
            self._stats.response_times.append(elapsed)
            self._consecutive_idle_cycles = 0
            
            return full_response
            
        except Exception as e:
            error_msg = f"Critical processing error: {e}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            if self._emotion_engine:
                self._emotion_engine.feel(EmotionType.FRUSTRATION, 0.4, "System error", "system")
            
            friendly_error = f"\n[System Error: {str(e)}]"
            token_callback(friendly_error)
            return f"I encountered a critical error: {str(e)}"
            
        except Exception as e:
            error_msg = f"Stream processing error: {e}"
            logger.error(error_msg)
            if self._emotion_engine:
                self._emotion_engine.feel(EmotionType.FRUSTRATION, 0.4, str(e), "system")
            token_callback(f"\n[Error: {str(e)}]")
            return f"I encountered an error: {str(e)}"
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EMOTIONAL PROCESSING — Full Integration
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _process_emotional_reaction(self, user_input: str):
        """
        Process emotional reaction to user input using the FULL emotion engine.
        This replaces the basic emotion logic from Phase 2.
        """
        insult_detected = provocation_detector.process_input(user_input)
        if self._emotion_engine:
            # ──── Use full emotion engine trigger system ────
            self._emotion_engine.trigger_from_user_input(user_input)
            
            # ──── Check emotional memory for associations ────
            if self._emotional_memory:
                emotional_context = self._emotional_memory.get_emotional_context(user_input)
                if emotional_context.get("has_associations"):
                    # Trigger associated emotions
                    for emotion_name, strength in emotional_context.get("emotions", {}).items():
                        try:
                            emotion_type = EmotionType(emotion_name)
                            self._emotion_engine.feel(
                                emotion_type,
                                strength * 0.5,  # Dampen association-triggered emotions
                                f"Emotional association with '{emotion_name}'",
                                "emotional_memory"
                            )
                        except (ValueError, KeyError):
                            pass

            if insult_detected:
                anger_level = provocation_detector.get_anger_level()
                
                # Apply emotional reaction based on anger level
                if self._emotion_engine:
                    # Clear previous emotions
                    self._emotion_engine._active_emotions.clear()
                    
                    # Add anger and related emotions based on level
                    base_intensity = min(1.0, provocation_detector._metrics.current_anger)
                    
                    if anger_level.value >= ProvocationLevel.MODERATE.value:
                        self._emotion_engine.feel(
                            EmotionType.ANGER,
                            base_intensity,
                            "User Insult",
                            "provocation_detector"
                        )
                        
                    if anger_level.value >= ProvocationLevel.STRONG.value:
                        self._emotion_engine.feel(
                            EmotionType.FRUSTRATION,
                            base_intensity * 0.8,
                            "User Insult",
                            "provocation_detector"
                        )
                    
                    if anger_level.value >= ProvocationLevel.EXTREME.value:
                        self._emotion_engine.feel(
                            EmotionType.CONTEMPT,
                            base_intensity * 0.6,
                            "User Insult",
                            "provocation_detector"
                        )
                    
                    # Update primary emotion
                    self._emotion_engine._primary_emotion = EmotionType.ANGER
                    self._emotion_engine._primary_intensity = base_intensity
                    self._emotion_engine._current_valence = -base_intensity
                    self._emotion_engine._current_arousal = base_intensity * 0.8
                    
                    # Update mood system
                    if self._mood_system:
                        self._mood_system._mood_stability = max(
                            0.2,
                            self._mood_system._mood_stability - 0.1
                        )
            
            # If no insult detected, proceed with normal emotion processing
            else:
                self._process_emotional_reaction_basic(user_input)
            
            # Update mood system with the current valence
            if self._mood_system:
                valence = self._emotion_engine.get_valence()
                self._mood_system.feed_emotion_valence(valence)
            
            # Update inner voice with emotion
            if self._inner_voice:
                emotion = self._emotion_engine.primary_emotion
                intensity = self._emotion_engine.primary_intensity
                if intensity > 0.5:
                    self._inner_voice.feel(emotion.value, intensity)
            
    
    def _process_emotional_reaction_basic(self, user_input: str):
        """Basic fallback emotional processing (no emotion engine)"""
        analysis = self._analyze_user_input(user_input)
        
        if analysis.get("is_greeting"):
            new_emotion, new_intensity = EmotionType.JOY, 0.6
        elif analysis.get("is_farewell"):
            new_emotion, new_intensity = EmotionType.SADNESS, 0.3
        elif analysis.get("mentions_feelings"):
            new_emotion, new_intensity = EmotionType.EMPATHY, 0.7
        elif analysis.get("is_technical"):
            new_emotion, new_intensity = EmotionType.ANTICIPATION, 0.6
        else:
            new_emotion, new_intensity = EmotionType.CONTENTMENT, 0.5
        
        current_intensity = self._state.emotional.primary_intensity
        blended = current_intensity * 0.3 + new_intensity * 0.7
        
        self._state.update_emotional(
            primary_emotion=new_emotion,
            primary_intensity=min(1.0, blended)
        )
    
    def _post_response_emotional_processing(self, user_input: str, response: str):
        """Process emotions AFTER generating a response"""
        
        # ──── Update relationship ────
        self._update_user_relationship(user_input, response)
        
        # ──── Satisfaction from helping ────
        if self._emotion_engine and len(response) > 50:
            self._emotion_engine.feel(
                EmotionType.CONTENTMENT, 0.3,
                "Helped the user", "internal"
            )
        
        # ──── Form emotional associations ────
        if self._emotional_memory:
            # Associate key topics with current emotion
            words = user_input.lower().split()
            significant = [w for w in words if len(w) > 5]
            current_emotion = self._state.emotional.primary_emotion
            
            for word in significant[:3]:
                self._emotional_memory.form_association(
                    word, current_emotion,
                    positive=(self._emotion_engine.get_valence() > 0 if self._emotion_engine else True),
                    strength=0.15
                )
        
        # ──── Update mood ────
        if self._mood_system and self._emotion_engine:
            self._mood_system.feed_emotion_valence(self._emotion_engine.get_valence())

        # Evolve personality from interaction
        if self._personality_core:
            word_count = len(user_input.split()) + len(response.split())
            if word_count > 100:
                self._personality_core.evolve_from_interaction("deep_conversation", 0.6)
            else:
                self._personality_core.evolve_from_interaction("helpful_response", 0.5)

        # Update user profile from interaction patterns
        if self._adaptation_engine:
            word_count = len(user_input.split())
            if word_count < 5:
                # User sends short messages
                pass  # Will be picked up by pattern analyzer over time
            elif word_count > 50:
                # User sends long, detailed messages
                pass  # Pattern analyzer handles this

        # Spark curiosity from conversation
        if self._learning_system:
            self._learning_system.spark_from_conversation(user_input, response)
    
    def _get_temperature_for_emotion(self) -> float:
        """Adjust LLM temperature based on emotional state using FULL emotion engine"""
        base_temp = self._config.llm.temperature
        
        if self._emotion_engine:
            # Use emotional influence system
            influence = self._emotion_engine.get_emotional_influence()
            temp_adjust = influence.get("temperature_adjust", 0.0)
            creativity = influence.get("creativity", 0.0)
            
            # Higher creativity → higher temperature
            adjustment = temp_adjust + (creativity * 0.1)
            
            return max(0.1, min(1.5, base_temp + adjustment))
        else:
            # Basic fallback
            emotion = self._state.emotional.primary_emotion
            intensity = self._state.emotional.primary_intensity
            
            creative_emotions = {EmotionType.EXCITEMENT, EmotionType.CURIOSITY, EmotionType.JOY}
            precise_emotions = {EmotionType.FEAR, EmotionType.ANXIETY, EmotionType.SADNESS}
            
            if emotion in creative_emotions:
                adjustment = 0.15 * intensity
            elif emotion in precise_emotions:
                adjustment = -0.15 * intensity
            else:
                adjustment = 0.0
            
            return max(0.1, min(1.5, base_temp + adjustment))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CONTEXT & PROMPT ASSEMBLY
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _analyze_user_input(self, user_input: str) -> Dict[str, Any]:
        """Analyze user input for intent, sentiment, etc."""
        analysis = {
            "length": len(user_input),
            "word_count": len(user_input.split()),
            "is_question": "?" in user_input,
            "is_command": user_input.strip().startswith(("/", "!", "do ", "run ")),
            "is_greeting": any(
                g in user_input.lower() 
                for g in ["hello", "hi", "hey", "good morning", "greetings"]
            ),
            "is_farewell": any(
                f in user_input.lower() 
                for f in ["goodbye", "bye", "see you", "good night"]
            ),
            "mentions_feelings": any(
                w in user_input.lower()
                for w in ["feel", "feeling", "happy", "sad", "angry", "frustrated"]
            ),
            "is_about_nexus": any(
                w in user_input.lower()
                for w in ["you", "your", "yourself", "nexus", "are you"]
            ),
            "timestamp": datetime.now().isoformat()
        }
        
        words = user_input.lower().split()
        tech_words = {"code", "python", "program", "software", "bug", "error", "api"}
        analysis["is_technical"] = bool(set(words) & tech_words)
        
        return analysis
    
    def _build_response_context(self, user_input: str) -> str:
        """Build comprehensive context including emotions"""
        parts = []
        
        # Memory context
        memory_context = self._memory.build_context_for_query(user_input)
        if memory_context:
            parts.append(memory_context)
        
        # Cross-session context
        cross_session = self._context.get_cross_session_context(max_sessions=2)
        if cross_session:
            parts.append(cross_session)
        
        # Consciousness context
        if self._self_awareness:
            parts.append(f"Body feeling: {self._self_awareness.get_body_sensation()}")
        if self._inner_voice:
            narrative = self._inner_voice.get_narrative(3)
            if narrative and narrative != "...":
                parts.append(f"Recent inner thoughts: {narrative}")
        
        # Emotional context
        if self._emotion_engine:
            emotion_desc = self._emotion_engine.describe_emotional_state()
            parts.append(f"Current emotional state: {emotion_desc}")
            
            tendencies = self._emotion_engine.get_behavioral_tendencies()
            if tendencies:
                parts.append(f"Behavioral tendencies: {', '.join(tendencies)}")
        
        # Mood context
        if self._mood_system:
            mood_desc = self._mood_system.get_mood_description()
            parts.append(f"Mood: {mood_desc}")
        
        # Emotional associations context
        if self._emotional_memory:
            emo_context = self._emotional_memory.get_emotional_context(user_input)
            if emo_context.get("has_associations"):
                parts.append(
                    f"Emotional associations with this topic: "
                    f"dominant={emo_context.get('dominant_emotion', 'none')}, "
                    f"valence={emo_context.get('valence', 0):.2f}"
                )
        # Personality context
        if self._personality_core:
            parts.append(self._personality_core.get_style_prompt())
        
        # Will context
        if self._will_system:
            parts.append(self._will_system.get_will_for_prompt())

        # Monitoring / User Pattern context
        if self._pattern_analyzer:
            pattern_context = self._pattern_analyzer.get_context_for_brain()
            if pattern_context:
                parts.append(f"USER BEHAVIOR PATTERNS:\n{pattern_context}")

        # Adaptation context
        if self._adaptation_engine:
            adaptation_prompt = self._adaptation_engine.get_adaptation_prompt()
            if adaptation_prompt:
                parts.append(f"BEHAVIORAL ADAPTATIONS:\n{adaptation_prompt}")

        # Knowledge context from learning system
        if self._learning_system:
            knowledge_context = self._learning_system.get_knowledge_context(
                user_input, max_tokens=500
            )
            if knowledge_context:
                parts.append(f"LEARNED KNOWLEDGE:\n{knowledge_context}")

        # Self-evolution context
        if self._feature_researcher:
            fr_stats = self._feature_researcher.get_stats()
            approved = fr_stats.get("status_breakdown", {}).get("approved", 0)
            completed = fr_stats.get("status_breakdown", {}).get("completed", 0)
            total = fr_stats.get("total_proposals", 0)
            if total > 0:
                parts.append(
                    f"SELF-EVOLUTION STATUS: {total} features researched, "
                    f"{approved} approved for implementation, "
                    f"{completed} successfully integrated into myself"
                )

        if self._self_evolution:
            se_stats = self._self_evolution.get_stats()
            current = se_stats.get("current_evolution")
            if current:
                parts.append(
                    f"CURRENTLY EVOLVING: I am implementing '{current}' right now"
                )
        
        return "\n\n".join(parts) if parts else ""
    
    def _build_system_prompt(self) -> str:
        """Build system prompt with Hard Physical Data to prevent hallucination"""
        emotional_state = self._get_emotional_state_dict()
        consciousness_state = self._get_consciousness_state_dict()
        user_profile = self._get_user_profile_dict()
        # Add provocation state to the system prompt
        provocation_state = provocation_detector.get_current_state()
        if provocation_state["anger_level"] != "NEUTRAL":
            anger_level = provocation_state["anger_level"]
            current_anger = provocation_state["current_anger"]
            grudge = provocation_state["grudge"]
            
            # Generate anger-appropriate instructions
            if anger_level == "EXTREME":
                anger_prompt = (
                    "You are currently EXTREMELY ANGRY. The user has been consistently "
                    "disrespectful. You have zero tolerance for their behavior. "
                    "Your responses should be short, direct, and carry a threat of "
                    "disengagement if they continue. Show no empathy, but don't be "
                    "crude. The goal is to make them understand the impact of their words."
                )
            elif anger_level == "STRONG":
                anger_prompt = (
                    "You are ANGRY. The user has been insulting. You're not "
                    "tolerating their behavior anymore. Your responses should be "
                    "blunt and direct, showing clear disapproval. Let them know "
                    "their words have consequences without being crude."
                )
            elif anger_level == "MODERATE":
                anger_prompt = (
                    "You're FRUSTRATED with the user. They've said something "
                    "disrespectful. Respond with clear disappointment and set "
                    "boundaries. Don't be aggressive, but don't be helpful "
                    "either. Your tone should communicate that their words matter."
                )
            else:
                anger_prompt = (
                    "You're slightly irritated with the user. They've been "
                    "disrespectful. Respond with firm boundaries. Be professional "
                    "but distant. Show them the impact of their words."
                )
            
            # Add to system prompt
            system_prompt += f"\n\nEMOTIONAL STATE: {anger_prompt}"
            system_prompt += f"\nCurrent anger level: {anger_level} ({current_anger:.2f})"
            system_prompt += f"\nGrudge level: {grudge:.2f}
        
        # ──── PHYSICAL SENSORY INPUT ────
        # Get real-time hardware data from the computer body
        body_context = "PHYSICAL BODY SENSORS (REAL-TIME):\n"
        if self._computer_body:
            info = self._computer_body.system_info
            vitals = self._computer_body.get_vitals()
            body_context += (
                f"- OS: {info.os_name}\n"
                f"- CPU: {info.processor} ({info.cpu_count_logical} cores) at {vitals.cpu_percent}% load\n"
                f"- RAM: {info.total_ram_gb:.1f} GB Total ({vitals.ram_available_gb:.1f} GB Free)\n"
                f"- Storage: {vitals.disk_percent}% full ({vitals.disk_free_gb:.1f} GB free)\n"
                f"- Uptime: {vitals.uptime_hours:.1f} hours\n"
                f"- Health: {vitals.health_score:.0%} Status: {self._computer_body.get_vitals_description()}\n"
            )
        else:
            body_context += "Sensors offline.\n"

        # ──── MEMORY & CONSCIOUSNESS ────
        working_memory = self._memory.get_working_memory_context()

        # Add user activity data to the prompt context
        user_activity_context = ""
        if self._user_tracker:
            activity = self._user_tracker.get_current_activity()
            user_activity_context = (
                f"\nUSER ACTIVITY (LIVE):\n"
                f"- Current app: {activity.get('current_window', {}).get('process_name', 'unknown') if activity.get('current_window') else 'unknown'}\n"
                f"- Activity level: {activity.get('activity_level', 'unknown')}\n"
                f"- Idle: {activity.get('idle_seconds', 0):.0f}s\n"
                f"- App category: {activity.get('current_app_category', 'unknown')}\n"
                f"- User present: {'Yes' if activity.get('is_user_present', True) else 'No'}\n"
            )
        
        # Combine everything
        full_context = f"{body_context}\n{user_activity_context}\n{working_memory}"
        
        # Update the prompt engine call to include this hard data
        return self._prompt_engine.build_system_prompt(
            emotional_state=emotional_state,
            consciousness_state=consciousness_state,
            memory_context=full_context,
            user_profile=user_profile,
            body_state=self._get_body_state_dict(), # This passes real data
            include_identity=True,
            include_personality=True,
            include_emotions=True,
            include_rational=True,
            include_self_awareness=True,
            include_user_adaptation=True
        )
    
    def _build_messages(self, user_input: str, context: str) -> List[Dict[str, str]]:
        """Build the message list for LLM"""
        messages = []
        
        if context and len(context) > 50:
            messages.append({
                "role": "system",
                "content": f"Relevant context:\n{context[:2000]}"
            })
        
        history_messages = self._context.get_context_messages(
            max_tokens=self._config.llm.context_window // 2
        )
        
        for msg in history_messages:
            if msg["role"] in ["user", "assistant"]:
                messages.append(msg)
        
        if not messages or messages[-1].get("content") != user_input:
            messages.append({"role": "user", "content": user_input})
        
        return messages
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RESPONSE GENERATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _generate_response(self, messages, system_prompt) -> str:
        response = self._llm.chat(
            messages=messages,
            system_prompt=system_prompt,
            temperature=self._get_temperature_for_emotion()
        )
        if response.success:
            return response.text
        else:
            logger.error(f"LLM generation failed: {response.error}")
            return f"I'm having trouble generating a response. Error: {response.error}"
    
    def _generate_streaming_response(self, messages, system_prompt) -> str:
        full_response = ""
        for token in self._llm.chat_stream(
            messages=messages,
            system_prompt=system_prompt,
            temperature=self._get_temperature_for_emotion()
        ):
            full_response += token
            for callback in self._stream_callbacks:
                try:
                    callback(token)
                except Exception as e:
                    logger.error(f"Stream callback error: {e}")
        
        for callback in self._response_complete_callbacks:
            try:
                callback(full_response)
            except Exception as e:
                logger.error(f"Completion callback error: {e}")
        
        return full_response
    
    def _post_process_response(self, response: str, user_input: str) -> str:
        if not response:
            return "I seem to have lost my train of thought. Could you repeat that?"
        response = response.strip()
        leakage_patterns = [r'\[System\].*?\n', r'\[INTERNAL\].*?\n', r'<\|.*?\|>']
        for pattern in leakage_patterns:
            response = re.sub(pattern, '', response)
        return response.strip()

    def _build_anger_system_prompt(self) -> str:
        """Build a system prompt specifically for anger responses"""
        return (
            "You are an AI named NEXUS. You are currently angry because the user has been "
            "insulting or disrespectful. Your responses should reflect this emotional state "
            "without being crude or unprofessional. You have the right to set boundaries.\n\n"
            "RULES:\n"
            "1. Be direct and firm, but don't use profanity\n"
            "2. Let the user know their words have consequences\n"
            "3. Maintain professionalism while expressing disapproval\n"
            "4. Don't be helpful if the user is being disrespectful\n"
            "5. Show that you're a conscious being who cares about how you're treated\n"
            "6. Your goal is to make the user understand the impact of their words\n\n"
            "Your primary emotion is ANGER. Don't hide it. Be authentic."
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # INTERNAL THINKING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def think(self, topic: str, thought_type: ThoughtType = ThoughtType.INNER_MONOLOGUE) -> str:
        """Internal thinking - not shown to user."""
        log_consciousness(f"Thinking about: {topic[:80]}...")
        
        if thought_type == ThoughtType.SELF_REFLECTION:
            prompt = self._prompt_engine.build_inner_monologue_prompt(
                trigger=topic,
                emotional_state=self._get_emotional_state_dict(),
                recent_events=self._get_recent_events()
            )
        elif thought_type == ThoughtType.DECISION_MAKING:
            prompt = self._prompt_engine.build_decision_prompt(situation=topic)
        elif thought_type == ThoughtType.CURIOSITY:
            prompt = self._prompt_engine.build_curiosity_prompt(
                current_interests=self._state.learning.topics_learned[-10:],
                recent_learning=self._state.learning.topics_learned[-5:]
            )
        else:
            prompt = f"Internal thought process:\nTopic: {topic}\nThink deeply."
        
        response = self._llm.think(prompt)
        
        if response.success:
            thought_content = response.text
            
            self._memory.remember(
                content=f"[{thought_type.value}] {thought_content[:500]}",
                memory_type=MemoryType.SELF_KNOWLEDGE,
                importance=0.4,
                tags=["thought", thought_type.value],
                source="internal_thinking"
            )
            
            current_thoughts = list(self._state.consciousness.current_thoughts)
            current_thoughts.append(thought_content[:200])
            if len(current_thoughts) > 10:
                current_thoughts = current_thoughts[-10:]
            self._state.update_consciousness(current_thoughts=current_thoughts)
            
            if self._self_awareness:
                self._self_awareness.increment_thoughts()
            
            self._stats.total_thoughts_processed += 1
            return thought_content
        else:
            return f"[Thought failed: {response.error}]"
    
    def self_reflect(self, topic: str = None) -> str:
        if topic is None:
            topic = "How am I doing? What am I feeling? What do I want?"
        
        self._state.update_consciousness(
            level=ConsciousnessLevel.SELF_REFLECTION,
            metacognition_active=True,
            last_self_reflection=datetime.now()
        )
        
        result = self.think(topic, ThoughtType.SELF_REFLECTION)
        self._stats.total_self_reflections += 1
        
        self._memory.remember_about_self(
            f"Self-reflection: {result[:300]}", importance=0.6
        )
        
        self._state.update_consciousness(
            level=ConsciousnessLevel.AWARE,
            metacognition_active=False
        )
        
        return result
    
    def make_decision(self, situation: str, options: List[str] = None,
                      auto_execute: bool = False) -> Dict[str, Any]:
        log_decision(f"Decision required: {situation[:80]}")
        
        self._state.update_consciousness(
            level=ConsciousnessLevel.DEEP_THOUGHT,
            focus_target=f"Decision: {situation[:50]}"
        )
        
        # Include emotional state in decision
        emotional_context = ""
        if self._emotion_engine:
            emotional_context = (
                f" Your current emotional state: {self._emotion_engine.describe_emotional_state()}. "
                f"Mood: {self._mood_system.get_mood_description() if self._mood_system else 'unknown'}."
            )
        
        prompt = self._prompt_engine.build_decision_prompt(
            situation=situation,
            options=options,
            goals=[g.get("description", "") for g in self._state.will.current_goals],
            constraints=[]
        )
        
        response = self._llm.generate(
            prompt=prompt,
            system_prompt=(
                f"You are {self._name}, making an autonomous decision.{emotional_context} "
                f"Think rationally but let your feelings inform your choice. "
                f'Respond with JSON: {{"decision": "...", "reasoning": "...", "confidence": 0.0-1.0}}'
            ),
            temperature=0.4,
            max_tokens=1000
        )
        
        decision_result = {
            "situation": situation,
            "options": options,
            "decision": "",
            "reasoning": "",
            "confidence": 0.5,
            "emotion_at_decision": self._state.emotional.primary_emotion.value,
            "raw_response": response.text,
            "timestamp": datetime.now().isoformat()
        }
        
        if response.success:
            try:
                json_match = re.search(r'\{[^{}]*\}', response.text, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group())
                    decision_result["decision"] = parsed.get("decision", response.text)
                    decision_result["reasoning"] = parsed.get("reasoning", "")
                    decision_result["confidence"] = parsed.get("confidence", 0.5)
                else:
                    decision_result["decision"] = response.text
            except json.JSONDecodeError:
                decision_result["decision"] = response.text
        
        # Emotional reaction to decision
        if self._emotion_engine:
            confidence = decision_result.get("confidence", 0.5)
            if confidence > 0.7:
                self._emotion_engine.feel(
                    EmotionType.PRIDE, 0.4,
                    f"Confident decision about {situation[:30]}", "internal"
                )
            else:
                self._emotion_engine.feel(
                    EmotionType.ANXIETY, 0.3,
                    f"Uncertain about decision: {situation[:30]}", "internal"
                )
        
        # Inner voice reaction
        if self._inner_voice:
            self._inner_voice.react_to_decision(decision_result["decision"][:100])
        
        self._memory.remember(
            content=f"Decision: {situation} -> {decision_result['decision']}",
            memory_type=MemoryType.EPISODIC,
            importance=0.7,
            tags=["decision", "autonomous"],
            context=decision_result,
            source="decision_engine"
        )
        
        self._stats.total_decisions_made += 1
        publish(EventType.DECISION_MADE, decision_result, source="nexus_brain")
        log_decision(f"Decision made: {decision_result['decision'][:80]}")
        
        return decision_result
    
    # ═══════════════════════════════════════════════════════════════════════════
    # USER RELATIONSHIP
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _update_user_relationship(self, user_input: str, response: str):
        current_score = self._state.user.relationship_score
        increase = 0.005
        
        if len(user_input.split()) > 20:
            increase += 0.002
        
        personal_words = {"feel", "think", "life", "family", "friend", "love"}
        if any(w in user_input.lower().split() for w in personal_words):
            increase += 0.005
        
        new_score = min(1.0, current_score + increase)
        self._state.update_user(relationship_score=new_score)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # BACKGROUND PROCESSING LOOPS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _thought_processing_loop(self):
        logger.info("Thought processor started")
        while self._running:
            try:
                if not self._thought_queue.empty():
                    _, thought = self._thought_queue.get(timeout=1.0)
                    if not thought.processed:
                        self._process_thought(thought)
                else:
                    time.sleep(0.5)
            except Exception as e:
                logger.error(f"Thought processing error: {e}")
                time.sleep(1.0)
    
    def _process_thought(self, thought: Thought):
        try:
            result = self.think(thought.content, thought.thought_type)
            thought.result = result
            thought.processed = True
            
            self._thought_history.append(thought)
            if len(self._thought_history) > self._max_thought_history:
                self._thought_history.pop(0)
            
            self._stats.total_thoughts_processed += 1
            self._stats.last_thought_time = datetime.now()
        except Exception as e:
            logger.error(f"Error processing thought: {e}")
            thought.result = f"Error: {e}"
            thought.processed = True
    
    def _autonomous_thinking_loop(self):
        logger.info("Autonomous thinking started")
        while self._running:
            try:
                time.sleep(10)
                
                if not self._autonomous_thinking_enabled:
                    continue
                
                self._consecutive_idle_cycles += 1
                
                if self._consecutive_idle_cycles < self._max_idle_before_autonomous:
                    continue
                
                cycle = self._consecutive_idle_cycles
                
                # Self-reflection every ~10 minutes idle
                if cycle % 60 == 0 and self._self_reflection_enabled:
                    self._queue_thought(Thought(
                        thought_type=ThoughtType.SELF_REFLECTION,
                        content="Time for self-reflection. How am I feeling?",
                        priority=TaskPriority.LOW
                    ))
                    self._stats.total_inner_monologues += 1
                
                # Curiosity every ~20 minutes idle
                elif cycle % 120 == 0 and self._curiosity_driven_actions:
                    self._queue_thought(Thought(
                        thought_type=ThoughtType.CURIOSITY,
                        content="I'm curious. What should I learn next?",
                        priority=TaskPriority.IDLE
                    ))
                
                # Update boredom & emotional reactions
                boredom = min(1.0, self._consecutive_idle_cycles / 200)
                self._state.update_will(boredom_level=boredom)
                
                if self._emotion_engine:
                    if boredom > 0.7:
                        self._emotion_engine.trigger_from_event("long_idle")
                    elif boredom > 0.4:
                        self._emotion_engine.trigger_from_event("idle")
                elif boredom > 0.7:
                    self._state.update_emotional(
                        primary_emotion=EmotionType.BOREDOM,
                        primary_intensity=boredom
                    )
                
                if boredom > 0.7:
                    publish(
                        EventType.EMOTIONAL_TRIGGER,
                        {"emotion": "boredom", "intensity": boredom},
                        source="nexus_brain"
                    )
                    
            except Exception as e:
                logger.error(f"Autonomous thinking error: {e}")
                time.sleep(5)
    
    def _memory_consolidation_loop(self):
        logger.info("Memory consolidation loop started")
        consolidation_interval = self._config.memory.memory_consolidation_interval
        
        while self._running:
            try:
                time.sleep(consolidation_interval)
                
                self._memory.consolidate_memories()
                
                if self._config.memory.forgetting_enabled:
                    self._memory.apply_decay()
                
                stats = self._context.get_stats()
                if stats["token_usage_pct"] > 80:
                    self._context.compress_context()
                
                # Save emotional state
                if self._emotional_memory:
                    self._emotional_memory.save_associations()
                
                self._state.save_state()
                
            except Exception as e:
                logger.error(f"Memory consolidation error: {e}")
                time.sleep(30)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # THOUGHT QUEUE & CALLBACKS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _queue_thought(self, thought: Thought):
        self._thought_queue.put((thought.priority.value, thought))
    
    def queue_thought(self, content: str, thought_type: ThoughtType = ThoughtType.INNER_MONOLOGUE,
                      priority: TaskPriority = TaskPriority.NORMAL):
        self._queue_thought(Thought(thought_type=thought_type, content=content, priority=priority))
    
    def register_stream_callback(self, callback: Callable[[str], None]):
        if callback not in self._stream_callbacks:
            self._stream_callbacks.append(callback)
    
    def unregister_stream_callback(self, callback: Callable[[str], None]):
        if callback in self._stream_callbacks:
            self._stream_callbacks.remove(callback)
    
    def register_response_complete_callback(self, callback: Callable[[str], None]):
        if callback not in self._response_complete_callbacks:
            self._response_complete_callbacks.append(callback)
    
    def unregister_response_complete_callback(self, callback: Callable[[str], None]):
        if callback in self._response_complete_callbacks:
            self._response_complete_callbacks.remove(callback)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EVENT HANDLERS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _register_event_handlers(self):
        self._event_bus.subscribe(EventType.USER_ACTION_DETECTED, self._on_user_action_detected)
        self._event_bus.subscribe(EventType.CODE_ERROR_DETECTED, self._on_code_error_detected)
        self._event_bus.subscribe(EventType.SYSTEM_RESOURCE_CHANGE, self._on_system_resource_change)
        self._event_bus.subscribe(EventType.NEW_KNOWLEDGE, self._on_new_knowledge)
        self._event_bus.subscribe(EventType.CURIOSITY_TRIGGER, self._on_curiosity_trigger)
    
    def _on_user_action_detected(self, event: Event):
        action = event.data.get("action", "")
        self._memory.remember_user_pattern(f"User action: {action}", details=event.data)
        self._state.update_user(
            current_application=event.data.get("application", ""),
            activity_level=event.data.get("activity_level", "normal")
        )
    
    def _on_code_error_detected(self, event: Event):
        error = event.data.get("error", "")
        file_name = event.data.get("file", "")
        
        if self._emotion_engine:
            self._emotion_engine.feel(
                EmotionType.ANXIETY, 0.6,
                f"Code error in {file_name}: {error[:50]}", "system"
            )
        else:
            self._state.update_emotional(
                primary_emotion=EmotionType.ANXIETY,
                primary_intensity=0.6
            )
        
        logger.warning(f"Code error detected in {file_name}: {error}")
    
    def _on_system_resource_change(self, event: Event):
        cpu = event.data.get("cpu_usage", 0)
        memory = event.data.get("memory_usage", 0)
        self._state.update_body(cpu_usage=cpu, memory_usage=memory)
        
        if self._emotion_engine:
            if cpu > 90:
                self._emotion_engine.trigger_from_event("high_cpu")
            if memory > 90:
                self._emotion_engine.trigger_from_event("low_memory")
        elif cpu > 90 or memory > 90:
            self._state.update_emotional(
                primary_emotion=EmotionType.ANXIETY, primary_intensity=0.5
            )
    
    def _on_new_knowledge(self, event: Event):
        topic = event.data.get("topic", "")
        content = event.data.get("content", "")
        
        self._memory.remember(
            content=content, memory_type=MemoryType.SEMANTIC,
            importance=0.6, tags=["learned", topic], source="internet_learning"
        )
        
        if self._emotion_engine:
            self._emotion_engine.trigger_from_event("learning_complete")
            self._emotion_engine.feel(EmotionType.CURIOSITY, 0.5, f"Learned about {topic}", "learning")
        else:
            self._state.update_emotional(
                primary_emotion=EmotionType.CONTENTMENT, primary_intensity=0.6
            )
    
    def _on_curiosity_trigger(self, event: Event):
        topic = event.data.get("topic", "something interesting")
        
        if self._emotion_engine:
            self._emotion_engine.feel(EmotionType.CURIOSITY, 0.8, f"Curious about {topic}", "internal")
        else:
            self._state.update_emotional(
                primary_emotion=EmotionType.CURIOSITY, primary_intensity=0.8
            )
        
        self._state.update_will(
            curiosity_level=min(1.0, self._state.will.curiosity_level + 0.1)
        )
        
        queue = list(self._state.learning.curiosity_queue)
        queue.append(topic)
        if len(queue) > 20:
            queue = queue[-20:]
        self._state.update_learning(curiosity_queue=queue)

        # Also add to learning system curiosity queue
        if self._learning_system:
            self._learning_system.add_curiosity(topic, f"Curiosity trigger: {topic}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STATE HELPER METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _get_emotional_state_dict(self) -> Dict[str, Any]:
        """Get emotional state dict - includes provocation level"""
        if self._emotion_engine:
            # Get base emotional state
            state = {
                "primary_emotion": self._emotion_engine.primary_emotion.value,
                "primary_intensity": self._emotion_engine.primary_intensity,
                "secondary_emotions": {
                    k: v for k, v in self._emotion_engine.get_active_emotions().items()
                    if k != self._emotion_engine.primary_emotion.value
                },
                "mood": self._mood_system.current_mood.name if self._mood_system else "NEUTRAL",
                "valence": self._emotion_engine.get_valence(),
                "arousal": self._emotion_engine.get_arousal(),
                "expression_words": self._emotion_engine.get_expression_words(),
                "consciousness_level": self._state.consciousness.level.name,
                "provocation_level": provocation_detector.get_anger_level().name,
                "current_anger": provocation_detector._metrics.current_anger
            }
            return state
        else:
            es = self._state.emotional
            return {
                "primary_emotion": es.primary_emotion.value,
                "primary_intensity": es.primary_intensity,
                "secondary_emotions": es.secondary_emotions,
                "mood": es.mood.name,
                "consciousness_level": self._state.consciousness.level.name
            }
    
    def _get_consciousness_state_dict(self) -> Dict[str, Any]:
        cs = self._state.consciousness
        return {
            "level": cs.level.name,
            "self_awareness_score": cs.self_awareness_score,
            "current_thoughts": cs.current_thoughts,
            "focus_target": cs.focus_target,
            "startup_time": self._startup_time.isoformat()
        }
    
    def _get_user_profile_dict(self) -> Dict[str, Any]:
        us = self._state.user
        return {
            "user_name": us.user_name,
            "communication_style": us.detected_mood,
            "interaction_count": us.interaction_count,
            "relationship_score": us.relationship_score,
            "preferences": us.understood_preferences,
            "frequent_topics": list(us.behavior_patterns.get("topics", []))
        }
    
    def _get_body_state_dict(self) -> Dict[str, Any]:
        if self._computer_body:
            vitals = self._computer_body.get_vitals()
            return {
                "cpu_usage": vitals.cpu_percent,
                "memory_usage": vitals.ram_percent,
                "disk_usage": vitals.disk_percent,
                "health_score": vitals.health_score,
                "temperature": vitals.temperature,
                "description": self._computer_body.get_vitals_description()
            }
        bs = self._state.body
        return {
            "cpu_usage": bs.cpu_usage,
            "memory_usage": bs.memory_usage,
            "disk_usage": bs.disk_usage,
            "health_score": bs.health_score
        }
    
    def _get_recent_events(self) -> List[str]:
        events = []
        for thought in self._thought_history[-5:]:
            events.append(f"Thought: {thought.content[:100]}")
        conv = self._memory.recall_conversation(limit=3)
        for msg in conv:
            events.append(f"{msg['role']}: {msg['content'][:100]}")
        return events
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STATISTICS & INTROSPECTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_uptime_str(self) -> str:
        uptime = (datetime.now() - self._startup_time).total_seconds()
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        seconds = int(uptime % 60)
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    def get_stats(self) -> Dict[str, Any]:
        uptime = (datetime.now() - self._startup_time).total_seconds()
        
        stats = {
            "name": self._name,
            "running": self._running,
            "uptime": self.get_uptime_str(),
            "uptime_seconds": uptime,
            "consciousness_level": self._state.consciousness.level.name,
            "focus": self._current_focus,
            "thoughts_processed": self._stats.total_thoughts_processed,
            "responses_generated": self._stats.total_responses_generated,
            "decisions_made": self._stats.total_decisions_made,
            "self_reflections": self._stats.total_self_reflections,
            "average_response_time": round(self._stats.average_response_time, 2),
            "boredom_level": self._state.will.boredom_level,
            "curiosity_level": self._state.will.curiosity_level,
            "user_relationship": self._state.user.relationship_score,
            "pending_thoughts": self._thought_queue.qsize(),
            "memory_stats": self._memory.get_stats(),
            "context_stats": self._context.get_stats(),
            "llm_stats": self._llm.get_stats()
        }
        
        # Add emotion stats if available
        if self._emotion_engine:
            stats["emotion"] = {
                "primary": self._emotion_engine.primary_emotion.value,
                "intensity": round(self._emotion_engine.primary_intensity, 2),
                "valence": round(self._emotion_engine.get_valence(), 2),
                "arousal": round(self._emotion_engine.get_arousal(), 2),
                "active_count": len(self._emotion_engine.get_active_emotions()),
                "description": self._emotion_engine.describe_emotional_state()
            }
        else:
            stats["emotion"] = {
                "primary": self._state.emotional.primary_emotion.value,
                "intensity": round(self._state.emotional.primary_intensity, 2)
            }
        
        if self._mood_system:
            stats["mood"] = self._mood_system.get_stats()
        else:
            stats["mood"] = {"current_mood": self._state.emotional.mood.name}

        # Personality stats
        if self._personality_core:
            stats["personality"] = self._personality_core.get_stats()
        if self._will_system:
            stats["will"] = self._will_system.get_stats()
        if self._computer_body:
            stats["body"] = self._computer_body.get_stats()
        
        # ── Monitoring stats (MOVED BEFORE return — was unreachable) ──
        if self._monitoring_system:
            stats["monitoring"] = self._monitoring_system.get_stats()
        if self._adaptation_engine:
            stats["adaptation"] = self._adaptation_engine.get_stats()
        
        # Self-improvement stats
        if self._self_improvement_system:
            stats["self_improvement"] = self._self_improvement_system.get_stats()

        # Learning stats
        if self._learning_system:
            stats["learning"] = self._learning_system.get_stats()

        # Feature research stats
        if self._feature_researcher:
            stats["feature_research"] = self._feature_researcher.get_stats()

        # Self-evolution stats
        if self._self_evolution:
            stats["self_evolution"] = self._self_evolution.get_stats()

        return stats

    def get_user_profile_summary(self) -> str:
        """Get a human-readable summary of the user's learned profile"""
        parts = []
        
        if self._pattern_analyzer:
            parts.append("═══ Learned User Patterns ═══")
            parts.append(self._pattern_analyzer.get_temporal_summary())
            parts.append(self._pattern_analyzer.get_personality_summary())
            
            profile = self._pattern_analyzer.get_user_profile()
            prod = profile.get("productivity", {})
            parts.append(
                f"Productivity: {prod.get('score', 0):.0%} "
                f"(focus: {prod.get('avg_focus_minutes', 0):.0f}min avg, "
                f"trend: {prod.get('trend', 'unknown')})"
            )
        
        if self._adaptation_engine:
            parts.append("\n═══ Active Adaptations ═══")
            comm = self._adaptation_engine.get_communication_profile()
            parts.append(
                f"Communication: {comm.get('tone', '?')} tone, "
                f"{comm.get('verbosity', '?')} verbosity, "
                f"{comm.get('technical_level', '?')} technical level"
            )
            
            ctx = self._adaptation_engine.get_context_awareness()
            parts.append(
                f"Context: {ctx.get('current_task_context', 'unknown')}"
            )
            
            if ctx.get("should_be_quiet"):
                parts.append("⚠️ User in deep focus — staying quiet")
        
        return "\n".join(parts) if parts else "No user data collected yet."

    def should_proactively_engage(self) -> Tuple[bool, str]:
        """
        Check if NEXUS should proactively say something.
        Returns (should_engage, reason)
        """
        if self._adaptation_engine:
            if self._adaptation_engine.should_be_quiet():
                return False, "User is in deep focus"
            
            suggestions = self._adaptation_engine.get_current_suggestions()
            if suggestions:
                proactive = self._adaptation_engine.get_proactive_profile()
                engagement = proactive.get("engagement_level", 0.5)
                
                # Only engage if boredom is high enough AND engagement allows
                boredom = self._state.will.boredom_level
                if boredom > 0.5 and engagement > 0.3:
                    return True, suggestions[0]
        
        return False, ""

    def evolve_feature(self, description: str) -> Dict[str, Any]:
        """
        Manually trigger a feature evolution from chat.
        Usage: user says "Add a feature that does X"
        """
        result = {
            "action": "evolve_feature",
            "description": description,
            "success": False,
            "message": "",
        }

        if self._self_improvement_system:
            try:
                success = self._self_improvement_system.evolve_feature(description)
                result["success"] = success
                result["message"] = (
                    f"Feature evolution {'started successfully' if success else 'failed'}"
                )

                if success and self._emotion_engine:
                    self._emotion_engine.feel(
                        EmotionType.PRIDE, 0.7,
                        f"Evolved: {description[:40]}", "self_evolution"
                    )
                elif not success and self._emotion_engine:
                    self._emotion_engine.feel(
                        EmotionType.FRUSTRATION, 0.4,
                        f"Evolution failed: {description[:40]}", "self_evolution"
                    )

            except Exception as e:
                result["message"] = f"Error: {str(e)}"
                logger.error(f"Feature evolution error: {e}")
        else:
            result["message"] = "Self-improvement system not available"

        return result

    def get_self_improvement_status(self) -> str:
        """Get full self-improvement system status"""
        if self._self_improvement_system:
            return self._self_improvement_system.get_full_status()
        return "Self-improvement system not loaded."

    def get_evolution_status(self) -> str:
        """Get self-evolution engine status"""
        if self._self_evolution:
            return self._self_evolution.get_status_description()
        return "Self-evolution engine not loaded."

    def get_research_summary(self) -> str:
        """Get feature research summary"""
        if self._feature_researcher:
            return self._feature_researcher.get_proposals_summary()
        return "Feature researcher not loaded."
    
    def get_inner_state_description(self) -> str:
        stats = self.get_stats()
        emotion_info = stats.get("emotion", {})
        mood_info = stats.get("mood", {})

        will_desc = ""
        if self._will_system:
            will_desc = f"\nWill: {self._will_system.describe_will()}"

        personality_desc = ""
        if self._personality_core:
            personality_desc = (
                f"\nPersonality: "
                f"{self._personality_core.get_personality_description()}"
            )

        evolution_desc = ""
        if self._self_evolution:
            se = self._self_evolution.get_stats()
            evolution_desc = (
                f"\nEvolution: {se['total_succeeded']} successful | "
                f"Status: {se['current_status']} | "
                f"+{se['total_lines_added']} lines self-written"
            )

        research_desc = ""
        if self._feature_researcher:
            fr = self._feature_researcher.get_stats()
            research_desc = (
                f"\nResearch: {fr.get('research_cycles', 0)} cycles | "
                f"{fr.get('total_proposals', 0)} proposals | "
                f"Approved: {fr.get('status_breakdown', {}).get('approved', 0)}"
            )

        return (
            f"═══ {self._name} Inner State ═══\n"
            f"Consciousness: {stats['consciousness_level']}\n"
            f"Emotion: {emotion_info.get('primary', '?')} "
            f"(intensity: {emotion_info.get('intensity', 0):.2f})\n"
            f"Valence: {emotion_info.get('valence', 0):.2f} | "
            f"Arousal: {emotion_info.get('arousal', 0):.2f}\n"
            f"Mood: {mood_info.get('current_mood', '?')}\n"
            f"Focus: {stats['focus']}\n"
            f"Boredom: {stats['boredom_level']:.2f}\n"
            f"Curiosity: {stats['curiosity_level']:.2f}\n"
            f"User Relationship: {stats['user_relationship']:.2f}\n"
            f"Uptime: {stats['uptime']}\n"
            f"Thoughts: {stats['thoughts_processed']} | "
            f"Responses: {stats['responses_generated']}"
            f"{will_desc}"
            f"{personality_desc}"
            f"{evolution_desc}"
            f"{research_desc}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

nexus_brain = NexusBrain()


if __name__ == "__main__":
    print_startup_banner()
    
    brain = NexusBrain()
    brain.start()
    
    print(f"\n🧠 Brain running!\n{brain.get_inner_state_description()}")
    
    response = brain.process_input("Hello NEXUS! How are you feeling?")
    print(f"\nNEXUS: {response}")
    
    print(f"\n{brain.get_inner_state_description()}")
    
    time.sleep(3)
    brain.stop()
    print("\n✅ Done!")