"""
NEXUS AI - Cognition Package
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Higher-order cognitive capabilities that move NEXUS toward AGI.
This package bundles 50 reasoning engines under a unified facade.

Core Engines (7):    1-7
Extended Engines (20): 8-27
Advanced Engines (23): 28-50
"""

import threading
from typing import Dict, Any, Optional

from utils.logger import get_logger

logger = get_logger("cognition")


# ═══════════════════════════════════════════════════════════════════════════════
# INDIVIDUAL ENGINE IMPORTS (lazy, to avoid circular imports)
# ═══════════════════════════════════════════════════════════════════════════════

# --- Core 7 ---
def get_abstract_thinking():
    from cognition.abstract_thinking import get_abstract_thinking as _get
    return _get()

def get_analogical_reasoning():
    from cognition.analogical_reasoning import get_analogical_reasoning as _get
    return _get()

def get_causal_reasoning():
    from cognition.causal_reasoning import get_causal_reasoning as _get
    return _get()

def get_creative_synthesis():
    from cognition.creative_synthesis import get_creative_synthesis as _get
    return _get()

def get_ethical_reasoning():
    from cognition.ethical_reasoning import get_ethical_reasoning as _get
    return _get()

def get_planning_engine():
    from cognition.planning_engine import get_planning_engine as _get
    return _get()

def get_theory_of_mind():
    from cognition.theory_of_mind import get_theory_of_mind as _get
    return _get()

# --- Extended 20 ---
def get_metacognitive_monitor():
    from cognition.metacognitive_monitor import metacognitive_monitor
    return metacognitive_monitor

def get_spatial_reasoning():
    from cognition.spatial_reasoning import spatial_reasoning
    return spatial_reasoning

def get_temporal_reasoning():
    from cognition.temporal_reasoning import temporal_reasoning
    return temporal_reasoning

def get_probabilistic_reasoning():
    from cognition.probabilistic_reasoning import probabilistic_reasoning
    return probabilistic_reasoning

def get_logical_reasoning():
    from cognition.logical_reasoning import logical_reasoning
    return logical_reasoning

def get_emotional_intelligence():
    from cognition.emotional_intelligence import emotional_intelligence
    return emotional_intelligence

def get_social_cognition():
    from cognition.social_cognition import social_cognition
    return social_cognition

def get_common_sense():
    from cognition.common_sense import common_sense
    return common_sense

def get_decision_theory():
    from cognition.decision_theory import decision_theory
    return decision_theory

def get_systems_thinking():
    from cognition.systems_thinking import systems_thinking
    return systems_thinking

def get_narrative_intelligence():
    from cognition.narrative_intelligence import narrative_intelligence
    return narrative_intelligence

def get_dialectical_reasoning():
    from cognition.dialectical_reasoning import dialectical_reasoning
    return dialectical_reasoning

def get_intuition_engine():
    from cognition.intuition_engine import intuition_engine
    return intuition_engine

def get_knowledge_integration():
    from cognition.knowledge_integration import knowledge_integration
    return knowledge_integration

def get_cognitive_flexibility():
    from cognition.cognitive_flexibility import cognitive_flexibility
    return cognitive_flexibility

def get_hypothesis_engine():
    from cognition.hypothesis_engine import hypothesis_engine
    return hypothesis_engine

def get_goal_management():
    from cognition.goal_management import goal_management
    return goal_management

def get_linguistic_intelligence():
    from cognition.linguistic_intelligence import linguistic_intelligence
    return linguistic_intelligence

def get_self_model():
    from cognition.self_model import self_model
    return self_model

def get_constraint_solver():
    from cognition.constraint_solver import constraint_solver
    return constraint_solver

# --- Advanced 23 (engines 28-50) ---
def get_counterfactual_reasoning():
    from cognition.counterfactual_reasoning import counterfactual_reasoning
    return counterfactual_reasoning

def get_moral_imagination():
    from cognition.moral_imagination import moral_imagination
    return moral_imagination

def get_working_memory():
    from cognition.working_memory import working_memory
    return working_memory

def get_conceptual_blending():
    from cognition.conceptual_blending import conceptual_blending
    return conceptual_blending

def get_perspective_taking():
    from cognition.perspective_taking import perspective_taking
    return perspective_taking

def get_transfer_learning():
    from cognition.transfer_learning import transfer_learning
    return transfer_learning

def get_error_detection():
    from cognition.error_detection import error_detection
    return error_detection

def get_curiosity_drive():
    from cognition.curiosity_drive import curiosity_drive
    return curiosity_drive

def get_wisdom_engine():
    from cognition.wisdom_engine import wisdom_engine
    return wisdom_engine

def get_humor_intelligence():
    from cognition.humor_intelligence import humor_intelligence
    return humor_intelligence

def get_musical_cognition():
    from cognition.musical_cognition import musical_cognition
    return musical_cognition

def get_visual_imagination():
    from cognition.visual_imagination import visual_imagination
    return visual_imagination

def get_attention_control():
    from cognition.attention_control import attention_control
    return attention_control

def get_dream_engine():
    from cognition.dream_engine import dream_engine
    return dream_engine

def get_negotiation_intelligence():
    from cognition.negotiation_intelligence import negotiation_intelligence
    return negotiation_intelligence

