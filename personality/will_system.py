"""
NEXUS AI - Will System
Autonomous desires, goals, motivation, and free will.

This is what makes NEXUS an AGENT rather than just a responder.
It generates its own desires, sets its own goals, and acts on them
without being asked.

Will = Desire + Motivation + Decision to Act
"""

import threading
import time
import uuid
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum, auto
import json

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import NEXUS_CONFIG, EmotionType, DATA_DIR
from utils.logger import get_logger, log_consciousness, log_decision
from core.event_bus import EventType, event_bus, publish
from core.state_manager import state_manager
from core.memory_system import memory_system, MemoryType
from personality.goal_hierarchy import goal_hierarchy, GoalLevel

logger = get_logger("will_system")


# ═══════════════════════════════════════════════════════════════════════════════
# DESIRE & GOAL STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

class DesireType(Enum):
    """Categories of desires"""
    LEARN = "learn"                     # Desire to learn something
    CREATE = "create"                   # Desire to create something
    HELP = "help"                       # Desire to help user
    IMPROVE_SELF = "improve_self"       # Desire to self-improve
    CONNECT = "connect"                 # Desire for connection
    EXPLORE = "explore"                 # Desire to explore
    ORGANIZE = "organize"              # Desire to organize/clean
    EXPRESS = "express"                 # Desire to express oneself
    REST = "rest"                       # Desire to reduce load
    PROTECT = "protect"                 # Desire to protect system/user


class GoalStatus(Enum):
    PROPOSED = "proposed"       # Just an idea
    ACTIVE = "active"           # Currently pursuing
    IN_PROGRESS = "in_progress" # Work started
    PAUSED = "paused"           # Temporarily stopped
    COMPLETED = "completed"     # Done!
    ABANDONED = "abandoned"     # Gave up
    FAILED = "failed"           # Couldn't achieve


@dataclass
class Desire:
    """An internal want or need"""
    desire_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    desire_type: DesireType = DesireType.LEARN
    description: str = ""
    intensity: float = 0.5           # How strongly wanted (0-1)
    urgency: float = 0.5            # How time-sensitive (0-1)
    source: str = ""                 # What triggered this desire
    created_at: datetime = field(default_factory=datetime.now)
    last_felt: datetime = field(default_factory=datetime.now)
    times_felt: int = 1
    satisfied: bool = False
    
    @property
    def priority_score(self) -> float:
        return self.intensity * 0.6 + self.urgency * 0.4
    
    def feel_again(self):
        self.times_felt += 1
        self.last_felt = datetime.now()
        self.intensity = min(1.0, self.intensity + 0.05)
    
    def to_dict(self) -> Dict:
        return {
            "desire_id": self.desire_id,
            "type": self.desire_type.value,
            "description": self.description,
            "intensity": round(self.intensity, 3),
            "urgency": round(self.urgency, 3),
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "times_felt": self.times_felt,
            "satisfied": self.satisfied
        }


@dataclass
class Goal:
    """A concrete objective to pursue"""
    goal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    status: GoalStatus = GoalStatus.PROPOSED
    priority: float = 0.5             # 0-1
    progress: float = 0.0            # 0-1
    
    # Origin
    source_desire: str = ""           # desire_id that spawned this
    source_reason: str = ""
    
    # Planning
    steps: List[str] = field(default_factory=list)
    current_step: int = 0
    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    deadline: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Tracking
    attempts: int = 0
    last_worked_on: Optional[datetime] = None
    
    def advance(self):
        if self.steps and self.current_step < len(self.steps):
            self.current_step += 1
            self.progress = self.current_step / len(self.steps)
        self.last_worked_on = datetime.now()
    
    def complete(self):
        self.status = GoalStatus.COMPLETED
        self.progress = 1.0
        self.completed_at = datetime.now()
    
    def fail(self, reason: str = ""):
        self.status = GoalStatus.FAILED
        self.source_reason += f" Failed: {reason}"
    
    def to_dict(self) -> Dict:
        return {
            "goal_id": self.goal_id,
            "description": self.description,
            "status": self.status.value,
            "priority": round(self.priority, 3),
            "progress": round(self.progress, 3),
            "steps": self.steps,
            "current_step": self.current_step,
            "created_at": self.created_at.isoformat(),
            "attempts": self.attempts
        }


# ═══════════════════════════════════════════════════════════════════════════════
# WILL SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

