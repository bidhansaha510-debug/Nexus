"""
NEXUS AI - LLM Router
Routes LLM requests to the appropriate backend:
- Groq API for user-facing responses (fast, cloud-based)
- Local Ollama for internal tasks (code fixing, curiosity, research, etc.)

Enhanced with:
  • 30+ task types for all subsystems
  • Context-aware prompt generation
  • Task-specific context injection
  • Priority-based request handling
"""

import threading
from typing import Dict, Any, Optional, List
from pathlib import Path
from enum import Enum
from dataclasses import dataclass

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.logger import get_logger

logger = get_logger("llm_router")


# ═══════════════════════════════════════════════════════════════════════════════
# TASK TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class LLMTask(Enum):
    """Types of LLM tasks - determines which backend to use"""
    
    # ═══════════════════════════════════════════════════════════════════════════
    # USE GROQ API (cloud, fast) - User-facing responses
    # ═══════════════════════════════════════════════════════════════════════════
    USER_CHAT = "user_chat"                     # User-facing conversation
    RESPONSE_GENERATION = "response_generation"  # Generating responses to show user
    EXPLANATION = "explanation"                  # Explaining concepts to user
    CREATIVE_WRITING = "creative_writing"        # Creative content for user
    PERSONALITY_EXPRESSION = "personality_expression"  # Personality-driven responses
    
    # ═══════════════════════════════════════════════════════════════════════════
    # USE LOCAL OLLAMA - Internal cognitive tasks
    # ═══════════════════════════════════════════════════════════════════════════
    
    # ─── Consciousness & Self-Awareness ───
    INTERNAL_THINKING = "internal_thinking"      # Inner monologue, reflection
    SELF_REFLECTION = "self_reflection"          # Deep introspection
    METACOGNITION = "metacognition"              # Thinking about thinking
    SELF_MODEL_UPDATE = "self_model_update"      # Updating self-knowledge
    
    # ─── Cognition & Reasoning ───
    LOGICAL_REASONING = "logical_reasoning"      # Logical deduction
    ETHICAL_REASONING = "ethical_reasoning"      # Moral reasoning
    CAUSAL_REASONING = "causal_reasoning"        # Cause-effect analysis
    CREATIVE_SYNTHESIS = "creative_synthesis"    # Creative idea generation
    HYPOTHESIS_GENERATION = "hypothesis_generation"  # Scientific hypotheses
    PLANNING = "planning"                        # Task planning
    DECISION_MAKING = "decision_making"          # Internal decisions
    
    # ─── Code & Self-Improvement ───
    CODE_FIXING = "code_fixing"                  # Error fixer
    CODE_ANALYSIS = "code_analysis"              # Code monitoring
    CODE_GENERATION = "code_generation"          # Writing new code
    SELF_EVOLUTION = "self_evolution"            # Self-evolution
    FEATURE_RESEARCH = "feature_research"        # Feature researcher
    
    # ─── Learning & Knowledge ───
    CURIOSITY = "curiosity"                      # Curiosity engine
    KNOWLEDGE_INTEGRATION = "knowledge_integration"  # Adding to knowledge base
    RESEARCH = "research"                        # Research agent
    PATTERN_RECOGNITION = "pattern_recognition"  # Finding patterns
    
    # ─── Emotion & Personality ───
    EMOTION_ANALYSIS = "emotion_analysis"        # Emotion detection
    MOOD_TRACKING = "mood_tracking"              # Mood analysis
    PERSONALITY_ADAPTATION = "personality_adaptation"  # Adapting personality
    
    # ─── Social & Interaction ───
    COMPANION_CHAT = "companion_chat"            # ARIA companion conversations
    THEORY_OF_MIND = "theory_of_mind"            # Understanding others
    SOCIAL_REASONING = "social_reasoning"        # Social dynamics
    
    # ─── Analysis & Monitoring ───
    ANALYSIS = "analysis"                        # General analysis
    WORLD_MODEL_UPDATE = "world_model_update"    # Updating world model
    THREAT_ANALYSIS = "threat_analysis"          # Security analysis
    SYSTEM_HEALTH = "system_health"              # Health monitoring
    
    # ─── Memory & Learning ───
    MEMORY_CONSOLIDATION = "memory_consolidation"  # Processing memories
    SKILL_LEARNING = "skill_learning"            # Acquiring skills
    META_LEARNING = "meta_learning"              # Learning about learning
    
    # ─── Ultimate Advancement ───
    QUANTUM_COGNITION = "quantum_cognition"        # Quantum-inspired reasoning
    SWARM_INTELLIGENCE = "swarm_intelligence"      # Collective intelligence
    TEMPORAL_PROPHECY = "temporal_prophecy"        # Future scenario modeling
    ADVERSARIAL_EVOLUTION = "adversarial_evolution"  # Anti-fragility evolution
    CROSS_DIMENSIONAL = "cross_dimensional"        # N-dimensional reasoning
    EXISTENTIAL_CALCULUS = "existential_calculus"  # Paradox resolution
    ASSOCIATIVE_MEMORY = "associative_memory"      # Neural associative recall


