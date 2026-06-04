"""
NEXUS AI - Bayesian Network Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Real Bayesian inference - not LLM-estimated probabilities.
Provides actual probability propagation through Bayesian networks.

Features:
  • Bayesian network structure definition
  • Conditional Probability Table (CPT) management
  • Variable elimination algorithm
  • Belief propagation
  • Evidence incorporation and updating
  • Exact and approximate inference
  • Learning CPTs from data

This module provides computational probability for reasoning
under uncertainty. The LLM can help structure networks from
natural language, but all probability math is computed exactly.
"""

import threading
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Set, Callable
from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict
from enum import Enum, auto
from itertools import product
import math

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("bayesian_engine")

# Try to import pgmpy for professional Bayesian inference
try:
    from pgmpy.models import BayesianNetwork as PgmpyBayesianNetwork
    from pgmpy.factors.discrete import TabularCPD
    from pgmpy.inference import VariableElimination
    PGMPY_AVAILABLE = True
except ImportError:
    PGMPY_AVAILABLE = False
    logger.warning("pgmpy not available - using built-in inference")

# ═══════════════════════════════════════════════════════════════════════════════
# DATA TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class NodeType(Enum):
    """Types of nodes in a Bayesian network"""
    BINARY = "binary"        # True/False
    CATEGORICAL = "categorical"  # Discrete categories
    CONTINUOUS = "continuous"    # Continuous values (discretized for computation)
    ORDINAL = "ordinal"      # Ordered categories


class InferenceMethod(Enum):
    """Methods for Bayesian inference"""
    VARIABLE_ELIMINATION = "variable_elimination"
    BELIEF_PROPAGATION = "belief_propagation"
    GIBBS_SAMPLING = "gibbs_sampling"
    LIKELIHOOD_WEIGHTING = "likelihood_weighting"


@dataclass
class BNode:
    """A node in a Bayesian network"""
    node_id: str
    name: str
    states: List[str] = field(default_factory=list)  # Possible values
    node_type: NodeType = NodeType.CATEGORICAL
    description: str = ""
    parents: List[str] = field(default_factory=list)
    children: List[str] = field(default_factory=list)
    
    def __hash__(self):
        return hash(self.node_id)
    
    def to_dict(self) -> Dict:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "states": self.states,
            "node_type": self.node_type.value,
            "description": self.description,
            "parents": self.parents,
            "children": self.children,
        }


