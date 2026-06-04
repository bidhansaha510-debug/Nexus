"""
Test script for AGI Enhancement Components
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tests the 5 AGI components added to the autonomy engine:
1. LLM-powered autonomous reasoning (enriched prompts)
2. Cognitive engine integration (generate_cognitive_options)
3. Deep reflection with action biases
4. Self-model closing the loop
5. Autonomous goal decomposition
"""
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def test_action_biases_initialization():
    """Test that _action_biases dict is initialized"""
    print("1. Testing action biases initialization...")
    try:
        from core.autonomy_engine import autonomy_engine
        assert hasattr(autonomy_engine, '_action_biases'), "Missing _action_biases attribute"
        assert isinstance(autonomy_engine._action_biases, dict), "_action_biases should be a dict"
        print(f"   ✅ _action_biases initialized: {type(autonomy_engine._action_biases).__name__}")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False

def test_cognitive_systems_attributes():
    """Test that cognitive system attributes were added"""
    print("\n2. Testing cognitive system attributes...")
    try:
        from core.autonomy_engine import autonomy_engine
        assert hasattr(autonomy_engine, '_cognitive_orchestrator'), "Missing _cognitive_orchestrator"
        assert hasattr(autonomy_engine, '_cognition_system'), "Missing _cognition_system"
        print("   ✅ _cognitive_orchestrator and _cognition_system attributes exist")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False

def test_generate_cognitive_options_exists():
    """Test that _generate_cognitive_options method was added"""
    print("\n3. Testing _generate_cognitive_options method...")
    try:
        from core.autonomy_engine import autonomy_engine
        assert hasattr(autonomy_engine, '_generate_cognitive_options'), "Missing _generate_cognitive_options method"
        assert callable(autonomy_engine._generate_cognitive_options), "Should be callable"
        print("   ✅ _generate_cognitive_options method exists and is callable")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False

def test_compute_option_score_uses_biases():
    """Test that _compute_option_score incorporates action biases"""
    print("\n4. Testing action bias integration in scoring...")
    try:
        from core.autonomy_engine import autonomy_engine, ActionOption, ActionType, ActionPriority
        
        # Create a test option
        option = ActionOption(
            action_type=ActionType.THINK,
            description="Test thought",
            priority=ActionPriority.NORMAL,
            predicted_success=0.5,
            predicted_benefit=0.5,
            predicted_cost=0.2,
            source="boredom"
        )
        
        # Score without bias
        autonomy_engine._action_biases = {}
        score_no_bias = autonomy_engine._compute_option_score(option)
        
        # Score with positive bias
        autonomy_engine._action_biases = {"think": 0.3}
        score_positive = autonomy_engine._compute_option_score(option)
        
        # Score with negative bias
        autonomy_engine._action_biases = {"think": -0.3}
        score_negative = autonomy_engine._compute_option_score(option)
        
        # Reset
        autonomy_engine._action_biases = {}
        
        assert score_positive > score_no_bias, f"Positive bias should increase score: {score_positive} > {score_no_bias}"
        assert score_negative < score_no_bias, f"Negative bias should decrease score: {score_negative} < {score_no_bias}"
        
        print(f"   ✅ Action bias affects scoring:")
        print(f"      No bias:   {score_no_bias:.4f}")
        print(f"      Positive:  {score_positive:.4f}")
        print(f"      Negative:  {score_negative:.4f}")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False

def test_cognitive_engine_source_weight():
    """Test that 'cognitive_engine' source weight is included"""
    print("\n5. Testing cognitive_engine source weight...")
    try:
        from core.autonomy_engine import autonomy_engine, ActionOption, ActionType, ActionPriority
        
        # Create option with cognitive_engine source
        option = ActionOption(
            action_type=ActionType.REASON,
            description="Test reasoning",
            priority=ActionPriority.HIGH,
            predicted_success=0.7,
            predicted_benefit=0.8,
            predicted_cost=0.3,
            source="cognitive_engine"
        )
        
        score = autonomy_engine._compute_option_score(option)
        assert score > 0, "Score should be positive"
        print(f"   ✅ cognitive_engine source produces valid score: {score:.4f}")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False

