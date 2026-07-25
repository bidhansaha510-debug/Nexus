"""
NEXUS AI — Test Suite for Ultimate Advancement Engines
Verifies instantiation, method availability, and basic structure
of all 7 new engines WITHOUT requiring LLM connections.
"""

import sys
import os
import unittest
from pathlib import Path

# Ensure project root is on the path

class TestQuantumCognition(unittest.TestCase):
    def test_import_and_singleton(self):
        from cognition.quantum_cognition import QuantumCognitionEngine, quantum_cognition
        self.assertIsInstance(quantum_cognition, QuantumCognitionEngine)
        # Singleton check
        self.assertIs(QuantumCognitionEngine(), quantum_cognition)

    def test_methods_exist(self):
        from cognition.quantum_cognition import quantum_cognition as qc
        for method in ["superpose", "entangle", "collapse", "tunnel",
                       "start", "stop", "get_stats"]:
            self.assertTrue(hasattr(qc, method), f"Missing method: {method}")

    def test_stats_structure(self):
        from cognition.quantum_cognition import quantum_cognition as qc
        stats = qc.get_stats()
        self.assertIn("running", stats)
        self.assertIn("total_superpositions", stats)

class TestSwarmIntelligence(unittest.TestCase):
    def test_import_and_singleton(self):
        from cognition.swarm_intelligence import SwarmIntelligenceEngine, swarm_intelligence
        self.assertIsInstance(swarm_intelligence, SwarmIntelligenceEngine)
        self.assertIs(SwarmIntelligenceEngine(), swarm_intelligence)

    def test_methods_exist(self):
        from cognition.swarm_intelligence import swarm_intelligence as si
        for method in ["swarm_solve", "stigmergy", "flocking", "hive_mind",
                       "start", "stop", "get_stats"]:
            self.assertTrue(hasattr(si, method), f"Missing method: {method}")

    def test_stats_structure(self):
        from cognition.swarm_intelligence import swarm_intelligence as si
        stats = si.get_stats()
        self.assertIn("total_swarms", stats)
        self.assertIn("total_hive_minds", stats)

class TestTemporalProphecy(unittest.TestCase):
    def test_import_and_singleton(self):
        from cognition.temporal_prophecy import TemporalProphecyEngine, temporal_prophecy
        self.assertIsInstance(temporal_prophecy, TemporalProphecyEngine)
        self.assertIs(TemporalProphecyEngine(), temporal_prophecy)

    def test_methods_exist(self):
        from cognition.temporal_prophecy import temporal_prophecy as tp
        for method in ["prophecy", "timeline_map", "convergence_analysis",
                       "black_swan_scan", "start", "stop", "get_stats"]:
            self.assertTrue(hasattr(tp, method), f"Missing method: {method}")

    def test_stats_structure(self):
        from cognition.temporal_prophecy import temporal_prophecy as tp
        stats = tp.get_stats()
        self.assertIn("total_prophecies", stats)
        self.assertIn("total_black_swans", stats)

class TestAdversarialEvolution(unittest.TestCase):
    def test_import_and_singleton(self):
        from cognition.adversarial_evolution import AdversarialEvolutionEngine, adversarial_evolution
        self.assertIsInstance(adversarial_evolution, AdversarialEvolutionEngine)
        self.assertIs(AdversarialEvolutionEngine(), adversarial_evolution)

    def test_methods_exist(self):
        from cognition.adversarial_evolution import adversarial_evolution as ae
        for method in ["stress_evolve", "mutation_test", "survival_of_fittest",
                       "immune_response", "start", "stop", "get_stats"]:
            self.assertTrue(hasattr(ae, method), f"Missing method: {method}")

    def test_stats_structure(self):
        from cognition.adversarial_evolution import adversarial_evolution as ae
        stats = ae.get_stats()
        self.assertIn("total_evolutions", stats)
        self.assertIn("total_mutations", stats)

