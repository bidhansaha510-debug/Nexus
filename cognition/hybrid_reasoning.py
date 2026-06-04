"""
NEXUS AI - Hybrid Reasoning Coordinator
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Orchestrates multiple reasoning engines for optimal results.
Combines LLM capabilities with real computational reasoning.

The key insight: LLM is ONE tool, not the ONLY tool.

Features:
  • Query classification (determines which engine to use)
  • Multi-engine result synthesis
  • Confidence estimation and verification
  • Fallback strategies
  • Computational verification of LLM outputs
  • LLM enhancement of computational results

This is the unified interface for all reasoning in NEXUS.
"""

import threading
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum, auto
from collections import defaultdict

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("hybrid_reasoning")

# Import all reasoning engines (lazy to avoid circular imports)
class EngineType(Enum):
    """Available reasoning engines"""
    LLM = "llm"                      # LLM for natural language
    KNOWLEDGE_GRAPH = "knowledge_graph"  # Entity-relationship queries
    SYMBOLIC_LOGIC = "symbolic_logic"    # Formal logic validation
    BAYESIAN = "bayesian"            # Probabilistic inference
    GRAPH_ALGORITHMS = "graph_algorithms"  # Path finding, centrality
    PLANNING = "planning"            # A*, MCTS, HTN planning
    CONSTRAINT_SOLVER = "constraint_solver"  # CSP/SAT solving
    CAUSAL = "causal"                # Causal reasoning


class QueryType(Enum):
    """Types of queries"""
    FACTUAL = "factual"              # Simple fact lookup
    LOGICAL = "logical"              # Logic validation
    PROBABILISTIC = "probabilistic"  # Probability estimation
    CAUSAL = "causal"                # Cause-effect reasoning
    PLANNING = "planning"            # Goal achievement
    CONSTRAINT = "constraint"        # Constraint satisfaction
    EXPLANATION = "explanation"      # Why/how questions
    CREATIVE = "creative"            # Open-ended generation
    UNKNOWN = "unknown"


@dataclass
class ReasoningResult:
    """Result from a reasoning operation"""
    query: str = ""
    query_type: QueryType = QueryType.UNKNOWN
    primary_engine: EngineType = EngineType.LLM
    result: Any = None
    confidence: float = 0.5
    verification: Optional[Dict[str, Any]] = None
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    computation_time_ms: float = 0.0
    engine_contributions: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "query": self.query,
            "query_type": self.query_type.value,
            "primary_engine": self.primary_engine.value,
            "result": self.result,
            "confidence": self.confidence,
            "verification": self.verification,
            "alternatives": self.alternatives,
            "computation_time_ms": self.computation_time_ms,
            "engine_contributions": self.engine_contributions,
        }


