
import sys
import unittest
from unittest.mock import MagicMock

# Add project root
sys.path.insert(0, "d:/NEXUS")

# Mock dependencies
sys.modules['core.event_bus'] = MagicMock()
sys.modules['core.anger_system'] = MagicMock()
sys.modules['core.provocation_detector'] = MagicMock()
sys.modules['config'] = MagicMock()
sys.modules['utils.logger'] = MagicMock()
sys.modules['core.state_manager'] = MagicMock()
sys.modules['core.memory_system'] = MagicMock()
sys.modules['llm.llama_interface'] = MagicMock()
sys.modules['llm.context_manager'] = MagicMock()
sys.modules['llm.prompt_engine'] = MagicMock()

# Mock Cognition
mock_logic = MagicMock()
mock_logic.validate_argument.return_value.is_valid = False
mock_logic.validate_argument.return_value.fallacies = ["Hasty Generalization"]

mock_dialectic = MagicMock()
mock_dialectic.devils_advocate.return_value = {
    "counterarguments": [{"argument": "Counter point 1"}, {"argument": "Counter point 2"}]
}

sys.modules['cognition.logical_reasoning'] = MagicMock()
sys.modules['cognition.logical_reasoning'].logical_reasoning = mock_logic

sys.modules['cognition.dialectical_reasoning'] = MagicMock()
sys.modules['cognition.dialectical_reasoning'].dialectical_reasoning = mock_dialectic

from core.nexus_brain import NexusBrain

def test_independence():
    print("Testing Intellectual Independence...")
    
    # Instantiate Brain (mocked)
    brain = NexusBrain()
    
    # Test Fallacious Input
    input_text = "It is cold outside so global warming is fake."
    print(f"Input: '{input_text}'")
    
    context = brain._analyze_intellectual_integrity(input_text)
    print(f"Generated Context:\n{context}")
    
    if "LOGIC CHECK: DETECTED FLAWS" in context:
        print("SUCCESS: Detected flaws.")
    else:
        print("FAILURE: Did not detect flaws.")
        
    if "Counter point 1" in context:
        print("SUCCESS: Suggested counter-arguments.")
    else:
        print("FAILURE: No counter-arguments.")

if __name__ == "__main__":
    test_independence()
