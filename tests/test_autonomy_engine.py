"""
Test script for AutonomyEngine integration
"""
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def test_autonomy_engine_import():
    """Test that AutonomyEngine can be imported"""
    print("1. Testing AutonomyEngine import...")
    try:
        from core.autonomy_engine import (
            AutonomyEngine, AutonomyState, ActionType, ActionPriority,
            ActionResult, Perception, ActionOption, ActionExecution,
            Reflection, autonomy_engine
        )
        print("   ✅ All AutonomyEngine components imported successfully")
        return True
    except ImportError as e:
        print(f"   ❌ Import failed: {e}")
        return False

def test_autonomy_engine_creation():
    """Test that autonomy_engine singleton exists"""
    print("\n2. Testing autonomy_engine singleton...")
    try:
        from core.autonomy_engine import autonomy_engine
        print(f"   ✅ autonomy_engine singleton exists: {type(autonomy_engine).__name__}")
        print(f"   State: {autonomy_engine._state.name}")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False

def test_core_init_export():
    """Test that AutonomyEngine is exported from core.__init__"""
    print("\n3. Testing core.__init__ export...")
    try:
        from core import AutonomyEngine, autonomy_engine
        print("   ✅ AutonomyEngine exported from core package")
        return True
    except ImportError as e:
        print(f"   ❌ Export failed: {e}")
        return False

def test_perception_creation():
    """Test Perception dataclass"""
    print("\n4. Testing Perception dataclass...")
    try:
        from core.autonomy_engine import Perception
        from datetime import datetime
        
        perception = Perception(
            timestamp=datetime.now(),
            primary_emotion="curiosity",
            emotion_intensity=0.6,
            cpu_usage=45.0,
            memory_usage=50.0,
            user_present=True
        )
        print(f"   ✅ Perception created: emotion={perception.primary_emotion}")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False

def test_action_option():
    """Test ActionOption dataclass"""
    print("\n5. Testing ActionOption dataclass...")
    try:
        from core.autonomy_engine import ActionOption, ActionType, ActionPriority
        
        option = ActionOption(
            action_type=ActionType.THINK,  # THINK is valid, not SELF_REFLECTION
            description="Reflect on recent interactions",
            priority=ActionPriority.NORMAL,
            predicted_benefit=0.6,
            predicted_cost=0.2
        )
        print(f"   ✅ ActionOption created: {option.action_type.value}")
        print(f"      Description: {option.description}")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False

def test_stats():
    """Test autonomy_engine stats"""
    print("\n6. Testing autonomy_engine stats...")
    try:
        from core.autonomy_engine import autonomy_engine
        
        stats = autonomy_engine.get_stats()
        print(f"   ✅ Stats retrieved:")
        print(f"      State: {stats['state']}")
        print(f"      Cycles: {stats.get('total_cycles', 0)}")
        print(f"      Actions executed: {stats.get('total_actions', 0)}")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False

def test_nexus_brain_integration():
    """Test that NexusBrain can load autonomy_engine"""
    print("\n7. Testing NexusBrain integration...")
    try:
        from core.nexus_brain import NexusBrain, nexus_brain
        
        # Check that _autonomy_engine attribute exists
        assert hasattr(nexus_brain, '_autonomy_engine'), "Missing _autonomy_engine attribute"
        print("   ✅ NexusBrain has _autonomy_engine attribute")
        
        # Try loading
        nexus_brain._load_autonomy_engine()
        print("   ✅ _load_autonomy_engine() works")
        
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("AUTONOMY ENGINE INTEGRATION TESTS")
    print("=" * 60)
    
    results = []
    results.append(test_autonomy_engine_import())
    results.append(test_autonomy_engine_creation())
    results.append(test_core_init_export())
    results.append(test_perception_creation())
    results.append(test_action_option())
    results.append(test_stats())
    results.append(test_nexus_brain_integration())
    
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"RESULTS: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("\n🎉 All tests passed! AutonomyEngine is fully integrated.")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Check the output above.")
        return 1

if __name__ == "__main__":
    exit(main())