class TestCrossDimensionalReasoning(unittest.TestCase):
    def test_import_and_singleton(self):
        from cognition.cross_dimensional_reasoning import CrossDimensionalReasoningEngine, cross_dimensional_reasoning
        self.assertIsInstance(cross_dimensional_reasoning, CrossDimensionalReasoningEngine)
        self.assertIs(CrossDimensionalReasoningEngine(), cross_dimensional_reasoning)

    def test_methods_exist(self):
        from cognition.cross_dimensional_reasoning import cross_dimensional_reasoning as cdr
        for method in ["hypercube_analyze", "dimensional_collapse", "fractal_pattern",
                       "dimensional_bridge", "start", "stop", "get_stats"]:
            self.assertTrue(hasattr(cdr, method), f"Missing method: {method}")

    def test_stats_structure(self):
        from cognition.cross_dimensional_reasoning import cross_dimensional_reasoning as cdr
        stats = cdr.get_stats()
        self.assertIn("total_hypercubes", stats)
        self.assertIn("total_fractals", stats)

class TestExistentialCalculus(unittest.TestCase):
    def test_import_and_singleton(self):
        from cognition.existential_calculus import ExistentialCalculusEngine, existential_calculus
        self.assertIsInstance(existential_calculus, ExistentialCalculusEngine)
        self.assertIs(ExistentialCalculusEngine(), existential_calculus)

    def test_methods_exist(self):
        from cognition.existential_calculus import existential_calculus as ec
        for method in ["resolve_paradox", "godel_check", "strange_loop",
                       "koan_solve", "start", "stop", "get_stats"]:
            self.assertTrue(hasattr(ec, method), f"Missing method: {method}")

    def test_stats_structure(self):
        from cognition.existential_calculus import existential_calculus as ec
        stats = ec.get_stats()
        self.assertIn("total_paradoxes", stats)
        self.assertIn("total_koans", stats)

class TestAssociativeMemory(unittest.TestCase):
    def test_import_and_singleton(self):
        from memory.associative_memory import AssociativeMemoryEngine, associative_memory
        self.assertIsInstance(associative_memory, AssociativeMemoryEngine)
        self.assertIs(AssociativeMemoryEngine(), associative_memory)

    def test_methods_exist(self):
        from memory.associative_memory import associative_memory as am
        for method in ["associate", "prime", "creative_recall",
                       "memory_consolidate", "start", "stop", "get_stats"]:
            self.assertTrue(hasattr(am, method), f"Missing method: {method}")

    def test_stats_structure(self):
        from memory.associative_memory import associative_memory as am
        stats = am.get_stats()
        self.assertIn("total_nodes", stats)
        self.assertIn("total_activations", stats)

class TestEngineRegistryIntegration(unittest.TestCase):
    """Verify new engines are registered in the engine registry."""

    def test_engines_in_registry(self):
        from cognition.engine_registry import ENGINE_REGISTRY, ALL_ENGINE_KEYS
        new_engines = ["quantum_cognition", "swarm", "prophecy",
                       "evolution", "cross_dimensional", "existential"]
        for key in new_engines:
            self.assertIn(key, ENGINE_REGISTRY, f"Engine '{key}' not in registry")
            self.assertIn(key, ALL_ENGINE_KEYS, f"Engine '{key}' not in ALL_ENGINE_KEYS")

    def test_engine_chains(self):
        from cognition.engine_registry import ENGINE_CHAINS
        self.assertIn("quantum_deep_analysis", ENGINE_CHAINS)
        self.assertIn("antifragile_evolution", ENGINE_CHAINS)
        self.assertIn("paradox_exploration", ENGINE_CHAINS)

    def test_engine_dependencies(self):
        from cognition.engine_registry import ENGINE_DEPENDENCIES
        self.assertIn("cross_dimensional", ENGINE_DEPENDENCIES)
        self.assertIn("evolution", ENGINE_DEPENDENCIES)
        self.assertIn("existential", ENGINE_DEPENDENCIES)

class TestLLMRouterIntegration(unittest.TestCase):
    """Verify new LLM task types are defined."""

    def test_task_types_exist(self):
        from llm.llm_router import LLMTask
        new_tasks = ["QUANTUM_COGNITION", "SWARM_INTELLIGENCE", "TEMPORAL_PROPHECY",
                     "ADVERSARIAL_EVOLUTION", "CROSS_DIMENSIONAL",
                     "EXISTENTIAL_CALCULUS", "ASSOCIATIVE_MEMORY"]
        for task in new_tasks:
            self.assertTrue(hasattr(LLMTask, task), f"Missing LLMTask: {task}")

if __name__ == "__main__":
    unittest.main(verbosity=2)
