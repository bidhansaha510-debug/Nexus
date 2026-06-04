"""
Test script for Vector Memory functionality
Tests the semantic search and associative memory capabilities
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from core.memory_system import MemorySystem, MemoryType

def test_vector_memory():
    """Test vector memory functionality"""
    print("=" * 60)
    print("NEXUS Vector Memory Test")
    print("=" * 60)
    
    # Initialize memory system
    ms = MemorySystem()
    
    print("\n1. Testing memory storage...")
    
    # Store test memories
    ms.remember(
        content="User's dog named Buddy is a golden retriever who loves playing fetch",
        memory_type=MemoryType.USER_PATTERN,
        importance=0.7,
        tags=["pet", "dog", "buddy"]
    )
    
    ms.remember(
        content="Had an amazing trip to Paris last summer, visited the Eiffel Tower at sunset",
        memory_type=MemoryType.EPISODIC,
        importance=0.8,
        emotional_valence=0.9,
        tags=["travel", "paris", "vacation", "france"]
    )
    
    ms.remember(
        content="User loves pizza with extra cheese and pepperoni",
        memory_type=MemoryType.USER_PATTERN,
        importance=0.6,
        tags=["food", "preference", "pizza"]
    )
    
    ms.remember(
        content="The Eiffel Tower was breathtaking, we had dinner at a cafe nearby",
        memory_type=MemoryType.EPISODIC,
        importance=0.7,
        emotional_valence=0.8,
        tags=["travel", "paris", "dinner"]
    )
    
    print("   Stored 4 test memories")
    
    # Test regular recall
    print("\n2. Testing regular keyword recall...")
    results = ms.recall(query="paris", limit=3)
    print(f"   Query: 'paris' -> Found {len(results)} memories")
    for r in results:
        print(f"   - [{r.memory_type.value}] {r.content[:60]}...")
    
    # Test associative recall (semantic search)
    print("\n3. Testing ASSOCIATIVE recall (semantic search)...")
    print("   This finds related memories even without keyword matches!")
    
    # Test 1: "France vacation" should find Paris memories
    print("\n   Query: 'France vacation' (should find Paris memories)")
    results = ms.recall_associative(query="France vacation", n_results=3)
    for r in results:
        print(f"   - [{r['type']}] {r['content'][:60]}... (relevance: {r['relevance']:.2f})")
    
    # Test 2: "My pet" should find dog memories
    print("\n   Query: 'My pet' (should find dog/Buddy memories)")
    results = ms.recall_associative(query="My pet", n_results=3)
    for r in results:
        print(f"   - [{r['type']}] {r['content'][:60]}... (relevance: {r['relevance']:.2f})")
    
    # Test 3: "What food do I like?" should find pizza
    print("\n   Query: 'What food do I like' (should find pizza)")
    results = ms.recall_associative(query="What food do I like", n_results=3)
    for r in results:
        print(f"   - [{r['type']}] {r['content'][:60]}... (relevance: {r['relevance']:.2f})")
    
    # Test 4: "That time in Europe" should find Paris/France memories
    print("\n   Query: 'That time in Europe' (should find travel memories)")
    results = ms.recall_associative(query="That time in Europe", n_results=3)
    for r in results:
        print(f"   - [{r['type']}] {r['content'][:60]}... (relevance: {r['relevance']:.2f})")
    
    # Test semantic recall with memory type filter
    print("\n4. Testing semantic recall with filters...")
    results = ms.recall_semantic(
        query="travel adventure",
        memory_type=MemoryType.EPISODIC,
        n_results=5
    )
    print(f"   Query: 'travel adventure' (episodic only) -> {len(results)} results")
    for mem, score in results:
        print(f"   - [{mem.memory_type.value}] {mem.content[:50]}... (similarity: {score:.2f})")
    
    # Test vector stats
    print("\n5. Vector Memory Statistics:")
    stats = ms.get_vector_stats()
    print(f"   Enabled: {stats.get('enabled', False)}")
    if stats.get('enabled'):
        print(f"   Total vector memories: {stats.get('total_memories', 0)}")
        print(f"   By type: {stats.get('by_type', {})}")
    
    # Regular stats
    print("\n6. Overall Memory Statistics:")
    stats = ms.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)


if __name__ == "__main__":
    test_vector_memory()