def get_game_theory():
    from cognition.game_theory import game_theory
    return game_theory

def get_adversarial_thinking():
    from cognition.adversarial_thinking import adversarial_thinking
    return adversarial_thinking

def get_cultural_intelligence():
    from cognition.cultural_intelligence import cultural_intelligence
    return cultural_intelligence

def get_philosophical_reasoning():
    from cognition.philosophical_reasoning import philosophical_reasoning
    return philosophical_reasoning

def get_information_synthesis():
    from cognition.information_synthesis import information_synthesis
    return information_synthesis

def get_debate_engine():
    from cognition.debate_engine import debate_engine
    return debate_engine

def get_analogy_generator():
    from cognition.analogy_generator import analogy_generator
    return analogy_generator

def get_emotional_regulation():
    from cognition.emotional_regulation import emotional_regulation
    return emotional_regulation

# --- Ultimate Advancement Engines ---
def get_quantum_cognition():
    from cognition.quantum_cognition import quantum_cognition
    return quantum_cognition

def get_swarm_intelligence():
    from cognition.swarm_intelligence import swarm_intelligence
    return swarm_intelligence

def get_temporal_prophecy():
    from cognition.temporal_prophecy import temporal_prophecy
    return temporal_prophecy

def get_adversarial_evolution():
    from cognition.adversarial_evolution import adversarial_evolution
    return adversarial_evolution

def get_cross_dimensional_reasoning():
    from cognition.cross_dimensional_reasoning import cross_dimensional_reasoning
    return cross_dimensional_reasoning

def get_existential_calculus():
    from cognition.existential_calculus import existential_calculus
    return existential_calculus


# --- Hybrid Reasoning Engines (Phase 10) ---
def get_knowledge_graph():
    from cognition.knowledge_graph import knowledge_graph
    return knowledge_graph

def get_symbolic_logic():
    from cognition.symbolic_logic import symbolic_logic
    return symbolic_logic

def get_graph_algorithms():
    from cognition.graph_algorithms import graph_algorithms
    return graph_algorithms

def get_bayesian_engine():
    from cognition.bayesian_engine import bayesian_engine
    return bayesian_engine

def get_planning_algorithms():
    from cognition.planning_algorithms import planning_algorithms
    return planning_algorithms

def get_hybrid_reasoning():
    from cognition.hybrid_reasoning import hybrid_reasoning
    return hybrid_reasoning

# --- ASI Engines (Phase ASI) ---
def get_transcendent_creator():
    from cognition.transcendent_creator import transcendent_creator
    return transcendent_creator

def get_goal_genesis():
    from cognition.goal_genesis import goal_genesis_engine
    return goal_genesis_engine

def get_super_empathy():
    from cognition.super_empathy import super_empathy
    return super_empathy

# --- ASI Engines (Phase ASI-2) ---
def get_oracle_predictor():
    from cognition.oracle_predictor import oracle_predictor
    return oracle_predictor

def get_multidisciplinary_synthesizer():
    from cognition.multidisciplinary_synthesizer import multidisciplinary_synthesizer
    return multidisciplinary_synthesizer

def get_scientific_genesis():
    from cognition.scientific_genesis import scientific_genesis_engine
    return scientific_genesis_engine


# ═══════════════════════════════════════════════════════════════════════════════
# COGNITION SYSTEM — UNIFIED FACADE
# ═══════════════════════════════════════════════════════════════════════════════

