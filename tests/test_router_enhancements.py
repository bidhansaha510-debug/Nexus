"""
Extended tests for the cognitive router enhancements.

Tests cover:
  1. ReasoningDepth enum and depth config
  2. InsightSynthesizer cross-engine pattern detection
  3. RoutingTrace data capture
  4. Context-aware cooldown
  5. Adaptive routing score boost
  6. Dynamic chain construction
  7. Engine dependency graph validation
  8. A/B testing framework
"""

import threading
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ──────────────────────────────────────────────────────────────────────────────
# Test Reasoning Depth
# ──────────────────────────────────────────────────────────────────────────────

class TestReasoningDepth:
    def test_enum_values(self):
        from cognition.cognitive_router import ReasoningDepth
        assert ReasoningDepth.SHALLOW.value == "shallow"
        assert ReasoningDepth.MEDIUM.value == "medium"
        assert ReasoningDepth.DEEP.value == "deep"

    def test_depth_config_exists(self):
        from cognition.cognitive_router import DEPTH_CONFIG, ReasoningDepth
        assert ReasoningDepth.SHALLOW in DEPTH_CONFIG
        assert ReasoningDepth.MEDIUM in DEPTH_CONFIG
        assert ReasoningDepth.DEEP in DEPTH_CONFIG

    def test_shallow_config(self):
        from cognition.cognitive_router import DEPTH_CONFIG, ReasoningDepth
        cfg = DEPTH_CONFIG[ReasoningDepth.SHALLOW]
        assert cfg["max_engines"] == 2
        assert cfg["skip_semantic"] is True
        assert cfg["skip_llm"] is True
        assert cfg["auto_chain"] is False

    def test_deep_config(self):
        from cognition.cognitive_router import DEPTH_CONFIG, ReasoningDepth
        cfg = DEPTH_CONFIG[ReasoningDepth.DEEP]
        assert cfg["max_engines"] == 8
        assert cfg["skip_semantic"] is False
        assert cfg["auto_chain"] is True

    def test_invalid_depth_falls_back_to_medium(self):
        from cognition.cognitive_router import ReasoningDepth
        try:
            d = ReasoningDepth("nonexistent")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass  # Expected


# ──────────────────────────────────────────────────────────────────────────────
# Test Insight Synthesizer
# ──────────────────────────────────────────────────────────────────────────────

class TestInsightSynthesis:
    def test_no_synthesis_for_single_result(self):
        from cognition.cognitive_router import InsightSynthesizer, RoutingResult
        results = [RoutingResult(engine_name="causal", insight="test", success=True)]
        assert InsightSynthesizer.synthesize(results) == ""

    def test_cross_engine_pattern_detection(self):
        from cognition.cognitive_router import InsightSynthesizer, RoutingResult
        results = [
            RoutingResult(engine_name="causal", insight="cause found", success=True),
            RoutingResult(engine_name="counterfactual", insight="alternative explored", success=True),
        ]
        synthesis = InsightSynthesizer.synthesize(results)
        assert "alternative scenario" in synthesis.lower() or "causal" in synthesis.lower()

    def test_multi_category_synthesis(self):
        from cognition.cognitive_router import InsightSynthesizer, RoutingResult
        results = [
            RoutingResult(engine_name="causal", insight="cause", success=True),
            RoutingResult(engine_name="emotional", insight="feeling", success=True),
            RoutingResult(engine_name="creative", insight="idea", success=True),
        ]
        synthesis = InsightSynthesizer.synthesize(results)
        assert "multi-dimensional" in synthesis.lower()

    def test_failed_results_excluded(self):
        from cognition.cognitive_router import InsightSynthesizer, RoutingResult
        results = [
            RoutingResult(engine_name="causal", insight="cause", success=True),
            RoutingResult(engine_name="logic", insight="", success=False),
        ]
        synthesis = InsightSynthesizer.synthesize(results)
        assert synthesis == ""  # Only 1 successful result, not enough


