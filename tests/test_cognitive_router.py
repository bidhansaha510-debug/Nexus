"""
Tests for the refactored CognitiveRouter.

Tests cover:
  1. Engine registry completeness
  2. False-positive reduction in keyword matching
  3. Word-boundary regex matching
  4. Cooldown sliding window
  5. Pattern deduplication
  6. Input sanitization
  7. Cache hit/miss
  8. Metrics tracking
"""

import threading
import pytest

# We patch the singleton to avoid side-effects in tests
import importlib
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestEngineRegistry:
    """Tests for the ENGINE_REGISTRY."""

    def test_registry_is_populated(self):
        from cognition.engine_registry import ENGINE_REGISTRY
        assert len(ENGINE_REGISTRY) >= 40, f"Expected 40+ engines, got {len(ENGINE_REGISTRY)}"

    def test_all_engine_keys_matches_registry(self):
        from cognition.engine_registry import ALL_ENGINE_KEYS, ENGINE_REGISTRY
        assert set(ALL_ENGINE_KEYS) == set(ENGINE_REGISTRY.keys()), (
            "ALL_ENGINE_KEYS is out of sync with ENGINE_REGISTRY"
        )

    def test_each_adapter_has_methods(self):
        from cognition.engine_registry import ENGINE_REGISTRY
        for key, adapter in ENGINE_REGISTRY.items():
            assert adapter.key == key, f"Adapter key mismatch: {adapter.key} != {key}"
            assert len(adapter.methods) >= 1, f"{key}: must have at least 1 method"
            for method in adapter.methods:
                assert callable(method.invoke), f"{key}.{method.name}: invoke is not callable"
                assert callable(method.format_result), f"{key}.{method.name}: format_result is not callable"


class TestIntentDetection:
    """Tests for keyword/pattern matching — false-positive reduction."""

    def _detect(self, text):
        """Helper: detect intents from text."""
        from cognition.cognitive_router import CognitiveRouter
        router = CognitiveRouter.__new__(CognitiveRouter)
        # Bypass singleton init — we just need _detect_intent
        return dict(router._detect_intent(text))

    def test_hello_triggers_nothing(self):
        """Normal greetings should NOT trigger engines."""
        result = self._detect("Hello, how are you doing today?")
        assert len(result) <= 1, f"Expected ≤1 engine for greeting, got {len(result)}: {result}"

    def test_when_alone_does_not_trigger_temporal(self):
        """The word 'when' alone should not trigger temporal engine."""
        result = self._detect("when")
        assert "temporal" not in result, "'when' alone should not match temporal"

    def test_when_did_triggers_temporal(self):
        """'when did' should trigger temporal."""
        result = self._detect("when did this happen?")
        assert "temporal" in result, "'when did' should match temporal"

    def test_where_alone_does_not_trigger_spatial(self):
        """The word 'where' alone should not trigger spatial engine."""
        result = self._detect("Tell me where")
        assert "spatial" not in result, "'where' alone should not match spatial"

    def test_where_is_triggers_spatial(self):
        """'where is' should trigger spatial."""
        result = self._detect("where is the nearest store?")
        assert "spatial" in result, "'where is' should match spatial"

    def test_feel_alone_does_not_trigger_emotional(self):
        """'feel' alone should not trigger emotional engine."""
        result = self._detect("I can feel the texture of this fabric")
        assert "emotional" not in result, "'feel the texture' should not match emotional"

    def test_i_feel_triggers_emotional(self):
        """'i feel' should trigger emotional."""
        result = self._detect("I feel really anxious about the exam")
        assert "emotional" in result, "'I feel' should match emotional"

    def test_plan_alone_does_not_trigger_planning(self):
        """'plan' as a standalone word should not trigger planning."""
        result = self._detect("The plan is simple")
        assert "planning" not in result, "'The plan is simple' should not match planning"

    def test_plan_for_triggers_planning(self):
        """'plan for' should trigger planning."""
        result = self._detect("Can you make a plan for my trip?")
        assert "planning" in result, "'make a plan' should match planning"

    def test_test_alone_does_not_trigger_hypothesis(self):
        """'test' alone should not trigger hypothesis engine."""
        result = self._detect("I have a test tomorrow")
        assert "hypothesis" not in result, "'test' alone should not match hypothesis"

    def test_should_i_triggers_decision(self):
        """'should i' should trigger decision engine."""
        result = self._detect("should i learn Python or JavaScript first?")
        assert "decision" in result, "'should i' should match decision"

    def test_normal_conversation_low_trigger_count(self):
        """A normal conversational message should trigger at most 2 engines."""
        messages = [
            "Hey, how's it going?",
            "Thanks for your help!",
            "That sounds good",
            "Okay, I'll try that",
            "Nice weather today",
        ]
        for msg in messages:
            result = self._detect(msg)
            assert len(result) <= 2, (
                f"Normal message '{msg}' triggered {len(result)} engines: {result}"
            )


