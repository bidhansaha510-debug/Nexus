"""
NEXUS AI - Memory System Tests
Validates store, recall, search, and memory types.
"""

import sys
import pytest
from pathlib import Path

def test_memory_system_imports():
    """Memory system module imports cleanly."""
    from core.memory_system import MemorySystem, MemoryType, Memory, memory_system
    assert memory_system is not None

def test_memory_types_exist():
    """All expected memory types are defined."""
    from core.memory_system import MemoryType
    assert hasattr(MemoryType, 'CONVERSATION')
    assert hasattr(MemoryType, 'FACT')
    assert hasattr(MemoryType, 'SELF')

def test_memory_system_has_methods():
    """Memory system exposes required API methods."""
    from core.memory_system import memory_system
    assert hasattr(memory_system, 'store')
    assert hasattr(memory_system, 'recall_recent')
    assert hasattr(memory_system, 'get_stats')
    assert callable(memory_system.get_stats)

def test_memory_system_stats():
    """Memory system returns stats dict."""
    from core.memory_system import memory_system
    stats = memory_system.get_stats()
    assert isinstance(stats, dict)

def test_memory_store_and_recall():
    """Can store a memory and recall recent ones."""
    from core.memory_system import memory_system, MemoryType
    # Store a test memory
    memory_system.store(
        content="Test memory for pytest",
        memory_type=MemoryType.FACT,
        importance=0.5,
        metadata={"source": "test"}
    )
    # Recall recent
    recent = memory_system.recall_recent(limit=5)
    assert isinstance(recent, list)

def test_remember_about_self():
    """Can store self-knowledge."""
    from core.memory_system import memory_system
    memory_system.remember_about_self(
        "I am being tested by pytest",
        importance=0.3
    )
