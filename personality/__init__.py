"""
NEXUS AI - Personality Package
Personality traits, autonomous will, goal hierarchy, and decision-making.
"""

from typing import Dict

from personality.personality_core import (
    PersonalityCore, personality_core,
    TraitProfile, TRAIT_PROFILES
)
from personality.will_system import (
    WillSystem, will_system,
    Desire, Goal, DesireType, GoalStatus
)
from personality.goal_hierarchy import (
    GoalHierarchy, goal_hierarchy,
    HierarchicalGoal, GoalLevel, GoalStatus as HierarchyGoalStatus, GoalType
)

__all__ = [
    'PersonalityCore', 'personality_core', 'TRAIT_PROFILES',
    'WillSystem', 'will_system',
    'Desire', 'Goal', 'DesireType', 'GoalStatus',
    'GoalHierarchy', 'goal_hierarchy',
    'HierarchicalGoal', 'GoalLevel', 'GoalType',
]


class PersonalitySystem:
    """Unified facade for the personality system."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._personality = personality_core
        self._will = will_system
        self._goals = goal_hierarchy
        self._running = False
    
    def start(self):
        if self._running:
            return
        self._will.start()
        self._running = True
    
    def stop(self):
        if not self._running:
            return
        self._will.stop()
        self._personality.save_personality()
        self._running = False
    
    @property
    def personality(self) -> PersonalityCore:
        return self._personality
    
    @property
    def will(self) -> WillSystem:
        return self._will
    
    @property
    def goals(self) -> GoalHierarchy:
        return self._goals
    
    def get_active_task(self):
        """Get the current active task from goal hierarchy."""
        return self._goals.get_active_task()
    
    def select_next_task(self):
        """Select the next best task to work on."""
        return self._goals.select_next_task()
    
    def get_motivation_context(self) -> str:
        """Get combined motivation context for prompts."""
        lines = [
            self._goals.get_prompt_context(),
            "",
            self._will.get_will_for_prompt()
        ]
        return "\n".join(lines)
    
    def get_stats(self) -> Dict:
        return {
            "personality": self._personality.get_stats(),
            "will": self._will.get_stats(),
            "goals": self._goals.get_stats()
        }


personality_system = PersonalitySystem()
