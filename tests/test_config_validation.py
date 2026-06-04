"""Tests for configuring and verifying Nexus defaults."""
import pytest

def test_config_loads(nexus_config):
    """Config module loads and provides valid defaults."""
    from config import EmotionType, ConsciousnessLevel, MoodState
    assert nexus_config.system_name in ["NEXUS", "JARVIS", "FRIDAY"]
    assert nexus_config.llm.model_name is not None
    assert nexus_config.llm.base_url is not None
    assert len(EmotionType) > 10
    assert len(ConsciousnessLevel) > 3
    assert len(MoodState) > 3

def test_config_data_dirs_exist():
    """Data directories should be created on config import."""
    from config import DATA_DIR, MEMORY_DIR, LOG_DIR
    assert DATA_DIR.exists()
    assert MEMORY_DIR.exists()
    assert LOG_DIR.exists()
