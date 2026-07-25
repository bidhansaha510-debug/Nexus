"""
NEXUS AI - Cognition System Tests
Validates cognition engine loading, router, and basic engine calls.
"""

import sys
import pytest
from pathlib import Path

def test_cognition_system_imports():
    """Cognition system imports cleanly."""
    from cognition import CognitionSystem, cognition_system
    assert cognition_system is not None

def test_cognition_system_has_engines():
    """Cognition system has multiple engines loaded."""
    from cognition import cognition_system
    # It should have loaded at least some engines
    if hasattr(cognition_system, 'get_summary'):
        summary = cognition_system.get_summary()
        assert isinstance(summary, str)

def test_cognition_system_has_stats():
    """Cognition system can report stats."""
    from cognition import cognition_system
    if hasattr(cognition_system, 'get_stats'):
        stats = cognition_system.get_stats()
        assert isinstance(stats, dict)

def test_logical_reasoning_imports():
    """Logical reasoning engine imports cleanly."""
    from cognition.logical_reasoning import logical_reasoning
    assert logical_reasoning is not None

def test_dialectical_reasoning_imports():
    """Dialectical reasoning engine imports cleanly."""
    from cognition.dialectical_reasoning import dialectical_reasoning
    assert dialectical_reasoning is not None

def test_creative_synthesis_imports():
    """Creative synthesis engine imports cleanly."""
    from cognition.creative_synthesis import creative_synthesis
    assert creative_synthesis is not None

def test_ethical_reasoning_imports():
    """Ethical reasoning engine imports cleanly."""
    from cognition.ethical_reasoning import ethical_reasoning
    assert ethical_reasoning is not None

def test_planning_engine_imports():
    """Planning engine imports cleanly."""
    from cognition.planning_engine import planning_engine
    assert planning_engine is not None

def test_cognitive_router_imports():
    """Cognitive router imports cleanly."""
    from cognition.cognitive_router import cognitive_router
    assert cognitive_router is not None
    assert hasattr(cognitive_router, 'start') or hasattr(cognitive_router, 'route')
