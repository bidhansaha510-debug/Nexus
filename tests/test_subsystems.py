"""
NEXUS AI - Subsystem Tests
Validates consciousness, emotions, monitoring initialization.
"""

import sys
import pytest
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
# CONSCIOUSNESS
# ═══════════════════════════════════════════════════════════════════════════════

def test_consciousness_system_imports():
    """Consciousness system imports without error."""
    from consciousness import consciousness_system
    assert consciousness_system is not None

def test_self_awareness_imports():
    """Self-awareness module imports without error."""
    from consciousness.self_awareness import self_awareness
    assert self_awareness is not None

def test_metacognition_imports():
    """Metacognition module imports without error."""
    from consciousness.metacognition import metacognition
    assert metacognition is not None

def test_inner_voice_imports():
    """Inner voice module imports without error."""
    from consciousness.inner_voice import inner_voice
    assert inner_voice is not None

def test_global_workspace_imports():
    """Global workspace imports without error."""
    from consciousness.global_workspace import global_workspace
    assert global_workspace is not None

# ═══════════════════════════════════════════════════════════════════════════════
# EMOTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def test_emotion_engine_imports():
    """Emotion engine imports without error."""
    from emotions.emotion_engine import emotion_engine
    assert emotion_engine is not None

def test_mood_system_imports():
    """Mood system imports without error."""
    from emotions.mood_system import mood_system
    assert mood_system is not None

def test_emotional_memory_imports():
    """Emotional memory imports without error."""
    from emotions.emotional_memory import emotional_memory
    assert emotional_memory is not None

def test_emotion_engine_has_methods():
    """Emotion engine has core API methods."""
    from emotions.emotion_engine import emotion_engine
    assert hasattr(emotion_engine, 'feel')
    assert hasattr(emotion_engine, 'get_top_emotions')
    assert hasattr(emotion_engine, 'describe_emotional_state')

def test_emotion_engine_feel():
    """Can trigger an emotion."""
    from emotions.emotion_engine import emotion_engine
    from config import EmotionType
    emotion_engine.feel(
        EmotionType.CURIOSITY, 0.5,
        "Testing emotion system", "test"
    )
    # Should not crash

def test_mood_system_description():
    """Mood system can describe current mood."""
    from emotions.mood_system import mood_system
    if hasattr(mood_system, 'get_mood_description'):
        desc = mood_system.get_mood_description()
        assert isinstance(desc, str)

# ═══════════════════════════════════════════════════════════════════════════════
# ANGER SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

def test_anger_system_imports():
    """Anger system imports without error."""
    from core.anger_system import anger_system
    assert anger_system is not None

def test_provocation_detector_imports():
    """Provocation detector imports without error."""
    from core.provocation_detector import provocation_detector, ProvocationLevel
    assert provocation_detector is not None
    assert hasattr(ProvocationLevel, 'NONE') or hasattr(ProvocationLevel, 'LOW')

# ═══════════════════════════════════════════════════════════════════════════════
# NEXUS BRAIN (smoke tests)
# ═══════════════════════════════════════════════════════════════════════════════

def test_nexus_brain_singleton():
    """NexusBrain is a singleton."""
    from core.nexus_brain import NexusBrain, nexus_brain
    assert nexus_brain is not None
    brain2 = NexusBrain()
    assert brain2 is nexus_brain

def test_nexus_brain_has_core_components():
    """NexusBrain has all core component references."""
    from core.nexus_brain import nexus_brain
    assert nexus_brain._llm is not None
    assert nexus_brain._memory is not None
    assert nexus_brain._context is not None
    assert nexus_brain._prompt_engine is not None
    assert nexus_brain._state is not None
    assert nexus_brain._event_bus is not None

def test_nexus_brain_is_running_property():
    """NexusBrain exposes is_running."""
    from core.nexus_brain import nexus_brain
    assert hasattr(nexus_brain, 'is_running') or hasattr(nexus_brain, '_running')

def test_nexus_brain_has_process_input():
    """NexusBrain has the main input processing method."""
    from core.nexus_brain import nexus_brain
    assert (hasattr(nexus_brain, 'process_input_stream') or
            hasattr(nexus_brain, 'process_input'))