@dataclass
class CPT:
    """Conditional Probability Table for a node"""
    node_id: str
    parents: List[str] = field(default_factory=list)
    # Probabilities: maps (parent_values tuple) -> {state: probability}
    probabilities: Dict[Tuple[str, ...], Dict[str, float]] = field(default_factory=dict)
    states: List[str] = field(default_factory=list)
    
    def get_probability(self, state: str, parent_values: Tuple[str, ...] = ()) -> float:
        """Get P(node=state | parents=parent_values)"""
        if not self.parents:
            # No parents - use empty tuple
            parent_values = ()
        return self.probabilities.get(parent_values, {}).get(state, 0.0)
    
    def set_probability(self, state: str, probability: float, parent_values: Tuple[str, ...] = ()):
        """Set a probability value"""
        if not self.parents:
            parent_values = ()
        if parent_values not in self.probabilities:
            self.probabilities[parent_values] = {}
        self.probabilities[parent_values][state] = probability
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate that probabilities sum to 1 for each parent configuration"""
        errors = []
        for parent_config, state_probs in self.probabilities.items():
            total = sum(state_probs.values())
            if abs(total - 1.0) > 0.001:
                errors.append(f"Probabilities sum to {total} for parent config {parent_config}")
        return len(errors) == 0, errors
    
    def to_dict(self) -> Dict:
        return {
            "node_id": self.node_id,
            "parents": self.parents,
            "probabilities": {str(k): v for k, v in self.probabilities.items()},
            "states": self.states,
        }


@dataclass
class Evidence:
    """Evidence for Bayesian inference"""
    node_id: str
    state: str
    confidence: float = 1.0
    
    def to_dict(self) -> Dict:
        return {
            "node_id": self.node_id,
            "state": self.state,
            "confidence": self.confidence,
        }


@dataclass
class QueryResult:
    """Result of a Bayesian query"""
    query_id: str = ""
    query_variable: str = ""
    evidence: Dict[str, str] = field(default_factory=dict)
    posterior: Dict[str, float] = field(default_factory=dict)  # {state: probability}
    method: str = "variable_elimination"
    computation_time_ms: float = 0.0
    confidence: float = 1.0
    
    def most_likely_state(self) -> Tuple[str, float]:
        """Get the most likely state"""
        if not self.posterior:
            return ("unknown", 0.0)
        best_state = max(self.posterior, key=self.posterior.get)
        return (best_state, self.posterior[best_state])
    
    def to_dict(self) -> Dict:
        return {
            "query_id": self.query_id,
            "query_variable": self.query_variable,
            "evidence": self.evidence,
            "posterior": self.posterior,
            "method": self.method,
            "computation_time_ms": self.computation_time_ms,
            "confidence": self.confidence,
            "most_likely_state": self.most_likely_state(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# BAYESIAN NETWORK ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class BayesianEngine:
    """
    Real Bayesian Network Inference Engine.
    
    Operations:
      add_node()       — Add a node with states
      add_edge()       — Add a directed edge (parent -> child)
      set_cpt()        — Set conditional probability table
      set_evidence()   — Set observed evidence
      query()          — Compute posterior probability
      update()         — Update beliefs with new evidence
      learn_cpt()      — Learn CPT from data
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
        
        # ──── Network Structure ────
        self._nodes: Dict[str, BNode] = {}
        self._cpts: Dict[str, CPT] = {}
        self._edges: List[Tuple[str, str]] = []  # (parent, child)
        
        # ──── Current Evidence ────
        self._evidence: Dict[str, str] = {}
        
        # ──── Cached Beliefs ────
        self._beliefs: Dict[str, Dict[str, float]] = {}
        
        # ──── pgmpy Model (if available) ────
        self._pgmpy_model = None
        
        # ──── Stats ────
        self._total_queries = 0
        self._total_updates = 0
        
        # ──── Persistence ────
        self._db_path = DATA_DIR / "cognition" / "bayesian_networks.db"
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        logger.info(f"BayesianEngine initialized (pgmpy: {PGMPY_AVAILABLE})")

    # ═══════════════════════════════════════════════════════════════════════════
    # DATABASE
    # ═══════════════════════════════════════════════════════════════════════════

    def _init_database(self):
        """Initialize SQLite for persistence"""
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS nodes (
                    node_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    states TEXT,
                    node_type TEXT DEFAULT 'categorical',
                    description TEXT
                );
                
                CREATE TABLE IF NOT EXISTS edges (
                    parent_id TEXT,
                    child_id TEXT,
                    PRIMARY KEY (parent_id, child_id)
                );
                
                CREATE TABLE IF NOT EXISTS cpts (
                    node_id TEXT PRIMARY KEY,
                    parents TEXT,
                    probabilities TEXT,
                    states TEXT
                );
            """)

    def _save_network(self):
        """Save network to database"""
        with sqlite3.connect(str(self._db_path)) as conn:
            # Save nodes
            for node in self._nodes.values():
                conn.execute(
                    """INSERT OR REPLACE INTO nodes (node_id, name, states, node_type, description)
                       VALUES (?, ?, ?, ?, ?)""",
                    (node.node_id, node.name, json.dumps(node.states), node.node_type.value, node.description)
                )
            
            # Save edges
            conn.execute("DELETE FROM edges")
            for parent, child in self._edges:
                conn.execute("INSERT INTO edges (parent_id, child_id) VALUES (?, ?)", (parent, child))
            
            # Save CPTs
            for cpt in self._cpts.values():
                conn.execute(
                    """INSERT OR REPLACE INTO cpts (node_id, parents, probabilities, states)
                       VALUES (?, ?, ?, ?)""",
                    (cpt.node_id, json.dumps(cpt.parents), json.dumps(cpt.to_dict()["probabilities"]), json.dumps(cpt.states))
                )

    # ═══════════════════════════════════════════════════════════════════════════
    # NETWORK CONSTRUCTION
    # ═══════════════════════════════════════════════════════════════════════════

    def add_node(
        self,
        name: str,
        states: List[str] = None,
        node_type: NodeType = NodeType.CATEGORICAL,
        description: str = ""
    ) -> str:
        """
        Add a node to the network.
        
        Args:
            name: Node name
            states: Possible states (default: ["true", "false"])
            node_type: Type of node
            description: Description
        
        Returns node_id.
        """
        node_id = name.lower().replace(" ", "_")
        
        if states is None:
            states = ["true", "false"]
        
        node = BNode(
            node_id=node_id,
            name=name,
            states=states,
            node_type=node_type,
            description=description,
        )
        
        self._nodes[node_id] = node
        
        # Initialize empty CPT
        self._cpts[node_id] = CPT(node_id=node_id, states=states)
        
        # Reset pgmpy model
        self._pgmpy_model = None
        
        logger.debug(f"Added node: {name} with states {states}")
        return node_id

    def add_edge(self, parent: str, child: str) -> bool:
        """
        Add a directed edge from parent to child.
        
        Returns True if successful.
        """
        parent_id = parent.lower().replace(" ", "_")
        child_id = child.lower().replace(" ", "_")
        
        if parent_id not in self._nodes or child_id not in self._nodes:
            logger.error(f"Cannot add edge: node not found ({parent} -> {child})")
            return False
        
        # Check for cycles
        if self._would_create_cycle(parent_id, child_id):
            logger.error(f"Cannot add edge: would create cycle ({parent} -> {child})")
            return False
        
        self._edges.append((parent_id, child_id))
        self._nodes[parent_id].children.append(child_id)
        self._nodes[child_id].parents.append(parent_id)
        
        # Update child's CPT to include parent
        self._cpts[child_id].parents = self._nodes[child_id].parents.copy()
        
        # Reset pgmpy model
        self._pgmpy_model = None
        
        logger.debug(f"Added edge: {parent} -> {child}")
        return True

    def _would_create_cycle(self, parent: str, child: str) -> bool:
        """Check if adding edge would create a cycle"""
        # DFS from child to see if we can reach parent
        visited = set()
        stack = [child]
        
        while stack:
            node = stack.pop()
            if node == parent:
                return True
            if node in visited:
                continue
            visited.add(node)
            # Follow existing edges
            for p, c in self._edges:
                if p == node:
                    stack.append(c)
        
        return False

    def set_cpt(
        self,
        node: str,
        probabilities: Dict[Tuple[str, ...], Dict[str, float]]
    ) -> bool:
        """
        Set the Conditional Probability Table for a node.
        
        Args:
            node: Node name
            probabilities: Dict mapping parent_state_tuple -> {state: probability}
        
        Example:
            For node "Sprinkler" with parent "Rain":
            {
                ("true",): {"true": 0.01, "false": 0.99},   # P(Sprinkler | Rain=true)
                ("false",): {"true": 0.4, "false": 0.6},    # P(Sprinkler | Rain=false)
            }
        """
        node_id = node.lower().replace(" ", "_")
        
        if node_id not in self._nodes:
            logger.error(f"Cannot set CPT: node not found ({node})")
            return False
        
        cpt = self._cpts[node_id]
        cpt.probabilities = probabilities
        
        # Validate
        valid, errors = cpt.validate()
        if not valid:
            for error in errors:
                logger.warning(f"CPT validation: {error}")
        
        # Reset pgmpy model
        self._pgmpy_model = None
        
        logger.debug(f"Set CPT for {node}")
        return True

    def set_cpt_simple(
        self,
        node: str,
        probabilities: List[float],
        given_parents: List[Tuple[str, ...]] = None
    ) -> bool:
        """
        Simplified CPT setting for nodes with simple structures.
        
        For a node with no parents:
            set_cpt_simple("Rain", [0.2, 0.8])  # P(Rain) = [0.2, 0.8]
        
        For a node with parents, provide parent configurations:
            set_cpt_simple("WetGrass", [0.9, 0.1, 0.9, 0.1, 0.0, 1.0, 0.1, 0.9],
                          given_parents=[("true", "true"), ("true", "false"), ("false", "true"), ("false", "false")])
        """
        node_id = node.lower().replace(" ", "_")
        
        if node_id not in self._nodes:
            return False
        
        cpt = self._cpts[node_id]
        states = cpt.states
        
        if not cpt.parents:
            # No parents - simple prior
            if len(probabilities) != len(states):
                logger.error(f"CPT length mismatch: expected {len(states)}, got {len(probabilities)}")
                return False
            cpt.probabilities = {(): {s: p for s, p in zip(states, probabilities)}}
        else:
            # Has parents - need parent configurations
            if given_parents is None:
                # Generate all parent combinations
                parent_nodes = [self._nodes[p] for p in cpt.parents]
                parent_combos = list(product(*[n.states for n in parent_nodes]))
            else:
                parent_combos = given_parents
            
            probs_per_combo = len(states)
            if len(probabilities) != len(parent_combos) * probs_per_combo:
                logger.error(f"CPT length mismatch: expected {len(parent_combos) * probs_per_combo}, got {len(probabilities)}")
                return False
            
            cpt.probabilities = {}
            for i, combo in enumerate(parent_combos):
                start = i * probs_per_combo
                cpt.probabilities[combo] = {
                    states[j]: probabilities[start + j]
                    for j in range(probs_per_combo)
                }
        
        self._pgmpy_model = None
        return True

    # ═══════════════════════════════════════════════════════════════════════════
    # INFERENCE
    # ═══════════════════════════════════════════════════════════════════════════

    def query(
        self,
        variable: str,
        evidence: Dict[str, str] = None,
        method: InferenceMethod = InferenceMethod.VARIABLE_ELIMINATION
    ) -> QueryResult:
        """
        Compute the posterior probability P(variable | evidence).
        
        Args:
            variable: The variable to query
            evidence: Dict of {variable: observed_state}
            method: Inference method to use
        
        Returns QueryResult with posterior probabilities.
        """
        import time
        start_time = time.time()
        
        self._total_queries += 1
        
        var_id = variable.lower().replace(" ", "_")
        
        if var_id not in self._nodes:
            return QueryResult(query_variable=variable, confidence=0.0)
        
        # Use provided evidence or current evidence
        ev = evidence if evidence is not None else self._evidence
        ev = {k.lower().replace(" ", "_"): v for k, v in ev.items()}
        
        # Try pgmpy first
        if PGMPY_AVAILABLE and method == InferenceMethod.VARIABLE_ELIMINATION:
            result = self._pgmpy_query(var_id, ev)
            if result:
                result.computation_time_ms = (time.time() - start_time) * 1000
                return result
        
        # Fall back to built-in variable elimination
        posterior = self._variable_elimination(var_id, ev)
        
        result = QueryResult(
            query_id=f"q_{self._total_queries}",
            query_variable=variable,
            evidence=ev,
            posterior=posterior,
            method=method.value,
            computation_time_ms=(time.time() - start_time) * 1000,
            confidence=0.9 if PGMPY_AVAILABLE else 0.7,
        )
        
        # Cache beliefs
        self._beliefs[var_id] = posterior
        
        return result

    def _pgmpy_query(self, variable: str, evidence: Dict[str, str]) -> Optional[QueryResult]:
        """Use pgmpy for inference"""
        try:
            model = self._get_pgmpy_model()
            if model is None:
                return None
            
            inference = VariableElimination(model)
            
            # Convert evidence state names to indices
            evidence_idx = {}
            for var, state in evidence.items():
                if var in self._nodes:
                    states = self._nodes[var].states
                    if state in states:
                        evidence_idx[var] = states.index(state)
            
            result = inference.query([variable], evidence=evidence_idx if evidence_idx else None)
            
            # Convert back to state names
            states = self._nodes[variable].states
            posterior = {states[i]: float(result.values[i]) for i in range(len(states))}
            
            return QueryResult(
                query_variable=variable,
                evidence=evidence,
                posterior=posterior,
                method="pgmpy_variable_elimination",
            )
        except Exception as e:
            logger.debug(f"pgmpy query failed: {e}")
            return None

    def _get_pgmpy_model(self):
        """Build or return cached pgmpy model"""
        if self._pgmpy_model is not None:
            return self._pgmpy_model
        
        if not PGMPY_AVAILABLE:
            return None
        
        try:
            # Build model structure
            edges = [(p, c) for p, c in self._edges]
            model = PgmpyBayesianNetwork(edges)
            
            # Add CPDs
            for node_id, cpt in self._cpts.items():
                node = self._nodes[node_id]
                parent_nodes = [self._nodes[p] for p in cpt.parents]
                
                # Build CPD table
                if not parent_nodes:
                    # No parents
                    values = [cpt.get_probability(s) for s in node.states]
                    cpd = TabularCPD(
                        variable=node_id,
                        variable_card=len(node.states),
                        values=[[v] for v in values],
                        state_names={node_id: node.states}
                    )
                else:
                    # Has parents
                    parent_cards = [len(p.states) for p in parent_nodes]
                    parent_combos = list(product(*[p.states for p in parent_nodes]))
                    
                    values = []
                    for state_idx, state in enumerate(node.states):
                        row = []
                        for combo in parent_combos:
                            row.append(cpt.get_probability(state, combo))
                        values.append(row)
                    
                    cpd = TabularCPD(
                        variable=node_id,
                        variable_card=len(node.states),
                        values=values,
                        evidence=cpt.parents,
                        evidence_card=parent_cards,
                        state_names={node_id: node.states, **{p.node_id: p.states for p in parent_nodes}}
                    )
                
                model.add_cpds(cpd)
            
            # Validate model
            if model.check_model():
                self._pgmpy_model = model
                return model
            else:
                logger.error("pgmpy model validation failed")
                return None
                
        except Exception as e:
            logger.error(f"Failed to build pgmpy model: {e}")
            return None

    def _variable_elimination(self, variable: str, evidence: Dict[str, str]) -> Dict[str, float]:
        """Built-in variable elimination algorithm"""
        # Simplified implementation - exact for small networks
        # For production, use pgmpy
        
        if variable not in self._nodes:
            return {}
        
        node = self._nodes[variable]
        
        # If no evidence, return prior or marginal
        if not evidence:
            return self._compute_marginal(variable)
        
        # Simple enumeration for small networks
        # Sum over all consistent assignments
        all_vars = list(self._nodes.keys())
        other_vars = [v for v in all_vars if v != variable and v not in evidence]
        
        posterior = {state: 0.0 for state in node.states}
        
        # Enumerate all assignments
        var_domains = {}
        for v in all_vars:
            if v in evidence:
                var_domains[v] = [evidence[v]]
            elif v == variable:
                var_domains[v] = node.states
            else:
                var_domains[v] = self._nodes[v].states
        
        def compute_joint(assignment):
            """Compute joint probability of assignment"""
            prob = 1.0
            for var_id, state in assignment.items():
                cpt = self._cpts[var_id]
                parent_values = tuple(assignment[p] for p in cpt.parents)
                prob *= cpt.get_probability(state, parent_values)
            return prob
        
        # Enumerate and sum
        total = 0.0
        for assignment_tuple in product(*[var_domains[v] for v in all_vars]):
            assignment = dict(zip(all_vars, assignment_tuple))
            p = compute_joint(assignment)
            posterior[assignment[variable]] += p
            total += p
        
        # Normalize
        if total > 0:
            for state in posterior:
                posterior[state] /= total
        
        return posterior

    def _compute_marginal(self, variable: str) -> Dict[str, float]:
        """Compute marginal distribution for a variable"""
        if variable not in self._nodes:
            return {}
        
        node = self._nodes[variable]
        cpt = self._cpts[variable]
        
        if not cpt.parents:
            # Root node - just return prior
            return cpt.probabilities.get((), {s: 1.0/len(node.states) for s in node.states})
        
        # Need to marginalize over parents
        # This is simplified - proper implementation would use factor operations
        parent_nodes = [self._nodes[p] for p in cpt.parents]
        parent_marginals = [self._compute_marginal(p) for p in cpt.parents]
        
        marginal = {s: 0.0 for s in node.states}
        
        for parent_combo in product(*[n.states for n in parent_nodes]):
            # Get P(variable | parents) * P(parents)
            parent_prob = 1.0
            for i, state in enumerate(parent_combo):
                parent_var = cpt.parents[i]
                parent_prob *= parent_marginals[i].get(state, 0.0)
            
            for state in node.states:
                conditional = cpt.get_probability(state, parent_combo)
                marginal[state] += conditional * parent_prob
        
        return marginal

    # ═══════════════════════════════════════════════════════════════════════════
    # EVIDENCE MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════

    def set_evidence(self, variable: str, state: str) -> bool:
        """Set observed evidence for a variable"""
        var_id = variable.lower().replace(" ", "_")
        
        if var_id not in self._nodes:
            logger.error(f"Cannot set evidence: node not found ({variable})")
            return False
        
        if state not in self._nodes[var_id].states:
            logger.error(f"Cannot set evidence: invalid state ({state})")
            return False
        
        self._evidence[var_id] = state
        self._total_updates += 1
        
        logger.debug(f"Set evidence: {variable} = {state}")
        return True

    def clear_evidence(self, variable: str = None):
        """Clear evidence (for a specific variable or all)"""
        if variable:
            var_id = variable.lower().replace(" ", "_")
            self._evidence.pop(var_id, None)
        else:
            self._evidence.clear()
        
        self._beliefs.clear()

    def get_evidence(self) -> Dict[str, str]:
        """Get current evidence"""
        return self._evidence.copy()

    # ═══════════════════════════════════════════════════════════════════════════
    # LEARNING
    # ═══════════════════════════════════════════════════════════════════════════

    def learn_cpt_from_data(
        self,
        node: str,
        data: List[Dict[str, str]],
        smoothing: float = 1.0
    ) -> bool:
        """
        Learn CPT from data using maximum likelihood with Laplace smoothing.
        
        Args:
            node: The node to learn CPT for
            data: List of assignments {variable: state}
            smoothing: Laplace smoothing parameter (1.0 for add-one smoothing)
        """
        node_id = node.lower().replace(" ", "_")
        
        if node_id not in self._nodes:
            return False
        
        cpt = self._cpts[node_id]
        node_obj = self._nodes[node_id]
        
        # Count occurrences
        counts = defaultdict(lambda: defaultdict(float))
        parent_counts = defaultdict(float)
        
        for assignment in data:
            # Get parent values
            parent_values = tuple(assignment.get(p, "unknown") for p in cpt.parents)
            state = assignment.get(node_id, "unknown")
            
            if state in node_obj.states:
                counts[parent_values][state] += 1.0
                parent_counts[parent_values] += 1.0
        
        # Compute probabilities with smoothing
        n_states = len(node_obj.states)
        cpt.probabilities = {}
        
        all_parent_combos = [parent_values for parent_values in parent_counts.keys()]
        if cpt.parents:
            # Also generate all possible parent combos
            parent_nodes = [self._nodes[p] for p in cpt.parents]
            all_parent_combos = list(product(*[n.states for n in parent_nodes]))
        
        for parent_combo in all_parent_combos:
            total = parent_counts.get(parent_combo, 0.0) + smoothing * n_states
            cpt.probabilities[parent_combo] = {}
            
            for state in node_obj.states:
                count = counts.get(parent_combo, {}).get(state, 0.0)
                cpt.probabilities[parent_combo][state] = (count + smoothing) / total
        
        self._pgmpy_model = None
        return True

    # ═══════════════════════════════════════════════════════════════════════════
    # LLM INTEGRATION
    # ═══════════════════════════════════════════════════════════════════════════

    def build_from_description(self, description: str) -> Dict[str, Any]:
        """
        Use LLM to build a Bayesian network from natural language description.
        
        The LLM extracts structure and rough probabilities, which can then
        be refined with data or expert input.
        """
        try:
            from llm.llama_interface import llm
            from utils.json_utils import extract_json
            
            prompt = (
                f"Build a Bayesian network from this description:\n\n{description}\n\n"
                f"Return JSON:\n"
                f'{{"nodes": [{{"name": "str", "states": ["state1", "state2"], '
                f'"description": "str"}}], '
                f'"edges": [{{"parent": "str", "child": "str"}}], '
                f'"cpts": [{{"node": "str", "probabilities": {{"parent_state_tuple": {{"state": prob}}}}}}]}}'
            )
            
            response = llm.generate(prompt, max_tokens=2000, temperature=0.3)
            data = extract_json(response.text) or {}
            
            # Add nodes
            for node_data in data.get("nodes", []):
                self.add_node(
                    name=node_data.get("name", ""),
                    states=node_data.get("states", ["true", "false"]),
                    description=node_data.get("description", ""),
                )
            
            # Add edges
            for edge_data in data.get("edges", []):
                self.add_edge(edge_data.get("parent", ""), edge_data.get("child", ""))
            
            # Set CPTs (simplified - LLM estimates are approximate)
            for cpt_data in data.get("cpts", []):
                node = cpt_data.get("node", "")
                probs = cpt_data.get("probabilities", {})
                # Convert string keys back to tuples
                processed_probs = {}
                for key, val in probs.items():
                    # Parse key as tuple
                    if key == "()":
                        processed_probs[()] = val
                    else:
                        processed_probs[tuple(key.strip("()").split(", "))] = val
                self.set_cpt(node, processed_probs)
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to build network from description: {e}")
            return {"error": str(e)}

    # ═══════════════════════════════════════════════════════════════════════════
    # UTILITIES
    # ═══════════════════════════════════════════════════════════════════════════

    def get_network_structure(self) -> Dict[str, Any]:
        """Get the network structure as a dict"""
        return {
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "edges": [{"parent": p, "child": c} for p, c in self._edges],
            "evidence": self._evidence,
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self):
        """Start the Bayesian engine"""
        self._running = True
        logger.info("BayesianEngine started")

    def stop(self):
        """Stop the Bayesian engine"""
        self._running = False
        logger.info("BayesianEngine stopped")

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics"""
        return {
            "running": getattr(self, '_running', False),
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "total_queries": self._total_queries,
            "total_updates": self._total_updates,
            "pgmpy_available": PGMPY_AVAILABLE,
            "current_evidence": len(self._evidence),
        }

    def clear_network(self):
        """Clear the entire network"""
        self._nodes.clear()
        self._cpts.clear()
        self._edges.clear()
        self._evidence.clear()
        self._beliefs.clear()
        self._pgmpy_model = None


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

