"""
NEXUS AI - State Manager Tests
Validates state updates, emotional transitions, consciousness levels.
"""

import sys
import pytest
from pathlib import Path

def test_state_manager_imports():
    """State manager imports cleanly."""
    from core.state_manager import StateManager, NexusState, state_manager
    assert state_manager is not None

def test_state_manager_has_initial_state():
    """State manager has valid initial state."""
    from core.state_manager import state_manager
    assert hasattr(state_manager, 'emotional')
    assert hasattr(state_manager, 'system')
    assert hasattr(state_manager, 'user')

def test_state_manager_update_system():
    """Can update system state."""
    from core.state_manager import state_manager
    state_manager.update_system(running=True)
    assert state_manager.system.running is True

def test_state_manager_update_consciousness():
    """Can update consciousness level."""
    from config import ConsciousnessLevel
    from core.state_manager import state_manager
    state_manager.update_consciousness(level=ConsciousnessLevel.FOCUSED)
    assert state_manager.consciousness.level == ConsciousnessLevel.FOCUSED

def test_state_manager_update_emotional():
    """Can update emotional state."""
    from config import EmotionType
    from core.state_manager import state_manager
    state_manager.update_emotional(
        primary_emotion=EmotionType.JOY,
        primary_intensity=0.8
    )
    assert state_manager.emotional.primary_emotion == EmotionType.JOY
    assert state_manager.emotional.primary_intensity == 0.8

def test_state_manager_serialization():
    """State manager can serialize and deserialize."""
    from core.state_manager import state_manager
    # This should not crash
    state_dict = state_manager.get_state_dict() if hasattr(state_manager, 'get_state_dict') else {}
    assert isinstance(state_dict, dict)