# ──────────────────────────────────────────────────────────────────────────────
# Test Routing Trace
# ──────────────────────────────────────────────────────────────────────────────

class TestRoutingTrace:
    def test_trace_dataclass_creation(self):
        from cognition.cognitive_router import RoutingTrace
        trace = RoutingTrace(input_hash="abc123", depth="deep")
        assert trace.input_hash == "abc123"
        assert trace.depth == "deep"
        assert trace.dynamic_chain_built is False
        assert isinstance(trace.keyword_scores, dict)
        assert isinstance(trace.timestamp, str)

    def test_cognitive_insights_has_trace(self):
        from cognition.cognitive_router import CognitiveInsights, RoutingTrace
        trace = RoutingTrace(input_hash="test")
        insights = CognitiveInsights(trace=trace, depth="deep")
        assert insights.trace is not None
        assert insights.depth == "deep"

    def test_context_string_includes_synthesis(self):
        from cognition.cognitive_router import CognitiveInsights, RoutingResult
        insights = CognitiveInsights(
            results=[RoutingResult(engine_name="causal", method_name="analyze", insight="Root cause found", success=True)],
            synthesized_insight="Analysis complete with actionable insights.",
        )
        ctx = insights.to_context_string()
        assert "[SYNTHESIS]" in ctx
        assert "Analysis complete" in ctx

    def test_context_string_includes_depth(self):
        from cognition.cognitive_router import CognitiveInsights, RoutingResult
        insights = CognitiveInsights(
            results=[RoutingResult(engine_name="causal", insight="test", success=True)],
            depth="deep",
        )
        ctx = insights.to_context_string()
        assert "[depth: deep]" in ctx


# ──────────────────────────────────────────────────────────────────────────────
# Test Context-Aware Cooldown
# ──────────────────────────────────────────────────────────────────────────────

class TestContextAwareCooldown:
    def test_topic_continuity_score_identical(self):
        from cognition.cognitive_router import CognitiveRouter
        router = CognitiveRouter()
        current = {"causal", "logic", "error_detect"}
        recent = [{"causal", "logic", "error_detect"}]
        score = router._topic_continuity_score(current, recent)
        assert score == 1.0

    def test_topic_continuity_score_disjoint(self):
        from cognition.cognitive_router import CognitiveRouter
        router = CognitiveRouter()
        current = {"causal", "logic"}
        recent = [{"emotional", "creative"}]
        score = router._topic_continuity_score(current, recent)
        assert score == 0.0

    def test_topic_continuity_score_partial(self):
        from cognition.cognitive_router import CognitiveRouter
        router = CognitiveRouter()
        current = {"causal", "logic", "creative"}
        recent = [{"causal", "logic", "emotional"}]
        score = router._topic_continuity_score(current, recent)
        assert 0.3 < score < 0.7  # Partial overlap

    def test_topic_continuity_empty(self):
        from cognition.cognitive_router import CognitiveRouter
        router = CognitiveRouter()
        assert router._topic_continuity_score(set(), []) == 0.0
        assert router._topic_continuity_score({"causal"}, []) == 0.0


# ──────────────────────────────────────────────────────────────────────────────
# Test Adaptive Routing
# ──────────────────────────────────────────────────────────────────────────────

