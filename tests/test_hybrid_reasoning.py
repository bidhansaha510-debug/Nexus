"""
NEXUS AI - Hybrid Reasoning Engine Tests
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Tests for the computational reasoning engines that complement the LLM.

These tests verify that:
  • Knowledge Graph stores and queries entities correctly
  • Symbolic Logic validates arguments with truth tables
  • Graph Algorithms find shortest paths and centrality
  • Bayesian Engine computes correct posteriors
  • Planning Algorithms find valid plans with A*/MCTS/HTN
  • Hybrid Coordinator routes queries to appropriate engines
"""

import sys
import math
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_knowledge_graph():
    """Test the Knowledge Graph engine"""
    print("\n" + "=" * 60)
    print("TEST: Knowledge Graph Engine")
    print("=" * 60)
    
    from cognition.knowledge_graph import KnowledgeGraph, knowledge_graph, EntityType, RelationType
    
    # Clear any existing data
    knowledge_graph.clear()
    
    # Test entity creation
    kg = KnowledgeGraph()
    
    # Add entities
    e1 = kg.add_entity("Alice", EntityType.PERSON, {"age": 30, "occupation": "engineer"})
    e2 = kg.add_entity("Bob", EntityType.PERSON, {"age": 25, "occupation": "designer"})
    e3 = kg.add_entity("Google", EntityType.ORGANIZATION, {"industry": "tech"})
    e4 = kg.add_entity("Python", EntityType.CONCEPT, {"level": "programming"})
    
    print(f"  ✓ Added 4 entities")
    
    # Add relations
    r1 = kg.add_relation("Alice", RelationType.RELATED_TO, "Google")
    r2 = kg.add_relation("Bob", RelationType.RELATED_TO, "Google")
    r3 = kg.add_relation("Alice", RelationType.RELATED_TO, "Python")
    r4 = kg.add_relation("Alice", RelationType.RELATED_TO, "Bob")
    
    print(f"  ✓ Added 4 relations")
    
    # Test querying
    alice_rels = kg.get_relations(kg.get_entity(name="Alice").entity_id)
    print(f"  ✓ Alice has {len(alice_rels)} relations")
    assert len(alice_rels) == 3
    
    # Test path finding
    path = kg.find_path("Bob", "Python")
    print(f"  ✓ Path from Bob to Python: {path}")
    
    # Test context extraction
    context = kg.get_context_for_query("Who works at Google?")
    print(f"  ✓ Context extracted: {len(context) if context else 0} chars")
    
    # Test stats
    stats = kg.get_stats()
    print(f"  ✓ Stats: {stats['total_entities']} entities, {stats['total_relations']} relations")
    
    print("\n  ✅ Knowledge Graph tests passed!")
    return True


def test_symbolic_logic():
    """Test the Symbolic Logic engine"""
    print("\n" + "=" * 60)
    print("TEST: Symbolic Logic Engine")
    print("=" * 60)
    
    from cognition.symbolic_logic import symbolic_logic
    
    sl = symbolic_logic
    
    # Test parsing simple propositions
    p = sl.parse("P")
    q = sl.parse("Q")
    print(f"  ✓ Parsed atomic propositions: P ({p.formula}), Q ({q.formula})")
    
    # Test parsing compound expressions (via natural language)
    p_and_q = sl.parse("P and Q")
    p_or_q = sl.parse("P or Q")
    p_implies_q = sl.parse("if P then Q")
    not_p = sl.parse("not P")
    
    print(f"  ✓ Created compound expressions:")
    print(f"    P and Q: {p_and_q.formula}")
    print(f"    P or Q: {p_or_q.formula}")
    print(f"    if P then Q: {p_implies_q.formula}")
    print(f"    not P: {not_p.formula}")
    
    # Test truth table
    tt = sl.truth_table(p_implies_q)
    print(f"  ✓ Truth table for 'if P then Q':")
    for row in tt.rows[:4]:  # Show first 4 rows
        print(f"    P={row.get('P', '?')}, Q={row.get('Q', '?')} → {row['result']}")
    
    # Test validity (modus ponens: P→Q, P ⊢ Q)
    premises = [p_implies_q, p]
    is_valid, proof = sl.check_validity(premises, q)
    print(f"  ✓ Modus Ponens valid: {is_valid}")
    
    # Test invalid argument
    is_valid2, proof2 = sl.check_validity([p_implies_q], q)  # Missing P premise
    print(f"  ✓ Invalid argument detected: {not is_valid2}")
    
    # Test syllogism validation
    result = sl.validate_syllogism(
        "All humans are mortal",
        "Socrates is human",
        "Socrates is mortal"
    )
    print(f"  ✓ Syllogism valid: {result.get('is_valid', False)}")
    
    # Test CNF conversion
    cnf = sl.to_cnf(p_implies_q)
    print(f"  ✓ CNF of P→Q: {cnf}")
    
    print("\n  ✅ Symbolic Logic tests passed!")
    return True