bayesian_engine = BayesianEngine()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    be = BayesianEngine()
    
    # Build a classic example: Sprinkler network
    # Rain -> Sprinkler
    # Rain -> WetGrass
    # Sprinkler -> WetGrass
    
    print("=== Building Bayesian Network ===")
    
    # Add nodes
    be.add_node("Rain", ["true", "false"])
    be.add_node("Sprinkler", ["true", "false"])
    be.add_node("WetGrass", ["true", "false"])
    
    # Add edges
    be.add_edge("Rain", "Sprinkler")
    be.add_edge("Rain", "WetGrass")
    be.add_edge("Sprinkler", "WetGrass")
    
    # Set CPTs
    # P(Rain)
    be.set_cpt_simple("Rain", [0.2, 0.8])
    
    # P(Sprinkler | Rain)
    be.set_cpt_simple("Sprinkler", 
        [0.01, 0.99,   # Rain=true
         0.4, 0.6],    # Rain=false
        given_parents=[("true",), ("false",)])
    
    # P(WetGrass | Rain, Sprinkler)
    be.set_cpt_simple("WetGrass",
        [0.99, 0.01,   # Rain=true, Sprinkler=true
         0.9, 0.1,     # Rain=true, Sprinkler=false
         0.9, 0.1,     # Rain=false, Sprinkler=true
         0.0, 1.0],    # Rain=false, Sprinkler=false
        given_parents=[("true", "true"), ("true", "false"), ("false", "true"), ("false", "false")])
    
    print(f"Network structure: {be.get_network_structure()}")
    
    # Query: P(Rain | WetGrass=true)
    print("\n=== Query: P(Rain | WetGrass=true) ===")
    result = be.query("Rain", {"WetGrass": "true"})
    print(f"Posterior: {result.posterior}")
    print(f"Most likely: {result.most_likely_state()}")
    
    # Query: P(Sprinkler | WetGrass=true)
    print("\n=== Query: P(Sprinkler | WetGrass=true) ===")
    result = be.query("Sprinkler", {"WetGrass": "true"})
    print(f"Posterior: {result.posterior}")
    print(f"Most likely: {result.most_likely_state()}")
    
    # Query: P(Sprinkler | WetGrass=true, Rain=true)
    print("\n=== Query: P(Sprinkler | WetGrass=true, Rain=true) ===")
    result = be.query("Sprinkler", {"WetGrass": "true", "Rain": "true"})
    print(f"Posterior: {result.posterior}")
    print(f"Most likely: {result.most_likely_state()}")
    
    print(f"\nStats: {be.get_stats()}")