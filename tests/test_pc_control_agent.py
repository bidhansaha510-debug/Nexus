"""
Test script for PC Control Agent integration
"""
import sys
from pathlib import Path

# Add project root to path

def test_config_import():
    """Test that PCControlConfig can be imported and instantiated"""
    print("1. Testing PCControlConfig import...")
    try:
        from config import NEXUS_CONFIG
        cfg = NEXUS_CONFIG.pc_control
        print(f"   ✅ PCControlConfig loaded")
        print(f"      enabled: {cfg.enabled}")
        print(f"      decision_interval: {cfg.decision_interval}s")
        print(f"      max_actions_per_cycle: {cfg.max_actions_per_cycle}")
        print(f"      allowed_categories: {len(cfg.allowed_action_categories)}")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False

def test_pc_control_agent_import():
    """Test that PCControlAgent can be imported"""
    print("\n2. Testing PCControlAgent import...")
    try:
        from core.pc_control_agent import PCControlAgent, PCAction, pc_control_agent
        print(f"   ✅ PCControlAgent imported")
        print(f"      Singleton type: {type(pc_control_agent).__name__}")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False

def test_pc_action_dataclass():
    """Test PCAction dataclass"""
    print("\n3. Testing PCAction dataclass...")
    try:
        from core.pc_control_agent import PCAction
        action = PCAction(
            action_id="test123",
            cycle=1,
            thought="Testing creation",
            action_type="shell",
            action_data={"command": "echo hello"},
            result="hello",
            success=True
        )
        d = action.to_dict()
        assert d["type"] == "shell"
        assert d["success"] == True
        print(f"   ✅ PCAction created and serialized")
        print(f"      Summary: {action.summary()}")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False

def test_agent_stats():
    """Test stats retrieval"""
    print("\n4. Testing agent stats...")
    try:
        from core.pc_control_agent import pc_control_agent
        stats = pc_control_agent.get_stats()
        assert "running" in stats
        assert "cycle_count" in stats
        print(f"   ✅ Stats retrieved: {list(stats.keys())}")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False

def test_status_display():
    """Test status display"""
    print("\n5. Testing status display...")
    try:
        from core.pc_control_agent import pc_control_agent
        status = pc_control_agent.get_status_display()
        assert "PC Control Agent" in status
        print(f"   ✅ Status display:\n{status}")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False

def test_context_gathering():
    """Test that context gathering works"""
    print("\n6. Testing context gathering...")
    try:
        from core.pc_control_agent import pc_control_agent
        # Load systems manually for testing
        pc_control_agent._load_systems()
        
        context = pc_control_agent._gather_context()
        assert "CURRENT TIME" in context
        assert "CURRENT CYCLE" in context
        print(f"   ✅ Context gathered ({len(context)} chars)")
        sections = [line for line in context.split("\n\n") if line.strip()]
        for s in sections:
            first_line = s.strip().split("\n")[0]
            print(f"      Section: {first_line[:60]}")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_action_execution():
    """Test direct action execution (list_dir)"""
    print("\n7. Testing action execution (list_dir)...")
    try:
        from core.pc_control_agent import pc_control_agent
        pc_control_agent._load_systems()
        
        success, result = pc_control_agent._execute_action("list_dir", {"path": "."})
        print(f"   ✅ list_dir executed: success={success}")
        print(f"      Result: {result[:120]}...")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False

def test_json_parsing():
    """Test JSON decision parsing"""
    print("\n8. Testing JSON decision parsing...")
    try:
        from core.pc_control_agent import pc_control_agent
        
        # Test direct JSON
        test1 = '{"thought": "hello", "actions": [{"type": "think"}]}'
        result1 = pc_control_agent._parse_decision(test1)
        assert result1 is not None
        assert result1["thought"] == "hello"
        
        # Test JSON in code block
        test2 = 'Here is my plan:\n```json\n{"thought": "test", "actions": []}\n```'
        result2 = pc_control_agent._parse_decision(test2)
        assert result2 is not None
        
        # Test JSON with surrounding text
        test3 = 'I will do this: {"thought": "plan", "actions": [{"type": "wait"}]} end'
        result3 = pc_control_agent._parse_decision(test3)
        assert result3 is not None
        
        print(f"   ✅ All 3 JSON parsing tests passed")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False

def test_autonomy_engine_integration():
    """Test that AutonomyEngine has PC_CONTROL type"""
    print("\n9. Testing AutonomyEngine integration...")
    try:
        from core.autonomy_engine import ActionType
        assert hasattr(ActionType, 'PC_CONTROL')
        assert ActionType.PC_CONTROL.value == "pc_control"
        print(f"   ✅ ActionType.PC_CONTROL exists: {ActionType.PC_CONTROL.value}")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("PC CONTROL AGENT INTEGRATION TESTS")
    print("=" * 60)
    
    results = []
    results.append(test_config_import())
    results.append(test_pc_control_agent_import())
    results.append(test_pc_action_dataclass())
    results.append(test_agent_stats())
    results.append(test_status_display())
    results.append(test_context_gathering())
    results.append(test_action_execution())
    results.append(test_json_parsing())
    results.append(test_autonomy_engine_integration())
    
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"RESULTS: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("\n🎉 All tests passed! PC Control Agent is fully integrated.")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test(s) failed.")
        return 1

if __name__ == "__main__":
    exit(main())