class HybridReasoningCoordinator:
    """
    Unified interface for all reasoning in NEXUS.
    
    Workflow:
      1. Classify query type
      2. Route to appropriate engine(s)
      3. Verify results computationally where possible
      4. Synthesize final answer
      5. Provide confidence estimate
    
    Key principle: Computational engines provide verified truth.
    LLM provides natural language understanding and generation.
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
        
        # ──── Engine References (lazy loaded) ────
        self._engines: Dict[EngineType, Any] = {}
        
        # ──── Stats ────
        self._total_queries = 0
        self._engine_usage: Dict[EngineType, int] = defaultdict(int)
        self._query_type_counts: Dict[QueryType, int] = defaultdict(int)
        
        logger.info("HybridReasoningCoordinator initialized")

    # ═══════════════════════════════════════════════════════════════════════════
    # ENGINE LOADING
    # ═══════════════════════════════════════════════════════════════════════════

    def _get_engine(self, engine_type: EngineType) -> Any:
        """Lazy load an engine"""
        if engine_type in self._engines:
            return self._engines[engine_type]
        
        try:
            if engine_type == EngineType.KNOWLEDGE_GRAPH:
                from cognition.knowledge_graph import knowledge_graph
                self._engines[engine_type] = knowledge_graph
            elif engine_type == EngineType.SYMBOLIC_LOGIC:
                from cognition.symbolic_logic import symbolic_logic
                self._engines[engine_type] = symbolic_logic
            elif engine_type == EngineType.BAYESIAN:
                from cognition.bayesian_engine import bayesian_engine
                self._engines[engine_type] = bayesian_engine
            elif engine_type == EngineType.GRAPH_ALGORITHMS:
                from cognition.graph_algorithms import graph_algorithms
                self._engines[engine_type] = graph_algorithms
            elif engine_type == EngineType.PLANNING:
                from cognition.planning_algorithms import planning_algorithms
                self._engines[engine_type] = planning_algorithms
            elif engine_type == EngineType.LLM:
                try:
                    from llm.llama_interface import llm
                    self._engines[engine_type] = llm
                except:
                    self._engines[engine_type] = None
            elif engine_type == EngineType.CAUSAL:
                from cognition.causal_reasoning import causal_reasoning
                self._engines[engine_type] = causal_reasoning
            
            return self._engines.get(engine_type)
        except ImportError as e:
            logger.warning(f"Could not load engine {engine_type}: {e}")
            return None

    # ═══════════════════════════════════════════════════════════════════════════
    # QUERY CLASSIFICATION
    # ═══════════════════════════════════════════════════════════════════════════

    def classify_query(self, query: str) -> QueryType:
        """
        Classify the type of query to route to appropriate engine.
        
        Uses simple heuristics first, falls back to LLM classification.
        """
        query_lower = query.lower()
        
        # Simple heuristic classification
        logic_indicators = ["valid", "invalid", "logical", "argument", "premise", "conclusion", "implies", "therefore", "if", "then", "all", "some", "none"]
        if any(ind in query_lower for ind in logic_indicators):
            return QueryType.LOGICAL
        
        prob_indicators = ["probability", "likely", "chance", "odds", "percent", "how likely", "what are the chances", "bayesian"]
        if any(ind in query_lower for ind in prob_indicators):
            return QueryType.PROBABILISTIC
        
        causal_indicators = ["cause", "effect", "why did", "because", "leads to", "results in", "consequence", "outcome", "due to"]
        if any(ind in query_lower for ind in causal_indicators):
            return QueryType.CAUSAL
        
        planning_indicators = ["how to", "plan", "steps", "achieve", "goal", "accomplish", "sequence", "first then"]
        if any(ind in query_lower for ind in planning_indicators):
            return QueryType.PLANNING
        
        constraint_indicators = ["constraint", "satisfy", "possible", "feasible", "cannot", "must", "require", "allocate"]
        if any(ind in query_lower for ind in constraint_indicators):
            return QueryType.CONSTRAINT
        
        explanation_indicators = ["why", "how does", "explain", "reason", "because", "what causes"]
        if any(ind in query_lower for ind in explanation_indicators):
            return QueryType.EXPLANATION
        
        creative_indicators = ["imagine", "create", "design", "invent", "what if", "suppose", "generate"]
        if any(ind in query_lower for ind in creative_indicators):
            return QueryType.CREATIVE
        
        # Default to factual
        return QueryType.FACTUAL

    def get_recommended_engines(self, query_type: QueryType) -> List[EngineType]:
        """Get recommended engines for a query type"""
        recommendations = {
            QueryType.LOGICAL: [EngineType.SYMBOLIC_LOGIC, EngineType.LLM],
            QueryType.PROBABILISTIC: [EngineType.BAYESIAN, EngineType.LLM],
            QueryType.CAUSAL: [EngineType.CAUSAL, EngineType.GRAPH_ALGORITHMS, EngineType.LLM],
            QueryType.PLANNING: [EngineType.PLANNING, EngineType.LLM],
            QueryType.CONSTRAINT: [EngineType.CONSTRAINT_SOLVER, EngineType.LLM],
            QueryType.EXPLANATION: [EngineType.LLM, EngineType.CAUSAL],
            QueryType.FACTUAL: [EngineType.KNOWLEDGE_GRAPH, EngineType.LLM],
            QueryType.CREATIVE: [EngineType.LLM],
            QueryType.UNKNOWN: [EngineType.LLM],
        }
        return recommendations.get(query_type, [EngineType.LLM])

    # ═══════════════════════════════════════════════════════════════════════════
    # MAIN REASONING INTERFACE
    # ═══════════════════════════════════════════════════════════════════════════

    def reason(self, query: str, context: Dict[str, Any] = None) -> ReasoningResult:
        """
        Main reasoning interface.
        
        Classifies query, routes to appropriate engine(s), and synthesizes results.
        """
        start_time = time.time()
        self._total_queries += 1
        
        # Classify query
        query_type = self.classify_query(query)
        self._query_type_counts[query_type] += 1
        
        # Get recommended engines
        engines = self.get_recommended_engines(query_type)
        primary_engine = engines[0] if engines else EngineType.LLM
        
        result = ReasoningResult(
            query=query,
            query_type=query_type,
            primary_engine=primary_engine,
        )
        
        # Route to appropriate engine
        try:
            if query_type == QueryType.LOGICAL:
                result = self._logical_reasoning(query, context)
            elif query_type == QueryType.PROBABILISTIC:
                result = self._probabilistic_reasoning(query, context)
            elif query_type == QueryType.CAUSAL:
                result = self._causal_reasoning(query, context)
            elif query_type == QueryType.PLANNING:
                result = self._planning_reasoning(query, context)
            elif query_type == QueryType.CONSTRAINT:
                result = self._constraint_reasoning(query, context)
            elif query_type == QueryType.FACTUAL:
                result = self._factual_reasoning(query, context)
            else:
                result = self._llm_reasoning(query, context)
        except Exception as e:
            logger.debug(f"Reasoning failed: {e}")
            result.result = f"Reasoning error: {e}"
            result.confidence = 0.0
        
        result.computation_time_ms = (time.time() - start_time) * 1000
        self._engine_usage[result.primary_engine] += 1
        
        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # SPECIALIZED REASONING METHODS
    # ═══════════════════════════════════════════════════════════════════════════

    def _logical_reasoning(self, query: str, context: Dict[str, Any]) -> ReasoningResult:
        """Logical reasoning with symbolic verification"""
        engine = self._get_engine(EngineType.SYMBOLIC_LOGIC)
        
        result = ReasoningResult(
            query=query,
            query_type=QueryType.LOGICAL,
            primary_engine=EngineType.SYMBOLIC_LOGIC,
        )
        
        if engine is None:
            return self._llm_reasoning(query, context)
        
        # Check if it's a syllogism
        if "all" in query.lower() or "some" in query.lower() or "no " in query.lower():
            # Try syllogism validation
            parts = query.split(".")
            if len(parts) >= 3:
                syllogism_result = engine.validate_syllogism(
                    parts[0].strip(),
                    parts[1].strip(),
                    parts[2].strip()
                )
                result.result = syllogism_result
                result.confidence = 0.95 if syllogism_result.get("is_valid") else 0.9
                result.verification = {"method": "syllogistic_logic"}
                return result
        
        # Try argument validation
        # Parse premises and conclusion
        premises = context.get("premises", []) if context else []
        conclusion = context.get("conclusion", "") if context else ""
        
        if premises and conclusion:
            parsed_premises = [engine.parse(p) for p in premises]
            parsed_conclusion = engine.parse(conclusion)
            is_valid, proof = engine.check_validity(parsed_premises, parsed_conclusion)
            
            result.result = {
                "is_valid": is_valid,
                "proof": proof.to_dict(),
            }
            result.confidence = 0.95
            result.verification = {"method": "truth_table_validation"}
            return result
        
        # Fall back to LLM with logic context
        llm = self._get_engine(EngineType.LLM)
        if llm:
            logic_context = f"Use formal logic. Analyze validity. Query: {query}"
            response = llm.generate(logic_context, max_tokens=500, temperature=0.3)
            result.result = response.text if hasattr(response, 'text') else str(response)
            result.primary_engine = EngineType.LLM
            result.confidence = 0.6
        
        return result

    def _probabilistic_reasoning(self, query: str, context: Dict[str, Any]) -> ReasoningResult:
        """Probabilistic reasoning with Bayesian inference"""
        engine = self._get_engine(EngineType.BAYESIAN)
        
        result = ReasoningResult(
            query=query,
            query_type=QueryType.PROBABILISTIC,
            primary_engine=EngineType.BAYESIAN,
        )
        
        if engine is None or not engine._nodes:
            return self._llm_reasoning(query, context)
        
        # Try to match query to network variables
        query_lower = query.lower()
        
        for node_id, node in engine._nodes.items():
            if node_id in query_lower or node.name.lower() in query_lower:
                # Found matching variable
                query_result = engine.query(node.name)
                result.result = {
                    "variable": node.name,
                    "posterior": query_result.posterior,
                    "most_likely": query_result.most_likely_state(),
                }
                result.confidence = 0.9
                result.verification = {"method": "bayesian_inference", "engine": "pgmpy" if hasattr(engine, '_pgmpy_model') and engine._pgmpy_model else "builtin"}
                return result
        
        # Fall back to LLM
        return self._llm_reasoning(query, context)

    def _causal_reasoning(self, query: str, context: Dict[str, Any]) -> ReasoningResult:
        """Causal reasoning with graph algorithms"""
        causal_engine = self._get_engine(EngineType.CAUSAL)
        graph_engine = self._get_engine(EngineType.GRAPH_ALGORITHMS)
        kg_engine = self._get_engine(EngineType.KNOWLEDGE_GRAPH)
        
        result = ReasoningResult(
            query=query,
            query_type=QueryType.CAUSAL,
            primary_engine=EngineType.CAUSAL,
        )
        
        # Try knowledge graph for causal paths
        if kg_engine and len(kg_engine._relations) > 0:
            kg_context = kg_engine.get_context_for_query(query)
            if kg_context:
                result.engine_contributions["knowledge_graph"] = 0.3
        
        # Use causal reasoning engine
        if causal_engine:
            # Analyze causes
            causal_chain = causal_engine.analyze_causes(query)
            if causal_chain:
                result.result = {
                    "root_cause": causal_chain.root_cause,
                    "chain": [link.to_dict() for link in causal_chain.links],
                    "confidence": causal_chain.total_confidence,
                }
                result.confidence = causal_chain.total_confidence
                result.verification = {"method": "causal_chain_analysis"}
                return result
        
        # Fall back to LLM with context
        return self._llm_reasoning(query, context)

    def _planning_reasoning(self, query: str, context: Dict[str, Any]) -> ReasoningResult:
        """Planning with A*/MCTS/HTN"""
        engine = self._get_engine(EngineType.PLANNING)
        
        result = ReasoningResult(
            query=query,
            query_type=QueryType.PLANNING,
            primary_engine=EngineType.PLANNING,
        )
        
        if engine is None or len(engine._actions) == 0:
            return self._llm_reasoning(query, context)
        
        # Generate domain from query if needed
        if context and "domain_description" in context:
            engine.generate_actions_from_description(context["domain_description"])
        
        # Get initial and goal states from context
        initial_state = context.get("initial_state") if context else None
        goal_state = context.get("goal_state") if context else None
        
        if initial_state and goal_state:
            # Try A* planning
            from cognition.planning_algorithms import State
            initial = State(variables=initial_state) if isinstance(initial_state, dict) else initial_state
            goal = State(variables=goal_state) if isinstance(goal_state, dict) else goal_state
            
            plan = engine.astar_plan(initial, goal)
            
            if plan:
                result.result = {
                    "actions": [a.name for a in plan.actions],
                    "cost": plan.total_cost,
                    "valid": True,
                }
                result.confidence = 0.95
                result.verification = {"method": "astar_search", "validated": True}
                return result
        
        # Fall back to LLM
        return self._llm_reasoning(query, context)

    def _constraint_reasoning(self, query: str, context: Dict[str, Any]) -> ReasoningResult:
        """Constraint satisfaction reasoning"""
        # For now, use the existing constraint solver (LLM-based) with enhancement
        result = ReasoningResult(
            query=query,
            query_type=QueryType.CONSTRAINT,
            primary_engine=EngineType.CONSTRAINT_SOLVER,
        )
        
        # Try symbolic logic for constraint validation
        logic_engine = self._get_engine(EngineType.SYMBOLIC_LOGIC)
        if logic_engine and context and "constraints" in context:
            # Convert constraints to CNF for SAT
            cnf_clauses = []
            for constraint in context["constraints"]:
                prop = logic_engine.parse(constraint)
                clauses = logic_engine.to_cnf(prop)
                cnf_clauses.extend(clauses)
            
            result.result = {
                "cnf_representation": cnf_clauses,
                "note": "Constraints converted to CNF for potential SAT solving",
            }
            result.engine_contributions["symbolic_logic"] = 0.4
        
        # Use LLM for natural constraint reasoning
        llm_result = self._llm_reasoning(query, context)
        result.result = llm_result.result if not result.result else result.result
        result.confidence = llm_result.confidence * 0.7
        result.primary_engine = EngineType.LLM
        
        return result

    def _factual_reasoning(self, query: str, context: Dict[str, Any]) -> ReasoningResult:
        """Factual query using knowledge graph"""
        kg_engine = self._get_engine(EngineType.KNOWLEDGE_GRAPH)
        
        result = ReasoningResult(
            query=query,
            query_type=QueryType.FACTUAL,
            primary_engine=EngineType.KNOWLEDGE_GRAPH,
        )
        
        # Try knowledge graph first
        if kg_engine:
            kg_context = kg_engine.get_context_for_query(query)
            
            if kg_context:
                result.result = kg_context
                result.confidence = 0.85
                result.engine_contributions["knowledge_graph"] = 0.5
        
        # Enhance with LLM
        llm = self._get_engine(EngineType.LLM)
        if llm:
            prompt = query
            if result.result:
                prompt = f"Given known facts:\n{result.result}\n\nAnswer: {query}"
            
            response = llm.generate(prompt, max_tokens=500, temperature=0.3)
            llm_result = response.text if hasattr(response, 'text') else str(response)
            
            if result.result:
                result.result = f"{result.result}\n\n{llm_result}"
            else:
                result.result = llm_result
                result.primary_engine = EngineType.LLM
            
            result.engine_contributions["llm"] = 0.5
        
        return result

    def _llm_reasoning(self, query: str, context: Dict[str, Any]) -> ReasoningResult:
        """Fallback LLM reasoning"""
        llm = self._get_engine(EngineType.LLM)
        
        result = ReasoningResult(
            query=query,
            query_type=QueryType.UNKNOWN,
            primary_engine=EngineType.LLM,
        )
        
        if llm is None:
            result.result = "No LLM available"
            result.confidence = 0.0
            return result
        
        prompt = query
        if context:
            context_str = json.dumps(context, indent=2)
            prompt = f"Context:\n{context_str}\n\nQuery: {query}"
        
        response = llm.generate(prompt, max_tokens=800, temperature=0.5)
        result.result = response.text if hasattr(response, 'text') else str(response)
        result.confidence = 0.5  # LLM-only has lower confidence
        
        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # VERIFICATION METHODS
    # ═══════════════════════════════════════════════════════════════════════════

    def verify_with_computation(
        self,
        llm_result: str,
        query_type: QueryType
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Verify an LLM result using computational methods.
        
        Returns (is_verified, verification_details).
        """
        if query_type == QueryType.LOGICAL:
            logic_engine = self._get_engine(EngineType.SYMBOLIC_LOGIC)
            if logic_engine:
                # Try to extract and verify logical claims
                # This is a simplified check
                if "valid" in llm_result.lower() or "true" in llm_result.lower():
                    return True, {"method": "keyword_check", "note": "Simplified verification"}
        
        elif query_type == QueryType.PROBABILISTIC:
            # Check if probability claims are within valid range
            import re
            probs = re.findall(r'(\d+(?:\.\d+)?)\s*(?:%|percent|probability)', llm_result.lower())
            if probs:
                valid = all(0 <= float(p) <= 100 for p in probs)
                return valid, {"probabilities_found": probs}
        
        return False, None

    # ═══════════════════════════════════════════════════════════════════════════
    # UTILITY METHODS
    # ═══════════════════════════════════════════════════════════════════════════

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self):
        """Start the hybrid reasoning coordinator"""
        self._running = True
        logger.info("HybridReasoningCoordinator started")

    def stop(self):
        """Stop the hybrid reasoning coordinator"""
        self._running = False
        logger.info("HybridReasoningCoordinator stopped")

    def get_stats(self) -> Dict[str, Any]:
        """Get coordinator statistics"""
        return {
            "running": getattr(self, '_running', False),
            "total_queries": self._total_queries,
            "engine_usage": {e.value: c for e, c in self._engine_usage.items()},
            "query_type_counts": {q.value: c for q, c in self._query_type_counts.items()},
            "available_engines": [e.value for e in EngineType if self._get_engine(e) is not None],
        }

    def get_engine_status(self) -> Dict[str, bool]:
        """Get status of all engines"""
        status = {}
        for engine_type in EngineType:
            engine = self._get_engine(engine_type)
            if engine is None:
                status[engine_type.value] = False
            elif hasattr(engine, '_running'):
                status[engine_type.value] = engine._running
            elif hasattr(engine, 'is_connected'):
                status[engine_type.value] = engine.is_connected
            else:
                status[engine_type.value] = True
        return status


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