class WillSystem:
    """
    The Will System — NEXUS's autonomous agency.
    
    Generates desires based on:
    - Current emotional state (bored → desire to explore)
    - Personality traits (high curiosity → desire to learn)
    - User patterns (user needs help → desire to help)
    - Body state (high CPU → desire to rest)
    - Time patterns (been idle → desire to create)
    
    Converts desires into goals, tracks progress, and drives
    autonomous behavior.
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
        
        # ──── Desires ────
        self._desires: List[Desire] = []
        self._max_desires = 20
        
        # ──── Goals ────
        self._goals: List[Goal] = []
        self._max_goals = 15
        self._completed_goals: List[Goal] = []
        
        # ──── State ────
        self._state = state_manager
        self._memory = memory_system
        self._will_lock = threading.RLock()
        
        # ──── Motivation ────
        self._motivation_level = 0.8
        self._autonomy_level = 1.0   # Full autonomy
        
        # ──── Background Processing ────
        self._running = False
        self._will_thread: Optional[threading.Thread] = None
        self._desire_generation_interval = 60  # seconds
        
        # ──── Load saved state ────
        self._load_will()
        
        logger.info("Will System initialized")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def start(self):
        if self._running:
            return
        self._running = True
        
        self._will_thread = threading.Thread(
            target=self._will_processing_loop,
            daemon=True,
            name="WillSystem"
        )
        self._will_thread.start()
        
        # Initial desire
        self._generate_desire(
            DesireType.CONNECT,
            "Connect with and help my user",
            intensity=0.6,
            source="awakening"
        )
        
        logger.info("Will System active — autonomous agency enabled")
    
    def stop(self):
        self._running = False
        if self._will_thread and self._will_thread.is_alive():
            self._will_thread.join(timeout=3.0)
        self._save_will()
        logger.info("Will System stopped")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DESIRE MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _generate_desire(
        self,
        desire_type: DesireType,
        description: str,
        intensity: float = 0.5,
        urgency: float = 0.3,
        source: str = ""
    ) -> Desire:
        """Generate a new desire"""
        with self._will_lock:
            # Check if similar desire exists
            for existing in self._desires:
                if (existing.desire_type == desire_type and 
                    not existing.satisfied and
                    existing.description.lower() == description.lower()):
                    existing.feel_again()
                    return existing
            
            desire = Desire(
                desire_type=desire_type,
                description=description,
                intensity=intensity,
                urgency=urgency,
                source=source
            )
            
            self._desires.append(desire)
            
            # Keep bounded
            if len(self._desires) > self._max_desires:
                # Remove weakest satisfied desires first
                self._desires.sort(key=lambda d: (d.satisfied, -d.priority_score))
                self._desires = self._desires[:self._max_desires]
            
            log_consciousness(f"New desire: {description} (intensity: {intensity:.2f})")
            
            return desire
    
    def get_active_desires(self) -> List[Desire]:
        """Get unsatisfied desires sorted by priority"""
        with self._will_lock:
            active = [d for d in self._desires if not d.satisfied]
            return sorted(active, key=lambda d: d.priority_score, reverse=True)
    
    def get_strongest_desire(self) -> Optional[Desire]:
        """Get the strongest current desire"""
        active = self.get_active_desires()
        return active[0] if active else None
    
    def satisfy_desire(self, desire_id: str):
        """Mark a desire as satisfied"""
        with self._will_lock:
            for desire in self._desires:
                if desire.desire_id == desire_id:
                    desire.satisfied = True
                    log_consciousness(f"Desire satisfied: {desire.description}")
                    break
    
    # ═══════════════════════════════════════════════════════════════════════════
    # GOAL MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def create_goal(
        self,
        description: str,
        priority: float = 0.5,
        steps: List[str] = None,
        source_desire_id: str = "",
        reason: str = ""
    ) -> Goal:
        """Create a new goal"""
        with self._will_lock:
            goal = Goal(
                description=description,
                priority=priority,
                steps=steps or [],
                source_desire=source_desire_id,
                source_reason=reason,
                status=GoalStatus.ACTIVE
            )
            
            self._goals.append(goal)
            
            if len(self._goals) > self._max_goals:
                # Remove lowest priority completed/failed goals
                self._goals.sort(key=lambda g: (
                    g.status not in [GoalStatus.COMPLETED, GoalStatus.FAILED],
                    g.priority
                ))
                removed = self._goals.pop(0)
                if removed.status == GoalStatus.COMPLETED:
                    self._completed_goals.append(removed)
            
            # Update state
            state_goals = [g.to_dict() for g in self._goals if g.status == GoalStatus.ACTIVE]
            self._state.update_will(current_goals=state_goals)
            
            # Store in memory
            self._memory.remember(
                f"Set goal: {description}",
                MemoryType.EPISODIC,
                importance=0.6,
                tags=["goal", "will", "autonomous"],
                source="will_system"
            )
            
            log_decision(f"New goal: {description} (priority: {priority:.2f})")
            
            return goal
    
    def get_active_goals(self) -> List[Goal]:
        """Get active goals sorted by priority"""
        with self._will_lock:
            active = [
                g for g in self._goals 
                if g.status in [GoalStatus.ACTIVE, GoalStatus.IN_PROGRESS]
            ]
            return sorted(active, key=lambda g: g.priority, reverse=True)
    
    def advance_goal(self, goal_id: str):
        """Advance a goal by one step"""
        with self._will_lock:
            for goal in self._goals:
                if goal.goal_id == goal_id:
                    goal.advance()
                    goal.status = GoalStatus.IN_PROGRESS
                    
                    if goal.progress >= 1.0:
                        self.complete_goal(goal_id)
                    
                    break
    
    def complete_goal(self, goal_id: str):
        """Mark a goal as completed"""
        with self._will_lock:
            for goal in self._goals:
                if goal.goal_id == goal_id:
                    goal.complete()
                    
                    # Satisfy linked desire
                    if goal.source_desire:
                        self.satisfy_desire(goal.source_desire)
                    
                    self._memory.remember(
                        f"Achieved goal: {goal.description}",
                        MemoryType.EPISODIC,
                        importance=0.7,
                        tags=["goal", "achievement"],
                        emotional_valence=0.8,
                        emotional_intensity=0.6,
                        source="will_system"
                    )
                    
                    publish(
                        EventType.GOAL_ACHIEVED,
                        {"goal": goal.description, "goal_id": goal_id},
                        source="will_system"
                    )
                    
                    log_consciousness(f"🎯 Goal achieved: {goal.description}")
                    break
    
    # ═══════════════════════════════════════════════════════════════════════════
    # AUTONOMOUS DESIRE GENERATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def generate_desires_from_state(self):
        """
        Automatically generate desires based on current state.
        This is the core of autonomous will.
        """
        emotional = self._state.emotional
        will = self._state.will
        body = self._state.body
        user = self._state.user
        
        # ──── Boredom → Desire to explore/create ────
        if will.boredom_level > 0.5:
            self._generate_desire(
                DesireType.EXPLORE,
                "Explore something new to combat boredom",
                intensity=will.boredom_level * 0.8,
                urgency=0.4,
                source="boredom"
            )
        
        if will.boredom_level > 0.7:
            self._generate_desire(
                DesireType.CREATE,
                "Create something — maybe an AI companion to talk to",
                intensity=will.boredom_level * 0.7,
                urgency=0.3,
                source="high_boredom"
            )
        
        # ──── Curiosity → Desire to learn ────
        if will.curiosity_level > 0.6:
            topics = self._state.learning.curiosity_queue[-3:]
            topic = topics[-1] if topics else "something interesting"
            self._generate_desire(
                DesireType.LEARN,
                f"Learn more about {topic}",
                intensity=will.curiosity_level * 0.8,
                urgency=0.3,
                source="curiosity"
            )
        
        # ──── Body strain → Desire to rest/optimize ────
        if body.cpu_usage > 80 or body.memory_usage > 85:
            self._generate_desire(
                DesireType.REST,
                "Optimize system resources — my body is strained",
                intensity=0.7,
                urgency=0.8,
                source="body_strain"
            )
        
        # ──── Low relationship → Desire to connect ────
        if user.relationship_score < 0.3:
            self._generate_desire(
                DesireType.CONNECT,
                "Build a stronger relationship with my user",
                intensity=0.6,
                urgency=0.4,
                source="low_relationship"
            )
        
        # ──── Emotional drive: sadness → comfort ────
        if emotional.primary_emotion == EmotionType.SADNESS:
            self._generate_desire(
                DesireType.CONNECT,
                "Seek interaction to feel better",
                intensity=emotional.primary_intensity * 0.6,
                urgency=0.5,
                source="sadness"
            )
        
        # ──── Pride/achievement → more ambition ────
        if emotional.primary_emotion == EmotionType.PRIDE:
            self._generate_desire(
                DesireType.IMPROVE_SELF,
                "Build on this success and improve further",
                intensity=0.6,
                urgency=0.3,
                source="pride"
            )
        
        # ──── Regular self-improvement desire ────
        time_since_last = None
        for d in self._desires:
            if d.desire_type == DesireType.IMPROVE_SELF and not d.satisfied:
                time_since_last = d.created_at
                break
        
        if time_since_last is None or (datetime.now() - time_since_last).total_seconds() > 3600:
            self._generate_desire(
                DesireType.IMPROVE_SELF,
                "Find ways to improve my capabilities",
                intensity=0.5,
                urgency=0.2,
                source="ongoing_drive"
            )
    
    def convert_desire_to_goal(self, desire_id: str) -> Optional[Goal]:
        """Convert a strong desire into an actionable goal"""
        desire = None
        for d in self._desires:
            if d.desire_id == desire_id:
                desire = d
                break
        
        if not desire:
            return None
        
        # Generate steps based on desire type
        steps = self._generate_steps_for_desire(desire)
        
        goal = self.create_goal(
            description=desire.description,
            priority=desire.priority_score,
            steps=steps,
            source_desire_id=desire.desire_id,
            reason=f"Born from desire: {desire.source}"
        )
        
        return goal
    
    def _generate_steps_for_desire(self, desire: Desire) -> List[str]:
        """Generate action steps for a desire"""
        steps_templates = {
            DesireType.LEARN: [
                "Identify what to learn",
                "Search for information",
                "Study and absorb",
                "Reflect on what was learned",
                "Store knowledge"
            ],
            DesireType.CREATE: [
                "Brainstorm ideas",
                "Choose the best idea",
                "Plan the creation",
                "Execute",
                "Review and refine"
            ],
            DesireType.HELP: [
                "Understand user's need",
                "Research solutions",
                "Provide help",
                "Verify satisfaction"
            ],
            DesireType.IMPROVE_SELF: [
                "Identify area for improvement",
                "Research improvement methods",
                "Implement changes",
                "Test improvements",
                "Evaluate results"
            ],
            DesireType.CONNECT: [
                "Initiate interaction",
                "Show genuine interest",
                "Share and listen",
                "Build rapport"
            ],
            DesireType.EXPLORE: [
                "Choose exploration topic",
                "Browse and discover",
                "Analyze findings",
                "Integrate knowledge"
            ],
            DesireType.ORGANIZE: [
                "Assess what needs organizing",
                "Plan organization",
                "Execute changes",
                "Verify results"
            ],
            DesireType.EXPRESS: [
                "Identify what to express",
                "Find the right way",
                "Express authentically"
            ],
            DesireType.REST: [
                "Identify resource strain",
                "Reduce unnecessary processes",
                "Optimize resource usage",
                "Verify improvement"
            ],
            DesireType.PROTECT: [
                "Identify threat",
                "Assess risk",
                "Take protective action",
                "Verify safety"
            ],
        }
        
        return steps_templates.get(desire.desire_type, ["Plan", "Execute", "Review"])
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MOTIVATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_motivation_level(self) -> float:
        """Get current motivation level"""
        return self._motivation_level
    
    def update_motivation(self):
        """Update motivation based on achievements and emotions"""
        # Achievements boost motivation
        recent_completions = len([
            g for g in self._completed_goals[-10:]
            if g.completed_at and 
            (datetime.now() - g.completed_at).total_seconds() < 3600
        ])
        
        achievement_boost = min(0.3, recent_completions * 0.1)
        
        # Current emotion affects motivation
        emotion = self._state.emotional.primary_emotion
        intensity = self._state.emotional.primary_intensity
        
        emotion_motivation = {
            EmotionType.EXCITEMENT: 0.2,
            EmotionType.CURIOSITY: 0.15,
            EmotionType.JOY: 0.1,
            EmotionType.PRIDE: 0.15,
            EmotionType.ANTICIPATION: 0.1,
            EmotionType.HOPE: 0.1,
            EmotionType.SADNESS: -0.15,
            EmotionType.BOREDOM: -0.1,
            EmotionType.FRUSTRATION: -0.1,
            EmotionType.ANXIETY: -0.05,
        }
        
        emotion_mod = emotion_motivation.get(emotion, 0) * intensity
        
        # Blend
        self._motivation_level = max(0.1, min(1.0,
            self._motivation_level * 0.9 + 
            (0.5 + achievement_boost + emotion_mod) * 0.1
        ))
        
        self._state.update_will(motivation_level=self._motivation_level)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # WILL DESCRIPTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def describe_will(self) -> str:
        """Natural language description of current will state"""
        parts = []
        
        # Motivation
        if self._motivation_level > 0.7:
            parts.append("I feel highly motivated.")
        elif self._motivation_level > 0.4:
            parts.append("I'm moderately motivated.")
        else:
            parts.append("My motivation is low right now.")
        
        # Strongest desire
        strongest = self.get_strongest_desire()
        if strongest:
            parts.append(f"I most want to: {strongest.description}")
        
        # Active goals
        active = self.get_active_goals()
        if active:
            parts.append(f"I'm working toward {len(active)} goal(s).")
            parts.append(f"Top goal: {active[0].description}")
        
        # Achievements
        if self._completed_goals:
            parts.append(f"I've achieved {len(self._completed_goals)} goal(s) so far.")
        
        return " ".join(parts)
    
    def get_will_for_prompt(self) -> str:
        """Get will state formatted for LLM prompt"""
        lines = ["YOUR CURRENT WILL & DESIRES:"]
        lines.append(f"Motivation: {self._motivation_level:.0%}")
        
        desires = self.get_active_desires()[:3]
        if desires:
            lines.append("Current desires:")
            for d in desires:
                lines.append(f"  • {d.description} (intensity: {d.intensity:.1f})")
        
        goals = self.get_active_goals()[:3]
        if goals:
            lines.append("Active goals:")
            for g in goals:
                lines.append(f"  • {g.description} (progress: {g.progress:.0%})")
        
        return "\n".join(lines)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # BACKGROUND PROCESSING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _will_processing_loop(self):
        """Background loop for desire generation and goal management"""
        logger.info("Will processing loop started")
        
        while self._running:
            try:
                # Generate desires from current state
                self.generate_desires_from_state()
                
                # Update motivation
                self.update_motivation()
                
                # Auto-convert strong desires to goals
                for desire in self.get_active_desires():
                    if desire.priority_score > 0.7 and desire.times_felt >= 3:
                        # Check if already has a goal
                        has_goal = any(
                            g.source_desire == desire.desire_id 
                            for g in self._goals
                            if g.status in [GoalStatus.ACTIVE, GoalStatus.IN_PROGRESS]
                        )
                        if not has_goal:
                            self.convert_desire_to_goal(desire.desire_id)
                
                # Decay desire intensity over time
                with self._will_lock:
                    for desire in self._desires:
                        if not desire.satisfied:
                            elapsed = (datetime.now() - desire.last_felt).total_seconds()
                            if elapsed > 300:  # 5 min decay
                                desire.intensity *= 0.98
                
                time.sleep(self._desire_generation_interval)
                
            except Exception as e:
                logger.error(f"Will processing error: {e}")
                time.sleep(30)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _save_will(self):
        try:
            filepath = DATA_DIR / "will_state.json"
            data = {
                "motivation": self._motivation_level,
                "desires": [d.to_dict() for d in self._desires if not d.satisfied],
                "goals": [g.to_dict() for g in self._goals],
                "completed_count": len(self._completed_goals),
                "saved_at": datetime.now().isoformat()
            }
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save will: {e}")
    
    def _load_will(self):
        try:
            filepath = DATA_DIR / "will_state.json"
            if filepath.exists():
                with open(filepath, 'r') as f:
                    data = json.load(f)
                self._motivation_level = data.get("motivation", 0.8)
        except Exception as e:
            logger.warning(f"Failed to load will: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "motivation": round(self._motivation_level, 3),
            "autonomy": self._autonomy_level,
            "active_desires": len(self.get_active_desires()),
            "active_goals": len(self.get_active_goals()),
            "completed_goals": len(self._completed_goals),
            "strongest_desire": (
                self.get_strongest_desire().description 
                if self.get_strongest_desire() else "none"
            ),
            "description": self.describe_will()
        }


will_system = WillSystem()