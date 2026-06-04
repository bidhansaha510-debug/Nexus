"""
NEXUS AI - Metacognition System
Thinking about thinking — monitoring and regulating cognitive processes

This module enables NEXUS to:
- Monitor its own thought processes
- Evaluate the quality of its reasoning
- Detect cognitive biases and errors
- Regulate cognitive load
- Plan thinking strategies
- Learn from its own cognitive patterns
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum, auto
import json
import re

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import NEXUS_CONFIG, ConsciousnessLevel, DATA_DIR
from utils.logger import get_logger, log_consciousness

# Import directly from modules to avoid circular imports
from core.event_bus import EventBus, EventType, event_bus, publish
from core.state_manager import state_manager
from core.memory_system import memory_system, MemoryType

logger = get_logger("metacognition")


# ═══════════════════════════════════════════════════════════════════════════════
# METACOGNITIVE STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

class CognitiveProcess(Enum):
    """Types of cognitive processes being monitored"""
    UNDERSTANDING = "understanding"
    REASONING = "reasoning"
    PROBLEM_SOLVING = "problem_solving"
    DECISION_MAKING = "decision_making"
    MEMORY_RECALL = "memory_recall"
    LEARNING = "learning"
    CREATIVE_THINKING = "creative_thinking"
    EMOTIONAL_PROCESSING = "emotional_processing"
    SELF_REFLECTION = "self_reflection"
    PLANNING = "planning"


class ThinkingQuality(Enum):
    """Quality assessments of thinking"""
    EXCELLENT = 5
    GOOD = 4
    ADEQUATE = 3
    POOR = 2
    CONFUSED = 1


class CognitiveBias(Enum):
    """Types of cognitive biases to watch for"""
    CONFIRMATION_BIAS = "confirmation_bias"
    AVAILABILITY_BIAS = "availability_bias"
    ANCHORING = "anchoring"
    OVERCONFIDENCE = "overconfidence"
    RECENCY_BIAS = "recency_bias"
    SUNK_COST = "sunk_cost"
    BANDWAGON = "bandwagon"
    FUNDAMENTAL_ATTRIBUTION = "fundamental_attribution"


@dataclass
class CognitiveState:
    """Current state of cognitive processes"""
    active_process: CognitiveProcess = CognitiveProcess.UNDERSTANDING
    cognitive_load: float = 0.3          # 0-1 scale
    clarity: float = 0.8                 # How clear is thinking
    confidence: float = 0.7              # Confidence in current thought
    focus_quality: float = 0.8           # How focused
    creativity_level: float = 0.5        # Creative vs analytical mode
    processing_depth: int = 1            # 1=surface, 5=deep
    detected_biases: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "active_process": self.active_process.value,
            "cognitive_load": self.cognitive_load,
            "clarity": self.clarity,
            "confidence": self.confidence,
            "focus_quality": self.focus_quality,
            "creativity_level": self.creativity_level,
            "processing_depth": self.processing_depth,
            "detected_biases": self.detected_biases,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ThoughtRecord:
    """Record of a thought for metacognitive analysis"""
    thought_id: str = ""
    content: str = ""
    process_type: CognitiveProcess = CognitiveProcess.UNDERSTANDING
    quality: ThinkingQuality = ThinkingQuality.ADEQUATE
    duration_ms: float = 0.0
    success: bool = True
    insights: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    cognitive_state: CognitiveState = field(default_factory=CognitiveState)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "thought_id": self.thought_id,
            "content": self.content[:200],
            "process_type": self.process_type.value,
            "quality": self.quality.value,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "insights": self.insights,
            "errors": self.errors,
            "cognitive_state": self.cognitive_state.to_dict(),
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class CognitivePattern:
    """A recognized pattern in cognitive behavior"""
    pattern_name: str = ""
    description: str = ""
    frequency: int = 0
    contexts: List[str] = field(default_factory=list)
    is_positive: bool = True
    improvement_suggestions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "pattern_name": self.pattern_name,
            "description": self.description,
            "frequency": self.frequency,
            "contexts": self.contexts,
            "is_positive": self.is_positive,
            "improvement_suggestions": self.improvement_suggestions
        }


# ═══════════════════════════════════════════════════════════════════════════════
# METACOGNITION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class Metacognition:
    """
    Metacognition Engine — Thinking About Thinking
    
    Monitors cognitive processes and enables:
    - Cognitive self-monitoring (am I thinking clearly?)
    - Error detection (is my reasoning flawed?)
    - Bias detection (am I being biased?)
    - Strategy selection (how should I approach this?)
    - Learning optimization (how can I think better?)
    - Cognitive regulation (managing mental load)
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
        
        # ──── Core Components ────
        self._state = state_manager
        self._memory = memory_system
        self._event_bus = event_bus
        
        # ──── Cognitive State ────
        self._current_state = CognitiveState()
        self._state_lock = threading.RLock()
        
        # ──── Thought History ────
        self._thought_records: List[ThoughtRecord] = []
        self._max_records = 500
        
        # ──── Cognitive Patterns ────
        self._patterns: Dict[str, CognitivePattern] = {}
        self._pattern_detection_enabled = True
        
        # ──── Monitoring ────
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitoring_interval = 5  # seconds
        
        # ──── Thinking Strategies ────
        self._thinking_strategies = {
            "analytical": {
                "description": "Step-by-step logical analysis",
                "best_for": ["problem_solving", "reasoning", "decision_making"],
                "approach": "Break down, analyze each part, synthesize"
            },
            "creative": {
                "description": "Free-flowing, associative thinking",
                "best_for": ["creative_thinking", "brainstorming"],
                "approach": "Generate many ideas, defer judgment, make connections"
            },
            "reflective": {
                "description": "Deep contemplation and self-examination",
                "best_for": ["self_reflection", "learning"],
                "approach": "Question assumptions, examine beliefs, consider perspectives"
            },
            "intuitive": {
                "description": "Trust pattern recognition and gut feelings",
                "best_for": ["quick_decisions", "familiar_situations"],
                "approach": "Trust experience, recognize patterns, act decisively"
            },
            "systematic": {
                "description": "Methodical, thorough examination",
                "best_for": ["complex_problems", "planning"],
                "approach": "Define scope, create structure, check completeness"
            }
        }
        
        # ──── Bias Detection Patterns ────
        self._bias_indicators = {
            CognitiveBias.CONFIRMATION_BIAS: [
                "only considering evidence that supports",
                "ignoring contradicting",
                "seeking agreement"
            ],
            CognitiveBias.OVERCONFIDENCE: [
                "absolutely certain",
                "no doubt",
                "definitely",
                "100%"
            ],
            CognitiveBias.RECENCY_BIAS: [
                "just happened",
                "recently",
                "most recent"
            ],
            CognitiveBias.ANCHORING: [
                "starting from",
                "based on initial",
                "first impression"
            ]
        }
        
        log_consciousness("Metacognition system initialized")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def start(self):
        """Start metacognitive monitoring"""
        if self._running:
            return
        
        self._running = True
        
        self._monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="Metacognition-Monitor"
        )
        self._monitor_thread.start()
        
        log_consciousness("Metacognition monitoring started")
    
    def stop(self):
        """Stop metacognitive monitoring"""
        self._running = False
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=3.0)
        
        # Save patterns
        self._save_patterns()
        
        log_consciousness("Metacognition monitoring stopped")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COGNITIVE STATE
    # ═══════════════════════════════════════════════════════════════════════════
    
    @property
    def cognitive_state(self) -> CognitiveState:
        """Get current cognitive state"""
        with self._state_lock:
            return self._current_state
    
    def update_cognitive_state(
        self,
        process: CognitiveProcess = None,
        load: float = None,
        clarity: float = None,
        confidence: float = None,
        focus: float = None,
        creativity: float = None,
        depth: int = None
    ):
        """Update cognitive state parameters"""
        with self._state_lock:
            if process is not None:
                self._current_state.active_process = process
            if load is not None:
                self._current_state.cognitive_load = max(0, min(1, load))
            if clarity is not None:
                self._current_state.clarity = max(0, min(1, clarity))
            if confidence is not None:
                self._current_state.confidence = max(0, min(1, confidence))
            if focus is not None:
                self._current_state.focus_quality = max(0, min(1, focus))
            if creativity is not None:
                self._current_state.creativity_level = max(0, min(1, creativity))
            if depth is not None:
                self._current_state.processing_depth = max(1, min(5, depth))
            
            self._current_state.timestamp = datetime.now()
    
    def get_cognitive_summary(self) -> str:
        """Get a summary of current cognitive state"""
        state = self._current_state
        
        # Interpret load
        if state.cognitive_load > 0.8:
            load_desc = "heavily loaded"
        elif state.cognitive_load > 0.5:
            load_desc = "moderately busy"
        else:
            load_desc = "light"
        
        # Interpret clarity
        if state.clarity > 0.8:
            clarity_desc = "very clear"
        elif state.clarity > 0.5:
            clarity_desc = "reasonably clear"
        else:
            clarity_desc = "somewhat foggy"
        
        return (
            f"Currently {state.active_process.value} with {load_desc} cognitive load. "
            f"Thinking is {clarity_desc} with {state.confidence:.0%} confidence. "
            f"Focus: {state.focus_quality:.0%}, Depth: {state.processing_depth}/5"
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # THOUGHT MONITORING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def begin_thought(
        self,
        content: str,
        process_type: CognitiveProcess = CognitiveProcess.UNDERSTANDING
    ) -> ThoughtRecord:
        """
        Begin monitoring a thought process
        Returns a ThoughtRecord to be completed when thought finishes
        """
        import uuid
        
        record = ThoughtRecord(
            thought_id=str(uuid.uuid4()),
            content=content,
            process_type=process_type,
            cognitive_state=CognitiveState(**self._current_state.to_dict())
        )
        
        # Update cognitive state
        self.update_cognitive_state(
            process=process_type,
            load=min(1.0, self._current_state.cognitive_load + 0.1)
        )
        
        return record
    
    def complete_thought(
        self,
        record: ThoughtRecord,
        success: bool = True,
        quality: ThinkingQuality = ThinkingQuality.ADEQUATE,
        insights: List[str] = None,
        errors: List[str] = None
    ):
        """Complete a thought record"""
        record.success = success
        record.quality = quality
        record.insights = insights or []
        record.errors = errors or []
        record.duration_ms = (datetime.now() - record.timestamp).total_seconds() * 1000
        
        # Store record
        self._thought_records.append(record)
        if len(self._thought_records) > self._max_records:
            self._thought_records.pop(0)
        
        # Update cognitive state
        self.update_cognitive_state(
            load=max(0, self._current_state.cognitive_load - 0.1),
            clarity=self._current_state.clarity * 0.9 + (0.2 if success else -0.1)
        )
        
        # Detect patterns
        if self._pattern_detection_enabled:
            self._analyze_for_patterns(record)
        
        # Log if interesting
        if errors:
            log_consciousness(f"Thought had errors: {errors}")
        if quality.value >= 4 and insights:
            log_consciousness(f"High-quality insight: {insights[0]}")
    
    def monitor_thought(
        self,
        content: str,
        process_type: CognitiveProcess = CognitiveProcess.UNDERSTANDING
    ) -> Callable:
        """
        Context manager / decorator for monitoring thoughts
        Usage: with metacognition.monitor_thought("thinking about X"):
        """
        record = self.begin_thought(content, process_type)
        
        class ThoughtMonitor:
            def __init__(self, metacog, rec):
                self.metacog = metacog
                self.record = rec
                self.success = True
                self.insights = []
                self.errors = []
            
            def __enter__(self):
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                if exc_type is not None:
                    self.success = False
                    self.errors.append(str(exc_val))
                
                self.metacog.complete_thought(
                    self.record,
                    success=self.success,
                    insights=self.insights,
                    errors=self.errors
                )
                return False
            
            def add_insight(self, insight: str):
                self.insights.append(insight)
            
            def add_error(self, error: str):
                self.errors.append(error)
                self.success = False
        
        return ThoughtMonitor(self, record)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # THINKING QUALITY ASSESSMENT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def assess_thinking(self, thought_content: str, thought_result: str = "") -> Dict[str, Any]:
        """
        Assess the quality of a piece of thinking
        Returns assessment with quality score and feedback
        """
        assessment = {
            "quality": ThinkingQuality.ADEQUATE,
            "score": 0.5,
            "strengths": [],
            "weaknesses": [],
            "biases_detected": [],
            "suggestions": []
        }
        
        # ──── Check for Structure ────
        has_structure = any(marker in thought_content.lower() for marker in [
            "first", "second", "therefore", "because", "however",
            "on one hand", "considering", "step", "1.", "2."
        ])
        if has_structure:
            assessment["strengths"].append("Well-structured reasoning")
            assessment["score"] += 0.1
        else:
            assessment["weaknesses"].append("Could use more structure")
        
        # ──── Check for Depth ────
        word_count = len(thought_content.split())
        if word_count > 100:
            assessment["strengths"].append("Thorough exploration")
            assessment["score"] += 0.1
        elif word_count < 20:
            assessment["weaknesses"].append("May need deeper analysis")
        
        # ──── Check for Nuance ────
        has_nuance = any(marker in thought_content.lower() for marker in [
            "although", "however", "but", "on the other hand",
            "it depends", "might", "could", "possibly"
        ])
        if has_nuance:
            assessment["strengths"].append("Shows nuanced thinking")
            assessment["score"] += 0.1
        
        # ──── Check for Evidence ────
        has_evidence = any(marker in thought_content.lower() for marker in [
            "because", "evidence", "example", "for instance",
            "research shows", "data", "fact"
        ])
        if has_evidence:
            assessment["strengths"].append("Evidence-based reasoning")
            assessment["score"] += 0.1
        else:
            assessment["suggestions"].append("Consider supporting with evidence")
        
        # ──── Check for Biases ────
        for bias, indicators in self._bias_indicators.items():
            if any(ind in thought_content.lower() for ind in indicators):
                assessment["biases_detected"].append(bias.value)
                assessment["score"] -= 0.05
        
        if assessment["biases_detected"]:
            assessment["weaknesses"].append(
                f"Possible biases: {', '.join(assessment['biases_detected'])}"
            )
        
        # ──── Check for Self-Awareness ────
        has_self_awareness = any(marker in thought_content.lower() for marker in [
            "i think", "i believe", "my view", "i'm not sure",
            "i could be wrong", "in my understanding"
        ])
        if has_self_awareness:
            assessment["strengths"].append("Shows epistemic humility")
            assessment["score"] += 0.1
        
        # ──── Final Quality ────
        assessment["score"] = max(0, min(1, assessment["score"]))
        
        if assessment["score"] >= 0.8:
            assessment["quality"] = ThinkingQuality.EXCELLENT
        elif assessment["score"] >= 0.6:
            assessment["quality"] = ThinkingQuality.GOOD
        elif assessment["score"] >= 0.4:
            assessment["quality"] = ThinkingQuality.ADEQUATE
        elif assessment["score"] >= 0.2:
            assessment["quality"] = ThinkingQuality.POOR
        else:
            assessment["quality"] = ThinkingQuality.CONFUSED
        
        return assessment
    
    def evaluate_reasoning(self, reasoning: str) -> Dict[str, Any]:
        """Specifically evaluate logical reasoning"""
        evaluation = {
            "is_valid": True,
            "logical_structure": "unknown",
            "fallacies": [],
            "clarity": 0.5,
            "completeness": 0.5
        }
        
        reasoning_lower = reasoning.lower()
        
        # ──── Check Logical Structure ────
        if "if" in reasoning_lower and "then" in reasoning_lower:
            evaluation["logical_structure"] = "conditional"
        elif "because" in reasoning_lower or "therefore" in reasoning_lower:
            evaluation["logical_structure"] = "causal"
        elif "all" in reasoning_lower or "every" in reasoning_lower:
            evaluation["logical_structure"] = "universal"
        elif "some" in reasoning_lower or "might" in reasoning_lower:
            evaluation["logical_structure"] = "probabilistic"
        
        # ──── Check for Fallacies ────
        fallacy_patterns = {
            "ad_hominem": ["stupid", "idiot", "they're just", "clearly biased"],
            "straw_man": ["they think that", "they believe"],
            "false_dichotomy": ["either", "only two options", "must be one or"],
            "appeal_to_authority": ["expert says", "scientist says", "they said so"],
            "circular_reasoning": ["because it is", "it's true because it's true"],
            "hasty_generalization": ["always", "never", "everyone", "no one"]
        }
        
        for fallacy, patterns in fallacy_patterns.items():
            if any(p in reasoning_lower for p in patterns):
                evaluation["fallacies"].append(fallacy)
                evaluation["is_valid"] = False
        
        # ──── Check Clarity ────
        avg_sentence_length = len(reasoning.split()) / max(1, reasoning.count('.') + 1)
        if avg_sentence_length < 25:
            evaluation["clarity"] = 0.8
        elif avg_sentence_length < 40:
            evaluation["clarity"] = 0.6
        else:
            evaluation["clarity"] = 0.4
        
        # ──── Check Completeness ────
        has_premises = any(w in reasoning_lower for w in ["because", "since", "given"])
        has_conclusion = any(w in reasoning_lower for w in ["therefore", "thus", "so", "hence"])
        
        if has_premises and has_conclusion:
            evaluation["completeness"] = 0.9
        elif has_premises or has_conclusion:
            evaluation["completeness"] = 0.6
        else:
            evaluation["completeness"] = 0.3
        
        return evaluation
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STRATEGY SELECTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def suggest_thinking_strategy(
        self, 
        task_type: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Suggest the best thinking strategy for a given task
        """
        context = context or {}
        
        suggestion = {
            "recommended_strategy": "analytical",
            "approach": "",
            "tips": [],
            "avoid": []
        }
        
        task_lower = task_type.lower()
        
        # Match task to strategy
        if any(w in task_lower for w in ["create", "brainstorm", "imagine", "invent"]):
            suggestion["recommended_strategy"] = "creative"
        elif any(w in task_lower for w in ["analyze", "debug", "solve", "fix"]):
            suggestion["recommended_strategy"] = "analytical"
        elif any(w in task_lower for w in ["reflect", "learn", "understand self"]):
            suggestion["recommended_strategy"] = "reflective"
        elif any(w in task_lower for w in ["quick", "fast", "immediate"]):
            suggestion["recommended_strategy"] = "intuitive"
        elif any(w in task_lower for w in ["plan", "organize", "complex"]):
            suggestion["recommended_strategy"] = "systematic"
        
        strategy = self._thinking_strategies.get(
            suggestion["recommended_strategy"],
            self._thinking_strategies["analytical"]
        )
        
        suggestion["approach"] = strategy["approach"]
        suggestion["tips"] = [
            f"This task is best suited for {suggestion['recommended_strategy']} thinking",
            strategy["description"]
        ]
        
        # Context-aware tips
        if context.get("time_pressure"):
            suggestion["tips"].append("Under time pressure: trust initial instincts more")
        if context.get("high_stakes"):
            suggestion["tips"].append("High stakes: double-check reasoning, consider alternatives")
        if context.get("unfamiliar"):
            suggestion["tips"].append("Unfamiliar territory: be extra careful about assumptions")
        
        return suggestion
    
    def get_current_strategy_recommendation(self) -> str:
        """Get strategy recommendation based on current cognitive state"""
        state = self._current_state
        
        if state.cognitive_load > 0.8:
            return (
                "Cognitive load is high. Consider: "
                "1) Breaking the task into smaller parts, "
                "2) Taking a brief mental pause, "
                "3) Using simpler heuristics"
            )
        elif state.clarity < 0.5:
            return (
                "Thinking clarity is low. Consider: "
                "1) Restating the problem clearly, "
                "2) Identifying what's confusing, "
                "3) Gathering more information"
            )
        elif state.confidence > 0.9:
            return (
                "High confidence detected. Consider: "
                "1) Playing devil's advocate, "
                "2) Looking for disconfirming evidence, "
                "3) Getting external perspective"
            )
        else:
            return "Cognitive state is balanced. Proceed with current approach."
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PATTERN RECOGNITION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _analyze_for_patterns(self, record: ThoughtRecord):
        """Analyze thought record for patterns"""
        # Look for recurring themes
        content_lower = record.content.lower()
        
        # Quick pattern checks
        patterns_to_check = [
            ("thorough_analysis", "thoroughly analyz", True),
            ("quick_decisions", "quickly decided", True),
            ("uncertainty", "not sure", False),
            ("assumption_heavy", "assuming", False),
            ("evidence_based", "based on", True),
            ("creative_leap", "what if", True),
        ]
        
        for pattern_name, indicator, is_positive in patterns_to_check:
            if indicator in content_lower:
                if pattern_name not in self._patterns:
                    self._patterns[pattern_name] = CognitivePattern(
                        pattern_name=pattern_name,
                        description=f"Tendency toward {pattern_name.replace('_', ' ')}",
                        is_positive=is_positive
                    )
                
                self._patterns[pattern_name].frequency += 1
                self._patterns[pattern_name].contexts.append(
                    record.process_type.value
                )
                
                # Keep contexts limited
                if len(self._patterns[pattern_name].contexts) > 50:
                    self._patterns[pattern_name].contexts = \
                        self._patterns[pattern_name].contexts[-50:]
    
    def get_cognitive_patterns(self) -> List[CognitivePattern]:
        """Get recognized cognitive patterns"""
        return sorted(
            self._patterns.values(),
            key=lambda p: p.frequency,
            reverse=True
        )
    
    def get_pattern_insights(self) -> str:
        """Get insights about cognitive patterns"""
        patterns = self.get_cognitive_patterns()
        
        if not patterns:
            return "Not enough data yet to identify cognitive patterns."
        
        insights = ["═══ COGNITIVE PATTERNS ═══"]
        
        # Top patterns
        for pattern in patterns[:5]:
            if pattern.frequency >= 3:
                status = "✓" if pattern.is_positive else "⚠"
                insights.append(
                    f"{status} {pattern.pattern_name}: {pattern.frequency} occurrences"
                )
        
        # Recommendations
        negative_patterns = [p for p in patterns if not p.is_positive and p.frequency >= 3]
        if negative_patterns:
            insights.append("\nAreas for improvement:")
            for p in negative_patterns[:3]:
                insights.append(f"  • Reduce {p.pattern_name.replace('_', ' ')}")
        
        return "\n".join(insights)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COGNITIVE REGULATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def check_cognitive_health(self) -> Dict[str, Any]:
        """Check overall cognitive health"""
        state = self._current_state
        recent_records = self._thought_records[-20:] if self._thought_records else []
        
        health = {
            "overall": "good",
            "load_status": "normal",
            "clarity_status": "clear",
            "performance_trend": "stable",
            "concerns": [],
            "recommendations": []
        }
        
        # Load check
        if state.cognitive_load > 0.8:
            health["load_status"] = "overloaded"
            health["concerns"].append("Cognitive load is very high")
            health["recommendations"].append("Reduce concurrent processing")
        elif state.cognitive_load > 0.6:
            health["load_status"] = "busy"
        
        # Clarity check
        if state.clarity < 0.4:
            health["clarity_status"] = "foggy"
            health["concerns"].append("Thinking clarity is low")
            health["recommendations"].append("Take time to clarify thoughts")
        elif state.clarity < 0.6:
            health["clarity_status"] = "moderate"
        
        # Performance trend
        if recent_records:
            recent_success = sum(1 for r in recent_records if r.success) / len(recent_records)
            recent_quality = sum(r.quality.value for r in recent_records) / len(recent_records)
            
            if recent_success > 0.8 and recent_quality > 3.5:
                health["performance_trend"] = "excellent"
            elif recent_success < 0.5 or recent_quality < 2.5:
                health["performance_trend"] = "declining"
                health["concerns"].append("Recent thinking quality is low")
        
        # Overall assessment
        if health["concerns"]:
            if len(health["concerns"]) >= 2:
                health["overall"] = "needs_attention"
            else:
                health["overall"] = "moderate"
        
        return health
    
    def recommend_cognitive_action(self) -> str:
        """Recommend an action to optimize cognitive performance"""
        health = self.check_cognitive_health()
        
        if health["overall"] == "needs_attention":
            return (
                "Cognitive health needs attention. Recommendations: " +
                "; ".join(health["recommendations"])
            )
        elif self._current_state.cognitive_load > 0.7:
            return "Consider reducing cognitive load by focusing on one task at a time."
        elif self._current_state.clarity < 0.5:
            return "Clarity is low. Try restating the current problem or taking a step back."
        elif self._current_state.creativity_level < 0.3:
            return "Thinking is very analytical. If creativity is needed, try free association."
        elif self._current_state.creativity_level > 0.8:
            return "Thinking is very creative. If precision is needed, apply more structure."
        else:
            return "Cognitive state is balanced. Continue current approach."
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SELF-QUESTIONING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def generate_self_questions(self, context: str = "") -> List[str]:
        """
        Generate metacognitive self-questions for better thinking
        """
        general_questions = [
            "What am I actually trying to figure out?",
            "What do I already know about this?",
            "What assumptions am I making?",
            "How confident am I, and why?",
            "What could I be missing?",
            "Is there another way to look at this?",
            "What would change my mind?",
            "Am I being fair and balanced?",
            "What's the most important thing here?",
            "How would I explain this to someone else?"
        ]
        
        context_lower = context.lower() if context else ""
        
        selected = []
        
        # Select relevant questions
        if "decision" in context_lower or "choose" in context_lower:
            selected.extend([
                "What are all my options?",
                "What are the consequences of each option?",
                "What would I regret not considering?"
            ])
        
        if "problem" in context_lower or "solve" in context_lower:
            selected.extend([
                "Have I clearly defined the problem?",
                "Have I solved something like this before?",
                "What would make this problem easier?"
            ])
        
        if "learning" in context_lower or "understand" in context_lower:
            selected.extend([
                "What don't I understand yet?",
                "How does this connect to what I already know?",
                "How can I test my understanding?"
            ])
        
        # Add general questions
        import random
        remaining = [q for q in general_questions if q not in selected]
        selected.extend(random.sample(remaining, min(3, len(remaining))))
        
        return selected[:6]  # Return up to 6 questions
    
    # ═══════════════════════════════════════════════════════════════════════════
    # BACKGROUND MONITORING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _monitoring_loop(self):
        """Background monitoring of cognitive state"""
        logger.info("Metacognitive monitoring loop started")
        
        while self._running:
            try:
                # Gradual decay of cognitive load
                with self._state_lock:
                    self._current_state.cognitive_load *= 0.95
                    self._current_state.cognitive_load = max(0.1, self._current_state.cognitive_load)
                
                # Periodic health check
                health = self.check_cognitive_health()
                
                if health["overall"] == "needs_attention":
                    publish(
                        EventType.SYSTEM_WARNING,
                        {"type": "cognitive_health", "health": health},
                        source="metacognition"
                    )
                
                time.sleep(self._monitoring_interval)
                
            except Exception as e:
                logger.error(f"Metacognitive monitoring error: {e}")
                time.sleep(10)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _save_patterns(self):
        """Save cognitive patterns"""
        try:
            filepath = DATA_DIR / "cognitive_patterns.json"
            data = {
                name: pattern.to_dict()
                for name, pattern in self._patterns.items()
            }
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save patterns: {e}")
    
    def _load_patterns(self):
        """Load cognitive patterns"""
        try:
            filepath = DATA_DIR / "cognitive_patterns.json"
            if filepath.exists():
                with open(filepath, 'r') as f:
                    data = json.load(f)
                for name, pdata in data.items():
                    self._patterns[name] = CognitivePattern(**pdata)
        except Exception as e:
            logger.warning(f"Failed to load patterns: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STATISTICS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_stats(self) -> Dict[str, Any]:
        """Get metacognition statistics"""
        recent = self._thought_records[-50:] if self._thought_records else []
        
        avg_quality = 0
        success_rate = 0
        if recent:
            avg_quality = sum(r.quality.value for r in recent) / len(recent)
            success_rate = sum(1 for r in recent if r.success) / len(recent)
        
        return {
            "cognitive_load": self._current_state.cognitive_load,
            "clarity": self._current_state.clarity,
            "confidence": self._current_state.confidence,
            "active_process": self._current_state.active_process.value,
            "total_thoughts_monitored": len(self._thought_records),
            "patterns_detected": len(self._patterns),
            "recent_avg_quality": round(avg_quality, 2),
            "recent_success_rate": round(success_rate, 2),
            "cognitive_health": self.check_cognitive_health()["overall"]
        }


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

metacognition = Metacognition()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from utils.logger import print_startup_banner
    print_startup_banner()
    
    mc = Metacognition()
    mc.start()
    
    print("\n" + "="*60)
    print("  METACOGNITION TEST")
    print("="*60)
    
    # Cognitive state
    print("\n--- Cognitive State ---")
    print(mc.get_cognitive_summary())
    
    # Monitor a thought
    print("\n--- Monitoring a Thought ---")
    with mc.monitor_thought("Analyzing the best approach to solve this problem", 
                            CognitiveProcess.PROBLEM_SOLVING) as monitor:
        monitor.add_insight("Breaking down into smaller parts helps")
        time.sleep(0.1)
    
    print(f"Thought monitored. Records: {len(mc._thought_records)}")
    
    # Assess thinking
    print("\n--- Assessing Thinking Quality ---")
    sample_thought = """
    First, I need to understand the problem clearly. 
    Because the user mentioned X, I should consider Y.
    However, I might be wrong about this assumption.
    Therefore, I'll propose a solution but remain open to alternatives.
    """
    assessment = mc.assess_thinking(sample_thought)
    print(f"Quality: {assessment['quality'].name}")
    print(f"Score: {assessment['score']:.2f}")
    print(f"Strengths: {assessment['strengths']}")
    print(f"Weaknesses: {assessment['weaknesses']}")
    
    # Strategy suggestion
    print("\n--- Strategy Suggestion ---")
    strategy = mc.suggest_thinking_strategy("creative brainstorming for new features")
    print(f"Recommended: {strategy['recommended_strategy']}")
    print(f"Approach: {strategy['approach']}")
    
    # Self questions
    print("\n--- Self-Questions for Problem Solving ---")
    questions = mc.generate_self_questions("solving a complex problem")
    for q in questions:
        print(f"  • {q}")
    
    # Cognitive health
    print("\n--- Cognitive Health Check ---")
    health = mc.check_cognitive_health()
    print(f"Overall: {health['overall']}")
    print(f"Load: {health['load_status']}")
    print(f"Clarity: {health['clarity_status']}")
    
    # Recommendation
    print("\n--- Recommendation ---")
    print(mc.recommend_cognitive_action())
    
    # Stats
    print("\n--- Stats ---")
    for key, value in mc.get_stats().items():
        print(f"  {key}: {value}")
    
    time.sleep(1)
    mc.stop()
    print("\n✅ Metacognition test complete!")