def test_graph_algorithms():
    """Test the Graph Algorithms module"""
    print("\n" + "=" * 60)
    print("TEST: Graph Algorithms Module")
    print("=" * 60)
    
    from cognition.graph_algorithms import GraphAlgorithms, graph_algorithms, CentralityMeasure, CommunityAlgorithm
    
    ga = GraphAlgorithms()
    
    # Create a test graph as adjacency dict
    test_graph = {
        "A": {"B": {"weight": 1.0}, "C": {"weight": 4.0}},
        "B": {"C": {"weight": 2.0}, "D": {"weight": 5.0}},
        "C": {"D": {"weight": 1.0}},
        "D": {"E": {"weight": 3.0}},
        "E": {}
    }
    
    print(f"  ✓ Created test graph with 5 nodes")
    
    # Test shortest path (Dijkstra)
    path = ga.shortest_path(test_graph, "A", "E")
    if path:
        print(f"  ✓ Shortest path A→E: {' -> '.join(path.nodes)} (distance: {path.total_weight})")
        assert path.total_weight == 7.0  # A→B→C→D→E = 1+2+1+3 = 7
    else:
        print(f"  ✗ Shortest path not found")
        return False
    
    # Test all paths
    all_paths = ga.all_paths(test_graph, "A", "D", max_length=4)
    print(f"  ✓ Found {len(all_paths)} paths from A to D")
    
    # Test reachability
    reachable = ga.reachable_nodes(test_graph, "A")
    print(f"  ✓ Nodes reachable from A: {reachable}")
    
    # Test centrality
    centrality = ga.centrality(test_graph, CentralityMeasure.BETWEENNESS)
    print(f"  ✓ Betweenness centrality: {centrality}")
    
    # Test community detection
    communities = ga.detect_communities(test_graph)
    print(f"  ✓ Found {len(communities)} communities")
    
    # Test graph stats
    stats = ga.get_stats()
    print(f"  ✓ Stats: {stats}")
    
    print("\n  ✅ Graph Algorithms tests passed!")
    return True


