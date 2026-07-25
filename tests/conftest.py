"""
NEXUS AI - Shared Test Fixtures
Provides isolated, reusable fixtures for all test modules.
"""

import sys
import os
import pytest
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).parent.parent

# ═══════════════════════════════════════════════════════════════════════════════
# LIST OF ALL IMPORTABLE MODULES (for parametrized import tests)
# ═══════════════════════════════════════════════════════════════════════════════

# Core infrastructure — must import cleanly
CORE_MODULES = [
    "config",
    "utils.logger",
    "utils.json_parser",
    "utils.json_utils",
    "utils.resilience",
    "utils.metrics",
    "core.event_bus",
    "core.state_manager",
    "core.memory_system",
]

# LLM modules
LLM_MODULES = [
    "llm.llama_interface",
    "llm.context_manager",
    "llm.prompt_engine",
    "llm.groq_interface",
    "llm.llm_router",
]

# Brain + subsystems — may trigger heavy init but should NOT crash
SUBSYSTEM_MODULES = [
    "core.anger_system",
    "core.provocation_detector",
    "core.ability_executor",
    "core.nexus_brain",
]

# Consciousness
CONSCIOUSNESS_MODULES = [
    "consciousness.global_workspace",
    "consciousness.self_awareness",
    "consciousness.metacognition",
    "consciousness.inner_voice",
]

# Cognition (sample — not all 95)
COGNITION_MODULES = [
    "cognition.logical_reasoning",
    "cognition.dialectical_reasoning",
    "cognition.creative_synthesis",
    "cognition.ethical_reasoning",
    "cognition.planning_engine",
]

# Emotions
EMOTION_MODULES = [
    "emotions.emotion_engine",
    "emotions.mood_system",
    "emotions.emotional_memory",
]

ALL_MODULES = (
    CORE_MODULES + LLM_MODULES + SUBSYSTEM_MODULES +
    CONSCIOUSNESS_MODULES + COGNITION_MODULES + EMOTION_MODULES
)

# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def nexus_config():
    """Fresh NEXUS config with test-safe overrides."""
    from config import NexusConfig
    config = NexusConfig()
    # Disable network-dependent features for tests
    config.internet.learning_enabled = False
    config.internet.research_enabled = False
    config.internet.tor_enabled = False
    config.social_media.enabled = False
    config.social_media.facebook_enabled = False
    config.social_media.twitter_enabled = False
    config.social_media.instagram_enabled = False
    config.monitoring.tracking_enabled = False
    config.pc_control.enabled = False
    config.web.enabled = False
    config.log_level = "WARNING"
    return config

@pytest.fixture
def fresh_event_bus():
    """Isolated event bus instance for testing."""
    from core.event_bus import EventBus
    bus = EventBus.__new__(EventBus)
    bus._initialized = False
    bus.__init__()
    return bus

@pytest.fixture
def mock_llm():
    """Mock LLM interface that returns canned responses without Ollama."""
    mock = MagicMock()
    mock.is_connected = True
    mock.model_name = "test-model"

    # Default generate response
    response = MagicMock()
    response.success = True
    response.text = "This is a test response from the mock LLM."
    response.tokens_used = 50
    response.generation_time = 0.1
    mock.generate.return_value = response

    # Default list_models
    mock.list_models.return_value = ["test-model"]

    return mock

@pytest.fixture
def memory_system_fixture(tmp_path):
    """Fresh in-memory/temp memory system for testing."""
    from core.memory_system import MemorySystem
    # Create a fresh instance with tmp_path for isolation
    ms = MemorySystem.__new__(MemorySystem)
    ms._initialized = False
    # Patch the DB path to use temp directory
    with patch('core.memory_system.MEMORY_DIR', tmp_path):
        ms.__init__()
    return ms

@pytest.fixture
def state_manager_fixture():
    """Fresh state manager for testing."""
    from core.state_manager import StateManager
    sm = StateManager.__new__(StateManager)
    sm._initialized = False
    sm.__init__()
    return sm

@pytest.fixture
def health_registry():
    """Fresh health registry for testing."""
    from utils.resilience import HealthRegistry
    registry = HealthRegistry.__new__(HealthRegistry)
    registry._initialized = False
    registry.__init__()
    return registry

@pytest.fixture
def metrics_collector():
    """Fresh metrics collector for testing."""
    from utils.metrics import MetricsCollector
    mc = MetricsCollector.__new__(MetricsCollector)
    mc._initialized = False
    mc.__init__()
    return mc

@pytest.fixture
def mock_brain(mock_llm, state_manager_fixture, memory_system_fixture, fresh_event_bus):
    """A NexusBrain instance with mocked dependencies for isolating test logic."""
    from core.nexus_brain import NexusBrain
    brain = NexusBrain.__new__(NexusBrain)
    brain._initialized = False
    
    # Patch dependencies globally for the init
    with patch('core.nexus_brain.llm', mock_llm), \
         patch('core.nexus_brain.state_manager', state_manager_fixture), \
         patch('core.nexus_brain.memory_system', memory_system_fixture), \
         patch('core.nexus_brain.event_bus', fresh_event_bus):
        brain.__init__()
        
    yield brain
    
    # Cleanup
    if getattr(brain, '_running', False):
        try:
            brain.stop()
        except:
            pass