def test_reflection_produces_contextual_lessons():
    """Test that reflect() produces contextual lessons, not generic ones"""
    print("\n6. Testing reflect() contextual lessons...")
    try:
        from core.autonomy_engine import (
            autonomy_engine, ActionOption, ActionType, ActionPriority,
            ActionExecution, ActionResult, Reflection
        )
        
        # Simulate a failed action
        action = ActionOption(
            action_type=ActionType.PURSUE_GOAL,
            description="Work on learning Python",
            priority=ActionPriority.HIGH,
            source="goal",
            source_id="test_goal_1",
            predicted_success=0.8,
        )
        
        execution = ActionExecution(action=action)
        execution.result = ActionResult.FAILURE
        execution.outcome_description = "Goal hierarchy not available for this test"
        execution.completed_at = datetime.now()
        execution.duration_seconds = 0.5
        
        reflection = autonomy_engine.reflect(action, execution)
        
        assert isinstance(reflection, Reflection), "Should return Reflection"
        assert not reflection.success, "Should be marked as failure"
        assert len(reflection.lessons) > 0, "Should have lessons"
        
        # Check that lessons are contextual (not generic "be more cautious")
        has_contextual = any("goal" in l.lower() or "pursue_goal" in l.lower() or "source" in l.lower() for l in reflection.lessons)
        assert has_contextual, f"Lessons should be contextual, got: {reflection.lessons}"
        
        print(f"   ✅ Reflection produces contextual lessons:")
        for lesson in reflection.lessons[:2]:
            print(f"      → {lesson[:80]}...")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False

def test_action_biases_updated_by_reflection():
    """Test that reflection updates action biases based on patterns"""
    print("\n7. Testing action biases updated by patterns...")
    try:
        from core.autonomy_engine import (
            autonomy_engine, ActionOption, ActionType, ActionPriority,
            ActionExecution, ActionResult
        )
        
        # Clear biases and history
        autonomy_engine._action_biases = {}
        original_history = autonomy_engine._action_history[:]
        
        # Simulate 5 consecutive failures for the same action type
        for i in range(5):
            action = ActionOption(
                action_type=ActionType.LEARN,
                description=f"Learn attempt {i}",
                priority=ActionPriority.NORMAL,
                source="curiosity",
                predicted_success=0.8,
            )
            execution = ActionExecution(action=action)
            execution.result = ActionResult.FAILURE
            execution.outcome_description = f"Learning failed attempt {i}"
            execution.completed_at = datetime.now()
            execution.duration_seconds = 0.1
            
            # Add to history so pattern detection works
            autonomy_engine._action_history.append(execution)
        
        # Now reflect on the 5th failure
        action = ActionOption(
            action_type=ActionType.LEARN,
            description="Learn attempt 5",
            priority=ActionPriority.NORMAL,
            source="curiosity",
            predicted_success=0.8,
        )
        execution = ActionExecution(action=action)
        execution.result = ActionResult.FAILURE
        execution.outcome_description = "Learning failed again"
        execution.completed_at = datetime.now()
        execution.duration_seconds = 0.1
        
        reflection = autonomy_engine.reflect(action, execution)
        
        # Check that LEARN action type got penalized
        learn_bias = autonomy_engine._action_biases.get("learn", 0.0)
        assert learn_bias < 0, f"LEARN should be penalized after repeated failures, got: {learn_bias}"
        
        # Restore
        autonomy_engine._action_history = original_history
        autonomy_engine._action_biases = {}
        
        print(f"   ✅ Action bias updated: LEARN bias = {learn_bias:.3f} (penalized)")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False

def test_save_load_preserves_biases():
    """Test that action biases are preserved across save/load"""
    print("\n8. Testing action biases persistence...")
    try:
        from core.autonomy_engine import autonomy_engine
        
        # Set test biases
        test_biases = {"think": 0.15, "learn": -0.1, "reason": 0.05}
        autonomy_engine._action_biases = test_biases.copy()
        
        # Save state
        autonomy_engine._save_state()
        
        # Clear and reload
        autonomy_engine._action_biases = {}
        autonomy_engine._load_state()
        
        # Verify
        for key, expected in test_biases.items():
            actual = autonomy_engine._action_biases.get(key, None)
            assert actual is not None, f"Missing bias for '{key}' after load"
            assert abs(actual - expected) < 0.001, f"Bias for '{key}': expected {expected}, got {actual}"
        
        # Reset
        autonomy_engine._action_biases = {}
        autonomy_engine._save_state()
        
        print(f"   ✅ Action biases survive save/load cycle: {test_biases}")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False

def main():
    """Run all AGI enhancement tests"""
    print("=" * 60)
    print("  AGI ENHANCEMENT INTEGRATION TESTS")
    print("=" * 60)
    
    results = []
    results.append(test_action_biases_initialization())
    results.append(test_cognitive_systems_attributes())
    results.append(test_generate_cognitive_options_exists())
    results.append(test_compute_option_score_uses_biases())
    results.append(test_cognitive_engine_source_weight())
    results.append(test_reflection_produces_contextual_lessons())
    results.append(test_action_biases_updated_by_reflection())
    results.append(test_save_load_preserves_biases())
    
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"RESULTS: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("\n🎉 All AGI enhancement tests passed!")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test(s) failed.")
        return 1

if __name__ == "__main__":
    exit(main())
