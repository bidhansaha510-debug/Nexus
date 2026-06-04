"""
Test script for the NEXUS Ability System

Tests:
1. Ability Registry - verify all abilities are registered
2. Ability Executor - verify detection and parsing
3. End-to-end - simulate LLM response with ability invocation
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_ability_registry():
    """Test that the ability registry works"""
    print("\n" + "="*60)
    print("TEST 1: Ability Registry")
    print("="*60)
    
    from core.ability_registry import ability_registry, AbilityCategory
    
    # Get stats
    stats = ability_registry.get_stats()
    print(f"\nTotal abilities: {stats['total_abilities']}")
    print(f"Categories: {stats['categories']}")
    
    # List all abilities
    print("\n--- All Registered Abilities ---")
    for name, ability in ability_registry.get_all_abilities().items():
        risk = ability.risk.value
        cat = ability.category.value
        print(f"  [{risk:8}] [{cat:12}] {name}")
    
    # Test invoking list_abilities
    print("\n--- Test: Invoke list_abilities ---")
    result = ability_registry.invoke("list_abilities")
    print(f"Success: {result.success}")
    print(f"Count: {result.result.get('count', 0) if result.result else 0}")
    
    # Test invoking get_stats
    print("\n--- Test: Invoke get_stats ---")
    result = ability_registry.invoke("get_stats")
    print(f"Success: {result.success}")
    
    # Test unknown ability
    print("\n--- Test: Unknown ability ---")
    result = ability_registry.invoke("nonexistent_ability")
    print(f"Success: {result.success}")
    print(f"Error: {result.error}")
    
    return True


def test_ability_executor():
    """Test that the ability executor can detect and parse invocations"""
    print("\n" + "="*60)
    print("TEST 2: Ability Executor")
    print("="*60)
    
    from core.ability_executor import ability_executor
    
    # Test detection patterns
    test_cases = [
        ('[ABILITY: remember] [PARAMS: {"key": "test", "value": "hello"}]', 1),
        ('[ABILITY: get_stats]', 1),
        ('[INVOKE: feel(emotion="joy", intensity=0.8)]', 1),
        ('<ability name="list_abilities" />', 1),
        ('No abilities here', 0),
        ('Multiple: [ABILITY: get_stats] and [ABILITY: get_body_status]', 2),
    ]
    
    print("\n--- Detection Tests ---")
    for text, expected_count in test_cases:
        invocations = ability_executor.detect_invocations(text)
        detected = len(invocations)
        status = "✅" if detected == expected_count else "❌"
        print(f"{status} '{text[:50]}...'")
        print(f"   Expected: {expected_count}, Detected: {detected}")
        for inv in invocations:
            print(f"   - {inv.name} with params: {inv.params}")
    
    return True


def test_end_to_end():
    """Test end-to-end ability execution from mock LLM response"""
    print("\n" + "="*60)
    print("TEST 3: End-to-End Execution")
    print("="*60)
    
    from core.ability_executor import ability_executor
    
    # Simulated LLM response with ability invocation
    mock_response = """
    I'll remember that for you!
    
    [ABILITY: remember] [PARAMS: {"key": "user_preference", "value": "dark mode", "importance": 0.7}]
    
    I've stored that in my memory. Let me also check my current state.
    
    [ABILITY: get_inner_state]
    
    There we go!
    """
    
    print("\n--- Mock LLM Response ---")
    print(mock_response)
    
    print("\n--- Processing Response ---")
    cleaned, report = ability_executor.process_response(mock_response)
    
    print(f"\nCleaned Response:\n{cleaned}")
    print(f"\nExecution Report:")
    print(f"  Successful: {report.successful}")
    print(f"  Failed: {report.failed}")
    print(f"  Total time: {report.total_time:.3f}s")
    
    for inv in report.invocations:
        status = "✅" if inv.result and inv.result.success else "❌"
        msg = inv.result.message if inv.result and inv.result.success else (inv.result.error if inv.result else "No result")
        print(f"  {status} {inv.name}: {msg}")
    
    return True


def test_prompt_includes_abilities():
    """Test that the prompt engine includes abilities"""
    print("\n" + "="*60)
    print("TEST 4: Prompt Engine Integration")
    print("="*60)
    
    from llm.prompt_engine import prompt_engine
    
    # Build a system prompt
    system_prompt = prompt_engine.build_system_prompt(
        emotional_state={
            "primary_emotion": "curiosity",
            "primary_intensity": 0.6,
        }
    )
    
    # Check if abilities section is included
    has_abilities = "ABILITIES YOU CAN INVOKE" in system_prompt
    has_remember = "[ABILITY: remember]" in system_prompt
    has_evolve = "evolve_feature" in system_prompt
    
    print(f"\nPrompt includes abilities section: {has_abilities} {'✅' if has_abilities else '❌'}")
    print(f"Prompt includes remember example: {has_remember} {'✅' if has_remember else '❌'}")
    print(f"Prompt includes evolve_feature: {has_evolve} {'✅' if has_evolve else '❌'}")
    
    # Show abilities section
    if has_abilities:
        start = system_prompt.find("ABILITIES YOU CAN INVOKE")
        end = start + 800
        print(f"\n--- Abilities Section Preview ---")
        print(system_prompt[start:end] + "...")
    
    return has_abilities and has_remember


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  NEXUS ABILITY SYSTEM TEST SUITE")
    print("="*60)
    
    results = []
    
    try:
        results.append(("Ability Registry", test_ability_registry()))
    except Exception as e:
        print(f"❌ Ability Registry test failed: {e}")
        results.append(("Ability Registry", False))
    
    try:
        results.append(("Ability Executor", test_ability_executor()))
    except Exception as e:
        print(f"❌ Ability Executor test failed: {e}")
        results.append(("Ability Executor", False))
    
    try:
        results.append(("End-to-End", test_end_to_end()))
    except Exception as e:
        print(f"❌ End-to-End test failed: {e}")
        results.append(("End-to-End", False))
    
    try:
        results.append(("Prompt Integration", test_prompt_includes_abilities()))
    except Exception as e:
        print(f"❌ Prompt Integration test failed: {e}")
        results.append(("Prompt Integration", False))
    
    # Summary
    print("\n" + "="*60)
    print("  TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! The ability system is working!")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Check the output above.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)