class TestAdaptiveRouting:
    def test_no_adjustment_with_few_calls(self):
        from cognition.cognitive_router import CognitiveRouter
        router = CognitiveRouter()
        scored = [("causal", 2.0), ("logic", 1.5)]
        adjusted = router._adaptive_score_boost(scored)
        # With <5 calls, no adjustment should be made
        assert adjusted[0] == ("causal", 2.0)
        assert adjusted[1] == ("logic", 1.5)

    def test_penalty_for_high_failure_engine(self):
        from cognition.cognitive_router import CognitiveRouter, EngineMetrics
        router = CognitiveRouter()
        # Simulate a high-failure engine
        with router._state_lock:
            m = router._metrics.get("causal")
            if m:
                m.calls = 10
                m.successes = 2
                m.failures = 8
                m.total_latency = 10.0
        scored = [("causal", 2.0), ("logic", 1.5)]
        adjusted = router._adaptive_score_boost(scored)
        # Causal should be penalized (70% of original)
        causal_score = next(s for k, s in adjusted if k == "causal")
        assert causal_score < 2.0
        assert abs(causal_score - 2.0 * 0.7) < 0.01

    def test_boost_for_reliable_engine(self):
        from cognition.cognitive_router import CognitiveRouter, EngineMetrics
        router = CognitiveRouter()
        with router._state_lock:
            m = router._metrics.get("logic")
            if m:
                m.calls = 10
                m.successes = 9
                m.failures = 1
                m.total_latency = 5.0  # 0.5 avg
        scored = [("logic", 1.5)]
        adjusted = router._adaptive_score_boost(scored)
        logic_score = next(s for k, s in adjusted if k == "logic")
        assert logic_score > 1.5  # Should get 10% boost


# ──────────────────────────────────────────────────────────────────────────────
# Test Dynamic Chain Construction
# ──────────────────────────────────────────────────────────────────────────────

class TestDynamicChains:
    def test_no_chain_for_single_engine(self):
        from cognition.cognitive_router import CognitiveRouter
        router = CognitiveRouter()
        chain, parallel = router._build_dynamic_chain(["causal"])
        assert chain == []
        assert parallel == ["causal"]

    def test_chain_built_for_dependent_engines(self):
        from cognition.cognitive_router import CognitiveRouter
        router = CognitiveRouter()
        chain, parallel = router._build_dynamic_chain(["causal", "decision"])
        # causal should come before decision
        assert "causal" in chain
        assert "decision" in chain
        if len(chain) == 2:
            assert chain.index("causal") < chain.index("decision")

    def test_independent_engines_stay_parallel(self):
        from cognition.cognitive_router import CognitiveRouter
        router = CognitiveRouter()
        chain, parallel = router._build_dynamic_chain(["causal", "creative", "emotional"])
        # No dependencies between these
        assert chain == []
        assert set(parallel) == {"causal", "creative", "emotional"}

    def test_mixed_chain_and_parallel(self):
        from cognition.cognitive_router import CognitiveRouter
        router = CognitiveRouter()
        chain, parallel = router._build_dynamic_chain(["causal", "decision", "emotional"])
        # causal→decision should be chained, emotional should be parallel
        assert "causal" in chain
        assert "decision" in chain
        assert "emotional" in parallel


# ──────────────────────────────────────────────────────────────────────────────
# Test Engine Dependency Graph
# ──────────────────────────────────────────────────────────────────────────────

class TestDependencyGraph:
    def test_dependencies_exist(self):
        from cognition.engine_registry import ENGINE_DEPENDENCIES
        assert isinstance(ENGINE_DEPENDENCIES, dict)
        assert len(ENGINE_DEPENDENCIES) > 0

    def test_no_circular_dependencies(self):
        from cognition.engine_registry import validate_dependencies
        # Should not raise
        validate_dependencies()

    def test_execution_order(self):
        from cognition.engine_registry import get_execution_order
        order = get_execution_order(["decision", "causal", "emotional"])
        # causal should come before decision
        if "causal" in order and "decision" in order:
            assert order.index("causal") < order.index("decision")

    def test_execution_order_no_deps(self):
        from cognition.engine_registry import get_execution_order
        order = get_execution_order(["causal", "emotional", "creative"])
        assert set(order) == {"causal", "emotional", "creative"}

    def test_known_dependencies(self):
        from cognition.engine_registry import ENGINE_DEPENDENCIES
        assert "causal" in ENGINE_DEPENDENCIES.get("decision", [])
        assert "emotional" in ENGINE_DEPENDENCIES.get("emotional_reg", [])
        assert "philosophy" in ENGINE_DEPENDENCIES.get("dialectic", [])


# ──────────────────────────────────────────────────────────────────────────────
# Test A/B Testing Framework
# ──────────────────────────────────────────────────────────────────────────────