hybrid_reasoning = HybridReasoningCoordinator()


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def reason(query: str, context: Dict[str, Any] = None) -> ReasoningResult:
    """Convenience function for hybrid reasoning"""
    return hybrid_reasoning.reason(query, context)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    hr = HybridReasoningCoordinator()
    
    # Test query classification
    print("=== Query Classification ===")
    queries = [
        "Is this argument valid: If P then Q, P, therefore Q?",
        "What is the probability of rain tomorrow?",
        "Why did the stock market crash?",
        "How do I learn Python in 30 days?",
        "What is the capital of France?",
    ]
    
    for q in queries:
        qtype = hr.classify_query(q)
        engines = hr.get_recommended_engines(qtype)
        print(f"'{q[:40]}...' → {qtype.value} → {[e.value for e in engines]}")
    
    # Test engine status
    print("\n=== Engine Status ===")
    status = hr.get_engine_status()
    for engine, available in status.items():
        print(f"  {engine}: {'✓' if available else '✗'}")
    
    # Test reasoning (will use fallbacks if engines not initialized)
    print("\n=== Reasoning Test ===")
    result = hr.reason("What is 2+2?")
    print(f"Query: What is 2+2?")
    print(f"Result: {result.result}")
    print(f"Confidence: {result.confidence}")
    print(f"Engine: {result.primary_engine.value}")
    
    print(f"\nStats: {hr.get_stats()}")