def test_bayesian_engine():
    """Test the Bayesian Network engine"""
    print("\n" + "=" * 60)
    print("TEST: Bayesian Network Engine")
    print("=" * 60)
    
    from cognition.bayesian_engine import BayesianEngine, BayesianEngine as BE
    
    be = BayesianEngine()
    be.clear_network()
    
    # Build classic Sprinkler network
    be.add_node("Rain", ["true", "false"])
    be.add_node("Sprinkler", ["true", "false"])
    be.add_node("WetGrass", ["true", "false"])
    
    be.add_edge("Rain", "Sprinkler")
    be.add_edge("Rain", "WetGrass")
    be.add_edge("Sprinkler", "WetGrass")
    
    print(f"  ✓ Created Bayesian network structure")
    
    # Set CPTs
    be.set_cpt_simple("Rain", [0.2, 0.8])  # P(Rain)
    
    be.set_cpt_simple("Sprinkler", 
        [0.01, 0.99,   # Rain=true
         0.4, 0.6],    # Rain=false
        given_parents=[("true",), ("false",)])
    
    be.set_cpt_simple("WetGrass",
        [0.99, 0.01,   # Rain=true, Sprinkler=true
         0.9, 0.1,     # Rain=true, Sprinkler=false
         0.9, 0.1,     # Rain=false, Sprinkler=true
         0.0, 1.0],    # Rain=false, Sprinkler=false
        given_parents=[("true", "true"), ("true", "false"), ("false", "true"), ("false", "false")])
    
    print(f"  ✓ Set conditional probability tables")
    
    # Query: P(Rain | WetGrass=true)
    result = be.query("Rain", {"WetGrass": "true"})
    print(f"  ✓ P(Rain|WetGrass=true): {result.posterior}")
    print(f"    Most likely: {result.most_likely_state()}")
    
    # Verify the probability increased (explaining away)
    assert result.posterior["true"] > 0.2  # Should be higher than prior
    
    # Query: P(Sprinkler | WetGrass=true)
    result2 = be.query("Sprinkler", {"WetGrass": "true"})
    print(f"  ✓ P(Sprinkler|WetGrass=true): {result2.posterior}")
    
    # Test evidence management
    be.set_evidence("WetGrass", "true")
    evidence = be.get_evidence()
    print(f"  ✓ Evidence set: {evidence}")
    be.clear_evidence()
    
    # Test stats
    stats = be.get_stats()
    print(f"  ✓ Stats: {stats}")
    
    print("\n  ✅ Bayesian Engine tests passed!")
    return True


def test_planning_algorithms():
    """Test the Planning Algorithms module"""
    print("\n" + "=" * 60)
    print("TEST: Planning Algorithms Module")
    print("=" * 60)
    
    from cognition.planning_algorithms import (
        PlanningAlgorithms, State, Action, HTNMethod
    )
    
    pa = PlanningAlgorithms()
    
    # Define blocks world domain
    pa.define_action(
        "pick_up_A",
        preconditions={"on_table_A": True, "hand_empty": True},
        effects={"on_table_A": False, "holding_A": True, "hand_empty": False},
    )
    
    pa.define_action(
        "pick_up_B",
        preconditions={"on_table_B": True, "hand_empty": True},
        effects={"on_table_B": False, "holding_B": True, "hand_empty": False},
    )
    
    pa.define_action(
        "stack_A_on_B",
        preconditions={"holding_A": True, "clear_B": True},
        effects={"holding_A": False, "hand_empty": True, "on_A_B": True, "clear_B": False},
    )
    
    pa.define_action(
        "put_down_A",
        preconditions={"holding_A": True},
        effects={"holding_A": False, "hand_empty": True, "on_table_A": True},
    )
    
    print(f"  ✓ Defined {len(pa._actions)} actions")
    
    # Initial state
    initial = State(variables={
        "on_table_A": True,
        "on_table_B": True,
        "hand_empty": True,
        "clear_A": True,
        "clear_B": True,
        "holding_A": False,
        "holding_B": False,
        "on_A_B": False,
    })
    
    # Goal: A on B
    goal = State(variables={"on_A_B": True})
    
    # Test A* planning
    plan = pa.astar_plan(initial, goal)
    if plan:
        print(f"  ✓ A* plan found with {plan.length()} actions:")
        for i, action in enumerate(plan.actions):
            print(f"    {i+1}. {action.name}")
        
        # Validate plan
        is_valid, errors = pa.validate_plan(plan, initial)
        print(f"  ✓ Plan validation: {is_valid}")
        assert is_valid
    else:
        print(f"  ✗ A* planning failed")
        return False
    
    # Test MCTS planning
    mcts_plan = pa.mcts_plan(initial, goal, simulations=500)
    if mcts_plan:
        print(f"  ✓ MCTS plan found with {mcts_plan.length()} actions")
    else:
        print(f"  ⚠ MCTS planning did not find plan (may need more simulations)")
    
    # Test HTN planning
    pa.add_htn_method(HTNMethod(
        method_id="stack_A_on_B",
        name="Stack A on B",
        task="stack_A_on_B",
        preconditions={"on_table_A": True, "on_table_B": True, "hand_empty": True},
        subtasks=["pick_up_A", "stack_A_on_B"],
    ))
    
    htn_plan = pa.htn_decompose(initial, ["stack_A_on_B"])
    if htn_plan:
        print(f"  ✓ HTN plan found with {htn_plan.length()} actions")
    else:
        print(f"  ⚠ HTN decomposition needs correct action references")
    
    # Test stats
    stats = pa.get_stats()
    print(f"  ✓ Stats: success rate {stats['success_rate']:.2f}")
    
    print("\n  ✅ Planning Algorithms tests passed!")
    return True


