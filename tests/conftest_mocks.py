"""
NEXUS AI — Extended Mock Fixtures for LLM Testing
══════════════════════════════════════════════════════════════════════════════
Provides reusable mock fixtures for Groq, Ollama, and other LLM interfaces
so tests can run without real API keys or network connectivity.

Usage in tests:
    def test_something(mock_groq_interface):
        from core.speculative_decoding import SpeculativeDecoder
        # groq_interface is already patched — no real API calls
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from dataclasses import dataclass


@dataclass
class MockLLMResponse:
    """Standardized mock response matching groq_interface.generate() return type."""
    success: bool = True
    text: str = "Mock LLM response for testing."
    tokens_used: int = 42
    generation_time: float = 0.05
    model: str = "test-model"
    error: str = ""


@pytest.fixture
def mock_groq_interface():
    """
    Mock the Groq LLM interface singleton.

    Patches `llm.groq_interface.groq_interface` so any module that imports it
    will get a MagicMock instead of attempting real API calls.

    Returns the mock object for assertion/configuration in tests.
    """
    mock = MagicMock()
    mock.is_connected = True
    mock.model_name = "llama-3.3-70b-versatile"
    mock.generate.return_value = MockLLMResponse()
    mock.chat.return_value = MockLLMResponse()
    mock.list_models.return_value = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"]

    with patch("llm.groq_interface.groq_interface", mock):
        yield mock


@pytest.fixture
def mock_ollama_interface():
    """
    Mock the Ollama LLM interface for tests that depend on local model calls.

    Returns the mock object for assertion/configuration in tests.
    """
    mock = MagicMock()
    mock.is_connected = True
    mock.model_name = "llama3.2:latest"
    mock.generate.return_value = MockLLMResponse(model="llama3.2:latest")
    mock.list_models.return_value = ["llama3.2:latest"]

    with patch("llm.llama_interface.llama_interface", mock):
        yield mock


@pytest.fixture
def mock_all_llms(mock_groq_interface, mock_ollama_interface):
    """
    Convenience fixture that mocks both Groq and Ollama interfaces.
    Useful for integration-level tests that may touch either backend.
    """
    return {
        "groq": mock_groq_interface,
        "ollama": mock_ollama_interface,
    }