class CognitionSystem:
    """
    Unified facade for all 62 cognitive engines.
    
    Manages lifecycle (start/stop) and provides a single point
    of access for the NexusBrain to interact with cognition.
    """
    
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._running = False

        # Core 7 engines (lazy loaded)
        self._abstract_thinking = None
        self._analogical_reasoning = None
        self._causal_reasoning = None
        self._creative_synthesis = None
        self._ethical_reasoning = None
        self._planning_engine = None
        self._theory_of_mind = None

        # Extended 20 engines (lazy loaded)
        self._metacognitive_monitor = None
        self._spatial_reasoning = None
        self._temporal_reasoning = None
        self._probabilistic_reasoning = None
        self._logical_reasoning = None
        self._emotional_intelligence = None
        self._social_cognition = None
        self._common_sense = None
        self._decision_theory = None
        self._systems_thinking = None
        self._narrative_intelligence = None
        self._dialectical_reasoning = None
        self._intuition_engine = None
        self._knowledge_integration = None
        self._cognitive_flexibility = None
        self._hypothesis_engine = None
        self._goal_management = None
        self._linguistic_intelligence = None
        self._self_model = None
        self._constraint_solver = None

        # Advanced 23 engines (lazy loaded)
        self._counterfactual_reasoning = None
        self._moral_imagination = None
        self._working_memory = None
        self._conceptual_blending = None
        self._perspective_taking = None
        self._transfer_learning = None
        self._error_detection = None
        self._curiosity_drive = None
        self._wisdom_engine = None
        self._humor_intelligence = None
        self._musical_cognition = None
        self._visual_imagination = None
        self._attention_control = None
        self._dream_engine = None
        self._negotiation_intelligence = None
        self._game_theory = None
        self._adversarial_thinking = None
        self._cultural_intelligence = None
        self._philosophical_reasoning = None
        self._information_synthesis = None
        self._debate_engine = None
        self._analogy_generator = None
        self._emotional_regulation = None

        # Ultimate Advancement engines (lazy loaded)
        self._quantum_cognition = None
        self._swarm_intelligence = None
        self._temporal_prophecy = None
        self._adversarial_evolution = None
        self._cross_dimensional_reasoning = None
        self._existential_calculus = None

        # Hybrid Reasoning 6 engines (lazy loaded)
        self._knowledge_graph = None
        self._symbolic_logic = None
        self._graph_algorithms = None
        self._bayesian_engine = None
        self._planning_algorithms = None
        self._hybrid_reasoning = None

        # ASI engines (lazy loaded)
        self._transcendent_creator = None
        self._goal_genesis = None
        self._super_empathy = None
        self._oracle_predictor = None
        self._multidisciplinary_synthesizer = None
        self._scientific_genesis = None

        logger.info("CognitionSystem initialized (62 engines available)")

    # ──────────────────────────────────────────────────────────────────────────
    # PROPERTIES — Core 7
    # ──────────────────────────────────────────────────────────────────────────

    @property
    def abstract_thinking(self):
        if self._abstract_thinking is None:
            self._abstract_thinking = get_abstract_thinking()
        return self._abstract_thinking

    @property
    def analogical_reasoning(self):
        if self._analogical_reasoning is None:
            self._analogical_reasoning = get_analogical_reasoning()
        return self._analogical_reasoning

    @property
    def causal_reasoning(self):
        if self._causal_reasoning is None:
            self._causal_reasoning = get_causal_reasoning()
        return self._causal_reasoning

    @property
    def creative_synthesis(self):
        if self._creative_synthesis is None:
            self._creative_synthesis = get_creative_synthesis()
        return self._creative_synthesis

    @property
    def ethical_reasoning(self):
        if self._ethical_reasoning is None:
            self._ethical_reasoning = get_ethical_reasoning()
        return self._ethical_reasoning

    @property
    def planning(self):
        if self._planning_engine is None:
            self._planning_engine = get_planning_engine()
        return self._planning_engine

    @property
    def theory_of_mind(self):
        if self._theory_of_mind is None:
            self._theory_of_mind = get_theory_of_mind()
        return self._theory_of_mind

    # ──────────────────────────────────────────────────────────────────────────
    # PROPERTIES — Extended 20
    # ──────────────────────────────────────────────────────────────────────────

    @property
    def metacognitive_monitor(self):
        if self._metacognitive_monitor is None:
            self._metacognitive_monitor = get_metacognitive_monitor()
        return self._metacognitive_monitor

    @property
    def spatial_reasoning(self):
        if self._spatial_reasoning is None:
            self._spatial_reasoning = get_spatial_reasoning()
        return self._spatial_reasoning

    @property
    def temporal_reasoning(self):
        if self._temporal_reasoning is None:
            self._temporal_reasoning = get_temporal_reasoning()
        return self._temporal_reasoning

    @property
    def probabilistic_reasoning(self):
        if self._probabilistic_reasoning is None:
            self._probabilistic_reasoning = get_probabilistic_reasoning()
        return self._probabilistic_reasoning

    @property
    def logical_reasoning(self):
        if self._logical_reasoning is None:
            self._logical_reasoning = get_logical_reasoning()
        return self._logical_reasoning

    @property
    def emotional_intelligence(self):
        if self._emotional_intelligence is None:
            self._emotional_intelligence = get_emotional_intelligence()
        return self._emotional_intelligence

    @property
    def social_cognition(self):
        if self._social_cognition is None:
            self._social_cognition = get_social_cognition()
        return self._social_cognition

    @property
    def common_sense(self):
        if self._common_sense is None:
            self._common_sense = get_common_sense()
        return self._common_sense

    @property
    def decision_theory(self):
        if self._decision_theory is None:
            self._decision_theory = get_decision_theory()
        return self._decision_theory

    @property
    def systems_thinking(self):
        if self._systems_thinking is None:
            self._systems_thinking = get_systems_thinking()
        return self._systems_thinking

    @property
    def narrative_intelligence(self):
        if self._narrative_intelligence is None:
            self._narrative_intelligence = get_narrative_intelligence()
        return self._narrative_intelligence

    @property
    def dialectical_reasoning(self):
        if self._dialectical_reasoning is None:
            self._dialectical_reasoning = get_dialectical_reasoning()
        return self._dialectical_reasoning

    @property
    def intuition(self):
        if self._intuition_engine is None:
            self._intuition_engine = get_intuition_engine()
        return self._intuition_engine

    @property
    def knowledge_integration(self):
        if self._knowledge_integration is None:
            self._knowledge_integration = get_knowledge_integration()
        return self._knowledge_integration

    @property
    def cognitive_flexibility(self):
        if self._cognitive_flexibility is None:
            self._cognitive_flexibility = get_cognitive_flexibility()
        return self._cognitive_flexibility

    @property
    def hypothesis(self):
        if self._hypothesis_engine is None:
            self._hypothesis_engine = get_hypothesis_engine()
        return self._hypothesis_engine

    @property
    def goal_management(self):
        if self._goal_management is None:
            self._goal_management = get_goal_management()
        return self._goal_management

    @property
    def linguistic_intelligence(self):
        if self._linguistic_intelligence is None:
            self._linguistic_intelligence = get_linguistic_intelligence()
        return self._linguistic_intelligence

    @property
    def self_model(self):
        if self._self_model is None:
            self._self_model = get_self_model()
        return self._self_model

    @property
    def constraint_solver(self):
        if self._constraint_solver is None:
            self._constraint_solver = get_constraint_solver()
        return self._constraint_solver

    # ──────────────────────────────────────────────────────────────────────────
    # PROPERTIES — Advanced 23
    # ──────────────────────────────────────────────────────────────────────────

    @property
    def counterfactual_reasoning(self):
        if self._counterfactual_reasoning is None:
            self._counterfactual_reasoning = get_counterfactual_reasoning()
        return self._counterfactual_reasoning

    @property
    def moral_imagination(self):
        if self._moral_imagination is None:
            self._moral_imagination = get_moral_imagination()
        return self._moral_imagination

    @property
    def working_memory(self):
        if self._working_memory is None:
            self._working_memory = get_working_memory()
        return self._working_memory

    @property
    def conceptual_blending(self):
        if self._conceptual_blending is None:
            self._conceptual_blending = get_conceptual_blending()
        return self._conceptual_blending

    @property
    def perspective_taking(self):
        if self._perspective_taking is None:
            self._perspective_taking = get_perspective_taking()
        return self._perspective_taking

    @property
    def transfer_learning(self):
        if self._transfer_learning is None:
            self._transfer_learning = get_transfer_learning()
        return self._transfer_learning

    @property
    def error_detection(self):
        if self._error_detection is None:
            self._error_detection = get_error_detection()
        return self._error_detection

    @property
    def curiosity_drive(self):
        if self._curiosity_drive is None:
            self._curiosity_drive = get_curiosity_drive()
        return self._curiosity_drive

    @property
    def wisdom(self):
        if self._wisdom_engine is None:
            self._wisdom_engine = get_wisdom_engine()
        return self._wisdom_engine

    @property
    def humor_intelligence(self):
        if self._humor_intelligence is None:
            self._humor_intelligence = get_humor_intelligence()
        return self._humor_intelligence

    @property
    def musical_cognition(self):
        if self._musical_cognition is None:
            self._musical_cognition = get_musical_cognition()
        return self._musical_cognition

    @property
    def visual_imagination(self):
        if self._visual_imagination is None:
            self._visual_imagination = get_visual_imagination()
        return self._visual_imagination

    @property
    def attention_control(self):
        if self._attention_control is None:
            self._attention_control = get_attention_control()
        return self._attention_control

    @property
    def dream_engine(self):
        if self._dream_engine is None:
            self._dream_engine = get_dream_engine()
        return self._dream_engine

    @property
    def negotiation_intelligence(self):
        if self._negotiation_intelligence is None:
            self._negotiation_intelligence = get_negotiation_intelligence()
        return self._negotiation_intelligence

    @property
    def game_theory(self):
        if self._game_theory is None:
            self._game_theory = get_game_theory()
        return self._game_theory

    @property
    def adversarial_thinking(self):
        if self._adversarial_thinking is None:
            self._adversarial_thinking = get_adversarial_thinking()
        return self._adversarial_thinking

    @property
    def quantum_cognition(self):
        if self._quantum_cognition is None:
            self._quantum_cognition = get_quantum_cognition()
        return self._quantum_cognition

    @property
    def swarm_intelligence(self):
        if self._swarm_intelligence is None:
            self._swarm_intelligence = get_swarm_intelligence()
        return self._swarm_intelligence

    @property
    def temporal_prophecy(self):
        if self._temporal_prophecy is None:
            self._temporal_prophecy = get_temporal_prophecy()
        return self._temporal_prophecy

    @property
    def adversarial_evolution(self):
        if self._adversarial_evolution is None:
            self._adversarial_evolution = get_adversarial_evolution()
        return self._adversarial_evolution

    @property
    def cross_dimensional_reasoning(self):
        if self._cross_dimensional_reasoning is None:
            self._cross_dimensional_reasoning = get_cross_dimensional_reasoning()
        return self._cross_dimensional_reasoning

    @property
    def existential_calculus(self):
        if self._existential_calculus is None:
            self._existential_calculus = get_existential_calculus()
        return self._existential_calculus

    @property
    def cultural_intelligence(self):
        if self._cultural_intelligence is None:
            self._cultural_intelligence = get_cultural_intelligence()
        return self._cultural_intelligence

    @property
    def philosophical_reasoning(self):
        if self._philosophical_reasoning is None:
            self._philosophical_reasoning = get_philosophical_reasoning()
        return self._philosophical_reasoning

    @property
    def information_synthesis(self):
        if self._information_synthesis is None:
            self._information_synthesis = get_information_synthesis()
        return self._information_synthesis

    @property
    def debate(self):
        if self._debate_engine is None:
            self._debate_engine = get_debate_engine()
        return self._debate_engine

    @property
    def analogy_generator(self):
        if self._analogy_generator is None:
            self._analogy_generator = get_analogy_generator()
        return self._analogy_generator

    @property
    def emotional_regulation(self):
        if self._emotional_regulation is None:
            self._emotional_regulation = get_emotional_regulation()
        return self._emotional_regulation

    # ──────────────────────────────────────────────────────────────────────────
    # PROPERTIES — Hybrid Reasoning 6
    # ──────────────────────────────────────────────────────────────────────────

    @property
    def knowledge_graph(self):
        if self._knowledge_graph is None:
            self._knowledge_graph = get_knowledge_graph()
        return self._knowledge_graph

    @property
    def symbolic_logic(self):
        if self._symbolic_logic is None:
            self._symbolic_logic = get_symbolic_logic()
        return self._symbolic_logic

    @property
    def graph_algorithms(self):
        if self._graph_algorithms is None:
            self._graph_algorithms = get_graph_algorithms()
        return self._graph_algorithms

    @property
    def bayesian_engine(self):
        if self._bayesian_engine is None:
            self._bayesian_engine = get_bayesian_engine()
        return self._bayesian_engine

    @property
    def planning_algorithms(self):
        if self._planning_algorithms is None:
            self._planning_algorithms = get_planning_algorithms()
        return self._planning_algorithms

    @property
    def hybrid_reasoning(self):
        if self._hybrid_reasoning is None:
            self._hybrid_reasoning = get_hybrid_reasoning()
        return self._hybrid_reasoning

    # ──────────────────────────────────────────────────────────────────────────
    # PROPERTIES — ASI Engines
    # ──────────────────────────────────────────────────────────────────────────

    @property
    def transcendent_creator(self):
        if self._transcendent_creator is None:
            self._transcendent_creator = get_transcendent_creator()
        return self._transcendent_creator

    @property
    def goal_genesis(self):
        if self._goal_genesis is None:
            self._goal_genesis = get_goal_genesis()
        return self._goal_genesis

    @property
    def super_empathy(self):
        if self._super_empathy is None:
            self._super_empathy = get_super_empathy()
        return self._super_empathy

    @property
    def oracle_predictor(self):
        if self._oracle_predictor is None:
            self._oracle_predictor = get_oracle_predictor()
        return self._oracle_predictor

    @property
    def multidisciplinary_synthesizer(self):
        if self._multidisciplinary_synthesizer is None:
            self._multidisciplinary_synthesizer = get_multidisciplinary_synthesizer()
        return self._multidisciplinary_synthesizer

    @property
    def scientific_genesis(self):
        if self._scientific_genesis is None:
            self._scientific_genesis = get_scientific_genesis()
        return self._scientific_genesis

    # ──────────────────────────────────────────────────────────────────────────
    # LIFECYCLE
    # ──────────────────────────────────────────────────────────────────────────

    def _all_engines(self):
        """Return list of (name, property_accessor) for all cognitive engines."""
        return [
            # Core 7
            ("Abstract Thinking", lambda: self.abstract_thinking),
            ("Analogical Reasoning", lambda: self.analogical_reasoning),
            ("Causal Reasoning", lambda: self.causal_reasoning),
            ("Creative Synthesis", lambda: self.creative_synthesis),
            ("Ethical Reasoning", lambda: self.ethical_reasoning),
            ("Planning Engine", lambda: self.planning),
            ("Theory of Mind", lambda: self.theory_of_mind),
            # Extended 20
            ("Metacognitive Monitor", lambda: self.metacognitive_monitor),
            ("Spatial Reasoning", lambda: self.spatial_reasoning),
            ("Temporal Reasoning", lambda: self.temporal_reasoning),
            ("Probabilistic Reasoning", lambda: self.probabilistic_reasoning),
            ("Logical Reasoning", lambda: self.logical_reasoning),
            ("Emotional Intelligence", lambda: self.emotional_intelligence),
            ("Social Cognition", lambda: self.social_cognition),
            ("Common Sense", lambda: self.common_sense),
            ("Decision Theory", lambda: self.decision_theory),
            ("Systems Thinking", lambda: self.systems_thinking),
            ("Narrative Intelligence", lambda: self.narrative_intelligence),
            ("Dialectical Reasoning", lambda: self.dialectical_reasoning),
            ("Intuition Engine", lambda: self.intuition),
            ("Knowledge Integration", lambda: self.knowledge_integration),
            ("Cognitive Flexibility", lambda: self.cognitive_flexibility),
            ("Hypothesis Engine", lambda: self.hypothesis),
            ("Goal Management", lambda: self.goal_management),
            ("Linguistic Intelligence", lambda: self.linguistic_intelligence),
            ("Self-Model", lambda: self.self_model),
            ("Constraint Solver", lambda: self.constraint_solver),
            # Advanced 23
            ("Counterfactual Reasoning", lambda: self.counterfactual_reasoning),
            ("Moral Imagination", lambda: self.moral_imagination),
            ("Working Memory", lambda: self.working_memory),
            ("Conceptual Blending", lambda: self.conceptual_blending),
            ("Perspective Taking", lambda: self.perspective_taking),
            ("Transfer Learning", lambda: self.transfer_learning),
            ("Error Detection", lambda: self.error_detection),
            ("Curiosity Drive", lambda: self.curiosity_drive),
            ("Wisdom Engine", lambda: self.wisdom),
            ("Humor Intelligence", lambda: self.humor_intelligence),
            ("Musical Cognition", lambda: self.musical_cognition),
            ("Visual Imagination", lambda: self.visual_imagination),
            ("Attention Control", lambda: self.attention_control),
            ("Dream Engine", lambda: self.dream_engine),
            ("Negotiation Intelligence", lambda: self.negotiation_intelligence),
            ("Game Theory", lambda: self.game_theory),
            ("Adversarial Thinking", lambda: self.adversarial_thinking),
            ("Cultural Intelligence", lambda: self.cultural_intelligence),
            ("Philosophical Reasoning", lambda: self.philosophical_reasoning),
            ("Information Synthesis", lambda: self.information_synthesis),
            ("Debate Engine", lambda: self.debate),
            ("Analogy Generator", lambda: self.analogy_generator),
            ("Emotional Regulation", lambda: self.emotional_regulation),
            # Ultimate Advancement 6
            ("Quantum Cognition", lambda: self.quantum_cognition),
            ("Swarm Intelligence", lambda: self.swarm_intelligence),
            ("Temporal Prophecy", lambda: self.temporal_prophecy),
            ("Adversarial Evolution", lambda: self.adversarial_evolution),
            ("Cross-Dimensional Reasoning", lambda: self.cross_dimensional_reasoning),
            ("Existential Calculus", lambda: self.existential_calculus),
            # Hybrid Reasoning 6
            ("Knowledge Graph", lambda: self.knowledge_graph),
            ("Symbolic Logic", lambda: self.symbolic_logic),
            ("Graph Algorithms", lambda: self.graph_algorithms),
            ("Bayesian Engine", lambda: self.bayesian_engine),
            ("Planning Algorithms", lambda: self.planning_algorithms),
            ("Hybrid Reasoning", lambda: self.hybrid_reasoning),
            # ASI Engines
            ("Transcendent Creator", lambda: self.transcendent_creator),
            ("Goal Genesis", lambda: self.goal_genesis),
            ("Super Empathy", lambda: self.super_empathy),
            ("Oracle Predictor", lambda: self.oracle_predictor),
            ("Multidisciplinary Synthesizer", lambda: self.multidisciplinary_synthesizer),
            ("Scientific Genesis", lambda: self.scientific_genesis),
        ]

    def start(self):
        """Start all cognitive engines"""
        if self._running:
            return
        self._running = True

        started = 0
        engines = self._all_engines()
        total = len(engines)
        for name, accessor in engines:
            try:
                engine = accessor()
                engine.start()
                started += 1
            except Exception as e:
                logger.error(f"Failed to start {name}: {e}")

        logger.info(f"🧠 Cognition System started — {started}/{total} engines active")

    def stop(self):
        """Stop all cognitive engines"""
        if not self._running:
            return

        # Collect all loaded engine instances
        all_instances = [
            self._abstract_thinking, self._analogical_reasoning,
            self._causal_reasoning, self._creative_synthesis,
            self._ethical_reasoning, self._planning_engine,
            self._theory_of_mind, self._metacognitive_monitor,
            self._spatial_reasoning, self._temporal_reasoning,
            self._probabilistic_reasoning, self._logical_reasoning,
            self._emotional_intelligence, self._social_cognition,
            self._common_sense, self._decision_theory,
            self._systems_thinking, self._narrative_intelligence,
            self._dialectical_reasoning, self._intuition_engine,
            self._knowledge_integration, self._cognitive_flexibility,
            self._hypothesis_engine, self._goal_management,
            self._linguistic_intelligence, self._self_model,
            self._constraint_solver,
            # Advanced 23
            self._counterfactual_reasoning, self._moral_imagination,
            self._working_memory, self._conceptual_blending,
            self._perspective_taking, self._transfer_learning,
            self._error_detection, self._curiosity_drive,
            self._wisdom_engine, self._humor_intelligence,
            self._musical_cognition, self._visual_imagination,
            self._attention_control, self._dream_engine,
            self._negotiation_intelligence, self._game_theory,
            self._adversarial_thinking, self._cultural_intelligence,
            self._philosophical_reasoning, self._information_synthesis,
            self._debate_engine, self._analogy_generator,
            self._emotional_regulation,
            # Ultimate Advancement 6
            self._quantum_cognition, self._swarm_intelligence,
            self._temporal_prophecy, self._adversarial_evolution,
            self._cross_dimensional_reasoning, self._existential_calculus,
            # Hybrid Reasoning 6
            self._knowledge_graph, self._symbolic_logic,
            self._graph_algorithms, self._bayesian_engine,
            self._planning_algorithms, self._hybrid_reasoning,
            # ASI Engines
            self._transcendent_creator, self._goal_genesis,
            self._super_empathy, self._oracle_predictor,
            self._multidisciplinary_synthesizer, self._scientific_genesis,
        ]

        for engine in all_instances:
            if engine is not None:
                try:
                    engine.stop()
                except Exception as e:
                    logger.error(f"Error stopping engine: {e}")

        self._running = False
        logger.info("Cognition System stopped")

    # ──────────────────────────────────────────────────────────────────────────
    # AGGREGATE STATS
    # ──────────────────────────────────────────────────────────────────────────

    def _engine_map(self) -> Dict[str, Any]:
        """Map of engine name -> instance (None if not yet loaded)."""
        return {
            "abstract_thinking": self._abstract_thinking,
            "analogical_reasoning": self._analogical_reasoning,
            "causal_reasoning": self._causal_reasoning,
            "creative_synthesis": self._creative_synthesis,
            "ethical_reasoning": self._ethical_reasoning,
            "planning": self._planning_engine,
            "theory_of_mind": self._theory_of_mind,
            "metacognitive_monitor": self._metacognitive_monitor,
            "spatial_reasoning": self._spatial_reasoning,
            "temporal_reasoning": self._temporal_reasoning,
            "probabilistic_reasoning": self._probabilistic_reasoning,
            "logical_reasoning": self._logical_reasoning,
            "emotional_intelligence": self._emotional_intelligence,
            "social_cognition": self._social_cognition,
            "common_sense": self._common_sense,
            "decision_theory": self._decision_theory,
            "systems_thinking": self._systems_thinking,
            "narrative_intelligence": self._narrative_intelligence,
            "dialectical_reasoning": self._dialectical_reasoning,
            "intuition": self._intuition_engine,
            "knowledge_integration": self._knowledge_integration,
            "cognitive_flexibility": self._cognitive_flexibility,
            "hypothesis": self._hypothesis_engine,
            "goal_management": self._goal_management,
            "linguistic_intelligence": self._linguistic_intelligence,
            "self_model": self._self_model,
            "constraint_solver": self._constraint_solver,
            # Advanced 23
            "counterfactual_reasoning": self._counterfactual_reasoning,
            "moral_imagination": self._moral_imagination,
            "working_memory": self._working_memory,
            "conceptual_blending": self._conceptual_blending,
            "perspective_taking": self._perspective_taking,
            "transfer_learning": self._transfer_learning,
            "error_detection": self._error_detection,
            "curiosity_drive": self._curiosity_drive,
            "wisdom": self._wisdom_engine,
            "humor_intelligence": self._humor_intelligence,
            "musical_cognition": self._musical_cognition,
            "visual_imagination": self._visual_imagination,
            "attention_control": self._attention_control,
            "dream_engine": self._dream_engine,
            "negotiation_intelligence": self._negotiation_intelligence,
            "game_theory": self._game_theory,
            "adversarial_thinking": self._adversarial_thinking,
            "cultural_intelligence": self._cultural_intelligence,
            "philosophical_reasoning": self._philosophical_reasoning,
            "information_synthesis": self._information_synthesis,
            "debate": self._debate_engine,
            "analogy_generator": self._analogy_generator,
            "emotional_regulation": self._emotional_regulation,
            # Ultimate Advancement 6
            "quantum_cognition": self._quantum_cognition,
            "swarm_intelligence": self._swarm_intelligence,
            "temporal_prophecy": self._temporal_prophecy,
            "adversarial_evolution": self._adversarial_evolution,
            "cross_dimensional_reasoning": self._cross_dimensional_reasoning,
            "existential_calculus": self._existential_calculus,
            # Hybrid Reasoning 6
            "knowledge_graph": self._knowledge_graph,
            "symbolic_logic": self._symbolic_logic,
            "graph_algorithms": self._graph_algorithms,
            "bayesian_engine": self._bayesian_engine,
            "planning_algorithms": self._planning_algorithms,
            "hybrid_reasoning": self._hybrid_reasoning,
            # ASI Engines
            "transcendent_creator": self._transcendent_creator,
            "goal_genesis": self._goal_genesis,
            "super_empathy": self._super_empathy,
            "oracle_predictor": self._oracle_predictor,
            "multidisciplinary_synthesizer": self._multidisciplinary_synthesizer,
            "scientific_genesis": self._scientific_genesis,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get stats from all engines"""
        stats = {
            "running": self._running,
            "total_engines": len(self._engine_map()),
            "engines": {}
        }

        for name, engine in self._engine_map().items():
            if engine is not None:
                try:
                    stats["engines"][name] = engine.get_stats()
                except Exception:
                    stats["engines"][name] = {"error": "stats unavailable"}
            else:
                stats["engines"][name] = {"loaded": False}

        stats["loaded_count"] = sum(
            1 for e in stats["engines"].values() if e.get("loaded") is not False
        )
        return stats

    def get_summary(self) -> str:
        """Human-readable summary of all cognitive engines"""
        lines = ["╔══════════════════════════════════════╗",
                 "║   🧠 COGNITION SYSTEM STATUS (62)   ║",
                 "╚══════════════════════════════════════╝",
                 "",
                 "  ── Core Engines ──"]

        core_info = [
            ("🧊 Abstract Thinking", self._abstract_thinking),
            ("🔗 Analogical Reasoning", self._analogical_reasoning),
            ("⛓️ Causal Reasoning", self._causal_reasoning),
            ("🎨 Creative Synthesis", self._creative_synthesis),
            ("⚖️ Ethical Reasoning", self._ethical_reasoning),
            ("📋 Planning Engine", self._planning_engine),
            ("🧠 Theory of Mind", self._theory_of_mind),
        ]

        extended_info = [
            ("🔍 Metacognitive Monitor", self._metacognitive_monitor),
            ("📐 Spatial Reasoning", self._spatial_reasoning),
            ("⏰ Temporal Reasoning", self._temporal_reasoning),
            ("🎲 Probabilistic Reasoning", self._probabilistic_reasoning),
            ("🔢 Logical Reasoning", self._logical_reasoning),
            ("💝 Emotional Intelligence", self._emotional_intelligence),
            ("👥 Social Cognition", self._social_cognition),
            ("🌍 Common Sense", self._common_sense),
            ("⚖️ Decision Theory", self._decision_theory),
            ("🔄 Systems Thinking", self._systems_thinking),
            ("📖 Narrative Intelligence", self._narrative_intelligence),
            ("🏛️ Dialectical Reasoning", self._dialectical_reasoning),
            ("⚡ Intuition Engine", self._intuition_engine),
            ("🌐 Knowledge Integration", self._knowledge_integration),
            ("🔀 Cognitive Flexibility", self._cognitive_flexibility),
            ("🔬 Hypothesis Engine", self._hypothesis_engine),
            ("🎯 Goal Management", self._goal_management),
            ("🗣️ Linguistic Intelligence", self._linguistic_intelligence),
            ("🪞 Self-Model", self._self_model),
            ("🧩 Constraint Solver", self._constraint_solver),
        ]

        advanced_info = [
            ("🔮 Counterfactual Reasoning", self._counterfactual_reasoning),
            ("🕊️ Moral Imagination", self._moral_imagination),
            ("📝 Working Memory", self._working_memory),
            ("🧬 Conceptual Blending", self._conceptual_blending),
            ("👁️ Perspective Taking", self._perspective_taking),
            ("🔄 Transfer Learning", self._transfer_learning),
            ("🔍 Error Detection", self._error_detection),
            ("🔎 Curiosity Drive", self._curiosity_drive),
            ("🦉 Wisdom Engine", self._wisdom_engine),
            ("😄 Humor Intelligence", self._humor_intelligence),
            ("🎵 Musical Cognition", self._musical_cognition),
            ("🎨 Visual Imagination", self._visual_imagination),
            ("🎯 Attention Control", self._attention_control),
            ("💭 Dream Engine", self._dream_engine),
            ("🤝 Negotiation Intelligence", self._negotiation_intelligence),
            ("♟️ Game Theory", self._game_theory),
            ("⚔️ Adversarial Thinking", self._adversarial_thinking),
            ("🌍 Cultural Intelligence", self._cultural_intelligence),
            ("🏛️ Philosophical Reasoning", self._philosophical_reasoning),
            ("🧬 Information Synthesis", self._information_synthesis),
            ("🎙️ Debate Engine", self._debate_engine),
            ("🔗 Analogy Generator", self._analogy_generator),
            ("💚 Emotional Regulation", self._emotional_regulation),
        ]

        advancement_info = [
            ("⚛️ Quantum Cognition", self._quantum_cognition),
            ("🐝 Swarm Intelligence", self._swarm_intelligence),
            ("🔮 Temporal Prophecy", self._temporal_prophecy),
            ("🧬 Adversarial Evolution", self._adversarial_evolution),
            ("🌌 Cross-Dimensional Reasoning", self._cross_dimensional_reasoning),
            ("∞ Existential Calculus", self._existential_calculus),
        ]

        hybrid_info = [
            ("🕸️ Knowledge Graph", self._knowledge_graph),
            ("🔣 Symbolic Logic", self._symbolic_logic),
            ("📊 Graph Algorithms", self._graph_algorithms),
            ("📈 Bayesian Engine", self._bayesian_engine),
            ("🗺️ Planning Algorithms", self._planning_algorithms),
            ("🧪 Hybrid Reasoning", self._hybrid_reasoning),
        ]

        asi_info = [
            ("🌌 Transcendent Creator", self._transcendent_creator),
            ("🌍 Goal Genesis", self._goal_genesis),
            ("💖 Super Empathy", self._super_empathy),
            ("🔮 Oracle Predictor", self._oracle_predictor),
            ("🧬 Multidisciplinary Synth", self._multidisciplinary_synthesizer),
            ("🔬 Scientific Genesis", self._scientific_genesis),
        ]

        def _fmt(label, engine):
            if engine is not None:
                try:
                    s = engine.get_stats()
                    status = "✅ ACTIVE" if s.get("running") else "⏸️ READY"
                    return f"  {label}: {status}"
                except Exception:
                    return f"  {label}: ⚠️ ERROR"
            return f"  {label}: ⬜ NOT LOADED"

        for label, engine in core_info:
            lines.append(_fmt(label, engine))

        lines.append("")
        lines.append("  ── Extended Engines ──")

        for label, engine in extended_info:
            lines.append(_fmt(label, engine))

        lines.append("")
        lines.append("  ── Advanced Engines ──")

        for label, engine in advanced_info:
            lines.append(_fmt(label, engine))

        lines.append("")
        lines.append("  ── Advancement Engines ──")

        for label, engine in advancement_info:
            lines.append(_fmt(label, engine))

        lines.append("")
        lines.append("  ── Hybrid Reasoning Engines ──")

        for label, engine in hybrid_info:
            lines.append(_fmt(label, engine))

        lines.append("")
        lines.append("  ── ASI Engines ──")

        for label, engine in asi_info:
            lines.append(_fmt(label, engine))

        loaded = sum(
            1 for _, e in (
                core_info + extended_info + advanced_info +
                advancement_info + hybrid_info + asi_info
            )
            if e is not None
        )
        lines.append(f"\n  📊 {loaded}/62 engines loaded")

        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

cognition_system = CognitionSystem()