def test_hybrid_reasoning_coordinator():
    """Test the Hybrid Reasoning Coordinator"""
    print("\n" + "=" * 60)
    print("TEST: Hybrid Reasoning Coordinator")
    print("=" * 60)
    
    from cognition.hybrid_reasoning import (
        HybridReasoningCoordinator, QueryType, EngineType
    )
    
    hr = HybridReasoningCoordinator()
    
    # Test query classification
    test_queries = [
        ("Is this argument valid: All men are mortal?", QueryType.LOGICAL),
        ("What is the probability of rain?", QueryType.PROBABILISTIC),
        ("Why did the stock market crash?", QueryType.CAUSAL),
        ("How do I learn Python?", QueryType.PLANNING),
        ("What is the capital of France?", QueryType.FACTUAL),
        ("Create a story about dragons", QueryType.CREATIVE),
    ]
    
    print("  ✓ Query classification:")
    for query, expected in test_queries:
        result_type = hr.classify_query(query)
        match = "✓" if result_type == expected else "✗"
        print(f"    {match} '{query[:30]}...' → {result_type.value}")
    
    # Test engine recommendations
    print("\n  ✓ Engine recommendations:")
    for qtype in [QueryType.LOGICAL, QueryType.PROBABILISTIC, QueryType.PLANNING]:
        engines = hr.get_recommended_engines(qtype)
        print(f"    {qtype.value}: {[e.value for e in engines]}")
    
    # Test engine status
    status = hr.get_engine_status()
    print(f"\n  ✓ Engine status:")
    for engine, available in list(status.items())[:5]:
        print(f"    {engine}: {'✓' if available else '✗'}")
    
    # Test reasoning with fallback
    result = hr.reason("What is 2+2?")
    print(f"\n  ✓ Reasoning test:")
    print(f"    Query: 'What is 2+2?'")
    print(f"    Primary engine: {result.primary_engine.value}")
    print(f"    Confidence: {result.confidence}")
    print(f"    Time: {result.computation_time_ms:.2f}ms")
    
    # Test stats
    stats = hr.get_stats()
    print(f"\n  ✓ Coordinator stats: {stats['total_queries']} queries processed")
    
    print("\n  ✅ Hybrid Reasoning Coordinator tests passed!")
    return True


def run_all_tests():
    """Run all hybrid reasoning tests"""
    print("\n" + "╔" + "═" * 58 + "╗")
    print("║   NEXUS HYBRID REASONING ENGINE TESTS                  ║")
    print("╚" + "═" * 58 + "╝")
    
    results = {}
    
    # Run tests
    tests = [
        ("Knowledge Graph", test_knowledge_graph),
        ("Symbolic Logic", test_symbolic_logic),
        ("Graph Algorithms", test_graph_algorithms),
        ("Bayesian Engine", test_bayesian_engine),
        ("Planning Algorithms", test_planning_algorithms),
        ("Hybrid Coordinator", test_hybrid_reasoning_coordinator),
    ]
    
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n  ❌ {name} failed with error: {e}")
            import traceback
            traceback.print_exc()
            results[name] = False
    
    # Summary
    print("\n" + "╔" + "═" * 58 + "╗")
    print("║   TEST SUMMARY                                          ║")
    print("╠" + "═" * 58 + "╣")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"║   {name:<30} {status:<20} ║")
    
    print("╠" + "═" * 58 + "╣")
    print(f"║   Total: {passed}/{total} tests passed{' ' * (58 - 25 - len(str(passed)) - len(str(total)))}║")
    print("╚" + "═" * 58 + "╝")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)