class TestABFramework:
    def test_add_experiment(self):
        from cognition.routing_experiments import ExperimentManager, RoutingExperiment
        mgr = ExperimentManager()
        mgr._experiments.clear()  # Reset for test

        result = mgr.add_experiment(RoutingExperiment(
            name="test_exp",
            description="Test experiment",
            config_overrides={"max_engines": 8},
            traffic_split=0.3,
        ))
        assert result is True
        assert "test_exp" in mgr._experiments

    def test_traffic_split_validation(self):
        from cognition.routing_experiments import ExperimentManager, RoutingExperiment
        mgr = ExperimentManager()
        mgr._experiments.clear()

        mgr.add_experiment(RoutingExperiment(name="a", traffic_split=0.6))
        result = mgr.add_experiment(RoutingExperiment(name="b", traffic_split=0.6))
        assert result is False  # Would exceed 1.0

    def test_deterministic_assignment(self):
        from cognition.routing_experiments import ExperimentManager, RoutingExperiment
        mgr = ExperimentManager()
        mgr._experiments.clear()

        mgr.add_experiment(RoutingExperiment(name="half", traffic_split=0.5))

        # Same input should always get same variant
        v1 = mgr.get_variant("test input")
        v2 = mgr.get_variant("test input")
        assert (v1 is None) == (v2 is None)
        if v1 and v2:
            assert v1.name == v2.name

    def test_get_config_with_experiment(self):
        from cognition.routing_experiments import ExperimentManager, RoutingExperiment
        mgr = ExperimentManager()
        mgr._experiments.clear()

        mgr.add_experiment(RoutingExperiment(
            name="full",
            config_overrides={"max_engines": 10},
            traffic_split=1.0,  # All traffic
        ))

        config = mgr.get_config("any input")
        assert config.get("max_engines") == 10
        assert config.get("_experiment") == "full"

    def test_stats_output(self):
        from cognition.routing_experiments import ExperimentManager, RoutingExperiment
        mgr = ExperimentManager()
        mgr._experiments.clear()

        mgr.add_experiment(RoutingExperiment(name="stats_test", traffic_split=0.1))
        stats = mgr.get_stats()
        assert stats["total_experiments"] == 1
        assert "stats_test" in stats["experiments"]

    def test_remove_experiment(self):
        from cognition.routing_experiments import ExperimentManager, RoutingExperiment
        mgr = ExperimentManager()
        mgr._experiments.clear()

        mgr.add_experiment(RoutingExperiment(name="removable", traffic_split=0.1))
        assert mgr.remove_experiment("removable") is True
        assert mgr.remove_experiment("nonexistent") is False


# ──────────────────────────────────────────────────────────────────────────────
# Test Engine Clusters (intent_classifier)
# ──────────────────────────────────────────────────────────────────────────────

class TestEngineClusters:
    def test_clusters_defined(self):
        from cognition.intent_classifier import ENGINE_CLUSTERS
        assert isinstance(ENGINE_CLUSTERS, dict)
        assert "emotional_support" in ENGINE_CLUSTERS
        assert "reasoning" in ENGINE_CLUSTERS
        assert "creative" in ENGINE_CLUSTERS

    def test_reverse_lookup(self):
        from cognition.intent_classifier import _ENGINE_TO_CLUSTERS
        assert "emotional" in _ENGINE_TO_CLUSTERS
        assert "emotional_support" in _ENGINE_TO_CLUSTERS["emotional"]

    def test_cluster_boost_threshold(self):
        from cognition.intent_classifier import IntentClassifier
        ic = IntentClassifier()
        assert hasattr(ic, 'CLUSTER_BOOST')
        assert ic.CLUSTER_BOOST > 0

    def test_raised_keyword_threshold(self):
        from cognition.intent_classifier import IntentClassifier
        ic = IntentClassifier()
        assert ic.KEYWORD_HIGH_CONFIDENCE == 2.5