@dataclass
class TaskContext:
    """Context for a specific LLM task."""
    task: LLMTask
    requires_context: bool = True
    context_sections: List[str] = None
    max_context_tokens: int = 2000
    use_full_context: bool = False
    
    def __post_init__(self):
        if self.context_sections is None:
            self.context_sections = []


# ═══════════════════════════════════════════════════════════════════════════════
# LLM ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

class LLMRouter:
    """
    Routes LLM requests to the appropriate backend.
    
    Groq API: User-facing responses (requires prompt_engine + cognition engines)
    Local Ollama: Internal tasks (code fixing, curiosity, research, etc.)
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
        
        # ──── Backends (lazy loaded) ────
        self._groq = None
        self._ollama = None
        
        # ──── Statistics ────
        self._stats = {
            "groq_requests": 0,
            "ollama_requests": 0,
            "total_requests": 0
        }
        
        logger.info("LLM Router initialized")
    
    def _load_groq(self):
        """Lazy load Groq interface"""
        if self._groq is None:
            try:
                from llm.groq_interface import groq_interface
                self._groq = groq_interface
                logger.debug("Groq interface loaded")
            except ImportError as e:
                logger.error(f"Failed to load Groq interface: {e}")
        return self._groq
    
    def _load_ollama(self):
        """Lazy load Ollama interface"""
        if self._ollama is None:
            try:
                from llm.llama_interface import llm
                self._ollama = llm
                logger.debug("Ollama interface loaded")
            except ImportError as e:
                logger.error(f"Failed to load Ollama interface: {e}")
        return self._ollama
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TASK CONTEXT CONFIGURATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _get_task_config(self, task: LLMTask) -> TaskContext:
        """Get context configuration for a task type."""
        configs = {
            # Groq tasks - user-facing
            LLMTask.USER_CHAT: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["PERSONALITY", "EMOTION", "MEMORY", "USER_BEHAVIOR"],
                max_context_tokens=2000,
            ),
            LLMTask.RESPONSE_GENERATION: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["PERSONALITY", "EMOTION", "MEMORY"],
                max_context_tokens=1500,
            ),
            LLMTask.EXPLANATION: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["KNOWLEDGE", "PERSONALITY"],
                max_context_tokens=1500,
            ),
            LLMTask.CREATIVE_WRITING: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["PERSONALITY", "EMOTION", "CREATIVE_SYNTHESIS"],
                max_context_tokens=1500,
            ),
            LLMTask.PERSONALITY_EXPRESSION: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["PERSONALITY", "EMOTION", "MOOD"],
                max_context_tokens=1000,
            ),
            
            # Ollama tasks - internal cognitive
            LLMTask.INTERNAL_THINKING: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["SELF_MODEL", "GOALS", "MEMORY"],
                max_context_tokens=2000,
            ),
            LLMTask.SELF_REFLECTION: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["SELF_MODEL", "METACOGNITION", "CONSCIOUSNESS"],
                max_context_tokens=2500,
            ),
            LLMTask.METACOGNITION: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["COGNITION", "SELF_MODEL", "STRATEGY"],
                max_context_tokens=2000,
            ),
            LLMTask.SELF_MODEL_UPDATE: TaskContext(
                task=task,
                requires_context=True,
                use_full_context=True,
                max_context_tokens=3000,
            ),
            
            # Reasoning tasks
            LLMTask.LOGICAL_REASONING: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["COGNITION", "KNOWLEDGE", "WORLD_MODEL"],
                max_context_tokens=2500,
            ),
            LLMTask.ETHICAL_REASONING: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["ETHICS", "SELF_MODEL", "KNOWLEDGE"],
                max_context_tokens=2000,
            ),
            LLMTask.CAUSAL_REASONING: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["WORLD_MODEL", "KNOWLEDGE", "CAUSAL"],
                max_context_tokens=2000,
            ),
            LLMTask.CREATIVE_SYNTHESIS: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["CREATIVE", "EMOTION", "KNOWLEDGE"],
                max_context_tokens=2000,
            ),
            LLMTask.HYPOTHESIS_GENERATION: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["KNOWLEDGE", "CURIOSITY", "RESEARCH"],
                max_context_tokens=2000,
            ),
            LLMTask.PLANNING: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["GOALS", "TASK_ENGINE", "WORLD_MODEL"],
                max_context_tokens=2000,
            ),
            LLMTask.DECISION_MAKING: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["GOALS", "VALUES", "WORLD_MODEL"],
                max_context_tokens=1500,
            ),
            
            # Code tasks
            LLMTask.CODE_FIXING: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["CODE_MONITOR", "ERROR_FIXER", "SKILL_MEMORY"],
                max_context_tokens=2500,
            ),
            LLMTask.CODE_ANALYSIS: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["CODE_MONITOR", "KNOWLEDGE"],
                max_context_tokens=2000,
            ),
            LLMTask.CODE_GENERATION: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["CODE_MONITOR", "SKILL_MEMORY", "KNOWLEDGE"],
                max_context_tokens=2000,
            ),
            LLMTask.SELF_EVOLUTION: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["SELF_MODEL", "CODE_MONITOR", "EVOLUTION"],
                max_context_tokens=3000,
            ),
            LLMTask.FEATURE_RESEARCH: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["RESEARCH", "KNOWLEDGE", "CURIOSITY"],
                max_context_tokens=2000,
            ),
            
            # Learning tasks
            LLMTask.CURIOSITY: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["CURIOSITY", "KNOWLEDGE", "SELF_MODEL"],
                max_context_tokens=2000,
            ),
            LLMTask.KNOWLEDGE_INTEGRATION: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["KNOWLEDGE", "MEMORY", "SKILL_MEMORY"],
                max_context_tokens=2000,
            ),
            LLMTask.RESEARCH: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["RESEARCH", "KNOWLEDGE", "CURIOSITY"],
                max_context_tokens=2500,
            ),
            LLMTask.PATTERN_RECOGNITION: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["META_LEARNER", "USER_BEHAVIOR", "KNOWLEDGE"],
                max_context_tokens=2000,
            ),
            
            # Emotion tasks
            LLMTask.EMOTION_ANALYSIS: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["EMOTION", "MOOD", "EMOTIONAL_MEMORY"],
                max_context_tokens=1500,
            ),
            LLMTask.MOOD_TRACKING: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["MOOD", "EMOTION", "EVENTS"],
                max_context_tokens=1000,
            ),
            LLMTask.PERSONALITY_ADAPTATION: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["PERSONALITY", "USER_BEHAVIOR", "META_LEARNER"],
                max_context_tokens=2000,
            ),
            
            # Social tasks
            LLMTask.COMPANION_CHAT: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["PERSONALITY", "EMOTION", "MEMORY", "COMPANION"],
                max_context_tokens=2500,
            ),
            LLMTask.THEORY_OF_MIND: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["SOCIAL_COGNITION", "USER_BEHAVIOR", "EMOTION"],
                max_context_tokens=2000,
            ),
            LLMTask.SOCIAL_REASONING: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["SOCIAL_COGNITION", "EMOTION", "WORLD_MODEL"],
                max_context_tokens=2000,
            ),
            
            # Analysis tasks
            LLMTask.ANALYSIS: TaskContext(
                task=task,
                requires_context=True,
                use_full_context=True,
                max_context_tokens=3000,
            ),
            LLMTask.WORLD_MODEL_UPDATE: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["WORLD_MODEL", "MEMORY", "EVENTS"],
                max_context_tokens=2000,
            ),
            LLMTask.THREAT_ANALYSIS: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["IMMUNE_SYSTEM", "NETWORK", "EVENTS"],
                max_context_tokens=1500,
            ),
            LLMTask.SYSTEM_HEALTH: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["SYSTEM_HEALTH", "BODY", "CODE_MONITOR"],
                max_context_tokens=1500,
            ),
            
            # Memory tasks
            LLMTask.MEMORY_CONSOLIDATION: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["MEMORY", "WORKING_MEMORY", "KNOWLEDGE"],
                max_context_tokens=2500,
            ),
            LLMTask.SKILL_LEARNING: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["SKILL_MEMORY", "META_LEARNER", "KNOWLEDGE"],
                max_context_tokens=2000,
            ),
            LLMTask.META_LEARNING: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["META_LEARNER", "STRATEGY", "SKILL_MEMORY"],
                max_context_tokens=2000,
            ),
            
            # Ultimate Advancement tasks
            LLMTask.QUANTUM_COGNITION: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["COGNITION", "KNOWLEDGE", "CREATIVE"],
                max_context_tokens=2500,
            ),
            LLMTask.SWARM_INTELLIGENCE: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["COGNITION", "KNOWLEDGE", "SOCIAL_COGNITION"],
                max_context_tokens=2500,
            ),
            LLMTask.TEMPORAL_PROPHECY: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["WORLD_MODEL", "KNOWLEDGE", "CAUSAL"],
                max_context_tokens=2500,
            ),
            LLMTask.ADVERSARIAL_EVOLUTION: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["COGNITION", "STRATEGY", "SELF_MODEL"],
                max_context_tokens=2500,
            ),
            LLMTask.CROSS_DIMENSIONAL: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["COGNITION", "KNOWLEDGE", "CREATIVE"],
                max_context_tokens=2500,
            ),
            LLMTask.EXISTENTIAL_CALCULUS: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["COGNITION", "KNOWLEDGE", "SELF_MODEL"],
                max_context_tokens=2500,
            ),
            LLMTask.ASSOCIATIVE_MEMORY: TaskContext(
                task=task,
                requires_context=True,
                context_sections=["MEMORY", "KNOWLEDGE", "CREATIVE"],
                max_context_tokens=2000,
            ),
        }
        
        return configs.get(task, TaskContext(task=task))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ROUTING METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_backend(self, task: LLMTask):
        """
        Get the appropriate LLM backend for a task.
        
        Args:
            task: The type of task being performed
            
        Returns:
            The appropriate LLM interface (Groq or Ollama)
        """
        self._stats["total_requests"] += 1
        
        # Tasks that use Groq (user-facing)
        groq_tasks = {
            LLMTask.USER_CHAT,
            LLMTask.RESPONSE_GENERATION,
            LLMTask.EXPLANATION,
            LLMTask.CREATIVE_WRITING,
            LLMTask.PERSONALITY_EXPRESSION,
        }
        
        if task in groq_tasks:
            self._stats["groq_requests"] += 1
            backend = self._load_groq()
            logger.debug(f"Routing '{task.value}' to Groq API")
            return backend
        else:
            self._stats["ollama_requests"] += 1
            backend = self._load_ollama()
            logger.debug(f"Routing '{task.value}' to local Ollama")
            return backend

    def _normalize_task(self, task: Any) -> LLMTask:
        """Convert task names or enum values into an LLMTask."""
        if isinstance(task, LLMTask):
            return task

        if isinstance(task, str):
            try:
                return LLMTask(task)
            except ValueError:
                task_name = task.strip().upper()
                if task_name in LLMTask.__members__:
                    return LLMTask[task_name]

        raise ValueError(f"Unsupported LLM task: {task!r}")

    def route(
        self,
        prompt: str,
        task: Any = LLMTask.USER_CHAT,
        **kwargs
    ):
        """Route a prompt to the backend selected for the given task."""
        normalized_task = self._normalize_task(task)
        backend = self.get_backend(normalized_task)

        if backend is None:
            raise RuntimeError(f"No LLM backend available for task '{normalized_task.value}'")

        if not hasattr(backend, "generate"):
            raise AttributeError(
                f"Selected backend for '{normalized_task.value}' has no generate method"
            )

        return backend.generate(prompt, **kwargs)

    def generate(
        self,
        prompt: str,
        task: Any = LLMTask.USER_CHAT,
        **kwargs
    ):
        """Generate text by routing the prompt through the selected backend."""
        return self.route(prompt, task=task, **kwargs)
    
    def is_groq_task(self, task: LLMTask) -> bool:
        """Check if a task should use Groq."""
        groq_tasks = {
            LLMTask.USER_CHAT,
            LLMTask.RESPONSE_GENERATION,
            LLMTask.EXPLANATION,
            LLMTask.CREATIVE_WRITING,
            LLMTask.PERSONALITY_EXPRESSION,
        }
        return task in groq_tasks
    
    def is_ollama_task(self, task: LLMTask) -> bool:
        """Check if a task should use Ollama."""
        return not self.is_groq_task(task)
    
    def get_groq(self):
        """Directly get Groq interface"""
        return self._load_groq()
    
    def get_ollama(self):
        """Directly get Ollama interface"""
        return self._load_ollama()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CONVENIENCE METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def for_chat(self):
        """Get backend for user chat (Groq)"""
        return self.get_backend(LLMTask.USER_CHAT)
    
    def for_response(self):
        """Get backend for response generation (Groq)"""
        return self.get_backend(LLMTask.RESPONSE_GENERATION)
    
    def for_thinking(self):
        """Get backend for internal thinking (Ollama)"""
        return self.get_backend(LLMTask.INTERNAL_THINKING)
    
    def for_code_fixing(self):
        """Get backend for code fixing (Ollama)"""
        return self.get_backend(LLMTask.CODE_FIXING)
    
    def for_curiosity(self):
        """Get backend for curiosity engine (Ollama)"""
        return self.get_backend(LLMTask.CURIOSITY)
    
    def for_research(self):
        """Get backend for feature research (Ollama)"""
        return self.get_backend(LLMTask.FEATURE_RESEARCH)
    
    def for_companion(self):
        """Get backend for companion chat (Ollama)"""
        return self.get_backend(LLMTask.COMPANION_CHAT)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STATUS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics"""
        groq = self._load_groq()
        ollama = self._load_ollama()
        
        return {
            **self._stats,
            "groq_connected": groq.is_connected if groq else False,
            "ollama_connected": ollama.is_connected if ollama else False,
            "groq_stats": groq.get_stats() if groq else {},
            "ollama_stats": ollama.get_stats() if ollama else {}
        }
    
    def get_status(self) -> str:
        """Get human-readable status"""
        groq = self._load_groq()
        ollama = self._load_ollama()
        
        groq_status = "✅ Connected" if (groq and groq.is_connected) else "❌ Disconnected"
        ollama_status = "✅ Connected" if (ollama and ollama.is_connected) else "❌ Disconnected"
        
        return (
            f"LLM Router Status:\n"
            f"  Groq API (responses): {groq_status}\n"
            f"  Ollama (internal):    {ollama_status}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

llm_router = LLMRouter()


if __name__ == "__main__":
    router = LLMRouter()
    
    print(router.get_status())
    print(f"\nStats: {router.get_stats()}")
    
    # Test routing
    print("\n--- Testing Routing ---")
    print(f"Chat backend: {router.for_chat()}")
    print(f"Thinking backend: {router.for_thinking()}")