class TestPatternDeduplication:
    """Tests that conflicting patterns are deduplicated."""

    def _detect(self, text):
        from cognition.cognitive_router import CognitiveRouter
        router = CognitiveRouter.__new__(CognitiveRouter)
        return dict(router._detect_intent(text))

    def test_what_if_fires_only_counterfactual(self):
        """'what if' should fire counterfactual, not flexibility."""
        result = self._detect("what if I had taken a different path?")
        assert "counterfactual" in result, "'what if' should match counterfactual"
        assert "flexibility" not in result, "'what if' should NOT also match flexibility"

    def test_debate_fires_only_debate(self):
        """'debate this' should fire debate, not dialectic."""
        result = self._detect("debate this topic for me")
        assert "debate" in result, "'debate this' should match debate"
        assert "dialectic" not in result, "'debate this' should NOT also match dialectic"


class TestInputSanitization:
    """Tests for input sanitization."""

    def test_truncates_long_input(self):
        from cognition.cognitive_router import CognitiveRouter, MAX_INPUT_LENGTH
        text = "a" * 5000
        sanitized = CognitiveRouter._sanitize_input(text)
        assert len(sanitized) <= MAX_INPUT_LENGTH

    def test_strips_control_characters(self):
        from cognition.cognitive_router import CognitiveRouter
        text = "Hello\x00World\x07Test\x1f"
        sanitized = CognitiveRouter._sanitize_input(text)
        assert "\x00" not in sanitized
        assert "\x07" not in sanitized
        assert "\x1f" not in sanitized
        assert "HelloWorldTest" == sanitized

    def test_strips_whitespace(self):
        from cognition.cognitive_router import CognitiveRouter
        assert CognitiveRouter._sanitize_input("  hello  ") == "hello"


class TestLRUCache:
    """Tests for the LRU cache."""

    def test_cache_hit(self):
        from cognition.cognitive_router import _LRUCache, CognitiveInsights
        cache = _LRUCache(maxsize=4)
        key = cache.make_key("test input")
        insight = CognitiveInsights(user_input="test input")
        cache.put(key, insight)
        assert cache.get(key) is insight

    def test_cache_miss(self):
        from cognition.cognitive_router import _LRUCache
        cache = _LRUCache(maxsize=4)
        assert cache.get("nonexistent") is None

    def test_cache_eviction(self):
        from cognition.cognitive_router import _LRUCache, CognitiveInsights
        cache = _LRUCache(maxsize=2)
        k1 = cache.make_key("input 1")
        k2 = cache.make_key("input 2")
        k3 = cache.make_key("input 3")
        cache.put(k1, CognitiveInsights(user_input="1"))
        cache.put(k2, CognitiveInsights(user_input="2"))
        cache.put(k3, CognitiveInsights(user_input="3"))  # should evict k1
        assert cache.get(k1) is None
        assert cache.get(k2) is not None
        assert cache.get(k3) is not None

    def test_cache_key_normalization(self):
        from cognition.cognitive_router import _LRUCache
        k1 = _LRUCache.make_key("  Hello World  ")
        k2 = _LRUCache.make_key("hello world")
        assert k1 == k2, "Cache keys should be case-insensitive and trim whitespace"


class TestEngineMetrics:
    """Tests for the EngineMetrics dataclass."""

    def test_avg_latency(self):
        from cognition.cognitive_router import EngineMetrics
        m = EngineMetrics(calls=4, total_latency=2.0)
        assert m.avg_latency == 0.5

    def test_failure_rate(self):
        from cognition.cognitive_router import EngineMetrics
        m = EngineMetrics(calls=10, failures=3)
        assert m.failure_rate == 0.3

    def test_zero_calls_no_division_error(self):
        from cognition.cognitive_router import EngineMetrics
        m = EngineMetrics()
        assert m.avg_latency == 0.0
        assert m.failure_rate == 0.0


class TestCooldown:
    """Tests for the sliding-window cooldown."""

    def test_engine_not_blocked_after_single_use(self):
        """With COOLDOWN_MESSAGES=3, an engine should NOT be blocked after appearing once."""
        from cognition.cognitive_router import CognitiveRouter, COOLDOWN_MESSAGES

        router = CognitiveRouter.__new__(CognitiveRouter)
        router._state_lock = threading.Lock()
        router._recent_engines = ["decision"]  # appeared once

        scored = [("decision", 1.2), ("ethics", 1.0)]
        selected = router._select_engines(scored)
        assert "decision" in selected, (
            "Engine should not be blocked after appearing once (cooldown=3)"
        )

    def test_engine_blocked_after_cooldown_threshold(self):
        """An engine appearing COOLDOWN_MESSAGES times should be skipped."""
        from cognition.cognitive_router import CognitiveRouter, COOLDOWN_MESSAGES

        router = CognitiveRouter.__new__(CognitiveRouter)
        router._state_lock = threading.Lock()
        router._recent_engines = ["decision"] * COOLDOWN_MESSAGES  # hit threshold

        scored = [("decision", 1.2), ("ethics", 1.0)]
        selected = router._select_engines(scored)
        assert "decision" not in selected, (
            f"Engine should be blocked after appearing {COOLDOWN_MESSAGES} times"
        )
        assert "ethics" in selected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
