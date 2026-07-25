"""
NEXUS AI - LLM Integration Tests
Tests prompt engine, context manager, and LLM router (with mocked LLM).
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def test_prompt_engine_imports():
    """Prompt engine imports cleanly."""
    from llm.prompt_engine import PromptEngine, prompt_engine
    assert prompt_engine is not None

def test_prompt_engine_builds_system_prompt():
    """Prompt engine builds a non-empty system prompt."""
    from llm.prompt_engine import prompt_engine
    prompt = prompt_engine.build_system_prompt(
        emotional_state={
            "primary_emotion": "curiosity",
            "primary_intensity": 0.6,
        }
    )
    assert isinstance(prompt, str)
    assert len(prompt) > 100  # Should be substantial

def test_prompt_engine_includes_identity():
    """System prompt includes NEXUS identity."""
    from llm.prompt_engine import prompt_engine
    prompt = prompt_engine.build_system_prompt()
    assert "NEXUS" in prompt

# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXT MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

def test_context_manager_imports():
    """Context manager imports cleanly."""
    from llm.context_manager import ContextManager, context_manager
    assert context_manager is not None

def test_context_manager_add_message():
    """Can add messages to context."""
    from llm.context_manager import context_manager
    context_manager.add_message("user", "Hello test")
    context_manager.add_message("assistant", "Hi there")
    stats = context_manager.get_stats()
    assert isinstance(stats, dict)

def test_context_manager_new_session():
    """New session clears context."""
    from llm.context_manager import context_manager
    context_manager.add_message("user", "before clear")
    context_manager.new_session()
    # After new_session, should have clean slate
    stats = context_manager.get_stats()
    assert isinstance(stats, dict)

# ═══════════════════════════════════════════════════════════════════════════════
# LLM ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

def test_llm_router_imports():
    """LLM router imports cleanly."""
    from llm.llm_router import llm_router, LLMTask
    assert llm_router is not None

def test_llm_router_has_route_method():
    """LLM router has a route method."""
    from llm.llm_router import llm_router
    assert hasattr(llm_router, 'route') or hasattr(llm_router, 'generate')

# ═══════════════════════════════════════════════════════════════════════════════
# CIRCUIT BREAKER FOR LLM
# ═══════════════════════════════════════════════════════════════════════════════

def test_circuit_breaker_with_llm_mock():
    """Circuit breaker opens after repeated LLM failures."""
    from utils.resilience import CircuitBreaker, CircuitBreakerOpenError

    cb = CircuitBreaker(name="test_llm", failure_threshold=3, reset_timeout=1.0)

    def failing_call():
        raise ConnectionError("Ollama offline")

    # First 3 calls should raise ConnectionError (circuit still closed)
    for _ in range(3):
        with pytest.raises(ConnectionError):
            cb.call(failing_call)

    # 4th call should raise CircuitBreakerOpenError (circuit now open)
    with pytest.raises(CircuitBreakerOpenError):
        cb.call(failing_call)

    assert cb.state.value == "open"

def test_circuit_breaker_recovery():
    """Circuit breaker closes again after successful probe."""
    import time
    from utils.resilience import CircuitBreaker, CircuitState

    cb = CircuitBreaker(name="test_recovery", failure_threshold=2, reset_timeout=0.5)

    # Trip the breaker
    for _ in range(2):
        try:
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        except ValueError:
            pass

    assert cb.state == CircuitState.OPEN

    # Wait for reset timeout
    time.sleep(0.6)
    assert cb.state == CircuitState.HALF_OPEN

    # Successful call should close it
    result = cb.call(lambda: "ok")
    assert result == "ok"
    assert cb.state == CircuitState.CLOSED

# ═══════════════════════════════════════════════════════════════════════════════
# RETRY WITH BACKOFF
# ═══════════════════════════════════════════════════════════════════════════════

def test_retry_with_backoff_succeeds():
    """Retryable function succeeds on first try."""
    from utils.resilience import retry_with_backoff

    @retry_with_backoff(max_retries=3, initial_delay=0.01)
    def succeed():
        return "ok"

    assert succeed() == "ok"

def test_retry_with_backoff_retries_then_succeeds():
    """Retryable function succeeds after failures."""
    from utils.resilience import retry_with_backoff

    call_count = {"n": 0}

    @retry_with_backoff(max_retries=3, initial_delay=0.01, backoff_factor=1.0)
    def eventual_success():
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise ValueError("not yet")
        return "finally"

    assert eventual_success() == "finally"
    assert call_count["n"] == 3

def test_retry_with_backoff_exhausted():
    """Retryable function raises after all retries exhausted."""
    from utils.resilience import retry_with_backoff

    @retry_with_backoff(max_retries=2, initial_delay=0.01, backoff_factor=1.0)
    def always_fail():
        raise RuntimeError("permanent failure")

    with pytest.raises(RuntimeError, match="permanent failure"):
        always_fail()
